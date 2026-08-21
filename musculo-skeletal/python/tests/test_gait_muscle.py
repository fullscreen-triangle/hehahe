"""Tests for the wearable loader, inverse dynamics, and the Hill model.

The load-bearing ones check that the analysis REFUSES what the data cannot
support: a walking session must not be run through the running impulse
relation, and a unit convention must be established rather than assumed.
"""

from __future__ import annotations

import math

import pytest

from vitruvius import gait_dynamics as gd
from vitruvius import hill
from vitruvius.wearable import load_all


# ── dataset ──────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def sessions():
    return load_all()


def test_all_sessions_load(sessions):
    assert len(sessions) == 6
    assert "sprintActigraphy" in sessions
    assert "underarmour" in sessions


def test_conventions_are_established_from_data_not_assumed(sessions):
    """The two devices use DIFFERENT conventions; both must be discovered."""
    sprint = sessions["sprintActigraphy"].convention
    shoe = sessions["underarmour"].convention
    assert sprint is not None and shoe is not None
    # The watch reports a single step with cadence in strides/min.
    assert sprint["k"] == 30
    assert sprint["length_is"] == "step"
    # The shoe pod reports a whole stride with cadence in strides/min.
    assert shoe["k"] == 60
    assert shoe["length_is"] == "stride"
    # If these were the same, one of them would be wrong by a factor of two.
    assert sprint["k"] != shoe["k"]


def test_accepted_convention_closes_the_identity(sessions):
    for name in ("sprintActigraphy", "underarmour", "workout2", "workout4"):
        c = sessions[name].convention
        assert c is not None, name
        assert c["error"] < 0.05, (name, c["error"])


def test_rejected_conventions_are_recorded(sessions):
    """A convention that fails must be reported, not silently dropped."""
    s = sessions["underarmour"]
    rejected = [c for c in s.unit_checks if not c.accepted and "length is" in c.convention]
    assert rejected, "no rejected convention recorded"
    for c in rejected:
        assert c.median_relative_error > 0.05


def test_gait_classification(sessions):
    assert sessions["sprintActigraphy"].gait == "run"
    assert sessions["workout2"].gait == "run"
    assert sessions["workout4"].gait == "run"
    # The Under Armour session is an interval session: most samples have no
    # flight phase but a substantial minority do. Calling it either "run" or
    # "walk" would misdescribe it, and classifying on the median duty factor
    # (which is 1.02) would land on a value that describes neither mode.
    assert sessions["underarmour"].gait == "mixed"


def test_mixed_session_reports_the_evidence(sessions):
    """The classification must show its counts, not just its verdict."""
    s = sessions["underarmour"]
    note = next(n for n in s.notes if "flight phase" in n)
    assert "MIXES" in note
    assert "/199" in note


def test_dead_channels_reported(sessions):
    s = sessions["sprintActigraphy"]
    joined = " ".join(s.notes)
    assert "power" in joined and "unusable" in joined


def test_step_length_artefact_dropped(sessions):
    s = sessions["sprintActigraphy"]
    assert any("step_length" in n and "partial" in n for n in s.notes)
    # And the surviving values are all plausible strides.
    assert min(s.col("step_length")) > 1000


# ── inverse dynamics: the exact part ─────────────────────────────────


def test_mean_grf_is_the_impulse_relation():
    """F_mean = mg / duty is exact, not fitted."""
    assert gd.mean_vertical_grf(0.5) == pytest.approx(2.0)
    assert gd.mean_vertical_grf(0.25) == pytest.approx(4.0)
    # Duty of 1 means permanent contact: the ground carries exactly body weight.
    assert gd.mean_vertical_grf(1.0) == pytest.approx(1.0)


def test_mean_grf_rejects_impossible_duty():
    with pytest.raises(ValueError):
        gd.mean_vertical_grf(0.0)
    with pytest.raises(ValueError):
        gd.mean_vertical_grf(1.5)


def test_peak_depends_on_the_assumed_waveform():
    """The peak is NOT determined by the impulse; the shape matters."""
    half = gd.peak_vertical_grf(0.3, "half-sine")
    tri = gd.peak_vertical_grf(0.3, "triangular")
    assert half == pytest.approx(gd.mean_vertical_grf(0.3) * math.pi / 2)
    assert tri == pytest.approx(gd.mean_vertical_grf(0.3) * 2.0)
    assert tri > half


def test_flight_time_is_stride_minus_two_contacts():
    # 0.6 s stride, 0.2 s contact -> 0.1 s flight per step
    assert gd.flight_time(0.6, 0.2) == pytest.approx(0.1)
    # Contact filling the whole step means no flight: walking.
    assert gd.flight_time(0.6, 0.3) == pytest.approx(0.0)
    assert gd.flight_time(0.6, 0.35) < 0


def test_ballistic_rise_matches_projectile_motion():
    """h = g t^2 / 8 for a flight of duration t."""
    t = 0.15
    assert gd.vertical_displacement_from_flight(t) == pytest.approx(gd.G * t * t / 8)
    # Independently: rise = v0^2/(2g) with v0 = g t / 2
    v0 = gd.G * t / 2
    assert gd.vertical_displacement_from_flight(t) == pytest.approx(v0 * v0 / (2 * gd.G))


def test_leg_compression_exceeds_vertical_displacement():
    """The sweep term is what separates leg from vertical stiffness."""
    dy = 0.06
    dl = gd.leg_compression(0.93, 0.20, 5.0, dy)
    assert dl > dy
    # Zero speed removes the sweep entirely.
    assert gd.leg_compression(0.93, 0.20, 0.0, dy) == pytest.approx(dy)


# ── inverse dynamics on the real sprint ──────────────────────────────


@pytest.fixture(scope="module")
def sprint_analysis(sessions):
    s = sessions["sprintActigraphy"]
    lookup = lambda name: dict(zip(s.series[name].x, s.series[name].y))  # noqa: E731
    st, vo = lookup("stance_time"), lookup("vertical_oscillation")
    times = s.series["speed"].x
    per_unit = s.convention["steps_per_cadence_unit"]
    a = gd.analyse_running(
        session_name="sprint",
        time_s=times,
        speed=s.series["speed"].y,
        contact_ms=[st.get(t, 0) for t in times],
        cadence_steps_min=[c * per_unit for c in s.series["cadence"].y],
        vertical_osc_mm=[vo.get(t, 0) for t in times],
        phases=s.phases,
        mass_kg=83.0,
        leg_length_m=0.93,
    )
    gd.horizontal_power(a)
    return a


def test_sprint_produces_physiological_forces(sprint_analysis):
    """Peak vertical GRF in sprinting is a few body weights, not tens."""
    peaks = sprint_analysis.col("grf_peak_bw")
    assert peaks, "no strides analysed"
    med = sorted(peaks)[len(peaks) // 2]
    # Sprinting peaks are commonly 3-6 BW. A value above 8 would mean the
    # cadence convention was misread -- which is exactly the bug this catches.
    assert 2.0 < med < 8.0, med


def test_sprint_flight_times_are_physiological(sprint_analysis):
    fl = sprint_analysis.col("flight_s")
    med = sorted(fl)[len(fl) // 2]
    # Sprint flight is on the order of 0.1-0.2 s per step.
    assert 0.05 < med < 0.25, med


def test_sprint_duty_factors_are_physiological(sprint_analysis):
    duty = sprint_analysis.col("duty")
    med = sorted(duty)[len(duty) // 2]
    # Duty per stride at sprint pace is around 0.25-0.35.
    assert 0.15 < med < 0.45, med


def test_leg_stiffness_is_physiological(sprint_analysis):
    ks = [s for s in sprint_analysis.col("leg_stiffness") if s == s]
    med = sorted(ks)[len(ks) // 2]
    # Running leg stiffness is typically 7-30 kN/m.
    assert 3.0 < med < 60.0, med


def test_phases_survive_into_the_analysis(sprint_analysis):
    phases = {s.phase for s in sprint_analysis.strides}
    assert "drive" in phases and "peak" in phases


def test_faster_running_has_shorter_contact(sprint_analysis):
    """A real relation the data must show if the analysis is sound."""
    fast = [s for s in sprint_analysis.strides if s.speed > 5.2]
    slow = [s for s in sprint_analysis.strides if s.speed < 4.6]
    assert fast and slow
    mean = lambda xs: sum(xs) / len(xs)  # noqa: E731
    assert mean([s.contact_s for s in fast]) < mean([s.contact_s for s in slow])


def test_mixed_session_excludes_the_flightless_samples(sessions):
    """Samples with no flight must be dropped, not silently analysed."""
    s = sessions["underarmour"]
    lookup = dict(zip(s.series["ground_contact_time"].x, s.series["ground_contact_time"].y))
    times = s.series["speed"].x
    a = gd.analyse_running(
        session_name="mixed",
        time_s=times,
        speed=s.series["speed"].y,
        contact_ms=[lookup.get(t, 0) for t in times],
        cadence_steps_min=[c * 2 for c in s.series["stride_cadence"].y],
        mass_kg=83.0,
    )
    # Some strides survive, but far from all of them.
    assert 0 < len(a.strides) < len(times)
    assert any("double support" in n for n in a.notes)
    # Every surviving stride must genuinely have flight.
    assert all(st.flight_s > 0 for st in a.strides)


def test_assumptions_are_stated(sprint_analysis):
    joined = " ".join(sprint_analysis.assumptions)
    assert "waveform" in joined
    assert "anthropometry" in joined


# ── Hill muscle model ────────────────────────────────────────────────


P = hill.MuscleParameters()


def test_force_length_peaks_at_optimum():
    assert hill.fl_ce(P.lmopt, P) == pytest.approx(1.0)
    assert hill.fl_ce(0.8 * P.lmopt, P) < 1.0
    assert hill.fl_ce(1.2 * P.lmopt, P) < 1.0


def test_parallel_element_is_slack_below_optimum():
    assert hill.fl_pe(0.9 * P.lmopt, P) == 0.0
    assert hill.fl_pe(P.lmopt, P) == 0.0
    assert hill.fl_pe(1.2 * P.lmopt, P) > 0.0
    # And it rises steeply.
    assert hill.fl_pe(1.4 * P.lmopt, P) > 4 * hill.fl_pe(1.2 * P.lmopt, P)


def test_tendon_reaches_fm0_at_its_reference_strain():
    """F_SE must be 1.0 at eps = epst0: that is what epst0 MEANS."""
    lt = P.ltslack * (1 + P.epst0)
    assert hill.fl_se(lt, P) == pytest.approx(1.0, rel=1e-3)


def test_tendon_toe_and_linear_regions_join_smoothly():
    """The exact OpenSim constants exist to make the slope continuous."""
    eps = P.epsttoe
    h = 1e-6
    lo = (hill.fl_se(P.ltslack * (1 + eps), P) - hill.fl_se(P.ltslack * (1 + eps - h), P)) / h
    hi = (hill.fl_se(P.ltslack * (1 + eps + h), P) - hill.fl_se(P.ltslack * (1 + eps), P)) / h
    assert lo == pytest.approx(hi, rel=1e-3)


def test_tendon_constants_match_the_exact_expressions():
    # The paper's rounded values are 0.609*epst0 and 1.712/epst0.
    assert P.epsttoe == pytest.approx(0.609 * P.epst0, rel=1e-2)
    assert P.ktlin == pytest.approx(1.712 / P.epst0, rel=1e-2)


def test_force_velocity_signs():
    """Below the isometric force the fibre shortens; above it, it lengthens."""
    fl = 1.0
    iso = 1.0 * fl
    assert hill.velocity_from_force(0.5 * iso, 1.0, fl, P) < 0     # concentric
    assert hill.velocity_from_force(1.2 * iso, 1.0, fl, P) > 0     # eccentric
    assert hill.velocity_from_force(iso, 1.0, fl, P) == pytest.approx(0.0, abs=1e-9)


def test_eccentric_asymptote_does_not_diverge():
    """The OpenSim guard is the whole reason this is finite."""
    fl = 1.0
    plateau = 1.0 * fl * P.fmlen
    v_at = hill.velocity_from_force(plateau, 1.0, fl, P)
    v_beyond = hill.velocity_from_force(plateau * 1.5, 1.0, fl, P)
    assert math.isfinite(v_at) and math.isfinite(v_beyond)
    # Beyond the plateau the velocity saturates rather than exploding.
    assert abs(v_beyond) < 100 * P.vmmax * P.lmopt


def test_shortening_saturates_at_vmax():
    """At zero force the fibre shortens at its maximum velocity."""
    v = hill.velocity_from_force(0.0, 1.0, 1.0, P)
    vmax = P.vmmax * P.lmopt
    assert -vmax * 1.05 < v < 0


def test_forward_and_inverse_force_velocity_agree():
    """fv_ce must invert velocity_from_force."""
    fl = 0.9
    for a in (0.3, 1.0):
        for fm in (0.1, 0.5, 0.9, 1.1):
            v = hill.velocity_from_force(fm * a * fl, a, fl, P)
            back = hill.fv_ce(v, a, fl, P)
            assert back == pytest.approx(fm * a * fl, rel=2e-2), (a, fm, v)


def test_activation_rises_faster_than_it_falls():
    """t_act < t_deact, so the same gap activates faster than it relaxes."""
    up = hill.d_activation(0.5, 1.0, P)
    down = hill.d_activation(0.5, 0.0, P)
    assert up > 0 > down
    assert abs(up) > abs(down)


def test_equilibrium_start_has_no_initial_transient():
    """Starting off equilibrium injects a purely numerical transient."""
    lmt = 0.313
    a = 0.5
    lm = hill.equilibrium_fibre_length(lmt, a, P)
    v = hill.d_fibre_length(lm, lmt, a, P)
    assert abs(v) < 1e-3, v


def test_simulation_runs_and_conserves_the_path():
    lmt = 0.313
    p = hill.MuscleParameters()
    lm0 = hill.equilibrium_fibre_length(lmt, p.u_min, p)
    r = hill.simulate(
        lmt_of_t=lambda t: lmt,
        excitation_of_t=lambda t: 1.0 if t > 0.05 else p.u_min,
        p=p, lm0=lm0, t0=0.0, t1=0.4, dt=5e-4,
    )
    assert len(r.states) > 100
    for s in r.states:
        # The path must close: L_MT = L_T + L_M cos(alpha), by construction.
        assert s.lt + s.lm * math.cos(s.alpha) == pytest.approx(s.lmt, abs=1e-9)
        assert math.isfinite(s.force_n)
    # An isometric contraction must develop force.
    assert max(r.col("force_n")) > 0.3 * p.fm0


def test_simulation_step_size_is_converged():
    """Halving the step must not move the answer: otherwise dt is a parameter."""
    lmt = 0.313
    p = hill.MuscleParameters()
    lm0 = hill.equilibrium_fibre_length(lmt, p.u_min, p)
    peaks = []
    for dt in (5e-4, 2.5e-4):
        r = hill.simulate(
            lmt_of_t=lambda t: lmt,
            excitation_of_t=lambda t: 1.0 if t > 0.05 else p.u_min,
            p=p, lm0=lm0, t0=0.0, t1=0.3, dt=dt,
        )
        peaks.append(max(r.col("force_n")))
    assert abs(peaks[0] - peaks[1]) / peaks[1] < 1e-3, peaks


# ── minimum jerk ─────────────────────────────────────────────────────


def test_minimum_jerk_endpoints():
    pos, vel, acc, _ = hill.minimum_jerk(0.0, 1.0, 1.0, 0.0)
    assert (pos, vel, acc) == pytest.approx((0.0, 0.0, 0.0))
    pos, vel, acc, _ = hill.minimum_jerk(0.0, 1.0, 1.0, 1.0)
    assert (pos, vel, acc) == pytest.approx((1.0, 0.0, 0.0))


def test_minimum_jerk_is_symmetric_about_the_midpoint():
    a = hill.minimum_jerk(0.0, 1.0, 1.0, 0.25)[0]
    b = hill.minimum_jerk(0.0, 1.0, 1.0, 0.75)[0]
    assert a + b == pytest.approx(1.0)


def test_minimum_jerk_peak_speed_ratio_is_15_over_8():
    """v_peak = 1.875 dx/d exactly; empirical reaching gives about 1.75."""
    d, dx = 1.0, 1.0
    vs = [hill.minimum_jerk(0.0, dx, d, i / 2000 * d)[1] for i in range(2001)]
    peak = max(vs)
    mean = dx / d
    assert peak / mean == pytest.approx(hill.MINJERK_PEAK_MEAN_RATIO, rel=1e-4)
    # And the model genuinely overshoots the empirical value.
    assert hill.MINJERK_PEAK_MEAN_RATIO > hill.MINJERK_EMPIRICAL_RATIO


def test_minimum_jerk_endpoint_jerk_is_nonzero():
    """Minimising integrated squared jerk does NOT make jerk vanish at the ends."""
    _, _, _, j0 = hill.minimum_jerk(0.0, 1.0, 1.0, 0.0)
    _, _, _, j1 = hill.minimum_jerk(0.0, 1.0, 1.0, 1.0)
    assert j0 == pytest.approx(60.0)
    assert j1 == pytest.approx(60.0)


def test_vertical_excursion_decomposes(sprint_analysis):
    """The device reports one number; it is the sum of two distinct parts."""
    for s in sprint_analysis.strides:
        assert s.vertical_osc_m is not None
        # total = stance dip + flight arc, by construction
        assert s.stance_dip_m + s.flight_rise_m == pytest.approx(s.vertical_osc_m, abs=1e-9)
        assert s.stance_dip_m > 0 and s.flight_rise_m > 0


def test_stance_dip_dominates_the_flight_arc_at_sprint_pace(sprint_analysis):
    """A real finding: the flight arc is the SMALLER part."""
    dips = [s.stance_dip_m for s in sprint_analysis.strides]
    arcs = [s.flight_rise_m for s in sprint_analysis.strides]
    med = lambda xs: sorted(xs)[len(xs) // 2]  # noqa: E731
    assert med(dips) > med(arcs)
    # About 7 cm against 2.7 cm on this dataset.
    assert 1.5 < med(dips) / med(arcs) < 6.0


def test_stiffness_uses_the_stance_dip_not_the_total(sprint_analysis):
    """Using the total oscillation would understate stiffness."""
    s = sprint_analysis.strides[0]
    peak_n = s.grf_peak_bw * sprint_analysis.mass_kg * gd.G
    assert s.vertical_stiffness == pytest.approx(
        gd.stiffness(peak_n, s.stance_dip_m), rel=1e-9
    )
    # And the total would give a materially different (lower) number.
    wrong = gd.stiffness(peak_n, s.vertical_osc_m)
    assert wrong < s.vertical_stiffness * 0.9


def test_stance_dip_assumption_is_stated(sprint_analysis):
    assert any("STANCE dip" in a for a in sprint_analysis.assumptions)
