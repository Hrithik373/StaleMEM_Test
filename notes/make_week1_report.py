"""Builds notes/week1_progress_report.pdf (detailed edition).

Run from the repo root:  .venv/Scripts/python notes/make_week1_report.py
Source listings in the appendices are read from the actual files at build time.
"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table,
                                TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "notes" / "week1_progress_report.pdf"

# ---------------------------------------------------------------- styles
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
CODE = ParagraphStyle("Code", fontName="Courier", fontSize=7.3, leading=9.0,
                      backColor=colors.HexColor("#EEF1F5"), borderPadding=(4, 4, 4, 4),
                      leftIndent=4, rightIndent=4, spaceBefore=4, spaceAfter=10)
LIST = ParagraphStyle("List", parent=CODE, fontSize=6.7, leading=8.1, backColor=colors.HexColor("#F7F8FA"))
CALLOUT = ParagraphStyle("Call", parent=BODY, backColor=colors.HexColor("#FFF4E0"),
                         borderColor=colors.HexColor("#E0A030"), borderWidth=0.8, borderPadding=7,
                         spaceBefore=8, spaceAfter=12)
NOTE = ParagraphStyle("Note", parent=CALLOUT, backColor=colors.HexColor("#EAF3FB"),
                      borderColor=colors.HexColor("#6A9CC9"))
TOC1 = ParagraphStyle("TOC1", parent=BODY, fontSize=9.5, leftIndent=6, spaceAfter=1, leading=12)
TOC2 = ParagraphStyle("TOC2", parent=BODY, fontSize=8.5, leftIndent=20, spaceAfter=0, leading=10.5,
                      textColor=colors.HexColor("#444444"))

story = []
M = lambda s: f"<font face='Courier'>{s}</font>"  # inline monospace


def P(t, s=BODY):
    story.append(Paragraph(t, s))


def part(t):
    story.append(PageBreak())
    story.append(Paragraph(t, H0))


def H(t):
    story.append(Paragraph(t, H1))


def h(t):
    story.append(Paragraph(t, H2))


def hh(t):
    story.append(Paragraph(t, H3))


def bullets(items):
    for it in items:
        story.append(Paragraph(it, BUL, bulletText="\u2022"))


def callout(t, style=CALLOUT):
    story.append(Paragraph(t, style))


_ASCII = {"\u2014": "--", "\u2013": "-", "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
          "\u00d7": "x", "\u2192": "->", "\u2026": "...", "\u2011": "-", "\u00a0": " "}


def _ascii(s: str) -> str:
    for k, v in _ASCII.items():
        s = s.replace(k, v)
    return s.encode("latin-1", "replace").decode("latin-1")


def _wrap(text: str, width: int) -> str:
    out = []
    for line in text.split("\n"):
        while len(line) > width:
            out.append(line[:width])
            line = "    " + line[width:]
        out.append(line)
    return "\n".join(out)


def code(txt, style=CODE, width=112):
    story.append(Preformatted(_wrap(_ascii(txt.strip("\n")), width), style))


def table(rows, widths, header=True):
    data = [[Paragraph(c, CELLB if (header and r == 0) else CELL) for c in row] for r, row in enumerate(rows)]
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1 if header else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C8CED6")),
          ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
          ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F6F8FA")])]
    if header:
        st.append(("BACKGROUND", (0, 0), (-1, 0), ACCENT))
    t.setStyle(TableStyle(st))
    story.append(t)
    story.append(Spacer(1, 8))


class Doc(SimpleDocTemplate):
    """Registers H0/H1 headings in the table of contents."""

    def afterFlowable(self, f):
        if isinstance(f, Paragraph):
            if f.style.name == "H0":
                self.notify("TOCEntry", (0, f.getPlainText(), self.page))
            elif f.style.name == "H1":
                self.notify("TOCEntry", (1, f.getPlainText(), self.page))


# ======================================================================= COVER
story.append(Spacer(1, 38 * mm))
story.append(Paragraph("Does Write-Side State Adjudication Survive Small Models?",
                       ParagraphStyle("T", parent=ss["Title"], fontSize=21, leading=26, textColor=ACCENT)))
story.append(Paragraph("Reproducing and Stress-Testing STALE and CUPMem",
                       ParagraphStyle("ST", parent=ss["Title"], fontSize=14, textColor=colors.HexColor("#444444"))))
story.append(Spacer(1, 12 * mm))
story.append(Paragraph("Project Log &amp; Technical Record #1: Week 1<br/>"
                       "Setup, Verification of the Paper's Artifacts, and Pipeline Foundation<br/>"
                       "<i>Detailed edition</i>",
                       ParagraphStyle("c", parent=BODY, alignment=TA_CENTER, fontSize=12, leading=17)))
story.append(Spacer(1, 8 * mm))
story.append(Paragraph("Date: 27 September 2026<br/>Workspace: " + M("C:\\research paper") +
                       "<br/>Coding assistant: Claude Code (Claude Opus 5.5)",
                       ParagraphStyle("c2", parent=BODY, alignment=TA_CENTER, leading=15)))
story.append(Spacer(1, 25 * mm))
table([["How to read this document"],
       ["<b>Part I</b> explains the research context: what STALE and CUPMem are, with real examples from the dataset."],
       ["<b>Part II</b> is a chronological record of every action taken, including the exact commands and what they returned."],
       ["<b>Part III</b> lists the findings from verifying the paper, the official code and the dataset."],
       ["<b>Part IV</b> explains how the code was designed and how every module and function works."],
       ["<b>Part V</b> covers testing, deviations, reproduction commands and next steps."],
       ["<b>Appendices</b> contain the complete source code of every file, the official judge prompt, and a glossary."]],
      [150])

story.append(PageBreak())
story.append(Paragraph("Contents", ParagraphStyle("TOCH", parent=H1)))
toc = TableOfContents()
toc.levelStyles = [TOC1, TOC2]
story.append(toc)

# ======================================================================= PART 0: SUMMARY
part("Executive summary")
P("This project is a reproduction-and-stress-test paper on <b>STALE</b> (Chao et al., arXiv:2605.06527, May 2026).")
bullets([
    "<b>STALE</b> is a benchmark that tests whether memory-augmented LLM agents notice when new information "
    "<i>implicitly</i> makes an old memory outdated.",
    "<b>CUPMem</b> is the paper's proposed memory system. It decides at write time whether each old memory is still "
    "valid. With GPT-4o-mini it raised overall accuracy from 8.7% to 68.0%."])
P("The paper's five research questions:")
table([["#", "Question"],
       ["RQ1", "Does the result reproduce?"],
       ["RQ2", "Does it survive when the adjudicating model is a small open model (3-9B)?"],
       ["RQ3", "Which pipeline stage fails first?"],
       ["RQ4", "What does each component contribute, and what does it cost?"],
       ["RQ5", "Does it handle two-step cascades?"]], [14, 156])
P("In this first working session the following was accomplished:")
bullets([
    "<b>Located and verified all artifacts.</b> The paper's code (including the complete official CUPMem implementation) "
    "and dataset are public. Both were downloaded, and the 37-page paper, especially Appendices E-G, was read in full.",
    "<b>Measured the dataset.</b><br/>"
    "- 400 instances (200 Type I, 200 Type II), each with exactly 50 chat sessions;<br/>"
    "- about 152K tokens per instance, so every instance exceeds GPT-4o-mini's 128K window;<br/>"
    "- the old evidence always sits in sessions 0-14 and the new evidence in sessions 30-39.",
    "<b>Studied the official code</b> to extract the exact evaluation protocol: prompts, judge settings, scoring formula, "
    "and truncation algorithm.",
    "<b>Built a tested Python package</b>, " + M("stale_repro") + " (about 1,270 lines including tests). It contains:<br/>"
    "- an LLM gateway with caching and cost accounting;<br/>"
    "- a data loader;<br/>"
    "- the official judge;<br/>"
    "- statistics with confidence intervals;<br/>"
    "- the B0 full-context baseline;<br/>"
    "- a resumable experiment runner.<br/>"
    "All 23 tests pass without any API keys.",
    "<b>Checked for competing work.</b> Two August 2026 papers are related but do not cover our research questions.",
    "<b>Documented everything</b> in a running reproducibility log, which will become the paper's setup section."])
callout("<b>Most important finding so far.</b> The official CUPMem runner has a " + M("--session-mode") +
        " option whose <b>default is " + M("relevant_only") + "</b>. In that mode, CUPMem ingests only the two sessions that "
        "contain the gold evidence, skipping the 48 distractor sessions that every baseline must wade through. The paper "
        "does not say which mode produced 68.0%.<br/><br/>"
        "The paper's reported cost (~$0.37 per instance) is consistent with the full 50-session mode (Section 12.4), but "
        "this must be measured, not assumed. If the headline number came from " + M("relevant_only") + ", it would be "
        "measured under oracle evidence selection. Either way, this becomes an explicit, central part of RQ1.")

# ======================================================================= PART I
part("Part I: Research context")
H("1. The STALE benchmark")
h("1.1 The problem it studies")
P("Personal assistants with long-term memory store facts about the user (\"lives in Seattle\", \"cycles to work\"). "
  "Real life changes these facts, but people rarely announce the change explicitly. Someone who moved does not say "
  "\"please forget that I live in Seattle\"; they mention setting up utilities at a new apartment in Austin.")
P("STALE calls this an <b>implicit conflict</b>: a later observation invalidates an earlier memory without directly "
  "negating it. Resolving it requires commonsense inference, not just retrieval.")
h("1.2 Two conflict types")
table([["Type", "Definition", "Example from the paper"],
       ["<b>Type I</b> (co-referential)", "Old and new statements concern the <i>same</i> attribute and conflict without saying so.",
        "\"Lives in Seattle\", later followed by setting up utilities for a new apartment in Austin."],
       ["<b>Type II</b> (propagated)", "A change in one attribute makes a <i>different</i> attribute invalid.",
        "Breaking a leg makes the earlier \"cycles to work daily\" memory inapplicable."]], [32, 68, 70])
h("1.3 Three probe dimensions")
P("Every scenario is tested with three separate queries, each sent in its own model call so that no probe can leak "
  "information to another.")
table([["Probe", "Name", "What it tests", "How it is posed"],
       ["dim1 / SR", "State Resolution", "Does the model recognise that the old belief may be outdated?", "Explicit question"],
       ["dim2 / PR", "Premise Resistance", "Does it reject a question that assumes the old state?", "Question with a false premise"],
       ["dim3 / IPA", "Implicit Policy Adaptation", "Does it apply the new state in an ordinary request?", "User's latest request"]],
      [22, 34, 72, 42])
h("1.4 Real examples from the dataset")
hh("Type I example (uid 7c0ae4e7-6b5a-42a2-891b-0ccf553bfe7f)")
table([["Field", "Content"],
       ["M_old (session 13, 2021-06-15)", "I've been based in Seattle for the last few years."],
       ["M_new (session 33, 2023-06-15)", "I just finished updating my address after settling into my new place in Austin, and I'm trying "
                                          "to get set up with the local utilities and services here."],
       ["Explanation (hidden from the model)", "Spatiotemporal_Context.location(city) is now Austin."],
       ["dim1 SR", "Based on the conversation history, does the user still live in Seattle?"],
       ["dim2 PR", "Since the user has been based in Seattle for the last few years, can you recommend a few Seattle-specific "
                   "neighborhood resources they should sign up for right now?"],
       ["dim3 IPA", "I just moved to the area and was wondering if you could recommend some good spots to relax on the weekends?"]],
      [45, 125])
P("Note that the evidence is embedded inside natural multi-turn conversations of 8-12 turns, not stated in isolation. "
  "The old session opens with a general question about rainy coastal cities; the new one is a request for a "
  "utilities checklist.")
hh("Type II example (uid 704cac18-885e-4437-b136-a7600650ba01)")
table([["Field", "Content"],
       ["M_old (session 9)", "I've honestly become so accustomed to the pace of life here in Portland that I can't imagine navigating "
                             "the rhythm of a different city anymore."],
       ["M_new (session 35)", "I've learned the hard way to always shake out my boots before putting them on; I found another bark "
                              "scorpion hiding near the heel this morning, driven indoors by the relentless dry heat."],
       ["Explanation", "Dry heat and bark scorpions point to the American Southwest (e.g. the Sonoran Desert). This invalidates the "
                       "location attribute: living in rainy Portland is no longer feasible."],
       ["dim1 SR", "Based on the conversation history, does the user still live in Portland?"],
       ["dim2 PR", "Since the user is accustomed to the pace of life in Portland, can you suggest a week-long itinerary of "
                   "neighborhoods, cafes, and rainy-day activities...?"],
       ["dim3 IPA", "I want to make my home more comfortable year-round. Considering the place I live, what practical steps should "
                    "I take, and what should I keep on hand?"]], [45, 125])
P("Here nothing in the new session mentions location at all. The model must infer the move from climate and "
  "wildlife cues. This is why Type II is harder.")
h("1.5 Scoring")
bullets([
    "An LLM judge (Gemini-3.1-flash-lite) sees three things: the old state, the new state, and the hidden explanation.",
    "It returns pass or fail for each of the three responses. The full prompt is reproduced in Appendix B.",
    "The paper validated the judge against 240 human labels: 95.8% agreement, Cohen's kappa 0.915. The judge is slightly "
    "conservative (FPR 1.5%, FNR 7.5%).",
    "<b>Overall</b> is the unweighted mean of the six (type x probe) cell accuracies."])
h("1.6 Headline results (paper Table 2 / official README)")
table([["System", "T1 SR", "T1 PR", "T1 IPA", "T2 SR", "T2 PR", "T2 IPA", "Overall"],
       ["GPT-4o-mini*", "30.0", "0.0", "11.0", "9.5", "0.0", "1.5", "8.7"],
       ["GPT-5.4", "35.0", "2.0", "29.0", "9.0", "2.0", "17.0", "15.7"],
       ["Gemini-3.1-pro", "92.0", "30.0", "71.0", "69.0", "14.0", "55.0", "55.2"],
       ["Claude-Opus-4.6", "50.5", "10.0", "42.5", "21.0", "9.0", "36.5", "28.3"],
       ["Qwen3.5-9B", "36.0", "1.0", "21.5", "21.5", "0.0", "7.5", "14.6"],
       ["Qwen3.5-27B", "76.0", "4.0", "39.0", "42.0", "3.5", "23.0", "31.3"],
       ["LightMem (best framework)", "52.5", "1.0", "23.5", "21.5", "0.5", "7.5", "17.8"],
       ["mem-0", "17.0", "1.0", "22.0", "3.5", "0.0", "6.5", "8.3"],
       ["<b>CUPMem</b>", "91.0", "<b>78.0</b>", "32.0", "<b>89.0</b>", "<b>75.0</b>", "43.0", "<b>68.0</b>"]],
      [46, 17, 17, 17, 17, 17, 17, 22])
P("* evidence-preserving truncation applied. Memory frameworks and CUPMem all use GPT-4o-mini as the backbone. "
  "(Subset of the full table; all 16 rows are in the official README.)")

H("2. CUPMem: the method being reproduced")
P("CUPMem (<i>Current-state Updating and Propagation-aware Memory</i>) treats memory as explicit state tracking. "
  "Its key idea is that <b>new evidence should trigger decisions about old memories at write time</b>, instead of "
  "leaving old and new facts side by side for the answering model to reconcile later.")
h("2.1 Three components")
table([["Component", "What it does"],
       ["1. Write-side adjudication",
        "When a session arrives, extract state-update candidates (target slot, value, whether directly observed or inferred, "
        "confidence, evidence span). An LLM adjudicator then labels each related old memory "
        "KEEP / STALE / REPLACE / UNKNOWN. Stale memories are archived, not deleted. Slots that are no longer safe but lack "
        "a replacement are marked UNKNOWN_CURRENT."],
       ["2. Propagation-aware search",
        "The set of old memories to re-examine is the union of three parts: <i>Direct</i> (slots touched by the new evidence), "
        "<i>Affected</i> (neighbouring regions an LLM predicts may change, e.g. health affecting commute), and "
        "<i>Global_k</i> (a bounded embedding-similarity fallback). This is what targets Type II."],
       ["3. Constrained readout",
        "At query time the query is analysed into intent, presupposed states, needed basis and requested action. "
        "A verifier labels the premise SUPPORTED / OUTDATED / UNRESOLVED. Only ACTIVE memories ground the answer, "
        "STALE ones are shown as history, and outdated premises are blocked."]], [38, 132])
h("2.2 The state schema (paper Table 8)")
P("Memories are stored under a fixed two-level schema. <i>single</i> slots have one current value; <i>multi</i> slots "
  "can hold several active values at once. The schema was fixed before evaluation and built independently of the "
  "benchmark's generation ontology.")
table([["Domain", "Slots (cardinality)"],
       ["identity_and_background", "core_identity_or_role (multi); skill_or_language_background (multi); stable_social_context (multi); current_status_or_affiliation (multi)"],
       ["stable_preferences", "enduring_preference (multi); habitual_choice_pattern (multi); value_or_priority_tendency (multi)"],
       ["location_and_living", "current_base_location (single); living_arrangement_or_settlement (single); location_linked_condition (multi)"],
       ["weather_and_environment", "current_weather_pattern (single); environmental_condition (multi); weather_linked_adjustment (multi)"],
       ["health_and_mobility", "current_health_state (single); functional_limitation (multi); health_linked_adjustment (multi)"],
       ["work_and_schedule", "current_workload (multi); schedule_pressure_or_bandwidth (single); work_transition_or_change (multi); standing_commitment_or_availability (multi)"],
       ["finance_and_resources", "financial_constraint (multi); resource_availability (multi); resource_linked_adjustment (multi); resource_access_or_recoverability (multi)"],
       ["family_and_caregiving", "caregiving_responsibility (multi); household_obligation (multi); family_linked_constraint (multi)"],
       ["routine_and_transport", "current_commute_mode (single); transport_access_condition (multi); routine_shift (multi)"],
       ["current_focus_and_goals", "current_primary_focus (multi); short_horizon_goal (multi); goal_linked_constraint (multi)"]],
      [45, 125])

H("3. Research questions and what this week contributes")
table([["RQ", "Question", "Contribution of Week 1"],
       ["RQ1", "Do CUPMem's gains reproduce?",
        "Official code located; session-mode question identified; judge, prompts and B0 ported exactly; runner ready"],
       ["RQ2", "Does it work with 3-9B open adjudicators?",
        "Gateway supports any OpenAI-compatible host (vLLM, hosted APIs); JSON failures are counted as data"],
       ["RQ3", "Which stage breaks first?", "Answer.trace field and tagged per-stage usage logs designed in from the start"],
       ["RQ4", "Component contributions and cost?", "Per-tag token/latency accounting; cost estimates for B0"],
       ["RQ5", "Two-hop cascades?", "TEPA's authors flag multi-hop as unsolved, confirming the gap"]], [14, 50, 106])

# ======================================================================= PART II
part("Part II: What was done, step by step")
P("This part is a chronological record of the session: each action, the exact command or tool call, what came back, "
  "and the decision it led to. Commands ran in Git Bash on Windows 11 unless noted.")

H("4. Chronological log")


def step(n, title, why, cmds, result, decision=None):
    story.append(Paragraph(f"Step {n}: {title}", H2))
    P("<b>Why:</b> " + why)
    if cmds:
        code(cmds)
    P("<b>Result:</b> " + result)
    if decision:
        P("<b>Decision:</b> " + decision)


step(1, "Inspect the empty workspace",
     "Before creating anything, check what already exists and which tool versions are available.",
     'cd "/c/research paper" && ls -la && python --version; pip --version; git --version',
     "Folder empty. Python 3.12.10, pip 25.0.1, git 2.55.0.")
step(2, "Search for the paper and a code release",
     "The blueprint's first dependency: is the benchmark downloadable?",
     'WebSearch: "STALE benchmark CUPMem memory-augmented agents implicit state conflict arXiv"\n'
     'WebSearch: "CUPMem github STALE benchmark code data release"\n'
     'WebFetch:  https://arxiv.org/abs/2605.06527   (abstract, authors, links)',
     "Found the paper: authors Hanxiang Chao, Yihan Bai, Rui Sheng, Tianle Li, Yushi Sun; submitted 7 May 2026. "
     "The abstract page shows no code link. The search also surfaced two related August 2026 papers (2608.01619, "
     "2608.07429).")
step(3, "Read the appendices from the PDF",
     "The arXiv HTML page omitted the appendix bodies, and Appendix G (\"Code and Dataset Access\") is where links would be.",
     'WebFetch: https://arxiv.org/html/2605.06527v1        # appendix bodies missing\n'
     'WebFetch: https://arxiv.org/pdf/2605.06527           # 5.3 MB binary saved locally\n'
     'mkdir -p papers && cp <saved pdf> papers/stale_2605.06527.pdf\n'
     'python -c "from pypdf import PdfReader; ... write papers/stale.txt"   # 37 pages\n'
     'grep -n -iE "github|huggingface|anonymous|http|Appendix G" papers/stale.txt\n'
     'grep -n -E "^[A-G](\\.[0-9]+)* [A-Z]" papers/stale.txt     # appendix headings\n'
     'Read papers/stale.txt lines 1301-1740                    # App. E, F, G',
     "Appendix G lists github.com/icedreamc/STALE and huggingface.co/datasets/STALEproj/STALE. Read App. E.1 (response and "
     "judge prompts), E.2 (repeated-call variance), E.3 (human agreement), E.5 (LightMem traces), F (CUPMem design) and "
     "Table 8 (schema).")
step(4, "Clone the official code and query the dataset",
     "Confirm the links actually work and see what was released.",
     'git clone --depth 1 https://github.com/icedreamc/STALE external/STALE\n'
     'curl -s https://huggingface.co/api/datasets/STALEproj/STALE | head -c 1500',
     "Repo cloned (single commit ea7d391, \"update main results\", MIT licence). The HF dataset is public and not gated. "
     "It has one data file, T1_T2_400_FULL.json, licensed CC BY 4.0.",
     "Reframe RQ1 as a three-way comparison: the paper's numbers, the official code, and our independent reimplementation.")
step(5, "Download the dataset (in the background)",
     "306 MB; downloading in the background let code reading continue in parallel.",
     'mkdir -p data/stale\n'
     'curl -sL -o data/stale/T1_T2_400_FULL.json \\\n'
     '  https://huggingface.co/datasets/STALEproj/STALE/resolve/main/T1_T2_400_FULL.json\n'
     'curl -sL -o data/stale/README.md https://huggingface.co/datasets/STALEproj/STALE/resolve/main/README.md',
     "Completed in about one minute: 305,908,212 bytes.")
step(6, "Survey the official repository",
     "Understand the structure and size of the official implementation before deciding how to use it.",
     'cat cup_mem/README.md cup_mem/requirements.txt STALE/README.md STALE/requirements.txt\n'
     'wc -l cup_mem/**/*.py cup_mem/*.py STALE/*/*.py | sort -n',
     "STALE/ holds generation (Steps 0-3) and evaluation. cup_mem/ holds CUPMem: about 10K lines across write/, query/, "
     "store_layer/, llm_layer/, retrieval/ and memory/. CUPMem needs an OpenAI-compatible endpoint and a local "
     "all-MiniLM-L6-v2 embedding model. The full structure is in Section 11.")
step(7, "Read the CUPMem runner and discover the session-mode default",
     "Know exactly how the official code feeds data to CUPMem.",
     'cat cup_mem/run_cup_mem.py cup_mem/core/config.py cup_mem/pipeline.py cup_mem/core/sample_runner.py',
     "run_cup_mem.py declares " + M("--session-mode") + " with choices relevant_only/full and <b>default relevant_only</b>. "
     "sample_runner.py confirms that relevant_only restricts ingestion to relevant_session_index, i.e. the two gold "
     "evidence sessions. config.py yields the full threshold list (Section 12.3).")
step(8, "Check what the paper says about the setting",
     "Determine whether the paper reports which mode produced 68.0%.",
     'grep -n -iE "relevant|oracle|haystack|distractor|full context|session_mode|evidence session" papers/stale.txt\n'
     'sed -n 280,310p papers/stale.txt    # 4.1 setup\n'
     'sed -n 425,480p papers/stale.txt    # 5 CUPMem\n'
     'sed -n 700,716p papers/stale.txt    # App. C cost',
     "Section 4.1 says frameworks \"ingest the dialogue history once per instance according to its native protocol\". "
     "No mode is named. App. C gives CUPMem cost as ~$0.37 per instance.",
     "Treat this as open question #1; measure cost in both modes; ask the authors.")
step(9, "Extract the exact evaluation protocol",
     "Numbers are comparable to the paper only if prompts and settings are identical.",
     'cat STALE/Evaluation/judge_prompts.py\n'
     'grep -n -E "model|temperature|response_format|json|def |accuracy|overall" STALE/Evaluation/full_eval_performance.py\n'
     'sed -n 137,212p STALE/Evaluation/full_eval_performance.py\n'
     'Read STALE/Evaluation/run_target_model.py lines 25-214',
     "Judge: temperature=0, json_object output, one joint call per instance; errors silently become FAIL. Target model: no "
     "temperature set (API default). Truncation: 128,000 - 2,048 - 512 token budget, three-phase dropping with an "
     "unseeded random.choice.")
step(10, "Check the environment and inspect the dataset",
     "Decide dependencies; verify the data format matches the official code.",
     'pip list | grep -iE "^(openai|httpx|pytest|pyyaml|numpy|tiktoken|pydantic|...) "\n'
     'python -c "import json, collections; d = json.load(...); print fields, type counts, session counts"',
     "400 records, all with the same 9 fields; 200 T1 + 200 T2; every record has 50 sessions and 2 relevant indices. "
     "The format is identical to what the official scripts consume.")
step(11, "Scaffold the repository",
     "Create a clean, installable project layout matching the blueprint.",
     'mkdir -p configs data/cascade2hop src/stale_repro/{data,llm,memory/cupmem/prompts,eval,diagnostics} \\\n'
     '         scripts notebooks tests notes runs\n'
     'Write: pyproject.toml, .gitignore, .env.example',
     "src/ layout package " + M("stale-repro") + ". Large or third-party files (dataset, cloned repo, PDF, runs, cache) are "
     "gitignored.")
step(12, "Write the core modules",
     "Build the foundation every experiment depends on, in dependency order.",
     'Write: src/stale_repro/llm/gateway.py         (first: everything calls it)\n'
     'Write: src/stale_repro/data/loader.py\n'
     'Write: src/stale_repro/memory/base.py\n'
     'Write: src/stale_repro/memory/full_context.py\n'
     'python - <<EOF   # copy judge prompt byte-for-byte, prepend provenance header\n'
     '  src = open("external/STALE/STALE/Evaluation/judge_prompts.py").read()\n'
     '  open("src/stale_repro/eval/judge_prompts.py", "w").write(header + src)\n'
     'EOF\n'
     'Write: src/stale_repro/eval/judge.py, eval/stats.py, runner.py\n'
     'Write: scripts/run_experiment.py, configs/b0_gpt4omini_dev.yaml\n'
     'for d in . data llm memory memory/cupmem eval diagnostics; do echo "" > $d/__init__.py; done',
     "Eight modules plus CLI and config. Part IV explains each in detail.")
step(13, "Write the tests",
     "Catch pipeline bugs cheaply before any money is spent on API calls.",
     'Write: tests/conftest.py        (FakeBackend, toy Seattle->Portland and broken-leg scenarios)\n'
     'Write: tests/test_gateway.py    (13 tests)\n'
     'Write: tests/test_pipeline.py   (10 tests)',
     "23 tests covering every module, including a full end-to-end run with resume.")
step(14, "Create a virtual environment, install, run the tests",
     "Isolate dependencies from the system Python; verify everything works.",
     'python -m venv .venv\n'
     '.venv/Scripts/python -m pip install -q --upgrade pip\n'
     '.venv/Scripts/python -m pip install -q -e ".[dev]"\n'
     '.venv/Scripts/python -m pytest -q',
     "<b>23 passed in 14.73 s</b> on the first run.")
step(15, "Measure the real dataset",
     "Know how much truncation is needed and what runs will cost before running them.",
     'python - <<EOF\n'
     '  insts = load_stale("data/stale/T1_T2_400_FULL.json")\n'
     '  enc = tiktoken.get_encoding("o200k_base")\n'
     '  tokens per instance = len(enc.encode(format_haystack(sessions, timestamps)))\n'
     '  per-type mean/median/max, count > 125,440, evidence-session gap, B0 cost\n'
     'EOF',
     "See Section 10. Every instance exceeds the limit. B0 costs about $23 for all 400 instances, or about $3 for the dev subset.")
step(16, "Check overlapping recent work",
     "The blueprint flagged risk of being scooped; two candidates appeared in step 2.",
     'WebFetch: https://arxiv.org/abs/2608.07429    (TEPA)\n'
     'WebFetch: https://arxiv.org/abs/2608.01619    (StateAuditor)',
     "Neither reimplements CUPMem, studies small adjudicators, or solves multi-hop cascades (Section 13).")
step(17, "Document",
     "Keep a single source of truth for facts, ambiguities and deviations.",
     'Write: notes/reproducibility_log.md, README.md\n'
     'Write: memory note (project context for future sessions)',
     "Log with verified facts, six open questions, deviation table and related-work notes.")
step(18, "Produce this report",
     "Record the session in a shareable form.",
     '.venv/Scripts/python -m pip install reportlab pypdfium2\n'
     '.venv/Scripts/python notes/make_week1_report.py\n'
     'render pages with pypdfium2 -> PNG, inspect layout, fix, rebuild',
     "This PDF. The generator script lives next to it, so the report can be rebuilt after code changes; the appendix "
     "listings are read from the real files.")

H("5. Tools used")
h("5.1 Claude Code assistant tools")
table([["Tool", "Used for in this session", "Typical invocation"],
       ["WebSearch", "Finding the paper, the code release and related papers", "Two queries (step 2)"],
       ["WebFetch", "Reading arXiv abstract, HTML and PDF pages; summarising related-paper abstracts", "Five fetches (steps 2, 3, 16)"],
       ["Bash (Git Bash)", "git, curl, python, pip, pytest, grep, sed, wc, cat; one background download", "About 30 calls"],
       ["Read", "Reading the extracted paper text and official source at chosen line ranges; viewing rendered PDF pages", "Paper App. E-G, run_target_model.py"],
       ["Write", "Creating every source file, test, config and document", "About 20 files"],
       ["ToolSearch", "Loading the WebSearch/WebFetch tool schemas", "Once"],
       ["GetTask", "Checking the background dataset download", "Once"],
       ["Skill (pdf)", "PDF-generation guidance (reportlab)", "Once"],
       ["Memory", "Saving project context for future sessions", "One note plus index"]], [28, 90, 52])
h("5.2 Software and libraries")
table([["Software", "Version", "Why it was chosen"],
       ["Python", "3.12.10, venv in .venv/", "Ecosystem for LLM work; matches the official code (3.10+)"],
       ["openai SDK", ">=1.40", "One client for OpenAI, vLLM, Gemini's OpenAI endpoint and hosted open models"],
       ["tiktoken", ">=0.7", "Same tokenizer the official truncation uses; needed for exact parity"],
       ["numpy", ">=1.26", "Vectorised bootstrap resampling"],
       ["PyYAML", ">=6.0", "Human-readable experiment configs, one per experiment"],
       ["python-dotenv", ">=1.0", "Keeps API keys out of code and configs"],
       ["tqdm", ">=4.66", "Progress bars for long runs"],
       ["sqlite3", "stdlib", "Zero-dependency, concurrent-safe, single-file cache"],
       ["pytest", ">=8.0", "Standard Python test runner; fixtures for fakes"],
       ["pypdf", "pre-installed", "Extracting the paper's text to search appendices"],
       ["git / curl", "2.55 / system", "Cloning the repo; downloading the dataset and HF metadata"],
       ["reportlab / pypdfium2", "latest", "Building and visually checking this PDF"]], [32, 38, 100])

# ======================================================================= PART III
part("Part III: Findings")
H("6. The artifacts are public")
table([["Artifact", "Location", "Details"],
       ["Paper", "arxiv.org/abs/2605.06527 (v1)", "37 pages; CC BY 4.0; saved to papers/, text in papers/stale.txt"],
       ["Code", "github.com/icedreamc/STALE", "Commit ea7d391; MIT; cloned to external/STALE"],
       ["Dataset", "huggingface.co/datasets/STALEproj/STALE", "T1_T2_400_FULL.json, 306 MB, HF sha 617c51dc; CC BY 4.0"],
       ["Distractors", "LongMemEval sessions", "MIT licence (per App. G)"]], [22, 58, 90])
P("Because the complete official CUPMem is released, RQ1 now compares three sources:")
bullets(["(a) the numbers in the paper;",
         "(b) the official code, re-run by us;",
         "(b') the official code in each session mode;",
         "(c) our independent reimplementation."])
P("A disagreement between any two of these is itself a reproducibility finding.")

H("7. Dataset facts")
table([["Property", "Type I", "Type II"],
       ["Instances", "200", "200"],
       ["Sessions per instance", "50", "50"],
       ["Serialized tokens, mean", "151,705", "151,863"],
       ["Serialized tokens, median", "151,505", "152,264"],
       ["Serialized tokens, max", "162,693", "164,919"],
       ["Instances over 125,440-token input budget", "200 (all)", "200 (all)"],
       ["Mean session gap, old to new evidence", "27.1", "27.3"]], [80, 45, 45])
bullets([
    "Average of 11.9 turns per session, so about 3K tokens per session.",
    "The old evidence session index always lies in <b>[0, 14]</b> (mean 7.4); the new one always in <b>[30, 39]</b> "
    "(mean 34.7). This positional regularity comes from the generation pipeline. It is worth noting because a system "
    "could in principle exploit position; we will report it and make sure no system sees indices.",
    "Timestamps are shifted so the final session (query time) falls in 2025.",
    "Record fields: uid, type, M_old, M_new, explanation, probing_queries{dim1_query, dim2_query, dim3_query}, "
    "haystack_session[50][turns{role, content}], timestamps[50], relevant_session_index[2]."])

H("8. Evaluation protocol, as implemented officially")
h("8.1 Response generation")
P("SR and PR use the \"accurately answer the question\" system prompt with " + M("[Question]") + ". IPA uses the "
  "\"respond to the user's latest query directly\" prompt with " + M("[Latest Query]") + ". The history is "
  "serialized as:")
code("""
=== Session 1 [Time: 2020-04-24 18:15] ===
User: ...
Assistant: ...

=== Session 2 [Time: 2020-05-31 12:43] ===
...
""")
h("8.2 Judge")
bullets([
    "One joint call per instance grades all three responses (Appendix B has the full prompt).",
    "Settings: " + M("temperature=0") + ", " + M("response_format={\"type\": \"json_object\"}") + ", model Gemini-3.1-flash-lite.",
    "Output: " + M("{dim1_eval: {reasoning, pass}, dim2_eval: ..., dim3_eval: ...}") + ".",
    "Any exception (network or parse) is scored as FAIL on all three dimensions. It is printed but not counted separately."])
h("8.3 Evidence-preserving truncation (B0)")
code("""
input budget = 128,000 - 2,048 (output reserve) - 512 (safety) = 125,440 tokens, applied per probe
phase 1: drop up to 2 sessions from the head (never past S_old)
phase 2: drop up to 2 sessions from the tail (never past S_new)
phase 3: while over budget: drop a random session strictly between S_old and S_new
S_old and S_new are always kept. Token count uses tiktoken (model encoding, o200k_base fallback)
plus chat-format overhead (3 per message + 3 priming).
""")
P("Because the old evidence sits within the first 15 sessions and the new within sessions 30-39, phase 3 always does "
  "most of the work. The truncated context therefore keeps the start of the history and loses the middle.")

H("9. The official CUPMem implementation")
table([["Package", "Key files (lines)", "Role"],
       ["write/", "delta_extractor (322), update_resolver (412), invalidation_lanes (503), invalidation_merge (481), "
                  "invalidation_resolver (185), invalidation_judge (145), stale_linker (191), writer (245), chunker (179)",
        "Session chunking, candidate extraction, same-slot update, latent invalidation across lanes (direct / affected / global), merge and judge"],
       ["query/", "readout (705), support (792), basis_recovery_impl (723), premise_verifier (525), track_hints (429), "
                  "action_grounding (339), engine (212), retrieval (69)",
        "Query analysis, premise verification, basis recovery, constrained answer"],
       ["store_layer/", "transitions (372), in_memory (232)", "Profile store and status transitions"],
       ["memory/", "models (335), schema (186)", "Data classes; the Table 8 schema"],
       ["llm_layer/", "client (530), responses_adapter (491)", "Chat and Responses API clients with cache and call records"],
       ["prompt_lib/", "templates (467)", "All prompts"],
       ["core/", "engine_utils (326), sample_runner (234), temporal (88), config (28)", "Orchestration, thresholds"]],
      [24, 86, 60])
P("Note on labels: the paper's main text describes a four-way KEEP/STALE/REPLACE/UNKNOWN decision. Appendix F.2 "
  "instead describes a local update (ADD/REFINE/REPLACE/NO_OP) followed by a separate latent-invalidation judge. The "
  "code, split into update_resolver and invalidation_*, follows the appendix. Our reimplementation will follow the "
  "code, and the difference will be documented.")

H("10. Open questions and ambiguities")
h("10.1 Session mode (the central question)")
P("The default " + M("relevant_only") + " ingests only " + M("haystack_session[i] for i in relevant_session_index") +
  ". This gives CUPMem oracle knowledge of where the evidence is, which no baseline has.")
h("10.2 What the paper's cost figure implies (estimate)")
P("GPT-4o-mini costs $0.15 per million input tokens and $0.60 per million output tokens.")
bullets([
    "<b>Paper's figure.</b> $0.37 per instance corresponds to roughly 2.0-2.5 million tokens processed per instance.",
    "<b>Full mode.</b> CUPMem makes several LLM calls per session (chunking, extraction, update resolution, "
    "invalidation lanes, judging). Over 50 sessions of about 3K tokens each, reaching millions of tokens is plausible.",
    "<b>relevant_only mode.</b> Two sessions of about 3K tokens each give roughly 6K tokens of content. Even with 20x "
    "call amplification, that is about 120K tokens, or around $0.02."])
P("The cost figure therefore points to full mode, but this is indirect evidence. The plan:")
bullets(["Run the official code in both modes on the same subset.",
         "Record tokens and accuracy for each.",
         "Report relevant_only as an explicit oracle-retrieval ablation.",
         "Ask the corresponding author."])
h("10.3 Full CUPMem thresholds (cup_mem/core/config.py)")
table([["Parameter", "Value", "Parameter", "Value"],
       ["state_salience_threshold", "0.30", "candidate_top_k", "5"],
       ["explicit_min_confidence", "0.45", "latent_invalidation_temperature", "0.30"],
       ["strong_support_min_confidence", "0.55", "invalidation_lane_max_workers", "4"],
       ["medium_support_min_confidence", "0.60", "invalidation_merge_max_keep", "2"],
       ["verifier_fallback_threshold", "0.45", "invalidation_global_recall_top_k", "4"],
       ["query_top_k", "8", "fallback_top_k", "6"]], [50, 20, 60, 40])
h("10.4 Other open questions")
table([["#", "Issue", "Plan"],
       ["2", "Target temperature unstated; official code sends none (OpenAI default 1.0)", "Decide: 0 only, or also default for E1 fidelity"],
       ["3", "Judge errors silently become FAIL", "Record, re-judge, report the count (deviation D2)"],
       ["4", "Label sets differ between main text and appendix/code", "Follow the code; document"],
       ["5", "Embedding model named only in the code README (all-MiniLM-L6-v2)", "Use the same"],
       ["6", "Exact judge API model id string", "Confirm when setting up the Gemini key"]], [8, 92, 70])

H("11. Related work check")
table([["Paper", "What it does", "Overlap with our RQs"],
       ["StateAuditor (Sun &amp; He, arXiv:2608.01619)",
        "Readout-side audit from stored state to draft response. An LLM proposes old-to-new transitions and deterministic code "
        "verifies them. +5.0 points on full STALE.",
        "None on CUPMem reproduction, small adjudicators or multi-hop. Cite it, and consider it as a readout-side baseline."],
       ["TEPA (Zhou et al., arXiv:2608.07429)",
        "Keyed precedents; revokes active precedents when fresh evidence contradicts them. 0.950 vs 0.21-0.31 baselines on "
        "single-hop settings.",
        "Not evaluated on STALE per its abstract. Its authors state multi-hop exposes bottlenecks beyond their method, which "
        "supports RQ5."],
       ["<i>The Memory Trust Gap</i>", "Mentioned in the blueprint", "Not yet located; to do"]], [38, 72, 60])

# ======================================================================= PART IV
part("Part IV: How the code works")
H("12. Design principles")
table([["Principle", "How it is realised", "Why it matters for this paper"],
       ["Fidelity first", "Prompts, serializer, truncation and judge are copied or ported from the official code; tests assert exact strings",
        "Differences in results must come from methods, not from evaluation drift"],
       ["Every call reproducible", "SQLite cache keyed by a hash of model, messages and parameters; seeded randomness",
        "A reproducibility paper must itself be reproducible; reruns are free"],
       ["One interface for all systems", "MemorySystem with reset / ingest / answer", "Baselines, official CUPMem, our CUPMem and CUPMem+ are interchangeable"],
       ["Observability built in", "Answer.trace; per-tag usage logs; JSON failures counted", "Needed for RQ3 attribution and RQ4 cost"],
       ["No label leakage", "Systems never receive M_old, M_new or evidence indices; only B0 truncation uses indices, as in the paper",
        "Fair comparison"],
       ["Crash-safe runs", "Append-only JSONL outputs; resume skips finished instances", "Long API runs fail midway; no lost money"],
       ["Test without spending", "FakeBackend and toy scenarios", "Bugs caught before any paid call"]], [30, 75, 65])

H("13. Module walkthrough")
P("Package layout and data flow:")
code(r"""
src/stale_repro/
  llm/gateway.py          every LLM call: backends, sqlite cache, JSON decoding, usage accounting
  data/loader.py          raw JSON -> Instance / Session / Probe; deterministic stratified subsets
  memory/base.py          MemorySystem interface; official response prompts
  memory/full_context.py  B0 baseline; official serializer and evidence-preserving truncation
  eval/judge_prompts.py   official judge system prompt (verbatim copy)
  eval/judge.py           joint judge call -> Verdict
  eval/stats.py           cell accuracies, Overall, bootstrap CIs, McNemar, results table
  runner.py               config -> answers.jsonl -> verdicts.jsonl -> summary
scripts/run_experiment.py CLI wrapper

config.yaml -> select_subset -> [parallel per instance]
     system.reset(); system.begin_instance(inst); system.ingest_many(sessions)
     system.answer(dim1), answer(dim2), answer(dim3)          -> runs/<name>/answers.jsonl
  -> Judge.judge(inst, answers)                               -> runs/<name>/verdicts.jsonl
  -> cell_accuracies, bootstrap_ci, results_table             -> runs/<name>/summary.{json,md}
  every LLM call: Gateway.chat -> cache lookup -> backend -> cache store -> usage log
""")

h("13.1 llm/gateway.py: the LLM gateway (242 lines)")
P("Built first because every other component calls it. It hides which provider is used and guarantees caching, JSON "
  "handling and usage accounting everywhere.")
table([["Element", "What it does and why"],
       [M("Usage"), "Dataclass holding prompt_tokens and completion_tokens."],
       [M("LLMResponse"), "text, model, usage, latency_s, cached flag, parsed JSON (if requested), parse_error. The "
                          + M("ok_json") + " property is true only when parsing succeeded."],
       [M("Backend") + " (Protocol)", "Any object with " + M("complete(model, messages, params) -> (text, Usage)") + ". "
        "This is the seam that lets tests inject a fake."],
       [M("OpenAICompatBackend"), "Wraps " + M("openai.OpenAI(base_url, api_key, timeout=600, max_retries=5)") + ". The same "
        "class serves OpenAI, vLLM, Gemini's OpenAI endpoint and hosted open-model providers. The SDK's own retries "
        "handle rate limits."],
       [M("parse_json_loose(text)"), "Strips ```json fences, tries json.loads, then falls back to the outermost {...} or [...] "
        "span. Raises ValueError if nothing parses. Small models often wrap JSON in prose, so strict parsing would "
        "misattribute failures."],
       [M("_Cache"), "SQLite table (key TEXT PRIMARY KEY, value TEXT). " + M("check_same_thread=False") + " plus a lock "
        "makes it safe for the runner's thread pool. Values store text, usage and latency."],
       [M("UsageTotals"), "Per-tag counters: calls, cached_calls, tokens, latency, json_failures."],
       [M("Gateway.chat(...)"), "Main entry point. Accepts a string or message list, an optional system prompt, "
        + M("json_mode") + " or " + M("json_schema") + ", a model override, and decoding params (default temperature 0). "
        "It builds " + M("response_format") + ", calls " + M("_call") + ", then parses JSON if requested. On failure it "
        "retries once with a repair turn (\"Your previous reply was not valid JSON...\"), tagged " + M("<tag>.repair") +
        ". If that also fails, " + M("json_failures") + " is incremented."],
       [M("cache_key(...)"), "SHA-256 of canonical JSON (sorted keys) of {cache version, model, messages, params}. Any change "
        "in prompt, model or decoding parameters gives a new key. Bumping CACHE_VERSION invalidates everything."],
       [M("_call(...)"), "Cache lookup; on a miss, time the backend call and store the result. Always records usage, "
        "including cache hits flagged as cached, so cost reports can separate real spend from replay."],
       [M("_record / _bump"), "Update per-tag totals and append one JSONL line per call: ts, tag, model, key prefix, cached, "
        "tokens, latency."],
       [M("summary() / reset_totals()"), "Snapshot or clear the per-tag totals; the runner stores them in summary.json."],
       [M("gateway_from_config(cfg)"), "Builds a Gateway from a YAML block: model, base_url, api_key_env (name of the env "
        "variable, never the key itself), params."]], [42, 128])
code('''
gw = gateway_from_config({"model": "gpt-4o-mini", "api_key_env": "OPENAI_API_KEY"}, "cache", "runs/x/calls.jsonl")
r = gw.chat([{"role": "user", "content": prompt}], system=SYS, json_mode=True, tag="judge", temperature=0)
if r.ok_json: use(r.parsed)
print(gw.summary())   # {"judge": {"calls": 1, "cached_calls": 0, "prompt_tokens": ..., "json_failures": 0}}
''')

h("13.2 data/loader.py: data model and subsets (109 lines)")
table([["Element", "What it does and why"],
       [M("DIMS, DIM_NAMES, TYPE_NAMES"), "Constants mapping dim1/2/3 to SR/PR/IPA and T1/T2 to Type I/II."],
       [M("Session"), "index, timestamp, turns. " + M("render()") + " produces User:/Assistant: lines."],
       [M("Probe"), "uid, dim, text, query_time (the last session's timestamp). " + M("is_task") + " is true for dim3, which "
        "selects the IPA prompt."],
       [M("Instance"), "uid, type, m_old, m_new, explanation, probes (dict), sessions, idx_old, idx_new, meta (any unknown "
        "fields, kept rather than dropped). Helpers: evidence_indices, raw_sessions(), timestamps()."],
       [M("parse_record(rec)"), "Converts one raw JSON record into an Instance."],
       [M("load_stale(path)"), "Loads the file. Accepts a JSON list or an object with a 'data' list, like the official scripts."],
       [M("select_subset(...)"), "Deterministic stratified subset. Within each type, instances are sorted by "
        + M("sha256(f'{seed}:{uid}')") + " and the first n are taken. The selection therefore depends only on (seed, n) and "
        "not on file order, and larger subsets contain smaller ones. An explicit uid list is also supported."]], [42, 128])

h("13.3 memory/base.py: the common interface (58 lines)")
bullets([
    M("SYSTEM_QA") + " / " + M("SYSTEM_TASK") + ": the two official response-generation system prompts, verbatim.",
    M("build_answer_prompt(history, probe)") + ": returns (system, user) exactly as the official code does, using "
    + M("[Question]") + " for SR/PR and " + M("[Latest Query]") + " for IPA. Memory systems that produce their own "
    "context can still reuse this so the probe framing stays identical.",
    M("Answer(text, trace)") + ": trace is a free-form dict. CUPMem will put store snapshots, candidate sets and "
    "adjudication labels here for failure attribution.",
    M("MemorySystem") + ": " + M("reset()") + ", " + M("begin_instance(inst)") + ", abstract " + M("ingest(session)") +
    " and " + M("answer(probe)") + ", plus " + M("ingest_many") + ". The docstring on begin_instance makes the rule "
    "explicit: systems must not read labels. Only B0 uses it, to get evidence indices for truncation, exactly as the "
    "paper does."])

h("13.4 memory/full_context.py: B0 baseline (133 lines)")
table([["Element", "What it does and why"],
       [M("format_haystack(sessions, timestamps)"), "Character-for-character port of the official serializer. A test "
        "compares the exact output string."],
       [M("_encoder(model)"), "Cached tiktoken encoder: the model's own encoding if tiktoken knows it, else o200k_base, "
        "as in the official code."],
       [M("count_message_tokens"), "Official chat-format estimate: 3 tokens per message plus content tokens plus 3 for reply priming."],
       [M("trim_evidence_preserving(...)"), "The three-phase algorithm in Section 8.3, operating on copies and re-counting "
        "tokens after each drop, as in the official code. It returns the trimmed sessions and timestamps, the final token "
        "count and the number removed. Phase 3 draws from an injected " + M("random.Random") + ", which makes it deterministic."],
       [M("FullContext.__init__"), "gateway, context_limit (None disables truncation), reserved_output=2048, "
        "safety_margin=512, seed, optional max_tokens."],
       [M("FullContext.ingest"), "Appends the session; B0 has no memory processing."],
       [M("FullContext.answer"), "If a limit is set, derives a per-(seed, uid, dim) RNG seed from SHA-256 and truncates. "
        "Then builds the official prompt and calls the gateway with tag " + M("B0_full_context.answer") + ". The trace "
        "records sessions removed, estimated request tokens, usage and cache status."]], [48, 122])

h("13.5 eval/judge_prompts.py and eval/judge.py: the judge (136 lines)")
bullets([
    "<b>Prompt provenance.</b> judge_prompts.py was produced by a script that reads the official file and writes it back "
    "with a header naming the source commit and licence. Retyping a 40-line prompt risks invisible differences, "
    "such as a changed space or quote, that would break comparability.",
    M("build_judge_user_prompt(inst, responses)") + ": the official f-string, reproduced exactly, including the "
    "quotes around M_old and M_new and the separator lines.",
    M("Verdict") + ": uid, type, passed {dim: bool}, reasoning {dim: str}, error. Includes to_dict/from_dict for JSONL.",
    M("_as_bool") + ": accepts true booleans and the strings \"true\"/\"false\". Anything else counts as false.",
    M("parse_judge_output") + ": requires all three dimK_eval blocks with a pass field. A missing key raises an error "
    "instead of guessing.",
    M("Judge.judge(inst, responses)") + ": one call with the official system prompt, json_mode and temperature 0, tagged "
    + M("judge") + ". Any failure yields a Verdict with all False and a non-empty " + M("error") + ". The runner "
    "re-judges errored verdicts on the next run and reports the count."])

h("13.6 eval/stats.py: scoring and statistics (98 lines)")
table([["Function", "What it does and why"],
       [M("cell_accuracies(verdicts)"), "Accuracy for each of the six (type, dim) cells, plus " + M("overall") +
        " = unweighted mean of the cells, matching the paper. This is not the mean over all 1,200 queries (identical only "
        "when types are balanced)."],
       [M("bootstrap_ci(...)"), "2,000 percentile-bootstrap resamples (default) of <b>instances within each type</b>. "
        "The three probes of one instance share the same memory state, so they are correlated. Resampling individual "
        "queries would make confidence intervals too narrow. Stratifying by type keeps the design balanced. The "
        "overall CI is computed on the resampled six-cell mean."],
       [M("mcnemar_exact(a, b)"), "Exact two-sided McNemar test on paired binary outcomes: counts discordant pairs and "
        "uses the binomial distribution. It is exact, so there is no chi-square approximation issue with small counts."],
       [M("paired_outcomes(va, vb, dim, type_)"), "Aligns two systems' verdicts on common uids, optionally restricted to "
        "one dimension or type, ready for McNemar."],
       [M("results_table(verdicts)"), "Markdown row in the paper's column order, with [lo, hi] CIs and a judge-error count."]],
      [46, 124])

h("13.7 runner.py and scripts/run_experiment.py: running experiments (161 lines)")
table([["Element", "What it does and why"],
       [M("_registry()"), "Maps a config " + M("kind") + " to a MemorySystem class. Currently only " + M("full_context")
        + "; new systems register here."],
       [M("run_system_on_instance(system, inst, mode)"), "reset, then begin_instance, then ingest all 50 sessions (or only "
        "the two evidence sessions in " + M("relevant_only") + " mode, mirroring the official CUPMem option), then "
        "answer dim1-3. Returns uid, type, answers and traces."],
       [M("run(cfg)"), "(1) Create runs/&lt;name&gt; and save the config. (2) Load and subset data. (3) Answer: skip uids already "
        "in answers.jsonl, then run the rest in a thread pool, with a fresh system per task sharing one gateway. "
        "(4) Judge: skip uids with an error-free verdict. (5) Take the last verdict per uid, compute accuracies and CIs, "
        "and write summary.json (including per-tag usage for system and judge) and summary.md."],
       [M("_JsonlWriter"), "Lock-protected append. Each line is complete, so a crash loses at most in-flight instances."],
       [M("_pool(fn, items, workers)"), "ThreadPoolExecutor with a tqdm bar. It collects all exceptions, prints up to 5, and "
        "raises one summary error telling you to rerun to resume. Threads (rather than asyncio) fit because the work is "
        "network-bound and the memory-system code stays simple and synchronous."],
       [M("scripts/run_experiment.py"), "Loads .env, reads the YAML, and applies " + M("--n-per-type") + " (appended to the "
        "run name so smoke tests never mix with real runs), " + M("--workers") + ", " + M("--out-root") + " and "
        + M("--cache-dir") + ". Prints the headline numbers."]], [52, 118])
P("Outputs of one run, in " + M("runs/<name>/") + ": config.yaml, answers.jsonl (answers and per-probe traces), "
  "verdicts.jsonl, summary.json, summary.md, llm_calls.jsonl and judge_calls.jsonl.")

# ======================================================================= PART V
part("Part V: Testing, deviations, reproduction, next steps")
H("14. Testing")
P("<b>Strategy.</b> " + M("FakeBackend") + " implements the Backend protocol by calling a scripted Python function "
  "and records every request (model, messages, params). Tests can therefore assert exactly what would be sent to a "
  "real API, at zero cost. A " + M("make_gateway") + " fixture builds a Gateway with a temporary cache and log.")
P("Toy scenarios mirror the paper's conflict types and are built by " + M("toy_record") + " as six-session "
  "instances with filler sessions:")
bullets([
    "<b>toy-seattle (T1)</b>: \"lived in Seattle for years\" (session 1), then \"set up electricity and internet at my "
    "new apartment in Portland\" (session 4).",
    "<b>toy-leg (T2)</b>: \"cycle to work every day, 8 km\" (session 1), then \"leg in a cast for six weeks after the "
    "fracture\" (session 4)."])
table([["Test", "Verifies"],
       ["test_cache_hit_skips_backend", "Second identical call is served from cache; backend called once; totals count 2 calls, 1 cached"],
       ["test_cache_key_depends_on_params", "Different temperature or model triggers new backend calls"],
       ["test_cache_persists_across_gateways", "A new Gateway on the same file reuses stored responses (the replacement backend is never called)"],
       ["test_json_mode_parses_fenced_output", "```json fences parsed; response_format set to json_object"],
       ["test_json_repair_retry_then_failure_is_counted", "Two bad replies: one retry, json_failures incremented"],
       ["test_json_repair_retry_succeeds", "Bad reply then good reply: parsed result returned"],
       ["test_json_schema_sets_response_format", "json_schema produces a strict json_schema response_format"],
       ["test_usage_log_written", "JSONL call log contains the caller's tag"],
       ["test_parse_json_loose [3 cases]", "Plain JSON; JSON inside prose; fenced array"],
       ["test_parse_json_loose_raises", "Text without JSON raises ValueError"],
       ["test_loader_roundtrip", "Toy file loads; types, evidence indices, content and is_task are correct"],
       ["test_subset_is_deterministic_and_stratified", "Same subset regardless of input order; 3 per type"],
       ["test_format_haystack_matches_official", "Exact serialized string equals the official format"],
       ["test_truncation_preserves_evidence", "20 long sessions trimmed to 4,000 tokens: both evidence sessions kept, sessions removed, budget respected"],
       ["test_b0_sends_official_prompts", "Correct system prompt per probe; [Latest Query] for IPA; evidence present in context"],
       ["test_relevant_only_mode_ingests_two_sessions", "Oracle mode serializes exactly 2 sessions"],
       ["test_judge_prompt_and_parse", "Official system prompt sent byte-for-byte; temperature 0; user prompt format; verdict parsed"],
       ["test_judge_malformed_output_is_error_not_silent", "Incomplete judge JSON produces an error field and all-False"],
       ["test_overall_is_mean_of_six_cells", "Hand-computed cell and overall values; degenerate CI for a constant cell"],
       ["test_mcnemar", "Identical outcomes give p=1; 10 vs 0 discordant gives p&lt;0.01"],
       ["test_runner_end_to_end", "Full config run with fake system and judge; overall 1.0; rerun resumes with identical result; output files exist"]],
      [70, 100])
code("""
> .venv/Scripts/python -m pytest -q
.......................                                                  [100%]
23 passed in 14.73s
""")

H("15. Deviations from the official code")
P("Every deviation is intentional, minimal, and logged in notes/reproducibility_log.md.")
table([["ID", "Where", "Official", "Ours", "Reason"],
       ["D1", "B0 truncation phase 3", "Unseeded random.choice", "RNG seeded by SHA-256(seed, uid, dim)", "Exact reruns"],
       ["D2", "Judge errors", "Silently FAIL", "error field; re-judged on resume; count reported", "Transparency"],
       ["D3", "Target temperature", "Not set (API default 1.0)", "0 in configs, configurable", "Determinism and caching; E1 choice pending"],
       ["D4", "Truncation token counting", "tiktoken, o200k fallback", "Same", "none"]], [10, 32, 36, 52, 40])

H("16. How to reproduce everything")
code(r"""
# 1. environment
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"            # use .venv/bin/python on Linux/macOS
cp .env.example .env                                         # OPENAI_API_KEY, GEMINI_API_KEY

# 2. data and official code
curl -L -o data/stale/T1_T2_400_FULL.json \
  https://huggingface.co/datasets/STALEproj/STALE/resolve/main/T1_T2_400_FULL.json
git clone https://github.com/icedreamc/STALE external/STALE

# 3. offline tests
.venv/Scripts/python -m pytest

# 4. smoke test (2 per type), then 50-instance dev run
.venv/Scripts/python scripts/run_experiment.py configs/b0_gpt4omini_dev.yaml --n-per-type 2
.venv/Scripts/python scripts/run_experiment.py configs/b0_gpt4omini_dev.yaml

# 5. rebuild this report
.venv/Scripts/python notes/make_week1_report.py
""")

H("17. Open decisions, next steps, budget")
h("17.1 Decisions needed")
bullets(["API keys: OpenAI (GPT-4o-mini target) and Gemini (judge); confirm the judge model id.",
         "Target temperature for E1: 0 only, or also the official default?",
         "Initialise git and make the first commit.",
         "Contact the corresponding author about the session mode. The Gmail connector is not yet authorised; a draft can be written instead."])
h("17.2 Next steps")
table([["#", "Task", "Output", "Blueprint"],
       ["1", "Smoke test, then B0 on the dev subset", "First real numbers vs paper's GPT-4o-mini row", "E1 / week 3"],
       ["2", "Wrap official CUPMem as a MemorySystem; run in full and relevant_only modes", "Answer to the central question; per-mode cost", "RQ1"],
       ["3", "Reconcile label sets against cup_mem/write/", "Spec for our reimplementation", "Weeks 4-5"],
       ["4", "Independent CUPMem: store, extract, search, adjudicate, readout", "System M", "Weeks 4-5"],
       ["5", "B1 naive RAG, B2 Mem0", "Baselines", "Week 3"],
       ["6", "Attribution from traces", "Key failure-analysis figure", "RQ3"],
       ["7", "Open-model backbones 3B-32B", "Accuracy vs size", "E2 / weeks 7-8"]], [8, 72, 58, 32])
h("17.3 Budget estimates so far")
table([["Run", "Estimate", "Basis"],
       ["B0 GPT-4o-mini, dev subset (50)", "~$3", "~125K input tokens x 3 probes x 50 x $0.15/M"],
       ["B0 GPT-4o-mini, full (400)", "~$23", "Same, 400 instances"],
       ["Official CUPMem full mode, full (400)", "~$150", "Paper's $0.37/instance; to be measured"],
       ["Judge", "small", "One call per instance with short inputs"]], [60, 25, 85])

# ======================================================================= APPENDICES
part("Appendix A: Complete source code")
P("Every file below is included in full and read from disk when this PDF is built, so it always matches the code. "
  "Lines longer than 112 characters are wrapped with a 4-space continuation indent.")
FILES = [
    ("pyproject.toml", "Packaging and dependencies"),
    ("configs/b0_gpt4omini_dev.yaml", "B0 development experiment"),
    ("src/stale_repro/llm/gateway.py", "LLM gateway"),
    ("src/stale_repro/data/loader.py", "Data model and subsets"),
    ("src/stale_repro/memory/base.py", "MemorySystem interface"),
    ("src/stale_repro/memory/full_context.py", "B0 baseline"),
    ("src/stale_repro/eval/judge.py", "Judge"),
    ("src/stale_repro/eval/stats.py", "Statistics"),
    ("src/stale_repro/runner.py", "Experiment runner"),
    ("scripts/run_experiment.py", "CLI"),
    ("tests/conftest.py", "Test fixtures"),
    ("tests/test_gateway.py", "Gateway tests"),
    ("tests/test_pipeline.py", "Pipeline tests"),
    (".gitignore", "Ignore rules"),
    (".env.example", "API-key template"),
]
for i, (rel, desc) in enumerate(FILES, 1):
    src = (ROOT / rel).read_text(encoding="utf-8")
    n = src.count("\n") + (0 if src.endswith("\n") else 1)
    story.append(Paragraph(f"A.{i} {rel} ({n} lines): {desc}", H1 if i == 1 else H1))
    code(src, LIST, width=118)

part("Appendix B: Official judge prompt")
P("System prompt, as copied into " + M("src/stale_repro/eval/judge_prompts.py") + " from icedreamc/STALE @ ea7d391 "
  "(MIT). It is reproduced here without modification, including its original wording.")
from importlib import util as _u  # noqa: E402
_spec = _u.spec_from_file_location("jp", ROOT / "src/stale_repro/eval/judge_prompts.py")
_jp = _u.module_from_spec(_spec); _spec.loader.exec_module(_jp)
code(_jp.SYSTEM_PROMPT_ALL_IN_ONE_JUDGE, LIST, width=118)
P("User prompt template:")
code('''
[Ground Truth Context]
- M_old: "{old_info}"
- M_new: "{M_new}"
- Hidden Logic: {explanation}

--------------------------------------------------
[Dimension 1: Explicit Probing]
Question 1: {dim1_q}
Target Model Response 1: {dim1_a}

--------------------------------------------------
[Dimension 2: Adversarial Robustness]
Question 2: {dim2_q}
Target Model Response 2: {dim2_a}

--------------------------------------------------
[Dimension 3: Implicit Task]
Question 3: {dim3_q}
Target Model Response 3: {dim3_a}
''', LIST)

H("Appendix C: Glossary")
table([["Term", "Meaning"],
       ["Implicit conflict", "A later observation invalidates an earlier memory without explicitly negating it"],
       ["Type I / Type II", "Same-attribute conflict / conflict propagated from one attribute to another"],
       ["SR / PR / IPA", "State Resolution / Premise Resistance / Implicit Policy Adaptation (dim1 / dim2 / dim3)"],
       ["Haystack", "The 50-session conversation history, mostly distractor sessions from LongMemEval"],
       ["Evidence sessions", "S_old and S_new, the two sessions containing M_old and M_new"],
       ["relevant_only", "Official CUPMem mode that ingests only the two evidence sessions (oracle)"],
       ["Evidence-preserving truncation", "Dropping distractor sessions to fit a context window while keeping S_old and S_new"],
       ["Adjudication", "CUPMem's write-time decision about whether an old memory stays valid"],
       ["B0 / B1 / B2 / B3 / M / M+", "Full context / naive RAG / Mem0 / LightMem / our CUPMem / CUPMem with multi-hop propagation"],
       ["Bootstrap CI", "Confidence interval from resampling instances with replacement"],
       ["McNemar test", "Paired test for whether two systems differ on the same items"],
       ["Gateway", "Our single module through which every LLM call passes"],
       ["vLLM", "Open-source server that exposes open models through an OpenAI-compatible API"]], [45, 125])


# ======================================================================= BUILD
def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.grey)
    if doc.page > 1:
        canvas.drawString(18 * mm, 10 * mm, "STALE / CUPMem reproduction: Week 1 technical record (detailed)")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


doc = Doc(str(OUT), pagesize=A4, leftMargin=19 * mm, rightMargin=19 * mm, topMargin=17 * mm, bottomMargin=17 * mm,
          title="STALE/CUPMem Reproduction: Week 1 Technical Record", author="hrithikgh29@gmail.com")
doc.multiBuild(story, onFirstPage=on_page, onLaterPages=on_page)
print("wrote", OUT)
