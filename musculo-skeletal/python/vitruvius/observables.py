"""The observable registry.

Every observable admitted by the language is declared here with the
procedure that computes it, the unit it carries, and the backend obligation
that discharges it. An observable without a defined measurement procedure is
not a result but a promise, so the checker rejects any name absent from this
table.

`stratum_band` records the frequency band a value is attributed to, which is
what backend obligation (B3) -- stratum honesty -- requires be reported.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ObsSpec:
    name: str
    unit: str
    arity: int
    procedure: str
    requires_event_type: bool = False
    requires_antagonist: bool = False
    open_circuit_only: bool = False
    stratum_band: tuple[float, float] | None = None


def _o(*a, **k) -> tuple[str, ObsSpec]:
    s = ObsSpec(*a, **k)
    return s.name, s


OBSERVABLES: dict[str, ObsSpec] = dict(
    [
        # ── topological: computed from the declaration alone ──────────
        _o("closure_index", "categorical", 0,
           "Decide whether every declared outbound path has a closing return "
           "phase realised by surviving elements. Returns 'closed' or 'open'."),
        _o("aperture_list", "list", 0,
           "Enumerate the circulations left without a return phase, each with "
           "the outbound phase now unclosed and the cause."),
        _o("resting_cut_weight", "conductance", 0,
           "Total weight of the minimum cut separating the floor's reference "
           "compartment from the medium."),
        _o("floor_value", "conductance", 0,
           "The circuit's irreducible residual beta, as derived by its "
           "declared floor specification."),

        # ── temporal ──────────────────────────────────────────────────
        _o("loop_latency", "s", 0,
           "Sum of the declared delays of the elements realising the "
           "outbound and return paths of the circulation."),
        _o("divergence_time", "s", 0,
           "Time at which an open circuit's state leaves the bounded region. "
           "Defined only for open circuits; NaN when the circuit is closed.",
           open_circuit_only=True),

        # ── oscillatory: require integration ──────────────────────────
        _o("tonic_rate", "Hz", 0,
           "Mean discharge rate of the circulation at rest, from the "
           "reciprocal of the loop traversal time damped by loop gain."),
        _o("oscillation_frequency", "Hz", 0,
           "Dominant frequency of the bounded limit cycle, by peak-picking "
           "the power spectrum of the simulated state."),
        _o("oscillation_amplitude", "a.u.", 0,
           "Root-mean-square excursion of the limit cycle about its centre."),
        _o("cop_rms", "mm", 0,
           "Root-mean-square displacement of the centre of pressure over the "
           "observation window."),
        _o("force_amplitude", "N", 0,
           "Peak force produced by the circulation's terminal muscle "
           "compartment over one cycle."),
        _o("force_output", "N", 0,
           "Mean force produced over the observation window."),

        # ── spectral ──────────────────────────────────────────────────
        _o("band_power", "fraction", 1,
           "Fraction of total spectral power falling in the named stratum's "
           "band, by Welch periodogram. Bands: reflex 1-3 Hz, spinal "
           "0.3-1 Hz, supraspinal 0.05-0.3 Hz."),
        _o("coupling_index", "dimensionless", 0,
           "Magnitude of the zero-lag cross-correlation between the slow "
           "(supraspinal) component and the envelope of the fast (reflex) "
           "component. Healthy range 0.3-0.6."),

        # ── estimation: Rule IV applies ───────────────────────────────
        _o("kappa", "fraction", 1,
           "Type-averaged catalytic power of the named event type: the mean "
           "over recorded instances of the fraction of the outstanding gap to "
           "the floor closed by an event of that type. Requires a declared "
           "event type with at least two instances (Rule IV); an "
           "instance-specific estimate is an algebraic identity and cannot "
           "fail.",
           requires_event_type=True),
        _o("type_separation", "fraction", 0,
           "eta = Var_between / (Var_between + Var_within) over the declared "
           "event types. Near zero means the typing does not separate and any "
           "composed estimate is uninterpretable."),
        _o("composition_residual", "fraction", 0,
           "Discrepancy between the type-averaged multiplicative prediction "
           "and the measured net power. Non-degenerate by construction."),

        # ── E6: antagonist pairs ──────────────────────────────────────
        _o("cocontraction_ratio", "fraction", 1,
           "Temporal overlap of activation in the agonist and antagonist "
           "circuits of a declared pair, coupled through their shared "
           "compartments. 1.0 is perfect co-activation, 0.0 perfect "
           "alternation.",
           requires_antagonist=True),
        _o("joint_stiffness", "N/m", 1,
           "Mechanical stiffness at the shared joint, emergent from the two "
           "coupled limit cycles rather than commanded.",
           requires_antagonist=True),
    ]
)


# Stratum frequency bands, used by band_power and for obligation (B3).
STRATUM_BANDS: dict[str, tuple[float, float]] = {
    "reflex": (1.0, 3.0),
    "spinal": (0.3, 1.0),
    "supraspinal": (0.05, 0.3),
}


def describe(name: str) -> str:
    s = OBSERVABLES.get(name)
    if s is None:
        return f"unknown observable '{name}'"
    return f"{s.name} [{s.unit}]: {s.procedure}"
