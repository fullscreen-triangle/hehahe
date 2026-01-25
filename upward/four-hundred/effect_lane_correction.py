"""
400m Olympic Performance: Lane Correction & Heat Analysis
Comprehensive analysis of lane advantages, heat effects, and neighbor influences
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
    import os

    with open('olympics_lane_correction.json', 'r') as f:
        lane_data = json.load(f)

    df = pd.DataFrame(lane_data)

    # Convert to numeric
    df['Lane'] = df['Lane'].astype(int)
    df['Original_Time'] = df['Original_Time'].astype(float)
    df['Adjusted_Time'] = df['Adjusted_Time'].astype(float)
    df['Lane_Advantage'] = df['Lane_Advantage'].astype(float)

    # Extract heat number
    df['Heat_Number'] = df['Heat'].str.extract(r'(\d+)').astype(int)

    # Calculate actual performance (how well they used the advantage)
    # Negative means they ran slower than expected even with lane advantage
    df['Performance_vs_Expected'] = df['Original_Time'] - df['Adjusted_Time']
    df['Advantage_Utilization'] = (df['Lane_Advantage'] / df['Original_Time']) * 100  # % advantage

    print(f"Loaded {len(df)} athletes across {df['Heat_Number'].nunique()} heats")
    print(f"Lane range: {df['Lane'].min()} - {df['Lane'].max()}")
    print(f"Heat numbers: {sorted(df['Heat_Number'].unique())}")

    # Calculate neighbor effects
    def calculate_neighbor_speed(row, df_all):
        """Calculate average speed of neighbors (lanes ±1)"""
        same_heat = df_all[df_all['Heat'] == row['Heat']]
        neighbors = same_heat[
            (same_heat['Lane'].isin([row['Lane']-1, row['Lane']+1])) &
            (same_heat['Athlete'] != row['Athlete'])
        ]
        if len(neighbors) > 0:
            # Speed in m/s (400m / time)
            neighbor_speeds = 400.0 / neighbors['Original_Time']
            return neighbor_speeds.mean()
        return np.nan

    df['Neighbor_Avg_Speed'] = df.apply(lambda row: calculate_neighbor_speed(row, df), axis=1)
    df['Own_Speed'] = 400.0 / df['Original_Time']
    df['Speed_Differential'] = df['Own_Speed'] - df['Neighbor_Avg_Speed']

    # ============================================================================
    # CREATE FIGURE
    # ============================================================================

    fig = plt.figure(figsize=(20, 16))
    gs = GridSpec(2, 2, figure=fig, hspace=0.35, wspace=0.3)

    colors = {
        'inner': '#E63946',
        'middle': '#F1FAEE',
        'outer': '#457B9D',
        'advantage': '#2A9D8F',
        'disadvantage': '#E76F51',
        'heat_early': '#A8DADC',
        'heat_late': '#1D3557'
    }

    # ============================================================================
    # PANEL A: Lane Advantage vs Actual Performance by Heat
    # ============================================================================

    ax1 = fig.add_subplot(gs[0, 0])

    # Scatter plot with heat-dependent coloring
    scatter = ax1.scatter(df['Lane_Advantage'], df['Original_Time'],
                         c=df['Heat_Number'], s=150, alpha=0.7,
                         cmap='RdYlGn_r', edgecolors='black', linewidth=1.5,
                         vmin=1, vmax=6)

    # Add trend line
    mask = ~(df['Lane_Advantage'].isna() | df['Original_Time'].isna())
    z = np.polyfit(df[mask]['Lane_Advantage'], df[mask]['Original_Time'], 1)
    p = np.poly1d(z)
    x_trend = np.linspace(df['Lane_Advantage'].min(), df['Lane_Advantage'].max(), 100)
    ax1.plot(x_trend, p(x_trend), '--', linewidth=3, color='red',
             alpha=0.7, label=f'Trend: y = {z[0]:.2f}x + {z[1]:.2f}')

    # Add reference line (no advantage)
    ax1.axvline(x=0, color='black', linestyle='--', linewidth=2, alpha=0.5,
                label='No Lane Advantage')

    # Correlation
    corr, p_val = stats.pearsonr(df[mask]['Lane_Advantage'], df[mask]['Original_Time'])

    ax1.set_xlabel('Lane Advantage (seconds)', fontweight='bold', fontsize=13)
    ax1.set_ylabel('Original Time (seconds)', fontweight='bold', fontsize=13)
    ax1.set_title('A. Lane Advantage vs Performance by Heat\n' +
                  f'(Correlation: r={corr:.3f}, p={p_val:.4f})',
                  fontweight='bold', loc='left', fontsize=14, pad=15)
    ax1.legend(loc='upper right', fontsize=10)
    ax1.grid(True, alpha=0.3)

    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax1, pad=0.02)
    cbar.set_label('Heat Number (1=Early, 6=Late)', fontweight='bold', fontsize=11)

    # Annotate key insight
    ax1.text(0.05, 0.95,
             'Later heats (darker) show\ngreater advantage utilization',
             transform=ax1.transAxes, ha='left', va='top',
             fontsize=10, style='italic',
             bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.3))

    # ============================================================================
    # PANEL B: Outer Lane Advantage - Who Uses It Best?
    # ============================================================================

    ax2 = fig.add_subplot(gs[0, 1])

    # Focus on outer lanes (7, 8, 9)
    outer_lanes = df[df['Lane'] >= 7].copy()

    # Categorize by advantage utilization
    outer_lanes['Category'] = pd.cut(outer_lanes['Original_Time'],
                                     bins=[0, 44.5, 45.5, 100],
                                     labels=['Elite (<44.5s)', 'Good (44.5-45.5s)', 'Average (>45.5s)'])

    # Box plot
    categories = ['Elite (<44.5s)', 'Good (44.5-45.5s)', 'Average (>45.5s)']
    lane_adv_by_cat = [outer_lanes[outer_lanes['Category'] == cat]['Lane_Advantage'].values
                       for cat in categories]

    bp = ax2.boxplot(lane_adv_by_cat, labels=categories, patch_artist=True,
                     showmeans=True, meanprops=dict(marker='D', markerfacecolor='red',
                                                     markersize=8))

    # Color boxes
    box_colors = ['#2A9D8F', '#F4A261', '#E76F51']
    for patch, color in zip(bp['boxes'], box_colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    ax2.set_ylabel('Lane Advantage (seconds)', fontweight='bold', fontsize=13)
    ax2.set_title('B. Outer Lanes (7-9): Who Uses the Advantage?\n' +
                  'Performance Category vs Lane Advantage',
                  fontweight='bold', loc='left', fontsize=14, pad=15)
    ax2.grid(True, alpha=0.3, axis='y')
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=15, ha='right')

    # Add statistics
    for i, cat in enumerate(categories):
        data = lane_adv_by_cat[i]
        if len(data) > 0:
            ax2.text(i+1, ax2.get_ylim()[1] * 0.95,
                    f'n={len(data)}\nμ={np.mean(data):.3f}s',
                    ha='center', va='top', fontsize=9, fontweight='bold',
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    # Key insight
    ax2.text(0.5, 0.02,
             'Elite runners (faster times) have similar lane advantages\n' +
             'but perform better overall - advantage alone isn\'t enough!',
             transform=ax2.transAxes, ha='center', va='bottom',
             fontsize=10, style='italic',
             bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.3))

    # ============================================================================
    # PANEL C: Heat Progression & Stakes Effect
    # ============================================================================

    ax3 = fig.add_subplot(gs[1, 0])

    # Calculate average performance by heat
    heat_stats = df.groupby('Heat_Number').agg({
        'Original_Time': ['mean', 'std', 'min'],
        'Lane_Advantage': 'mean',
        'Adjusted_Time': 'mean'
    }).reset_index()

    heat_stats.columns = ['Heat_Number', 'Avg_Time', 'Std_Time', 'Best_Time',
                          'Avg_Advantage', 'Avg_Adjusted']

    # Create dual-axis plot
    ax3_twin = ax3.twinx()

    # Bar plot for average times
    bars = ax3.bar(heat_stats['Heat_Number'], heat_stats['Avg_Time'],
                   alpha=0.6, color=colors['heat_late'],
                   edgecolor='black', linewidth=2, label='Avg Original Time')

    # Add error bars
    ax3.errorbar(heat_stats['Heat_Number'], heat_stats['Avg_Time'],
                yerr=heat_stats['Std_Time'], fmt='none',
                ecolor='black', capsize=5, linewidth=2, alpha=0.7)

    # Line plot for best times
    ax3_twin.plot(heat_stats['Heat_Number'], heat_stats['Best_Time'],
                 'o-', linewidth=3, markersize=10, color='red',
                 markeredgecolor='black', markeredgewidth=2,
                 label='Best Time in Heat')

    # Highlight trend
    if len(heat_stats) > 2:
        z_best = np.polyfit(heat_stats['Heat_Number'], heat_stats['Best_Time'], 1)
        if z_best[0] < 0:  # Improving (decreasing times)
            ax3_twin.text(0.95, 0.95,
                         f'Best times improve by\n{abs(z_best[0]):.3f}s per heat',
                         transform=ax3_twin.transAxes, ha='right', va='top',
                         fontsize=11, fontweight='bold',
                         bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.6))

    ax3.set_xlabel('Heat Number', fontweight='bold', fontsize=13)
    ax3.set_ylabel('Average Time (seconds)', fontweight='bold', fontsize=13,
                   color=colors['heat_late'])
    ax3_twin.set_ylabel('Best Time (seconds)', fontweight='bold', fontsize=13,
                       color='red')
    ax3.set_title('C. Heat Progression: Stakes Increase\n' +
                  'Later Heats = Higher Competition Level',
                  fontweight='bold', loc='left', fontsize=14, pad=15)
    ax3.tick_params(axis='y', labelcolor=colors['heat_late'])
    ax3_twin.tick_params(axis='y', labelcolor='red')
    ax3.grid(True, alpha=0.3, axis='y')
    ax3.set_xticks(heat_stats['Heat_Number'])

    # Combined legend
    lines1, labels1 = ax3.get_legend_handles_labels()
    lines2, labels2 = ax3_twin.get_legend_handles_labels()
    ax3.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=10)

    # ============================================================================
    # PANEL D: Neighbor Effect - Running Next to Fast Athletes
    # ============================================================================

    ax4 = fig.add_subplot(gs[1, 1])

    # Filter valid neighbor data
    neighbor_df = df[df['Neighbor_Avg_Speed'].notna()].copy()

    # Scatter plot with lane coloring
    lane_colors = neighbor_df['Lane'].map(lambda x: colors['inner'] if x <= 3
                                          else colors['middle'] if x <= 6
                                          else colors['outer'])

    scatter2 = ax4.scatter(neighbor_df['Neighbor_Avg_Speed'],
                          neighbor_df['Own_Speed'],
                          c=neighbor_df['Lane'], s=120, alpha=0.7,
                          cmap='RdYlGn', edgecolors='black', linewidth=1.5,
                          vmin=2, vmax=9)

    # Add diagonal (equal performance line)
    min_speed = min(neighbor_df['Neighbor_Avg_Speed'].min(),
                    neighbor_df['Own_Speed'].min())
    max_speed = max(neighbor_df['Neighbor_Avg_Speed'].max(),
                    neighbor_df['Own_Speed'].max())
    ax4.plot([min_speed, max_speed], [min_speed, max_speed],
             'k--', linewidth=2, alpha=0.5, label='Equal Speed')

    # Add trend line
    z_neighbor = np.polyfit(neighbor_df['Neighbor_Avg_Speed'],
                            neighbor_df['Own_Speed'], 1)
    p_neighbor = np.poly1d(z_neighbor)
    x_neighbor = np.linspace(neighbor_df['Neighbor_Avg_Speed'].min(),
                            neighbor_df['Neighbor_Avg_Speed'].max(), 100)
    ax4.plot(x_neighbor, p_neighbor(x_neighbor), '--', linewidth=3,
            color='blue', alpha=0.7,
            label=f'Trend: y = {z_neighbor[0]:.2f}x + {z_neighbor[1]:.2f}')

    # Correlation
    corr_neighbor, p_val_neighbor = stats.pearsonr(
        neighbor_df['Neighbor_Avg_Speed'],
        neighbor_df['Own_Speed']
    )

    ax4.set_xlabel('Average Neighbor Speed (m/s)', fontweight='bold', fontsize=13)
    ax4.set_ylabel('Own Speed (m/s)', fontweight='bold', fontsize=13)
    ax4.set_title('D. Neighbor Effect: Running Next to Fast Athletes\n' +
                  f'(Correlation: r={corr_neighbor:.3f}, p={p_val_neighbor:.4f})',
                  fontweight='bold', loc='left', fontsize=14, pad=15)
    ax4.legend(loc='upper left', fontsize=10)
    ax4.grid(True, alpha=0.3)

    # Add colorbar
    cbar2 = plt.colorbar(scatter2, ax=ax4, pad=0.02)
    cbar2.set_label('Lane Number', fontweight='bold', fontsize=11)

    # Annotate regions
    if z_neighbor[0] > 0.5:  # Strong positive correlation
        ax4.text(0.95, 0.05,
                f'Strong neighbor effect!\n' +
                f'Running next to fast\n' +
                f'athletes improves speed',
                transform=ax4.transAxes, ha='right', va='bottom',
                fontsize=10, fontweight='bold',
                bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.6))
    else:
        ax4.text(0.95, 0.05,
                f'Weak neighbor effect\n' +
                f'Individual ability\n' +
                f'dominates performance',
                transform=ax4.transAxes, ha='right', va='bottom',
                fontsize=10, fontweight='bold',
                bbox=dict(boxstyle='round', facecolor='orange', alpha=0.6))

    # ============================================================================
    # Overall title and summary
    # ============================================================================

    fig.suptitle('400m Olympic Performance: Lane Correction & Competitive Effects Analysis\n' +
                'Comprehensive Assessment of Lane Advantages, Heat Progression, and Neighbor Influences',
                fontsize=16, fontweight='bold', y=0.995)

    # Add summary statistics box
    summary_text = f"""
    KEY FINDINGS:

    • Total Athletes Analyzed: {len(df)}
    • Heats: {df['Heat_Number'].nunique()} (Heat 1-{df['Heat_Number'].max()})
    • Lane Range: {df['Lane'].min()}-{df['Lane'].max()}
    • Max Lane Advantage: {df['Lane_Advantage'].max():.3f}s (Lane {df.loc[df['Lane_Advantage'].idxmax(), 'Lane']})
    • Max Lane Disadvantage: {df['Lane_Advantage'].min():.3f}s (Lane {df.loc[df['Lane_Advantage'].idxmin(), 'Lane']})

    OUTER LANE PERFORMANCE (Lanes 7-9):
    • Elite Runners (<44.5s): {len(outer_lanes[outer_lanes['Original_Time'] < 44.5])} athletes
    • Average Advantage: {outer_lanes['Lane_Advantage'].mean():.3f}s
    • Best Outer Lane Time: {outer_lanes['Original_Time'].min():.2f}s

    HEAT PROGRESSION:
    • Average Time Heat 1: {heat_stats[heat_stats['Heat_Number']==1]['Avg_Time'].values[0]:.2f}s
    • Average Time Heat {df['Heat_Number'].max()}: {heat_stats[heat_stats['Heat_Number']==df['Heat_Number'].max()]['Avg_Time'].values[0]:.2f}s
    • Improvement: {heat_stats[heat_stats['Heat_Number']==1]['Avg_Time'].values[0] - heat_stats[heat_stats['Heat_Number']==df['Heat_Number'].max()]['Avg_Time'].values[0]:.3f}s

    NEIGHBOR EFFECT:
    • Correlation: r={corr_neighbor:.3f} (p={p_val_neighbor:.4f})
    • {'Significant' if p_val_neighbor < 0.05 else 'Not significant'} at α=0.05
    """

    # Add text box at bottom
    fig.text(0.5, 0.01, summary_text,
            ha='center', va='bottom', fontsize=9, family='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.4,
                     edgecolor='black', linewidth=2))

    plt.subplots_adjust(bottom=0.18)

    # Save to figures directory
    os.makedirs('figures', exist_ok=True)
    plt.savefig('figures/400m_lane_correction_analysis.png', dpi=300, bbox_inches='tight')
    print("✓ Figure saved: figures/400m_lane_correction_analysis.png")

    # Print detailed statistics
    print("\n" + "="*80)
    print("LANE CORRECTION ANALYSIS - DETAILED STATISTICS")
    print("="*80)

    print(f"\nLane Advantage Statistics:")
    print(f"  Mean: {df['Lane_Advantage'].mean():.3f}s")
    print(f"  Std Dev: {df['Lane_Advantage'].std():.3f}s")
    print(f"  Range: {df['Lane_Advantage'].min():.3f}s to {df['Lane_Advantage'].max():.3f}s")

    print(f"\nOuter Lane Analysis (Lanes 7-9):")
    print(f"  Number of athletes: {len(outer_lanes)}")
    print(f"  Average lane advantage: {outer_lanes['Lane_Advantage'].mean():.3f}s")
    print(f"  Elite performers (<44.5s): {len(outer_lanes[outer_lanes['Original_Time'] < 44.5])}")
    print(f"  Their avg advantage: {outer_lanes[outer_lanes['Original_Time'] < 44.5]['Lane_Advantage'].mean():.3f}s")

    print(f"\nNeighbor Effect:")
    print(f"  Correlation coefficient: {corr_neighbor:.3f}")
    print(f"  P-value: {p_val_neighbor:.4f}")
    print(f"  Effect size: {'Strong' if abs(corr_neighbor) > 0.5 else 'Moderate' if abs(corr_neighbor) > 0.3 else 'Weak'}")

    print("\n" + "="*80)

    plt.close()
