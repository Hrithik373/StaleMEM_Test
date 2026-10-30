"""Generate manuscript figures from the checked-in experiment records."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[2]
FIGURES = Path(__file__).resolve().parent
SUMMARY = ROOT / "runs" / "b0_gemini31fl_dev" / "summary.json"
ROWS = ROOT / "runs" / "analysis" / "ingestion_rows.jsonl"

NAVY = "#17324D"
BLUE = "#2878A8"
ORANGE = "#D97732"
TEAL = "#3B8C83"
GRAY = "#687783"
PALE = "#F1F5F8"
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "figure.dpi": 160,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def save(fig: plt.Figure, stem: str) -> None:
    fig.savefig(FIGURES / f"{stem}.png", dpi=300)
    fig.savefig(FIGURES / f"{stem}.pdf")
    plt.close(fig)


def workflow() -> None:
    fig, ax = plt.subplots(figsize=(7.1, 2.35))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    boxes = [
        (0.015, 0.22, 0.22, 0.59, "STALE instance",
         "50 timestamped sessions\nOld + updated evidence\n3 evaluation probes", NAVY),
        (0.275, 0.22, 0.22, 0.59, "B0: long context",
         "Full history + one probe\nper response call\nGemini-3.1-flash-lite", BLUE),
        (0.535, 0.22, 0.205, 0.59, "Three responses",
         "SR: state resolution\nPR: premise resistance\nIPA: policy adaptation", TEAL),
        (0.78, 0.22, 0.205, 0.59, "Joint evaluator",
         "One call per instance\nReleased rubric\n3 binary verdicts", ORANGE),
    ]
    for x, y, w, h, title, body, color in boxes:
        patch = FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.02",
            linewidth=1.2, edgecolor=color, facecolor=PALE,
        )
        ax.add_patch(patch)
        ax.text(x + w / 2, y + h - 0.15, title, ha="center", va="center",
                color=color, fontsize=9.5, fontweight="bold")
        ax.text(x + w / 2, y + h / 2 - 0.035, body, ha="center", va="center",
                color=NAVY, fontsize=8.1, linespacing=1.45)
    for x1, x2 in ((0.238, 0.27), (0.498, 0.53), (0.743, 0.775)):
        ax.annotate("", xy=(x2, 0.515), xytext=(x1, 0.515),
                    arrowprops={"arrowstyle": "-|>", "color": GRAY, "lw": 1.5})
    ax.text(0.5, 0.055,
            "No retrieval or persistent memory stage; evaluator sees ground-truth labels",
            ha="center", va="center", fontsize=8, color=GRAY, style="italic")
    fig.tight_layout(pad=0.25)
    save(fig, "figure_1_workflow")


def accuracy() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    labels = ["Type I SR", "Type I PR", "Type I IPA",
              "Type II SR", "Type II PR", "Type II IPA", "Overall"]
    keys = [
        "T1.dim1", "T1.dim2", "T1.dim3",
        "T2.dim1", "T2.dim2", "T2.dim3", "overall",
    ]
    paper = np.array([41.0, 1.5, 42.0, 25.0, 1.5, 23.5, 22.4])
    means = np.array([summary["accuracy"][key] * 100 for key in keys])
    lows = np.array([summary["ci95"][key][0] * 100 for key in keys])
    highs = np.array([summary["ci95"][key][1] * 100 for key in keys])
    y = np.arange(len(labels))[::-1]
    fig, ax = plt.subplots(figsize=(3.5, 3.35))
    ax.axvline(0, color="#AAB4BC", linewidth=0.8, zorder=0)
    for i, yi in enumerate(y):
        ax.plot([paper[i]], [yi + 0.13], marker="D", color=NAVY,
                markersize=5, linestyle="none", zorder=3)
        ax.errorbar(
            means[i], yi - 0.13,
            xerr=np.array([[means[i] - lows[i]], [highs[i] - means[i]]]),
            fmt="o", color=ORANGE, ecolor=ORANGE, elinewidth=1.8,
            capsize=3.5, markersize=5.5, markeredgecolor="white",
            markeredgewidth=0.7, zorder=4,
        )
        if highs[i] == lows[i]:
            ax.plot(means[i], yi - 0.13, marker="|", color=ORANGE,
                    markersize=10, markeredgewidth=1.7, zorder=5)
    ax.set_yticks(y, labels)
    ax.set_xlim(-2, 82)
    ax.set_xticks(np.arange(0, 81, 10))
    ax.set_xlabel("Accuracy (%)")
    ax.xaxis.grid(True, color="#E4E9ED", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.scatter([], [], marker="D", color=NAVY, s=26,
               label="STALE paper (n=200/type)")
    ax.errorbar([], [], xerr=[[1], [1]], fmt="o", color=ORANGE,
                ecolor=ORANGE, capsize=3, label="This study (n=25/type; 95% bootstrap CI)")
    ax.legend(frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=1,
              fontsize=5.8, handletextpad=0.35, labelspacing=0.3,
              borderaxespad=0.2)
    ax.tick_params(axis="both", labelsize=7)
    ax.set_xlabel("Accuracy (%)", fontsize=8)
    fig.tight_layout(pad=0.45)
    save(fig, "figure_2_accuracy")


def context_lengths() -> None:
    if not SUMMARY.exists() or not ROWS.exists():
        raise FileNotFoundError("Expected run summary and ingestion rows are required")
    rows = [json.loads(line) for line in ROWS.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    if len(rows) != 400:
        raise ValueError(f"Expected 400 ingestion rows, found {len(rows)}")
    full = np.array([row["full_tokens"] for row in rows])
    relevant = np.array([row["relevant_tokens"] for row in rows])
    limit = 128_000
    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(3.5, 3.35), gridspec_kw={"height_ratios": [1.15, 1]},
    )
    bins = np.arange(136_000, 168_001, 2_000)
    top.hist(full, bins=bins, color=BLUE, edgecolor="white", linewidth=0.6)
    top.axvline(limit, color=ORANGE, linestyle="--", linewidth=1.5,
                label="128K limit")
    top.axvline(full.mean(), color=NAVY, linestyle="-.", linewidth=1.3,
                label=f"Mean = {full.mean()/1000:.1f}K")
    top.set_title("History length (400/400 exceed 128K)", loc="left",
                  color=NAVY, fontweight="bold", fontsize=8.5)
    top.set_xlabel("Serialized tokens", fontsize=7.5)
    top.set_ylabel("Instances", fontsize=7.5)
    top.ticklabel_format(axis="x", style="plain")
    top.tick_params(axis="x", labelrotation=20, labelsize=6.8)
    top.tick_params(axis="y", labelsize=7)
    top.legend(frameon=False, fontsize=6.5, loc="upper left")
    bottom.boxplot(
        [full, relevant], orientation="horizontal", patch_artist=True, showfliers=False,
        boxprops={"facecolor": "#D9E8F1", "edgecolor": BLUE},
        medianprops={"color": NAVY, "linewidth": 1.5},
        whiskerprops={"color": BLUE}, capprops={"color": BLUE},
    )
    bottom.set_xscale("log")
    bottom.set_yticks([1, 2], ["Full history", "Two gold sessions"])
    bottom.set_xlabel("Serialized tokens (log scale)", fontsize=7.5)
    bottom.set_title("Input scale comparison", loc="left",
                     color=NAVY, fontweight="bold", fontsize=8.5)
    bottom.tick_params(axis="both", labelsize=7)
    bottom.grid(axis="x", which="both", color="#E4E9ED", linewidth=0.7)
    bottom.set_axisbelow(True)
    bottom.text(0.98, 0.06, f"Gold-session mean: {relevant.mean()/1000:.1f}K tokens",
                transform=bottom.transAxes, ha="right", va="bottom",
                fontsize=6.5, color=TEAL)
    fig.tight_layout(h_pad=0.8, pad=0.4)
    save(fig, "figure_3_context")


def main() -> None:
    if not SUMMARY.exists():
        raise FileNotFoundError(f"Run summary not found: {SUMMARY}")
    workflow()
    accuracy()
    context_lengths()
    print("Generated 3 figures (PDF and PNG) in", FIGURES)


if __name__ == "__main__":
    main()
