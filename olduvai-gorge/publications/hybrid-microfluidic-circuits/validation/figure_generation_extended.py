"""
Extended Figure Generation: Substrate-Context Separation, Learning, Consciousness

Generates 5 new publication panels validating:
1. Substrate-neutral thoughts
2. Learning as context remapping
3. Circuit closure requirement
4. Emotional field modulation
5. Free will as context selection
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D
from pathlib import Path
import json

from validation_extended import (
    SubstrateContextExperiment,
    LearningContextRemappingExperiment,
    CircuitClosureExperiment,
    EmotionalFieldModulationExperiment,
    FreeWillContextSelectionExperiment
)


class ExtendedFigureGenerator:
    """Generate publication-quality panels for extended validation."""

    def __init__(self, output_dir='./extended_validation_figures'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        plt.rcParams.update({
            'figure.facecolor': 'white',
            'axes.facecolor': 'white',
            'axes.edgecolor': 'black',
            'axes.linewidth': 1.2,
            'font.size': 8,
            'font.family': 'sans-serif',
            'xtick.direction': 'out',
            'ytick.direction': 'out',
            'grid.alpha': 0.3,
            'grid.linestyle': '--'
        })

    def panel_7_substrate_context_separation(self):
        """Panel 7: Substrate-neutral thoughts with different emotional contexts."""
        fig, axes = plt.subplots(1, 4, figsize=(22, 4.5))
        fig.patch.set_facecolor('white')

        result = SubstrateContextExperiment.run()
        data = result['substrate_context_separation']

        # Chart A: Motor outputs in three contexts
        time = np.linspace(0, 0.5, 200)
        contexts = ['pain_automatic', 'skill_intentional', 'neutral_analytical']
        colors = ['#d62728', '#2ca02c', '#ff7f0e']
        context_labels = ['Pain (Reflex)', 'Skill (Intentional)', 'Neutral (Analytical)']

        for ctx, color, label in zip(contexts, colors, context_labels):
            output = np.array(data[ctx]['motor_output'])
            axes[0].plot(time * 1000, output, linewidth=2.5, color=color, label=label)

        axes[0].set_xlabel('Time (ms)', fontsize=9)
        axes[0].set_ylabel('Motor Output', fontsize=9)
        axes[0].legend(fontsize=7, loc='upper right')
        axes[0].grid(True, alpha=0.3)
        axes[0].set_title('A. Same Substrate, Different Contexts', fontsize=10, weight='bold', loc='left')

        # Chart B: 3D emotional context space
        ax = fig.add_axes([0.27, 0.15, 0.18, 0.8], projection='3d')

        context_points = [
            (20, 0.02, 1),  # Pain
            (200, 0.2, 0.5),  # Skill
            (100, 0.1, 0)   # Neutral
        ]
        colors_3d = ['#d62728', '#2ca02c', '#ff7f0e']
        labels_3d = ['Pain', 'Skill', 'Neutral']

        for point, color, label in zip(context_points, colors_3d, labels_3d):
            ax.scatter(*point, c=color, s=200, marker='o', edgecolor='black', linewidth=1.5, zorder=5)

        ax.set_xlabel('τ (ms)', fontsize=8)
        ax.set_ylabel('Execution\nSpeed', fontsize=8)
        ax.set_zlabel('Perceived\nQuality', fontsize=8)
        ax.set_title('B. Emotional Context Space', fontsize=10, weight='bold')

        # Chart C: Peak amplitude comparison
        peak_amps = [data[ctx]['peak_amplitude'] for ctx in contexts]
        bars = axes[2].bar(context_labels, peak_amps, color=colors, alpha=0.7, edgecolor='black', linewidth=1.2)
        axes[2].set_ylabel('Peak Amplitude', fontsize=9)
        axes[2].grid(True, alpha=0.3, axis='y')
        axes[2].set_title('C. Amplitude by Context', fontsize=10, weight='bold', loc='left')
        axes[2].tick_params(axis='x', rotation=45)

        # Chart D: Time to peak
        times_to_peak = [data[ctx]['time_to_peak'] * 1000 for ctx in contexts]
        axes[3].bar(context_labels, times_to_peak, color=colors, alpha=0.7, edgecolor='black', linewidth=1.2)
        axes[3].set_ylabel('Time to Peak (ms)', fontsize=9)
        axes[3].grid(True, alpha=0.3, axis='y')
        axes[3].set_title('D. Response Latency', fontsize=10, weight='bold', loc='left')
        axes[3].tick_params(axis='x', rotation=45)

        plt.tight_layout()
        return fig

    def panel_8_learning_context_remapping(self):
        """Panel 8: Learning as emotional context remapping."""
        fig, axes = plt.subplots(1, 4, figsize=(22, 4.5))
        fig.patch.set_facecolor('white')

        result = LearningContextRemappingExperiment.run()
        data = result['learning_context_remapping']

        time = np.linspace(0, 1.0, 300)
        stages = ['stage_0_naive', 'stage_1_early_learning', 'stage_2_mid_learning', 'stage_3_mastery']
        stage_labels = ['Naive', 'Early\nLearning', 'Mid\nLearning', 'Mastery']
        colors = ['#d62728', '#ff7f0e', '#2ca02c', '#1f77b4']

        # Chart A: Motor output evolution through learning
        for stage, color, label in zip(stages, colors, stage_labels):
            output = np.array(data[stage]['output'])
            axes[0].plot(time, output, linewidth=2.5, color=color, label=label, alpha=0.8)

        axes[0].set_xlabel('Time (s)', fontsize=9)
        axes[0].set_ylabel('Motor Output', fontsize=9)
        axes[0].legend(fontsize=7, loc='upper right')
        axes[0].grid(True, alpha=0.3)
        axes[0].set_title('A. Learning Progression', fontsize=10, weight='bold', loc='left')

        # Chart B: 3D learning landscape
        ax = fig.add_axes([0.27, 0.15, 0.18, 0.8], projection='3d')

        stage_nums = np.arange(len(stages))
        taus = [data[stage]['tau_effective'] for stage in stages]
        accessibility = [data[stage]['substrate_accessibility_slow_circuit'] for stage in stages]

        # Create surface
        stage_grid, time_grid = np.meshgrid(stage_nums, np.linspace(0, 1, 20))
        accessibility_grid = np.zeros_like(stage_grid, dtype=float)
        for i, s in enumerate(stage_nums):
            accessibility_grid[:, i] = accessibility[i]

        ax.plot_surface(stage_grid, time_grid, accessibility_grid, cmap='viridis', alpha=0.8)
        ax.set_xlabel('Learning Stage', fontsize=8)
        ax.set_ylabel('Time', fontsize=8)
        ax.set_zlabel('Slow Circuit\nAccessibility', fontsize=8)
        ax.set_title('B. 3D Learning Surface', fontsize=10, weight='bold')

        # Chart C: Substrate accessibility across learning
        accessibility_vals = [data[stage]['substrate_accessibility_slow_circuit'] for stage in stages]
        control_vals = [data[stage]['conscious_control_available'] for stage in stages]

        x_pos = np.arange(len(stage_labels))
        width = 0.35

        axes[2].bar(x_pos - width/2, accessibility_vals, width, label='Slow Circuit\nAccess',
                   color='#1f77b4', alpha=0.7, edgecolor='black', linewidth=1.2)
        axes[2].bar(x_pos + width/2, control_vals, width, label='Conscious\nControl',
                   color='#ff7f0e', alpha=0.7, edgecolor='black', linewidth=1.2)

        axes[2].set_xticks(x_pos)
        axes[2].set_xticklabels(stage_labels, fontsize=8)
        axes[2].set_ylabel('Availability', fontsize=9)
        axes[2].legend(fontsize=7)
        axes[2].set_ylim([0, 1.2])
        axes[2].grid(True, alpha=0.3, axis='y')
        axes[2].set_title('C. Context Accessibility', fontsize=10, weight='bold', loc='left')

        # Chart D: Execution speed progression
        execution_speeds = [data[stage]['execution_speed'] for stage in stages]
        axes[3].plot(stage_labels, execution_speeds, 'o-', color='#2ca02c', markersize=8,
                    linewidth=2.5, markeredgecolor='black', markeredgewidth=1.2)
        axes[3].set_ylabel('Execution Speed (1/τ)', fontsize=9)
        axes[3].grid(True, alpha=0.3)
        axes[3].set_title('D. Speed Progression', fontsize=10, weight='bold', loc='left')

        plt.tight_layout()
        return fig

    def panel_9_circuit_closure_requirement(self):
        """Panel 9: Circuit closure requirement and deafferentation effects."""
        fig, axes = plt.subplots(1, 4, figsize=(22, 4.5))
        fig.patch.set_facecolor('white')

        result = CircuitClosureExperiment.run()
        data = result['circuit_closure']

        time = np.linspace(0, 1.0, 200)

        # Chart A: Charge circulation comparison
        complete = np.array(data['complete_circuit']['output'])
        severed = np.array(data['deafferented_circuit']['output'])
        visual = np.array(data['visual_substitute_circuit']['output'])

        axes[0].plot(time, complete, linewidth=2.5, color='#2ca02c', label='Complete Circuit')
        axes[0].plot(time, severed, linewidth=2.5, color='#d62728', label='Severed Return', linestyle='--')
        axes[0].plot(time, visual, linewidth=2.5, color='#ff7f0e', label='Visual Substitute')
        axes[0].axhline(0, color='black', linestyle='-', linewidth=0.5)
        axes[0].set_xlabel('Time (s)', fontsize=9)
        axes[0].set_ylabel('Charge Balance', fontsize=9)
        axes[0].legend(fontsize=7)
        axes[0].grid(True, alpha=0.3)
        axes[0].set_title('A. Circuit Closure States', fontsize=10, weight='bold', loc='left')

        # Chart B: 3D circuit states
        ax = fig.add_axes([0.27, 0.15, 0.18, 0.8], projection='3d')

        circuit_types = ['Complete', 'Severed', 'Visual']
        circuit_colors = ['#2ca02c', '#d62728', '#ff7f0e']

        # 3D positions representing circuit characteristics
        circuit_points = [
            (1.0, 1.0, 1.0),   # Complete: balanced, fast, coordinated
            (0.0, 0.0, 0.0),   # Severed: unbalanced, stopped, abolished
            (0.5, 0.3, 0.6)    # Visual: balanced but slow, partial control
        ]

        for point, color, label in zip(circuit_points, circuit_colors, circuit_types):
            ax.scatter(*point, c=color, s=300, marker='o', edgecolor='black', linewidth=1.5, zorder=5)

        ax.set_xlabel('Circuit Balance', fontsize=8)
        ax.set_ylabel('Execution Speed', fontsize=8)
        ax.set_zlabel('Movement\nCoordination', fontsize=8)
        ax.set_title('B. Circuit State Space', fontsize=10, weight='bold')

        # Chart C: Movement capability
        capabilities = {
            'Complete': 'Full Coordinated',
            'Severed': 'Abolished',
            'Visual': 'With Attention'
        }
        capability_scores = [1.0, 0.0, 0.6]

        axes[2].bar(circuit_types, capability_scores, color=circuit_colors, alpha=0.7,
                   edgecolor='black', linewidth=1.2)
        axes[2].set_ylabel('Movement Capability', fontsize=9)
        axes[2].set_ylim([0, 1.2])
        axes[2].grid(True, alpha=0.3, axis='y')
        axes[2].set_title('C. Movement Capability', fontsize=10, weight='bold', loc='left')

        # Chart D: Conscious overhead
        overhead = [0.1, np.inf, 0.8]  # Complete needs minimal, severed impossible, visual high
        overhead_display = [0.1, 1.0, 0.8]  # For display

        axes[3].bar(circuit_types, overhead_display, color=circuit_colors, alpha=0.7,
                   edgecolor='black', linewidth=1.2)
        axes[3].set_ylabel('Conscious Overhead', fontsize=9)
        axes[3].set_ylim([0, 1.2])
        axes[3].grid(True, alpha=0.3, axis='y')
        axes[3].set_title('D. Cognitive Demand', fontsize=10, weight='bold', loc='left')

        plt.tight_layout()
        return fig

    def panel_10_emotional_field_modulation(self):
        """Panel 10: Emotional field modulation of sensation quality."""
        fig, axes = plt.subplots(1, 4, figsize=(22, 4.5))
        fig.patch.set_facecolor('white')

        result = EmotionalFieldModulationExperiment.run()
        data = result['emotional_field_modulation']

        time = np.linspace(0, 0.5, 200)
        fields = ['pain_field', 'pleasure_field', 'neutral_field', 'skill_field']
        field_labels = ['Pain', 'Pleasure', 'Neutral', 'Skill']
        colors = ['#d62728', '#2ca02c', '#ff7f0e', '#1f77b4']

        # Chart A: Sensation time courses in different emotional fields
        for field, color, label in zip(fields, colors, field_labels):
            sensation = np.array(data[field]['sensation_time_course'])
            axes[0].plot(time * 1000, sensation, linewidth=2.5, color=color, label=label)

        axes[0].set_xlabel('Time (ms)', fontsize=9)
        axes[0].set_ylabel('Sensation Quality', fontsize=9)
        axes[0].legend(fontsize=7, loc='upper right')
        axes[0].grid(True, alpha=0.3)
        axes[0].set_title('A. Sensation Time Courses', fontsize=10, weight='bold', loc='left')

        # Chart B: 3D emotional field space
        ax = fig.add_axes([0.27, 0.15, 0.18, 0.8], projection='3d')

        field_points = [
            (0.02, 0.05, 0),    # Pain
            (0.2, 0.5, 1),      # Pleasure
            (0.1, 0.15, 0.5),   # Neutral
            (0.05, 0.2, 0.7)    # Skill
        ]

        for point, color, label in zip(field_points, colors, field_labels):
            ax.scatter(*point, c=color, s=200, marker='o', edgecolor='black', linewidth=1.5, zorder=5)

        ax.set_xlabel('τ_fast (s)', fontsize=8)
        ax.set_ylabel('τ_slow (s)', fontsize=8)
        ax.set_zlabel('Perceived\nQuality', fontsize=8)
        ax.set_title('B. Emotional Field Space', fontsize=10, weight='bold')

        # Chart C: Peak sensation by field
        peaks = [data[field]['peak_sensation'] for field in fields]
        axes[2].bar(field_labels, peaks, color=colors, alpha=0.7, edgecolor='black', linewidth=1.2)
        axes[2].set_ylabel('Peak Sensation', fontsize=9)
        axes[2].grid(True, alpha=0.3, axis='y')
        axes[2].set_title('C. Peak Intensity', fontsize=10, weight='bold', loc='left')

        # Chart D: Sensation duration
        durations = [data[field]['sensation_duration'] for field in fields]
        axes[3].bar(field_labels, durations, color=colors, alpha=0.7, edgecolor='black', linewidth=1.2)
        axes[3].set_ylabel('Duration (normalized)', fontsize=9)
        axes[3].grid(True, alpha=0.3, axis='y')
        axes[3].set_title('D. Sensation Duration', fontsize=10, weight='bold', loc='left')

        plt.tight_layout()
        return fig

    def panel_11_free_will_context_selection(self):
        """Panel 11: Free will as intentional context selection."""
        fig, axes = plt.subplots(1, 4, figsize=(22, 4.5))
        fig.patch.set_facecolor('white')

        result = FreeWillContextSelectionExperiment.run()
        data = result['free_will_context_selection']

        time = np.linspace(0, 1.0, 300)
        modes = ['no_control_automatic', 'partial_control_deliberate', 'full_control_skilled']
        mode_labels = ['No Control\n(Automatic)', 'Partial Control\n(Deliberate)', 'Full Control\n(Skilled)']
        colors = ['#d62728', '#ff7f0e', '#2ca02c']

        # Chart A: Voluntary modulation responses
        for mode, color, label in zip(modes, colors, mode_labels):
            response = np.array(data[mode]['modulated_response'])
            axes[0].plot(time, response, linewidth=2.5, color=color, label=label, alpha=0.8)

        axes[0].set_xlabel('Time (s)', fontsize=9)
        axes[0].set_ylabel('Motor Response', fontsize=9)
        axes[0].legend(fontsize=7, loc='upper right')
        axes[0].grid(True, alpha=0.3)
        axes[0].set_title('A. Voluntary Modulation', fontsize=10, weight='bold', loc='left')

        # Chart B: 3D free will state space
        ax = fig.add_axes([0.27, 0.15, 0.18, 0.8], projection='3d')

        will_points = [
            (0.0, 0.0, 0.0),   # No control
            (0.5, 0.5, 0.5),   # Partial control
            (1.0, 1.0, 1.0)    # Full control
        ]

        for point, color, label in zip(will_points, colors, mode_labels):
            ax.scatter(*point, c=color, s=250, marker='o', edgecolor='black', linewidth=1.5, zorder=5)

        ax.set_xlabel('Voluntary\nIntention', fontsize=8)
        ax.set_ylabel('Conscious\nModulation', fontsize=8)
        ax.set_zlabel('Intentional\nInfluence', fontsize=8)
        ax.set_title('B. Free Will State Space', fontsize=10, weight='bold')

        # Chart C: Conscious modulation levels
        modulation_fracs = [data[mode]['conscious_modulation_fraction'] for mode in modes]
        bars = axes[2].bar(mode_labels, modulation_fracs, color=colors, alpha=0.7,
                          edgecolor='black', linewidth=1.2)
        axes[2].set_ylabel('Modulation Fraction', fontsize=9)
        axes[2].set_ylim([0, 1.2])
        axes[2].grid(True, alpha=0.3, axis='y')
        axes[2].set_title('C. Conscious Control', fontsize=10, weight='bold', loc='left')

        # Chart D: Intentional influence
        intentional_inf = [data[mode]['intentional_influence'] for mode in modes]
        axes[3].bar(mode_labels, intentional_inf, color=colors, alpha=0.7,
                   edgecolor='black', linewidth=1.2)
        axes[3].set_ylabel('Intentional Influence', fontsize=9)
        axes[3].set_ylim([-1.2, 1.2])
        axes[3].grid(True, alpha=0.3, axis='y')
        axes[3].set_title('D. Volitional Influence', fontsize=10, weight='bold', loc='left')

        plt.tight_layout()
        return fig

    def generate_all_panels(self):
        """Generate all 5 extended validation panels."""
        panels = [
            (self.panel_7_substrate_context_separation, 'Panel_7_Substrate_Context_Separation'),
            (self.panel_8_learning_context_remapping, 'Panel_8_Learning_Context_Remapping'),
            (self.panel_9_circuit_closure_requirement, 'Panel_9_Circuit_Closure_Requirement'),
            (self.panel_10_emotional_field_modulation, 'Panel_10_Emotional_Field_Modulation'),
            (self.panel_11_free_will_context_selection, 'Panel_11_Free_Will_Context_Selection')
        ]

        results = {}
        for panel_func, panel_name in panels:
            print(f"Generating {panel_name}...")
            fig = panel_func()

            filepath_pdf = self.output_dir / f'{panel_name}.pdf'
            fig.savefig(filepath_pdf, dpi=300, bbox_inches='tight', facecolor='white')

            filepath_png = self.output_dir / f'{panel_name}.png'
            fig.savefig(filepath_png, dpi=300, bbox_inches='tight', facecolor='white')

            plt.close(fig)

            results[panel_name] = {
                'pdf': str(filepath_pdf),
                'png': str(filepath_png)
            }

        return results


def main():
    """Generate all extended validation figures."""
    print("\n" + "="*70)
    print("EXTENDED VALIDATION FIGURE GENERATION")
    print("="*70 + "\n")

    generator = ExtendedFigureGenerator(output_dir='./extended_validation_figures')
    results = generator.generate_all_panels()

    print("\nGenerated figures:")
    for panel_name, files in results.items():
        print(f"  {panel_name}: PDF + PNG")

    return results


if __name__ == '__main__':
    main()
