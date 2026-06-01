"""
Sensation Mechanics: Time Constant Categorization and Quality

Validates core claims:
- Sensation rate = |dQ/dt|
- Time constant determines sensation category (pain vs pleasure)
- Total sensation is finite
- Sensation quality emerges from spatiotemporal charge patterns
"""

import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum


class SensationCategory(Enum):
    """Sensation categories based on time constant."""
    PAIN = "pain"  # Fast decay (small τ)
    NEUTRAL = "neutral"  # Intermediate τ
    PLEASURE = "pleasure"  # Slow decay (large τ)


@dataclass
class SensationProfile:
    """Characterization of a sensation response."""
    category: SensationCategory
    time_constant: float
    peak_sensation: float
    total_sensation: float
    decay_rate: float  # How quickly sensation fades
    temporal_width: float  # Duration at 50% of peak


class SensationCategorizer:
    """
    Categorizes sensation based on time constant characteristics.

    Theorem: Sensation Category from Time Constant
    - Pain: τ < τ_c (typically 10-100 ms for fast nociceptors)
    - Neutral: τ ≈ τ_c
    - Pleasure: τ > τ_c (typically 100 ms - 1 s for hedonic stimuli)
    """

    def __init__(self, tau_critical: float = 0.05, tau_width: float = 0.02):
        """
        Initialize categorizer.

        Args:
            tau_critical: Boundary time constant (typically neural integration timescale)
            tau_width: Width of neutral zone around critical timescale
        """
        self.tau_critical = tau_critical
        self.tau_width = tau_width

    def categorize(self, tau: float) -> SensationCategory:
        """
        Categorize sensation based on time constant.

        Args:
            tau: Relaxation timescale

        Returns:
            SensationCategory enum
        """
        tau_lower = self.tau_critical - self.tau_width / 2
        tau_upper = self.tau_critical + self.tau_width / 2

        if tau < tau_lower:
            return SensationCategory.PAIN
        elif tau_lower <= tau <= tau_upper:
            return SensationCategory.NEUTRAL
        else:
            return SensationCategory.PLEASURE

    def categorize_profile(self, time: np.ndarray, sensation_rate: np.ndarray,
                          Delta_Q: float, tau_estimated: float) -> SensationProfile:
        """
        Create full sensation profile.

        Args:
            time: Time points
            sensation_rate: Sensation rate over time
            Delta_Q: Total charge perturbation
            tau_estimated: Estimated time constant

        Returns:
            SensationProfile object
        """
        category = self.categorize(tau_estimated)
        peak_sensation = np.max(sensation_rate)
        total_sensation = np.trapezoid(sensation_rate, time)

        # Decay rate: how quickly sensation decreases
        # Measured as negative derivative at peak
        peak_idx = np.argmax(sensation_rate)
        if peak_idx < len(sensation_rate) - 1:
            decay_rate = -(sensation_rate[peak_idx + 1] - sensation_rate[peak_idx]) / (
                time[peak_idx + 1] - time[peak_idx]
            )
        else:
            decay_rate = 0.0

        # Temporal width at 50% of peak
        half_max = peak_sensation / 2
        above_half = sensation_rate >= half_max
        if np.any(above_half):
            indices = np.where(above_half)[0]
            temporal_width = time[indices[-1]] - time[indices[0]] if len(indices) > 1 else 0
        else:
            temporal_width = 0

        return SensationProfile(
            category=category,
            time_constant=tau_estimated,
            peak_sensation=float(peak_sensation),
            total_sensation=float(total_sensation),
            decay_rate=float(decay_rate),
            temporal_width=float(temporal_width)
        )


class MultimodalSensation:
    """
    Multi-modal sensation integration through frequency matching.

    Theorem: Frequency Matching for Cross-Circuit Influence
    Two circuits couple effectively when |Δf| / f_avg < Δf_thresh ≈ 0.1
    """

    def __init__(self, freq_match_threshold: float = 0.1):
        """
        Initialize multimodal sensation processor.

        Args:
            freq_match_threshold: Tolerance for frequency matching
        """
        self.freq_match_threshold = freq_match_threshold

    def frequency_matching_score(self, tau1: float, tau2: float) -> float:
        """
        Compute frequency matching between two circuits.

        Score = |Δτ| / (τ1 + τ2), ranges from 0 (perfect match) to 1 (no match)

        Args:
            tau1, tau2: Time constants of two circuits

        Returns:
            Matching score (0 = perfect match, 1 = no match)
        """
        if tau1 + tau2 == 0:
            return 1.0
        return abs(tau1 - tau2) / (tau1 + tau2)

    def is_frequency_matched(self, tau1: float, tau2: float) -> bool:
        """
        Check if two circuits are frequency matched.

        Args:
            tau1, tau2: Time constants

        Returns:
            True if frequency matched within threshold
        """
        score = self.frequency_matching_score(tau1, tau2)
        return score < self.freq_match_threshold

    def coupled_sensation_rate(self, P1: np.ndarray, P2: np.ndarray,
                               tau1: float, tau2: float,
                               weights: Tuple[float, float] = (1.0, 1.0)) -> np.ndarray:
        """
        Compute integrated sensation from two modalities.

        If frequency matched: constructive/destructive interference
        If not matched: simple summation with weighting

        Args:
            P1, P2: Sensation rates from two modalities
            tau1, tau2: Time constants
            weights: Salience weights [w1, w2]

        Returns:
            Combined sensation rate
        """
        w1, w2 = weights

        if self.is_frequency_matched(tau1, tau2):
            # Frequency matched: interference pattern
            # Phase relationship determined by time constant difference
            phase_diff = 2 * np.pi * (tau1 - tau2) / (tau1 + tau2)
            return np.abs(w1 * P1 + w2 * P2 * np.cos(phase_diff))
        else:
            # Not matched: independent summation
            return w1 * P1 + w2 * P2

    def disambiguate_stimuli(self, sensations: List[np.ndarray],
                             taus: List[float]) -> Dict:
        """
        Analyze multi-modal sensation for disambiguation.

        Args:
            sensations: List of sensation rates from different modalities
            taus: Time constants for each modality

        Returns:
            Disambiguation analysis
        """
        n_modalities = len(sensations)
        matching_matrix = np.zeros((n_modalities, n_modalities))

        for i in range(n_modalities):
            for j in range(n_modalities):
                if i != j:
                    matching_matrix[i, j] = self.frequency_matching_score(taus[i], taus[j])

        # Identify clusters of matched modalities
        clusters = []
        used = set()

        for i in range(n_modalities):
            if i in used:
                continue
            cluster = [i]
            used.add(i)

            for j in range(i + 1, n_modalities):
                if j not in used and self.is_frequency_matched(taus[i], taus[j]):
                    cluster.append(j)
                    used.add(j)

            clusters.append(cluster)

        return {
            'n_clusters': len(clusters),
            'clusters': clusters,
            'matching_matrix': matching_matrix.tolist(),
            'integration_possible': len(clusters) == 1  # All modalities match
        }


class SensationQuality:
    """
    Characterize sensation quality from spatiotemporal charge patterns.

    Quality emerges from:
    1. Which compartments are perturbed (spatial pattern)
    2. Order and overlap of timescales
    3. Relative amplitudes across timescales
    """

    @staticmethod
    def spatial_pattern(Q0: np.ndarray, compartment_names: List[str]) -> Dict:
        """
        Extract spatial pattern of initial perturbation.

        Args:
            Q0: Initial charge perturbation across compartments
            compartment_names: Names of compartments

        Returns:
            Spatial pattern characterization
        """
        perturbation_strength = np.abs(Q0)
        dominant_idx = np.argmax(perturbation_strength)

        return {
            'dominant_compartment': compartment_names[dominant_idx],
            'perturbation_vector': Q0.tolist(),
            'perturbation_magnitude': float(np.linalg.norm(Q0)),
            'spatial_entropy': float(-np.sum(
                (perturbation_strength / np.sum(perturbation_strength) + 1e-10) *
                np.log(perturbation_strength / np.sum(perturbation_strength) + 1e-10)
            ))
        }

    @staticmethod
    def temporal_pattern(taus: List[float], amplitudes: List[float]) -> Dict:
        """
        Characterize temporal response pattern.

        Args:
            taus: List of timescales
            amplitudes: Amplitudes for each timescale

        Returns:
            Temporal pattern characterization
        """
        taus = np.array(taus)
        amplitudes = np.array(np.abs(amplitudes))

        # Timescale distribution
        tau_min, tau_max = np.min(taus), np.max(taus)
        tau_ratio = tau_max / tau_min if tau_min > 0 else 1.0

        # Amplitude distribution
        dominant_idx = np.argmax(amplitudes)
        amplitude_concentration = amplitudes[dominant_idx] / np.sum(amplitudes)

        # Effective timescale
        tau_eff = np.sum(amplitudes * taus) / np.sum(amplitudes)

        return {
            'tau_range': [float(tau_min), float(tau_max)],
            'tau_ratio': float(tau_ratio),
            'timescale_diversity': float(np.std(np.log10(taus + 1e-10))),
            'dominant_amplitude_fraction': float(amplitude_concentration),
            'effective_timescale': float(tau_eff),
            'n_timescales': len(taus)
        }


def validate_sensation_conservation(Delta_Q: float, dt: float,
                                     sensation_rate: np.ndarray,
                                     rtol: float = 0.05) -> Dict:
    """
    Validate that total sensation equals charge perturbation.

    Theorem: Sensation Integral is Finite
    ∫ P(t) dt = ΔQ

    Args:
        Delta_Q: Total charge perturbation
        dt: Time step
        sensation_rate: Sensation rate over time
        rtol: Relative tolerance

    Returns:
        Validation results
    """
    total_sensation = np.trapezoid(sensation_rate, dx=dt)
    relative_error = abs(total_sensation - Delta_Q) / (Delta_Q + 1e-10)

    return {
        'passes_validation': relative_error < rtol,
        'predicted': float(Delta_Q),
        'measured': float(total_sensation),
        'relative_error': float(relative_error),
        'tolerance': rtol
    }


def validate_pain_pleasure_transition(categorizer: SensationCategorizer,
                                      tau_values: np.ndarray) -> Dict:
    """
    Validate pain/pleasure transition at critical time constant.

    Args:
        categorizer: SensationCategorizer instance
        tau_values: Array of time constants to test

    Returns:
        Validation results
    """
    categories = [categorizer.categorize(tau) for tau in tau_values]
    category_transitions = np.diff(
        [cat.value != SensationCategory.NEUTRAL.value for cat in categories]
    )

    # Count transitions
    n_transitions = np.sum(np.abs(category_transitions))

    return {
        'n_timescales_tested': int(len(tau_values)),
        'tau_critical': float(categorizer.tau_critical),
        'tau_range': [float(np.min(tau_values)), float(np.max(tau_values))],
        'category_counts': {
            'pain': int(np.sum([c == SensationCategory.PAIN for c in categories])),
            'neutral': int(np.sum([c == SensationCategory.NEUTRAL for c in categories])),
            'pleasure': int(np.sum([c == SensationCategory.PLEASURE for c in categories]))
        },
        'transition_sharpness': int(n_transitions)
    }
