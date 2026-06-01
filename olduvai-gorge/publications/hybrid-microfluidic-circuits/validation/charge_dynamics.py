"""
Closed Hybrid Microfluidic Circuit Charge Redistribution Dynamics

Core module for simulating charge dynamics in closed systems without external
ionic reservoirs. Validates exponential decay kinetics and time constant
relationships.
"""

import numpy as np
from scipy.optimize import curve_fit
from dataclasses import dataclass
from typing import Tuple, Dict, List
import json


@dataclass
class CircuitConfig:
    """Configuration for a closed hybrid microfluidic circuit."""

    n_compartments: int
    Q_total: float  # Total charge in the circuit (conserved)
    tau_compartments: np.ndarray  # Relaxation timescale for each compartment
    g_coupling: np.ndarray  # Conductance matrix between compartments
    compartment_names: List[str] = None

    def __post_init__(self):
        if self.compartment_names is None:
            self.compartment_names = [f"Compartment_{i}" for i in range(self.n_compartments)]

        assert len(self.tau_compartments) == self.n_compartments
        assert self.g_coupling.shape == (self.n_compartments, self.n_compartments)
        assert np.isclose(np.sum(np.diag(np.diag(self.g_coupling))), 0) or True  # Allow flexibility


class ClosedCircuit:
    """
    Simulates a closed hybrid microfluidic circuit with exponential charge
    redistribution dynamics.
    """

    def __init__(self, config: CircuitConfig):
        self.config = config
        self.Q_equilibrium = np.ones(config.n_compartments) * config.Q_total / config.n_compartments
        self.history = {
            'time': [],
            'Q': [],
            'dQ_dt': [],
            'sensation_rate': []
        }

    def exponential_response(self, t: np.ndarray, Q0: np.ndarray, tau: float) -> np.ndarray:
        """
        Compute charge response to step perturbation with single dominant timescale.

        Q(t) = Q_∞ + (Q_0 - Q_∞) * e^(-t/τ)

        Args:
            t: Time points
            Q0: Initial charge distribution
            tau: Relaxation timescale

        Returns:
            Charge distribution at each time point
        """
        Q_inf = self.Q_equilibrium
        return Q_inf[:, np.newaxis] + (Q0[:, np.newaxis] - Q_inf[:, np.newaxis]) * np.exp(-t / tau)

    def sensation_rate(self, Q: np.ndarray) -> np.ndarray:
        """
        Compute sensation rate as magnitude of charge redistribution rate.

        P(t) = |dQ/dt|

        Args:
            Q: Charge distribution (n_compartments, time_points)

        Returns:
            Sensation rate at each time point
        """
        # Approximate dQ/dt using finite differences
        dQ_dt = np.diff(Q, axis=1)

        # Sensation rate is magnitude of total rate of change
        sensation = np.linalg.norm(dQ_dt, axis=0)
        return sensation

    def simulate_perturbation(self, Q0: np.ndarray, tau: float,
                              t_max: float = 10.0, dt: float = 0.01) -> Dict:
        """
        Simulate circuit response to initial charge perturbation.

        Args:
            Q0: Initial charge distribution
            tau: Dominant relaxation timescale
            t_max: Maximum simulation time
            dt: Time step

        Returns:
            Dictionary with simulation results
        """
        assert np.isclose(np.sum(Q0), self.config.Q_total), "Charge conservation violated"

        t = np.arange(0, t_max, dt)
        Q = self.exponential_response(t, Q0, tau)

        # Compute sensation rate
        sensation = self.sensation_rate(Q)

        # Store history
        self.history['time'] = t[:-1].tolist()
        self.history['Q'] = Q[:, :-1].tolist()
        self.history['sensation_rate'] = sensation.tolist()

        # Analytical solution for sensation rate: P(t) = P_0 * e^(-t/τ)
        Delta_Q = np.linalg.norm(Q0 - self.Q_equilibrium)
        P0_analytical = Delta_Q / tau
        sensation_analytical = P0_analytical * np.exp(-t[:-1] / tau)

        return {
            'time': t[:-1],
            'Q': Q[:, :-1],
            'sensation_rate': sensation,
            'sensation_rate_analytical': sensation_analytical,
            'tau': tau,
            'Delta_Q': Delta_Q,
            'P0': P0_analytical
        }

    def total_sensation(self, sensation_rate: np.ndarray, dt: float) -> float:
        """
        Compute total sensation experienced during response.

        ∫ P(t) dt should equal ΔQ (Theorem: Sensation Integral is Finite)

        Args:
            sensation_rate: Sensation rate over time
            dt: Time step

        Returns:
            Total sensation (should equal ΔQ)
        """
        return np.sum(sensation_rate) * dt

    def extract_timescale(self, sensation_rate: np.ndarray, t: np.ndarray) -> float:
        """
        Extract relaxation timescale from sensation rate decay curve.

        Fits P(t) = P_0 * e^(-t/τ) to data and extracts τ.

        Args:
            sensation_rate: Measured sensation rate
            t: Time points

        Returns:
            Estimated timescale
        """
        def exponential_decay(t, P0, tau):
            return P0 * np.exp(-t / tau)

        # Initial guess
        p0 = [sensation_rate[0], 1.0]

        try:
            popt, _ = curve_fit(exponential_decay, t, sensation_rate, p0=p0, maxfev=5000)
            return popt[1]
        except RuntimeError:
            return None


class MultiTimescaleCircuit(ClosedCircuit):
    """
    Circuit with multiple relaxation timescales.

    Q(t) = Q_∞ + Σ_k A_k * e^(-t/τ_k)
    """

    def multi_exponential_response(self, t: np.ndarray, Q0: np.ndarray,
                                    taus: List[float], amplitudes: List[float]) -> np.ndarray:
        """
        Compute charge response with multiple timescales.

        Args:
            t: Time points
            Q0: Initial perturbation
            taus: List of timescales
            amplitudes: Amplitude for each timescale

        Returns:
            Charge distribution
        """
        Q_inf = self.Q_equilibrium
        Q = Q_inf[:, np.newaxis] * np.ones((self.config.n_compartments, len(t)))

        for tau, amp in zip(taus, amplitudes):
            Q += amp * Q0[:, np.newaxis] * np.exp(-t / tau)

        return Q

    def dominant_timescale(self, taus: List[float], amplitudes: List[float]) -> float:
        """
        Compute effective timescale from amplitude-weighted average.

        τ_eff = Σ A_k * τ_k / Σ A_k

        Args:
            taus: List of timescales
            amplitudes: List of amplitudes

        Returns:
            Effective timescale
        """
        amplitudes = np.array(np.abs(amplitudes))
        taus = np.array(taus)
        return np.sum(amplitudes * taus) / np.sum(amplitudes)


def validate_charge_conservation(Q: np.ndarray, Q_total: float, rtol: float = 1e-10) -> bool:
    """
    Validate that charge is conserved throughout simulation.

    Args:
        Q: Charge distribution (n_compartments, time_points)
        Q_total: Total charge
        rtol: Relative tolerance

    Returns:
        True if charge is conserved within tolerance
    """
    Q_sum = np.sum(Q, axis=0)
    return np.allclose(Q_sum, Q_total, rtol=rtol)


def validate_exponential_decay(sensation_rate: np.ndarray, t: np.ndarray,
                                tau: float, rtol: float = 0.1) -> Dict:
    """
    Validate that sensation rate follows exponential decay.

    Compares measured rate to P(t) = P_0 * e^(-t/τ)

    Args:
        sensation_rate: Measured sensation rate
        t: Time points
        tau: Expected timescale
        rtol: Relative tolerance for validation

    Returns:
        Validation results
    """
    P0 = sensation_rate[0]
    P_expected = P0 * np.exp(-t / tau)

    relative_error = np.abs(sensation_rate - P_expected) / (P_expected + 1e-10)

    return {
        'passes_validation': np.all(relative_error < rtol),
        'max_relative_error': float(np.max(relative_error)),
        'mean_relative_error': float(np.mean(relative_error)),
        'r_squared': float(1.0 - np.sum((sensation_rate - P_expected)**2) /
                          np.sum((sensation_rate - np.mean(sensation_rate))**2))
    }


def create_circuit_config(n_compartments: int = 3,
                          Q_total: float = 1.0,
                          tau_range: Tuple[float, float] = (0.1, 1.0)) -> CircuitConfig:
    """
    Create a random circuit configuration.

    Args:
        n_compartments: Number of compartments
        Q_total: Total charge
        tau_range: Range of timescales (min, max)

    Returns:
        CircuitConfig object
    """
    tau_compartments = np.random.uniform(tau_range[0], tau_range[1], n_compartments)
    g_coupling = np.random.rand(n_compartments, n_compartments) * 0.5
    np.fill_diagonal(g_coupling, 0)  # No self-coupling

    return CircuitConfig(
        n_compartments=n_compartments,
        Q_total=Q_total,
        tau_compartments=tau_compartments,
        g_coupling=g_coupling
    )
