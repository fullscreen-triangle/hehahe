/**
 * Synthetic football scene for the front-end tool.
 *
 * 22 players (2 teams × 11) on a regulation pitch (105 × 68 m). A
 * "true" ball trajectory drives each player's torso facing direction
 * with a small per-player reaction lag and angular noise — exactly
 * mirrors the Python MockDetector in
 * publications/football-observation-operator/tracker/detector.py
 * but in JS for browser use.
 *
 * The scene exposes a `step(dt)` method that advances all dynamics
 * one frame and returns the current detection set + ground-truth ball
 * position. The front-end tool feeds this into the attention-focus
 * solver and into the WebGL2 shader.
 */

// Pitch dimensions (FIFA Laws of the Game, midpoint values).
export const PITCH_X = 105.0; // metres, goal-to-goal
export const PITCH_Y = 68.0;  // metres, touchline-to-touchline

const TWO_PI = Math.PI * 2;

function rand(rng) {
  return rng();
}

function randn(rng) {
  // Box-Muller
  let u = 0, v = 0;
  while (u === 0) u = rng();
  while (v === 0) v = rng();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(TWO_PI * v);
}

function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a = (a + 0x6D2B79F5) | 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// 4-3-3 formation, attacking from left to right.
const FORMATION_HOME = [
  [-48, 0],                            // GK
  [-32, -22], [-32, -8], [-32, 8], [-32, 22],   // back four
  [-14, -14], [-14, 0], [-14, 14],             // midfield three
  [4, -22], [4, 22],                            // wingers
  [10, 0],                                      // striker
];

function buildPlayers(rng) {
  const players = [];
  for (let team = 0; team < 2; team++) {
    const sign = team === 0 ? 1 : -1;
    FORMATION_HOME.forEach(([x, y], i) => {
      players.push({
        id: team * 11 + i,
        team,
        role: i === 0 ? 'keeper' : 'field',
        position: [sign * x, sign * y],
        velocity: [0, 0],
        facing: [sign, 0],
        reactionLag: 0.18 + 0.08 * randn(rng),
        facingNoiseRad: 0.06,
        baseSpeed: 6.0,
        // History of (t, ballPos) used to interpolate the reaction-lagged
        // facing target.
        _history: [],
      });
    });
  }
  return players;
}

/** Default ball trajectory: a long passing build-up that sweeps the
 * pitch laterally and forward. Returns ball position in metres. */
export function defaultBallTrajectory(t) {
  const phase = (t * 0.18) % 1.0;
  // Crude scripted route: from the home defensive third to the
  // attacking third over ~30 seconds, with lateral oscillation.
  const xLin = -40 + 80 * Math.min(1.0, phase * 1.4);
  const yOsc = 18 * Math.sin(t * 0.42);
  return [xLin, yOsc];
}

export class SyntheticScene {
  constructor(opts = {}) {
    this.rng = mulberry32(opts.seed ?? 42);
    this.players = buildPlayers(this.rng);
    this.t = 0;
    this.ballFn = opts.ballTrajectory ?? defaultBallTrajectory;
    this.positionNoiseM = opts.positionNoiseM ?? 0.15;
    this.facingNoiseRad = opts.facingNoiseRad ?? 0.04;
  }

  reset() {
    this.t = 0;
    this.players = buildPlayers(this.rng);
  }

  /** Advance one frame; return current detections + ground-truth ball. */
  step(dt) {
    this.t += dt;
    const ball = this.ballFn(this.t);

    for (const p of this.players) {
      // Move toward the ball at base speed (field players); keepers
      // creep toward the ball more slowly; runner roles would chase
      // the goal but we omit them for the synthetic demo.
      const target = ball;
      const dx = target[0] - p.position[0];
      const dy = target[1] - p.position[1];
      const dn = Math.hypot(dx, dy);
      if (dn > 1e-3) {
        const speed = p.role === 'keeper' ? 1.5 : p.baseSpeed;
        const ux = dx / dn;
        const uy = dy / dn;
        p.velocity = [ux * speed, uy * speed];
        p.position[0] += ux * speed * dt;
        p.position[1] += uy * speed * dt;
      }
      // Clamp to pitch
      p.position[0] = Math.max(-PITCH_X / 2, Math.min(PITCH_X / 2, p.position[0]));
      p.position[1] = Math.max(-PITCH_Y / 2, Math.min(PITCH_Y / 2, p.position[1]));

      // Record reaction-lagged ball position for facing target.
      p._history.push([this.t, [ball[0], ball[1]]]);
      const keepFrom = this.t - Math.max(p.reactionLag, 0) * 1.5 - 0.5;
      while (p._history.length > 0 && p._history[0][0] < keepFrom) {
        p._history.shift();
      }
      const target_t = Math.max(0, this.t - p.reactionLag);
      let best = p._history[0] ?? [this.t, ball];
      for (const e of p._history) {
        if (e[0] <= target_t) best = e;
        else break;
      }
      const targetBall = best[1];
      const fdx = targetBall[0] - p.position[0];
      const fdy = targetBall[1] - p.position[1];
      const fn = Math.hypot(fdx, fdy);
      let facing;
      if (fn < 1e-6) {
        facing = p.facing;
      } else {
        // Add per-player facing noise
        const theta = p.facingNoiseRad * randn(this.rng);
        const c = Math.cos(theta), s = Math.sin(theta);
        const fx = fdx / fn;
        const fy = fdy / fn;
        facing = [c * fx - s * fy, s * fx + c * fy];
      }
      p.facing = facing;
    }

    // Build the detection list (positions + facings with detector
    // noise applied, NOT touching the ground-truth player.position).
    const detections = this.players.map((p) => {
      const noiseX = this.positionNoiseM * randn(this.rng);
      const noiseY = this.positionNoiseM * randn(this.rng);
      const theta = this.facingNoiseRad * randn(this.rng);
      const c = Math.cos(theta), s = Math.sin(theta);
      const facing = [
        c * p.facing[0] - s * p.facing[1],
        s * p.facing[0] + c * p.facing[1],
      ];
      return {
        id: p.id,
        team: p.team,
        role: p.role,
        position: [p.position[0] + noiseX, p.position[1] + noiseY],
        facing,
        weight: p.role === 'keeper' ? 0.6 : 1.0,
      };
    });

    return { ball, detections, t: this.t };
  }
}
