/**
 * DualBodyPanel — fullscreen video viewport with team-anatomy panels
 * and a ball-stats readout overlaid on top with transparent
 * backgrounds. The video (passed as `children`) fills the entire
 * container; the analytic overlays sit above it.
 *
 * Layout (absolute positioning, z-stack):
 *   • z-0   video viewport (children)
 *   • z-10  Team A body silhouette + rosette (top-left)
 *   • z-10  Team B body silhouette + rosette (top-right)
 *   • z-10  ball stats card (bottom-centre, narrow)
 *   • z-10  inter-team min-sep readout (top-centre)
 *
 * All overlay panels use `bg-transparent` so the live frame remains
 * visible underneath; numbers are kept legible with a thin border and
 * a subtle backdrop blur on the chips. Overlays are
 * `pointer-events-none` so video controls underneath stay clickable.
 */

import { useEffect, useRef, useState } from "react";
import BallStatsCard from "./BallStatsCard";

const METRICS = [
  { key: "motor",      label: "MOTOR",   max: 1.0, color: "#58E6D9", unit: "" },
  { key: "speed",      label: "SPD",     max: 9.0, color: "#F0A830", unit: "m/s" },
  { key: "stride",     label: "STRD",    max: 2.4, color: "#B63E96", unit: "m" },
  { key: "vertOsc",    label: "OSC",     max: 12,  color: "#4FD1C5", unit: "cm" },
  { key: "grfBW",      label: "GRF",     max: 4.0, color: "#E6395A", unit: "BW" },
  { key: "cardiac",    label: "CARD",    max: 1.0, color: "#E6395A", unit: "" },
];

const SMOOTH = 0.20;

export default function DualBodyPanel({
  teamA,
  teamB,
  ballMetrics,
  interTeamMinM,
  children,
}) {
  return (
    <div className="relative w-full bg-black overflow-hidden"
         style={{ height: "70vh", minHeight: "32rem" }}>
      {/* Fullscreen video viewport */}
      <div className="absolute inset-0 z-0">
        {children}
      </div>

      {/* Both teams stacked on the left so the rosettes sit one above
          the other for direct cross-team comparison. */}
      <div className="absolute top-3 left-3 z-10
                      w-[20vw] min-w-[200px] max-w-[260px]
                      flex flex-col gap-3 pointer-events-none">
        <div className="border border-darkBorder bg-dark/65 backdrop-blur-sm p-3">
          <BodyCard team={teamA} side="left" />
        </div>
        <div className="border border-darkBorder bg-dark/65 backdrop-blur-sm p-3">
          <BodyCard team={teamB} side="right" />
        </div>
      </div>

      {/* Inter-team minimum separation — top-centre chip */}
      {Number.isFinite(interTeamMinM) && (
        <div className="absolute top-3 left-1/2 -translate-x-1/2 z-10
                        mono text-[10px] uppercase tracking-widest
                        bg-dark/65 backdrop-blur-sm border border-darkBorder
                        px-3 py-1.5 text-light pointer-events-none">
          inter-team min sep
          <span className="text-primary ml-2">
            {interTeamMinM.toFixed(2)} m
          </span>
        </div>
      )}

      {/* Ball stats — bottom-centre overlay, semi-transparent card */}
      <div className="absolute bottom-14 left-1/2 -translate-x-1/2 z-10
                      w-[58vw] min-w-[360px] max-w-[680px]
                      pointer-events-none">
        <div className="border border-darkBorder bg-dark/65 backdrop-blur-sm">
          <BallStatsCard ballMetrics={ballMetrics} />
        </div>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────

function BodyCard({ team, side }) {
  const t = team ?? emptyTeam();
  return (
    <div className="flex flex-col">
      <div className="mono text-[10px] uppercase tracking-widest mb-2"
           style={{ color: t.color || "#cfcfe2" }}>
        {t.label || `Team ${side === "left" ? "A" : "B"}`}
      </div>
      <CircularRosette
        values={{
          motor:    clip(t.motor    ?? 0, 0, 1),
          speed:    t.meanSpeed     ?? 0,
          stride:   t.meanStride    ?? 0,
          vertOsc:  t.meanOsc       ?? 0,
          grfBW:    t.meanGrf       ?? 0,
          cardiac:  clip(t.cardiac  ?? 0, 0, 1),
        }}
        bodyColor={t.color || "#cfcfe2"}
      />
      <div className="mono text-[10px] text-muted mt-2 space-y-0.5">
        <Row k="players" v={t.nPlayers ?? 0} />
        <Row k="speed"   v={(t.meanSpeed ?? 0).toFixed(1) + " m/s"} />
        <Row k="stride"  v={(t.meanStride ?? 0).toFixed(2) + " m"} />
        <Row k="osc"     v={(t.meanOsc ?? 0).toFixed(1) + " cm"} />
        <Row k="GRF"     v={(t.meanGrf ?? 0).toFixed(1) + " BW"} />
        {Number.isFinite(t.minSeparationM) && (
          <Row k="min sep" v={t.minSeparationM.toFixed(2) + " m"} />
        )}
      </div>
    </div>
  );
}

function Row({ k, v }) {
  return (
    <div className="flex justify-between">
      <span className="uppercase tracking-wider">{k}</span>
      <span className="text-light">{v}</span>
    </div>
  );
}

function emptyTeam() {
  return {
    nPlayers: 0, meanSpeed: 0, meanStride: 0, meanOsc: 0, meanGrf: 0,
    motor: 0, cardiac: 0, color: "#cfcfe2", label: "Team",
  };
}

const clip = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

// ────────────────────────────────────────────────────────────────────
// Circular bars rendered around a body silhouette.
// ────────────────────────────────────────────────────────────────────

function CircularRosette({ values, bodyColor }) {
  // Internal exponential smoothing so bars animate when values jump.
  const smoothedRef = useRef({});
  const [, force] = useState(0);

  useEffect(() => {
    let raf;
    const tick = () => {
      raf = requestAnimationFrame(tick);
      const cur = smoothedRef.current;
      let dirty = false;
      for (const m of METRICS) {
        const target = values[m.key] ?? 0;
        const c = cur[m.key] ?? 0;
        const next = c + SMOOTH * (target - c);
        if (Math.abs(next - c) > 1e-4) dirty = true;
        cur[m.key] = next;
      }
      if (dirty) force((x) => (x + 1) & 0xff);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [values]);

  const SIZE = 200;
  const CX = SIZE / 2, CY = SIZE / 2;
  // Outer ring at r=86; subsequent rings step inward.
  const rings = METRICS.map((m, i) => 86 - i * 8);
  const startAngle = -Math.PI * 0.95;
  const endAngle = Math.PI * 0.95;

  return (
    <svg viewBox={`0 0 ${SIZE} ${SIZE}`} className="block w-full h-auto">
      {/* Background ring tracks (faint) */}
      {METRICS.map((m, i) => (
        <ArcPath
          key={`bg-${m.key}`}
          cx={CX} cy={CY} r={rings[i]}
          start={startAngle} end={endAngle}
          color="rgba(255,255,255,0.10)"
          width={4}
        />
      ))}

      {/* Active arcs */}
      {METRICS.map((m, i) => {
        const v = smoothedRef.current[m.key] ?? 0;
        const norm = clip(v / m.max, 0, 1);
        const arcEnd = startAngle + norm * (endAngle - startAngle);
        return (
          <ArcPath
            key={`fg-${m.key}`}
            cx={CX} cy={CY} r={rings[i]}
            start={startAngle} end={arcEnd}
            color={m.color}
            width={5}
          />
        );
      })}

      {/* Metric tick labels at the outer edge */}
      {METRICS.map((m, i) => {
        const a = endAngle + 0.12;
        const x = CX + rings[i] * Math.cos(a);
        const y = CY + rings[i] * Math.sin(a);
        return (
          <text
            key={`l-${m.key}`}
            x={x} y={y}
            fill={m.color}
            fontSize="6.5"
            fontFamily="ui-monospace, Menlo, monospace"
            textAnchor="end"
          >
            {m.label}
          </text>
        );
      })}

      {/* Body silhouette in the middle (schematic) */}
      <BodySilhouette cx={CX} cy={CY} color={bodyColor} />
    </svg>
  );
}

function ArcPath({ cx, cy, r, start, end, color, width }) {
  if (Math.abs(end - start) < 1e-4) {
    return <circle cx={cx} cy={cy} r={r} fill="none" stroke={color}
                   strokeOpacity="0" />;
  }
  const x1 = cx + r * Math.cos(start);
  const y1 = cy + r * Math.sin(start);
  const x2 = cx + r * Math.cos(end);
  const y2 = cy + r * Math.sin(end);
  const large = (end - start) > Math.PI ? 1 : 0;
  const sweep = (end - start) > 0 ? 1 : 0;
  const d = `M ${x1} ${y1} A ${r} ${r} 0 ${large} ${sweep} ${x2} ${y2}`;
  return (
    <path d={d}
          fill="none"
          stroke={color}
          strokeWidth={width}
          strokeLinecap="round" />
  );
}

function BodySilhouette({ cx, cy, color }) {
  // A small humanoid: head + torso + arms + legs, all centred at (cx, cy).
  // Scale was chosen so the rosette wraps comfortably around it.
  return (
    <g opacity="0.9">
      {/* Head */}
      <circle cx={cx} cy={cy - 26} r={8} fill="none"
              stroke={color} strokeWidth="1.4" />
      {/* Torso */}
      <line x1={cx} y1={cy - 18} x2={cx} y2={cy + 8}
            stroke={color} strokeWidth="3.2" strokeLinecap="round" />
      {/* Arms */}
      <line x1={cx} y1={cy - 12} x2={cx - 14} y2={cy + 4}
            stroke={color} strokeWidth="2.2" strokeLinecap="round" />
      <line x1={cx} y1={cy - 12} x2={cx + 14} y2={cy + 4}
            stroke={color} strokeWidth="2.2" strokeLinecap="round" />
      {/* Legs */}
      <line x1={cx} y1={cy + 8}  x2={cx - 8} y2={cy + 30}
            stroke={color} strokeWidth="2.6" strokeLinecap="round" />
      <line x1={cx} y1={cy + 8}  x2={cx + 8} y2={cy + 30}
            stroke={color} strokeWidth="2.6" strokeLinecap="round" />
    </g>
  );
}
