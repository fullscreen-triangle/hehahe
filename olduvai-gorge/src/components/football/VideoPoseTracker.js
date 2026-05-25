import { useEffect, useRef, useState } from "react";
import {
  loadPoseLandmarker,
  extractTorsoDetection,
} from "@/lib/football/poseFromVideo";
import { robustFocusPoint } from "@/lib/football/attentionFocus";
import { TeamClassifier, sampleTorsoColor } from "@/lib/football/teamClassifier";
import { PlayerKinematics } from "@/lib/football/biomechanics";
import { BallTrajectory } from "@/lib/football/ballMetrics";
import {
  loadAnthropometry,
  profileFor,
  derivedFromProfile,
} from "@/lib/football/anthropometry";

/**
 * VideoPoseTracker — BlazePose in browser + team classifier +
 * per-player kinematics + ball-trajectory metrics.
 *
 * Renders the video, overlays bounding boxes + skeleton + team colour
 * + facing arrows + ball focus dot, and emits per-frame structured
 * state to `onFrameUpdate`.
 *
 * Props:
 *   src                  — video URL / object URL
 *   onFrameUpdate        — callback({ players, ballMetrics, focus,
 *                                     teamColors }) per processed frame
 *   detectionHz          — pose-detection rate cap (Hz), default 12
 *   continent            — anthropometric profile selector
 *   className            — extra wrapper classes
 */
export default function VideoPoseTracker({
  src,
  onFrameUpdate,
  detectionHz = 12,
  continent = "South America",
  className = "",
}) {
  const videoRef = useRef(null);
  const overlayRef = useRef(null);
  const sampleCanvasRef = useRef(null);

  const landmarkerRef = useRef(null);
  const teamCxRef = useRef(new TeamClassifier());
  const kinByIdRef = useRef(new Map());
  const ballRef = useRef(new BallTrajectory());
  const lastDetectRef = useRef(0);
  const trackerStateRef = useRef([]);  // most recent tracked players

  const [status, setStatus] = useState("idle");
  const [err, setErr] = useState(null);
  const [muted, setMuted] = useState(true);

  // Load MediaPipe + anthropometric data on mount.
  useEffect(() => {
    let alive = true;
    setStatus("loading");
    Promise.all([loadPoseLandmarker({ numPoses: 8 }), loadAnthropometry()])
      .then(([lm]) => {
        if (!alive) return;
        landmarkerRef.current = lm;
        setStatus("ready");
      })
      .catch((e) => {
        if (!alive) return;
        setErr(String(e?.message ?? e));
        setStatus("error");
      });
    return () => {
      alive = false;
      if (landmarkerRef.current) {
        try { landmarkerRef.current.close(); } catch (_) {}
        landmarkerRef.current = null;
      }
    };
  }, []);

  // Per-frame loop.
  useEffect(() => {
    if (status !== "ready") return;
    const video = videoRef.current;
    const canvas = overlayRef.current;
    const sampleCanvas = sampleCanvasRef.current;
    if (!video || !canvas || !sampleCanvas) return;

    const ctx = canvas.getContext("2d");
    const sctx = sampleCanvas.getContext("2d", { willReadFrequently: true });
    let raf;

    const tick = () => {
      raf = requestAnimationFrame(tick);
      const now = performance.now();
      const minDelta = 1000 / Math.max(1, detectionHz);
      if (now - lastDetectRef.current < minDelta) return;
      if (video.readyState < 2 || video.paused || video.ended) return;
      lastDetectRef.current = now;

      const r = video.getBoundingClientRect();
      if (canvas.width !== Math.round(r.width)
          || canvas.height !== Math.round(r.height)) {
        canvas.width = Math.max(1, Math.round(r.width));
        canvas.height = Math.max(1, Math.round(r.height));
      }
      const W = canvas.width, H = canvas.height;

      // Mirror the current video frame into the sample canvas so the
      // team classifier can read pixels (the <video> itself isn't a
      // valid getImageData source, and reading it on the overlay canvas
      // would taint it).
      if (sampleCanvas.width !== video.videoWidth ||
          sampleCanvas.height !== video.videoHeight) {
        sampleCanvas.width = video.videoWidth || 640;
        sampleCanvas.height = video.videoHeight || 360;
      }
      sctx.drawImage(video, 0, 0, sampleCanvas.width, sampleCanvas.height);

      const result = landmarkerRef.current.detectForVideo(video, now);
      const players = [];
      if (result && result.landmarks) {
        for (let i = 0; i < result.landmarks.length; i++) {
          const pose = {
            landmarks: result.landmarks[i],
            worldLandmarks: result.worldLandmarks?.[i] ?? null,
          };
          const det = extractTorsoDetection(pose);
          if (!det) continue;

          // Stable id from this frame's index + nearest previous-id
          // by hip distance (1-frame greedy assignment).
          const id = assignStableId(det, trackerStateRef.current, i);

          // Sample jersey colour from the sample canvas (which holds
          // the video frame in pixel space).
          const bboxPx = bboxToPixels(det.bbox, sampleCanvas.width, sampleCanvas.height);
          const colorSample = sampleTorsoColor(sctx, bboxPx);
          const team = teamCxRef.current.classify(id, colorSample);

          // Kinematics per stable id.
          const profile = profileFor(continent);
          if (!kinByIdRef.current.has(id)) {
            kinByIdRef.current.set(id, new PlayerKinematics(profile));
          }
          const kin = kinByIdRef.current.get(id);
          const metrics = kin.update(now / 1000, result.landmarks[i]);

          players.push({
            id,
            team,
            position: det.position,
            facing: det.facing,
            weight: det.weight,
            bbox: det.bbox,
            landmarks: result.landmarks[i],
            colorSample,
            metrics,
          });
        }
      }
      trackerStateRef.current = players;

      // Garbage-collect kinematics state for ids not seen this frame.
      const ids = new Set(players.map((p) => p.id));
      for (const k of [...kinByIdRef.current.keys()]) {
        if (!ids.has(k)) kinByIdRef.current.delete(k);
      }

      // Attention focus across all detected players, then ball metrics.
      let focus = null;
      if (players.length >= 2) {
        const est = robustFocusPoint(players.map((p) => ({
          position: p.position,
          facing: p.facing,
          weight: p.weight,
        })));
        focus = est.point;
      }
      const possessed = focus
        ? players.some((p) => Math.hypot(
            p.position[0] - focus[0], p.position[1] - focus[1]) < 0.05)
        : false;
      if (focus) ballRef.current.update(now / 1000, focus, possessed);

      // Choose a px/m scale from the median of detected players (each
      // kinematic supplies pxPerMetre in image-normalised units).
      const scales = players
        .map((p) => p.metrics?.pxPerMetre)
        .filter((v) => v && Number.isFinite(v) && v > 0);
      const pxPerMetre = scales.length > 0
        ? scales.sort((a, b) => a - b)[Math.floor(scales.length / 2)]
        : null;
      const ballMetrics = ballRef.current.snapshot({ pxPerMetre });

      // Draw everything.
      drawOverlay(ctx, W, H, players, focus, teamCxRef.current.teamColors());

      onFrameUpdate?.({
        players,
        focus,
        ballMetrics,
        teamColors: teamCxRef.current.teamColors(),
        pxPerMetre,
      });
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [status, detectionHz, onFrameUpdate, continent]);

  // Reset on src change.
  useEffect(() => {
    teamCxRef.current.reset();
    kinByIdRef.current.clear();
    ballRef.current.reset();
    trackerStateRef.current = [];
  }, [src]);

  return (
    <div className={`relative w-full ${className}`}
         style={{ aspectRatio: "16 / 9", background: "#000" }}>
      <video
        ref={videoRef}
        src={src || undefined}
        playsInline
        muted={muted}
        loop
        controls
        preload="auto"
        crossOrigin="anonymous"
        className="absolute inset-0 w-full h-full object-contain"
      />
      <canvas
        ref={overlayRef}
        className="absolute inset-0 w-full h-full pointer-events-none"
      />
      <canvas ref={sampleCanvasRef} style={{ display: "none" }} />
      <StatusBadge status={status} err={err}
                   nPlayers={trackerStateRef.current.length} />
      <button
        onClick={() => {
          const v = videoRef.current;
          if (!v) return;
          const next = !muted;
          setMuted(next);
          v.muted = next;
        }}
        className="absolute bottom-2 right-2 mono text-[10px] uppercase tracking-widest px-2 py-1 bg-dark/70 text-light border border-darkBorder hover:border-primary"
      >
        {muted ? "muted" : "sound on"}
      </button>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────

function StatusBadge({ status, err, nPlayers }) {
  let label, colour;
  switch (status) {
    case "idle":    label = "—";                 colour = "#8a8aa0"; break;
    case "loading": label = "loading BlazePose"; colour = "#F0A830"; break;
    case "ready":   label = `${nPlayers} pose${nPlayers === 1 ? "" : "s"}`;
                    colour = "#58E6D9"; break;
    case "error":   label = "error";             colour = "#E6395A"; break;
    default:        label = status;              colour = "#cfcfe2";
  }
  return (
    <div className="absolute top-2 left-2 mono text-[10px] uppercase tracking-widest bg-dark/70 px-2 py-1 backdrop-blur"
         style={{ color: colour }}
         title={err ?? undefined}>
      {label}
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────
// Helpers
// ────────────────────────────────────────────────────────────────────

let _nextId = 1;
function assignStableId(det, prevPlayers, frameIdx) {
  if (!prevPlayers || prevPlayers.length === 0) {
    return _nextId++;
  }
  let best = null, bestD = 0.10;
  for (const p of prevPlayers) {
    const d = Math.hypot(
      det.position[0] - p.position[0],
      det.position[1] - p.position[1]);
    if (d < bestD) { bestD = d; best = p; }
  }
  if (best) return best.id;
  return _nextId++;
}

function bboxToPixels(bboxNorm, W, H) {
  return {
    xmin: bboxNorm.xmin * W,
    ymin: bboxNorm.ymin * H,
    xmax: bboxNorm.xmax * W,
    ymax: bboxNorm.ymax * H,
  };
}

// ────────────────────────────────────────────────────────────────────
// Overlay drawing
// ────────────────────────────────────────────────────────────────────

const POSE_EDGES = [
  // Face core
  [11, 12], [11, 23], [12, 24], [23, 24],
  // Right arm
  [11, 13], [13, 15], [15, 17], [15, 19], [15, 21],
  // Left arm
  [12, 14], [14, 16], [16, 18], [16, 20], [16, 22],
  // Right leg
  [23, 25], [25, 27], [27, 29], [27, 31], [29, 31],
  // Left leg
  [24, 26], [26, 28], [28, 30], [28, 32], [30, 32],
];

function drawOverlay(ctx, W, H, players, focus, teamColors) {
  ctx.clearRect(0, 0, W, H);

  // 1. Attention rays as faint streaks.
  for (const p of players) {
    const px = p.position[0] * W;
    const py = p.position[1] * H;
    const reach = 0.40 * Math.max(W, H);
    const ex = px + p.facing[0] * reach;
    const ey = py + p.facing[1] * reach;
    const grad = ctx.createLinearGradient(px, py, ex, ey);
    const baseCol = teamColors[p.team] ?? "rgba(160,160,180,0.6)";
    grad.addColorStop(0, withAlpha(baseCol, 0.45));
    grad.addColorStop(1, withAlpha(baseCol, 0.00));
    ctx.strokeStyle = grad;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(px, py);
    ctx.lineTo(ex, ey);
    ctx.stroke();
  }

  // 2. Per-player bbox + skeleton + facing arrow.
  for (const p of players) {
    const teamCol = teamColors[p.team] ?? "#cfcfe2";
    const bbox = p.bbox;
    if (bbox) {
      ctx.strokeStyle = withAlpha(teamCol, 0.85);
      ctx.lineWidth = 2;
      ctx.strokeRect(bbox.xmin * W, bbox.ymin * H,
                     (bbox.xmax - bbox.xmin) * W,
                     (bbox.ymax - bbox.ymin) * H);
      // Id badge
      ctx.fillStyle = withAlpha(teamCol, 0.85);
      ctx.fillRect(bbox.xmin * W, bbox.ymin * H - 18, 26, 16);
      ctx.fillStyle = "#0a0a0f";
      ctx.font = "11px ui-monospace, Menlo, monospace";
      ctx.fillText(`#${p.id}`, bbox.xmin * W + 3, bbox.ymin * H - 5);
    }

    // Skeleton
    const lm = p.landmarks;
    if (lm) {
      ctx.strokeStyle = withAlpha(teamCol, 0.95);
      ctx.lineWidth = 2;
      for (const [a, b] of POSE_EDGES) {
        const la = lm[a], lb = lm[b];
        if (!la || !lb) continue;
        const av = (la.visibility ?? 1), bv = (lb.visibility ?? 1);
        if (av < 0.3 || bv < 0.3) continue;
        ctx.beginPath();
        ctx.moveTo(la.x * W, la.y * H);
        ctx.lineTo(lb.x * W, lb.y * H);
        ctx.stroke();
      }
      // Keypoints
      ctx.fillStyle = withAlpha(teamCol, 0.95);
      for (let i = 0; i < lm.length; i++) {
        const k = lm[i];
        if (!k || (k.visibility ?? 1) < 0.3) continue;
        ctx.beginPath();
        ctx.arc(k.x * W, k.y * H, 2.6, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    // Facing arrow at the hip
    const px = p.position[0] * W;
    const py = p.position[1] * H;
    drawArrow(ctx, px, py, p.facing[0], p.facing[1], teamCol, 22);

    // Speed label
    if (p.metrics?.valid) {
      ctx.fillStyle = withAlpha("#ffffff", 0.85);
      ctx.font = "10px ui-monospace, Menlo, monospace";
      ctx.fillText(`${p.metrics.speedMps.toFixed(1)} m/s`,
                   px + 4, py + 12);
    }
  }

  // 3. Focus dot.
  if (focus) {
    const fx = focus[0] * W;
    const fy = focus[1] * H;
    ctx.fillStyle = "rgba(255, 255, 255, 0.95)";
    ctx.beginPath();
    ctx.arc(fx, fy, 8, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = "rgba(182, 62, 150, 0.95)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(fx, fy, 14, 0, Math.PI * 2);
    ctx.stroke();
  }
}

function drawArrow(ctx, px, py, fx, fy, color, length) {
  const n = Math.hypot(fx, fy) || 1;
  const ux = fx / n, uy = fy / n;
  const vx = -uy, vy = ux;
  const tx = px + ux * length;
  const ty = py + uy * length;
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.moveTo(tx, ty);
  ctx.lineTo(px + vx * 4, py + vy * 4);
  ctx.lineTo(px - vx * 4, py - vy * 4);
  ctx.closePath();
  ctx.fill();
}

function withAlpha(col, a) {
  if (col.startsWith("#")) {
    const r = parseInt(col.slice(1, 3), 16);
    const g = parseInt(col.slice(3, 5), 16);
    const b = parseInt(col.slice(5, 7), 16);
    return `rgba(${r},${g},${b},${a})`;
  }
  // Already rgb(); convert.
  const m = col.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
  if (m) return `rgba(${m[1]},${m[2]},${m[3]},${a})`;
  return col;
}
