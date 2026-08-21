"""Reading the wearable running dataset, and establishing what it supports.

The dataset is real: Under Armour connected footwear and a running watch,
recorded over several sessions. Two file shapes are present, and they support
very different analyses, so the loader reports what each one can carry rather
than presenting them as interchangeable.

    sprintActigraphy.json   1 Hz records with stance time, vertical
                            oscillation, step length, cadence, speed, and a
                            phase label per sample. This is the file inverse
                            dynamics is grounded in: it has the two
                            quantities -- contact time and flight time --
                            that determine the vertical impulse.

    underarmour.json        per-5-metre series: speed, stride length, ground
    workoutN.json           contact time, stride cadence, and (in some) a
                            foot strike index. No vertical oscillation, so
                            flight time must be inferred rather than measured.

── What the channels actually mean ───────────────────────────────────

`foot_strike_angle` is reported as whole degrees and nothing finer: the
sessions span 1-6, 5-10, and 3-9 degrees respectively, so it is a genuine
angle quantised to 1 degree rather than a category. The quantisation is
coarse relative to the spread -- six distinct values across a whole session --
so it is used to CLASSIFY strides (forefoot / midfoot / rearfoot bands) and
to report a distribution, never differentiated or fed into a torque as if it
carried sub-degree information.

`power` is null in every record of the sprint file and `accumulated_power` is
pinned at 65535 (the uint16 sentinel for "no data"), so neither is usable.

── Unit checks, run on load ──────────────────────────────────────────

Cadence could be strides/min or steps/min, and stride length could be a full
stride or a single step; the pairing changes every derived force by 2x. The
loader does not guess -- it tests the identity v = SL * cadence / 60 against
the recorded speed and reports the residual. On this dataset the stride
reading agrees to better than 1%, and the step reading is off by a factor of
two, so the convention is established from the data itself.
"""

from __future__ import annotations

import json
import math
import statistics
from dataclasses import dataclass, field
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "web" / "public" / "angle"

# Records whose step_length is far below the session median are startup
# artefacts: the watch reports a partial step on the first sample after the
# metric becomes available.
STEP_LENGTH_ARTEFACT_RATIO = 0.5


@dataclass
class Series:
    """One named channel: x in the file's own abscissa, y as recorded."""

    name: str
    x: list[float]
    y: list[float]
    unit: str = ""

    def __len__(self) -> int:
        return len(self.y)


@dataclass
class UnitCheck:
    """The result of testing a unit convention against a redundant identity."""

    identity: str
    convention: str
    median_relative_error: float
    accepted: bool
    note: str = ""


@dataclass
class Session:
    """A loaded session, with what it can and cannot support."""

    name: str
    source: str
    kind: str                      # "sprint" | "distance"
    n: int
    series: dict[str, Series] = field(default_factory=dict)
    unit_checks: list[UnitCheck] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    # sprint only
    phases: list[str] = field(default_factory=list)
    time_s: list[float] = field(default_factory=list)
    # "run" | "walk" | "mixed"; decided from the duty factor, see _classify_gait
    gait: str = "unknown"
    # the length/cadence convention established from the data, or None
    convention: dict | None = None

    def has(self, *names: str) -> bool:
        return all(n in self.series for n in names)

    def col(self, name: str) -> list[float]:
        return self.series[name].y


# ── unit establishment ───────────────────────────────────────────────


# The three conventions a device might use. Each is v = L * cadence / k with
# a different meaning for L and cadence, and they differ by factors of two, so
# picking the wrong one scales every derived force accordingly.
STRIDE_CONVENTIONS = (
    # k,   length is,  cadence counts,  steps per cadence unit
    (30.0, "step", "strides/min", 2),
    (60.0, "stride", "strides/min", 2),
    (60.0, "step", "steps/min", 1),
    (120.0, "stride", "steps/min", 1),
)


def _check_stride_convention(speed, length_m, cadence) -> tuple[list[UnitCheck], dict | None]:
    """Establish, from the data, what the length and cadence channels mean.

    v = L * cadence / k must hold. The candidate conventions differ only in k
    (and in what L and cadence denote), so testing the identity against the
    recorded speed decides between them without any assumption about the
    manufacturer's convention -- which is worth doing, because this dataset
    uses DIFFERENT conventions in different files.

    Returns the checks and the accepted convention, or None if none closes.
    """
    checks: list[UnitCheck] = []
    best = None
    seen = set()
    for k, what_len, what_cad, steps_per_unit in STRIDE_CONVENTIONS:
        key = (k, what_len, what_cad)
        if key in seen:
            continue
        seen.add(key)
        errs = []
        for v, L, c in zip(speed, length_m, cadence):
            if not v or v <= 0 or not c:
                continue
            errs.append(abs(L * c / k - v) / v)
        if not errs:
            continue
        med = statistics.median(errs)
        accepted = med < 0.05
        checks.append(
            UnitCheck(
                identity="v = length * cadence / k",
                convention=f"length is one {what_len}, cadence in {what_cad} (k={k:g})",
                median_relative_error=med,
                accepted=accepted,
                note=(
                    f"accepted: closes to {med * 100:.1f}%"
                    if accepted
                    else f"rejected: {med * 100:.0f}% median error"
                ),
            )
        )
        if accepted and (best is None or med < best["error"]):
            best = {
                "k": k,
                "length_is": what_len,
                "cadence_counts": what_cad,
                "steps_per_cadence_unit": steps_per_unit,
                "error": med,
            }
    return checks, best


def _check_contact_fraction(stance_ms, cadence_spm) -> UnitCheck:
    """Stance time must be a plausible fraction of the step period.

    At cadence c steps/min the step period is 60000/c ms. A duty factor
    outside (0, 1) would mean the two channels are in different units.
    """
    fracs = []
    for st, c in zip(stance_ms, cadence_spm):
        if not c or st is None:
            continue
        step_ms = 60000.0 / c
        fracs.append(st / step_ms)
    med = statistics.median(fracs) if fracs else float("nan")
    # A duty factor near or above 1 is not a unit error -- it is walking,
    # where double support makes contact fill the step. Only a value far
    # outside [0, 1.3] would indicate mismatched units.
    ok = 0.05 < med < 1.3
    return UnitCheck(
        identity="duty factor = stance_time / step_period",
        convention="stance_time in ms, cadence in steps/min",
        median_relative_error=float("nan"),
        accepted=ok,
        note=(
            f"median duty factor {med:.3f}"
            + ("" if ok else " -- outside [0.05, 1.3], units are inconsistent")
        ),
    )


def _classify_gait(stance_ms, cadence_strides) -> str:
    """Running, walking, or mixed -- decided PER SAMPLE, not on an average.

    Running has a flight phase, so contact occupies less than the step period.
    Walking has double support, so contact meets or exceeds it. The boundary
    is a definition, not a tunable threshold: a step with no flight is not
    running.

    Classifying on the median duty factor alone would be wrong for an
    interval session, where a mixture of walking and running samples produces
    a median near 1 that describes neither. So the fractions are counted and
    a session is called mixed unless one mode clearly dominates.
    """
    flights = []
    for st, c in zip(stance_ms, cadence_strides):
        if not c:
            continue
        step_s = 30.0 / c                 # half a stride, seconds
        flights.append(step_s - st / 1000.0)
    if not flights:
        return "unknown"
    n = len(flights)
    running = sum(1 for f in flights if f > 0)
    frac = running / n
    if frac >= 0.9:
        return "run"
    if frac <= 0.1:
        return "walk"
    return "mixed"


def gait_fractions(stance_ms, cadence_strides) -> tuple[int, int]:
    """(samples with flight, total) -- the evidence behind the classification."""
    tot = run = 0
    for st, c in zip(stance_ms, cadence_strides):
        if not c:
            continue
        tot += 1
        if 30.0 / c - st / 1000.0 > 0:
            run += 1
    return run, tot


def _gait_note(gait: str, running: int = 0, total: int = 0) -> str:
    frac = f"{running}/{total} samples have a flight phase" if total else ""
    if gait == "walk":
        return (
            f"{frac}: this session is WALKING. Without flight there is no "
            "aerial phase to close the vertical impulse over, so the running "
            "impulse relation does not apply and those samples are excluded."
        )
    if gait == "run":
        return f"{frac}: this session is RUNNING."
    return (
        f"{frac}: this session MIXES walking and running -- an interval "
        "session. Samples without flight are excluded from the running "
        "analysis rather than the whole session being accepted or rejected."
    )


# ── loaders ──────────────────────────────────────────────────────────

UNITS = {
    "speed": "m/s",
    "stride_length": "m",
    "ground_contact_time": "ms",
    "stride_cadence": "strides/min",
    "distance": "m",
    "elevation": "m",
    "heartrate": "bpm",
    "cadence": "steps/min",
    "foot_strike_angle": "index 1-6",
}


def load_distance_session(path: Path) -> Session:
    """A per-distance session: channels keyed by name, each [[x, y], ...]."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    s = Session(name=path.stem, source=str(path), kind="distance", n=0)

    for key, pairs in raw.items():
        if not isinstance(pairs, list) or not pairs:
            continue
        if not isinstance(pairs[0], list) or len(pairs[0]) != 2:
            s.notes.append(f"channel '{key}' is not an [x, y] series; skipped")
            continue
        xs, ys = [], []
        for p in pairs:
            if p[1] is None or isinstance(p[1], (dict, list)):
                continue
            xs.append(float(p[0]))
            ys.append(float(p[1]))
        if ys:
            s.series[key] = Series(key, xs, ys, UNITS.get(key, ""))
    s.n = max((len(v) for v in s.series.values()), default=0)

    if s.has("speed", "stride_length", "stride_cadence"):
        # Channels can differ in length; compare on the shared abscissa.
        sp, sl, cd = _align(s, "speed", "stride_length", "stride_cadence")
        checks, best = _check_stride_convention(sp, sl, cd)
        s.unit_checks += checks
        s.convention = best
        if best is None:
            s.notes.append(
                "no length/cadence convention closes the identity v = L*c/k; "
                "derived forces from this session would be unfounded"
            )

    if s.has("ground_contact_time", "stride_cadence"):
        gct, cd = _align(s, "ground_contact_time", "stride_cadence")
        # stride_cadence is strides/min; steps/min is twice that.
        s.unit_checks.append(_check_contact_fraction(gct, [c * 2 for c in cd]))
        s.gait = _classify_gait(gct, cd)
        s.notes.append(_gait_note(s.gait, *gait_fractions(gct, cd)))

    if "foot_strike_angle" in s.series:
        vals = sorted({int(v) for v in s.col("foot_strike_angle")})
        s.notes.append(
            f"foot_strike_angle spans {vals[0]}-{vals[-1]} deg in whole-degree "
            f"steps ({len(vals)} distinct values). Quantisation is coarse "
            "relative to the spread, so it is used for classification and "
            "distribution only, never differentiated."
        )
    return s


def load_sprint(path: Path) -> Session:
    """The 1 Hz sprint record: a list of per-sample dicts."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    s = Session(name=path.stem, source=str(path), kind="sprint", n=len(raw))

    s.time_s = [float(r["time"]) for r in raw]
    s.phases = [str(r.get("segments", "")) for r in raw]

    channels = {
        "speed": "m/s",
        "cadence": "steps/min",
        "stance_time": "ms",
        "stance_time_percent": "%",
        "vertical_oscillation": "mm",
        "step_length": "mm",
        "heart_rate": "bpm",
        "altitude": "m",
        "dist": "m",
    }
    for key, unit in channels.items():
        xs, ys = [], []
        for r in raw:
            v = r.get(key)
            if v is None:
                continue
            xs.append(float(r["time"]))
            ys.append(float(v))
        if ys:
            s.series[key] = Series(key, xs, ys, unit)

    # Startup artefact: step_length reports a partial step on the first
    # sample after the metric becomes available.
    if "step_length" in s.series:
        sl = s.series["step_length"]
        med = statistics.median(sl.y)
        keep = [(x, y) for x, y in zip(sl.x, sl.y) if y > med * STEP_LENGTH_ARTEFACT_RATIO]
        dropped = len(sl.y) - len(keep)
        if dropped:
            s.series["step_length"] = Series(
                sl.name, [k[0] for k in keep], [k[1] for k in keep], sl.unit
            )
            s.notes.append(
                f"dropped {dropped} step_length sample(s) below "
                f"{STEP_LENGTH_ARTEFACT_RATIO:.0%} of the session median "
                f"({med:.0f} mm): a partial first step, not a stride"
            )

    # Establish the convention here too, rather than assuming the watch uses
    # the same one as the shoe pod. On this dataset it does NOT: the sprint
    # file reports step_length as a single STEP with cadence in strides/min
    # (k=30), while the shoe files report a full stride with cadence in
    # strides/min (k=60).
    if s.has("speed", "step_length", "cadence"):
        sp, sl_mm, cd = _align(s, "speed", "step_length", "cadence")
        checks, best = _check_stride_convention(sp, [v / 1000.0 for v in sl_mm], cd)
        s.unit_checks += checks
        s.convention = best
        if best is None:
            s.notes.append(
                "no length/cadence convention closes the identity v = L*c/k; "
                "derived forces from this session would be unfounded"
            )

    if s.has("stance_time", "cadence"):
        st, cd = _align(s, "stance_time", "cadence")
        # Convert the cadence channel to strides/min using the ESTABLISHED
        # convention rather than a guess.
        per_unit = (s.convention or {}).get("steps_per_cadence_unit", 2)
        strides_per_min = [c * per_unit / 2.0 for c in cd if c]
        st_ok = [x for x, c in zip(st, cd) if c]
        s.unit_checks.append(
            _check_contact_fraction(st_ok, [c * 2 for c in strides_per_min])
        )
        s.gait = _classify_gait(st_ok, strides_per_min)
        s.notes.append(_gait_note(s.gait, *gait_fractions(st_ok, strides_per_min)))

    for dead, why in (
        ("power", "null in every record"),
        ("accumulated_power", "pinned at 65535, the uint16 no-data sentinel"),
    ):
        vals = {r.get(dead) for r in raw}
        if vals <= {None} or vals == {65535}:
            s.notes.append(f"channel '{dead}' is unusable: {why}")

    return s


def _align(s: Session, *names: str) -> tuple[list[float], ...]:
    """Channels sampled on a common abscissa, intersected on x."""
    keys = [set(s.series[n].x) for n in names]
    common = sorted(set.intersection(*keys))
    out = []
    for n in names:
        lookup = dict(zip(s.series[n].x, s.series[n].y))
        out.append([lookup[x] for x in common])
    return tuple(out)


def load_all(directory: Path = DATA) -> dict[str, Session]:
    """Every session in the dataset directory."""
    out: dict[str, Session] = {}
    for p in sorted(directory.glob("*.json")):
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            print(f"  skipping {p.name}: {exc}")
            continue
        session = load_sprint(p) if isinstance(raw, list) else load_distance_session(p)
        out[session.name] = session
    return out


def describe(s: Session) -> str:
    """A short report of what a session carries and what it supports."""
    lines = [f"{s.name}  ({s.kind}, n={s.n})"]
    for name, ser in s.series.items():
        lo, hi = min(ser.y), max(ser.y)
        lines.append(f"    {name:<22} n={len(ser):<4} [{lo:.4g} .. {hi:.4g}] {ser.unit}")
    for c in s.unit_checks:
        mark = "ok " if c.accepted else "NO "
        lines.append(f"    [{mark}] {c.convention}: {c.note}")
    for n in s.notes:
        lines.append(f"    ! {n}")
    return "\n".join(lines)
