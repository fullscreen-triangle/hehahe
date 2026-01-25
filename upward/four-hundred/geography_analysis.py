"""
400m Olympic Performance: Geographic & Country Analysis
Analysis of performance patterns by country and region
"""

import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.gridspec import GridSpec
from collections import Counter
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
    # Load from correct path
    import os
    data_path = '400m_athletes_complete_biometrics.json'

    with open(data_path, 'r') as f:
        athletes_data = json.load(f)

    df = pd.DataFrame(athletes_data)

    # Convert Medal to standard format (map Gold/Silver/Bronze to 1/2/3)
    medal_map = {'Gold': '1', 'Silver': '2', 'Bronze': '3', '0': '0'}
    df['Medal'] = df['Medal'].astype(str).map(lambda x: medal_map.get(x, '0'))

    df = df[df['Height'] > 0]
    df = df[df['Weight'] > 0]

    # Regional classification (simplified)
    region_map = {
        'USA': 'North America', 'CAN': 'North America', 'MEX': 'North America',
        'JAM': 'Caribbean', 'BAH': 'Caribbean', 'TRI': 'Caribbean', 'CUB': 'Caribbean',
        'BAR': 'Caribbean', 'DOM': 'Caribbean', 'GRN': 'Caribbean',
        'GBR': 'Europe', 'FRA': 'Europe', 'GER': 'Europe', 'ITA': 'Europe',
        'ESP': 'Europe', 'POL': 'Europe', 'RUS': 'Europe', 'UKR': 'Europe',
        'BEL': 'Europe', 'NED': 'Europe', 'SWE': 'Europe', 'NOR': 'Europe',
        'DEN': 'Europe', 'FIN': 'Europe', 'SUI': 'Europe', 'AUT': 'Europe',
        'CZE': 'Europe', 'HUN': 'Europe', 'ROM': 'Europe', 'BUL': 'Europe',
        'KEN': 'Africa', 'ETH': 'Africa', 'RSA': 'Africa', 'NGR': 'Africa',
        'BOT': 'Africa', 'ZIM': 'Africa', 'UGA': 'Africa', 'TAN': 'Africa',
        'AUS': 'Oceania', 'NZL': 'Oceania',
        'CHN': 'Asia', 'JPN': 'Asia', 'KOR': 'Asia', 'IND': 'Asia',
        'BRN': 'Asia', 'QAT': 'Asia', 'KSA': 'Asia',
        'BRA': 'South America', 'ARG': 'South America', 'CHI': 'South America',
        'COL': 'South America', 'VEN': 'South America'
    }

    df['Region'] = df['NOC'].map(region_map).fillna('Other')

    print(f"Analyzing {df['NOC'].nunique()} countries across {df['Region'].nunique()} regions")

    # ============================================================================
    # CREATE FIGURE
    # ============================================================================

    fig = plt.figure(figsize=(22, 18))
    gs = GridSpec(4, 3, figure=fig, hspace=0.4, wspace=0.35)

    colors = {
        'gold': '#FFD700',
        'silver': '#C0C0C0',
        'bronze': '#CD7F32',
        'north_america': '#E63946',
        'caribbean': '#F1FAEE',
        'europe': '#457B9D',
        'africa': '#2A9D8F',
        'asia': '#E9C46A',
        'oceania': '#F4A261',
        'south_america': '#264653'
    }

    # ============================================================================
    # PANEL A: Medal Count by Country (Top 20)
    # ============================================================================

    ax1 = fig.add_subplot(gs[0, :2])

    medal_counts = df[df['Medal'].isin(['1', '2', '3'])].groupby('NOC').size().sort_values(ascending=False).head(20)

    bars = ax1.barh(range(len(medal_counts)), medal_counts.values, color=colors['gold'], alpha=0.8)

    # Color code by region
    for i, (country, count) in enumerate(medal_counts.items()):
        region = df[df['NOC'] == country]['Region'].iloc[0]
        region_color = colors.get(region.lower().replace(' ', '_'), colors['gold'])
        bars[i].set_color(region_color)
        bars[i].set_alpha(0.8)

    ax1.set_yticks(range(len(medal_counts)))
    ax1.set_yticklabels(medal_counts.index)
    ax1.set_xlabel('Total Medals', fontweight='bold', fontsize=12)
    ax1.set_title('A. Top 20 Countries by Medal Count (All-Time)',
                fontweight='bold', loc='left', fontsize=14)
    ax1.grid(True, alpha=0.3, axis='x')

    # Add value labels
    for i, (country, count) in enumerate(medal_counts.items()):
        ax1.text(count + 0.5, i, f'{int(count)}',
                va='center', fontweight='bold', fontsize=9)

    # ============================================================================
    # PANEL B: Regional Medal Distribution
    # ============================================================================

    ax2 = fig.add_subplot(gs[0, 2])

    region_medals = df[df['Medal'].isin(['1', '2', '3'])].groupby('Region').size().sort_values(ascending=False)

    colors_pie = [colors.get(r.lower().replace(' ', '_'), '#CCCCCC') for r in region_medals.index]

    wedges, texts, autotexts = ax2.pie(region_medals.values, labels=region_medals.index,
                                        autopct='%1.1f%%', colors=colors_pie, startangle=90)

    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
        autotext.set_fontsize(9)

    ax2.set_title('B. Medal Distribution by Region',
                fontweight='bold', loc='left', fontsize=14, pad=20)

    # ============================================================================
    # PANEL C: Anthropometric Comparison by Region
    # ============================================================================

    ax3 = fig.add_subplot(gs[1, 0])

    regions = df['Region'].unique()
    region_heights = []
    region_labels = []

    for region in sorted(regions):
        region_data = df[df['Region'] == region]
        medalists = region_data[region_data['Medal'].isin(['1', '2', '3'])]
        if len(medalists) > 0:
            region_heights.append(medalists['Height'].values)
            region_labels.append(f"{region}\n(n={len(medalists)})")

    bp = ax3.boxplot(region_heights, labels=region_labels, patch_artist=True,
                    showmeans=True, meanline=True)

    for i, (patch, region) in enumerate(zip(bp['boxes'], sorted(regions))):
        region_color = colors.get(region.lower().replace(' ', '_'), '#CCCCCC')
        patch.set_facecolor(region_color)
        patch.set_alpha(0.6)

    ax3.set_ylabel('Height (cm)', fontweight='bold', fontsize=12)
    ax3.set_title('C. Height Distribution by Region (Medalists)',
                fontweight='bold', loc='left', fontsize=14)
    ax3.grid(True, alpha=0.3, axis='y')
    plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45, ha='right')

    # ============================================================================
    # PANEL D: Weight Distribution by Region
    # ============================================================================

    ax4 = fig.add_subplot(gs[1, 1])

    region_weights = []

    for region in sorted(regions):
        region_data = df[df['Region'] == region]
        medalists = region_data[region_data['Medal'].isin(['1', '2', '3'])]
        if len(medalists) > 0:
            region_weights.append(medalists['Weight'].values)

    bp = ax4.boxplot(region_weights, labels=region_labels, patch_artist=True,
                    showmeans=True, meanline=True)

    for i, (patch, region) in enumerate(zip(bp['boxes'], sorted(regions))):
        region_color = colors.get(region.lower().replace(' ', '_'), '#CCCCCC')
        patch.set_facecolor(region_color)
        patch.set_alpha(0.6)

    ax4.set_ylabel('Weight (kg)', fontweight='bold', fontsize=12)
    ax4.set_title('D. Weight Distribution by Region (Medalists)',
                fontweight='bold', loc='left', fontsize=14)
    ax4.grid(True, alpha=0.3, axis='y')
    plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45, ha='right')

    # ============================================================================
    # PANEL E: BMI Comparison by Region
    # ============================================================================

    ax5 = fig.add_subplot(gs[1, 2])

    region_bmi = []

    for region in sorted(regions):
        region_data = df[df['Region'] == region]
        medalists = region_data[region_data['Medal'].isin(['1', '2', '3'])]
        if len(medalists) > 0:
            region_bmi.append(medalists['bmi'].values)

    bp = ax5.boxplot(region_bmi, labels=region_labels, patch_artist=True,
                    showmeans=True, meanline=True)

    for i, (patch, region) in enumerate(zip(bp['boxes'], sorted(regions))):
        region_color = colors.get(region.lower().replace(' ', '_'), '#CCCCCC')
        patch.set_facecolor(region_color)
        patch.set_alpha(0.6)

    # Add optimal BMI range
    ax5.axhspan(21, 24, alpha=0.2, color='green', label='Optimal Range')

    ax5.set_ylabel('BMI (kg/m²)', fontweight='bold', fontsize=12)
    ax5.set_title('E. BMI Distribution by Region (Medalists)',
                fontweight='bold', loc='left', fontsize=14)
    ax5.legend(loc='upper right', fontsize=8)
    ax5.grid(True, alpha=0.3, axis='y')
    plt.setp(ax5.xaxis.get_majorticklabels(), rotation=45, ha='right')

    # ============================================================================
    # PANEL F: Top Performing Countries - Detailed Stats
    # ============================================================================

    ax6 = fig.add_subplot(gs[2, :2])

    top_countries = medal_counts.head(10).index

    country_stats = []
    for country in top_countries:
        country_data = df[df['NOC'] == country]
        medalists = country_data[country_data['Medal'].isin(['1', '2', '3'])]

        country_stats.append({
            'country': country,
            'medals': len(medalists),
            'height': medalists['Height'].mean(),
            'weight': medalists['Weight'].mean(),
            'bmi': medalists['bmi'].mean(),
            'age': medalists['Age'].mean()
        })

    stats_df = pd.DataFrame(country_stats)

    # Create grouped bar chart
    x = np.arange(len(stats_df))
    width = 0.18

    # Normalize metrics for comparison
    metrics = ['height', 'weight', 'bmi', 'age']
    normalized = stats_df[metrics].copy()
    for col in metrics:
        min_val = normalized[col].min()
        max_val = normalized[col].max()
        if max_val > min_val:
            normalized[col] = (normalized[col] - min_val) / (max_val - min_val)

    colors_metrics = ['#E63946', '#457B9D', '#2A9D8F', '#E9C46A']
    labels_metrics = ['Height', 'Weight', 'BMI', 'Age']

    for i, (metric, color, label) in enumerate(zip(metrics, colors_metrics, labels_metrics)):
        offset = (i - len(metrics)/2) * width + width/2
        ax6.bar(x + offset, normalized[metric], width,
            label=label, color=color, alpha=0.8)

    ax6.set_ylabel('Normalized Score (0-1)', fontweight='bold', fontsize=12)
    ax6.set_title('F. Top 10 Countries - Anthropometric Profile Comparison',
                fontweight='bold', loc='left', fontsize=14)
    ax6.set_xticks(x)
    ax6.set_xticklabels(stats_df['country'], rotation=45)
    ax6.legend(loc='upper right', fontsize=9)
    ax6.grid(True, alpha=0.3, axis='y')

    # ============================================================================
    # PANEL G: Country Performance Over Time (Top 5)
    # ============================================================================

    ax7 = fig.add_subplot(gs[2, 2])

    top_5_countries = medal_counts.head(5).index
    years = sorted(df['Year'].unique())

    for country in top_5_countries:
        country_medals_by_year = []
        for year in years:
            year_country = df[(df['Year'] == year) & (df['NOC'] == country)]
            medals = len(year_country[year_country['Medal'].isin(['1', '2', '3'])])
            country_medals_by_year.append(medals)

        ax7.plot(years, country_medals_by_year, 'o-', linewidth=2.5,
                markersize=6, label=country, alpha=0.8)

    ax7.set_xlabel('Olympic Year', fontweight='bold', fontsize=12)
    ax7.set_ylabel('Medals Won', fontweight='bold', fontsize=12)
    ax7.set_title('G. Medal Trends Over Time (Top 5 Countries)',
                fontweight='bold', loc='left', fontsize=14)
    ax7.legend(loc='upper left', fontsize=9)
    ax7.grid(True, alpha=0.3)

    # ============================================================================
    # PANEL H: Regional Dominance by Era
    # ============================================================================

    ax8 = fig.add_subplot(gs[3, 0])

    # Define eras
    eras = [
        ('1896-1936', 1896, 1936),
        ('1948-1968', 1948, 1968),
        ('1972-1992', 1972, 1992),
        ('1996-2016', 1996, 2016)
    ]

    era_region_medals = []

    for era_name, start, end in eras:
        era_data = df[(df['Year'] >= start) & (df['Year'] <= end)]
        era_medals = era_data[era_data['Medal'].isin(['1', '2', '3'])]

        region_counts = era_medals['Region'].value_counts()
        era_region_medals.append(region_counts)

    # Stack bar chart
    regions_all = df['Region'].unique()
    bottom = np.zeros(len(eras))

    for region in regions_all:
        values = [era.get(region, 0) for era in era_region_medals]
        region_color = colors.get(region.lower().replace(' ', '_'), '#CCCCCC')
        ax8.bar(range(len(eras)), values, bottom=bottom,
            label=region, color=region_color, alpha=0.8)
        bottom += values

    ax8.set_xticks(range(len(eras)))
    ax8.set_xticklabels([era[0] for era in eras], rotation=45)
    ax8.set_ylabel('Number of Medals', fontweight='bold', fontsize=12)
    ax8.set_title('H. Regional Dominance by Era',
                fontweight='bold', loc='left', fontsize=14)
    ax8.legend(loc='upper left', fontsize=8, ncol=2)
    ax8.grid(True, alpha=0.3, axis='y')

    # ============================================================================
    # PANEL I: Success Rate by Country (Top 15)
    # ============================================================================

    ax9 = fig.add_subplot(gs[3, 1:])

    # Calculate success rate (medals / total athletes)
    country_success = []

    for country in df['NOC'].unique():
        country_data = df[df['NOC'] == country]
        total_athletes = len(country_data)
        total_medals = len(country_data[country_data['Medal'].isin(['1', '2', '3'])])

        if total_athletes >= 5:  # Minimum threshold
            success_rate = (total_medals / total_athletes) * 100
            country_success.append({
                'country': country,
                'success_rate': success_rate,
                'total_athletes': total_athletes,
                'total_medals': total_medals
            })

    success_df = pd.DataFrame(country_success).sort_values('success_rate', ascending=False).head(15)

    bars = ax9.barh(range(len(success_df)), success_df['success_rate'],
                color=colors['gold'], alpha=0.8)

    # Color by region
    for i, row in success_df.iterrows():
        idx = list(success_df.index).index(i)
        region = df[df['NOC'] == row['country']]['Region'].iloc[0]
        region_color = colors.get(region.lower().replace(' ', '_'), colors['gold'])
        bars[idx].set_color(region_color)

    ax9.set_yticks(range(len(success_df)))
    ax9.set_yticklabels(success_df['country'])
    ax9.set_xlabel('Success Rate (%)', fontweight='bold', fontsize=12)
    ax9.set_title('I. Medal Success Rate by Country (min. 5 athletes)',
                fontweight='bold', loc='left', fontsize=14)
    ax9.grid(True, alpha=0.3, axis='x')

    # Add labels
    for i, row in success_df.iterrows():
        idx = list(success_df.index).index(i)
        ax9.text(row['success_rate'] + 1, idx,
                f"{row['success_rate']:.1f}% ({int(row['total_medals'])}/{int(row['total_athletes'])})",
                va='center', fontsize=8, fontweight='bold')

    # ============================================================================
    # Overall title
    # ============================================================================

    fig.suptitle('400m Olympic Performance: Geographic & Country Analysis\n' +
                'Comprehensive Assessment of Regional and National Performance Patterns',
                fontsize=16, fontweight='bold', y=0.997)

    # Save to figures directory
    os.makedirs('figures', exist_ok=True)
    plt.savefig('figures/400m_geographic_analysis.png', dpi=300, bbox_inches='tight')
    print("✓ Figure saved: figures/400m_geographic_analysis.png")

    plt.close()
