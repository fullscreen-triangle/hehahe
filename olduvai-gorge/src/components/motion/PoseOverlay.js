import { useEffect, useRef } from "react";
import { MP_CONNECTIONS } from "@/lib/poseData";

/**
 * Skeleton overlay drawn on top of the video canvas. The drawing IS
 * the per-frame computation: each frame the canvas is wiped and
 * redrawn from the current frame's landmark/joint state.
 */
export default function PoseOverlay({ width, height, frame, schema }) {
  const canvasRef = useRef();

  useEffect(() => {
    const c = canvasRef.current;
    if (!c) return;
    const ctx = c.getContext("2d");
    ctx.clearRect(0, 0, width, height);

    if (!frame) return;

    if (schema === "mediapipe" && frame.landmarks) {
      drawMediaPipe(ctx, frame.landmarks, width, height);
    } else if (schema === "bolt" && frame.joints) {
      drawBoltJointBar(ctx, frame.joints, width, height);
    }
  }, [frame, schema, width, height]);

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      className="absolute inset-0 pointer-events-none"
    />
  );
}

function drawMediaPipe(ctx, landmarks, w, h) {
  ctx.lineWidth = 2;
  ctx.strokeStyle = "rgba(88, 230, 217, 0.85)";
  // Connections
  for (const [a, b] of MP_CONNECTIONS) {
    const la = landmarks[a];
    const lb = landmarks[b];
    if (!la || !lb) continue;
    if (la.visibility < 0.4 || lb.visibility < 0.4) continue;
    ctx.beginPath();
    ctx.moveTo(la.x * w, la.y * h);
    ctx.lineTo(lb.x * w, lb.y * h);
    ctx.stroke();
  }
  // Keypoints
  for (let i = 0; i < landmarks.length; i++) {
    const lm = landmarks[i];
    if (lm.visibility < 0.4) continue;
    const r = 3 + 2 * (lm.visibility ?? 0);
    ctx.fillStyle = i < 11 ? "rgba(240, 168, 48, 0.95)" : "rgba(182, 62, 150, 0.95)";
    ctx.beginPath();
    ctx.arc(lm.x * w, lm.y * h, r, 0, Math.PI * 2);
    ctx.fill();
  }
}

function drawBoltJointBar(ctx, joints, w, h) {
  // Bolt schema gives only joint angles. Draw a per-joint bar across
  // the bottom of the frame for an immediate visual readout.
  const order = ["hip", "knee", "ankle", "shoulder", "elbow"];
  const barW = w / order.length;
  ctx.font = "11px ui-monospace, Consolas, monospace";
  order.forEach((k, i) => {
    const v = joints[k] ?? 0;
    const norm = Math.max(0, Math.min(1, v / 180));
    const x = i * barW + 8;
    const y = h - 10;
    const bw = barW - 16;
    ctx.fillStyle = "rgba(20, 20, 28, 0.65)";
    ctx.fillRect(x, y - 28, bw, 28);
    ctx.fillStyle = "rgba(88, 230, 217, 0.7)";
    ctx.fillRect(x, y - 4, bw * norm, 4);
    ctx.fillStyle = "rgba(232, 232, 240, 0.95)";
    ctx.fillText(k, x + 4, y - 14);
    ctx.fillStyle = "rgba(88, 230, 217, 0.95)";
    ctx.fillText(`${v.toFixed(0)}°`, x + 4, y - 24);
  });
}
