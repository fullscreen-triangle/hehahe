"""Shared style for the manuscript panels.

Eight panels, each four charts in a row on a white background, at least one
of them three-dimensional. Minimal text: every panel carries axis labels and
tick values only, with the interpretation left to the caption. No tables, no
schematics, no chart whose content is a word.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent / "results"
OUT = HERE

# ── palette ─────────────────────────────────────────────────────────
CLOSED = "#1b6ca8"     # closed circulation
OPEN = "#c1442e"       # open circulation
ACCENT = "#e08a1e"     # a third condition
NEUTRAL = "#4a4a4a"
LIGHT = "#9db8cc"
GRID = "#d9d9d9"
SURF = "viridis"

plt.rcParams.update({
    "figure.facecolor": "white",
    "savefig.facecolor": "white",
    "axes.facecolor": "white",
    "font.size": 8.5,
    "axes.labelsize": 8.5,
    "axes.titlesize": 9,
    "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5,
    "legend.fontsize": 7.5,
    "axes.edgecolor": "#333333",
    "axes.linewidth": 0.8,
    "grid.color": GRID,
    "grid.linewidth": 0.5,
    "lines.linewidth": 1.6,
    "figure.dpi": 200,
    "savefig.dpi": 200,
})


def new_panel(n=4, width=16.0, height=3.9, d3=()):
    """A row of n axes; indices listed in `d3` are 3-D."""
    fig = plt.figure(figsize=(width, height))
    axes = []
    for i in range(n):
        if i in d3:
            ax = fig.add_subplot(1, n, i + 1, projection="3d")
            ax.set_facecolor("white")
            ax.xaxis.pane.set_facecolor("white")
            ax.yaxis.pane.set_facecolor("white")
            ax.zaxis.pane.set_facecolor("white")
            ax.xaxis.pane.set_edgecolor(GRID)
            ax.yaxis.pane.set_edgecolor(GRID)
            ax.zaxis.pane.set_edgecolor(GRID)
            ax.grid(True, color=GRID, linewidth=0.4)
            ax.tick_params(pad=0.5)
            ax.zaxis.labelpad = 6
            ax.xaxis.labelpad = 4
            ax.yaxis.labelpad = 4
        else:
            ax = fig.add_subplot(1, n, i + 1)
            ax.grid(True, axis="y", alpha=0.6)
            ax.set_axisbelow(True)
            for side in ("top", "right"):
                ax.spines[side].set_visible(False)
            ax.ticklabel_format(axis="both", style="sci",
                                scilimits=(-3, 4), useOffset=False)
            ax.xaxis.set_major_locator(plt.MaxNLocator(6))
            ax.yaxis.set_major_locator(plt.MaxNLocator(6))
        axes.append(ax)
    return fig, axes


def tag(ax, letter, d3=False):
    """Single-letter subplot tag; the only text beyond axis labels."""
    if d3:
        ax.text2D(-0.04, 1.04, letter, transform=ax.transAxes,
                  fontsize=11, fontweight="bold", va="top")
    else:
        ax.text(-0.04, 1.06, letter, transform=ax.transAxes,
                fontsize=11, fontweight="bold", va="top")


def save(fig, name):
    fig.tight_layout(w_pad=2.4)
    fig.subplots_adjust(bottom=0.16)
    path = OUT / f"{name}.png"
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  wrote {path.name}")
    return path


# ── result access ───────────────────────────────────────────────────

def load_rows():
    return json.loads((RESULTS / "observations.json").read_text())


def load(program):
    for f in RESULTS.glob(f"{program}*.json"):
        return json.loads(f.read_text())
    raise FileNotFoundError(program)


def value(rows, program, experiment, arm, observable, phase=None):
    for r in rows:
        if (r["program"].startswith(program) and r["experiment"] == experiment
                and r["arm"] == arm and r["observable"] == observable
                and (phase is None or r["phase"] == phase)):
            return r["value"]
    return None


def sim(circuit_name, program_file, arm="intact", experiment=None,
        seed=0, duration=30.0):
    """Re-run the backend to obtain a state trace for plotting."""
    import sys
    sys.path.insert(0, str(HERE.parent))
    from vitruvius import Backend, check, parse
    from vitruvius.runtime import Runtime

    src = (HERE.parent / "experiments" / program_file).read_text(encoding="utf-8")
    prog = parse(src)
    checked = check(prog)
    backend = Backend(seed=seed, duration=duration)
    rt = Runtime(prog, checked, backend)

    for x in prog.experiments:
        if experiment and x.name != experiment:
            continue
        res = rt.run_experiment(x)
        for a in res.all_arms():
            if a.name == arm:
                return backend, a.circuit, backend.simulate(a.circuit)
    raise LookupError(f"{program_file}:{experiment}:{arm}")
