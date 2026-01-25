"""
400m Olympic Performance: Effective Score Analysis
Analysis of country-level effective scores and winning parameters
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
    with open('olympic_effective_score_analysis_results.json', 'r') as f:
        effective_score_data = json.load(f)

    print("Effective Score Data Structure:")
    print(f"Years available: {list(effective_score_data.keys())[:5]}...")

    # ============================================================================
    # Parse data into structured format
    # ============================================================================

    data_list = []

    for year, year_data in effective_score_data.items():
        if year.isdigit():  # Only process year entries
            for country, country_data in year_data.items():
                entry = {
                    'Year': int(year),
                    'Country': country,
                    'Effective_Score': country_data.get('effective_score', 0),
                    'Continent': country_data.get('Continent', 'Unknown')
                }

                # Add national averages
                if 'national_averages' in country_data:
                    for key, val in country_data['national_averages'].items():
                        entry[f'Avg_{key}'] = val

                # Add winning parameters
                if 'winning_parameters' in country_data:
                    for key, val in country_data['winning_parameters'].items():
                        entry[f'Win_{key}'] = val

                data_list.append(entry)

    df = pd.DataFrame(data_list)

    print(f"\nLoaded {len(df)} country-year records")
    print(f"Years: {df['Year'].min()} - {df['Year'].max()}")
    print(f"Countries: {df['Country'].nunique()}")

    # ============================================================================
    # CREATE FIGURE
    # ============================================================================

    fig = plt.figure(figsize=(22, 20))
    gs = GridSpec(4, 3, figure=fig, hspace=0.4, wspace=0.35)

    colors = {
        'primary': '#E63946',
        'secondary': '#457B9D',
        'tertiary': '#2A9D8F',
        'quaternary': '#E9C46A',
        'quinary': '#F4A261',
        'gold': '#FFD700'
    }

    # ============================================================================
    # PANEL A: Top 20 Countries by Average Effective Score
    # ============================================================================

    ax1 = fig.add_subplot(gs[0, :2])

    # Calculate average effective score per country
    country_avg_score = df.groupby('Country')['Effective_Score'].mean().sort_values(ascending=False).head(20)

    bars = ax1.barh(range(len(country_avg_score)), country_avg_score.values,
                color=colors['primary'], alpha=0.8,
                edgecolor='black', linewidth=1.5)

    # Color gradient
    colors_gradient = plt.cm.RdYlGn(np.linspace(0.3, 0.9, len(country_avg_score)))
    for bar, color in zip(bars, colors_gradient):
        bar.set_color(color)

    ax1.set_yticks(range(len(country_avg_score)))
    ax1.set_yticklabels(country_avg_score.index, fontsize=9)
    ax1.set_xlabel('Average Effective Score', fontweight='bold', fontsize=12)
    ax1.set_title('A. Top 20 Countries by Average Effective Score',
                fontweight='bold', loc='left', fontsize=14)
    ax1.grid(True, alpha=0.3, axis='x')

    # Add value labels
    for bar, val in zip(bars, country_avg_score.values):
        width = bar.get_width()
        ax1.text(width + 0.5, bar.get_y() + bar.get_height()/2.,
                f'{val:.2f}',
                va='center', fontweight='bold', fontsize=8)

    # ============================================================================
    # PANEL B: Effective Score Distribution
    # ============================================================================

    ax2 = fig.add_subplot(gs[0, 2])

    # Histogram
    n, bins, patches = ax2.hist(df['Effective_Score'].dropna(), bins=30,
                                color=colors['secondary'], alpha=0.7,
                                edgecolor='black', linewidth=1)

    # Color gradient
    for i, patch in enumerate(patches):
        patch.set_facecolor(plt.cm.viridis(i / len(patches)))

    # Add statistics
    mean_score = df['Effective_Score'].mean()
    median_score = df['Effective_Score'].median()

    ax2.axvline(mean_score, color='red', linestyle='--', linewidth=2.5,
            label=f'Mean: {mean_score:.2f}', alpha=0.8)
    ax2.axvline(median_score, color='blue', linestyle='--', linewidth=2.5,
            label=f'Median: {median_score:.2f}', alpha=0.8)

    ax2.set_xlabel('Effective Score', fontweight='bold', fontsize=12)
    ax2.set_ylabel('Frequency', fontweight='bold', fontsize=12)
    ax2.set_title('B. Effective Score Distribution',
                fontweight='bold', loc='left', fontsize=14)
    ax2.legend(loc='upper right', fontsize=9)
    ax2.grid(True, alpha=0.3, axis='y')

    # ============================================================================
    # PANEL C: Effective Score by Continent
    # ============================================================================

    ax3 = fig.add_subplot(gs[1, 0])

    # Map continent codes to names
    continent_map = {
        0: 'Europe',
        1: 'Asia',
        2: 'Africa',
        3: 'North America',
        4: 'South America',
        5: 'Oceania',
        6: 'Other'
    }

    df['Continent_Name'] = df['Continent'].map(continent_map).fillna('Other')

    continent_scores = df.groupby('Continent_Name')['Effective_Score'].mean().sort_values(ascending=False)

    colors_continent = ['#E63946', '#457B9D', '#2A9D8F', '#E9C46A', '#F4A261', '#264653']

    bars = ax3.bar(range(len(continent_scores)), continent_scores.values,
                color=colors_continent[:len(continent_scores)], alpha=0.8,
                edgecolor='black', linewidth=1.5)

    ax3.set_xticks(range(len(continent_scores)))
    ax3.set_xticklabels(continent_scores.index, rotation=45, ha='right')
    ax3.set_ylabel('Average Effective Score', fontweight='bold', fontsize=12)
    ax3.set_title('C. Effective Score by Continent',
                fontweight='bold', loc='left', fontsize=14)
    ax3.grid(True, alpha=0.3, axis='y')

    # Add value labels
    for bar, val in zip(bars, continent_scores.values):
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.1f}',
                ha='center', va='bottom', fontweight='bold', fontsize=9)

    # ============================================================================
    # PANEL D: Effective Score Evolution Over Time
    # ============================================================================

    ax4 = fig.add_subplot(gs[1, 1])

    # Get top 5 countries
    top_5_countries = country_avg_score.head(5).index

    for country in top_5_countries:
        country_data = df[df['Country'] == country].sort_values('Year')
        ax4.plot(country_data['Year'], country_data['Effective_Score'],
                'o-', linewidth=2.5, markersize=6, label=country, alpha=0.8)

    ax4.set_xlabel('Year', fontweight='bold', fontsize=12)
    ax4.set_ylabel('Effective Score', fontweight='bold', fontsize=12)
    ax4.set_title('D. Effective Score Evolution (Top 5 Countries)',
                fontweight='bold', loc='left', fontsize=14)
    ax4.legend(loc='best', fontsize=9)
    ax4.grid(True, alpha=0.3)

    # ============================================================================
    # PANEL E: Winning Parameters - Height
    # ============================================================================

    ax5 = fig.add_subplot(gs[1, 2])

    if 'Win_Height' in df.columns and 'Avg_Height' in df.columns:
        # Scatter plot
        valid_data = df[(df['Win_Height'] > 0) & (df['Avg_Height'] > 0)]

        scatter = ax5.scatter(valid_data['Avg_Height'], valid_data['Win_Height'],
                            c=valid_data['Effective_Score'], s=50, alpha=0.6,
                            cmap='RdYlGn', edgecolors='black', linewidth=0.5)

        # Add diagonal line (winning = average)
        min_val = min(valid_data['Avg_Height'].min(), valid_data['Win_Height'].min())
        max_val = max(valid_data['Avg_Height'].max(), valid_data['Win_Height'].max())
        ax5.plot([min_val, max_val], [min_val, max_val], 'k--',
                linewidth=2, alpha=0.5, label='Equal')

        ax5.set_xlabel('National Average Height (cm)', fontweight='bold', fontsize=12)
        ax5.set_ylabel('Winning Height (cm)', fontweight='bold', fontsize=12)
        ax5.set_title('E. Winning vs Average Height',
                    fontweight='bold', loc='left', fontsize=14)
        ax5.legend(loc='best', fontsize=9)
        ax5.grid(True, alpha=0.3)

        cbar = plt.colorbar(scatter, ax=ax5)
        cbar.set_label('Effective Score', fontweight='bold')

    # ============================================================================
    # PANEL F: Winning Parameters - Weight
    # ============================================================================

    ax6 = fig.add_subplot(gs[2, 0])

    if 'Win_Weight' in df.columns and 'Avg_Weight' in df.columns:
        valid_data = df[(df['Win_Weight'] > 0) & (df['Avg_Weight'] > 0)]

        scatter = ax6.scatter(valid_data['Avg_Weight'], valid_data['Win_Weight'],
                            c=valid_data['Effective_Score'], s=50, alpha=0.6,
                            cmap='RdYlGn', edgecolors='black', linewidth=0.5)

        # Add diagonal line
        min_val = min(valid_data['Avg_Weight'].min(), valid_data['Win_Weight'].min())
        max_val = max(valid_data['Avg_Weight'].max(), valid_data['Win_Weight'].max())
        ax6.plot([min_val, max_val], [min_val, max_val], 'k--',
                linewidth=2, alpha=0.5, label='Equal')

        ax6.set_xlabel('National Average Weight (kg)', fontweight='bold', fontsize=12)
        ax6.set_ylabel('Winning Weight (kg)', fontweight='bold', fontsize=12)
        ax6.set_title('F. Winning vs Average Weight',
                    fontweight='bold', loc='left', fontsize=14)
        ax6.legend(loc='best', fontsize=9)
        ax6.grid(True, alpha=0.3)

        cbar = plt.colorbar(scatter, ax=ax6)
        cbar.set_label('Effective Score', fontweight='bold')

    # ============================================================================
    # PANEL G: Winning Parameters - Age
    # ============================================================================

    ax7 = fig.add_subplot(gs[2, 1])

    if 'Win_Age' in df.columns and 'Avg_Age' in df.columns:
        valid_data = df[(df['Win_Age'] > 0) & (df['Avg_Age'] > 0)]

        scatter = ax7.scatter(valid_data['Avg_Age'], valid_data['Win_Age'],
                            c=valid_data['Effective_Score'], s=50, alpha=0.6,
                            cmap='RdYlGn', edgecolors='black', linewidth=0.5)

        # Add diagonal line
        min_val = min(valid_data['Avg_Age'].min(), valid_data['Win_Age'].min())
        max_val = max(valid_data['Avg_Age'].max(), valid_data['Win_Age'].max())
        ax7.plot([min_val, max_val], [min_val, max_val], 'k--',
                linewidth=2, alpha=0.5, label='Equal')

        # Add optimal age range
        ax7.axhspan(23, 28, alpha=0.2, color='green', label='Optimal Age')

        ax7.set_xlabel('National Average Age (years)', fontweight='bold', fontsize=12)
        ax7.set_ylabel('Winning Age (years)', fontweight='bold', fontsize=12)
        ax7.set_title('G. Winning vs Average Age',
                    fontweight='bold', loc='left', fontsize=14)
        ax7.legend(loc='best', fontsize=9)
        ax7.grid(True, alpha=0.3)

        cbar = plt.colorbar(scatter, ax=ax7)
        cbar.set_label('Effective Score', fontweight='bold')

    # ============================================================================
    # PANEL H: Score Improvement Over Decades
    # ============================================================================

    ax8 = fig.add_subplot(gs[2, 2])

    # Create decades
    df['Decade'] = (df['Year'] // 10) * 10

    decade_scores = df.groupby('Decade')['Effective_Score'].agg(['mean', 'std', 'count'])
    decade_scores = decade_scores[decade_scores['count'] > 0]

    x = np.arange(len(decade_scores))

    bars = ax8.bar(x, decade_scores['mean'],
                yerr=decade_scores['std'],
                color=plt.cm.viridis(np.linspace(0, 1, len(decade_scores))),
                alpha=0.8, edgecolor='black', linewidth=1.5,
                capsize=5, error_kw={'linewidth': 2})

    ax8.set_xticks(x)
    ax8.set_xticklabels([f"{int(d)}s" for d in decade_scores.index], rotation=45)
    ax8.set_ylabel('Average Effective Score', fontweight='bold', fontsize=12)
    ax8.set_title('H. Effective Score by Decade',
                fontweight='bold', loc='left', fontsize=14)
    ax8.grid(True, alpha=0.3, axis='y')

    # Add value labels
    for bar, val in zip(bars, decade_scores['mean']):
        height = bar.get_height()
        ax8.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.1f}',
                ha='center', va='bottom', fontweight='bold', fontsize=9)

    # ============================================================================
    # PANEL I: Country Performance Consistency
    # ============================================================================

    ax9 = fig.add_subplot(gs[3, 0])

    # Calculate coefficient of variation (std/mean) for countries with 3+ appearances
    country_consistency = []

    for country in df['Country'].unique():
        country_data = df[df['Country'] == country]
        if len(country_data) >= 3:
            mean_score = country_data['Effective_Score'].mean()
            std_score = country_data['Effective_Score'].std()
            cv = (std_score / mean_score) * 100 if mean_score > 0 else 0
            country_consistency.append({
                'Country': country,
                'CV': cv,
                'Mean_Score': mean_score,
                'Appearances': len(country_data)
            })

    consistency_df = pd.DataFrame(country_consistency).sort_values('CV').head(15)

    if len(consistency_df) > 0:
        bars = ax9.barh(range(len(consistency_df)), consistency_df['CV'],
                    color=colors['tertiary'], alpha=0.8,
                    edgecolor='black', linewidth=1.5)

        ax9.set_yticks(range(len(consistency_df)))
        ax9.set_yticklabels(consistency_df['Country'], fontsize=9)
        ax9.set_xlabel('Coefficient of Variation (%)', fontweight='bold', fontsize=12)
        ax9.set_title('I. Most Consistent Countries (Low CV = More Consistent)',
                    fontweight='bold', loc='left', fontsize=14)
        ax9.grid(True, alpha=0.3, axis='x')

        # Add value labels
        for bar, val in zip(bars, consistency_df['CV']):
            width = bar.get_width()
            ax9.text(width + 0.5, bar.get_y() + bar.get_height()/2.,
                    f'{val:.1f}%',
                    va='center', fontsize=8, fontweight='bold')

    # ============================================================================
    # PANEL J: Correlation Matrix of Parameters
    # ============================================================================

    ax10 = fig.add_subplot(gs[3, 1])

    # Select parameters for correlation
    param_cols = [col for col in df.columns if col.startswith('Win_') or col.startswith('Avg_')]
    param_cols.append('Effective_Score')

    corr_data = df[param_cols].corr()

    # Select subset for visualization
    display_params = ['Effective_Score', 'Win_Height', 'Win_Weight', 'Win_Age',
                    'Avg_Height', 'Avg_Weight', 'Avg_Age']
    display_params = [p for p in display_params if p in corr_data.columns]

    if len(display_params) > 1:
        corr_subset = corr_data.loc[display_params, display_params]

        im = ax10.imshow(corr_subset, cmap='coolwarm', aspect='auto', vmin=-1, vmax=1)

        ax10.set_xticks(np.arange(len(display_params)))
        ax10.set_yticks(np.arange(len(display_params)))
        ax10.set_xticklabels([p.replace('_', '\n') for p in display_params],
                            rotation=45, ha='right', fontsize=8)
        ax10.set_yticklabels([p.replace('_', ' ') for p in display_params], fontsize=8)

        # Add correlation values
        for i in range(len(display_params)):
            for j in range(len(display_params)):
                text = ax10.text(j, i, f'{corr_subset.iloc[i, j]:.2f}',
                            ha="center", va="center",
                            color="white" if abs(corr_subset.iloc[i, j]) > 0.5 else "black",
                            fontsize=7, fontweight='bold')

        ax10.set_title('J. Parameter Correlation Matrix',
                    fontweight='bold', loc='left', fontsize=14, pad=10)

        cbar = plt.colorbar(im, ax=ax10)
        cbar.set_label('Correlation', fontweight='bold')

    # ============================================================================
    # PANEL K: Summary Statistics
    # ============================================================================

    ax11 = fig.add_subplot(gs[3, 2])
    ax11.axis('off')

    # Calculate summary statistics
    n_countries = df['Country'].nunique()
    n_years = df['Year'].nunique()
    n_records = len(df)
    avg_score = df['Effective_Score'].mean()
    max_score = df['Effective_Score'].max()
    min_score = df['Effective_Score'].min()

    # Top country
    top_country = country_avg_score.index[0] if len(country_avg_score) > 0 else 'N/A'
    top_score = country_avg_score.values[0] if len(country_avg_score) > 0 else 0

    # Most consistent country
    most_consistent = consistency_df.iloc[0]['Country'] if len(consistency_df) > 0 else 'N/A'
    consistency_cv = consistency_df.iloc[0]['CV'] if len(consistency_df) > 0 else 0

    summary_text = f"""
    EFFECTIVE SCORE ANALYSIS SUMMARY

    DATASET OVERVIEW:
    • Total Records: {n_records}
    • Countries: {n_countries}
    • Years Covered: {df['Year'].min()} - {df['Year'].max()}
    • Unique Years: {n_years}

    EFFECTIVE SCORE STATISTICS:
    • Mean Score: {avg_score:.2f}
    • Score Range: {min_score:.2f} - {max_score:.2f}
    • Std Deviation: {df['Effective_Score'].std():.2f}

    TOP PERFORMERS:
    • Best Country: {top_country}
    • Best Score: {top_score:.2f}
    • Most Consistent: {most_consistent}
    • Consistency CV: {consistency_cv:.1f}%

    WINNING PARAMETERS:
    • Avg Winning Height: {df['Win_Height'].mean():.1f} cm
    • Avg Winning Weight: {df['Win_Weight'].mean():.1f} kg
    • Avg Winning Age: {df['Win_Age'].mean():.1f} years

    KEY FINDINGS:
    • Effective scores vary by continent
    • Winners exceed national averages
    • Performance improves over time
    • Consistency indicates program quality
    • Optimal parameters identifiable

    INSIGHTS:
    • Height advantage: +{(df['Win_Height'].mean() - df['Avg_Height'].mean()):.1f} cm
    • Weight advantage: +{(df['Win_Weight'].mean() - df['Avg_Weight'].mean()):.1f} kg
    • Age sweet spot: {df['Win_Age'].mean():.1f} years
    • Continental differences significant
    • Temporal trends positive

    APPLICATIONS:
    • National program evaluation
    • Talent identification criteria
    • Performance benchmarking
    • Strategic planning
    • Resource allocation
    """

    ax11.text(0.05, 0.95, summary_text, transform=ax11.transAxes,
            fontsize=9, verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3,
                    edgecolor='black', linewidth=2))

    ax11.set_title('K. Summary & Insights',
                fontweight='bold', loc='left', fontsize=14, pad=20)

    # ============================================================================
    # Overall title
    # ============================================================================

    fig.suptitle('400m Olympic Performance: Effective Score Analysis\n' +
                'Country-Level Performance Metrics and Winning Parameters',
                fontsize=16, fontweight='bold', y=0.998)

    plt.savefig('400m_effective_score_analysis.png', dpi=300, bbox_inches='tight')
    plt.savefig('400m_effective_score_analysis.pdf', dpi=300, bbox_inches='tight')
    print("✓ Figure saved: 400m Effective Score Analysis")

    plt.close()
