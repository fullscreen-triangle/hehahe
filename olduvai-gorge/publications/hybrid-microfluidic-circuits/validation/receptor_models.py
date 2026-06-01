"""
Receptor Models and Diversity

Validates the sufficiency principle and optimal receptor distributions.

Theorem: Diversity Maximizes Behavioral Responsiveness
A system with heterogeneous time constants can detect broader range of stimuli
than monolithic system with same metabolic budget.
"""

import numpy as np
from typing import List, Dict, Tuple
from dataclasses import dataclass
import json


@dataclass
class ReceptorType:
    """Characterization of a receptor type."""
    name: str
    tau: float  # Time constant
    activation_threshold: float  # Minimum stimulus for activation
    conduction_velocity: float  # Speed of signal propagation
    spontaneous_rate: float  # Baseline firing rate
    density: float  # Number per unit area (normalized)
    metabolic_cost: float  # Energy cost per receptor


class ReceptorPopulation:
    """
    Population of receptors with heterogeneous time constants.

    Validates Theorem: Logarithmic Spacing Optimality
    For M receptor types spanning τ_min to τ_max, optimal spacing is:
    τ_k = τ_min * r^k, where r = (τ_max/τ_min)^(1/M)
    """

    def __init__(self, receptor_types: List[ReceptorType]):
        """
        Initialize receptor population.

        Args:
            receptor_types: List of ReceptorType objects
        """
        self.receptor_types = receptor_types
        self.n_types = len(receptor_types)

    def tau_values(self) -> np.ndarray:
        """Get array of time constants."""
        return np.array([r.tau for r in self.receptor_types])

    def densities(self) -> np.ndarray:
        """Get array of receptor densities."""
        return np.array([r.density for r in self.receptor_types])

    def total_density(self) -> float:
        """Total receptor density (sum across types)."""
        return float(np.sum(self.densities()))

    def metabolic_cost(self) -> float:
        """Total metabolic cost."""
        costs = np.array([r.metabolic_cost for r in self.receptor_types])
        densities = self.densities()
        return float(np.sum(costs * densities))

    def stimulus_coverage(self, stimulus_timescales: np.ndarray,
                         frequency_match_threshold: float = 0.15) -> Dict:
        """
        Assess what stimulus timescales the population can detect.

        A stimulus with timescale τ_stim is detected if any receptor type
        has |τ_receptor - τ_stim| / (τ_receptor + τ_stim) < threshold

        Args:
            stimulus_timescales: Array of stimulus time constants
            frequency_match_threshold: Matching tolerance

        Returns:
            Coverage analysis
        """
        coverage = np.zeros(len(stimulus_timescales), dtype=bool)
        closest_receptor = np.zeros(len(stimulus_timescales))

        for i, tau_stim in enumerate(stimulus_timescales):
            # Find closest receptor type
            for tau_rec in self.tau_values():
                matching_score = abs(tau_rec - tau_stim) / (tau_rec + tau_stim)
                if matching_score < frequency_match_threshold:
                    coverage[i] = True
                    closest_receptor[i] = tau_rec
                    break

        coverage_fraction = np.sum(coverage) / len(stimulus_timescales)
        detectable_range = [
            stimulus_timescales[i] for i in range(len(stimulus_timescales))
            if coverage[i]
        ]

        return {
            'total_stimuli_tested': int(len(stimulus_timescales)),
            'stimuli_detected': int(np.sum(coverage)),
            'coverage_fraction': float(coverage_fraction),
            'detectable_range': detectable_range,
            'gaps_in_coverage': self._find_coverage_gaps(coverage, stimulus_timescales)
        }

    def _find_coverage_gaps(self, coverage: np.ndarray,
                           stimulus_timescales: np.ndarray) -> List[Tuple]:
        """Identify gaps in stimulus coverage."""
        gaps = []
        in_gap = False
        gap_start = None

        for i, detected in enumerate(coverage):
            if not detected and not in_gap:
                gap_start = stimulus_timescales[i]
                in_gap = True
            elif detected and in_gap:
                gap_end = stimulus_timescales[i - 1]
                gaps.append((float(gap_start), float(gap_end)))
                in_gap = False

        if in_gap:
            gaps.append((float(gap_start), float(stimulus_timescales[-1])))

        return gaps

    def logarithmic_spacing_score(self) -> Dict:
        """
        Compute how well the receptor population matches logarithmic spacing.

        Optimal: τ_k = τ_min * r^k where r = (τ_max / τ_min)^(1/(M-1))

        Returns:
            Spacing analysis
        """
        taus = np.sort(self.tau_values())
        M = len(taus)

        if M < 2:
            return {'error': 'Need at least 2 receptor types'}

        tau_min, tau_max = taus[0], taus[-1]
        r_optimal = (tau_max / tau_min) ** (1.0 / (M - 1))

        # Expected logarithmic spacing
        tau_expected = tau_min * r_optimal ** np.arange(M)

        # Compute error
        log_taus = np.log10(taus)
        log_expected = np.log10(tau_expected)
        log_error = log_taus - log_expected

        return {
            'n_receptor_types': int(M),
            'tau_range': [float(tau_min), float(tau_max)],
            'optimal_ratio': float(r_optimal),
            'actual_taus': taus.tolist(),
            'expected_taus': tau_expected.tolist(),
            'log_error': log_error.tolist(),
            'mean_log_error': float(np.mean(np.abs(log_error))),
            'max_log_error': float(np.max(np.abs(log_error)))
        }

    def efficiency_score(self, stimulus_coverage: float,
                        normalized_cost: float) -> float:
        """
        Score receptor population on efficiency: coverage per unit cost.

        efficiency = coverage / cost

        Args:
            stimulus_coverage: Fraction of stimuli detected
            normalized_cost: Metabolic cost (normalized to [0, 1])

        Returns:
            Efficiency score
        """
        if normalized_cost < 1e-10:
            return 0.0
        return stimulus_coverage / normalized_cost


class ReceptorComparison:
    """
    Compare monolithic vs diverse receptor populations.

    Validates Theorem: Diversity Maximizes Behavioral Responsiveness
    """

    @staticmethod
    def monolithic_population(tau: float, total_density: float,
                             metabolic_cost: float) -> ReceptorPopulation:
        """
        Create monolithic population (single receptor type).

        Args:
            tau: Single time constant
            total_density: Total receptor density
            metabolic_cost: Total metabolic cost

        Returns:
            ReceptorPopulation with single type
        """
        receptor = ReceptorType(
            name="Monolithic",
            tau=tau,
            activation_threshold=0.1,
            conduction_velocity=1.0,
            spontaneous_rate=0.01,
            density=total_density,
            metabolic_cost=metabolic_cost
        )
        return ReceptorPopulation([receptor])

    @staticmethod
    def logarithmic_diverse_population(tau_min: float, tau_max: float,
                                       n_types: int, total_density: float,
                                       metabolic_cost: float) -> ReceptorPopulation:
        """
        Create diverse population with logarithmic spacing.

        Args:
            tau_min, tau_max: Range of time constants
            n_types: Number of receptor types
            total_density: Total density distributed across types
            metabolic_cost: Total cost distributed across types

        Returns:
            ReceptorPopulation with logarithmic spacing
        """
        r = (tau_max / tau_min) ** (1.0 / (n_types - 1))
        taus = tau_min * r ** np.arange(n_types)

        # Distribute density and cost equally
        density_per_type = total_density / n_types
        cost_per_type = metabolic_cost / n_types

        receptors = []
        for i, tau in enumerate(taus):
            # Conduction velocity increases with tau (slow sensations are processed quickly)
            conduction_velocity = 0.5 + 0.5 * (tau - tau_min) / (tau_max - tau_min)

            receptors.append(
                ReceptorType(
                    name=f"Type_{i+1}",
                    tau=float(tau),
                    activation_threshold=0.1,
                    conduction_velocity=float(conduction_velocity),
                    spontaneous_rate=0.01,
                    density=density_per_type,
                    metabolic_cost=cost_per_type
                )
            )

        return ReceptorPopulation(receptors)

    @staticmethod
    def compare_populations(pop_monolithic: ReceptorPopulation,
                           pop_diverse: ReceptorPopulation,
                           stimulus_timescales: np.ndarray) -> Dict:
        """
        Compare monolithic vs diverse populations.

        Args:
            pop_monolithic: Monolithic population
            pop_diverse: Diverse population
            stimulus_timescales: Array of stimulus timescales to test

        Returns:
            Comparison results
        """
        coverage_mono = pop_monolithic.stimulus_coverage(stimulus_timescales)
        coverage_div = pop_diverse.stimulus_coverage(stimulus_timescales)

        cost_mono = pop_monolithic.metabolic_cost()
        cost_div = pop_diverse.metabolic_cost()

        efficiency_mono = pop_monolithic.efficiency_score(
            coverage_mono['coverage_fraction'],
            cost_mono / (cost_mono + cost_div)
        )
        efficiency_div = pop_diverse.efficiency_score(
            coverage_div['coverage_fraction'],
            cost_div / (cost_mono + cost_div)
        )

        return {
            'monolithic': {
                'n_types': int(pop_monolithic.n_types),
                'tau_values': pop_monolithic.tau_values().tolist(),
                'coverage_fraction': coverage_mono['coverage_fraction'],
                'total_metabolic_cost': float(cost_mono),
                'efficiency_score': float(efficiency_mono),
                'detectable_range': coverage_mono['detectable_range']
            },
            'diverse': {
                'n_types': int(pop_diverse.n_types),
                'tau_values': pop_diverse.tau_values().tolist(),
                'coverage_fraction': coverage_div['coverage_fraction'],
                'total_metabolic_cost': float(cost_div),
                'efficiency_score': float(efficiency_div),
                'detectable_range': coverage_div['detectable_range']
            },
            'improvement': {
                'coverage_gain': float(
                    (coverage_div['coverage_fraction'] - coverage_mono['coverage_fraction']) /
                    (coverage_mono['coverage_fraction'] + 1e-10)
                ),
                'efficiency_gain': float(efficiency_div / (efficiency_mono + 1e-10)),
                'diversity_superior': coverage_div['coverage_fraction'] > coverage_mono['coverage_fraction']
            }
        }


class ReceptorAdaptation:
    """
    Model receptor adaptation and replacement-mediated learning.

    Theorem: Replacement-Mediated Learning
    When a receptor is replaced, new receptor adopts host circuit's charge
    distribution context.
    """

    def __init__(self, population: ReceptorPopulation):
        """
        Initialize adaptation model.

        Args:
            population: ReceptorPopulation
        """
        self.initial_population = population
        self.current_population = population

    def adaptation_step(self, stimulus_timescales: np.ndarray,
                       stimulus_weights: np.ndarray) -> Dict:
        """
        Simulate one adaptation step.

        Receptors with mismatch to stimulus statistics are replaced with
        receptors tuned to stimulus mode.

        Args:
            stimulus_timescales: Distribution of encountered stimulus timescales
            stimulus_weights: Frequency of each stimulus timescale

        Returns:
            Adaptation results
        """
        # Find mode of stimulus distribution
        weighted_mean = np.sum(stimulus_timescales * stimulus_weights) / np.sum(stimulus_weights)

        # Identify receptor type furthest from stimulus mode
        taus = self.current_population.tau_values()
        distances = np.abs(taus - weighted_mean)
        worst_type_idx = np.argmax(distances)

        # Replace with receptor tuned to mode
        new_receptors = list(self.current_population.receptor_types)
        old_receptor = new_receptors[worst_type_idx]

        # New receptor has tau closer to stimulus mode
        new_tau = weighted_mean + 0.1 * (old_receptor.tau - weighted_mean)

        new_receptors[worst_type_idx] = ReceptorType(
            name=old_receptor.name,
            tau=new_tau,
            activation_threshold=old_receptor.activation_threshold,
            conduction_velocity=old_receptor.conduction_velocity,
            spontaneous_rate=old_receptor.spontaneous_rate,
            density=old_receptor.density,
            metabolic_cost=old_receptor.metabolic_cost
        )

        self.current_population = ReceptorPopulation(new_receptors)

        return {
            'replaced_receptor': old_receptor.name,
            'old_tau': float(old_receptor.tau),
            'new_tau': float(new_tau),
            'tau_change': float(new_tau - old_receptor.tau),
            'stimulus_mode': float(weighted_mean),
            'population_spacing': self.current_population.logarithmic_spacing_score()
        }

    def multiple_adaptation_steps(self, stimulus_timescales: np.ndarray,
                                  stimulus_weights: np.ndarray,
                                  n_steps: int) -> List[Dict]:
        """
        Simulate multiple adaptation steps.

        Args:
            stimulus_timescales: Distribution of stimuli
            stimulus_weights: Stimulus frequency
            n_steps: Number of adaptation steps

        Returns:
            List of adaptation results
        """
        results = []
        for _ in range(n_steps):
            result = self.adaptation_step(stimulus_timescales, stimulus_weights)
            results.append(result)

        return results
