"""
400m Olympic Performance: Model Evaluation & Classification Analysis
Comprehensive visualization of prediction model performance
"""

import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.gridspec import GridSpec
from sklearn.metrics import confusion_matrix, roc_curve, auc
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

    def load_model_data(filepath):
        """Load model evaluation JSON"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return data

    # Load both model files from same folder
    model_2024 = load_model_data('olympic_400m_analysis_20241115_040822.json')
    model_physio = load_model_data('olympic_400m_physio_analysis_20241126_003701.json')

    # ============================================================================
    # EXTRACT METRICS
    # ============================================================================

    def extract_classification_metrics(model_data):
        """Extract classification report metrics"""
        perf = model_data['model_evaluation']['model_performance']

        classes = []
        precision = []
        recall = []
        f1 = []
        support = []

        for key, metrics in perf.items():
            if key not in ['accuracy', 'macro avg', 'weighted avg']:
                classes.append(int(key))
                precision.append(metrics['precision'])
                recall.append(metrics['recall'])
                f1.append(metrics['f1-score'])
                support.append(metrics['support'])

        return pd.DataFrame({
            'class': classes,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'support': support
        })

    df_2024 = extract_classification_metrics(model_2024)
    df_physio = extract_classification_metrics(model_physio)

    # Get overall metrics
    acc_2024 = model_2024['model_evaluation']['model_performance']['accuracy']
    acc_physio = model_physio['model_evaluation']['model_performance']['accuracy']

    # ============================================================================
    # CREATE FIGURE
    # ============================================================================

    fig = plt.figure(figsize=(20, 16))
    gs = GridSpec(3, 3, figure=fig, hspace=0.35, wspace=0.35)

    colors = {
        'primary': '#2E86AB',
        'secondary': '#A23B72',
        'tertiary': '#F18F01',
        'quaternary': '#C73E1D',
        'success': '#06A77D',
        'warning': '#F77F00'
    }

    # ============================================================================
    # PANEL A: Classification Performance by Class (2024 Model)
    # ============================================================================

    ax1 = fig.add_subplot(gs[0, 0])

    x = np.arange(len(df_2024))
    width = 0.25

    bars1 = ax1.bar(x - width, df_2024['precision'], width,
                label='Precision', color=colors['primary'], alpha=0.8)
    bars2 = ax1.bar(x, df_2024['recall'], width,
                label='Recall', color=colors['secondary'], alpha=0.8)
    bars3 = ax1.bar(x + width, df_2024['f1_score'], width,
                label='F1-Score', color=colors['tertiary'], alpha=0.8)

    # Add value labels
    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax1.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.2f}',
                        ha='center', va='bottom', fontsize=8)

    ax1.set_xlabel('Performance Class', fontweight='bold', fontsize=12)
    ax1.set_ylabel('Score', fontweight='bold', fontsize=12)
    ax1.set_title('A. Classification Performance by Class (Standard Model)',
                fontweight='bold', loc='left', fontsize=13)
    ax1.set_xticks(x)
    ax1.set_xticklabels([f'Class {c}' for c in df_2024['class']], rotation=45)
    ax1.legend(loc='upper right', fontsize=9)
    ax1.grid(True, alpha=0.3, axis='y')
    ax1.set_ylim(0, 1.1)

    # Add overall accuracy
    ax1.text(0.5, 0.95, f'Overall Accuracy: {acc_2024:.3f}',
            transform=ax1.transAxes, ha='center', va='top',
            bbox=dict(boxstyle='round', facecolor=colors['success'], alpha=0.3),
            fontweight='bold', fontsize=10)

    # ============================================================================
    # PANEL B: Classification Performance (Physiological Model)
    # ============================================================================

    ax2 = fig.add_subplot(gs[0, 1])

    x = np.arange(len(df_physio))

    bars1 = ax2.bar(x - width, df_physio['precision'], width,
                label='Precision', color=colors['primary'], alpha=0.8)
    bars2 = ax2.bar(x, df_physio['recall'], width,
                label='Recall', color=colors['secondary'], alpha=0.8)
    bars3 = ax2.bar(x + width, df_physio['f1_score'], width,
                label='F1-Score', color=colors['tertiary'], alpha=0.8)

    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax2.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.2f}',
                        ha='center', va='bottom', fontsize=8)

    ax2.set_xlabel('Performance Class', fontweight='bold', fontsize=12)
    ax2.set_ylabel('Score', fontweight='bold', fontsize=12)
    ax2.set_title('B. Classification Performance (Physiological Model)',
                fontweight='bold', loc='left', fontsize=13)
    ax2.set_xticks(x)
    ax2.set_xticklabels([f'Class {c}' for c in df_physio['class']], rotation=45)
    ax2.legend(loc='upper right', fontsize=9)
    ax2.grid(True, alpha=0.3, axis='y')
    ax2.set_ylim(0, 1.1)

    ax2.text(0.5, 0.95, f'Overall Accuracy: {acc_physio:.3f}',
            transform=ax2.transAxes, ha='center', va='top',
            bbox=dict(boxstyle='round', facecolor=colors['success'], alpha=0.3),
            fontweight='bold', fontsize=10)

    # ============================================================================
    # PANEL C: Model Comparison
    # ============================================================================

    ax3 = fig.add_subplot(gs[0, 2])

    # Compare weighted averages
    metrics_2024 = model_2024['model_evaluation']['model_performance']['weighted avg']
    metrics_physio = model_physio['model_evaluation']['model_performance']['weighted avg']

    comparison_data = {
        'Precision': [metrics_2024['precision'], metrics_physio['precision']],
        'Recall': [metrics_2024['recall'], metrics_physio['recall']],
        'F1-Score': [metrics_2024['f1-score'], metrics_physio['f1-score']],
        'Accuracy': [acc_2024, acc_physio]
    }

    x = np.arange(len(comparison_data))
    width = 0.35

    bars1 = ax3.bar(x - width/2, [comparison_data[k][0] for k in comparison_data.keys()],
                width, label='Standard Model', color=colors['primary'], alpha=0.8)
    bars2 = ax3.bar(x + width/2, [comparison_data[k][1] for k in comparison_data.keys()],
                width, label='Physiological Model', color=colors['secondary'], alpha=0.8)

    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.3f}',
                    ha='center', va='bottom', fontsize=9, fontweight='bold')

    ax3.set_ylabel('Score', fontweight='bold', fontsize=12)
    ax3.set_title('C. Model Comparison (Weighted Averages)',
                fontweight='bold', loc='left', fontsize=13)
    ax3.set_xticks(x)
    ax3.set_xticklabels(comparison_data.keys(), rotation=45)
    ax3.legend(loc='lower right', fontsize=9)
    ax3.grid(True, alpha=0.3, axis='y')
    ax3.set_ylim(0, 1.1)

    # ============================================================================
    # PANEL D: Support Distribution
    # ============================================================================

    ax4 = fig.add_subplot(gs[1, 0])

    x = np.arange(len(df_2024))
    width = 0.35

    bars1 = ax4.bar(x - width/2, df_2024['support'], width,
                label='Standard Model', color=colors['primary'], alpha=0.8)
    bars2 = ax4.bar(x + width/2, df_physio['support'], width,
                label='Physiological Model', color=colors['secondary'], alpha=0.8)

    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax4.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height)}',
                        ha='center', va='bottom', fontsize=8)

    ax4.set_xlabel('Performance Class', fontweight='bold', fontsize=12)
    ax4.set_ylabel('Number of Samples', fontweight='bold', fontsize=12)
    ax4.set_title('D. Class Distribution (Sample Support)',
                fontweight='bold', loc='left', fontsize=13)
    ax4.set_xticks(x)
    ax4.set_xticklabels([f'Class {c}' for c in df_2024['class']])
    ax4.legend(loc='upper right', fontsize=9)
    ax4.grid(True, alpha=0.3, axis='y')

    # Add total
    total_2024 = df_2024['support'].sum()
    total_physio = df_physio['support'].sum()
    ax4.text(0.5, 0.95, f'Total Samples: {int(total_2024)} / {int(total_physio)}',
            transform=ax4.transAxes, ha='center', va='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
            fontsize=9)

    # ============================================================================
    # PANEL E: Performance Heatmap (Standard Model)
    # ============================================================================

    ax5 = fig.add_subplot(gs[1, 1])

    # Create performance matrix
    perf_matrix_2024 = df_2024[['precision', 'recall', 'f1_score']].T.values

    im = ax5.imshow(perf_matrix_2024, cmap='RdYlGn', aspect='auto', vmin=0, vmax=1)

    ax5.set_xticks(np.arange(len(df_2024)))
    ax5.set_yticks(np.arange(3))
    ax5.set_xticklabels([f'Class {c}' for c in df_2024['class']])
    ax5.set_yticklabels(['Precision', 'Recall', 'F1-Score'])

    # Add text annotations
    for i in range(3):
        for j in range(len(df_2024)):
            text = ax5.text(j, i, f'{perf_matrix_2024[i, j]:.2f}',
                        ha="center", va="center", color="black",
                        fontweight='bold', fontsize=9)

    ax5.set_title('E. Performance Heatmap (Standard Model)',
                fontweight='bold', loc='left', fontsize=13, pad=10)

    cbar = plt.colorbar(im, ax=ax5)
    cbar.set_label('Score', fontweight='bold')

    # ============================================================================
    # PANEL F: Performance Heatmap (Physiological Model)
    # ============================================================================

    ax6 = fig.add_subplot(gs[1, 2])

    perf_matrix_physio = df_physio[['precision', 'recall', 'f1_score']].T.values

    im = ax6.imshow(perf_matrix_physio, cmap='RdYlGn', aspect='auto', vmin=0, vmax=1)

    ax6.set_xticks(np.arange(len(df_physio)))
    ax6.set_yticks(np.arange(3))
    ax6.set_xticklabels([f'Class {c}' for c in df_physio['class']])
    ax6.set_yticklabels(['Precision', 'Recall', 'F1-Score'])

    for i in range(3):
        for j in range(len(df_physio)):
            text = ax6.text(j, i, f'{perf_matrix_physio[i, j]:.2f}',
                        ha="center", va="center", color="black",
                        fontweight='bold', fontsize=9)

    ax6.set_title('F. Performance Heatmap (Physiological Model)',
                fontweight='bold', loc='left', fontsize=13, pad=10)

    cbar = plt.colorbar(im, ax=ax6)
    cbar.set_label('Score', fontweight='bold')

    # ============================================================================
    # PANEL G: Class Imbalance Analysis
    # ============================================================================

    ax7 = fig.add_subplot(gs[2, 0])

    # Calculate class proportions
    total_samples = df_2024['support'].sum()
    proportions = df_2024['support'] / total_samples * 100

    colors_pie = [colors['primary'], colors['secondary'], colors['tertiary'],
                colors['quaternary'], colors['success'], colors['warning']][:len(df_2024)]

    wedges, texts, autotexts = ax7.pie(proportions, labels=[f'Class {c}' for c in df_2024['class']],
                                        autopct='%1.1f%%', colors=colors_pie, startangle=90)

    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
        autotext.set_fontsize(9)

    ax7.set_title('G. Class Distribution (Imbalance Analysis)',
                fontweight='bold', loc='left', fontsize=13, pad=10)

    # Add legend with sample counts
    legend_labels = [f'Class {c}: n={int(s)}' for c, s in zip(df_2024['class'], df_2024['support'])]
    ax7.legend(legend_labels, loc='upper left', bbox_to_anchor=(1, 1), fontsize=8)

    # ============================================================================
    # PANEL H: Precision-Recall Trade-off
    # ============================================================================

    ax8 = fig.add_subplot(gs[2, 1])

    # Standard model
    ax8.scatter(df_2024['recall'], df_2024['precision'],
            s=df_2024['support']*5, alpha=0.6, color=colors['primary'],
            label='Standard Model', edgecolors='black', linewidth=1.5)

    # Physiological model
    ax8.scatter(df_physio['recall'], df_physio['precision'],
            s=df_physio['support']*5, alpha=0.6, color=colors['secondary'],
            label='Physiological Model', edgecolors='black', linewidth=1.5,
            marker='s')

    # Add class labels
    for idx, row in df_2024.iterrows():
        if row['recall'] > 0 or row['precision'] > 0:
            ax8.annotate(f"C{row['class']}",
                        (row['recall'], row['precision']),
                        fontsize=8, ha='center')

    # Diagonal line (perfect precision-recall)
    ax8.plot([0, 1], [0, 1], 'k--', alpha=0.3, linewidth=1)

    ax8.set_xlabel('Recall', fontweight='bold', fontsize=12)
    ax8.set_ylabel('Precision', fontweight='bold', fontsize=12)
    ax8.set_title('H. Precision-Recall Trade-off',
                fontweight='bold', loc='left', fontsize=13)
    ax8.legend(loc='lower left', fontsize=9)
    ax8.grid(True, alpha=0.3)
    ax8.set_xlim(-0.05, 1.05)
    ax8.set_ylim(-0.05, 1.05)

    # ============================================================================
    # PANEL I: Model Performance Summary
    # ============================================================================

    ax9 = fig.add_subplot(gs[2, 2])
    ax9.axis('off')

    summary_text = f"""
    MODEL PERFORMANCE SUMMARY

    STANDARD MODEL (Nov 2024):
    • Overall Accuracy: {acc_2024:.3f}
    • Weighted Precision: {metrics_2024['precision']:.3f}
    • Weighted Recall: {metrics_2024['recall']:.3f}
    • Weighted F1-Score: {metrics_2024['f1-score']:.3f}
    • Total Samples: {int(total_2024)}

    PHYSIOLOGICAL MODEL (Nov 2024):
    • Overall Accuracy: {acc_physio:.3f}
    • Weighted Precision: {metrics_physio['precision']:.3f}
    • Weighted Recall: {metrics_physio['recall']:.3f}
    • Weighted F1-Score: {metrics_physio['f1-score']:.3f}
    • Total Samples: {int(total_physio)}

    KEY FINDINGS:
    • Class 0 dominates dataset (>90% samples)
    • Severe class imbalance affects minority classes
    • Both models struggle with rare classes (1-5)
    • High precision on majority class
    • Need for balanced sampling or cost-sensitive learning

    RECOMMENDATIONS:
    1. Implement SMOTE or class weighting
    2. Collect more minority class samples
    3. Consider ensemble methods
    4. Use stratified cross-validation
    5. Optimize threshold for each class
    """

    ax9.text(0.05, 0.95, summary_text, transform=ax9.transAxes,
            fontsize=9, verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3,
                    edgecolor='black', linewidth=2))

    ax9.set_title('I. Performance Summary & Recommendations',
                fontweight='bold', loc='left', fontsize=13, pad=20)

    # ============================================================================
    # Overall title
    # ============================================================================

    fig.suptitle('400m Olympic Performance: Model Evaluation & Classification Analysis\n' +
                'Comprehensive Assessment of Prediction Models',
                fontsize=16, fontweight='bold', y=0.995)

    # Save to figures directory
    os.makedirs('figures', exist_ok=True)
    plt.savefig('figures/400m_model_evaluation.png', dpi=300, bbox_inches='tight')
    print("✓ Figure saved: figures/400m_model_evaluation.png")

    plt.close()
