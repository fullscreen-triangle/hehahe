/**
 * Operational semantics.
 *
 *   E-Lesion   apply one pending ablation
 *   E-Observe  discharge one pending observable, incrementing the record
 *   E-Report   produce the result once both sets are exhausted
 *
 * Lesions precede observations, so an experiment observes the circuit it
 * declared. The committed record is monotone, so a repeated value in the
 * store is never a return to an earlier configuration.
 */

import type { CircuitExpr, ExperimentDecl, Observable, Program } from "./ast";
import { Backend, type Measurement, type MeasureCtx } from "./backend";
import {
  type Circuit, apertureReport, apertures, closureIndex,
  reroute, withNoise, withScaling, withoutElement, withoutReturn,
} from "./circuit";
import { type CheckResult } from "./checker";
import { check } from "./checker";
import { parse } from "./parser";

export interface ArmResult {
  name: string;
  circuit: Circuit;
  closure: "closed" | "open";
  apertures: string[];
  store: Map<string, Measurement>;
  record: number;
  provenance: string[];
}

export interface PhaseResult { name: string; arms: ArmResult[]; }

export interface ExperimentResult {
  name: string;
  phased: boolean;
  arms: ArmResult[];
  phases: PhaseResult[];
}

export interface RunResult {
  experiments: ExperimentResult[];
  checked: CheckResult;
  backend: Backend;
  elapsedMs: number;
  steps: number;
}

export const allArms = (x: ExperimentResult): ArmResult[] =>
  x.phased ? x.phases.flatMap((p) => p.arms) : x.arms;

export class Runtime {
  constructor(
    private prog: Program,
    private checked: CheckResult,
    private backend: Backend,
  ) {}

  private ctx(): MeasureCtx {
    return {
      eventTypes: this.checked.eventTypes,
      antagonists: this.checked.antagonists,
      circuits: this.checked.circuits,
      corpora: new Map(),
    };
  }

  private observeAll(c: Circuit, observables: Observable[], name: string, ctx: MeasureCtx): ArmResult {
    const aps = apertures(c).map(apertureReport);
    const arm: ArmResult = {
      name, circuit: c,
      closure: closureIndex(c),
      apertures: aps,
      store: new Map(),
      record: 0,
      provenance: [...c.provenance],
    };
    for (const o of observables) {
      const key = o.args.length ? `${o.name}(${o.args.join(",")})` : o.name;
      arm.store.set(key, this.backend.measure(c, o.name, o.args, { ...ctx, apertures: aps }));
      arm.record++; // monotone: strictly increases at each E-Observe
    }
    return arm;
  }

  runExperiment(x: ExperimentDecl): ExperimentResult {
    const ctx = this.ctx();
    const res: ExperimentResult = {
      name: x.name, phased: x.phases.length > 0, arms: [], phases: [],
    };
    const intact = this.evalExpr(x.intact);
    if (!intact) return res;

    if (!res.phased) {
      res.arms.push(this.observeAll(intact, x.observables, "intact", ctx));
      for (const les of x.lesions) {
        const c = this.evalExpr(les.expr);
        if (c) res.arms.push(this.observeAll(c, x.observables, les.name, ctx));
      }
      return res;
    }

    const byName = new Map<string, Circuit>();
    for (const ph of x.phases) {
      const pr: PhaseResult = { name: ph.name, arms: [] };
      let base = intact;
      if (ph.fromPhase && byName.has(ph.fromPhase)) base = byName.get(ph.fromPhase)!;

      if (!ph.lesions.length) {
        pr.arms.push(this.observeAll(base, ph.observables, "intact", ctx));
        byName.set(ph.name, base);
      } else {
        let last = base;
        for (const les of ph.lesions) {
          const c = this.evalExpr(les.expr);
          if (!c) continue;
          pr.arms.push(this.observeAll(c, ph.observables, les.name, ctx));
          last = c;
        }
        byName.set(ph.name, last);
      }
      res.phases.push(pr);
    }
    return res;
  }

  private evalExpr(expr: CircuitExpr): Circuit | null {
    // The checker already validated every expression; re-evaluate for the
    // concrete circuit without emitting duplicate diagnostics.
    return evalCircuitExpr(expr, this.checked);
  }

  run(): RunResult {
    const t0 = performance.now();
    const experiments = this.prog.experiments.map((x) => this.runExperiment(x));
    const steps = experiments.reduce(
      (n, x) => n + allArms(x).reduce((m, a) => m + a.record + 1, 0),
      0,
    );
    return {
      experiments,
      checked: this.checked,
      backend: this.backend,
      elapsedMs: performance.now() - t0,
      steps,
    };
  }
}

/** Pure evaluation of a circuit expression against already-checked circuits. */
export function evalCircuitExpr(expr: CircuitExpr, checked: CheckResult): Circuit | null {
  if (expr.op === "ref") return checked.circuits.get(expr.name) ?? null;
  const base = evalCircuitExpr(expr.base, checked);
  if (!base) return null;

  switch (expr.op) {
    case "withoutElement": return withoutElement(base, expr.element);
    case "withoutReturn": return withoutReturn(base, expr.from);
    case "withScaling":
      try { return withScaling(base, expr.element, expr.factor); } catch { return base; }
    case "withNoise": return withNoise(base, expr.s1, expr.s2, expr.amplitude);
    case "reroute": {
      const out = reroute(base, expr.from, expr.path);
      for (const name of expr.path) {
        if (!out.compartments.has(name)) {
          for (const c of checked.circuits.values()) {
            const comp = c.compartments.get(name);
            if (comp) { out.compartments.set(name, comp); break; }
          }
        }
      }
      return out;
    }
    default: return base;
  }
}

export interface CompileResult {
  ok: boolean;
  program?: Program;
  checked?: CheckResult;
  parseError?: string;
  parseLine?: number;
}

export function compile(src: string): CompileResult {
  try {
    const program = parse(src);
    const checked = check(program);
    return { ok: checked.ok, program, checked };
  } catch (e: any) {
    const m = /line (\d+)/.exec(e?.message ?? "");
    return { ok: false, parseError: e?.message ?? String(e), parseLine: m ? +m[1] : undefined };
  }
}

export function runSource(src: string, backend?: Backend): RunResult | CompileResult {
  const c = compile(src);
  if (!c.ok || !c.program || !c.checked) return c;
  return new Runtime(c.program, c.checked, backend ?? new Backend()).run();
}
