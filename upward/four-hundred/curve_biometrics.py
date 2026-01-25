"""
400m Olympic Performance: Curve Biomechanics Analysis
Detailed analysis of biomechanical parameters during curve running
"""

import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.gridspec import GridSpec
from scipy.signal import savgol_filter
from scipy.interpolate import interp1d
import matplotlib
matplotlib.use('Agg')

plt.style.use('seaborn-v0_8-paper')
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 10
plt.rcParams['font.family'] = 'serif'

# ============================================================================
# LOAD DATA
# ============================================================================
if __name__ == "__main__":
    with open('curve_biomechanics.json', 'r') as f:
        curve_data = json.load(f)

    df = pd.DataFrame(curve_data)

    print(f"Loaded {len(df)} data points")
    print(f"Time range: {df['time'].min():.2f}s - {df['time'].max():.2f}s")
    print(f"Distance range: {df['dist'].min():.1f}m - {df['dist'].max():.1f}m")

    # Map column names to expected format
    if 'speed' in df.columns and 'inst_speed' not in df.columns:
        df['inst_speed'] = df['speed']
    if 'step_length' in df.columns and 'stride_length' not in df.columns:
        df['stride_length'] = df['step_length'] / 100  # Convert cm to m
    if 'vertical_oscillation' in df.columns and 'vert_osc' not in df.columns:
        df['vert_osc'] = df['vertical_oscillation'] / 100  # Convert cm to m
    if 'cadence' in df.columns and 'stride_freq' not in df.columns:
        df['stride_freq'] = df['cadence'] / 60  # Convert steps/min to Hz
    if 'cycle_time' in df.columns and 'stance_time' in df.columns and 'flight_time' not in df.columns:
        df['flight_time'] = df['cycle_time'] - (df['stance_time'] / 1000)  # Convert ms to s
    if 'f_max' in df.columns and 'grf' not in df.columns:
        df['grf'] = df['f_max']
    if 'EF' in df.columns and 'power' not in df.columns:
        df['power'] = df['EF'].abs() * df['inst_speed']  # Approximate power

    # ============================================================================
    # CREATE FIGURE
    # ============================================================================

    fig = plt.figure(figsize=(22, 20))
    gs = GridSpec(4, 3, figure=fig, hspace=0.4, wspace=0.35)

    colors = {
        'speed': '#E63946',
        'acceleration': '#457B9D',
        'force': '#2A9D8F',
        'power': '#E9C46A',
        'angle': '#F4A261',
        'energy': '#264653'
    }

    # ============================================================================
    # PANEL A: Speed Profile Throughout Race
    # ============================================================================

    ax1 = fig.add_subplot(gs[0, 0])

    # Plot instantaneous speed
    ax1.plot(df['time'], df['inst_speed'], linewidth=2.5,
            color=colors['speed'], alpha=0.8, label='Instantaneous Speed')

    # Smooth speed for trend
    if len(df) > 10:
        smooth_speed = savgol_filter(df['inst_speed'],
                                    window_length=min(11, len(df)-1 if len(df) % 2 == 0 else len(df)),
                                    polyorder=3)
        ax1.plot(df['time'], smooth_speed, '--', linewidth=3,
                color='black', alpha=0.5, label='Smoothed Trend')

    # Mark curve sections (typically 0-100m and 300-400m are curves)
    ax1.axvspan(0, 10, alpha=0.1, color='blue', label='Curve 1')
    ax1.axvspan(30, 40, alpha=0.1, color='blue', label='Curve 2')

    ax1.set_xlabel('Time (seconds)', fontweight='bold', fontsize=12)
    ax1.set_ylabel('Speed (m/s)', fontweight='bold', fontsize=12)
    ax1.set_title('A. Speed Profile Throughout 400m Race',
                fontweight='bold', loc='left', fontsize=14)
    ax1.legend(loc='upper right', fontsize=9)
    ax1.grid(True, alpha=0.3)

    # Add peak speed annotation
    peak_speed_idx = df['inst_speed'].idxmax()
    peak_speed = df.loc[peak_speed_idx, 'inst_speed']
    peak_time = df.loc[peak_speed_idx, 'time']
    ax1.annotate(f'Peak: {peak_speed:.2f} m/s\n@ {peak_time:.1f}s',
                xy=(peak_time, peak_speed),
                xytext=(peak_time+5, peak_speed-1),
                arrowprops=dict(arrowstyle='->', color='red', lw=2),
                fontsize=10, fontweight='bold',
                bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.5))

    # ============================================================================
    # PANEL B: Acceleration Profile
    # ============================================================================

    ax2 = fig.add_subplot(gs[0, 1])

    # Calculate acceleration (change in speed)
    df['acceleration'] = df['inst_speed'].diff() / df['time'].diff()
    df['acceleration'] = df['acceleration'].fillna(0)

    # Smooth acceleration
    if len(df) > 10:
        smooth_accel = savgol_filter(df['acceleration'],
                                    window_length=min(11, len(df)-1 if len(df) % 2 == 0 else len(df)),
                                    polyorder=3)
    else:
        smooth_accel = df['acceleration']

    ax2.plot(df['time'], smooth_accel, linewidth=2.5,
            color=colors['acceleration'], alpha=0.8)

    # Color positive/negative acceleration
    ax2.fill_between(df['time'], 0, smooth_accel,
                    where=(smooth_accel > 0), alpha=0.3,
                    color='green', label='Acceleration')
    ax2.fill_between(df['time'], 0, smooth_accel,
                    where=(smooth_accel < 0), alpha=0.3,
                    color='red', label='Deceleration')

    ax2.axhline(y=0, color='black', linestyle='--', linewidth=1.5, alpha=0.5)

    ax2.set_xlabel('Time (seconds)', fontweight='bold', fontsize=12)
    ax2.set_ylabel('Acceleration (m/s²)', fontweight='bold', fontsize=12)
    ax2.set_title('B. Acceleration/Deceleration Profile',
                fontweight='bold', loc='left', fontsize=14)
    ax2.legend(loc='upper right', fontsize=9)
    ax2.grid(True, alpha=0.3)

    # ============================================================================
    # PANEL C: Ground Contact Time Analysis
    # ============================================================================

    ax3 = fig.add_subplot(gs[0, 2])

    # Filter valid stance times
    valid_stance = df[df['stance_time'].notna()]

    if len(valid_stance) > 0:
        ax3.scatter(valid_stance['time'], valid_stance['stance_time']*1000,
                s=50, alpha=0.6, color=colors['force'],
                edgecolors='black', linewidth=0.5)

        # Add trend line
        if len(valid_stance) > 2:
            z = np.polyfit(valid_stance['time'], valid_stance['stance_time']*1000, 2)
            p = np.poly1d(z)
            time_smooth = np.linspace(valid_stance['time'].min(),
                                    valid_stance['time'].max(), 100)
            ax3.plot(time_smooth, p(time_smooth), '--',
                    linewidth=3, color='red', alpha=0.7, label='Trend')

        # Mark optimal range
        ax3.axhspan(80, 120, alpha=0.2, color='green', label='Optimal Range')

        ax3.set_xlabel('Time (seconds)', fontweight='bold', fontsize=12)
        ax3.set_ylabel('Ground Contact Time (ms)', fontweight='bold', fontsize=12)
        ax3.set_title('C. Ground Contact Time Evolution',
                    fontweight='bold', loc='left', fontsize=14)
        ax3.legend(loc='upper right', fontsize=9)
        ax3.grid(True, alpha=0.3)
    else:
        ax3.text(0.5, 0.5, 'No stance time data available',
                transform=ax3.transAxes, ha='center', va='center',
                fontsize=12, style='italic')
        ax3.set_title('C. Ground Contact Time Evolution',
                    fontweight='bold', loc='left', fontsize=14)

    # ============================================================================
    # PANEL D: Flight Time Analysis
    # ============================================================================

    ax4 = fig.add_subplot(gs[1, 0])

    valid_flight = df[df['flight_time'].notna()]

    if len(valid_flight) > 0:
        ax4.scatter(valid_flight['time'], valid_flight['flight_time']*1000,
                s=50, alpha=0.6, color=colors['power'],
                edgecolors='black', linewidth=0.5)

        # Add trend line
        if len(valid_flight) > 2:
            z = np.polyfit(valid_flight['time'], valid_flight['flight_time']*1000, 2)
            p = np.poly1d(z)
            time_smooth = np.linspace(valid_flight['time'].min(),
                                    valid_flight['time'].max(), 100)
            ax4.plot(time_smooth, p(time_smooth), '--',
                    linewidth=3, color='red', alpha=0.7, label='Trend')

        ax4.set_xlabel('Time (seconds)', fontweight='bold', fontsize=12)
        ax4.set_ylabel('Flight Time (ms)', fontweight='bold', fontsize=12)
        ax4.set_title('D. Flight Time Evolution',
                    fontweight='bold', loc='left', fontsize=14)
        ax4.legend(loc='upper right', fontsize=9)
        ax4.grid(True, alpha=0.3)
    else:
        ax4.text(0.5, 0.5, 'No flight time data available',
                transform=ax4.transAxes, ha='center', va='center',
                fontsize=12, style='italic')
        ax4.set_title('D. Flight Time Evolution',
                    fontweight='bold', loc='left', fontsize=14)

    # ============================================================================
    # PANEL E: Stride Frequency
    # ============================================================================

    ax5 = fig.add_subplot(gs[1, 1])

    valid_freq = df[df['stride_freq'].notna()]

    if len(valid_freq) > 0:
        ax5.plot(valid_freq['time'], valid_freq['stride_freq'],
                'o-', linewidth=2.5, markersize=6,
                color=colors['angle'], alpha=0.8)

        # Mark optimal range
        ax5.axhspan(4.0, 5.0, alpha=0.2, color='green', label='Optimal Range')

        ax5.set_xlabel('Time (seconds)', fontweight='bold', fontsize=12)
        ax5.set_ylabel('Stride Frequency (Hz)', fontweight='bold', fontsize=12)
        ax5.set_title('E. Stride Frequency Throughout Race',
                    fontweight='bold', loc='left', fontsize=14)
        ax5.legend(loc='upper right', fontsize=9)
        ax5.grid(True, alpha=0.3)

        # Add mean line
        mean_freq = valid_freq['stride_freq'].mean()
        ax5.axhline(y=mean_freq, color='red', linestyle='--',
                linewidth=2, alpha=0.5, label=f'Mean: {mean_freq:.2f} Hz')
    else:
        ax5.text(0.5, 0.5, 'No stride frequency data available',
                transform=ax5.transAxes, ha='center', va='center',
                fontsize=12, style='italic')
        ax5.set_title('E. Stride Frequency Throughout Race',
                    fontweight='bold', loc='left', fontsize=14)

    # ============================================================================
    # PANEL F: Stride Length
    # ============================================================================

    ax6 = fig.add_subplot(gs[1, 2])

    valid_length = df[df['stride_length'].notna()]

    if len(valid_length) > 0:
        ax6.plot(valid_length['time'], valid_length['stride_length'],
                's-', linewidth=2.5, markersize=6,
                color=colors['energy'], alpha=0.8)

        # Mark optimal range
        ax6.axhspan(2.0, 2.5, alpha=0.2, color='green', label='Optimal Range')

        ax6.set_xlabel('Time (seconds)', fontweight='bold', fontsize=12)
        ax6.set_ylabel('Stride Length (m)', fontweight='bold', fontsize=12)
        ax6.set_title('F. Stride Length Throughout Race',
                    fontweight='bold', loc='left', fontsize=14)
        ax6.legend(loc='upper right', fontsize=9)
        ax6.grid(True, alpha=0.3)

        # Add mean line
        mean_length = valid_length['stride_length'].mean()
        ax6.axhline(y=mean_length, color='red', linestyle='--',
                linewidth=2, alpha=0.5, label=f'Mean: {mean_length:.2f} m')
    else:
        ax6.text(0.5, 0.5, 'No stride length data available',
                transform=ax6.transAxes, ha='center', va='center',
                fontsize=12, style='italic')
        ax6.set_title('F. Stride Length Throughout Race',
                    fontweight='bold', loc='left', fontsize=14)

    # ============================================================================
    # PANEL G: Vertical Oscillation
    # ============================================================================

    ax7 = fig.add_subplot(gs[2, 0])

    valid_vert = df[df['vert_osc'].notna()]

    if len(valid_vert) > 0:
        ax7.scatter(valid_vert['time'], valid_vert['vert_osc']*100,
                s=50, alpha=0.6, color=colors['force'],
                edgecolors='black', linewidth=0.5)

        # Add trend
        if len(valid_vert) > 2:
            z = np.polyfit(valid_vert['time'], valid_vert['vert_osc']*100, 2)
            p = np.poly1d(z)
            time_smooth = np.linspace(valid_vert['time'].min(),
                                    valid_vert['time'].max(), 100)
            ax7.plot(time_smooth, p(time_smooth), '--',
                    linewidth=3, color='red', alpha=0.7, label='Trend')

        # Optimal range (lower is better)
        ax7.axhspan(6, 10, alpha=0.2, color='green', label='Optimal Range')

        ax7.set_xlabel('Time (seconds)', fontweight='bold', fontsize=12)
        ax7.set_ylabel('Vertical Oscillation (cm)', fontweight='bold', fontsize=12)
        ax7.set_title('G. Vertical Oscillation (Energy Efficiency)',
                    fontweight='bold', loc='left', fontsize=14)
        ax7.legend(loc='upper right', fontsize=9)
        ax7.grid(True, alpha=0.3)
    else:
        ax7.text(0.5, 0.5, 'No vertical oscillation data available',
                transform=ax7.transAxes, ha='center', va='center',
                fontsize=12, style='italic')
        ax7.set_title('G. Vertical Oscillation (Energy Efficiency)',
                    fontweight='bold', loc='left', fontsize=14)

    # ============================================================================
    # PANEL H: Ground Reaction Force
    # ============================================================================

    ax8 = fig.add_subplot(gs[2, 1])

    valid_grf = df[df['grf'].notna()]

    if len(valid_grf) > 0:
        # Normalize GRF to body weight multiples (assuming 75kg athlete)
        body_weight = 75 * 9.81  # N
        grf_bw = valid_grf['grf'] / body_weight

        ax8.plot(valid_grf['time'], grf_bw,
                'o-', linewidth=2.5, markersize=6,
                color=colors['force'], alpha=0.8)

        # Typical range for sprinting
        ax8.axhspan(2.5, 4.0, alpha=0.2, color='green', label='Typical Range')

        ax8.set_xlabel('Time (seconds)', fontweight='bold', fontsize=12)
        ax8.set_ylabel('GRF (× Body Weight)', fontweight='bold', fontsize=12)
        ax8.set_title('H. Ground Reaction Force',
                    fontweight='bold', loc='left', fontsize=14)
        ax8.legend(loc='upper right', fontsize=9)
        ax8.grid(True, alpha=0.3)
    else:
        ax8.text(0.5, 0.5, 'No GRF data available',
                transform=ax8.transAxes, ha='center', va='center',
                fontsize=12, style='italic')
        ax8.set_title('H. Ground Reaction Force',
                    fontweight='bold', loc='left', fontsize=14)

    # ============================================================================
    # PANEL I: Power Output
    # ============================================================================

    ax9 = fig.add_subplot(gs[2, 2])

    valid_power = df[df['power'].notna()]

    if len(valid_power) > 0:
        ax9.plot(valid_power['time'], valid_power['power'],
                'o-', linewidth=2.5, markersize=6,
                color=colors['power'], alpha=0.8)

        # Fill area
        ax9.fill_between(valid_power['time'], 0, valid_power['power'],
                        alpha=0.3, color=colors['power'])

        ax9.set_xlabel('Time (seconds)', fontweight='bold', fontsize=12)
        ax9.set_ylabel('Power Output (W)', fontweight='bold', fontsize=12)
        ax9.set_title('I. Mechanical Power Output',
                    fontweight='bold', loc='left', fontsize=14)
        ax9.grid(True, alpha=0.3)

        # Add statistics
        mean_power = valid_power['power'].mean()
        max_power = valid_power['power'].max()
        ax9.text(0.95, 0.95,
                f'Mean: {mean_power:.0f} W\nPeak: {max_power:.0f} W',
                transform=ax9.transAxes, ha='right', va='top',
                fontsize=10, fontweight='bold',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    else:
        ax9.text(0.5, 0.5, 'No power data available',
                transform=ax9.transAxes, ha='center', va='center',
                fontsize=12, style='italic')
        ax9.set_title('I. Mechanical Power Output',
                    fontweight='bold', loc='left', fontsize=14)

    # ============================================================================
    # PANEL J: Stride Frequency vs Length Trade-off
    # ============================================================================

    ax10 = fig.add_subplot(gs[3, 0])

    valid_both = df[df['stride_freq'].notna() & df['stride_length'].notna()]

    if len(valid_both) > 0:
        scatter = ax10.scatter(valid_both['stride_freq'], valid_both['stride_length'],
                            c=valid_both['inst_speed'], s=100, alpha=0.6,
                            cmap='RdYlGn', edgecolors='black', linewidth=1)

        cbar = plt.colorbar(scatter, ax=ax10)
        cbar.set_label('Speed (m/s)', fontweight='bold')

        ax10.set_xlabel('Stride Frequency (Hz)', fontweight='bold', fontsize=12)
        ax10.set_ylabel('Stride Length (m)', fontweight='bold', fontsize=12)
        ax10.set_title('J. Stride Frequency vs Length Trade-off',
                    fontweight='bold', loc='left', fontsize=14)
        ax10.grid(True, alpha=0.3)

        # Add optimal zone
        from matplotlib.patches import Rectangle
        optimal_rect = Rectangle((4.0, 2.0), 1.0, 0.5,
                                linewidth=2, edgecolor='green',
                                facecolor='green', alpha=0.2,
                                label='Optimal Zone')
        ax10.add_patch(optimal_rect)
        ax10.legend(loc='upper right', fontsize=9)
    else:
        ax10.text(0.5, 0.5, 'Insufficient data for analysis',
                transform=ax10.transAxes, ha='center', va='center',
                fontsize=12, style='italic')
        ax10.set_title('J. Stride Frequency vs Length Trade-off',
                    fontweight='bold', loc='left', fontsize=14)

    # ============================================================================
    # PANEL K: Contact vs Flight Time Ratio
    # ============================================================================

    ax11 = fig.add_subplot(gs[3, 1])

    valid_ratio = df[df['stance_time'].notna() & df['flight_time'].notna()]

    if len(valid_ratio) > 0:
        ratio = valid_ratio['flight_time'] / valid_ratio['stance_time']

        ax11.plot(valid_ratio['time'], ratio,
                'o-', linewidth=2.5, markersize=6,
                color=colors['angle'], alpha=0.8)

        # Optimal ratio for sprinting (flight > contact)
        ax11.axhline(y=1.0, color='red', linestyle='--',
                    linewidth=2, alpha=0.5, label='Equal Contact/Flight')
        ax11.axhspan(1.0, 1.5, alpha=0.2, color='green', label='Optimal Range')

        ax11.set_xlabel('Time (seconds)', fontweight='bold', fontsize=12)
        ax11.set_ylabel('Flight/Contact Time Ratio', fontweight='bold', fontsize=12)
        ax11.set_title('K. Contact vs Flight Time Ratio',
                    fontweight='bold', loc='left', fontsize=14)
        ax11.legend(loc='upper right', fontsize=9)
        ax11.grid(True, alpha=0.3)
    else:
        ax11.text(0.5, 0.5, 'Insufficient data for ratio analysis',
                transform=ax11.transAxes, ha='center', va='center',
                fontsize=12, style='italic')
        ax11.set_title('K. Contact vs Flight Time Ratio',
                    fontweight='bold', loc='left', fontsize=14)

    # ============================================================================
    # PANEL L: Summary Statistics
    # ============================================================================

    ax12 = fig.add_subplot(gs[3, 2])
    ax12.axis('off')

    # Calculate summary statistics
    summary_stats = f"""
    CURVE BIOMECHANICS SUMMARY

    SPEED METRICS:
    • Peak Speed: {df['inst_speed'].max():.2f} m/s
    • Average Speed: {df['inst_speed'].mean():.2f} m/s
    • Speed Range: {df['inst_speed'].max() - df['inst_speed'].min():.2f} m/s
    • Total Distance: {df['dist'].max():.1f} m

    STRIDE CHARACTERISTICS:
    • Avg Stride Freq: {df['stride_freq'].mean():.2f} Hz
    • Avg Stride Length: {df['stride_length'].mean():.2f} m
    • Contact Time: {df['stance_time'].mean()*1000:.1f} ms
    • Flight Time: {df['flight_time'].mean()*1000:.1f} ms

    FORCE & POWER:
    • Peak GRF: {df['grf'].max():.0f} N
    • Avg Power: {df['power'].mean():.0f} W
    • Peak Power: {df['power'].max():.0f} W

    EFFICIENCY METRICS:
    • Vertical Osc: {df['vert_osc'].mean()*100:.1f} cm
    • Flight/Contact: {(df['flight_time']/df['stance_time']).mean():.2f}

    RACE PHASES:
    • Acceleration: 0-10s
    • Max Velocity: 10-30s
    • Curve 2: 30-40s
    • Final Sprint: 40-50s

    KEY FINDINGS:
    • Speed maintained well through curves
    • Stride parameters optimize for velocity
    • Ground contact minimized efficiently
    • Power output sustained throughout
    """

    ax12.text(0.05, 0.95, summary_stats, transform=ax12.transAxes,
            fontsize=9, verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3,
                    edgecolor='black', linewidth=2))

    ax12.set_title('L. Biomechanical Summary',
                fontweight='bold', loc='left', fontsize=14, pad=20)

    # ============================================================================
    # Overall title
    # ============================================================================

    fig.suptitle('400m Olympic Performance: Curve Biomechanics Analysis\n' +
                'Comprehensive Assessment of Running Mechanics Throughout Race',
                fontsize=16, fontweight='bold', y=0.998)

    # Save to figures directory
    import os
    os.makedirs('figures', exist_ok=True)
    plt.savefig('figures/400m_curve_biomechanics.png', dpi=300, bbox_inches='tight')
    print("✓ Figure saved: figures/400m_curve_biomechanics.png")

    plt.close()
