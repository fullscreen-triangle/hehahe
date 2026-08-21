# Anatomical binding

## The problem with "load a GLB and animate it"

The obvious way to add 3D models to the Vitruvius IDE is the one both
prototype snippets describe: load a mesh, look up a compartment's name in a
map, and drive that mesh's scale from an observable. `vitruvian-model.jsx`
says so explicitly — *replace `buildProceduralAnatomy()` with a `GLTFLoader`
call and point each entry's `meshName` at the corresponding GLB group name.*

That architecture makes the model a **decoration**. The animation is
`scale = 1 + amp·sin(2π·rate·t)`: a hand-authored throb whose parameters are
named after observables. The geometry cannot disagree with the circuit,
because nothing about the geometry is ever consulted. A viewer that pulses a
mesh at `tonic_rate` shows you a number the results table already gave you,
rendered less precisely.

Worse, it is unfalsifiable in the specific sense this project cares about. The
manuscript's claims are of the form *closure is decidable from declared paths*
and *attenuation cannot reach severance*. A decorative viewer restates them.
It cannot check them.

## What the models actually contain

Inspection of the three GLBs (`scripts/inspect-glb.mjs`) found one fact that
determines the design:

```
windows_3d_viewer_flexing_arm.glb
  32 joints in THREE co-registered chains:
    bone_Clevicle   vein_Clevicle   muscle_Clevicle
    bone_UpperArm   vein_UpperArm   muscle_UpperArm
    bone_LowerArm   vein_LowerArm   muscle_LowerArm
    bone_Bicep      vein_Bicep      muscle_Bicep
    bone_Tricep     vein_Tricep     muscle_Tricep
    ... 10 segments total

  max rest-translation difference across the three chains: 0.0000
```

Three tissue layers, identical topology, exactly co-registered. That is not a
modelling coincidence — it is a **compartment-indexed structure already in the
file**. The rig distinguishes *the same anatomical segment considered as bone,
as vasculature, and as muscle*, which is precisely what Rule I
(compartment consistency) says you may not silently mix.

It also contains a ready-made antagonist pair (`bone_Bicep` / `bone_Tricep`)
under a shared parent (`bone_UpperArm`) — the exact structure the
`antagonist` construct declares.

The other two models:

| Model | Structure | Use |
|---|---|---|
| `xbot_multiple_animations.glb` | 68 Mixamo joints, clips `Walking` 0.87 s, `Running` 0.63 s, `Jump`, `Idle` | periodic gait **clock** |
| `anatomy_study.glb` | 6 meshes named `Object_0…5`, **no skin, no animation** | not bindable by name; backdrop only |

## The design: the rig is a second witness

A binding declares which joint each compartment inhabits:

```
bind postural_loop to rig("flexing_arm") {
  alpha_mn -> muscle_UpperArm;
  nmj      -> muscle_Bicep;
  fibre    -> muscle_Bicep;
  spindle  -> muscle_Front_LowerArm;
}
```

The joint hierarchy is a graph with its own adjacency, authored by someone who
never saw this program. So a binding can be **checked**, and the checks can
fail in ways the circuit alone cannot produce:

- **B1 Adjacency.** If `outbound: a -> b` but the joints bound to `a` and `b`
  are not adjacent in the skeleton, the declared conduction path crosses
  anatomy it never mentions. Reported as a *bind diagnostic*, with the
  intervening joints named.

  *This fired on a circuit written without it in mind:* `ec_coup` conducts
  `bicep_belly → lower_arm`, and the rig reports those joints two hops apart
  via `muscle_UpperArm` — anatomy the program never names.

- **B2 Tissue consistency.** The rig's three chains are a compartment index in
  the sense of Rule I. An element conducting `muscle_Bicep -> vein_LowerArm`
  crosses tissue compartments; that is either a real transduction step or a
  binding error, and the analysis says which one it cannot tell.

- **B3 Reachability.** The transitive closure of the bound joints must contain
  the circulation. A closed circuit whose binding is disconnected in the
  skeleton is a contradiction between two independent descriptions.

- **B4 Span.** Anatomical path length between bound joints, from rest
  transforms, gives a *conduction distance*. With a declared conduction
  velocity this predicts a delay — which can be compared against the delay the
  program declares. Disagreement is informative in both directions.

  *Measured, at 50 m/s:* `to_belly` 2.7 cm predicts 0.5 ms against 3.0 ms
  declared; `ec_coup` 7.1 cm predicts 1.4 ms against 8.0 ms. Both ratios are
  **0.18** — identical across two independent elements. Constant ratio means
  the declared delays carry a fixed component conduction distance does not
  explain, which is physiologically what one expects: synaptic and
  excitation-contraction delay does not scale with axon length. The rig
  recovered that without being told it.

None of these can be derived from the `.vvs` source. They require the rig.
That is the point: **the anatomy is an independent source of falsification**,
not an illustration of conclusions already reached.

## Driving the rig from integrated state

Joint rotation is driven by the arm's actual trace (`Backend.simulate`), not
by a summary statistic. The angular gain is **calibrated per arm** so that the
arm's own resting excursion occupies 10% of the joint's range; everything
above that is the trajectory growing. A fixed gain would decide the question
by fiat — large enough and every arm leaves range, small enough and none
does.

The joint limit itself comes from the rig's rest pose (longer segments get
tighter angular limits), so it is a quantity the program cannot influence.

### What this actually found

Measured on `13_anatomical_binding.vvs`, 20 s, dt = 2 ms:

| arm | resting peak | late peak | growth |
|---|---|---|---|
| intact | 5.86e-2 | 6.75e-2 | **1.15×** |
| severed | 1.21e+1 | 5.00e+1 | **4.14×** |

The separation is clean and in the predicted direction: the closed circuit
stays at its resting scale, the open one grows several-fold. But **neither
crosses the 10× threshold** at which the joint would leave range — the open
arm saturates the integrator at 50.0 first.

So the anatomical witness **does not fire**, while the engine **does** report
`divergence_time = 3.72 s`. The viewer states both, and does not reconcile
them. That disagreement is the whole reason for having a second witness: a
test tuned until it agreed with the engine would be reporting the engine.

The panel therefore always shows the growth ratio and how close it came,
never only a fired/not-fired flag — a test that speaks only when it triggers
hides its own margin.

### One design consequence

The animation clock advances in **wall-clock** seconds, clamped at 0.25 s per
step, and is deliberately *not* tied to frame delivery. On a software
rasteriser (headless CI, any machine without a GPU) this rig renders at ~6 fps;
tying the clock to frames made the same program report different divergence
times on different hardware, which is exactly the backend-dependence the
language exists to avoid. Verified: 0.994× real time at 6 fps.

## The gait clock

`Walking` (0.87 s) and `Running` (0.63 s) are periodic clips with known phase.
Program 10 declares a biological and a prosthetic hip at **identical latency**
(72.8 ms) and **different force** (474.5 N vs 335.6 N, ratio 0.707107 =
√(0.9/1.8)).

Binding the two circulations to `LeftUpLeg` and `RightUpLeg` and driving the
clip at its own period turns that ratio into a **visible limp** whose
magnitude is √(C₁/C₂) — a quantity from the specification, not a tuned
animation parameter. Running the identical binding under `Running` asks
whether the asymmetry scales with cadence, which the static panels cannot
answer.

## What the tissue clips are, and are not

`artery_view`, `muscle_view`, `bone_view` are layer *reveals*, not motions.
They map naturally onto the tissue chains and are used as visibility control.

They are **not** strata. Artery/muscle/bone is a tissue axis;
reflex/spinal/supraspinal is a latency axis. Conflating them would be
convenient and wrong, and the viewer does not do it.

## Cost

31 MB across three models. Each is lazy-loaded on first use of the view that
needs it, and cached. `anatomy_study.glb` (16 MB, no bindable structure) is an
optional backdrop, off by default, behind an explicit toggle that names its
size.

`GLTFLoader` and `OrbitControls` come from `three/examples/jsm/` in the
already-installed `three@0.169.0`. No new dependency.

---

# Posture: reading a program out of a pose stream

The binding work above runs one direction: a program is written, a rig
illustrates and checks it. The Posture view runs the other direction. A rig's
animation clip is sampled as a body-sway record, decomposed into rambling and
trembling, accounted for in charge, and turned back into Vitruvius source that
is loaded into the editor and can be run against the record it came from.

## Why a clip is a sway record

An animation clip is joint transforms sampled at a fixed rate. That is the
same class of signal a waist IMU or a force plate produces, so the IEP
decomposition applies without reinterpretation: low-pass at 0.4 Hz gives
rambling, the residual is trembling, and the two sum back to the input
exactly (checked, not assumed -- `reconstructionError` is reported).

## What these clips cannot support, and why it is said out loud

The decomposition returns numbers whatever you feed it. Two limits are
computed per record and shown *before* any result:

| | value | consequence |
|---|---|---|
| sample rate | 30 Hz | Nyquist 15 Hz. Physiological tremor above ~5 Hz is invisible and would alias into the trembling band. |
| `Idle` duration | 1.967 s | **shorter than one rambling period.** Resolving below 0.4 Hz at 3 cycles needs 7.5 s. |

So on a single pass of `Idle` the panel shows rambling as `—`, not a number,
and the generated source omits the supraspinal compartment entirely with a
comment saying why. A circuit whose slowest stratum was invented by a filter
would be worse than no circuit.

## The loop artefact — the failure this design had to catch

Reaching the rambling band means looping a 2-second clip ~31 times. Looping
injects a periodicity at 1/clipDuration that was never in the subject, and for
`Idle` that lands at **0.508 Hz — inside the trembling band**, where it is
indistinguishable from a finding.

Measured, on the real clip:

| record | dominant trembling peak | verdict |
|---|---|---|
| `Idle`, single pass (2 s) | **1.758 Hz** | genuine |
| `Idle`, looped to 62 s | **0.502 Hz** | **artefact** — 1.4% from the loop rate |

The analysis compares the peak against the known repeat frequency and, when
they coincide, refuses to derive a loop delay from it. The generated `.vvs`
says so in its own header rather than emitting a number that looks measured:

```
-- ! Dominant trembling peak is 0.502 Hz and the record was looped at
-- ! 0.508 Hz. These coincide to within 1.4%, so the peak is the LOOP,
-- ! not the subject.
...
-- Loop delay NOT derived from the spectrum: the dominant peak coincides
-- with the looping frequency, so it is an artefact of how the record was
-- assembled. A default reflex-scale delay is used instead and must not be
-- read as measured.
```

This was found by running the pipeline on the real file, not by anticipating
it. The first looped run reported 0.502 Hz as a finding.

## Charge

Power is the kinetic cost of the motion actually present -- mean squared
velocity times an effective moving mass. That is crude, and labelled crude:
there is no force plate here. What it does do is scale with the movement
rather than being assumed, so a still record and a restless one produce
genuinely different programs.

The conversion is exact and compartment-indexed:

```
Q = sqrt(2 C P),   C_brain 1.0 mF | C_motor 141 uF | C_perception 500 uF
```

Verified against the published component rates: thought 133.5 mC/s at 8.92 W,
motor 290.9 mC/s at 300 W, and the parameter-free dream/thought ratio
sqrt(0.95) = 0.9747 which holds at *any* power level (tested at two).

The generator inverts its own map -- `C = Q^2/(2P)` -- so the capacitance
written into the source is the one the measured charge implies, and a test
asserts it recovers `C_motor` to 10 decimal places.

## Sleep activity

The same pose stream, read for position changes rather than spectra:
repositions, arousals, per-hour rate, longest undisturbed stretch, wake
fraction. A reposition requires a *sustained* displacement, not a transient --
without that a single noisy sample counts as a roll and the rate inflates by
an order of magnitude. Thresholds are multiples of the record's own
quiet-period spread, so they carry no rig-unit assumption.

## Round trip

Generate loads the program into the editor and switches to Circuit, so the
record's own claim can be run immediately. Verified in-browser end to end:
generated source checks with **0 errors**, and the generated experiment
carries a `severed` lesion so the closure claim can be tested against the
body the record came from.

## One bug worth recording

`GLTFLoader` **strips** characters illegal in an animation property path
rather than substituting them, so the GLB's `mixamorig:Hips_01` becomes
`mixamorigHips_01` in the loaded scene while the manifest -- read straight out
of the container -- keeps the colon. A direct `getObjectByName` fails on
exactly the rigs that need it, and fails quietly enough to look like an empty
signal. `findJoint` compares names with separators removed on both sides, and
a genuine miss now names the nearest candidates.

`sampleClip` also clones the scene before driving a mixer over it: the loaded
scene is cached and shared with the 3-D views, and mutating it mid-render
corrupts whatever else is drawing.

---

# Body segment parameters and the sunburst

## The setup script

`scripts/set-body-parameters.mjs` expands a subject's mass and stature into
per-segment masses, lengths, centres of mass, and moments of inertia. This is
the step everything downstream reads: instead of a hard-coded "effective
moving mass" the charge accounting can take a real segment mass for the region
it is measuring.

```
node scripts/set-body-parameters.mjs --mass 83 --stature 1.85 --sex male --write
node scripts/set-body-parameters.mjs --model dempster --length thigh=0.44
```

Tables live in `src/lang/bsp.ts` with their citations; the script only drives
them, so the app and the CLI cannot drift apart.

## Two models, never mixed

| | de Leva (1996) | Dempster (1955) / Winter (2009) |
|---|---|---|
| sample | 100 young men, 15 young women, gamma-ray scan | 8 elderly male cadavers |
| female data | yes, separate table | **none** |
| thigh | hip joint centre → knee joint centre | greater trochanter → knee |
| trunk | suprasternale → midhip | trochanter → glenohumeral |

de Leva's thigh is ~42% heavier than Dempster's and his trunk ~15% lighter,
because the segments are *defined differently*. Mixing rows produces a body
whose segments do not tile, so `segmentParameters(model, sex)` takes the model
explicitly and **throws** for Dempster+female rather than substituting male
cadaver parameters for a woman. The UI surfaces that refusal.

Both models close at **100.00%** of body mass — asserted in tests, because a
fractional table that does not sum to the whole body is wrong in a way no
single row reveals.

## Three transcription hazards, all now guarded by tests

**The BMClab CSVs mislabel de Leva's shank.** They name the KJC–AJC row
`Shank` and the KJC–LMAL row `Shank 2`, whereas de Leva's *primary* shank is
KJC–LMAL. Indexing that CSV by `"Shank"` silently returns the **alternative**
parameters. The tables here follow de Leva's own convention.

**Winter's `head+neck` row violates the parallel-axis identity.** For every
limb segment `Rg_prox² = Rg_cm² + CM_prox²` holds to <0.0005 — which makes it
a transcription check on the whole table at once. `head+neck` is marked "PC"
(calculated) and its radii are referenced to a different length, so it fails by
1.23. Both facts are asserted: the identity for limbs, *and* the violation for
head+neck, so a future "fix" that made it conform would fail the test.

**A trunk-length error I made and caught.** Winter Figure 4.1 tabulates a
0.520H "shoulder to hip" span, and I first used it as Dempster's trunk length.
But Dempster's trunk is trochanter→glenohumeral, which from the figure's own
heights is 0.818H − 0.720H = **0.098H**. The wrong value inflated trunk moment
of inertia by ~28×. Derived fractions are now checked against the figure's
heights in a test, and `STATURE_FRACTION_SOURCE` records which values are
quoted and which are differences.

Body *breadths* (shoulder 0.259H, chest 0.174H, hip 0.191H) are kept in a
separate `BREADTH_FRACTION` map, with a test asserting no breadth leaks into
the length law — a breadth is measured across the body, not along a segment
axis.

## The reference figure

`public/anatomy` is a jQuery template painting regions over two PNG
photographs (600 KB). `scripts/extract-anatomy.mjs` pulls out the path
geometry alone — **45 regions, 26 KB, no jQuery, no images** — so the figure
renders at any size with fill under our control.

It is a lookup, not an illustration. A result carrying a region paints it; a
result carrying none paints nothing, which correctly says the quantity is not
localised. `resolveRegion` maps caller names (`soleus`, `quadriceps`, `hip`)
onto template names, and handles `ana18`'s `elbow` — the template's own typo
for `left-elbow`, left unrenamed so the extract script keeps agreeing with its
source.

Colour is a monotone-luminance ramp, deliberately not a rainbow: a rainbow
invents boundaries where the data has none, which for a "how much, and where"
diagram would fabricate structure.

## The sunburst

`Parameters` shows the whole parameter tree as one ring — anthropometry,
segment inertia, charge, and run results — with the figure at the centre.
Hovering any arc reads out its value, unit, and derivation, and lights the
body where that quantity lives. Clicking zooms; a breadcrumb makes it
reversible.

Arc angle is **leaf count, not value**, so a parameter with value 0 still
occupies its share of the ring rather than vanishing. The centre figure is
never covered — it sits in the hole, and that is the whole point.

The reference figure also appears **top right of every results page**
(Results, Compare, Aperture, Spectra, State space) showing segment mass, so
any result can be located on the body without leaving the page. It is
deliberately absent from Circuit, Anatomy, and Posture: those are already
anatomical, and a second small body would compete rather than orient.

### One React bug worth recording

`Sunburst`'s draw effect originally listed `onSelect` in its dependencies. An
inline callback is a new function every render, so the effect tore down and
rebound the ring on every hover — destroying the very handler that had just
set the hover state. The callback is now held in a ref and the effect no
longer depends on its identity.

---

# Wearable running dataset: inverse dynamics and muscle simulation

`python analyse_wearable.py` reads the six session files in
`web/public/angle`, establishes what each can support, runs the inverse
dynamics, drives a Hill muscle model over one stance phase, and writes
`results/wearable_analysis.json` plus four panels.

## The units were not assumed — they were discovered, and they differ

`v = length x cadence / k` is a redundant identity: speed is recorded
independently of stride length and cadence, so testing the identity decides
what the channels mean. That mattered here, because **the two devices use
different conventions**:

| file | k | length is | cadence counts | residual |
|---|---|---|---|---|
| `sprintActigraphy` (watch) | **30** | one step | strides/min | 2.6% |
| `underarmour`, `workout2/4` (shoe pod) | **60** | full stride | strides/min | 0.6% |

Assuming the Garmin convention for both gave a peak GRF of **11 body
weights** and a flight time of 0.43 s — physiologically impossible, and the
signal that something was wrong. With the conventions resolved from the data
the same sprint gives **5.8 BW** and 0.149 s.

Rejected conventions are recorded with their residuals (the steps/min reading
misses by 50%), so the choice is auditable rather than asserted.

## Gait is classified per sample, not on an average

`underarmour` has a median duty factor of **1.02** — right at the
walk/run boundary, which describes neither mode. Counting per sample shows
**67 of 199 steps have a flight phase**: it is an interval session. It is
labelled `mixed`, and the flightless samples are excluded from the running
analysis rather than the whole session being accepted or rejected.

## What is exact, and what is assumed

The mean vertical GRF is **exact**, not fitted: over one stride at steady
speed the ground must return exactly the vertical momentum gravity removes,
so `F_mean = mg / duty`. Everything past that needs an assumption, and each
is named where it is used:

- **peak GRF** needs a contact waveform (half-sine, mean-to-peak π/2)
- **joint moments** are quasi-static — segment angular acceleration neglected
- **the Achilles moment arm** is the dominant uncertainty converting an ankle
  moment into a tendon force, so it is a parameter

## A decomposition the data forced

Panel 2D began as "measured oscillation vs ballistic prediction" and showed
every point 3.6× off the identity line. That is not an error — a device's
*vertical oscillation* is the **total** per-step excursion, while the
ballistic rise is the **flight arc alone**. They differ by the stance dip:

```
measured 9.9 cm  =  stance dip 7.1 cm  +  flight arc 2.7 cm
```

McMahon & Cheng's leg-stiffness formula needs the **stance dip**, and I was
passing the total. Fixing it moved leg stiffness from 24.9 to **29.2 kN/m**
and vertical stiffness from 48.2 to **66.2 kN/m**, both now squarely in the
published sprinting range. The panel now stacks the two parts, and a test
asserts the stance dip exceeds the flight arc at sprint pace.

## Sprint results (83 kg, 1.85 m, 42 strides, 4.3–5.6 m/s)

| | |
|---|---|
| duty factor | 0.272 |
| contact / flight | 171 / 149 ms |
| mean vertical GRF | 3.68 BW *(exact)* |
| peak vertical GRF | 5.77 BW *(half-sine assumed)* |
| leg stiffness | 29.2 kN/m |
| ankle moment at peak | 273 N·m |
| required Achilles force | 5455 N |

The watch's own phase labels survive into the analysis, so `drive`,
`transition`, `peak`, and `deceleration` can be compared: contact time rises
monotonically from 168 ms in drive to 184 ms in deceleration.

## The muscle model is run forward, not fitted

A Thelen (2003) unit is driven over one stance phase from a prescribed
excitation and asked whether it *can* produce the force inverse dynamics says
the tendon carried. It reaches **9.8 kN against 5.5 kN required** (ratio
1.80). Agreement is a result; a shortfall would also have been a result and
is reported rather than tuned away.

Implementation notes worth keeping:

- The **eccentric asymptote cap** (`asy_e_thresh = 0.95`) is in OpenSim but
  **not in Thelen (2003)**. Without it the force-velocity inverse is singular
  at the eccentric plateau and the integrator diverges.
- The tendon toe/linear constants use the **exact** OpenSim expressions, not
  the paper's rounded `0.609 ε₀` / `1.712/ε₀`. A test asserts the slope is
  continuous at the junction.
- Thelen's f-v expression **already contains** activation and force-length.
  Multiplying again — correct for McLean 2003, whose f-v is a pure multiplier
  — double-counts. Only the Thelen form is implemented, so they cannot mix.
- Starting the fibre at equilibrium for a *different* activation than the
  simulation begins with produced a single spurious sample at 2600 mm/s
  against a 930 mm/s limit. Now `a0` is passed explicitly.

## Minimum jerk

The swing trajectory gives a peak-to-mean speed ratio of exactly **15/8 =
1.875**, which is what the criterion predicts analytically. Reaching studies
report **1.75**, so the criterion **overshoots by 7.1%** — reported rather
than smoothed over. Endpoint jerk is ±60Δ/d³, *not* zero: minimising
integrated squared jerk does not make jerk vanish at the ends.

## What the data cannot support

`foot_strike_angle` is whole degrees only (1–6, 5–10, 3–9 across sessions),
so it classifies strides and reports a distribution; it is never
differentiated. `power` is null in every sprint record and
`accumulated_power` is pinned at 65535 — the uint16 no-data sentinel. Both
are reported as unusable rather than silently skipped.

**Muscle forces are not identified from these data.** A joint moment is the
*net* moment; splitting it between agonist and antagonist is indeterminate
without EMG or an optimisation criterion.
