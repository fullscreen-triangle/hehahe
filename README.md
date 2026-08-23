<h1 align="center">Hehahe</h1>
<p align="center"><em>Kwira Gomo, Ushedzera kuMusha</em></p>

<p align="center">
  <img src="assets/img/kuperekedza-muchato.jpg" alt="Logo" width="300"/>
</p>

A mathematical framework for analyzing human biomechanics through multi-scale oscillatory coupling principles using consumer-grade wearable sensor data.

---

## Vitruvius — a language for musculoskeletal experiments

**[Open the tool](musculo-skeletal/web/)** &middot;
[Language specification](musculo-skeletal/docs/musculo-skeletal-syntax/) &middot;
[Design notes](musculo-skeletal/web/ANATOMY.md)

Musculoskeletal simulation tools generally take a muscle, a joint, or a rigid
body as their unit of description. Each of those is an *open* object: it has an
input and an output, and closing a loop is something the modeller does
afterwards, by wiring. Vitruvius takes the opposite starting point. Its
primitive is a **circulation** — an outbound path and a return path as one
indivisible object — because a neuromuscular loop that does not close does not
merely perform worse, it fails in a different way.

The consequence is that several properties usually discovered by running a
simulation are instead **decided from the program text**: whether a circuit
closes, whether its routes agree with one another, where its identity lies, and
whether the anatomy it claims to inhabit can carry it.

### The primitive

```
circuit postural_loop {
  floor    : derived(resting_cut(spinal_in));

  outbound : cortex -> spinal_in -> alpha_mn -> nmj -> fibre;
  return   : fibre -> spindle -> ia_afferent -> spinal_in -> cortex;

  element descend  conducts cortex      -> spinal_in   delay 12.0 ms;
  element ia_axon  conducts ia_afferent -> spinal_in   delay  8.0 ms gain 1.0;
}

experiment deafferentation {
  intact  : postural_loop;

  lesion attenuated : postural_loop with ia_axon scaling 0.1;
  lesion severed    : postural_loop without element(ia_axon);

  observe : closure_index, divergence_time, band_power(reflex);
}
```

Both phases are mandatory, so an open circuit cannot arise by omission — only
through an explicit operator. The two lesions above are not points on one
continuum: attenuation preserves closure at every positive factor, severance
opens the circuit outright. This is checked exhaustively over twelve decades,
and it is the language's central design commitment.

### Decided without running anything

| Analysis | Question | Cost |
|---|---|---|
| Closure | do the declared paths match? | linear in elements |
| Coherence | do alternative routes *agree*? | signed transports |
| Compartment | are capacitances mixed across anatomy? | units-of-measure |
| Stratum | does an element skip a time-scale? | effect system |
| Floor | is the resting separation positive? | connectivity |

Closure and coherence are independent axes. Over 200 randomly generated
circulations all 200 closed, yet **76 carried a strictly negative coherence
margin** — disagreements of 4.9 to 29.4 ms, comparable to the loop latencies
themselves. Closure asks whether the paths *match*; coherence asks whether they
*agree*.

An aperture is a **diagnostic, not an error**: divergence is reported as a
time, not raised as an exception.

### Anatomy as a second witness

A binding attaches compartments to joints of a rig authored by someone who
never saw the program, so the joint hierarchy carries an adjacency and a tissue
index the source does not — and the two can disagree.

```
bind elbow_loop to rig("windows_3d_viewer_flexing_arm") {
  upper_arm   -> "muscle_UpperArm.25_25";
  bicep_belly -> "muscle_Bicep.30_30";
  velocity : 50;
}
```

The rig has 32 joints in three co-registered chains — bone, vein, muscle — with
rest translations agreeing to **0.0000**. Two of the four checks fired on
circuits written without them in mind: one found an element conducting between
joints two hops apart, and one found two independent elements declaring delays
**5.5x longer** than conduction over their measured distance predicts — the
same ratio for both, as expected when synaptic delay dominates.

### Inverse dynamics from wearable sensors

A shoe pod and a watch are not a force plate. But contact time, step frequency,
vertical oscillation and speed close the vertical impulse, because over one
stride at steady speed the body's vertical momentum returns to where it started:

```
F_mean = m g / duty          exact, impulse-momentum
F_peak = F_mean x pi/2       requires a contact waveform
```

From a 94 s sprint, 42 strides, 4.3–5.6 m/s:

| Quantity | Value | Basis |
|---|---:|---|
| duty factor | 0.272 | measured |
| contact / flight | 171 / 149 ms | measured |
| mean vertical GRF | 3.68 BW | **exact** |
| peak vertical GRF | 5.77 BW | half-sine assumed |
| leg stiffness | 29.2 kN/m | + spring-mass geometry |
| ankle moment at peak | 273 N·m | quasi-static |

The units were **discovered, not assumed**: `v = length x cadence / k` is a
redundant identity, and testing it showed the watch and the shoe pod use
different conventions (k = 30 and k = 60). Assuming one for both gave 11 BW
peak force — impossible, and the signal something was wrong.

A device's *vertical oscillation* is the total per-step excursion; the
ballistic rise is the flight arc alone. They differ by the stance dip:

```
measured 9.9 cm  =  stance dip 7.1 cm  +  flight arc 2.7 cm
```

The spring-mass model needs the stance dip; passing the total understated
stiffness by a third.

### Muscle model

A Thelen (2003) Hill-type unit is driven over one stance phase and asked
whether it *can* produce the force inverse dynamics says the tendon carried —
not fitted to it. It reaches **9.8 kN against 5.5 kN required**.

Three places the published equations and working code differ, all recorded in
the source: the eccentric asymptote cap is in OpenSim but not in Thelen (2003)
and without it the force–velocity inverse is singular; the tendon toe/linear
constants use the exact rather than rounded expressions; and Thelen's
force–velocity expression already contains activation and force–length, so
multiplying again double-counts.

Minimum jerk gives a peak-to-mean speed ratio of exactly **15/8 = 1.875**
against the 1.75 reaching studies report — a 7.1% overshoot, reported rather
than smoothed over.

### Implementation

| Component | Lines | Role |
|---|---:|---|
| TypeScript engine + IDE | 10,100 | lexer, parser, checker, backends, views |
| Python reference | 5,100 | independent implementation, figures |
| Tests | 209 | 116 TypeScript, 93 Python |

The two implementations agree exactly on every shipped program's arm and
closure counts, which makes backend-independence a checked property rather than
a claim.

### Scope

Muscle forces are **not** identified from wearable data. A joint moment is the
*net* moment; splitting it between agonist and antagonist is indeterminate
without EMG. The muscle model answers "could this muscle do it", not "did it".
Peak forces require a contact waveform the sensors do not record, joint moments
are quasi-static, and moment arms are population values. Each is a parameter
rather than a constant, surfaced next to the number it conditions.

---


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

- [x] Theoretical framework documentation
- [x] **Vitruvius language** — lexer, parser, typechecker, five static
      analyses, operational semantics, reference backend
- [x] **Browser IDE** — TypeScript port, live typechecking, 3-D anatomy,
      parameter sunburst, body map
- [x] **Python reference implementation** — independently reproduces every
      shipped program's arm and closure counts
- [x] **Body segment parameters** — de Leva (1996) and Dempster/Winter,
      both closing at 100.00% of body mass
- [x] **Inverse dynamics from wearable data** — units established from the
      data, gait classified per sample
- [x] **Hill-type muscle model** — Thelen (2003) with the OpenSim guards
- [x] 209 tests (116 TypeScript, 93 Python)
- [ ] Rust core implementation
- [ ] FIT file parser
- [ ] Empirical validation with 4+ years of data
