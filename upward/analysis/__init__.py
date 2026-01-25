"""
Statistical analysis and validation modules.
"""

from validation.analysis.coupling import (
    compute_coupling_matrix,
    compute_coupling_strength,
    compute_phase_locking_value,
)
from validation.analysis.frequency import compute_frequency_spectrum, detect_frequency_peaks
from validation.analysis.gear_ratios import compute_gear_ratio, validate_gear_ratios

__all__ = [
    "compute_coupling_matrix",
    "compute_coupling_strength",
    "compute_phase_locking_value",
    "compute_frequency_spectrum",
    "detect_frequency_peaks",
    "compute_gear_ratio",
    "validate_gear_ratios",
]

