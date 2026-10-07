"""Experiment runner: config -> answers.jsonl -> verdicts.jsonl -> summary.md.

Resumable: instances already present in answers/verdicts are skipped, so a
crashed or interrupted run can simply be restarted with the same config.
"""
from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

import yaml
from tqdm import tqdm

from .data.loader import DIMS, Instance, load_stale, select_subset
from .eval.judge import Judge, Verdict
from .eval.stats import bootstrap_ci, cell_accuracies, results_table
from .llm.gateway import Gateway, gateway_from_config
from .memory.base import MemorySystem


def _registry() -> dict[str, Callable[..., MemorySystem]]:
    from .memory.full_context import FullContext
    reg: dict[str, Callable[..., MemorySystem]] = {"full_context": FullContext}
    return reg


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


class _JsonlWriter:
    def __init__(self, path: Path):
        self.path, self._lock = path, threading.Lock()

    def write(self, obj: dict) -> None:
        with self._lock, self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def run_system_on_instance(system: MemorySystem, inst: Instance, session_mode: str = "full") -> dict:
    system.reset()
    system.begin_instance(inst)
    sessions = inst.sessions
    if session_mode == "relevant_only":  # oracle ablation, mirrors official CUPMem runner
        sessions = [inst.sessions[i] for i in inst.evidence_indices]
    system.ingest_many(sessions)
    answers, traces = {}, {}
    for d in DIMS:
        a = system.answer(inst.probes[d])
        answers[d], traces[d] = a.text, a.trace
    return {"uid": inst.uid, "type": inst.type, "answers": answers, "traces": traces}


def run(cfg: dict, out_root: str | Path = "runs", cache_dir: str | Path = "cache") -> dict:
    out = Path(out_root) / cfg["name"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")

    insts = select_subset(load_stale(cfg["data"]), **cfg.get("subset", {}))
    by_uid = {x.uid: x for x in insts}
    workers = int(cfg.get("workers", 4))
    session_mode = cfg.get("session_mode", "full")

    # ---- answer generation
    sys_cfg = cfg["system"]
    sys_gw = gateway_from_config(sys_cfg["llm"], cache_dir, log_path=out / "llm_calls.jsonl")
    factory = _registry()[sys_cfg["kind"]]
    ans_path = out / "answers.jsonl"
    done = {r["uid"] for r in _read_jsonl(ans_path)}
    todo = [x for x in insts if x.uid not in done]
    writer = _JsonlWriter(ans_path)

    def _answer(inst: Instance) -> None:
        system = factory(sys_gw, **sys_cfg.get("args", {}))
        writer.write(run_system_on_instance(system, inst, session_mode))

    _pool(_answer, todo, workers, "answering")
    answers = {r["uid"]: r for r in _read_jsonl(ans_path) if r["uid"] in by_uid}

    if not cfg.get("judge"):  # answers only; judge later by rerunning with a judge block
        summary = {"name": cfg["name"], "n_answered": len(answers), "judged": False,
                   "usage_system": sys_gw.summary()}
        (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary

    # ---- judging
    judge = Judge(gateway_from_config(cfg["judge"]["llm"], cache_dir, log_path=out / "judge_calls.jsonl"))
    ver_path = out / "verdicts.jsonl"
    judged = {r["uid"] for r in _read_jsonl(ver_path) if not r.get("error")}
    vwriter = _JsonlWriter(ver_path)
    to_judge = [by_uid[u] for u in answers if u not in judged]

    def _judge(inst: Instance) -> None:
        vwriter.write(judge.judge(inst, answers[inst.uid]["answers"]).to_dict())

    _pool(_judge, to_judge, workers, "judging")
    latest: dict[str, Verdict] = {}
    for r in _read_jsonl(ver_path):  # last verdict per uid wins (re-judged errors)
        if r["uid"] in by_uid:
            latest[r["uid"]] = Verdict.from_dict(r)
    verdicts = list(latest.values())

    summary = {
        "name": cfg["name"], "n_instances": len(verdicts),
        "judge_errors": sum(1 for v in verdicts if v.error),
        "accuracy": cell_accuracies(verdicts), "ci95": bootstrap_ci(verdicts),
        "usage_system": sys_gw.summary(), "usage_judge": judge.gw.summary(),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out / "summary.md").write_text(f"# {cfg['name']}\n\n{results_table(verdicts)}\n", encoding="utf-8")
    return summary


def _pool(fn: Callable[[Instance], None], items: list[Instance], workers: int, desc: str) -> None:
    if not items:
        return
    errors: list[tuple[str, BaseException]] = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fn, x): x.uid for x in items}
        for f in tqdm(as_completed(futs), total=len(futs), desc=desc):
            if (e := f.exception()) is not None:
                errors.append((futs[f], e))
    if errors:
        for uid, e in errors[:5]:
            print(f"[{desc}] {uid}: {type(e).__name__}: {e}")
        raise RuntimeError(f"{len(errors)} {desc} task(s) failed; rerun to resume")
