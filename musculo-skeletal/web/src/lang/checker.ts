/**
 * Typechecker and static analyses.
 *
 * The four non-standard rules:
 *   Rule I   compartment consistency -- charge carries the capacitance it
 *                                      was computed against
 *   Rule II  stratum containment     -- an element may touch only adjacent
 *                                      strata
 *   Rule III floor positivity        -- a fractional observable needs beta > 0
 *   Rule IV  typed-event estimation  -- kappa requires a declared event type
 *
 * Diagnostics separate errors (which reject) from warnings (which do not).
 * An open circuit is a warning, never an error: it is the model of
 * deafferentation and simulating it is the point.
 *
 * None of this consults a backend, so the diagnostics are identical under
 * every conforming backend and available at the cost of parsing.
 */

import {
  type AntagonistDecl, type CircuitDecl, type CircuitExpr, type ElementDecl,
  type Program, type Quantity, type Span, dimension, si,
} from "./ast";
import {
  type Circuit, type Compartment, type Element, apertureReport, apertures,
  closureIndex, floorOf, reroute, separationCost, stratumOf, withNoise,
  withScaling, withoutElement, withoutReturn,
} from "./circuit";
import type { Stratum } from "./lexer";
import { OBSERVABLES } from "./observables";

export const STRATUM_ORDER: Record<Stratum, number> = {
  reflex: 0, spinal: 1, supraspinal: 2,
};

export type Severity = "error" | "warning" | "note";

export interface Diagnostic {
  severity: Severity;
  rule: string;
  message: string;
  span?: Span;
}

export interface CheckResult {
  circuits: Map<string, Circuit>;
  diagnostics: Diagnostic[];
  eventTypes: Map<string, string[]>;
  antagonists: Map<string, AntagonistDecl>;
  ok: boolean;
  errors: Diagnostic[];
  warnings: Diagnostic[];
}

class Checker {
  private diags: Diagnostic[] = [];
  private compartments = new Map<string, Compartment>();
  private circuits = new Map<string, Circuit>();
  private eventTypes = new Map<string, string[]>();

  constructor(private prog: Program) {}

  private err(rule: string, message: string, span?: Span) {
    this.diags.push({ severity: "error", rule, message, span });
  }
  private warn(rule: string, message: string, span?: Span) {
    this.diags.push({ severity: "warning", rule, message, span });
  }
  private note(rule: string, message: string, span?: Span) {
    this.diags.push({ severity: "note", rule, message, span });
  }

  check(): CheckResult {
    this.collectCompartments();
    this.expandTemplates();
    this.buildCircuits();
    this.checkEventTypes();
    this.checkExperiments();

    const errors = this.diags.filter((d) => d.severity === "error");
    const warnings = this.diags.filter((d) => d.severity === "warning");
    return {
      circuits: this.circuits,
      diagnostics: this.diags,
      eventTypes: this.eventTypes,
      antagonists: new Map(this.prog.antagonists.map((a) => [a.name, a])),
      ok: errors.length === 0,
      errors,
      warnings,
    };
  }

  private collectCompartments() {
    for (const d of this.prog.compartments) {
      if (this.compartments.has(d.name)) {
        this.err("duplicate", `compartment '${d.name}' redeclared`, d.span);
        continue;
      }
      if (dimension(d.capacitance) !== "capacitance") {
        this.err(
          "units",
          `compartment '${d.name}' capacitance has unit '${d.capacitance.unit}', expected a capacitance`,
          d.span,
        );
      }
      const cap = si(d.capacitance);
      if (cap <= 0) this.err("units", `compartment '${d.name}' capacitance must be > 0`, d.span);
      this.compartments.set(d.name, { name: d.name, capacitance: cap, stratum: d.stratum });
    }
  }

  /** E1. Expansion happens before typechecking, so every proof applies. */
  private expandTemplates() {
    const tmpls = new Map(this.prog.templates.map((t) => [t.name, t]));

    for (const inst of this.prog.instances) {
      const t = tmpls.get(inst.template);
      if (!t) {
        this.err("unknown", `no template '${inst.template}'`, inst.span);
        continue;
      }
      if (inst.args.length !== t.params.length) {
        this.err(
          "arity",
          `template '${t.name}' expects ${t.params.length} arguments, got ${inst.args.length}`,
          inst.span,
        );
        continue;
      }
      const sub = new Map<string, string | Quantity>();
      t.params.forEach((p, i) => sub.set(p, inst.args[i]));

      const repName = (x: string): string => {
        const v = sub.get(x);
        return typeof v === "string" ? v : x;
      };

      const elements: ElementDecl[] = t.elements.map((e) => ({
        ...e,
        name: `${inst.name}_${e.name}`,
        src: repName(e.src),
        dst: repName(e.dst),
      }));

      let floor = t.floor;
      if (floor.derivedArg) {
        const v = sub.get(floor.derivedArg);
        if (typeof v === "string") floor = { ...floor, derivedArg: v };
      }

      this.prog.circuits.push({
        kind: "circuit",
        name: inst.name,
        floor,
        outbound: t.outbound.map(repName),
        ret: t.ret.map(repName),
        elements,
        span: inst.span,
      });
    }
  }

  private buildCircuits() {
    for (const d of this.prog.circuits) {
      if (this.circuits.has(d.name)) {
        this.err("duplicate", `circuit '${d.name}' redeclared`, d.span);
        continue;
      }

      const used = new Set<string>([...d.outbound, ...d.ret]);
      for (const e of d.elements) { used.add(e.src); used.add(e.dst); }

      const comps = new Map<string, Compartment>();
      for (const name of used) {
        const c = this.compartments.get(name);
        if (!c) {
          this.err("unknown", `circuit '${d.name}' references undeclared compartment '${name}'`, d.span);
          continue;
        }
        comps.set(name, c);
      }

      const elements = new Map<string, Element>();
      for (const e of d.elements) {
        if (elements.has(e.name)) {
          this.err("duplicate", `element '${e.name}' redeclared in '${d.name}'`, e.span);
          continue;
        }
        if (e.delay && dimension(e.delay) !== "time") {
          this.err("units", `element '${e.name}' delay has unit '${e.delay.unit}', expected a time`, e.span);
        }
        elements.set(e.name, {
          name: e.name, src: e.src, dst: e.dst,
          delay: e.delay ? si(e.delay) : 0, gain: e.gain,
        });
      }

      const circ: Circuit = {
        name: d.name,
        compartments: comps,
        outbound: [...d.outbound],
        ret: [...d.ret],
        elements,
        floorSpec: d.floor,
        noiseEdges: [],
        provenance: [],
      };

      this.checkStrata(circ, d);
      this.checkFloor(circ, d);
      this.circuits.set(d.name, circ);
    }
  }

  /** Rule II. */
  private checkStrata(c: Circuit, d: CircuitDecl) {
    for (const e of c.elements.values()) {
      const a = stratumOf(c, e.src);
      const b = stratumOf(c, e.dst);
      if (!a || !b) continue;
      if (Math.abs(STRATUM_ORDER[a] - STRATUM_ORDER[b]) >= 2) {
        const decl = d.elements.find((x) => x.name === e.name);
        this.err(
          "T-Stratum",
          `element '${e.name}' in circuit '${c.name}' conducts ${a} -> ${b}, which are not ` +
          `adjacent. Influence between non-adjacent strata must traverse the intervening ` +
          `stratum; to model a shortcut deliberately, use 'with noise across'`,
          decl?.span ?? d.span,
        );
      }
    }
  }

  /** Rule III. */
  private checkFloor(c: Circuit, d: CircuitDecl) {
    const spec = d.floor;
    if (spec.derivedCall === "sample_minimum") {
      this.warn(
        "T-Floor",
        `circuit '${c.name}' derives its floor by sample_minimum, which is positive ` +
        `whenever the sample is and therefore cannot falsify a positivity claim; ` +
        `prefer resting_cut`,
        d.span,
      );
    }
    if (spec.derivedArg && !c.compartments.has(spec.derivedArg)) {
      this.err(
        "T-Floor",
        `circuit '${c.name}' derives its floor from unknown compartment '${spec.derivedArg}'`,
        d.span,
      );
      return;
    }
    const beta = floorOf(c);
    if (beta <= 0) {
      this.err(
        "T-Floor",
        `circuit '${c.name}' has floor ${beta}; a fractional observable requires a strictly positive floor`,
        d.span,
      );
    }
  }

  private checkEventTypes() {
    for (const d of this.prog.eventTypes) {
      if (this.eventTypes.has(d.name)) {
        this.err("duplicate", `event type '${d.name}' redeclared`, d.span);
        continue;
      }
      for (const a of d.args) {
        if (!this.compartments.has(a)) {
          this.err("unknown", `event type '${d.name}' references undeclared compartment '${a}'`, d.span);
        }
      }
      this.eventTypes.set(d.name, [...d.args]);
    }
  }

  private checkExperiments() {
    for (const x of this.prog.experiments) {
      const base = this.evalExpr(x.intact, x.span);
      if (!base) continue;

      const groups: { lesions: typeof x.lesions; observables: typeof x.observables }[] =
        x.phases.length
          ? x.phases.map((p) => ({ lesions: p.lesions, observables: p.observables }))
          : [{ lesions: x.lesions, observables: x.observables }];

      for (const g of groups) {
        const seenScaling = new Set<string>();
        for (const les of g.lesions) {
          this.checkLesionKeys(les.expr, seenScaling, les.span);
          const c = this.evalExpr(les.expr, les.span);
          if (!c) continue;
          if (closureIndex(c) === "open") {
            for (const ap of apertures(c)) {
              this.warn("aperture", `lesion '${les.name}': ${apertureReport(ap)}`, les.span);
            }
          }
        }
        for (const o of g.observables) this.checkObservable(o, x.name);
      }
    }
  }

  /** Duplicate scalings of one element break idempotence. */
  private checkLesionKeys(expr: CircuitExpr, seen: Set<string>, span: Span) {
    let node: CircuitExpr | undefined = expr;
    while (node) {
      if (node.op === "withScaling") {
        if (seen.has(node.element)) {
          this.err(
            "T-Lesion",
            `element '${node.element}' scaled more than once; repeated scaling is not ` +
            `idempotent, so lesion order would matter`,
            span,
          );
        }
        seen.add(node.element);
      }
      node = "base" in node ? node.base : undefined;
    }
  }

  private checkObservable(o: { name: string; args: string[]; span: Span }, expName: string) {
    const spec = OBSERVABLES.get(o.name);
    if (!spec) {
      this.err(
        "unknown-observable",
        `experiment '${expName}' requests unknown observable '${o.name}'. Observables must ` +
        `have a defined measurement procedure`,
        o.span,
      );
      return;
    }
    if (spec.arity !== o.args.length) {
      this.err("arity", `observable '${o.name}' takes ${spec.arity} argument(s), got ${o.args.length}`, o.span);
      return;
    }
    // Rule IV.
    if (spec.requiresEventType) {
      if (!o.args.length) {
        this.err(
          "T-Event",
          `'${o.name}' requires a declared event type; an instance-specific estimate is an ` +
          `identity and cannot fail`,
          o.span,
        );
        return;
      }
      if (!this.eventTypes.has(o.args[0])) {
        this.err("T-Event", `'${o.name}' names undeclared event type '${o.args[0]}'`, o.span);
      }
    }
    if (spec.requiresAntagonist) {
      const names = new Set(this.prog.antagonists.map((a) => a.name));
      if (!o.args.length || !names.has(o.args[0])) {
        this.err("unknown", `'${o.name}' requires a declared antagonist pair`, o.span);
      }
    }
    if (o.name === "band_power" && o.args.length) {
      if (!(o.args[0] in STRATUM_ORDER)) {
        this.err("unknown", `band_power names unknown stratum '${o.args[0]}'`, o.span);
      }
    }
  }

  evalExpr(expr: CircuitExpr, span: Span): Circuit | null {
    if (expr.op === "ref") {
      const c = this.circuits.get(expr.name);
      if (!c) { this.err("unknown", `no circuit '${expr.name}'`, span); return null; }
      return c;
    }
    const base = this.evalExpr(expr.base, span);
    if (!base) return null;

    switch (expr.op) {
      case "withoutElement":
        if (!base.elements.has(expr.element)) {
          this.warn("lesion", `element '${expr.element}' is not present in '${base.name}'; removal is the identity`, span);
        }
        return withoutElement(base, expr.element);

      case "withoutReturn":
        return withoutReturn(base, expr.from);

      case "withScaling":
        if (!base.elements.has(expr.element)) {
          this.warn("lesion", `element '${expr.element}' is not present in '${base.name}'; scaling is the identity`, span);
        }
        if (expr.factor <= 0) {
          this.err(
            "T-Lesion",
            "scaling must be strictly positive; attenuation cannot express severance (use 'without element')",
            span,
          );
          return base;
        }
        return withScaling(base, expr.element, expr.factor);

      case "withNoise":
        for (const s of [expr.s1, expr.s2]) {
          if (!(s in STRATUM_ORDER)) { this.err("unknown", `no stratum '${s}'`, span); return base; }
        }
        return withNoise(base, expr.s1, expr.s2, expr.amplitude);

      case "reroute": {
        for (const name of expr.path) {
          if (!this.compartments.has(name)) {
            this.err("unknown", `reroute path references undeclared compartment '${name}'`, span);
            return base;
          }
        }
        const out = reroute(base, expr.from, expr.path);
        for (const name of expr.path) {
          if (!out.compartments.has(name)) out.compartments.set(name, this.compartments.get(name)!);
        }
        const strata = new Set(expr.path.map((c) => stratumOf(out, c)).filter(Boolean));
        if (strata.size > 1) {
          this.note(
            "reroute",
            `rerouted return traverses strata ${[...strata].sort().join(", ")}; the substituted ` +
            `path carries the delay and bandwidth of the higher stratum`,
            span,
          );
        }
        return out;
      }
    }
  }
}

export function check(prog: Program): CheckResult {
  return new Checker(prog).check();
}
