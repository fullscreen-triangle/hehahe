"""Abstract syntax for Vitruvius.

Mirrors the context-free grammar of specification section 3, plus the
E1 (templates), E3 (reroute), E4 (phases) and E6 (antagonist) extensions.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ── quantities ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class Quantity:
    """A number with a unit, normalised to SI at construction."""

    value: float
    unit: str

    _SI: dict[str, tuple[float, str]] = field(default=None, repr=False, compare=False)

    def si(self) -> float:
        scale = {
            "s": 1.0, "ms": 1e-3,
            "F": 1.0, "mF": 1e-3, "uF": 1e-6, "nF": 1e-9, "pF": 1e-12,
            "Hz": 1.0, "N": 1.0, "m": 1.0, "mm": 1e-3, "W": 1.0, "C": 1.0,
        }
        return self.value * scale.get(self.unit, 1.0)

    def dimension(self) -> str:
        return {
            "s": "time", "ms": "time",
            "F": "capacitance", "mF": "capacitance", "uF": "capacitance",
            "nF": "capacitance", "pF": "capacitance",
            "Hz": "frequency", "N": "force", "m": "length", "mm": "length",
            "W": "power", "C": "charge",
        }.get(self.unit, "dimensionless")

    def __str__(self) -> str:
        return f"{self.value:g} {self.unit}"


# ── declarations ─────────────────────────────────────────────────────

@dataclass
class CompartmentDecl:
    name: str
    capacitance: Quantity
    stratum: str
    line: int = 0


@dataclass
class ElementDecl:
    name: str
    src: str
    dst: str
    delay: Quantity | None = None
    gain: float = 1.0
    line: int = 0


@dataclass
class FloorSpec:
    """Either a literal quantity or a `derived(expr)` form."""

    literal: Quantity | None = None
    derived_call: str | None = None
    derived_arg: str | None = None

    @property
    def is_derived(self) -> bool:
        return self.derived_call is not None


@dataclass
class CircuitDecl:
    name: str
    floor: FloorSpec
    outbound: list[str]
    ret: list[str]
    elements: list[ElementDecl] = field(default_factory=list)
    line: int = 0


@dataclass
class TemplateDecl:
    """E1. A parameterised circuit; expanded before typechecking."""

    name: str
    params: list[str]
    floor: FloorSpec
    outbound: list[str]
    ret: list[str]
    elements: list[ElementDecl] = field(default_factory=list)
    line: int = 0


@dataclass
class InstanceDecl:
    """E1. `circuit foo = template(args);`"""

    name: str
    template: str
    args: list[object]
    line: int = 0


@dataclass
class EventTypeDecl:
    name: str
    ctor: str
    args: list[str]
    line: int = 0


@dataclass
class AntagonistDecl:
    """E6. Two circuits coupled through shared compartments."""

    name: str
    agonist: str
    antagonist: str
    shared: list[str]
    line: int = 0


# ── circuit expressions (lesion operators) ───────────────────────────

@dataclass
class CircuitRef:
    name: str
    line: int = 0


@dataclass
class WithoutElement:
    base: object
    element: str
    line: int = 0


@dataclass
class WithoutReturn:
    base: object
    frm: str
    line: int = 0


@dataclass
class WithScaling:
    base: object
    element: str
    factor: float
    line: int = 0


@dataclass
class WithNoise:
    base: object
    s1: str
    s2: str
    amplitude: float
    line: int = 0


@dataclass
class Reroute:
    """E3. Replace the return phase from `frm` with an explicit path."""

    base: object
    frm: str
    path: list[str]
    line: int = 0


CircuitExpr = (
    CircuitRef | WithoutElement | WithoutReturn | WithScaling | WithNoise | Reroute
)


# ── experiments ──────────────────────────────────────────────────────

@dataclass
class Observable:
    name: str
    args: list[str] = field(default_factory=list)
    line: int = 0

    def key(self) -> str:
        return f"{self.name}({','.join(self.args)})" if self.args else self.name


@dataclass
class LesionDecl:
    name: str
    expr: object
    line: int = 0


@dataclass
class PhaseDecl:
    """E4. A named stage with its own lesions and observations."""

    name: str
    lesions: list[LesionDecl]
    observables: list[Observable]
    from_phase: str | None = None
    line: int = 0


@dataclass
class ExperimentDecl:
    name: str
    intact: object
    lesions: list[LesionDecl] = field(default_factory=list)
    observables: list[Observable] = field(default_factory=list)
    phases: list[PhaseDecl] = field(default_factory=list)
    line: int = 0

    @property
    def is_phased(self) -> bool:
        return bool(self.phases)


@dataclass
class Program:
    module: str | None = None
    imports: list[str] = field(default_factory=list)
    compartments: list[CompartmentDecl] = field(default_factory=list)
    circuits: list[CircuitDecl] = field(default_factory=list)
    templates: list[TemplateDecl] = field(default_factory=list)
    instances: list[InstanceDecl] = field(default_factory=list)
    event_types: list[EventTypeDecl] = field(default_factory=list)
    antagonists: list[AntagonistDecl] = field(default_factory=list)
    experiments: list[ExperimentDecl] = field(default_factory=list)
