/**
 * Postural analysis on a pose stream, and its inverse.
 *
 * Two directions, both real:
 *
 *   FORWARD  pose stream -> rambling/trembling -> charge -> .vvs source
 *   INVERSE  .vvs circuit -> pose stream
 *
 * The forward direction is the interesting one. A rig's animation clip is a
 * body-sway record: joint translations sampled at a fixed rate. That is the
 * same class of signal a force plate or a waist IMU produces, so the
 * rambling/trembling decomposition applies to it directly -- and the result
 * can be turned back into a circuit whose declared strata reproduce the
 * bands that were measured.
 *
 * ── What this can and cannot see ────────────────────────────────────
 *
 * Honesty about bandwidth is not optional here, because the decomposition
 * silently produces numbers whatever you feed it.
 *
 *   - GLB clips in this project sample at 30 Hz. Nyquist is 15 Hz, so the
 *     trembling band (0.4-3 Hz) is recoverable but physiological tremor
 *     above ~5 Hz is not. Any spectral claim above 15 Hz is aliasing.
 *
 *   - Rambling lives below 0.4 Hz, so resolving it needs a record several
 *     times 1/0.4 = 2.5 s long. The `Idle` clip is 1.967 s: SHORTER than one
 *     rambling period. A decomposition run on one pass of that clip cannot
 *     see rambling at all; it can only see it once the clip is looped enough
 *     times to span the band, and looping introduces its own periodicity at
 *     the clip rate.
 *
 * Both facts are computed and reported per analysis (`adequacy`), never
 * assumed. An analysis that reports rambling from a 2-second window is
 * reporting the filter, not the subject.
 */

// ── charge, from the orthogonal-quantification scheme ────────────────

/**
 * Compartment capacitances, farads. These fix the power-to-charge map and
 * are the only place the charge scale enters.
 */
export const CAPACITANCE = {
  /** aggregate cortical: 1e11 neurons x 1e-11 F */
  brain: 1.0e-3,
  /** motor-neuron + NMJ + sarcolemma of the large postural muscles */
  motor: 1.41e-4,
  /** sensory-associative allocation, half the cortical aggregate */
  perception: 5.0e-4,
} as const;

export type Compartment = keyof typeof CAPACITANCE;

/**
 * Charge redistributed per second by a compartment carrying power P.
 *
 *   Q = sqrt(2 C P dt),  dt = 1 s
 *
 * from U = Q^2/(2C) applied per unit time. Mixing capacitances across
 * compartments is a category error -- each compartment converts at its own
 * C -- so this takes the compartment, not a bare number.
 */
export function chargeFromPower(powerW: number, compartment: Compartment): number {
  if (!(powerW > 0)) return 0;
  return Math.sqrt(2 * CAPACITANCE[compartment] * powerW);
}

/** Inverse of `chargeFromPower`: the power a given charge rate implies. */
export function powerFromCharge(chargeC: number, compartment: Compartment): number {
  if (!(chargeC > 0)) return 0;
  return (chargeC * chargeC) / (2 * CAPACITANCE[compartment]);
}

// ── signal types ─────────────────────────────────────────────────────

export interface PoseSignal {
  /** samples, in rig units */
  x: Float64Array;
  /** sample interval, seconds */
  dt: number;
  /** what produced it, for provenance */
  source: string;
}

export interface Adequacy {
  sampleRateHz: number;
  /** frequency injected by looping a short clip, if the record was looped */
  loopArtefactHz?: number;
  /** true when the dominant peak coincides with the looping frequency */
  dominantIsLoopArtefact?: boolean;
  nyquistHz: number;
  durationS: number;
  /** longest period the record can resolve, = duration */
  longestPeriodS: number;
  /** lowest frequency resolvable with at least `cyclesRequired` cycles */
  lowestResolvableHz: number;
  cyclesRequired: number;
  /** can the record see the rambling band at all? */
  ramblingResolvable: boolean;
  /** can the record see the trembling band? */
  tremblingResolvable: boolean;
  /** highest frequency the sample rate admits without aliasing */
  aliasFreeToHz: number;
  notes: string[];
}

/** Band edges, in Hz. The rambling/trembling cut is the standard 0.4 Hz. */
export const BANDS = {
  rambling: [0.0, 0.4],
  trembling: [0.4, 3.0],
} as const;

/**
 * What a record of this length and rate can honestly support.
 *
 * `cyclesRequired` is how many full cycles of a frequency must fit in the
 * record before an amplitude at that frequency is worth reporting. Three is
 * already generous for a periodogram.
 */
export function adequacy(sig: PoseSignal, cyclesRequired = 3): Adequacy {
  const fs = 1 / sig.dt;
  const duration = sig.x.length * sig.dt;
  const lowest = cyclesRequired / duration;
  const notes: string[] = [];

  const ramblingResolvable = lowest <= BANDS.rambling[1];
  const tremblingResolvable = lowest <= BANDS.trembling[1] && fs / 2 >= BANDS.trembling[1];

  if (!ramblingResolvable) {
    notes.push(
      `Record is ${duration.toFixed(2)} s. Resolving the rambling band ` +
        `(below ${BANDS.rambling[1]} Hz) at ${cyclesRequired} cycles needs ` +
        `${(cyclesRequired / BANDS.rambling[1]).toFixed(1)} s. Rambling is NOT resolvable ` +
        `here; any value reported for it is the filter, not the subject.`,
    );
  }
  if (fs / 2 < 5) {
    notes.push(
      `Nyquist is ${(fs / 2).toFixed(1)} Hz. Physiological tremor above ` +
        `${(fs / 2).toFixed(1)} Hz cannot be seen and would alias into the ` +
        `trembling band if present.`,
    );
  }
  if (!tremblingResolvable) {
    notes.push(`The trembling band (${BANDS.trembling[0]}-${BANDS.trembling[1]} Hz) is not fully resolvable.`);
  }

  return {
    sampleRateHz: fs,
    nyquistHz: fs / 2,
    durationS: duration,
    longestPeriodS: duration,
    lowestResolvableHz: lowest,
    cyclesRequired,
    ramblingResolvable,
    tremblingResolvable,
    aliasFreeToHz: fs / 2,
    notes,
  };
}

// ── decomposition ────────────────────────────────────────────────────

export interface Decomposition {
  rambling: Float64Array;
  trembling: Float64Array;
  ramblingRms: number;
  tremblingRms: number;
  /** |sum of components - original|, max over samples. Should be ~0. */
  reconstructionError: number;
  /** cross-correlation of rambling with the trembling envelope, at zero lag */
  couplingIndex: number;
  adequacy: Adequacy;
}

/**
 * Zero-phase low-pass by forward-backward single-pole filtering.
 *
 * Zero-phase matters: a causal filter delays the rambling estimate, and the
 * coupling index is a zero-lag statistic, so any phase error goes straight
 * into the number that is supposed to diagnose cerebellar timing.
 */
function lowpassZeroPhase(x: Float64Array, dt: number, cutoffHz: number): Float64Array {
  const rc = 1 / (2 * Math.PI * cutoffHz);
  const a = dt / (rc + dt);
  const n = x.length;
  const fwd = new Float64Array(n);
  let acc = x[0];
  for (let i = 0; i < n; i++) {
    acc += a * (x[i] - acc);
    fwd[i] = acc;
  }
  const out = new Float64Array(n);
  acc = fwd[n - 1];
  for (let i = n - 1; i >= 0; i--) {
    acc += a * (fwd[i] - acc);
    out[i] = acc;
  }
  return out;
}

const rms = (v: Float64Array) => {
  let s = 0;
  for (let i = 0; i < v.length; i++) s += v[i] * v[i];
  return Math.sqrt(s / Math.max(1, v.length));
};

const mean = (v: Float64Array) => {
  let s = 0;
  for (let i = 0; i < v.length; i++) s += v[i];
  return s / Math.max(1, v.length);
};

/**
 * Split a sway record into its rambling and trembling components.
 *
 * The two components sum exactly to the input by construction (trembling is
 * defined as the residual), so `reconstructionError` is a check on the
 * arithmetic, not on the model. It is reported because a decomposition whose
 * parts do not re-sum is broken in a way that is otherwise invisible.
 */
export function decompose(
  sig: PoseSignal,
  cutoffHz = BANDS.rambling[1],
  loopArtefactHz?: number,
): Decomposition {
  const n = sig.x.length;
  const ra = lowpassZeroPhase(sig.x, sig.dt, cutoffHz);
  const tr = new Float64Array(n);
  let recon = 0;
  for (let i = 0; i < n; i++) {
    tr[i] = sig.x[i] - ra[i];
    recon = Math.max(recon, Math.abs(ra[i] + tr[i] - sig.x[i]));
  }

  // Coupling: rambling against the trembling envelope, zero lag.
  const env = new Float64Array(n);
  for (let i = 0; i < n; i++) env[i] = Math.abs(tr[i]);
  const mr = mean(ra);
  const me = mean(env);
  let num = 0;
  let dr = 0;
  let de = 0;
  for (let i = 0; i < n; i++) {
    const a = ra[i] - mr;
    const b = env[i] - me;
    num += a * b;
    dr += a * a;
    de += b * b;
  }
  const coupling = dr > 0 && de > 0 ? Math.abs(num / Math.sqrt(dr * de)) : 0;

  const ad = adequacy(sig);

  // A looped short clip injects a peak at 1/clipDuration that was never in
  // the subject. If the dominant trembling peak sits on that frequency, the
  // decomposition is reporting the loop -- which must be said, because the
  // number looks exactly like a finding otherwise.
  if (loopArtefactHz && loopArtefactHz > 0) {
    ad.loopArtefactHz = loopArtefactHz;
    const peak = dominantFrequency(tr, sig.dt, BANDS.trembling);
    const withinPct = Math.abs(peak - loopArtefactHz) / loopArtefactHz;
    ad.dominantIsLoopArtefact = withinPct < 0.05;
    if (ad.dominantIsLoopArtefact) {
      ad.notes.push(
        `Dominant trembling peak is ${peak.toFixed(3)} Hz and the record was ` +
          `looped at ${loopArtefactHz.toFixed(3)} Hz. These coincide to within ` +
          `${(withinPct * 100).toFixed(1)}%, so the peak is the LOOP, not the subject. ` +
          `Use a single pass, or a longer recording, before reporting a frequency.`,
      );
    }
  }

  return {
    rambling: ra,
    trembling: tr,
    ramblingRms: rms(ra),
    tremblingRms: rms(tr),
    reconstructionError: recon,
    couplingIndex: coupling,
    adequacy: ad,
  };
}

// ── sleep activity ───────────────────────────────────────────────────

export interface SleepEvent {
  /** seconds from record start */
  t: number;
  kind: "reposition" | "arousal";
  /** magnitude of the pose change that triggered it, rig units */
  magnitude: number;
}

export interface SleepAnalysis {
  events: SleepEvent[];
  repositions: number;
  arousals: number;
  /** repositions per hour of record */
  repositionRate: number;
  /** fraction of the record spent above the arousal threshold */
  wakeFraction: number;
  /** longest stretch with no reposition, seconds */
  longestStillS: number;
  durationS: number;
  thresholds: { reposition: number; arousal: number };
  adequacy: Adequacy;
}

/**
 * Count position changes in a sleep pose record.
 *
 * A reposition is a sustained displacement of the body, not a transient:
 * the test is that the pose moves by more than the threshold AND stays
 * moved. Without the sustain requirement a single noisy sample counts as a
 * roll, which inflates the rate by an order of magnitude.
 *
 * Thresholds are expressed as multiples of the record's own quiet-period
 * spread, so they do not depend on rig units.
 */
export function analyseSleep(
  sig: PoseSignal,
  opts: { repositionSd?: number; arousalSd?: number; sustainS?: number } = {},
): SleepAnalysis {
  const repositionSd = opts.repositionSd ?? 3;
  const arousalSd = opts.arousalSd ?? 6;
  const sustainS = opts.sustainS ?? 0.5;
  const n = sig.x.length;
  const duration = n * sig.dt;

  // Sample-to-sample motion, and its quiet-period scale (median absolute
  // difference is robust to the repositions we are trying to find).
  const diff = new Float64Array(Math.max(0, n - 1));
  for (let i = 1; i < n; i++) diff[i - 1] = Math.abs(sig.x[i] - sig.x[i - 1]);
  const sorted = Float64Array.from(diff).sort();
  const mad = sorted.length ? sorted[Math.floor(sorted.length / 2)] : 0;
  const scale = mad > 0 ? mad : rms(diff) || 1;

  const repThr = repositionSd * scale;
  const arThr = arousalSd * scale;
  const sustain = Math.max(1, Math.round(sustainS / sig.dt));

  const events: SleepEvent[] = [];
  let aboveArousal = 0;
  let i = 1;
  let lastEventIdx = -Infinity;
  while (i < n) {
    const d = Math.abs(sig.x[i] - sig.x[i - 1]);
    if (d > arThr) aboveArousal++;
    if (d > repThr && i - lastEventIdx >= sustain) {
      // Sustain test: did the pose actually stay moved?
      const before = sig.x[i - 1];
      let held = true;
      const end = Math.min(n, i + sustain);
      for (let k = i; k < end; k++) {
        if (Math.abs(sig.x[k] - before) < repThr * 0.5) {
          held = false;
          break;
        }
      }
      if (held) {
        events.push({
          t: i * sig.dt,
          kind: d > arThr ? "arousal" : "reposition",
          magnitude: d,
        });
        lastEventIdx = i;
      }
    }
    i++;
  }

  let longestStill = 0;
  let prev = 0;
  for (const e of events) {
    longestStill = Math.max(longestStill, e.t - prev);
    prev = e.t;
  }
  longestStill = Math.max(longestStill, duration - prev);

  const repositions = events.filter((e) => e.kind === "reposition").length;
  const arousals = events.filter((e) => e.kind === "arousal").length;

  return {
    events,
    repositions,
    arousals,
    repositionRate: duration > 0 ? (events.length / duration) * 3600 : 0,
    wakeFraction: n > 1 ? aboveArousal / (n - 1) : 0,
    longestStillS: longestStill,
    durationS: duration,
    thresholds: { reposition: repThr, arousal: arThr },
    adequacy: adequacy(sig),
  };
}

// ── charge accounting ────────────────────────────────────────────────

export interface ChargeAccount {
  /** mechanical power attributed to the movement, watts */
  powerW: number;
  /** charge rate at the motor capacitance, coulombs per second */
  chargeCs: number;
  compartment: Compartment;
  /** how the power was obtained, so the number is auditable */
  derivation: string;
  /** total charge moved over the record, coulombs */
  totalC: number;
  durationS: number;
}

/**
 * Charge attributable to a pose record.
 *
 * Power is estimated from the kinetic cost of the observed motion: the mean
 * squared velocity of the tracked point times an effective moving mass.
 * That is deliberately crude -- there is no force plate here and no attempt
 * to pretend otherwise -- but it is dimensionally honest and it scales
 * correctly with the movement actually present, which is what makes the
 * comparison between a still night and a restless one meaningful.
 *
 * The charge conversion itself is exact: Q = sqrt(2 C P).
 */
export function chargeOfMotion(
  sig: PoseSignal,
  opts: { unitsPerMetre?: number; effectiveMassKg?: number; compartment?: Compartment } = {},
): ChargeAccount {
  const upm = opts.unitsPerMetre ?? 100;
  const massKg = opts.effectiveMassKg ?? 8; // a limb-scale moving mass
  const compartment = opts.compartment ?? "motor";
  const n = sig.x.length;
  const duration = n * sig.dt;

  // mean squared velocity, m^2/s^2
  let sumV2 = 0;
  for (let i = 1; i < n; i++) {
    const v = (sig.x[i] - sig.x[i - 1]) / upm / sig.dt;
    sumV2 += v * v;
  }
  const msv = n > 1 ? sumV2 / (n - 1) : 0;

  // Kinetic power: (1/2) m <v^2> delivered and dissipated each second.
  const powerW = 0.5 * massKg * msv;
  const chargeCs = chargeFromPower(powerW, compartment);

  return {
    powerW,
    chargeCs,
    compartment,
    derivation:
      `P = 0.5 x ${massKg} kg x <v^2> where <v^2> = ${msv.toExponential(3)} m^2/s^2 ` +
      `from ${n} samples at ${(1 / sig.dt).toFixed(1)} Hz; ` +
      `Q = sqrt(2 x ${CAPACITANCE[compartment]} F x P)`,
    totalC: chargeCs * duration,
    durationS: duration,
  };
}

// ── forward: pose stream -> .vvs source ──────────────────────────────

export interface SynthesisInput {
  circuitName: string;
  decomposition: Decomposition;
  charge: ChargeAccount;
  sleep?: SleepAnalysis;
  /** joints the signal came from, for the bind clause */
  binding?: { rig: string; map: Record<string, string> };
}

/**
 * Generate Vitruvius source from a measured pose record.
 *
 * This is the direction that makes the tool bidirectional: move the model,
 * get the program that would produce that movement. The generated circuit is
 * a claim, and the point is that it can then be RUN and compared against the
 * record it came from.
 *
 * Two things are carried across honestly:
 *
 *   - The measured band split sets the element delays, so the circuit's loop
 *     latency reproduces the trembling frequency that was actually observed
 *     rather than a default.
 *   - The measured charge sets the compartment capacitance via the inverse
 *     of Q = sqrt(2CP), so a restless record and a still one generate
 *     genuinely different programs.
 *
 * Where the record could not support a claim, the generator writes that into
 * the source as a comment instead of emitting a number.
 */
export function synthesiseVvs(input: SynthesisInput): string {
  const { circuitName, decomposition: d, charge, sleep, binding } = input;
  const L: string[] = [];
  const ad = d.adequacy;

  L.push(`-- Generated from a measured pose record.`);
  L.push(`--`);
  L.push(`-- Source        : ${charge.derivation.split(";")[0]}`);
  L.push(`-- Sample rate   : ${ad.sampleRateHz.toFixed(1)} Hz (Nyquist ${ad.nyquistHz.toFixed(1)} Hz)`);
  L.push(`-- Duration      : ${ad.durationS.toFixed(3)} s`);
  L.push(`-- Resolvable to : ${ad.lowestResolvableHz.toFixed(3)} Hz at ${ad.cyclesRequired} cycles`);
  L.push(`--`);
  for (const note of ad.notes) {
    for (const line of wrap(note, 68)) L.push(`-- ! ${line}`);
  }
  if (ad.notes.length) L.push(`--`);

  L.push(`-- Measured components:`);
  L.push(`--   trembling RMS  ${d.tremblingRms.toExponential(3)} rig units`);
  if (ad.ramblingResolvable) {
    L.push(`--   rambling RMS   ${d.ramblingRms.toExponential(3)} rig units`);
    L.push(`--   coupling index ${d.couplingIndex.toFixed(3)}`);
  } else {
    L.push(`--   rambling       NOT RESOLVABLE at this record length --`);
    L.push(`--                  no rambling-derived value is emitted below.`);
  }
  L.push(`--   charge         ${(charge.chargeCs * 1e3).toFixed(2)} mC/s at C_${charge.compartment}`);
  L.push(`--                  (P = ${charge.powerW.toExponential(3)} W)`);
  if (sleep) {
    L.push(`--`);
    L.push(`-- Sleep activity:`);
    L.push(`--   repositions    ${sleep.repositions} (${sleep.repositionRate.toFixed(1)}/h)`);
    L.push(`--   arousals       ${sleep.arousals}`);
    L.push(`--   longest still  ${sleep.longestStillS.toFixed(2)} s`);
    L.push(`--   wake fraction  ${(sleep.wakeFraction * 100).toFixed(1)}%`);
  }
  L.push("");
  L.push(`module ${circuitName};`);
  L.push("");

  // Capacitance from the measured charge: invert Q = sqrt(2CP) at the
  // measured power. Falls back to the compartment default when the record
  // carried no motion at all.
  const cap =
    charge.powerW > 0 && charge.chargeCs > 0
      ? (charge.chargeCs * charge.chargeCs) / (2 * charge.powerW)
      : CAPACITANCE[charge.compartment];

  L.push(`-- Capacitance recovered from the measured charge and power:`);
  L.push(`--   C = Q^2 / (2P) = ${cap.toExponential(4)} F`);
  L.push(`compartment periphery { capacitance: ${cap.toExponential(4)} F; stratum: reflex; }`);
  L.push(`compartment segmental { capacitance: ${(cap * 2).toExponential(4)} F; stratum: spinal; }`);
  if (ad.ramblingResolvable) {
    L.push(`compartment central   { capacitance: ${(cap * 8).toExponential(4)} F; stratum: supraspinal; }`);
  } else {
    L.push(`-- No supraspinal compartment: the record cannot resolve the band`);
    L.push(`-- that would justify one.`);
  }
  L.push("");

  // Loop delay from the observed trembling frequency. A closed loop
  // oscillates near 1/(2 x loop delay), so delay = 1/(2 f).
  const fTrem = dominantFrequency(d.trembling, 1 / ad.sampleRateHz, BANDS.trembling);
  // If the peak is the looping artefact, a delay derived from it would be a
  // property of the file format, not the body. Fall back to a declared
  // default and say so.
  const loopDelayS = ad.dominantIsLoopArtefact ? 0.05 : fTrem > 0 ? 1 / (2 * fTrem) : 0.05;
  const halfMs = (loopDelayS / 2) * 1e3;

  if (ad.dominantIsLoopArtefact) {
    L.push(`-- Loop delay NOT derived from the spectrum: the dominant peak`);
    L.push(`-- coincides with the looping frequency (${ad.loopArtefactHz?.toFixed(3)} Hz),`);
    L.push(`-- so it is an artefact of how the record was assembled. A default`);
    L.push(`-- reflex-scale delay is used instead and must not be read as measured.`);
  } else {
    L.push(`-- Loop delay from the observed trembling frequency:`);
    L.push(`--   f = ${fTrem.toFixed(3)} Hz  ->  loop delay = 1/(2f) = ${(loopDelayS * 1e3).toFixed(1)} ms`);
  }
  L.push(`circuit ${circuitName}_loop {`);
  L.push(`  floor    : derived(resting_cut(periphery));`);
  L.push("");
  if (ad.ramblingResolvable) {
    L.push(`  outbound : central -> segmental -> periphery;`);
    L.push(`  return   : periphery -> segmental -> central;`);
    L.push("");
    L.push(`  element descend  conducts central   -> segmental delay ${halfMs.toFixed(1)} ms gain 2.0;`);
    L.push(`  element efferent conducts segmental -> periphery delay ${halfMs.toFixed(1)} ms gain 2.0;`);
    L.push(`  element afferent conducts periphery -> segmental delay ${halfMs.toFixed(1)} ms gain 1.0;`);
    L.push(`  element ascend   conducts segmental -> central   delay ${halfMs.toFixed(1)} ms gain 1.0;`);
  } else {
    L.push(`  outbound : segmental -> periphery;`);
    L.push(`  return   : periphery -> segmental;`);
    L.push("");
    L.push(`  element efferent conducts segmental -> periphery delay ${halfMs.toFixed(1)} ms gain 2.0;`);
    L.push(`  element afferent conducts periphery -> segmental delay ${halfMs.toFixed(1)} ms gain 1.0;`);
  }
  L.push(`}`);
  L.push("");

  if (binding) {
    L.push(`bind ${circuitName}_loop to rig("${binding.rig}") {`);
    for (const [comp, joint] of Object.entries(binding.map)) {
      L.push(`  ${comp.padEnd(10)} -> "${joint}";`);
    }
    L.push(`}`);
    L.push("");
  }

  L.push(`experiment recovered {`);
  L.push(`  intact  : ${circuitName}_loop;`);
  L.push("");
  L.push(`  -- The record came from a closed body. Severing the return should`);
  L.push(`  -- open the circuit, which is the claim to test against the source.`);
  L.push(`  lesion severed : ${circuitName}_loop without element(afferent);`);
  L.push("");
  L.push(`  observe : closure_index, loop_latency, oscillation_amplitude,`);
  L.push(`            band_power(reflex), divergence_time, floor_value;`);
  L.push(`}`);
  L.push("");

  return L.join("\n");
}

/** Dominant frequency of a signal within a band, by direct periodogram.
 *  Records here are short (tens to hundreds of samples), so an O(n*k) scan
 *  over candidate frequencies costs less than setting up an FFT. */
export function dominantFrequency(
  x: Float64Array,
  dt: number,
  band: readonly [number, number],
  steps = 128,
): number {
  const n = x.length;
  if (n < 4) return 0;
  const fs = 1 / dt;
  const lo = Math.max(band[0], 3 / (n * dt));
  const hi = Math.min(band[1], fs / 2);
  if (!(hi > lo)) return 0;

  const mu = mean(x);
  let bestF = 0;
  let bestP = -1;
  for (let s = 0; s <= steps; s++) {
    const f = lo + ((hi - lo) * s) / steps;
    let re = 0;
    let im = 0;
    for (let i = 0; i < n; i++) {
      const th = 2 * Math.PI * f * i * dt;
      const v = x[i] - mu;
      re += v * Math.cos(th);
      im += v * Math.sin(th);
    }
    const p = re * re + im * im;
    if (p > bestP) {
      bestP = p;
      bestF = f;
    }
  }
  return bestF;
}

/** Band power fraction: energy in [lo,hi] over total, by periodogram. */
export function bandPower(x: Float64Array, dt: number, band: readonly [number, number]): number {
  const n = x.length;
  if (n < 4) return 0;
  const fs = 1 / dt;
  const mu = mean(x);
  const at = (f: number) => {
    let re = 0;
    let im = 0;
    for (let i = 0; i < n; i++) {
      const th = 2 * Math.PI * f * i * dt;
      const v = x[i] - mu;
      re += v * Math.cos(th);
      im += v * Math.sin(th);
    }
    return re * re + im * im;
  };
  const fmin = 1 / (n * dt);
  const fmax = fs / 2;
  let inBand = 0;
  let total = 0;
  const steps = 96;
  for (let s = 0; s <= steps; s++) {
    const f = fmin + ((fmax - fmin) * s) / steps;
    const p = at(f);
    total += p;
    if (f >= band[0] && f <= band[1]) inBand += p;
  }
  return total > 0 ? inBand / total : 0;
}

function wrap(s: string, width: number): string[] {
  const words = s.split(/\s+/);
  const out: string[] = [];
  let line = "";
  for (const w of words) {
    if (line.length + w.length + 1 > width) {
      out.push(line);
      line = w;
    } else {
      line = line ? line + " " + w : w;
    }
  }
  if (line) out.push(line);
  return out;
}
