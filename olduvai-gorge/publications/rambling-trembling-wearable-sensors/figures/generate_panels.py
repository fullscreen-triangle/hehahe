"""
Generate five figure panels for Paper 2:
"Rambling and Trembling as Distinct Components of the Closed
Postural Control Circuit"

Each panel: 4 charts in a row, white background, minimal text,
at least one 3D chart, no conceptual / text / table figures.

Panels:
  1. IEP Decomposition of CoP
  2. Spectral Structure
  3. Dual-Task and Aging Effects
  4. Pathology Signatures
  5. Multi-Sensor Consistency
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa
from scipy.signal import welch, butter, filtfilt, hilbert

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'validation'))
import validate_paper2 as vp2  # noqa

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

BLUE = '#4C72B0'
RED = '#C44E52'
GREEN = '#55A868'
ORANGE = '#DD8452'
PURPLE = '#8172B2'
GOLD = '#CCB974'


# ═══════════════════════════════════════════════════════════════════
# Panel 1: IEP Decomposition
# ═══════════════════════════════════════════════════════════════════

def panel1_decomposition():
    fig = plt.figure(figsize=FIGSIZE)

    sim = vp2.simulate_postural_sway(duration_s=30.0, dt=0.005, seed=1)
    cop = sim["cop"] * 1000  # mm
    t = sim["t"]
    ra, tr = vp2.decompose_rambling_trembling(sim["cop"], t)
    ra = ra * 1000
    tr = tr * 1000

    # (A) 3D: CoP, rambling, trembling as three traces along z
    ax1 = fig.add_subplot(1, 4, 1, projection='3d')
    ax1.plot(t, cop, np.zeros_like(t), color=BLUE, lw=0.6, label='CoP')
    ax1.plot(t, ra, np.ones_like(t) * 10, color=ORANGE, lw=1.0,
             label='rambling')
    ax1.plot(t, tr, np.ones_like(t) * 20, color=PURPLE, lw=0.6,
             label='trembling')
    ax1.set_xlabel('t (s)', labelpad=2)
    ax1.set_ylabel('amplitude (mm)', labelpad=2)
    ax1.set_zlabel('component', labelpad=2)
    ax1.set_zticks([0, 10, 20])
    ax1.set_zticklabels(['CoP', 'rambling', 'trembling'], fontsize=7)
    ax1.view_init(elev=18, azim=-55)
    ax1.set_title('(A)', loc='left')

    # (B) CoP time series
    ax2 = fig.add_subplot(1, 4, 2)
    ax2.plot(t, cop, color=BLUE, lw=0.6)
    ax2.set_xlabel('t (s)')
    ax2.set_ylabel('CoP (mm)')
    ax2.axhline(0, color='gray', lw=0.3)
    ax2.set_title('(B)', loc='left')

    # (C) Rambling
    ax3 = fig.add_subplot(1, 4, 3)
    ax3.plot(t, ra, color=ORANGE, lw=0.9)
    ax3.set_xlabel('t (s)')
    ax3.set_ylabel('rambling (mm)')
    ax3.axhline(0, color='gray', lw=0.3)
    ax3.set_title('(C)', loc='left')

    # (D) Trembling
    ax4 = fig.add_subplot(1, 4, 4)
    ax4.plot(t, tr, color=PURPLE, lw=0.6)
    ax4.set_xlabel('t (s)')
    ax4.set_ylabel('trembling (mm)')
    ax4.axhline(0, color='gray', lw=0.3)
    ax4.set_title('(D)', loc='left')

    _finish(fig, os.path.join(OUT_DIR, 'panel1_decomposition.png'))


# ═══════════════════════════════════════════════════════════════════
# Panel 2: Spectral Structure
# ═══════════════════════════════════════════════════════════════════

def panel2_spectral():
    fig = plt.figure(figsize=FIGSIZE)

    # Run at three cognitive loads for 3D spectra
    loads = [0.0, 0.5, 1.0]
    colors_load = [BLUE, ORANGE, RED]
    all_f = None
    all_P = []
    for load in loads:
        sim = vp2.simulate_postural_sway(duration_s=30.0, seed=2,
                                          cognitive_load=load)
        dt = sim["t"][1] - sim["t"][0]
        f, P = welch(sim["cop"], fs=1.0/dt, nperseg=int(10.0/dt))
        if all_f is None:
            all_f = f
        all_P.append(P)
    all_P = np.array(all_P)

    # (A) 3D spectrum: PSD over (freq, cognitive_load)
    ax1 = fig.add_subplot(1, 4, 1, projection='3d')
    mask = (all_f > 0.03) & (all_f < 3.5)
    f_plot = all_f[mask]
    P_plot = all_P[:, mask]
    X, Y = np.meshgrid(f_plot, loads)
    ax1.plot_surface(X, Y, np.log10(P_plot + 1e-16), cmap='plasma',
                      linewidth=0, antialiased=True, alpha=0.9)
    ax1.set_xlabel('freq (Hz)', labelpad=2)
    ax1.set_ylabel('cognitive load', labelpad=2)
    ax1.set_zlabel('log PSD', labelpad=2)
    ax1.view_init(elev=22, azim=-55)
    ax1.set_title('(A)', loc='left')

    # (B) PSD with three bands highlighted
    sim = vp2.simulate_postural_sway(duration_s=30.0, seed=2)
    dt = sim["t"][1] - sim["t"][0]
    f, P = welch(sim["cop"], fs=1.0/dt, nperseg=int(10.0/dt))
    ax2 = fig.add_subplot(1, 4, 2)
    ax2.loglog(f[1:], P[1:], color=BLUE, lw=1.2)
    ax2.axvspan(0.05, 0.3, alpha=0.15, color=GREEN)
    ax2.axvspan(0.3, 1.0, alpha=0.15, color=ORANGE)
    ax2.axvspan(1.0, 3.0, alpha=0.15, color=PURPLE)
    ax2.set_xlabel('freq (Hz)')
    ax2.set_ylabel('PSD (m²/Hz)')
    ax2.set_xlim(0.05, 5)
    ax2.set_title('(B)', loc='left')

    # (C) Rambling vs trembling PSD overlay
    ra, tr = vp2.decompose_rambling_trembling(sim["cop"], sim["t"])
    f_r, P_r = welch(ra, fs=1.0/dt, nperseg=int(10.0/dt))
    f_t, P_t = welch(tr, fs=1.0/dt, nperseg=int(10.0/dt))
    ax3 = fig.add_subplot(1, 4, 3)
    ax3.loglog(f_r[1:], P_r[1:], color=ORANGE, lw=1.2, label='rambling')
    ax3.loglog(f_t[1:], P_t[1:], color=PURPLE, lw=1.2, label='trembling')
    ax3.set_xlabel('freq (Hz)')
    ax3.set_ylabel('PSD (m²/Hz)')
    ax3.set_xlim(0.05, 5)
    ax3.legend(fontsize=7, loc='upper right', frameon=False)
    ax3.set_title('(C)', loc='left')

    # (D) Band-power bars
    def band_p(f_, P_, lo, hi):
        m = (f_ >= lo) & (f_ < hi)
        return float(np.trapezoid(P_[m], f_[m]))

    supra = band_p(f, P, 0.05, 0.3)
    spinal = band_p(f, P, 0.3, 1.0)
    reflex = band_p(f, P, 1.0, 3.0)
    total = supra + spinal + reflex
    ax4 = fig.add_subplot(1, 4, 4)
    bars = ax4.bar(['supra', 'spinal', 'reflex'],
                    [100 * supra / total,
                     100 * spinal / total,
                     100 * reflex / total],
                    color=[GREEN, ORANGE, PURPLE], edgecolor='white')
    ax4.set_ylabel('band power (%)')
    ax4.set_title('(D)', loc='left')

    _finish(fig, os.path.join(OUT_DIR, 'panel2_spectral.png'))


# ═══════════════════════════════════════════════════════════════════
# Panel 3: Dual-Task and Aging Effects
# ═══════════════════════════════════════════════════════════════════

def panel3_dual_task_aging():
    fig = plt.figure(figsize=FIGSIZE)

    # Collect cognitive load data
    loads = [0.0, 0.25, 0.5, 0.75, 1.0]
    cog_ra, cog_tr = [], []
    for load in loads:
        ra_vals, tr_vals = [], []
        for seed in range(3):
            sim = vp2.simulate_postural_sway(duration_s=30.0, seed=seed,
                                              cognitive_load=load)
            if sim["fell"]:
                continue
            ra, tr = vp2.decompose_rambling_trembling(sim["cop"], sim["t"])
            ra_vals.append(np.std(ra) * 1000)
            tr_vals.append(np.std(tr) * 1000)
        cog_ra.append(np.mean(ra_vals))
        cog_tr.append(np.mean(tr_vals))

    ages = [1.0, 0.9, 0.75, 0.6, 0.5]
    age_ra, age_tr = [], []
    for a in ages:
        ra_vals, tr_vals = [], []
        for seed in range(3):
            sim = vp2.simulate_postural_sway(duration_s=30.0, seed=seed,
                                              age_factor=a)
            if sim["fell"]:
                continue
            ra, tr = vp2.decompose_rambling_trembling(sim["cop"], sim["t"])
            ra_vals.append(np.std(ra) * 1000)
            tr_vals.append(np.std(tr) * 1000)
        age_ra.append(np.mean(ra_vals))
        age_tr.append(np.mean(tr_vals))

    # (A) 3D: condition (cog, age) × component × amplitude
    ax1 = fig.add_subplot(1, 4, 1, projection='3d')
    xs = np.arange(5)
    # Bars for cognitive load (y=0) and aging (y=1), two components (z)
    for i, (c_ra, c_tr, load) in enumerate(zip(cog_ra, cog_tr, loads)):
        ax1.bar3d([i], [0], [0], 0.7, 0.4, c_ra,
                  color=ORANGE, alpha=0.85, shade=True)
        ax1.bar3d([i], [0.5], [0], 0.7, 0.4, c_tr,
                  color=PURPLE, alpha=0.85, shade=True)
    for i, (a_ra, a_tr, af) in enumerate(zip(age_ra, age_tr, ages)):
        ax1.bar3d([i], [1.5], [0], 0.7, 0.4, a_ra,
                  color=ORANGE, alpha=0.85, shade=True)
        ax1.bar3d([i], [2.0], [0], 0.7, 0.4, a_tr,
                  color=PURPLE, alpha=0.85, shade=True)
    ax1.set_xticks(range(5))
    ax1.set_xticklabels(['1', '2', '3', '4', '5'], fontsize=7)
    ax1.set_yticks([0.2, 0.7, 1.7, 2.2])
    ax1.set_yticklabels(['cog-Ra', 'cog-Tr', 'age-Ra', 'age-Tr'],
                        fontsize=7)
    ax1.set_xlabel('level', labelpad=2)
    ax1.set_zlabel('RMS (mm)', labelpad=2)
    ax1.view_init(elev=28, azim=-60)
    ax1.set_title('(A)', loc='left')

    # (B) Cognitive load vs rambling and trembling
    ax2 = fig.add_subplot(1, 4, 2)
    ax2.plot(loads, cog_ra, 'o-', color=ORANGE, label='rambling',
             markersize=5)
    ax2.plot(loads, cog_tr, 's-', color=PURPLE, label='trembling',
             markersize=5)
    ax2.set_xlabel('cognitive load')
    ax2.set_ylabel('RMS (mm)')
    ax2.legend(fontsize=7, loc='upper left', frameon=False)
    ax2.set_title('(B)', loc='left')

    # (C) Aging vs rambling and trembling
    ax3 = fig.add_subplot(1, 4, 3)
    ages_x = [1.0 - a for a in ages]  # aging progression
    ax3.plot(ages_x, age_ra, 'o-', color=ORANGE, markersize=5)
    ax3.plot(ages_x, age_tr, 's-', color=PURPLE, markersize=5)
    ax3.set_xlabel('aging (1 − loop-gain factor)')
    ax3.set_ylabel('RMS (mm)')
    ax3.set_title('(C)', loc='left')

    # (D) Preferential-effect scatter
    ra_change_cog = [(r - cog_ra[0]) / cog_ra[0] * 100 for r in cog_ra]
    tr_change_cog = [(r - cog_tr[0]) / cog_tr[0] * 100 for r in cog_tr]
    ra_change_age = [(r - age_ra[0]) / age_ra[0] * 100 for r in age_ra]
    tr_change_age = [(r - age_tr[0]) / age_tr[0] * 100 for r in age_tr]
    ax4 = fig.add_subplot(1, 4, 4)
    ax4.plot(ra_change_cog, tr_change_cog, 'o-', color=BLUE,
             markersize=6, label='dual-task')
    ax4.plot(ra_change_age, tr_change_age, 's-', color=RED,
             markersize=6, label='aging')
    ax4.plot([-20, 300], [-20, 300], 'k--', lw=0.5, alpha=0.4)
    ax4.set_xlabel('Δrambling (%)')
    ax4.set_ylabel('Δtrembling (%)')
    ax4.legend(fontsize=7, loc='lower right', frameon=False)
    ax4.set_title('(D)', loc='left')

    _finish(fig, os.path.join(OUT_DIR, 'panel3_dual_task_aging.png'))


# ═══════════════════════════════════════════════════════════════════
# Panel 4: Pathology Signatures
# ═══════════════════════════════════════════════════════════════════

def panel4_pathology():
    fig = plt.figure(figsize=FIGSIZE)

    def get_stats(n=5, **kw):
        ra_list, tr_list = [], []
        for seed in range(n):
            sim = vp2.simulate_postural_sway(duration_s=30.0, seed=seed, **kw)
            if sim["fell"]:
                continue
            ra, tr = vp2.decompose_rambling_trembling(sim["cop"], sim["t"])
            ra_list.append(np.std(ra) * 1000)
            tr_list.append(np.std(tr) * 1000)
        return np.array(ra_list), np.array(tr_list)

    ctrl_ra, ctrl_tr = get_stats()
    pd_ra, pd_tr = get_stats(parkinson_factor=0.7)
    at_ra, at_tr = get_stats(cerebellar_noise=0.8)

    # (A) 3D clustered bars: 3 conditions × 2 components × trials
    ax1 = fig.add_subplot(1, 4, 1, projection='3d')
    conditions = ['ctrl', 'PD', 'ataxia']
    ra_data = [ctrl_ra, pd_ra, at_ra]
    tr_data = [ctrl_tr, pd_tr, at_tr]
    for i, (ra_vals, tr_vals) in enumerate(zip(ra_data, tr_data)):
        for j, v in enumerate(ra_vals):
            ax1.bar3d([i], [j], [0], 0.35, 0.6, v,
                      color=ORANGE, alpha=0.8, shade=True)
        for j, v in enumerate(tr_vals):
            ax1.bar3d([i + 0.4], [j], [0], 0.35, 0.6, v,
                      color=PURPLE, alpha=0.8, shade=True)
    ax1.set_xticks([0.35, 1.35, 2.35])
    ax1.set_xticklabels(conditions)
    ax1.set_ylabel('trial', labelpad=2)
    ax1.set_zlabel('RMS (mm)', labelpad=2)
    ax1.view_init(elev=26, azim=-60)
    ax1.set_title('(A)', loc='left')

    # (B) PD vs control: trembling bar + error bars
    ax2 = fig.add_subplot(1, 4, 2)
    categories = ['control', 'Parkinson']
    mean_ra = [np.mean(ctrl_ra), np.mean(pd_ra)]
    sem_ra = [np.std(ctrl_ra) / np.sqrt(len(ctrl_ra)),
              np.std(pd_ra) / np.sqrt(len(pd_ra))]
    mean_tr = [np.mean(ctrl_tr), np.mean(pd_tr)]
    sem_tr = [np.std(ctrl_tr) / np.sqrt(len(ctrl_tr)),
              np.std(pd_tr) / np.sqrt(len(pd_tr))]
    x = np.arange(2)
    ax2.bar(x - 0.18, mean_ra, 0.35, yerr=sem_ra, color=ORANGE,
            edgecolor='white', label='rambling', capsize=3)
    ax2.bar(x + 0.18, mean_tr, 0.35, yerr=sem_tr, color=PURPLE,
            edgecolor='white', label='trembling', capsize=3)
    ax2.set_xticks(x)
    ax2.set_xticklabels(categories)
    ax2.set_ylabel('RMS (mm)')
    ax2.legend(fontsize=7, loc='upper left', frameon=False)
    ax2.set_title('(B)', loc='left')

    # (C) Cerebellar coupling index: control vs ataxic
    def coupling(ra, tr):
        env = np.abs(hilbert(tr))
        a0 = ra - np.mean(ra)
        e0 = env - np.mean(env)
        if np.std(a0) == 0 or np.std(e0) == 0:
            return 0
        return abs(np.corrcoef(a0, e0)[0, 1])

    ctrl_C, at_C = [], []
    for seed in range(5):
        sim_c = vp2.simulate_postural_sway(duration_s=30.0, seed=seed)
        sim_a = vp2.simulate_postural_sway(duration_s=30.0, seed=seed,
                                            cerebellar_noise=0.8)
        for sim, lst in [(sim_c, ctrl_C), (sim_a, at_C)]:
            if not sim["fell"]:
                ra, tr = vp2.decompose_rambling_trembling(
                    sim["cop"], sim["t"])
                lst.append(coupling(ra, tr))
    ax3 = fig.add_subplot(1, 4, 3)
    vp = ax3.violinplot([ctrl_C, at_C], positions=[0, 1],
                        showmeans=True, showmedians=False)
    for body, col in zip(vp['bodies'], [BLUE, RED]):
        body.set_facecolor(col)
        body.set_alpha(0.6)
    ax3.set_xticks([0, 1])
    ax3.set_xticklabels(['control', 'ataxia'])
    ax3.set_ylabel('coupling index')
    ax3.set_title('(C)', loc='left')

    # (D) Deafferented: fall time distribution
    fall_times = []
    for seed in range(20):
        sim = vp2.simulate_postural_sway(duration_s=10.0, seed=seed,
                                          deafferented=True)
        if sim["fell"]:
            fall_times.append(sim["fall_time_s"])
    ax4 = fig.add_subplot(1, 4, 4)
    ax4.hist(fall_times, bins=10, color=RED, edgecolor='white',
             alpha=0.85)
    ax4.axvline(np.mean(fall_times), color='black', lw=1.5, ls='--',
                label=f'mean={np.mean(fall_times):.2f}s')
    ax4.set_xlabel('fall time (s)')
    ax4.set_ylabel('count')
    ax4.legend(fontsize=7, loc='upper right', frameon=False)
    ax4.set_title('(D)', loc='left')

    _finish(fig, os.path.join(OUT_DIR, 'panel4_pathology.png'))


# ═══════════════════════════════════════════════════════════════════
# Panel 5: Multi-Sensor Consistency
# ═══════════════════════════════════════════════════════════════════

def panel5_multisensor():
    fig = plt.figure(figsize=FIGSIZE)

    sim = vp2.simulate_postural_sway(duration_s=30.0, seed=7)
    cop = sim["cop"]
    t = sim["t"]
    dt = t[1] - t[0]

    accel = np.gradient(np.gradient(cop, dt), dt)
    accel_noisy = accel + np.random.default_rng(1).normal(
        0, 1e-3 * 9.81, len(accel))
    b_hp, a_hp = butter(2, 0.05 / (0.5 / dt), btype='high')
    vel = filtfilt(b_hp, a_hp, np.cumsum(accel_noisy) * dt)
    pos = filtfilt(b_hp, a_hp, np.cumsum(vel) * dt)

    theta = sim["theta"]
    emg_raw = 1.0 + 50.0 * theta
    b_lp2, a_lp2 = butter(2, 5.0 / (0.5 / dt), btype='low')
    emg = filtfilt(b_lp2, a_lp2, emg_raw)

    insole = np.round(cop * 2000) / 2000

    ra_cop, tr_cop = vp2.decompose_rambling_trembling(cop, t)
    ra_imu, tr_imu = vp2.decompose_rambling_trembling(pos, t)
    ra_emg, tr_emg = vp2.decompose_rambling_trembling(emg, t)
    ra_ins, tr_ins = vp2.decompose_rambling_trembling(insole, t)

    def calibrate(x, ref):
        return x * (np.std(ref) / np.std(x)) if np.std(x) > 0 else x

    ra_imu_c = calibrate(ra_imu, ra_cop)
    ra_emg_c = calibrate(ra_emg, ra_cop)
    ra_ins_c = calibrate(ra_ins, ra_cop)

    # (A) 3D: sensor × frequency × PSD
    sensors = ['CoP', 'IMU', 'EMG', 'insole']
    sensor_signals = [cop, pos, emg, insole]
    psds = []
    f_axis = None
    for sig in sensor_signals:
        f, P = welch(sig, fs=1.0/dt, nperseg=int(5.0/dt))
        if f_axis is None:
            f_axis = f
        psds.append(np.log10(P + 1e-20))
    psds = np.array(psds)
    mask = (f_axis > 0.05) & (f_axis < 3.0)
    ax1 = fig.add_subplot(1, 4, 1, projection='3d')
    X, Y = np.meshgrid(f_axis[mask], np.arange(4))
    ax1.plot_surface(X, Y, psds[:, mask], cmap='plasma',
                     linewidth=0, antialiased=True, alpha=0.95)
    ax1.set_xlabel('freq (Hz)', labelpad=2)
    ax1.set_yticks(range(4))
    ax1.set_yticklabels(sensors, fontsize=7)
    ax1.set_zlabel('log PSD', labelpad=2)
    ax1.view_init(elev=24, azim=-60)
    ax1.set_title('(A)', loc='left')

    # (B) Cross-sensor correlations (bars)
    def corr(a, b):
        return abs(float(np.corrcoef(a - np.mean(a), b - np.mean(b))[0, 1]))
    corrs = {
        'CoP-IMU': corr(ra_cop, ra_imu_c),
        'CoP-EMG': corr(ra_cop, ra_emg_c),
        'CoP-insole': corr(ra_cop, ra_ins_c),
        'insole (Tr)': corr(tr_cop, calibrate(tr_ins, tr_cop))
    }
    ax2 = fig.add_subplot(1, 4, 2)
    ax2.bar(list(corrs.keys()), list(corrs.values()),
            color=[BLUE, ORANGE, GREEN, PURPLE], edgecolor='white')
    ax2.axhline(0.8, color='gray', ls='--', lw=0.8)
    ax2.set_ylim(0, 1.05)
    ax2.set_ylabel('|r|')
    plt.setp(ax2.get_xticklabels(), rotation=20, ha='right')
    ax2.set_title('(B)', loc='left')

    # (C) Scatter: CoP vs insole rambling (calibrated)
    ax3 = fig.add_subplot(1, 4, 3)
    ax3.scatter(ra_cop * 1000, ra_ins_c * 1000, s=2, color=GREEN,
                alpha=0.4)
    lim = [min(ra_cop.min(), ra_ins_c.min()) * 1000,
           max(ra_cop.max(), ra_ins_c.max()) * 1000]
    ax3.plot(lim, lim, 'k--', lw=0.7)
    ax3.set_xlabel('CoP rambling (mm)')
    ax3.set_ylabel('insole rambling (mm)')
    ax3.set_title('(C)', loc='left')

    # (D) Cohen's d curve: effect vs sample size
    from scipy import stats
    # Use the real Cohen's d from validation
    ctrl_tr_all, pd_tr_all = [], []
    for seed in range(10):
        sim_c = vp2.simulate_postural_sway(duration_s=30.0, seed=seed,
                                            parkinson_factor=0.0)
        sim_p = vp2.simulate_postural_sway(duration_s=30.0, seed=seed,
                                            parkinson_factor=0.7)
        if not sim_c["fell"]:
            _, tr = vp2.decompose_rambling_trembling(sim_c["cop"], sim_c["t"])
            ctrl_tr_all.append(np.std(tr))
        if not sim_p["fell"]:
            _, tr = vp2.decompose_rambling_trembling(sim_p["cop"], sim_p["t"])
            pd_tr_all.append(np.std(tr))
    d = ((np.mean(pd_tr_all) - np.mean(ctrl_tr_all)) /
         np.sqrt((np.var(ctrl_tr_all) + np.var(pd_tr_all)) / 2))
    # Power curve: n_required as function of desired power
    powers = np.linspace(0.5, 0.99, 30)
    z_beta = stats.norm.ppf(powers)
    z_alpha = stats.norm.ppf(0.975)
    n_req = 2 * ((z_alpha + z_beta) ** 2) / (d ** 2)
    ax4 = fig.add_subplot(1, 4, 4)
    ax4.plot(powers, n_req, color=RED, lw=1.8)
    ax4.axvline(0.8, color='gray', ls='--', lw=0.8)
    ax4.set_xlabel('statistical power')
    ax4.set_ylabel('required n per group')
    ax4.set_yscale('log')
    ax4.set_title('(D)', loc='left')

    _finish(fig, os.path.join(OUT_DIR, 'panel5_multisensor.png'))


def main():
    print('Generating Paper 2 panels ...')
    panel1_decomposition()
    panel2_spectral()
    panel3_dual_task_aging()
    panel4_pathology()
    panel5_multisensor()
    print('Done.')


if __name__ == '__main__':
    main()
