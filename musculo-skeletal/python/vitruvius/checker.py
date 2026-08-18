"""Typechecker and static analyses for Vitruvius.

Implements the four non-standard rules of specification section 4:

  Rule I   compartment consistency  -- charge carries the capacitance it was
                                       computed against; mixing is an error
  Rule II  stratum containment      -- an element may touch only adjacent
                                       strata; a two-level shortcut is rejected
  Rule III floor positivity         -- a fractional observable needs beta > 0
  Rule IV  typed-event estimation   -- kappa requires a declared event type
                                       with at least two instances

plus template expansion (E1) and the aperture analysis of section 5.

Diagnostics are separated into errors (which reject the program) and
warnings (which do not). An open circuit is a warning, never an error: it
is the model of deafferentation and simulating it is the point.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from .ast_nodes import (
    CircuitDecl, CircuitRef, ElementDecl, InstanceDecl, Program, Quantity,
    Reroute, TemplateDecl, WithNoise, WithScaling, WithoutElement,
    WithoutReturn,
)
from .circuit import (
    Circuit, Closure, Compartment, Element, reroute as op_reroute,
    with_noise as op_noise, with_scaling as op_scale,
    without_element as op_wo_elem, without_return as op_wo_ret,
)

STRATUM_ORDER = {"reflex": 0, "spinal": 1, "supraspinal": 2}


@dataclass
class Diagnostic:
    severity: str  # "error" | "warning" | "note"
    rule: str
    message: str
    line: int = 0

    def __str__(self) -> str:
        loc = f" (line {self.line})" if self.line else ""
        return f"[{self.severity}] {self.rule}: {self.message}{loc}"


class CheckError(Exception):
    def __init__(self, diags: list[Diagnostic]):
        super().__init__("\n".join(str(d) for d in diags))
        self.diagnostics = diags


@dataclass
class CheckResult:
    circuits: dict[str, Circuit] = field(default_factory=dict)
    diagnostics: list[Diagnostic] = field(default_factory=list)
    event_types: dict[str, list[str]] = field(default_factory=dict)
    antagonists: dict[str, object] = field(default_factory=dict)

    @property
    def errors(self) -> list[Diagnostic]:
        return [d for d in self.diagnostics if d.severity == "error"]

    @property
    def warnings(self) -> list[Diagnostic]:
        return [d for d in self.diagnostics if d.severity == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors


class Checker:
    def __init__(self, prog: Program):
        self.prog = prog
        self.diags: list[Diagnostic] = []
        self.compartments: dict[str, Compartment] = {}
        self.circuits: dict[str, Circuit] = {}
        self.event_types: dict[str, list[str]] = {}

    def err(self, rule: str, msg: str, line: int = 0) -> None:
        self.diags.append(Diagnostic("error", rule, msg, line))

    def warn(self, rule: str, msg: str, line: int = 0) -> None:
        self.diags.append(Diagnostic("warning", rule, msg, line))

    def note(self, rule: str, msg: str, line: int = 0) -> None:
        self.diags.append(Diagnostic("note", rule, msg, line))

    # ── entry point ──────────────────────────────────────────────────

    def check(self) -> CheckResult:
        self._collect_compartments()
        self._expand_templates()
        self._build_circuits()
        self._check_event_types()
        self._check_experiments()

        return CheckResult(
            circuits=self.circuits,
            diagnostics=self.diags,
            event_types=self.event_types,
            antagonists={a.name: a for a in self.prog.antagonists},
        )

    # ── compartments ─────────────────────────────────────────────────

    def _collect_compartments(self) -> None:
        for d in self.prog.compartments:
            if d.name in self.compartments:
                self.err("duplicate", f"compartment '{d.name}' redeclared", d.line)
                continue
            if d.capacitance.dimension() != "capacitance":
                self.err(
                    "units",
                    f"compartment '{d.name}' capacitance has unit "
                    f"'{d.capacitance.unit}', expected a capacitance",
                    d.line,
                )
            cap = d.capacitance.si()
            if cap <= 0:
                self.err("units", f"compartment '{d.name}' capacitance must be > 0",
                         d.line)
            self.compartments[d.name] = Compartment(d.name, cap, d.stratum)

    # ── E1: template expansion ───────────────────────────────────────

    def _expand_templates(self) -> None:
        """Expand each instance to a plain circuit declaration.

        Expansion happens before typechecking, so every proof about circuit
        declarations applies unchanged to the expanded form.
        """
        tmpls = {t.name: t for t in self.prog.templates}

        for inst in self.prog.instances:
            t = tmpls.get(inst.template)
            if t is None:
                self.err("unknown", f"no template '{inst.template}'", inst.line)
                continue
            if len(inst.args) != len(t.params):
                self.err(
                    "arity",
                    f"template '{t.name}' expects {len(t.params)} arguments, "
                    f"got {len(inst.args)}",
                    inst.line,
                )
                continue

            sub = dict(zip(t.params, inst.args))

            def rep(x: str):
                return sub.get(x, x)

            def rep_name(x: str) -> str:
                v = sub.get(x, x)
                return v if isinstance(v, str) else x

            elements = []
            for e in t.elements:
                delay = e.delay
                if delay is None and e.name in sub:
                    pass
                # A parameter used in delay position arrives as a Quantity.
                if isinstance(e.delay, str) and e.delay in sub:
                    delay = sub[e.delay]
                elements.append(
                    ElementDecl(
                        name=f"{inst.name}_{e.name}",
                        src=rep_name(e.src),
                        dst=rep_name(e.dst),
                        delay=delay if isinstance(delay, Quantity) else e.delay,
                        gain=e.gain,
                        line=e.line,
                    )
                )

            floor = t.floor
            if floor.is_derived and floor.derived_arg in sub:
                v = sub[floor.derived_arg]
                if isinstance(v, str):
                    floor = replace(floor, derived_arg=v)

            self.prog.circuits.append(
                CircuitDecl(
                    name=inst.name,
                    floor=floor,
                    outbound=[rep_name(x) for x in t.outbound],
                    ret=[rep_name(x) for x in t.ret],
                    elements=elements,
                    line=inst.line,
                )
            )

    # ── circuits ─────────────────────────────────────────────────────

    def _build_circuits(self) -> None:
        for d in self.prog.circuits:
            if d.name in self.circuits:
                self.err("duplicate", f"circuit '{d.name}' redeclared", d.line)
                continue

            used = set(d.outbound) | set(d.ret)
            for e in d.elements:
                used.add(e.src)
                used.add(e.dst)

            comps: dict[str, Compartment] = {}
            for cname in used:
                c = self.compartments.get(cname)
                if c is None:
                    self.err("unknown",
                             f"circuit '{d.name}' references undeclared "
                             f"compartment '{cname}'", d.line)
                    continue
                comps[cname] = c

            elements: dict[str, Element] = {}
            for e in d.elements:
                if e.name in elements:
                    self.err("duplicate",
                             f"element '{e.name}' redeclared in '{d.name}'", e.line)
                    continue
                delay = e.delay.si() if isinstance(e.delay, Quantity) else 0.0
                if isinstance(e.delay, Quantity) and e.delay.dimension() != "time":
                    self.err("units",
                             f"element '{e.name}' delay has unit "
                             f"'{e.delay.unit}', expected a time", e.line)
                elements[e.name] = Element(e.name, e.src, e.dst, delay, e.gain)

            circ = Circuit(
                name=d.name,
                compartments=comps,
                outbound=list(d.outbound),
                ret=list(d.ret),
                elements=elements,
                floor_spec=d.floor,
            )

            self._check_strata(circ, d.line)
            self._check_floor(circ, d)
            self.circuits[d.name] = circ

    # ── Rule II: stratum containment ─────────────────────────────────

    def _check_strata(self, c: Circuit, line: int) -> None:
        for e in c.elements.values():
            s_src = c.stratum_of(e.src)
            s_dst = c.stratum_of(e.dst)
            if s_src is None or s_dst is None:
                continue
            d = abs(STRATUM_ORDER[s_src] - STRATUM_ORDER[s_dst])
            if d >= 2:
                self.err(
                    "T-Stratum",
                    f"element '{e.name}' in circuit '{c.name}' conducts "
                    f"{s_src} -> {s_dst}, which are not adjacent. Influence "
                    f"between non-adjacent strata must traverse the "
                    f"intervening stratum; to model a shortcut deliberately, "
                    f"use 'with noise across'",
                    line,
                )

    # ── Rule III: floor positivity ───────────────────────────────────

    def _check_floor(self, c: Circuit, d: CircuitDecl) -> None:
        spec = d.floor
        if spec.is_derived and spec.derived_call == "sample_minimum":
            self.warn(
                "T-Floor",
                f"circuit '{c.name}' derives its floor by sample_minimum, which "
                f"is positive whenever the sample is and therefore cannot "
                f"falsify a positivity claim; prefer resting_cut",
                d.line,
            )
        if spec.is_derived and spec.derived_arg:
            if spec.derived_arg not in c.compartments:
                self.err("T-Floor",
                         f"circuit '{c.name}' derives its floor from unknown "
                         f"compartment '{spec.derived_arg}'", d.line)
                return

        beta = c.floor()
        if beta <= 0:
            self.err(
                "T-Floor",
                f"circuit '{c.name}' has floor {beta}; a fractional observable "
                f"requires a strictly positive floor",
                d.line,
            )

    # ── Rule IV: typed events ────────────────────────────────────────

    def _check_event_types(self) -> None:
        for d in self.prog.event_types:
            if d.name in self.event_types:
                self.err("duplicate", f"event type '{d.name}' redeclared", d.line)
                continue
            for a in d.args:
                if a not in self.compartments:
                    self.err("unknown",
                             f"event type '{d.name}' references undeclared "
                             f"compartment '{a}'", d.line)
            self.event_types[d.name] = list(d.args)

    # ── experiments ──────────────────────────────────────────────────

    def _check_experiments(self) -> None:
        for x in self.prog.experiments:
            base = self._eval_expr(x.intact, x.line)
            if base is None:
                continue

            groups = (
                [(p.name, p.lesions, p.observables, p.line) for p in x.phases]
                if x.is_phased
                else [(None, x.lesions, x.observables, x.line)]
            )

            for pname, lesions, observables, line in groups:
                seen_scaling: set[str] = set()
                for les in lesions:
                    self._check_lesion_keys(les, seen_scaling)
                    c = self._eval_expr(les.expr, les.line)
                    if c is None:
                        continue
                    if c.closure_index() is Closure.OPEN:
                        for ap in c.apertures():
                            self.warn("aperture",
                                      f"lesion '{les.name}': {ap.report()}",
                                      les.line)

                for o in observables:
                    self._check_observable(o, x, pname)

    def _check_lesion_keys(self, les, seen: set[str]) -> None:
        """Duplicate scalings of one element break idempotence (Thm 6.5)."""
        node = les.expr
        while True:
            if isinstance(node, WithScaling):
                if node.element in seen:
                    self.err(
                        "T-Lesion",
                        f"element '{node.element}' scaled more than once; "
                        f"repeated scaling is not idempotent, so lesion order "
                        f"would matter",
                        les.line,
                    )
                seen.add(node.element)
            nxt = getattr(node, "base", None)
            if nxt is None:
                break
            node = nxt

    def _check_observable(self, o, x, phase: str | None) -> None:
        from .observables import OBSERVABLES

        if o.name not in OBSERVABLES:
            self.err(
                "unknown-observable",
                f"experiment '{x.name}' requests unknown observable "
                f"'{o.name}'. Observables must have a defined measurement "
                f"procedure; see observables.py for the registry",
                o.line,
            )
            return

        spec = OBSERVABLES[o.name]
        if spec.arity != len(o.args):
            self.err("arity",
                     f"observable '{o.name}' takes {spec.arity} argument(s), "
                     f"got {len(o.args)}", o.line)
            return

        # Rule IV: kappa needs a declared event type with >= 2 instances.
        if spec.requires_event_type:
            if not o.args:
                self.err("T-Event",
                         f"'{o.name}' requires a declared event type; an "
                         f"instance-specific estimate is an identity and "
                         f"cannot fail", o.line)
                return
            et = o.args[0]
            if et not in self.event_types:
                self.err("T-Event",
                         f"'{o.name}' names undeclared event type '{et}'",
                         o.line)

        if spec.requires_antagonist:
            names = {a.name for a in self.prog.antagonists}
            if not o.args or o.args[0] not in names:
                self.err("unknown",
                         f"'{o.name}' requires a declared antagonist pair",
                         o.line)

    # ── circuit expression evaluation ────────────────────────────────

    def _eval_expr(self, expr, line: int) -> Circuit | None:
        if isinstance(expr, CircuitRef):
            c = self.circuits.get(expr.name)
            if c is None:
                self.err("unknown", f"no circuit '{expr.name}'", line)
                return None
            return c

        base = self._eval_expr(getattr(expr, "base", None), line)
        if base is None:
            return None

        if isinstance(expr, WithoutElement):
            if expr.element not in base.elements:
                self.warn("lesion",
                          f"element '{expr.element}' is not present in "
                          f"'{base.name}'; removal is the identity", line)
            return op_wo_elem(base, expr.element)

        if isinstance(expr, WithoutReturn):
            return op_wo_ret(base, expr.frm)

        if isinstance(expr, WithScaling):
            if expr.element not in base.elements:
                self.warn("lesion",
                          f"element '{expr.element}' is not present in "
                          f"'{base.name}'; scaling is the identity", line)
            if expr.factor <= 0:
                self.err(
                    "T-Lesion",
                    "scaling must be strictly positive; attenuation cannot "
                    "express severance (use 'without element')",
                    line,
                )
                return base
            return op_scale(base, expr.element, expr.factor)

        if isinstance(expr, WithNoise):
            for s in (expr.s1, expr.s2):
                if s not in STRATUM_ORDER:
                    self.err("unknown", f"no stratum '{s}'", line)
                    return base
            return op_noise(base, expr.s1, expr.s2, expr.amplitude)

        if isinstance(expr, Reroute):
            for cname in expr.path:
                if cname not in self.compartments:
                    self.err("unknown",
                             f"reroute path references undeclared compartment "
                             f"'{cname}'", line)
                    return base
            out = op_reroute(base, expr.frm, expr.path)
            for cname in expr.path:
                if cname not in out.compartments:
                    out.compartments[cname] = self.compartments[cname]

            # A reroute crossing strata is legal but costly; say so.
            strata = {
                out.stratum_of(c) for c in expr.path if out.stratum_of(c)
            }
            if len(strata) > 1:
                self.note(
                    "reroute",
                    f"rerouted return traverses strata {sorted(strata)}; "
                    f"the substituted path carries the delay and bandwidth of "
                    f"the higher stratum",
                    line,
                )
            return out

        self.err("internal", f"unhandled circuit expression {type(expr).__name__}",
                 line)
        return None


def check(prog: Program) -> CheckResult:
    return Checker(prog).check()
