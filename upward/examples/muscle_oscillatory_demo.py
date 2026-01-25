"""
Comprehensive Demo: Oscillatory Muscle Modeling

Demonstrates the multi-scale oscillatory coupling framework applied to
muscle mechanics and body segment coordination.

This example shows:
1. Basic muscle simulation with and without oscillatory coupling
2. Multi-scale frequency decomposition
3. Coupling strength analysis
4. State space visualization
5. Body segment coordination
6. Performance prediction from coupling dynamics
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Import oscillatory muscle framework
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from muscle import (
    OscillatoryMuscleModel,
    LowerLimbModel,
    OscillatoryCouplingAnalyzer,
    StateSpaceCoordinates,
    OscillatoryHierarchy,
)


def demo_1_basic_comparison():
    """Demo 1: Compare classical vs oscillatory muscle model."""
    print("\n" + "="*60)
    print("DEMO 1: Classical vs Oscillatory Muscle Model")
    print("="*60)

    # Create two models
    muscle_coupled = OscillatoryMuscleModel()
    muscle_uncoupled = OscillatoryMuscleModel()

    # Excitation: step input
    def excitation(t):
        return 1.0 if 0.5 <= t <= 2.5 else 0.01

    # Muscle-tendon length: isometric
    lmt0 = 0.31
    def lmt_isometric(t):
        return lmt0

    print("\nSimulating with oscillatory coupling...")
    results_coupled = muscle_coupled.simulate_muscle_with_coupling(
        excitation, lmt_isometric,
        t_span=(0, 3.5),
        enable_coupling=True
    )

    print("Simulating without oscillatory coupling (classical)...")
    results_uncoupled = muscle_uncoupled.simulate_muscle_with_coupling(
        excitation, lmt_isometric,
        t_span=(0, 3.5),
        enable_coupling=False
    )

    # Compute metrics
    metrics_coupled = muscle_coupled.compute_performance_metrics(results_coupled)
    metrics_uncoupled = muscle_uncoupled.compute_performance_metrics(results_uncoupled)

    print("\n--- Performance Metrics ---")
    print("\nWith Oscillatory Coupling:")
    for key, val in metrics_coupled.items():
        print(f"  {key:25s}: {val:10.4f}")

    print("\nWithout Coupling (Classical):")
    for key, val in metrics_uncoupled.items():
        print(f"  {key:25s}: {val:10.4f}")

    # Calculate improvement
    force_diff = ((metrics_coupled['peak_force'] - metrics_uncoupled['peak_force']) /
                  metrics_uncoupled['peak_force'] * 100)
    print(f"\nForce modulation from coupling: {force_diff:+.2f}%")

    # Visualization
    fig = plt.figure(figsize=(14, 10))

    # Force comparison
    ax1 = plt.subplot(3, 2, 1)
    ax1.plot(results_coupled['time'], results_coupled['muscle_force'],
             'b-', linewidth=2, label='With Coupling')
    ax1.plot(results_uncoupled['time'], results_uncoupled['muscle_force'],
             'r--', linewidth=2, label='Classical')
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Force (N)')
    ax1.set_title('Muscle Force')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Activation
    ax2 = plt.subplot(3, 2, 2)
    ax2.plot(results_coupled['time'], results_coupled['activation'],
             'b-', linewidth=2, label='With Coupling')
    ax2.plot(results_uncoupled['time'], results_uncoupled['activation'],
             'r--', linewidth=2, label='Classical')
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Activation')
    ax2.set_title('Muscle Activation')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Coupling strength over time
    ax3 = plt.subplot(3, 2, 3)
    ax3.plot(results_coupled['time'], results_coupled['coupling_strength'], 'g-', linewidth=2)
    ax3.set_xlabel('Time (s)')
    ax3.set_ylabel('Avg Coupling Strength')
    ax3.set_title('Inter-Scale Coupling Evolution')
    ax3.grid(True, alpha=0.3)

    # State space trajectory
    ax4 = plt.subplot(3, 2, 4)
    coords = results_coupled['state_coordinates']
    if np.any(coords):
        ax4.plot(coords[:, 0], coords[:, 1], 'b-', linewidth=1.5)
        ax4.scatter(coords[0, 0], coords[0, 1], c='g', s=100, marker='o',
                   label='Start', zorder=5)
        ax4.scatter(coords[-1, 0], coords[-1, 1], c='r', s=100, marker='s',
                   label='End', zorder=5)
        ax4.set_xlabel('Knowledge Dimension')
        ax4.set_ylabel('Time Dimension')
        ax4.set_title('State Space Trajectory')
        ax4.legend()
        ax4.grid(True, alpha=0.3)

    # Coupling matrix
    ax5 = plt.subplot(3, 2, 5)
    if results_coupled['coupling_matrix'] is not None:
        cm = results_coupled['coupling_matrix']
        im = ax5.imshow(cm, cmap='hot', aspect='auto', interpolation='nearest')
        ax5.set_title('Final Coupling Matrix')
        ax5.set_xlabel('Scale Index')
        ax5.set_ylabel('Scale Index')

        # Add scale labels
        scale_names_short = [name[:4] for name in results_coupled['scales']]
        ax5.set_xticks(range(len(scale_names_short)))
        ax5.set_yticks(range(len(scale_names_short)))
        ax5.set_xticklabels(scale_names_short, rotation=45)
        ax5.set_yticklabels(scale_names_short)

        plt.colorbar(im, ax=ax5, label='Coupling Strength')

    # Force difference
    ax6 = plt.subplot(3, 2, 6)
    force_diff_trace = (results_coupled['muscle_force'] -
                        results_uncoupled['muscle_force'])
    ax6.plot(results_coupled['time'], force_diff_trace, 'purple', linewidth=2)
    ax6.axhline(y=0, color='k', linestyle='--', alpha=0.5)
    ax6.set_xlabel('Time (s)')
    ax6.set_ylabel('Force Difference (N)')
    ax6.set_title('Coupling Effect on Force')
    ax6.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('demo1_muscle_comparison.png', dpi=150, bbox_inches='tight')
    print("\nPlot saved: demo1_muscle_comparison.png")
    plt.show()

    return results_coupled, results_uncoupled


def demo_2_frequency_decomposition():
    """Demo 2: Multi-scale frequency decomposition of muscle force."""
    print("\n" + "="*60)
    print("DEMO 2: Multi-Scale Frequency Decomposition")
    print("="*60)

    muscle = OscillatoryMuscleModel()

    # Rhythmic excitation (simulate tremor or rhythmic activity)
    def excitation_rhythmic(t):
        base = 0.5
        tremor = 0.3 * np.sin(2 * np.pi * 6 * t)  # 6 Hz tremor
        rhythm = 0.2 * np.sin(2 * np.pi * 1.5 * t)  # 1.5 Hz movement
        return np.clip(base + tremor + rhythm, 0.01, 1.0)

    # Isometric
    def lmt(t):
        return 0.31

    print("\nSimulating muscle with rhythmic excitation...")
    results = muscle.simulate_muscle_with_coupling(
        excitation_rhythmic, lmt,
        t_span=(0, 5.0),
        dt=0.001,
        enable_coupling=True
    )

    # Extract oscillatory signals
    force_signal = results['muscle_force']
    time_signal = results['time']

    print("\nExtracting oscillatory components at each scale...")
    oscillatory_signals = muscle.extract_oscillatory_components(
        force_signal, time_signal
    )

    # Visualize
    fig = plt.figure(figsize=(14, 10))

    # Original force
    ax1 = plt.subplot(4, 2, 1)
    ax1.plot(time_signal, force_signal, 'k-', linewidth=1)
    ax1.set_ylabel('Force (N)')
    ax1.set_title('Original Force Signal')
    ax1.grid(True, alpha=0.3)

    # Excitation
    ax2 = plt.subplot(4, 2, 2)
    exc = [excitation_rhythmic(t) for t in time_signal]
    ax2.plot(time_signal, exc, 'b-', linewidth=1)
    ax2.set_ylabel('Excitation')
    ax2.set_title('Rhythmic Excitation')
    ax2.grid(True, alpha=0.3)

    # Individual scale signals
    scales = muscle.scales
    for i, scale in enumerate(scales[:6]):  # Plot first 6 scales
        ax = plt.subplot(4, 2, i+3)
        if scale.name in oscillatory_signals:
            signal = oscillatory_signals[scale.name]
            ax.plot(time_signal, signal, linewidth=1)
            ax.set_ylabel('Amplitude')
            ax.set_title(f'{scale.name} ({scale.freq_min:.1f}-{scale.freq_max:.1f} Hz)')
            ax.grid(True, alpha=0.3)

            if i >= 4:
                ax.set_xlabel('Time (s)')

    plt.tight_layout()
    plt.savefig('demo2_frequency_decomposition.png', dpi=150, bbox_inches='tight')
    print("\nPlot saved: demo2_frequency_decomposition.png")
    plt.show()

    # Compute power spectral density
    print("\n--- Power Spectral Density at Each Scale ---")
    for scale in scales:
        if scale.name in oscillatory_signals:
            signal = oscillatory_signals[scale.name]
            power = np.mean(signal**2)
            print(f"{scale.name:20s}: {power:10.2e} N²")

    return results, oscillatory_signals


def demo_3_dynamic_coupling():
    """Demo 3: Dynamic coupling during transient activation."""
    print("\n" + "="*60)
    print("DEMO 3: Dynamic Coupling During Activation")
    print("="*60)

    muscle = OscillatoryMuscleModel()

    # Rapid activation then hold
    def excitation(t):
        if t < 0.5:
            return 0.01
        elif t < 0.7:
            return (t - 0.5) / 0.2  # Ramp up
        elif t < 2.5:
            return 1.0
        else:
            return np.exp(-(t - 2.5) / 0.3)  # Exponential decay

    def lmt(t):
        return 0.31

    print("\nSimulating with dynamic coupling analysis...")
    results = muscle.simulate_muscle_with_coupling(
        excitation, lmt,
        t_span=(0, 4.0),
        enable_coupling=True
    )

    # Analyze coupling evolution
    t = results['time']
    force = results['muscle_force']
    coupling = results['coupling_strength']
    coords = results['state_coordinates']

    # Find key time points
    idx_activation = np.argmax(results['activation'] > 0.5)
    idx_peak_force = np.argmax(force)
    t_activation = t[idx_activation] if idx_activation > 0 else 0
    t_peak = t[idx_peak_force]

    print(f"\nActivation threshold reached at: {t_activation:.3f} s")
    print(f"Peak force reached at: {t_peak:.3f} s")
    print(f"Delay: {t_peak - t_activation:.3f} s")

    # Visualize
    fig = plt.figure(figsize=(14, 8))

    # Force and coupling overlay
    ax1 = plt.subplot(2, 2, 1)
    ax1_twin = ax1.twinx()

    l1 = ax1.plot(t, force, 'b-', linewidth=2, label='Force')
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Force (N)', color='b')
    ax1.tick_params(axis='y', labelcolor='b')

    l2 = ax1_twin.plot(t, coupling, 'r-', linewidth=2, label='Coupling')
    ax1_twin.set_ylabel('Coupling Strength', color='r')
    ax1_twin.tick_params(axis='y', labelcolor='r')

    ax1.set_title('Force and Coupling Dynamics')
    ax1.grid(True, alpha=0.3)

    # State space 3D trajectory
    ax2 = plt.subplot(2, 2, 2, projection='3d')
    if np.any(coords):
        # Color by time
        colors = plt.cm.viridis(np.linspace(0, 1, len(t)))
        ax2.scatter(coords[:, 0], coords[:, 1], coords[:, 2],
                   c=colors, s=10, alpha=0.6)
        ax2.plot(coords[:, 0], coords[:, 1], coords[:, 2],
                'k-', alpha=0.3, linewidth=0.5)

        # Mark start and end
        ax2.scatter([coords[0, 0]], [coords[0, 1]], [coords[0, 2]],
                   c='green', s=100, marker='o', label='Start')
        ax2.scatter([coords[-1, 0]], [coords[-1, 1]], [coords[-1, 2]],
                   c='red', s=100, marker='s', label='End')

        ax2.set_xlabel('Knowledge')
        ax2.set_ylabel('Time')
        ax2.set_zlabel('Entropy')
        ax2.set_title('3D State Space Trajectory')
        ax2.legend()

    # Activation vs Force phase plot
    ax3 = plt.subplot(2, 2, 3)
    activation = results['activation']
    ax3.plot(activation, force, 'b-', linewidth=1, alpha=0.7)
    ax3.scatter(activation[idx_peak_force], force[idx_peak_force],
               c='red', s=100, marker='*', zorder=5, label='Peak')
    ax3.set_xlabel('Activation')
    ax3.set_ylabel('Force (N)')
    ax3.set_title('Force-Activation Phase Space')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # Coupling vs Force
    ax4 = plt.subplot(2, 2, 4)
    valid_idx = coupling > 0
    if np.any(valid_idx):
        ax4.scatter(coupling[valid_idx], force[valid_idx],
                   c=t[valid_idx], cmap='viridis', s=10, alpha=0.6)
        ax4.set_xlabel('Coupling Strength')
        ax4.set_ylabel('Force (N)')
        ax4.set_title('Force vs Coupling')
        plt.colorbar(ax4.collections[0], ax=ax4, label='Time (s)')
        ax4.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('demo3_dynamic_coupling.png', dpi=150, bbox_inches='tight')
    print("\nPlot saved: demo3_dynamic_coupling.png")
    plt.show()

    return results


def demo_4_body_segments():
    """Demo 4: Oscillatory coupling in body segments during gait."""
    print("\n" + "="*60)
    print("DEMO 4: Body Segment Oscillatory Coupling")
    print("="*60)

    # Create lower limb model
    body_mass = 75  # kg
    height = 1.78  # m

    print(f"\nCreating lower limb model:")
    print(f"  Body mass: {body_mass} kg")
    print(f"  Height: {height} m")

    model = LowerLimbModel(body_mass, height)

    print(f"\nSegment properties:")
    print(f"  Thigh:  {model.thigh.length:.3f} m, {model.thigh.mass:.2f} kg, "
          f"{model.thigh.natural_frequency:.1f} Hz")
    print(f"  Shank:  {model.shank.length:.3f} m, {model.shank.mass:.2f} kg, "
          f"{model.shank.natural_frequency:.1f} Hz")
    print(f"  Foot:   {model.foot.length:.3f} m, {model.foot.mass:.2f} kg, "
          f"{model.foot.natural_frequency:.1f} Hz")

    # Simulate gait
    stride_freq = 1.6  # Hz (96 steps/min)
    print(f"\nSimulating gait at {stride_freq} Hz ({stride_freq*60:.0f} steps/min)...")

    results = model.simulate_gait_cycle(
        stride_frequency=stride_freq,
        t_span=(0, 2.0)
    )

    # Visualize
    fig = plt.figure(figsize=(14, 10))

    t = results['time']
    angles_deg = results['angles'] * 180 / np.pi
    velocities_deg = results['angular_velocities'] * 180 / np.pi
    energies = results['energies']

    joint_names = results['joint_names']
    colors = ['blue', 'red', 'green']

    # Joint angles
    ax1 = plt.subplot(3, 2, 1)
    for i, (name, color) in enumerate(zip(joint_names, colors)):
        ax1.plot(t, angles_deg[:, i], color=color, linewidth=2, label=name)
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Angle (deg)')
    ax1.set_title('Joint Angles During Gait')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Angular velocities
    ax2 = plt.subplot(3, 2, 2)
    for i, (name, color) in enumerate(zip(joint_names, colors)):
        ax2.plot(t, velocities_deg[:, i], color=color, linewidth=2, label=name)
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Angular Velocity (deg/s)')
    ax2.set_title('Joint Angular Velocities')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Phase plots
    for i, (name, color) in enumerate(zip(joint_names, colors)):
        ax = plt.subplot(3, 3, i+4)
        ax.plot(angles_deg[:, i], velocities_deg[:, i],
               color=color, linewidth=1, alpha=0.7)
        ax.scatter(angles_deg[0, i], velocities_deg[0, i],
                  c='green', s=50, marker='o', zorder=5)
        ax.scatter(angles_deg[-1, i], velocities_deg[-1, i],
                  c='red', s=50, marker='s', zorder=5)
        ax.set_xlabel('Angle (deg)')
        ax.set_ylabel('Velocity (deg/s)')
        ax.set_title(f'{name} Phase Space')
        ax.grid(True, alpha=0.3)

    # Oscillatory energies
    ax7 = plt.subplot(3, 3, 7)
    for i, (name, color) in enumerate(zip(joint_names, colors)):
        ax7.plot(t, energies[:, i], color=color, linewidth=2, label=name)
    ax7.set_xlabel('Time (s)')
    ax7.set_ylabel('Energy (J)')
    ax7.set_title('Oscillatory Energy per Segment')
    ax7.legend()
    ax7.grid(True, alpha=0.3)

    # Total energy
    ax8 = plt.subplot(3, 3, 8)
    total_energy = np.sum(energies, axis=1)
    ax8.plot(t, total_energy, 'k-', linewidth=2)
    ax8.set_xlabel('Time (s)')
    ax8.set_ylabel('Total Energy (J)')
    ax8.set_title('Total Oscillatory Energy')
    ax8.grid(True, alpha=0.3)

    # Coupling matrix
    ax9 = plt.subplot(3, 3, 9)
    coupling = results['coupling_matrix']
    im = ax9.imshow(coupling, cmap='hot', aspect='auto', interpolation='nearest')
    ax9.set_title('Segment Coupling Matrix')
    ax9.set_xticks(range(3))
    ax9.set_yticks(range(3))
    ax9.set_xticklabels(joint_names)
    ax9.set_yticklabels(joint_names)
    plt.colorbar(im, ax=ax9, label='Coupling')

    plt.tight_layout()
    plt.savefig('demo4_body_segments.png', dpi=150, bbox_inches='tight')
    print("\nPlot saved: demo4_body_segments.png")
    plt.show()

    # Compute coupling metrics
    print("\n--- Segment Coupling Analysis ---")
    for i, name_i in enumerate(joint_names):
        for j, name_j in enumerate(joint_names):
            if i < j:
                print(f"{name_i}-{name_j} coupling: {coupling[i, j]:.3f}")

    return results


def demo_5_performance_prediction():
    """Demo 5: Performance prediction from coupling dynamics."""
    print("\n" + "="*60)
    print("DEMO 5: Performance Prediction from Coupling")
    print("="*60)

    print("\nSimulating muscles with varying coupling strengths...")

    # Simulate with different "training" states (different coupling)
    conditions = {
        'Fatigued': 0.3,
        'Normal': 1.0,
        'Trained': 1.5,
    }

    results_dict = {}
    metrics_dict = {}

    for condition, coupling_factor in conditions.items():
        print(f"\n  {condition} (coupling × {coupling_factor})...")

        muscle = OscillatoryMuscleModel()

        # Modify coupling (simplified: scale parameters)
        muscle.P['t_act'] = 0.015 / coupling_factor
        muscle.P['t_deact'] = 0.050 / coupling_factor

        def excitation(t):
            return 1.0 if 0.5 <= t <= 2.0 else 0.01

        def lmt(t):
            return 0.31

        results = muscle.simulate_muscle_with_coupling(
            excitation, lmt,
            t_span=(0, 3.0),
            enable_coupling=True
        )

        metrics = muscle.compute_performance_metrics(results)

        results_dict[condition] = results
        metrics_dict[condition] = metrics

    # Display comparison
    print("\n--- Performance Metrics Comparison ---")
    metric_names = list(metrics_dict['Normal'].keys())

    print(f"\n{'Metric':<25s} | {'Fatigued':>12s} | {'Normal':>12s} | {'Trained':>12s}")
    print("-" * 70)

    for metric in metric_names:
        values = [metrics_dict[c][metric] for c in conditions.keys()]
        print(f"{metric:<25s} | {values[0]:12.4f} | {values[1]:12.4f} | {values[2]:12.4f}")

    # Visualize
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))

    colors_cond = {'Fatigued': 'orange', 'Normal': 'blue', 'Trained': 'green'}

    for i, (condition, results) in enumerate(results_dict.items()):
        color = colors_cond[condition]

        # Force
        axes[0, 0].plot(results['time'], results['muscle_force'],
                       color=color, linewidth=2, label=condition)

        # Activation
        axes[0, 1].plot(results['time'], results['activation'],
                       color=color, linewidth=2, label=condition)

        # Coupling
        axes[0, 2].plot(results['time'], results['coupling_strength'],
                       color=color, linewidth=2, label=condition)

    axes[0, 0].set_xlabel('Time (s)')
    axes[0, 0].set_ylabel('Force (N)')
    axes[0, 0].set_title('Muscle Force')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)

    axes[0, 1].set_xlabel('Time (s)')
    axes[0, 1].set_ylabel('Activation')
    axes[0, 1].set_title('Activation Dynamics')
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)

    axes[0, 2].set_xlabel('Time (s)')
    axes[0, 2].set_ylabel('Coupling Strength')
    axes[0, 2].set_title('Coupling Evolution')
    axes[0, 2].legend()
    axes[0, 2].grid(True, alpha=0.3)

    # Bar plots for metrics
    metrics_to_plot = ['peak_force', 'total_work', 'average_coupling']
    titles = ['Peak Force (N)', 'Total Work (J)', 'Avg Coupling']

    for i, (metric, title) in enumerate(zip(metrics_to_plot, titles)):
        ax = axes[1, i]
        values = [metrics_dict[c][metric] for c in conditions.keys()]
        bars = ax.bar(conditions.keys(), values,
                     color=[colors_cond[c] for c in conditions.keys()],
                     alpha=0.7, edgecolor='black')
        ax.set_ylabel(title)
        ax.set_title(title)
        ax.grid(True, alpha=0.3, axis='y')

        # Add value labels
        for bar, val in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{val:.2f}', ha='center', va='bottom')

    plt.tight_layout()
    plt.savefig('demo5_performance_prediction.png', dpi=150, bbox_inches='tight')
    print("\nPlot saved: demo5_performance_prediction.png")
    plt.show()

    return results_dict, metrics_dict


def main():
    """Run all demonstrations."""
    print("\n" + "="*60)
    print("OSCILLATORY MUSCLE MODELING - COMPREHENSIVE DEMO")
    print("="*60)
    print("\nThis demo showcases the multi-scale oscillatory coupling framework")
    print("applied to muscle mechanics and body segment coordination.")
    print("\nPress Ctrl+C to exit at any time.\n")

    try:
        # Run demos
        print("\n[1/5] Running Demo 1: Classical vs Oscillatory Comparison...")
        demo_1_basic_comparison()

        print("\n[2/5] Running Demo 2: Frequency Decomposition...")
        demo_2_frequency_decomposition()

        print("\n[3/5] Running Demo 3: Dynamic Coupling...")
        demo_3_dynamic_coupling()

        print("\n[4/5] Running Demo 4: Body Segments...")
        demo_4_body_segments()

        print("\n[5/5] Running Demo 5: Performance Prediction...")
        demo_5_performance_prediction()

        print("\n" + "="*60)
        print("ALL DEMOS COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("\nGenerated plots:")
        print("  - demo1_muscle_comparison.png")
        print("  - demo2_frequency_decomposition.png")
        print("  - demo3_dynamic_coupling.png")
        print("  - demo4_body_segments.png")
        print("  - demo5_performance_prediction.png")
        print("\nThese plots demonstrate the key features of the oscillatory")
        print("coupling framework for biomechanical modeling.")

    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
    except Exception as e:
        print(f"\n\nError occurred: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
