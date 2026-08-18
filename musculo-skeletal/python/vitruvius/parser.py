"""Recursive-descent parser for Vitruvius.

The grammar is LL(1) (specification Proposition 3.2), so one token of
lookahead suffices everywhere and no backtracking is used.

Two syntactic facts are load-bearing and enforced here:

  * `outbound` and `return` are mandatory in a circuit declaration, so an
    open circuit cannot arise by omission -- only through an explicit
    `without` / `reroute` operator inside an experiment.
  * `excluding`-style optionality is absent: postfix lesion operators are
    parsed as a left-associative chain, matching the left-recursion
    elimination given in the specification.
"""

from __future__ import annotations

from .ast_nodes import (
    AntagonistDecl, CircuitDecl, CircuitRef, CompartmentDecl, ElementDecl,
    EventTypeDecl, ExperimentDecl, FloorSpec, InstanceDecl, LesionDecl,
    Observable, PhaseDecl, Program, Quantity, Reroute, TemplateDecl,
    WithNoise, WithScaling, WithoutElement, WithoutReturn,
)
from .lexer import STRATA, Tok, Token, tokenize


class ParseError(Exception):
    def __init__(self, msg: str, tok: Token):
        super().__init__(f"{msg} (got {tok.text!r} at line {tok.line}, col {tok.col})")
        self.token = tok


class Parser:
    def __init__(self, toks: list[Token]):
        self.toks = toks
        self.i = 0

    # ── token helpers ────────────────────────────────────────────────

    @property
    def cur(self) -> Token:
        return self.toks[self.i]

    def at(self, kind: Tok, text: str | None = None) -> bool:
        t = self.cur
        return t.kind == kind and (text is None or t.text == text)

    def at_kw(self, *words: str) -> bool:
        return self.cur.kind == Tok.KEYWORD and self.cur.text in words

    def eat(self, kind: Tok, text: str | None = None) -> Token:
        if not self.at(kind, text):
            want = text or kind.name
            raise ParseError(f"expected {want}", self.cur)
        t = self.cur
        self.i += 1
        return t

    def kw(self, word: str) -> Token:
        return self.eat(Tok.KEYWORD, word)

    def punct(self, ch: str) -> Token:
        return self.eat(Tok.PUNCT, ch)

    def ident(self) -> str:
        # Stratum names are keywords but are legal in identifier position
        # inside paths and argument lists.
        if self.cur.kind == Tok.KEYWORD and self.cur.text in STRATA:
            t = self.cur
            self.i += 1
            return t.text
        return self.eat(Tok.IDENT).text

    def quantity(self) -> Quantity:
        t = self.cur
        if t.kind == Tok.QUANTITY:
            self.i += 1
            return Quantity(float(t.value), t.unit)
        if t.kind == Tok.NUMBER:
            self.i += 1
            return Quantity(float(t.value), "")
        raise ParseError("expected a quantity", t)

    def number(self) -> float:
        t = self.cur
        if t.kind in (Tok.NUMBER, Tok.QUANTITY):
            self.i += 1
            return float(t.value)
        raise ParseError("expected a number", t)

    # ── program ──────────────────────────────────────────────────────

    def parse_program(self) -> Program:
        prog = Program()

        if self.at_kw("module"):
            self.kw("module")
            prog.module = self.ident()
            self.punct(";")

        while self.at_kw("import"):
            self.kw("import")
            prog.imports.append(self.ident())
            self.punct(";")

        while not self.at(Tok.EOF):
            if self.at_kw("compartment"):
                prog.compartments.append(self.parse_compartment())
            elif self.at_kw("circuit"):
                decl = self.parse_circuit_or_template_or_instance()
                if isinstance(decl, TemplateDecl):
                    prog.templates.append(decl)
                elif isinstance(decl, InstanceDecl):
                    prog.instances.append(decl)
                else:
                    prog.circuits.append(decl)
            elif self.at_kw("event"):
                prog.event_types.append(self.parse_event_type())
            elif self.at_kw("antagonist"):
                prog.antagonists.append(self.parse_antagonist())
            elif self.at_kw("experiment"):
                prog.experiments.append(self.parse_experiment())
            else:
                raise ParseError("expected a declaration", self.cur)

        return prog

    # ── compartment ──────────────────────────────────────────────────

    def parse_compartment(self) -> CompartmentDecl:
        ln = self.kw("compartment").line
        name = self.ident()
        self.punct("{")
        self.kw("capacitance")
        self.punct(":")
        cap = self.quantity()
        self.punct(";")
        self.kw("stratum")
        self.punct(":")
        if not self.at_kw(*STRATA):
            raise ParseError("expected a stratum name", self.cur)
        stratum = self.cur.text
        self.i += 1
        self.punct(";")
        self.punct("}")
        return CompartmentDecl(name, cap, stratum, ln)

    # ── circuit / template / instance ────────────────────────────────

    def parse_circuit_or_template_or_instance(self):
        ln = self.kw("circuit").line

        if self.at_kw("template"):
            self.kw("template")
            name = self.ident()
            self.punct("(")
            params: list[str] = []
            if not self.at(Tok.PUNCT, ")"):
                params.append(self.ident())
                while self.at(Tok.PUNCT, ","):
                    self.punct(",")
                    params.append(self.ident())
            self.punct(")")
            floor, outb, ret, elems = self.parse_circuit_body()
            return TemplateDecl(name, params, floor, outb, ret, elems, ln)

        name = self.ident()

        if self.at(Tok.PUNCT, "="):  # instance
            self.punct("=")
            tmpl = self.ident()
            self.punct("(")
            args: list[object] = []
            if not self.at(Tok.PUNCT, ")"):
                args.append(self.template_arg())
                while self.at(Tok.PUNCT, ","):
                    self.punct(",")
                    args.append(self.template_arg())
            self.punct(")")
            self.punct(";")
            return InstanceDecl(name, tmpl, args, ln)

        floor, outb, ret, elems = self.parse_circuit_body()
        return CircuitDecl(name, floor, outb, ret, elems, ln)

    def template_arg(self) -> object:
        if self.cur.kind in (Tok.NUMBER, Tok.QUANTITY):
            return self.quantity()
        return self.ident()

    def parse_circuit_body(self):
        self.punct("{")
        self.kw("floor")
        self.punct(":")
        floor = self.parse_floor_spec()
        self.punct(";")
        self.kw("outbound")
        self.punct(":")
        outb = self.parse_path()
        self.punct(";")
        self.kw("return")
        self.punct(":")
        ret = self.parse_path()
        self.punct(";")

        elems: list[ElementDecl] = []
        while self.at_kw("element"):
            elems.append(self.parse_element())
        self.punct("}")
        return floor, outb, ret, elems

    def parse_floor_spec(self) -> FloorSpec:
        if self.at_kw("derived"):
            self.kw("derived")
            self.punct("(")
            call = self.ident()
            arg = None
            if self.at(Tok.PUNCT, "("):
                self.punct("(")
                arg = self.ident()
                self.punct(")")
            self.punct(")")
            return FloorSpec(derived_call=call, derived_arg=arg)
        return FloorSpec(literal=self.quantity())

    def parse_path(self) -> list[str]:
        path = [self.ident()]
        while self.at(Tok.ARROW):
            self.eat(Tok.ARROW)
            path.append(self.ident())
        return path

    def parse_element(self) -> ElementDecl:
        ln = self.kw("element").line
        name = self.ident()
        self.kw("conducts")
        src = self.ident()
        self.eat(Tok.ARROW)
        dst = self.ident()

        delay = None
        gain = 1.0
        if self.at_kw("delay"):
            self.kw("delay")
            delay = self.quantity()
        if self.at_kw("gain"):
            self.kw("gain")
            gain = self.number()
        self.punct(";")
        return ElementDecl(name, src, dst, delay, gain, ln)

    # ── event types / antagonists ────────────────────────────────────

    def parse_event_type(self) -> EventTypeDecl:
        ln = self.kw("event").line
        self.kw("type")
        name = self.ident()
        self.punct("=")
        ctor = self.ident()
        args: list[str] = []
        if self.at(Tok.PUNCT, "("):
            self.punct("(")
            if not self.at(Tok.PUNCT, ")"):
                args.append(self.ident())
                while self.at(Tok.PUNCT, ","):
                    self.punct(",")
                    args.append(self.ident())
            self.punct(")")
        self.punct(";")
        return EventTypeDecl(name, ctor, args, ln)

    def parse_antagonist(self) -> AntagonistDecl:
        ln = self.kw("antagonist").line
        name = self.ident()
        self.punct("{")
        self.kw("agonist")
        self.punct(":")
        ago = self.ident()
        self.punct(";")
        self.kw("antagonist")
        self.punct(":")
        ant = self.ident()
        self.punct(";")
        self.kw("shared")
        self.punct(":")
        shared = [self.ident()]
        while self.at(Tok.PUNCT, ","):
            self.punct(",")
            shared.append(self.ident())
        self.punct(";")
        self.punct("}")
        return AntagonistDecl(name, ago, ant, shared, ln)

    # ── experiments ──────────────────────────────────────────────────

    def parse_experiment(self) -> ExperimentDecl:
        ln = self.kw("experiment").line
        name = self.ident()
        self.punct("{")
        self.kw("intact")
        self.punct(":")
        intact = self.parse_circuit_expr()
        self.punct(";")

        lesions: list[LesionDecl] = []
        observables: list[Observable] = []
        phases: list[PhaseDecl] = []

        while not self.at(Tok.PUNCT, "}"):
            if self.at_kw("lesion"):
                lesions.append(self.parse_lesion())
            elif self.at_kw("phase"):
                phases.append(self.parse_phase())
            elif self.at_kw("observe"):
                self.kw("observe")
                self.punct(":")
                observables = self.parse_observables()
                self.punct(";")
            else:
                raise ParseError("expected lesion, phase, or observe", self.cur)

        self.punct("}")

        if phases and (lesions or observables):
            raise ParseError(
                "an experiment is either phased or flat, not both", self.cur
            )
        return ExperimentDecl(name, intact, lesions, observables, phases, ln)

    def parse_phase(self) -> PhaseDecl:
        ln = self.kw("phase").line
        name = self.ident()
        from_phase = None
        if self.at_kw("from"):
            self.kw("from")
            from_phase = self.ident()
        self.punct("{")

        lesions: list[LesionDecl] = []
        observables: list[Observable] = []
        while not self.at(Tok.PUNCT, "}"):
            if self.at_kw("lesion"):
                lesions.append(self.parse_lesion())
            elif self.at_kw("observe"):
                self.kw("observe")
                self.punct(":")
                observables = self.parse_observables()
                self.punct(";")
            else:
                raise ParseError("expected lesion or observe", self.cur)
        self.punct("}")
        return PhaseDecl(name, lesions, observables, from_phase, ln)

    def parse_lesion(self) -> LesionDecl:
        ln = self.kw("lesion").line
        name = self.ident()
        self.punct(":")
        expr = self.parse_circuit_expr()
        self.punct(";")
        return LesionDecl(name, expr, ln)

    def parse_observables(self) -> list[Observable]:
        obs = [self.parse_observable()]
        while self.at(Tok.PUNCT, ","):
            self.punct(",")
            obs.append(self.parse_observable())
        return obs

    def parse_observable(self) -> Observable:
        ln = self.cur.line
        name = self.ident()
        args: list[str] = []
        if self.at(Tok.PUNCT, "("):
            self.punct("(")
            if not self.at(Tok.PUNCT, ")"):
                args.append(self.ident())
                while self.at(Tok.PUNCT, ","):
                    self.punct(",")
                    args.append(self.ident())
            self.punct(")")
        return Observable(name, args, ln)

    # ── circuit expressions ──────────────────────────────────────────

    def parse_circuit_expr(self):
        """Left-associative chain of postfix lesion operators."""
        ln = self.cur.line
        expr = CircuitRef(self.ident(), ln)

        while self.at_kw("without", "with", "reroute"):
            if self.at_kw("without"):
                self.kw("without")
                if self.at_kw("return"):
                    self.kw("return")
                    self.punct("(")
                    frm = self.ident()
                    self.punct(")")
                    expr = WithoutReturn(expr, frm, ln)
                elif self.at_kw("element"):
                    self.kw("element")
                    self.punct("(")
                    el = self.ident()
                    self.punct(")")
                    expr = WithoutElement(expr, el, ln)
                else:
                    raise ParseError("expected 'return' or 'element'", self.cur)

            elif self.at_kw("with"):
                self.kw("with")
                if self.at_kw("noise"):
                    self.kw("noise")
                    self.kw("across")
                    s1 = self.ident()
                    self.punct(",")
                    s2 = self.ident()
                    self.punct("(")
                    amp = self.number()
                    self.punct(")")
                    expr = WithNoise(expr, s1, s2, amp, ln)
                else:
                    el = self.ident()
                    self.kw("scaling")
                    expr = WithScaling(expr, el, self.number(), ln)

            else:  # reroute
                self.kw("reroute")
                self.kw("return")
                self.punct("(")
                frm = self.ident()
                self.punct(")")
                self.kw("through")
                expr = Reroute(expr, frm, self.parse_path(), ln)

        return expr


def parse(src: str) -> Program:
    return Parser(tokenize(src)).parse_program()
