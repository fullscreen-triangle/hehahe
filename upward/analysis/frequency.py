"""
Frequency domain analysis tools.
"""

from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy import signal
from scipy.fft import rfft, rfftfreq


def compute_frequency_spectrum(
    data: np.ndarray,
    sampling_rate: float,
    method: str = "welch",
    nperseg: Optional[int] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute power spectral density of time series.

    Parameters
    ----------
    data : np.ndarray
        Time series data
    sampling_rate : float
        Sampling rate in Hz
    method : str
        Method: "welch", "periodogram", "fft"
    nperseg : int, optional
        Segment length for Welch method

    Returns
    -------
    Tuple[np.ndarray, np.ndarray]
        Frequencies and power spectral density
    """
    if method == "welch":
        if nperseg is None:
            nperseg = min(256, len(data) // 4)
        f, psd = signal.welch(data, fs=sampling_rate, nperseg=nperseg)
    elif method == "periodogram":
        f, psd = signal.periodogram(data, fs=sampling_rate)
    elif method == "fft":
        fft_vals = rfft(data)
        psd = np.abs(fft_vals) ** 2
        f = rfftfreq(len(data), 1 / sampling_rate)
    else:
        raise ValueError(f"Unknown method: {method}")

    return f, psd


def detect_frequency_peaks(
    frequencies: np.ndarray,
    psd: np.ndarray,
    prominence: float = 0.1,
    min_frequency: float = 0.0,
    max_frequency: Optional[float] = None,
) -> List[Dict]:
    """
    Detect prominent frequency peaks.

    Parameters
    ----------
    frequencies : np.ndarray
        Frequency values
    psd : np.ndarray
        Power spectral density
    prominence : float
        Minimum prominence for peak detection
    min_frequency : float
        Minimum frequency to consider
    max_frequency : float, optional
        Maximum frequency to consider

    Returns
    -------
    List[Dict]
        List of peaks with frequency, power, and prominence
    """
    # Filter frequency range
    mask = frequencies >= min_frequency
    if max_frequency is not None:
        mask &= frequencies <= max_frequency

    f_filtered = frequencies[mask]
    psd_filtered = psd[mask]

    # Detect peaks
    peak_indices, properties = signal.find_peaks(
        psd_filtered,
        prominence=prominence * psd_filtered.max(),
    )

    peaks = []
    for i, idx in enumerate(peak_indices):
        peaks.append(
            {
                "frequency": f_filtered[idx],
                "power": psd_filtered[idx],
                "prominence": properties["prominences"][i],
            }
        )

    # Sort by power
    peaks.sort(key=lambda x: x["power"], reverse=True)

    return peaks


def extract_scale_frequencies(
    data: np.ndarray,
    sampling_rate: float,
    scale_bands: Dict[str, Tuple[float, float]],
) -> Dict[str, Dict]:
    """
    Extract dominant frequencies for each hierarchical scale.

    Parameters
    ----------
    data : np.ndarray
        Time series data
    sampling_rate : float
        Sampling rate in Hz
    scale_bands : Dict[str, Tuple[float, float]]
        Frequency bands for each scale

    Returns
    -------
    Dict[str, Dict]
        Dominant frequency and power for each scale
    """
    f, psd = compute_frequency_spectrum(data, sampling_rate)

    scale_frequencies = {}
    for scale_name, (f_min, f_max) in scale_bands.items():
        # Filter to scale band
        mask = (f >= f_min) & (f <= f_max)
        if not mask.any():
            scale_frequencies[scale_name] = {
                "frequency": None,
                "power": 0.0,
            }
            continue

        f_band = f[mask]
        psd_band = psd[mask]

        # Find dominant frequency
        max_idx = np.argmax(psd_band)

        scale_frequencies[scale_name] = {
            "frequency": f_band[max_idx],
            "power": psd_band[max_idx],
            "band_power": np.trapz(psd_band, f_band),
        }

    return scale_frequencies


def compute_instantaneous_frequency(
    data: np.ndarray,
    sampling_rate: float,
) -> np.ndarray:
    """
    Compute instantaneous frequency using Hilbert transform.

    Parameters
    ----------
    data : np.ndarray
        Time series data
    sampling_rate : float
        Sampling rate in Hz

    Returns
    -------
    np.ndarray
        Instantaneous frequency
    """
    analytic_signal = signal.hilbert(data)
    instantaneous_phase = np.unwrap(np.angle(analytic_signal))
    instantaneous_frequency = np.diff(instantaneous_phase) / (2.0 * np.pi) * sampling_rate

    return instantaneous_frequency

