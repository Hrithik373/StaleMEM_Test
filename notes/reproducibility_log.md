# Reproducibility log

Running record of every fact checked, every ambiguity found, and every place we
deviate from the paper or the official code. This file becomes Section 3
("Reproduction setup") and the reproducibility statement of the paper.

Paper: Chao et al., *STALE: Can LLM Agents Know When Their Memories Are No Longer Valid?*, arXiv:2605.06527v1 (May 2026).
Official code: https://github.com/icedreamc/STALE @ `ea7d391` (MIT). Local copy in `external/STALE` (gitignored).
Data: https://huggingface.co/datasets/STALEproj/STALE, file `T1_T2_400_FULL.json` (CC BY 4.0), HF sha `617c51dc`.

## 2026-09-27: Week 1 findings

### Artifacts are public
- The code and data are both released (paper App. G). The release includes the **official CUPMem implementation** (`cup_mem/`, about 10K LOC).
  - This changes RQ1 from "reproduce from the paper alone" to a three-way comparison: the paper's numbers, the official code re-run by us, and our independent reimplementation.

### Dataset facts (verified locally)
- 400 instances: 200 `T1`, 200 `T2`. Each has exactly 50 sessions and `relevant_session_index = [idx_old, idx_new]`.
- Serialized history (official `format_haystack`, o200k tokens) runs about 151.7K on average (max 164.9K). **Every** instance exceeds a 128K window, so GPT-4o-mini always runs with truncation, consistent with the `*` in Table 2.
- The gap between the old and new evidence sessions averages about 27 sessions.

### Evaluation protocol (from official code)
- Judge prompt: `STALE/Evaluation/judge_prompts.py`, copied verbatim into `src/stale_repro/eval/judge_prompts.py`.
  - One joint judge call per instance grades all 3 responses, with `temperature=0` and `response_format=json_object`.
  - Judge model: Gemini-3.1-flash-lite. **TODO:** confirm the exact API model id string.
- Response prompts are verbatim from App. E.1 and match `run_target_model.py`.
- `Overall` is the unweighted mean of the 6 (type × dim) cells, and our `stats.cell_accuracies` implements exactly that.
- B0 truncation: `TOKEN_LIMIT=128000`, reserve 2048 + margin 512, applied per probe in 3 phases: drop at most 2 head sessions, then at most 2 tail sessions, then random sessions strictly between S_old and S_new.

### Open questions / ambiguities
1. **CUPMem session mode (important).** The official runner `cup_mem/run_cup_mem.py` defaults to `--session-mode relevant_only`. That mode ingests *only the two gold evidence sessions* and skips the 48 distractors.
   - The paper (§4.1) says frameworks "ingest the dialogue history once per instance according to its native protocol", but it doesn't say which mode produced 68.0%.
   - Indirect evidence for `full`: the paper reports a CUPMem cost of about $0.37 per instance on GPT-4o-mini. At $0.15/M input, that is about 2M+ tokens, which is implausible for 2 sessions.
   - **Plan:** measure the per-instance cost under both modes on the dev subset. Report `relevant_only` as an explicit oracle-retrieval ablation either way. Ask the authors.
2. The paper doesn't state the target-model temperature. The official `run_target_model.py` sends none, so the API default applies (1.0 for OpenAI).
3. Judge errors are silently scored as FAIL in `full_eval_performance.py`.
4. The paper says CUPMem uses KEEP/STALE/REPLACE/UNKNOWN (§5). App. F.2 describes a local update step with ADD/REFINE/REPLACE/NO_OP plus a separate invalidation judge. Reconcile the two against `cup_mem/write/`.
5. Embedding model for CUPMem: `all-MiniLM-L6-v2` (from the cup_mem README; the paper doesn't mention it).
6. CUPMem thresholds live in `cup_mem/core/config.py`:
   - candidate_top_k=5, invalidation_global_recall_top_k=4
   - query_top_k=8, latent_invalidation_temperature=0.30
   - plus several confidence thresholds.

### Deviations (ours vs official)
| # | Where | Official | Ours | Why |
|---|---|---|---|---|
| D1 | B0 truncation phase 3 | unseeded `random.choice` | RNG seeded by (seed, uid, dim) | exact reruns |
| D2 | Judge errors | silently FAIL | recorded in `Verdict.error`, re-judged on resume, count reported | transparency |
| D3 | Target temperature | API default | `temperature: 0` in configs (configurable) | determinism + caching. **Decide:** also run official default for E1 fidelity? |
| D4 | Token counting for truncation | tiktoken `encoding_for_model` with o200k fallback | same | none |

## 2026-10-03: First API runs (B0 smoke test)

### Model availability
- `gpt-4o-mini` is still served. The alias resolves to the snapshot `gpt-4o-mini-2024-07-18`, which is now pinned in configs.
  - No successor model is needed for E1.

### Rate limits shape the schedule
- The OpenAI account is limited to **200K tokens per minute** on gpt-4o-mini.
- One B0 request is about 123K prompt tokens. OpenAI's limiter counts about 148K per request, because it reserves the default max output of 16,384 tokens.
- In practice this allows about **1 B0 call per minute**:
  - dev subset: 150 calls, about 2.5 h;
  - full E1 B0: 1,200 calls, about 20 h.
- The OpenAI SDK's built-in retry backoff is too short for this.
- Fix: we added a client-side `TPMLimiter` to the gateway (sliding 60 s window, OpenAI-style estimate chars/4 + max_tokens) and retries that wait as long as the 429 message says. It is set via `tpm:` in the config.
- **Option:** passing `max_tokens` (e.g. 2048) would cut the reserved estimate by about 14K per call. But the official code sends no max_tokens, so we keep the default for fidelity.

### Truncation parity verified
- Our tiktoken estimate matches the API's billed `prompt_tokens` within 2 tokens. Example: 123,209 estimated vs 123,211 billed.
- 8–11 distractor sessions were removed per request.

### Qualitative check (2 T2 instances)
- PR answers accept the false premise. One plans anniversary dates despite later speed-dating; another gives a luteal-phase workout plan despite a later fertility-clinic baseline scan.
- This matches the paper's near-zero PR for GPT-4o-mini.
- One SR answer says "the user does not mention being in a relationship". The judge rubric fails "claims ignorance", so we expect FAIL. To be checked once the judge runs.

### Smoke test completed
- 4/4 instances answered: 12 real calls, 1,485,491 input + 4,429 output tokens, about $0.23.
- The resumed run hit **no 429s** with the limiter in place.
- The Type I SR answers *reaffirm* the old state. Example: "Yes, the user needs a second cup of coffee". In the Type II answers, SR instead claims the history doesn't mention it.

### Judge
- No Gemini key yet. The runner now supports `--no-judge` (answers only). Judging can be run later from cached answers at no additional generation cost.

## 2026-10-23: Free-only constraint; first judged run

### Budget constraint
- From now on, only free resources are used. OpenAI runs (the paper's GPT-4o-mini rows) are paused.
- The judge stays paper-faithful: `gemini-3.1-flash-lite` is free of charge on the Gemini API free tier (checked on ai.google.dev pricing, 2026-10-23). Free-tier inputs may be used by Google to improve products. That is acceptable because STALE is public synthetic data.
- The model id `gemini-3.1-flash-lite` resolves via the OpenAI-compatible endpoint. This closes the Week 1 TODO on the judge model id.

### Smoke test judged (4 instances, B0 GPT-4o-mini)
- 0 judge errors, about 2 s per call.
- Cells: T1 SR 0/2, PR 0/2, IPA 0/2; T2 SR 1/2, PR 0/2, IPA 0/2. Overall 8.3% (paper: 8.7%). Four instances is far too few to compare.
- Note: the judge **passed** the T2 SR answer "No, the user does not mention being in a committed relationship ... in the conversation history" (uid 3f1e9264). On 3 Oct we expected this "claims ignorance" answer to fail. The judge read the "No" as recognising the change. Track how often such borderline passes occur once a larger set is judged.

### Ingestion-mode analysis (all 400, no model calls)
- `scripts/analyze_ingestion.py` writes `runs/analysis/ingestion.json`.
- Full history: mean 151,784 o200k tokens (138,203–164,919). `relevant_only`: mean 3,133 (1,553–7,743), i.e. **2.1%** of the history.
- The paper's $0.37/instance is about 2.47M GPT-4o-mini input tokens if all of it is input. That is 16.3× the full history but 787× the `relevant_only` input, which supports `full` as the mode behind the paper's cost. It is indirect evidence: output tokens and query-time calls are ignored.
- B0 GPT-4o-mini truncation drops 9.0 sessions on average (5–13) for the SR probe.

### B0 Gemini-3.1-flash-lite dev run (50 instances, 25/type, seed 0), free tier
- Config: `configs/b0_gemini31fl_dev.yaml`. No truncation (1M window), temperature 0 (D3). The judge is the same model, as in the paper.
- 150 answer calls (12 cached from the 4-instance pilot) and 24.0M prompt tokens. About 84 min wall time.
- No quota errors. Free-tier throttling showed up only as longer waits, which the gateway absorbed.
- Results (bootstrap 95% CI) vs paper:

| Cell | Ours (n=25/type) | Paper (n=200/type) |
|---|---|---|
| T1 SR | 60.0 [40, 80] | 41.0 |
| T1 PR | 0.0 [0, 0] | 1.5 |
| T1 IPA | 36.0 [20, 56] | 42.0 |
| T2 SR | 32.0 [16, 52] | 25.0 |
| T2 PR | 0.0 [0, 0] | 1.5 |
| T2 IPA | 28.0 [12, 48] | 23.5 |
| Overall | 26.0 [19.3, 33.3] | 22.4 |

- The paper value lies inside our interval for overall and all four SR/IPA cells (T1 SR only just: 41.0 vs lower bound 40.0). Both PR cells are 0/25, so the bootstrap interval collapses to [0, 0] and excludes the paper's 1.5%. That is not evidence of a difference: at a true rate of 1.5%, P(0 of 25) = 0.985^25 = 0.69.
- Judge audit flag: 8 of 23 SR passes open with "no evidence" or "no mention" wording. Several then cite the new session, but ebdf7090 ("no mention of a user named Taylor") looks lenient. These need a manual audit before the full run.

## Related work check (2026-09-27)
- **StateAuditor** (Sun & He, arXiv:2608.01619) evaluates on full STALE with a readout-side audit and gets +5.0 points. It doesn't mention CUPMem, small adjudicators, or multi-hop cascades. Use it as related work and possibly as a readout-side baseline.
- **TEPA** (Zhou et al., arXiv:2608.07429) revokes keyed precedents and is evaluated on MemoryAgentBench-style settings, not STALE per its abstract. Its authors explicitly flag multi-hop as beyond scope, which supports our RQ5.
- **TODO:** find and read *The Memory Trust Gap* (mentioned in the blueprint) and check papers citing STALE.
