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
