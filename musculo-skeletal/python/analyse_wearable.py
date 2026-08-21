"""Inverse dynamics and muscle simulation from the wearable running dataset.

    python analyse_wearable.py                 # analyse, write JSON, draw panels
    python analyse_wearable.py --no-figures    # numbers only
    python analyse_wearable.py --mass 83 --stature 1.85

The chain, and what each link rests on:

    1. LOAD          establish each file's length/cadence convention from the
                     data itself, and classify gait per sample
    2. INVERSE       vertical impulse over a stride -> mean GRF (exact)
       DYNAMICS      + a contact waveform -> peak GRF (assumed, stated)
                     + spring-mass geometry -> leg and vertical stiffness
    3. ANTHROPOMETRY de Leva segment masses and inertias for the subject
    4. JOINT         quasi-static moments at peak force, then the ankle
       MOMENTS       moment divided by an Achilles moment arm -> the tendon
                     force the plantarflexors must carry
    5. MUSCLE        a Thelen (2003) Hill unit driven over one stance phase,
                     asked whether it CAN produce that force
    6. MINIMUM JERK  the swing-phase trajectory the data implies, against the
                     minimum-jerk prediction

Step 5 is the interesting one. The muscle model is not fitted to the data:
it is run forward from an excitation and its output compared against the
force inverse dynamics says the tendon carried. Agreement is a result;
disagreement is also a result, and is reported rather than tuned away.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path

from vitruvius import gait_dynamics as gd
from vitruvius import hill
from vitruvius.wearable import Session, load_all

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"

# Subject anthropometry. Not device data -- stated wherever it is used.
DEFAULT_MASS_KG = 83.0
DEFAULT_STATURE_M = 1.85

# Achilles tendon moment arm about the ankle. Population value; the dominant
# uncertainty in converting an ankle moment into a tendon force, so it is a
# parameter rather than a constant.
ACHILLES_ARM_M = 0.050


# ── 1. loading and the running analysis ──────────────────────────────


def running_analysis(s: Session, mass_kg: float, leg_length_m: float) -> gd.GaitAnalysis | None:
    """Run the inverse dynamics on whichever channels a session provides."""
    if s.convention is None:
        return None
    per_unit = s.convention["steps_per_cadence_unit"]

    if s.kind == "sprint":
        if not s.has("stance_time", "cadence", "speed"):
            return None
        look = lambda n: dict(zip(s.series[n].x, s.series[n].y))  # noqa: E731
        st, vo = look("stance_time"), look("vertical_oscillation")
        times = s.series["speed"].x
        return gd.analyse_running(
            session_name=s.name,
            time_s=times,
            speed=s.series["speed"].y,
            contact_ms=[st.get(t, 0.0) for t in times],
            cadence_steps_min=[c * per_unit for c in s.series["cadence"].y],
            vertical_osc_mm=[vo.get(t, 0.0) for t in times],
            phases=s.phases,
            mass_kg=mass_kg,
            leg_length_m=leg_length_m,
        )

    if not s.has("ground_contact_time", "stride_cadence", "speed"):
        return None
    gct = dict(zip(s.series["ground_contact_time"].x, s.series["ground_contact_time"].y))
    times = s.series["speed"].x
    # `distance` is the abscissa here, so "time" is really distance travelled.
    return gd.analyse_running(
        session_name=s.name,
        time_s=times,
        speed=s.series["speed"].y,
        contact_ms=[gct.get(t, 0.0) for t in times],
        cadence_steps_min=[c * per_unit for c in s.series["stride_cadence"].y],
        mass_kg=mass_kg,
        leg_length_m=leg_length_m,
    )


# ── 4/5. from a joint moment to a muscle ─────────────────────────────


def stance_muscle_simulation(
    peak_grf_n: float,
    contact_s: float,
    p: hill.MuscleParameters,
    achilles_arm_m: float = ACHILLES_ARM_M,
) -> dict:
    """Can a plantarflexor produce the force stance requires?

    The ankle moment at peak vertical force, divided by the Achilles moment
    arm, is the tendon force the plantarflexors must carry. The muscle model
    is then driven over one stance phase and asked whether it reaches that
    force -- forward, from an excitation, NOT fitted to the target.

    The muscle-tendon path is prescribed as a stretch-shorten cycle: the unit
    lengthens through the first 40% of stance as the ankle dorsiflexes under
    load, then shortens through push-off. That shape is an assumption about
    ankle kinematics, which these sensors do not record, and it is reported
    as one.
    """
    moments = gd.stance_joint_moments(peak_grf_n)
    ankle = next(m for m in moments if m.joint == "ankle")
    required_n = ankle.moment_nm / achilles_arm_m

    lmt0 = 0.313
    stretch = 0.012          # metres of MTU lengthening during loading

    def lmt(t: float) -> float:
        if contact_s <= 0:
            return lmt0
        u = min(max(t / contact_s, 0.0), 1.0)
        # Lengthen to 40% of stance, then shorten below rest through push-off.
        if u <= 0.4:
            return lmt0 + stretch * (u / 0.4)
        return lmt0 + stretch * (1.0 - (u - 0.4) / 0.6) - stretch * 0.6 * ((u - 0.4) / 0.6)

    def excite(t: float) -> float:
        # Pre-activation before contact, full drive through stance, release at
        # toe-off: the standard plantarflexor pattern.
        if contact_s <= 0:
            return p.u_min
        u = t / contact_s
        if u < 0.0:
            return 0.2
        if u < 0.85:
            return 1.0
        return p.u_min

    # Start the fibre at equilibrium for the activation it ACTUALLY begins
    # with. Initialising at equilibrium for a different activation leaves the
    # first step inconsistent, which shows up as a single spurious sample at
    # several times the maximum shortening velocity -- a numerical artefact
    # that looks like an eccentric spike.
    a0 = excite(0.0)
    lm0 = hill.equilibrium_fibre_length(lmt(0.0), a0, p)
    sim = hill.simulate(
        lmt_of_t=lmt, excitation_of_t=excite, p=p,
        lm0=lm0, a0=a0, t0=0.0, t1=contact_s, dt=2.5e-4,
    )
    produced = max(sim.col("force_n")) if sim.states else 0.0

    return {
        "ankle_moment_nm": ankle.moment_nm,
        "achilles_arm_m": achilles_arm_m,
        "required_tendon_force_n": required_n,
        "produced_peak_force_n": produced,
        "ratio_produced_required": produced / required_n if required_n else float("nan"),
        "fm0_n": p.fm0,
        "sufficient": produced >= required_n,
        "assumption": (
            "muscle-tendon path prescribed as a stretch-shorten cycle "
            f"({stretch * 1000:.0f} mm lengthening to 40% of stance, then "
            "shortening); ankle kinematics are not recorded by these sensors"
        ),
        "series": {
            "t": sim.col("t"),
            "force_n": sim.col("force_n"),
            "lm": sim.col("lm"),
            "a": sim.col("a"),
            "f_ce": sim.col("f_ce"),
            "f_pe": sim.col("f_pe"),
            "vm": sim.col("vm"),
        },
    }


# ── 6. swing phase against minimum jerk ──────────────────────────────


def swing_minimum_jerk(step_length_m: float, swing_s: float, n: int = 200) -> dict:
    """The swing foot's trajectory, against the minimum-jerk prediction.

    During swing the foot travels forward by roughly two step lengths
    relative to the body. Minimum jerk predicts a specific speed profile with
    a peak-to-mean ratio of exactly 15/8 = 1.875, while reaching studies
    report about 1.75. Whether locomotion obeys the same criterion as
    reaching is a real question, and the ratio is the discriminator.
    """
    travel = 2.0 * step_length_m
    ts = [swing_s * i / (n - 1) for i in range(n)]
    pos, vel, acc, jerk = [], [], [], []
    for t in ts:
        px, vx, ax, jx = hill.minimum_jerk(0.0, travel, swing_s, t)
        pos.append(px)
        vel.append(vx)
        acc.append(ax)
        jerk.append(jx)
    mean_v = travel / swing_s
    return {
        "travel_m": travel,
        "swing_s": swing_s,
        "t": ts,
        "position_m": pos,
        "velocity_ms": vel,
        "acceleration_ms2": acc,
        "jerk_ms3": jerk,
        "peak_velocity_ms": max(vel),
        "mean_velocity_ms": mean_v,
        "peak_mean_ratio": max(vel) / mean_v,
        "model_ratio": hill.MINJERK_PEAK_MEAN_RATIO,
        "empirical_reaching_ratio": hill.MINJERK_EMPIRICAL_RATIO,
    }


# ── report ───────────────────────────────────────────────────────────


def q(xs: list[float], p: float) -> float:
    if not xs:
        return float("nan")
    ys = sorted(xs)
    i = min(len(ys) - 1, max(0, int(round(p * (len(ys) - 1)))))
    return ys[i]


def summarise(a: gd.GaitAnalysis) -> dict:
    return {
        "n_strides": len(a.strides),
        "speed_ms": {"min": q(a.col("speed"), 0), "median": q(a.col("speed"), 0.5),
                     "max": q(a.col("speed"), 1)},
        "contact_ms": {"median": q(a.col("contact_s"), 0.5) * 1e3},
        "flight_ms": {"median": q(a.col("flight_s"), 0.5) * 1e3},
        "duty": {"median": q(a.col("duty"), 0.5)},
        "grf_mean_bw": {"median": q(a.col("grf_mean_bw"), 0.5)},
        "grf_peak_bw": {"median": q(a.col("grf_peak_bw"), 0.5),
                        "max": q(a.col("grf_peak_bw"), 1)},
        "vertical_stiffness_kn_m": {"median": q(a.col("vertical_stiffness"), 0.5)},
        "leg_stiffness_kn_m": {"median": q(a.col("leg_stiffness"), 0.5)},
        "leg_compression_cm": {"median": q(a.col("leg_compression_m"), 0.5) * 100},
        "assumptions": a.assumptions,
        "notes": a.notes,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mass", type=float, default=DEFAULT_MASS_KG)
    ap.add_argument("--stature", type=float, default=DEFAULT_STATURE_M)
    ap.add_argument("--achilles-arm", type=float, default=ACHILLES_ARM_M)
    ap.add_argument("--no-figures", action="store_true")
    args = ap.parse_args()

    # Leg length for the spring-mass model: standing greater-trochanter
    # height above the ground.
    #
    # Winter's Figure 4.1 labels a "hip height" of 0.720H, but that fraction
    # cannot be the trochanter: it would put the hip at 1.33 m on a 1.85 m
    # subject, well above the ~0.93-0.98 m that anthropometry gives. The
    # 0.720H label belongs to a higher landmark. Rather than propagate a leg
    # length that is 40% too long -- which would inflate every leg-stiffness
    # figure -- the trochanter fraction used here is 0.530H, the value that
    # reproduces measured hip heights, and it is stated as such.
    LEG_LENGTH_FRACTION = 0.530
    leg_length_m = LEG_LENGTH_FRACTION * args.stature

    print(f"Subject: {args.mass} kg, {args.stature} m  "
          f"(leg {leg_length_m:.3f} m = {LEG_LENGTH_FRACTION}H)")
    print("Anthropometry is subject data, not device data.\n")

    sessions = load_all()
    record: dict = {
        "schema": "vitruvius-wearable/1",
        "subject": {"mass_kg": args.mass, "stature_m": args.stature,
                    "leg_length_m": leg_length_m},
        "sessions": {},
    }

    print("-- sessions " + "-" * 60)
    analyses: dict[str, gd.GaitAnalysis] = {}
    for name, s in sessions.items():
        conv = s.convention
        conv_s = (
            f"k={conv['k']:g} ({conv['length_is']}, {conv['cadence_counts']}, "
            f"{conv['error'] * 100:.1f}%)"
            if conv else "none established"
        )
        print(f"{name:<18} {s.kind:<9} n={s.n:<4} gait={s.gait:<8} {conv_s}")
        entry: dict = {
            "kind": s.kind,
            "n": s.n,
            "gait": s.gait,
            "convention": conv,
            "channels": {k: {"n": len(v), "unit": v.unit} for k, v in s.series.items()},
            "unit_checks": [
                {"convention": c.convention, "accepted": c.accepted, "note": c.note}
                for c in s.unit_checks
            ],
            "notes": s.notes,
        }
        a = running_analysis(s, args.mass, leg_length_m)
        if a and a.strides:
            gd.horizontal_power(a)
            analyses[name] = a
            entry["running"] = summarise(a)
            entry["strides"] = [
                {
                    "t": st.t, "speed": st.speed, "contact_s": st.contact_s,
                    "flight_s": st.flight_s, "duty": st.duty,
                    "grf_mean_bw": st.grf_mean_bw, "grf_peak_bw": st.grf_peak_bw,
                    "vertical_stiffness": st.vertical_stiffness,
                    "leg_stiffness": st.leg_stiffness,
                    "leg_compression_m": st.leg_compression_m,
                    "vertical_osc_m": st.vertical_osc_m,
                    "phase": st.phase,
                }
                for st in a.strides
            ]
        elif a:
            entry["running"] = {"n_strides": 0, "notes": a.notes}
        record["sessions"][name] = entry
    print()

    # The sprint is the session with the full channel set.
    sprint = analyses.get("sprintActigraphy")
    if sprint is None:
        print("no session supports the running analysis; stopping")
        return 1

    print("-- sprint inverse dynamics " + "-" * 45)
    s = summarise(sprint)
    print(f"  strides            {s['n_strides']}")
    print(f"  speed              {s['speed_ms']['min']:.2f} .. {s['speed_ms']['max']:.2f} m/s")
    print(f"  contact / flight   {s['contact_ms']['median']:.0f} / {s['flight_ms']['median']*1e0:.0f} ms")
    print(f"  duty factor        {s['duty']['median']:.3f}")
    print(f"  mean vertical GRF  {s['grf_mean_bw']['median']:.2f} BW   (exact, impulse-momentum)")
    print(f"  peak vertical GRF  {s['grf_peak_bw']['median']:.2f} BW   (half-sine waveform assumed)")
    print(f"  leg compression    {s['leg_compression_cm']['median']:.1f} cm")
    print(f"  vertical stiffness {s['vertical_stiffness_kn_m']['median']:.1f} kN/m")
    print(f"  leg stiffness      {s['leg_stiffness_kn_m']['median']:.1f} kN/m")
    for x in s["assumptions"]:
        print(f"  ! {x}")
    print()

    # Per phase, since the sprint file labels them.
    by_phase: dict[str, list[gd.Stride]] = {}
    for st in sprint.strides:
        by_phase.setdefault(st.phase or "unlabelled", []).append(st)
    print("  phase          n   v(m/s)  contact  duty   peak GRF  k_leg")
    phase_rows = {}
    for ph, group in by_phase.items():
        row = {
            "n": len(group),
            "speed": statistics.mean(g.speed for g in group),
            "contact_ms": statistics.mean(g.contact_s for g in group) * 1e3,
            "duty": statistics.mean(g.duty for g in group),
            "grf_peak_bw": statistics.mean(g.grf_peak_bw for g in group),
            "leg_stiffness": statistics.mean(
                g.leg_stiffness for g in group if g.leg_stiffness
            ) if any(g.leg_stiffness for g in group) else float("nan"),
        }
        phase_rows[ph] = row
        print(f"  {ph:<13} {row['n']:>2}   {row['speed']:>5.2f}   {row['contact_ms']:>5.0f}ms  "
              f"{row['duty']:>5.3f}  {row['grf_peak_bw']:>6.2f}   {row['leg_stiffness']:>5.1f}")
    record["sessions"]["sprintActigraphy"]["by_phase"] = phase_rows
    print()

    # Joint moments at the hardest stride.
    hardest = max(sprint.strides, key=lambda x: x.grf_peak_bw)
    peak_n = hardest.grf_peak_bw * args.mass * gd.G
    print("-- joint moments at peak force " + "-" * 41)
    print(f"  stride at t={hardest.t:.0f}s, {hardest.speed:.2f} m/s, "
          f"peak GRF {peak_n:.0f} N ({hardest.grf_peak_bw:.2f} BW)")
    moments = gd.stance_joint_moments(peak_n)
    for m in moments:
        print(f"  {m.joint:<6} {m.moment_nm:>7.1f} N m   arm {m.moment_arm_m * 100:.1f} cm   [{m.region}]")
    print("  ! quasi-static: segment angular acceleration is neglected")
    record["joint_moments"] = {
        "stride_t": hardest.t,
        "peak_grf_n": peak_n,
        "moments": [
            {"joint": m.joint, "region": m.region, "moment_nm": m.moment_nm,
             "moment_arm_m": m.moment_arm_m, "derivation": m.derivation}
            for m in moments
        ],
        "note": "quasi-static; segment angular acceleration neglected",
    }
    print()

    # Muscle simulation.
    print("-- plantarflexor simulation " + "-" * 44)
    p = hill.MuscleParameters(name="plantarflexor")
    ms = stance_muscle_simulation(peak_n, hardest.contact_s, p, args.achilles_arm)
    print(f"  ankle moment            {ms['ankle_moment_nm']:.1f} N m")
    print(f"  Achilles arm            {ms['achilles_arm_m'] * 100:.1f} cm")
    print(f"  required tendon force   {ms['required_tendon_force_n']:.0f} N")
    print(f"  model peak force        {ms['produced_peak_force_n']:.0f} N   "
          f"(F_max = {ms['fm0_n']:.0f} N)")
    print(f"  produced / required     {ms['ratio_produced_required']:.2f}")
    if ms["sufficient"]:
        print("  -> the modelled muscle CAN carry the stance load")
    else:
        deficit = ms["required_tendon_force_n"] / max(ms["produced_peak_force_n"], 1e-9)
        print(f"  -> the modelled muscle CANNOT: it falls short by {deficit:.1f}x.")
        print("     A single generic unit is not the whole plantarflexor group,")
        print("     and F_max here is the Nigg & Herzog exercise value, not a")
        print("     measured soleus. The shortfall sizes what is missing rather")
        print("     than being tuned away.")
    print(f"  ! {ms['assumption']}")
    record["muscle"] = {k: v for k, v in ms.items() if k != "series"}
    record["muscle"]["series_length"] = len(ms["series"]["t"])
    print()

    # Minimum jerk over the swing phase.
    swing_s = hardest.stride_s / 2 - hardest.contact_s + hardest.contact_s
    mj = swing_minimum_jerk(hardest.step_length_m, hardest.stride_s - hardest.contact_s)
    print("-- swing phase vs minimum jerk " + "-" * 41)
    print(f"  swing duration          {mj['swing_s'] * 1e3:.0f} ms")
    print(f"  foot travel             {mj['travel_m']:.2f} m")
    print(f"  peak / mean speed       {mj['peak_mean_ratio']:.3f}")
    print(f"  minimum-jerk prediction {mj['model_ratio']:.3f} (= 15/8, exact)")
    print(f"  reaching studies report {mj['empirical_reaching_ratio']:.2f}")
    print(f"  -> the criterion overshoots the empirical value by "
          f"{(mj['model_ratio'] / mj['empirical_reaching_ratio'] - 1) * 100:.1f}%")
    record["minimum_jerk"] = {k: v for k, v in mj.items()
                              if k not in ("t", "position_m", "velocity_ms",
                                           "acceleration_ms2", "jerk_ms3")}
    print()

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "wearable_analysis.json"
    out.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(f"wrote {out.relative_to(HERE)}")

    if not args.no_figures:
        from figures.make_wearable_panels import draw_all
        print()
        draw_all(record, sprint, analyses, ms, mj)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
