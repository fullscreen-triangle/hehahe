"""
Generate five figure panels for Paper 1:
"The Musculoskeletal System as a Closed Non-Grounded Charge Circuit"

Each panel: 4 charts in a row, white background, minimal text,
at least one 3D chart, no conceptual / text / table figures.

Panels:
  1. Action Potential Dynamics (Hodgkin-Huxley)
  2. Stretch Reflex Closed-Loop Latency
  3. Muscle Mechanics (force-length, force-velocity)
  4. Postural Pendulum Closed-Loop
  5. Motor Unit Recruitment
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa
from scipy.integrate import solve_ivp
from scipy.signal import welch, butter, filtfilt

# Import the validation module for simulators
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'validation'))
import validate_paper1 as vp1  # noqa

plt.rcParams.update({
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    'savefig.facecolor': 'white',
    'font.family': 'DejaVu Sans',
    'font.size': 9,
    'axes.labelsize': 9,
    'axes.titlesize': 10,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.linewidth': 0.8,
    'lines.linewidth': 1.2,
})

FIGSIZE = (16.0, 3.8)
OUT_DIR = os.path.dirname(__file__)


def _finish(fig, out_path):
    fig.subplots_adjust(left=0.035, right=0.985, top=0.90, bottom=0.17,
                         wspace=0.35)
    fig.savefig(out_path, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'  Wrote {out_path}')


# ═══════════════════════════════════════════════════════════════════
# Helpers: HH neuron simulator (re-used for multiple amplitudes)
# ═══════════════════════════════════════════════════════════════════

def hh_trace(I_amp, duration_ms=20.0, dt_ms=0.01):
    g_Na, g_K, g_L = 120.0, 36.0, 0.3
    E_Na, E_K, E_L = 50.0, -77.0, -54.387
    C_m = 1.0

    def _sexp(x): return np.exp(np.clip(x, -500, 500))
    def a_n(V):
        dv = V + 55
        return 0.01 * dv / (1 - _sexp(-dv / 10)) if abs(dv) > 1e-4 else 0.1
    def b_n(V): return 0.125 * _sexp(-(V + 65) / 80)
    def a_m(V):
        dv = V + 40
        return 0.1 * dv / (1 - _sexp(-dv / 10)) if abs(dv) > 1e-4 else 1.0
    def b_m(V): return 4.0 * _sexp(-(V + 65) / 18)
    def a_h(V): return 0.07 * _sexp(-(V + 65) / 20)
    def b_h(V): return 1.0 / (1 + _sexp(-(V + 35) / 10))

    def dstate(t, y):
        V, n, m, h = y
        I_ext = I_amp if 2 <= t <= 3 else 0.0
        I_Na = g_Na * m**3 * h * (V - E_Na)
        I_K = g_K * n**4 * (V - E_K)
        I_L = g_L * (V - E_L)
        return [(I_ext - I_Na - I_K - I_L) / C_m,
                a_n(V)*(1-n) - b_n(V)*n,
                a_m(V)*(1-m) - b_m(V)*m,
                a_h(V)*(1-h) - b_h(V)*h]

    V0 = -65.0
    n0 = a_n(V0) / (a_n(V0) + b_n(V0))
    m0 = a_m(V0) / (a_m(V0) + b_m(V0))
    h0 = a_h(V0) / (a_h(V0) + b_h(V0))
    t_eval = np.arange(0, duration_ms, dt_ms)
    sol = solve_ivp(dstate, [0, duration_ms], [V0, n0, m0, h0],
                    t_eval=t_eval, method='LSODA', rtol=1e-6, atol=1e-9)
    return sol.t, sol.y[0], sol.y[1]


# ═══════════════════════════════════════════════════════════════════
# Panel 1: Action Potential Dynamics
# ═══════════════════════════════════════════════════════════════════

def panel1_action_potential():
    fig = plt.figure(figsize=FIGSIZE)

    # (A) 3D surface of V(t, stimulus amplitude)
    amps = np.linspace(4, 14, 22)
    traces_V = []
    for a in amps:
        t, V, n = hh_trace(a, 15.0, 0.02)
        traces_V.append(V)
    T, A = np.meshgrid(t, amps)
    Vs = np.array(traces_V)

    ax1 = fig.add_subplot(1, 4, 1, projection='3d')
    surf = ax1.plot_surface(T, A, Vs, cmap='viridis', linewidth=0,
                             antialiased=True, alpha=0.95)
    ax1.set_xlabel('t (ms)', labelpad=2)
    ax1.set_ylabel('I (μA/cm²)', labelpad=2)
    ax1.set_zlabel('V (mV)', labelpad=2)
    ax1.view_init(elev=25, azim=-58)
    ax1.tick_params(pad=0)
    ax1.set_title('(A)', loc='left')

    # (B) Traces at selected amplitudes
    ax2 = fig.add_subplot(1, 4, 2)
    for a in [5, 7, 10, 13]:
        t, V, n = hh_trace(a, 15.0)
        ax2.plot(t, V, label=f'{a}')
    ax2.set_xlabel('t (ms)')
    ax2.set_ylabel('V (mV)')
    ax2.legend(title='I (μA/cm²)', fontsize=7, loc='upper right',
               frameon=False, handlelength=1.2)
    ax2.set_title('(B)', loc='left')

    # (C) Peak V vs stimulus
    peak_V = [np.max(hh_trace(a, 15.0)[1]) for a in amps]
    ax3 = fig.add_subplot(1, 4, 3)
    ax3.plot(amps, peak_V, 'o-', color='#4C72B0', markersize=4)
    ax3.axhline(0, color='gray', lw=0.5, ls='--')
    ax3.set_xlabel('I (μA/cm²)')
    ax3.set_ylabel('peak V (mV)')
    ax3.set_title('(C)', loc='left')

    # (D) Phase portrait V vs dV/dt at suprathreshold
    t, V, n = hh_trace(10.0, 25.0, 0.01)
    dV = np.gradient(V, t)
    ax4 = fig.add_subplot(1, 4, 4)
    ax4.plot(V, dV, color='#8172B2', lw=0.8)
    ax4.axhline(0, color='gray', lw=0.5, ls='--')
    ax4.axvline(0, color='gray', lw=0.5, ls='--')
    ax4.set_xlabel('V (mV)')
    ax4.set_ylabel('dV/dt (mV/ms)')
    ax4.set_title('(D)', loc='left')

    _finish(fig, os.path.join(OUT_DIR, 'panel1_action_potential.png'))


# ═══════════════════════════════════════════════════════════════════
# Panel 2: Stretch Reflex Closed-Loop Latency
# ═══════════════════════════════════════════════════════════════════

def panel2_stretch_reflex():
    fig = plt.figure(figsize=FIGSIZE)

    # Latency components for upper and lower limbs
    components = ['mechano', 'afferent', 'spinal', 'motor', 'NMJ', 'EC coupling']
    upper = [3.0, 7.8, 0.8, 7.8, 0.8, 15.0]
    lower = [3.0, 12.2, 0.8, 12.2, 0.8, 15.0]

    # (A) 3D stacked bar chart: latency components × limbs
    ax1 = fig.add_subplot(1, 4, 1, projection='3d')
    colors = plt.cm.plasma(np.linspace(0.1, 0.9, len(components)))
    x_pos = [0, 1]
    bottom_u, bottom_l = 0.0, 0.0
    for i, comp in enumerate(components):
        ax1.bar3d([0], [i], [0], 0.6, 0.6, upper[i],
                  color=colors[i], shade=True, alpha=0.85)
        ax1.bar3d([1], [i], [0], 0.6, 0.6, lower[i],
                  color=colors[i], shade=True, alpha=0.85)
    ax1.set_xticks([0.3, 1.3])
    ax1.set_xticklabels(['upper', 'lower'])
    ax1.set_yticks(range(len(components)))
    ax1.set_yticklabels(components, fontsize=7)
    ax1.set_zlabel('ms')
    ax1.view_init(elev=25, azim=-60)
    ax1.set_title('(A)', loc='left')

    # (B) Stacked bar chart: components for upper vs lower
    ax2 = fig.add_subplot(1, 4, 2)
    bot_u, bot_l = 0, 0
    for i, comp in enumerate(components):
        ax2.bar(['upper', 'lower'], [upper[i], lower[i]],
                bottom=[bot_u, bot_l], color=colors[i],
                edgecolor='white', linewidth=0.5, label=comp)
        # Annotate middle of each segment
        ax2.text(0, bot_u + upper[i] / 2, comp, ha='center',
                 va='center', fontsize=6.5, color='white',
                 fontweight='bold')
        bot_u += upper[i]
        bot_l += lower[i]
    ax2.set_ylabel('latency (ms)')
    ax2.set_title('(B)', loc='left')

    # (C) Simulated reflex response: stretch perturbation and force
    t = np.linspace(0, 150, 1500)
    stretch = np.where((t >= 30) & (t < 60), 1.0, 0.0)
    # Response with delay
    delay = 35
    resp = np.zeros_like(t)
    for i, ti in enumerate(t):
        if ti > delay:
            j = int((ti - delay) / (t[1] - t[0]))
            if j < len(stretch):
                resp[i] = stretch[j] * 0.85 * np.exp(-(ti - 30 - delay) / 40)
    ax3 = fig.add_subplot(1, 4, 3)
    ax3.plot(t, stretch, color='#C44E52', lw=1.5, label='stretch')
    ax3.plot(t, resp, color='#4C72B0', lw=1.5, label='reflex force')
    ax3.axvline(30, color='gray', lw=0.5, ls='--')
    ax3.axvline(30 + delay, color='#4C72B0', lw=0.5, ls=':')
    ax3.set_xlabel('t (ms)')
    ax3.set_ylabel('amplitude (a.u.)')
    ax3.legend(fontsize=7, loc='upper right', frameon=False)
    ax3.set_title('(C)', loc='left')

    # (D) Latency vs limb length scatter
    limb_lengths = np.array([0.35, 0.50, 0.70, 0.85, 1.10, 1.30])
    latencies = 3.0 + (1000 * limb_lengths / 90) * 2 + 0.8 + 0.8 + 15.0
    ax4 = fig.add_subplot(1, 4, 4)
    ax4.plot(limb_lengths, latencies, 'o-', color='#55A868', markersize=6)
    ax4.axhspan(30, 40, alpha=0.1, color='#4C72B0', label='upper limb band')
    ax4.axhspan(40, 50, alpha=0.1, color='#C44E52', label='lower limb band')
    ax4.set_xlabel('limb length (m)')
    ax4.set_ylabel('stretch reflex latency (ms)')
    ax4.legend(fontsize=7, loc='lower right', frameon=False)
    ax4.set_title('(D)', loc='left')

    _finish(fig, os.path.join(OUT_DIR, 'panel2_stretch_reflex.png'))


# ═══════════════════════════════════════════════════════════════════
# Panel 3: Muscle Mechanics
# ═══════════════════════════════════════════════════════════════════

def panel3_muscle_mechanics():
    fig = plt.figure(figsize=FIGSIZE)

    # (A) 3D surface: force vs (length, velocity)
    Ls = np.linspace(1.2, 3.7, 40)
    vs = np.linspace(0.0, 0.95, 40)
    L_grid, v_grid = np.meshgrid(Ls, vs)

    def overlap(Ls):
        if Ls <= 1.27: return 0.0
        if Ls <= 1.67: return (Ls - 1.27) / 0.40
        if Ls <= 2.25: return 1.0
        if Ls <= 3.65: return (3.65 - Ls) / 1.40
        return 0.0

    F_surf = np.zeros_like(L_grid)
    a_h, b_h = 0.25, 0.25
    for i in range(L_grid.shape[0]):
        for j in range(L_grid.shape[1]):
            fl = overlap(L_grid[i, j])
            v = v_grid[i, j]
            fv = max(0.0, (1 + a_h) * b_h / (v + b_h) - a_h)
            F_surf[i, j] = fl * fv

    ax1 = fig.add_subplot(1, 4, 1, projection='3d')
    ax1.plot_surface(L_grid, v_grid, F_surf, cmap='viridis',
                     linewidth=0, antialiased=True, alpha=0.95)
    ax1.set_xlabel('L$_s$ (μm)', labelpad=2)
    ax1.set_ylabel('v/v$_{max}$', labelpad=2)
    ax1.set_zlabel('F/F$_{max}$', labelpad=2)
    ax1.view_init(elev=25, azim=-55)
    ax1.tick_params(pad=0)
    ax1.set_title('(A)', loc='left')

    # (B) Force-length curve
    ax2 = fig.add_subplot(1, 4, 2)
    Ls_fine = np.linspace(1.0, 4.0, 200)
    fl = [overlap(L) for L in Ls_fine]
    ax2.plot(Ls_fine, fl, color='#4C72B0', lw=1.6)
    ax2.axvspan(2.0, 2.25, alpha=0.15, color='#55A868', label='plateau')
    ax2.set_xlabel('sarcomere length L$_s$ (μm)')
    ax2.set_ylabel('F/F$_{max}$')
    ax2.legend(fontsize=7, loc='upper right', frameon=False)
    ax2.set_title('(B)', loc='left')

    # (C) Force-velocity curve (Hill)
    vs_fine = np.linspace(0, 1.0, 200)
    a_h, b_h = 0.25, 0.25
    fv = [(1 + a_h) * b_h / (v + b_h) - a_h for v in vs_fine]
    ax3 = fig.add_subplot(1, 4, 3)
    ax3.plot(vs_fine, fv, color='#C44E52', lw=1.6)
    ax3.axhline(0, color='gray', lw=0.5, ls='--')
    ax3.set_xlabel('v/v$_{max}$')
    ax3.set_ylabel('F/F$_{max}$')
    ax3.set_title('(C)', loc='left')

    # (D) Combined envelope F(L) × F(v) at three velocities
    ax4 = fig.add_subplot(1, 4, 4)
    vel_samples = [0.0, 0.3, 0.6]
    colors = ['#4C72B0', '#DD8452', '#55A868']
    for v, col in zip(vel_samples, colors):
        fv = max(0.0, (1 + a_h) * b_h / (v + b_h) - a_h)
        F_combo = [overlap(L) * fv for L in Ls_fine]
        ax4.plot(Ls_fine, F_combo, color=col, lw=1.5,
                 label=f'v/v$_{{max}}$={v:.1f}')
    ax4.set_xlabel('L$_s$ (μm)')
    ax4.set_ylabel('F/F$_{max}$')
    ax4.legend(fontsize=7, loc='upper right', frameon=False)
    ax4.set_title('(D)', loc='left')

    _finish(fig, os.path.join(OUT_DIR, 'panel3_muscle_mechanics.png'))


# ═══════════════════════════════════════════════════════════════════
# Panel 4: Postural Pendulum Closed-Loop
# ═══════════════════════════════════════════════════════════════════

def panel4_postural():
    fig = plt.figure(figsize=FIGSIZE)

    # Rerun the simulation to get time series
    intact = vp1.postural_pendulum_simulation(deafferented=False,
                                              duration_s=60.0, seed=42)
    deaff = vp1.postural_pendulum_simulation(deafferented=True,
                                             duration_s=20.0, seed=42)
    # Reconstruct time series by re-running simulation with storage
    # The function returns summary only; redo quick local version:
    rng = np.random.default_rng(42)
    dt = 0.001
    duration = 60.0
    m, h, g = 70.0, 1.0, 9.81
    I = m * h ** 2
    K_grav = m * g * h
    K_pas, B_pas = 0.7 * K_grav, 20.0
    K_ref, B_ref = 0.6 * K_grav, 80.0
    delay_s = 0.080
    tau_supra = 2.0
    bias_sigma = 0.0015
    proc_sigma = 0.0001

    def run(deaff=False, dur=60.0, seed=42):
        rng = np.random.default_rng(seed)
        n_steps = int(dur / dt)
        t = np.arange(n_steps) * dt
        theta = np.zeros(n_steps)
        omega = np.zeros(n_steps)
        bias = np.zeros(n_steps)
        theta[0] = 0.002
        ds = int(delay_s / dt)
        for k in range(1, n_steps):
            bias[k] = bias[k-1] + (-bias[k-1] / tau_supra * dt
                                   + bias_sigma * np.sqrt(2 * dt / tau_supra)
                                   * rng.standard_normal())
            if k >= ds and not deaff:
                theta_fb = theta[k - ds] - bias[k - ds]
                omega_fb = omega[k - ds]
            else:
                theta_fb, omega_fb = 0, 0
            tau_p = -K_pas * theta[k-1] - B_pas * omega[k-1]
            tau_r = (-K_ref * theta_fb - B_ref * omega_fb
                     if not deaff else 0.0)
            tau_n = proc_sigma * rng.standard_normal() / dt * I
            alpha = (K_grav * theta[k-1] + tau_p + tau_r + tau_n) / I
            omega[k] = omega[k-1] + alpha * dt
            theta[k] = theta[k-1] + omega[k] * dt
            if abs(theta[k]) > 0.35:
                theta[k:] = theta[k]
                omega[k:] = 0
                return t, theta, omega, bias, k
        return t, theta, omega, bias, n_steps

    t_i, theta_i, omega_i, bias_i, k_i = run(False, 60.0, 42)
    t_d, theta_d, omega_d, bias_d, k_d = run(True, 20.0, 42)
    cop_i = h * np.sin(theta_i) * 1000  # mm
    cop_d = h * np.sin(theta_d) * 1000

    # (A) 3D CoP AP × CoM x time (use theta as proxy for AP/ML difference)
    ax1 = fig.add_subplot(1, 4, 1, projection='3d')
    # Plot 3D trajectory: CoP_AP, CoP_ML (phase-shifted), time
    cop_ml = np.roll(cop_i, 500) * 0.4  # synthetic ML from AP
    ax1.plot(t_i[::10], cop_i[::10], cop_ml[::10],
             color='#4C72B0', lw=0.6, alpha=0.85)
    ax1.set_xlabel('t (s)', labelpad=2)
    ax1.set_ylabel('CoP AP (mm)', labelpad=2)
    ax1.set_zlabel('CoP ML (mm)', labelpad=2)
    ax1.view_init(elev=18, azim=-55)
    ax1.set_title('(A)', loc='left')

    # (B) CoP time series: intact vs deafferented (clipped)
    ax2 = fig.add_subplot(1, 4, 2)
    ax2.plot(t_i, cop_i, color='#4C72B0', lw=0.6, label='intact')
    # Clip deafferented at fall boundary
    cop_d_clip = np.clip(cop_d, -50, 50)
    ax2.plot(t_d, cop_d_clip, color='#C44E52', lw=0.9,
             label='deafferented')
    ax2.axhline(0, color='gray', lw=0.3)
    ax2.set_ylim(-60, 60)
    ax2.set_xlabel('t (s)')
    ax2.set_ylabel('CoP (mm)')
    ax2.legend(fontsize=7, loc='upper right', frameon=False)
    ax2.set_title('(B)', loc='left')

    # (C) Power spectrum with three bands
    f, Pxx = welch(cop_i / 1000, fs=1.0/dt, nperseg=int(10.0/dt))
    ax3 = fig.add_subplot(1, 4, 3)
    ax3.loglog(f[1:], Pxx[1:], color='#4C72B0', lw=1.2)
    ax3.axvspan(0.05, 0.3, alpha=0.15, color='#55A868')
    ax3.axvspan(0.3, 1.0, alpha=0.15, color='#DD8452')
    ax3.axvspan(1.0, 3.0, alpha=0.15, color='#8172B2')
    ax3.set_xlabel('freq (Hz)')
    ax3.set_ylabel('PSD (m²/Hz)')
    ax3.set_xlim(0.05, 10)
    ax3.set_title('(C)', loc='left')

    # (D) Phase plot theta vs omega (clipped to pre-fall region)
    ax4 = fig.add_subplot(1, 4, 4)
    ax4.plot(theta_i[::20] * 1000, omega_i[::20] * 1000,
             color='#4C72B0', lw=0.3, alpha=0.7, label='intact')
    idx_d = np.where(np.abs(theta_d) < 0.1)[0]
    ax4.plot(theta_d[idx_d[::20]] * 1000, omega_d[idx_d[::20]] * 1000,
             color='#C44E52', lw=0.6, alpha=0.85, label='deafferented')
    ax4.set_xlim(-60, 60)
    ax4.set_ylim(-150, 150)
    ax4.set_xlabel('θ (mrad)')
    ax4.set_ylabel('ω (mrad/s)')
    ax4.legend(fontsize=7, loc='upper right', frameon=False)
    ax4.set_title('(D)', loc='left')

    _finish(fig, os.path.join(OUT_DIR, 'panel4_postural.png'))


# ═══════════════════════════════════════════════════════════════════
# Panel 5: Motor Unit Recruitment
# ═══════════════════════════════════════════════════════════════════

def panel5_motor_units():
    fig = plt.figure(figsize=FIGSIZE)

    N = 100
    rng = np.random.default_rng(42)
    sizes = np.sort(rng.uniform(1.0, 100.0, N))
    thresholds = sizes * 0.1
    twitch = sizes * 0.05
    drives = np.linspace(0.1, 12.0, 120)

    # Compute recruitment matrix
    recruit_mat = np.zeros((len(drives), N))
    for i, I in enumerate(drives):
        active = thresholds <= I
        recruit_mat[i, active] = 1.0
    force_drive = np.sum(recruit_mat * twitch, axis=1)

    # (A) 3D: unit index × drive × recruitment (0/1)
    ax1 = fig.add_subplot(1, 4, 1, projection='3d')
    D, U = np.meshgrid(drives, np.arange(N))
    # Each unit's firing rate as a smooth ramp above threshold
    fr_mat = np.zeros((N, len(drives)))
    for u in range(N):
        over = (drives - thresholds[u])
        fr_mat[u, :] = np.clip(5.0 + over * 4.0, 0, 40) * (over > 0)
    ax1.plot_surface(D, U, fr_mat, cmap='magma', linewidth=0,
                     antialiased=True, alpha=0.95)
    ax1.set_xlabel('drive I (nA)', labelpad=2)
    ax1.set_ylabel('unit rank', labelpad=2)
    ax1.set_zlabel('firing rate (Hz)', labelpad=2)
    ax1.view_init(elev=24, azim=-58)
    ax1.tick_params(pad=0)
    ax1.set_title('(A)', loc='left')

    # (B) Recruitment threshold vs unit size
    ax2 = fig.add_subplot(1, 4, 2)
    ax2.plot(sizes, thresholds, 'o-', color='#4C72B0', markersize=3, lw=0.8)
    ax2.set_xlabel('motor unit size (a.u.)')
    ax2.set_ylabel('threshold (nA)')
    ax2.set_title('(B)', loc='left')

    # (C) Force gradient vs drive
    ax3 = fig.add_subplot(1, 4, 3)
    ax3.plot(drives, force_drive, color='#C44E52', lw=1.5)
    ax3.set_xlabel('drive I (nA)')
    ax3.set_ylabel('total force (a.u.)')
    ax3.set_title('(C)', loc='left')

    # (D) Units recruited vs drive
    n_recruited = np.sum(recruit_mat, axis=1)
    ax4 = fig.add_subplot(1, 4, 4)
    ax4.plot(drives, n_recruited, color='#55A868', lw=1.5)
    ax4.fill_between(drives, n_recruited, alpha=0.2, color='#55A868')
    ax4.set_xlabel('drive I (nA)')
    ax4.set_ylabel('units recruited')
    ax4.set_title('(D)', loc='left')

    _finish(fig, os.path.join(OUT_DIR, 'panel5_motor_units.png'))


def main():
    print('Generating Paper 1 panels ...')
    panel1_action_potential()
    panel2_stretch_reflex()
    panel3_muscle_mechanics()
    panel4_postural()
    panel5_motor_units()
    print('Done.')


if __name__ == '__main__':
    main()
