# Vitruvius — Python reference implementation

A runnable implementation of the `.vvs` language specified in
[`../docs/musculo-skeletal-syntax/`](../docs/musculo-skeletal-syntax/).

The production targets are TypeScript and Rust. This exists so experiments
can be run now, and so the specification's claims are **executable rather
than merely stated** — if the implementation drifts from the paper, a test
fails.

## Quick start

```bash
python run_all.py                        # run everything -> results/*.json
python validate_coherence.py             # 2432 checks -> coherence_validation.json
python -m vitruvius check  experiments/01_stroke_umn_lmn.vvs
python -m vitruvius run    experiments/03_nerve_block_phases.vvs
python -m vitruvius table  experiments/05_tremor_classification.vvs
python -m vitruvius observables          # the registry, with procedures
python -m pytest                         # 50 tests
```

```python
from vitruvius import run_file, summary_table

r = run_file("experiments/02_spinal_cord_injury.vvs")
print(summary_table(r, ["closure_index", "tonic_rate", "divergence_time"]))
```

## Pipeline

```
 .vvs ──► lexer ──► parser ──► checker ──► runtime ──► report
                                  │           │
                          static analyses   backend
                          (no numerics)    (numerics)
```

The checker computes the closure index, compartment consistency, stratum
containment, and floor positivity **without consulting a backend**, so a
model is checkable at the cost of parsing and the diagnostics do not change
when the backend does.

| module | role |
|---|---|
| `lexer.py` | tokens |
| `parser.py` | LL(1) recursive descent, no backtracking |
| `ast_nodes.py` | syntax tree, quantities with units |
| `circuit.py` | closure index, aperture reports, lesion operators |
| `checker.py` | the four typing rules, template expansion |
| `observables.py` | **the registry** — every observable and its procedure |
| `backend.py` | numerics; obligations B1–B4 |
| `estimation.py` | catalytic power, telescoping, the typed estimator |
| `antagonist.py` | coupled pairs sharing compartments |
| `coherence.py` | **coherence, identity/character, opacity, floor** |
| `runtime.py` | operational semantics, phases |
| `report.py` | formatting |
| `serialize.py` | JSON export with backend provenance |

## What the language enforces

**Severance and attenuation are different operators.** `without element(k)`
opens a circulation; `with k scaling 0.1` does not, at any positive factor.
A signal-and-gain formulation makes these the same limit; here the
difference is visible statically. `scaling 0` is rejected outright.

**An open circuit is a diagnostic, never an error.** It is the model of
deafferentation and simulating it is the point. The compiler names the
aperture and states the prediction; the program still runs.

**Charge carries the compartment it was computed against.** Mixing
capacitances is a type error, not a silent numerical mistake.

**Influence must traverse intervening strata.** A reflex-level element
reading supraspinal state is rejected. To model a shortcut deliberately,
`with noise across` declares it — so cross-stratum coupling is always a
declared lesion, never an oversight.

**An untyped `kappa` is unwritable.** Estimating an event's power from the
same data that measures the outcome is an algebraic identity that agrees
with itself on every possible dataset. Rule IV requires a declared event
type; `type_separation` reports whether that typing separates at all.

**Closure is not coherence.** A circuit offering two routes between the same
compartments can be perfectly closed while the routes disagree on the
traversal delay. `coherence_margin` asks whether the paths *agree*, not
merely whether they *match* — computed from declared delays alone, so a
lesion can be refused before it is committed. In the shipped programs three
circuits share a closure index *and* a loop latency (33.8 ms) and are
separated only by coherence.

**Severance repairs, attenuation does not.** Coherence reads delays; scaling
alters a gain. So `without element` removes a disagreeing route and restores
agreement, while `with … scaling` leaves the disagreement exactly where it
was — 120/120 in both directions.

**Every observable has a procedure.** `observables.py` is the registry;
a name absent from it is rejected. An observable without a defined
measurement is a promise, not a result.

## Extensions beyond the paper's core grammar

Implemented here because the experiments need them:

- **E1 templates** — `circuit template limb(...)` + `circuit x = limb(...)`.
  Pure sugar; expands before typechecking, so every proof carries over.
- **E3 reroute** — `reroute return(v) through p`. The *only* operator that
  carries a circuit from open back to **closed**, so it is what lets the
  language model repair (TMR, mirror therapy) rather than only ablation.
- **E4 phases** — `phase name { ... }`, optionally `from` a predecessor.
  Without it, all lesions apply before any observation and the temporal
  ordering of a nerve block is inexpressible.
- **E6 antagonists** — two circuits sharing compartments. This is Kirchhoff
  at a shared vertex within one medium, not composition of two models.

Deliberately **not** implemented: stochastic element failure (would make
the closure index a runtime property and cost backend-independence, while
buying nothing that phases do not give); bilateral declarations (an
observable, not syntax).

## Experiments

| file | derives |
|---|---|
| `01_stroke_umn_lmn.vvs` | spasticity vs flaccidity from closure alone |
| `02_spinal_cord_injury.vvs` | level-dependent SCI picture (templates) |
| `03_nerve_block_phases.vvs` | **coordination loss with intact strength** |
| `04_tmr_reroute.vvs` | amputation, TMR, mirror therapy as closure repair |
| `05_tremor_classification.vvs` | four tremor types, one anatomy |
| `06_cocontraction.vvs` | joint stiffness as an emergent property |
| `07_telescoping.py` | the degenerate estimator, demonstrated |
| `11_coherence_holonomy.vvs` | **closed circuits that disagree with themselves** |
| `12_identity_character.vvs` | **identity as a region; character as an invariant** |
| `08_myasthenia.vvs` | fatigable weakness as a phase trajectory |
| `09_rehabilitation.vvs` | why multi-component trial statistics are vacuous |
| `10_gait_asymmetry.vvs` | prosthetic compliance as capacitance |

## Results

`python run_all.py` writes to `results/`:

| file | contents |
|---|---|
| `<program>.json` | full record: circuits, closure, apertures, every observation |
| `index.json` | one row per program |
| `observations.json` / `.csv` | flat table, 308 observations |
| `coherence_validation.json` | 2432 checks over 8 claim groups |
| `07_telescoping.json` | the estimator demonstration |

Every measurement records what the backend was obliged to disclose — the
floor it used, the frequency band, the seed, the sample count — so a
results file is self-describing. Undefined values are `null` with
`"undefined": true`, distinguishable from absent ones.

Selected findings, all derived rather than encoded:

```
01  cortical lesion      supraspinal open  / segmental closed 15.7 Hz  -> spasticity
    anterior horn        supraspinal open  / segmental open,  no rhythm -> flaccidity

03  proprioceptive_loss  OPEN but force 420.0 N -- identical to baseline
    motor_block          OPEN and force   0.0 N

04  amputated OPEN -> tmr CLOSED (65.8 ms) / mirror CLOSED (35.8 ms)
    vs intact 49.8 ms: the repaired circulation is not the original one

08  myasthenic  closed, 63.0 N, rhythm intact     (attenuation)
    denervated  open,    0.0 N, rhythm undefined  (severance)

10  biological 474.5 N vs prosthetic 335.6 N -- ratio 0.707 = sqrt(0.9/1.8),
    from Q = sqrt(2CP) and a single declared capacitance difference
```

Two kinds of result. The **reproductions** (01, 02, 05) recover known
clinical taxonomy — the novelty is the derivation, since nothing in those
files encodes the conclusion. The **novel predictions** (03, 04, 06) state
things not currently available:

- proprioceptive block preserves force *exactly* while opening the loop
  (420 N in both baseline and `proprioceptive_loss`), so the framework
  predicts coordination failure rather than weakness;
- TMR restores closure through a path with different latency (65.8 ms vs
  49.8 ms), so the repaired circulation is not the original one;
- joint stiffness rises when reciprocal inhibition degrades, without any
  stiffness being commanded anywhere.

## Caveats

The backend is a **linearised reference implementation**, not a validated
biophysical simulator. Loop dynamics are a delayed multi-stratum system;
cross-bridge kinetics and musculotendon mechanics are not integrated. Its
job is to discharge observables so the language can be exercised, and the
absolute numbers should not be read as physiological predictions. The
closure analysis, by contrast, is exact and backend-independent.

Compartment values, delays, and strata are **declarations**. The type
system guarantees they are used consistently, not that they are true.
