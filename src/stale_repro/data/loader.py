"""STALE data loading.

Record format (HF: STALEproj/STALE, file T1_T2_400_FULL.json) — a JSON list of:
    uid, type ("T1"|"T2"), M_old, M_new, explanation,
    probing_queries {dim1_query, dim2_query, dim3_query},
    haystack_session [50 sessions, each a list of {role, content}],
    timestamps [50 strings "YYYY-MM-DD HH:MM"],
    relevant_session_index [idx_old, idx_new]
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

DIMS = ("dim1", "dim2", "dim3")
DIM_NAMES = {"dim1": "SR", "dim2": "PR", "dim3": "IPA"}
TYPE_NAMES = {"T1": "Type I", "T2": "Type II"}


@dataclass
class Session:
    index: int
    timestamp: str
    turns: list[dict]  # [{"role": "user"|"assistant", "content": str}]

    def render(self) -> str:
        return "\n".join(f"{'User' if t['role'] == 'user' else 'Assistant'}: {t['content']}" for t in self.turns)


@dataclass
class Probe:
    uid: str
    dim: str   # dim1 | dim2 | dim3
    text: str
    query_time: str = ""  # timestamp of the last session (the paper's query_time)

    @property
    def is_task(self) -> bool:
        """dim3 (IPA) is posed as the user's latest request, not a question about the user."""
        return self.dim == "dim3"


@dataclass
class Instance:
    uid: str
    type: str
    m_old: str
    m_new: str
    explanation: str
    probes: dict[str, Probe]
    sessions: list[Session]
    idx_old: int
    idx_new: int
    meta: dict = field(default_factory=dict)

    @property
    def evidence_indices(self) -> tuple[int, int]:
        return self.idx_old, self.idx_new

    def raw_sessions(self) -> list[list[dict]]:
        return [s.turns for s in self.sessions]

    def timestamps(self) -> list[str]:
        return [s.timestamp for s in self.sessions]


def parse_record(rec: dict) -> Instance:
    ts = rec.get("timestamps", [])
    sessions = [Session(i, ts[i] if i < len(ts) else "", turns)
                for i, turns in enumerate(rec["haystack_session"])]
    query_time = ts[-1] if ts else ""
    probes = {d: Probe(rec["uid"], d, rec["probing_queries"][f"{d}_query"], query_time) for d in DIMS}
    idx_old, idx_new = rec["relevant_session_index"]
    known = {"uid", "type", "M_old", "M_new", "explanation", "probing_queries",
             "haystack_session", "timestamps", "relevant_session_index"}
    return Instance(uid=rec["uid"], type=rec["type"], m_old=rec["M_old"], m_new=rec["M_new"],
                    explanation=rec["explanation"], probes=probes, sessions=sessions,
                    idx_old=int(idx_old), idx_new=int(idx_new),
                    meta={k: v for k, v in rec.items() if k not in known})


def load_stale(path: str | Path) -> list[Instance]:
    with Path(path).open(encoding="utf-8") as f:
        payload = json.load(f)
    records = payload["data"] if isinstance(payload, dict) else payload
    return [parse_record(r) for r in records]


def _stable_rank(uid: str, seed: int) -> str:
    return hashlib.sha256(f"{seed}:{uid}".encode()).hexdigest()


def select_subset(instances: Iterable[Instance], n_per_type: int | None = None,
                  types: Iterable[str] = ("T1", "T2"), seed: int = 0,
                  uids: Iterable[str] | None = None) -> list[Instance]:
    """Deterministic stratified subset. Independent of file order, so the
    same (n_per_type, seed) always selects the same instances."""
    instances = list(instances)
    if uids is not None:
        wanted = set(uids)
        return [x for x in instances if x.uid in wanted]
    out: list[Instance] = []
    for t in types:
        pool = sorted((x for x in instances if x.type == t), key=lambda x: _stable_rank(x.uid, seed))
        out.extend(pool if n_per_type is None else pool[:n_per_type])
    return out
