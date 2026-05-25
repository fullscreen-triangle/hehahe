/**
 * Per-player biomechanics from pose history.
 *
 * Inputs: a rolling history of (t, landmarks) for one tracked player.
 * Outputs: speed (m/s), stride length (m), cadence (steps/s), vertical
 * oscillation (cm), an order-of-magnitude ground-reaction-force
 * estimate (multiples of body weight).
 *
 * Anthropometric scale is taken from the continent-average profile so
 * that pixel-space landmark distances can be converted to metres via
 * the known segment lengths. This is rougher than a calibrated
 * homography but is the right thing when no pitch calibration is
 * available — the player's own body acts as the metric ruler.
 */

import { derivedFromProfile } from "./anthropometry";

// BlazePose landmark indices
const LM = {
  NOSE: 0,
  LSHOULDER: 11, RSHOULDER: 12,
  LHIP: 23, RHIP: 24,
  LKNEE: 25, RKNEE: 26,
  LANKLE: 27, RANKLE: 28,
  LHEEL: 29, RHEEL: 30,
  LFOOTIDX: 31, RFOOTIDX: 32,
};

const HISTORY_LEN = 32;       // ~2.5 s at 12 Hz detection rate

/** Per-player rolling state. Caller persists one per stable id. */
export class PlayerKinematics {
  constructor(profile) {
    this.history = [];        // [{t, landmarks, hipMid, ankleL, ankleR}]
    this.lastStrideTime = null;
    this.strides = [];
    this.profile = profile;
  }

  /** Update with a new frame; returns derived metrics. */
  update(t, landmarks) {
    if (!landmarks || landmarks.length < 33) return this._zero();
    const lh = landmarks[LM.LHIP], rh = landmarks[LM.RHIP];
    if (!lh || !rh) return this._zero();
    const hipMid = {
      x: (lh.x + rh.x) * 0.5,
      y: (lh.y + rh.y) * 0.5,
    };
    const la = landmarks[LM.LANKLE], ra = landmarks[LM.RANKLE];
    const ankleL = la ? { x: la.x, y: la.y, v: la.visibility ?? 1 } : null;
    const ankleR = ra ? { x: ra.x, y: ra.y, v: ra.visibility ?? 1 } : null;

    this.history.push({ t, landmarks, hipMid, ankleL, ankleR });
    while (this.history.length > HISTORY_LEN) this.history.shift();

    return this._compute();
  }

  _zero() {
    return {
      speedMps: 0, strideM: 0, cadenceHz: 0,
      verticalOscCm: 0, grfBW: 0,
      pxPerMetre: null, valid: false,
    };
  }

  _compute() {
    const h = this.history;
    if (h.length < 4) return this._zero();
    const derived = derivedFromProfile(this.profile);

    // 1. Pixel-to-metre scale from anthropometric leg length.
    const pxPerMetre = this._pxPerMetre(derived.legLengthM);
    if (!pxPerMetre) return this._zero();

    // 2. Horizontal speed: hip x-velocity over the most recent ~0.5 s.
    const last = h[h.length - 1];
    const target = last.t - 0.5;
    let earliest = h[0];
    for (const e of h) { if (e.t >= target) { earliest = e; break; } }
    const dt = Math.max(1e-3, last.t - earliest.t);
    const dxNorm = last.hipMid.x - earliest.hipMid.x;
    // hip positions are image-normalised in [0,1]; convert to metres via
    // pixel-equivalent then divide by px/m. We do not know image
    // resolution here, so we treat the normalised coords as fraction-of-frame
    // and scale by the typical (height of person in normalised coords) ↔ height
    // anthropometric mapping below.
    const dxM = dxNorm / pxPerMetre;
    const speedMps = Math.abs(dxM) / dt;

    // 3. Vertical oscillation: peak-to-peak of hip y over the window
    //    converted via the same scale (y is image-normalised so we
    //    multiply by frame-height fraction → metres via the same scale).
    let ymin = Infinity, ymax = -Infinity;
    for (const e of h) {
      if (e.hipMid.y < ymin) ymin = e.hipMid.y;
      if (e.hipMid.y > ymax) ymax = e.hipMid.y;
    }
    const verticalOscCm = ((ymax - ymin) / pxPerMetre) * 100;

    // 4. Stride: detect foot strikes via local minima of ankle y
    //    (lowest point in image space = ground contact). Time between
    //    successive same-foot strikes × horizontal speed = stride length.
    const ankleSeries = h
      .filter((e) => e.ankleR && e.ankleR.v > 0.4)
      .map((e) => ({ t: e.t, y: e.ankleR.y }));
    let strideSeconds = null;
    if (ankleSeries.length >= 6) {
      const strikes = findLocalMaxima(ankleSeries.map((e) => e.y));
      if (strikes.length >= 2) {
        const a = ankleSeries[strikes[strikes.length - 2]].t;
        const b = ankleSeries[strikes[strikes.length - 1]].t;
        strideSeconds = b - a;
      }
    }
    const strideM = strideSeconds ? speedMps * strideSeconds : 0;
    const cadenceHz = strideSeconds ? 1 / strideSeconds : 0;

    // 5. Vertical GRF (order-of-magnitude): peak vertical acceleration
    //    of the hip during the stride times body mass, expressed in
    //    body weights. We compute hip-y double derivative across the
    //    window and take the peak.
    let peakAccel = 0;
    if (h.length >= 5) {
      for (let i = 2; i < h.length; i++) {
        const dt1 = Math.max(1e-3, h[i].t - h[i - 1].t);
        const dt2 = Math.max(1e-3, h[i - 1].t - h[i - 2].t);
        const v1 = (h[i].hipMid.y - h[i - 1].hipMid.y) / dt1;
        const v0 = (h[i - 1].hipMid.y - h[i - 2].hipMid.y) / dt2;
        const a = Math.abs((v1 - v0) / dt1) / pxPerMetre;   // m/s²
        if (a > peakAccel) peakAccel = a;
      }
    }
    // Vertical GRF in body weights = (g + a_peak)/g, image y is downward
    // so accel sign is ambiguous; use magnitude only.
    const grfBW = 1 + peakAccel / 9.81;

    return {
      speedMps, strideM, cadenceHz, verticalOscCm,
      grfBW, pxPerMetre, valid: true,
    };
  }

  /**
   * Estimate pixels-per-metre using the player's apparent leg length
   * in normalised image coords against the anthropometric truth.
   * Returns null if landmarks are too partial.
   */
  _pxPerMetre(legLengthM) {
    const h = this.history;
    if (h.length === 0) return null;
    const last = h[h.length - 1];
    const lm = last.landmarks;
    const lh = lm[LM.LHIP], la = lm[LM.LANKLE];
    const rh = lm[LM.RHIP], ra = lm[LM.RANKLE];
    const samples = [];
    if (lh && la && lh.visibility > 0.4 && la.visibility > 0.4) {
      samples.push(Math.hypot(lh.x - la.x, lh.y - la.y));
    }
    if (rh && ra && rh.visibility > 0.4 && ra.visibility > 0.4) {
      samples.push(Math.hypot(rh.x - ra.x, rh.y - ra.y));
    }
    if (samples.length === 0) return null;
    const meanLegNorm = samples.reduce((a, b) => a + b, 0) / samples.length;
    if (meanLegNorm < 1e-4) return null;
    return meanLegNorm / legLengthM;       // (normalised-units / metre)
  }
}

/** Indices of local maxima in a 1-D array (used for ground-strike detection). */
function findLocalMaxima(xs) {
  const out = [];
  for (let i = 1; i < xs.length - 1; i++) {
    if (xs[i] > xs[i - 1] && xs[i] >= xs[i + 1]) out.push(i);
  }
  return out;
}
