/**
 * Pose-data loaders. Two schemas live in /public/poses/:
 *
 *   A) Bolt biomechanics (joint angles + GRF + balance)
 *      { frames: { "0": { joint_angles, center_of_mass, ground_reaction, balance_metrics } } }
 *
 *   B) MediaPipe landmarks (33 keypoints per pose)
 *      { video_info: {...}, pose_data: [ { frame, timestamp, poses: [{ landmarks: [...] }] } ] }
 *
 * Both are converted to a unified per-frame stream that the motion
 * tool consumes:
 *   { frameIndex, t (sec), joints?, com?, grf?, landmarks?, derived }
 *
 * `derived` carries framework-relevant signals computed on load:
 *   motorIntensity      ∈ [0,1]   |Δjoint| or |Δlandmarks| over time
 *   balanceLoad         ∈ [0,1]   sway-area-style proxy
 *   cardiacLoad         ∈ [0,1]   inferred from impact force / GRF
 *   perceptionLoad      ∈ [0,1]   1 minus stability score
 */

export const MOTION_LIBRARY = [
  {
    id: "bolt",
    label: "Bolt — 100 m record",
    video: "/videos/bolt-force-motion_annotated.mp4",
    pose:  "/poses/bolt_100m_record_side_biomechanics_analysis.json",
    schema: "bolt",
    note: "Joint angles + GRF + CoM, biomechanical schema.",
  },
  {
    id: "powell",
    label: "Powell — sprint start",
    video: "/videos/powell-start_annotated.mp4",
    pose:  "/poses/powell-start_pose_data.json",
    schema: "mediapipe",
    note: "MediaPipe 33-landmark pose.",
  },
  {
    id: "drogba",
    label: "Drogba — header",
    video: "/videos/drogba-header_annotated.mp4",
    pose:  "/poses/drogba-header_pose_data.json",
    schema: "mediapipe",
    note: "Aerial header — full-body explosive motion.",
  },
  {
    id: "beijing",
    label: "Beijing — bird's-eye",
    video: "/videos/beijing_annotated.mp4",
    pose:  "/poses/beijing_pose_data.json",
    schema: "mediapipe",
    note: "Aggregate gait — pose track is sparse.",
  },
  {
    id: "struggle",
    label: "Struggle",
    video: "/videos/struggle_annotated.mp4",
    pose:  null,
    schema: null,
    note: "Annotation only, no pose track.",
  },
];

export async function loadMotion(item) {
  if (!item.pose) return { frames: [], schema: null, info: null };
  const r = await fetch(item.pose);
  const raw = await r.json();
  if (item.schema === "bolt") return parseBolt(raw);
  if (item.schema === "mediapipe") return parseMediaPipe(raw);
  return { frames: [], schema: null, info: null };
}

// ─── Bolt biomechanics ──────────────────────────────────────────────
function parseBolt(raw) {
  const entries = Object.entries(raw.frames).sort(
    (a, b) => parseInt(a[0]) - parseInt(b[0])
  );
  const frames = entries.map(([k, f], i, all) => {
    const prev = i > 0 ? all[i - 1][1] : f;
    const j = f.joint_angles || {};
    const pj = prev.joint_angles || {};
    const dJoint = jointDelta(j, pj);
    return {
      frameIndex: f.frame_index ?? parseInt(k),
      t: i / 30, // assume 30 fps for bolt analysis (it doesn't carry fps)
      joints: j,
      com: f.center_of_mass,
      grf: f.ground_reaction,
      balance: f.balance_metrics,
      derived: deriveBolt(f, dJoint),
    };
  });
  return {
    frames,
    schema: "bolt",
    info: { fps: 30, total: frames.length, jointKeys: ["hip", "knee", "ankle", "shoulder", "elbow"] },
  };
}

function jointDelta(a, b) {
  let s = 0;
  let n = 0;
  for (const k of Object.keys(a)) {
    if (b[k] !== undefined) {
      s += Math.abs(a[k] - b[k]);
      n++;
    }
  }
  return n > 0 ? s / n : 0;
}

function deriveBolt(f, dJoint) {
  const motor = clamp01(dJoint / 60); // 60° change = saturated motor
  const stab = f.balance_metrics?.stability_score ?? 0.5;
  const sway = f.balance_metrics?.sway_area ?? 10;
  const balance = clamp01(sway / 50);
  const grfTotal = Math.abs(f.ground_reaction?.impact_force ?? 0);
  const cardiac = clamp01(grfTotal / 2500);
  const perception = clamp01(1 - stab);
  return { motorIntensity: motor, balanceLoad: balance, cardiacLoad: cardiac, perceptionLoad: perception };
}

// ─── MediaPipe ──────────────────────────────────────────────────────
function parseMediaPipe(raw) {
  const fps = raw.video_info?.fps ?? 30;
  const frames = raw.pose_data.map((entry, i, all) => {
    const lm = entry.poses?.[0]?.landmarks ?? null;
    const prev = i > 0 ? all[i - 1].poses?.[0]?.landmarks : lm;
    const dPose = lm && prev ? landmarkDelta(lm, prev) : 0;
    return {
      frameIndex: entry.frame,
      t: entry.timestamp,
      landmarks: lm,
      derived: {
        motorIntensity: clamp01(dPose * 18), // dPose ~0.05 → saturated
        balanceLoad: 0.3,
        cardiacLoad: 0.4,
        perceptionLoad: 0.3,
      },
    };
  });
  return {
    frames,
    schema: "mediapipe",
    info: { fps, total: raw.video_info?.total_frames ?? frames.length, jointKeys: [] },
  };
}

function landmarkDelta(a, b) {
  if (!a || !b) return 0;
  const n = Math.min(a.length, b.length);
  if (n === 0) return 0;
  let s = 0;
  for (let i = 0; i < n; i++) {
    const dx = (a[i].x ?? 0) - (b[i].x ?? 0);
    const dy = (a[i].y ?? 0) - (b[i].y ?? 0);
    const dz = (a[i].z ?? 0) - (b[i].z ?? 0);
    s += Math.sqrt(dx * dx + dy * dy + dz * dz);
  }
  return s / n;
}

const clamp01 = (v) => Math.max(0, Math.min(1, v));

// MediaPipe pose-landmark connection list (subset for skeleton drawing)
export const MP_CONNECTIONS = [
  // Face core
  [11, 12], [11, 23], [12, 24], [23, 24],
  // Right arm
  [11, 13], [13, 15], [15, 17], [15, 19], [15, 21],
  // Left arm
  [12, 14], [14, 16], [16, 18], [16, 20], [16, 22],
  // Right leg
  [23, 25], [25, 27], [27, 29], [27, 31],
  // Left leg
  [24, 26], [26, 28], [28, 30], [28, 32],
];
