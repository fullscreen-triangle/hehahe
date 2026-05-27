/**
 * Context-dependent coordinate field for image-plane pixel pairs.
 *
 * Implements the per-frame scale-field approach of
 * `publications/sources/context-dependent-coordinates.tex`:
 *
 *   α(u,v) = local pixel-to-metre scale (image-norm / metre).
 *
 * Each detected player carries an anatomical anchor — their own
 * apparent leg-length in image-normalised units against the
 * continent-average leg length in metres — giving one observation of
 * α at the player's hip position. The field at an arbitrary query
 * point is interpolated from the nearest anchors (inverse-distance
 * weighted), with a confidence that falls off when no anchor is
 * within a reasonable image-norm radius.
 *
 * The world distance between two query points is then the line
 * integral of α along the pixel path between them. For most football
 * uses the trapezoidal-rule approximation
 *
 *   d_world ≈ ½(α(p₁) + α(p₂)) · ||p₁ − p₂||_px
 *
 * is enough. For long lines that cross strong perspective gradients
 * (e.g. one player on the near touchline, one on the far touchline)
 * we sample α at a handful of intermediate points and Simpson's-rule
 * integrate.
 *
 * No camera calibration, no homography, no field-line detection
 * required — the only external prior is the continent-average leg
 * length supplied by `anthropometry.js`.
 */

/**
 * Anchors are {position:[u,v] in 0..1 image-norm, pxPerMetre} pairs.
 * The "pxPerMetre" carried in by biomechanics.js is in image-norm
 * units per real metre, so a value of 0.18 means 0.18 of the frame's
 * shorter dimension equals 1 m at that player's depth.
 */
export class ContextScaleField {
  constructor(opts = {}) {
    this.idwPower = opts.idwPower ?? 2.0;       // 1/d^p weighting
    this.minWeightSum = opts.minWeightSum ?? 1e-3;
    this.fallbackAlpha = opts.fallbackAlpha ?? null;
    this.maxRadius = opts.maxRadius ?? 0.8;     // ignore anchors farther than this
    this.anchors = [];
  }

  /** Replace the anchor set for the current frame. */
  setAnchors(anchors) {
    this.anchors = (anchors || [])
      .filter((a) => a && a.position
              && Number.isFinite(a.pxPerMetre) && a.pxPerMetre > 0)
      .map((a) => ({
        position: [a.position[0], a.position[1]],
        pxPerMetre: a.pxPerMetre,
        weight: a.weight ?? 1,
      }));
  }

  /**
   * Evaluate α at a query image-norm point.
   * Returns { alpha, confidence } with confidence ∈ [0, 1].
   */
  alphaAt(query) {
    if (!query) return { alpha: this._fallback(), confidence: 0 };
    if (this.anchors.length === 0) {
      return { alpha: this._fallback(), confidence: 0 };
    }
    let weightSum = 0;
    let alphaSum = 0;
    let nearest = Infinity;
    for (const a of this.anchors) {
      const dx = query[0] - a.position[0];
      const dy = query[1] - a.position[1];
      const d = Math.hypot(dx, dy);
      if (d > this.maxRadius) continue;
      if (d < nearest) nearest = d;
      const w = a.weight / Math.pow(Math.max(d, 1e-3), this.idwPower);
      weightSum += w;
      alphaSum += w * a.pxPerMetre;
    }
    if (weightSum < this.minWeightSum) {
      return { alpha: this._fallback(), confidence: 0 };
    }
    const alpha = alphaSum / weightSum;
    const confidence = Math.max(0, Math.min(1, 1 - nearest / this.maxRadius));
    return { alpha, confidence };
  }

  /**
   * Line-integral world distance between two image-norm points.
   * Uses N+1 samples along the line; N defaults to 4 (enough for the
   * trapezoidal rule to cover football-frame perspective gradients).
   */
  worldDistance(p1, p2, N = 4) {
    if (!p1 || !p2) return null;
    if (this.anchors.length === 0) return null;
    const samples = [];
    for (let i = 0; i <= N; i++) {
      const t = i / N;
      const x = p1[0] * (1 - t) + p2[0] * t;
      const y = p1[1] * (1 - t) + p2[1] * t;
      const { alpha } = this.alphaAt([x, y]);
      samples.push(alpha);
    }
    // Simpson's rule if N is even, else trapezoid.
    const dx = p2[0] - p1[0];
    const dy = p2[1] - p1[1];
    const arcPx = Math.hypot(dx, dy);
    if (arcPx < 1e-6) return 0;
    const meanInvAlpha = simpsonOrTrap(samples.map((a) => 1 / Math.max(a, 1e-6)));
    return arcPx * meanInvAlpha;
  }

  /**
   * Convert an image-norm length at a single point to metres. Use
   * this when you don't have two distinct endpoints — e.g. taking a
   * ball-speed magnitude in image-norm/s and turning it into m/s.
   */
  lengthAt(query, lengthNorm) {
    const { alpha } = this.alphaAt(query);
    if (!alpha || alpha < 1e-6) return null;
    return lengthNorm / alpha;
  }

  /**
   * Median anchor α — useful as a fallback "global" scale when the
   * query falls outside all anchors' influence radius.
   */
  medianAlpha() {
    if (this.anchors.length === 0) return null;
    const sorted = this.anchors.map((a) => a.pxPerMetre).sort((a, b) => a - b);
    return sorted[Math.floor(sorted.length / 2)];
  }

  _fallback() {
    if (this.fallbackAlpha) return this.fallbackAlpha;
    return this.medianAlpha() ?? null;
  }
}

/** Simpson's 1/3 rule (even N) or trapezoid (odd N) over equispaced
 *  samples; returns the *mean* value (integral / range), suitable for
 *  multiplying by a chord length. */
function simpsonOrTrap(samples) {
  const n = samples.length;
  if (n < 2) return samples[0] ?? 0;
  if (n % 2 === 1 && n >= 3) {
    // Simpson's 1/3 over n-1 intervals (n must be odd for samples).
    let s = samples[0] + samples[n - 1];
    for (let i = 1; i < n - 1; i++) {
      s += (i % 2 === 1 ? 4 : 2) * samples[i];
    }
    return s / (3 * (n - 1));
  }
  // Trapezoid mean.
  let s = (samples[0] + samples[n - 1]) * 0.5;
  for (let i = 1; i < n - 1; i++) s += samples[i];
  return s / (n - 1);
}
