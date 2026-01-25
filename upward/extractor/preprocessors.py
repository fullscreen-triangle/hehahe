"""
Data preprocessing and cleaning utilities.
"""

from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import interpolate, signal
from scipy.ndimage import median_filter

from validation.data.loaders import ActivityData


def clean_timeseries(
    data: pd.Series,
    method: str = "median",
    window_size: int = 5,
    outlier_std: float = 3.0,
) -> pd.Series:
    """
    Clean time series data by removing outliers and smoothing.

    Parameters
    ----------
    data : pd.Series
        Input time series
    method : str
        Cleaning method: "median", "gaussian", "none"
    window_size : int
        Window size for filtering
    outlier_std : float
        Standard deviations for outlier detection

    Returns
    -------
    pd.Series
        Cleaned time series
    """
    if data is None or len(data) == 0:
        return data

    cleaned = data.copy()

    # Remove outliers
    mean = cleaned.mean()
    std = cleaned.std()
    mask = np.abs(cleaned - mean) < (outlier_std * std)
    cleaned[~mask] = np.nan

    # Interpolate missing values
    cleaned = cleaned.interpolate(method="linear", limit_direction="both")

    # Apply smoothing filter
    if method == "median":
        cleaned = pd.Series(
            median_filter(cleaned.values, size=window_size),
            index=cleaned.index,
        )
    elif method == "gaussian":
        b, a = signal.butter(3, 0.1)
        cleaned = pd.Series(
            signal.filtfilt(b, a, cleaned.values),
            index=cleaned.index,
        )

    return cleaned


def resample_timeseries(
    timestamp: pd.Series,
    data: pd.Series,
    target_hz: float = 1.0,
    method: str = "linear",
) -> Tuple[pd.Series, pd.Series]:
    """
    Resample time series to uniform sampling rate.

    Parameters
    ----------
    timestamp : pd.Series
        Timestamps
    data : pd.Series
        Data values
    target_hz : float
        Target sampling rate in Hz
    method : str
        Interpolation method: "linear", "cubic"

    Returns
    -------
    Tuple[pd.Series, pd.Series]
        Resampled timestamp and data
    """
    if data is None or len(data) == 0:
        return timestamp, data

    # Convert to seconds since start
    t_seconds = (timestamp - timestamp.iloc[0]).dt.total_seconds().values

    # Create uniform time grid
    duration = t_seconds[-1] - t_seconds[0]
    n_samples = int(duration * target_hz)
    t_uniform = np.linspace(t_seconds[0], t_seconds[-1], n_samples)

    # Interpolate
    mask = ~np.isnan(data.values)
    if mask.sum() < 2:
        return timestamp, data

    if method == "linear":
        f = interpolate.interp1d(
            t_seconds[mask],
            data.values[mask],
            kind="linear",
            bounds_error=False,
            fill_value="extrapolate",
        )
    elif method == "cubic":
        f = interpolate.interp1d(
            t_seconds[mask],
            data.values[mask],
            kind="cubic",
            bounds_error=False,
            fill_value="extrapolate",
        )
    else:
        raise ValueError(f"Unknown interpolation method: {method}")

    data_uniform = f(t_uniform)

    # Convert back to timestamps
    timestamp_uniform = pd.to_datetime(t_uniform, unit="s", origin=timestamp.iloc[0])

    return pd.Series(timestamp_uniform), pd.Series(data_uniform)


def detect_sessions(
    activities: List[ActivityData],
    min_duration_minutes: float = 5.0,
    max_gap_minutes: float = 60.0,
) -> List[List[int]]:
    """
    Detect related sessions that should be analyzed together.

    Parameters
    ----------
    activities : List[ActivityData]
        List of activity sessions
    min_duration_minutes : float
        Minimum session duration
    max_gap_minutes : float
        Maximum gap between related sessions

    Returns
    -------
    List[List[int]]
        Groups of session indices
    """
    if not activities:
        return []

    # Extract session start times and durations
    sessions = []
    for i, activity in enumerate(activities):
        start = activity.timestamp.iloc[0]
        end = activity.timestamp.iloc[-1]
        duration = (end - start).total_seconds() / 60.0

        if duration >= min_duration_minutes:
            sessions.append((i, start, end, duration))

    # Sort by start time
    sessions.sort(key=lambda x: x[1])

    # Group sessions
    groups = []
    current_group = [sessions[0][0]]

    for i in range(1, len(sessions)):
        prev_end = sessions[i - 1][2]
        curr_start = sessions[i][1]
        gap = (curr_start - prev_end).total_seconds() / 60.0

        if gap <= max_gap_minutes:
            current_group.append(sessions[i][0])
        else:
            groups.append(current_group)
            current_group = [sessions[i][0]]

    if current_group:
        groups.append(current_group)

    return groups


def compute_derived_metrics(activity: ActivityData) -> dict:
    """
    Compute derived biomechanical metrics.

    Parameters
    ----------
    activity : ActivityData
        Activity session data

    Returns
    -------
    dict
        Derived metrics
    """
    metrics = {}

    # Step frequency (cadence in steps/min to Hz)
    if activity.cadence is not None:
        metrics["step_frequency_hz"] = activity.cadence / 60.0

    # Running economy (if speed and heart rate available)
    if activity.speed is not None and activity.heart_rate is not None:
        # Simplified running economy: HR / speed
        mask = (activity.speed > 0) & (activity.heart_rate > 0)
        if mask.any():
            metrics["running_economy"] = (
                activity.heart_rate[mask] / activity.speed[mask]
            ).median()

    # Vertical ratio (vertical oscillation / stride length)
    if activity.vertical_oscillation is not None and activity.stride_length is not None:
        mask = activity.stride_length > 0
        if mask.any():
            metrics["vertical_ratio"] = (
                activity.vertical_oscillation[mask] / activity.stride_length[mask]
            ).median()

    # Ground contact time ratio
    if activity.ground_contact_time is not None and activity.cadence is not None:
        # Duty factor: contact time / stride time
        stride_time = 60.0 / activity.cadence  # seconds
        mask = stride_time > 0
        if mask.any():
            metrics["duty_factor"] = (
                activity.ground_contact_time[mask] / stride_time[mask]
            ).median()

    # Heart rate zones (if HR available)
    if activity.heart_rate is not None:
        hr_max = 220 - 30  # Assume age 30 for reference
        metrics["hr_zone_1"] = (activity.heart_rate < 0.6 * hr_max).sum() / len(
            activity.heart_rate
        )
        metrics["hr_zone_2"] = (
            (activity.heart_rate >= 0.6 * hr_max) & (activity.heart_rate < 0.7 * hr_max)
        ).sum() / len(activity.heart_rate)
        metrics["hr_zone_3"] = (
            (activity.heart_rate >= 0.7 * hr_max) & (activity.heart_rate < 0.8 * hr_max)
        ).sum() / len(activity.heart_rate)
        metrics["hr_zone_4"] = (
            (activity.heart_rate >= 0.8 * hr_max) & (activity.heart_rate < 0.9 * hr_max)
        ).sum() / len(activity.heart_rate)
        metrics["hr_zone_5"] = (activity.heart_rate >= 0.9 * hr_max).sum() / len(
            activity.heart_rate
        )

    return metrics
