"""
Gear ratio analysis and validation.
"""

from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy import stats


def compute_gear_ratio(
    freq1: float,
    freq2: float,
) -> float:
    """
    Compute gear ratio between two frequencies.

    R_{1→2} = ω₁ / ω₂

    Parameters
    ----------
    freq1 : float
        Higher frequency scale
    freq2 : float
        Lower frequency scale

    Returns
    -------
    float
        Gear ratio
    """
    if freq2 == 0:
        return np.inf
    return freq1 / freq2


def validate_gear_ratios(
    measured_ratios: Dict[str, float],
    theoretical_ratios: Dict[str, float],
    tolerance: float = 0.15,
) -> Dict[str, Dict]:
    """
    Validate measured gear ratios against theoretical predictions.

    Parameters
    ----------
    measured_ratios : Dict[str, float]
        Measured gear ratios
    theoretical_ratios : Dict[str, float]
        Theoretical gear ratios
    tolerance : float
        Acceptable relative error

    Returns
    -------
    Dict[str, Dict]
        Validation results for each ratio
    """
    results = {}

    for ratio_name in measured_ratios:
        if ratio_name not in theoretical_ratios:
            continue

        measured = measured_ratios[ratio_name]
        theoretical = theoretical_ratios[ratio_name]

        relative_error = abs(measured - theoretical) / theoretical
        is_valid = relative_error <= tolerance

        results[ratio_name] = {
            "measured": measured,
            "theoretical": theoretical,
            "relative_error": relative_error,
            "is_valid": is_valid,
        }

    return results


def compute_transitive_gear_ratio(
    ratios: List[float],
) -> float:
    """
    Compute compound gear ratio through transitive property.

    R_{i→k} = R_{i→j} × R_{j→k}

    Parameters
    ----------
    ratios : List[float]
        Sequence of gear ratios

    Returns
    -------
    float
        Compound gear ratio
    """
    result = 1.0
    for ratio in ratios:
        result *= ratio
    return result


def estimate_gear_ratio_from_timeseries(
    data1: np.ndarray,
    data2: np.ndarray,
    sampling_rate: float,
    method: str = "peak_frequency",
) -> Tuple[float, float]:
    """
    Estimate gear ratio from time series data.

    Parameters
    ----------
    data1 : np.ndarray
        Higher frequency time series
    data2 : np.ndarray
        Lower frequency time series
    sampling_rate : float
        Sampling rate in Hz
    method : str
        Method: "peak_frequency", "median_frequency"

    Returns
    -------
    Tuple[float, float]
        (gear_ratio, confidence)
    """
    from validation.analysis.frequency import compute_frequency_spectrum, detect_frequency_peaks

    # Compute spectra
    f1, psd1 = compute_frequency_spectrum(data1, sampling_rate)
    f2, psd2 = compute_frequency_spectrum(data2, sampling_rate)

    if method == "peak_frequency":
        # Find dominant peaks
        peaks1 = detect_frequency_peaks(f1, psd1, prominence=0.1)
        peaks2 = detect_frequency_peaks(f2, psd2, prominence=0.1)

        if not peaks1 or not peaks2:
            return np.nan, 0.0

        freq1 = peaks1[0]["frequency"]
        freq2 = peaks2[0]["frequency"]

        ratio = freq1 / freq2 if freq2 > 0 else np.nan

        # Confidence based on peak prominence
        confidence = min(peaks1[0]["prominence"], peaks2[0]["prominence"])

    elif method == "median_frequency":
        # Compute median frequency
        cumsum1 = np.cumsum(psd1)
        cumsum2 = np.cumsum(psd2)

        idx1 = np.searchsorted(cumsum1, cumsum1[-1] / 2)
        idx2 = np.searchsorted(cumsum2, cumsum2[-1] / 2)

        freq1 = f1[idx1]
        freq2 = f2[idx2]

        ratio = freq1 / freq2 if freq2 > 0 else np.nan
        confidence = 0.5  # Median is moderately confident

    else:
        raise ValueError(f"Unknown method: {method}")

    return ratio, confidence


def compute_hierarchical_gear_ratios(
    scale_frequencies: Dict[str, float],
    hierarchy: List[str],
) -> Dict[str, float]:
    """
    Compute gear ratios for entire hierarchical system.

    Parameters
    ----------
    scale_frequencies : Dict[str, float]
        Dominant frequency for each scale
    hierarchy : List[str]
        Ordered list of scale names (high to low frequency)

    Returns
    -------
    Dict[str, float]
        Gear ratios between adjacent scales
    """
    gear_ratios = {}

    for i in range(len(hierarchy) - 1):
        scale_high = hierarchy[i]
        scale_low = hierarchy[i + 1]

        if scale_high in scale_frequencies and scale_low in scale_frequencies:
            freq_high = scale_frequencies[scale_high]
            freq_low = scale_frequencies[scale_low]

            if freq_high and freq_low and freq_low > 0:
                ratio = freq_high / freq_low
                gear_ratios[f"{scale_high}_to_{scale_low}"] = ratio

    return gear_ratios


def test_gear_ratio_consistency(
    gear_ratios: Dict[str, float],
    hierarchy: List[str],
    tolerance: float = 0.2,
) -> bool:
    """
    Test transitive consistency of gear ratios.

    For scales i, j, k: R_{i→k} ≈ R_{i→j} × R_{j→k}

    Parameters
    ----------
    gear_ratios : Dict[str, float]
        Measured gear ratios
    hierarchy : List[str]
        Scale hierarchy
    tolerance : float
        Acceptable relative error

    Returns
    -------
    bool
        True if ratios are consistent
    """
    # Test all possible transitive relationships
    for i in range(len(hierarchy) - 2):
        scale_i = hierarchy[i]
        scale_j = hierarchy[i + 1]
        scale_k = hierarchy[i + 2]

        ratio_ij_key = f"{scale_i}_to_{scale_j}"
        ratio_jk_key = f"{scale_j}_to_{scale_k}"
        ratio_ik_key = f"{scale_i}_to_{scale_k}"

        if all(key in gear_ratios for key in [ratio_ij_key, ratio_jk_key, ratio_ik_key]):
            # Compute transitive ratio
            transitive = gear_ratios[ratio_ij_key] * gear_ratios[ratio_jk_key]
            direct = gear_ratios[ratio_ik_key]

            relative_error = abs(transitive - direct) / direct
            if relative_error > tolerance:
                return False

    return True
