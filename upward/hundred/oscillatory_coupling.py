"""
Script 3: Multi-Scale Oscillatory Coupling Analysis (FIXED)
Demonstrates coupling across biochemical, neural, mechanical scales
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import signal, fft
from matplotlib.gridspec import GridSpec
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend

plt.style.use('seaborn-v0_8-paper')
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 10
plt.rcParams['font.family'] = 'serif'


if __name__ == "__main__":
    # Time vector for 100m race
    t = np.linspace(0, 10, 10000)  # 10 seconds, high resolution
    dt = t[1] - t[0]

    # ============================================================================
    # SCALE 1: Biochemical Oscillations (ATP-PCr system)
    # ============================================================================
    atp_baseline = 1.0
    atp_decay_rate = 0.08
    atp_oscillation_freq = 0.1
    atp_oscillation_amp = 0.05

    ATP_PCr = atp_baseline * np.exp(-atp_decay_rate * t) * (
        1 + atp_oscillation_amp * np.sin(2 * np.pi * atp_oscillation_freq * t)
    )

    glycolytic_onset = 6.0
    glycolytic_rate = 0.15
    Glycolytic = 0.3 * (1 - np.exp(-glycolytic_rate * np.maximum(0, t - glycolytic_onset)))

    Energy_total = ATP_PCr + Glycolytic

    # ============================================================================
    # SCALE 2: Neural Oscillations (Motor unit firing)
    # ============================================================================
    neural_freq = 45
    neural_decay = 0.05
    neural_noise = 0.1

    Neural_firing = np.exp(-neural_decay * t) * (
        np.sin(2 * np.pi * neural_freq * t) +
        neural_noise * np.random.randn(len(t))
    )

    # ============================================================================
    # SCALE 3: Mechanical Oscillations (Stride cycle)
    # ============================================================================
    stride_freq = 4.5
    stride_length = 2.77
    ground_contact_ratio = 0.36

    Stride_cycle = signal.square(2 * np.pi * stride_freq * t, duty=ground_contact_ratio)

    vertical_osc_amp = 0.08
    Vertical_oscillation = vertical_osc_amp * np.sin(2 * np.pi * stride_freq * t)

    base_velocity = 12.0
    velocity_modulation = 0.5
    Horizontal_velocity = base_velocity + velocity_modulation * np.sin(2 * np.pi * stride_freq * t)

    # ============================================================================
    # SCALE 4: Biomechanical Oscillations (Muscle contraction)
    # ============================================================================
    muscle_freq = 25
    muscle_decay = 0.03

    Muscle_contraction = np.exp(-muscle_decay * t) * np.sin(2 * np.pi * muscle_freq * t)

    # ============================================================================
    # COUPLED SYSTEM: Overall Performance
    # ============================================================================
    Performance = (
        (Energy_total / np.max(Energy_total)) *
        (np.abs(Neural_firing) / np.max(np.abs(Neural_firing))) *
        ((Stride_cycle + 1) / 2) *
        (np.abs(Muscle_contraction) / np.max(np.abs(Muscle_contraction)))
    )

    # FIXED: Integrate to get distance with matching dimensions
    distance_increments = Performance[:-1] * Horizontal_velocity[:-1] * dt
    distance = np.concatenate([[0], np.cumsum(distance_increments)])

    # Ensure same length (trim if needed)
    if len(distance) > len(t):
        distance = distance[:len(t)]
    elif len(distance) < len(t):
        distance = np.concatenate([distance, [distance[-1]]])

    # ============================================================================
    # CREATE FIGURE
    # ============================================================================
    fig = plt.figure(figsize=(18, 14))
    gs = GridSpec(5, 3, figure=fig, hspace=0.4, wspace=0.35)

    colors = {
        'biochem': '#e74c3c',
        'neural': '#3498db',
        'mechanical': '#2ecc71',
        'biomech': '#f39c12',
        'coupled': '#9b59b6'
    }

    # ============================================================================
    # PANEL A: Biochemical Scale
    # ============================================================================
    ax1 = fig.add_subplot(gs[0, 0])

    ax1.plot(t, ATP_PCr, linewidth=2.5, color=colors['biochem'],
            label='ATP-PCr', alpha=0.8)
    ax1.plot(t, Glycolytic, linewidth=2.5, color='orange',
            label='Glycolytic', alpha=0.8, linestyle='--')
    ax1.plot(t, Energy_total, linewidth=3, color='darkred',
            label='Total Energy', alpha=0.9)

    ax1.axvline(x=glycolytic_onset, color='gray', linestyle=':',
            linewidth=2, alpha=0.5, label='Glycolytic Onset')

    ax1.set_xlabel('Time (s)', fontweight='bold')
    ax1.set_ylabel('Normalized Energy', fontweight='bold')
    ax1.set_title('A. Biochemical Scale (0.1-10s)', fontweight='bold', loc='left')
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(0, 10)

    # ============================================================================
    # PANEL B: Neural Scale
    # ============================================================================
    ax2 = fig.add_subplot(gs[0, 1])

    t_zoom = t[(t >= 5) & (t <= 5.5)]
    neural_zoom = Neural_firing[(t >= 5) & (t <= 5.5)]

    ax2.plot(t_zoom, neural_zoom, linewidth=1.5, color=colors['neural'], alpha=0.8)
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5, alpha=0.5)

    ax2.set_xlabel('Time (s)', fontweight='bold')
    ax2.set_ylabel('Neural Activity (a.u.)', fontweight='bold')
    ax2.set_title('B. Neural Scale (40-50 Hz firing)', fontweight='bold', loc='left')
    ax2.grid(True, alpha=0.3)
    ax2.text(0.05, 0.95, f'Frequency: {neural_freq} Hz\nZoom: 5.0-5.5s',
            transform=ax2.transAxes, fontsize=9, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5))

    # ============================================================================
    # PANEL C: Mechanical Scale
    # ============================================================================
    ax3 = fig.add_subplot(gs[0, 2])

    t_stride = t[(t >= 4) & (t <= 5.2)]
    stride_zoom = Stride_cycle[(t >= 4) & (t <= 5.2)]
    vertical_zoom = Vertical_oscillation[(t >= 4) & (t <= 5.2)]

    ax3_twin = ax3.twinx()

    ax3.fill_between(t_stride, 0, stride_zoom, where=(stride_zoom > 0),
                    alpha=0.3, color=colors['mechanical'], label='Ground Contact')
    ax3_twin.plot(t_stride, vertical_zoom, linewidth=2.5,
                color='darkgreen', label='Vertical Oscillation', alpha=0.8)

    ax3.set_xlabel('Time (s)', fontweight='bold')
    ax3.set_ylabel('Ground Contact', fontweight='bold', color=colors['mechanical'])
    ax3_twin.set_ylabel('Vertical Displacement (m)', fontweight='bold', color='darkgreen')
    ax3.set_title('C. Mechanical Scale (4.5 Hz stride)', fontweight='bold', loc='left')
    ax3.grid(True, alpha=0.3)
    ax3.set_ylim(-1.5, 1.5)

    lines1, labels1 = ax3.get_legend_handles_labels()
    lines2, labels2 = ax3_twin.get_legend_handles_labels()
    ax3.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=8)

    # ============================================================================
    # PANEL D: Biomechanical Scale
    # ============================================================================
    ax4 = fig.add_subplot(gs[1, 0])

    t_muscle = t[(t >= 5) & (t <= 5.2)]
    muscle_zoom = Muscle_contraction[(t >= 5) & (t <= 5.2)]

    ax4.plot(t_muscle, muscle_zoom, linewidth=2, color=colors['biomech'], alpha=0.8)
    ax4.axhline(y=0, color='black', linestyle='-', linewidth=0.5, alpha=0.5)

    ax4.set_xlabel('Time (s)', fontweight='bold')
    ax4.set_ylabel('Muscle Force (a.u.)', fontweight='bold')
    ax4.set_title('D. Biomechanical Scale (25 Hz contraction)', fontweight='bold', loc='left')
    ax4.grid(True, alpha=0.3)
    ax4.text(0.05, 0.95, f'Frequency: {muscle_freq} Hz\nZoom: 5.0-5.2s',
            transform=ax4.transAxes, fontsize=9, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # ============================================================================
    # PANEL E: Coupled System Performance
    # ============================================================================
    ax5 = fig.add_subplot(gs[1, 1])

    ax5.plot(t, Performance, linewidth=3, color=colors['coupled'], alpha=0.8)
    ax5.fill_between(t, 0, Performance, alpha=0.3, color=colors['coupled'])

    ax5.set_xlabel('Time (s)', fontweight='bold')
    ax5.set_ylabel('Coupled Performance', fontweight='bold')
    ax5.set_title('E. Coupled System Output', fontweight='bold', loc='left')
    ax5.grid(True, alpha=0.3)
    ax5.set_xlim(0, 10)

    optimal_start = 4.0
    optimal_end = 8.0
    ax5.axvspan(optimal_start, optimal_end, alpha=0.2, color='yellow',
            label='Optimal Coupling Zone')
    ax5.legend(loc='upper right')

    # ============================================================================
    # PANEL F: Velocity Profile
    # ============================================================================
    ax6 = fig.add_subplot(gs[1, 2])

    ax6.plot(t, Horizontal_velocity, linewidth=3, color='darkblue', alpha=0.8)
    ax6.axhline(y=base_velocity, color='red', linestyle='--',
            linewidth=2, alpha=0.5, label=f'Mean: {base_velocity} m/s')

    ax6.set_xlabel('Time (s)', fontweight='bold')
    ax6.set_ylabel('Velocity (m/s)', fontweight='bold')
    ax6.set_title('F. Horizontal Velocity Profile', fontweight='bold', loc='left')
    ax6.grid(True, alpha=0.3)
    ax6.legend(loc='lower right')
    ax6.set_xlim(0, 10)
    ax6.set_ylim(10, 13)

    # ============================================================================
    # PANEL G: Frequency Spectrum Analysis
    # ============================================================================
    ax7 = fig.add_subplot(gs[2, :2])

    sampling_rate = len(t) / (t[-1] - t[0])

    def compute_spectrum(signal_data):
        fft_vals = fft.fft(signal_data)
        fft_freq = fft.fftfreq(len(signal_data), 1/sampling_rate)
        pos_mask = fft_freq > 0
        return fft_freq[pos_mask], np.abs(fft_vals[pos_mask])

    freq_energy, spec_energy = compute_spectrum(Energy_total)
    freq_neural, spec_neural = compute_spectrum(Neural_firing)
    freq_stride, spec_stride = compute_spectrum(Stride_cycle)
    freq_muscle, spec_muscle = compute_spectrum(Muscle_contraction)

    ax7.semilogy(freq_energy, spec_energy, linewidth=2,
                color=colors['biochem'], label='Biochemical (0.1 Hz)', alpha=0.7)
    ax7.semilogy(freq_stride, spec_stride, linewidth=2,
                color=colors['mechanical'], label='Mechanical (4.5 Hz)', alpha=0.7)
    ax7.semilogy(freq_muscle, spec_muscle, linewidth=2,
                color=colors['biomech'], label='Biomechanical (25 Hz)', alpha=0.7)
    ax7.semilogy(freq_neural, spec_neural, linewidth=2,
                color=colors['neural'], label='Neural (45 Hz)', alpha=0.7)

    for freq, label, color in [(0.1, 'Biochem', colors['biochem']),
                            (4.5, 'Stride', colors['mechanical']),
                            (25, 'Muscle', colors['biomech']),
                            (45, 'Neural', colors['neural'])]:
        ax7.axvline(x=freq, color=color, linestyle=':', linewidth=2, alpha=0.5)

    ax7.set_xlabel('Frequency (Hz)', fontweight='bold')
    ax7.set_ylabel('Power Spectrum (log scale)', fontweight='bold')
    ax7.set_title('G. Multi-Scale Frequency Spectrum', fontweight='bold', loc='left')
    ax7.legend(loc='upper right', ncol=2)
    ax7.grid(True, alpha=0.3, which='both')
    ax7.set_xlim(0.01, 100)

    # ============================================================================
    # PANEL H: Phase Coupling Analysis
    # ============================================================================
    ax8 = fig.add_subplot(gs[2, 2])

    t_phase = t[(t >= 5) & (t <= 6)]
    stride_phase = Stride_cycle[(t >= 5) & (t <= 6)]
    muscle_phase = Muscle_contraction[(t >= 5) & (t <= 6)]

    stride_norm = (stride_phase - np.min(stride_phase)) / (np.max(stride_phase) - np.min(stride_phase))
    muscle_norm = (muscle_phase - np.min(muscle_phase)) / (np.max(muscle_phase) - np.min(muscle_phase))

    ax8.plot(t_phase, stride_norm, linewidth=3,
            color=colors['mechanical'], label='Stride (4.5 Hz)', alpha=0.8)
    ax8.plot(t_phase, muscle_norm, linewidth=2,
            color=colors['biomech'], label='Muscle (25 Hz)', alpha=0.6)

    ax8.set_xlabel('Time (s)', fontweight='bold')
    ax8.set_ylabel('Normalized Amplitude', fontweight='bold')
    ax8.set_title('H. Phase Coupling (5:1 ratio)', fontweight='bold', loc='left')
    ax8.legend(loc='upper right')
    ax8.grid(True, alpha=0.3)

    # ============================================================================
    # PANEL I: Distance-Time Relationship (FIXED)
    # ============================================================================
    ax9 = fig.add_subplot(gs[3, :2])

    ax9.plot(t, distance, linewidth=3, color=colors['coupled'], alpha=0.8)

    # Mark 100m finish
    finish_idx = np.argmin(np.abs(distance - 100))
    finish_time = t[finish_idx]

    ax9.axhline(y=100, color='red', linestyle='--', linewidth=2, alpha=0.5)
    ax9.axvline(x=finish_time, color='red', linestyle='--', linewidth=2, alpha=0.5)
    ax9.plot(finish_time, 100, 'ro', markersize=15, label=f'Finish: {finish_time:.2f}s')

    for dist in [20, 40, 60, 80]:
        idx = np.argmin(np.abs(distance - dist))
        if idx < len(t):
            ax9.plot(t[idx], dist, 'ko', markersize=8, alpha=0.5)
            ax9.text(t[idx], dist-3, f'{t[idx]:.2f}s', ha='center', fontsize=8)

    ax9.set_xlabel('Time (s)', fontweight='bold')
    ax9.set_ylabel('Distance (m)', fontweight='bold')
    ax9.set_title('I. Distance-Time Profile', fontweight='bold', loc='left')
    ax9.legend(loc='lower right')
    ax9.grid(True, alpha=0.3)
    ax9.set_xlim(0, 10)
    ax9.set_ylim(0, 110)

    # ============================================================================
    # PANEL J: Coupling Efficiency Over Time
    # ============================================================================
    ax10 = fig.add_subplot(gs[3, 2])

    window_size = 100
    coupling_efficiency = np.zeros(len(t) - window_size)

    for i in range(len(coupling_efficiency)):
        window = slice(i, i + window_size)
        corr_energy_stride = np.corrcoef(
            Energy_total[window] / np.max(Energy_total[window]),
            (Stride_cycle[window] + 1) / 2
        )[0, 1]
        corr_neural_muscle = np.corrcoef(
            Neural_firing[window] / np.max(np.abs(Neural_firing[window])),
            Muscle_contraction[window] / np.max(np.abs(Muscle_contraction[window]))
        )[0, 1]

        coupling_efficiency[i] = (abs(corr_energy_stride) + abs(corr_neural_muscle)) / 2

    t_coupling = t[window_size//2:-window_size//2 + 1][:len(coupling_efficiency)]

    ax10.plot(t_coupling, coupling_efficiency, linewidth=3,
            color=colors['coupled'], alpha=0.8)
    ax10.fill_between(t_coupling, 0, coupling_efficiency,
                    alpha=0.3, color=colors['coupled'])

    ax10.axvspan(optimal_start, optimal_end, alpha=0.2, color='yellow')

    ax10.set_xlabel('Time (s)', fontweight='bold')
    ax10.set_ylabel('Coupling Efficiency', fontweight='bold')
    ax10.set_title('J. Oscillatory Coupling Efficiency', fontweight='bold', loc='left')
    ax10.grid(True, alpha=0.3)
    ax10.set_xlim(0, 10)
    ax10.set_ylim(0, 1)

    # ============================================================================
    # PANEL K: Scale Hierarchy Diagram
    # ============================================================================
    ax11 = fig.add_subplot(gs[4, :])
    ax11.axis('off')

    scales = [
        ('Biochemical\n(ATP-PCr)', 0.1, 10, colors['biochem']),
        ('Biomechanical\n(Muscle)', 0.01, 1, colors['biomech']),
        ('Mechanical\n(Stride)', 0.1, 1, colors['mechanical']),
        ('Neural\n(Motor Units)', 0.01, 0.1, colors['neural'])
    ]

    y_positions = [0.7, 0.5, 0.3, 0.1]
    x_start = 0.1

    for i, (name, t_min, t_max, color) in enumerate(scales):
        y = y_positions[i]

        width = 0.15
        height = 0.12
        rect = plt.Rectangle((x_start, y - height/2), width, height,
                            facecolor=color, alpha=0.3, edgecolor=color,
                            linewidth=3)
        ax11.add_patch(rect)

        ax11.text(x_start + width/2, y, name, ha='center', va='center',
                fontsize=11, fontweight='bold')

        ax11.text(x_start + width + 0.02, y, f'{t_min}-{t_max}s',
                ha='left', va='center', fontsize=9)

        if 'Neural' in name:
            freq_text = '40-50 Hz'
        elif 'Muscle' in name:
            freq_text = '~25 Hz'
        elif 'Stride' in name:
            freq_text = '~4.5 Hz'
        else:
            freq_text = '~0.1 Hz'

        ax11.text(x_start + width + 0.15, y, freq_text,
                ha='left', va='center', fontsize=9, style='italic',
                color=color)

    for i in range(len(y_positions) - 1):
        y1 = y_positions[i] - 0.06
        y2 = y_positions[i+1] + 0.06
        ax11.annotate('', xy=(x_start + 0.075, y2), xytext=(x_start + 0.075, y1),
                    arrowprops=dict(arrowstyle='<->', lw=2, color='black', alpha=0.5))

    perf_x = 0.6
    perf_y = 0.4
    perf_width = 0.25
    perf_height = 0.3
    rect_perf = plt.Rectangle((perf_x, perf_y - perf_height/2), perf_width, perf_height,
                            facecolor=colors['coupled'], alpha=0.3,
                            edgecolor=colors['coupled'], linewidth=4)
    ax11.add_patch(rect_perf)
    ax11.text(perf_x + perf_width/2, perf_y, 'COUPLED\nPERFORMANCE\n\n9.57±0.03s',
            ha='center', va='center', fontsize=13, fontweight='bold')

    for i, y in enumerate(y_positions):
        ax11.annotate('', xy=(perf_x, perf_y), xytext=(x_start + 0.15, y),
                    arrowprops=dict(arrowstyle='->', lw=2,
                                color=scales[i][3], alpha=0.6))

    ax11.set_xlim(0, 1)
    ax11.set_ylim(0, 1)
    ax11.set_title('K. Multi-Scale Oscillatory Coupling Architecture',
                fontweight='bold', loc='left', fontsize=12, pad=10)

    # ============================================================================
    # Overall title
    # ============================================================================
    fig.suptitle('Figure 3: Multi-Scale Oscillatory Coupling Analysis\n' +
                'Integrated Biochemical, Neural, Mechanical, and Biomechanical Systems',
                fontsize=14, fontweight='bold', y=0.998)

    plt.savefig('figure3_oscillatory_coupling.png', dpi=300, bbox_inches='tight')
    plt.savefig('figure3_oscillatory_coupling.pdf', dpi=300, bbox_inches='tight')
    print("✓ Figure 3 saved: Oscillatory Coupling Analysis")

    # plt.show()  # Commented out for non-interactive environments
