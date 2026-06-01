"""
Sensation Mechanics Framework Validation Package

Complete implementation of theoretical predictions from "Sensation Mechanics
in Closed Hybrid Microfluidic Circuits".

Modules:
--------
- charge_dynamics: Core charge redistribution simulation
- sensation_mechanics: Sensation rate calculation and categorization
- receptor_models: Receptor populations and diversity analysis
- temperature_effects: Temperature-dependent kinetics
- validation_suite: Comprehensive test suite with JSON export

Quick Start:
-----------
from validation_suite import ValidationSuite

suite = ValidationSuite()
results = suite.run_all_tests()
suite.save_results(results)

This will execute all validation tests and save results to JSON.
"""

__version__ = '1.0.0'
__author__ = 'Physics Research Group'

from .charge_dynamics import (
    CircuitConfig,
    ClosedCircuit,
    MultiTimescaleCircuit,
    validate_charge_conservation,
    validate_exponential_decay
)

from .sensation_mechanics import (
    SensationCategorizer,
    SensationCategory,
    SensationProfile,
    MultimodalSensation,
    SensationQuality,
    validate_sensation_conservation,
    validate_pain_pleasure_transition
)

from .receptor_models import (
    ReceptorType,
    ReceptorPopulation,
    ReceptorComparison,
    ReceptorAdaptation
)

from .temperature_effects import (
    TemperatureModel,
    ThermalSensationAnalysis,
    validate_arrhenius_scaling
)

from .validation_suite import ValidationSuite

__all__ = [
    'CircuitConfig',
    'ClosedCircuit',
    'MultiTimescaleCircuit',
    'SensationCategorizer',
    'SensationCategory',
    'ReceptorType',
    'ReceptorPopulation',
    'TemperatureModel',
    'ValidationSuite',
]
