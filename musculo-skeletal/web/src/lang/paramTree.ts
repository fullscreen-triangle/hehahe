/**
 * Building the parameter tree for a subject and (optionally) a run.
 *
 * This is what the sunburst navigates. Every leaf carries its anatomical
 * region, so the reference figure at the centre becomes a heatmap of whatever
 * subtree the cursor is on, and a quantity that is genuinely not localised
 * (body mass, a whole-circuit latency) carries `region: null` so the figure
 * paints nothing rather than picking somewhere plausible.
 */

import { analyseSubject, massClosure, REFERENCE_SAMPLE, type Subject } from "./bsp";
import { CAPACITANCE, chargeFromPower } from "./posture";
import type { ParamNode } from "./parameters";
import type { ArmResult } from "./runtime";

/** Anthropometry and segment inertia, from the subject alone. */
export function anthropometryTree(subject: Subject): ParamNode {
  const segments = analyseSubject(subject);
  const ref = REFERENCE_SAMPLE.deLeva[subject.sex];

  const massNode: ParamNode = {
    name: "mass",
    description: "segment mass, one side for paired segments",
    unit: "kg",
    children: segments.map((s) => ({
      name: s.segment,
      value: s.massKg,
      unit: "kg",
      region: s.region,
      description: `${(s.mass * 100).toFixed(2)}% of body mass` + (s.paired ? ", per side" : ""),
      derivation: `${s.mass} x ${subject.massKg} kg`,
    })),
  };

  const lengthNode: ParamNode = {
    name: "length",
    description: "segment length",
    unit: "m",
    children: segments.map((s) => ({
      name: s.segment,
      value: Number.isFinite(s.lengthM) ? s.lengthM : undefined,
      unit: "m",
      region: s.region,
      description: `${s.endpoints[0]} to ${s.endpoints[1]}`,
      derivation:
        s.lengthSource === "measured" ? "measured on the subject"
        : s.lengthSource === "scaled" ? `sample mean scaled by stature ${subject.statureM}/${ref.statureM}`
        : s.lengthSource === "stature" ? "Winter Fig 4.1 stature fraction"
        : "no length source covers this segment",
    })),
  };

  const cmNode: ParamNode = {
    name: "centre of mass",
    description: "CM distance from the proximal endpoint",
    unit: "m",
    children: segments.map((s) => ({
      name: s.segment,
      value: Number.isFinite(s.cmFromProximalM) ? s.cmFromProximalM : undefined,
      unit: "m",
      region: s.region,
      description: `${(s.cmProximal * 100).toFixed(2)}% of segment length from ${s.endpoints[0]}`,
    })),
  };

  const inertiaNode: ParamNode = {
    name: "inertia",
    description: "moment of inertia about the segment CM",
    unit: "kg m2",
    children: segments.map((s) => ({
      name: s.segment,
      value: s.inertiaCmKgM2 ?? undefined,
      unit: "kg m2",
      region: s.region,
      description: s.inertiaCmKgM2 === null
        ? "not computable: no segment length"
        : `I = m (rg L)^2, rg = ${(s.rg.sagittal ?? s.rg.cm ?? NaN).toFixed(3)}`,
      derivation: s.inertiaProximalKgM2 !== null
        ? `about proximal end: ${s.inertiaProximalKgM2.toExponential(3)} kg m2`
        : undefined,
    })),
  };

  return {
    name: "anthropometry",
    description: `${subject.model}, ${subject.sex}, ${subject.massKg} kg, ${subject.statureM} m`,
    children: [
      {
        name: "whole body",
        children: [
          { name: "mass", value: subject.massKg, unit: "kg", region: null,
            description: "total body mass; not localised to any segment" },
          { name: "stature", value: subject.statureM, unit: "m", region: null },
          { name: "mass closure", value: massClosure(subject.model, subject.sex), unit: "fraction",
            region: null,
            description: "segment masses summed; should be 1",
            derivation: "a value far from 1 means segments were double-counted" },
        ],
      },
      massNode, lengthNode, cmNode, inertiaNode,
    ],
  };
}

/** Charge, from the subject's own segment masses rather than an assumed one. */
export function chargeTree(subject: Subject, powerByRegion: Record<string, number>): ParamNode {
  const entries = Object.entries(powerByRegion);
  return {
    name: "charge",
    description: "Q = sqrt(2CP), compartment-indexed",
    children: [
      {
        name: "capacitance",
        unit: "F",
        children: (Object.keys(CAPACITANCE) as (keyof typeof CAPACITANCE)[]).map((k) => ({
          name: k,
          value: CAPACITANCE[k],
          unit: "F",
          region: k === "brain" ? "brain" : k === "motor" ? "right-thigh" : null,
          description: k === "perception" ? "sensory-associative allocation, not localised" : undefined,
        })),
      },
      {
        name: "rate",
        unit: "C/s",
        children: entries.length
          ? entries.map(([region, P]) => ({
              name: region,
              value: chargeFromPower(P, "motor"),
              unit: "C/s",
              region,
              description: `from ${P.toExponential(3)} W at the motor capacitance`,
              derivation: `sqrt(2 x ${CAPACITANCE.motor} F x ${P.toExponential(3)} W)`,
            }))
          : [{ name: "no measured power", region: null, description: "run a record to populate" }],
      },
    ],
  };
}

/** Observables from a run, grouped by arm. */
export function resultsTree(arms: ArmResult[]): ParamNode {
  if (!arms.length) {
    return { name: "results", children: [{ name: "not run", region: null, description: "press Run" }] };
  }
  return {
    name: "results",
    description: `${arms.length} arms`,
    children: arms.map((a) => ({
      name: a.name,
      description: `closure ${a.closure}`,
      children: [...a.store.entries()].map(([key, m]) => ({
        name: key,
        value: typeof m.value === "number" ? m.value : undefined,
        unit: m.unit,
        // Observables are circuit-level, not segment-level: a loop latency
        // belongs to the whole circulation, not to one muscle. Claiming a
        // region here would be a guess.
        region: null,
        description: typeof m.value === "string" ? m.value : m.note,
      })),
    })),
  };
}

/** The whole tree. */
export function buildParamTree(opts: {
  subject: Subject;
  arms?: ArmResult[];
  powerByRegion?: Record<string, number>;
}): ParamNode {
  const children: ParamNode[] = [anthropometryTree(opts.subject)];
  if (opts.powerByRegion) children.push(chargeTree(opts.subject, opts.powerByRegion));
  if (opts.arms?.length) children.push(resultsTree(opts.arms));
  return { name: "parameters", children };
}
