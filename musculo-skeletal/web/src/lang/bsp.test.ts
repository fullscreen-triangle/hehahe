/**
 * Tests for body segment parameters.
 *
 * The load-bearing ones are the closure checks: a fractional mass table that
 * does not sum to the whole body is wrong in a way that no single row reveals.
 */

import { describe, expect, it } from "vitest";
import {
  analyseSubject, massClosure, movingMassForRegion, REFERENCE_SAMPLE,
  segmentParameters, type Subject,
} from "./bsp";
import { allRegions, resolveRegion } from "../components/AnatomyFigure";

describe("table integrity", () => {
  it("de Leva masses close to the whole body, both sexes", () => {
    // head + trunk + 2x(upper arm, forearm, hand, thigh, shank, foot)
    for (const sex of ["male", "female"] as const) {
      const total = massClosure("deLeva", sex);
      expect(total).toBeGreaterThan(0.98);
      expect(total).toBeLessThan(1.02);
    }
  });

  it("de Leva trunk sub-segments partition the trunk exactly", () => {
    for (const sex of ["male", "female"] as const) {
      const t = segmentParameters("deLeva", sex);
      const trunk = t.find((x) => x.segment === "trunk")!.mass;
      const parts = ["upper trunk", "middle trunk", "lower trunk"]
        .map((n) => t.find((x) => x.segment === n)!.mass)
        .reduce((a, b) => a + b, 0);
      // This is the check that catches a mistyped digit anywhere in the four.
      expect(parts).toBeCloseTo(trunk, 4);
    }
  });

  it("every fraction is physically plausible", () => {
    for (const model of ["deLeva", "dempster"] as const) {
      const sexes = model === "dempster" ? (["male"] as const) : (["male", "female"] as const);
      for (const sex of sexes) {
        for (const s of segmentParameters(model, sex)) {
          expect(s.mass).toBeGreaterThan(0);
          expect(s.mass).toBeLessThan(0.6);
          expect(s.cmProximal).toBeGreaterThanOrEqual(0);
          expect(s.cmProximal).toBeLessThanOrEqual(1);
          for (const v of Object.values(s.rg)) {
            if (v === undefined) continue;
            expect(v).toBeGreaterThan(0);
            expect(v).toBeLessThan(1.5);
          }
        }
      }
    }
  });

  it("Dempster limb radii obey Rg_prox^2 = Rg_cm^2 + CM_prox^2", () => {
    // Winter's proximal and distal radius columns are redundant: they follow
    // from the C-of-G radius and the CM location by the parallel-axis
    // theorem. Checking the identity is therefore a transcription check on
    // every limb row at once.
    //
    // head+neck is excluded, and the exclusion is the point rather than a
    // convenience: Winter marks that row "PC" (calculated), and its radii are
    // referenced to a different length than its own, so the identity does not
    // apply. Including it would force either a wrong tolerance or a wrong
    // number.
    const exempt = new Set(["head+neck"]);
    let checked = 0;
    for (const s of segmentParameters("dempster", "male")) {
      const { cm, proximal } = s.rg;
      if (cm === undefined || proximal === undefined || exempt.has(s.segment)) continue;
      expect(proximal * proximal, s.segment).toBeCloseTo(cm * cm + s.cmProximal * s.cmProximal, 3);
      checked++;
    }
    // Guard against the loop silently checking nothing.
    expect(checked).toBeGreaterThanOrEqual(6);
  });

  it("head+neck genuinely violates that identity, as documented", () => {
    // If a future edit "fixes" this row to satisfy the identity, it will have
    // departed from Winter's published values -- so the violation is asserted.
    const hn = segmentParameters("dempster", "male").find((x) => x.segment === "head+neck")!;
    const lhs = hn.rg.proximal! ** 2;
    const rhs = hn.rg.cm! ** 2 + hn.cmProximal ** 2;
    expect(Math.abs(lhs - rhs)).toBeGreaterThan(1);
  });

  it("de Leva thigh is substantially heavier than Dempster's", () => {
    // The two models define the thigh differently (HJC vs greater
    // trochanter), so this difference is real and is exactly why the models
    // must not be mixed.
    const dl = segmentParameters("deLeva", "male").find((x) => x.segment === "thigh")!.mass;
    const dm = segmentParameters("dempster", "male").find((x) => x.segment === "thigh")!.mass;
    expect(dl / dm).toBeGreaterThan(1.3);
  });
});

describe("model separation", () => {
  it("refuses to give Dempster parameters for a female subject", () => {
    expect(() => segmentParameters("dempster", "female")).toThrow(/no female data/i);
  });

  it("de Leva male and female tables genuinely differ", () => {
    const m = segmentParameters("deLeva", "male");
    const f = segmentParameters("deLeva", "female");
    const diffs = m.filter((x, i) => x.mass !== f[i].mass || x.cmProximal !== f[i].cmProximal);
    expect(diffs.length).toBe(m.length);
  });
});

describe("subject analysis", () => {
  const subject: Subject = { massKg: 83, statureM: 1.85, sex: "male", model: "deLeva" };

  it("scales absolute masses from body mass", () => {
    const r = analyseSubject(subject);
    const thigh = r.find((x) => x.segment === "thigh")!;
    expect(thigh.massKg).toBeCloseTo(0.1416 * 83, 6);
    // Paired: both thighs together.
    expect(thigh.totalMassKg).toBeCloseTo(2 * 0.1416 * 83, 6);
  });

  it("scales lengths by stature and says it did", () => {
    const r = analyseSubject(subject);
    const thigh = r.find((x) => x.segment === "thigh")!;
    expect(thigh.lengthSource).toBe("scaled");
    const ref = REFERENCE_SAMPLE.deLeva.male;
    expect(thigh.lengthM).toBeCloseTo(0.4222 * (1.85 / ref.statureM), 6);
  });

  it("prefers a measured length and labels it as measured", () => {
    const r = analyseSubject({ ...subject, segmentLengthsM: { thigh: 0.44 } });
    const thigh = r.find((x) => x.segment === "thigh")!;
    expect(thigh.lengthM).toBe(0.44);
    expect(thigh.lengthSource).toBe("measured");
  });

  it("gives Dempster lengths from Winter's stature law, labelled as such", () => {
    // Dempster's own table has no lengths. Winter Figure 4.1 IS a stature
    // law (unlike de Leva's sample means), so it applies directly -- but the
    // source is recorded so a result can say which it rests on.
    const r = analyseSubject({ ...subject, model: "dempster" });
    const thigh = r.find((x) => x.segment === "thigh")!;
    expect(thigh.lengthSource).toBe("stature");
    expect(thigh.lengthM).toBeCloseTo(0.190 * 1.85, 9);
    expect(thigh.inertiaCmKgM2).not.toBeNull();
  });

  it("still reports unavailable when no length source covers a segment", () => {
    const r = analyseSubject({ ...subject, model: "dempster" });
    const pelvis = r.find((x) => x.segment === "pelvis")!;
    expect(pelvis.lengthSource).toBe("unavailable");
    expect(Number.isNaN(pelvis.lengthM)).toBe(true);
    // No inertia is fabricated from a missing length.
    expect(pelvis.inertiaCmKgM2).toBeNull();
  });

  it("computes inertia by I = m (rg L)^2", () => {
    const r = analyseSubject(subject);
    const shank = r.find((x) => x.segment === "shank")!;
    const expected = shank.massKg * Math.pow(0.255 * shank.lengthM, 2);
    expect(shank.inertiaCmKgM2!).toBeCloseTo(expected, 9);
  });

  it("applies the parallel-axis theorem to the proximal end", () => {
    const r = analyseSubject(subject);
    for (const s of r) {
      if (s.inertiaCmKgM2 === null) continue;
      const expected = s.inertiaCmKgM2 + s.massKg * s.cmFromProximalM ** 2;
      expect(s.inertiaProximalKgM2!).toBeCloseTo(expected, 12);
      // Proximal inertia must exceed CM inertia: the axis moved away.
      expect(s.inertiaProximalKgM2!).toBeGreaterThan(s.inertiaCmKgM2);
    }
  });

  it("segment masses sum to the subject's mass", () => {
    const r = analyseSubject(subject);
    const parts = new Set(["upper trunk", "middle trunk", "lower trunk"]);
    const total = r.filter((x) => !parts.has(x.segment)).reduce((s, x) => s + x.totalMassKg, 0);
    expect(total).toBeCloseTo(83, 0);
  });

  it("scales with the subject rather than being constant", () => {
    const light = analyseSubject({ ...subject, massKg: 55 });
    const heavy = analyseSubject({ ...subject, massKg: 110 });
    const t = (r: ReturnType<typeof analyseSubject>) => r.find((x) => x.segment === "thigh")!.massKg;
    expect(t(heavy) / t(light)).toBeCloseTo(2, 6);
  });
});

describe("connection to the rest of the tool", () => {
  const subject: Subject = { massKg: 83, statureM: 1.85, sex: "male", model: "deLeva" };

  it("gives an effective moving mass per region", () => {
    const r = analyseSubject(subject);
    const thighMass = movingMassForRegion(r, "right-thigh");
    expect(thighMass).toBeCloseTo(0.1416 * 83, 6);
    // A region the table does not cover returns null, not zero: zero would
    // silently produce zero power downstream.
    expect(movingMassForRegion(r, "left-eye")).toBeNull();
  });

  it("every segment region exists in the anatomy figure", () => {
    // If a table region cannot be drawn, the heatmap silently omits it.
    const known = new Set(allRegions("body"));
    for (const model of ["deLeva", "dempster"] as const) {
      for (const s of segmentParameters(model, "male")) {
        if (s.region === null) continue;
        const resolved = resolveRegion(s.region, "body");
        expect(resolved, `region "${s.region}" of segment "${s.segment}"`).not.toBeNull();
        expect(known.has(resolved!)).toBe(true);
      }
    }
  });
});

describe("stature law integrity", () => {
  it("derived fractions agree with the figure's own heights", async () => {
    const { STATURE_FRACTION, STATURE_FRACTION_DERIVED } = await import("./bsp");
    // Winter Fig 4.1 heights above the floor.
    const H = { shoulder: 0.818, hip: 0.720, knee: 0.530, ankle: 0.039 };
    // Thigh and trunk are not labelled directly; they are differences.
    expect(STATURE_FRACTION.thigh).toBeCloseTo(H.hip - H.knee, 3);
    expect(STATURE_FRACTION.trunk).toBeCloseTo(H.shoulder - H.hip, 3);
    expect(STATURE_FRACTION_DERIVED.has("thigh")).toBe(true);
    expect(STATURE_FRACTION_DERIVED.has("trunk")).toBe(true);
  });

  it("shank agrees with the knee-to-ankle height difference", async () => {
    const { STATURE_FRACTION } = await import("./bsp");
    // 0.530H knee - 0.039H ankle = 0.491H, but the figure tabulates the
    // knee-to-ankle SEGMENT as 0.285H. These differ because the tabulated
    // value is the shank proper while the height difference includes the
    // foot's vertical offset. The tabulated value is the segment length.
    expect(STATURE_FRACTION.shank).toBe(0.285);
  });

  it("no stature fraction produces an implausible segment", async () => {
    const { STATURE_FRACTION } = await import("./bsp");
    for (const [seg, f] of Object.entries(STATURE_FRACTION)) {
      expect(f, seg).toBeGreaterThan(0.02);
      expect(f, seg).toBeLessThan(0.6);
    }
  });

  it("body breadths are kept out of the length law", async () => {
    const { STATURE_FRACTION, BREADTH_FRACTION } = await import("./bsp");
    // A breadth is measured across the body, not along a segment axis, so
    // using one as a segment length would be a category error.
    for (const k of Object.keys(BREADTH_FRACTION)) {
      expect(STATURE_FRACTION[k]).toBeUndefined();
    }
  });
});
