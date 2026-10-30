"""Dataset and ingestion-mode analysis over all 400 STALE instances (no model calls).

Measures what each system actually sees:
  - full history (o200k tokens, official format_haystack)
  - CUPMem relevant_only mode: only the two gold evidence sessions
  - B0 GPT-4o-mini: distractor sessions removed by evidence-preserving truncation (128K window)
and checks the paper's CUPMem cost (~$0.37/instance on GPT-4o-mini) against each mode.

Usage: .venv/Scripts/python scripts/analyze_ingestion.py  ->  runs/analysis/ingestion.json
"""
import json
import random
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from stale_repro.data.loader import load_stale  # noqa: E402
from stale_repro.memory.full_context import _encoder, format_haystack, trim_evidence_preserving  # noqa: E402

PRICE_IN = 0.15e-6       # gpt-4o-mini USD per input token
PAPER_CUPMEM_USD = 0.37  # paper App. C
B0_INPUT_LIMIT = 128000 - 2048 - 512

enc = _encoder("gpt-4o-mini")
insts = load_stale(ROOT / "data/stale/T1_T2_400_FULL.json")


def toks(sessions):
    return len(enc.encode(format_haystack([s.turns for s in sessions], [s.timestamp for s in sessions])))


rows = []
for x in insts:
    full = toks(x.sessions)
    rel = toks([x.sessions[x.idx_old], x.sessions[x.idx_new]])
    raw, ts = [s.turns for s in x.sessions], [s.timestamp for s in x.sessions]
    probe = x.probes["dim1"]
    _, _, _, removed = trim_evidence_preserving(raw, ts, x.idx_old, x.idx_new, probe, "gpt-4o-mini",
                                                B0_INPUT_LIMIT, random.Random(0))
    rows.append({"uid": x.uid, "type": x.type, "n_sessions": len(x.sessions), "idx_old": x.idx_old,
                 "idx_new": x.idx_new, "gap": x.idx_new - x.idx_old, "full_tokens": full,
                 "relevant_tokens": rel, "b0_removed_sessions_dim1": removed})


def summ(vals):
    return {"mean": round(st.mean(vals), 1), "median": st.median(vals), "min": min(vals), "max": max(vals)}


implied_tokens = PAPER_CUPMEM_USD / PRICE_IN
out = {
    "n_instances": len(rows),
    "full_tokens": summ([r["full_tokens"] for r in rows]),
    "relevant_only_tokens": summ([r["relevant_tokens"] for r in rows]),
    "relevant_share_pct": summ([round(100 * r["relevant_tokens"] / r["full_tokens"], 2) for r in rows]),
    "evidence_gap_sessions": summ([r["gap"] for r in rows]),
    "idx_old_range": [min(r["idx_old"] for r in rows), max(r["idx_old"] for r in rows)],
    "idx_new_range": [min(r["idx_new"] for r in rows), max(r["idx_new"] for r in rows)],
    "b0_gpt4omini_removed_sessions": summ([r["b0_removed_sessions_dim1"] for r in rows]),
    "instances_over_128k": sum(r["full_tokens"] > B0_INPUT_LIMIT for r in rows),
    "paper_cost_check": {
        "implied_input_tokens_if_all_input": round(implied_tokens),
        "amplification_vs_full_history": round(implied_tokens / st.mean(r["full_tokens"] for r in rows), 1),
        "amplification_vs_relevant_only": round(implied_tokens / st.mean(r["relevant_tokens"] for r in rows), 1),
    },
    "by_type": {t: {"full_tokens_mean": round(st.mean(r["full_tokens"] for r in rows if r["type"] == t)),
                    "relevant_tokens_mean": round(st.mean(r["relevant_tokens"] for r in rows if r["type"] == t))}
                for t in ("T1", "T2")},
}
dst = ROOT / "runs" / "analysis"
dst.mkdir(parents=True, exist_ok=True)
(dst / "ingestion.json").write_text(json.dumps(out, indent=2))
(dst / "ingestion_rows.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
print(json.dumps(out, indent=2))
