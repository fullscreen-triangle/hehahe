"""A Thelen (2003) Hill-type muscle-tendon unit.

Implemented from Thelen, J Biomech Eng 125(1):70-77 (2003), with the
singularity guards that OpenSim's `Thelen2003Muscle` adds and that the paper
does not state. Those guards are not cosmetic: without the eccentric
asymptote cap the force-velocity inverse is singular at the eccentric
plateau, and the integrator walks straight into it.

── Structure ─────────────────────────────────────────────────────────

    L_MT = L_T + L_M cos(alpha)        muscle-tendon path
    F_M  = F_CE + F_PE                 fibre force
    F_T  = F_SE = F_M cos(alpha)       tendon carries the fibre force

The state integrated is the fibre length L_M; activation is a separate
first-order state. Equilibrium between tendon and fibre gives the fibre
velocity, which is the ODE.

── One convention that bites ─────────────────────────────────────────

Thelen's force-velocity expression returns fibre VELOCITY given force, and it
already contains activation and the force-length factor. Multiplying by them
again -- which is correct for a model whose f_v is a pure multiplier, such as
McLean 2003 -- double-counts. Only the Thelen form is implemented here, so
the two cannot be mixed by accident.

Sign convention: v_M < 0 is shortening (concentric).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class MuscleParameters:
    """Thelen (2003) parameters.

    The defaults are the Nigg & Herzog (2006) chapter 4 exercise values used
    by the BMClab notebooks. They are NOT a named muscle: do not present them
    as soleus or vastus without substituting real values.
    """

    name: str = "generic"
    fm0: float = 7400.0          # maximum isometric force, N
    lmopt: float = 0.093         # optimal fibre length, m
    ltslack: float = 0.223       # tendon slack length, m
    alpha0: float = 0.0          # pennation angle at optimal fibre length, rad

    # force-length, CE
    gammal: float = 0.45         # Gaussian shape factor (NB: no factor of 2)
    # force-length, PE
    kpe: float = 5.0
    epsm0: float = 0.6           # PE strain at fm0
    # force-length, SE
    epst0: float = 0.04          # tendon strain at fm0
    kttoe: float = 3.0
    fttoe: float = 0.33
    # force-velocity
    vmmax: float = 10.0          # maximum shortening velocity, lmopt/s
    fmlen: float = 1.4           # eccentric force plateau, xfm0
    af: float = 0.25             # Hill shape factor
    # activation dynamics
    t_act: float = 0.015
    t_deact: float = 0.050
    u_min: float = 0.01

    # ── guards, from OpenSim rather than from Thelen (2003) ──
    #
    # As fm approaches a*fl*fmlen the denominator b of the velocity
    # expression goes to zero and vm diverges. OpenSim freezes b at 95% of
    # the plateau. Without this the integrator diverges at the eccentric
    # limit; with it the model saturates, which is the physical behaviour.
    asy_e_thresh: float = 0.95
    # fl -> 0 as the fibre shortens; clamp so the ODE stays finite.
    lm_min_frac: float = 0.1
    # cos(alpha) -> 0 as the fibre rotates; clamp.
    cos_alpha_min: float = 0.1

    @property
    def epsttoe(self) -> float:
        """Strain at the toe/linear transition.

        The exact OpenSim expression, not the paper's rounded 0.609*epst0.
        """
        e = math.e
        return 0.99 * self.epst0 * e**3 / (1.66 * e**3 - 0.67)

    @property
    def ktlin(self) -> float:
        """Linear-region tendon stiffness, exact OpenSim expression."""
        return 0.67 / (self.epst0 - self.epsttoe)

    @property
    def width(self) -> float:
        """Constant fibre width, Scott & Winter (1991)."""
        return self.lmopt * math.sin(self.alpha0)


# ── the four constitutive curves ─────────────────────────────────────


def fl_ce(lm: float, p: MuscleParameters) -> float:
    """Normalised active force-length of the contractile element.

    Gaussian in normalised fibre length. Note gammal sits in the denominator
    without a factor of two, so it is not a variance.
    """
    lm_bar = lm / p.lmopt
    return math.exp(-((lm_bar - 1.0) ** 2) / p.gammal)


def fl_pe(lm: float, p: MuscleParameters) -> float:
    """Normalised passive force-length of the parallel element.

    Zero below slack (taken as the optimal fibre length), exponential above.
    """
    lm_bar = lm / p.lmopt
    if lm_bar <= 1.0:
        return 0.0
    num = math.exp(p.kpe * (lm_bar - 1.0) / p.epsm0) - 1.0
    return num / (math.exp(p.kpe) - 1.0)


def fl_se(lt: float, p: MuscleParameters) -> float:
    """Normalised tendon force-length: exponential toe then linear."""
    if p.ltslack <= 0:
        return 0.0
    eps = (lt - p.ltslack) / p.ltslack
    if eps <= 0:
        return 0.0
    if eps <= p.epsttoe:
        return (p.fttoe / (math.exp(p.kttoe) - 1.0)) * (
            math.exp(p.kttoe * eps / p.epsttoe) - 1.0
        )
    return p.ktlin * (eps - p.epsttoe) + p.fttoe


def velocity_from_force(fm_bar: float, a: float, fl: float, p: MuscleParameters) -> float:
    """Fibre velocity from normalised fibre force. Thelen (2003) inverse f-v.

    Returns m/s, negative for shortening. Activation and force-length are
    already inside this expression -- do not apply them again.
    """
    vmmax = p.vmmax * p.lmopt          # lmopt/s -> m/s
    a = max(a, p.u_min)
    afl = a * fl

    if fm_bar <= 0.0:
        # Undocumented in the paper; taken from the reference implementation.
        b = afl
    elif fm_bar <= afl:
        # shortening
        b = afl + fm_bar / p.af
    else:
        # lengthening, with the eccentric asymptote frozen at asy_e_thresh
        plateau = afl * p.fmlen
        f_eff = min(fm_bar, plateau * p.asy_e_thresh)
        b = (2.0 + 2.0 / p.af) * (plateau - f_eff) / (p.fmlen - 1.0)

    if b == 0.0:
        return 0.0
    return (0.25 + 0.75 * a) * vmmax * (fm_bar - afl) / b


def fv_ce(vm: float, a: float, fl: float, p: MuscleParameters) -> float:
    """Normalised fibre force from velocity: the forward force-velocity.

    The symbolic inverse of `velocity_from_force`. Used when the velocity is
    known (e.g. driven by a measured length trajectory) rather than the
    force.
    """
    vmmax = p.vmmax * p.lmopt
    a = max(a, p.u_min)
    af, fmlen = p.af, p.fmlen
    if vm <= 0.0:
        num = af * a * fl * (4.0 * vm + vmmax * (3.0 * a + 1.0))
        den = -4.0 * vm + vmmax * af * (3.0 * a + 1.0)
    else:
        k = 3.0 * a * fmlen - 3.0 * a + fmlen - 1.0
        num = a * fl * (af * vmmax * k + 8.0 * vm * fmlen * (af + 1.0))
        den = af * vmmax * k + 8.0 * vm * (af + 1.0)
    return num / den if den else 0.0


def pennation(lm: float, p: MuscleParameters) -> float:
    """Pennation angle at fibre length lm, constant-width model."""
    if p.alpha0 == 0.0:
        return 0.0
    w = p.width
    if lm <= 0:
        return math.asin(1.0)
    return math.asin(min(1.0, w / lm))


def cos_pennation(lm: float, p: MuscleParameters) -> float:
    return max(p.cos_alpha_min, math.cos(pennation(lm, p)))


# ── activation dynamics ──────────────────────────────────────────────


def d_activation(a: float, u: float, p: MuscleParameters) -> float:
    """da/dt with Thelen's state-dependent time constant."""
    a = min(max(a, p.u_min), 1.0)
    u = min(max(u, p.u_min), 1.0)
    if u > a:
        tau = p.t_act * (0.5 + 1.5 * a)
    else:
        tau = p.t_deact / (0.5 + 1.5 * a)
    return (u - a) / tau


# ── the muscle-tendon ODE ────────────────────────────────────────────


def d_fibre_length(lm: float, lmt: float, a: float, p: MuscleParameters) -> float:
    """dL_M/dt from tendon-fibre force equilibrium.

    The tendon length follows from the path and the fibre; the tendon force
    it carries must equal the fibre force projected along the tendon, which
    fixes the CE force and hence the velocity.
    """
    lm = max(lm, p.lm_min_frac * p.lmopt)
    ca = cos_pennation(lm, p)
    lt = lmt - lm * ca
    f_se = fl_se(lt, p)
    f_pe = fl_pe(lm, p)
    fl = max(fl_ce(lm, p), 1e-6)
    # Force the CE must carry, normalised.
    fm_ce = f_se / ca - f_pe
    return velocity_from_force(fm_ce, a, fl, p)


@dataclass
class MuscleState:
    t: float
    lm: float
    a: float
    lmt: float
    lt: float
    alpha: float
    f_se: float          # normalised
    f_ce: float
    f_pe: float
    force_n: float       # tendon force, newtons
    vm: float


@dataclass
class SimulationResult:
    parameters: MuscleParameters
    states: list[MuscleState] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def col(self, name: str) -> list[float]:
        return [getattr(s, name) for s in self.states]


def simulate(
    *,
    lmt_of_t,
    excitation_of_t,
    p: MuscleParameters,
    lm0: float | None = None,
    a0: float | None = None,
    t0: float = 0.0,
    t1: float = 1.0,
    dt: float = 5e-4,
) -> SimulationResult:
    """Integrate the muscle-tendon unit over a prescribed path length.

    `lmt_of_t` gives the muscle-tendon length in metres; `excitation_of_t`
    gives neural excitation u in [0, 1]. Both are functions of time, which is
    what lets a measured joint trajectory drive the muscle.

    Integration is classical RK4 at a fixed step. The reference
    implementation uses adaptive Dormand-Prince, which is better for the
    stiff clamped regions; RK4 at 0.5 ms is used here because the driving
    signal is itself sampled and a fixed grid keeps the output aligned with
    it. The step is small enough that halving it changes peak force by less
    than 0.1% -- checked in the tests.
    """
    lm = lm0 if lm0 is not None else 0.9 * p.lmopt
    # Starting activation must match whatever lm0 was equilibrated for, or the
    # first step is inconsistent and emits a spurious velocity spike.
    a = a0 if a0 is not None else p.u_min
    res = SimulationResult(parameters=p)
    res.notes.append(
        f"RK4 at dt={dt * 1e3:.2f} ms; eccentric asymptote frozen at "
        f"{p.asy_e_thresh:.0%} of the plateau (OpenSim guard, not in Thelen 2003)"
    )

    t = t0
    n = int(round((t1 - t0) / dt))
    for i in range(n + 1):
        lmt = lmt_of_t(t)
        u = excitation_of_t(t)

        lm = max(lm, p.lm_min_frac * p.lmopt)
        ca = cos_pennation(lm, p)
        lt = lmt - lm * ca
        f_se = fl_se(lt, p)
        f_pe = fl_pe(lm, p)
        fl = max(fl_ce(lm, p), 1e-6)
        f_ce = f_se / ca - f_pe
        vm = velocity_from_force(f_ce, a, fl, p)

        res.states.append(
            MuscleState(
                t=t, lm=lm, a=a, lmt=lmt, lt=lt,
                alpha=pennation(lm, p),
                f_se=f_se, f_ce=f_ce, f_pe=f_pe,
                force_n=f_se * p.fm0, vm=vm,
            )
        )
        if i == n:
            break

        # RK4 on (lm, a).
        def deriv(tt, l, act):
            return (
                d_fibre_length(l, lmt_of_t(tt), act, p),
                d_activation(act, excitation_of_t(tt), p),
            )

        k1 = deriv(t, lm, a)
        k2 = deriv(t + dt / 2, lm + dt / 2 * k1[0], a + dt / 2 * k1[1])
        k3 = deriv(t + dt / 2, lm + dt / 2 * k2[0], a + dt / 2 * k2[1])
        k4 = deriv(t + dt, lm + dt * k3[0], a + dt * k3[1])
        lm += dt / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
        a += dt / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
        a = min(max(a, p.u_min), 1.0)
        t += dt

    return res


def equilibrium_fibre_length(lmt: float, a: float, p: MuscleParameters) -> float:
    """Fibre length at which the tendon and fibre forces balance.

    Solved by bisection on the force residual. Used to start a simulation
    from a consistent state rather than an arbitrary one: starting off
    equilibrium injects a transient that looks like a physiological response
    but is purely numerical.
    """
    def residual(lm: float) -> float:
        ca = cos_pennation(lm, p)
        lt = lmt - lm * ca
        return fl_se(lt, p) / ca - (a * fl_ce(lm, p) + fl_pe(lm, p))

    lo, hi = p.lm_min_frac * p.lmopt, min(1.8 * p.lmopt, lmt / max(1e-6, cos_pennation(p.lmopt, p)))
    flo, fhi = residual(lo), residual(hi)
    if flo * fhi > 0:
        return 0.9 * p.lmopt
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        fm = residual(mid)
        if flo * fm <= 0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm
    return 0.5 * (lo + hi)


# ── minimum jerk ─────────────────────────────────────────────────────


def minimum_jerk(xi: float, xf: float, d: float, t: float) -> tuple[float, float, float, float]:
    """Flash & Hogan (1985) minimum-jerk trajectory: position, vel, acc, jerk.

    x(t) = xi + (xf - xi) [10 tau^3 - 15 tau^4 + 6 tau^5],  tau = t/d

    Velocity and acceleration vanish at both endpoints; jerk does NOT -- it is
    +-60 dx/d^3 there, which is why the criterion minimises the integral of
    squared jerk rather than jerk itself.
    """
    if d <= 0:
        return xf, 0.0, 0.0, 0.0
    tau = min(max(t / d, 0.0), 1.0)
    dx = xf - xi
    pos = xi + dx * (10 * tau**3 - 15 * tau**4 + 6 * tau**5)
    vel = dx / d * (30 * tau**2 - 60 * tau**3 + 30 * tau**4)
    acc = dx / d**2 * (60 * tau - 180 * tau**2 + 120 * tau**3)
    jerk = dx / d**3 * (60 - 360 * tau + 360 * tau**2)
    return pos, vel, acc, jerk


#: Peak-to-mean speed ratio of a minimum-jerk movement: v_peak = 1.875 dx/d
#: while the mean is dx/d, so the ratio is exactly 15/8. Reaching studies
#: report about 1.75, so the criterion overshoots by ~7% -- a real and often
#: unremarked discrepancy.
MINJERK_PEAK_MEAN_RATIO = 15.0 / 8.0
MINJERK_EMPIRICAL_RATIO = 1.75
