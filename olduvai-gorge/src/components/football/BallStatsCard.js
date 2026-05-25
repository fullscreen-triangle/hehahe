/**
 * BallStatsCard — persistent ball-metric readout that updates with
 * the focus trajectory. Inspired by the "color the puck" reference:
 * a small always-visible card showing speed, flight, curve, and
 * cumulative possession metrics.
 *
 * Circular bars are used for the rapidly-changing scalars (speed,
 * curvature) and numeric readouts for the slower aggregate stats
 * (flight fraction, last flight duration, time in possession).
 */

import { useEffect, useRef, useState } from "react";

const SMOOTH = 0.25;

export default function BallStatsCard({ ballMetrics }) {
  const m = ballMetrics ?? {};
  const speedMps = Number.isFinite(m.speed_mps) ? m.speed_mps : null;
  const accelMps2 = Number.isFinite(m.accel_mps2) ? m.accel_mps2 : null;
  const curvaturePerM = Number.isFinite(m.curvature_per_m) ? m.curvature_per_m : null;
  const flightFraction = m.flightFraction ?? 0;
  const lastFlightMs = m.lastFlightMs ?? 0;
  const inFlightNow = m.inFlightNow ?? false;

  return (
    <div className="border border-darkBorder bg-darkSoft/70 backdrop-blur p-3
                    grid grid-cols-6 gap-3 md:grid-cols-3 sm:grid-cols-2">
      <SpinDial label="BALL SPEED"
                value={speedMps}
                max={45}
                unit="m/s"
                color="#58E6D9"
                fallback={m.speed_units_per_s?.toFixed(2)}
                fallbackUnit="px·s⁻¹" />
      <SpinDial label="ACCEL"
                value={accelMps2}
                max={50}
                unit="m/s²"
                color="#F0A830"
                fallback={m.accel_units_per_s2?.toFixed(2)}
                fallbackUnit="px·s⁻²" />
      <SpinDial label="CURVE"
                value={curvaturePerM}
                max={2.5}
                unit="rad/m"
                color="#B63E96"
                fallback={m.curvature_per_unit?.toFixed(3)}
                fallbackUnit="rad/u" />
      <SmallStat label="FLIGHT %" value={(flightFraction * 100).toFixed(0)} unit="%" />
      <SmallStat label="LAST FLIGHT"
                 value={lastFlightMs ? lastFlightMs.toFixed(0) : "—"}
                 unit="ms" />
      <SmallStat label="STATE"
                 value={inFlightNow ? "FLIGHT" : "POSSESSED"}
                 unit=""
                 color={inFlightNow ? "#F0A830" : "#58E6D9"} />
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────

function SpinDial({ label, value, max, unit, color, fallback, fallbackUnit }) {
  const smoothedRef = useRef(0);
  const [, force] = useState(0);

  useEffect(() => {
    let raf;
    const tick = () => {
      raf = requestAnimationFrame(tick);
      const target = Number.isFinite(value) ? value : 0;
      const cur = smoothedRef.current;
      const next = cur + SMOOTH * (target - cur);
      if (Math.abs(next - cur) > 1e-3) {
        smoothedRef.current = next;
        force((x) => (x + 1) & 0xff);
      }
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value]);

  const v = smoothedRef.current;
  const norm = Math.max(0, Math.min(1, v / max));
  const SIZE = 76;
  const CX = SIZE / 2, CY = SIZE / 2, R = 28;
  const start = -Math.PI * 0.85;
  const end = Math.PI * 0.85;
  const arcEnd = start + norm * (end - start);

  return (
    <div className="flex flex-col items-center">
      <div className="mono text-[9px] uppercase tracking-widest text-muted mb-0.5">
        {label}
      </div>
      <svg viewBox={`0 0 ${SIZE} ${SIZE}`} width={SIZE} height={SIZE}>
        <Arc cx={CX} cy={CY} r={R} start={start} end={end}
             color="rgba(255,255,255,0.08)" width={5} />
        <Arc cx={CX} cy={CY} r={R} start={start} end={arcEnd}
             color={color} width={5} />
        {Number.isFinite(value) ? (
          <text x={CX} y={CY + 3} textAnchor="middle"
                fontFamily="ui-monospace, Menlo, monospace"
                fontSize="13" fill={color}>
            {v.toFixed(v < 10 ? 1 : 0)}
          </text>
        ) : (
          <text x={CX} y={CY + 3} textAnchor="middle"
                fontFamily="ui-monospace, Menlo, monospace"
                fontSize="11" fill={color}>
            {fallback ?? "—"}
          </text>
        )}
      </svg>
      <div className="mono text-[9px] text-light mt-0.5">
        {Number.isFinite(value) ? unit : (fallbackUnit ?? unit)}
      </div>
    </div>
  );
}

function SmallStat({ label, value, unit, color = "#cfcfe2" }) {
  return (
    <div className="flex flex-col items-center justify-center">
      <div className="mono text-[9px] uppercase tracking-widest text-muted mb-0.5">
        {label}
      </div>
      <div className="mono text-base" style={{ color }}>
        {value}
      </div>
      {unit && (
        <div className="mono text-[9px] text-light">{unit}</div>
      )}
    </div>
  );
}

function Arc({ cx, cy, r, start, end, color, width }) {
  if (Math.abs(end - start) < 1e-4) return null;
  const x1 = cx + r * Math.cos(start);
  const y1 = cy + r * Math.sin(start);
  const x2 = cx + r * Math.cos(end);
  const y2 = cy + r * Math.sin(end);
  const large = (end - start) > Math.PI ? 1 : 0;
  const sweep = (end - start) > 0 ? 1 : 0;
  const d = `M ${x1} ${y1} A ${r} ${r} 0 ${large} ${sweep} ${x2} ${y2}`;
  return (
    <path d={d} fill="none" stroke={color} strokeWidth={width}
          strokeLinecap="round" />
  );
}
