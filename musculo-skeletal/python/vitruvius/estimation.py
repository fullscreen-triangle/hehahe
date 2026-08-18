"""Catalytic power, the telescoping obstruction, and the typed estimator.

Specification section 6. The content is mostly negative and it is the
reason Rule IV exists:

  * kappa(gamma) = (S_before - S_after) / (S_before - beta) is the fraction
    of the outstanding gap to the floor that an event closes.
  * Residual factors multiply, so the net power of a cascade is
    1 - prod(1 - kappa_i).
  * If each kappa_i is estimated from the same state sequence that
    determines the measured net power, the two are the SAME function of the
    data. Every discrepancy statistic then takes its degenerate value on
    every data set whatsoever. The test cannot fail, so it has no power.
  * Estimating instead from the event TYPE breaks the identity and yields a
    test with a genuine null hypothesis.
  * That test is informative only when between-type variance exceeds
    within-type variance, which the statistic eta reports.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass
class Event:
    """One transition, with the observable before and after."""

    etype: str
    s_before: float
    s_after: float


def kappa(s_before: float, s_after: float, floor: float) -> float:
    gap = s_before - floor
    if gap <= 0:
        return float("nan")
    return (s_before - s_after) / gap


def residual_factor(s_before: float, s_after: float, floor: float) -> float:
    return 1.0 - kappa(s_before, s_after, floor)


def net_power(s_first: float, s_last: float, floor: float) -> float:
    """Measured net power of a cascade, from its endpoints alone."""
    gap = s_first - floor
    if gap <= 0:
        return float("nan")
    return (s_first - s_last) / gap


def compose_multiplicative(kappas: list[float]) -> float:
    prod = 1.0
    for k in kappas:
        prod *= (1.0 - k)
    return 1.0 - prod


def compose_additive(kappas: list[float]) -> float:
    return min(sum(kappas), 1.0)


def compose_maximum(kappas: list[float]) -> float:
    return max(kappas) if kappas else float("nan")


def compose_geometric(kappas: list[float]) -> float:
    if not kappas:
        return float("nan")
    prod = 1.0
    for k in kappas:
        prod *= (1.0 - k)
    prod = max(prod, 0.0)
    return 1.0 - prod ** (1.0 / len(kappas))


# ── the degenerate estimator ────────────────────────────────────────

def instance_specific_prediction(cascade: list[Event], floor: float) -> float:
    """Compose powers estimated from the cascade's own state sequence.

    This is the natural thing to write and it is an identity: the returned
    value equals `measured_net_power` on every input. Provided so the
    degeneracy can be demonstrated rather than merely asserted.
    """
    ks = [kappa(e.s_before, e.s_after, floor) for e in cascade]
    return compose_multiplicative(ks)


def measured_net_power(cascade: list[Event], floor: float) -> float:
    if not cascade:
        return float("nan")
    return net_power(cascade[0].s_before, cascade[-1].s_after, floor)


def telescoping_residual(cascade: list[Event], floor: float) -> float:
    """Difference between the instance-specific prediction and its own
    measurement. Zero to machine precision, always."""
    return abs(
        instance_specific_prediction(cascade, floor)
        - measured_net_power(cascade, floor)
    )


# ── the typed estimator ─────────────────────────────────────────────

def type_averaged_powers(corpus: list[Event], floor: float) -> dict[str, float]:
    """Mean power per event type, over a corpus independent of any one
    cascade being predicted."""
    acc: dict[str, list[float]] = {}
    for e in corpus:
        k = kappa(e.s_before, e.s_after, floor)
        if math.isfinite(k):
            acc.setdefault(e.etype, []).append(k)
    return {t: float(np.mean(v)) for t, v in acc.items() if v}


def typed_prediction(cascade: list[Event], type_means: dict[str, float]) -> float:
    ks = [type_means.get(e.etype, 0.0) for e in cascade]
    return compose_multiplicative(ks)


def type_separation(corpus: list[Event], floor: float) -> float:
    """eta = Var_between / (Var_between + Var_within).

    Near zero means the typing does not separate the powers, so a composed
    estimate is uninterpretable regardless of sample size.
    """
    groups: dict[str, list[float]] = {}
    for e in corpus:
        k = kappa(e.s_before, e.s_after, floor)
        if math.isfinite(k):
            groups.setdefault(e.etype, []).append(k)

    groups = {t: v for t, v in groups.items() if len(v) >= 1}
    if len(groups) < 2:
        return float("nan")

    means = [float(np.mean(v)) for v in groups.values()]
    var_between = float(np.var(means))
    within = [float(np.var(v)) for v in groups.values() if len(v) >= 2]
    var_within = float(np.mean(within)) if within else 0.0

    denom = var_between + var_within
    if denom <= 0:
        return float("nan")
    return var_between / denom


def composition_residual(
    cascades: list[list[Event]], corpus: list[Event], floor: float
) -> float:
    """Mean absolute discrepancy of the typed prediction. Non-degenerate:
    unlike the instance-specific version this need not be zero."""
    means = type_averaged_powers(corpus, floor)
    res = []
    for c in cascades:
        if not c:
            continue
        pred = typed_prediction(c, means)
        meas = measured_net_power(c, floor)
        if math.isfinite(pred) and math.isfinite(meas):
            res.append(abs(pred - meas))
    return float(np.mean(res)) if res else float("nan")


# ── synthesis of a corpus from a circuit ────────────────────────────

def corpus_from_circuit(backend, circuit, event_types: dict[str, list[str]],
                        n_instances: int = 24, seed: int = 0) -> list[Event]:
    """Generate a corpus of typed events from a circuit's simulated trace.

    Each declared event type names a pair of compartments; instances are
    drawn from successive windows of the trace, so instances of one type
    share a mechanism but differ in realisation. That is exactly the
    condition under which the typed estimator has a genuine null.
    """
    rng = np.random.default_rng(seed)
    x = backend.simulate(circuit)
    floor = circuit.floor()
    sig = np.abs(x.sum(axis=1)) + floor * 1.5

    events: list[Event] = []
    win = max(len(sig) // (n_instances * max(len(event_types), 1) + 1), 2)

    # A lesion must be able to move the estimates, so the type-characteristic
    # power is read from the circuit's surviving elements between the named
    # compartments -- not from the stratum alone.
    def local_gain(comps: list[str]) -> float:
        g, hits = 1.0, 0
        for e in circuit.elements.values():
            if e.src in comps or e.dst in comps:
                g *= e.gain
                hits += 1
        return g ** (1.0 / hits) if hits else 1.0

    noise = max((amp for _, _, amp in circuit.noise_edges), default=0.0)

    for ti, (tname, comps) in enumerate(sorted(event_types.items())):
        # Type-characteristic effect: how strongly this pairing acts.
        strata = [circuit.stratum_of(c) for c in comps if circuit.stratum_of(c)]
        depth = {"reflex": 0.55, "spinal": 0.35, "supraspinal": 0.18}
        base = float(np.mean([depth.get(s, 0.3) for s in strata])) if strata else 0.3
        base *= local_gain(comps)

        # Cross-stratum noise disperses powers within a type, which is what
        # drives eta down: the typing stops separating.
        spread = 0.06 + 0.9 * noise

        for j in range(n_instances):
            start = (ti * n_instances + j) * win
            if start + win >= len(sig):
                start = rng.integers(0, max(len(sig) - win - 1, 1))
            s_b = float(sig[start]) + floor
            jitter = float(rng.normal(0.0, spread))
            k = min(max(base + jitter, 0.01), 0.95)
            s_a = floor + (s_b - floor) * (1.0 - k)
            events.append(Event(tname, s_b, s_a))

    return events


def measure_estimation(backend, circuit, name: str, args: list[str],
                       ctx: dict, rep) -> object:
    """Dispatch target for the estimation observables."""
    from .backend import Measurement

    etypes = ctx.get("event_types", {})
    if not etypes:
        return Measurement(float("nan"), "fraction", rep,
                           note="no event types declared")

    # Cache per circuit arm, not per experiment: each lesion has its own
    # corpus, or a lesion could not move the estimate.
    key = (circuit.name, tuple(circuit.provenance),
           tuple(sorted(circuit.elements)))
    cache = ctx.setdefault("_corpora", {})
    corpus = cache.get(key)
    if corpus is None:
        corpus = corpus_from_circuit(backend, circuit, etypes,
                                     seed=backend.seed)
        cache[key] = corpus

    floor = circuit.floor()

    if name == "type_separation":
        return Measurement(type_separation(corpus, floor), "fraction", rep)

    if name == "kappa":
        et = args[0] if args else None
        means = type_averaged_powers(corpus, floor)
        n = sum(1 for e in corpus if e.etype == et)
        if et not in means:
            return Measurement(float("nan"), "fraction", rep,
                               note=f"no instances of type '{et}'")
        return Measurement(means[et], "fraction", rep,
                           note=f"type-averaged over {n} instances")

    if name == "composition_residual":
        by_type: dict[str, list[Event]] = {}
        for e in corpus:
            by_type.setdefault(e.etype, []).append(e)
        cascades = [v[:3] for v in by_type.values() if len(v) >= 3]
        return Measurement(composition_residual(cascades, corpus, floor),
                           "fraction", rep,
                           note="typed estimator; non-degenerate by construction")

    return Measurement(float("nan"), "fraction", rep)
