/**
 * Ball metrics derived from the attention-focus trajectory.
 *
 * The focus point is the framework's inferred ball position. Its
 * trajectory carries:
 *   - speed             — finite-difference velocity magnitude
 *   - acceleration      — second-derivative magnitude
 *   - flightFraction    — fraction of recent samples in flight
 *                         (defined as focus speed above a threshold
 *                          while no player is within possession radius)
 *   - curvature         — instantaneous turning angle per metre
 *                         (proxy for ball curve / swerve)
 *   - lastFlightMs      — duration of the most recent flight segment
 *
 * No homography required; metrics are computed in whatever coordinate
 * system the focus is expressed in. If `pxPerMetre` is supplied,
 * outputs are converted to metres/SI; otherwise the units are
 * normalised-image-units.
 */

const HISTORY_LEN = 60;        // ~5 s at 12 Hz

export class BallTrajectory {
  constructor() {
    this.history = [];          // [{t, x, y}]
    this.flightState = false;
    this.lastFlightStart = null;
    this.lastFlightDurationMs = 0;
  }

  reset() {
    this.history = [];
    this.flightState = false;
    this.lastFlightStart = null;
    this.lastFlightDurationMs = 0;
  }

  /**
   * Push a new focus sample.
   * @param {number} t          seconds (e.g. performance.now()/1000)
   * @param {[number,number]} focus
   * @param {boolean} possessed whether any player is in possession
   */
  update(t, focus, possessed) {
    this.history.push({ t, x: focus[0], y: focus[1] });
    while (this.history.length > HISTORY_LEN) this.history.shift();

    const speed = this._currentSpeed();
    const inFlight = !possessed && speed > 0.04;
    if (inFlight && !this.flightState) {
      this.lastFlightStart = t;
      this.flightState = true;
    } else if (!inFlight && this.flightState && this.lastFlightStart != null) {
      this.lastFlightDurationMs = (t - this.lastFlightStart) * 1000;
      this.flightState = false;
    }
  }

  _currentSpeed() {
    if (this.history.length < 2) return 0;
    const last = this.history[this.history.length - 1];
    const prev = this.history[Math.max(0, this.history.length - 4)];
    const dt = Math.max(1e-3, last.t - prev.t);
    return Math.hypot(last.x - prev.x, last.y - prev.y) / dt;
  }

  /** Compute the metric snapshot.
   * @param {{pxPerMetre:number|null}} ctx — optional metric scale.
   */
  snapshot(ctx = {}) {
    const pxPerMetre = ctx.pxPerMetre ?? null;
    const speed = this._currentSpeed();

    // Acceleration: 2nd central difference of recent samples.
    let accel = 0;
    if (this.history.length >= 5) {
      const n = this.history.length;
      const a = this.history[n - 5];
      const b = this.history[n - 3];
      const c = this.history[n - 1];
      const dt1 = Math.max(1e-3, b.t - a.t);
      const dt2 = Math.max(1e-3, c.t - b.t);
      const vx1 = (b.x - a.x) / dt1, vy1 = (b.y - a.y) / dt1;
      const vx2 = (c.x - b.x) / dt2, vy2 = (c.y - b.y) / dt2;
      const dtA = Math.max(1e-3, c.t - a.t);
      accel = Math.hypot(vx2 - vx1, vy2 - vy1) / dtA;
    }

    // Curvature: angular change between successive velocity vectors,
    // divided by arc length.
    let curvature = 0;
    if (this.history.length >= 4) {
      const n = this.history.length;
      const a = this.history[n - 4];
      const b = this.history[n - 2];
      const c = this.history[n - 1];
      const ax = b.x - a.x, ay = b.y - a.y;
      const bx = c.x - b.x, by = c.y - b.y;
      const na = Math.hypot(ax, ay), nb = Math.hypot(bx, by);
      if (na > 1e-6 && nb > 1e-6) {
        const cosA = (ax * bx + ay * by) / (na * nb);
        const angle = Math.acos(Math.max(-1, Math.min(1, cosA)));
        const arc = (na + nb) * 0.5;
        curvature = arc > 1e-6 ? angle / arc : 0;
      }
    }

    // Flight fraction over the recent window.
    const recent = this.history.slice(-24);
    const inFlightHere = (i) => {
      if (i < 2) return false;
      const dt = Math.max(1e-3, recent[i].t - recent[i - 1].t);
      const v = Math.hypot(
        recent[i].x - recent[i - 1].x,
        recent[i].y - recent[i - 1].y) / dt;
      return v > 0.04;
    };
    let nFlight = 0;
    for (let i = 0; i < recent.length; i++) if (inFlightHere(i)) nFlight++;
    const flightFraction = recent.length > 0 ? nFlight / recent.length : 0;

    // Unit conversions if scale available.
    const scaleSpeed = pxPerMetre ? 1 / pxPerMetre : 1;
    const scaleAccel = pxPerMetre ? 1 / pxPerMetre : 1;
    const scaleCurv  = pxPerMetre ? pxPerMetre : 1;

    return {
      speed_units_per_s: speed,
      speed_mps: pxPerMetre ? speed * scaleSpeed : null,
      accel_units_per_s2: accel,
      accel_mps2: pxPerMetre ? accel * scaleAccel : null,
      curvature_per_unit: curvature,
      curvature_per_m: pxPerMetre ? curvature * scaleCurv : null,
      flightFraction,
      lastFlightMs: this.lastFlightDurationMs,
      inFlightNow: this.flightState,
    };
  }
}
