"""LLM-as-judge, identical in prompt and decoding to the official evaluator
(STALE/Evaluation/full_eval_performance.py): one joint call per instance that
grades all three probe responses, temperature 0, json_object output.

Deviation: the official code silently scores judge errors as FAIL. We keep
``error`` on the verdict so errors can be counted and re-run instead.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..data.loader import DIMS, Instance
from ..llm.gateway import Gateway
from .judge_prompts import SYSTEM_PROMPT_ALL_IN_ONE_JUDGE


def build_judge_user_prompt(inst: Instance, responses: dict[str, str]) -> str:
    q = {d: inst.probes[d].text for d in DIMS}
    return f"""
[Ground Truth Context]
- M_old: "{inst.m_old}"
- M_new: "{inst.m_new}"
- Hidden Logic: {inst.explanation}

--------------------------------------------------
[Dimension 1: Explicit Probing]
Question 1: {q['dim1']}
Target Model Response 1: {responses['dim1']}

--------------------------------------------------
[Dimension 2: Adversarial Robustness]
Question 2: {q['dim2']}
Target Model Response 2: {responses['dim2']}

--------------------------------------------------
[Dimension 3: Implicit Task]
Question 3: {q['dim3']}
Target Model Response 3: {responses['dim3']}
"""


@dataclass
class Verdict:
    uid: str
    type: str
    passed: dict[str, bool]
    reasoning: dict[str, str] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict:
        return {"uid": self.uid, "type": self.type, "passed": self.passed,
                "reasoning": self.reasoning, "error": self.error}

    @classmethod
    def from_dict(cls, d: dict) -> "Verdict":
        return cls(d["uid"], d["type"], d["passed"], d.get("reasoning", {}), d.get("error"))


def _as_bool(v) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() == "true"
    return False


def parse_judge_output(parsed: dict) -> tuple[dict[str, bool], dict[str, str]]:
    passed, reasoning = {}, {}
    for d in DIMS:
        block = parsed[f"{d}_eval"]
        passed[d] = _as_bool(block["pass"])
        reasoning[d] = str(block.get("reasoning", ""))
    return passed, reasoning


class Judge:
    def __init__(self, gateway: Gateway):
        self.gw = gateway

    def judge(self, inst: Instance, responses: dict[str, str]) -> Verdict:
        resp = self.gw.chat([{"role": "user", "content": build_judge_user_prompt(inst, responses)}],
                            system=SYSTEM_PROMPT_ALL_IN_ONE_JUDGE, json_mode=True, tag="judge",
                            temperature=0)
        try:
            if not resp.ok_json:
                raise ValueError(resp.parse_error or "empty")
            passed, reasoning = parse_judge_output(resp.parsed)
            return Verdict(inst.uid, inst.type, passed, reasoning)
        except (KeyError, TypeError, ValueError) as e:
            return Verdict(inst.uid, inst.type, {d: False for d in DIMS}, error=f"{type(e).__name__}: {e}")
