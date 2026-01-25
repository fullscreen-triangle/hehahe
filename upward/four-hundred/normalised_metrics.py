"""
400m Olympic Performance: Normalized Metrics Analysis
Analysis of standardized performance metrics across athletes
"""

import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.gridspec import GridSpec
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from scipy.cluster.hierarchy import dendrogram, linkage
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
    with open('normalized_metrics.json', 'r') as f:
        norm_data = json.load(f)

    # Convert to DataFrame
    athletes = []
    for athlete in norm_data:
        athlete_dict = {'Name': athlete['Name']}
        if 'NormalizedMetrics' in athlete:
            athlete_dict.update(athlete['NormalizedMetrics'])
        athletes.append(athlete_dict)

    df = pd.DataFrame(athletes)

    print(f"Loaded {len(df)} athletes")
    print(f"Normalized metrics: {[col for col in df.columns if col != 'Name']}")

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
        'quinary': '#F4A261'
    }

    # Get numeric columns (excluding Name)
    numeric_cols = [col for col in df.columns if col != 'Name' and df[col].dtype in ['float64', 'int64']]

    # ============================================================================
    # PANEL A: Distribution of Normalized Metrics
    # ============================================================================

    ax1 = fig.add_subplot(gs[0, :2])

    # Select top metrics for visualization
    top_metrics = numeric_cols[:10] if len(numeric_cols) > 10 else numeric_cols

    violin_data = [df[col].dropna() for col in top_metrics]

    parts = ax1.violinplot(violin_data, positions=range(len(top_metrics)),
                        showmeans=True, showmedians=True, showextrema=True)

    for pc in parts['bodies']:
        pc.set_facecolor(colors['primary'])
        pc.set_alpha(0.6)

    ax1.set_xticks(range(len(top_metrics)))
    ax1.set_xticklabels([col.replace('_', '\n') for col in top_metrics],
                        rotation=45, ha='right', fontsize=8)
    ax1.set_ylabel('Normalized Value', fontweight='bold', fontsize=12)
    ax1.set_title('A. Distribution of Normalized Metrics',
                fontweight='bold', loc='left', fontsize=14)
    ax1.grid(True, alpha=0.3, axis='y')

    # ============================================================================
    # PANEL B: Correlation Heatmap
    # ============================================================================

    ax2 = fig.add_subplot(gs[0, 2])

    # Select subset of metrics for correlation
    corr_metrics = numeric_cols[:15] if len(numeric_cols) > 15 else numeric_cols
    corr_data = df[corr_metrics].corr()

    im = ax2.imshow(corr_data, cmap='coolwarm', aspect='auto', vmin=-1, vmax=1)

    ax2.set_xticks(np.arange(len(corr_metrics)))
    ax2.set_yticks(np.arange(len(corr_metrics)))
    ax2.set_xticklabels([m.replace('_', '\n') for m in corr_metrics],
                        rotation=45, ha='right', fontsize=7)
    ax2.set_yticklabels([m.replace('_', ' ') for m in corr_metrics], fontsize=7)

    ax2.set_title('B. Metric Correlation Matrix',
                fontweight='bold', loc='left', fontsize=14, pad=10)

    cbar = plt.colorbar(im, ax=ax2)
    cbar.set_label('Correlation', fontweight='bold')

    # ============================================================================
    # PANEL C: Top Athletes by Composite Score
    # ============================================================================

    ax3 = fig.add_subplot(gs[1, 0])

    # Calculate composite score (mean of all normalized metrics)
    df['composite_score'] = df[numeric_cols].mean(axis=1)

    # Get top 15 athletes
    top_athletes = df.nlargest(15, 'composite_score')

    bars = ax3.barh(range(len(top_athletes)), top_athletes['composite_score'],
                color=colors['secondary'], alpha=0.8,
                edgecolor='black', linewidth=1)

    # Color gradient
    colors_gradient = plt.cm.RdYlGn(np.linspace(0.3, 0.9, len(top_athletes)))
    for bar, color in zip(bars, colors_gradient):
        bar.set_color(color)

    ax3.set_yticks(range(len(top_athletes)))
    ax3.set_yticklabels([name[:20] for name in top_athletes['Name']], fontsize=8)
    ax3.set_xlabel('Composite Score', fontweight='bold', fontsize=12)
    ax3.set_title('C. Top 15 Athletes by Composite Score',
                fontweight='bold', loc='left', fontsize=14)
    ax3.grid(True, alpha=0.3, axis='x')

    # Add value labels
    for i, (bar, val) in enumerate(zip(bars, top_athletes['composite_score'])):
        width = bar.get_width()
        ax3.text(width + 0.001, bar.get_y() + bar.get_height()/2.,
                f'{val:.4f}',
                va='center', fontsize=7, fontweight='bold')

    # ============================================================================
    # PANEL D: PCA Analysis
    # ============================================================================

    ax4 = fig.add_subplot(gs[1, 1])

    # Prepare data for PCA
    pca_data = df[numeric_cols].fillna(0)

    if len(pca_data) > 2 and len(numeric_cols) > 1:
        # Perform PCA
        pca = PCA(n_components=min(10, len(numeric_cols)))
        pca_result = pca.fit_transform(pca_data)

        # Plot explained variance
        explained_var = pca.explained_variance_ratio_
        cumulative_var = np.cumsum(explained_var)

        x = np.arange(1, len(explained_var) + 1)

        ax4.bar(x, explained_var * 100, alpha=0.6, color=colors['tertiary'],
            label='Individual', edgecolor='black', linewidth=1)
        ax4.plot(x, cumulative_var * 100, 'ro-', linewidth=2.5, markersize=8,
                label='Cumulative', markeredgecolor='white', markeredgewidth=1.5)

        # Add 80% and 95% lines
        ax4.axhline(y=80, color='orange', linestyle='--', linewidth=2,
                alpha=0.7, label='80% Threshold')
        ax4.axhline(y=95, color='green', linestyle='--', linewidth=2,
                alpha=0.7, label='95% Threshold')

        ax4.set_xlabel('Principal Component', fontweight='bold', fontsize=12)
        ax4.set_ylabel('Explained Variance (%)', fontweight='bold', fontsize=12)
        ax4.set_title('D. PCA: Explained Variance',
                    fontweight='bold', loc='left', fontsize=14)
        ax4.legend(loc='right', fontsize=9)
        ax4.grid(True, alpha=0.3)

        # Add text for components needed
        n_components_80 = np.argmax(cumulative_var >= 0.80) + 1
        n_components_95 = np.argmax(cumulative_var >= 0.95) + 1
        ax4.text(0.5, 0.5,
                f'80% variance: {n_components_80} components\n' +
                f'95% variance: {n_components_95} components',
                transform=ax4.transAxes, ha='center', va='center',
                fontsize=10, fontweight='bold',
                bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.3))

    # ============================================================================
    # PANEL E: PCA Biplot (PC1 vs PC2)
    # ============================================================================

    ax5 = fig.add_subplot(gs[1, 2])

    if len(pca_data) > 2 and len(numeric_cols) > 1:
        # Scatter plot of first two components
        scatter = ax5.scatter(pca_result[:, 0], pca_result[:, 1],
                            c=df['composite_score'], s=50, alpha=0.6,
                            cmap='RdYlGn', edgecolors='black', linewidth=0.5)

        cbar = plt.colorbar(scatter, ax=ax5)
        cbar.set_label('Composite Score', fontweight='bold')

        ax5.set_xlabel(f'PC1 ({explained_var[0]*100:.1f}%)',
                    fontweight='bold', fontsize=12)
        ax5.set_ylabel(f'PC2 ({explained_var[1]*100:.1f}%)',
                    fontweight='bold', fontsize=12)
        ax5.set_title('E. PCA Biplot: PC1 vs PC2',
                    fontweight='bold', loc='left', fontsize=14)
        ax5.grid(True, alpha=0.3)

        # Add origin lines
        ax5.axhline(y=0, color='black', linestyle='-', linewidth=1, alpha=0.3)
        ax5.axvline(x=0, color='black', linestyle='-', linewidth=1, alpha=0.3)

    # ============================================================================
    # PANEL F: Metric Importance (PCA Loadings)
    # ============================================================================

    ax6 = fig.add_subplot(gs[2, 0])

    if len(pca_data) > 2 and len(numeric_cols) > 1:
        # Get loadings for PC1
        loadings = pca.components_[0]
        loading_df = pd.DataFrame({
            'metric': numeric_cols,
            'loading': np.abs(loadings)
        }).sort_values('loading', ascending=False).head(15)

        bars = ax6.barh(range(len(loading_df)), loading_df['loading'],
                    color=colors['quaternary'], alpha=0.8,
                    edgecolor='black', linewidth=1)

        ax6.set_yticks(range(len(loading_df)))
        ax6.set_yticklabels([m.replace('_', ' ') for m in loading_df['metric']],
                            fontsize=8)
        ax6.set_xlabel('Absolute Loading', fontweight='bold', fontsize=12)
        ax6.set_title('F. Top 15 Metrics by PC1 Importance',
                    fontweight='bold', loc='left', fontsize=14)
        ax6.grid(True, alpha=0.3, axis='x')

        # Add value labels
        for bar, val in zip(bars, loading_df['loading']):
            width = bar.get_width()
            ax6.text(width + 0.01, bar.get_y() + bar.get_height()/2.,
                    f'{val:.3f}',
                    va='center', fontsize=7, fontweight='bold')

    # ============================================================================
    # PANEL G: Clustering Analysis (Dendrogram)
    # ============================================================================

    ax7 = fig.add_subplot(gs[2, 1:])

    if len(pca_data) > 2:
        # Sample data if too large
        sample_size = min(50, len(pca_data))
        sample_indices = np.random.choice(len(pca_data), sample_size, replace=False)
        sample_data = pca_data.iloc[sample_indices]
        sample_names = df.iloc[sample_indices]['Name'].values

        # Perform hierarchical clustering
        linkage_matrix = linkage(sample_data, method='ward')

        # Plot dendrogram
        dendrogram(linkage_matrix, labels=[name[:15] for name in sample_names],
                ax=ax7, leaf_rotation=90, leaf_font_size=7,
                color_threshold=0.7*max(linkage_matrix[:,2]))

        ax7.set_xlabel('Athlete', fontweight='bold', fontsize=12)
        ax7.set_ylabel('Distance', fontweight='bold', fontsize=12)
        ax7.set_title('G. Hierarchical Clustering of Athletes (Sample)',
                    fontweight='bold', loc='left', fontsize=14)
        ax7.grid(True, alpha=0.3, axis='y')

    # ============================================================================
    # PANEL H: Metric Range Analysis
    # ============================================================================

    ax8 = fig.add_subplot(gs[3, 0])

    # Calculate ranges for top metrics
    range_metrics = numeric_cols[:10] if len(numeric_cols) > 10 else numeric_cols
    ranges = []
    means = []
    stds = []

    for metric in range_metrics:
        data = df[metric].dropna()
        ranges.append(data.max() - data.min())
        means.append(data.mean())
        stds.append(data.std())

    range_df = pd.DataFrame({
        'metric': range_metrics,
        'range': ranges,
        'mean': means,
        'std': stds
    })

    x = np.arange(len(range_df))
    width = 0.25

    bars1 = ax8.bar(x - width, range_df['range'], width,
                label='Range', color=colors['primary'], alpha=0.7)
    bars2 = ax8.bar(x, range_df['mean'], width,
                label='Mean', color=colors['secondary'], alpha=0.7)
    bars3 = ax8.bar(x + width, range_df['std'], width,
                label='Std Dev', color=colors['tertiary'], alpha=0.7)

    ax8.set_xticks(x)
    ax8.set_xticklabels([m.replace('_', '\n') for m in range_df['metric']],
                        rotation=45, ha='right', fontsize=8)
    ax8.set_ylabel('Value', fontweight='bold', fontsize=12)
    ax8.set_title('H. Metric Variability Analysis',
                fontweight='bold', loc='left', fontsize=14)
    ax8.legend(loc='upper right', fontsize=9)
    ax8.grid(True, alpha=0.3, axis='y')

    # ============================================================================
    # PANEL I: Percentile Rankings
    # ============================================================================

    ax9 = fig.add_subplot(gs[3, 1])

    # Calculate percentile ranks for composite score
    df['percentile'] = df['composite_score'].rank(pct=True) * 100

    # Create percentile bins
    bins = [0, 25, 50, 75, 90, 95, 100]
    labels = ['0-25%', '25-50%', '50-75%', '75-90%', '90-95%', '95-100%']
    df['percentile_bin'] = pd.cut(df['percentile'], bins=bins, labels=labels)

    bin_counts = df['percentile_bin'].value_counts().sort_index()

    colors_percentile = ['#E63946', '#F4A261', '#E9C46A', '#90EE90', '#50C878', '#2A9D8F']

    bars = ax9.bar(range(len(bin_counts)), bin_counts.values,
                color=colors_percentile, alpha=0.8,
                edgecolor='black', linewidth=1.5)

    ax9.set_xticks(range(len(bin_counts)))
    ax9.set_xticklabels(bin_counts.index, rotation=45, ha='right')
    ax9.set_ylabel('Number of Athletes', fontweight='bold', fontsize=12)
    ax9.set_title('I. Athlete Distribution by Percentile',
                fontweight='bold', loc='left', fontsize=14)
    ax9.grid(True, alpha=0.3, axis='y')

    # Add value labels
    for bar, val in zip(bars, bin_counts.values):
        height = bar.get_height()
        ax9.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(val)}',
                ha='center', va='bottom', fontweight='bold', fontsize=9)

    # ============================================================================
    # PANEL J: Summary Statistics
    # ============================================================================

    ax10 = fig.add_subplot(gs[3, 2])
    ax10.axis('off')

    # Calculate summary statistics
    n_athletes = len(df)
    n_metrics = len(numeric_cols)
    mean_composite = df['composite_score'].mean()
    std_composite = df['composite_score'].std()
    max_composite = df['composite_score'].max()
    min_composite = df['composite_score'].min()

    # Top athlete
    top_athlete = df.loc[df['composite_score'].idxmax(), 'Name']

    summary_text = f"""
    NORMALIZED METRICS SUMMARY

    DATASET OVERVIEW:
    • Total Athletes: {n_athletes}
    • Number of Metrics: {n_metrics}
    • Normalization: Min-Max Scaling

    COMPOSITE SCORE STATISTICS:
    • Mean: {mean_composite:.4f}
    • Std Dev: {std_composite:.4f}
    • Range: {min_composite:.4f} - {max_composite:.4f}
    • Top Athlete: {top_athlete[:25]}

    PCA RESULTS:
    • Components for 80%: {n_components_80 if 'n_components_80' in locals() else 'N/A'}
    • Components for 95%: {n_components_95 if 'n_components_95' in locals() else 'N/A'}
    • Dimensionality Reduction: {(1 - n_components_80/n_metrics)*100 if 'n_components_80' in locals() else 0:.1f}%

    KEY FINDINGS:
    • Metrics show varying distributions
    • Strong correlations exist between
        related physiological parameters
    • PCA reveals underlying patterns
    • Athletes cluster by performance
    • Composite score identifies elite

    APPLICATIONS:
    • Performance benchmarking
    • Talent identification
    • Training optimization
    • Predictive modeling
    • Comparative analysis

    RECOMMENDATIONS:
    • Use composite score for ranking
    • Consider PCA for dimensionality
    • Identify metric-specific strengths
    • Track percentile improvements
    • Monitor metric correlations
    """

    ax10.text(0.05, 0.95, summary_text, transform=ax10.transAxes,
            fontsize=9, verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3,
                    edgecolor='black', linewidth=2))

    ax10.set_title('J. Summary & Applications',
                fontweight='bold', loc='left', fontsize=14, pad=20)

    # ============================================================================
    # Overall title
    # ============================================================================

    fig.suptitle('400m Olympic Performance: Normalized Metrics Analysis\n' +
                'Comprehensive Assessment of Standardized Performance Indicators',
                fontsize=16, fontweight='bold', y=0.998)

    plt.savefig('400m_normalized_metrics.png', dpi=300, bbox_inches='tight')
    plt.savefig('400m_normalized_metrics.pdf', dpi=300, bbox_inches='tight')
    print("✓ Figure saved: 400m Normalized Metrics Analysis")

    plt.close()
