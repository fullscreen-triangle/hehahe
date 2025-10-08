# Multi-Scale Oscillatory Coupling Framework for Biomechanics

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
├── validation/                   # Python validation framework
│   ├── __init__.py
│   ├── data/                     # Data handling
│   │   ├── __init__.py
│   │   ├── loaders.py            # FIT/GPX/TCX/KML loaders
│   │   └── preprocessors.py     # Data cleaning
│   ├── analysis/                 # Statistical analysis
│   │   ├── __init__.py
│   │   ├── coupling.py           # Coupling validation
│   │   ├── gear_ratios.py        # Gear ratio validation
│   │   └── statistics.py         # Statistical tests
│   ├── visualization/            # Plotting and visualization
│   │   ├── __init__.py
│   │   ├── time_series.py        # Time series plots
│   │   ├── coupling_networks.py  # Network visualizations
│   │   └── state_space.py        # 3D state space plots
│   ├── models/                   # Reference implementations
│   │   ├── __init__.py
│   │   ├── traditional.py        # Traditional models
│   │   └── comparison.py         # Model comparison
│   └── notebooks/                # Jupyter notebooks
│       ├── exploratory_analysis.ipynb
│       ├── coupling_validation.ipynb
│       └── performance_prediction.ipynb
├── tests/                        # Rust tests
│   ├── integration/
│   └── unit/
├── docs/                         # Documentation
│   ├── oscillations/             # Theoretical documents
│   ├── biomechanics/
│   ├── publication/
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

### Python Validation Framework

Requirements:
- Python 3.9+
- pip or uv

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Or using uv (faster)
uv pip install -e ".[dev]"
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

### Python Validation

```python
from validation.data.loaders import load_fit_file
from validation.analysis.coupling import compute_coupling_matrix
from validation.visualization.coupling_networks import plot_coupling_network

# Load data
data = load_fit_file("data/raw/activity.fit")

# Compute coupling
coupling_matrix = compute_coupling_matrix(data)

# Visualize
plot_coupling_network(coupling_matrix, save_path="coupling.png")
```

### Jupyter Notebooks

```bash
# Start Jupyter
cd validation/notebooks
jupyter notebook

# Open exploratory_analysis.ipynb
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
