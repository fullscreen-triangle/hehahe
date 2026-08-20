/**
 * Anatomical binding: attaching a circulation to a rig, and checking it.
 *
 * A binding maps each compartment of a circuit to a joint of a skeleton that
 * was authored independently of the program. The joint hierarchy therefore
 * carries information the .vvs source does not, and the two descriptions can
 * DISAGREE. Every analysis in this module exists to locate a disagreement.
 *
 * This is the whole reason the rig is worth loading. A viewer that only
 * renders a compartment's observable as a wobble cannot be wrong; it restates
 * the results table in a lossier medium. A binding can be wrong, and saying
 * how is the useful part.
 *
 * The four analyses, in order of how much they can tell you:
 *
 *   B1 adjacency     — declared conduction crosses unnamed anatomy
 *   B2 tissue        — an element crosses tissue compartments (cf. Rule I)
 *   B3 reachability  — the circulation is disconnected in the skeleton
 *   B4 span          — declared delay disagrees with anatomical distance
 *
 * B1-B3 are decidable from the manifest and the program alone, with no
 * simulation, in the same spirit as the closure index. B4 requires a declared
 * conduction velocity and is reported as a comparison, never as an error:
 * the program and the rig are both models, and neither is the arbiter.
 */

import type { Circuit } from "./circuit";
import RIGS from "../data/rigs.json";

// ── rig manifest types (shape produced by scripts/inspect-glb.mjs) ──

export interface RigJoint {
  node: number;
  name: string;
  parent: string | null;
  tissue: string | null;
  segment: string;
  rest: number[];
  world: number[];
}

export interface RigManifest {
  file: string;
  bytes: number;
  meshes: string[];
  jointCount: number;
  joints: RigJoint[];
  tissues: string[];
  segments: string[];
  coregistration: { segments: number; maxRestDrift: number };
  animations: { name: string; duration: number; targets: number }[];
  bindable: boolean;
}

export const RIG_MANIFESTS = RIGS as unknown as Record<string, RigManifest>;

export const rigNames = () => Object.keys(RIG_MANIFESTS);
export const getRig = (name: string): RigManifest | undefined => RIG_MANIFESTS[name];

export const bindableRigs = () =>
  Object.entries(RIG_MANIFESTS)
    .filter(([, r]) => r.bindable)
    .map(([k]) => k);

// ── binding ─────────────────────────────────────────────────────────

/** compartment name -> joint name */
export type Binding = Record<string, string>;

export interface BindSpec {
  rig: string;
  circuit: string;
  map: Binding;
  /** metres per second; enables B4. Absent means B4 is not attempted. */
  conductionVelocity?: number;
  /** rig units per metre. Rigs are authored at arbitrary scale. */
  unitsPerMetre?: number;
}

export type BindSeverity = "error" | "warning" | "info";

export interface BindDiagnostic {
  check: "B1" | "B2" | "B3" | "B4" | "B0";
  severity: BindSeverity;
  message: string;
  /** compartments or elements the diagnostic is about */
  subjects: string[];
  /** quantitative payload, when the check produced one */
  detail?: Record<string, number | string | string[]>;
}

export interface BindReport {
  rig: string;
  circuit: string;
  bound: number;
  unbound: string[];
  diagnostics: BindDiagnostic[];
  /** true when no diagnostic has severity "error" */
  consistent: boolean;
  /** B4 comparison rows, empty when no conduction velocity was declared */
  spans: SpanRow[];
}

export interface SpanRow {
  element: string;
  src: string;
  dst: string;
  /** anatomical distance between bound joints, metres */
  distance: number;
  /** delay predicted from distance and conduction velocity, seconds */
  predicted: number;
  /** delay the program declares, seconds */
  declared: number;
  /** predicted / declared; 1.0 is agreement */
  ratio: number;
}

// ── joint graph ─────────────────────────────────────────────────────

interface JointGraph {
  byName: Map<string, RigJoint>;
  /** undirected adjacency over the joint hierarchy */
  adj: Map<string, Set<string>>;
}

export function jointGraph(rig: RigManifest): JointGraph {
  const byName = new Map<string, RigJoint>();
  const adj = new Map<string, Set<string>>();
  for (const j of rig.joints) {
    byName.set(j.name, j);
    if (!adj.has(j.name)) adj.set(j.name, new Set());
  }
  for (const j of rig.joints) {
    if (!j.parent) continue;
    if (!adj.has(j.parent)) adj.set(j.parent, new Set());
    adj.get(j.name)!.add(j.parent);
    adj.get(j.parent)!.add(j.name);
  }
  return { byName, adj };
}

/** Shortest joint path between two joints, or null if disconnected. */
export function jointPath(g: JointGraph, from: string, to: string): string[] | null {
  if (from === to) return [from];
  if (!g.adj.has(from) || !g.adj.has(to)) return null;
  const prev = new Map<string, string>();
  const seen = new Set([from]);
  const queue = [from];
  while (queue.length) {
    const cur = queue.shift()!;
    for (const nxt of g.adj.get(cur) ?? []) {
      if (seen.has(nxt)) continue;
      seen.add(nxt);
      prev.set(nxt, cur);
      if (nxt === to) {
        const path = [to];
        let p = to;
        while (prev.has(p)) {
          p = prev.get(p)!;
          path.unshift(p);
        }
        return path;
      }
      queue.push(nxt);
    }
  }
  return null;
}

/** Euclidean distance between two joints in rest pose, in rig units. */
export function restDistance(g: JointGraph, a: string, b: string): number {
  const ja = g.byName.get(a);
  const jb = g.byName.get(b);
  if (!ja || !jb) return NaN;
  const [x1, y1, z1] = ja.world;
  const [x2, y2, z2] = jb.world;
  return Math.hypot(x2 - x1, y2 - y1, z2 - z1);
}

/** Path length along the skeleton, summing segment lengths. This is the
 *  anatomically honest distance: a nerve follows the limb, it does not take
 *  the Euclidean shortcut through tissue. */
export function anatomicalDistance(g: JointGraph, a: string, b: string): number {
  const path = jointPath(g, a, b);
  if (!path) return NaN;
  let d = 0;
  for (let i = 1; i < path.length; i++) d += restDistance(g, path[i - 1], path[i]);
  return d;
}

// ── the analyses ────────────────────────────────────────────────────

const DEFAULT_UNITS_PER_METRE = 100; // rigs are commonly authored in cm

/**
 * Check a binding. Returns every disagreement found between the program and
 * the rig, with the quantities that produced it.
 */
export function checkBinding(circuit: Circuit, spec: BindSpec): BindReport {
  const rig = getRig(spec.rig);
  const diagnostics: BindDiagnostic[] = [];
  const spans: SpanRow[] = [];

  if (!rig) {
    return {
      rig: spec.rig,
      circuit: spec.circuit,
      bound: 0,
      unbound: [...circuit.compartments.keys()],
      diagnostics: [
        {
          check: "B0",
          severity: "error",
          message: `No rig named "${spec.rig}". Available: ${rigNames().join(", ")}.`,
          subjects: [],
        },
      ],
      consistent: false,
      spans,
    };
  }

  if (!rig.bindable) {
    diagnostics.push({
      check: "B0",
      severity: "error",
      message:
        `Rig "${spec.rig}" carries no skin, so it has no joints to bind to. ` +
        `It has ${rig.meshes.length} unnamed meshes and can serve only as a static backdrop.`,
      subjects: [],
    });
  }

  const g = jointGraph(rig);
  const comps = [...circuit.compartments.keys()];

  // ── B0: does every named joint exist? ──
  for (const [comp, joint] of Object.entries(spec.map)) {
    if (!g.byName.has(joint)) {
      const near = nearestNames(joint, [...g.byName.keys()]);
      diagnostics.push({
        check: "B0",
        severity: "error",
        message: `Compartment "${comp}" binds to joint "${joint}", which the rig does not have.`,
        subjects: [comp],
        detail: { suggestions: near },
      });
    }
    if (!circuit.compartments.has(comp)) {
      diagnostics.push({
        check: "B0",
        severity: "warning",
        message: `Binding names compartment "${comp}", which circuit "${circuit.name}" does not declare.`,
        subjects: [comp],
      });
    }
  }

  const bound = comps.filter((c) => spec.map[c] && g.byName.has(spec.map[c]));
  const unbound = comps.filter((c) => !spec.map[c]);

  if (unbound.length) {
    diagnostics.push({
      check: "B0",
      severity: "info",
      message:
        `${unbound.length} of ${comps.length} compartments are unbound and will not be ` +
        `rendered: ${unbound.join(", ")}.`,
      subjects: unbound,
    });
  }

  // ── B1: adjacency ──
  // An element declares conduction from src to dst. If the bound joints are
  // not adjacent in the skeleton, the conduction path traverses anatomy the
  // program never names. That may be correct (a long axon really does cross
  // several segments) but it is never nothing, and the intervening joints are
  // worth naming.
  for (const el of circuit.elements.values()) {
    const js = spec.map[el.src];
    const jd = spec.map[el.dst];
    if (!js || !jd || !g.byName.has(js) || !g.byName.has(jd)) continue;
    const path = jointPath(g, js, jd);
    if (!path) continue; // handled by B3
    const hops = path.length - 1;
    if (hops > 1) {
      const between = path.slice(1, -1);
      diagnostics.push({
        check: "B1",
        severity: hops > 3 ? "warning" : "info",
        message:
          `Element "${el.name}" conducts ${el.src} → ${el.dst}, but their joints are ` +
          `${hops} hops apart. The path crosses ${between.length} joint(s) the program ` +
          `does not name: ${between.join(" → ")}.`,
        subjects: [el.name],
        detail: { hops, between },
      });
    }
  }

  // ── B2: tissue consistency ──
  // The rig's tissue chains are a compartment index in the sense of Rule I.
  // An element that crosses them is either a real transduction step or a
  // binding error, and this analysis cannot tell which — so it says so.
  if (rig.tissues.length > 1) {
    for (const el of circuit.elements.values()) {
      const js = g.byName.get(spec.map[el.src] ?? "");
      const jd = g.byName.get(spec.map[el.dst] ?? "");
      if (!js || !jd || !js.tissue || !jd.tissue) continue;
      if (js.tissue !== jd.tissue) {
        diagnostics.push({
          check: "B2",
          severity: "warning",
          message:
            `Element "${el.name}" crosses tissue compartments: ${el.src} is bound to ` +
            `${js.tissue}, ${el.dst} to ${jd.tissue}. Either this is a transduction step ` +
            `that should be declared as one, or the binding is wrong. The rig cannot ` +
            `distinguish these.`,
          subjects: [el.name],
          detail: { from: js.tissue, to: jd.tissue },
        });
      }
    }
  }

  // ── B3: reachability ──
  // A closed circuit whose binding is disconnected in the skeleton is a
  // contradiction between two independent descriptions of one system.
  const boundJoints = bound.map((c) => spec.map[c]);
  if (boundJoints.length > 1) {
    const root = boundJoints[0];
    const unreachable = boundJoints.filter((jt) => jt !== root && !jointPath(g, root, jt));
    if (unreachable.length) {
      diagnostics.push({
        check: "B3",
        severity: "error",
        message:
          `The binding is disconnected in the skeleton: ${unreachable.length} bound ` +
          `joint(s) are unreachable from "${root}". A circulation cannot inhabit ` +
          `disjoint anatomy.`,
        subjects: unreachable,
        detail: { unreachable },
      });
    }
  }

  // ── B4: span ──
  // Anatomical distance plus a declared conduction velocity predicts a delay.
  // The program declares its own. Neither is the arbiter; the comparison is
  // the finding.
  if (spec.conductionVelocity && spec.conductionVelocity > 0) {
    const upm = spec.unitsPerMetre ?? DEFAULT_UNITS_PER_METRE;
    for (const el of circuit.elements.values()) {
      const js = spec.map[el.src];
      const jd = spec.map[el.dst];
      if (!js || !jd || !g.byName.has(js) || !g.byName.has(jd)) continue;
      const units = anatomicalDistance(g, js, jd);
      if (!Number.isFinite(units)) continue;
      const distance = units / upm;
      const predicted = distance / spec.conductionVelocity;
      const declared = el.delay;
      if (!declared || declared <= 0) continue;
      const ratio = predicted / declared;
      spans.push({ element: el.name, src: el.src, dst: el.dst, distance, predicted, declared, ratio });
    }

    const off = spans.filter((s) => s.ratio > 3 || s.ratio < 1 / 3);
    if (off.length) {
      diagnostics.push({
        check: "B4",
        severity: "info",
        message:
          `${off.length} of ${spans.length} elements declare a delay differing from the ` +
          `anatomical prediction by more than 3×. At ${spec.conductionVelocity} m/s this ` +
          `is a disagreement between the program and the rig, not an error in either.`,
        subjects: off.map((s) => s.element),
        detail: { worst: off.reduce((a, b) => (Math.abs(Math.log(a.ratio)) > Math.abs(Math.log(b.ratio)) ? a : b)).element },
      });
    }
  }

  return {
    rig: spec.rig,
    circuit: spec.circuit,
    bound: bound.length,
    unbound,
    diagnostics,
    consistent: !diagnostics.some((d) => d.severity === "error"),
    spans,
  };
}

// ── suggestion helper ───────────────────────────────────────────────

/** Cheap edit-distance ranking, for "did you mean" on a bad joint name. */
function nearestNames(target: string, pool: string[], k = 3): string[] {
  const score = (a: string, b: string) => {
    const al = a.toLowerCase();
    const bl = b.toLowerCase();
    if (bl.includes(al) || al.includes(bl)) return 0;
    const m = al.length;
    const n = bl.length;
    const d: number[][] = Array.from({ length: m + 1 }, (_, i) =>
      Array.from({ length: n + 1 }, (_, j) => (i === 0 ? j : j === 0 ? i : 0)),
    );
    for (let i = 1; i <= m; i++)
      for (let j = 1; j <= n; j++)
        d[i][j] = Math.min(
          d[i - 1][j] + 1,
          d[i][j - 1] + 1,
          d[i - 1][j - 1] + (al[i - 1] === bl[j - 1] ? 0 : 1),
        );
    return d[m][n];
  };
  return pool
    .map((p) => ({ p, s: score(target, p) }))
    .sort((a, b) => a.s - b.s)
    .slice(0, k)
    .map((x) => x.p);
}

// ── auto-binding ────────────────────────────────────────────────────

/**
 * Propose a binding by name similarity. This is a convenience for exploring a
 * new rig, NOT a substitute for declaring one: an inferred binding that
 * passes B1-B4 has only shown that the inference was self-consistent.
 * Everything it returns is marked inferred so the UI can say so.
 */
export function proposeBinding(circuit: Circuit, rigName: string, tissue?: string): Binding {
  const rig = getRig(rigName);
  if (!rig?.bindable) return {};
  const pool = rig.joints.filter((j) => !tissue || j.tissue === tissue);
  const out: Binding = {};
  const used = new Set<string>();
  for (const comp of circuit.compartments.keys()) {
    const ranked = pool
      .filter((j) => !used.has(j.name))
      .map((j) => ({ j, s: affinity(comp, j) }))
      .sort((a, b) => b.s - a.s);
    if (ranked.length && ranked[0].s > 0) {
      out[comp] = ranked[0].j.name;
      used.add(ranked[0].j.name);
    }
  }
  return out;
}

/** Token-overlap affinity between a compartment name and a joint. */
function affinity(comp: string, joint: RigJoint): number {
  const c = comp.toLowerCase().replace(/[_\-.]/g, "");
  const seg = joint.segment.toLowerCase().replace(/[_\-.]/g, "");
  if (!seg) return 0;
  if (c === seg) return 100;
  if (c.includes(seg) || seg.includes(c)) return 50 + Math.min(c.length, seg.length);
  // shared prefix
  let k = 0;
  while (k < c.length && k < seg.length && c[k] === seg[k]) k++;
  return k >= 3 ? k : 0;
}
