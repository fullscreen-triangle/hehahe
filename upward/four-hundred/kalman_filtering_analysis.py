"""
400m Olympic Performance: Kalman Filter Analysis
Signal processing and noise reduction in speed measurements
"""

import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.gridspec import GridSpec
from scipy import stats
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
    with open('kalman_filter_results.json', 'r') as f:
        kalman_data = json.load(f)

    df = pd.DataFrame(kalman_data)

    print(f"Loaded {len(df)} filtered data points")
    print(f"Columns: {df.columns.tolist()}")

    # Map column names to expected format
    if 'adjusted_speed' in df.columns and 'filtered_speed' not in df.columns:
        df['filtered_speed'] = df['adjusted_speed']
    if 'estimated_speed' in df.columns and 'predicted_speed' not in df.columns:
        df['predicted_speed'] = df['estimated_speed']
    if 'estimated_acceleration' in df.columns and 'innovation' not in df.columns:
        df['innovation'] = df['estimated_acceleration']

    # ============================================================================
    # CREATE FIGURE
    # ============================================================================

    fig = plt.figure(figsize=(22, 18))
    gs = GridSpec(4, 3, figure=fig, hspace=0.4, wspace=0.35)

    colors = {
        'measured': '#E63946',
        'filtered': '#457B9D',
        'predicted': '#2A9D8F',
        'error': '#F4A261',
        'uncertainty': '#E9C46A'
    }

    # ============================================================================
    # PANEL A: Measured vs Filtered Speed
    # ============================================================================

    ax1 = fig.add_subplot(gs[0, :2])

    # Plot measured speed (noisy)
    ax1.plot(df['time'], df['measured_speed'],
            linewidth=1.5, alpha=0.5, color=colors['measured'],
            label='Measured (Raw)', linestyle='-')

    # Plot filtered speed (smooth)
    ax1.plot(df['time'], df['filtered_speed'],
            linewidth=3, alpha=0.9, color=colors['filtered'],
            label='Kalman Filtered')

    # Plot predicted speed
    if 'predicted_speed' in df.columns:
        ax1.plot(df['time'], df['predicted_speed'],
                linewidth=2, alpha=0.7, color=colors['predicted'],
                linestyle='--', label='Predicted')

    ax1.set_xlabel('Time (seconds)', fontweight='bold', fontsize=12)
    ax1.set_ylabel('Speed (m/s)', fontweight='bold', fontsize=12)
    ax1.set_title('A. Kalman Filter: Measured vs Filtered Speed',
                fontweight='bold', loc='left', fontsize=14)
    ax1.legend(loc='upper right', fontsize=10)
    ax1.grid(True, alpha=0.3)

    # Add noise reduction annotation
    noise_reduction = np.std(df['measured_speed']) / np.std(df['filtered_speed'])
    ax1.text(0.5, 0.95,
            f'Noise Reduction Factor: {noise_reduction:.2f}×',
            transform=ax1.transAxes, ha='center', va='top',
            fontsize=11, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.5))

    # ============================================================================
    # PANEL B: Measurement Uncertainty
    # ============================================================================

    ax2 = fig.add_subplot(gs[0, 2])

    if 'uncertainty' in df.columns or 'variance' in df.columns:
        uncertainty_col = 'uncertainty' if 'uncertainty' in df.columns else 'variance'

        ax2.plot(df['time'], df[uncertainty_col],
                linewidth=2.5, color=colors['uncertainty'], alpha=0.8)

        ax2.fill_between(df['time'], 0, df[uncertainty_col],
                        alpha=0.3, color=colors['uncertainty'])

        ax2.set_xlabel('Time (seconds)', fontweight='bold', fontsize=12)
        ax2.set_ylabel('Measurement Uncertainty', fontweight='bold', fontsize=12)
        ax2.set_title('B. Kalman Filter Uncertainty Evolution',
                    fontweight='bold', loc='left', fontsize=14)
        ax2.grid(True, alpha=0.3)

        # Add mean uncertainty
        mean_uncertainty = df[uncertainty_col].mean()
        ax2.axhline(y=mean_uncertainty, color='red', linestyle='--',
                linewidth=2, alpha=0.5,
                label=f'Mean: {mean_uncertainty:.4f}')
        ax2.legend(loc='upper right', fontsize=9)
    else:
        ax2.text(0.5, 0.5, 'No uncertainty data available',
                transform=ax2.transAxes, ha='center', va='center',
                fontsize=12, style='italic')
        ax2.set_title('B. Kalman Filter Uncertainty Evolution',
                    fontweight='bold', loc='left', fontsize=14)

    # ============================================================================
    # PANEL C: Measurement Residuals
    # ============================================================================

    ax3 = fig.add_subplot(gs[1, 0])

    # Calculate residuals (measurement error)
    df['residual'] = df['measured_speed'] - df['filtered_speed']

    ax3.scatter(df['time'], df['residual'],
            s=30, alpha=0.5, color=colors['error'],
            edgecolors='black', linewidth=0.5)

    # Add zero line
    ax3.axhline(y=0, color='black', linestyle='-', linewidth=2, alpha=0.7)

    # Add confidence bands (±2σ)
    std_residual = df['residual'].std()
    ax3.axhspan(-2*std_residual, 2*std_residual,
            alpha=0.2, color='green', label='±2σ Confidence')

    ax3.set_xlabel('Time (seconds)', fontweight='bold', fontsize=12)
    ax3.set_ylabel('Residual (m/s)', fontweight='bold', fontsize=12)
    ax3.set_title('C. Measurement Residuals (Noise)',
                fontweight='bold', loc='left', fontsize=14)
    ax3.legend(loc='upper right', fontsize=9)
    ax3.grid(True, alpha=0.3)

    # Add statistics
    ax3.text(0.95, 0.95,
            f'Mean: {df["residual"].mean():.4f}\nStd: {std_residual:.4f}',
            transform=ax3.transAxes, ha='right', va='top',
            fontsize=9, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # ============================================================================
    # PANEL D: Residual Distribution
    # ============================================================================

    ax4 = fig.add_subplot(gs[1, 1])

    # Histogram of residuals
    n, bins, patches = ax4.hist(df['residual'], bins=30,
                                color=colors['error'], alpha=0.7,
                                edgecolor='black', linewidth=1)

    # Fit normal distribution
    mu, sigma = stats.norm.fit(df['residual'])
    x = np.linspace(df['residual'].min(), df['residual'].max(), 100)
    ax4.plot(x, stats.norm.pdf(x, mu, sigma) * len(df['residual']) * (bins[1]-bins[0]),
            'r--', linewidth=3, label=f'Normal(μ={mu:.3f}, σ={sigma:.3f})')

    ax4.set_xlabel('Residual (m/s)', fontweight='bold', fontsize=12)
    ax4.set_ylabel('Frequency', fontweight='bold', fontsize=12)
    ax4.set_title('D. Residual Distribution (Normality Check)',
                fontweight='bold', loc='left', fontsize=14)
    ax4.legend(loc='upper right', fontsize=9)
    ax4.grid(True, alpha=0.3, axis='y')

    # Add normality test
    _, p_value = stats.shapiro(df['residual'])
    ax4.text(0.95, 0.85,
            f'Shapiro-Wilk p-value: {p_value:.4f}\n' +
            ('Normally distributed ✓' if p_value > 0.05 else 'Not normal ✗'),
            transform=ax4.transAxes, ha='right', va='top',
            fontsize=9, fontweight='bold',
            bbox=dict(boxstyle='round',
                    facecolor='green' if p_value > 0.05 else 'red',
                    alpha=0.3))

    # ============================================================================
    # PANEL E: Q-Q Plot (Normality Assessment)
    # ============================================================================

    ax5 = fig.add_subplot(gs[1, 2])

    stats.probplot(df['residual'], dist="norm", plot=ax5)
    ax5.get_lines()[0].set_marker('o')
    ax5.get_lines()[0].set_markersize(5)
    ax5.get_lines()[0].set_markerfacecolor(colors['error'])
    ax5.get_lines()[0].set_alpha(0.6)
    ax5.get_lines()[1].set_linewidth(2)
    ax5.get_lines()[1].set_color('red')

    ax5.set_xlabel('Theoretical Quantiles', fontweight='bold', fontsize=12)
    ax5.set_ylabel('Sample Quantiles', fontweight='bold', fontsize=12)
    ax5.set_title('E. Q-Q Plot (Residual Normality)',
                fontweight='bold', loc='left', fontsize=14)
    ax5.grid(True, alpha=0.3)

    # ============================================================================
    # PANEL F: Autocorrelation of Residuals
    # ============================================================================

    ax6 = fig.add_subplot(gs[2, 0])

    # Calculate autocorrelation
    max_lag = min(50, len(df) // 2)
    autocorr = [df['residual'].autocorr(lag=i) for i in range(max_lag)]

    ax6.stem(range(max_lag), autocorr, linefmt=colors['error'],
            markerfmt='o', basefmt=' ')

    # Add confidence bands
    confidence = 1.96 / np.sqrt(len(df))
    ax6.axhline(y=confidence, color='blue', linestyle='--',
            linewidth=2, alpha=0.5, label='95% Confidence')
    ax6.axhline(y=-confidence, color='blue', linestyle='--',
            linewidth=2, alpha=0.5)
    ax6.axhline(y=0, color='black', linestyle='-', linewidth=1)

    ax6.set_xlabel('Lag', fontweight='bold', fontsize=12)
    ax6.set_ylabel('Autocorrelation', fontweight='bold', fontsize=12)
    ax6.set_title('F. Residual Autocorrelation (Independence Check)',
                fontweight='bold', loc='left', fontsize=14)
    ax6.legend(loc='upper right', fontsize=9)
    ax6.grid(True, alpha=0.3)

    # ============================================================================
    # PANEL G: Innovation Sequence
    # ============================================================================

    ax7 = fig.add_subplot(gs[2, 1])

    if 'innovation' in df.columns:
        ax7.plot(df['time'], df['innovation'],
                linewidth=2, alpha=0.7, color=colors['predicted'])

        ax7.axhline(y=0, color='black', linestyle='--', linewidth=1.5)

        # Add confidence bands
        std_innov = df['innovation'].std()
        ax7.axhspan(-2*std_innov, 2*std_innov,
                alpha=0.2, color='green', label='±2σ')

        ax7.set_xlabel('Time (seconds)', fontweight='bold', fontsize=12)
        ax7.set_ylabel('Innovation', fontweight='bold', fontsize=12)
        ax7.set_title('G. Innovation Sequence (Filter Performance)',
                    fontweight='bold', loc='left', fontsize=14)
        ax7.legend(loc='upper right', fontsize=9)
        ax7.grid(True, alpha=0.3)
    else:
        # Calculate innovation as difference between measurement and prediction
        if 'predicted_speed' in df.columns:
            innovation = df['measured_speed'] - df['predicted_speed']

            ax7.plot(df['time'], innovation,
                    linewidth=2, alpha=0.7, color=colors['predicted'])

            ax7.axhline(y=0, color='black', linestyle='--', linewidth=1.5)

            std_innov = innovation.std()
            ax7.axhspan(-2*std_innov, 2*std_innov,
                    alpha=0.2, color='green', label='±2σ')

            ax7.set_xlabel('Time (seconds)', fontweight='bold', fontsize=12)
            ax7.set_ylabel('Innovation', fontweight='bold', fontsize=12)
            ax7.set_title('G. Innovation Sequence (Filter Performance)',
                        fontweight='bold', loc='left', fontsize=14)
            ax7.legend(loc='upper right', fontsize=9)
            ax7.grid(True, alpha=0.3)
        else:
            ax7.text(0.5, 0.5, 'No innovation data available',
                    transform=ax7.transAxes, ha='center', va='center',
                    fontsize=12, style='italic')
            ax7.set_title('G. Innovation Sequence (Filter Performance)',
                        fontweight='bold', loc='left', fontsize=14)

    # ============================================================================
    # PANEL H: Signal-to-Noise Ratio
    # ============================================================================

    ax8 = fig.add_subplot(gs[2, 2])

    # Calculate SNR over time (rolling window)
    window = 20
    df['signal_power'] = df['filtered_speed'].rolling(window=window).var()
    df['noise_power'] = df['residual'].rolling(window=window).var()
    df['snr'] = 10 * np.log10(df['signal_power'] / df['noise_power'])

    valid_snr = df[df['snr'].notna()]

    if len(valid_snr) > 0:
        ax8.plot(valid_snr['time'], valid_snr['snr'],
                linewidth=2.5, color=colors['filtered'], alpha=0.8)

        ax8.fill_between(valid_snr['time'], 0, valid_snr['snr'],
                        alpha=0.3, color=colors['filtered'])

        ax8.set_xlabel('Time (seconds)', fontweight='bold', fontsize=12)
        ax8.set_ylabel('SNR (dB)', fontweight='bold', fontsize=12)
        ax8.set_title('H. Signal-to-Noise Ratio Evolution',
                    fontweight='bold', loc='left', fontsize=14)
        ax8.grid(True, alpha=0.3)

        # Add mean SNR
        mean_snr = valid_snr['snr'].mean()
        ax8.axhline(y=mean_snr, color='red', linestyle='--',
                linewidth=2, alpha=0.5,
                label=f'Mean: {mean_snr:.1f} dB')
        ax8.legend(loc='lower right', fontsize=9)
    else:
        ax8.text(0.5, 0.5, 'Insufficient data for SNR calculation',
                transform=ax8.transAxes, ha='center', va='center',
                fontsize=12, style='italic')
        ax8.set_title('H. Signal-to-Noise Ratio Evolution',
                    fontweight='bold', loc='left', fontsize=14)

    # ============================================================================
    # PANEL I: Filter Performance Metrics
    # ============================================================================

    ax9 = fig.add_subplot(gs[3, 0])

    # Calculate various performance metrics
    metrics = {
        'RMSE': np.sqrt(np.mean(df['residual']**2)),
        'MAE': np.mean(np.abs(df['residual'])),
        'Max Error': np.max(np.abs(df['residual'])),
        'Std Dev': df['residual'].std(),
        'Bias': df['residual'].mean()
    }

    bars = ax9.barh(list(metrics.keys()), list(metrics.values()),
                color=[colors['error'], colors['uncertainty'],
                        colors['measured'], colors['filtered'], colors['predicted']],
                alpha=0.8, edgecolor='black', linewidth=1.5)

    # Add value labels
    for i, (bar, val) in enumerate(zip(bars, metrics.values())):
        ax9.text(val + 0.01, bar.get_y() + bar.get_height()/2,
                f'{val:.4f}',
                va='center', fontweight='bold', fontsize=9)

    ax9.set_xlabel('Value (m/s)', fontweight='bold', fontsize=12)
    ax9.set_title('I. Filter Performance Metrics',
                fontweight='bold', loc='left', fontsize=14)
    ax9.grid(True, alpha=0.3, axis='x')

    # ============================================================================
    # PANEL J: Cumulative Error
    # ============================================================================

    ax10 = fig.add_subplot(gs[3, 1])

    # Calculate cumulative absolute error
    cumulative_error = np.cumsum(np.abs(df['residual']))

    ax10.plot(df['time'], cumulative_error,
            linewidth=3, color=colors['error'], alpha=0.8)

    ax10.fill_between(df['time'], 0, cumulative_error,
                    alpha=0.3, color=colors['error'])

    ax10.set_xlabel('Time (seconds)', fontweight='bold', fontsize=12)
    ax10.set_ylabel('Cumulative Absolute Error (m/s)', fontweight='bold', fontsize=12)
    ax10.set_title('J. Cumulative Error Accumulation',
                fontweight='bold', loc='left', fontsize=14)
    ax10.grid(True, alpha=0.3)

    # Add final error
    final_error = cumulative_error.iloc[-1]
    ax10.text(0.95, 0.95,
            f'Final Cumulative Error:\n{final_error:.2f} m/s',
            transform=ax10.transAxes, ha='right', va='top',
            fontsize=10, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.5))

    # ============================================================================
    # PANEL K: Summary Statistics
    # ============================================================================

    ax11 = fig.add_subplot(gs[3, 2])
    ax11.axis('off')

    # Calculate comprehensive statistics
    noise_reduction = np.std(df['measured_speed']) / np.std(df['filtered_speed'])
    correlation = df['measured_speed'].corr(df['filtered_speed'])
    mean_snr = valid_snr['snr'].mean() if len(valid_snr) > 0 else 0

    summary_text = f"""
    KALMAN FILTER PERFORMANCE SUMMARY

    NOISE REDUCTION:
    • Noise Reduction Factor: {noise_reduction:.2f}×
    • Raw Signal Std Dev: {np.std(df['measured_speed']):.4f} m/s
    • Filtered Signal Std Dev: {np.std(df['filtered_speed']):.4f} m/s

    ERROR METRICS:
    • RMSE: {metrics['RMSE']:.4f} m/s
    • MAE: {metrics['MAE']:.4f} m/s
    • Max Error: {metrics['Max Error']:.4f} m/s
    • Bias: {metrics['Bias']:.4f} m/s

    SIGNAL QUALITY:
    • Mean SNR: {mean_snr:.1f} dB
    • Correlation: {correlation:.4f}
    • Residual Normality: {'✓ Pass' if p_value > 0.05 else '✗ Fail'}

    FILTER CHARACTERISTICS:
    • Data Points: {len(df)}
    • Time Range: {df['time'].min():.1f}s - {df['time'].max():.1f}s
    • Sampling Rate: {1/df['time'].diff().mean():.1f} Hz

    PERFORMANCE ASSESSMENT:
    {'✓ Excellent' if noise_reduction > 2 else '✓ Good' if noise_reduction > 1.5 else '⚠ Fair'} Noise Reduction
    {'✓ Excellent' if metrics['RMSE'] < 0.1 else '✓ Good' if metrics['RMSE'] < 0.2 else '⚠ Fair'} Accuracy
    {'✓ Excellent' if mean_snr > 20 else '✓ Good' if mean_snr > 10 else '⚠ Fair'} Signal Quality
    {'✓ Pass' if abs(metrics['Bias']) < 0.01 else '⚠ Check'} Bias Test

    RECOMMENDATIONS:
    • Filter is {'performing optimally' if noise_reduction > 2 and metrics['RMSE'] < 0.1 else 'performing adequately'}
    • {'No adjustments needed' if p_value > 0.05 else 'Consider tuning process noise'}
    • {'Residuals are white noise' if np.max(np.abs(autocorr[1:])) < 0.2 else 'Check for systematic errors'}
    """

    ax11.text(0.05, 0.95, summary_text, transform=ax11.transAxes,
            fontsize=9, verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3,
                    edgecolor='black', linewidth=2))

    ax11.set_title('K. Performance Summary & Assessment',
                fontweight='bold', loc='left', fontsize=14, pad=20)

    # ============================================================================
    # Overall title
    # ============================================================================

    fig.suptitle('400m Olympic Performance: Kalman Filter Analysis\n' +
                'Signal Processing & Noise Reduction in Speed Measurements',
                fontsize=16, fontweight='bold', y=0.998)

    # Save to figures directory
    import os
    os.makedirs('figures', exist_ok=True)
    plt.savefig('figures/400m_kalman_filter_analysis.png', dpi=300, bbox_inches='tight')
    print("✓ Figure saved: figures/400m_kalman_filter_analysis.png")

    plt.close()
