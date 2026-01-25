"""
400m Olympic Performance: Athlete Physiological Analysis
Comprehensive visualization of anthropometric and physiological data
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

    # Load from same folder
    data_path = '400m_athletes_complete_biometrics.json'

    with open(data_path, 'r') as f:
        athletes_data = json.load(f)

    df = pd.DataFrame(athletes_data)

    # Convert Medal to standard format (map Gold/Silver/Bronze to 1/2/3)
    medal_map = {'Gold': 1, 'Silver': 2, 'Bronze': 3, '0': 0, 0: 0, '1': 1, '2': 2, '3': 3}
    df['Medal_numeric'] = df['Medal'].astype(str).map(lambda x: medal_map.get(x, 0))
    df['Medal'] = df['Medal'].astype(str).map(lambda x: str(medal_map.get(x, 0)))

    # Filter for valid data
    df = df[df['Height'] > 0]
    df = df[df['Weight'] > 0]

    print(f"Loaded {len(df)} athletes")
    print(f"Years: {df['Year'].min()} - {df['Year'].max()}")
    print(f"Medal distribution:\n{df['Medal'].value_counts()}")

    # ============================================================================
    # CREATE FIGURE
    # ============================================================================

    fig = plt.figure(figsize=(20, 16))
    gs = GridSpec(3, 3, figure=fig, hspace=0.35, wspace=0.35)

    colors = {
        'gold': '#FFD700',
        'silver': '#C0C0C0',
        'bronze': '#CD7F32',
        'no_medal': '#4A90E2',
        'primary': '#2E86AB',
        'secondary': '#A23B72'
    }

    # ============================================================================
    # PANEL A: Height vs Weight by Medal Status
    # ============================================================================

    ax1 = fig.add_subplot(gs[0, 0])

    medal_groups = df.groupby('Medal')
    for medal, group in medal_groups:
        if medal == '3':  # Gold
            color = colors['gold']
            label = 'Gold'
            marker = '*'
            size = 200
            zorder = 4
        elif medal == '2':  # Silver
            color = colors['silver']
            label = 'Silver'
            marker = 'D'
            size = 150
            zorder = 3
        elif medal == '1':  # Bronze
            color = colors['bronze']
            label = 'Bronze'
            marker = '^'
            size = 150
            zorder = 2
        else:
            color = colors['no_medal']
            label = 'No Medal'
            marker = 'o'
            size = 50
            zorder = 1

        ax1.scatter(group['Height'], group['Weight'],
                s=size, alpha=0.6, color=color, label=label,
                marker=marker, edgecolors='black', linewidth=1, zorder=zorder)

    ax1.set_xlabel('Height (cm)', fontweight='bold', fontsize=12)
    ax1.set_ylabel('Weight (kg)', fontweight='bold', fontsize=12)
    ax1.set_title('A. Anthropometric Profile: Height vs Weight by Medal Status',
                fontweight='bold', loc='left', fontsize=13)
    ax1.legend(loc='upper left', fontsize=9)
    ax1.grid(True, alpha=0.3)

    # Add regression line
    z = np.polyfit(df['Height'], df['Weight'], 1)
    p = np.poly1d(z)
    x_line = np.linspace(df['Height'].min(), df['Height'].max(), 100)
    ax1.plot(x_line, p(x_line), "r--", alpha=0.5, linewidth=2, label='Trend')

    # ============================================================================
    # PANEL B: BMI Distribution by Medal Status
    # ============================================================================

    ax2 = fig.add_subplot(gs[0, 1])

    medal_order = ['0', '1', '2', '3']
    medal_labels = ['No Medal', 'Bronze', 'Silver', 'Gold']
    medal_colors = [colors['no_medal'], colors['bronze'], colors['silver'], colors['gold']]

    bmi_data = [df[df['Medal'] == m]['bmi'].dropna() for m in medal_order]

    parts = ax2.violinplot(bmi_data, positions=range(len(medal_order)),
                        showmeans=True, showmedians=True, showextrema=True)

    for pc, color in zip(parts['bodies'], medal_colors):
        pc.set_facecolor(color)
        pc.set_alpha(0.6)

    ax2.set_xticks(range(len(medal_order)))
    ax2.set_xticklabels(medal_labels, rotation=45)
    ax2.set_ylabel('BMI (kg/m²)', fontweight='bold', fontsize=12)
    ax2.set_title('B. BMI Distribution by Medal Status',
                fontweight='bold', loc='left', fontsize=13)
    ax2.grid(True, alpha=0.3, axis='y')

    # Add mean values
    for i, data in enumerate(bmi_data):
        if len(data) > 0:
            mean_val = np.mean(data)
            ax2.text(i, mean_val, f'{mean_val:.1f}',
                    ha='center', va='bottom', fontsize=8, fontweight='bold',
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))

    # ============================================================================
    # PANEL C: Body Composition Analysis
    # ============================================================================

    ax3 = fig.add_subplot(gs[0, 2])

    # Select key body composition metrics
    composition_metrics = ['lean_body_mass', 'body_fat_percentage', 'skeletal_muscle_mass']
    composition_labels = ['Lean Mass (kg)', 'Body Fat (%)', 'Muscle Mass (kg)']

    medalists = df[df['Medal'].isin(['1', '2', '3'])]
    non_medalists = df[df['Medal'] == '0']

    x = np.arange(len(composition_metrics))
    width = 0.35

    means_medalists = [medalists[m].mean() for m in composition_metrics]
    means_non_medalists = [non_medalists[m].mean() for m in composition_metrics]

    bars1 = ax3.bar(x - width/2, means_medalists, width,
                label='Medalists', color=colors['gold'], alpha=0.8)
    bars2 = ax3.bar(x + width/2, means_non_medalists, width,
                label='Non-Medalists', color=colors['no_medal'], alpha=0.8)

    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}',
                    ha='center', va='bottom', fontsize=9)

    ax3.set_ylabel('Value', fontweight='bold', fontsize=12)
    ax3.set_title('C. Body Composition: Medalists vs Non-Medalists',
                fontweight='bold', loc='left', fontsize=13)
    ax3.set_xticks(x)
    ax3.set_xticklabels(composition_labels, rotation=45, ha='right')
    ax3.legend(loc='upper right', fontsize=9)
    ax3.grid(True, alpha=0.3, axis='y')

    # ============================================================================
    # PANEL D: Leg Mass Components
    # ============================================================================

    ax4 = fig.add_subplot(gs[1, 0])

    leg_components = ['foot_mass', 'leg_mass', 'thigh_mass', 'total_leg_mass']
    leg_labels = ['Foot', 'Leg', 'Thigh', 'Total Leg']

    means_med = [medalists[c].mean() for c in leg_components]
    means_non_med = [non_medalists[c].mean() for c in leg_components]

    x = np.arange(len(leg_components))

    bars1 = ax4.bar(x - width/2, means_med, width,
                label='Medalists', color=colors['primary'], alpha=0.8)
    bars2 = ax4.bar(x + width/2, means_non_med, width,
                label='Non-Medalists', color=colors['secondary'], alpha=0.8)

    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.2f}',
                    ha='center', va='bottom', fontsize=8)

    ax4.set_ylabel('Mass (kg)', fontweight='bold', fontsize=12)
    ax4.set_title('D. Leg Mass Components Analysis',
                fontweight='bold', loc='left', fontsize=13)
    ax4.set_xticks(x)
    ax4.set_xticklabels(leg_labels, rotation=45)
    ax4.legend(loc='upper left', fontsize=9)
    ax4.grid(True, alpha=0.3, axis='y')

    # ============================================================================
    # PANEL E: Age Distribution Over Time
    # ============================================================================

    ax5 = fig.add_subplot(gs[1, 1])

    years = sorted(df['Year'].unique())
    age_by_year_medal = []
    age_by_year_no_medal = []

    for year in years:
        year_data = df[df['Year'] == year]
        medalists_year = year_data[year_data['Medal'].isin(['1', '2', '3'])]
        non_medalists_year = year_data[year_data['Medal'] == '0']

        if len(medalists_year) > 0:
            age_by_year_medal.append(medalists_year['Age'].mean())
        else:
            age_by_year_medal.append(np.nan)

        if len(non_medalists_year) > 0:
            age_by_year_no_medal.append(non_medalists_year['Age'].mean())
        else:
            age_by_year_no_medal.append(np.nan)

    ax5.plot(years, age_by_year_medal, 'o-', linewidth=2.5, markersize=8,
            color=colors['gold'], label='Medalists', alpha=0.8)
    ax5.plot(years, age_by_year_no_medal, 's-', linewidth=2.5, markersize=8,
            color=colors['no_medal'], label='Non-Medalists', alpha=0.8)

    ax5.set_xlabel('Olympic Year', fontweight='bold', fontsize=12)
    ax5.set_ylabel('Mean Age (years)', fontweight='bold', fontsize=12)
    ax5.set_title('E. Age Trends Over Olympic History',
                fontweight='bold', loc='left', fontsize=13)
    ax5.legend(loc='upper left', fontsize=9)
    ax5.grid(True, alpha=0.3)

    # ============================================================================
    # PANEL F: Correlation Heatmap (Key Metrics)
    # ============================================================================

    ax6 = fig.add_subplot(gs[1, 2])

    # Select key metrics for correlation
    key_metrics = ['Height', 'Weight', 'bmi', 'lean_body_mass',
                'body_fat_percentage', 'skeletal_muscle_mass',
                'total_leg_mass', 'Medal_numeric']

    corr_data = df[key_metrics].corr()

    im = ax6.imshow(corr_data, cmap='coolwarm', aspect='auto', vmin=-1, vmax=1)

    ax6.set_xticks(np.arange(len(key_metrics)))
    ax6.set_yticks(np.arange(len(key_metrics)))
    ax6.set_xticklabels([m.replace('_', '\n') for m in key_metrics],
                        rotation=45, ha='right', fontsize=8)
    ax6.set_yticklabels([m.replace('_', '\n') for m in key_metrics], fontsize=8)

    # Add correlation values
    for i in range(len(key_metrics)):
        for j in range(len(key_metrics)):
            text = ax6.text(j, i, f'{corr_data.iloc[i, j]:.2f}',
                        ha="center", va="center",
                        color="white" if abs(corr_data.iloc[i, j]) > 0.5 else "black",
                        fontsize=7)

    ax6.set_title('F. Correlation Matrix (Key Physiological Metrics)',
                fontweight='bold', loc='left', fontsize=13, pad=10)

    cbar = plt.colorbar(im, ax=ax6)
    cbar.set_label('Correlation Coefficient', fontweight='bold')

    # ============================================================================
    # PANEL G: Body Surface Area vs Performance
    # ============================================================================

    ax7 = fig.add_subplot(gs[2, 0])

    for medal, group in medal_groups:
        if medal == '3':
            color = colors['gold']
            label = 'Gold'
            marker = '*'
            size = 200
        elif medal == '2':
            color = colors['silver']
            label = 'Silver'
            marker = 'D'
            size = 150
        elif medal == '1':
            color = colors['bronze']
            label = 'Bronze'
            marker = '^'
            size = 150
        else:
            color = colors['no_medal']
            label = 'No Medal'
            marker = 'o'
            size = 50

        ax7.scatter(group['body_surface_area'], group['theoretical_max_speed'],
                s=size, alpha=0.6, color=color, label=label,
                marker=marker, edgecolors='black', linewidth=1)

    ax7.set_xlabel('Body Surface Area (m²)', fontweight='bold', fontsize=12)
    ax7.set_ylabel('Theoretical Max Speed (m/s)', fontweight='bold', fontsize=12)
    ax7.set_title('G. Body Surface Area vs Theoretical Max Speed',
                fontweight='bold', loc='left', fontsize=13)
    ax7.legend(loc='best', fontsize=9)
    ax7.grid(True, alpha=0.3)

    # ============================================================================
    # PANEL H: Trunk Mass Distribution
    # ============================================================================

    ax8 = fig.add_subplot(gs[2, 1])

    trunk_components = ['thorax_mass', 'abdomen_mass', 'pelvis_mass']
    trunk_labels = ['Thorax', 'Abdomen', 'Pelvis']

    means_med = [medalists[c].mean() for c in trunk_components]
    means_non_med = [non_medalists[c].mean() for c in trunk_components]

    x = np.arange(len(trunk_components))

    bars1 = ax8.bar(x - width/2, means_med, width,
                label='Medalists', color=colors['primary'], alpha=0.8)
    bars2 = ax8.bar(x + width/2, means_non_med, width,
                label='Non-Medalists', color=colors['secondary'], alpha=0.8)

    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax8.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}',
                    ha='center', va='bottom', fontsize=9)

    ax8.set_ylabel('Mass (kg)', fontweight='bold', fontsize=12)
    ax8.set_title('H. Trunk Mass Components',
                fontweight='bold', loc='left', fontsize=13)
    ax8.set_xticks(x)
    ax8.set_xticklabels(trunk_labels)
    ax8.legend(loc='upper right', fontsize=9)
    ax8.grid(True, alpha=0.3, axis='y')

    # ============================================================================
    # PANEL I: Statistical Summary
    # ============================================================================

    ax9 = fig.add_subplot(gs[2, 2])
    ax9.axis('off')

    # Calculate key statistics
    n_total = len(df)
    n_medalists = len(df[df['Medal'].isin(['1', '2', '3'])])
    n_gold = len(df[df['Medal'] == '3'])
    n_silver = len(df[df['Medal'] == '2'])
    n_bronze = len(df[df['Medal'] == '1'])

    mean_height_med = medalists['Height'].mean()
    mean_height_non = non_medalists['Height'].mean()
    mean_weight_med = medalists['Weight'].mean()
    mean_weight_non = non_medalists['Weight'].mean()
    mean_bmi_med = medalists['bmi'].mean()
    mean_bmi_non = non_medalists['bmi'].mean()

    summary_text = f"""
    ATHLETE PHYSIOLOGICAL SUMMARY

    DATASET OVERVIEW:
    • Total Athletes: {n_total}
    • Medalists: {n_medalists} ({n_medalists/n_total*100:.1f}%)
        - Gold: {n_gold}
        - Silver: {n_silver}
        - Bronze: {n_bronze}
    • Olympic Years: {df['Year'].min()} - {df['Year'].max()}

    ANTHROPOMETRIC COMPARISON:

    Medalists:
    • Height: {mean_height_med:.1f} cm
    • Weight: {mean_weight_med:.1f} kg
    • BMI: {mean_bmi_med:.1f} kg/m²
    • Lean Mass: {medalists['lean_body_mass'].mean():.1f} kg
    • Body Fat: {medalists['body_fat_percentage'].mean():.1f}%

    Non-Medalists:
    • Height: {mean_height_non:.1f} cm
    • Weight: {mean_weight_non:.1f} kg
    • BMI: {mean_bmi_non:.1f} kg/m²
    • Lean Mass: {non_medalists['lean_body_mass'].mean():.1f} kg
    • Body Fat: {non_medalists['body_fat_percentage'].mean():.1f}%

    KEY FINDINGS:
    • Medalists tend to be taller (+{mean_height_med-mean_height_non:.1f} cm)
    • Higher lean body mass in medalists
    • Lower body fat percentage in medalists
    • Optimal BMI range: {medalists['bmi'].quantile(0.25):.1f}-{medalists['bmi'].quantile(0.75):.1f}
    """

    ax9.text(0.05, 0.95, summary_text, transform=ax9.transAxes,
            fontsize=9, verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3,
                    edgecolor='black', linewidth=2))

    ax9.set_title('I. Statistical Summary',
                fontweight='bold', loc='left', fontsize=13, pad=20)

    # ============================================================================
    # Overall title
    # ============================================================================

    fig.suptitle('400m Olympic Performance: Athlete Physiological Analysis\n' +
                'Comprehensive Assessment of Anthropometric and Body Composition Data',
                fontsize=16, fontweight='bold', y=0.995)

    # Save to figures directory
    os.makedirs('figures', exist_ok=True)
    plt.savefig('figures/400m_athlete_physiological_analysis.png', dpi=300, bbox_inches='tight')
    print("✓ Figure saved: figures/400m_athlete_physiological_analysis.png")

    plt.close()
