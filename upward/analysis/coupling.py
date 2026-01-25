"""
Coupling analysis tools.
"""

from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy import signal


def compute_hilbert_phase(data: np.ndarray) -> np.ndarray:
    """
    Compute instantaneous phase using Hilbert transform.

    Parameters
    ----------
    data : np.ndarray
        Time series data

    Returns
    -------
    np.ndarray
        Instantaneous phase
    """
    analytic_signal = signal.hilbert(data)
    phase = np.angle(analytic_signal)
    return phase


def compute_phase_locking_value(
    phase1: np.ndarray,
    phase2: np.ndarray,
    window_size: Optional[int] = None,
) -> float:
    """
    Compute phase locking value between two signals.

    PLV = |⟨exp(i(φ₁ - φ₂))⟩|

    Parameters
    ----------
    phase1 : np.ndarray
        Phase of first signal
    phase2 : np.ndarray
        Phase of second signal
    window_size : int, optional
        Window size for sliding PLV

    Returns
    -------
    float
        Phase locking value [0, 1]
    """
    if window_size is None:
        phase_diff = phase1 - phase2
        plv = np.abs(np.mean(np.exp(1j * phase_diff)))
    else:
        # Sliding window PLV
        phase_diff = phase1 - phase2
        plv_values = []
        for i in range(len(phase_diff) - window_size + 1):
            window = phase_diff[i : i + window_size]
            plv_values.append(np.abs(np.mean(np.exp(1j * window))))
        plv = np.mean(plv_values)

    return plv


def compute_coupling_strength(
    data1: np.ndarray,
    data2: np.ndarray,
    sampling_rate: float,
    method: str = "plv",
) -> float:
    """
    Compute coupling strength between two time series.

    Parameters
    ----------
    data1 : np.ndarray
        First time series
    data2 : np.ndarray
        Second time series
    sampling_rate : float
        Sampling rate in Hz
    method : str
        Method: "plv" (phase locking), "coherence", "correlation"

    Returns
    -------
    float
        Coupling strength [0, 1]
    """
    if method == "plv":
        phase1 = compute_hilbert_phase(data1)
        phase2 = compute_hilbert_phase(data2)
        return compute_phase_locking_value(phase1, phase2)

    elif method == "coherence":
        f, coh = signal.coherence(data1, data2, fs=sampling_rate)
        return np.mean(coh)

    elif method == "correlation":
        corr = np.corrcoef(data1, data2)[0, 1]
        return np.abs(corr)

    else:
        raise ValueError(f"Unknown method: {method}")


def compute_coupling_matrix(
    signals: Dict[str, np.ndarray],
    sampling_rate: float,
    method: str = "plv",
) -> Tuple[np.ndarray, List[str]]:
    """
    Compute coupling matrix between multiple signals.

    Parameters
    ----------
    signals : Dict[str, np.ndarray]
        Dictionary of signal name to time series
    sampling_rate : float
        Sampling rate in Hz
    method : str
        Coupling method

    Returns
    -------
    Tuple[np.ndarray, List[str]]
        Coupling matrix and signal names
    """
    signal_names = list(signals.keys())
    n_signals = len(signal_names)

    coupling_matrix = np.zeros((n_signals, n_signals))

    for i, name1 in enumerate(signal_names):
        for j, name2 in enumerate(signal_names):
            if i == j:
                coupling_matrix[i, j] = 1.0
            elif i < j:
                coupling = compute_coupling_strength(
                    signals[name1],
                    signals[name2],
                    sampling_rate,
                    method,
                )
                coupling_matrix[i, j] = coupling
                coupling_matrix[j, i] = coupling

    return coupling_matrix, signal_names


def compute_phase_coherence_index(
    data1: np.ndarray,
    data2: np.ndarray,
    sampling_rate: float,
    frequency_band: Tuple[float, float],
) -> float:
    """
    Compute phase coherence in specific frequency band.

    Parameters
    ----------
    data1 : np.ndarray
        First time series
    data2 : np.ndarray
        Second time series
    sampling_rate : float
        Sampling rate in Hz
    frequency_band : Tuple[float, float]
        (min_freq, max_freq) in Hz

    Returns
    -------
    float
        Phase coherence index
    """
    # Bandpass filter
    sos = signal.butter(
        4,
        frequency_band,
        btype="band",
        fs=sampling_rate,
        output="sos",
    )

    data1_filtered = signal.sosfilt(sos, data1)
    data2_filtered = signal.sosfilt(sos, data2)

    # Compute phases
    phase1 = compute_hilbert_phase(data1_filtered)
    phase2 = compute_hilbert_phase(data2_filtered)

    # Phase coherence
    return compute_phase_locking_value(phase1, phase2)


def detect_coupling_decay(
    coupling_time_series: np.ndarray,
    timestamps: np.ndarray,
) -> Tuple[float, float]:
    """
    Detect exponential decay in coupling strength.

    C(t) = C₀ * exp(-t/τ)

    Parameters
    ----------
    coupling_time_series : np.ndarray
        Time series of coupling strength
    timestamps : np.ndarray
        Time points (in seconds)

    Returns
    -------
    Tuple[float, float]
        (C₀, τ) initial coupling and decay time constant
    """
    # Log transform for linear fit
    mask = coupling_time_series > 0
    log_coupling = np.log(coupling_time_series[mask])
    t = timestamps[mask]

    # Linear fit: log(C) = log(C₀) - t/τ
    coeffs = np.polyfit(t, log_coupling, 1)
    slope = coeffs[0]
    intercept = coeffs[1]

    c0 = np.exp(intercept)
    tau = -1.0 / slope if slope != 0 else np.inf

    return c0, tau


def compute_coupling_strength_with_amplitude(
    data1: np.ndarray,
    data2: np.ndarray,
) -> float:
    """
    Compute coupling strength with amplitude modulation.

    C_ij = |⟨A_i(φ_j) exp(iφ_i)⟩|

    Parameters
    ----------
    data1 : np.ndarray
        First time series
    data2 : np.ndarray
        Second time series

    Returns
    -------
    float
        Coupling strength
    """
    # Hilbert transform
    analytic1 = signal.hilbert(data1)
    analytic2 = signal.hilbert(data2)

    # Extract amplitude and phase
    amplitude1 = np.abs(analytic1)
    phase1 = np.angle(analytic1)
    phase2 = np.angle(analytic2)

    # Amplitude modulation as function of phase2
    coupling_vector = amplitude1 * np.exp(1j * phase1)
    coupling_strength = np.abs(np.mean(coupling_vector))

    return coupling_strength
