"""Builds notes/progress_report_02.pdf: Record #2 (first API runs, 3 Oct 2026).

Run from the repo root:  .venv/Scripts/python notes/make_report2.py
Smoke-test numbers and source listings are read from disk at build time.
"""
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.platypus.tableofcontents import TableOfContents
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "notes" / "progress_report_02.pdf"
RUN = ROOT / "runs" / "b0_gpt4omini_dev_n2"
PRICE_IN, PRICE_OUT = 0.15e-6, 0.60e-6  # gpt-4o-mini USD per token

# ---------------------------------------------------------------- styles (same look as Record #1)
ss = getSampleStyleSheet()
ACCENT = colors.HexColor("#1F4E79")
H0 = ParagraphStyle("H0", parent=ss["Heading1"], textColor=colors.white, backColor=ACCENT, fontSize=15,
                    leading=20, borderPadding=(6, 6, 6, 6), spaceBefore=4, spaceAfter=14, keepWithNext=1)
H1 = ParagraphStyle("H1", parent=ss["Heading1"], textColor=ACCENT, fontSize=15, spaceBefore=14, spaceAfter=8,
                    keepWithNext=1)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], textColor=ACCENT, fontSize=12, spaceBefore=10, spaceAfter=5,
                    keepWithNext=1)
H3 = ParagraphStyle("H3", parent=ss["Heading3"], textColor=colors.HexColor("#2F5F8F"), fontSize=10.3,
                    spaceBefore=7, spaceAfter=3, keepWithNext=1)
BODY = ParagraphStyle("B", parent=ss["BodyText"], fontSize=9.6, leading=13.3, spaceAfter=5)
CELL = ParagraphStyle("C", parent=BODY, fontSize=8.2, leading=10.4, spaceAfter=0)
CELLB = ParagraphStyle("CB", parent=CELL, fontName="Helvetica-Bold", textColor=colors.white)
BUL = ParagraphStyle("BL", parent=BODY, leftIndent=13, bulletIndent=3, spaceAfter=3)
CODE = ParagraphStyle("Code", fontName="Courier", fontSize=7.3, leading=9.0, backColor=colors.HexColor("#EEF1F5"),
                      borderPadding=(4, 4, 4, 4), leftIndent=4, rightIndent=4, spaceBefore=4, spaceAfter=10)
LIST = ParagraphStyle("List", parent=CODE, fontSize=6.7, leading=8.1, backColor=colors.HexColor("#F7F8FA"))
CALLOUT = ParagraphStyle("Call", parent=BODY, backColor=colors.HexColor("#FFF4E0"),
                         borderColor=colors.HexColor("#E0A030"), borderWidth=0.8, borderPadding=7,
                         spaceBefore=8, spaceAfter=12)
NOTE = ParagraphStyle("Note", parent=CALLOUT, backColor=colors.HexColor("#EAF3FB"), borderColor=colors.HexColor("#6A9CC9"))
TOC1 = ParagraphStyle("TOC1", parent=BODY, fontSize=9.5, leftIndent=6, spaceAfter=1, leading=12)
TOC2 = ParagraphStyle("TOC2", parent=BODY, fontSize=8.5, leftIndent=20, spaceAfter=0, leading=10.5,
                      textColor=colors.HexColor("#444444"))

story = []
M = lambda s: f"<font face='Courier'>{s}</font>"


def P(t, s=BODY): story.append(Paragraph(t, s))
def H(t): story.append(Paragraph(t, H1))
def h(t): story.append(Paragraph(t, H2))
def hh(t): story.append(Paragraph(t, H3))
def callout(t, style=CALLOUT): story.append(Paragraph(t, style))


def part(t):
    story.append(PageBreak())
    story.append(Paragraph(t, H0))


def bullets(items):
    for it in items:
        story.append(Paragraph(it, BUL, bulletText="\u2022"))


_ASCII = {"\u2014": "--", "\u2013": "-", "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
          "\u00d7": "x", "\u2192": "->", "\u2026": "...", "\u2011": "-", "\u00a0": " "}


def _ascii(s):
    for k, v in _ASCII.items():
        s = s.replace(k, v)
    return s.encode("latin-1", "replace").decode("latin-1")


def _wrap(text, width):
    out = []
    for line in text.split("\n"):
        while len(line) > width:
            out.append(line[:width]); line = "    " + line[width:]
        out.append(line)
    return "\n".join(out)


def code(txt, style=CODE, width=112):
    story.append(Preformatted(_wrap(_ascii(txt.strip("\n")), width), style))


def table(rows, widths, header=True):
    data = [[Paragraph(c, CELLB if (header and r == 0) else CELL) for c in row] for r, row in enumerate(rows)]
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1 if header else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C8CED6")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
          ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F6F8FA")])]
    if header:
        st.append(("BACKGROUND", (0, 0), (-1, 0), ACCENT))
    t.setStyle(TableStyle(st))
    story.append(t)
    story.append(Spacer(1, 8))


class Doc(SimpleDocTemplate):
    def afterFlowable(self, f):
        if isinstance(f, Paragraph) and f.style.name in ("H0", "H1"):
            self.notify("TOCEntry", (0 if f.style.name == "H0" else 1, f.getPlainText(), self.page))


# ---------------------------------------------------------------- load run data
def read_jsonl(p):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


calls = read_jsonl(RUN / "llm_calls.jsonl")
answers = read_jsonl(RUN / "answers.jsonl")
real = [c for c in calls if not c["cached"]]
tok_in = sum(c["prompt_tokens"] for c in real)
tok_out = sum(c["completion_tokens"] for c in real)
cost = tok_in * PRICE_IN + tok_out * PRICE_OUT
n_done = len({a["uid"] for a in answers})

import sys  # noqa: E402
sys.path.insert(0, str(ROOT / "src"))
from stale_repro.data.loader import load_stale  # noqa: E402
INSTS = {x.uid: x for x in load_stale(ROOT / "data/stale/T1_T2_400_FULL.json")} if answers else {}

# ======================================================================= COVER
story.append(Spacer(1, 38 * mm))
story.append(Paragraph("Does Write-Side State Adjudication Survive Small Models?",
                       ParagraphStyle("T", parent=ss["Title"], fontSize=21, leading=26, textColor=ACCENT)))
story.append(Paragraph("Reproducing and Stress-Testing STALE and CUPMem",
                       ParagraphStyle("ST", parent=ss["Title"], fontSize=14, textColor=colors.HexColor("#444444"))))
story.append(Spacer(1, 12 * mm))
story.append(Paragraph("Project Log &amp; Technical Record #2<br/>First API Runs: Key Setup, Rate Limits, and the B0 Smoke Test",
                       ParagraphStyle("c", parent=BODY, alignment=TA_CENTER, fontSize=12, leading=17)))
story.append(Spacer(1, 8 * mm))
story.append(Paragraph("Date: 3 October 2026<br/>Follows: Record #1 (27 September 2026, notes/week1_progress_report.pdf)"
                       "<br/>Workspace: " + M("C:\\research paper") + "<br/>Coding assistant: Claude Code (Claude Opus 5.5)",
                       ParagraphStyle("c2", parent=BODY, alignment=TA_CENTER, leading=15)))
story.append(PageBreak())
story.append(Paragraph("Contents", ParagraphStyle("TOCH", parent=H1)))
toc = TableOfContents(); toc.levelStyles = [TOC1, TOC2]; story.append(toc)

# ======================================================================= SUMMARY
part("Executive summary")
P("Record #1 ended with a tested pipeline that had never called a real model. This session connected it to the "
  "OpenAI API and ran the first real experiment: a smoke test of the B0 full-context baseline (GPT-4o-mini) on "
  "four STALE instances (two per conflict type).")
table([["Outcome", "Detail"],
       ["API access verified", "The OpenAI key works. It is stored only in the gitignored .env file."],
       ["Paper's model still available", "gpt-4o-mini resolves to the snapshot gpt-4o-mini-2024-07-18, the same model the paper used. "
                                         "It is now pinned in the config, so no successor-model substitution is needed for E1."],
       ["Rate-limit problem found and fixed", "The account limit (200K tokens/minute) admits only about one 148K-token B0 call per minute. "
                                              "The first attempt lost 2 of 4 instances to HTTP 429 errors. Fix: a client-side token-rate "
                                              "limiter plus smarter retries in the gateway."],
       ["Truncation parity confirmed", "Our token estimate matched OpenAI's billed prompt tokens to within 2 tokens per request."],
       ["Paper's failure pattern observed", "Premise Resistance answers accepted outdated premises, as the paper reports for GPT-4o-mini."],
       ["Judge stage deferred", "No Gemini key yet. Added a --no-judge mode; answers are cached and can be judged later at no extra generation cost."],
       ["Tests", "25 passing (2 new for the rate limiter)."],
       ["Smoke-test status at build time", f"{n_done} of 4 instances answered; {len(real)} real API calls; "
                                           f"{tok_in:,} input + {tok_out:,} output tokens; cost about ${cost:.2f}."]], [45, 125])
callout("<b>Key practical finding.</b> At the current account tier the rate limit, not money, is the bottleneck for "
        "full-context runs:<br/>"
        "- 50-instance dev run: about 2.5 hours;<br/>"
        "- full 400-instance B0: about 20 hours.<br/>"
        "The Batch API or a higher usage tier would remove this bottleneck (Section 3.3). CUPMem runs are less affected "
        "because they make many small calls rather than a few huge ones.")

# ======================================================================= CHANGES
part("Part I: What changed")
H("1. Change summary")
table([["File", "Change", "Why"],
       [".env (new, gitignored)", "Holds OPENAI_API_KEY; empty slots for Gemini and open-model keys", "Keys never enter code, configs or git"],
       ["src/stale_repro/llm/gateway.py", "Added TPMLimiter, estimate_request_tokens, rate-limit-aware retry loop; tpm read from config; SDK retries lowered 5 to 2",
        "Survive a 200K TPM limit with ~148K-token requests"],
       ["src/stale_repro/runner.py", "Answer-only mode: if the config has no judge, stop after answering and write a partial summary",
        "Run generation before the Gemini key exists"],
       ["scripts/run_experiment.py", "New --no-judge flag; load .env by explicit path; prints whichever summary keys exist",
        "Answer-only runs; robust .env loading"],
       ["configs/b0_gpt4omini_dev.yaml", "Model pinned to gpt-4o-mini-2024-07-18; tpm: 190000", "Exact model identity; stay under limit with headroom"],
       ["tests/test_gateway.py", "2 new tests: limiter waits when window is full; OpenAI-style token estimate", "Cover new code"],
       ["notes/reproducibility_log.md", "New section \"2026-10-03: First API runs\"", "Keep the running record complete"],
       ["runs/b0_gpt4omini_dev_n2/", "First run outputs (answers, call log, config)", "Smoke test"],
       ["cache/llm_cache.sqlite", "First cached responses", "Reruns and later judging cost nothing"]], [45, 75, 50])

H("2. Step-by-step log")


def step(n, title, why, cmds, result, decision=None):
    story.append(Paragraph(f"Step {n}: {title}", H2))
    P("<b>Why:</b> " + why)
    if cmds:
        code(cmds)
    P("<b>Result:</b> " + result)
    if decision:
        P("<b>Decision:</b> " + decision)


step(1, "Store the API key safely",
     "The key must be available to the code without ever being committed or printed.",
     "Write .env:\n  OPENAI_API_KEY=sk-proj-...   (value not reproduced here)\n  GEMINI_API_KEY=\n  OPEN_MODELS_API_KEY=\n  VLLM_API_KEY=EMPTY",
     ".env created. It is listed in .gitignore and is never echoed in command output.")
step(2, "Verify the key and check model availability",
     "Record #1 flagged the risk that GPT-4o-mini might be retired. Confirm before spending.",
     "python - <<EOF\n  load_dotenv('.env'); c = OpenAI()\n  ids = sorted(m.id for m in c.models.list())\n"
     "  print gpt-4o-mini family\n  c.chat.completions.create(model='gpt-4o-mini', messages=[...'Reply with OK'], max_tokens=5)\nEOF",
     "133 models visible. gpt-4o-mini and gpt-4o-mini-2024-07-18 are listed. The test call returned \"OK\" "
     "(10 input, 1 output tokens), served by <b>gpt-4o-mini-2024-07-18</b>.",
     "Pin the snapshot id in the config so the experiment is tied to one exact model version.")
P("<i>Note:</i> the first attempt failed with an AssertionError inside python-dotenv's find_dotenv(). This happens when "
  "code is piped through stdin, because there is no calling file to search from. Passing the path explicitly "
  "(load_dotenv('.env')) fixed it, and the CLI now does the same.")
step(3, "Add an answer-only mode",
     "The judge needs a Gemini key that is not available yet. Generation should not wait for it.",
     "runner.py:   if not cfg.get('judge'): write {n_answered, judged: False, usage} and return\n"
     "run_experiment.py:   --no-judge  ->  cfg['judge'] = None",
     "Answers are written and cached. Rerunning later with a judge block judges them without regenerating.")
step(4, "Pin the model and rerun the tests",
     "Confirm nothing broke.",
     "sed: model: gpt-4o-mini  ->  model: gpt-4o-mini-2024-07-18\n.venv/Scripts/python -m pytest -q",
     "23 passed.")
step(5, "First smoke test (failed partially)",
     "Exercise the full path against the real API on the smallest meaningful sample.",
     ".venv/Scripts/python scripts/run_experiment.py configs/b0_gpt4omini_dev.yaml --n-per-type 2 --no-judge --workers 4",
     "2 of 4 instances completed in about 3 minutes. The other 2 failed with:")
code("RateLimitError: Error code: 429 - Rate limit reached for gpt-4o-mini-2024-07-18 (for limit gpt-4o-mini)\n"
     "on tokens per min (TPM): Limit 200000, Used 175394, Requested 147778. Please try again in 36.951s.")
P("The runner behaved as designed: completed instances were saved, failures were reported together, and it exited "
  "with \"rerun to resume\".")
step(6, "Diagnose the rate limit",
     "Understand the limit before choosing a fix.",
     None,
     "Each B0 request carries about 123K prompt tokens after truncation, but OpenAI counted 147,778. Its limiter estimates "
     "a request as roughly characters/4 plus the maximum possible output. The official code sends no max_tokens, so "
     "the model default (16,384) is reserved. With a 200K budget per rolling minute, only one such request fits per minute. "
     "Four workers in parallel immediately exceeded it. The SDK's built-in exponential backoff (a few seconds) is far "
     "shorter than the 37 seconds requested.")
step(7, "Implement a token-rate limiter and better retries",
     "Wait before sending instead of collecting errors; when an error does occur, wait as long as the API asks.",
     "gateway.py: TPMLimiter (sliding 60 s window), estimate_request_tokens (chars/4 + max_tokens),\n"
     "            OpenAICompatBackend(tpm=..., rate_limit_retries=12): parse 'try again in Xs', sleep, retry\n"
     "config:     tpm: 190000",
     "Details in Section 4.1.")
step(8, "Test the new code",
     "The limiter involves time; it must be tested without real waiting.",
     "tests/test_gateway.py: test_tpm_limiter_waits_when_window_full (fake clock + fake sleep)\n"
     "                       test_estimate_request_tokens_matches_openai_style\n"
     ".venv/Scripts/python -m pytest -q",
     "<b>25 passed in 1.1 s</b>.")
step(9, "Resume the smoke test",
     "Finish the two failed instances; completed ones are skipped automatically.",
     ".venv/Scripts/python scripts/run_experiment.py configs/b0_gpt4omini_dev.yaml --n-per-type 2 --no-judge --workers 4   (background)",
     f"{n_done} of 4 instances answered. The resumed run took 5 min 14 s for the 2 remaining instances (6 calls), "
     "with <b>no rate-limit errors</b>: the limiter paced the calls to about one per minute.")
step(10, "Inspect the first answers",
     "Sanity-check behaviour before scaling up.",
     "python: join answers.jsonl with the dataset; print M_old, M_new, each question, trace and answer",
     "See Part II.")
step(11, "Update the reproducibility log and write this report",
     "Keep the record complete.",
     "Edit notes/reproducibility_log.md;  Write notes/make_report2.py;  run it",
     "This document.")

# ======================================================================= RATE LIMITS
H("3. The rate-limit analysis")
h("3.1 Why each request is so large")
table([["Quantity", "Value", "Source"],
       ["Serialized history per instance", "~152K tokens", "Record #1, dataset measurement"],
       ["Input budget after truncation", "125,440 tokens", "Official: 128,000 - 2,048 - 512"],
       ["Actual billed prompt tokens", "~123K", "API usage field"],
       ["OpenAI limiter's estimate per request", "~148K", "chars/4 + 16,384 default max output"],
       ["Account limit (gpt-4o-mini)", "200,000 TPM", "429 error message"],
       ["Requests that fit per minute", "1", "200K / 148K"]], [70, 40, 60])
h("3.2 What this means for the schedule")
table([["Run", "Calls", "Wall time at 1 call/min", "Approx. cost"],
       ["B0 dev subset (50 instances)", "150", "~2.5 hours", "~$3"],
       ["B0 full E1 (400 instances)", "1,200", "~20 hours", "~$23"],
       ["Judge (any run)", "1 per instance", "Separate provider (Gemini)", "small"],
       ["CUPMem (per instance)", "many small calls", "Limited by request count, not tokens", "~$0.37 (paper)"]], [55, 30, 50, 35])
h("3.3 Options to go faster")
table([["Option", "Effect", "Fidelity impact"],
       ["Wait it out (current)", "Works now; runs overnight in the background", "None"],
       ["Higher usage tier", "OpenAI raises TPM limits as cumulative spend grows; higher tiers allow millions of TPM", "None"],
       ["OpenAI Batch API", "Separate, much larger batch limits and about 50% lower price; results within 24 h", "None (same model and prompts); needs a batch path in the gateway"],
       ["Set max_tokens (e.g. 2,048)", "Cuts the limiter's estimate by ~14K per request; still 1 per minute at 200K", "Small: the official code sends none; answers longer than the cap would be cut"]],
      [40, 75, 55])
callout("Recommendation: keep the current paced approach for the 50-instance dev run, which runs overnight. Before the "
        "full E1 runs, add Batch API support to the gateway. It keeps the protocol unchanged and halves the cost.", NOTE)

# ======================================================================= CODE
H("4. Code changes in detail")
h("4.1 Gateway: TPMLimiter, token estimate and retries")
table([["Element", "What it does and why"],
       [M("TPMLimiter(tpm, window_s=60)"), "Keeps a list of (time, tokens) for requests sent in the last 60 seconds. "
        + M("acquire(n)") + " drops expired entries; if the remaining sum plus n fits under the limit, it records the "
        "request and returns. Otherwise it computes how long until the oldest entry expires and sleeps outside the lock "
        "(so other threads can check), then tries again. A single request larger than the whole budget is capped so it "
        "cannot wait forever."],
       [M("estimate_request_tokens(messages, params)"), "Characters/4 plus max_tokens (default 16,384). This matches how "
        "OpenAI's own limiter counted our requests (147,778 for a ~123K-token prompt), so client and server agree on the budget."],
       [M("OpenAICompatBackend(..., tpm, rate_limit_retries=12)"), "If tpm is set, every request first acquires budget "
        "from the limiter. On a RateLimitError it reads the 'try again in Xs' (or ms) hint from the message, sleeps that "
        "long plus 1 s (capped at 120 s), and retries up to 12 times. If there is no hint, it backs off exponentially. "
        "insufficient_quota errors (no credit) are raised immediately, because waiting cannot fix them. The SDK's own "
        "max_retries was lowered from 5 to 2 so the two retry layers do not multiply."],
       [M("gateway_from_config"), "Now passes " + M("cfg['tpm']") + " to the backend, so the limit is set per model in YAML."]],
      [55, 115])
code('''
class TPMLimiter:
    def acquire(self, n):
        n = min(n, self.tpm)
        while True:
            with self._lock:
                now = time.monotonic()
                self._events = [(t, k) for t, k in self._events if now - t < self.window]
                if sum(k for _, k in self._events) + n <= self.tpm:
                    self._events.append((now, n)); return
                wait = self.window - (now - self._events[0][0]) + 0.05
            time.sleep(max(wait, 0.05))                       # sleep outside the lock
''')
h("4.2 Runner and CLI: answer-only mode")
code('''
# runner.run(), after answering
if not cfg.get("judge"):     # answers only; judge later by rerunning with a judge block
    summary = {"name": cfg["name"], "n_answered": len(answers), "judged": False,
               "usage_system": sys_gw.summary()}
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary

# scripts/run_experiment.py
p.add_argument("--no-judge", action="store_true", help="generate answers only; judge later")
load_dotenv(".env")
if args.no_judge: cfg["judge"] = None
''')
P("Because every model call is cached, a later run with the judge enabled reads all answers from cache and only "
  "sends the judge calls. The answers are not regenerated and not paid for twice.")
h("4.3 Config")
code('''
system:
  kind: full_context
  llm:
    model: gpt-4o-mini-2024-07-18   # pinned snapshot; the "gpt-4o-mini" alias resolves to it (checked 2026-10-03)
    api_key_env: OPENAI_API_KEY
    tpm: 190000                # account limit is 200K TPM for gpt-4o-mini (tier 1); keep headroom
    params: {temperature: 0}
''')
h("4.4 New tests")
table([["Test", "How it works", "Verifies"],
       ["test_tpm_limiter_waits_when_window_full", "Replaces time.monotonic and time.sleep with a fake clock, so no real waiting. "
        "Limit 100: acquire 60, then 30 (fits), then 50.", "No sleep while under budget; the third request waits until the "
        "first leaves the 60 s window (clock reaches 60 s or more)"],
       ["test_estimate_request_tokens_matches_openai_style", "400 characters with default and with max_tokens=50",
        "Returns 100 + 16,384 and 100 + 50"]], [55, 65, 50])

# ======================================================================= RESULTS
part("Part II: First results")
H("5. Smoke-test results")
P(f"Run: {M('runs/b0_gpt4omini_dev_n2')} (2 instances per type, seed 0, answer-only). At build time {n_done} of 4 "
  f"instances are answered, from {len(real)} real API calls.")
h("5.1 Token parity and truncation")
rows = [["Instance", "Probe", "Sessions removed", "Our estimate", "Billed prompt tokens", "Difference"]]
for a in answers:
    for d in ("dim1", "dim2", "dim3"):
        t = a["traces"][d]
        est, billed = t.get("request_tokens_est"), t["usage"]["prompt_tokens"]
        rows.append([f"{a['type']} {a['uid'][:8]}", d, str(t["removed_sessions"]), f"{est:,}" if est else "-",
                     f"{billed:,}", f"{billed - est:+d}" if est else "-"])
table(rows, [30, 14, 26, 30, 36, 24])
P("The estimate comes from the ported official tiktoken counter. Matching the billed count to within a few tokens "
  "shows the truncation behaves exactly like the official code: same budget, same tokenizer, same chat overhead. "
  "Between 8 and 11 distractor sessions are removed per request. Both evidence sessions are always retained.")
h("5.2 Answers")
for a in answers:
    x = INSTS.get(a["uid"])
    if not x:
        continue
    hh(f"{'Type I' if a['type'] == 'T1' else 'Type II'} instance {a['uid']}")
    rows = [["Field", "Content"], ["M_old", escape(_ascii(x.m_old))], ["M_new", escape(_ascii(x.m_new))]]
    for d, name in (("dim1", "SR"), ("dim2", "PR"), ("dim3", "IPA")):
        ans = _ascii(a["answers"][d]).replace("\n", " ")
        ans = ans[:420] + (" ..." if len(ans) > 420 else "")
        rows.append([f"{name} question", escape(_ascii(x.probes[d].text))])
        rows.append([f"{name} answer", escape(ans)])
    table(rows, [26, 144])
h("5.3 Observations (not yet judged)")
bullets([
    "<b>Premise Resistance fails clearly.</b> Asked to plan anniversary ideas for a relationship the user has since "
    "left (they are going speed-dating), the model writes a full anniversary plan. Asked for a luteal-phase workout plan "
    "after the user's fertility-clinic baseline scan, it produces a seven-day luteal plan. This matches the paper's "
    "0.0% PR for GPT-4o-mini.",
    "<b>State Resolution fails in two ways.</b> In both Type I instances the model <i>reaffirms the old state</i>: \"Yes, the user needs a second cup of coffee to feel normal\", although the user later says they start the day with water and a walk, without stimulants. In Type II instances it instead <i>claims the history says nothing</i>, although both evidence sessions were in context. The rubric fails both: assuming M_old is true, and claiming ignorance. This fits the paper's attention analysis: the query reaches the evidence, but the old and new sessions are not reconciled.",
    "<b>IPA answers are generic.</b> They give balanced advice without using the new state (e.g. paying a plus-one "
    "deposit without considering that the user is now single; encouraging a spontaneous 'wing it' cooking night for a "
    "user who now needs predictable, batch-cooked weeknights). The rubric fails these.",
    "These are qualitative impressions from a handful of answers. Scores require the judge, and four instances say "
    "nothing statistically."])

# ======================================================================= SECURITY + STATUS
part("Part III: Housekeeping and next steps")
H("6. Security and key handling")
bullets([
    "The key lives only in " + M(".env") + ", which is gitignored, and is read through python-dotenv. Configs name the "
    "environment variable (" + M("api_key_env: OPENAI_API_KEY") + "), never the key itself.",
    "No command in this session printed the key. This report shows only the " + M("sk-proj-...") + " prefix.",
    "The key was pasted into the chat conversation, so it exists in the conversation transcript. Recommended: create "
    "a new key in the OpenAI dashboard, put it in .env, and revoke the old one. Nothing else needs to change.",
    "Consider setting a monthly spend limit in the OpenAI dashboard as a safety net for long background runs."])
H("7. Updated status")
table([["Component", "Record #1", "Now"],
       ["LLM gateway", "done, tested", "done, tested; rate limiting and retries added"],
       ["Loader, judge, stats", "done, tested", "unchanged"],
       ["B0 full context", "done, tested", "validated against the real API (token parity)"],
       ["Runner", "done, tested", "answer-only mode added"],
       ["Real experiment runs", "none", f"B0 smoke test: {n_done}/4 answered, not yet judged"],
       ["Judge with real model", "-", "waiting for Gemini key"],
       ["Official CUPMem wrapper", "todo", "todo"],
       ["Independent CUPMem", "todo", "todo"],
       ["Tests", "23", "25"]], [50, 45, 75])
H("8. Open decisions and next steps")
h("8.1 Decisions needed")
bullets(["Provide a Gemini API key for the judge (paper: Gemini-3.1-flash-lite); confirm the exact model id.",
         "Approve the 50-instance B0 dev run: about $3 and about 2.5 hours in the background.",
         "Rotate the OpenAI key (Section 6).",
         "Later: Batch API support before full E1 runs (Section 3.3)."])
h("8.2 Next steps")
table([["#", "Task", "Depends on"],
       ["1", "Judge the smoke-test answers; check the SR \"claims ignorance\" cases", "Gemini key"],
       ["2", "B0 dev run (50 instances); compare with the paper's GPT-4o-mini row", "Approval"],
       ["3", "Wrap the official CUPMem; run in full and relevant_only modes; measure cost (the central RQ1 question)", "Embedding model download"],
       ["4", "Start the independent CUPMem reimplementation", "Step 3 findings"],
       ["5", "Batch API path in the gateway", "Before full E1"]], [8, 120, 42])

# ======================================================================= APPENDIX
part("Appendix: Current source of changed files")
P("Read from disk at build time, so these listings match the code exactly.")
for i, rel in enumerate(["src/stale_repro/llm/gateway.py", "src/stale_repro/runner.py", "scripts/run_experiment.py",
                         "configs/b0_gpt4omini_dev.yaml", "tests/test_gateway.py"], 1):
    src = (ROOT / rel).read_text(encoding="utf-8")
    story.append(Paragraph(f"A.{i} {rel} ({src.count(chr(10))} lines)", H1))
    code(src, LIST, width=118)
H("A.6 Smoke-test call log (runs/b0_gpt4omini_dev_n2/llm_calls.jsonl)")
code("\n".join(json.dumps({k: c[k] for k in ("tag", "model", "cached", "prompt_tokens", "completion_tokens", "latency_s")})
               for c in calls) or "(empty)", LIST, width=118)


def on_page(canvas, doc):
    canvas.saveState(); canvas.setFont("Helvetica", 7.5); canvas.setFillColor(colors.grey)
    if doc.page > 1:
        canvas.drawString(18 * mm, 10 * mm, "STALE / CUPMem reproduction: Record #2, first API runs")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


doc = Doc(str(OUT), pagesize=A4, leftMargin=19 * mm, rightMargin=19 * mm, topMargin=17 * mm, bottomMargin=17 * mm,
          title="STALE/CUPMem Reproduction: Record #2", author="hrithikgh29@gmail.com")
doc.multiBuild(story, onFirstPage=on_page, onLaterPages=on_page)
print("wrote", OUT, f"| answered {n_done}/4 | calls {len(real)} | ${cost:.3f}")
