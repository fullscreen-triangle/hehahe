/** Abstract syntax for Vitruvius, with source spans for editor markers. */

import type { Stratum } from "./lexer";

export interface Span {
  line: number;
  col: number;
  start: number;
  end: number;
}

export interface Quantity {
  value: number;
  unit: string;
}

const SI_SCALE: Record<string, number> = {
  s: 1, ms: 1e-3,
  F: 1, mF: 1e-3, uF: 1e-6, nF: 1e-9, pF: 1e-12,
  Hz: 1, N: 1, m: 1, mm: 1e-3, W: 1, C: 1,
};

const DIMENSION: Record<string, string> = {
  s: "time", ms: "time",
  F: "capacitance", mF: "capacitance", uF: "capacitance",
  nF: "capacitance", pF: "capacitance",
  Hz: "frequency", N: "force", m: "length", mm: "length",
  W: "power", C: "charge",
};

export const si = (q: Quantity) => q.value * (SI_SCALE[q.unit] ?? 1);
export const dimension = (q: Quantity) => DIMENSION[q.unit] ?? "dimensionless";

export interface CompartmentDecl {
  kind: "compartment";
  name: string;
  capacitance: Quantity;
  stratum: Stratum;
  span: Span;
}

export interface ElementDecl {
  name: string;
  src: string;
  dst: string;
  delay?: Quantity;
  gain: number;
  span: Span;
}

export interface FloorSpec {
  literal?: Quantity;
  derivedCall?: string;
  derivedArg?: string;
}

export interface CircuitDecl {
  kind: "circuit";
  name: string;
  floor: FloorSpec;
  outbound: string[];
  ret: string[];
  elements: ElementDecl[];
  span: Span;
}

export interface TemplateDecl {
  kind: "template";
  name: string;
  params: string[];
  floor: FloorSpec;
  outbound: string[];
  ret: string[];
  elements: ElementDecl[];
  span: Span;
}

export interface InstanceDecl {
  kind: "instance";
  name: string;
  template: string;
  args: (string | Quantity)[];
  span: Span;
}

export interface EventTypeDecl {
  kind: "eventType";
  name: string;
  ctor: string;
  args: string[];
  span: Span;
}

export interface AntagonistDecl {
  kind: "antagonist";
  name: string;
  agonist: string;
  antagonist: string;
  shared: string[];
  span: Span;
}

// ── circuit expressions ─────────────────────────────────────────────

export type CircuitExpr =
  | { op: "ref"; name: string; span: Span }
  | { op: "withoutElement"; base: CircuitExpr; element: string; span: Span }
  | { op: "withoutReturn"; base: CircuitExpr; from: string; span: Span }
  | { op: "withScaling"; base: CircuitExpr; element: string; factor: number; span: Span }
  | { op: "withNoise"; base: CircuitExpr; s1: Stratum; s2: Stratum; amplitude: number; span: Span }
  | { op: "reroute"; base: CircuitExpr; from: string; path: string[]; span: Span };

export interface Observable {
  name: string;
  args: string[];
  span: Span;
}

export interface LesionDecl {
  name: string;
  expr: CircuitExpr;
  span: Span;
}

export interface PhaseDecl {
  name: string;
  lesions: LesionDecl[];
  observables: Observable[];
  fromPhase?: string;
  span: Span;
}

export interface ExperimentDecl {
  kind: "experiment";
  name: string;
  intact: CircuitExpr;
  lesions: LesionDecl[];
  observables: Observable[];
  phases: PhaseDecl[];
  span: Span;
}

export interface Program {
  module?: string;
  imports: string[];
  compartments: CompartmentDecl[];
  circuits: CircuitDecl[];
  templates: TemplateDecl[];
  instances: InstanceDecl[];
  eventTypes: EventTypeDecl[];
  antagonists: AntagonistDecl[];
  experiments: ExperimentDecl[];
}

export const emptyProgram = (): Program => ({
  imports: [],
  compartments: [],
  circuits: [],
  templates: [],
  instances: [],
  eventTypes: [],
  antagonists: [],
  experiments: [],
});
