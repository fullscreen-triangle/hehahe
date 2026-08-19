# Vitruvius IDE

A browser IDE for `.vvs` — the language specified in
[`../docs/musculo-skeletal-syntax/`](../docs/musculo-skeletal-syntax/).

The point of difference from a mock-up: **the language is really here**. The
lexer, parser, typechecker, four static analyses, operational semantics, and
reference backend are all ported to TypeScript and run in the browser. Editing
a program re-typechecks it; running one integrates it. Nothing is a fixture.

```bash
npm install
npm run dev      # http://localhost:5173
npm test         # 31 tests
npm run build
```

## Why this isn't a mock

The engine is verified against the Python reference implementation. All nine
shipped programs reproduce the same arm counts, closure indices, and warning
counts, and the headline results match to full precision:

```
03  proprioceptive_loss   OPEN, force 420.0 N — identical to baseline
04  amputated OPEN → tmr CLOSED 65.8 ms / mirror CLOSED 35.8 ms
10  force ratio 0.707107 = sqrt(0.9/1.8)
```

If you edit a program in the browser, those numbers change accordingly,
because they are computed rather than looked up.

## Architecture

```
 .vvs ──► lexer ──► parser ──► checker ──► runtime ──► views
                                  │           │
                          static analyses   backend
                          (no numerics)    (numerics)
```

The split is the language's central architectural commitment, and the UI
makes it visible: **closure, compartment, stratum, and floor analyses run on
every keystroke**, so the Circuit and Aperture tabs are populated before you
press Run. Only the observation store needs the integrator.

| module | role |
|---|---|
| `lang/lexer.ts` | tokens, with source spans for editor markers |
| `lang/parser.ts` | LL(1) recursive descent, no backtracking |
| `lang/circuit.ts` | closure index, aperture reports, lesion operators |
| `lang/checker.ts` | the four typing rules, template expansion |
| `lang/observables.ts` | the registry — every observable and its procedure |
| `lang/backend.ts` | deterministic integrator, obligations B1–B4 |
| `lang/runtime.ts` | operational semantics, phases |

## What the IDE surfaces

**Live diagnostics.** Gutter markers, inline underlines, and hover
explanations come from the real checker. A squiggle under an observable means
it is genuinely absent from the registry.

**An aperture is a diagnostic, not an error.** An open circuit compiles, runs,
and reports. What the language refuses is silence: the Aperture tab names the
circulation opened and states the prediction that follows, before any number
is read.

**Six views.** Circuit (stratum-banded topology, laid out from the declared
circulation, with severed edges marked and animated charge flow), Spectra
(PSD per arm with a frequency brush that re-integrates band powers), State
space (3-D `state × d(state)/dt × time`, rotatable), Results (matrix with
tier tags, heat shading, and per-cell backend provenance), Compare (slope
chart across arms plus a closure-vs-value split), and Aperture.

**Provenance on every value.** Hovering a result cell shows the floor used,
the frequency band, the seed, and the sample count — obligations (B2) and
(B3), which the specification requires a backend to disclose.

**Export.** `Export JSON` writes the same schema the Python runner produces,
so a browser session and a batch run are comparable artefacts.

## Keyboard

| key | action |
|---|---|
| `⌘↵` / `Ctrl+↵` | run |
| `Ctrl+Space` | complete keyword or observable |
| `Tab` | indent |

## Caveats

The backend is a **linearised reference implementation**: a delayed
multi-stratum loop, without cross-bridge kinetics or musculotendon mechanics.
Absolute magnitudes are not physiological predictions. What is exact and
backend-independent is the closure analysis and anything derived from
declared values by `Q = √(2CP)` — the force ratio is exact; the 420 N it
scales is a convention.

The spectral estimate is a naive DFT over a log-spaced grid rather than an
FFT, which is adequate at these window lengths and keeps the port
dependency-free. Large `dur` values will be slow.
