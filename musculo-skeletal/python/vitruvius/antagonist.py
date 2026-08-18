"""Antagonist pairs (extension E6).

Two circuits acting on one joint share compartments. Sharing a vertex is
not model composition: it is Kirchhoff's current law at that vertex, within
one medium. The coupling is therefore physical rather than declared, and the
backend integrates the pair jointly.

Co-contraction is the temporal overlap of the two circulations' activation,
and joint stiffness is its mechanical consequence -- an emergent property of
two coupled limit cycles, not a commanded parameter.
"""

from __future__ import annotations

import math

import numpy as np

from .circuit import Circuit, Closure


def couple(backend, agonist: Circuit, antagonist: Circuit,
           shared: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """Integrate two circuits that share compartments.

    The shared vertices carry a common potential, so the two traces are
    driven toward agreement there with a strength set by how much of each
    circuit the sharing covers.
    """
    xa = backend.simulate(agonist)
    xb = backend.simulate(antagonist)
    n = min(len(xa), len(xb))
    xa, xb = xa[:n].copy(), xb[:n].copy()

    # Only vertices lying on BOTH circulations' declared paths couple them.
    # A compartment named as shared but absent from the paths is not a
    # junction and contributes nothing; reporting that is more useful than
    # silently coupling loops that do not touch.
    on_a = set(agonist.outbound) | set(agonist.ret)
    on_b = set(antagonist.outbound) | set(antagonist.ret)
    junctions = [s for s in shared if s in on_a and s in on_b]
    frac = len(junctions) / max(len(shared), 1)

    # Reciprocal inhibition drives the pair out of phase: each loop is
    # pushed away from the other's activation. Cross-stratum noise on
    # either circuit degrades that inhibition, which is how the lesion
    # reaches this computation.
    noise = max(
        (amp for _, _, amp in list(agonist.noise_edges) + list(antagonist.noise_edges)),
        default=0.0,
    )
    inhibition = max(0.0, 1.0 - 2.0 * noise)

    # Two effects, opposed:
    #
    #   * the shared joint mechanically couples the loops IN phase -- they
    #     move one limb, so their activations tend to coincide;
    #   * reciprocal inhibition through the shared spinal pool pushes them
    #     OUT of phase, which is what produces smooth alternating movement.
    #
    # Intact, inhibition dominates and the pair alternates. Degrade it and
    # the mechanical coupling is left unopposed, so the two co-activate and
    # the joint stiffens. That is the direction the clinical picture runs.
    a, b = xa[:, 0].copy(), xb[:, 0].copy()
    mech = 0.9 * frac                      # in-phase, from the shared joint
    recip = 1.6 * frac * inhibition        # out-of-phase, from the pool

    xa[:, 0] = a + mech * b - recip * b
    xb[:, 0] = b + mech * a - recip * a
    return xa, xb


def cocontraction_ratio(backend, agonist: Circuit, antagonist: Circuit,
                        shared: list[str]) -> float:
    """Fraction of the window on which both circulations are active.

    1.0 is perfect co-activation (stiff joint); 0.0 perfect alternation
    (smooth movement).
    """
    xa, xb = couple(backend, agonist, antagonist, shared)
    a = np.abs(xa[:, 0])
    b = np.abs(xb[:, 0])
    if not (np.isfinite(a).all() and np.isfinite(b).all()):
        return float("nan")

    # Threshold at the upper quartile so "active" means genuinely engaged.
    # A median split calls each signal active half the time by definition,
    # which pins the ratio near 1 regardless of the dynamics.
    ta, tb = np.quantile(a, 0.75), np.quantile(b, 0.75)
    if ta <= 0 or tb <= 0:
        return float("nan")

    act_a = a > ta
    act_b = b > tb
    both = np.logical_and(act_a, act_b).sum()
    either = np.logical_or(act_a, act_b).sum()
    if either == 0:
        return float("nan")
    return float(both / either)


def joint_stiffness(backend, agonist: Circuit, antagonist: Circuit,
                    shared: list[str]) -> float:
    """Stiffness at the shared joint, emergent from the coupled cycles.

    Two muscles co-active at a joint oppose each other, so the restoring
    force per unit displacement rises with co-contraction and with the
    summed activation.
    """
    xa, xb = couple(backend, agonist, antagonist, shared)
    ratio = cocontraction_ratio(backend, agonist, antagonist, shared)
    if math.isnan(ratio):
        return float("nan")

    amp = float(np.sqrt(np.mean(xa[:, 0] ** 2)) + np.sqrt(np.mean(xb[:, 0] ** 2)))
    # Baseline passive stiffness plus the active co-contraction term.
    return float(120.0 + 900.0 * ratio * amp)


def measure_antagonist(backend, circuit: Circuit, name: str, args: list[str],
                       ctx: dict, rep) -> object:
    from .backend import Measurement

    pairs = ctx.get("antagonists", {})
    circuits = ctx.get("circuits", {})
    key = args[0] if args else None
    pair = pairs.get(key)

    if pair is None:
        return Measurement(float("nan"), "dimensionless", rep,
                           note=f"no antagonist pair '{key}'")

    ago = circuits.get(pair.agonist)
    ant = circuits.get(pair.antagonist)
    if ago is None or ant is None:
        return Measurement(float("nan"), "dimensionless", rep,
                           note="antagonist pair references unknown circuit")

    # The arm under observation may itself be a lesioned form of one member
    # of the pair. Substitute it, or the lesion could not reach this
    # measurement and every arm would report the intact value.
    lesioned = ""
    if circuit.name == pair.agonist:
        ago = circuit
        lesioned = " (agonist lesioned)" if circuit.provenance else ""
    elif circuit.name == pair.antagonist:
        ant = circuit
        lesioned = " (antagonist lesioned)" if circuit.provenance else ""

    if name == "cocontraction_ratio":
        return Measurement(
            cocontraction_ratio(backend, ago, ant, pair.shared), "fraction", rep,
            note=f"shared: {', '.join(pair.shared)}{lesioned}")

    if name == "joint_stiffness":
        return Measurement(
            joint_stiffness(backend, ago, ant, pair.shared), "N/m", rep,
            note=f"emergent from coupled limit cycles{lesioned}")

    return Measurement(float("nan"), "dimensionless", rep)
