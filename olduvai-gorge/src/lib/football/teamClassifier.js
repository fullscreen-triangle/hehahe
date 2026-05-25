/**
 * Two-team classifier from jersey colour.
 *
 * For each detected player the caller samples the dominant RGB colour
 * in their torso bounding box. We cluster those colours into two
 * groups via online K-means in HSV (hue + saturation), with temporal
 * stabilisation so a player's team assignment doesn't flicker between
 * frames.
 *
 * Goalkeepers and referees often wear distinct colours; v1 just lumps
 * everyone into 2 clusters and accepts a small misclassification rate.
 * The role-binding layer (see paper §5) will reassign them later.
 */

const SMOOTHING = 0.05;       // online K-means learning rate
const HISTORY_LEN = 12;       // temporal majority vote depth
const MIN_SAT_FOR_CLUSTERING = 0.08;  // skip near-grey samples

// Convert RGB (0..255) → HSV (h in [0,360), s, v in [0,1]).
export function rgbToHsv(r, g, b) {
  const rn = r / 255, gn = g / 255, bn = b / 255;
  const max = Math.max(rn, gn, bn);
  const min = Math.min(rn, gn, bn);
  const v = max;
  const d = max - min;
  const s = max === 0 ? 0 : d / max;
  let h;
  if (d === 0) h = 0;
  else if (max === rn) h = ((gn - bn) / d) % 6;
  else if (max === gn) h = (bn - rn) / d + 2;
  else h = (rn - gn) / d + 4;
  h = (h * 60 + 360) % 360;
  return [h, s, v];
}

export function hsvToRgb(h, s, v) {
  const c = v * s;
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
  const m = v - c;
  let rp, gp, bp;
  if (h < 60)       [rp, gp, bp] = [c, x, 0];
  else if (h < 120) [rp, gp, bp] = [x, c, 0];
  else if (h < 180) [rp, gp, bp] = [0, c, x];
  else if (h < 240) [rp, gp, bp] = [0, x, c];
  else if (h < 300) [rp, gp, bp] = [x, 0, c];
  else              [rp, gp, bp] = [c, 0, x];
  return [
    Math.round((rp + m) * 255),
    Math.round((gp + m) * 255),
    Math.round((bp + m) * 255),
  ];
}

// Hue distance with wraparound on a circle.
function hueDist(h1, h2) {
  const d = Math.abs(h1 - h2);
  return Math.min(d, 360 - d);
}

/**
 * Read the dominant colour of the torso area in a frame.
 *
 * @param {CanvasRenderingContext2D} ctx
 * @param {Object} bbox  — {xmin, ymin, xmax, ymax} in pixel coords
 * @returns {[number, number, number] | null}  — mean RGB or null
 */
export function sampleTorsoColor(ctx, bbox) {
  const cx = (bbox.xmin + bbox.xmax) * 0.5;
  // Torso vertically sits roughly at 25%-55% from the top of the bbox.
  const yTop = bbox.ymin + 0.25 * (bbox.ymax - bbox.ymin);
  const yBot = bbox.ymin + 0.55 * (bbox.ymax - bbox.ymin);
  const w = Math.max(2, Math.floor((bbox.xmax - bbox.xmin) * 0.35));
  const h = Math.max(2, Math.floor(yBot - yTop));
  const x = Math.max(0, Math.floor(cx - w / 2));
  const y = Math.max(0, Math.floor(yTop));
  try {
    const img = ctx.getImageData(x, y, w, h);
    let r = 0, g = 0, b = 0, n = 0;
    for (let i = 0; i < img.data.length; i += 4) {
      r += img.data[i];
      g += img.data[i + 1];
      b += img.data[i + 2];
      n++;
    }
    if (n === 0) return null;
    return [r / n, g / n, b / n];
  } catch {
    return null;
  }
}

/** Stateful two-team classifier. Persist one instance per session. */
export class TeamClassifier {
  constructor() {
    // Two cluster centroids in (hue, sat); initialised lazily.
    this.centroids = null;     // [[h0, s0], [h1, s1]]
    this.history = new Map();  // playerId → recent team assignments
    this.frameCount = 0;
  }

  reset() {
    this.centroids = null;
    this.history.clear();
    this.frameCount = 0;
  }

  /**
   * Assign a team (0 or 1) to a player given a colour sample.
   * Returns null if the sample is unusable.
   */
  classify(playerId, rgb) {
    if (!rgb) return this._historicalAssignment(playerId);
    const [h, s] = rgbToHsv(rgb[0], rgb[1], rgb[2]);
    if (s < MIN_SAT_FOR_CLUSTERING) {
      return this._historicalAssignment(playerId);
    }
    this._updateCentroids(h, s);
    const d0 = hueDist(h, this.centroids[0][0]) + 50 * Math.abs(s - this.centroids[0][1]);
    const d1 = hueDist(h, this.centroids[1][0]) + 50 * Math.abs(s - this.centroids[1][1]);
    const team = d0 < d1 ? 0 : 1;

    // Temporal majority vote.
    const hist = this.history.get(playerId) ?? [];
    hist.push(team);
    while (hist.length > HISTORY_LEN) hist.shift();
    this.history.set(playerId, hist);
    const c0 = hist.filter((t) => t === 0).length;
    const stable = c0 >= hist.length - c0 ? 0 : 1;
    return stable;
  }

  _historicalAssignment(playerId) {
    const hist = this.history.get(playerId);
    if (!hist || hist.length === 0) return null;
    const c0 = hist.filter((t) => t === 0).length;
    return c0 >= hist.length - c0 ? 0 : 1;
  }

  _updateCentroids(h, s) {
    if (!this.centroids) {
      // Bootstrap by placing the two centroids opposite on the hue
      // wheel; subsequent samples will refine them quickly.
      this.centroids = [
        [h, s],
        [(h + 180) % 360, s],
      ];
      return;
    }
    const d0 = hueDist(h, this.centroids[0][0]);
    const d1 = hueDist(h, this.centroids[1][0]);
    const k = d0 < d1 ? 0 : 1;
    const c = this.centroids[k];
    // Hue update with wraparound.
    const dh = ((h - c[0] + 540) % 360) - 180;
    c[0] = (c[0] + SMOOTHING * dh + 360) % 360;
    c[1] = c[1] + SMOOTHING * (s - c[1]);
  }

  /** Approximate display colour for each cluster. */
  teamColors() {
    if (!this.centroids) return ["#58E6D9", "#F0A830"];
    return this.centroids.map(([h, s]) => {
      const rgb = hsvToRgb(h, Math.max(0.45, s), 0.9);
      return `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
    });
  }
}
