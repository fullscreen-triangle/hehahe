#!/usr/bin/env python3
"""
Example Usage of Sensation Mechanics Validation Framework

Demonstrates key features and how to use the package for custom analysis.
"""

import numpy as np
import json
from pathlib import Path

from charge_dynamics import ClosedCircuit, create_circuit_config, validate_exponential_decay
from sensation_mechanics import SensationCategorizer, SensationQuality, MultimodalSensation
from receptor_models import ReceptorType, ReceptorPopulation, ReceptorComparison
from temperature_effects import TemperatureModel, ThermalSensationAnalysis
from utils import save_json, exponential_fit, compute_statistics


def example_1_basic_circuit():
    """Example 1: Simulate a basic closed circuit."""
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Closed Circuit Simulation")
    print("="*70)

    # Create circuit with 3 compartments
    config = create_circuit_config(n_compartments=3, Q_total=1.0)
    circuit = ClosedCircuit(config)

    # Create perturbation: 60% charge in first compartment, rest distributed
    Q0 = np.array([0.6, 0.3, 0.1])

    # Simulate response with tau = 0.3 seconds
    result = circuit.simulate_perturbation(Q0, tau=0.3, t_max=3.0, dt=0.01)

    print(f"\nCircuit Configuration:")
    print(f"  Compartments: {config.n_compartments}")
    print(f"  Total Charge: {config.Q_total}")
    print(f"  Initial Perturbation: {Q0}")
    print(f"\nSimulation Results:")
    print(f"  Time span: 0 to {result['time'][-1]:.2f} seconds")
    print(f"  Peak sensation rate: {np.max(result['sensation_rate']):.4f}")
    print(f"  Relaxation timescale: {result['tau']} seconds")

    # Validate exponential decay
    validation = validate_exponential_decay(
        result['sensation_rate'],
        result['time'],
        result['tau']
    )
    print(f"\nExponential Decay Validation:")
    print(f"  R² = {validation['r_squared']:.4f}")
    print(f"  Max relative error: {validation['max_relative_error']:.4f}")

    return result


def example_2_sensation_categorization():
    """Example 2: Categorize sensation based on time constant."""
    print("\n" + "="*70)
    print("EXAMPLE 2: Sensation Categorization (Pain vs Pleasure)")
    print("="*70)

    categorizer = SensationCategorizer(
        tau_critical=0.05,  # 50 milliseconds
        tau_width=0.02
    )

    # Test different time constants
    test_taus = np.array([0.01, 0.03, 0.05, 0.10, 0.50])
    print(f"\nCategorizing sensations at different time constants:")
    print(f"Critical timescale: {categorizer.tau_critical} seconds\n")

    results = []
    for tau in test_taus:
        category = categorizer.categorize(tau)
        results.append({
            'tau_seconds': float(tau),
            'tau_milliseconds': float(tau * 1000),
            'category': category.value
        })
        print(f"  τ = {tau*1000:6.1f} ms → {category.value.upper()}")

    return results


def example_3_receptor_diversity():
    """Example 3: Compare monolithic vs diverse receptor populations."""
    print("\n" + "="*70)
    print("EXAMPLE 3: Receptor Diversity Advantage")
    print("="*70)

    tau_min, tau_max = 0.01, 1.0
    total_density = 100.0
    metabolic_cost = 50.0

    # Create two populations with same resources
    pop_mono = ReceptorComparison.monolithic_population(
        tau=np.sqrt(tau_min * tau_max),  # Geometric mean
        total_density=total_density,
        metabolic_cost=metabolic_cost
    )

    pop_diverse = ReceptorComparison.logarithmic_diverse_population(
        tau_min=tau_min,
        tau_max=tau_max,
        n_types=8,
        total_density=total_density,
        metabolic_cost=metabolic_cost
    )

    print(f"\nPopulation Configurations:")
    print(f"  Time constant range: {tau_min} to {tau_max} seconds")
    print(f"  Total density: {total_density}")
    print(f"  Total cost: {metabolic_cost}")

    print(f"\nMonolithic Population:")
    print(f"  Receptor types: 1")
    print(f"  Time constant: {pop_mono.tau_values()[0]:.4f} s")

    print(f"\nDiverse Population:")
    print(f"  Receptor types: {pop_diverse.n_types}")
    print(f"  Time constants (logarithmic spacing):")
    for i, tau in enumerate(pop_diverse.tau_values()):
        print(f"    Type {i+1}: {tau:.4f} s")

    # Test stimulus coverage
    stimulus_taus = np.logspace(np.log10(tau_min * 0.5), np.log10(tau_max * 2), 100)
    comparison = ReceptorComparison.compare_populations(
        pop_mono, pop_diverse, stimulus_taus
    )

    print(f"\nCoverage Analysis:")
    print(f"  Stimulus timescale range: {stimulus_taus[0]:.4f} to {stimulus_taus[-1]:.4f} s")
    print(f"  Monolithic coverage: {comparison['monolithic']['coverage_fraction']*100:.1f}%")
    print(f"  Diverse coverage: {comparison['diverse']['coverage_fraction']*100:.1f}%")
    print(f"  Improvement: {comparison['improvement']['coverage_gain']*100:.1f}%")

    return comparison


def example_4_temperature_effects():
    """Example 4: Temperature-dependent sensation dynamics."""
    print("\n" + "="*70)
    print("EXAMPLE 4: Temperature Effects on Sensation")
    print("="*70)

    model = TemperatureModel(
        tau_ref=0.1,
        E_a=12000.0,  # J/mol
        T_ref=298.15  # 25°C
    )

    print(f"\nTemperature Model Parameters:")
    print(f"  Reference τ at 25°C: {model.tau_ref} s")
    print(f"  Activation energy: {model.E_a} J/mol")

    # Compute timescales across temperature range
    temperatures_C = np.array([10, 20, 25, 30, 37, 40])
    temperatures_K = temperatures_C + 273.15

    print(f"\nTimescale vs Temperature:")
    for T_C, T_K in zip(temperatures_C, temperatures_K):
        tau = model.timescale_at_temperature(T_K)
        print(f"  {T_C:3d}°C ({T_K:6.2f}K): τ = {tau:.4f} s")

    # Q10 coefficient
    q10 = model.temperature_coefficient_Q10(
        T_low=283.15,  # 10°C
        T_high=293.15  # 20°C
    )
    print(f"\nQ10 Temperature Coefficient (10°C → 20°C): {q10:.2f}")
    print("  (Interpretation: timescale changes by factor of {:.2f} per 10°C)".format(q10))

    # Thermal sensation analysis
    analyzer = ThermalSensationAnalysis()
    warm_cold = analyzer.warm_cold_sensation_crossover()
    pain_threshold = analyzer.thermal_pain_threshold()

    print(f"\nThermal Sensation Characteristics:")
    print(f"  Warm/cold sensation crossover: {warm_cold['crossover_temperature_C']:.1f}°C")
    print(f"  Pain threshold (TRPV1): {pain_threshold['pain_threshold_C']:.1f}°C")

    return {
        'temperature_scaling': {
            'temperatures_C': temperatures_C.tolist(),
            'timescales_s': [model.timescale_at_temperature(T) for T in temperatures_K]
        },
        'warm_cold_crossover': warm_cold,
        'pain_threshold': pain_threshold
    }


def example_5_multimodal_integration():
    """Example 5: Multi-modal sensation integration."""
    print("\n" + "="*70)
    print("EXAMPLE 5: Multi-Modal Sensation Integration")
    print("="*70)

    integrator = MultimodalSensation(freq_match_threshold=0.1)

    # Test frequency matching between different modalities
    modalities = {
        'Pain (fast nociceptor)': 0.02,
        'Temperature (warm)': 0.1,
        'Pressure (mechanoreceptor)': 0.05,
        'Pleasure (hedonic)': 0.5
    }

    print(f"\nModality Time Constants:")
    for name, tau in modalities.items():
        print(f"  {name:.<40} τ = {tau:.3f} s")

    print(f"\nFrequency Matching Matrix:")
    print(f"{'Modality':.<30} {'vs Pain':>12} {'vs Temp':>12} {'vs Press':>12} {'vs Pleas':>12}")
    print("-" * 80)

    mods_list = list(modalities.items())
    for i, (name_i, tau_i) in enumerate(mods_list):
        row = f"{name_i:.<30}"
        for j, (name_j, tau_j) in enumerate(mods_list):
            if i == j:
                row += f"{'─':>12}"
            else:
                score = integrator.frequency_matching_score(tau_i, tau_j)
                matched = "✓ MATCH" if score < integrator.freq_match_threshold else "✗ no"
                row += f"{matched:>12}"
        print(row)

    print(f"\nInterpretation:")
    print(f"  Matched modalities can integrate and interfere")
    print(f"  Unmatched modalities remain perceptually distinct")
    print(f"  Pain/temperature are frequency-matched → hard to dissociate")
    print(f"  Pain/pleasure are mismatched → feel different despite same mechanism")

    return {
        'modalities': modalities,
        'frequency_match_threshold': integrator.freq_match_threshold
    }


def example_6_sensation_quality():
    """Example 6: Analyze sensation quality from spatial patterns."""
    print("\n" + "="*70)
    print("EXAMPLE 6: Sensation Quality Analysis")
    print("="*70)

    compartment_names = ['Dermis', 'Epidermis', 'Subcutaneous']

    # Different stimuli produce different spatial patterns
    patterns = {
        'Sharp_pain': np.array([0.9, 0.05, 0.05]),
        'Pressure': np.array([0.3, 0.4, 0.3]),
        'Heat': np.array([0.1, 0.8, 0.1])
    }

    print(f"\nSpatial Perturbation Patterns:")
    for stimulus_type, pattern in patterns.items():
        spatial = SensationQuality.spatial_pattern(pattern, compartment_names)
        print(f"\n  {stimulus_type}:")
        print(f"    Dominant compartment: {spatial['dominant_compartment']}")
        print(f"    Perturbation magnitude: {spatial['perturbation_magnitude']:.3f}")
        print(f"    Spatial entropy: {spatial['spatial_entropy']:.3f}")

    # Different temporal patterns
    temporal_profiles = {
        'Fast_pain': {
            'taus': [0.02, 0.05],
            'amplitudes': [0.8, 0.2]
        },
        'Slow_pleasure': {
            'taus': [0.5, 1.0],
            'amplitudes': [0.6, 0.4]
        }
    }

    print(f"\n\nTemporal Response Patterns:")
    for response_type, profile in temporal_profiles.items():
        temporal = SensationQuality.temporal_pattern(profile['taus'], profile['amplitudes'])
        print(f"\n  {response_type}:")
        print(f"    Timescale range: {temporal['tau_range'][0]:.3f} to {temporal['tau_range'][1]:.3f} s")
        print(f"    Effective timescale: {temporal['effective_timescale']:.3f} s")
        print(f"    Timescale diversity: {temporal['timescale_diversity']:.3f}")

    return {
        'spatial_patterns': {k: SensationQuality.spatial_pattern(v, compartment_names)
                            for k, v in patterns.items()},
        'temporal_patterns': {k: SensationQuality.temporal_pattern(v['taus'], v['amplitudes'])
                             for k, v in temporal_profiles.items()}
    }


def main():
    """Run all examples."""
    print("\n" + "="*70)
    print("SENSATION MECHANICS VALIDATION FRAMEWORK - USAGE EXAMPLES")
    print("="*70)

    # Run examples
    ex1 = example_1_basic_circuit()
    ex2 = example_2_sensation_categorization()
    ex3 = example_3_receptor_diversity()
    ex4 = example_4_temperature_effects()
    ex5 = example_5_multimodal_integration()
    ex6 = example_6_sensation_quality()

    # Combine all results
    all_results = {
        'example_1_basic_circuit': {
            'peak_sensation': float(np.max(ex1['sensation_rate'])),
            'total_time': float(ex1['time'][-1])
        },
        'example_2_categorization': ex2,
        'example_3_receptor_diversity': ex3,
        'example_4_temperature': ex4,
        'example_5_multimodal': ex5,
        'example_6_sensation_quality': ex6
    }

    # Save results
    output_dir = Path('./example_results')
    output_file = save_json(all_results, output_dir / 'example_results.json')
    print(f"\n\nAll example results saved to: {output_file}")

    print("\n" + "="*70)
    print("Examples completed successfully!")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
