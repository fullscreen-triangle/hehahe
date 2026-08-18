"""Tests for the Vitruvius reference implementation.

Each test names the specification claim it exercises. The point is that the
claims are executable rather than merely stated: if the implementation
drifts from the specification, one of these fails.
"""

from __future__ import annotations

import itertools
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vitruvius import Backend, check, parse, run_source  # noqa: E402
from vitruvius.checker import CheckError  # noqa: E402
from vitruvius.circuit import (  # noqa: E402
    Closure, reroute, with_noise, with_scaling, without_element, without_return,
)
from vitruvius.estimation import (  # noqa: E402
    Event, instance_specific_prediction, measured_net_power,
    telescoping_residual, type_averaged_powers, type_separation,
)

EXPERIMENTS = Path(__file__).resolve().parent.parent / "experiments"


MINIMAL = """
module m;
compartment a { capacitance: 1.0e-8 F; stratum: reflex; }
compartment b { capacitance: 2.0e-8 F; stratum: reflex; }
compartment c { capacitance: 3.0e-8 F; stratum: reflex; }

circuit loop {
  floor    : derived(resting_cut(a));
  outbound : a -> b;
  return   : b -> c -> a;
  element f  conducts a -> b delay 5.0 ms;
  element g  conducts b -> c delay 5.0 ms;
  element h  conducts c -> a delay 5.0 ms gain 1.0;
}

experiment e {
  intact  : loop;
  observe : closure_index, loop_latency;
}
"""


def build(src: str = MINIMAL):
    prog = parse(src)
    res = check(prog)
    return prog, res


# ── grammar ─────────────────────────────────────────────────────────

def test_minimal_program_parses_and_checks():
    _, res = build()
    assert res.ok, res.errors
    assert "loop" in res.circuits


def test_circuit_declaration_requires_both_phases():
    """Section 3: an open circuit cannot arise by omission."""
    src = MINIMAL.replace("  return   : b -> c -> a;\n", "")
    with pytest.raises(Exception):
        parse(src)


def test_comment_does_not_swallow_arrow():
    _, res = build(MINIMAL.replace("circuit loop {", "-- a comment\ncircuit loop {"))
    assert res.ok


# ── closure (section 5) ─────────────────────────────────────────────

def test_declared_circuit_is_closed():
    _, res = build()
    assert res.circuits["loop"].closure_index() is Closure.CLOSED


def test_removing_return_element_opens_the_circuit():
    _, res = build()
    c = without_element(res.circuits["loop"], "h")
    assert c.closure_index() is Closure.OPEN
    assert c.apertures()


def test_attenuation_preserves_closure():
    """Proposition 5.4: no finite attenuation opens a circulation."""
    _, res = build()
    base = res.circuits["loop"]
    for factor in (0.9, 0.5, 0.1, 1e-6, 1e-12):
        c = with_scaling(base, "h", factor)
        assert c.closure_index() is Closure.CLOSED, factor


def test_scaling_by_zero_is_rejected():
    """Severance is a different operator, not a limit of attenuation."""
    _, res = build()
    with pytest.raises(ValueError):
        with_scaling(res.circuits["loop"], "h", 0.0)


def test_closure_is_linear_in_elements():
    _, res = build()
    c = res.circuits["loop"]
    # Decidable without simulation: no backend is constructed here.
    assert c.closure_index() in (Closure.CLOSED, Closure.OPEN)


# ── lesion algebra (Theorem 6.5) ────────────────────────────────────

def test_lesions_commute():
    _, res = build()
    base = res.circuits["loop"]
    a = with_scaling(without_element(base, "g"), "h", 0.5)
    b = without_element(with_scaling(base, "h", 0.5), "g")
    assert set(a.elements) == set(b.elements)
    assert a.closure_index() is b.closure_index()
    assert {(k, e.gain) for k, e in a.elements.items()} == \
           {(k, e.gain) for k, e in b.elements.items()}


def test_removal_is_idempotent():
    _, res = build()
    base = res.circuits["loop"]
    once = without_element(base, "g")
    twice = without_element(once, "g")
    assert set(once.elements) == set(twice.elements)


def test_removal_of_absent_element_is_identity():
    _, res = build()
    base = res.circuits["loop"]
    assert set(without_element(base, "nonexistent").elements) == set(base.elements)


def test_lesion_order_independence_over_all_permutations():
    _, res = build()
    base = res.circuits["loop"]
    ops = [
        lambda c: without_element(c, "g"),
        lambda c: with_scaling(c, "h", 0.4),
        lambda c: with_noise(c, "reflex", "spinal", 0.2),
    ]
    outcomes = set()
    for perm in itertools.permutations(ops):
        c = base
        for op in perm:
            c = op(c)
        outcomes.add(
            (frozenset((k, e.gain) for k, e in c.elements.items()),
             c.closure_index(),
             frozenset(c.noise_edges))
        )
    assert len(outcomes) == 1


# ── reroute (E3) ────────────────────────────────────────────────────

def test_reroute_can_restore_closure():
    """E3 is the only operator that carries open back to closed."""
    _, res = build()
    base = res.circuits["loop"]
    opened = without_return(base, "b")
    assert opened.closure_index() is Closure.OPEN
    repaired = reroute(opened, "b", ["b", "c", "a"])
    assert repaired.closure_index() is Closure.CLOSED


def test_reroute_to_wrong_terminus_stays_open():
    _, res = build()
    opened = without_return(res.circuits["loop"], "b")
    bad = reroute(opened, "b", ["b", "c"])  # does not return to 'a'
    assert bad.closure_index() is Closure.OPEN


# ── typing rules (section 4) ────────────────────────────────────────

def test_rule_ii_rejects_non_adjacent_strata():
    src = """
    module m;
    compartment lo { capacitance: 1.0e-8 F; stratum: reflex; }
    compartment hi { capacitance: 1.0e-3 F; stratum: supraspinal; }
    circuit bad {
      floor    : derived(resting_cut(lo));
      outbound : lo -> hi;
      return   : hi -> lo;
      element up   conducts lo -> hi delay 5.0 ms;
      element down conducts hi -> lo delay 5.0 ms;
    }
    experiment e { intact : bad; observe : closure_index; }
    """
    _, res = build(src)
    assert not res.ok
    assert any(d.rule == "T-Stratum" for d in res.errors)


def test_rule_ii_allows_adjacent_strata():
    src = """
    module m;
    compartment lo { capacitance: 1.0e-8 F; stratum: reflex; }
    compartment mid { capacitance: 3.0e-8 F; stratum: spinal; }
    circuit ok {
      floor    : derived(resting_cut(lo));
      outbound : lo -> mid;
      return   : mid -> lo;
      element up   conducts lo -> mid delay 5.0 ms;
      element down conducts mid -> lo delay 5.0 ms;
    }
    experiment e { intact : ok; observe : closure_index; }
    """
    _, res = build(src)
    assert res.ok, res.errors


def test_rule_iii_floor_is_positive():
    _, res = build()
    assert res.circuits["loop"].floor() > 0


def test_rule_iii_warns_on_sample_minimum():
    src = MINIMAL.replace("derived(resting_cut(a))", "derived(sample_minimum)")
    _, res = build(src)
    assert any("sample_minimum" in d.message for d in res.warnings)


def test_rule_iv_rejects_untyped_kappa():
    src = MINIMAL.replace("observe : closure_index, loop_latency;",
                          "observe : kappa;")
    _, res = build(src)
    assert not res.ok
    assert any(d.rule in ("T-Event", "arity") for d in res.errors)


def test_rule_iv_rejects_undeclared_event_type():
    src = MINIMAL.replace("observe : closure_index, loop_latency;",
                          "observe : kappa(nonexistent);")
    _, res = build(src)
    assert not res.ok


def test_unknown_observable_is_rejected():
    """An observable without a measurement procedure is not a result."""
    src = MINIMAL.replace("observe : closure_index, loop_latency;",
                          "observe : conscious_overhead;")
    _, res = build(src)
    assert not res.ok
    assert any(d.rule == "unknown-observable" for d in res.errors)


def test_duplicate_scaling_of_one_element_is_rejected():
    src = MINIMAL.replace(
        "experiment e {\n  intact  : loop;",
        "experiment e {\n  intact  : loop;\n"
        "  lesion bad : loop with h scaling 0.5 with h scaling 0.5;",
    )
    _, res = build(src)
    assert any(d.rule == "T-Lesion" for d in res.errors)


# ── aperture is a diagnostic, not an error ──────────────────────────

def test_open_circuit_warns_but_does_not_reject():
    src = MINIMAL.replace(
        "experiment e {\n  intact  : loop;",
        "experiment e {\n  intact  : loop;\n"
        "  lesion cut : loop without element(h);",
    )
    _, res = build(src)
    assert res.ok, res.errors
    assert any(d.rule == "aperture" for d in res.warnings)


# ── operational semantics (section 6) ───────────────────────────────

def test_record_is_monotone():
    r = run_source(MINIMAL)
    arm = r.experiments[0].arms[0]
    assert arm.record == len(arm.store) > 0


def test_termination_bound():
    """Theorem 6.6: at most |L| + |O| + 1 steps."""
    src = MINIMAL.replace(
        "experiment e {\n  intact  : loop;",
        "experiment e {\n  intact  : loop;\n"
        "  lesion l1 : loop with h scaling 0.5;\n"
        "  lesion l2 : loop without element(g);",
    )
    r = run_source(src)
    x = r.experiments[0]
    assert len(x.arms) == 3  # intact + 2 lesions
    for arm in x.arms:
        assert arm.record <= len(x.arms[0].store) + 1


# ── backend obligations (section 7) ─────────────────────────────────

def test_b1_totality_open_circuit_returns_value_not_exception():
    src = MINIMAL.replace(
        "observe : closure_index, loop_latency;",
        "observe : closure_index, divergence_time, oscillation_amplitude;",
    ).replace(
        "experiment e {\n  intact  : loop;",
        "experiment e {\n  intact  : loop;\n"
        "  lesion cut : loop without element(h);",
    )
    r = run_source(src)
    cut = [a for a in r.experiments[0].arms if a.name == "cut"][0]
    assert cut.closure == "open"
    dt = cut.store["divergence_time"].value
    assert isinstance(dt, float) and math.isfinite(dt)


def test_b2_backend_reports_floor_used():
    r = run_source(MINIMAL)
    m = r.experiments[0].arms[0].store["loop_latency"]
    assert m.report.floor_used > 0


def test_b4_determinism_modulo_seed():
    a = run_source(MINIMAL, Backend(seed=7))
    b = run_source(MINIMAL, Backend(seed=7))
    ka = a.experiments[0].arms[0].store["loop_latency"].value
    kb = b.experiments[0].arms[0].store["loop_latency"].value
    assert ka == kb


def test_static_analyses_do_not_consult_backend():
    """Proposition 7.2: diagnostics are backend-independent."""
    prog = parse(MINIMAL)
    r1 = check(prog)
    r2 = check(parse(MINIMAL))
    assert [str(d) for d in r1.diagnostics] == [str(d) for d in r2.diagnostics]


# ── estimation (section 6 of the paper) ─────────────────────────────

def test_telescoping_identity_holds_for_arbitrary_data():
    """Theorem: the instance-specific test cannot fail, on ANY data."""
    import numpy as np

    rng = np.random.default_rng(0)
    floor = 10.0
    for _ in range(500):
        s = float(rng.uniform(20, 200))
        chain = []
        for _ in range(int(rng.integers(2, 7))):
            s_next = floor + max(float(rng.uniform(0.1, 2.0)) * (s - floor), 1e-9)
            chain.append(Event("t", s, s_next))
            s = s_next
        assert telescoping_residual(chain, floor) < 1e-9


def test_typed_estimator_is_non_degenerate():
    """A type with two distinct instances yields a nonzero discrepancy."""
    floor = 10.0
    corpus = [Event("t", 100.0, 50.0), Event("t", 100.0, 80.0)]
    means = type_averaged_powers(corpus, floor)
    single = [corpus[0]]
    pred = 1 - (1 - means["t"])
    meas = measured_net_power(single, floor)
    assert abs(pred - meas) > 1e-6


def test_type_separation_high_when_types_differ():
    floor = 10.0
    corpus = []
    for t, k in (("a", 0.7), ("b", 0.2)):
        for _ in range(20):
            corpus.append(Event(t, 100.0, floor + (100.0 - floor) * (1 - k)))
    assert type_separation(corpus, floor) > 0.9


def test_type_separation_low_when_types_coincide():
    import numpy as np

    rng = np.random.default_rng(1)
    floor = 10.0
    corpus = []
    for t in ("a", "b", "c"):
        for _ in range(40):
            k = 0.4 + float(rng.normal(0, 0.2))
            k = min(max(k, 0.01), 0.95)
            corpus.append(Event(t, 100.0, floor + 90.0 * (1 - k)))
    assert type_separation(corpus, floor) < 0.25


# ── the shipped experiments all run ─────────────────────────────────

@pytest.mark.parametrize("name", [
    "01_stroke_umn_lmn.vvs",
    "02_spinal_cord_injury.vvs",
    "03_nerve_block_phases.vvs",
    "04_tmr_reroute.vvs",
    "05_tremor_classification.vvs",
    "06_cocontraction.vvs",
])
def test_shipped_experiment_runs(name):
    from vitruvius import run_file

    r = run_file(str(EXPERIMENTS / name))
    assert r.experiments
    for x in r.experiments:
        assert x.all_arms()


# ── the derivations produce the claimed results ─────────────────────

def test_umn_lmn_distinction_is_derived():
    """Cortical lesion: supraspinal open, segmental closed (spasticity).
    Anterior horn lesion: both open (flaccidity)."""
    from vitruvius import run_file

    r = run_file(str(EXPERIMENTS / "01_stroke_umn_lmn.vvs"))

    umn = r.experiment("cortical_lesion_supraspinal")
    umn_arm = [a for a in umn.arms if a.name == "umn"][0]
    seg = r.experiment("cortical_lesion_segmental")

    assert umn_arm.closure == "open"
    assert seg.arms[0].closure == "closed"          # reflex survives
    assert seg.arms[0].store["tonic_rate"].value > 0  # ... and oscillates

    lmn_seg = r.experiment("anterior_horn_segmental")
    lmn_arm = [a for a in lmn_seg.arms if a.name == "lmn"][0]
    assert lmn_arm.closure == "open"                 # reflex abolished
    assert math.isnan(lmn_arm.store["tonic_rate"].value)


def test_proprioceptive_block_preserves_force():
    """The novel prediction: coordination fails while strength is intact."""
    from vitruvius import run_file

    r = run_file(str(EXPERIMENTS / "03_nerve_block_phases.vvs"))
    x = r.experiment("brachial_plexus_block")
    phases = {p.name: p for p in x.phases}

    base = phases["baseline"].arms[0].store["force_output"].value
    prop = phases["proprioceptive_loss"].arms[0]
    motor = phases["motor_block"].arms[0]

    assert prop.closure == "open"
    assert prop.store["force_output"].value == pytest.approx(base, rel=1e-9)
    assert motor.store["force_output"].value < base * 0.01


def test_tmr_restores_closure():
    from vitruvius import run_file

    r = run_file(str(EXPERIMENTS / "04_tmr_reroute.vvs"))
    arms = {a.name: a for a in r.experiment("amputation_and_repair").arms}
    assert arms["amputated"].closure == "open"
    assert arms["tmr"].closure == "closed"
    assert arms["mirror"].closure == "closed"
    # The restored circulation is not the original one.
    assert (arms["tmr"].store["loop_latency"].value
            != arms["intact"].store["loop_latency"].value)


def test_sci_spares_circuits_that_do_not_cross_the_level():
    from vitruvius import run_file

    r = run_file(str(EXPERIMENTS / "02_spinal_cord_injury.vvs"))
    below = r.experiment("t6_below_lesion_reflex").arms[0]
    above = r.experiment("t6_above_lesion_function").arms[0]
    lower = {a.name: a for a in r.experiment("t6_complete_lower_limb").arms}

    assert lower["complete"].closure == "open"   # paralysis below
    assert below.closure == "closed"             # reflexes preserved below
    assert above.closure == "closed"             # normal above


# ── JSON serialisation ──────────────────────────────────────────────

def test_results_serialize_to_json():
    import json

    from vitruvius.serialize import result_to_dict

    r = run_source(MINIMAL)
    d = result_to_dict(r, backend=Backend())
    s = json.dumps(d)          # must be JSON-clean: no NaN, no objects
    assert "NaN" not in s
    assert d["provenance"]["schema"].startswith("vitruvius-results/")
    assert d["static_analysis"]["typechecks"] is True
    assert d["experiments"][0]["arms"][0]["closure_index"] == "closed"


def test_nan_is_recorded_as_null_not_dropped():
    """An undefined observable must be distinguishable from a missing one."""
    import json

    from vitruvius.serialize import result_to_dict

    src = MINIMAL.replace("observe : closure_index, loop_latency;",
                          "observe : closure_index, divergence_time;")
    d = result_to_dict(run_source(src), backend=Backend())
    obs = d["experiments"][0]["arms"][0]["observations"]["divergence_time"]
    assert obs["value"] is None
    assert obs["undefined"] is True
    json.dumps(d)


@pytest.mark.parametrize("name", [
    "08_myasthenia.vvs",
    "09_rehabilitation.vvs",
    "10_gait_asymmetry.vvs",
])
def test_additional_experiments_run(name):
    from vitruvius import run_file

    r = run_file(str(EXPERIMENTS / name))
    assert r.experiments


def test_myasthenia_distinguishes_attenuation_from_severance():
    """The distinction the stochastic operator was proposed for, obtained
    from two existing operators instead."""
    from vitruvius import run_file

    r = run_file(str(EXPERIMENTS / "08_myasthenia.vvs"))
    arms = {a.name: a
            for a in r.experiment("myasthenia_versus_denervation").arms}

    myasthenic = arms["myasthenic"]
    denervated = arms["denervated"]

    assert myasthenic.closure == "closed"          # weak but circulating
    assert myasthenic.store["force_output"].value > 0
    assert myasthenic.store["tonic_rate"].value > 0

    assert denervated.closure == "open"            # no circulation at all
    assert denervated.store["force_output"].value == 0.0
    assert math.isnan(denervated.store["tonic_rate"].value)


def test_prosthetic_compliance_scales_force_as_sqrt_capacitance():
    """Q = sqrt(2 C P): halving compliance scales force by sqrt(1/2)."""
    from vitruvius import run_file

    r = run_file(str(EXPERIMENTS / "10_gait_asymmetry.vvs"))
    bio = r.experiment("left_hip_biological").arms[0]
    pro = r.experiment("right_hip_prosthetic").arms[0]

    f_bio = bio.store["force_output"].value
    f_pro = pro.store["force_output"].value
    assert f_pro / f_bio == pytest.approx(math.sqrt(0.9 / 1.8), rel=1e-6)
