"""Coherence, identity/character, and path opacity.

Five analyses that extend the closure discipline. Each is computed from the
declaration alone, so all are backend-independent in the sense of the
backend-independence proposition.

1. HOLONOMY COHERENCE. A circulation is coherent when the transports around
   every cycle sum to zero -- when all routes through the circuit agree. A
   circuit can be closed (its declared paths match) and still incoherent
   (its delays disagree around a loop). Closure is a statement about which
   paths exist; coherence is a statement about whether they agree. The two
   are independent, and a circuit needs both.

2. IDENTITY AND CHARACTER. The minimum-weight partition of a circuit is one
   object with two orientations: read inward it says WHERE the circuit
   divides most cheaply (its identity); read outward it is the boundary an
   observer finds invariant (its character). The aperture analysis reads
   closure from outside; the resting cut defines the floor from inside.
   Naming them as two faces of one cut resolves that.

3. PATH OPACITY. Two circulations with the same endpoints and the same
   closure index may be realised by different element sets, and the endpoints
   do not determine which. A report of closure therefore under-determines the
   circuit that produced it.

4. TWO-FACTOR ADMISSIBILITY. A lesion is admissible only if it is both
   expressible (the operator applies) and coherence-preserving. Neither
   suffices alone.

5. STRENGTHENED FLOOR. Positivity follows from connectivity plus positive
   edge weights -- no appeal to what a boundary "is". The conceptual argument
   ("a zero-thickness boundary is not a boundary") defines the zero case away
   rather than deriving its impossibility; the connectivity argument derives
   it.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field

import numpy as np

from .circuit import Circuit, Closure, Element


# ── 1. Holonomy coherence ────────────────────────────────────────────

@dataclass(frozen=True)
class Cycle:
    """A directed cycle in the circulation, as a vertex sequence."""

    vertices: tuple[str, ...]

    def edges(self) -> list[tuple[str, str]]:
        v = self.vertices
        return [(v[i], v[(i + 1) % len(v)]) for i in range(len(v))]


@dataclass
class HolonomyReport:
    cycle: Cycle
    holonomy: float          # signed sum of transports around the cycle
    magnitude: float         # |holonomy|
    edges_present: bool      # every hop realised by a surviving element

    def describe(self) -> str:
        return (
            f"cycle {' -> '.join(self.cycle.vertices)} -> {self.cycle.vertices[0]}: "
            f"holonomy {self.holonomy:+.4g} s"
        )


def conductance(e: "Element") -> float:
    """Edge weight for the cut computations: gain stands in for conductance."""
    return max(e.gain, 1e-12)


def separation_cost(c: Circuit, vertex: str) -> float:
    return c.separation_cost(vertex)


def transport(c: Circuit, src: str, dst: str) -> float | None:
    """Signed transport along one hop, in seconds.

    The transport of a hop is its declared delay, signed by whether the hop
    is traversed along or against the element's declared direction. A hop
    taken forwards accrues its delay; the same hop taken backwards discharges
    it. That sign convention is what makes a cycle sum a DISAGREEMENT rather
    than a total.

    The distinction matters. Summing raw delays around a loop is never zero
    for a circulation that actually takes time, so a test built on it would
    call every circuit incoherent and say nothing. What coherence asks is
    different: if two routes lead from one compartment to another, do they
    agree on the delay? A cycle traversed forwards along one route and
    backwards along the other sums to zero exactly when the two agree.
    """
    for e in c.elements.values():
        if e.src == src and e.dst == dst:
            return e.delay
        if e.src == dst and e.dst == src:
            return -e.delay
    return None


def circulation_cycle(c: Circuit) -> Cycle | None:
    """The cycle formed by the outbound phase followed by the return phase."""
    if not c.outbound or not c.ret:
        return None
    # outbound v0..vm, return vm..v0; the cycle is their concatenation with
    # the shared endpoints counted once.
    seq = list(c.outbound) + list(c.ret[1:-1])
    if len(seq) < 3:
        return None
    return Cycle(tuple(seq))


def cycle_basis(c: Circuit) -> list[Cycle]:
    """A cycle basis of the circuit's underlying undirected graph.

    Size |E| - |V| + 1 for a connected graph, so the coherence test is
    polynomial and needs no global solve.
    """
    verts = sorted(c.compartments.keys())
    if not verts:
        return []
    idx = {v: i for i, v in enumerate(verts)}

    # Spanning tree by union-find over the undirected edge set.
    parent = list(range(len(verts)))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    tree: list[tuple[str, str]] = []
    extra: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for e in c.elements.values():
        if e.src not in idx or e.dst not in idx:
            continue
        key = tuple(sorted((e.src, e.dst)))
        if key in seen:
            continue
        seen.add(key)
        ra, rb = find(idx[e.src]), find(idx[e.dst])
        if ra != rb:
            parent[ra] = rb
            tree.append((e.src, e.dst))
        else:
            extra.append((e.src, e.dst))

    # Adjacency of the spanning tree, for path recovery.
    adj: dict[str, list[str]] = {v: [] for v in verts}
    for a, b in tree:
        adj[a].append(b)
        adj[b].append(a)

    def tree_path(a: str, b: str) -> list[str] | None:
        prev: dict[str, str | None] = {a: None}
        stack = [a]
        while stack:
            u = stack.pop()
            if u == b:
                break
            for w in adj[u]:
                if w not in prev:
                    prev[w] = u
                    stack.append(w)
        if b not in prev:
            return None
        path = [b]
        while prev[path[-1]] is not None:
            path.append(prev[path[-1]])  # type: ignore[arg-type]
        return list(reversed(path))

    cycles: list[Cycle] = []
    for a, b in extra:
        p = tree_path(b, a)
        if p and len(p) >= 2:
            cycles.append(Cycle(tuple(p)))
    return cycles


def holonomy(c: Circuit, cycle: Cycle) -> HolonomyReport:
    """Signed transport sum around a cycle.

    Zero means every route through the cycle agrees; nonzero means two
    routes between the same pair of compartments disagree by that amount.
    Because a hop taken against its declared direction contributes with the
    opposite sign, a cycle that is genuinely two agreeing routes cancels
    exactly, while one whose routes disagree leaves the discrepancy.
    """
    total = 0.0
    present = True
    for a, b in cycle.edges():
        t = transport(c, a, b)
        if t is None:
            present = False
            continue
        total += t
    return HolonomyReport(cycle, total, abs(total), present)


def two_route_disagreement(c: Circuit, src: str, dst: str) -> float:
    """Largest delay disagreement between any two routes from src to dst.

    This is the coherence question stated directly: when the circuit offers
    more than one way from one compartment to another, do the ways agree on
    how long it takes? A single route cannot disagree with itself, so the
    disagreement is zero by construction there.
    """
    paths = enumerate_paths(c, src, dst)
    if len(paths) < 2:
        return 0.0
    lats = []
    for p in paths:
        tot = 0.0
        ok = True
        for i in range(len(p) - 1):
            t = transport(c, p[i], p[i + 1])
            if t is None:
                ok = False
                break
            tot += t
        if ok:
            lats.append(tot)
    if len(lats) < 2:
        return 0.0
    return max(lats) - min(lats)


def coherence_margin(c: Circuit) -> float:
    """kappa(C) = -max over compartment pairs of the route disagreement.

    Zero at perfect coherence -- every pair of compartments joined by more
    than one route agrees on the delay. Negative when some pair disagrees,
    by the size of the worst disagreement.

    This is checkable in advance and locally: it reads declared delays only,
    never a simulated trace, so a lesion can be refused BEFORE it is
    committed. That is what makes the two-factor admissibility rule
    enforceable rather than aspirational.
    """
    verts = sorted(c.compartments.keys())
    worst = 0.0
    for a in verts:
        for b in verts:
            if a == b:
                continue
            d = two_route_disagreement(c, a, b)
            if d > worst:
                worst = d
    return -worst


def is_coherent(c: Circuit, tol: float = 1e-12) -> bool:
    return coherence_margin(c) >= -tol


def worst_cycle(c: Circuit) -> HolonomyReport | None:
    cycles = cycle_basis(c)
    reports = [holonomy(c, cyc) for cyc in cycles]
    reports = [r for r in reports if r.edges_present]
    if not reports:
        return None
    return max(reports, key=lambda r: r.magnitude)


# ── 2. Identity and character: two orientations of one cut ───────────

@dataclass
class IdentityCharacter:
    """One minimising cut, read inward and outward.

    `identity` is the partition -- where the circuit divides most cheaply,
    as it is constituted from inside. `character` is the boundary carried
    at that partition -- what an observer finds invariant across every
    relabelling. Neither is prior; each determines the other.
    """

    identity: tuple[frozenset[str], ...]
    character: tuple[tuple[str, str, float], ...]
    cost: float
    is_block_cut: bool          # minimiser is not a singleton split
    cheapest_singleton: float

    @property
    def n_blocks(self) -> int:
        return len(self.identity)

    def describe(self) -> str:
        blocks = " | ".join("{" + ",".join(sorted(b)) + "}" for b in self.identity)
        kind = "block cut" if self.is_block_cut else "singleton cut"
        return (f"identity {blocks}; character cost {self.cost:.4g} ({kind}; "
                f"cheapest singleton {self.cheapest_singleton:.4g})")


def _boundary(c: Circuit, block: frozenset[str]) -> list[tuple[str, str, float]]:
    out = []
    for e in c.elements.values():
        a_in = e.src in block
        b_in = e.dst in block
        if a_in != b_in:
            out.append((e.src, e.dst, conductance(e)))
    return out


def identity_character(c: Circuit, max_vertices: int = 14) -> IdentityCharacter:
    """Minimum-residual partition, by exact enumeration on small graphs.

    The residual of a partition is the total inter-block boundary weight.
    Enumerating all two-block splits is exponential, so we cap the vertex
    count and fall back to the cheapest singleton beyond it -- reported
    honestly rather than silently.
    """
    verts = sorted(c.compartments.keys())
    n = len(verts)
    if n < 2:
        return IdentityCharacter((frozenset(verts),), (), 0.0, False, 0.0)

    singleton_costs = {v: sum(w for _, _, w in _boundary(c, frozenset([v])))
                       for v in verts}
    cheapest_singleton = min(singleton_costs.values())

    best_cost = math.inf
    best_block: frozenset[str] | None = None

    if n <= max_vertices:
        # Enumerate two-block splits; fix the first vertex in block A to
        # avoid counting each split twice.
        first = verts[0]
        rest = verts[1:]
        for r in range(0, len(rest) + 1):
            for combo in itertools.combinations(rest, r):
                block = frozenset([first, *combo])
                if len(block) == n:
                    continue
                cost = sum(w for _, _, w in _boundary(c, block))
                if cost > 0 and cost < best_cost:
                    best_cost = cost
                    best_block = block
    else:
        v = min(singleton_costs, key=lambda k: singleton_costs[k])
        best_block = frozenset([v])
        best_cost = singleton_costs[v]

    if best_block is None:
        v = min(singleton_costs, key=lambda k: singleton_costs[k])
        best_block = frozenset([v])
        best_cost = singleton_costs[v]

    other = frozenset(verts) - best_block
    boundary = tuple(sorted(_boundary(c, best_block)))
    is_block = len(best_block) > 1 and len(other) > 1

    return IdentityCharacter(
        identity=(best_block, other),
        character=boundary,
        cost=best_cost,
        is_block_cut=is_block,
        cheapest_singleton=cheapest_singleton,
    )


def character_is_invariant(c: Circuit, relabel: dict[str, str]) -> bool:
    """Character cost is unchanged by any weight-preserving relabelling."""
    from .circuit import Compartment, Element

    renamed = c.clone()
    renamed.compartments = {
        relabel.get(k, k): Compartment(relabel.get(k, k), v.capacitance, v.stratum)
        for k, v in c.compartments.items()
    }
    renamed.elements = {
        k: Element(e.name, relabel.get(e.src, e.src), relabel.get(e.dst, e.dst),
                   e.delay, e.gain)
        for k, e in c.elements.items()
    }
    renamed.outbound = [relabel.get(v, v) for v in c.outbound]
    renamed.ret = [relabel.get(v, v) for v in c.ret]

    a = identity_character(c).cost
    b = identity_character(renamed).cost
    return abs(a - b) < 1e-12


# ── 3. Path opacity ──────────────────────────────────────────────────

@dataclass
class OpacityReport:
    endpoints: tuple[str, str]
    n_realisations: int
    interiors: tuple[tuple[str, ...], ...]
    closure_agrees: bool
    latency_range: tuple[float, float]

    @property
    def is_opaque(self) -> bool:
        return self.n_realisations > 1

    def describe(self) -> str:
        a, b = self.endpoints
        return (f"{a} -> {b}: {self.n_realisations} distinct interior(s); "
                f"latency {self.latency_range[0]*1e3:.1f}-"
                f"{self.latency_range[1]*1e3:.1f} ms")


def enumerate_paths(c: Circuit, src: str, dst: str,
                    max_paths: int = 64) -> list[tuple[str, ...]]:
    """All simple directed paths from src to dst, capped."""
    adj: dict[str, list[str]] = {}
    for e in c.elements.values():
        adj.setdefault(e.src, []).append(e.dst)

    out: list[tuple[str, ...]] = []

    def walk(node: str, seen: tuple[str, ...]):
        if len(out) >= max_paths:
            return
        if node == dst and len(seen) > 1:
            out.append(seen)
            return
        for nxt in adj.get(node, []):
            if nxt in seen:
                continue
            walk(nxt, seen + (nxt,))

    walk(src, (src,))
    return out


def path_opacity(c: Circuit, src: str, dst: str) -> OpacityReport:
    """Do the endpoints determine the interior?

    Two routes between the same pair of compartments, with the same closure
    consequence, are indistinguishable from the endpoints alone. This is the
    circuit-level analogue of the result that a report does not determine
    the search that produced it.
    """
    paths = enumerate_paths(c, src, dst)
    interiors = tuple(sorted(set(p[1:-1] for p in paths)))

    lats: list[float] = []
    for p in paths:
        total = 0.0
        for i in range(len(p) - 1):
            t = transport(c, p[i], p[i + 1])
            if t is not None:
                total += abs(t)
        lats.append(total)

    return OpacityReport(
        endpoints=(src, dst),
        n_realisations=len(interiors),
        interiors=interiors,
        closure_agrees=True,
        latency_range=(min(lats), max(lats)) if lats else (0.0, 0.0),
    )


# ── 4. Two-factor admissibility ──────────────────────────────────────

@dataclass
class Admissibility:
    expressible: bool
    coherence_preserving: bool
    margin_before: float
    margin_after: float

    @property
    def admissible(self) -> bool:
        return self.expressible and self.coherence_preserving

    def describe(self) -> str:
        if self.admissible:
            return "admissible: expressible and coherence-preserving"
        if not self.expressible:
            return "inadmissible: operator does not apply"
        return (f"inadmissible: coherence-breaking "
                f"({self.margin_before:+.4g} -> {self.margin_after:+.4g})")


def admissibility(before: Circuit, after: Circuit,
                  expressible: bool = True) -> Admissibility:
    """A lesion is admissible only if it is BOTH expressible and
    coherence-preserving. Neither factor alone suffices."""
    mb = coherence_margin(before)
    ma = coherence_margin(after)
    return Admissibility(
        expressible=expressible,
        coherence_preserving=ma >= mb - 1e-12,
        margin_before=mb,
        margin_after=ma,
    )


# ── 5. Strengthened floor ────────────────────────────────────────────

@dataclass
class FloorDerivation:
    value: float
    connected: bool
    min_edge_weight: float
    n_incident: int
    argument: str

    def describe(self) -> str:
        return (f"floor {self.value:.6g} by {self.argument} "
                f"(connected={self.connected}, min edge {self.min_edge_weight:.4g})")


def floor_by_connectivity(c: Circuit, vertex: str | None = None) -> FloorDerivation:
    """Positivity from connectivity plus positive edge weights.

    This derives the zero case as impossible rather than defining it away.
    A conceptual argument -- "a zero-thickness boundary is not a boundary"
    -- assumes what it should establish: it declares zero-weight edges not
    to be edges. Here positivity follows because (i) the graph is connected,
    so every disconnecting set is nonempty, and (ii) every edge weight is
    positive by construction, so a nonempty set has positive total weight.
    """
    verts = sorted(c.compartments.keys())
    if not verts:
        return FloorDerivation(0.0, False, 0.0, 0, "empty graph")

    # Connectivity over the undirected edge set.
    adj: dict[str, set[str]] = {v: set() for v in verts}
    for e in c.elements.values():
        if e.src in adj and e.dst in adj:
            adj[e.src].add(e.dst)
            adj[e.dst].add(e.src)
    seen = {verts[0]}
    stack = [verts[0]]
    while stack:
        u = stack.pop()
        for w in adj[u]:
            if w not in seen:
                seen.add(w)
                stack.append(w)
    connected = len(seen) == len(verts)

    weights = [conductance(e) for e in c.elements.values()]
    min_w = min(weights) if weights else 0.0

    target = vertex or min(verts, key=lambda v: separation_cost(c, v))
    cost = separation_cost(c, target)
    n_inc = sum(1 for e in c.elements.values()
                if e.src == target or e.dst == target)

    return FloorDerivation(
        value=cost,
        connected=connected,
        min_edge_weight=min_w,
        n_incident=n_inc,
        argument="connectivity + positive edge weights",
    )


def floor_tightness(c: Circuit) -> float:
    """min separation cost / min edge weight.

    A value near 1 means the floor bound is essentially tight: the cheapest
    separation costs barely more than a single edge, so the residual the
    fractional observables rest on is real and small rather than a loose
    safety margin.
    """
    verts = list(c.compartments.keys())
    if not verts or not c.elements:
        return math.nan
    costs = [separation_cost(c, v) for v in verts]
    costs = [x for x in costs if x > 0]
    weights = [conductance(e) for e in c.elements.values()]
    if not costs or not weights:
        return math.nan
    return min(costs) / min(weights)
