"""Draw eval/results.png, the evaluation slide, from results_run1.json and results.json.

Run from backend/: .venv/bin/python ../eval/make_chart.py (needs eval/requirements.txt).
"""

import json
from pathlib import Path as FilePath

import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch, Rectangle
from matplotlib.path import Path

EVAL = FilePath(__file__).parent
SURFACE, INK, INK_2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
SERIES = {"bare": ("Bare prompt", "#2a78d6"), "persona_cot": ("Persona + chain of thought", "#eb6834")}
RUNS = [json.loads((EVAL / name).read_text()) for name in ("results_run1.json", "results.json")]


def bar(ax, x, width, height, color):
    """A bar with 4px rounded top corners and a square base on the baseline."""
    box = ax.get_window_extent()
    rx = 4 * (ax.get_xlim()[1] - ax.get_xlim()[0]) / box.width
    ry = min(4 * ax.get_ylim()[1] / box.height, height / 2)
    right, top = x + width, height
    verts = [(x, 0), (x, top - ry), (x, top), (x + rx, top), (right - rx, top), (right, top), (right, top - ry), (right, 0), (x, 0)]
    codes = [Path.MOVETO, Path.LINETO, Path.CURVE3, Path.CURVE3, Path.LINETO, Path.CURVE3, Path.CURVE3, Path.LINETO, Path.CLOSEPOLY]
    ax.add_patch(PathPatch(Path(verts, codes), fc=color, ec="none"))


def panel(ax, key, title, note, ymax, fmt):
    ax.set_ylim(0, ymax)
    ax.set_xlim(-0.6, 1.6)
    width, gap = 0.26, 0.02
    for run_i, run in enumerate(RUNS):
        for s_i, kind in enumerate(SERIES):
            x = run_i - width - gap / 2 + s_i * (width + gap)
            value = run[kind][key]
            bar(ax, x, width, value, SERIES[kind][1])
            ax.text(x + width / 2, value + ymax * 0.02, fmt(value), ha="center", va="bottom", fontsize=15, color=INK, fontweight="bold")
    ax.set_xticks([0, 1], ["Run 1", "Run 2"], fontsize=13, color=INK_2)
    ax.tick_params(axis="y", labelsize=11, colors=MUTED, length=0)
    ax.tick_params(axis="x", length=0, pad=8)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(AXIS)
    ax.set_facecolor(SURFACE)
    ax.set_title(title, loc="left", fontsize=16, color=INK, fontweight="bold", pad=28)
    ax.text(0, 1.03, note, transform=ax.transAxes, fontsize=12, color=INK_2)


def main() -> None:
    plt.rcParams["font.family"] = ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"]
    fig, (left, right) = plt.subplots(1, 2, figsize=(16, 9), dpi=100, facecolor=SURFACE)
    fig.subplots_adjust(left=0.06, right=0.97, top=0.71, bottom=0.16, wspace=0.22)
    panel(left, "tier_matches", "Accuracy: tiers that match the labels", "Out of 10 postings, first run of 3. Higher is better.", 10, str)
    panel(right, "mean_spread", "Consistency: mean score spread", "Max minus min of 3 runs, in points, averaged over 10 postings. Lower is better.",
          12, lambda v: f"{v:g}")
    fig.text(0.06, 0.93, "On 10 postings, the bare prompt scored as accurately as persona + CoT, and more consistently", fontsize=22, color=INK, fontweight="bold")
    fig.text(0.06, 0.885, "Same student, same postings, same Haiku settings as the app. Each run is a full separate pass.",
             fontsize=14, color=INK_2)
    handles = [Rectangle((0, 0), 1, 1, fc=c) for _, c in SERIES.values()]
    fig.legend(handles, [label for label, _ in SERIES.values()], loc="upper left", bbox_to_anchor=(0.055, 0.87), ncol=2, columnspacing=2,
               frameon=False, fontsize=13, labelcolor=INK_2, handlelength=1, handleheight=1)
    fig.text(0.06, 0.05, "Labels: written by Claude from the rubric before any model run, not by a human recruiter. "
             "In run 1 the bare prompt broke its format once in 30 replies (it answered 250) and that reply is left out.\n"
             "The scorer's value is its explanation: every score comes with a requirements table, gaps and a resume tip. "
             "The bare prompt returns only a number.", fontsize=11, color=MUTED, linespacing=1.6)
    fig.savefig(EVAL / "results.png", facecolor=SURFACE)


if __name__ == "__main__":
    main()
