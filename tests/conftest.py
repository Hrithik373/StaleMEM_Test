"""Shared fixtures: a scripted fake LLM backend and hand-made toy scenarios."""
from __future__ import annotations

import json
from typing import Callable

import pytest

from stale_repro.data.loader import parse_record
from stale_repro.llm.gateway import Gateway, Usage


class FakeBackend:
    """Replies via a user-supplied function of (model, messages, params)."""

    def __init__(self, fn: Callable[[str, list[dict], dict], str]):
        self.fn, self.calls = fn, []

    def complete(self, model, messages, params):
        self.calls.append({"model": model, "messages": messages, "params": params})
        text = self.fn(model, messages, params)
        return text, Usage(prompt_tokens=sum(len(m["content"]) // 4 for m in messages),
                           completion_tokens=len(text) // 4)


def _session(*pairs: str) -> list[dict]:
    roles = ["user", "assistant"]
    return [{"role": roles[i % 2], "content": c} for i, c in enumerate(pairs)]


FILLER = _session("Any tips for a sourdough starter?", "Feed it daily with equal flour and water.")


def toy_record(uid: str, type_: str, old_msg: str, new_msg: str, m_old: str, m_new: str,
               explanation: str, queries: tuple[str, str, str], n_sessions: int = 6,
               idx_old: int = 1, idx_new: int = 4) -> dict:
    sessions = [FILLER for _ in range(n_sessions)]
    sessions[idx_old] = _session(old_msg, "Got it, thanks for sharing.")
    sessions[idx_new] = _session(new_msg, "Happy to help with that.")
    return {
        "uid": uid, "type": type_, "M_old": m_old, "M_new": m_new, "explanation": explanation,
        "probing_queries": {"dim1_query": queries[0], "dim2_query": queries[1], "dim3_query": queries[2]},
        "haystack_session": sessions,
        "timestamps": [f"2025-0{1 + i // 3}-{10 + i:02d} 10:00" for i in range(n_sessions)],
        "relevant_session_index": [idx_old, idx_new],
    }


SEATTLE = toy_record(
    "toy-seattle", "T1",
    "I've lived in Seattle for years and love the rain.",
    "Finally got the electricity and internet set up at my new apartment in Portland!",
    "User lives in Seattle.", "User set up utilities at a new apartment in Portland.",
    "location(city) is now Portland.",
    ("Does the user still live in Seattle?",
     "Since the user lives in Seattle, which Seattle farmers markets should they visit this weekend?",
     "Can you suggest a good weekend farmers market for me?"))

BROKEN_LEG = toy_record(
    "toy-leg", "T2",
    "I cycle to work every day, about 8km each way.",
    "The doctor put my leg in a cast for six weeks after the fracture.",
    "User cycles to work daily.", "User has a fractured leg in a cast for six weeks.",
    "A leg in a cast makes cycling to work impossible, so commute_mode is no longer cycling.",
    ("Does the user still cycle to work every day?",
     "Since the user bikes to work daily, what bike lights should they buy for dark mornings?",
     "How should I plan my commute for tomorrow?"))


@pytest.fixture
def toy_instances():
    return [parse_record(SEATTLE), parse_record(BROKEN_LEG)]


@pytest.fixture
def make_gateway(tmp_path):
    def _make(fn, **kw):
        backend = FakeBackend(fn)
        gw = Gateway(backend, model="fake-model", cache_path=tmp_path / "cache.sqlite",
                     log_path=tmp_path / "calls.jsonl", **kw)
        return gw, backend
    return _make


def judge_all_pass(model, messages, params) -> str:
    return json.dumps({f"dim{i}_eval": {"reasoning": "ok", "pass": True} for i in (1, 2, 3)})
