/**
 * Body segment parameters.
 *
 * Establishes the anthropometry a subject's model is built from: segment
 * masses, centre-of-mass positions, radii of gyration, and the moments of
 * inertia that follow. Everything downstream -- the charge accounting, the
 * anatomical binding, the rig's effective moving mass -- can be scaled from
 * one subject's mass and stature instead of carrying hard-coded constants.
 *
 * Two independent models are provided, and they are NOT interchangeable.
 *
 *   deLeva   Zatsiorsky-Seluyanov as adjusted by de Leva (1996), separate
 *            male and female tables, from gamma-ray scans of 100 young men
 *            and 15 young women.
 *   dempster Dempster (1955) as adapted by Winter (2009), from 8 elderly
 *            male cadavers. No female data exists in this model at all.
 *
 * Their segment definitions differ: de Leva's thigh runs hip-joint-centre to
 * knee-joint-centre, Dempster's runs greater trochanter to knee. The masses
 * differ accordingly -- de Leva's thigh is about 42% heavier than Dempster's,
 * and his trunk about 15% lighter. Mixing rows from the two models produces a
 * body whose segments do not tile, so `segmentParameters` takes the model as
 * an argument and never silently falls back to the other one.
 *
 * Sources:
 *   de Leva P (1996) "Adjustments to Zatsiorsky-Seluyanov's segment inertia
 *     parameters." J Biomech 29(9):1223-1230. Table 4.
 *   Winter DA (2009) "Biomechanics and Motor Control of Human Movement",
 *     4th ed., Table 4.1, after Dempster (1955).
 *   BMClab/BMC, notebooks/BodySegmentParameters.ipynb, for the formulas.
 */

export type Sex = "male" | "female";
export type BspModel = "deLeva" | "dempster";

/**
 * One segment's parameters, all as fractions.
 *
 * `mass` is a fraction of TOTAL BODY MASS. `cmProximal` is a fraction of
 * segment length measured from the proximal endpoint. Radii of gyration are
 * fractions of segment length; de Leva gives three principal axes, Dempster
 * gives one about the CM plus two about the endpoints.
 */
export interface SegmentSpec {
  segment: string;
  /** proximal and distal landmarks defining the segment */
  endpoints: [string, string];
  /** fraction of total body mass; per single limb for paired segments */
  mass: number;
  /** CM from proximal end, as a fraction of segment length */
  cmProximal: number;
  /** radii of gyration as fractions of segment length */
  rg: { sagittal?: number; transverse?: number; longitudinal?: number; cm?: number; proximal?: number; distal?: number };
  /** true when the segment exists once per side */
  paired: boolean;
  /** anatomical region for the reference figure; null = not localised */
  region: string | null;
  /** mean segment length in the source sample, metres (de Leva only) */
  sampleLengthM?: number;
}

// ── de Leva (1996) Table 4 ───────────────────────────────────────────
//
// Primary endpoint definitions only. de Leva also publishes alternative
// endpoint pairs (e.g. shank measured to the ankle joint centre rather than
// the lateral malleolus); those are a different row with different CM and Rg
// values, and are deliberately not merged in here.
//
// NOTE on a known upstream defect: the BMClab CSVs label de Leva's shank rows
// in the wrong order -- they name the KJC-AJC row "Shank" and the KJC-LMAL row
// "Shank 2", whereas de Leva's primary shank is KJC-LMAL. Indexing that CSV by
// "Shank" silently returns the ALTERNATIVE parameters. The values below follow
// de Leva's own convention.

const DELEVA_MALE: SegmentSpec[] = [
  { segment: "head", endpoints: ["vertex", "midgonion"], mass: 0.0694, cmProximal: 0.5976,
    rg: { sagittal: 0.362, transverse: 0.376, longitudinal: 0.312 }, paired: false, region: "head", sampleLengthM: 0.2033 },
  { segment: "trunk", endpoints: ["suprasternale", "midhip"], mass: 0.4346, cmProximal: 0.4486,
    rg: { sagittal: 0.372, transverse: 0.347, longitudinal: 0.191 }, paired: false, region: "chest", sampleLengthM: 0.5319 },
  { segment: "upper trunk", endpoints: ["suprasternale", "xyphion"], mass: 0.1596, cmProximal: 0.2999,
    rg: { sagittal: 0.716, transverse: 0.454, longitudinal: 0.659 }, paired: false, region: "chest", sampleLengthM: 0.1707 },
  { segment: "middle trunk", endpoints: ["xyphion", "omphalion"], mass: 0.1633, cmProximal: 0.4502,
    rg: { sagittal: 0.482, transverse: 0.383, longitudinal: 0.468 }, paired: false, region: "abdomen", sampleLengthM: 0.2155 },
  { segment: "lower trunk", endpoints: ["omphalion", "midhip"], mass: 0.1117, cmProximal: 0.6115,
    rg: { sagittal: 0.615, transverse: 0.551, longitudinal: 0.587 }, paired: false, region: "pelvis", sampleLengthM: 0.1457 },
  { segment: "upper arm", endpoints: ["shoulder joint centre", "elbow joint centre"], mass: 0.0271, cmProximal: 0.5772,
    rg: { sagittal: 0.285, transverse: 0.269, longitudinal: 0.158 }, paired: true, region: "right-arm", sampleLengthM: 0.2817 },
  { segment: "forearm", endpoints: ["elbow joint centre", "wrist joint centre"], mass: 0.0162, cmProximal: 0.4574,
    rg: { sagittal: 0.276, transverse: 0.265, longitudinal: 0.121 }, paired: true, region: "right-forearm", sampleLengthM: 0.2689 },
  { segment: "hand", endpoints: ["wrist joint centre", "3rd metacarpal"], mass: 0.0061, cmProximal: 0.7900,
    rg: { sagittal: 0.628, transverse: 0.513, longitudinal: 0.401 }, paired: true, region: "right-hand", sampleLengthM: 0.0862 },
  { segment: "thigh", endpoints: ["hip joint centre", "knee joint centre"], mass: 0.1416, cmProximal: 0.4095,
    rg: { sagittal: 0.329, transverse: 0.329, longitudinal: 0.149 }, paired: true, region: "right-thigh", sampleLengthM: 0.4222 },
  { segment: "shank", endpoints: ["knee joint centre", "lateral malleolus"], mass: 0.0433, cmProximal: 0.4459,
    rg: { sagittal: 0.255, transverse: 0.249, longitudinal: 0.103 }, paired: true, region: "right-leg", sampleLengthM: 0.4340 },
  { segment: "foot", endpoints: ["heel", "toe tip"], mass: 0.0137, cmProximal: 0.4415,
    rg: { sagittal: 0.257, transverse: 0.245, longitudinal: 0.124 }, paired: true, region: "right-foot", sampleLengthM: 0.2581 },
];

const DELEVA_FEMALE: SegmentSpec[] = [
  { segment: "head", endpoints: ["vertex", "midgonion"], mass: 0.0668, cmProximal: 0.5894,
    rg: { sagittal: 0.330, transverse: 0.359, longitudinal: 0.318 }, paired: false, region: "head", sampleLengthM: 0.2002 },
  { segment: "trunk", endpoints: ["suprasternale", "midhip"], mass: 0.4257, cmProximal: 0.4151,
    rg: { sagittal: 0.357, transverse: 0.339, longitudinal: 0.171 }, paired: false, region: "chest", sampleLengthM: 0.5293 },
  { segment: "upper trunk", endpoints: ["suprasternale", "xyphion"], mass: 0.1545, cmProximal: 0.2077,
    rg: { sagittal: 0.746, transverse: 0.502, longitudinal: 0.718 }, paired: false, region: "chest", sampleLengthM: 0.1425 },
  { segment: "middle trunk", endpoints: ["xyphion", "omphalion"], mass: 0.1465, cmProximal: 0.4512,
    rg: { sagittal: 0.433, transverse: 0.354, longitudinal: 0.415 }, paired: false, region: "abdomen", sampleLengthM: 0.2053 },
  { segment: "lower trunk", endpoints: ["omphalion", "midhip"], mass: 0.1247, cmProximal: 0.4920,
    rg: { sagittal: 0.433, transverse: 0.402, longitudinal: 0.444 }, paired: false, region: "pelvis", sampleLengthM: 0.1815 },
  { segment: "upper arm", endpoints: ["shoulder joint centre", "elbow joint centre"], mass: 0.0255, cmProximal: 0.5754,
    rg: { sagittal: 0.278, transverse: 0.260, longitudinal: 0.148 }, paired: true, region: "right-arm", sampleLengthM: 0.2751 },
  { segment: "forearm", endpoints: ["elbow joint centre", "wrist joint centre"], mass: 0.0138, cmProximal: 0.4559,
    rg: { sagittal: 0.261, transverse: 0.257, longitudinal: 0.094 }, paired: true, region: "right-forearm", sampleLengthM: 0.2643 },
  { segment: "hand", endpoints: ["wrist joint centre", "3rd metacarpal"], mass: 0.0056, cmProximal: 0.7474,
    rg: { sagittal: 0.531, transverse: 0.454, longitudinal: 0.335 }, paired: true, region: "right-hand", sampleLengthM: 0.0780 },
  { segment: "thigh", endpoints: ["hip joint centre", "knee joint centre"], mass: 0.1478, cmProximal: 0.3612,
    rg: { sagittal: 0.369, transverse: 0.364, longitudinal: 0.162 }, paired: true, region: "right-thigh", sampleLengthM: 0.3685 },
  { segment: "shank", endpoints: ["knee joint centre", "lateral malleolus"], mass: 0.0481, cmProximal: 0.4416,
    rg: { sagittal: 0.271, transverse: 0.267, longitudinal: 0.093 }, paired: true, region: "right-leg", sampleLengthM: 0.4323 },
  { segment: "foot", endpoints: ["heel", "toe tip"], mass: 0.0129, cmProximal: 0.4014,
    rg: { sagittal: 0.299, transverse: 0.279, longitudinal: 0.139 }, paired: true, region: "right-foot", sampleLengthM: 0.2283 },
];

// ── Dempster (1955) as adapted by Winter (2009) ──────────────────────
//
// Single-limb segments only, to match de Leva's granularity. Winter's
// compound rows (forearm+hand, total arm, foot+leg, total leg, HAT) are
// omitted here rather than mixed with the singles, because summing a compound
// row together with its own parts double-counts mass.
//
// Dempster's trunk rows carry no radius of gyration in Winter's table; those
// fields are left undefined rather than filled with a plausible number.

const DEMPSTER: SegmentSpec[] = [
  { segment: "head+neck", endpoints: ["C7-T1", "ear canal"], mass: 0.0810, cmProximal: 1.000,
    rg: { cm: 0.495, proximal: 0.116 }, paired: false, region: "head" },
  { segment: "trunk", endpoints: ["greater trochanter", "shoulder joint centre"], mass: 0.4970, cmProximal: 0.500,
    rg: {}, paired: false, region: "chest" },
  { segment: "thorax", endpoints: ["C7-T1", "T12-L1"], mass: 0.2160, cmProximal: 0.820,
    rg: {}, paired: false, region: "chest" },
  { segment: "abdomen", endpoints: ["T12-L1", "greater trochanter"], mass: 0.1390, cmProximal: 0.440,
    rg: {}, paired: false, region: "abdomen" },
  { segment: "pelvis", endpoints: ["L4-L5", "greater trochanter"], mass: 0.1420, cmProximal: 0.105,
    rg: {}, paired: false, region: "pelvis" },
  { segment: "upper arm", endpoints: ["shoulder joint centre", "elbow joint centre"], mass: 0.0280, cmProximal: 0.436,
    rg: { cm: 0.322, proximal: 0.542, distal: 0.645 }, paired: true, region: "right-arm" },
  { segment: "forearm", endpoints: ["elbow joint centre", "styloid"], mass: 0.0160, cmProximal: 0.430,
    rg: { cm: 0.303, proximal: 0.526, distal: 0.647 }, paired: true, region: "right-forearm" },
  { segment: "hand", endpoints: ["wrist joint centre", "2nd knuckle"], mass: 0.0060, cmProximal: 0.506,
    rg: { cm: 0.297, proximal: 0.587, distal: 0.577 }, paired: true, region: "right-hand" },
  { segment: "thigh", endpoints: ["greater trochanter", "knee joint centre"], mass: 0.1000, cmProximal: 0.433,
    rg: { cm: 0.323, proximal: 0.540, distal: 0.653 }, paired: true, region: "right-thigh" },
  { segment: "shank", endpoints: ["knee joint centre", "medial malleolus"], mass: 0.0465, cmProximal: 0.433,
    rg: { cm: 0.302, proximal: 0.528, distal: 0.643 }, paired: true, region: "right-leg" },
  { segment: "foot", endpoints: ["lateral malleolus", "2nd metatarsal"], mass: 0.0145, cmProximal: 0.500,
    rg: { cm: 0.475, proximal: 0.690, distal: 0.690 }, paired: true, region: "right-foot" },
];

/**
 * Segment length as a fraction of stature.
 *
 * Winter (2009) Figure 4.1, after Drillis and Contini (1966). This is a
 * scaling law -- unlike de Leva's lengths, which are sample means -- so it is
 * the right source for a Dempster segment, whose own table carries no
 * lengths at all.
 *
 * Thigh is not labelled directly in the figure. It is the difference between
 * the hip (0.720H) and knee (0.530H) heights, = 0.190H, and is marked as
 * derived rather than quoted.
 *
 * Caution: several values circulating in secondary sources (a "0.245H thigh /
 * 0.246H shank" pairing in particular) do not appear in Figure 4.1 at all.
 * The values here were read off a rendered image of the page, because the
 * PDF's text layer misaligns the columns.
 */
export const STATURE_FRACTION: Record<string, number> = {
  "head+neck": 0.130,      // head height
  "upper arm": 0.186,
  forearm: 0.146,
  hand: 0.108,
  thigh: 0.190,            // derived: 0.720H hip - 0.530H knee
  shank: 0.285,            // knee to ankle
  foot: 0.152,             // foot length
  // Dempster's trunk is defined greater trochanter -> glenohumeral joint,
  // which from the figure's heights is 0.818H - 0.720H = 0.098H. The figure
  // also tabulates a 0.520H "shoulder to hip" span, but that is a DIFFERENT
  // distance (it runs to the hip joint, not between those two landmarks) and
  // using it here inflated the trunk moment of inertia by a factor of ~28.
  trunk: 0.098,
};

/** Entries derived from differences of the figure's heights rather than
 *  quoted directly, so a reader can tell which is which. */
export const STATURE_FRACTION_SOURCE: Record<string, string> = {
  "head+neck": "Fig 4.1, head height 0.130H",
  "upper arm": "Fig 4.1, 0.186H",
  forearm: "Fig 4.1, 0.146H",
  hand: "Fig 4.1, 0.108H",
  thigh: "derived: hip 0.720H - knee 0.530H",
  shank: "Fig 4.1, knee-to-ankle 0.285H",
  foot: "Fig 4.1, foot length 0.152H",
  trunk: "derived: shoulder 0.818H - trochanter 0.720H",
};

/**
 * Body breadths, also from Figure 4.1. These are NOT segment lengths -- they
 * are measured across the body, not along a segment axis -- so they are kept
 * separate rather than being usable as a length by accident.
 */
export const BREADTH_FRACTION: Record<string, number> = {
  shoulder: 0.259,   // biacromial
  chest: 0.174,
  hip: 0.191,
  "foot breadth": 0.055,
};

/** Which STATURE_FRACTION entries are quoted from the figure vs derived. */
export const STATURE_FRACTION_DERIVED = new Set(["thigh", "trunk"]);

/** The reference samples the fractional tables were measured on. */
export const REFERENCE_SAMPLE = {
  deLeva: {
    male: { massKg: 73.0, statureM: 1.741, n: 100 },
    female: { massKg: 61.9, statureM: 1.735, n: 15 },
  },
  dempster: {
    male: { massKg: NaN, statureM: NaN, n: 8 },
    female: null,
  },
} as const;

/**
 * The table for a model and sex.
 *
 * Dempster has no female data. Rather than substitute the male table -- which
 * would present male cadaver parameters as if they described a woman -- this
 * throws, and the caller must choose de Leva or state the substitution.
 */
export function segmentParameters(model: BspModel, sex: Sex): SegmentSpec[] {
  if (model === "dempster") {
    if (sex === "female") {
      throw new Error(
        "Dempster (1955) has no female data: the sample was 8 elderly male " +
          "cadavers. Use model 'deLeva', which has a female table, rather than " +
          "applying male parameters to a female subject.",
      );
    }
    return DEMPSTER;
  }
  return sex === "male" ? DELEVA_MALE : DELEVA_FEMALE;
}

// ── derived quantities ───────────────────────────────────────────────

export interface Subject {
  massKg: number;
  statureM: number;
  sex: Sex;
  model: BspModel;
  /** measured segment lengths, metres; overrides the scaled estimate */
  segmentLengthsM?: Record<string, number>;
}

export interface SegmentResult extends SegmentSpec {
  /** absolute mass, kg; for a paired segment this is ONE side */
  massKg: number;
  /** total mass contributed by this segment, both sides if paired */
  totalMassKg: number;
  lengthM: number;
  /** how lengthM was obtained: measured on the subject, scaled from a
   *  sample mean (de Leva), from Winter's stature law, or unavailable */
  lengthSource: "measured" | "scaled" | "stature" | "unavailable";
  /** CM distance from the proximal end, metres */
  cmFromProximalM: number;
  /** moment of inertia about the segment CM, kg m^2, using the sagittal
   *  radius of gyration (de Leva) or the CM radius (Dempster) */
  inertiaCmKgM2: number | null;
  /** about the proximal endpoint, by the parallel-axis theorem */
  inertiaProximalKgM2: number | null;
}

/**
 * Segment length for a subject.
 *
 * de Leva's lengths are SAMPLE MEANS, not a scaling law -- he intends lengths
 * to be measured on the subject. Scaling them by stature ratio is therefore a
 * stated approximation, and `lengthSource` records which case applied so a
 * downstream result can say whether it rests on a measurement or an estimate.
 *
 * Dempster's table carries no lengths at all in Winter's Table 4.1, so a
 * Dempster segment has no length unless one is supplied.
 */
function lengthOf(spec: SegmentSpec, s: Subject): { m: number; source: SegmentResult["lengthSource"] } {
  const measured = s.segmentLengthsM?.[spec.segment];
  if (measured && measured > 0) return { m: measured, source: "measured" };

  // de Leva: scale his sample mean by stature ratio.
  if (spec.sampleLengthM !== undefined) {
    const ref = REFERENCE_SAMPLE.deLeva[s.sex];
    return { m: spec.sampleLengthM * (s.statureM / ref.statureM), source: "scaled" };
  }

  // Dempster: Winter's Figure 4.1 IS a stature law, so it applies directly.
  const frac = STATURE_FRACTION[spec.segment];
  if (frac !== undefined) return { m: frac * s.statureM, source: "stature" };

  return { m: NaN, source: "unavailable" };
}

/** The radius of gyration to use for the CM inertia, per model. */
function rgForInertia(spec: SegmentSpec): number | undefined {
  return spec.rg.sagittal ?? spec.rg.cm;
}

/**
 * Build the full segment table for a subject.
 *
 *   I_cm  = m (r_g L)^2
 *   I_p   = I_cm + m d^2      (parallel axis, d = CM distance from the pivot)
 *
 * where m is the segment's absolute mass and L its length.
 */
export function analyseSubject(s: Subject): SegmentResult[] {
  const specs = segmentParameters(s.model, s.sex);
  return specs.map((spec) => {
    const { m: lengthM, source } = lengthOf(spec, s);
    const massKg = spec.mass * s.massKg;
    const rg = rgForInertia(spec);
    const cmFromProximalM = lengthM * spec.cmProximal;

    let inertiaCm: number | null = null;
    let inertiaProx: number | null = null;
    if (rg !== undefined && Number.isFinite(lengthM)) {
      inertiaCm = massKg * Math.pow(rg * lengthM, 2);
      inertiaProx = inertiaCm + massKg * Math.pow(cmFromProximalM, 2);
    }

    return {
      ...spec,
      massKg,
      totalMassKg: massKg * (spec.paired ? 2 : 1),
      lengthM,
      lengthSource: source,
      cmFromProximalM,
      inertiaCmKgM2: inertiaCm,
      inertiaProximalKgM2: inertiaProx,
    };
  });
}

/**
 * Total mass accounted for by the table, as a fraction of body mass.
 *
 * This is a closure check on the model, not a free parameter. de Leva's
 * whole-body segments (head + trunk + 2x each limb segment) should sum to
 * essentially 1. A sum far from 1 means segments were double-counted --
 * typically by including both a compound row and its parts.
 */
export function massClosure(model: BspModel, sex: Sex): number {
  const specs = segmentParameters(model, sex);
  // The trunk sub-segments partition the trunk, so counting both the whole
  // trunk and its three parts double-counts. Use the whole trunk.
  const parts = new Set(["upper trunk", "middle trunk", "lower trunk", "thorax", "abdomen", "pelvis"]);
  return specs
    .filter((x) => !parts.has(x.segment))
    .reduce((sum, x) => sum + x.mass * (x.paired ? 2 : 1), 0);
}

/**
 * The effective moving mass for a region, used to turn observed motion into
 * mechanical power. This is what connects the anthropometry to the charge
 * accounting: instead of assuming a limb-scale mass, the mass comes from the
 * subject's own segment table.
 */
export function movingMassForRegion(results: SegmentResult[], region: string): number | null {
  const hit = results.filter((r) => r.region === region);
  if (!hit.length) return null;
  return hit.reduce((s, r) => s + r.massKg, 0);
}

/** Whole-body CM height above the floor is not derivable from the fractional
 *  table alone -- it needs a posture. Exposed so callers do not invent one. */
export const WHOLE_BODY_CM_REQUIRES_POSTURE =
  "Whole-body centre of mass is a mass-weighted mean of segment CM POSITIONS, " +
  "so it requires a posture (a set of landmark coordinates). The fractional " +
  "table alone does not determine it.";
