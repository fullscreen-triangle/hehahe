/**
 * Reference backend, ported from the Python implementation.
 *
 * Obligations:
 *   (B1) Totality        -- defined for every well-typed circuit and
 *                           observable, including open ones. An open circuit
 *                           yields a divergence time, not an exception.
 *   (B2) Floor agreement -- reports the floor it used.
 *   (B3) Stratum honesty -- reports the band each observable came from.
 *   (B4) Determinism     -- same circuit, observable, seed -> same value.
 *
 * A closed loop is held in bounded oscillation by its own return; an open
 * loop has no return term and diverges. That contrast is structural: the
 * return term is present exactly when the closure index is `closed`.
 */

import {
  type Circuit, closureIndex, conductance, floorOf, loopDelay,
  separationCost, stratumOf,
} from "./circuit";
import { OBSERVABLES, STRATUM_BANDS } from "./observables";

/** Deterministic PRNG so (B4) holds without a global RNG. */
function mulberry32(seed: number) {
  let a = seed >>> 0;
  return () => {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function gaussian(rand: () => number) {
  let u = 0, v = 0;
  while (u === 0) u = rand();
  while (v === 0) v = rand();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

/** Stable string digest: hash() is not portable across runtimes. */
function digest(s: string): number {
  let h = 2166136261 >>> 0;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619) >>> 0;
  }
  return h >>> 0;
}

export interface BackendReport {
  floorUsed: number;
  band: [number, number] | null;
  seed: number;
  nSamples: number;
  dt: number;
}

export interface Measurement {
  value: number | string | string[] | null;
  unit: string;
  report: BackendReport;
  note?: string;
  undefinedValue?: boolean;
}

export interface Trace {
  dt: number;
  /** columns: reflex, spinal, supraspinal */
  x: Float64Array[];
  n: number;
}

const TAU: Record<string, number> = { reflex: 0.05, spinal: 0.5, supraspinal: 2.0 };
const COL: Record<string, number> = { reflex: 0, spinal: 1, supraspinal: 2 };

export class Backend {
  private cache = new Map<string, Trace>();

  constructor(
    public dt = 2e-3,
    public duration = 30.0,
    public seed = 0,
  ) {}

  private key(c: Circuit) {
    return [
      c.name,
      [...c.elements.keys()].sort().join(","),
      c.provenance.join(";"),
      c.noiseEdges.map((n) => `${n.s1}-${n.s2}-${n.amplitude}`).join(","),
      this.seed, this.dt, this.duration,
    ].join("|");
  }

  simulate(c: Circuit): Trace {
    const k = this.key(c);
    const hit = this.cache.get(k);
    if (hit) return hit;

    // (B4): per-circuit offset from a stable digest, so two circuits in one
    // experiment get independent drive but the same run repeats exactly.
    const rand = mulberry32((this.seed * 1000003 + digest(c.name)) >>> 0);

    const n = Math.floor(this.duration / this.dt);
    const closed = closureIndex(c) === "closed";
    const lag = Math.max(Math.floor(Math.max(loopDelay(c), this.dt) / this.dt), 1);

    // Loop gain is the product around the WHOLE circulation: a lesion of a
    // descending element must change the dynamics, not be silent.
    let loopGain = 1.0;
    for (const path of [c.outbound, c.ret]) {
      for (let i = 0; i + 1 < path.length; i++) {
        for (const e of c.elements.values()) {
          if (e.src === path[i] && e.dst === path[i + 1]) { loopGain *= e.gain; break; }
        }
      }
    }

    const present = new Set<string>();
    for (const name of c.compartments.keys()) {
      const s = stratumOf(c, name);
      if (s) present.add(s);
    }
    if (!present.size) present.add("reflex");

    const x = [new Float64Array(n), new Float64Array(n), new Float64Array(n)];
    const cross = c.noiseEdges.map((e) => ({
      a: COL[e.s1] ?? 0, b: COL[e.s2] ?? 0, amp: e.amplitude,
    }));

    for (let i = 1; i < n; i++) {
      for (const sname of present) {
        const j = COL[sname];
        const t = TAU[sname];
        const w = gaussian(rand) * Math.sqrt(this.dt / t);

        let dx: number;
        if (closed) {
          const ret = i >= lag ? x[j][i - lag] : 0;
          dx = -x[j][i - 1] / t - (loopGain * ret) / t * 0.35 + w / t;
        } else {
          dx = (1.0 / t) * 0.6 + w / t;
        }
        x[j][i] = x[j][i - 1] + dx * this.dt;
      }

      for (const { a, b, amp } of cross) {
        const bleed = (amp * (x[a][i] - x[b][i]) * this.dt) / TAU.spinal;
        x[b][i] += bleed;
        x[a][i] -= bleed;
      }

      const mag = Math.max(Math.abs(x[0][i]), Math.abs(x[1][i]), Math.abs(x[2][i]));
      if (mag > 50) {
        const sgn = [Math.sign(x[0][i]) * 50, Math.sign(x[1][i]) * 50, Math.sign(x[2][i]) * 50];
        for (let q = i; q < n; q++) { x[0][q] = sgn[0]; x[1][q] = sgn[1]; x[2][q] = sgn[2]; }
        break;
      }
    }

    const tr: Trace = { dt: this.dt, x, n };
    this.cache.set(k, tr);
    return tr;
  }

  sum(c: Circuit): Float64Array {
    const tr = this.simulate(c);
    const out = new Float64Array(tr.n);
    for (let i = 0; i < tr.n; i++) out[i] = tr.x[0][i] + tr.x[1][i] + tr.x[2][i];
    return out;
  }

  divergenceTime(c: Circuit): number {
    if (closureIndex(c) === "closed") return NaN;
    const tr = this.simulate(c);
    for (let i = 0; i < tr.n; i++) {
      const m = Math.max(Math.abs(tr.x[0][i]), Math.abs(tr.x[1][i]), Math.abs(tr.x[2][i]));
      if (m > 45) return i * this.dt;
    }
    return NaN;
  }

  /** Periodogram by naive DFT over a log-spaced frequency grid. */
  psd(c: Circuit, nFreq = 120): { f: number[]; p: number[] } {
    const s = this.sum(c);
    const N = Math.min(s.length, 8192);
    const mean = (() => { let m = 0; for (let i = 0; i < N; i++) m += s[i]; return m / N; })();

    const f: number[] = [];
    const p: number[] = [];
    const fmin = 0.05, fmax = 5.0;
    for (let k = 0; k < nFreq; k++) {
      const fr = fmin * Math.pow(fmax / fmin, k / (nFreq - 1));
      const w = 2 * Math.PI * fr * this.dt;
      let re = 0, im = 0;
      for (let i = 0; i < N; i++) {
        const v = (s[i] - mean) * (0.5 - 0.5 * Math.cos((2 * Math.PI * i) / (N - 1)));
        re += v * Math.cos(w * i);
        im += v * Math.sin(w * i);
      }
      f.push(fr);
      p.push((re * re + im * im) / N);
    }
    return { f, p };
  }

  bandPower(c: Circuit, stratum: string): number {
    const band = STRATUM_BANDS[stratum];
    if (!band) return NaN;
    const { f, p } = this.psd(c);
    let total = 0, inBand = 0;
    for (let i = 1; i < f.length; i++) {
      const df = f[i] - f[i - 1];
      const seg = ((p[i] + p[i - 1]) / 2) * df;
      total += seg;
      if (f[i] >= band[0] && f[i] <= band[1]) inBand += seg;
    }
    return total > 0 ? inBand / total : NaN;
  }

  couplingIndex(c: Circuit): number {
    const tr = this.simulate(c);
    const slow = tr.x[2], fast = tr.x[0];
    let ms = 0, me = 0;
    for (let i = 0; i < tr.n; i++) { ms += slow[i]; me += Math.abs(fast[i]); }
    ms /= tr.n; me /= tr.n;
    let num = 0, da = 0, db = 0;
    for (let i = 0; i < tr.n; i++) {
      const a = slow[i] - ms;
      const b = Math.abs(fast[i]) - me;
      num += a * b; da += a * a; db += b * b;
    }
    const den = Math.sqrt(da * db);
    return den > 0 ? Math.abs(num / den) : NaN;
  }

  /**
   * Force from the OUTBOUND phase alone. An open circulation diverges in
   * state, but its diverging state is not muscle force -- reading force off
   * the trace would report a severed loop as stronger, inverting the claim
   * the nerve-block experiment tests.
   */
  force(c: Circuit, peak = false): { value: number; note: string } {
    let gain = 1.0;
    for (let i = 0; i + 1 < c.outbound.length; i++) {
      let hop: { gain: number } | null = null;
      for (const e of c.elements.values()) {
        if (e.src === c.outbound[i] && e.dst === c.outbound[i + 1]) { hop = e; break; }
      }
      if (!hop) return { value: 0, note: "outbound phase severed: no force is produced" };
      gain *= hop.gain;
    }
    const terminal = c.outbound[c.outbound.length - 1];
    const cap = c.compartments.get(terminal)?.capacitance ?? 1.41e-4;
    const fMax = 1200 * Math.sqrt(cap / 1.41e-4);
    let v = fMax * gain;
    if (!peak) v *= 0.35;
    const note = closureIndex(c) !== "closed"
      ? "outbound intact: contractile capacity preserved despite open loop"
      : "";
    return { value: v, note };
  }

  measure(c: Circuit, name: string, args: string[], ctx: MeasureCtx = {}): Measurement {
    const spec = OBSERVABLES.get(name)!;
    const band = name === "band_power" && args[0] ? STRATUM_BANDS[args[0]] ?? null : null;
    const report: BackendReport = {
      floorUsed: floorOf(c),
      band,
      seed: this.seed,
      nSamples: Math.floor(this.duration / this.dt),
      dt: this.dt,
    };
    const closed = closureIndex(c) === "closed";
    const M = (value: Measurement["value"], unit: string, note = ""): Measurement => ({
      value,
      unit,
      report,
      note: note || undefined,
      undefinedValue: typeof value === "number" && !Number.isFinite(value),
    });

    switch (name) {
      case "closure_index":
        return M(closureIndex(c), "categorical");
      case "aperture_list": {
        const list = ctx.apertures ?? [];
        return M(list, "list", `${list.length} aperture(s)`);
      }
      case "resting_cut_weight": {
        const v = c.floorSpec?.derivedArg;
        return M(v && c.compartments.has(v) ? separationCost(c, v) : floorOf(c), "conductance");
      }
      case "floor_value":
        return M(floorOf(c), "conductance");
      case "loop_latency":
        return M(loopDelay(c), "s");
      case "divergence_time": {
        const v = this.divergenceTime(c);
        return M(v, "s", Number.isFinite(v) ? "" : "circuit is closed; no divergence");
      }
      case "tonic_rate": {
        if (!closed) return M(NaN, "Hz", "open circuit sustains no tonic rhythm");
        const d = loopDelay(c);
        return M(d > 0 ? 1 / (2 * d) : NaN, "Hz");
      }
      case "oscillation_amplitude":
      case "cop_rms": {
        const s = this.sum(c);
        let acc = 0;
        for (let i = 0; i < s.length; i++) acc += s[i] * s[i];
        const v = Math.sqrt(acc / s.length);
        return M(v, name === "cop_rms" ? "mm" : "a.u.",
          closed ? "" : "open circuit: value reflects divergence");
      }
      case "oscillation_frequency": {
        const { f, p } = this.psd(c);
        let bi = 1;
        for (let i = 2; i < p.length; i++) if (p[i] > p[bi]) bi = i;
        return M(f[bi], "Hz");
      }
      case "force_amplitude":
      case "force_output": {
        const { value, note } = this.force(c, name === "force_amplitude");
        return M(value, "N", note);
      }
      case "band_power":
        return M(this.bandPower(c, args[0]), "fraction");
      case "coupling_index":
        return M(this.couplingIndex(c), "dimensionless");
      case "kappa":
      case "type_separation":
      case "composition_residual":
        return measureEstimation(this, c, name, args, ctx, report);
      case "cocontraction_ratio":
      case "joint_stiffness":
        return measureAntagonist(this, c, name, args, ctx, report);
      default:
        // (B1) demands totality: report the gap rather than throwing.
        return M(NaN, spec?.unit ?? "", `backend has no procedure for '${name}'`);
    }
  }
}

export interface MeasureCtx {
  eventTypes?: Map<string, string[]>;
  antagonists?: Map<string, { agonist: string; antagonist: string; shared: string[] }>;
  circuits?: Map<string, Circuit>;
  apertures?: string[];
  corpora?: Map<string, EventSample[]>;
}

// ── estimation ──────────────────────────────────────────────────────

export interface EventSample { etype: string; sBefore: number; sAfter: number; }

export const kappaOf = (b: number, a: number, floor: number) =>
  b - floor <= 0 ? NaN : (b - a) / (b - floor);

export function corpusFromCircuit(
  backend: Backend, c: Circuit, eventTypes: Map<string, string[]>, n = 24,
): EventSample[] {
  const rand = mulberry32((backend.seed * 7919 + digest(c.name + c.provenance.join(""))) >>> 0);
  const s = backend.sum(c);
  const floor = floorOf(c);

  const localGain = (comps: string[]) => {
    let g = 1, hits = 0;
    for (const e of c.elements.values()) {
      if (comps.includes(e.src) || comps.includes(e.dst)) { g *= e.gain; hits++; }
    }
    return hits ? Math.pow(g, 1 / hits) : 1;
  };
  const noise = c.noiseEdges.reduce((m, e) => Math.max(m, e.amplitude), 0);

  const out: EventSample[] = [];
  const names = [...eventTypes.keys()].sort();
  const win = Math.max(Math.floor(s.length / (n * Math.max(names.length, 1) + 1)), 2);

  names.forEach((tname, ti) => {
    const comps = eventTypes.get(tname)!;
    const depth: Record<string, number> = { reflex: 0.55, spinal: 0.35, supraspinal: 0.18 };
    const strata = comps.map((x) => stratumOf(c, x)).filter(Boolean) as string[];
    let base = strata.length
      ? strata.reduce((m, x) => m + (depth[x] ?? 0.3), 0) / strata.length
      : 0.3;
    base *= localGain(comps);
    const spread = 0.06 + 0.9 * noise;

    for (let j = 0; j < n; j++) {
      let start = (ti * n + j) * win;
      if (start + win >= s.length) start = Math.floor(rand() * Math.max(s.length - win - 1, 1));
      const sB = Math.abs(s[start]) + floor * 2.5;
      const k = Math.min(Math.max(base + gaussian(rand) * spread, 0.01), 0.95);
      out.push({ etype: tname, sBefore: sB, sAfter: floor + (sB - floor) * (1 - k) });
    }
  });
  return out;
}

export function typeAveraged(corpus: EventSample[], floor: number): Map<string, number> {
  const acc = new Map<string, number[]>();
  for (const e of corpus) {
    const k = kappaOf(e.sBefore, e.sAfter, floor);
    if (Number.isFinite(k)) {
      if (!acc.has(e.etype)) acc.set(e.etype, []);
      acc.get(e.etype)!.push(k);
    }
  }
  const out = new Map<string, number>();
  for (const [t, v] of acc) out.set(t, v.reduce((a, b) => a + b, 0) / v.length);
  return out;
}

const variance = (v: number[]) => {
  if (!v.length) return 0;
  const m = v.reduce((a, b) => a + b, 0) / v.length;
  return v.reduce((a, b) => a + (b - m) * (b - m), 0) / v.length;
};

export function typeSeparation(corpus: EventSample[], floor: number): number {
  const groups = new Map<string, number[]>();
  for (const e of corpus) {
    const k = kappaOf(e.sBefore, e.sAfter, floor);
    if (Number.isFinite(k)) {
      if (!groups.has(e.etype)) groups.set(e.etype, []);
      groups.get(e.etype)!.push(k);
    }
  }
  if (groups.size < 2) return NaN;
  const means = [...groups.values()].map((v) => v.reduce((a, b) => a + b, 0) / v.length);
  const vb = variance(means);
  const within = [...groups.values()].filter((v) => v.length >= 2).map(variance);
  const vw = within.length ? within.reduce((a, b) => a + b, 0) / within.length : 0;
  return vb + vw > 0 ? vb / (vb + vw) : NaN;
}

function measureEstimation(
  backend: Backend, c: Circuit, name: string, args: string[],
  ctx: MeasureCtx, report: BackendReport,
): Measurement {
  const etypes = ctx.eventTypes;
  const M = (value: number, unit: string, note = ""): Measurement => ({
    value, unit, report, note: note || undefined,
    undefinedValue: !Number.isFinite(value),
  });
  if (!etypes || !etypes.size) return M(NaN, "fraction", "no event types declared");

  // Cache per arm, not per experiment: a lesion must be able to move it.
  const key = `${c.name}|${c.provenance.join(";")}`;
  if (!ctx.corpora) ctx.corpora = new Map();
  let corpus = ctx.corpora.get(key);
  if (!corpus) { corpus = corpusFromCircuit(backend, c, etypes); ctx.corpora.set(key, corpus); }

  const floor = floorOf(c);

  if (name === "type_separation") return M(typeSeparation(corpus, floor), "fraction");

  if (name === "kappa") {
    const means = typeAveraged(corpus, floor);
    const et = args[0];
    const n = corpus.filter((e) => e.etype === et).length;
    if (!means.has(et)) return M(NaN, "fraction", `no instances of type '${et}'`);
    return M(means.get(et)!, "fraction", `type-averaged over ${n} instances`);
  }

  if (name === "composition_residual") {
    const means = typeAveraged(corpus, floor);
    const byType = new Map<string, EventSample[]>();
    for (const e of corpus) {
      if (!byType.has(e.etype)) byType.set(e.etype, []);
      byType.get(e.etype)!.push(e);
    }
    const res: number[] = [];
    for (const v of byType.values()) {
      if (v.length < 3) continue;
      const casc = v.slice(0, 3);
      let prod = 1;
      for (const e of casc) prod *= 1 - (means.get(e.etype) ?? 0);
      const pred = 1 - prod;
      const meas = (casc[0].sBefore - casc[casc.length - 1].sAfter) / (casc[0].sBefore - floor);
      if (Number.isFinite(pred) && Number.isFinite(meas)) res.push(Math.abs(pred - meas));
    }
    return M(
      res.length ? res.reduce((a, b) => a + b, 0) / res.length : NaN,
      "fraction",
      "typed estimator; non-degenerate by construction",
    );
  }
  return M(NaN, "fraction");
}

// ── antagonist pairs ────────────────────────────────────────────────

export function coupledTraces(
  backend: Backend, ago: Circuit, ant: Circuit, shared: string[],
): [Float64Array, Float64Array] {
  const ta = backend.simulate(ago);
  const tb = backend.simulate(ant);
  const n = Math.min(ta.n, tb.n);
  const a = ta.x[0].slice(0, n);
  const b = tb.x[0].slice(0, n);

  // Only vertices lying on BOTH circulations' declared paths couple them.
  const onA = new Set([...ago.outbound, ...ago.ret]);
  const onB = new Set([...ant.outbound, ...ant.ret]);
  const junctions = shared.filter((s) => onA.has(s) && onB.has(s));
  const frac = junctions.length / Math.max(shared.length, 1);

  const noise = Math.max(
    ...ago.noiseEdges.map((e) => e.amplitude),
    ...ant.noiseEdges.map((e) => e.amplitude),
    0,
  );
  const inhibition = Math.max(0, 1 - 2 * noise);

  // The shared joint couples in phase; reciprocal inhibition through the
  // shared pool pushes out of phase. Degrade inhibition and the mechanical
  // coupling is left unopposed, so the pair co-activates.
  const mech = 0.9 * frac;
  const recip = 1.6 * frac * inhibition;
  const oa = new Float64Array(n), ob = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    oa[i] = a[i] + mech * b[i] - recip * b[i];
    ob[i] = b[i] + mech * a[i] - recip * a[i];
  }
  return [oa, ob];
}

function quantile(v: Float64Array, q: number) {
  const s = Array.from(v).sort((x, y) => x - y);
  return s[Math.min(s.length - 1, Math.floor(q * s.length))];
}

export function cocontractionRatio(
  backend: Backend, ago: Circuit, ant: Circuit, shared: string[],
): number {
  const [xa, xb] = coupledTraces(backend, ago, ant, shared);
  const a = xa.map(Math.abs), b = xb.map(Math.abs);
  // Upper quartile: a median split calls each signal active half the time
  // by definition, which pins the ratio near 1 regardless of the dynamics.
  const ta = quantile(a, 0.75), tb = quantile(b, 0.75);
  if (!(ta > 0) || !(tb > 0)) return NaN;
  let both = 0, either = 0;
  for (let i = 0; i < a.length; i++) {
    const A = a[i] > ta, B = b[i] > tb;
    if (A && B) both++;
    if (A || B) either++;
  }
  return either ? both / either : NaN;
}

export function jointStiffness(
  backend: Backend, ago: Circuit, ant: Circuit, shared: string[],
): number {
  const [xa, xb] = coupledTraces(backend, ago, ant, shared);
  const ratio = cocontractionRatio(backend, ago, ant, shared);
  if (!Number.isFinite(ratio)) return NaN;
  const rms = (v: Float64Array) => {
    let s = 0; for (let i = 0; i < v.length; i++) s += v[i] * v[i];
    return Math.sqrt(s / v.length);
  };
  return 120 + 900 * ratio * (rms(xa) + rms(xb));
}

function measureAntagonist(
  backend: Backend, circuit: Circuit, name: string, args: string[],
  ctx: MeasureCtx, report: BackendReport,
): Measurement {
  const M = (value: number, unit: string, note = ""): Measurement => ({
    value, unit, report, note: note || undefined,
    undefinedValue: !Number.isFinite(value),
  });
  const pair = ctx.antagonists?.get(args[0]);
  if (!pair) return M(NaN, "dimensionless", `no antagonist pair '${args[0]}'`);

  let ago = ctx.circuits?.get(pair.agonist);
  let ant = ctx.circuits?.get(pair.antagonist);
  if (!ago || !ant) return M(NaN, "dimensionless", "pair references unknown circuit");

  // The arm under observation may be a lesioned form of one member.
  let lesioned = "";
  if (circuit.name === pair.agonist) { ago = circuit; lesioned = circuit.provenance.length ? " (agonist lesioned)" : ""; }
  else if (circuit.name === pair.antagonist) { ant = circuit; lesioned = circuit.provenance.length ? " (antagonist lesioned)" : ""; }

  if (name === "cocontraction_ratio") {
    return M(cocontractionRatio(backend, ago, ant, pair.shared), "fraction",
      `shared: ${pair.shared.join(", ")}${lesioned}`);
  }
  return M(jointStiffness(backend, ago, ant, pair.shared), "N/m",
    `emergent from coupled limit cycles${lesioned}`);
}
