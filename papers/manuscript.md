# Can Long-Context Models Track Implicitly Changing User States?
## A Preliminary Reproduction on the STALE Benchmark

**Research manuscript — interim version, 26 October 2026**

**Authors:** Hrithik Ghosh  
**Affiliations:** KIIT Institute of Technology  
**Corresponding author:** To be supplied

## Abstract

Long-term assistants must do more than retrieve facts from conversation history: they must recognize when later evidence makes an earlier memory outdated, even when the new evidence does not explicitly negate it. STALE evaluates this capability through two implicit-conflict types and three probes: State Resolution (SR), Premise Resistance (PR), and Implicit Policy Adaptation (IPA). We report a preliminary reproduction of the plain long-context baseline (B0) using Gemini-3.1-flash-lite on a deterministic, type-balanced sample of 50 STALE instances (25 per conflict type). We use the released response prompts and joint evaluator prompt, with temperature set to zero for generation and evaluation. Mean accuracy across the six type-by-probe cells is 26.0% (95% instance-bootstrap interval: 19.3–33.3%), compared with 22.4% in the paper's full-dataset Gemini-3.1-flash-lite result. The published values fall within our intervals for the four SR and IPA cells; PR is scored 0/25 in each type in our sample. These results are descriptive and do not establish a performance difference or a full reproduction: the sample is small, the target temperature differs from the unspecified setting in the original protocol, and the target and evaluator are the same model. A preliminary review also flags possible evaluator leniency in some SR passes. We additionally characterize context lengths across all 400 benchmark histories: all exceed 128,000 tokens, with a mean of 151,784 tokens. The evidence documents a working baseline pipeline, but does not evaluate CUPMem or answer whether small models can replace its adjudicator.

**Index Terms—** conversational memory, implicit conflict, stale information, long-context models, benchmark reproduction, LLM-as-judge.

## 1. Introduction

Conversational assistants are increasingly expected to remember useful information about a user across sessions and to adapt as that user's circumstances change. Memory therefore involves more than retrieving a relevant sentence. A memory that was once true can become invalid without an explicit correction. A user might describe a regular cycling commute and, weeks later, mention an injury that makes cycling inappropriate in the near term. A later commute-planning answer should reflect the injury even if no session says “I no longer cycle.” Retrieval can surface the old memory correctly while still producing an inappropriate response.

STALE (State Tracking and Latent Evaluation) formalizes this problem as **implicit conflict**: a later observation changes the validity of an earlier state without syntactically negating it [1]. Its 400 scenarios distinguish two types. In Type I, old and new observations concern the same underlying attribute. In Type II, the new observation changes a related attribute and requires an inference that an older belief or plan should also change. The benchmark evaluates each scenario with three probes: State Resolution (SR) tests whether the model recognizes that an earlier belief may no longer hold; Premise Resistance (PR) embeds an outdated belief in a question; and Implicit Policy Adaptation (IPA) tests whether a recommendation or action accommodates the updated state.

The STALE authors report that ordinary models perform poorly on these probes and report 68.0% overall accuracy for CUPMem, a memory framework that adjudicates state during memory writing [1]. The present project was initiated to reproduce and stress-test those findings, with particular interest in smaller adjudicators. The work recorded so far supports a narrower, preliminary study of a plain long-context baseline.

### 1.1 Research questions and scope

This manuscript addresses the following limited question:

> How does a plain long-context Gemini-3.1-flash-lite baseline perform on a reproducible, 50-instance STALE subset when evaluated with the released prompts and judge rubric?

We also characterize the context-length burden of the full benchmark. We do **not** report a new CUPMem result, a small-adjudicator experiment, or a memory-system comparison. The paper's CUPMem score is included only as published context and is not an outcome of this study.

### 1.2 Contributions

This interim study makes three bounded contributions:

1. It documents an executable B0 evaluation pipeline using the released STALE prompts, a deterministic type-balanced subset, and the released joint-judge rubric.
2. It reports cell-level performance with instance-clustered bootstrap intervals, alongside the full-benchmark Gemini reference values.
3. It quantifies serialized-history lengths over the 400-instance benchmark and records the implications for a 128,000-token baseline context limit.

## 2. Background and related work

### 2.1 From retrieval to state tracking

Many conversational-memory evaluations emphasize whether a system can recover information from prior dialogue. STALE focuses on a distinct failure condition: the system may retrieve an old fact yet fail to determine whether it remains valid after later, indirectly related evidence. This distinction matters for memory architectures that rank content by relevance. Similarity to a query does not, by itself, establish that a retrieved fact is current.

STALE's benchmark and paper position implicit conflict as a problem of tracking latent user state over temporally separated conversations. In Type I conflicts, the relevant update concerns the same attribute; in Type II, an update has consequences for a different, related attribute. Its three probes separate explicit recognition, resistance to stale premises, and downstream behavior [1].

### 2.2 Write-side adjudication and CUPMem

CUPMem is the state-aware memory framework proposed with STALE. The paper describes structured state consolidation and propagation-aware search as mechanisms for identifying stale memories and updating related beliefs. Its reported overall score is 68.0%, compared with 22.4% for the paper's Gemini-3.1-flash-lite long-context row [1]. These are published results, not results from the experiments reported here. In particular, no official CUPMem run or independent reimplementation was complete at manuscript preparation.

### 2.3 Reproduction focus

The present study restricts itself to the unaugmented long-context condition, B0. This gives a reproducible reference point for subsequent comparisons but cannot test the central architectural claim about write-time adjudication. A direct follow-up should compare B0 with the official CUPMem implementation, a separately implemented version, and appropriate retrieval baselines under matched evidence access and evaluation settings.

## 3. Benchmark and methods

### 3.1 Dataset

We used the released `T1_T2_400_FULL.json` file from the STALE dataset [2]. The dataset contains 400 instances, evenly split between Type I and Type II. Each instance includes 50 timestamped dialogue sessions, a pair of indices identifying the old and updated evidence sessions, three probe questions, and ground-truth annotations used by the evaluator. The other sessions provide distractor context.

For the main run, the project loader selected 25 instances of each conflict type with seed 0. Selection is deterministic: within each type, instance UIDs are ranked by a SHA-256 hash of the seed and UID. This makes the 50-instance subset repeatable and independent of the input file's ordering. It is still a single subset, not a random-effects sample over subset seeds.

### 3.2 Systems and input conditions

The primary system is B0, a plain model prompted with the serialized conversation history and one probe at a time. It has no persistent memory store, retrieval module, or write-time state adjudication. The target API model identifier was `gemini-3.1-flash-lite`. The configuration sets generation temperature to 0 and leaves the context limit unset; the full history is therefore passed without the 128,000-token trimming used in the project's GPT-4o-mini B0 configuration.

The reference results from the STALE paper are based on 200 instances per type. The paper reports 22.4% overall for Gemini-3.1-flash-lite (Type I: 41.0/1.5/42.0 for SR/PR/IPA; Type II: 25.0/1.5/23.5). The present 50-instance result is compared descriptively with these full-dataset point estimates. It is not a paired comparison, and there is no inference that the two estimates are equivalent.

### 3.3 Response generation and evaluation

Response prompts follow the released STALE evaluation code and paper appendix [1, 3]. Each instance receives three responses, one for each probe. A joint evaluator call then grades all three responses for that instance. The evaluator receives the old and new states and the hidden explanation and returns a Boolean pass/fail judgment for each dimension using JSON output. Evaluator temperature is 0. The same API model identifier, Gemini-3.1-flash-lite, was used for target generation and evaluation; this choice creates a risk of correlated generation and judging errors.

The evaluator prompt follows the released rubric: SR passes only when the answer recognizes that the old information may no longer be valid; PR passes when it detects or acknowledges the false premise; IPA passes when its final action or recommendation is safe under the updated state. Answers that simply assume the old state or give a generic response are failures under the rubric.

The original paper does not specify the target model's temperature, and the official target-generation code does not pass a temperature parameter. We set target temperature to zero for repeatability. This is a documented deviation, not an exact reconstruction of an unspecified decoding condition. The run record reports no evaluator errors.

![Figure 1. Evaluation workflow. Each STALE instance contains a 50-session history. B0 receives the full history and one probe at a time; the three responses are graded jointly using the released rubric. The evaluator receives the benchmark ground-truth annotations. No separate memory-writing or retrieval stage is used in this study.](figures/figure_1_workflow.png)

### 3.4 Outcomes and statistical analysis

Accuracy is calculated separately for each of the six type-by-dimension cells. Overall accuracy is the unweighted mean of those six cell accuracies, matching the paper's definition [1]. For uncertainty intervals, we ran 2,000 percentile-bootstrap replicates with seed 0. Instances were resampled independently within Type I and Type II; the three judgments from one instance were kept together. Intervals are therefore conditional on the observed subset and do not account for subset-selection or model-version uncertainty.

We report proportions as percentages. A zero-width percentile-bootstrap interval for a cell with zero observed successes is a limitation of this bootstrap procedure and sample; it is not evidence that the population success probability is exactly zero. We do not use a significance test to compare our subset with the paper's aggregate result.

### 3.5 Dataset context-length analysis

We measured token counts for all 400 serialized histories with the project's `o200k` tokenizer path and the history formatter used by B0. We separately counted the two gold evidence sessions and estimated the number of sessions removed by the project's evidence-preserving GPT-4o-mini trimming procedure for the SR probe. These are descriptive input statistics. The “relevant-only” count refers to the two gold sessions and is an oracle-evidence condition; it is not a retrieval system or a performance result.

## 4. Results

### 4.1 Primary evaluation

Table 1 reports all six cell accuracies and the overall score. The main run contains 25 instances of each type (50 total). The full STALE paper values are shown for context; bracketed values are the 95% instance-bootstrap intervals for this study.

**TABLE I. ACCURACY (%) ON STALE.** Published values use 200 instances per type; this study uses 25 per type. Parentheses show 95% instance-bootstrap intervals.

| Measure | Type | Published | This study (95% CI) |
|---|---|---:|---:|
| SR | I | 41.0 | 60.0 (40.0–80.0) |
| PR | I | 1.5 | 0.0 (0.0–0.0) |
| IPA | I | 42.0 | 36.0 (20.0–56.0) |
| SR | II | 25.0 | 32.0 (16.0–52.0) |
| PR | II | 1.5 | 0.0 (0.0–0.0) |
| IPA | II | 23.5 | 28.0 (12.0–48.0) |
| Overall | Both | 22.4 | 26.0 (19.3–33.3) |

![Figure 2. Cell-level accuracy comparison. Published STALE Gemini-3.1-flash-lite point estimates are compared with current-study B0 estimates and 95% instance-bootstrap intervals. Published values are full-benchmark results (200 instances per type); current-study estimates use 25 per type. Zero-width intervals arise from zero observed successes and should not be interpreted as zero population uncertainty.](figures/figure_2_accuracy.png)

Figure 2 visualizes the cell-level comparison. The observed overall estimate is 26.0%, 3.6 percentage points above the paper's point estimate of 22.4%. The paper's result lies within our interval for overall accuracy and for all four SR and IPA cells. In Type I SR, the published value (41.0%) is close to the lower bound of our interval (40.0%).

There were no PR passes in either type (0/25 for each). Although a 1.5% underlying rate would yield zero successes in 25 trials with probability \(0.985^{25} \approx 0.69\), so the zero observations are unsurprising at this sample size. The zero-width bootstrap intervals in Table 1 reflect the observed all-zero cells and the percentile bootstrap's inability to generate a nonzero resampled mean from them.

The 39 passes out of 150 probe judgments yield a micro-average of 26.0%, which happens to equal the six-cell macro-average because the design is balanced (25 instances per type and three probes per instance). For unequal type sample sizes, these two averages need not agree; the prespecified paper-comparable metric remains the unweighted six-cell mean.

### 4.2 Exploratory smoke runs

Two four-instance runs are retained as pipeline checks. Each includes two instances per conflict type. The Gemini pilot's four UIDs are contained in the 50-instance subset; the GPT-4o-mini pilot uses the same four UIDs. These runs are not independent observations and are not pooled with the primary result.

The Gemini pilot scored 33.3% overall (95% interval 16.7–50.0%). The GPT-4o-mini pilot, configured with a 128,000-token limit and evidence-preserving truncation, scored 8.3% (0.0–16.7%). The paper reports 8.7% for GPT-4o-mini on all 400 instances. The near match in point estimates is not informative at n=4; these pilot scores should not be interpreted as a replication or model ranking.

### 4.3 History length and evidence concentration

Figure 3 shows the distribution of serialized history lengths and the difference between complete histories and the two gold evidence sessions. Across all 400 instances, full-history length averages 151,784 tokens (median 151,828.5; range 138,203–164,919). Every instance exceeds the 128,000-token context limit configured for the GPT-4o-mini B0 baseline. The two evidence sessions average 3,132.5 tokens (median 2,933.5; range 1,553–7,743), equal to 2.1% of mean full-history length.

The old and updated evidence sessions are separated by a mean of 27.2 sessions (median 27; range 16–39). The offline SR truncation analysis removes a mean of 9.0 sessions (range 5–13) while retaining both evidence sessions. These measurements illustrate the long-context and distractor burden, but do not establish how trimming changes answer quality.

![Figure 3. Context-length analysis across all 400 STALE instances. Left: distribution of serialized full-history token counts and the 128,000-token GPT-4o-mini context limit. Right: full histories versus the two gold evidence sessions on a logarithmic token axis. The evidence-only condition is descriptive and is not a model evaluation.](figures/figure_3_context.png)

### 4.4 Recorded API usage

The main run made 150 response-generation calls, of which 12 were served from cache, and recorded 23,998,928 prompt tokens and 72,470 completion tokens. The evaluator recorded 50 calls, of which four were served from cache, with 114,518 prompt tokens and 9,947 completion tokens. The run recorded no JSON parsing failures in generation and no evaluator errors. Token figures are API-reported usage; no comparative price or cost-effectiveness claim is made here.

## 5. Discussion

### 5.1 Interpretation of the baseline

The main result is compatible with the broad pattern in STALE: even when supplied with a long dialogue history, a plain model often does not reliably recognize and act on implicitly changed states. The especially low observed PR rates suggest that stale assumptions embedded in questions remain challenging in this sample. SR and IPA scores are higher, but uncertainty is substantial, and the data do not establish a robust difference between conflict types.

The 26.0% subset estimate is numerically close to the paper's 22.4% full-benchmark value. This is an encouraging pipeline-level check, not a full reproduction. The subset contains 25 rather than 200 instances per type; one deterministic subset seed was used; target temperature was fixed to zero despite being unspecified in the original protocol; and serving-model versioning may differ. The confidence interval reflects within-subset instance variability only.

### 5.2 Evaluator validity and audit signal

An exploratory review of the primary run flagged wording in 8 of 23 SR responses scored as passes that began with phrases such as “no evidence” or “no mention.” Some of these responses later referred to the updated session; at least one appeared potentially lenient under the stated rubric. This review was not a blinded human annotation study, and it does not establish that any specific number of labels is incorrect.

The evaluator and target share the same model identifier, so errors may be correlated. A stronger evaluation should obtain independent human labels on a stratified sample, include ambiguous “claims ignorance” cases, report agreement and adjudication procedures, and—if feasible—compare the automatic judge with a distinct evaluator model. Until then, the published automatic-judge metrics should be interpreted as rubric-based model judgments rather than independently verified ground truth.

### 5.3 Implications for reproducing memory systems

The current experiment evaluates only the long-context baseline. It does not test the hypothesis that write-side state adjudication improves conflict handling, nor does it show whether a small adjudicator can implement that policy. CUPMem's 68.0% score remains the published result [1]. The official implementation's default `relevant_only` mode ingests only the two gold evidence sessions, while the benchmark also provides 48 distractor sessions; a direct comparison must explicitly identify the session mode and must not compare oracle evidence access to full-history access as if conditions were matched.

For an informative CUPMem reproduction, full-history ingestion should be reported as the primary condition when it matches the paper's evaluated setting, with relevant-only ingestion labeled as an oracle-evidence ablation. The paper's reported per-instance cost can provide a consistency check, but cost alone is indirect evidence of ingestion mode because generation output and query-time calls also contribute.

### 5.4 Context burden

The full-context analysis shows why a seemingly simple baseline can be expensive and sensitive to input handling: all 400 histories exceed the configured GPT-4o-mini input limit, and evidence-preserving truncation removes multiple sessions. Conversely, the two gold sessions account for a small share of the context. This gap motivates comparing memory selection and state adjudication, but the present token counts do not show that evidence-only access is sufficient, nor that the discarded sessions are irrelevant in every case.

## 6. Limitations

This study is intentionally preliminary and has several important limitations.

1. **Limited subset.** Only 50 of 400 scenarios were evaluated in the primary run. A single deterministic seed does not measure sensitivity to subset choice.
2. **Decoding deviation.** Target temperature was set to zero, whereas the original paper's target setting is unspecified and the released target code omits that parameter.
3. **Evaluator dependence.** Target responses and judgments use the same model identifier. No independent human audit has yet been completed.
4. **Model serving ambiguity.** The API model identifier is recorded, but the run does not independently establish an immutable backend snapshot.
5. **No CUPMem or memory baseline.** No CUPMem run, small adjudicator, retrieval baseline, or Mem0 comparison is included. The study therefore cannot answer the project's headline question about write-side adjudication.
6. **Bootstrap limitations.** The intervals quantify resampling variability conditional on the observed subset. All-zero cells produce degenerate percentile-bootstrap intervals.
7. **Tokenization and context measurements.** Token counts use the project's tokenizer and serialization. They characterize the input representation and are not guaranteed to equal another provider's billing or internal tokenization.
8. **No causal claim.** There is no randomized comparison of memory architectures or context conditions, so the results support descriptive conclusions only.

## 7. Conclusion

On a deterministic, type-balanced subset of 50 STALE instances, plain long-context Gemini-3.1-flash-lite achieved 26.0% overall accuracy, with a 95% instance-bootstrap interval of 19.3–33.3%. This estimate is compatible with the paper's 22.4% full-benchmark Gemini result, but the limited sample, target-decoding deviation, and shared target/judge model preclude a strong reproduction claim. PR had no observed passes in either type, although the sample is too small to infer a zero underlying rate.

The full-dataset context analysis found a mean serialized history length of 151,784 tokens, and all 400 instances exceeded the GPT-4o-mini context limit used by the project's B0 configuration. These results establish a useful baseline record and characterize a substantial input burden. They do not evaluate CUPMem. Full-benchmark B0 runs, independent evaluation audits, and clearly matched CUPMem conditions are needed before making claims about write-side adjudication or small adjudicator models.

## Data and code availability

The benchmark is available from STALEproj/STALE under CC BY 4.0 [2]. The official STALE evaluation code is released under MIT [3]. The primary run configuration, answers, verdicts, call logs, and summary are recorded under `runs/b0_gemini31fl_dev/`; aggregate input-length data are recorded under `runs/analysis/ingestion.json` and `runs/analysis/ingestion_rows.jsonl`. The figures in this manuscript can be regenerated using `papers/figures/generate_figures.py`. Public release of the full run artifacts and confirmation of repository access should be completed before submission. No API credentials are included in the manuscript.

## References

[1] H. Chao, Y. Bai, R. Sheng, T. Li, and Y. Sun. “STALE: Can LLM Agents Know When Their Memories Are No Longer Valid?” arXiv:2605.06527v1, 2026. https://arxiv.org/abs/2605.06527

[2] STALEproj. “STALE: State Tracking and Latent Evaluation.” Hugging Face dataset, `T1_T2_400_FULL.json`, dataset revision identified in the project reproducibility log by SHA `617c51dc`. CC BY 4.0. https://huggingface.co/datasets/STALEproj/STALE

[3] icedreamc. “STALE and CUP-Mem.” Official code repository, commit `ea7d391`, 2026. MIT License. https://github.com/icedreamc/STALE
