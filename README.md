<h1 align="center">Hehahe</h1>
<p align="center"><em>Kwira Gomo, Ushedzera kuMusha</em></p>

<p align="center">
  <img src="assets/img/kuperekedza-muchato.jpg" alt="Logo" width="300"/>
</p>

A mathematical framework for analyzing human biomechanics through multi-scale oscillatory coupling principles using consumer-grade wearable sensor data.

## Overview

This project implements the theoretical framework described in `docs/publication/consumer-grade-sensors-biomechanics.tex`, providing tools for:

- Multi-scale oscillatory coupling analysis (10 hierarchical scales)
- Gear ratio transformations for O(1) complexity navigation
- Tri-dimensional state space coordinate computation
- Surface compliance effect quantification
- Activity-sleep mirror coupling analysis
- Performance prediction from coupling dynamics
- Decoupling threshold detection

## Architecture

The project consists of two components:

### 1. Core Framework (Rust)
High-performance implementation of the mathematical framework for production use:
- FIT file parsing and time series extraction
- Multi-scale frequency decomposition
- Coupling strength computation
- Gear ratio analysis
- State space coordinate calculation
- Performance prediction models

### 2. Validation Framework (Python)
Research and validation tools for empirical analysis:
- Statistical validation of theoretical predictions
- Visualization and exploratory analysis
- Comparative studies with traditional models
- Data quality assessment
- Result verification against Rust implementation

## Project Structure

```
hehahe/
├── src/                          # Rust core framework
│   ├── lib.rs                    # Library root
│   ├── main.rs                   # CLI application
│   ├── parsers/                  # Data file parsers
│   │   ├── mod.rs
│   │   ├── fit.rs                # FIT file parser
│   │   ├── gpx.rs                # GPX parser
│   │   ├── tcx.rs                # TCX parser
│   │   └── kml.rs                # KML parser
│   ├── oscillatory/              # Oscillatory analysis
│   │   ├── mod.rs
│   │   ├── hierarchy.rs          # 10-scale hierarchy
│   │   ├── coupling.rs           # Coupling strength computation
│   │   ├── gear_ratio.rs         # Gear ratio transformations
│   │   └── frequency.rs          # Frequency domain analysis
│   ├── state_space/              # State coordinates
│   │   ├── mod.rs
│   │   ├── knowledge.rs          # Knowledge dimension
│   │   ├── temporal.rs           # Time dimension
│   │   └── entropy.rs            # Entropy dimension
│   ├── models/                   # Predictive models
│   │   ├── mod.rs
│   │   ├── performance.rs        # Sprint performance
│   │   ├── sleep.rs              # Sleep quality
│   │   ├── surface.rs            # Surface compliance
│   │   └── coupling_decay.rs     # Decoupling detection
│   └── utils/                    # Utilities
│       ├── mod.rs
│       ├── signal.rs             # Signal processing
│       └── math.rs               # Mathematical utilities
├── upward/                       # Python implementation (biomechanics)
│   ├── __init__.py
│   ├── muscle/                   # Oscillatory muscle modeling
│   │   ├── __init__.py
│   │   ├── muscle_model.py       # Extended Hill-type muscle model
│   │   ├── body_segmentation.py  # Body segments as coupled oscillators
│   │   └── README.md
│   ├── analysis/                 # Analysis tools
│   │   ├── __init__.py
│   │   ├── coupling.py           # Coupling strength analysis
│   │   ├── frequency.py          # Frequency domain analysis
│   │   └── gear_ratios.py        # Gear ratio computation
│   ├── extractor/                # Data extraction
│   │   ├── __init__.py
│   │   ├── fit_parser.py         # FIT file parsing
│   │   └── time_series.py        # Time series extraction
│   ├── stabilography/            # Postural analysis
│   │   └── postural_sway.py      # Oscillatory postural analysis
│   ├── examples/                 # Example scripts
│   │   ├── __init__.py
│   │   └── muscle_oscillatory_demo.py  # Comprehensive demo
│   ├── config.py
│   ├── requirements.txt
│   ├── setup.py
│   └── README.md
├── tests/                        # Rust tests
│   ├── integration/
│   └── unit/
├── docs/                         # Documentation
│   ├── oscillations/             # Theoretical documents
│   ├── biomechanics/
│   ├── biology/
│   ├── publication/
│   ├── notes/                    # Jupyter notebooks (reference)
│   └── api/                      # API documentation
├── data/                         # Data directory (gitignored)
│   ├── raw/                      # Raw FIT/GPX/TCX/KML files
│   ├── processed/                # Processed time series
│   └── results/                  # Analysis results
├── Cargo.toml                    # Rust dependencies
├── pyproject.toml                # Python project config
├── .gitignore
└── README.md
```

## Installation

### Rust Framework

Requirements:
- Rust 1.70+ (install via [rustup](https://rustup.rs/))

```bash
# Build the project
cargo build --release

# Run tests
cargo test

# Install CLI tool
cargo install --path .
```

### Python Framework (upward)

Requirements:
- Python 3.9+
- pip or uv

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
cd upward
pip install -r requirements.txt

# Or install in development mode
pip install -e .
```

## Usage

### Rust CLI

```bash
# Parse FIT file and compute coupling analysis
hehahe analyze --input data/raw/activity.fit --output data/processed/

# Batch process directory
hehahe batch --input-dir data/raw/ --output-dir data/processed/

# Predict sprint performance
hehahe predict-sprint --input data/processed/training_session.json

# Analyze sleep quality
hehahe analyze-sleep --input data/raw/sleep.fit
```

### Python - Oscillatory Muscle Modeling

```python
from upward.muscle import OscillatoryMuscleModel, LowerLimbModel

# Create muscle model with oscillatory coupling
muscle = OscillatoryMuscleModel()

# Define excitation and length functions
def excitation(t):
    return 1.0 if 0.5 <= t <= 2.0 else 0.01

def muscle_tendon_length(t):
    return 0.31  # Isometric contraction

# Simulate with oscillatory coupling
results = muscle.simulate_muscle_with_coupling(
    excitation, muscle_tendon_length,
    enable_coupling=True
)

# Analyze performance
metrics = muscle.compute_performance_metrics(results)
print(f"Peak force: {metrics['peak_force']:.2f} N")
print(f"Average coupling: {metrics['average_coupling']:.3f}")

# Body segment simulation
limb = LowerLimbModel(body_mass=70, height=1.75)
gait_results = limb.simulate_gait_cycle(stride_frequency=1.5)
```

### Comprehensive Demo

```bash
# Run comprehensive demo with all examples
cd upward/examples
python muscle_oscillatory_demo.py

# This generates multiple visualization plots demonstrating:
# - Classical vs oscillatory muscle models
# - Multi-scale frequency decomposition
# - Dynamic coupling during activation
# - Body segment coordination
# - Performance prediction from coupling
```

## Data Format

### FIT Files (Primary)

Expected fields:
- **Activity Sessions:**
  - Timestamp
  - Heart rate (bpm)
  - Cadence (steps/min)
  - Speed (m/s)
  - Altitude (m)
  - Temperature (°C)
  - Accelerometer data (if available)
  - Ground contact time (ms, if available)
  - Vertical oscillation (cm, if available)

- **Sleep Sessions:**
  - Timestamp
  - Sleep stage (awake/light/deep/REM)
  - Heart rate
  - Movement
  - Respiration rate (if available)

### Supported Formats

- **FIT**: Primary format (Garmin, Suunto, Polar, etc.)
- **GPX**: GPS tracks (position, elevation, time)
- **TCX**: Training Center XML (heart rate, cadence)
- **KML**: Google Earth format (position, time)

## Mathematical Framework

### 10-Scale Oscillatory Hierarchy

1. **Quantum Membrane** (10¹²-10¹⁵ Hz)
2. **Intracellular** (10³-10⁶ Hz)
3. **Cellular** (10⁻¹-10² Hz)
4. **Tissue** (10⁻²-10¹ Hz)
5. **Neural** (1-100 Hz)
6. **Neuromuscular** (0.01-20 Hz)
7. **Cardiovascular** (0.01-5 Hz)
8. **Locomotor** (0.5-3 Hz)
9. **Circadian** (10⁻⁵ Hz)
10. **Allometric** (10⁻⁸-10⁻⁵ Hz)

### Key Equations

**Coupling Strength:**
```
C_ij(t) = |1/T ∫₀ᵀ A_i(φ_j(t+τ)) e^(iφ_i(t+τ)) dτ|
```

**Gear Ratio:**
```
R_{i→j} = ω_i / ω_j
```

**State Coordinates:**
```
s = (s_knowledge, s_time, s_entropy)
```

**Decoupling Threshold:**
```
C_critical = 1/(N-1) √(Σω_k² / Σω_k)
```

## Performance

### Rust Framework
- FIT file parsing: ~2ms per file
- Coupling computation: ~50ms per session
- Full analysis pipeline: ~100ms per session
- Memory usage: <10MB per session

### Python Validation
- Statistical validation: ~500ms per comparison
- Visualization generation: ~2s per plot
- Batch analysis: ~1s per session

## Configuration

### Rust (`Cargo.toml`)

```toml
[profile.release]
opt-level = 3
lto = true
codegen-units = 1
```

### Python (`pyproject.toml`)

Configure analysis parameters in `validation/config.py`:
- Frequency band definitions
- Coupling thresholds
- Surface compliance factors
- Sleep stage parameters

## Testing

### Rust
```bash
# Unit tests
cargo test

# Integration tests
cargo test --test '*'

# Benchmarks
cargo bench
```

### Python
```bash
# Unit tests
pytest validation/tests/

# With coverage
pytest --cov=validation validation/tests/

# Specific test
pytest validation/tests/test_coupling.py
```

## Data Privacy

All data processing occurs locally. No data is transmitted externally. Ensure compliance with data protection regulations when handling personal health data.

## Contributing

This is a research project. Contributions should:
1. Maintain mathematical rigor
2. Include comprehensive tests
3. Document theoretical basis
4. Provide validation results

## Citation

If you use this framework in research, please cite:

```bibtex
@article{sachikonye2024oscillatory,
  title={Multi-Scale Oscillatory Coupling Analysis for Human Biomechanics Using Consumer-Grade Wearable Sensors},
  author={Sachikonye, Kundai Farai},
  journal={In preparation},
  year={2024}
}
```

## License

[To be determined]

## References

See `docs/publication/consumer-grade-sensors-biomechanics.tex` for complete theoretical foundation and references.

## Contact

Kundai Farai Sachikonye
kundai.sachikonye@tum.de

## Status

**Current Status:** Initial implementation phase

- [x] Theoretical framework documentation
- [ ] Rust core implementation
- [ ] Python validation framework
- [ ] FIT file parser
- [ ] Coupling analysis algorithms
- [ ] State space computation
- [ ] Performance prediction models
- [ ] Empirical validation with 4+ years of data
- [ ] Documentation and examples
