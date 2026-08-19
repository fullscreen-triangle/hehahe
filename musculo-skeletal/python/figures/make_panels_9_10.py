"""Panels 9-10: coherence, identity/character, opacity, and the floor."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from panel_style import (  # noqa: E402
    ACCENT, CLOSED, GRID, LIGHT, NEUTRAL, OPEN, SURF,
    RESULTS, new_panel, plt, save, tag,
)


def load_validation() -> dict:
    return json.loads((RESULTS / "coherence_validation.json").read_text())


# ── Panel 9: closure and coherence are independent ──────────────────

def panel9(V):
    g = {x["group"]: x for x in V["groups"]}
    fig, ax = new_panel(d3=(3,))

    # A: the two axes are independent -- margin against closure, all closed
    c1 = g["C1"]["detail"]
    margins = np.array(c1["margins_s"]) * 1e3
    coh = margins >= -1e-12
    rng = np.random.default_rng(0)
    jitter = rng.normal(0, 0.06, size=margins.size)
    ax[0].scatter(np.ones_like(margins) + jitter, margins,
                  s=13, c=np.where(coh, CLOSED, OPEN), alpha=0.7, linewidths=0)
    ax[0].axhline(0, color=NEUTRAL, lw=1.0, ls="--")
    ax[0].set_xlim(0.4, 1.6)
    ax[0].set_xticks([1])
    ax[0].set_xticklabels(["closed"])
    ax[0].set_xlabel("closure index")
    ax[0].set_ylabel("coherence margin (ms)")
    tag(ax[0], "A")

    # B: distribution of the disagreement
    ax[1].hist(-margins[~coh], bins=22, color=OPEN, alpha=0.85,
               edgecolor="white", linewidth=0.4)
    ax[1].axvline(0, color=NEUTRAL, lw=1.0)
    ax[1].set_xlabel("route disagreement (ms)")
    ax[1].set_ylabel("count of circuits")
    tag(ax[1], "B")

    # C: two-factor -- removal repairs, scaling does not
    c3 = g["C3"]["detail"]
    before = np.array([r["before"] for r in c3["sample"]]) * 1e3
    after_rm = np.array([r["after_removal"] for r in c3["sample"]]) * 1e3
    after_sc = np.array([r["after_scaling"] for r in c3["sample"]]) * 1e3
    order = np.argsort(before)
    xs = np.arange(before.size)
    ax[2].plot(xs, before[order], color=NEUTRAL, lw=1.4)
    ax[2].plot(xs, after_sc[order], color=OPEN, lw=1.4, ls=(0, (4, 2)))
    ax[2].plot(xs, after_rm[order], color=CLOSED, lw=1.8)
    ax[2].axhline(0, color=NEUTRAL, lw=0.9, ls=":")
    ax[2].set_xlabel("circuit (sorted by initial margin)")
    ax[2].set_ylabel("coherence margin (ms)")
    tag(ax[2], "C")

    # D: 3-D disagreement over route mismatch and parallel-path count
    mism = np.linspace(0, 25, 40)
    npar = np.arange(1, 6)
    M, N = np.meshgrid(mism, npar)
    Z = M * (N >= 2)
    s3 = ax[3].plot_surface(M, N, Z, cmap=SURF, linewidth=0, alpha=0.96)
    ax[3].contour(M, N, Z, zdir="z", offset=0, levels=5,
                  colors="#888888", linewidths=0.4)
    ax[3].set_xlabel("route delay mismatch (ms)")
    ax[3].set_ylabel("parallel routes")
    ax[3].set_zlabel("disagreement (ms)")
    ax[3].set_yticks([1, 2, 3, 4, 5])
    ax[3].view_init(elev=26, azim=-128)
    fig.colorbar(s3, ax=ax[3], shrink=0.55, pad=0.12)
    tag(ax[3], "D", d3=True)

    return save(fig, "panel9-coherence-closure")


# ── Panel 10: identity/character, opacity, and the floor ────────────

def panel10(V):
    g = {x["group"]: x for x in V["groups"]}
    fig, ax = new_panel(d3=(2,))

    # A: block cut vs cheapest singleton
    c5 = g["C5"]["detail"]
    names = list(c5)
    cost = [c5[n]["cost"] for n in names]
    sing = [c5[n]["cheapest_singleton"] for n in names]
    xs = np.arange(len(names))
    ax[0].bar(xs - 0.19, cost, width=0.36, color=CLOSED, edgecolor="white")
    ax[0].bar(xs + 0.19, sing, width=0.36, color=ACCENT, edgecolor="white")
    for i, n in enumerate(names):
        if c5[n]["is_block_cut"]:
            ax[0].plot([i - 0.19], [cost[i]], marker="v", ms=8,
                       color=OPEN, clip_on=False)
    ax[0].set_xticks(xs)
    ax[0].set_xticklabels([n.replace("_", "\n") for n in names])
    ax[0].set_ylabel("cut cost (conductance)")
    tag(ax[0], "A")

    # B: character invariance -- the deviation is exactly zero, so plotting
    # it on a log axis renders nothing. Show the paired costs instead: each
    # relabelled circuit against its original, all on the identity line.
    c4 = g["C4"]["detail"]
    pairs = c4.get("pairs", [])
    if pairs:
        base = np.array([p_["base"] for p_ in pairs])
        rel = np.array([p_["relabelled"] for p_ in pairs])
    else:
        base = rel = np.array([])
    if base.size:
        jit = np.random.default_rng(1).normal(0, 0.012, size=base.size)
        ax[1].scatter(base + jit, rel - jit, s=26, color=CLOSED,
                      alpha=0.55, linewidths=0)
        lo, hi = base.min() * 0.9, base.max() * 1.1
        ax[1].plot([lo, hi], [lo, hi], color=OPEN, lw=1.3, ls="--")
        ax[1].set_xlim(lo, hi)
        ax[1].set_ylim(lo, hi)
    ax[1].set_xlabel("character cost, original")
    ax[1].set_ylabel("character cost, relabelled")
    tag(ax[1], "B")

    # C: 3-D opacity -- interiors and latency spread
    c6 = g["C6"]["detail"]
    rows = [r for r in c6["sample"] if r["n"] >= 1]
    nreal = np.array([r["n"] for r in rows], dtype=float)
    lo = np.array([r["lat_lo"] for r in rows]) * 1e3
    spread = np.array([r["spread"] for r in rows]) * 1e3
    p = ax[2].scatter(nreal, lo, spread, c=spread, cmap=SURF, s=22, alpha=0.9)
    ax[2].set_xlabel("distinct interiors")
    ax[2].set_ylabel("shortest route (ms)")
    ax[2].set_zlabel("latency spread (ms)")
    ax[2].set_xticks([1, 2])
    ax[2].view_init(elev=24, azim=-132)
    fig.colorbar(p, ax=ax[2], shrink=0.55, pad=0.12)
    tag(ax[2], "C", d3=True)

    # D: floor tightness distribution
    c7 = g["C7"]["detail"]
    ratios = np.array(c7["ratios"])
    ax[3].hist(ratios, bins=26, color=CLOSED, alpha=0.85,
               edgecolor="white", linewidth=0.4)
    ax[3].axvline(1.0, color=OPEN, lw=1.4)
    ax[3].axvline(c7["min_tightness"], color=NEUTRAL, ls="--", lw=1.0)
    ax[3].set_xlabel(r"separation cost / min edge weight")
    ax[3].set_ylabel("count of circuits")
    ax[3].set_xlim(0.8, max(3.2, ratios.max() * 1.05))
    tag(ax[3], "D")

    return save(fig, "panel10-identity-opacity-floor")


if __name__ == "__main__":
    V = load_validation()
    panel9(V)
    panel10(V)
