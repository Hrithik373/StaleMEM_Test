"""Scoring and statistics.

``Overall`` follows the paper: the unweighted mean of the six (type x dim) cell
accuracies. CIs are percentile bootstraps that resample *instances* within each
type (the three probes of one instance are not independent).
"""
from __future__ import annotations

from math import comb

import numpy as np

from ..data.loader import DIMS, DIM_NAMES, TYPE_NAMES
from .judge import Verdict

TYPES = ("T1", "T2")
CELLS = [(t, d) for t in TYPES for d in DIMS]


def _matrix(verdicts: list[Verdict], t: str) -> np.ndarray:
    rows = [[v.passed[d] for d in DIMS] for v in verdicts if v.type == t]
    return np.asarray(rows, dtype=float).reshape(-1, len(DIMS))


def cell_accuracies(verdicts: list[Verdict]) -> dict[str, float]:
    out: dict[str, float] = {}
    for t in TYPES:
        m = _matrix(verdicts, t)
        for j, d in enumerate(DIMS):
            out[f"{t}.{d}"] = float(m[:, j].mean()) if len(m) else float("nan")
    present = [v for v in out.values() if not np.isnan(v)]
    out["overall"] = float(np.mean(present)) if present else float("nan")
    return out


def bootstrap_ci(verdicts: list[Verdict], n_boot: int = 2000, alpha: float = 0.05,
                 seed: int = 0) -> dict[str, tuple[float, float]]:
    rng = np.random.default_rng(seed)
    mats = {t: _matrix(verdicts, t) for t in TYPES}
    samples: dict[str, list[float]] = {f"{t}.{d}": [] for t, d in CELLS} | {"overall": []}
    for _ in range(n_boot):
        cells = []
        for t in TYPES:
            m = mats[t]
            if not len(m):
                continue
            bm = m[rng.integers(0, len(m), len(m))].mean(axis=0)
            for j, d in enumerate(DIMS):
                samples[f"{t}.{d}"].append(bm[j])
                cells.append(bm[j])
        samples["overall"].append(float(np.mean(cells)))
    lo, hi = 100 * alpha / 2, 100 * (1 - alpha / 2)
    return {k: (float(np.percentile(v, lo)), float(np.percentile(v, hi))) for k, v in samples.items() if v}


def mcnemar_exact(a: list[bool], b: list[bool]) -> dict:
    """Exact two-sided McNemar test on paired binary outcomes."""
    if len(a) != len(b):
        raise ValueError("paired outcomes must have equal length")
    n01 = sum(1 for x, y in zip(a, b) if x and not y)
    n10 = sum(1 for x, y in zip(a, b) if y and not x)
    n = n01 + n10
    if n == 0:
        return {"a_only": 0, "b_only": 0, "p_value": 1.0}
    k = min(n01, n10)
    p = min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)
    return {"a_only": n01, "b_only": n10, "p_value": p}


def paired_outcomes(va: list[Verdict], vb: list[Verdict], dim: str | None = None,
                    type_: str | None = None) -> tuple[list[bool], list[bool]]:
    ia, ib = {v.uid: v for v in va}, {v.uid: v for v in vb}
    common = sorted(set(ia) & set(ib))
    dims = [dim] if dim else list(DIMS)
    a, b = [], []
    for u in common:
        if type_ and ia[u].type != type_:
            continue
        for d in dims:
            a.append(ia[u].passed[d]); b.append(ib[u].passed[d])
    return a, b


def results_table(verdicts: list[Verdict], ci: bool = True, **boot_kw) -> str:
    acc = cell_accuracies(verdicts)
    cis = bootstrap_ci(verdicts, **boot_kw) if ci else {}
    head = ["n"] + [f"{TYPE_NAMES[t]} {DIM_NAMES[d]}" for t, d in CELLS] + ["Overall"]
    keys = [f"{t}.{d}" for t, d in CELLS] + ["overall"]

    def fmt(k: str) -> str:
        s = f"{100 * acc[k]:.1f}"
        if k in cis:
            s += f" [{100 * cis[k][0]:.1f}, {100 * cis[k][1]:.1f}]"
        return s

    n_err = sum(1 for v in verdicts if v.error)
    row = [f"{len(verdicts)}" + (f" ({n_err} judge err)" if n_err else "")] + [fmt(k) for k in keys]
    return "| " + " | ".join(head) + " |\n|" + "---|" * len(head) + "\n| " + " | ".join(row) + " |"
