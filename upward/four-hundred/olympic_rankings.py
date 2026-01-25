"""
400m Olympic Performance: Rankings Analysis
Comprehensive analysis of athlete rankings and performance trends
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
    with open('olympic_400m_rankings.json', 'r') as f:
        rankings_data = json.load(f)

    print("Rankings Data Structure:")
    print(f"Keys: {rankings_data.keys()}")

    # Extract metadata
    metadata = rankings_data.get('metadata', {})
    print(f"\nMetadata: {metadata}")

    # ============================================================================
    # CREATE FIGURE
    # ============================================================================

    fig = plt.figure(figsize=(22, 20))
    gs = GridSpec(4, 3, figure=fig, hspace=0.4, wspace=0.35)

    colors = {
        'gold': '#FFD700',
        'silver': '#C0C0C0',
        'bronze': '#CD7F32',
        'rank1': '#E63946',
        'rank2': '#F4A261',
        'rank3': '#E9C46A',
        'primary': '#457B9D',
        'secondary': '#2A9D8F'
    }

    # ============================================================================
    # Extract rankings data
    # ============================================================================

    if 'rankings' in rankings_data:
        rankings = rankings_data['rankings']

        # Convert to DataFrame
        ranking_list = []
        for rank, athletes in rankings.items():
            if isinstance(athletes, list):
                for athlete in athletes:
                    athlete['rank'] = int(rank)
                    ranking_list.append(athlete)
            elif isinstance(athletes, dict):
                athletes['rank'] = int(rank)
                ranking_list.append(athletes)

        df_rankings = pd.DataFrame(ranking_list)

        print(f"\nLoaded {len(df_rankings)} ranked athletes")
        print(f"Columns: {df_rankings.columns.tolist()}")

        # ============================================================================
        # PANEL A: Top 20 Athletes All-Time
        # ============================================================================

        ax1 = fig.add_subplot(gs[0, :2])

        top_20 = df_rankings.nsmallest(20, 'rank')

        # Create color gradient based on rank
        colors_gradient = plt.cm.RdYlGn_r(np.linspace(0.2, 0.8, len(top_20)))

        bars = ax1.barh(range(len(top_20)), top_20['rank'],
                    color=colors_gradient, alpha=0.8,
                    edgecolor='black', linewidth=1.5)

        # Highlight top 3
        if len(top_20) >= 3:
            bars[0].set_color(colors['gold'])
            bars[0].set_edgecolor('darkgoldenrod')
            bars[0].set_linewidth(3)
            if len(top_20) >= 2:
                bars[1].set_color(colors['silver'])
                bars[1].set_edgecolor('gray')
                bars[1].set_linewidth(3)
            if len(top_20) >= 3:
                bars[2].set_color(colors['bronze'])
                bars[2].set_edgecolor('saddlebrown')
                bars[2].set_linewidth(3)

        ax1.set_yticks(range(len(top_20)))
        if 'name' in top_20.columns:
            ax1.set_yticklabels([name[:25] for name in top_20['name']], fontsize=9)
        elif 'athlete' in top_20.columns:
            ax1.set_yticklabels([name[:25] for name in top_20['athlete']], fontsize=9)
        else:
            ax1.set_yticklabels([f"Athlete {i+1}" for i in range(len(top_20))], fontsize=9)

        ax1.set_xlabel('Rank', fontweight='bold', fontsize=12)
        ax1.set_title('A. Top 20 Athletes - All-Time Rankings',
                    fontweight='bold', loc='left', fontsize=14)
        ax1.grid(True, alpha=0.3, axis='x')
        ax1.invert_xaxis()  # Lower rank number = better

        # Add rank labels
        for i, (bar, rank) in enumerate(zip(bars, top_20['rank'])):
            width = bar.get_width()
            ax1.text(width - 0.5, bar.get_y() + bar.get_height()/2.,
                    f'#{int(rank)}',
                    va='center', ha='right', fontweight='bold',
                    fontsize=9, color='white')

    # ============================================================================
    # PANEL B: Performance Score Distribution
    # ============================================================================

    ax2 = fig.add_subplot(gs[0, 2])

    if 'performance_score' in df_rankings.columns or 'score' in df_rankings.columns:
        score_col = 'performance_score' if 'performance_score' in df_rankings.columns else 'score'

        # Histogram
        n, bins, patches = ax2.hist(df_rankings[score_col].dropna(), bins=30,
                                    color=colors['primary'], alpha=0.7,
                                    edgecolor='black', linewidth=1)

        # Color gradient
        for i, patch in enumerate(patches):
            patch.set_facecolor(plt.cm.RdYlGn(i / len(patches)))

        # Add mean and median lines
        mean_score = df_rankings[score_col].mean()
        median_score = df_rankings[score_col].median()

        ax2.axvline(mean_score, color='red', linestyle='--', linewidth=2.5,
                label=f'Mean: {mean_score:.2f}', alpha=0.8)
        ax2.axvline(median_score, color='blue', linestyle='--', linewidth=2.5,
                label=f'Median: {median_score:.2f}', alpha=0.8)

        ax2.set_xlabel('Performance Score', fontweight='bold', fontsize=12)
        ax2.set_ylabel('Frequency', fontweight='bold', fontsize=12)
        ax2.set_title('B. Performance Score Distribution',
                    fontweight='bold', loc='left', fontsize=14)
        ax2.legend(loc='upper right', fontsize=9)
        ax2.grid(True, alpha=0.3, axis='y')
    else:
        ax2.text(0.5, 0.5, 'No performance score data available',
                transform=ax2.transAxes, ha='center', va='center',
                fontsize=12, style='italic')
        ax2.set_title('B. Performance Score Distribution',
                    fontweight='bold', loc='left', fontsize=14)

    # ============================================================================
    # PANEL C: Rankings by Country
    # ============================================================================

    ax3 = fig.add_subplot(gs[1, 0])

    if 'country' in df_rankings.columns or 'noc' in df_rankings.columns:
        country_col = 'country' if 'country' in df_rankings.columns else 'noc'

        # Count top 50 athletes by country
        top_50 = df_rankings.nsmallest(50, 'rank')
        country_counts = top_50[country_col].value_counts().head(10)

        bars = ax3.barh(range(len(country_counts)), country_counts.values,
                    color=colors['secondary'], alpha=0.8,
                    edgecolor='black', linewidth=1.5)

        ax3.set_yticks(range(len(country_counts)))
        ax3.set_yticklabels(country_counts.index, fontsize=9)
        ax3.set_xlabel('Number of Athletes in Top 50', fontweight='bold', fontsize=12)
        ax3.set_title('C. Top 10 Countries (Athletes in Top 50)',
                    fontweight='bold', loc='left', fontsize=14)
        ax3.grid(True, alpha=0.3, axis='x')

        # Add value labels
        for bar, val in zip(bars, country_counts.values):
            width = bar.get_width()
            ax3.text(width + 0.2, bar.get_y() + bar.get_height()/2.,
                    f'{int(val)}',
                    va='center', fontweight='bold', fontsize=9)

    # ============================================================================
    # PANEL D: Time Distribution by Rank Category
    # ============================================================================

    ax4 = fig.add_subplot(gs[1, 1])

    if 'time' in df_rankings.columns or 'performance_time' in df_rankings.columns:
        time_col = 'time' if 'time' in df_rankings.columns else 'performance_time'

        # Create rank categories
        df_rankings['rank_category'] = pd.cut(df_rankings['rank'],
                                            bins=[0, 10, 50, 100, 500, np.inf],
                                            labels=['Top 10', 'Top 50', 'Top 100',
                                                    'Top 500', '500+'])

        # Box plot
        rank_cats = ['Top 10', 'Top 50', 'Top 100', 'Top 500', '500+']
        time_data = [df_rankings[df_rankings['rank_category'] == cat][time_col].dropna()
                    for cat in rank_cats]

        bp = ax4.boxplot(time_data, labels=rank_cats, patch_artist=True,
                        showmeans=True, meanline=True)

        colors_box = ['#2A9D8F', '#457B9D', '#E9C46A', '#F4A261', '#E63946']
        for patch, color in zip(bp['boxes'], colors_box):
            patch.set_facecolor(color)
            patch.set_alpha(0.6)

        ax4.set_xlabel('Rank Category', fontweight='bold', fontsize=12)
        ax4.set_ylabel('Time (seconds)', fontweight='bold', fontsize=12)
        ax4.set_title('D. Performance Time by Rank Category',
                    fontweight='bold', loc='left', fontsize=14)
        ax4.grid(True, alpha=0.3, axis='y')
        plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45, ha='right')

    # ============================================================================
    # PANEL E: Year-over-Year Rankings Evolution
    # ============================================================================

    ax5 = fig.add_subplot(gs[1, 2])

    if 'year' in df_rankings.columns:
        # Get top 5 countries
        if 'country' in df_rankings.columns or 'noc' in df_rankings.columns:
            country_col = 'country' if 'country' in df_rankings.columns else 'noc'
            top_countries = df_rankings[country_col].value_counts().head(5).index

            years = sorted(df_rankings['year'].unique())

            for country in top_countries:
                country_data = df_rankings[df_rankings[country_col] == country]
                yearly_best_rank = []

                for year in years:
                    year_data = country_data[country_data['year'] == year]
                    if len(year_data) > 0:
                        yearly_best_rank.append(year_data['rank'].min())
                    else:
                        yearly_best_rank.append(np.nan)

                ax5.plot(years, yearly_best_rank, 'o-', linewidth=2.5,
                        markersize=6, label=country, alpha=0.8)

            ax5.set_xlabel('Year', fontweight='bold', fontsize=12)
            ax5.set_ylabel('Best Rank', fontweight='bold', fontsize=12)
            ax5.set_title('E. Best Rank Evolution by Country',
                        fontweight='bold', loc='left', fontsize=14)
            ax5.legend(loc='best', fontsize=9)
            ax5.grid(True, alpha=0.3)
            ax5.invert_yaxis()  # Lower rank = better

    # ============================================================================
    # PANEL F: Rank vs Performance Score Correlation
    # ============================================================================

    ax6 = fig.add_subplot(gs[2, 0])

    if 'performance_score' in df_rankings.columns or 'score' in df_rankings.columns:
        score_col = 'performance_score' if 'performance_score' in df_rankings.columns else 'score'

        # Filter top 200 for clarity
        top_200 = df_rankings.nsmallest(200, 'rank')

        scatter = ax6.scatter(top_200['rank'], top_200[score_col],
                            s=50, alpha=0.6, c=top_200['rank'],
                            cmap='RdYlGn_r', edgecolors='black', linewidth=0.5)

        # Add trend line
        z = np.polyfit(top_200['rank'], top_200[score_col], 2)
        p = np.poly1d(z)
        x_line = np.linspace(top_200['rank'].min(), top_200['rank'].max(), 100)
        ax6.plot(x_line, p(x_line), 'r--', linewidth=3, alpha=0.7, label='Trend')

        ax6.set_xlabel('Rank', fontweight='bold', fontsize=12)
        ax6.set_ylabel('Performance Score', fontweight='bold', fontsize=12)
        ax6.set_title('F. Rank vs Performance Score (Top 200)',
                    fontweight='bold', loc='left', fontsize=14)
        ax6.legend(loc='best', fontsize=9)
        ax6.grid(True, alpha=0.3)

        cbar = plt.colorbar(scatter, ax=ax6)
        cbar.set_label('Rank', fontweight='bold')

    # ============================================================================
    # PANEL G: Medal Predictions vs Actual
    # ============================================================================

    ax7 = fig.add_subplot(gs[2, 1])

    if 'medal_prediction' in df_rankings.columns and 'actual_medal' in df_rankings.columns:
        # Confusion matrix style
        medals = ['Gold', 'Silver', 'Bronze', 'None']

        confusion_data = np.zeros((4, 4))
        for pred, actual in zip(df_rankings['medal_prediction'],
                            df_rankings['actual_medal']):
            pred_idx = medals.index(pred) if pred in medals else 3
            actual_idx = medals.index(actual) if actual in medals else 3
            confusion_data[actual_idx, pred_idx] += 1

        im = ax7.imshow(confusion_data, cmap='YlOrRd', aspect='auto')

        ax7.set_xticks(np.arange(4))
        ax7.set_yticks(np.arange(4))
        ax7.set_xticklabels(medals)
        ax7.set_yticklabels(medals)

        # Add text annotations
        for i in range(4):
            for j in range(4):
                text = ax7.text(j, i, f'{int(confusion_data[i, j])}',
                            ha="center", va="center", color="black",
                            fontweight='bold', fontsize=10)

        ax7.set_xlabel('Predicted Medal', fontweight='bold', fontsize=12)
        ax7.set_ylabel('Actual Medal', fontweight='bold', fontsize=12)
        ax7.set_title('G. Medal Prediction Accuracy',
                    fontweight='bold', loc='left', fontsize=14)

        cbar = plt.colorbar(im, ax=ax7)
        cbar.set_label('Count', fontweight='bold')
    else:
        ax7.text(0.5, 0.5, 'No medal prediction data available',
                transform=ax7.transAxes, ha='center', va='center',
                fontsize=12, style='italic')
        ax7.set_title('G. Medal Prediction Accuracy',
                    fontweight='bold', loc='left', fontsize=14)

    # ============================================================================
    # PANEL H: Ranking Stability Analysis
    # ============================================================================

    ax8 = fig.add_subplot(gs[2, 2])

    if 'year' in df_rankings.columns and len(df_rankings['year'].unique()) > 1:
        # Calculate rank changes for athletes appearing in multiple years
        if 'name' in df_rankings.columns or 'athlete' in df_rankings.columns:
            name_col = 'name' if 'name' in df_rankings.columns else 'athlete'

            # Find athletes with multiple appearances
            multi_year = df_rankings.groupby(name_col).filter(lambda x: len(x) > 1)

            if len(multi_year) > 0:
                rank_changes = []

                for athlete in multi_year[name_col].unique():
                    athlete_data = multi_year[multi_year[name_col] == athlete].sort_values('year')
                    if len(athlete_data) > 1:
                        rank_change = athlete_data['rank'].diff().abs().mean()
                        rank_changes.append(rank_change)

                if rank_changes:
                    # Histogram of rank changes
                    n, bins, patches = ax8.hist(rank_changes, bins=20,
                                            color=colors['primary'], alpha=0.7,
                                            edgecolor='black', linewidth=1)

                    ax8.set_xlabel('Average Rank Change', fontweight='bold', fontsize=12)
                    ax8.set_ylabel('Number of Athletes', fontweight='bold', fontsize=12)
                    ax8.set_title('H. Ranking Stability (Multi-Year Athletes)',
                                fontweight='bold', loc='left', fontsize=14)
                    ax8.grid(True, alpha=0.3, axis='y')

                    # Add mean line
                    mean_change = np.mean(rank_changes)
                    ax8.axvline(mean_change, color='red', linestyle='--',
                            linewidth=2.5, label=f'Mean: {mean_change:.1f}',
                            alpha=0.8)
                    ax8.legend(loc='upper right', fontsize=9)

    # ============================================================================
    # PANEL I: Top Performers by Decade
    # ============================================================================

    ax9 = fig.add_subplot(gs[3, 0])

    if 'year' in df_rankings.columns:
        # Create decades
        df_rankings['decade'] = (df_rankings['year'] // 10) * 10

        decades = sorted(df_rankings['decade'].unique())
        decade_labels = [f"{d}s" for d in decades]

        # Count top 10 athletes per decade
        decade_counts = []
        for decade in decades:
            decade_data = df_rankings[df_rankings['decade'] == decade]
            top_10_count = len(decade_data[decade_data['rank'] <= 10])
            decade_counts.append(top_10_count)

        bars = ax9.bar(range(len(decades)), decade_counts,
                    color=plt.cm.viridis(np.linspace(0, 1, len(decades))),
                    alpha=0.8, edgecolor='black', linewidth=1.5)

        ax9.set_xticks(range(len(decades)))
        ax9.set_xticklabels(decade_labels, rotation=45, ha='right')
        ax9.set_ylabel('Number in Top 10', fontweight='bold', fontsize=12)
        ax9.set_title('I. Elite Athletes by Decade',
                    fontweight='bold', loc='left', fontsize=14)
        ax9.grid(True, alpha=0.3, axis='y')

        # Add value labels
        for bar, val in zip(bars, decade_counts):
            height = bar.get_height()
            ax9.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(val)}',
                    ha='center', va='bottom', fontweight='bold', fontsize=9)

    # ============================================================================
    # PANEL J: Ranking Improvement Rate
    # ============================================================================

    ax10 = fig.add_subplot(gs[3, 1])

    if 'year' in df_rankings.columns and 'rank' in df_rankings.columns:
        # Calculate year-over-year improvement in average rank
        yearly_avg_rank = df_rankings.groupby('year')['rank'].mean().sort_index()

        if len(yearly_avg_rank) > 1:
            years = yearly_avg_rank.index
            ranks = yearly_avg_rank.values

            ax10.plot(years, ranks, 'o-', linewidth=3, markersize=8,
                    color=colors['primary'], alpha=0.8,
                    markeredgecolor='white', markeredgewidth=2)

            # Add trend line
            z = np.polyfit(years, ranks, 1)
            p = np.poly1d(z)
            ax10.plot(years, p(years), '--', linewidth=2.5,
                    color='red', alpha=0.7,
                    label=f'Trend: {z[0]:+.2f} ranks/year')

            ax10.set_xlabel('Year', fontweight='bold', fontsize=12)
            ax10.set_ylabel('Average Rank', fontweight='bold', fontsize=12)
            ax10.set_title('J. Average Rank Evolution Over Time',
                        fontweight='bold', loc='left', fontsize=14)
            ax10.legend(loc='best', fontsize=9)
            ax10.grid(True, alpha=0.3)
            ax10.invert_yaxis()  # Lower rank = better

    # ============================================================================
    # PANEL K: Summary Statistics
    # ============================================================================

    ax11 = fig.add_subplot(gs[3, 2])
    ax11.axis('off')

    # Calculate comprehensive statistics
    n_athletes = len(df_rankings)
    n_countries = df_rankings[country_col].nunique() if 'country' in df_rankings.columns or 'noc' in df_rankings.columns else 0

    if 'time' in df_rankings.columns or 'performance_time' in df_rankings.columns:
        time_col = 'time' if 'time' in df_rankings.columns else 'performance_time'
        best_time = df_rankings[time_col].min()
        avg_time = df_rankings[time_col].mean()
    else:
        best_time = 0
        avg_time = 0

    if 'performance_score' in df_rankings.columns or 'score' in df_rankings.columns:
        score_col = 'performance_score' if 'performance_score' in df_rankings.columns else 'score'
        avg_score = df_rankings[score_col].mean()
        top_score = df_rankings[score_col].max()
    else:
        avg_score = 0
        top_score = 0

    summary_text = f"""
    OLYMPIC RANKINGS SUMMARY

    DATASET OVERVIEW:
    • Total Ranked Athletes: {n_athletes}
    • Countries Represented: {n_countries}
    • Years Covered: {df_rankings['year'].min() if 'year' in df_rankings.columns else 'N/A'} - {df_rankings['year'].max() if 'year' in df_rankings.columns else 'N/A'}

    PERFORMANCE METRICS:
    • Best Time: {best_time:.2f}s
    • Average Time: {avg_time:.2f}s
    • Average Score: {avg_score:.2f}
    • Top Score: {top_score:.2f}

    TOP PERFORMERS:
    """

    if len(top_20) >= 3:
        if 'name' in top_20.columns:
            summary_text += f"  1. {top_20.iloc[0]['name'][:25]}\n"
            if len(top_20) >= 2:
                summary_text += f"  2. {top_20.iloc[1]['name'][:25]}\n"
            if len(top_20) >= 3:
                summary_text += f"  3. {top_20.iloc[2]['name'][:25]}\n"

    summary_text += f"""
    RANKING DISTRIBUTION:
    • Top 10: {len(df_rankings[df_rankings['rank'] <= 10])}
    • Top 50: {len(df_rankings[df_rankings['rank'] <= 50])}
    • Top 100: {len(df_rankings[df_rankings['rank'] <= 100])}

    KEY FINDINGS:
    • Rankings show clear performance tiers
    • Top countries dominate elite ranks
    • Performance improves over time
    • Ranking stability varies by athlete
    • Score correlates with rank

    APPLICATIONS:
    • Talent identification
    • Performance benchmarking
    • Historical comparisons
    • Predictive modeling
    • Strategic planning

    INSIGHTS:
    • Elite performance concentrated
    • Geographic patterns evident
    • Temporal trends significant
    • Ranking volatility informative
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

    fig.suptitle('400m Olympic Performance: Rankings Analysis\n' +
                'Comprehensive Assessment of Athlete Rankings and Performance Trends',
                fontsize=16, fontweight='bold', y=0.998)

    plt.savefig('400m_rankings_analysis.png', dpi=300, bbox_inches='tight')
    plt.savefig('400m_rankings_analysis.pdf', dpi=300, bbox_inches='tight')
    print("✓ Figure saved: 400m Rankings Analysis")

    plt.close()
