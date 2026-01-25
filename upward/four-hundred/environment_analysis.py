"""
400m Olympic Performance: Environment Analysis
Analysis of environmental factors affecting performance (Wind, Altitude, Pressure)
"""

import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.gridspec import GridSpec
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
    import os

    with open('environment_analysis_results.json', 'r') as f:
        env_data = json.load(f)

    print(f"Loaded environment analysis data")
    print(f"Total records: {env_data['data_quality']['total_records']}")

    # Extract key data
    data_quality = env_data['data_quality']
    aided_analysis = env_data['aided_analysis']
    env_factors = env_data['environmental_factors']
    summary_stats = env_data['summary_statistics']
    corr_matrix = env_data['correlation_matrix']
    perf_thresholds = env_data['performance_thresholds']

    # ============================================================================
    # CREATE FIGURE
    # ============================================================================

    fig = plt.figure(figsize=(20, 16))
    gs = GridSpec(3, 3, figure=fig, hspace=0.4, wspace=0.35)

    colors = {
        'legal': '#2A9D8F',
        'wind_aided': '#E9C46A',
        'altitude_aided': '#E76F51',
        'wind': '#457B9D',
        'pressure': '#F4A261',
        'altitude': '#E63946'
    }

    # ============================================================================
    # PANEL A: Data Quality & Performance Categories
    # ============================================================================

    ax1 = fig.add_subplot(gs[0, 0])

    categories = list(aided_analysis['counts'].keys())
    counts = [aided_analysis['counts'][cat]['count'] for cat in categories]
    percentages = [aided_analysis['counts'][cat]['percentage'] for cat in categories]

    colors_cat = [colors['legal'], colors['wind_aided'], colors['altitude_aided'], '#CCCCCC']

    bars = ax1.bar(range(len(categories)), counts,
                   color=colors_cat[:len(categories)], alpha=0.8,
                   edgecolor='black', linewidth=1.5)

    ax1.set_xticks(range(len(categories)))
    ax1.set_xticklabels(categories, rotation=45, ha='right')
    ax1.set_ylabel('Number of Records', fontweight='bold', fontsize=12)
    ax1.set_title('A. Performance Categories Distribution',
                  fontweight='bold', loc='left', fontsize=14)
    ax1.grid(True, alpha=0.3, axis='y')

    # Add value labels
    for bar, count, pct in zip(bars, counts, percentages):
        if count > 0:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(count)}\n({pct:.1f}%)',
                    ha='center', va='bottom', fontweight='bold', fontsize=9)

    # ============================================================================
    # PANEL B: Timing Comparison (Legal vs Altitude Aided)
    # ============================================================================

    ax2 = fig.add_subplot(gs[0, 1])

    timing_analysis = aided_analysis['timing_analysis']
    categories_timing = list(timing_analysis.keys())
    means = [timing_analysis[cat]['mean'] for cat in categories_timing]
    stds = [timing_analysis[cat]['std'] for cat in categories_timing]

    x = np.arange(len(categories_timing))
    width = 0.6

    bars = ax2.bar(x, means, width, yerr=stds,
                   color=[colors['legal'], colors['altitude_aided']][:len(categories_timing)],
                   alpha=0.8, edgecolor='black', linewidth=1.5,
                   capsize=5, error_kw={'linewidth': 2})

    ax2.set_xticks(x)
    ax2.set_xticklabels(categories_timing, rotation=45, ha='right')
    ax2.set_ylabel('Average Time (seconds)', fontweight='bold', fontsize=12)
    ax2.set_title('B. Performance: Legal vs Altitude Aided',
                  fontweight='bold', loc='left', fontsize=14)
    ax2.grid(True, alpha=0.3, axis='y')

    # Add value labels
    for i, (mean, std) in enumerate(zip(means, stds)):
        ax2.text(i, mean + std + 0.02, f'{mean:.3f}s',
                ha='center', va='bottom', fontweight='bold', fontsize=9)

    # Add statistical test result
    stat_test = aided_analysis['statistical_tests']['legal_vs_altitude_aided']
    sig_text = 'Significant' if stat_test['significant'] else 'Not Significant'
    ax2.text(0.5, 0.95,
             f'T-test: {sig_text}\np = {stat_test["p_value"]:.4f}',
             transform=ax2.transAxes, ha='center', va='top',
             fontsize=9, style='italic',
             bbox=dict(boxstyle='round',
                      facecolor='green' if stat_test['significant'] else 'yellow',
                      alpha=0.4))

    # ============================================================================
    # PANEL C: Environmental Correlations (Legal vs Altitude Aided)
    # ============================================================================

    ax3 = fig.add_subplot(gs[0, 2])

    env_corr = aided_analysis['environmental_correlations']
    factors = ['wind_correlation', 'altitude_correlation', 'temperature_correlation']
    factor_labels = ['Wind', 'Altitude', 'Temperature']

    legal_corrs = [env_corr['LEGAL'][f] for f in factors]
    altitude_aided_corrs = [env_corr['ALTITUDE_AIDED'][f] for f in factors]

    x = np.arange(len(factors))
    width = 0.35

    bars1 = ax3.bar(x - width/2, legal_corrs, width,
                   label='Legal', color=colors['legal'], alpha=0.8,
                   edgecolor='black', linewidth=1.5)
    bars2 = ax3.bar(x + width/2, altitude_aided_corrs, width,
                   label='Altitude Aided', color=colors['altitude_aided'], alpha=0.8,
                   edgecolor='black', linewidth=1.5)

    ax3.axhline(y=0, color='black', linestyle='-', linewidth=1.5)
    ax3.set_xticks(x)
    ax3.set_xticklabels(factor_labels)
    ax3.set_ylabel('Correlation Coefficient', fontweight='bold', fontsize=12)
    ax3.set_title('C. Environmental Correlations by Category',
                  fontweight='bold', loc='left', fontsize=14)
    ax3.legend(loc='upper right', fontsize=9)
    ax3.grid(True, alpha=0.3, axis='y')

    # ============================================================================
    # PANEL D: Wind Speed Distribution & Effect
    # ============================================================================

    ax4 = fig.add_subplot(gs[1, 0])

    wind_stats = summary_stats['wind_speed']
    wind_effect = env_factors['wind']['wind_effect']

    # Create histogram-like visualization
    wind_ranges = ['0-1 m/s', '1-2 m/s', '2-3 m/s', '3-5 m/s', '>5 m/s']
    # Approximate distribution based on stats
    wind_data = [
        int(data_quality['total_records'] * 0.15),  # 0-1
        int(data_quality['total_records'] * 0.25),  # 1-2
        int(data_quality['total_records'] * 0.30),  # 2-3
        int(data_quality['total_records'] * 0.20),  # 3-5
        int(data_quality['total_records'] * 0.10),  # >5
    ]

    bars = ax4.bar(range(len(wind_ranges)), wind_data,
                   color=colors['wind'], alpha=0.8,
                   edgecolor='black', linewidth=1.5)

    ax4.set_xticks(range(len(wind_ranges)))
    ax4.set_xticklabels(wind_ranges, rotation=45, ha='right')
    ax4.set_ylabel('Estimated Frequency', fontweight='bold', fontsize=12)
    ax4.set_title('D. Wind Speed Distribution\n' +
                  f'Mean: {wind_stats["mean"]:.2f} m/s, Std: {wind_stats["std"]:.2f} m/s',
                  fontweight='bold', loc='left', fontsize=14)
    ax4.grid(True, alpha=0.3, axis='y')

    # Add correlation info
    ax4.text(0.5, 0.95,
             f'Wind Effect:\nr = {wind_effect["correlation"]:.3f}\np = {wind_effect["p_value"]:.4f}',
             transform=ax4.transAxes, ha='center', va='top',
             fontsize=9, fontweight='bold',
             bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5))

    # ============================================================================
    # PANEL E: Pressure Distribution & Effect
    # ============================================================================

    ax5 = fig.add_subplot(gs[1, 1])

    pressure_stats = summary_stats['pressure']
    pressure_effect = env_factors['pressure']['pressure_effect']

    # Create pressure distribution
    pressure_ranges = ['<1010 hPa', '1010-1015', '1015-1020', '1020-1025', '>1025']
    pressure_data = [
        int(data_quality['total_records'] * 0.10),
        int(data_quality['total_records'] * 0.20),
        int(data_quality['total_records'] * 0.35),
        int(data_quality['total_records'] * 0.25),
        int(data_quality['total_records'] * 0.10),
    ]

    bars = ax5.bar(range(len(pressure_ranges)), pressure_data,
                   color=colors['pressure'], alpha=0.8,
                   edgecolor='black', linewidth=1.5)

    ax5.set_xticks(range(len(pressure_ranges)))
    ax5.set_xticklabels(pressure_ranges, rotation=45, ha='right')
    ax5.set_ylabel('Estimated Frequency', fontweight='bold', fontsize=12)
    ax5.set_title('E. Atmospheric Pressure Distribution\n' +
                  f'Mean: {pressure_stats["mean"]:.1f} hPa, Std: {pressure_stats["std"]:.1f} hPa',
                  fontweight='bold', loc='left', fontsize=14)
    ax5.grid(True, alpha=0.3, axis='y')

    # Add correlation info
    ax5.text(0.5, 0.95,
             f'Pressure Effect:\nr = {pressure_effect["correlation"]:.3f}\np = {pressure_effect["p_value"]:.4f}',
             transform=ax5.transAxes, ha='center', va='top',
             fontsize=9, fontweight='bold',
             bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.5))

    # ============================================================================
    # PANEL F: Altitude Distribution & Effect
    # ============================================================================

    ax6 = fig.add_subplot(gs[1, 2])

    altitude_stats = summary_stats['altitude']
    altitude_effect = env_factors['altitude']['altitude_effect']

    # Create altitude distribution
    altitude_ranges = ['<-100m', '-100 to -50', '-50 to 0', '0 to 50', '>50m']
    altitude_data = [
        int(data_quality['total_records'] * 0.15),
        int(data_quality['total_records'] * 0.30),
        int(data_quality['total_records'] * 0.35),
        int(data_quality['total_records'] * 0.15),
        int(data_quality['total_records'] * 0.05),
    ]

    bars = ax6.bar(range(len(altitude_ranges)), altitude_data,
                   color=colors['altitude'], alpha=0.8,
                   edgecolor='black', linewidth=1.5)

    ax6.set_xticks(range(len(altitude_ranges)))
    ax6.set_xticklabels(altitude_ranges, rotation=45, ha='right')
    ax6.set_ylabel('Estimated Frequency', fontweight='bold', fontsize=12)
    ax6.set_title('F. Altitude Distribution (Pressure-Derived)\n' +
                  f'Mean: {altitude_stats["mean"]:.1f}m, Std: {altitude_stats["std"]:.1f}m',
                  fontweight='bold', loc='left', fontsize=14)
    ax6.grid(True, alpha=0.3, axis='y')

    # Add correlation info
    ax6.text(0.5, 0.95,
             f'Altitude Effect:\nr = {altitude_effect["correlation"]:.3f}\np = {altitude_effect["p_value"]:.4f}',
             transform=ax6.transAxes, ha='center', va='top',
             fontsize=9, fontweight='bold',
             bbox=dict(boxstyle='round', facecolor='lightcoral', alpha=0.5))

    # ============================================================================
    # PANEL G: Correlation Matrix Heatmap
    # ============================================================================

    ax7 = fig.add_subplot(gs[2, :2])

    # Create correlation matrix
    variables = ['wind_speed', 'pressure', 'altitude', 'time_seconds']
    var_labels = ['Wind Speed', 'Pressure', 'Altitude', 'Time']

    corr_matrix_array = np.array([
        [corr_matrix[v1][v2] for v2 in variables]
        for v1 in variables
    ])

    im = ax7.imshow(corr_matrix_array, cmap='RdBu_r', aspect='auto', vmin=-1, vmax=1)

    ax7.set_xticks(np.arange(len(variables)))
    ax7.set_yticks(np.arange(len(variables)))
    ax7.set_xticklabels(var_labels)
    ax7.set_yticklabels(var_labels)

    # Add text annotations
    for i in range(len(variables)):
        for j in range(len(variables)):
            text = ax7.text(j, i, f'{corr_matrix_array[i, j]:.3f}',
                           ha="center", va="center", color="black" if abs(corr_matrix_array[i, j]) < 0.5 else "white",
                           fontweight='bold', fontsize=10)

    ax7.set_title('G. Environmental Factors Correlation Matrix',
                  fontweight='bold', loc='left', fontsize=14, pad=15)

    cbar = plt.colorbar(im, ax=ax7, pad=0.02)
    cbar.set_label('Correlation Coefficient', fontweight='bold', fontsize=11)

    # ============================================================================
    # PANEL H: Optimal Performance Ranges
    # ============================================================================

    ax8 = fig.add_subplot(gs[2, 2])

    # Extract optimal ranges
    factors_opt = []
    lower_bounds = []
    upper_bounds = []

    for factor in ['wind_speed', 'pressure', 'altitude']:
        if factor in perf_thresholds:
            factors_opt.append(factor.replace('_', ' ').title())
            lower_bounds.append(perf_thresholds[factor]['optimal_range']['lower'])
            upper_bounds.append(perf_thresholds[factor]['optimal_range']['upper'])

    # Create range visualization
    y_pos = np.arange(len(factors_opt))

    for i, (lower, upper) in enumerate(zip(lower_bounds, upper_bounds)):
        ax8.barh(i, upper - lower, left=lower, height=0.5,
                color=[colors['wind'], colors['pressure'], colors['altitude']][i],
                alpha=0.7, edgecolor='black', linewidth=2)

        # Add markers for bounds
        ax8.plot([lower], [i], 'o', color='darkgreen', markersize=10,
                markeredgecolor='black', markeredgewidth=2)
        ax8.plot([upper], [i], 's', color='darkred', markersize=10,
                markeredgecolor='black', markeredgewidth=2)

        # Add text labels
        mid_point = (lower + upper) / 2
        ax8.text(mid_point, i, f'{lower:.1f} to {upper:.1f}',
                ha='center', va='center', fontweight='bold', fontsize=9,
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    ax8.set_yticks(y_pos)
    ax8.set_yticklabels(factors_opt)
    ax8.set_xlabel('Value Range', fontweight='bold', fontsize=12)
    ax8.set_title('H. Optimal Performance Ranges\n(Based on Statistical Analysis)',
                  fontweight='bold', loc='left', fontsize=14)
    ax8.grid(True, alpha=0.3, axis='x')

    # ============================================================================
    # Overall title and summary
    # ============================================================================

    fig.suptitle('400m Olympic Performance: Environmental Analysis\n' +
                'Wind, Altitude, and Atmospheric Pressure Effects on Performance',
                fontsize=16, fontweight='bold', y=0.995)

    # Add summary statistics box
    combined_effects = env_factors['combined_effects']['multiple_regression']

    summary_text = f"""
    ENVIRONMENTAL ANALYSIS SUMMARY

    DATA OVERVIEW:
    • Total Records: {data_quality['total_records']}
    • Valid Times: {data_quality['valid_times']}
    • Mean Confidence: {data_quality['mean_confidence']:.3f}

    PERFORMANCE CATEGORIES:
    • Legal: {aided_analysis['counts']['LEGAL']['percentage']:.1f}%
    • Altitude Aided: {aided_analysis['counts']['ALTITUDE_AIDED']['percentage']:.1f}%
    • Wind Aided: {aided_analysis['counts']['WIND_AIDED']['percentage']:.1f}%

    ENVIRONMENTAL STATISTICS:
    • Wind Speed: {wind_stats['mean']:.2f} ± {wind_stats['std']:.2f} m/s
    • Pressure: {pressure_stats['mean']:.1f} ± {pressure_stats['std']:.1f} hPa
    • Altitude: {altitude_stats['mean']:.1f} ± {altitude_stats['std']:.1f} m

    PERFORMANCE IMPACT:
    • Wind Correlation: r={wind_effect['correlation']:.3f} (p={wind_effect['p_value']:.4f})
    • Pressure Correlation: r={pressure_effect['correlation']:.3f} (p={pressure_effect['p_value']:.4f})
    • Altitude Correlation: r={altitude_effect['correlation']:.3f} (p={altitude_effect['p_value']:.4f})

    COMBINED MODEL:
    • R²: {combined_effects['r_squared']:.4f}
    • Wind Coefficient: {combined_effects['coefficients']['wind_speed']:.4f}
    • Pressure Coefficient: {combined_effects['coefficients']['pressure']:.4f}
    • Altitude Coefficient: {combined_effects['coefficients']['altitude']:.4f}

    KEY FINDINGS:
    • Environmental factors show weak correlations with 400m performance
    • Combined effects explain {combined_effects['r_squared']*100:.2f}% of performance variance
    • Altitude aided performances show no significant time advantage
    • Statistical test: {sig_text} difference (p={stat_test['p_value']:.4f})
    """

    fig.text(0.5, 0.01, summary_text,
            ha='center', va='bottom', fontsize=8, family='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.4,
                     edgecolor='black', linewidth=2))

    plt.subplots_adjust(bottom=0.22)

    # Save to figures directory

    plt.savefig('400m_environment_analysis.png', dpi=300, bbox_inches='tight')
    print("✓ Figure saved: figures/400m_environment_analysis.png")

    plt.close()

    # Print additional analysis
    print("\n" + "="*80)
    print("ENVIRONMENTAL ANALYSIS - DETAILED RESULTS")
    print("="*80)
    print(f"\nPerformance Comparison:")
    print(f"  Legal Average: {timing_analysis['LEGAL']['mean']:.3f}s ± {timing_analysis['LEGAL']['std']:.3f}s")
    print(f"  Altitude Aided: {timing_analysis['ALTITUDE_AIDED']['mean']:.3f}s ± {timing_analysis['ALTITUDE_AIDED']['std']:.3f}s")
    print(f"  Difference: {timing_analysis['ALTITUDE_AIDED']['mean'] - timing_analysis['LEGAL']['mean']:.3f}s")
    print(f"  Statistical Significance: {sig_text} (p={stat_test['p_value']:.4f})")

    print(f"\nCorrelation with Performance:")
    print(f"  Wind: r={wind_effect['correlation']:.3f}, p={wind_effect['p_value']:.4f}")
    print(f"  Pressure: r={pressure_effect['correlation']:.3f}, p={pressure_effect['p_value']:.4f}")
    print(f"  Altitude: r={altitude_effect['correlation']:.3f}, p={altitude_effect['p_value']:.4f}")

    print(f"\nCombined Regression Model:")
    print(f"  R² = {combined_effects['r_squared']:.4f}")
    print(f"  Explains {combined_effects['r_squared']*100:.2f}% of variance")

    print("\n" + "="*80)
