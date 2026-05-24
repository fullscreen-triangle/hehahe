/**
 * Attention-focus solver — JS port of the Python reference in
 * publications/football-observation-operator/tracker/attention_focus.py.
 *
 * Each player contributes an attention ray Lᵢ = {pᵢ + t·fᵢ : t ≥ 0}.
 * The estimated ball/focus point is the weighted least-squares
 * minimiser of perpendicular distance to all rays:
 *
 *     b* = argmin_b  Σᵢ wᵢ · ||(I − fᵢfᵢᵀ)(b − pᵢ)||²
 *
 * Closed-form 2×2 solve, optional IRLS Huber wrapper, in-front-of-
 * player gate. The shader version splats each ray into an accumulator
 * texture and reads the peak; this JS version is the CPU oracle and
 * the small-N fallback (≤ 22 players is trivially fast on CPU).
 */

const RIDGE = 1e-3;

function unit(v) {
  const n = Math.hypot(v[0], v[1]);
  return n < 1e-9 ? [1, 0] : [v[0] / n, v[1] / n];
}

/**
 * Weighted least-squares attention-focus solve.
 *
 * @param {Array<{position:[number,number], facing:[number,number], weight:number}>} rays
 * @returns {{point:[number,number], confidence:number, residualRms:number, nEff:number}}
 */
export function solveFocusPoint(rays) {
  // Normal-equations Σwᵢ Mᵢ b = Σwᵢ Mᵢ pᵢ with Mᵢ = I − fᵢ fᵢᵀ.
  let A00 = RIDGE, A01 = 0, A11 = RIDGE;
  let r0 = 0, r1 = 0;
  let nEff = 0;
  for (const ray of rays) {
    if (ray.weight <= 0) continue;
    const f = unit(ray.facing);
    const w = ray.weight;
    // M = I − f fᵀ
    const m00 = 1 - f[0] * f[0];
    const m01 = -f[0] * f[1];
    const m11 = 1 - f[1] * f[1];
    A00 += w * m00;
    A01 += w * m01;
    A11 += w * m11;
    // Mᵢ pᵢ
    const p0 = ray.position[0], p1 = ray.position[1];
    const mp0 = m00 * p0 + m01 * p1;
    const mp1 = m01 * p0 + m11 * p1;
    r0 += w * mp0;
    r1 += w * mp1;
    nEff++;
  }
  // 2×2 inverse
  const det = A00 * A11 - A01 * A01;
  if (Math.abs(det) < 1e-12 || nEff === 0) {
    return { point: [0, 0], confidence: 0, residualRms: Infinity, nEff: 0 };
  }
  const invDet = 1 / det;
  const b0 = invDet * (A11 * r0 - A01 * r1);
  const b1 = invDet * (-A01 * r0 + A00 * r1);

  // Residual RMS
  let sq = 0;
  let n = 0;
  for (const ray of rays) {
    if (ray.weight <= 0) continue;
    const f = unit(ray.facing);
    const dx = b0 - ray.position[0];
    const dy = b1 - ray.position[1];
    const dot = dx * f[0] + dy * f[1];
    const perpX = dx - dot * f[0];
    const perpY = dy - dot * f[1];
    sq += perpX * perpX + perpY * perpY;
    n++;
  }
  const residualRms = n > 0 ? Math.sqrt(sq / n) : 0;
  const confidence = Math.exp(-((residualRms / 4) ** 2));
  return { point: [b0, b1], confidence, residualRms, nEff };
}

/**
 * Robust IRLS focus solve. Huber re-weighting suppresses off-ball
 * runners; in-front-of-player gate zeroes rays facing away from the
 * current estimate.
 */
export function robustFocusPoint(rays, opts = {}) {
  const maxIter = opts.maxIter ?? 6;
  const huberK = opts.huberK ?? 3.0;
  const dropBehind = opts.dropBehindPlayer ?? true;

  if (!rays.length) return { point: [0, 0], confidence: 0, residualRms: Infinity, nEff: 0 };

  // Working copy with mutable weights
  const work = rays.map((r) => ({
    position: [r.position[0], r.position[1]],
    facing: unit(r.facing),
    weight: r.weight ?? 1,
  }));

  let prev = null;
  let estimate = solveFocusPoint(work);
  for (let it = 0; it < maxIter; it++) {
    const b = estimate.point;
    if (prev && Math.hypot(b[0] - prev[0], b[1] - prev[1]) < 1e-4) break;
    prev = b;
    for (const ray of work) {
      const dx = b[0] - ray.position[0];
      const dy = b[1] - ray.position[1];
      const dot = dx * ray.facing[0] + dy * ray.facing[1];
      if (dropBehind && dot <= 0) {
        ray.weight = 0;
        continue;
      }
      const perpX = dx - dot * ray.facing[0];
      const perpY = dy - dot * ray.facing[1];
      const dist = Math.hypot(perpX, perpY);
      const huber = dist <= huberK ? 1 : huberK / dist;
      ray.weight = (ray.weight > 0 ? ray.weight : 1e-9) * huber;
    }
    estimate = solveFocusPoint(work);
  }
  return estimate;
}

/**
 * Per-pixel attention density (product of Gaussian factors on the
 * angle to each ray). Used by both the JS reference renderer and as
 * the formula the shader implements per fragment.
 */
export function attentionDensityAt(query, rays, sigmaAngleRad = 0.30) {
  let logP = 0;
  let n = 0;
  for (const ray of rays) {
    if (ray.weight <= 0) continue;
    const dx = query[0] - ray.position[0];
    const dy = query[1] - ray.position[1];
    const norm = Math.hypot(dx, dy);
    if (norm < 1e-6) continue;
    const f = unit(ray.facing);
    const cosTheta = (dx * f[0] + dy * f[1]) / norm;
    if (cosTheta <= 0) return 0;
    const theta = Math.acos(Math.max(-1, Math.min(1, cosTheta)));
    logP += -0.5 * ((theta / sigmaAngleRad) ** 2) * ray.weight;
    n++;
  }
  return n > 0 ? Math.exp(logP) : 0;
}
