"""
Comprehensive Validation Test Suite for Sensation Mechanics Framework

Executes all key predictions and saves results to JSON format.
"""

import numpy as np
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from charge_dynamics import (
    CircuitConfig, ClosedCircuit, MultiTimescaleCircuit,
    validate_charge_conservation, validate_exponential_decay,
    create_circuit_config
)

from sensation_mechanics import (
    SensationCategorizer, SensationQuality, MultimodalSensation,
    validate_sensation_conservation, validate_pain_pleasure_transition
)

from receptor_models import (
    ReceptorType, ReceptorPopulation, ReceptorComparison, ReceptorAdaptation
)

from temperature_effects import (
    TemperatureModel, ThermalSensationAnalysis, validate_arrhenius_scaling
)


class ValidationSuite:
    """
    Comprehensive test suite for sensation mechanics framework.

    Tests all major theorems and predictions.
    """

    def __init__(self, output_dir: str = './validation_results'):
        """
        Initialize validation suite.

        Args:
            output_dir: Directory for saving results
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results = {}
        self.timestamp = datetime.now().isoformat()

    def test_charge_conservation(self) -> Dict:
        """Test charge conservation in closed circuits."""
        print("Testing charge conservation...")

        config = create_circuit_config(n_compartments=5, Q_total=1.0)
        circuit = ClosedCircuit(config)

        # Random initial perturbation
        Q0 = np.random.randn(config.n_compartments)
        Q0 = Q0 / np.sum(Q0) * config.Q_total  # Normalize to conserved total

        # Simulate
        result = circuit.simulate_perturbation(Q0, tau=0.5, t_max=5.0)

        conservation_check = validate_charge_conservation(
            result['Q'], config.Q_total
        )

        return {
            'test_name': 'Charge Conservation',
            'passes': conservation_check,
            'n_compartments': config.n_compartments,
            'Q_total': float(config.Q_total),
            'max_deviation': float(np.max(np.abs(
                np.sum(result['Q'], axis=0) - config.Q_total
            )))
        }

    def test_exponential_decay(self) -> Dict:
        """Test exponential decay of sensation rate."""
        print("Testing exponential decay kinetics...")

        config = create_circuit_config(n_compartments=3)
        circuit = ClosedCircuit(config)

        Q0 = np.random.randn(config.n_compartments)
        Q0 = Q0 / np.sum(Q0) * config.Q_total

        tau = 0.3
        result = circuit.simulate_perturbation(Q0, tau=tau, t_max=5.0)

        validation = validate_exponential_decay(
            result['sensation_rate'],
            result['time'],
            tau,
            rtol=0.15
        )

        return {
            'test_name': 'Exponential Decay',
            'passes': validation['passes_validation'],
            'tau_nominal': float(tau),
            'r_squared': validation['r_squared'],
            'max_relative_error': validation['max_relative_error'],
            'mean_relative_error': validation['mean_relative_error']
        }

    def test_sensation_integral(self) -> Dict:
        """Test that total sensation equals charge perturbation."""
        print("Testing sensation integral conservation...")

        config = create_circuit_config(n_compartments=3)
        circuit = ClosedCircuit(config)

        Q0 = np.random.randn(config.n_compartments)
        Q0 = Q0 / np.sum(Q0) * config.Q_total

        tau = 0.4
        dt = 0.01
        result = circuit.simulate_perturbation(Q0, tau=tau, t_max=8.0, dt=dt)

        validation = validate_sensation_conservation(
            result['Delta_Q'],
            dt,
            result['sensation_rate'],
            rtol=0.1
        )

        return {
            'test_name': 'Sensation Integral',
            'passes': validation['passes_validation'],
            'predicted_integral': validation['predicted'],
            'measured_integral': validation['measured'],
            'relative_error': validation['relative_error']
        }

    def test_pain_pleasure_categorization(self) -> Dict:
        """Test pain/pleasure categorization by time constant."""
        print("Testing pain/pleasure categorization...")

        categorizer = SensationCategorizer(
            tau_critical=0.05,
            tau_width=0.02
        )

        # Test range of timescales
        taus = np.logspace(-3, 1, 50)  # 0.001 to 10 seconds

        validation = validate_pain_pleasure_transition(categorizer, taus)

        return {
            'test_name': 'Pain/Pleasure Categorization',
            'tau_critical': float(categorizer.tau_critical),
            'n_timescales_tested': validation['n_timescales_tested'],
            'category_counts': validation['category_counts'],
            'transition_sharpness': validation['transition_sharpness'],
            'passes': validation['category_counts']['pain'] > 0 and
                      validation['category_counts']['pleasure'] > 0
        }

    def test_receptor_diversity_advantage(self) -> Dict:
        """Test that diverse receptor populations outperform monolithic."""
        print("Testing receptor diversity advantage...")

        tau_min, tau_max = 0.01, 1.0
        total_density = 100.0
        metabolic_cost = 50.0

        # Monolithic
        pop_mono = ReceptorComparison.monolithic_population(
            tau=np.sqrt(tau_min * tau_max),  # Geometric mean
            total_density=total_density,
            metabolic_cost=metabolic_cost
        )

        # Diverse (logarithmic spacing)
        pop_div = ReceptorComparison.logarithmic_diverse_population(
            tau_min=tau_min,
            tau_max=tau_max,
            n_types=8,
            total_density=total_density,
            metabolic_cost=metabolic_cost
        )

        # Test stimulus coverage
        stimulus_taus = np.logspace(np.log10(tau_min * 0.5), np.log10(tau_max * 2), 100)

        comparison = ReceptorComparison.compare_populations(
            pop_mono, pop_div, stimulus_taus
        )

        return {
            'test_name': 'Receptor Diversity Advantage',
            'passes': comparison['improvement']['diversity_superior'],
            'monolithic_coverage': comparison['monolithic']['coverage_fraction'],
            'diverse_coverage': comparison['diverse']['coverage_fraction'],
            'coverage_improvement': comparison['improvement']['coverage_gain'],
            'efficiency_improvement': comparison['improvement']['efficiency_gain'],
            'receptor_types_diverse': comparison['diverse']['n_types']
        }

    def test_logarithmic_spacing(self) -> Dict:
        """Test optimal logarithmic spacing of receptors."""
        print("Testing logarithmic spacing optimality...")

        pop = ReceptorComparison.logarithmic_diverse_population(
            tau_min=0.01,
            tau_max=1.0,
            n_types=8,
            total_density=100.0,
            metabolic_cost=50.0
        )

        spacing = pop.logarithmic_spacing_score()

        return {
            'test_name': 'Logarithmic Spacing',
            'n_receptor_types': spacing['n_receptor_types'],
            'mean_log_error': spacing['mean_log_error'],
            'max_log_error': spacing['max_log_error'],
            'optimal_ratio': spacing['optimal_ratio'],
            'passes': spacing['mean_log_error'] < 0.1
        }

    def test_frequency_matching(self) -> Dict:
        """Test frequency matching for multi-circuit coupling."""
        print("Testing frequency matching...")

        integrator = MultimodalSensation(freq_match_threshold=0.1)

        # Create two test cases
        test_cases = [
            {'tau1': 0.05, 'tau2': 0.06, 'matched': True},   # Close match
            {'tau1': 0.05, 'tau2': 0.5, 'matched': False},   # No match
        ]

        results = []
        for case in test_cases:
            matched = integrator.is_frequency_matched(case['tau1'], case['tau2'])
            score = integrator.frequency_matching_score(case['tau1'], case['tau2'])
            results.append({
                'tau1': case['tau1'],
                'tau2': case['tau2'],
                'expected_match': case['matched'],
                'predicted_match': matched,
                'correct': matched == case['matched'],
                'matching_score': float(score)
            })

        all_correct = np.all([r['correct'] for r in results])

        return {
            'test_name': 'Frequency Matching',
            'passes': all_correct,
            'test_cases': results
        }

    def test_arrhenius_scaling(self) -> Dict:
        """Test Arrhenius scaling of timescales with temperature."""
        print("Testing Arrhenius temperature scaling...")

        model = TemperatureModel(tau_ref=0.1, E_a=12000.0, T_ref=298.15)

        # Generate synthetic data
        temperatures = np.linspace(278.15, 318.15, 30)  # 5°C to 45°C
        taus = np.array([model.timescale_at_temperature(T) for T in temperatures])

        validation = validate_arrhenius_scaling(temperatures, taus, E_a_expected=12000.0)

        return {
            'test_name': 'Arrhenius Temperature Scaling',
            'passes': validation['passes_validation'],
            'temperature_range_C': [float(temperatures[0] - 273.15),
                                   float(temperatures[-1] - 273.15)],
            'E_a_fitted': validation['E_a_fitted'],
            'E_a_expected': validation['E_a_expected'],
            'E_a_error_percent': float(validation['E_a_error_fraction'] * 100),
            'r_squared': validation['r_squared']
        }

    def test_thermal_sensation(self) -> Dict:
        """Test thermal sensation characteristics."""
        print("Testing thermal sensation...")

        analyzer = ThermalSensationAnalysis()

        warm_cold = analyzer.warm_cold_sensation_crossover()
        pain_threshold = analyzer.thermal_pain_threshold()
        receptor_compare = analyzer.compare_receptor_temperature_sensitivity()

        return {
            'test_name': 'Thermal Sensation',
            'warm_cold_crossover_C': float(warm_cold['crossover_temperature_C']),
            'pain_threshold_C': float(pain_threshold['pain_threshold_C']),
            'receptor_sensitivities': receptor_compare
        }

    def test_multi_timescale_dynamics(self) -> Dict:
        """Test circuits with multiple relaxation timescales."""
        print("Testing multi-timescale dynamics...")

        config = create_circuit_config(n_compartments=3)
        circuit = MultiTimescaleCircuit(config)

        Q0 = np.random.randn(config.n_compartments)
        Q0 = Q0 / np.sum(Q0) * config.Q_total

        taus = [0.1, 0.5, 2.0]
        amplitudes = [0.5, 0.3, 0.2]

        t = np.arange(0, 10, 0.01)
        Q = circuit.multi_exponential_response(t, Q0, taus, amplitudes)

        tau_eff = circuit.dominant_timescale(taus, amplitudes)

        return {
            'test_name': 'Multi-Timescale Dynamics',
            'n_timescales': len(taus),
            'timescales': taus,
            'effective_timescale': float(tau_eff),
            'amplitude_weighted': float(
                np.sum(np.array(np.abs(amplitudes)) * np.array(taus)) /
                np.sum(np.abs(amplitudes))
            ),
            'passes': np.isclose(tau_eff,
                np.sum(np.array(np.abs(amplitudes)) * np.array(taus)) /
                np.sum(np.abs(amplitudes)))
        }

    def test_receptor_adaptation(self) -> Dict:
        """Test replacement-mediated receptor learning."""
        print("Testing receptor adaptation...")

        pop = ReceptorComparison.logarithmic_diverse_population(
            tau_min=0.01,
            tau_max=1.0,
            n_types=6,
            total_density=100.0,
            metabolic_cost=50.0
        )

        adapter = ReceptorAdaptation(pop)

        # Stimulus with strong peak at specific timescale
        stimulus_taus = np.logspace(-2, 0, 100)
        stimulus_weights = np.exp(-((np.log10(stimulus_taus) - (-0.5))**2) / 0.1)
        stimulus_weights /= np.sum(stimulus_weights)

        # Run adaptation steps
        adaptation_history = adapter.multiple_adaptation_steps(
            stimulus_taus, stimulus_weights, n_steps=5
        )

        return {
            'test_name': 'Receptor Adaptation',
            'n_adaptation_steps': len(adaptation_history),
            'initial_spacing': pop.logarithmic_spacing_score(),
            'final_spacing': adapter.current_population.logarithmic_spacing_score(),
            'adaptation_history': adaptation_history
        }

    def run_all_tests(self) -> Dict:
        """Execute all validation tests."""
        print("\n" + "="*60)
        print("SENSATION MECHANICS FRAMEWORK VALIDATION SUITE")
        print("="*60 + "\n")

        tests = [
            self.test_charge_conservation,
            self.test_exponential_decay,
            self.test_sensation_integral,
            self.test_pain_pleasure_categorization,
            self.test_receptor_diversity_advantage,
            self.test_logarithmic_spacing,
            self.test_frequency_matching,
            self.test_arrhenius_scaling,
            self.test_thermal_sensation,
            self.test_multi_timescale_dynamics,
            self.test_receptor_adaptation,
        ]

        results = []
        for test_func in tests:
            try:
                result = test_func()
                results.append(result)
                status = "[PASS]" if result.get('passes', True) else "[FAIL]"
                print(f"{status} - {result['test_name']}")
            except Exception as e:
                print(f"[ERROR] - {test_func.__name__}: {str(e)}")
                results.append({
                    'test_name': test_func.__name__,
                    'error': str(e)
                })

        return {
            'timestamp': self.timestamp,
            'total_tests': len(results),
            'tests_passed': sum(1 for r in results if r.get('passes', False)),
            'tests': results
        }

    def save_results(self, results: Dict, filename: str = 'validation_results.json'):
        """
        Save validation results to JSON.

        Args:
            results: Results dictionary
            filename: Output filename
        """
        output_path = self.output_dir / filename

        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        print(f"\nResults saved to: {output_path}")
        return output_path


def main():
    """Execute validation suite."""
    suite = ValidationSuite(output_dir='./validation_results')
    results = suite.run_all_tests()

    # Print summary
    print("\n" + "="*60)
    print(f"SUMMARY: {results['tests_passed']}/{results['total_tests']} tests passed")
    print("="*60 + "\n")

    # Save results
    suite.save_results(results)

    return results


if __name__ == '__main__':
    main()
