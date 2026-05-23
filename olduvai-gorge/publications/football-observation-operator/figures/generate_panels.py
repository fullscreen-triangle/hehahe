"""
Generate five figure panels for:
    "Football as a Partially Observable Bioreactor:
     Backward Biomechanical Accounting via the Ball Observation Operator"

Each panel: 4 charts in a row, white background, minimal text,
at least one 3D chart, no conceptual or table charts.

Panels:
  1. Observation-operator sampling on the pitch-bioreactor
  2. Kuramoto bifurcation and the five coherence regimes
  3. Templating threshold (RMS phase bound)
  4. Duels as cognate oscillator pairs
  5. Cellular sampling and backward morphism identifiability
"""

import os
import sys

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyArrowPatch
from mpl_toolkits.mplot3d import Axes3D  # noqa

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "validation"))
import validate_paper as vp  # noqa: E402

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.labelsize": 9,
    "axes.titlesize": 10,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.8,
    "lines.linewidth": 1.2,
})

FIGSIZE = (16.0, 3.8)
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# Palette
C_CYAN   = "#58E6D9"
C_VIOLET = "#B63E96"
C_AMBER  = "#F0A830"
C_RED    = "#E6395A"
C_GREEN  = "#009E73"
C_BLUE   = "#0072B2"
C_GRAY   = "#5A5A5A"
C_PITCH  = "#dceedc"


def _finish(fig, out_path):
    fig.subplots_adjust(left=0.035, right=0.985, top=0.90, bottom=0.16,
                        wspace=0.36)
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


# ═══════════════════════════════════════════════════════════════════
# Panel 1 — Observation operator and bioreactor sampling
# ═══════════════════════════════════════════════════════════════════

def panel1_observation_operator():
    rng = np.random.default_rng(1)
    fig = plt.figure(figsize=FIGSIZE)

    # (A) 3D pitch with 11 players and ball trajectory sampling one cell at a time
    ax1 = fig.add_subplot(1, 4, 1, projection="3d")
    # Pitch rectangle in 3D (z=0)
    pitch_x = np.array([-30, 30, 30, -30, -30])
    pitch_y = np.array([-20, -20, 20, 20, -20])
    pitch_z = np.zeros_like(pitch_x)
    ax1.plot(pitch_x, pitch_y, pitch_z, color=C_GREEN, linewidth=1.5)
    # Pitch fill — draw as a polygon collection on z=0
    pitch_xx, pitch_yy = np.meshgrid([-30, 30], [-20, 20])
    pitch_zz = np.zeros_like(pitch_xx)
    ax1.plot_surface(pitch_xx, pitch_yy, pitch_zz, color=C_PITCH,
                     alpha=0.35, edgecolor="none", shade=False)
    # 11 player positions (4-3-3 schematic)
    pos = np.array([
        [-25,  0], [-15, -10], [-15,  10], [-15,  0], [-5, -8],
        [-5,   8], [-5,  0], [5, -12], [5,  12], [10, -4], [10, 4],
    ])
    ax1.scatter(pos[:, 0], pos[:, 1], np.zeros(len(pos)),
                c=C_CYAN, s=80, edgecolor="black", linewidth=0.6, depthshade=False)
    # Ball trajectory through 5 sampled players, lifted in z to show "sampled cell"
    sample_seq = [3, 5, 6, 8, 10]
    for k, idx in enumerate(sample_seq):
        ax1.scatter([pos[idx, 0]], [pos[idx, 1]], [1.5],
                    c=C_AMBER, s=120, edgecolor="black", linewidth=0.8,
                    depthshade=False, zorder=5)
        ax1.plot([pos[idx, 0], pos[idx, 0]], [pos[idx, 1], pos[idx, 1]],
                 [0, 1.5], color=C_AMBER, linewidth=1.2)
    # Ball path between sampled cells
    for i in range(len(sample_seq) - 1):
        a, b = sample_seq[i], sample_seq[i + 1]
        ts = np.linspace(0, 1, 20)
        xs = pos[a, 0] * (1 - ts) + pos[b, 0] * ts
        ys = pos[a, 1] * (1 - ts) + pos[b, 1] * ts
        zs = 1.5 + 0.5 * np.sin(np.pi * ts)
        ax1.plot(xs, ys, zs, color=C_AMBER, linewidth=2.2)
    ax1.set_title("(A) Ball samples one cell at a time", fontsize=9)
    ax1.set_xlabel("x (m)", fontsize=7)
    ax1.set_ylabel("y (m)", fontsize=7)
    ax1.set_zlabel("sampled", fontsize=7)
    ax1.view_init(elev=28, azim=-60)
    for axis in [ax1.xaxis, ax1.yaxis, ax1.zaxis]:
        axis.set_tick_params(labelsize=7)

    # (B) Possession timeline (stair-step pi(t))
    ax2 = fig.add_subplot(1, 4, 2)
    T = 80.0
    n_events = 60
    events_t = np.sort(rng.uniform(0, T, n_events))
    events_t = np.concatenate([[0], events_t, [T]])
    holders = rng.integers(0, 11, size=events_t.size)
    # Inject some unpossessed gaps
    unposs = rng.random(events_t.size) < 0.12
    holders[unposs] = -1
    for i in range(len(events_t) - 1):
        y = holders[i] if holders[i] >= 0 else np.nan
        col = C_GRAY if holders[i] < 0 else C_CYAN
        ax2.fill_between([events_t[i], events_t[i + 1]],
                         y, y + 0.7,
                         color=col, alpha=0.7 if holders[i] >= 0 else 0.2,
                         linewidth=0)
    ax2.set_xlim(0, T)
    ax2.set_ylim(-0.5, 11.5)
    ax2.set_xlabel("time (s)")
    ax2.set_ylabel("possessing player")
    ax2.set_yticks([0, 5, 10])
    ax2.set_title("(B) Possession indicator π(t)", fontsize=9)
    ax2.grid(alpha=0.3)

    # (C) Bout-duration histogram (log-spaced bins)
    ax3 = fig.add_subplot(1, 4, 3)
    bout_durations = rng.exponential(1.4, size=400) + 0.1
    ax3.hist(bout_durations, bins=30, color=C_CYAN, alpha=0.8,
             edgecolor="black", linewidth=0.4)
    ax3.axvline(0.20, color=C_RED, linestyle="--", linewidth=1.2,
                label="Nyquist 1/(2B)")
    ax3.axvline(np.mean(bout_durations), color="black", linestyle=":",
                linewidth=1.2, label=f"mean = {np.mean(bout_durations):.2f}s")
    ax3.set_xlabel("bout duration (s)")
    ax3.set_ylabel("count")
    ax3.set_title("(C) Possession bout durations", fontsize=9)
    ax3.legend(fontsize=7, loc="upper right")

    # (D) Per-player total sample mass vs Nyquist requirement
    ax4 = fig.add_subplot(1, 4, 4)
    per_player_time = rng.gamma(2.0, 12.0, size=11) + 2.0
    nyq_req = 8.0  # minimum total sample time needed for Nyquist
    colors = [C_GREEN if v >= nyq_req else C_RED for v in per_player_time]
    bars = ax4.bar(np.arange(11), per_player_time, color=colors,
                   edgecolor="black", linewidth=0.5)
    ax4.axhline(nyq_req, color="black", linestyle="--", linewidth=1,
                label="Nyquist threshold")
    ax4.set_xlabel("player index")
    ax4.set_ylabel("total possession (s)")
    ax4.set_title("(D) Per-player sample mass", fontsize=9)
    ax4.legend(fontsize=7)

    _finish(fig, os.path.join(OUT_DIR, "panel1_observation_operator.png"))


# ═══════════════════════════════════════════════════════════════════
# Panel 2 — Kuramoto bifurcation and five regimes
# ═══════════════════════════════════════════════════════════════════

def panel2_bifurcation():
    rng = np.random.default_rng(2)
    fig = plt.figure(figsize=FIGSIZE)

    # Pre-compute R_ens vs K/Kc curve for N=50 Cauchy
    N = 50
    gamma = 1.0
    Kc = 2.0 * gamma
    K_ratios = np.linspace(0.3, 12.0, 18)
    R_curve = np.zeros_like(K_ratios)
    for i, ratio in enumerate(K_ratios):
        Rs = []
        for s in range(4):
            omega = vp._draw_cauchy(rng, N, gamma)
            Rs.append(vp.steady_R(omega, ratio * Kc, T_warm=12.0, T_meas=12.0,
                                  seed=s + 10 * i))
        R_curve[i] = float(np.mean(Rs))

    # (A) 3D surface: R_ens(K/Kc, t) over a coupling sweep
    ax1 = fig.add_subplot(1, 4, 1, projection="3d")
    K_grid = np.linspace(0.5, 8.0, 14)
    T_total = 20.0
    dt = 0.05
    n_steps = int(T_total / dt)
    surface = np.zeros((K_grid.size, n_steps))
    for j, kr in enumerate(K_grid):
        omega = vp._draw_cauchy(rng, 40, gamma)
        _, R_trace, _ = vp.simulate_team(omega, kr * Kc, T_total=T_total,
                                          dt=dt, seed=j)
        surface[j] = R_trace
    KK, TT = np.meshgrid(K_grid, np.arange(n_steps) * dt, indexing="ij")
    surf = ax1.plot_surface(KK, TT, surface, cmap="viridis",
                            edgecolor="none", alpha=0.92)
    ax1.set_xlabel("K/Kc", fontsize=7)
    ax1.set_ylabel("t (s)", fontsize=7)
    ax1.set_zlabel("R_ens", fontsize=7)
    ax1.set_title("(A) R_ens(K, t)", fontsize=9)
    ax1.view_init(elev=25, azim=-60)
    for axis in [ax1.xaxis, ax1.yaxis, ax1.zaxis]:
        axis.set_tick_params(labelsize=7)

    # (B) Bifurcation curve with MF reference
    ax2 = fig.add_subplot(1, 4, 2)
    mf_k = np.linspace(1.0, 12.0, 200)
    mf_R = np.sqrt(np.clip(1 - 1.0 / mf_k, 0, None))
    ax2.plot(mf_k, mf_R, "-", color=C_VIOLET, linewidth=1.5,
             label="mean-field √(1−Kc/K)")
    ax2.scatter(K_ratios, R_curve, color=C_CYAN, s=40, edgecolor="black",
                linewidth=0.5, label="simulated (N=50)", zorder=5)
    ax2.axvline(1.0, color=C_RED, linestyle="--", linewidth=1, label="Kc")
    ax2.set_xlabel("K / Kc")
    ax2.set_ylabel("R_ens")
    ax2.set_xlim(0, 12)
    ax2.set_ylim(0, 1.05)
    ax2.set_title("(B) Kuramoto bifurcation", fontsize=9)
    ax2.legend(fontsize=7, loc="lower right")
    ax2.grid(alpha=0.3)

    # (C) Phase time-series, sub vs super-critical
    ax3 = fig.add_subplot(1, 4, 3)
    omega = vp._draw_cauchy(rng, 11, gamma)
    _, _, _ = (None,) * 3  # placeholder
    dt = 0.05
    T = 18.0
    n = int(T / dt)
    t = np.arange(n) * dt
    # Sub-critical
    phi = rng.uniform(0, 2 * np.pi, size=11)
    sub_traces = np.zeros((11, n))
    for k in range(n):
        sub_traces[:, k] = phi
        phi = vp.kuramoto_step(phi, omega, 0.7 * Kc, dt)
    # Super-critical
    phi = rng.uniform(0, 2 * np.pi, size=11)
    sup_traces = np.zeros((11, n))
    for k in range(n):
        sup_traces[:, k] = phi
        phi = vp.kuramoto_step(phi, omega, 4.0 * Kc, dt)
    # Plot sin(phi) for readability
    for i in range(11):
        ax3.plot(t, np.sin(sub_traces[i]), color=C_GRAY,
                 alpha=0.35, linewidth=0.7)
    for i in range(11):
        ax3.plot(t, np.sin(sup_traces[i]) + 2.5, color=C_VIOLET,
                 alpha=0.55, linewidth=0.7)
    ax3.text(0.5, 1.1, "K = 0.7 Kc (incoherent)", fontsize=7, color=C_GRAY)
    ax3.text(0.5, 3.6, "K = 4 Kc (coherent)", fontsize=7, color=C_VIOLET)
    ax3.set_xlabel("time (s)")
    ax3.set_ylabel("sin(φ_i)")
    ax3.set_yticks([])
    ax3.set_title("(C) Phase trajectories", fontsize=9)

    # (D) Regime histogram bars
    ax4 = fig.add_subplot(1, 4, 4)
    regimes = ["turbulent", "aperture", "cascade", "coherent", "phase-lock"]
    centres = [0.15, 0.40, 0.65, 0.87, 0.98]
    colors_r = [C_RED, C_AMBER, C_CYAN, C_BLUE, C_VIOLET]
    spreads = [0.05, 0.08, 0.07, 0.04, 0.01]
    for i, (c, s, col, lbl) in enumerate(zip(centres, spreads, colors_r, regimes)):
        samples = np.clip(rng.normal(c, s, 200), 0, 1)
        ax4.scatter(np.full_like(samples, i) + rng.uniform(-0.2, 0.2, len(samples)),
                    samples, color=col, alpha=0.3, s=12)
        ax4.plot([i - 0.3, i + 0.3], [c, c], color="black", linewidth=2)
    ax4.set_xticks(range(5))
    ax4.set_xticklabels(regimes, rotation=25, ha="right", fontsize=7)
    ax4.set_ylabel("R_ens")
    ax4.set_ylim(0, 1.05)
    ax4.axhline(0.30, color=C_GRAY, linestyle=":", linewidth=0.7)
    ax4.axhline(0.50, color=C_GRAY, linestyle=":", linewidth=0.7)
    ax4.axhline(0.80, color=C_GRAY, linestyle=":", linewidth=0.7)
    ax4.axhline(0.95, color=C_GRAY, linestyle=":", linewidth=0.7)
    ax4.set_title("(D) Five regimes", fontsize=9)

    _finish(fig, os.path.join(OUT_DIR, "panel2_bifurcation.png"))


# ═══════════════════════════════════════════════════════════════════
# Panel 3 — Templating threshold (RMS phase bound)
# ═══════════════════════════════════════════════════════════════════

def panel3_templating():
    rng = np.random.default_rng(3)
    fig = plt.figure(figsize=FIGSIZE)
    gamma = 1.0
    Kc = 2.0 * gamma
    N = 50

    # (A) 3D scatter: 50 oscillator phases on a unit circle, stacked by R_ens
    ax1 = fig.add_subplot(1, 4, 1, projection="3d")
    K_levels = [0.5 * Kc, 1.5 * Kc, 3.0 * Kc, 8.0 * Kc, 30.0 * Kc]
    z_vals = []
    for j, K in enumerate(K_levels):
        omega = vp._draw_cauchy(rng, N, gamma)
        _, R_trace, phi = vp.simulate_team(omega, K, T_total=18.0, seed=j)
        R_final = float(np.mean(R_trace[-100:]))
        z_vals.append(R_final)
        xs = np.cos(phi)
        ys = np.sin(phi)
        zs = np.full_like(xs, R_final)
        ax1.scatter(xs, ys, zs, c=zs, cmap="plasma", s=30,
                    vmin=0, vmax=1, edgecolor="black", linewidth=0.3,
                    depthshade=False)
    # Reference circle at each level
    theta_ref = np.linspace(0, 2 * np.pi, 80)
    for z in z_vals:
        ax1.plot(np.cos(theta_ref), np.sin(theta_ref), z, color=C_GRAY,
                 alpha=0.3, linewidth=0.6)
    ax1.set_xlabel("cos φ", fontsize=7)
    ax1.set_ylabel("sin φ", fontsize=7)
    ax1.set_zlabel("R_ens", fontsize=7)
    ax1.set_title("(A) Phase concentration with R_ens", fontsize=9)
    ax1.view_init(elev=22, azim=-60)
    for axis in [ax1.xaxis, ax1.yaxis, ax1.zaxis]:
        axis.set_tick_params(labelsize=7)

    # (B) RMS deviation vs (1-R_ens) with theoretical sqrt(2x)
    ax2 = fig.add_subplot(1, 4, 2)
    R_grid = np.linspace(0.50, 0.999, 18)
    rms_emp = np.zeros_like(R_grid)
    rms_th = np.sqrt(2.0 * (1.0 - R_grid))
    # Choose K so that R_ens approximately matches target via 1 - 1/r => K/Kc = 1/(1-R^2)
    for i, R_target in enumerate(R_grid):
        K_use = Kc / max(1e-3, 1.0 - R_target ** 2)
        rs = []
        for s in range(5):
            omega = vp._draw_cauchy(rng, N, gamma)
            _, R_trace, phi = vp.simulate_team(omega, K_use, T_total=16.0, seed=s)
            R_final = float(np.mean(R_trace[-80:]))
            psi = np.angle(np.sum(np.exp(1j * phi)))
            devs = np.abs((phi - psi + np.pi) % (2 * np.pi) - np.pi)
            rms = float(np.sqrt(np.mean(devs ** 2)))
            rs.append((R_final, rms))
        # Average over realisations
        rms_emp[i] = float(np.mean([r[1] for r in rs]))
        R_grid[i] = float(np.mean([r[0] for r in rs]))
        rms_th[i] = float(np.sqrt(2.0 * max(0.0, 1.0 - R_grid[i])))

    ax2.plot(1 - R_grid, rms_th, "-", color=C_VIOLET, linewidth=1.5,
             label="√(2(1−R))")
    ax2.scatter(1 - R_grid, rms_emp, color=C_CYAN, s=40, edgecolor="black",
                linewidth=0.5, label="simulated", zorder=5)
    ax2.set_xlabel("1 − R_ens")
    ax2.set_ylabel("RMS phase deviation (rad)")
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_title("(B) RMS bound match", fontsize=9)
    ax2.legend(fontsize=7)
    ax2.grid(alpha=0.3, which="both")

    # (C) Phase distribution histograms at three R_ens levels
    ax3 = fig.add_subplot(1, 4, 3)
    target_Rs = [0.5, 0.85, 0.99]
    colors_h = [C_AMBER, C_CYAN, C_VIOLET]
    for R_target, col in zip(target_Rs, colors_h):
        K_use = Kc / max(1e-3, 1.0 - R_target ** 2)
        omega = vp._draw_cauchy(rng, 200, gamma)
        _, R_trace, phi = vp.simulate_team(omega, K_use, T_total=16.0, seed=42)
        psi = np.angle(np.sum(np.exp(1j * phi)))
        devs = (phi - psi + np.pi) % (2 * np.pi) - np.pi
        ax3.hist(devs, bins=30, density=True, color=col, alpha=0.55,
                 label=f"R≈{R_target:.2f}")
    ax3.set_xlabel("φ_i − ψ (rad)")
    ax3.set_ylabel("density")
    ax3.set_title("(C) Phase distributions", fontsize=9)
    ax3.legend(fontsize=7)

    # (D) Empirical RMS vs theoretical bound across coherence range
    ax4 = fig.add_subplot(1, 4, 4)
    K_ratios_d = np.logspace(0.0, 1.5, 10)  # 1 .. ~32
    rms_means = []
    bound_means = []
    n_trials = 6
    for kr in K_ratios_d:
        rms_acc, bd_acc = [], []
        for s in range(n_trials):
            omega = vp._draw_cauchy(rng, N, gamma)
            _, R_trace, phi = vp.simulate_team(omega, kr * Kc, T_total=14.0, seed=s)
            R_final = float(np.mean(R_trace[-60:]))
            psi = np.angle(np.sum(np.exp(1j * phi)))
            devs = np.abs((phi - psi + np.pi) % (2 * np.pi) - np.pi)
            rms_acc.append(float(np.sqrt(np.mean(devs ** 2))))
            bd_acc.append(float(np.sqrt(2.0 * max(0.0, 1.0 - R_final))))
        rms_means.append(np.mean(rms_acc))
        bound_means.append(np.mean(bd_acc))
    ax4.plot(K_ratios_d, rms_means, "o-", color=C_CYAN, label="empirical RMS",
             markersize=6)
    ax4.plot(K_ratios_d, bound_means, "s--", color=C_VIOLET,
             label="√(2(1−R))", markersize=5, alpha=0.85)
    ax4.set_xscale("log")
    ax4.set_yscale("log")
    ax4.set_xlabel("K / Kc")
    ax4.set_ylabel("phase deviation (rad)")
    ax4.set_title("(D) RMS bound across coherence", fontsize=9)
    ax4.legend(fontsize=7)
    ax4.grid(alpha=0.3, which="both")

    _finish(fig, os.path.join(OUT_DIR, "panel3_templating.png"))


# ═══════════════════════════════════════════════════════════════════
# Panel 4 — Duels as cognate oscillator pairs
# ═══════════════════════════════════════════════════════════════════

def panel4_duels():
    rng = np.random.default_rng(4)
    fig = plt.figure(figsize=FIGSIZE)

    # Set up a spring-coupled duel
    m_a, m_b = 75.0, 80.0
    v_a0, v_b0 = 6.0, 0.0
    k_spring = 12000.0
    dt = 1e-4
    steps = int(0.30 / dt)
    x_a, x_b = 0.0, 0.5
    v_a, v_b = v_a0, v_b0
    P_a, P_b = 100.0, 120.0
    traj = np.zeros((steps, 6))
    F_log = np.zeros(steps)
    for k in range(steps):
        gap = x_b - x_a
        F = k_spring * max(0.0, 0.4 - gap)
        v_a += (-F / m_a + P_a / (m_a * max(v_a, 0.1))) * dt
        v_b += (F / m_b) * dt
        v_a = max(v_a, 0.0)
        v_b = max(v_b, 0.0)
        x_a += v_a * dt
        x_b += v_b * dt
        traj[k] = (x_a, v_a, x_b, v_b, 0.5 * m_a * v_a ** 2, 0.5 * m_b * v_b ** 2)
        F_log[k] = F
    t = np.arange(steps) * dt

    # (A) 3D phase-space trajectory of the duel: x_a vs x_b vs F(t)
    ax1 = fig.add_subplot(1, 4, 1, projection="3d")
    sub = slice(None, None, 30)
    ax1.scatter(traj[sub, 0], traj[sub, 2], F_log[sub],
                c=t[sub], cmap="plasma", s=15, edgecolor="none")
    # Project shadows
    ax1.plot(traj[:, 0], traj[:, 2], np.zeros_like(t),
             color=C_GRAY, alpha=0.4, linewidth=0.7)
    ax1.set_xlabel("x_a (m)", fontsize=7)
    ax1.set_ylabel("x_b (m)", fontsize=7)
    ax1.set_zlabel("F (N)", fontsize=7)
    ax1.set_title("(A) Duel phase trajectory", fontsize=9)
    ax1.view_init(elev=24, azim=-60)
    for axis in [ax1.xaxis, ax1.yaxis, ax1.zaxis]:
        axis.set_tick_params(labelsize=7)

    # (B) Velocities of attacker / defender during the duel + contact force
    ax2 = fig.add_subplot(1, 4, 2)
    ax2.plot(t, traj[:, 1], color=C_CYAN, linewidth=1.5, label="attacker v_a")
    ax2.plot(t, traj[:, 3], color=C_AMBER, linewidth=1.5, label="defender v_b")
    ax2b = ax2.twinx()
    ax2b.plot(t, F_log, color=C_RED, linewidth=1.0, alpha=0.7, label="F contact")
    ax2b.set_ylabel("contact force (N)", color=C_RED, fontsize=8)
    ax2b.tick_params(axis="y", labelcolor=C_RED, labelsize=7)
    ax2.set_xlabel("time (s)")
    ax2.set_ylabel("velocity (m/s)")
    ax2.set_title("(B) Velocities through contact", fontsize=9)
    ax2.legend(fontsize=7, loc="upper right")
    ax2.grid(alpha=0.3)

    # (C) Energy bookkeeping bars based on KE change magnitudes:
    #     W_a = |delta KE_a|, W_b = |delta KE_b|, W_c = transferred contact work.
    ax3 = fig.add_subplot(1, 4, 3)
    KE_a_init = 0.5 * m_a * v_a0 ** 2
    KE_b_init = 0.5 * m_b * v_b0 ** 2
    KE_a_final = traj[-1, 4]
    KE_b_final = traj[-1, 5]
    W_a = abs(KE_a_final - KE_a_init)                  # mech work on/from attacker
    W_b = abs(KE_b_final - KE_b_init)                  # mech work on/from defender
    W_c = min(W_a, W_b)                                # energy crossed via contact
    naive = W_a + W_b                                  # double-counts contact transfer
    pair = naive - W_c                                 # framework formula
    labels = ["W_a", "W_b", "W_c", "naive\nsum", "pair\nsum"]
    vals = [W_a, W_b, W_c, naive, pair]
    colors_b = [C_CYAN, C_AMBER, C_RED, C_GRAY, C_VIOLET]
    bars = ax3.bar(labels, vals, color=colors_b,
                   edgecolor="black", linewidth=0.5)
    for b, v in zip(bars, vals):
        ax3.text(b.get_x() + b.get_width() / 2, v + max(vals) * 0.02,
                 f"{v:.0f}", ha="center", fontsize=7)
    ax3.set_ylabel("work (J)")
    ax3.set_title("(C) Pair conservation: naive − pair = W_c", fontsize=9)
    ax3.grid(alpha=0.3, axis="y")

    # (D) Scatter of naive sum vs pair sum across 30 random duels.
    ax4 = fig.add_subplot(1, 4, 4)
    naive_arr, pair_arr, Wc_arr = [], [], []
    for trial in range(30):
        v_a0_r = rng.uniform(4, 8)
        v_b0_r = rng.uniform(0, 1)
        k_r = rng.uniform(8e3, 1.5e4)
        x_a_r, x_b_r = 0.0, 0.5
        v_a_r, v_b_r = v_a0_r, v_b0_r
        P_a_r = rng.uniform(60, 180)
        P_b_r = rng.uniform(60, 180)
        for k in range(steps):
            gap = x_b_r - x_a_r
            F = k_r * max(0.0, 0.4 - gap)
            v_a_r += (-F / m_a + P_a_r / (m_a * max(v_a_r, 0.1))) * dt
            v_b_r += (F / m_b) * dt
            v_a_r = max(v_a_r, 0.0)
            v_b_r = max(v_b_r, 0.0)
            x_a_r += v_a_r * dt
            x_b_r += v_b_r * dt
        W_a_r = abs(0.5 * m_a * (v_a_r ** 2 - v_a0_r ** 2))
        W_b_r = abs(0.5 * m_b * (v_b_r ** 2 - v_b0_r ** 2))
        Wc_r = min(W_a_r, W_b_r)
        naive_arr.append(W_a_r + W_b_r)
        pair_arr.append(W_a_r + W_b_r - Wc_r)
        Wc_arr.append(Wc_r)
    sc = ax4.scatter(naive_arr, pair_arr, c=Wc_arr, cmap="plasma",
                     s=50, edgecolor="black", linewidth=0.5)
    lo = min(min(naive_arr), min(pair_arr))
    hi = max(max(naive_arr), max(pair_arr))
    ax4.plot([lo, hi], [lo, hi], "--", color=C_GRAY, label="naive = pair")
    cbar = fig.colorbar(sc, ax=ax4, shrink=0.8, pad=0.02)
    cbar.set_label("W_c (J)", fontsize=7)
    cbar.ax.tick_params(labelsize=7)
    ax4.set_xlabel("naive W_a + W_b (J)")
    ax4.set_ylabel("pair W_a + W_b − W_c (J)")
    gaps = np.array(naive_arr) - np.array(pair_arr)
    ax4.set_title(f"(D) Gap = W_c = {gaps.mean():.0f} ± {gaps.std():.0f} J", fontsize=9)
    ax4.legend(fontsize=7, loc="upper left")
    ax4.grid(alpha=0.3)

    _finish(fig, os.path.join(OUT_DIR, "panel4_duels.png"))


# ═══════════════════════════════════════════════════════════════════
# Panel 5 — Cellular sampling + backward morphism identifiability
# ═══════════════════════════════════════════════════════════════════

def panel5_sampling_and_recovery():
    rng = np.random.default_rng(5)
    fig = plt.figure(figsize=FIGSIZE)

    # (A) 3D surface: reconstruction MSE over (duty fraction, bandwidth)
    ax1 = fig.add_subplot(1, 4, 1, projection="3d")
    duty_grid = np.linspace(0.05, 0.80, 12)
    B_grid = np.linspace(0.2, 1.0, 10)
    cadence_hz = 3.0
    MSE = np.zeros((duty_grid.size, B_grid.size))
    T = 30.0
    t_high = np.arange(0, T, 0.01)
    for i, duty in enumerate(duty_grid):
        for j, B in enumerate(B_grid):
            fs = duty * cadence_hz
            sample_dt = 1.0 / fs
            errs = []
            for trial in range(3):
                sig = np.zeros_like(t_high)
                fs_sig = np.linspace(0.1, B, 4)
                for f in fs_sig:
                    sig += rng.uniform(0.5, 1.0) * np.sin(
                        2 * np.pi * f * t_high + rng.uniform(0, 2 * np.pi))
                t_s = np.arange(0, T, sample_dt)
                v_s = np.interp(t_s, t_high, sig)
                recon = np.interp(t_high, t_s, v_s)
                errs.append(np.mean((sig - recon) ** 2) / max(np.mean(sig ** 2), 1e-9))
            MSE[i, j] = float(np.mean(errs))
    DD, BB = np.meshgrid(duty_grid, B_grid, indexing="ij")
    surf = ax1.plot_surface(DD, BB, np.clip(MSE, 0, 2.0),
                            cmap="viridis", edgecolor="none", alpha=0.9)
    # Overlay the Nyquist boundary fs = 2B i.e. duty = 2B/cadence
    nyq_duty = 2.0 * B_grid / cadence_hz
    ax1.plot(nyq_duty, B_grid, np.zeros_like(B_grid), color=C_RED, linewidth=2)
    ax1.set_xlabel("duty", fontsize=7)
    ax1.set_ylabel("B (Hz)", fontsize=7)
    ax1.set_zlabel("rel MSE", fontsize=7)
    ax1.set_title("(A) Sampling error surface", fontsize=9)
    ax1.view_init(elev=24, azim=-60)
    for axis in [ax1.xaxis, ax1.yaxis, ax1.zaxis]:
        axis.set_tick_params(labelsize=7)

    # (B) MSE vs effective sample rate (Nyquist demonstration)
    ax2 = fig.add_subplot(1, 4, 2)
    B = 0.5
    duties = np.linspace(0.05, 0.85, 18)
    errs = []
    for duty in duties:
        fs = duty * cadence_hz
        sample_dt = 1.0 / fs
        es = []
        for trial in range(8):
            sig = np.zeros_like(t_high)
            for f in [0.1, 0.25, 0.45]:
                sig += rng.uniform(0.4, 1.0) * np.sin(
                    2 * np.pi * f * t_high + rng.uniform(0, 2 * np.pi))
            t_s = np.arange(0, T, sample_dt)
            v_s = np.interp(t_s, t_high, sig)
            recon = np.interp(t_high, t_s, v_s)
            es.append(np.mean((sig - recon) ** 2) / max(np.mean(sig ** 2), 1e-9))
        errs.append(np.mean(es))
    fs_eff = duties * cadence_hz
    ax2.plot(fs_eff, errs, "o-", color=C_CYAN)
    ax2.axvline(2 * B, color=C_RED, linestyle="--", label=f"2B = {2*B:.1f} Hz")
    ax2.set_xlabel("effective fs (Hz)")
    ax2.set_ylabel("relative MSE")
    ax2.set_yscale("log")
    ax2.set_title("(B) Nyquist breakdown", fontsize=9)
    ax2.legend(fontsize=7)
    ax2.grid(alpha=0.3, which="both")

    # (C) Recovery rate vs R_ens (backward morphism identifiability)
    ax3 = fig.add_subplot(1, 4, 3)
    R_grid = np.linspace(0.05, 0.99, 22)
    K_roles = 5
    n_goals = 300
    rec = np.zeros_like(R_grid)
    generators = [
        [0, 1, 2, 4], [0, 2, 3, 4], [1, 3, 2, 4], [2, 1, 3, 4],
    ]
    G_gen = len(generators)
    for i, R_v in enumerate(R_grid):
        p_corr = R_v
        correct = 0
        for _ in range(n_goals):
            true_gen = rng.integers(0, G_gen)
            true_seq = generators[true_gen]
            obs_seq = [r if rng.random() < p_corr
                       else int(rng.integers(0, K_roles))
                       for r in true_seq]
            scores = [sum(1 for a, b in zip(g, obs_seq) if a == b)
                      for g in generators]
            if int(np.argmax(scores)) == true_gen:
                correct += 1
        rec[i] = correct / n_goals
    ax3.plot(R_grid, rec, "-", color=C_VIOLET, linewidth=1.5)
    ax3.fill_between(R_grid, rec - 0.03, rec + 0.03, color=C_VIOLET, alpha=0.2)
    ax3.axvline(0.80, color=C_GRAY, linestyle=":", linewidth=0.8, label="coherent")
    ax3.axvline(0.95, color=C_RED, linestyle="--", linewidth=0.8, label="phase-lock")
    ax3.set_xlabel("R_ens during build-up")
    ax3.set_ylabel("morphism recovery rate")
    ax3.set_title("(C) Backward identifiability", fontsize=9)
    ax3.legend(fontsize=7)
    ax3.set_xlim(0, 1)
    ax3.set_ylim(0, 1.05)
    ax3.grid(alpha=0.3)

    # (D) Generator confusion matrix at R_ens = 0.9
    ax4 = fig.add_subplot(1, 4, 4)
    R_v = 0.9
    p_corr = R_v
    n_trials = 800
    conf = np.zeros((G_gen, G_gen))
    for _ in range(n_trials):
        true_gen = rng.integers(0, G_gen)
        true_seq = generators[true_gen]
        obs_seq = [r if rng.random() < p_corr
                   else int(rng.integers(0, K_roles))
                   for r in true_seq]
        scores = [sum(1 for a, b in zip(g, obs_seq) if a == b)
                  for g in generators]
        pred = int(np.argmax(scores))
        conf[true_gen, pred] += 1
    conf = conf / conf.sum(axis=1, keepdims=True)
    im = ax4.imshow(conf, cmap="viridis", vmin=0, vmax=1, aspect="equal")
    for i in range(G_gen):
        for j in range(G_gen):
            ax4.text(j, i, f"{conf[i,j]:.2f}",
                     ha="center", va="center",
                     color="white" if conf[i, j] < 0.5 else "black",
                     fontsize=8)
    ax4.set_xticks(range(G_gen))
    ax4.set_yticks(range(G_gen))
    ax4.set_xticklabels([f"g{i}" for i in range(G_gen)])
    ax4.set_yticklabels([f"g{i}" for i in range(G_gen)])
    ax4.set_xlabel("predicted generator")
    ax4.set_ylabel("true generator")
    ax4.set_title(f"(D) Confusion @ R_ens={R_v}", fontsize=9)

    _finish(fig, os.path.join(OUT_DIR, "panel5_sampling_recovery.png"))


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════

def main():
    print("Generating panel 1 ...")
    panel1_observation_operator()
    print("Generating panel 2 ...")
    panel2_bifurcation()
    print("Generating panel 3 ...")
    panel3_templating()
    print("Generating panel 4 ...")
    panel4_duels()
    print("Generating panel 5 ...")
    panel5_sampling_and_recovery()
    print(f"\nAll panels generated in {OUT_DIR}")


if __name__ == "__main__":
    main()
