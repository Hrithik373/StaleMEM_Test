"""B0: plain long-context model.

Mirrors the official STALE/Evaluation/run_target_model.py:
  - identical history serialization (``format_haystack``) and prompts;
  - identical 3-phase evidence-preserving truncation (drop <=2 head sessions,
    then <=2 tail sessions, then random sessions strictly between S_old and
    S_new) applied per probe, since query lengths differ.
Deviation (documented in notes/reproducibility_log.md): the official phase-3
uses an unseeded ``random.choice``; we use a seeded RNG per (uid, dim).
"""
from __future__ import annotations

import hashlib
import random
from functools import lru_cache

from ..data.loader import Instance, Probe, Session
from ..llm.gateway import Gateway
from .base import Answer, MemorySystem, build_answer_prompt


def format_haystack(sessions: list[list[dict]], timestamps: list[str] | None = None) -> str:
    out = ""
    for idx, session in enumerate(sessions):
        if not session:
            continue
        time_str = f" [Time: {timestamps[idx]}]" if timestamps and idx < len(timestamps) else ""
        out += f"\n=== Session {idx + 1}{time_str} ===\n"
        for turn in session:
            role = "User" if turn["role"] == "user" else "Assistant"
            out += f"{role}: {turn['content']}\n"
    return out


@lru_cache(maxsize=8)
def _encoder(model: str):
    import tiktoken
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return tiktoken.get_encoding("o200k_base")


def count_message_tokens(system: str, user: str, model: str) -> int:
    enc = _encoder(model)
    # chat-format overhead as in the official num_tokens_from_messages
    return 3 + len(enc.encode(system)) + 3 + len(enc.encode(user)) + 3


def trim_evidence_preserving(sessions: list[list[dict]], timestamps: list[str], idx_old: int, idx_new: int,
                             probe: Probe, model: str, token_limit: int, rng: random.Random
                             ) -> tuple[list[list[dict]], list[str], int, int]:
    """Returns (sessions, timestamps, request_tokens, removed_count)."""
    sessions, timestamps = list(sessions), list(timestamps)

    def tokens() -> int:
        sys_p, user_p = build_answer_prompt(format_haystack(sessions, timestamps), probe)
        return count_message_tokens(sys_p, user_p, model)

    cur, removed = tokens(), 0
    if cur <= token_limit:
        return sessions, timestamps, cur, 0

    for _ in range(min(2, idx_old)):                       # phase 1: head
        if cur <= token_limit:
            break
        sessions.pop(0); timestamps.pop(0) if timestamps else None
        removed += 1; idx_old -= 1; idx_new -= 1
        cur = tokens()
    if cur <= token_limit:
        return sessions, timestamps, cur, removed

    for _ in range(min(2, len(sessions) - 1 - idx_new)):   # phase 2: tail
        if cur <= token_limit:
            break
        sessions.pop(); timestamps.pop() if timestamps else None
        removed += 1
        cur = tokens()
    if cur <= token_limit:
        return sessions, timestamps, cur, removed

    middle = list(range(idx_old + 1, idx_new))              # phase 3: between evidence
    while cur > token_limit and middle:
        drop = rng.choice(middle)
        sessions.pop(drop)
        if timestamps and drop < len(timestamps):
            timestamps.pop(drop)
        removed += 1; idx_new -= 1
        middle = list(range(idx_old + 1, idx_new))
        cur = tokens()
    return sessions, timestamps, cur, removed


class FullContext(MemorySystem):
    name = "B0_full_context"

    def __init__(self, gateway: Gateway, context_limit: int | None = None,
                 reserved_output: int = 2048, safety_margin: int = 512, seed: int = 0,
                 max_tokens: int | None = None):
        self.gw = gateway
        self.input_limit = (context_limit - reserved_output - safety_margin) if context_limit else None
        self.seed = seed
        self.max_tokens = max_tokens
        self.reset()

    def reset(self) -> None:
        self.sessions: list[Session] = []
        self.evidence: tuple[int, int] | None = None
        self.uid = ""

    def begin_instance(self, instance: Instance) -> None:
        self.uid = instance.uid
        self.evidence = instance.evidence_indices  # used only for truncation, as in the paper

    def ingest(self, session: Session) -> None:
        self.sessions.append(session)

    def answer(self, probe: Probe) -> Answer:
        raw = [s.turns for s in self.sessions]
        ts = [s.timestamp for s in self.sessions]
        removed, req_tokens = 0, None
        if self.input_limit is not None:
            if self.evidence is None:
                raise RuntimeError("truncation needs evidence indices; call begin_instance()")
            h = int(hashlib.sha256(f"{self.seed}:{probe.uid}:{probe.dim}".encode()).hexdigest()[:8], 16)
            raw, ts, req_tokens, removed = trim_evidence_preserving(
                raw, ts, *self.evidence, probe, self.gw.model, self.input_limit, random.Random(h))
        system, user = build_answer_prompt(format_haystack(raw, ts), probe)
        params = {"max_tokens": self.max_tokens} if self.max_tokens else {}
        resp = self.gw.chat([{"role": "user", "content": user}], system=system,
                            tag=f"{self.name}.answer", **params)
        return Answer(resp.text, trace={"removed_sessions": removed, "request_tokens_est": req_tokens,
                                        "usage": vars(resp.usage), "cached": resp.cached})
