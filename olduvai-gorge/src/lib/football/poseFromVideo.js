/**
 * Runtime loader for MediaPipe Tasks Vision pose detection, plus
 * helpers to extract a torso facing vector from a BlazePose result.
 *
 * Loaded from CDN at runtime via webpack-ignored dynamic import so the
 * Next.js build does not pull in the WASM bundle. This keeps the
 * deployed website small; the user only pays the model-download cost
 * when they actually open the video tool.
 *
 * The torso facing vector is computed from world-coordinate landmarks
 * (shoulders + hips) via the cross-product
 *     forward = up × left
 * where up = shoulder_mid → hip_mid (inverted because MediaPipe y
 * is downward) and left = right_shoulder → left_shoulder. The 2D
 * projection of `forward` onto the image plane is the facing direction
 * used by the attention-focus solver.
 *
 * BlazePose landmark indices used:
 *   0  nose
 *   11 left shoulder        12 right shoulder
 *   23 left hip             24 right hip
 *   27 left ankle           28 right ankle
 */

const CDN_VERSION = "0.10.20";
const VISION_BUNDLE_URL =
  `https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@${CDN_VERSION}/vision_bundle.mjs`;
const WASM_BASE =
  `https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@${CDN_VERSION}/wasm`;
const MODEL_URL =
  "https://storage.googleapis.com/mediapipe-models/pose_landmarker/" +
  "pose_landmarker_lite/float16/1/pose_landmarker_lite.task";

let _modulePromise = null;

/** Lazy CDN load of the @mediapipe/tasks-vision ES module. */
function loadModule() {
  if (_modulePromise) return _modulePromise;
  // webpackIgnore prevents Next.js/webpack from trying to resolve
  // this URL at build time; the browser fetches it at runtime.
  _modulePromise = import(/* webpackIgnore: true */ VISION_BUNDLE_URL);
  return _modulePromise;
}

/**
 * Async factory that returns a configured PoseLandmarker.
 *
 * The model file is the BlazePose "lite" variant — fastest, lowest
 * memory, sufficient quality for our purposes since we only need the
 * shoulder+hip subset of landmarks. Switch to `_full` or `_heavy` if
 * the user's footage demands.
 *
 * @param {{ numPoses?: number }} opts
 * @returns {Promise<PoseLandmarker>}
 */
export async function loadPoseLandmarker(opts = {}) {
  const mod = await loadModule();
  const { PoseLandmarker, FilesetResolver } = mod;
  const vision = await FilesetResolver.forVisionTasks(WASM_BASE);
  return PoseLandmarker.createFromOptions(vision, {
    baseOptions: {
      modelAssetPath: MODEL_URL,
      delegate: "GPU",
    },
    runningMode: "VIDEO",
    numPoses: opts.numPoses ?? 5,
    outputSegmentationMasks: false,
    minPoseDetectionConfidence: 0.4,
    minPosePresenceConfidence: 0.4,
    minTrackingConfidence: 0.4,
  });
}

// ────────────────────────────────────────────────────────────────────
// Torso facing extraction
// ────────────────────────────────────────────────────────────────────

/**
 * Convert a single pose into a {position, facing, weight} detection
 * compatible with the attention-focus solver.
 *
 * - position: normalised image coordinates of the hip midpoint
 *   (xs, ys ∈ [0,1], with origin top-left). We pass these straight
 *   into the solver; the solver is dimensionless so any consistent
 *   coordinate system works.
 * - facing: unit vector in the same coordinate system, pointing in
 *   the direction the torso is oriented (front side).
 * - weight: scaled by the visibility of the four torso landmarks.
 *
 * If the pose is too partial to extract a torso (missing >2 of the 4
 * key landmarks), returns null.
 */
export function extractTorsoDetection(pose, options = {}) {
  if (!pose) return null;
  const lm = pose.landmarks ?? pose;            // imageLandmarks
  const wl = pose.worldLandmarks ?? null;
  if (!lm || lm.length < 25) return null;

  const lShoulder = lm[11], rShoulder = lm[12];
  const lHip = lm[23], rHip = lm[24];
  if (!lShoulder || !rShoulder || !lHip || !rHip) return null;

  const minVis = options.minVis ?? 0.35;
  const visible = [lShoulder, rShoulder, lHip, rHip]
    .filter((p) => (p.visibility ?? 1) >= minVis).length;
  if (visible < 3) return null;

  // Hip midpoint in image-normalised coords.
  const hipMid = [
    (lHip.x + rHip.x) * 0.5,
    (lHip.y + rHip.y) * 0.5,
  ];

  // Prefer world landmarks for the torso geometry (they have a
  // genuine depth axis that lets us disambiguate front from back).
  let facing;
  if (wl && wl.length >= 25 && wl[11] && wl[12] && wl[23] && wl[24]) {
    const ws = wl[11], rs = wl[12], lh = wl[23], rh = wl[24];
    // up = shoulder_mid → hip_mid (MediaPipe y is downward so we
    // negate to point "up" anatomically; this only matters for
    // disambiguating front-back via the cross product sign).
    const upX = ((lh.x + rh.x) - (ws.x + rs.x)) * 0.5;
    const upY = ((lh.y + rh.y) - (ws.y + rs.y)) * 0.5;
    const upZ = ((lh.z + rh.z) - (ws.z + rs.z)) * 0.5;
    // left = right_shoulder → left_shoulder
    const lfX = ws.x - rs.x;
    const lfY = ws.y - rs.y;
    const lfZ = ws.z - rs.z;
    // forward = up × left
    const fX = upY * lfZ - upZ * lfY;
    const fY = upZ * lfX - upX * lfZ;
    const fZ = upX * lfY - upY * lfX;
    // Project onto image plane (x, y components only; ignore depth).
    let fx = fX, fy = fY;
    const n = Math.hypot(fx, fy);
    if (n > 1e-6) {
      facing = [fx / n, fy / n];
    } else {
      facing = [0, 1];
    }
  } else {
    // Fallback: torso vector inferred from image landmarks alone.
    // Use perpendicular to (shoulder midpoint → hip midpoint) on the
    // side where the nose is.
    const shMid = [
      (lShoulder.x + rShoulder.x) * 0.5,
      (lShoulder.y + rShoulder.y) * 0.5,
    ];
    const ux = hipMid[0] - shMid[0];
    const uy = hipMid[1] - shMid[1];
    const un = Math.hypot(ux, uy);
    if (un < 1e-6) return null;
    // Perpendicular CCW
    let px = -uy / un;
    let py = ux / un;
    // If the nose is on the opposite side, flip.
    const nose = lm[0];
    if (nose) {
      const nx = nose.x - shMid[0];
      const ny = nose.y - shMid[1];
      const sideDot = nx * px + ny * py;
      if (sideDot < 0) { px = -px; py = -py; }
    }
    facing = [px, py];
  }

  const weight = Math.min(1, visible / 4) *
    Math.min(1, ((lShoulder.visibility ?? 1)
                  + (rShoulder.visibility ?? 1)
                  + (lHip.visibility ?? 1)
                  + (rHip.visibility ?? 1)) / 4);

  return {
    position: hipMid,
    facing,
    weight,
    bbox: bboxFromLandmarks(lm),
    rawPose: pose,
  };
}

function bboxFromLandmarks(lm) {
  let xmin = 1, ymin = 1, xmax = 0, ymax = 0;
  for (const p of lm) {
    if (!p) continue;
    if (p.x < xmin) xmin = p.x;
    if (p.y < ymin) ymin = p.y;
    if (p.x > xmax) xmax = p.x;
    if (p.y > ymax) ymax = p.y;
  }
  return { xmin, ymin, xmax, ymax };
}

/**
 * Run pose detection on a video element and return the list of
 * detections (one per detected person), ready for the focus solver.
 *
 * @param {PoseLandmarker} landmarker
 * @param {HTMLVideoElement} videoEl
 * @param {number} timestampMs  — performance.now() value
 */
export function detectionsFromVideoFrame(landmarker, videoEl, timestampMs) {
  if (videoEl.readyState < 2) return [];
  const result = landmarker.detectForVideo(videoEl, timestampMs);
  if (!result || !result.landmarks) return [];
  const detections = [];
  for (let i = 0; i < result.landmarks.length; i++) {
    const pose = {
      landmarks: result.landmarks[i],
      worldLandmarks: result.worldLandmarks?.[i] ?? null,
    };
    const det = extractTorsoDetection(pose);
    if (det) detections.push(det);
  }
  return detections;
}
