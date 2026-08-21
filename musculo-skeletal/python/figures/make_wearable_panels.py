"""Panels for the wearable running analysis.

Four panels, each four charts in a row on a white background, at least one
three-dimensional. No chart whose content is a word: every axis carries a
measured or derived quantity.

    W1  the sprint as mechanics: speed, contact/flight, GRF, and the
        force-duty surface the impulse relation determines
    W2  spring-mass: stiffness against speed and compression, with the
        phase structure the watch labelled
    W3  the Hill muscle over one stance phase: activation, length, the
        force-velocity plane it traverses, and the tendon/fibre split
    W4  the constitutive curves and minimum jerk: what the model IS, and
        the swing trajectory it predicts
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from panel_style import (  # noqa: E402
    ACCENT, CLOSED, GRID, LIGHT, NEUTRAL, OPEN, SURF,
    new_panel, plt, save, tag,
)

from vitruvius import gait_dynamics as gd  # noqa: E402
from vitruvius import hill  # noqa: E402

PHASE_COLOUR = {
    "drive": CLOSED,
    "transition": ACCENT,
    "peak": OPEN,
    "deceleration": NEUTRAL,
    "start": LIGHT,
}


# ── W1: the sprint as mechanics ──────────────────────────────────────


def panel_sprint(sprint):
    fig, ax = new_panel(d3=(3,))
    st = sprint.strides
    t = [s.t for s in st]

    # A: speed and the contact/flight split
    ax[0].plot(t, [s.speed for s in st], color=CLOSED, lw=1.8)
    ax[0].set_xlabel("time (s)")
    ax[0].set_ylabel("speed (m/s)", color=CLOSED)
    ax[0].tick_params(axis="y", labelcolor=CLOSED)
    twin = ax[0].twinx()
    twin.plot(t, [s.contact_s * 1e3 for s in st], color=OPEN, lw=1.4)
    twin.plot(t, [s.flight_s * 1e3 for s in st], color=ACCENT, lw=1.4, ls=(0, (4, 2)))
    twin.set_ylabel("contact / flight (ms)", color=NEUTRAL, labelpad=1, fontsize=7.5)
    twin.tick_params(axis="y", labelsize=7)
    twin.spines["top"].set_visible(False)
    tag(ax[0], "A")

    # B: the impulse relation, with the measured strides on it
    duty = np.linspace(0.20, 0.36, 200)
    ax[1].plot(duty, 1.0 / duty, color=NEUTRAL, lw=1.4)
    ax[1].plot(duty, np.pi / 2 / duty, color=NEUTRAL, lw=1.4, ls=(0, (4, 2)))
    for s in st:
        ax[1].scatter(s.duty, s.grf_peak_bw, s=22,
                      color=PHASE_COLOUR.get(s.phase, NEUTRAL), alpha=0.85, linewidths=0)
        ax[1].scatter(s.duty, s.grf_mean_bw, s=10,
                      color=PHASE_COLOUR.get(s.phase, NEUTRAL), alpha=0.4, linewidths=0)
    ax[1].set_xlabel("duty factor")
    ax[1].set_ylabel("vertical GRF (body weights)")
    # Bound the view to the observed range: the analytic curves diverge as
    # duty -> 0 and would otherwise compress every measured stride into a
    # corner.
    ds = [x.duty for x in st]
    ax[1].set_xlim(min(ds) - 0.015, max(ds) + 0.015)
    tag(ax[1], "B")

    # C: contact time against speed, by phase
    for ph in ("drive", "transition", "peak", "deceleration"):
        g = [s for s in st if s.phase == ph]
        if not g:
            continue
        ax[2].scatter([s.speed for s in g], [s.contact_s * 1e3 for s in g],
                      s=30, color=PHASE_COLOUR[ph], alpha=0.9, linewidths=0)
    ax[2].set_xlabel("speed (m/s)")
    ax[2].set_ylabel("contact time (ms)")
    tag(ax[2], "C")

    # D: 3-D peak GRF surface over duty and body mass
    dd = np.linspace(0.18, 0.45, 40)
    mm = np.linspace(55, 110, 40)
    D, M = np.meshgrid(dd, mm)
    Z = (np.pi / 2 / D) * M * gd.G / 1000.0          # kN
    s3 = ax[3].plot_surface(D, M, Z, cmap=SURF, linewidth=0, alpha=0.55)
    obs_d = np.array([s.duty for s in st])
    obs_f = (np.pi / 2 / obs_d) * sprint.mass_kg * gd.G / 1000.0
    # The observed strides lie ON the surface by construction, so they are
    # drawn opaque and slightly raised: the point is that the subject occupies
    # one narrow band of a relation that spans the whole mass-duty plane.
    ax[3].scatter(obs_d, np.full_like(obs_d, sprint.mass_kg), obs_f * 1.02,
                  color=OPEN, s=26, depthshade=False, edgecolors="white",
                  linewidths=0.4, zorder=10)
    ax[3].set_xlabel("duty factor")
    ax[3].set_ylabel("body mass (kg)")
    ax[3].set_zlabel("peak GRF (kN)")
    ax[3].view_init(elev=24, azim=-131)
    fig.colorbar(s3, ax=ax[3], shrink=0.55, pad=0.12)
    tag(ax[3], "D", d3=True)

    return save(fig, "wearable1-sprint-mechanics")


# ── W2: spring-mass ──────────────────────────────────────────────────


def panel_spring(sprint):
    fig, ax = new_panel(d3=(2,))
    st = [s for s in sprint.strides if s.leg_stiffness]

    # A: leg vs vertical stiffness
    for s in st:
        c = PHASE_COLOUR.get(s.phase, NEUTRAL)
        ax[0].scatter(s.vertical_stiffness, s.leg_stiffness, s=30, color=c,
                      alpha=0.9, linewidths=0)
    lim = [0, max(s.vertical_stiffness for s in st) * 1.05]
    ax[0].plot(lim, lim, color=NEUTRAL, lw=0.9, ls=":")
    ax[0].set_xlabel("vertical stiffness (kN/m)")
    ax[0].set_ylabel("leg stiffness (kN/m)")
    tag(ax[0], "A")

    # B: leg compression against speed
    ax[1].scatter([s.speed for s in st], [s.leg_compression_m * 100 for s in st],
                  s=30, c=[PHASE_COLOUR.get(s.phase, NEUTRAL) for s in st],
                  alpha=0.9, linewidths=0)
    ax[1].set_xlabel("speed (m/s)")
    ax[1].set_ylabel("leg compression (cm)")
    tag(ax[1], "B")

    # C: 3-D trajectory through (speed, contact, stiffness)
    p = ax[2].scatter([s.speed for s in st], [s.contact_s * 1e3 for s in st],
                      [s.leg_stiffness for s in st],
                      c=[s.grf_peak_bw for s in st], cmap=SURF, s=26, alpha=0.95)
    ax[2].set_xlabel("speed (m/s)")
    ax[2].set_ylabel("contact (ms)")
    ax[2].set_zlabel("leg stiffness (kN/m)")
    ax[2].view_init(elev=22, azim=-129)
    fig.colorbar(p, ax=ax[2], shrink=0.55, pad=0.12)
    tag(ax[2], "C", d3=True)

    # D: the vertical excursion decomposed.
    #
    # The device reports one number; it is the sum of two mechanically
    # distinct parts. Stacking them shows that the flight arc is the smaller
    # of the two at sprint pace, and that the stance dip -- the part the leg
    # spring actually compresses through -- is what stiffness must be defined
    # against.
    order = np.argsort([s.speed for s in st])
    xs = np.arange(len(st))
    dip = np.array([st[i].stance_dip_m * 100 for i in order])
    arc = np.array([st[i].flight_rise_m * 100 for i in order])
    ax[3].bar(xs, dip, width=0.9, color=CLOSED, alpha=0.85, label="stance dip")
    ax[3].bar(xs, arc, width=0.9, bottom=dip, color=ACCENT, alpha=0.9,
              label="flight arc")
    tot = np.array([(st[i].vertical_osc_m or 0) * 100 for i in order])
    ax[3].plot(xs, tot, color=NEUTRAL, lw=1.2, ls=":")
    ax[3].set_xlabel("stride, ordered by speed")
    ax[3].set_ylabel("vertical excursion (cm)")
    ax[3].legend(frameon=False, fontsize=7, loc="upper left")
    tag(ax[3], "D")

    return save(fig, "wearable2-spring-mass")


# ── W3: the muscle over stance ───────────────────────────────────────


def panel_muscle(ms, required_n):
    fig, ax = new_panel(d3=(2,))
    s = ms["series"]
    t = np.array(s["t"]) * 1e3
    f = np.array(s["force_n"])

    # A: force against the requirement
    ax[0].plot(t, f / 1000.0, color=CLOSED, lw=1.8)
    ax[0].axhline(required_n / 1000.0, color=OPEN, lw=1.4, ls=(0, (4, 2)))
    ax[0].fill_between(t, 0, f / 1000.0, color=CLOSED, alpha=0.12)
    ax[0].set_xlabel("stance time (ms)")
    ax[0].set_ylabel("tendon force (kN)")
    tag(ax[0], "A")

    # B: activation and fibre length
    ax[1].plot(t, s["a"], color=ACCENT, lw=1.6)
    ax[1].set_xlabel("stance time (ms)")
    ax[1].set_ylabel("activation", color=ACCENT)
    ax[1].tick_params(axis="y", labelcolor=ACCENT)
    tw = ax[1].twinx()
    tw.plot(t, np.array(s["lm"]) * 1e3, color=CLOSED, lw=1.6)
    tw.set_ylabel("fibre length (mm)", color=CLOSED, labelpad=1, fontsize=7.5)
    tw.tick_params(axis="y", labelcolor=CLOSED, labelsize=7)
    tw.spines["top"].set_visible(False)
    tag(ax[1], "B")

    # C: 3-D path through the force-velocity-length space
    p = ax[2].scatter(np.array(s["vm"]) * 1e3, np.array(s["lm"]) * 1e3, f / 1000.0,
                      c=t, cmap=SURF, s=8, alpha=0.9)
    ax[2].set_xlabel("fibre velocity (mm/s)")
    ax[2].set_ylabel("fibre length (mm)")
    ax[2].set_zlabel("force (kN)")
    ax[2].view_init(elev=20, azim=-124)
    fig.colorbar(p, ax=ax[2], shrink=0.55, pad=0.12)
    tag(ax[2], "C", d3=True)

    # D: the force-velocity plane the fibre traverses.
    #
    # The parallel element is identically zero throughout this contraction --
    # the fibre never exceeds its optimal length (peak 0.99 lmopt) -- so
    # plotting it would be a flat line at zero occupying a quarter of the
    # panel. The operating path through the force-velocity plane is what
    # actually varies, and it shows the eccentric-to-concentric transition
    # that the stretch-shorten cycle produces.
    p = hill.MuscleParameters()
    vgrid = np.linspace(-p.vmmax * p.lmopt, 0.35 * p.vmmax * p.lmopt, 300)
    ax[3].plot(vgrid * 1e3, [hill.fv_ce(v, 1.0, 1.0, p) for v in vgrid],
               color=GRID, lw=1.2)
    sc = ax[3].scatter(np.array(s["vm"]) * 1e3, s["f_ce"], c=t, cmap=SURF,
                       s=9, alpha=0.9, linewidths=0)
    ax[3].axvline(0, color=NEUTRAL, lw=0.8, ls=":")
    ax[3].set_xlabel("fibre velocity (mm/s)")
    ax[3].set_ylabel("normalised CE force")
    fig.colorbar(sc, ax=ax[3], shrink=0.72, pad=0.02, label="stance time (ms)")
    tag(ax[3], "D")

    return save(fig, "wearable3-muscle-stance")


# ── W4: constitutive curves and minimum jerk ─────────────────────────


def panel_model(mj):
    p = hill.MuscleParameters()
    fig, ax = new_panel(d3=(1,))

    # A: the three force-length curves
    lm = np.linspace(0.4, 1.8, 300) * p.lmopt
    ax[0].plot(lm / p.lmopt, [hill.fl_ce(x, p) for x in lm], color=CLOSED, lw=1.8)
    ax[0].plot(lm / p.lmopt, [hill.fl_pe(x, p) for x in lm], color=OPEN, lw=1.6)
    ax[0].plot(lm / p.lmopt, [hill.fl_ce(x, p) + hill.fl_pe(x, p) for x in lm],
               color=NEUTRAL, lw=1.2, ls=(0, (4, 2)))
    ax[0].set_xlabel("normalised fibre length")
    ax[0].set_ylabel("normalised force")
    ax[0].set_ylim(0, 2.0)
    tag(ax[0], "A")

    # B: 3-D force-velocity surface over activation
    vm = np.linspace(-p.vmmax * p.lmopt, 0.5 * p.vmmax * p.lmopt, 60)
    acts = np.linspace(0.05, 1.0, 40)
    V, A = np.meshgrid(vm, acts)
    Z = np.vectorize(lambda v, a: hill.fv_ce(v, a, 1.0, p))(V, A)
    s3 = ax[1].plot_surface(V * 1e3, A, Z, cmap=SURF, linewidth=0, alpha=0.95)
    ax[1].set_xlabel("fibre velocity (mm/s)")
    ax[1].set_ylabel("activation")
    ax[1].set_zlabel("normalised force")
    ax[1].view_init(elev=24, azim=-133)
    fig.colorbar(s3, ax=ax[1], shrink=0.55, pad=0.12)
    tag(ax[1], "B", d3=True)

    # C: the tendon curve, toe and linear
    eps = np.linspace(0, 0.09, 400)
    lt = p.ltslack * (1 + eps)
    ax[2].plot(eps * 100, [hill.fl_se(x, p) for x in lt], color=CLOSED, lw=1.8)
    ax[2].axvline(p.epsttoe * 100, color=NEUTRAL, lw=0.9, ls=":")
    ax[2].axvline(p.epst0 * 100, color=OPEN, lw=0.9, ls=(0, (4, 2)))
    ax[2].set_xlabel("tendon strain (%)")
    ax[2].set_ylabel("normalised tendon force")
    tag(ax[2], "C")

    # D: minimum-jerk swing speed profile
    t = np.array(mj["t"]) * 1e3
    ax[3].plot(t, mj["velocity_ms"], color=CLOSED, lw=1.8)
    ax[3].axhline(mj["mean_velocity_ms"], color=NEUTRAL, lw=1.0, ls=":")
    ax[3].axhline(mj["peak_velocity_ms"], color=OPEN, lw=1.0, ls=(0, (4, 2)))
    tw = ax[3].twinx()
    tw.plot(t, np.array(mj["acceleration_ms2"]), color=ACCENT, lw=1.2, alpha=0.75)
    tw.set_ylabel("acceleration (m/s2)", color=ACCENT, labelpad=1, fontsize=7.5)
    tw.tick_params(axis="y", labelcolor=ACCENT)
    tw.spines["top"].set_visible(False)
    ax[3].set_xlabel("swing time (ms)")
    ax[3].set_ylabel("foot speed (m/s)", color=CLOSED)
    tag(ax[3], "D")

    return save(fig, "wearable4-model-curves")


def draw_all(record, sprint, analyses, ms, mj):
    print("drawing panels")
    panel_sprint(sprint)
    panel_spring(sprint)
    panel_muscle(ms, ms["required_tendon_force_n"])
    panel_model(mj)
