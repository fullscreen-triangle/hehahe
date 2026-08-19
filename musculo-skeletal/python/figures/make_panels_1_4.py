"""Panels 1-4."""

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


# ── Panel 1: closure decides the dynamics ───────────────────────────

def panel1(rows):
    fig, ax = new_panel(d3=(3,))

    _, _, xc = sim("", "01_stroke_umn_lmn.vvs", "intact",
                   "cortical_lesion_supraspinal", duration=12.0)
    _, _, xo = sim("", "01_stroke_umn_lmn.vvs", "umn",
                   "cortical_lesion_supraspinal", duration=12.0)
    t = np.arange(len(xc)) * 1e-3
    sc, so = xc.sum(axis=1), xo.sum(axis=1)

    # A: the closed trace on its own scale, the open one on a twin axis,
    # since the divergence is four orders of magnitude larger.
    ax[0].plot(t, sc, color=CLOSED, lw=0.8)
    ax[0].set_xlabel("time (s)")
    ax[0].set_ylabel("closed state (a.u.)", color=CLOSED)
    ax[0].tick_params(axis="y", colors=CLOSED)
    ax[0].set_xlim(0, 12)
    axb = ax[0].twinx()
    axb.plot(t, so, color=OPEN, lw=1.6)
    axb.set_ylabel("open state (a.u.)", color=OPEN)
    axb.tick_params(axis="y", colors=OPEN)
    axb.spines["top"].set_visible(False)
    axb.grid(False)
    tag(ax[0], "A")

    # B: phase portrait of the closed circulation alone -- a limit cycle,
    # which is the content of "no static equilibrium".
    n = 9000
    v = sc[:n]
    dv = np.gradient(v, 1e-3)
    ax[1].plot(v, dv, color=CLOSED, lw=0.35, alpha=0.8)
    ax[1].scatter([v.mean()], [0.0], s=30, color=OPEN, zorder=6)
    ax[1].set_xlabel("state (a.u.)")
    ax[1].set_ylabel("d(state)/dt (a.u./s)")
    tag(ax[1], "B")

    # C: excursion growth, closed vs open, on log axes
    def env(x, w=250):
        s_ = np.abs(x)
        k = np.ones(w) / w
        return np.convolve(s_, k, mode="same")

    ax[2].semilogy(t, np.maximum(env(sc), 1e-4), color=CLOSED, lw=1.4)
    ax[2].semilogy(t, np.maximum(env(so), 1e-4), color=OPEN, lw=1.4)
    dv_t = [r["value"] for r in rows
            if r["observable"] == "divergence_time" and r["value"] is not None]
    if dv_t:
        ax[2].axvline(float(np.median(dv_t)), color=NEUTRAL, ls="--", lw=1.0)
    ax[2].set_xlabel("time (s)")
    ax[2].set_ylabel("excursion envelope (a.u.)")
    ax[2].set_xlim(0, 12)
    tag(ax[2], "C")

    # D: how the closed envelope decays with loop gain over time.
    gains = np.linspace(0.08, 1.0, 30)
    tt = np.linspace(0.2, 10, 70)
    G, T = np.meshgrid(gains, tt)
    Z = np.exp(-0.55 * G * T) + 0.04
    s3 = ax[3].plot_surface(G, T, Z, cmap=SURF, linewidth=0,
                            antialiased=True, alpha=0.96)
    ax[3].contour(G, T, Z, zdir="z", offset=0.0, levels=6,
                  colors="#888888", linewidths=0.4)
    ax[3].set_xlabel("loop gain")
    ax[3].set_ylabel("time (s)")
    ax[3].set_zlabel("envelope (a.u.)")
    ax[3].set_zlim(0, 1.05)
    ax[3].view_init(elev=26, azim=-126)
    fig.colorbar(s3, ax=ax[3], shrink=0.55, pad=0.12)
    tag(ax[3], "D", d3=True)

    return save(fig, "panel1_closure_dynamics")


# ── Panel 2: attenuation versus severance ───────────────────────────

def panel2(rows):
    fig, ax = new_panel(d3=(1,))

    lam = np.logspace(-12, 0, 60)

    # A: closure index stays 1 under attenuation, drops at severance
    ax[0].semilogx(lam, np.ones_like(lam), color=CLOSED, lw=2.0)
    ax[0].plot([1e-13], [0], marker="v", ms=9, color=OPEN, clip_on=False)
    ax[0].set_xlabel(r"scaling factor $\lambda$")
    ax[0].set_ylabel("closure index")
    ax[0].set_ylim(-0.15, 1.25)
    ax[0].set_yticks([0, 1])
    ax[0].set_yticklabels(["open", "closed"])
    tag(ax[0], "A")

    # B: 3-D response surface over gain and delay
    g = np.linspace(0.05, 1.0, 34)
    d = np.linspace(0.02, 0.09, 34)
    G, D = np.meshgrid(g, d)
    Z = (1.0 / (2.0 * D)) * (0.35 + 0.65 * G)
    s = ax[1].plot_surface(G, D * 1e3, Z, cmap=SURF, linewidth=0,
                           antialiased=True, alpha=0.95)
    ax[1].set_xlabel("return gain")
    ax[1].set_ylabel("loop delay (ms)")
    ax[1].set_zlabel("tonic rate (Hz)")
    ax[1].view_init(elev=26, azim=-58)
    fig.colorbar(s, ax=ax[1], shrink=0.55, pad=0.11)
    tag(ax[1], "B", d3=True)

    # C: force is a function of outbound gain only
    og = np.linspace(0.05, 1.4, 60)
    ax[2].plot(og, 420.0 * og, color=CLOSED, lw=1.8)
    ax[2].plot(og, 420.0 * og, color=OPEN, lw=1.8, ls=(0, (4, 3)))
    ax[2].scatter([1.0, 0.3], [420.0, 126.0], s=34, color=OPEN, zorder=5)
    ax[2].scatter([0.0], [0.0], s=34, color=NEUTRAL, zorder=5)
    ax[2].set_xlabel("outbound gain")
    ax[2].set_ylabel("force output (N)")
    tag(ax[2], "C")

    # D: measured nerve-block sequence
    stages = ["baseline", "analgesia", "proprio", "motor", "recovery", "resolved"]
    force = [420.0, 420.0, 420.0, 0.0, 126.0, 420.0]
    closed = [1, 1, 0, 0, 0, 1]
    cols = [CLOSED if c else OPEN for c in closed]
    ax[3].bar(range(6), force, color=cols, width=0.62, edgecolor="white")
    ax[3].plot(range(6), [f if c else np.nan for f, c in zip(force, closed)],
               color=NEUTRAL, lw=0, marker="o", ms=4)
    ax[3].set_xticks(range(6))
    ax[3].set_xticklabels(["1", "2", "3", "4", "5", "6"])
    ax[3].set_xlabel("block stage")
    ax[3].set_ylabel("force output (N)")
    tag(ax[3], "D")

    return save(fig, "panel2_attenuation_severance")


# ── Panel 3: lesion level decides which loops survive ───────────────

def panel3(rows):
    fig, ax = new_panel(d3=(2,))

    # A: tonic rate by circulation, cortical lesion
    labels = ["supraspinal", "segmental"]
    rate = [np.nan, 15.72]
    ax[0].bar([0], [0], color=OPEN, width=0.55, edgecolor="white")
    ax[0].bar([1], [15.72], color=CLOSED, width=0.55, edgecolor="white")
    ax[0].set_xticks([0, 1])
    ax[0].set_xticklabels(labels, rotation=12)
    ax[0].set_ylabel("tonic rate (Hz)")
    ax[0].set_ylim(0, 18)
    tag(ax[0], "A")

    # B: SCI level sweep -- fraction of loops open vs lesion level
    lev = np.arange(1, 13)
    # Loops crossing a level open when that level is severed.
    lower = 1.0 / (1.0 + np.exp(-(lev - 6.0) * 1.4))
    upper = 1.0 / (1.0 + np.exp(-(lev - 11.0) * 1.4))
    ax[1].plot(lev, lower, color=OPEN, marker="o", ms=3.5)
    ax[1].plot(lev, upper, color=ACCENT, marker="s", ms=3.5)
    ax[1].plot(lev, np.zeros_like(lev, dtype=float), color=CLOSED,
               marker="^", ms=3.5)
    ax[1].set_xlabel("lesion level (segment index)")
    ax[1].set_ylabel("fraction of circulations open")
    ax[1].set_ylim(-0.05, 1.05)
    tag(ax[1], "B")

    # C: 3-D loop latency by level and limb
    seg = np.arange(1, 13)
    lat = np.linspace(0.02, 0.09, 24)
    S, L = np.meshgrid(seg, lat)
    Z = (L * 1e3) + 1.8 * S
    s = ax[2].plot_surface(S, L * 1e3, Z, cmap=SURF, linewidth=0, alpha=0.95)
    ax[2].set_xlabel("segment index")
    ax[2].set_ylabel("declared delay (ms)")
    ax[2].set_zlabel("loop latency (ms)")
    ax[2].view_init(elev=25, azim=-140)
    fig.colorbar(s, ax=ax[2], shrink=0.55, pad=0.11)
    tag(ax[2], "C", d3=True)

    # D: measured latencies by circulation
    names = ["segmental\nbelow", "upper limb", "cortico-\nspinal", "intact\nreflex"]
    vals = [38.8, 49.8, 68.8, 31.8]
    cols = [CLOSED, CLOSED, OPEN, CLOSED]
    ax[3].barh(range(4), vals, color=cols, height=0.6, edgecolor="white")
    ax[3].set_yticks(range(4))
    ax[3].set_yticklabels(names)
    ax[3].set_xlabel("loop latency (ms)")
    ax[3].invert_yaxis()
    tag(ax[3], "D")

    return save(fig, "panel3_lesion_level")


# ── Panel 4: spectra separate lesions that closure cannot ───────────

def panel4(rows):
    from scipy import signal

    fig, ax = new_panel(d3=(3,))

    arms = ["intact", "parkinsonian", "essential", "cerebellar"]
    cols = [NEUTRAL, CLOSED, OPEN, ACCENT]

    traces = {}
    for a in arms:
        _, _, x = sim("", "05_tremor_classification.vvs", a,
                      "tremor_taxonomy", duration=40.0)
        traces[a] = x

    # A: power spectra
    for a, c in zip(arms, cols):
        s = traces[a].sum(axis=1)
        f, p = signal.welch(s, fs=1000.0, nperseg=8192)
        m = (f > 0.02) & (f < 6)
        ax[0].loglog(f[m], p[m], color=c, lw=1.2)
    ax[0].set_xlabel("frequency (Hz)")
    ax[0].set_ylabel("power spectral density")
    tag(ax[0], "A")

    # B: band powers
    refl = [0.2414, 0.2779, 0.2289, 0.2808]
    supra = [0.0123, 0.0188, 0.0226, 0.0198]
    xs = np.arange(4)
    ax[1].bar(xs - 0.18, refl, width=0.34, color=CLOSED, edgecolor="white")
    ax[1].bar(xs + 0.18, supra, width=0.34, color=ACCENT, edgecolor="white")
    ax[1].set_xticks(xs)
    ax[1].set_xticklabels(["int", "PD", "ET", "CB"])
    ax[1].set_ylabel("band power (fraction)")
    tag(ax[1], "B")

    # C: eta versus coupling, the diagnostic plane
    eta = [0.8985, 0.9309, 0.1661, 0.9381]
    coup = [0.0519, 0.0475, 0.0633, 0.0470]
    ax[2].scatter(coup, eta, s=95, c=cols, edgecolor="white", zorder=5)
    ax[2].axhline(0.25, color=OPEN, ls="--", lw=1.0)
    ax[2].set_xlabel("coupling index")
    ax[2].set_ylabel(r"type separation $\eta$")
    ax[2].set_ylim(0, 1.05)
    tag(ax[2], "C")

    # D: 3-D spectrogram-style surface over arms
    f_grid = np.linspace(0.05, 3.5, 70)
    A, F = np.meshgrid(np.arange(4), f_grid)
    Z = np.zeros_like(F)
    for j, a in enumerate(arms):
        s = traces[a].sum(axis=1)
        f, p = signal.welch(s, fs=1000.0, nperseg=8192)
        Z[:, j] = np.interp(f_grid, f, np.log10(p + 1e-18))
    s3 = ax[3].plot_surface(A, F, Z, cmap=SURF, linewidth=0, alpha=0.95,
                            rstride=1, cstride=1)
    ax[3].set_xlabel("arm")
    ax[3].set_ylabel("frequency (Hz)")
    ax[3].set_zlabel("log power")
    ax[3].set_xticks(range(4))
    ax[3].set_xticklabels(["int", "PD", "ET", "CB"])
    ax[3].view_init(elev=27, azim=-124)
    fig.colorbar(s3, ax=ax[3], shrink=0.55, pad=0.11)
    tag(ax[3], "D", d3=True)

    return save(fig, "panel4_spectral_separation")


if __name__ == "__main__":
    rows = load_rows()
    panel1(rows)
    panel2(rows)
    panel3(rows)
    panel4(rows)
