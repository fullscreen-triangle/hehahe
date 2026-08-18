"""Operational semantics.

Implements the reduction rules of specification section 6:

    E-Lesion    apply one pending ablation
    E-Observe   discharge one pending observable, incrementing the record
    E-Report    produce the result once both sets are exhausted

Lesions precede observations, so an experiment observes the circuit it
declared rather than an intermediate. The committed record is monotone, so a
repeated value in the store is never a return to an earlier configuration --
which matters because the underlying system has no terminal state.

Phased experiments (extension E4) run each phase as an independent
experiment sharing the intact circuit, or cumulatively when a phase names a
predecessor with `from`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .ast_nodes import (
    CircuitRef, ExperimentDecl, Program, Reroute, WithNoise, WithScaling,
    WithoutElement, WithoutReturn,
)
from .backend import Backend, Measurement
from .checker import CheckResult, check
from .circuit import (
    Circuit, Closure, reroute as op_reroute, with_noise as op_noise,
    with_scaling as op_scale, without_element as op_wo_elem,
    without_return as op_wo_ret,
)
from .parser import parse


@dataclass
class ArmResult:
    """One arm of an experiment: the intact circuit or one lesion."""

    name: str
    circuit: Circuit
    closure: str
    apertures: list[str] = field(default_factory=list)
    store: dict[str, Measurement] = field(default_factory=dict)
    record: int = 0
    provenance: list[str] = field(default_factory=list)


@dataclass
class PhaseResult:
    name: str
    arms: list[ArmResult] = field(default_factory=list)


@dataclass
class ExperimentResult:
    name: str
    phased: bool
    arms: list[ArmResult] = field(default_factory=list)
    phases: list[PhaseResult] = field(default_factory=list)

    def all_arms(self) -> list[ArmResult]:
        if not self.phased:
            return self.arms
        return [a for p in self.phases for a in p.arms]


@dataclass
class RunResult:
    experiments: list[ExperimentResult] = field(default_factory=list)
    checked: CheckResult | None = None

    def experiment(self, name: str) -> ExperimentResult | None:
        for e in self.experiments:
            if e.name == name:
                return e
        return None


class Runtime:
    def __init__(self, prog: Program, checked: CheckResult,
                 backend: Backend | None = None):
        self.prog = prog
        self.checked = checked
        self.backend = backend or Backend()

    # ── circuit expression evaluation ────────────────────────────────

    def eval_expr(self, expr) -> Circuit:
        if isinstance(expr, CircuitRef):
            return self.checked.circuits[expr.name]

        base = self.eval_expr(expr.base)

        if isinstance(expr, WithoutElement):
            return op_wo_elem(base, expr.element)
        if isinstance(expr, WithoutReturn):
            return op_wo_ret(base, expr.frm)
        if isinstance(expr, WithScaling):
            return op_scale(base, expr.element, expr.factor)
        if isinstance(expr, WithNoise):
            return op_noise(base, expr.s1, expr.s2, expr.amplitude)
        if isinstance(expr, Reroute):
            out = op_reroute(base, expr.frm, expr.path)
            for cname in expr.path:
                if cname not in out.compartments:
                    c = self.checked.circuits
                    for circ in c.values():
                        if cname in circ.compartments:
                            out.compartments[cname] = circ.compartments[cname]
                            break
            return out

        raise TypeError(f"unhandled circuit expression {type(expr).__name__}")

    # ── E-Observe ────────────────────────────────────────────────────

    def observe_all(self, c: Circuit, observables, name: str) -> ArmResult:
        arm = ArmResult(
            name=name,
            circuit=c,
            closure=c.closure_index().value,
            apertures=[a.report() for a in c.apertures()],
            provenance=list(c.provenance),
        )

        ctx = {
            "event_types": self.checked.event_types,
            "antagonists": self.checked.antagonists,
            "circuits": self.checked.circuits,
        }

        for o in observables:
            m = self.backend.measure(c, o.name, o.args, ctx)
            arm.store[o.key()] = m
            arm.record += 1  # monotone: strictly increases at each E-Observe

        return arm

    # ── E-Lesion, then E-Observe, then E-Report ──────────────────────

    def run_experiment(self, x: ExperimentDecl) -> ExperimentResult:
        res = ExperimentResult(name=x.name, phased=x.is_phased)
        intact = self.eval_expr(x.intact)

        if not x.is_phased:
            res.arms.append(self.observe_all(intact, x.observables, "intact"))
            for les in x.lesions:
                c = self.eval_expr(les.expr)
                res.arms.append(self.observe_all(c, x.observables, les.name))
            return res

        by_name: dict[str, Circuit] = {}
        for ph in x.phases:
            pr = PhaseResult(name=ph.name)

            base = intact
            if ph.from_phase and ph.from_phase in by_name:
                base = by_name[ph.from_phase]

            if not ph.lesions:
                pr.arms.append(self.observe_all(base, ph.observables, "intact"))
                by_name[ph.name] = base
            else:
                last = base
                for les in ph.lesions:
                    c = self.eval_expr(les.expr)
                    pr.arms.append(self.observe_all(c, ph.observables, les.name))
                    last = c
                by_name[ph.name] = last

            res.phases.append(pr)

        return res

    def run(self) -> RunResult:
        out = RunResult(checked=self.checked)
        for x in self.prog.experiments:
            out.experiments.append(self.run_experiment(x))
        return out


def run_source(src: str, backend: Backend | None = None,
               strict: bool = True) -> RunResult:
    """Parse, check, and run a .vvs program."""
    prog = parse(src)
    checked = check(prog)

    if strict and not checked.ok:
        from .checker import CheckError

        raise CheckError(checked.errors)

    return Runtime(prog, checked, backend).run()


def run_file(path: str, backend: Backend | None = None,
             strict: bool = True) -> RunResult:
    with open(path, "r", encoding="utf-8") as fh:
        return run_source(fh.read(), backend, strict)
