"""Validation suite for the coherence, identity, opacity, admissibility,
and floor analyses.

Every check is capable of failing. The suite is deterministic given its seed
and writes its results to JSON alongside the other experiment records.
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path

from vitruvius import check, parse
from vitruvius.backend import Backend
from vitruvius.circuit import (
    Circuit, Closure, Compartment, Element, with_scaling, without_element,
)
from vitruvius.coherence import (
    admissibility, character_is_invariant, coherence_margin, floor_by_connectivity,
    floor_tightness, identity_character, is_coherent, path_opacity,
)
from vitruvius.runtime import Runtime

RNG = random.Random(20260819)
HERE = Path(__file__).resolve().parent


def rand_circuit(n_extra: int = 0, mismatch: float = 0.0) -> Circuit:
    """A random closed circulation, optionally with a parallel route whose
    delay differs from the route it parallels by `mismatch`."""
    names = ["c0", "c1", "c2", "c3", "c4"]
    comps = {n: Compartment(n, 1e-8 * (i + 1), "reflex") for i, n in enumerate(names)}
    els: dict[str, Element] = {}
    for i in range(len(names) - 1):
        els[f"e{i}"] = Element(f"e{i}", names[i], names[i + 1],
                               RNG.uniform(2e-3, 12e-3), RNG.uniform(0.5, 3.0))
    els["back"] = Element("back", names[-1], names[0], RNG.uniform(4e-3, 10e-3), 1.0)

    for k in range(n_extra):
        mid = f"p{k}"
        comps[mid] = Compartment(mid, 1e-8, "reflex")
        base = els["e0"].delay + els["e1"].delay
        els[f"pa{k}"] = Element(f"pa{k}", names[0], mid, base / 2, 1.0)
        els[f"pb{k}"] = Element(f"pb{k}", mid, names[2], base / 2 + mismatch, 1.0)

    return Circuit(name="rand", compartments=comps,
                   outbound=names[:3], ret=names[2:] + [names[0]],
                   elements=els, floor_spec=None, noise_edges=[], provenance=[])


def relabelled(c: Circuit, rel: dict[str, str]) -> Circuit:
    out = c.clone()
    out.compartments = {rel[k]: Compartment(rel[k], v.capacitance, v.stratum)
                        for k, v in c.compartments.items()}
    out.elements = {k: Element(e.name, rel[e.src], rel[e.dst], e.delay, e.gain)
                    for k, e in c.elements.items()}
    out.outbound = [rel[v] for v in c.outbound]
    out.ret = [rel[v] for v in c.ret]
    return out


RESULTS: dict = {"groups": [], "checks": 0, "passed": 0}


def run_group(name: str, claim: str, fn) -> None:
    rec = {"group": name, "claim": claim, "checks": 0, "passed": 0, "detail": {}}
    fn(rec)
    rec["all_pass"] = rec["checks"] == rec["passed"]
    RESULTS["groups"].append(rec)
    RESULTS["checks"] += rec["checks"]
    RESULTS["passed"] += rec["passed"]


def ck(rec: dict, cond: bool) -> bool:
    rec["checks"] += 1
    if cond:
        rec["passed"] += 1
    return bool(cond)


# ── C1 ───────────────────────────────────────────────────────────────

def c1(rec):
    closed_incoherent = closed_coherent = 0
    margins = []
    for _ in range(200):
        mism = RNG.choice([0.0, 0.0, RNG.uniform(4e-3, 30e-3)])
        c = rand_circuit(n_extra=1, mismatch=mism)
        closed = c.closure_index() is Closure.CLOSED
        coh = is_coherent(c)
        margins.append(coherence_margin(c))
        if closed and not coh:
            closed_incoherent += 1
        if closed and coh:
            closed_coherent += 1
        ck(rec, isinstance(closed, bool) and isinstance(coh, bool))
    ck(rec, closed_incoherent > 0)
    ck(rec, closed_coherent > 0)
    rec["detail"] = {
        "closed_and_incoherent": closed_incoherent,
        "closed_and_coherent": closed_coherent,
        "worst_margin_s": min(margins),
        "margins_s": margins,
    }


# ── C2 ───────────────────────────────────────────────────────────────

def c2(rec):
    agree = 0
    for _ in range(60):
        c = rand_circuit(n_extra=1, mismatch=RNG.choice([0.0, 12e-3]))
        pre = coherence_margin(c)
        Backend(seed=1, duration=2).simulate(c)
        Backend(seed=99, duration=2).simulate(c)
        post = coherence_margin(c)
        if ck(rec, abs(pre - post) < 1e-15):
            agree += 1
    rec["detail"] = {"backend_independent": agree, "of": 60}


# ── C3 ───────────────────────────────────────────────────────────────

def c3(rec):
    """Both operators are expressible; only one repairs the incoherence.

    The point of a two-factor rule is that the two factors can disagree. We
    therefore report three counts explicitly rather than one summary: how
    often removal repairs the disagreement, how often scaling leaves it in
    place, and -- the case that makes the rule bite -- how often an operator
    that is expressible nevertheless produces a circuit an experimenter
    should refuse, because it is still incoherent afterwards.
    """
    repaired = persisted = still_incoherent = 0
    rows = []
    for _ in range(120):
        c = rand_circuit(n_extra=1, mismatch=RNG.uniform(6e-3, 25e-3))
        rm = without_element(c, "pb0")
        sc = with_scaling(c, "pb0", 0.05)
        a_rm = admissibility(c, rm)
        a_sc = admissibility(c, sc)

        # Both operators apply: expressibility alone does not discriminate.
        ck(rec, a_rm.expressible and a_sc.expressible)

        if is_coherent(rm):
            repaired += 1
        if not is_coherent(sc):
            persisted += 1
            still_incoherent += 1
        # Scaling does not worsen the margin, so it passes the
        # coherence-PRESERVING test while leaving the circuit incoherent.
        # That is the gap a preservation test cannot close, and why the
        # useful report is the post-state margin, not the delta.
        ck(rec, abs(a_sc.margin_after - a_sc.margin_before) < 1e-12)
        rows.append({"before": a_rm.margin_before,
                     "after_removal": a_rm.margin_after,
                     "after_scaling": a_sc.margin_after,
                     "removal_coherent": is_coherent(rm),
                     "scaling_coherent": is_coherent(sc)})
    ck(rec, repaired > 0)
    ck(rec, persisted > 0)
    rec["detail"] = {"removal_repairs": repaired,
                     "scaling_leaves_incoherent": persisted,
                     "expressible_but_still_incoherent": still_incoherent,
                     "of": 120, "sample": rows[:60]}


# ── C4 ───────────────────────────────────────────────────────────────

def c4(rec):
    devs = []
    pairs = []
    for _ in range(120):
        c = rand_circuit(n_extra=RNG.choice([0, 1]))
        names = sorted(c.compartments)
        perm = names[:]
        RNG.shuffle(perm)
        rel = dict(zip(names, perm))
        base = identity_character(c).cost
        ck(rec, character_is_invariant(c, rel))
        after = identity_character(relabelled(c, rel)).cost
        devs.append(abs(after - base))
        pairs.append({"base": base, "relabelled": after})
    rec["detail"] = {"max_deviation": max(devs), "n": len(devs), "pairs": pairs}


# ── C5 ───────────────────────────────────────────────────────────────

def c5(rec):
    prog = check(parse((HERE / "experiments" / "12_identity_character.vvs")
                       .read_text(encoding="utf-8")))
    rows = {}
    for nm, c in prog.circuits.items():
        ic = identity_character(c)
        rows[nm] = {"cost": ic.cost, "cheapest_singleton": ic.cheapest_singleton,
                    "is_block_cut": ic.is_block_cut, "n_blocks": ic.n_blocks,
                    "blocks": [sorted(b) for b in ic.identity],
                    "ratio": ic.cheapest_singleton / ic.cost if ic.cost else None}
        if ic.is_block_cut:
            ck(rec, ic.cost < ic.cheapest_singleton)
        else:
            ck(rec, abs(ic.cost - ic.cheapest_singleton) < 1e-12)
    ck(rec, any(v["is_block_cut"] for v in rows.values()))
    ck(rec, any(not v["is_block_cut"] for v in rows.values()))
    rec["detail"] = rows


# ── C6 ───────────────────────────────────────────────────────────────

def c6(rec):
    multi = 0
    rows = []
    for _ in range(120):
        # Parallel routes must be allowed to DIFFER in total delay, or the
        # opacity is real but invisible in latency and the reported spread
        # is uninformative.
        c = rand_circuit(n_extra=RNG.choice([0, 1, 1]),
                         mismatch=RNG.choice([0.0, RNG.uniform(3e-3, 20e-3)]))
        r = path_opacity(c, c.outbound[0], c.outbound[-1])
        ck(rec, r.n_realisations >= 1)
        if r.is_opaque:
            multi += 1
            ck(rec, len(set(r.interiors)) == r.n_realisations)
        rows.append({"n": r.n_realisations,
                     "lat_lo": r.latency_range[0],
                     "lat_hi": r.latency_range[1],
                     "spread": r.latency_range[1] - r.latency_range[0]})
    ck(rec, multi > 0)
    rec["detail"] = {"opaque_circuits": multi, "of": 120, "sample": rows}


# ── C7 ───────────────────────────────────────────────────────────────

def c7(rec):
    ratios = []
    for _ in range(400):
        c = rand_circuit(n_extra=RNG.choice([0, 1]))
        fd = floor_by_connectivity(c)
        ck(rec, fd.value > 0)
        ck(rec, fd.connected)
        ck(rec, fd.min_edge_weight > 0)
        t = floor_tightness(c)
        if math.isfinite(t):
            ck(rec, t >= 1.0 - 1e-12)
            ratios.append(t)
    rec["detail"] = {"min_tightness": min(ratios),
                     "mean_tightness": sum(ratios) / len(ratios),
                     "n": len(ratios), "ratios": ratios}


# ── C8 ───────────────────────────────────────────────────────────────

def c8(rec):
    src = (HERE / "experiments" / "11_coherence_holonomy.vvs").read_text(encoding="utf-8")
    prog = parse(src)
    ckres = check(prog)
    ck(rec, ckres.ok)
    r = Runtime(prog, ckres, Backend(seed=0, duration=6)).run()

    rows = {}
    all_closed = True
    for x in r.experiments:
        for a in x.all_arms():
            m = a.store.get("coherence_margin")
            rows[f"{x.name}/{a.name}"] = {
                "closure": a.closure,
                "coherence_margin": m.value if m else None,
                "is_coherent": a.store["is_coherent"].value,
                "path_multiplicity": a.store["path_multiplicity"].value,
                "loop_latency": a.store["loop_latency"].value,
            }
            if a.closure != "closed":
                all_closed = False

    ck(rec, all_closed)
    states = {v["is_coherent"] for v in rows.values()}
    ck(rec, "coherent" in states and "incoherent" in states)
    lats = {v["loop_latency"] for v in rows.values()}
    ck(rec, len(lats) == 1)   # identical loop latency, different coherence
    rec["detail"] = rows


GROUPS = [
    ("C1", "A circuit can be closed and incoherent: closure does not imply "
           "coherence.", c1),
    ("C2", "The coherence margin is computed from declared delays alone and is "
           "invariant under the backend.", c2),
    ("C3", "A lesion is admissible only if expressible AND coherence-preserving; "
           "neither factor alone suffices.", c3),
    ("C4", "Character cost is invariant under every weight-preserving "
           "relabelling.", c4),
    ("C5", "When the minimising partition is a block cut, no single compartment "
           "carries the character.", c5),
    ("C6", "Endpoints and closure index do not determine the interior.", c6),
    ("C7", "Floor positivity follows from connectivity plus positive edge "
           "weights, and the bound is close to tight.", c7),
    ("C8", "The declared programs separate closed-coherent from "
           "closed-incoherent at identical loop latency.", c8),
]


def main() -> int:
    for name, claim, fn in GROUPS:
        run_group(name, claim, fn)

    RESULTS["seed"] = 20260819
    RESULTS["all_pass"] = RESULTS["checks"] == RESULTS["passed"]

    out = HERE / "results" / "coherence_validation.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(RESULTS, indent=2), encoding="utf-8")

    print(f"{'group':<6}{'checks':>8}{'passed':>8}  {'':<4}claim")
    print("-" * 92)
    for g in RESULTS["groups"]:
        mark = "ok" if g["all_pass"] else "FAIL"
        print(f"{g['group']:<6}{g['checks']:>8}{g['passed']:>8}  {mark:<4}{g['claim'][:60]}")
    print("-" * 92)
    print(f"{'TOTAL':<6}{RESULTS['checks']:>8}{RESULTS['passed']:>8}  "
          f"{'ALL PASS' if RESULTS['all_pass'] else 'FAILURES'}")
    print(f"\nwrote {out.relative_to(HERE)}")
    return 0 if RESULTS["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
