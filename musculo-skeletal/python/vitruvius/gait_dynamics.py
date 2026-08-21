"""Inverse dynamics from wearable running data.

What a shoe pod and a watch record is not a force plate. There is no measured
ground reaction force here, no joint kinematics, no EMG. What there IS, per
step, is contact time, step frequency, vertical oscillation, and speed -- and
those four are enough to close the vertical impulse, because over one whole
stride at steady speed the body's vertical momentum returns to where it
started.

That single conservation statement is the whole basis of what follows, and it
is worth stating plainly because it bounds the claims:

    Over one stride, the vertical impulse from the ground must cancel the
    impulse from gravity.

        F_mean_vertical * t_contact = m * g * t_stride

    so the mean vertical GRF during contact is

        F_mean = m * g * (t_stride / t_contact) = m * g / duty

This is exact for steady running, not a model fit. Everything downstream that
needs a peak rather than a mean requires a waveform assumption, and each such
assumption is named at the point it is used.

── What is derived, and on what ─────────────────────────────────────

    mean vertical GRF     impulse-momentum over a stride          exact
    peak vertical GRF     + half-sine contact waveform            assumed
    flight time           t_stride - 2 * t_contact                exact given cadence
    vertical stiffness    peak force / vertical displacement      standard
    leg stiffness         peak force / leg compression            + geometry
    joint moments         + segment inertia from the BSP tables   quasi-static
    mechanical work       from CoM excursion and speed change     exact

── What is NOT derived ──────────────────────────────────────────────

Muscle forces are not identified from these data. A joint moment is the NET
moment; splitting it between agonist and antagonist is indeterminate without
EMG or an optimisation criterion, and this module does not pretend otherwise.
The muscle model in `hill.py` runs FORWARD from an activation, and its output
is compared against the measured joint moment rather than fitted to it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

G = 9.80665


@dataclass
class Stride:
    """One stride's worth of derived mechanics."""

    t: float                      # session time, s
    speed: float                  # m/s
    contact_s: float
    stride_s: float
    duty: float                   # contact / stride, per LEG
    flight_s: float
    step_length_m: float
    # Total pelvis excursion per step, as the device reports it: the stance
    # dip plus the flight arc.
    vertical_osc_m: float | None
    # The flight arc alone, from ballistics.
    flight_rise_m: float
    # The stance-phase dip: what the leg spring actually compresses through.
    stance_dip_m: float

    # derived
    grf_mean_bw: float            # mean vertical GRF during contact, body weights
    grf_peak_bw: float            # peak, under the half-sine assumption
    vertical_stiffness: float | None      # kN/m
    leg_stiffness: float | None           # kN/m
    leg_compression_m: float | None
    # energetics
    vertical_work_j: float | None
    horizontal_power_w: float | None

    phase: str = ""


@dataclass
class GaitAnalysis:
    session: str
    mass_kg: float
    leg_length_m: float
    strides: list[Stride] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)

    def col(self, name: str) -> list[float]:
        return [getattr(s, name) for s in self.strides if getattr(s, name) is not None]


# ── the exact part ───────────────────────────────────────────────────


def mean_vertical_grf(duty: float) -> float:
    """Mean vertical GRF during contact, in body weights.

    From impulse-momentum over one stride at steady speed: the ground must
    return exactly the vertical momentum gravity removes. `duty` is contact
    time over stride time for ONE leg.

    No waveform is assumed here -- this is the time-average over contact, and
    it is what the conservation law determines.
    """
    if not (0 < duty <= 1):
        raise ValueError(f"duty factor must be in (0, 1], got {duty}")
    return 1.0 / duty


def peak_vertical_grf(duty: float, waveform: str = "half-sine") -> float:
    """Peak vertical GRF, in body weights.

    The peak is NOT determined by the impulse alone -- it depends on the shape
    of the contact waveform, which these sensors do not record. Two standard
    shapes are offered and the choice is reported as an assumption:

        half-sine   F(t) = F_peak sin(pi t / t_c);  mean = 2/pi * peak
                    the usual first approximation for running, Blickhan (1989)
        triangular  mean = 1/2 * peak; a cruder bound

    The half-sine is the default because it is the shape the spring-mass
    model of running produces, but the factor is stated so a reader can
    substitute their own.
    """
    mean = mean_vertical_grf(duty)
    if waveform == "half-sine":
        return mean * math.pi / 2.0
    if waveform == "triangular":
        return mean * 2.0
    raise ValueError(f"unknown waveform {waveform!r}")


def flight_time(stride_s: float, contact_s: float) -> float:
    """Flight time per step.

    A stride is two steps. Each step is one contact plus one flight, so

        t_flight = t_stride / 2 - t_contact

    A negative result means contact exceeds the step period, i.e. double
    support: that is walking, and the caller must not treat it as running.
    """
    return stride_s / 2.0 - contact_s


def vertical_displacement_from_flight(flight_s: float) -> float:
    """CoM rise during flight, from ballistics: h = g t^2 / 8.

    During flight the CoM is a projectile. Taking off and landing at the same
    height, the rise is g (t/2)^2 / 2 = g t^2 / 8.

    This is an INDEPENDENT estimate of vertical oscillation, so where the
    sensor also reports it the two can be compared -- and they measure
    different things: the sensor reports total CoM excursion including the
    compression during contact, while this is the flight arc alone.
    """
    return G * flight_s * flight_s / 8.0


# ── the part that needs geometry ─────────────────────────────────────


def leg_compression(
    leg_length_m: float, contact_s: float, speed: float, vertical_disp_m: float
) -> float:
    """Leg compression during contact, from the spring-mass geometry.

    The leg sweeps a half-angle theta while the foot is planted:

        theta = asin(v * t_c / (2 * L0))

    and the CoM drops by the vertical oscillation plus the shortening implied
    by that sweep:

        dL = dy + L0 (1 - cos theta)

    after McMahon & Cheng (1990). The sweep term is what distinguishes leg
    stiffness from vertical stiffness; without it the two would be the same
    number.
    """
    ratio = speed * contact_s / (2.0 * leg_length_m)
    if ratio >= 1.0:
        # The foot would have to travel further than the leg is long.
        return float("nan")
    theta = math.asin(ratio)
    return vertical_disp_m + leg_length_m * (1.0 - math.cos(theta))


def stiffness(peak_force_n: float, deflection_m: float) -> float:
    """k = F_peak / deflection, in kN/m."""
    if deflection_m <= 0:
        return float("nan")
    return peak_force_n / deflection_m / 1000.0


# ── analysis over a session ──────────────────────────────────────────


def analyse_running(
    *,
    session_name: str,
    time_s: list[float],
    speed: list[float],
    contact_ms: list[float],
    cadence_steps_min: list[float],
    step_length_m: list[float] | None = None,
    vertical_osc_mm: list[float] | None = None,
    phases: list[str] | None = None,
    mass_kg: float = 83.0,
    leg_length_m: float = 0.93,
    waveform: str = "half-sine",
) -> GaitAnalysis:
    """Per-sample gait mechanics for a running session.

    Every input is a channel the device actually recorded. `mass_kg` and
    `leg_length_m` come from the subject's anthropometry, not from the device.
    """
    out = GaitAnalysis(session_name, mass_kg, leg_length_m)
    out.assumptions.append(
        f"peak vertical GRF uses a {waveform} contact waveform "
        f"(mean-to-peak factor {peak_vertical_grf(0.5, waveform) / mean_vertical_grf(0.5):.4f}); "
        "the sensors do not record the waveform"
    )
    out.assumptions.append(
        f"body mass {mass_kg} kg and leg length {leg_length_m:.3f} m are "
        "subject anthropometry, not device data"
    )
    out.assumptions.append(
        "stiffness uses the STANCE dip (measured oscillation minus the "
        "ballistic flight arc), which is what the leg spring compresses "
        "through; using the total oscillation would overstate compression"
    )

    bw = mass_kg * G
    n = min(len(time_s), len(speed), len(contact_ms), len(cadence_steps_min))
    skipped_walk = 0

    for i in range(n):
        c_ms = contact_ms[i]
        cad = cadence_steps_min[i]
        v = speed[i]
        if not cad or not c_ms or v <= 0:
            continue

        stride_s = 120.0 / cad          # two steps per stride
        contact_s = c_ms / 1000.0
        duty = contact_s / stride_s
        fl = flight_time(stride_s, contact_s)

        if fl <= 0:
            # Double support: the running impulse relation does not apply.
            skipped_walk += 1
            continue

        # Vertical excursion decomposes into two parts that are NOT
        # interchangeable:
        #
        #   flight arc   the ballistic rise between takeoff and apex
        #   stance dip   how far the CoM falls while the foot is planted
        #
        # A device's "vertical oscillation" is the TOTAL per-step excursion,
        # i.e. their sum. The spring-mass model needs the stance dip alone --
        # that is the displacement the leg spring compresses through -- so
        # passing the total inflates leg compression and understates
        # stiffness. On this dataset the total is 9.9 cm against a 2.7 cm
        # flight arc, so the difference is not a rounding matter.
        flight_rise = vertical_displacement_from_flight(fl)
        measured_total = None
        if vertical_osc_mm is not None and i < len(vertical_osc_mm) and vertical_osc_mm[i]:
            measured_total = vertical_osc_mm[i] / 1000.0
            dip = max(measured_total - flight_rise, 1e-4)
        else:
            # Without a measurement, the flight arc is the only handle we
            # have; a symmetric spring-mass step makes the dip comparable.
            dip = flight_rise

        grf_mean = mean_vertical_grf(duty)
        grf_peak = peak_vertical_grf(duty, waveform)
        peak_n = grf_peak * bw

        # Vertical stiffness is defined against the stance displacement too.
        k_vert = stiffness(peak_n, dip)
        dl = leg_compression(leg_length_m, contact_s, v, dip)
        k_leg = stiffness(peak_n, dl) if dl == dl and dl > 0 else None

        sl = (
            step_length_m[i]
            if step_length_m is not None and i < len(step_length_m) and step_length_m[i]
            else v * stride_s / 2.0
        )

        out.strides.append(
            Stride(
                t=time_s[i],
                speed=v,
                contact_s=contact_s,
                stride_s=stride_s,
                duty=duty,
                flight_s=fl,
                step_length_m=sl,
                vertical_osc_m=measured_total,
                flight_rise_m=flight_rise,
                stance_dip_m=dip,
                grf_mean_bw=grf_mean,
                grf_peak_bw=grf_peak,
                vertical_stiffness=k_vert,
                leg_stiffness=k_leg,
                leg_compression_m=dl if dl == dl else None,
                # Work to raise the CoM each step, both legs per stride.
                # Work to raise the CoM through its total excursion.
                vertical_work_j=mass_kg * G * (measured_total or flight_rise),
                horizontal_power_w=None,
                phase=phases[i] if phases and i < len(phases) else "",
            )
        )

    if skipped_walk:
        out.notes.append(
            f"{skipped_walk} sample(s) had no flight phase (double support) and "
            "were excluded: the running impulse relation does not hold in walking"
        )
    if not out.strides:
        out.notes.append("no running strides found in this session")
    return out


def horizontal_power(analysis: GaitAnalysis) -> None:
    """Fill in horizontal power from the speed record.

    Power to change kinetic energy is d/dt (m v^2 / 2). This needs successive
    samples, so it is a second pass rather than a per-sample quantity, and it
    is left None where the time step is unknown or zero.
    """
    s = analysis.strides
    for i in range(1, len(s)):
        dt = s[i].t - s[i - 1].t
        if dt <= 0:
            continue
        dke = 0.5 * analysis.mass_kg * (s[i].speed ** 2 - s[i - 1].speed ** 2)
        s[i].horizontal_power_w = dke / dt


# ── joint moments, quasi-static ──────────────────────────────────────


@dataclass
class JointMoment:
    joint: str
    region: str
    moment_nm: float
    moment_arm_m: float
    derivation: str


def stance_joint_moments(
    peak_grf_n: float,
    *,
    ankle_arm_m: float = 0.055,
    knee_arm_m: float = 0.045,
    hip_arm_m: float = 0.070,
) -> list[JointMoment]:
    """Peak sagittal joint moments during stance, quasi-statically.

    At the instant of peak vertical force, the moment about each joint is the
    ground reaction force times its perpendicular distance from the joint
    centre. This is QUASI-STATIC: it ignores segment angular acceleration and
    the inertia of the shank and thigh, which at peak force are small
    relative to the GRF term but not zero.

    The moment arms are population values for mid-stance in running, and they
    are the dominant uncertainty here -- they vary with strike pattern, shoe,
    and speed. They are parameters rather than constants for that reason.
    """
    return [
        JointMoment("ankle", "right-ankle", peak_grf_n * ankle_arm_m, ankle_arm_m,
                    "GRF x perpendicular distance to the ankle joint centre"),
        JointMoment("knee", "right-knee", peak_grf_n * knee_arm_m, knee_arm_m,
                    "GRF x perpendicular distance to the knee joint centre"),
        JointMoment("hip", "right-thigh", peak_grf_n * hip_arm_m, hip_arm_m,
                    "GRF x perpendicular distance to the hip joint centre"),
    ]
