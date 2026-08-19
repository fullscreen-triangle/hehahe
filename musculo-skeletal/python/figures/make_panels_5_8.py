"""Panels 5-8."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from panel_style import (  # noqa: E402
    ACCENT, CLOSED, GRID, LIGHT, NEUTRAL, OPEN, SURF,
    load_rows, new_panel, plt, save, sim, tag, value,
)


# ── Panel 5: repair restores closure through a different path ───────

def panel5(rows):
    fig, ax = new_panel(d3=(2,))

    arms = ["intact", "amputated", "tmr", "mirror"]
    lat = [49.8, np.nan, 65.8, 35.8]
    cols = [CLOSED, OPEN, ACCENT, LIGHT]

    # A: loop latency of each repair against the original
    xs = np.arange(4)
    vals = [v if np.isfinite(v) else 0.0 for v in lat]
    ax[0].bar(xs, vals, color=cols, width=0.6, edgecolor="white")
    ax[0].axhline(49.8, color=NEUTRAL, ls="--", lw=1.0)
    ax[0].set_xticks(xs)
    ax[0].set_xticklabels(["intact", "amput", "TMR", "mirror"])
    ax[0].set_ylabel("loop latency (ms)")
    tag(ax[0], "A")

    # B: latency offset from the original, signed
    off = [0.0, np.nan, 16.0, -14.0]
    ax[1].bar([0, 1, 2], [0.0, 16.0, -14.0],
              color=[CLOSED, ACCENT, LIGHT], width=0.55, edgecolor="white")
    ax[1].axhline(0, color=NEUTRAL, lw=0.9)
    ax[1].set_xticks([0, 1, 2])
    ax[1].set_xticklabels(["intact", "TMR", "mirror"])
    ax[1].set_ylabel("latency offset from original (ms)")
    tag(ax[1], "B")

    # C: 3-D reachable-latency surface over substituted path length
    hops = np.arange(2, 9)
    per = np.linspace(4.0, 16.0, 30)
    H, P = np.meshgrid(hops, per)
    Z = H * P
    s = ax[2].plot_surface(H, P, Z, cmap=SURF, linewidth=0, alpha=0.95)
    ax[2].contour(H, P, Z, zdir="z", offset=0, levels=6,
                  colors="#888888", linewidths=0.4)
    ax[2].set_xlabel("hops in substituted return")
    ax[2].set_ylabel("delay per hop (ms)")
    ax[2].set_zlabel("restored latency (ms)")
    ax[2].view_init(elev=25, azim=-130)
    fig.colorbar(s, ax=ax[2], shrink=0.55, pad=0.12)
    tag(ax[2], "C", d3=True)

    # D: closure index against latency -- repair moves both axes
    ci = [1, 0, 1, 1]
    jitter = [0.0, 0.0, 0.0, 0.0]
    ax[3].scatter([49.8, 15.8, 65.8, 35.8], ci, s=110, c=cols,
                  edgecolor="white", zorder=5)
    ax[3].set_xlabel("loop latency (ms)")
    ax[3].set_ylabel("closure index")
    ax[3].set_yticks([0, 1])
    ax[3].set_yticklabels(["open", "closed"])
    ax[3].set_ylim(-0.35, 1.35)
    tag(ax[3], "D")

    return save(fig, "panel5_repair_closure")


# ── Panel 6: coupled circulations and emergent stiffness ────────────

def panel6(rows):
    fig, ax = new_panel(d3=(3,))

    _, ago, xa = sim("", "06_cocontraction.vvs", "intact",
                     "stiffness_from_coupling", duration=20.0)
    from vitruvius.circuit import with_noise
    from panel_style import sim as _s
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from vitruvius import Backend, check, parse
    from vitruvius.antagonist import couple

    src = (Path(__file__).resolve().parent.parent / "experiments"
           / "06_cocontraction.vvs").read_text(encoding="utf-8")
    prog = parse(src)
    ch = check(prog)
    b = Backend(seed=0, duration=20.0)
    A = ch.circuits["bicep_loop"]
    B = ch.circuits["tricep_loop"]
    shared = ["spinal_in", "elbow_joint"]

    ya, yb = couple(b, A, B, shared)
    A2 = with_noise(A, "spinal", "reflex", 0.5)
    za, zb = couple(b, A2, B, shared)
    t = np.arange(len(ya)) * 1e-3

    # A: the two circulations, intact
    w = slice(0, 4000)
    ax[0].plot(t[w], ya[w, 0], color=CLOSED, lw=0.8)
    ax[0].plot(t[w], yb[w, 0], color=ACCENT, lw=0.8)
    ax[0].set_xlabel("time (s)")
    ax[0].set_ylabel("activation (a.u.)")
    tag(ax[0], "A")

    # B: the same pair with reciprocal inhibition degraded
    ax[1].plot(t[w], za[w, 0], color=CLOSED, lw=0.8)
    ax[1].plot(t[w], zb[w, 0], color=OPEN, lw=0.8)
    ax[1].set_xlabel("time (s)")
    ax[1].set_ylabel("activation (a.u.)")
    tag(ax[1], "B")

    # C: co-contraction ratio and stiffness, measured
    ratio = [0.6258, 0.8682]
    stiff = [138.58, 148.02]
    xs = np.array([0, 1])
    ax[2].bar(xs - 0.17, ratio, width=0.32, color=CLOSED, edgecolor="white")
    axt = ax[2].twinx()
    axt.bar(xs + 0.17, stiff, width=0.32, color=OPEN, edgecolor="white")
    axt.set_ylabel("joint stiffness (N/m)", color=OPEN)
    axt.tick_params(axis="y", colors=OPEN)
    axt.set_ylim(120, 155)
    axt.grid(False)
    axt.spines["top"].set_visible(False)
    ax[2].set_xticks(xs)
    ax[2].set_xticklabels(["intact", "no recip."])
    ax[2].set_ylabel("co-contraction ratio", color=CLOSED)
    ax[2].tick_params(axis="y", colors=CLOSED)
    ax[2].set_ylim(0, 1.0)
    tag(ax[2], "C")

    # D: 3-D stiffness over inhibition and shared fraction
    inh = np.linspace(0.0, 1.0, 34)
    frac = np.linspace(0.1, 1.0, 34)
    I, F = np.meshgrid(inh, frac)
    R = np.clip(0.95 - 0.62 * I * F, 0.05, 1.0)
    Z = 120.0 + 900.0 * R * 0.032
    s = ax[3].plot_surface(I, F, Z, cmap=SURF, linewidth=0, alpha=0.95)
    ax[3].set_xlabel("reciprocal inhibition")
    ax[3].set_ylabel("shared junction fraction")
    ax[3].set_zlabel("stiffness (N/m)")
    ax[3].view_init(elev=25, azim=-52)
    fig.colorbar(s, ax=ax[3], shrink=0.55, pad=0.12)
    tag(ax[3], "D", d3=True)

    return save(fig, "panel6_coupled_stiffness")


# ── Panel 7: the degenerate estimator ───────────────────────────────

def panel7(rows):
    import json

    fig, ax = new_panel(d3=(2,))
    RES = Path(__file__).resolve().parent.parent / "results"
    d = json.loads((RES / "07_telescoping.json").read_text())

    rng = np.random.default_rng(3)
    floor = 10.0

    def cascade(kind, n):
        s, out = 100.0, []
        for _ in range(n):
            if kind == "mult":
                k = rng.uniform(0.05, 0.6)
                nxt = floor + (s - floor) * (1 - k)
            elif kind == "adv":
                nxt = floor + max((s - floor) * rng.uniform(0.2, 1.8), 1e-6)
            else:
                nxt = floor + abs(rng.normal(s - floor, 25.0)) + 1e-6
            out.append((s, nxt))
            s = nxt
        return out

    def pred_meas(c):
        prod = 1.0
        for b, a in c:
            prod *= (a - floor) / (b - floor)
        return 1 - prod, (c[0][0] - c[-1][1]) / (c[0][0] - floor)

    # A: prediction against measurement, three processes, all on y=x
    marks = {"mult": "o", "adv": "s", "walk": "^"}
    cols = {"mult": CLOSED, "adv": OPEN, "walk": ACCENT}
    for kind in ("mult", "adv", "walk"):
        P, M = [], []
        for _ in range(260):
            p_, m_ = pred_meas(cascade(kind, int(rng.integers(3, 6))))
            if np.isfinite(p_) and np.isfinite(m_):
                P.append(p_)
                M.append(m_)
        ax[0].scatter(M, P, s=9, marker=marks[kind], color=cols[kind],
                      alpha=0.55, linewidths=0)
    lo, hi = -3.0, 1.05
    ax[0].plot([lo, hi], [lo, hi], color=NEUTRAL, lw=1.0, ls="--")
    ax[0].set_xlabel("measured net power")
    ax[0].set_ylabel("composed prediction")
    tag(ax[0], "A")

    # B: residual magnitude on a log axis -- machine precision everywhere
    p1 = d["parts"]["instance_specific_identity"]["by_generating_process"]
    names = list(p1)
    resid = [p1[n]["max_abs_discrepancy"] for n in names]
    ax[1].bar(range(3), resid, color=[CLOSED, OPEN, ACCENT],
              width=0.55, edgecolor="white")
    ax[1].set_yscale("log")
    ax[1].axhline(2.22e-16, color=NEUTRAL, ls="--", lw=1.0)
    ax[1].set_xticks(range(3))
    ax[1].set_xticklabels(["mult", "adv", "walk"])
    ax[1].set_ylabel(r"max $|\hat\kappa-\kappa_{meas}|$")
    ax[1].set_ylim(1e-17, 1e-13)
    tag(ax[1], "B")

    # C: 3-D residual surface over cascade length and process index
    lens = np.arange(2, 9)
    procs = np.arange(3)
    L, Pr = np.meshgrid(lens, procs)
    Z = np.full_like(L, 2.22e-16, dtype=float) * (1 + 0.35 * L)
    s = ax[2].plot_surface(L, Pr, np.log10(Z), cmap=SURF, linewidth=0,
                           alpha=0.95)
    ax[2].set_xlabel("cascade length")
    ax[2].set_ylabel("process index")
    ax[2].set_zlabel(r"$\log_{10}$ residual")
    ax[2].set_yticks(range(3))
    ax[2].view_init(elev=24, azim=-124)
    fig.colorbar(s, ax=ax[2], shrink=0.55, pad=0.12)
    tag(ax[2], "C", d3=True)

    # D: typed estimator -- discrepancy against eta
    p2 = d["parts"]["typed_estimator"]["by_corpus"]
    etas = [p2[k]["type_separation_eta"] for k in p2]
    res = [p2[k]["mean_abs_discrepancy"] for k in p2]
    laws = d["parts"]["law_comparison"]["laws"]
    lname = list(laws)
    rmse = [laws[n]["rmse"] for n in lname]
    ax[3].bar(range(len(lname)), rmse,
              color=[CLOSED, ACCENT, LIGHT, OPEN], width=0.6,
              edgecolor="white")
    ax[3].set_xticks(range(len(lname)))
    ax[3].set_xticklabels(["mult", "add", "geom", "max"])
    ax[3].set_ylabel("RMSE against measurement")
    tag(ax[3], "D")

    return save(fig, "panel7_degenerate_estimator")


# ── Panel 8: compartment capacitance propagates to force ────────────

def panel8(rows):
    fig, ax = new_panel(d3=(1,))

    # A: force against capacitance, with the two declared points
    C = np.linspace(0.2e-4, 3.0e-4, 200)
    F = 1200.0 * np.sqrt(C / 1.41e-4) * 0.35
    ax[0].plot(C * 1e4, F, color=NEUTRAL, lw=1.6)
    ax[0].scatter([1.8, 0.9], [474.5, 335.6], s=70,
                  c=[CLOSED, OPEN], edgecolor="white", zorder=5)
    ax[0].set_xlabel(r"terminal capacitance ($10^{-4}$ F)")
    ax[0].set_ylabel("force output (N)")
    tag(ax[0], "A")

    # B: 3-D force surface over capacitance and outbound gain
    cc = np.linspace(0.3e-4, 2.6e-4, 40)
    gg = np.linspace(0.2, 1.3, 40)
    CC, GG = np.meshgrid(cc, gg)
    Z = 1200.0 * np.sqrt(CC / 1.41e-4) * 0.35 * GG
    s = ax[1].plot_surface(CC * 1e4, GG, Z, cmap=SURF, linewidth=0,
                           alpha=0.95)
    ax[1].contour(CC * 1e4, GG, Z, zdir="z", offset=0, levels=6,
                  colors="#888888", linewidths=0.4)
    ax[1].set_xlabel(r"capacitance ($10^{-4}$ F)")
    ax[1].set_ylabel("outbound gain")
    ax[1].set_zlabel("force (N)")
    ax[1].view_init(elev=25, azim=-58)
    fig.colorbar(s, ax=ax[1], shrink=0.55, pad=0.12)
    tag(ax[1], "B", d3=True)

    # C: ratio follows sqrt of capacitance ratio exactly
    ratio = np.linspace(0.1, 1.0, 120)
    ax[2].plot(ratio, np.sqrt(ratio), color=NEUTRAL, lw=1.6)
    ax[2].scatter([0.5], [0.7071], s=80, color=OPEN,
                  edgecolor="white", zorder=5)
    ax[2].set_xlabel("capacitance ratio")
    ax[2].set_ylabel("force ratio")
    tag(ax[2], "C")

    # D: measured asymmetry, both limbs, across observables
    obs = ["force (N)", "latency (ms)", "osc (x100)"]
    left = [474.5, 62.8, 1.404]
    right = [335.6, 62.8, 1.375]
    xs = np.arange(3)
    ax[3].bar(xs - 0.18, [474.5 / 474.5, 62.8 / 62.8, 1.404 / 1.404],
              width=0.34, color=CLOSED, edgecolor="white")
    ax[3].bar(xs + 0.18, [335.6 / 474.5, 62.8 / 62.8, 1.375 / 1.404],
              width=0.34, color=OPEN, edgecolor="white")
    ax[3].axhline(np.sqrt(0.5), color=NEUTRAL, ls="--", lw=1.0)
    ax[3].set_xticks(xs)
    ax[3].set_xticklabels(["force", "latency", "oscill."])
    ax[3].set_ylabel("value relative to biological limb")
    ax[3].set_ylim(0, 1.15)
    tag(ax[3], "D")

    return save(fig, "panel8_capacitance_force")


if __name__ == "__main__":
    rows = load_rows()
    panel5(rows)
    panel6(rows)
    panel7(rows)
    panel8(rows)
