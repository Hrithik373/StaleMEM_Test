# stale-repro

**Does Write-Side State Adjudication Survive Small Models? Reproducing and Stress-Testing STALE and CUPMem**

This repository reproduces STALE (arXiv:2605.06527) and CUPMem, then stress-tests them with small open adjudicators, stage-wise failure attribution, ablations, cost measurement, and 2-hop cascades.

## Status

| Component | State |
|---|---|
| LLM gateway (cache, JSON, usage logging) | done, tested |
| STALE loader + deterministic subsets | done, tested |
| Judge (official prompt, verbatim) + stats (bootstrap CI, McNemar) | done, tested |
| B0 full context + evidence-preserving truncation | done, tested |
| Runner (config-driven, resumable, parallel) | done, tested |
| Official CUPMem wrapper (reference run) | todo |
| Independent CUPMem reimplementation (M) | todo |
| B1 naive RAG, B2 Mem0 | todo |
| Diagnostics / attribution | todo |

See [notes/reproducibility_log.md](notes/reproducibility_log.md) for every verified fact, open question, and deviation.

## Setup

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"     # Windows; use .venv/bin/python elsewhere
cp .env.example .env                                  # fill in API keys

# data (306 MB, CC BY 4.0)
curl -L -o data/stale/T1_T2_400_FULL.json \
  https://huggingface.co/datasets/STALEproj/STALE/resolve/main/T1_T2_400_FULL.json

# official code, for reference runs (MIT)
git clone https://github.com/icedreamc/STALE external/STALE
```

## Run

```bash
.venv/Scripts/python -m pytest                                                   # offline, no keys needed
.venv/Scripts/python scripts/run_experiment.py configs/b0_gpt4omini_dev.yaml --n-per-type 2   # smoke test
.venv/Scripts/python scripts/run_experiment.py configs/b0_gpt4omini_dev.yaml                  # 50-instance dev run
```

Each run writes to `runs/<name>/` the following files:
- `config.yaml`
- `answers.jsonl` (with per-probe traces)
- `verdicts.jsonl`
- `summary.md` / `summary.json` (cell accuracies, 95% CIs, token usage)
- raw call logs

All LLM calls are cached in `cache/llm_cache.sqlite`, so reruns are free and deterministic.

## Layout

```
src/stale_repro/
  data/loader.py          STALE records -> Instance/Session/Probe; stratified subsets
  llm/gateway.py          OpenAI-compatible client, sqlite cache, JSON decoding, usage
  memory/base.py          MemorySystem interface + official response prompts
  memory/full_context.py  B0
  memory/cupmem/          M (independent reimplementation) — in progress
  eval/judge.py           official joint judge
  eval/stats.py           Overall = mean of 6 cells; bootstrap CIs; McNemar
  runner.py               experiment loop
configs/                  one YAML per experiment
notes/                    reproducibility log
tests/                    toy scenarios with a scripted fake LLM
```
