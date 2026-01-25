"""
Configuration parameters for validation framework.
"""

from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np


@dataclass
class FrequencyBands:
    """Frequency bands for each hierarchical scale."""

    quantum_membrane: Tuple[float, float] = (1e12, 1e15)  # Hz
    intracellular: Tuple[float, float] = (1e3, 1e6)  # Hz
    cellular: Tuple[float, float] = (0.1, 100)  # Hz
    tissue: Tuple[float, float] = (0.01, 10)  # Hz
    neural: Tuple[float, float] = (1, 100)  # Hz
    neuromuscular: Tuple[float, float] = (0.01, 20)  # Hz
    cardiovascular: Tuple[float, float] = (0.01, 5)  # Hz
    locomotor: Tuple[float, float] = (0.5, 3)  # Hz
    circadian: Tuple[float, float] = (1e-5, 1e-4)  # Hz
    allometric: Tuple[float, float] = (1e-8, 1e-5)  # Hz

    def get_measurable_bands(self) -> Dict[str, Tuple[float, float]]:
        """Return only scales measurable by consumer sensors."""
        return {
            "neural": self.neural,
            "neuromuscular": self.neuromuscular,
            "cardiovascular": self.cardiovascular,
            "locomotor": self.locomotor,
            "circadian": self.circadian,
        }


@dataclass
class CouplingParameters:
    """Parameters for coupling analysis."""

    # Coupling strength thresholds
    strong_coupling: float = 0.8
    moderate_coupling: float = 0.6
    weak_coupling: float = 0.4
    critical_coupling: float = 0.42

    # Window parameters
    coupling_window_seconds: float = 60.0
    phase_locking_window_seconds: float = 30.0

    # Gear ratio tolerances
    gear_ratio_tolerance: float = 0.15  # 15% tolerance


@dataclass
class SurfaceParameters:
    """Surface compliance parameters."""

    # Reference values (rigid surface)
    k_ref: float = 30000.0  # N/m
    c_ref: float = 500.0  # Ns/m

    # Surface categories
    surface_stiffness: Dict[str, float] = None
    surface_damping: Dict[str, float] = None

    def __post_init__(self):
        if self.surface_stiffness is None:
            self.surface_stiffness = {
                "track": 28000.0,
                "asphalt": 32000.0,
                "concrete": 35000.0,
                "treadmill": 15000.0,
                "grass": 8000.0,
                "sand": 3000.0,
            }
        if self.surface_damping is None:
            self.surface_damping = {
                "track": 600.0,
                "asphalt": 450.0,
                "concrete": 400.0,
                "treadmill": 800.0,
                "grass": 1200.0,
                "sand": 2000.0,
            }

    def compute_compliance_factor(self, surface_type: str) -> float:
        """Compute compliance factor for given surface."""
        k_surface = self.surface_stiffness.get(surface_type, self.k_ref)
        c_surface = self.surface_damping.get(surface_type, self.c_ref)

        return ((self.k_ref - k_surface) / self.k_ref) * (c_surface / self.c_ref)


@dataclass
class SleepParameters:
    """Sleep analysis parameters."""

    # Error accumulation
    alpha: float = 0.1  # error units per MET-minute
    met_baseline: float = 1.0  # MET

    # Cleanup rates
    beta_deep: float = 2.5  # cleanup rate for deep sleep
    beta_rem: float = 2.0  # cleanup rate for REM sleep
    beta_light: float = 0.5  # cleanup rate for light sleep

    # Mirror coupling
    optimal_mirror_ratio: float = 1.0
    acceptable_deviation: float = 0.35

    # Sleep stage durations (expected proportions)
    expected_deep_proportion: float = 0.20
    expected_rem_proportion: float = 0.25
    expected_light_proportion: float = 0.50
    expected_wake_proportion: float = 0.05


@dataclass
class PerformanceParameters:
    """Performance prediction parameters."""

    # Sprint performance
    t_optimal_100m: float = 9.58  # World record
    sprint_coupling_k1: float = 2.5
    sprint_coupling_k2: float = 15.0

    # Decoupling parameters
    tau_elite: float = 12.3  # seconds
    tau_elite_std: float = 1.8
    c_initial_elite: float = 0.89
    c_initial_elite_std: float = 0.04

    # Performance categories
    elite_threshold: float = 10.0  # seconds for 100m
    sub_elite_threshold: float = 10.5
    competitive_threshold: float = 11.0


# Global configuration instance
class Config:
    """Global configuration."""

    def __init__(self):
        self.frequency_bands = FrequencyBands()
        self.coupling = CouplingParameters()
        self.surface = SurfaceParameters()
        self.sleep = SleepParameters()
        self.performance = PerformanceParameters()

    def to_dict(self) -> dict:
        """Export configuration as dictionary."""
        return {
            "frequency_bands": self.frequency_bands.__dict__,
            "coupling": self.coupling.__dict__,
            "surface": {
                "k_ref": self.surface.k_ref,
                "c_ref": self.surface.c_ref,
                "stiffness": self.surface.surface_stiffness,
                "damping": self.surface.surface_damping,
            },
            "sleep": self.sleep.__dict__,
            "performance": self.performance.__dict__,
        }


# Create default configuration
config = Config()

