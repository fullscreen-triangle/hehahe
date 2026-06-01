"""
Temperature-Dependent Charge Redistribution Dynamics

Validates Arrhenius scaling of relaxation timescales.

Theorem: Arrhenius Scaling of Timescale
τ(T) = τ_0 * e^(E_a / (k_B * T))
"""

import numpy as np
from typing import Dict, Tuple
from scipy.optimize import curve_fit


# Physical constants
BOLTZMANN_CONSTANT = 1.380649e-23  # J/K
BOLTZMANN_eV = 8.617333e-5  # eV/K


class TemperatureModel:
    """
    Model temperature dependence of charge redistribution timescales.

    Based on Arrhenius equation with activation energy E_a.
    """

    def __init__(self, tau_ref: float = 1.0, E_a: float = 12000.0,
                 T_ref: float = 298.15):
        """
        Initialize temperature model.

        Args:
            tau_ref: Reference timescale at T_ref (seconds)
            E_a: Activation energy (J/mol, typical ~12 kJ/mol for ion transport)
            T_ref: Reference temperature (K, default 298.15 K = 25°C)
        """
        self.tau_ref = tau_ref
        self.E_a = E_a  # J/mol
        self.T_ref = T_ref
        self.R = 8.314  # Gas constant J/(mol·K)

    def timescale_at_temperature(self, T: float) -> float:
        """
        Compute timescale at temperature T using Arrhenius equation.

        τ(T) = τ_ref * e^(E_a / (R * T))

        Assumes reference at T_ref, then applies Boltzmann factor.

        Args:
            T: Temperature in Kelvin

        Returns:
            Timescale at temperature T
        """
        # Relative to reference
        exponent = (self.E_a / self.R) * (1.0 / T - 1.0 / self.T_ref)
        return self.tau_ref * np.exp(exponent)

    def temperature_coefficient_Q10(self, T_low: float = 285.15,
                                    T_high: float = 295.15) -> float:
        """
        Compute Q10 temperature coefficient.

        Q10 = τ(T+10K) / τ(T)

        Typical biological values: Q10 ~ 2-3

        Args:
            T_low: Low temperature (K)
            T_high: High temperature (K, typically T_low + 10)

        Returns:
            Q10 value
        """
        tau_low = self.timescale_at_temperature(T_low)
        tau_high = self.timescale_at_temperature(T_high)
        delta_T = T_high - T_low
        return (tau_high / tau_low) ** (10.0 / delta_T)

    def sensation_intensity_vs_temperature(self, T: np.ndarray,
                                          Delta_Q: float) -> np.ndarray:
        """
        Compute peak sensation intensity across temperature range.

        Peak sensation: P_0 = ΔQ / τ(T)

        Args:
            T: Array of temperatures (K)
            Delta_Q: Charge perturbation

        Returns:
            Peak sensation intensity at each temperature
        """
        taus = np.array([self.timescale_at_temperature(t) for t in T])
        return Delta_Q / taus

    def sensation_decay_time_vs_temperature(self, T: np.ndarray) -> np.ndarray:
        """
        Compute sensation decay time across temperature.

        Decay time ∝ τ(T)

        Args:
            T: Array of temperatures (K)

        Returns:
            Sensation decay time at each temperature
        """
        return np.array([self.timescale_at_temperature(t) for t in T])


class ThermalSensationAnalysis:
    """
    Analyze thermal sensation characteristics.

    Thermal sensation emerges from temperature-induced changes in
    ion channel kinetics.
    """

    def __init__(self):
        """Initialize thermal sensation analyzer."""
        # Different receptor types have different thermal sensitivities
        self.TRPV1_model = TemperatureModel(tau_ref=0.05, E_a=15000.0, T_ref=298.15)
        self.TRPM8_model = TemperatureModel(tau_ref=0.1, E_a=8000.0, T_ref=298.15)
        self.TRPA1_model = TemperatureModel(tau_ref=0.02, E_a=18000.0, T_ref=298.15)

    def warm_cold_sensation_crossover(self) -> Dict:
        """
        Analyze crossover between warm and cold sensation.

        At skin temperature (~33°C), warm receptors (TRPV1) become dominant.
        At cold temperatures (~10°C), cold receptors (TRPM8) become dominant.

        Returns:
            Analysis of receptor dominance
        """
        temperatures = np.linspace(278.15, 313.15, 100)  # 5°C to 40°C

        # Compute sensation rates (proportional to 1/τ)
        warm_rate = 1.0 / np.array([self.TRPV1_model.timescale_at_temperature(T)
                                     for T in temperatures])
        cold_rate = 1.0 / np.array([self.TRPM8_model.timescale_at_temperature(T)
                                     for T in temperatures])

        # Relative dominance
        dominance_index = (warm_rate - cold_rate) / (warm_rate + cold_rate)

        # Find crossover
        crossover_idx = np.argmin(np.abs(dominance_index))
        crossover_temp = temperatures[crossover_idx]

        warm_indices = np.where(dominance_index > 0)[0]
        cold_indices = np.where(dominance_index < 0)[0]

        return {
            'crossover_temperature_K': float(crossover_temp),
            'crossover_temperature_C': float(crossover_temp - 273.15),
            'warm_dominant_above_K': float(temperatures[warm_indices[0]]) if len(warm_indices) > 0 else float(temperatures[0]),
            'cold_dominant_below_K': float(temperatures[cold_indices[-1]]) if len(cold_indices) > 0 else float(temperatures[-1]),
            'temperatures_C': (temperatures - 273.15).tolist(),
            'dominance_index': dominance_index.tolist()
        }

    def thermal_pain_threshold(self) -> Dict:
        """
        Analyze thermal pain thresholds.

        TRPV1 activation threshold ~43°C (pain temperature).

        Returns:
            Pain threshold analysis
        """
        temperatures = np.linspace(288.15, 323.15, 150)  # 15°C to 50°C

        # TRPV1 activation increases dramatically with temperature
        sensation_rate = 1.0 / np.array([self.TRPV1_model.timescale_at_temperature(T)
                                         for T in temperatures])

        # Normalize
        normalized = (sensation_rate - np.min(sensation_rate)) / (np.max(sensation_rate) - np.min(sensation_rate))

        # Pain threshold at ~50% of maximum
        pain_threshold_idx = np.argmin(np.abs(normalized - 0.5))
        pain_threshold_T = temperatures[pain_threshold_idx]

        return {
            'pain_threshold_K': float(pain_threshold_T),
            'pain_threshold_C': float(pain_threshold_T - 273.15),
            'temperatures_C': (temperatures - 273.15).tolist(),
            'normalized_sensation_rate': normalized.tolist()
        }

    def compare_receptor_temperature_sensitivity(self) -> Dict:
        """
        Compare temperature sensitivity across receptor types.

        Returns:
            Temperature sensitivity comparison
        """
        temperatures = np.linspace(278.15, 313.15, 50)  # 5°C to 40°C

        models = {
            'TRPV1_warm': self.TRPV1_model,
            'TRPM8_cold': self.TRPM8_model,
            'TRPA1_cold': self.TRPA1_model
        }

        results = {}

        for name, model in models.items():
            taus = np.array([model.timescale_at_temperature(T) for T in temperatures])
            sensation_rates = 1.0 / taus

            # Q10 at different temperatures
            q10_values = []
            for i in range(len(temperatures) - 10):
                tau_low = model.timescale_at_temperature(temperatures[i])
                tau_high = model.timescale_at_temperature(temperatures[i + 10])
                q10 = tau_high / tau_low
                q10_values.append(q10)

            results[name] = {
                'temperature_range_C': [float(temperatures[0] - 273.15),
                                       float(temperatures[-1] - 273.15)],
                'tau_range': [float(np.min(taus)), float(np.max(taus))],
                'sensation_rate_range': [float(np.min(sensation_rates)),
                                        float(np.max(sensation_rates))],
                'mean_Q10': float(np.mean(q10_values)),
                'Q10_range': [float(np.min(q10_values)), float(np.max(q10_values))]
            }

        return results


def validate_arrhenius_scaling(temperatures: np.ndarray, taus: np.ndarray,
                               E_a_expected: float = 12000.0) -> Dict:
    """
    Validate Arrhenius scaling of timescales.

    Fits τ(T) = τ_0 * e^(E_a / (R*T)) to data and extracts E_a.

    Args:
        temperatures: Array of temperatures (K)
        taus: Array of measured timescales (s)
        E_a_expected: Expected activation energy (J/mol)

    Returns:
        Validation results
    """
    def arrhenius(T, tau_0, E_a):
        return tau_0 * np.exp(E_a / (8.314 * T))

    try:
        popt, pcov = curve_fit(arrhenius, temperatures, taus,
                               p0=[taus[0], E_a_expected],
                               maxfev=5000)
        tau_0_fit, E_a_fit = popt

        # Compute R-squared
        residuals = taus - arrhenius(temperatures, *popt)
        ss_res = np.sum(residuals**2)
        ss_tot = np.sum((taus - np.mean(taus))**2)
        r_squared = 1.0 - (ss_res / ss_tot)

        return {
            'passes_validation': np.abs(E_a_fit - E_a_expected) / E_a_expected < 0.3,
            'tau_0_fitted': float(tau_0_fit),
            'E_a_fitted': float(E_a_fit),
            'E_a_expected': float(E_a_expected),
            'E_a_error_fraction': float(abs(E_a_fit - E_a_expected) / E_a_expected),
            'r_squared': float(r_squared),
            'n_datapoints': int(len(temperatures))
        }
    except RuntimeError:
        return {'error': 'Fitting failed'}


def predict_thermal_adaptation(initial_temp: float = 298.15,
                               adapted_temp: float = 308.15) -> Dict:
    """
    Predict how thermal adaptation changes sensation characteristics.

    Receptor adaptation shifts activation threshold with temperature history.

    Args:
        initial_temp: Initial temperature (K)
        adapted_temp: Adapted temperature (K)

    Returns:
        Adaptation prediction
    """
    model = TemperatureModel()

    tau_initial = model.timescale_at_temperature(initial_temp)
    tau_adapted = model.timescale_at_temperature(adapted_temp)

    # Sensation rate shifts
    sensation_change = tau_adapted / tau_initial

    return {
        'initial_temperature_C': float(initial_temp - 273.15),
        'adapted_temperature_C': float(adapted_temp - 273.15),
        'timescale_ratio': float(tau_adapted / tau_initial),
        'sensation_rate_change': float(1.0 / sensation_change),
        'interpretation': 'Warming decreases sensation rate (faster relaxation)',
        'cooling_effect': 'Cooling increases sensation rate (slower relaxation)'
    }
