"""Reference backend.

Discharges the four obligations of specification section 7:

  (B1) Totality        -- defined for every well-typed circuit and observable,
                          including open circuits. An open circuit yields a
                          value describing the failure (a divergence time), not
                          an exception. The divergence is the finding.
  (B2) Floor agreement -- reports the floor it used; must match the circuit's
                          declared floor.
  (B3) Stratum honesty -- reports the band over which each observable was
                          computed.
  (B4) Determinism     -- same circuit, observable, and seed give the same
                          value.

The dynamics integrated here are a delayed multi-stratum loop, linearised
about the operating cycle. A closed loop is held in bounded oscillation by
its own return; an open loop has no return term and diverges. That contrast
is the whole point, and it is structural rather than tuned: the return term
is present exactly when the closure index is `closed`.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field

import numpy as np

from .circuit import Circuit, Closure
from .observables import OBSERVABLES, STRATUM_BANDS


@dataclass
class BackendReport:
    """What (B2) and (B3) require a backend to disclose."""

    floor_used: float
    band: tuple[float, float] | None
    seed: int
    n_samples: int
    dt: float


@dataclass
class Measurement:
    value: object
    unit: str
    report: BackendReport
    note: str = ""

    def __repr__(self) -> str:  # pragma: no cover
        v = self.value
        if isinstance(v, float):
            v = f"{v:.6g}"
        return f"{v} {self.unit}".strip()


class Backend:
    """Continuous reference backend."""

    def __init__(self, dt: float = 1e-3, duration: float = 60.0, seed: int = 0):
        self.dt = dt
        self.duration = duration
        self.seed = seed
        self._cache: dict[tuple, np.ndarray] = {}

    # ── dynamics ─────────────────────────────────────────────────────

    def simulate(self, c: Circuit) -> np.ndarray:
        """Integrate the circulation, returning the state trace.

        Three strata are driven at their own time constants and coupled
        through the loop. The return term enters with the loop delay; when
        the circuit is open there is no return term and the state is driven
        by an unopposed outbound term, which diverges.
        """
        key = (id(c), c.name, tuple(sorted(c.elements)), self.seed,
               len(c.noise_edges), tuple(c.provenance))
        if key in self._cache:
            return self._cache[key]

        # Seed per circuit identity, not per backend: two circuits in one
        # experiment are distinct physical loops and must receive
        # independent drive, or an antagonist pair would be two copies of
        # one signal and always perfectly co-active.
        # (B4) demands determinism, so the per-circuit offset uses a stable
        # digest rather than hash(), which is randomised per process.
        digest = int(hashlib.sha256(c.name.encode()).hexdigest()[:8], 16)
        rng = np.random.default_rng((self.seed * 1_000_003 + digest) % (2**32))
        n = int(self.duration / self.dt)
        closed = c.closure_index() is Closure.CLOSED

        tau_loop = max(c.loop_delay(), self.dt)
        lag = max(int(tau_loop / self.dt), 1)

        # Loop gain: the product of the gains around the WHOLE circulation.
        # Attenuating any element -- descending or ascending -- weakens the
        # restoring term, so a lesion anywhere on the loop changes the
        # dynamics. Computing this from the return path alone would make
        # descending lesions silent, which is wrong.
        ret_gain = 1.0
        for path in (c.outbound, c.ret):
            for a, b in zip(path, path[1:]):
                for e in c.elements.values():
                    if e.src == a and e.dst == b:
                        ret_gain *= e.gain
                        break

        # Stratum time constants (seconds), centres of the declared bands.
        tau = {"reflex": 0.05, "spinal": 0.5, "supraspinal": 2.0}
        present = {c.stratum_of(v) for v in c.compartments}
        present.discard(None)
        if not present:
            present = {"reflex"}

        x = np.zeros((n, 3))  # columns: reflex, spinal, supraspinal
        cols = {"reflex": 0, "spinal": 1, "supraspinal": 2}

        drive = 1.0
        noise_amp = 0.0
        cross = []
        for s1, s2, amp in c.noise_edges:
            noise_amp = max(noise_amp, amp)
            cross.append((cols.get(s1, 0), cols.get(s2, 0), amp))

        diverged_at = -1

        for i in range(1, n):
            for sname in present:
                j = cols[sname]
                t = tau[sname]
                # Stochastic drive scaled to the stratum's own time constant.
                w = rng.normal(0.0, math.sqrt(self.dt / t))

                if closed:
                    # The return closes the loop: a delayed, gain-weighted
                    # restoring term. Bounded oscillation, never a fixed point.
                    ret = x[i - lag, j] if i >= lag else 0.0
                    dx = (-x[i - 1, j] / t) - (ret_gain * ret / t) * 0.35 + w / t
                else:
                    # No return term. The outbound drive is unopposed.
                    dx = (drive / t) * 0.6 + w / t

                x[i, j] = x[i - 1, j] + dx * self.dt

            for (a, b, amp) in cross:
                # A cross-stratum coupling edge injects the fast component's
                # phase into the slow one and vice versa.
                bleed = amp * (x[i, a] - x[i, b]) * self.dt / tau["spinal"]
                x[i, b] += bleed
                x[i, a] -= bleed

            if diverged_at < 0 and np.max(np.abs(x[i])) > 50.0:
                diverged_at = i
                x[i:] = np.sign(x[i]) * 50.0
                break

        self._cache[key] = x
        return x

    def divergence_time(self, c: Circuit) -> float:
        if c.closure_index() is Closure.CLOSED:
            return float("nan")
        x = self.simulate(c)
        mag = np.max(np.abs(x), axis=1)
        idx = np.argmax(mag > 45.0)
        if mag[idx] <= 45.0:
            return float("nan")
        return float(idx * self.dt)

    # ── spectra ──────────────────────────────────────────────────────

    def _psd(self, sig: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        from scipy import signal

        nper = min(len(sig), int(10.0 / self.dt))
        f, p = signal.welch(sig, fs=1.0 / self.dt, nperseg=nper)
        return f, p

    def band_power(self, c: Circuit, stratum: str) -> float:
        band = STRATUM_BANDS.get(stratum)
        if band is None:
            return float("nan")
        x = self.simulate(c)
        sig = x.sum(axis=1)
        if not np.isfinite(sig).all() or np.allclose(sig, sig[0]):
            return float("nan")
        f, p = self._psd(sig)
        total = np.trapezoid(p, f)
        if total <= 0:
            return float("nan")
        m = (f >= band[0]) & (f <= band[1])
        return float(np.trapezoid(p[m], f[m]) / total)

    def _force(self, c: Circuit, peak: bool = False) -> tuple[float, str]:
        """Force from the outbound phase alone.

        The outbound phase carries the command to the muscle, so force is a
        product of the gains along it, scaled by the terminal compartment's
        capacitance via Q = sqrt(2 C P). Whether the RETURN phase is intact
        does not enter: a severed return abolishes coordination, not
        contractile capacity, which is precisely the dissociation the
        deafferentation experiments turn on.
        """
        gain = 1.0
        realised = True
        for a, b in zip(c.outbound, c.outbound[1:]):
            hop = None
            for e in c.elements.values():
                if e.src == a and e.dst == b:
                    hop = e
                    break
            if hop is None:
                realised = False
                break
            gain *= hop.gain

        if not realised:
            return 0.0, "outbound phase severed: no force is produced"

        terminal = c.outbound[-1] if c.outbound else None
        cap = c.compartments[terminal].capacitance if terminal in c.compartments else 1e-4
        # Peak tetanic force of a large postural muscle, order 10^3 N,
        # scaled by outbound gain and the terminal capacitance ratio.
        f_max = 1200.0 * math.sqrt(cap / 1.41e-4)
        v = f_max * gain
        if not peak:
            v *= 0.35  # mean over the duty cycle rather than peak

        note = ""
        if c.closure_index() is not Closure.CLOSED:
            note = "outbound intact: contractile capacity preserved despite open loop"
        return float(v), note

    def coupling_index(self, c: Circuit) -> float:
        """Zero-lag correlation of the slow component with the fast envelope."""
        x = self.simulate(c)
        slow, fast = x[:, 2], x[:, 0]
        if np.allclose(fast, fast[0]) or np.allclose(slow, slow[0]):
            return float("nan")
        env = np.abs(fast)
        a = slow - slow.mean()
        b = env - env.mean()
        denom = math.sqrt(float((a * a).sum()) * float((b * b).sum()))
        if denom <= 0:
            return float("nan")
        return float(abs((a * b).sum() / denom))

    # ── dispatch ─────────────────────────────────────────────────────

    def measure(self, c: Circuit, name: str, args: list[str],
                ctx: dict | None = None) -> Measurement:
        """(B1) Total: never raises for a well-typed request."""
        ctx = ctx or {}
        spec = OBSERVABLES[name]
        band = STRATUM_BANDS.get(args[0]) if (args and name == "band_power") else None
        rep = BackendReport(
            floor_used=c.floor(),
            band=band,
            seed=self.seed,
            n_samples=int(self.duration / self.dt),
            dt=self.dt,
        )

        closed = c.closure_index() is Closure.CLOSED

        if name == "closure_index":
            return Measurement(c.closure_index().value, "categorical", rep)

        if name == "aperture_list":
            aps = [a.report() for a in c.apertures()]
            return Measurement(aps, "list", rep,
                               note=f"{len(aps)} aperture(s)")

        if name == "resting_cut_weight":
            spec_f = c.floor_spec
            v = getattr(spec_f, "derived_arg", None)
            if v and v in c.compartments:
                return Measurement(c.separation_cost(v), "conductance", rep)
            return Measurement(c.floor(), "conductance", rep)

        if name == "floor_value":
            return Measurement(c.floor(), "conductance", rep)

        if name == "loop_latency":
            return Measurement(c.loop_delay(), "s", rep)

        if name == "divergence_time":
            v = self.divergence_time(c)
            note = "" if not math.isnan(v) else "circuit is closed; no divergence"
            return Measurement(v, "s", rep, note=note)

        if name == "tonic_rate":
            if not closed:
                return Measurement(float("nan"), "Hz", rep,
                                   note="open circuit sustains no tonic rhythm")
            d = c.loop_delay()
            return Measurement(1.0 / (2.0 * d) if d > 0 else float("nan"), "Hz", rep)

        if name in ("oscillation_amplitude", "cop_rms"):
            x = self.simulate(c)
            sig = x.sum(axis=1)
            v = float(np.sqrt(np.mean(sig**2)))
            unit = "mm" if name == "cop_rms" else "a.u."
            note = "" if closed else "open circuit: value reflects divergence"
            return Measurement(v, unit, rep, note=note)

        if name == "oscillation_frequency":
            x = self.simulate(c)
            sig = x.sum(axis=1)
            if np.allclose(sig, sig[0]):
                return Measurement(float("nan"), "Hz", rep)
            f, p = self._psd(sig)
            if len(f) < 2:
                return Measurement(float("nan"), "Hz", rep)
            return Measurement(float(f[int(np.argmax(p[1:])) + 1]), "Hz", rep)

        if name in ("force_amplitude", "force_output"):
            # Force is produced by the OUTBOUND phase, so it is computed from
            # outbound integrity alone. This matters: an open circulation
            # diverges in state, but its diverging state is not muscle force.
            # Reading force off the trace would report a severed loop as
            # stronger, inverting the claim the experiment is testing.
            v, note = self._force(c, peak=(name == "force_amplitude"))
            return Measurement(v, "N", rep, note=note)

        if name == "band_power":
            return Measurement(self.band_power(c, args[0]), "fraction", rep)

        if name == "coupling_index":
            return Measurement(self.coupling_index(c), "dimensionless", rep)

        if name in ("kappa", "type_separation", "composition_residual"):
            from .estimation import measure_estimation

            return measure_estimation(self, c, name, args, ctx, rep)

        if name in ("cocontraction_ratio", "joint_stiffness"):
            from .antagonist import measure_antagonist

            return measure_antagonist(self, c, name, args, ctx, rep)

        # (B1) demands totality: report the gap rather than raising.
        return Measurement(float("nan"), spec.unit, rep,
                           note=f"backend has no procedure for '{name}'")
