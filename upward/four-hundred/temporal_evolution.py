"""
400m Olympic Performance: Temporal Evolution & Historical Trends
Analysis of performance changes across Olympic history
"""

import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.gridspec import GridSpec
from scipy import stats
from scipy.interpolate import make_interp_spline
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
    medal_map = {'Gold': '1', 'Silver': '2', 'Bronze': '3', '0': '0'}
    df['Medal'] = df['Medal'].astype(str).map(lambda x: medal_map.get(x, '0'))

    df = df[df['Height'] > 0]
    df = df[df['Weight'] > 0]

    print(f"Analyzing {len(df)} athletes across {df['Year'].nunique()} Olympic Games")

    # ============================================================================
    # CREATE FIGURE
    # ============================================================================

    fig = plt.figure(figsize=(22, 18))
    gs = GridSpec(4, 3, figure=fig, hspace=0.4, wspace=0.35)

    colors = {
        'gold': '#FFD700',
        'silver': '#C0C0C0',
        'bronze': '#CD7F32',
        'trend': '#E63946',
        'primary': '#457B9D',
        'secondary': '#1D3557',
        'accent': '#F1FAEE'
    }

    # ============================================================================
    # PANEL A: Height Evolution Over Time
    # ============================================================================

    ax1 = fig.add_subplot(gs[0, 0])

    years = sorted(df['Year'].unique())
    height_stats = []

    for year in years:
        year_data = df[df['Year'] == year]
        medalists = year_data[year_data['Medal'].isin(['1', '2', '3'])]
        non_medalists = year_data[year_data['Medal'] == '0']

        height_stats.append({
            'year': year,
            'med_mean': medalists['Height'].mean() if len(medalists) > 0 else np.nan,
            'med_std': medalists['Height'].std() if len(medalists) > 0 else np.nan,
            'non_med_mean': non_medalists['Height'].mean() if len(non_medalists) > 0 else np.nan,
            'non_med_std': non_medalists['Height'].std() if len(non_medalists) > 0 else np.nan,
            'overall_mean': year_data['Height'].mean()
        })

    height_df = pd.DataFrame(height_stats)

    # Plot with error bands
    ax1.plot(height_df['year'], height_df['med_mean'], 'o-',
            linewidth=3, markersize=8, color=colors['gold'],
            label='Medalists', alpha=0.8)
    ax1.fill_between(height_df['year'],
                    height_df['med_mean'] - height_df['med_std'],
                    height_df['med_mean'] + height_df['med_std'],
                    alpha=0.2, color=colors['gold'])

    ax1.plot(height_df['year'], height_df['non_med_mean'], 's-',
            linewidth=3, markersize=8, color=colors['primary'],
            label='Non-Medalists', alpha=0.8)
    ax1.fill_between(height_df['year'],
                    height_df['non_med_mean'] - height_df['non_med_std'],
                    height_df['non_med_mean'] + height_df['non_med_std'],
                    alpha=0.2, color=colors['primary'])

    # Add trend line
    z = np.polyfit(height_df['year'].dropna(), height_df['overall_mean'].dropna(), 1)
    p = np.poly1d(z)
    ax1.plot(height_df['year'], p(height_df['year']), '--',
            linewidth=2, color=colors['trend'], alpha=0.7,
            label=f'Trend: +{z[0]:.2f} cm/year')

    ax1.set_xlabel('Olympic Year', fontweight='bold', fontsize=12)
    ax1.set_ylabel('Height (cm)', fontweight='bold', fontsize=12)
    ax1.set_title('A. Height Evolution Across Olympic History',
                fontweight='bold', loc='left', fontsize=14)
    ax1.legend(loc='upper left', fontsize=9)
    ax1.grid(True, alpha=0.3)

    # Add annotation for significant changes
    max_height_year = height_df.loc[height_df['overall_mean'].idxmax(), 'year']
    max_height = height_df['overall_mean'].max()
    ax1.annotate(f'Peak: {max_height:.1f} cm\n({int(max_height_year)})',
                xy=(max_height_year, max_height),
                xytext=(max_height_year-10, max_height+2),
                arrowprops=dict(arrowstyle='->', color='red', lw=2),
                fontsize=9, fontweight='bold',
                bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.5))

    # ============================================================================
    # PANEL B: Weight Evolution Over Time
    # ============================================================================

    ax2 = fig.add_subplot(gs[0, 1])

    weight_stats = []

    for year in years:
        year_data = df[df['Year'] == year]
        medalists = year_data[year_data['Medal'].isin(['1', '2', '3'])]
        non_medalists = year_data[year_data['Medal'] == '0']

        weight_stats.append({
            'year': year,
            'med_mean': medalists['Weight'].mean() if len(medalists) > 0 else np.nan,
            'med_std': medalists['Weight'].std() if len(medalists) > 0 else np.nan,
            'non_med_mean': non_medalists['Weight'].mean() if len(non_medalists) > 0 else np.nan,
            'non_med_std': non_medalists['Weight'].std() if len(non_medalists) > 0 else np.nan,
            'overall_mean': year_data['Weight'].mean()
        })

    weight_df = pd.DataFrame(weight_stats)

    ax2.plot(weight_df['year'], weight_df['med_mean'], 'o-',
            linewidth=3, markersize=8, color=colors['gold'],
            label='Medalists', alpha=0.8)
    ax2.fill_between(weight_df['year'],
                    weight_df['med_mean'] - weight_df['med_std'],
                    weight_df['med_mean'] + weight_df['med_std'],
                    alpha=0.2, color=colors['gold'])

    ax2.plot(weight_df['year'], weight_df['non_med_mean'], 's-',
            linewidth=3, markersize=8, color=colors['primary'],
            label='Non-Medalists', alpha=0.8)
    ax2.fill_between(weight_df['year'],
                    weight_df['non_med_mean'] - weight_df['non_med_std'],
                    weight_df['non_med_mean'] + weight_df['non_med_std'],
                    alpha=0.2, color=colors['primary'])

    # Trend line
    z = np.polyfit(weight_df['year'].dropna(), weight_df['overall_mean'].dropna(), 1)
    p = np.poly1d(z)
    ax2.plot(weight_df['year'], p(weight_df['year']), '--',
            linewidth=2, color=colors['trend'], alpha=0.7,
            label=f'Trend: +{z[0]:.2f} kg/year')

    ax2.set_xlabel('Olympic Year', fontweight='bold', fontsize=12)
    ax2.set_ylabel('Weight (kg)', fontweight='bold', fontsize=12)
    ax2.set_title('B. Weight Evolution Across Olympic History',
                fontweight='bold', loc='left', fontsize=14)
    ax2.legend(loc='upper left', fontsize=9)
    ax2.grid(True, alpha=0.3)

    # ============================================================================
    # PANEL C: BMI Evolution Over Time
    # ============================================================================

    ax3 = fig.add_subplot(gs[0, 2])

    bmi_stats = []

    for year in years:
        year_data = df[df['Year'] == year]
        medalists = year_data[year_data['Medal'].isin(['1', '2', '3'])]
        non_medalists = year_data[year_data['Medal'] == '0']

        bmi_stats.append({
            'year': year,
            'med_mean': medalists['bmi'].mean() if len(medalists) > 0 else np.nan,
            'med_std': medalists['bmi'].std() if len(medalists) > 0 else np.nan,
            'non_med_mean': non_medalists['bmi'].mean() if len(non_medalists) > 0 else np.nan,
            'overall_mean': year_data['bmi'].mean()
        })

    bmi_df = pd.DataFrame(bmi_stats)

    ax3.plot(bmi_df['year'], bmi_df['med_mean'], 'o-',
            linewidth=3, markersize=8, color=colors['gold'],
            label='Medalists', alpha=0.8)
    ax3.plot(bmi_df['year'], bmi_df['non_med_mean'], 's-',
            linewidth=3, markersize=8, color=colors['primary'],
            label='Non-Medalists', alpha=0.8)

    # Optimal BMI range
    ax3.axhspan(21, 24, alpha=0.2, color='green', label='Optimal Range')

    ax3.set_xlabel('Olympic Year', fontweight='bold', fontsize=12)
    ax3.set_ylabel('BMI (kg/m²)', fontweight='bold', fontsize=12)
    ax3.set_title('C. BMI Evolution Across Olympic History',
                fontweight='bold', loc='left', fontsize=14)
    ax3.legend(loc='upper left', fontsize=9)
    ax3.grid(True, alpha=0.3)

    # ============================================================================
    # PANEL D: Age Distribution Evolution
    # ============================================================================

    ax4 = fig.add_subplot(gs[1, 0])

    age_stats = []

    for year in years:
        year_data = df[df['Year'] == year]
        medalists = year_data[year_data['Medal'].isin(['1', '2', '3'])]

        age_stats.append({
            'year': year,
            'med_mean': medalists['Age'].mean() if len(medalists) > 0 else np.nan,
            'med_median': medalists['Age'].median() if len(medalists) > 0 else np.nan,
            'med_min': medalists['Age'].min() if len(medalists) > 0 else np.nan,
            'med_max': medalists['Age'].max() if len(medalists) > 0 else np.nan,
            'overall_mean': year_data['Age'].mean()
        })

    age_df = pd.DataFrame(age_stats)

    ax4.plot(age_df['year'], age_df['med_mean'], 'o-',
            linewidth=3, markersize=8, color=colors['gold'],
            label='Mean Age (Medalists)', alpha=0.8)
    ax4.fill_between(age_df['year'],
                    age_df['med_min'],
                    age_df['med_max'],
                    alpha=0.2, color=colors['gold'],
                    label='Age Range')

    # Add peak performance age band
    ax4.axhspan(23, 28, alpha=0.15, color='green', label='Peak Age Range')

    ax4.set_xlabel('Olympic Year', fontweight='bold', fontsize=12)
    ax4.set_ylabel('Age (years)', fontweight='bold', fontsize=12)
    ax4.set_title('D. Age Distribution of Medalists Over Time',
                fontweight='bold', loc='left', fontsize=14)
    ax4.legend(loc='upper left', fontsize=9)
    ax4.grid(True, alpha=0.3)

    # ============================================================================
    # PANEL E: Body Composition Evolution
    # ============================================================================

    ax5 = fig.add_subplot(gs[1, 1])

    body_comp_stats = []

    for year in years:
        year_data = df[df['Year'] == year]
        medalists = year_data[year_data['Medal'].isin(['1', '2', '3'])]

        body_comp_stats.append({
            'year': year,
            'lean_mass': medalists['lean_body_mass'].mean() if len(medalists) > 0 else np.nan,
            'body_fat': medalists['body_fat_percentage'].mean() if len(medalists) > 0 else np.nan,
            'muscle_mass': medalists['skeletal_muscle_mass'].mean() if len(medalists) > 0 else np.nan
        })

    comp_df = pd.DataFrame(body_comp_stats)

    ax5_twin = ax5.twinx()

    line1 = ax5.plot(comp_df['year'], comp_df['lean_mass'], 'o-',
                    linewidth=3, markersize=8, color=colors['primary'],
                    label='Lean Body Mass (kg)', alpha=0.8)
    line2 = ax5.plot(comp_df['year'], comp_df['muscle_mass'], 's-',
                    linewidth=3, markersize=8, color=colors['secondary'],
                    label='Muscle Mass (kg)', alpha=0.8)

    line3 = ax5_twin.plot(comp_df['year'], comp_df['body_fat'], '^-',
                        linewidth=3, markersize=8, color=colors['trend'],
                        label='Body Fat (%)', alpha=0.8)

    ax5.set_xlabel('Olympic Year', fontweight='bold', fontsize=12)
    ax5.set_ylabel('Mass (kg)', fontweight='bold', fontsize=12, color=colors['primary'])
    ax5_twin.set_ylabel('Body Fat (%)', fontweight='bold', fontsize=12, color=colors['trend'])

    ax5.set_title('E. Body Composition Evolution (Medalists)',
                fontweight='bold', loc='left', fontsize=14)

    # Combine legends
    lines = line1 + line2 + line3
    labels = [l.get_label() for l in lines]
    ax5.legend(lines, labels, loc='upper left', fontsize=9)

    ax5.grid(True, alpha=0.3)
    ax5.tick_params(axis='y', labelcolor=colors['primary'])
    ax5_twin.tick_params(axis='y', labelcolor=colors['trend'])

    # ============================================================================
    # PANEL F: Participation Growth
    # ============================================================================

    ax6 = fig.add_subplot(gs[1, 2])

    participation = []

    for year in years:
        year_data = df[df['Year'] == year]

        participation.append({
            'year': year,
            'total': len(year_data),
            'medalists': len(year_data[year_data['Medal'].isin(['1', '2', '3'])]),
            'countries': year_data['NOC'].nunique()
        })

    part_df = pd.DataFrame(participation)

    ax6_twin = ax6.twinx()

    bar1 = ax6.bar(part_df['year'], part_df['total'],
                alpha=0.6, color=colors['primary'], label='Total Athletes')
    line1 = ax6_twin.plot(part_df['year'], part_df['countries'], 'ro-',
                        linewidth=3, markersize=10, label='Countries',
                        markeredgecolor='white', markeredgewidth=2)

    ax6.set_xlabel('Olympic Year', fontweight='bold', fontsize=12)
    ax6.set_ylabel('Number of Athletes', fontweight='bold', fontsize=12, color=colors['primary'])
    ax6_twin.set_ylabel('Number of Countries', fontweight='bold', fontsize=12, color='red')

    ax6.set_title('F. Participation Growth Over Time',
                fontweight='bold', loc='left', fontsize=14)

    # Combine legends
    lines = [bar1] + line1
    labels = ['Total Athletes', 'Countries']
    ax6.legend(lines, labels, loc='upper left', fontsize=9)

    ax6.grid(True, alpha=0.3, axis='y')
    ax6.tick_params(axis='y', labelcolor=colors['primary'])
    ax6_twin.tick_params(axis='y', labelcolor='red')

    # ============================================================================
    # PANEL G: Decade-by-Decade Comparison
    # ============================================================================

    ax7 = fig.add_subplot(gs[2, :2])

    # Group by decades
    df['Decade'] = (df['Year'] // 10) * 10

    decades = sorted(df['Decade'].unique())
    decade_labels = [f"{d}s" for d in decades]

    metrics = ['Height', 'Weight', 'bmi', 'lean_body_mass']
    metric_labels = ['Height\n(cm)', 'Weight\n(kg)', 'BMI\n(kg/m²)', 'Lean Mass\n(kg)']

    # Normalize data for comparison
    decade_data = []
    for decade in decades:
        decade_athletes = df[df['Decade'] == decade]
        medalists = decade_athletes[decade_athletes['Medal'].isin(['1', '2', '3'])]

        if len(medalists) > 0:
            decade_data.append([
                medalists['Height'].mean(),
                medalists['Weight'].mean(),
                medalists['bmi'].mean(),
                medalists['lean_body_mass'].mean()
            ])
        else:
            decade_data.append([np.nan] * 4)

    decade_array = np.array(decade_data)

    # Normalize each metric to 0-1 scale for comparison
    normalized_data = np.zeros_like(decade_array)
    for i in range(decade_array.shape[1]):
        col = decade_array[:, i]
        valid = ~np.isnan(col)
        if valid.any():
            min_val = np.nanmin(col)
            max_val = np.nanmax(col)
            if max_val > min_val:
                normalized_data[:, i] = (col - min_val) / (max_val - min_val)

    x = np.arange(len(metrics))
    width = 0.8 / len(decades)

    colors_decades = plt.cm.viridis(np.linspace(0, 1, len(decades)))

    for i, (decade, color) in enumerate(zip(decades, colors_decades)):
        offset = (i - len(decades)/2) * width + width/2
        bars = ax7.bar(x + offset, normalized_data[i], width,
                    label=f'{decade}s', color=color, alpha=0.8)

    ax7.set_ylabel('Normalized Score (0-1)', fontweight='bold', fontsize=12)
    ax7.set_title('G. Decade-by-Decade Evolution (Normalized Metrics)',
                fontweight='bold', loc='left', fontsize=14)
    ax7.set_xticks(x)
    ax7.set_xticklabels(metric_labels)
    ax7.legend(loc='upper left', fontsize=8, ncol=2)
    ax7.grid(True, alpha=0.3, axis='y')

    # ============================================================================
    # PANEL H: Rate of Change Analysis
    # ============================================================================

    ax8 = fig.add_subplot(gs[2, 2])

    # Calculate year-over-year changes
    changes = {
        'Height': [],
        'Weight': [],
        'BMI': [],
        'Lean Mass': []
    }

    for i in range(1, len(years)):
        prev_year = years[i-1]
        curr_year = years[i]

        prev_data = df[df['Year'] == prev_year]
        curr_data = df[df['Year'] == curr_year]

        prev_med = prev_data[prev_data['Medal'].isin(['1', '2', '3'])]
        curr_med = curr_data[curr_data['Medal'].isin(['1', '2', '3'])]

        if len(prev_med) > 0 and len(curr_med) > 0:
            changes['Height'].append(
                (curr_med['Height'].mean() - prev_med['Height'].mean()) / (curr_year - prev_year)
            )
            changes['Weight'].append(
                (curr_med['Weight'].mean() - prev_med['Weight'].mean()) / (curr_year - prev_year)
            )
            changes['BMI'].append(
                (curr_med['bmi'].mean() - prev_med['bmi'].mean()) / (curr_year - prev_year)
            )
            changes['Lean Mass'].append(
                (curr_med['lean_body_mass'].mean() - prev_med['lean_body_mass'].mean()) / (curr_year - prev_year)
            )

    # Box plot of changes
    change_data = [changes['Height'], changes['Weight'], changes['BMI'], changes['Lean Mass']]
    change_labels = ['Height\n(cm/yr)', 'Weight\n(kg/yr)', 'BMI\n(kg/m²/yr)', 'Lean Mass\n(kg/yr)']

    bp = ax8.boxplot(change_data, tick_labels=change_labels, patch_artist=True,
                    showmeans=True, meanline=True)

    for patch, color in zip(bp['boxes'], [colors['primary'], colors['secondary'],
                                        colors['trend'], colors['gold']]):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)

    ax8.axhline(y=0, color='black', linestyle='--', linewidth=2, alpha=0.5)

    ax8.set_ylabel('Rate of Change (per year)', fontweight='bold', fontsize=12)
    ax8.set_title('H. Rate of Change Analysis (Year-over-Year)',
                fontweight='bold', loc='left', fontsize=14)
    ax8.grid(True, alpha=0.3, axis='y')

    # ============================================================================
    # PANEL I: Generational Shifts
    # ============================================================================

    ax9 = fig.add_subplot(gs[3, :])

    # Define generations
    generations = [
        ('Early Era', 1896, 1936),
        ('Post-War', 1948, 1968),
        ('Modern Era', 1972, 1992),
        ('Contemporary', 1996, 2016)
    ]

    gen_stats = []

    for gen_name, start, end in generations:
        gen_data = df[(df['Year'] >= start) & (df['Year'] <= end)]
        medalists = gen_data[gen_data['Medal'].isin(['1', '2', '3'])]

        if len(medalists) > 0:
            gen_stats.append({
                'generation': gen_name,
                'Height': medalists['Height'].mean(),
                'Weight': medalists['Weight'].mean(),
                'bmi': medalists['bmi'].mean(),
                'Age': medalists['Age'].mean(),
                'lean_body_mass': medalists['lean_body_mass'].mean(),
                'body_fat_percentage': medalists['body_fat_percentage'].mean(),
                'n': len(medalists)
            })

    gen_df = pd.DataFrame(gen_stats)

    # Create grouped bar chart
    x = np.arange(len(gen_df))
    width = 0.12

    metrics_gen = ['Height', 'Weight', 'bmi', 'Age', 'lean_body_mass', 'body_fat_percentage']
    labels_gen = ['Height\n(cm)', 'Weight\n(kg)', 'BMI', 'Age\n(yrs)',
                'Lean Mass\n(kg)', 'Body Fat\n(%)']
    colors_gen = ['#E63946', '#F1FAEE', '#A8DADC', '#457B9D', '#1D3557', '#F77F00']

    # Normalize for visualization
    normalized_gen = gen_df[metrics_gen].copy()
    for col in metrics_gen:
        min_val = normalized_gen[col].min()
        max_val = normalized_gen[col].max()
        if max_val > min_val:
            normalized_gen[col] = (normalized_gen[col] - min_val) / (max_val - min_val)

    for i, (metric, label, color) in enumerate(zip(metrics_gen, labels_gen, colors_gen)):
        offset = (i - len(metrics_gen)/2) * width + width/2
        bars = ax9.bar(x + offset, normalized_gen[metric], width,
                    label=label, color=color, alpha=0.8)

    ax9.set_ylabel('Normalized Score (0-1)', fontweight='bold', fontsize=12)
    ax9.set_title('I. Generational Shifts in Athlete Characteristics (Medalists)',
                fontweight='bold', loc='left', fontsize=14)
    ax9.set_xticks(x)
    ax9.set_xticklabels([f"{row['generation']}\n(n={int(row['n'])})"
                        for _, row in gen_df.iterrows()])
    ax9.legend(loc='upper left', fontsize=9, ncol=6)
    ax9.grid(True, alpha=0.3, axis='y')

    # Add sample sizes
    for i, row in gen_df.iterrows():
        ax9.text(i, -0.15, f"Years: {generations[i][1]}-{generations[i][2]}",
                ha='center', fontsize=8, style='italic')

    # ============================================================================
    # Overall title
    # ============================================================================

    fig.suptitle('400m Olympic Performance: Temporal Evolution & Historical Trends\n' +
                'Comprehensive Analysis of Athlete Characteristics Across Olympic History',
                fontsize=16, fontweight='bold', y=0.997)

    # Save to figures directory
    os.makedirs('figures', exist_ok=True)
    plt.savefig('figures/400m_temporal_evolution.png', dpi=300, bbox_inches='tight')
    print("✓ Figure saved: figures/400m_temporal_evolution.png")

    plt.close()
