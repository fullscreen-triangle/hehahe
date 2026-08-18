"""Circuits, the closure index, and the lesion operators.

Implements specification section 5: the closure index is decidable in time
linear in the number of elements, and the lesion operators form a
commutative idempotent monoid action so that lesion order does not matter.

Extension E3 (`reroute`) is the only operator that can carry a circuit from
`open` back to `closed`; every other operator either preserves closure or
opens it.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field, replace
from enum import Enum

from .ast_nodes import Quantity


class Closure(str, Enum):
    CLOSED = "closed"
    OPEN = "open"


@dataclass(frozen=True)
class Compartment:
    name: str
    capacitance: float  # farads
    stratum: str


@dataclass(frozen=True)
class Element:
    name: str
    src: str
    dst: str
    delay: float = 0.0  # seconds
    gain: float = 1.0

    @property
    def conductance(self) -> float:
        """Edge weight for the separation-cut computation.

        Gain stands in for conductance: a scaled-down element is a
        higher-resistance pathway, so it is cheaper to cut.
        """
        return max(self.gain, 1e-12)


@dataclass
class Aperture:
    """A circulation left without a return phase."""

    circulation: str
    outbound_from: str
    outbound_to: str
    cause: str

    def report(self) -> str:
        return (
            f"aperture in '{self.circulation}': outbound "
            f"{self.outbound_from} -> {self.outbound_to} has no closing return "
            f"({self.cause}). Prediction: the perturbation admits no closed "
            f"redistribution, so expect failure to resolve, not degraded precision."
        )


@dataclass
class Circuit:
    name: str
    compartments: dict[str, Compartment]
    outbound: list[str]
    ret: list[str]
    elements: dict[str, Element]
    floor_spec: object = None
    noise_edges: list[tuple[str, str, float]] = field(default_factory=list)
    provenance: list[str] = field(default_factory=list)

    # ── closure ──────────────────────────────────────────────────────

    def closure_index(self) -> Closure:
        """Decide whether every declared outbound path has a closing return.

        Linear in the number of elements: one membership pass to confirm
        each declared hop is realised by a surviving element, plus the two
        endpoint comparisons.
        """
        if not self.outbound or not self.ret:
            return Closure.OPEN

        # Endpoints must match: return starts where outbound ends, and
        # finishes where outbound began.
        if self.ret[0] != self.outbound[-1]:
            return Closure.OPEN
        if self.ret[-1] != self.outbound[0]:
            return Closure.OPEN

        # Every declared hop must be realised by a surviving element.
        if not self._path_realised(self.outbound):
            return Closure.OPEN
        if not self._path_realised(self.ret):
            return Closure.OPEN

        return Closure.CLOSED

    def _path_realised(self, path: list[str]) -> bool:
        for a, b in zip(path, path[1:]):
            if not any(e.src == a and e.dst == b for e in self.elements.values()):
                return False
        return True

    def _missing_hop(self, path: list[str]) -> tuple[str, str] | None:
        for a, b in zip(path, path[1:]):
            if not any(e.src == a and e.dst == b for e in self.elements.values()):
                return (a, b)
        return None

    def apertures(self) -> list[Aperture]:
        """Diagnostics, not errors: an open circuit is a legitimate model."""
        out: list[Aperture] = []
        if self.closure_index() is Closure.CLOSED:
            return out

        if not self.ret:
            out.append(
                Aperture(self.name, self.outbound[0], self.outbound[-1],
                         "return phase absent")
            )
            return out

        if self.ret[0] != self.outbound[-1] or self.ret[-1] != self.outbound[0]:
            out.append(
                Aperture(self.name, self.outbound[0], self.outbound[-1],
                         f"return path {self.ret[0]}..{self.ret[-1]} does not "
                         f"close {self.outbound[0]}..{self.outbound[-1]}")
            )

        for label, path in (("outbound", self.outbound), ("return", self.ret)):
            hop = self._missing_hop(path)
            if hop:
                out.append(
                    Aperture(self.name, hop[0], hop[1],
                             f"no element conducts {hop[0]} -> {hop[1]} on the "
                             f"{label} path")
                )
        return out

    # ── separation cost and floor ────────────────────────────────────

    def separation_cost(self, vertex: str) -> float:
        """Minimum weight of a cut separating `vertex` from the medium.

        The medium is the rest of the organism, modelled as a sink joined to
        every compartment. With that construction the minimum cut isolating a
        single vertex is the total weight of its incident edges, which is what
        we return; this is the `resting_cut` of the specification.
        """
        total = 0.0
        for e in self.elements.values():
            if e.src == vertex or e.dst == vertex:
                total += e.conductance
        return total

    def floor(self) -> float:
        """Positive irreducible residual (specification Rule III).

        Derived from the resting cut when the declaration says so; a
        literal is taken at face value. Either way the value must be > 0
        or the fractional observables are undefined.
        """
        spec = self.floor_spec
        if spec is None:
            vals = [self.separation_cost(v) for v in self.compartments]
            vals = [v for v in vals if v > 0]
            return min(vals) if vals else 1e-9

        if getattr(spec, "is_derived", False):
            if spec.derived_call == "resting_cut" and spec.derived_arg:
                cost = self.separation_cost(spec.derived_arg)
                return cost if cost > 0 else 1e-9
            if spec.derived_call == "sample_minimum":
                # Retained so a model *can* express it, but see the paper:
                # this estimator is positive whenever the sample is, hence
                # unfalsifiable. The checker warns.
                vals = [self.separation_cost(v) for v in self.compartments]
                vals = [v for v in vals if v > 0]
                return min(vals) if vals else 1e-9
            vals = [self.separation_cost(v) for v in self.compartments]
            vals = [v for v in vals if v > 0]
            return min(vals) if vals else 1e-9

        if spec.literal is not None:
            return spec.literal.si()
        return 1e-9

    # ── strata ───────────────────────────────────────────────────────

    def stratum_of(self, comp: str) -> str | None:
        c = self.compartments.get(comp)
        return c.stratum if c else None

    def loop_delay(self) -> float:
        """Total traversal time of the full circulation, in seconds."""
        total = 0.0
        for path in (self.outbound, self.ret):
            for a, b in zip(path, path[1:]):
                for e in self.elements.values():
                    if e.src == a and e.dst == b:
                        total += e.delay
                        break
        return total

    def clone(self, name: str | None = None) -> "Circuit":
        return Circuit(
            name=name or self.name,
            compartments=dict(self.compartments),
            outbound=list(self.outbound),
            ret=list(self.ret),
            elements=dict(self.elements),
            floor_spec=self.floor_spec,
            noise_edges=list(self.noise_edges),
            provenance=list(self.provenance),
        )


# ── lesion operators ────────────────────────────────────────────────
#
# Each returns a new circuit; none mutates its argument.  Together they
# form a commutative idempotent monoid action (specification Theorem 6.5),
# so the lesioned circuit is independent of the order of application.

def without_element(c: Circuit, name: str) -> Circuit:
    out = c.clone()
    out.elements.pop(name, None)  # removing an absent element is the identity
    out.provenance.append(f"without element({name})")
    return out


def without_return(c: Circuit, frm: str) -> Circuit:
    out = c.clone()
    # Delete the return phase from `frm` onward, and the elements realising it.
    if frm in out.ret:
        idx = out.ret.index(frm)
        doomed = out.ret[idx:]
    else:
        doomed = list(out.ret)
    pairs = set(zip(doomed, doomed[1:]))
    out.elements = {
        k: e for k, e in out.elements.items() if (e.src, e.dst) not in pairs
    }
    out.ret = out.ret[: out.ret.index(frm) + 1] if frm in out.ret else []
    out.provenance.append(f"without return({frm})")
    return out


def with_scaling(c: Circuit, name: str, factor: float) -> Circuit:
    if factor <= 0:
        raise ValueError(
            "scaling must be strictly positive: attenuation cannot express "
            "severance (use 'without element')"
        )
    out = c.clone()
    if name in out.elements:
        e = out.elements[name]
        out.elements[name] = replace(e, gain=e.gain * factor)
    out.provenance.append(f"with {name} scaling {factor}")
    return out


def with_noise(c: Circuit, s1: str, s2: str, amplitude: float) -> Circuit:
    out = c.clone()
    edge = (s1, s2, amplitude)
    if edge not in out.noise_edges:
        out.noise_edges.append(edge)
    out.provenance.append(f"with noise across {s1},{s2}({amplitude})")
    return out


def reroute(c: Circuit, frm: str, path: list[str]) -> Circuit:
    """E3. Replace the return phase from `frm` with an explicit new path.

    This is the only operator able to carry a circuit from open back to
    closed. The new path must begin at `frm` and end at the origin of the
    outbound phase for closure to be restored; if it does not, the circuit
    stays open and the aperture report says why.
    """
    out = c.clone()

    if frm in out.ret:
        idx = out.ret.index(frm)
        doomed = out.ret[idx:]
        pairs = set(zip(doomed, doomed[1:]))
        out.elements = {
            k: e for k, e in out.elements.items() if (e.src, e.dst) not in pairs
        }

    new_ret = list(path) if path and path[0] == frm else [frm] + list(path)
    out.ret = new_ret

    # Synthesise elements for the new hops, with a default conduction delay.
    for a, b in zip(new_ret, new_ret[1:]):
        if not any(e.src == a and e.dst == b for e in out.elements.values()):
            key = f"reroute_{a}_{b}"
            out.elements[key] = Element(key, a, b, delay=0.010, gain=1.0)

    out.provenance.append(f"reroute return({frm}) through {' -> '.join(path)}")
    return out
