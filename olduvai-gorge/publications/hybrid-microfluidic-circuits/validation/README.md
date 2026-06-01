# Sensation Mechanics Framework Validation

Complete Python implementation and validation of the theoretical framework presented in:

> "Sensation Mechanics in Closed Hybrid Microfluidic Circuits: Temporal Decay Kinetics, Receptor Diversity, and the Sufficiency Principle"

## Overview

This package provides:

1. **Charge Dynamics Simulation** - Exponential charge redistribution in closed circuits
2. **Sensation Mechanics** - Calculation of sensation rate as |dQ/dt|
3. **Receptor Models** - Population heterogeneity and diversity optimization
4. **Temperature Effects** - Arrhenius scaling of timescales
5. **Comprehensive Validation** - 11 major tests with JSON output

## Installation

```bash
# Requires Python 3.7+
pip install numpy scipy
```

## Quick Start

### Run Full Validation Suite

```python
from validation_suite import ValidationSuite

suite = ValidationSuite(output_dir='./my_results')
results = suite.run_all_tests()
suite.save_results(results, 'my_validation.json')
```

### Individual Tests

```python
from charge_dynamics import ClosedCircuit, create_circuit_config

# Create a simple circuit
config = create_circuit_config(n_compartments=3)
circuit = ClosedCircuit(config)

# Simulate response to charge perturbation
import numpy as np
Q0 = np.array([0.5, 0.3, 0.2])
result = circuit.simulate_perturbation(Q0, tau=0.5, t_max=5.0)

# Analyze sensation
print(f"Peak sensation: {np.max(result['sensation_rate']):.4f}")
print(f"Total sensation: {circuit.total_sensation(result['sensation_rate'], dt=0.01):.4f}")
```

## Test Suite Details

### 1. Charge Conservation Test
**Validates:** Axiom 1 - Total charge is conserved
- Creates closed circuit with 5 compartments
- Verifies Σq_i(t) = Q_total throughout simulation
- Expected: deviation < 1e-10

### 2. Exponential Decay Test
**Validates:** Theorem - Sensation Decay
- Tests P(t) = P_0 * e^(-t/τ)
- Fits exponential to simulated sensation rate
- Expected: R² > 0.95

### 3. Sensation Integral Test
**Validates:** Theorem - Sensation Integral is Finite
- Checks ∫P(t)dt = ΔQ
- Expected: relative error < 10%

### 4. Pain/Pleasure Categorization Test
**Validates:** Theorem - Sensation Category from Time Constant
- Tests categorization across τ range 10^-3 to 10 seconds
- Verifies sharp transition at critical τ_c
- Expected: distinct pain and pleasure categories

### 5. Receptor Diversity Advantage Test
**Validates:** Theorem - Diversity Maximizes Behavioral Responsiveness
- Compares monolithic vs logarithmic-spaced diverse populations
- Tests stimulus coverage across 100 different timescales
- Expected: diverse population covers >90% vs <20% for monolithic

### 6. Logarithmic Spacing Test
**Validates:** Theorem - Logarithmic Spacing Optimality
- Checks if 8-receptor population matches optimal spacing
- Computes τ_k = τ_min * r^k with r = (τ_max/τ_min)^(1/7)
- Expected: mean log-error < 0.1

### 7. Frequency Matching Test
**Validates:** Theorem - Frequency Matching for Cross-Circuit Influence
- Tests matching score: |Δτ|/(τ1+τ2)
- Verifies threshold Δf_thresh ≈ 0.1
- Expected: correct classification of matched vs unmatched pairs

### 8. Arrhenius Temperature Scaling Test
**Validates:** Theorem - Arrhenius Scaling of Timescale
- Fits τ(T) = τ_0 * e^(E_a/(R*T)) to synthetic data
- Extracts activation energy
- Expected: E_a fitted within 30% of expected 12 kJ/mol

### 9. Thermal Sensation Test
**Validates:** Temperature dependence of sensation
- Computes warm/cold sensation crossover (~33°C)
- Identifies pain threshold (~43°C)
- Compares TRPV1, TRPM8, TRPA1 sensitivities

### 10. Multi-Timescale Dynamics Test
**Validates:** Multi-exponential charge response
- Tests Q(t) = Q_∞ + Σ A_k e^(-t/τ_k)
- Verifies effective timescale computation
- Expected: τ_eff matches amplitude-weighted average

### 11. Receptor Adaptation Test
**Validates:** Replacement-Mediated Learning
- Simulates 5 adaptation steps
- Tracks how receptor population evolves toward stimulus statistics
- Verifies logarithmic spacing maintained

## Output Format

Results are saved as JSON with structure:

```json
{
  "timestamp": "2024-01-15T10:30:45.123456",
  "total_tests": 11,
  "tests_passed": 11,
  "tests": [
    {
      "test_name": "Charge Conservation",
      "passes": true,
      "n_compartments": 5,
      "Q_total": 1.0,
      "max_deviation": 1.23e-15
    },
    ...
  ]
}
```

## Key Classes

### ClosedCircuit
```python
config = CircuitConfig(
    n_compartments=3,
    Q_total=1.0,
    tau_compartments=np.array([0.1, 0.5, 1.0]),
    g_coupling=coupling_matrix
)
circuit = ClosedCircuit(config)
result = circuit.simulate_perturbation(Q0, tau=0.5, t_max=10.0)
```

### SensationCategorizer
```python
categorizer = SensationCategorizer(tau_critical=0.05)
category = categorizer.categorize(tau=0.02)  # Returns SensationCategory.PAIN
```

### ReceptorPopulation
```python
pop = ReceptorComparison.logarithmic_diverse_population(
    tau_min=0.01, tau_max=1.0, n_types=8,
    total_density=100.0, metabolic_cost=50.0
)
coverage = pop.stimulus_coverage(np.logspace(-3, 1, 50))
```

### TemperatureModel
```python
model = TemperatureModel(tau_ref=0.1, E_a=12000.0, T_ref=298.15)
tau_at_37C = model.timescale_at_temperature(310.15)
q10 = model.temperature_coefficient_Q10()
```

## Predicted Outcomes

All tests expect **PASS** with the following characteristics:

| Test | Expected Outcome |
|------|-----------------|
| Charge Conservation | max_deviation < 1e-10 |
| Exponential Decay | R² > 0.95 |
| Sensation Integral | relative_error < 10% |
| Pain/Pleasure | sharp transition at τ_c |
| Diversity Advantage | diverse > 5× monolithic coverage |
| Log Spacing | mean_log_error < 0.1 |
| Frequency Matching | 100% correct classification |
| Arrhenius | E_a error < 30% |
| Thermal | crossover ~33°C, pain ~43°C |
| Multi-Timescale | τ_eff matches amplitude average |
| Adaptation | receptor distribution evolves |

## Creating Custom Tests

```python
from charge_dynamics import ClosedCircuit
from sensation_mechanics import SensationCategorizer

# Custom circuit
config = CircuitConfig(...)
circuit = ClosedCircuit(config)

# Custom stimulus
Q0 = my_stimulus_vector
result = circuit.simulate_perturbation(Q0, tau=my_tau)

# Custom analysis
categorizer = SensationCategorizer(tau_critical=my_critical)
profile = categorizer.categorize_profile(
    result['time'], result['sensation_rate'],
    np.linalg.norm(Q0), my_tau
)
```

## Theoretical Validation

The validation suite tests these core theorems:

1. **Axiom 1 - Charge Conservation** (closed systems only)
2. **Axiom 2 - Finite Dissipation** (exponential decay)
3. **Axiom 3 - Finite Observational Resolution** (discrete time steps)
4. **Theorem 1 - Sensation = |dQ/dt|** (rate of charge redistribution)
5. **Theorem 2 - Sensation Decay** (exponential with τ)
6. **Theorem 3 - Sensation Integral Finite** (∫P(t)dt = ΔQ)
7. **Theorem 4 - Category from Time Constant** (pain vs pleasure)
8. **Theorem 5 - Diversity Advantage** (logarithmic spacing optimal)
9. **Theorem 6 - Frequency Matching** (|Δf|/f_avg < 0.1)
10. **Theorem 7 - Arrhenius Scaling** (τ(T) = τ_0 e^(E_a/RT))
11. **Theorem 8 - Replacement Learning** (adaptation through turnover)

## References

See parent directory for full paper:
`hybrid-microfluidic-circuit-dynamics.tex`

## License

Research framework. Citation appreciated.

## Author

Physics Research Group, 2024
