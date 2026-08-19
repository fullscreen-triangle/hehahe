/**
 * Results matrix with heat shading, undefined-vs-absent distinction, and
 * per-cell backend provenance on hover.
 *
 * An undefined value is shown as "undef", never as a blank or a zero: the
 * distinction between an observable that has no defined value here (a tonic
 * rate on an open circuit) and one that was never requested is exactly what
 * a reader needs.
 */

import { useMemo, useState } from "react";
import type { ArmResult } from "../lang/runtime";
import { OBSERVABLES } from "../lang/observables";
import { MONO, SANS, type Theme } from "../theme";

interface Props { arms: ArmResult[]; theme: Theme; }

const fmt = (v: unknown) => {
  if (v === null || v === undefined) return "—";
  if (typeof v === "string") return v;
  if (Array.isArray(v)) return `${v.length} item(s)`;
  if (typeof v === "number") {
    if (!Number.isFinite(v)) return "undef";
    if (v !== 0 && (Math.abs(v) < 1e-3 || Math.abs(v) >= 1e5)) return v.toExponential(2);
    return v.toFixed(Math.abs(v) < 1 ? 4 : 2);
  }
  return String(v);
};

export function ResultsView({ arms, theme: T }: Props) {
  const [hover, setHover] = useState<{ x: number; y: number; text: string } | null>(null);

  const obsNames = useMemo(() => {
    const s: string[] = [];
    for (const a of arms) for (const k of a.store.keys()) if (!s.includes(k)) s.push(k);
    return s;
  }, [arms]);

  /** Per-row range for heat shading; only numeric rows shade. */
  const ranges = useMemo(() => {
    const m = new Map<string, [number, number]>();
    for (const o of obsNames) {
      const vals: number[] = [];
      for (const a of arms) {
        const v = a.store.get(o)?.value;
        if (typeof v === "number" && Number.isFinite(v)) vals.push(v);
      }
      if (vals.length > 1) m.set(o, [Math.min(...vals), Math.max(...vals)]);
    }
    return m;
  }, [arms, obsNames]);

  const shade = (o: string, v: unknown) => {
    if (typeof v !== "number" || !Number.isFinite(v)) return "transparent";
    const r = ranges.get(o);
    if (!r || r[1] === r[0]) return "transparent";
    const t = (v - r[0]) / (r[1] - r[0]);
    return `${T.accent}${Math.round(10 + t * 40).toString(16).padStart(2, "0")}`;
  };

  return (
    <div style={{ height: "100%", overflow: "auto", padding: 12 }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontFamily: MONO, fontSize: 11.5 }}>
        <thead>
          <tr style={{ borderBottom: `1px solid ${T.border}` }}>
            <th style={{ textAlign: "left", padding: "7px 8px", color: T.textMuted, fontWeight: 500, position: "sticky", left: 0, background: T.panelBg }}>
              observable
            </th>
            {arms.map((a) => (
              <th key={a.name} style={{
                textAlign: "right", padding: "7px 10px", fontWeight: 600,
                color: a.closure === "open" ? T.open : T.closed, whiteSpace: "nowrap",
              }}>
                {a.closure === "open" ? "◇" : "●"} {a.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {obsNames.map((o) => {
            const spec = OBSERVABLES.get(o.split("(")[0]);
            return (
              <tr key={o} style={{ borderBottom: `1px solid ${T.borderSoft}` }}>
                <td
                  style={{ padding: "5px 8px", color: T.text, position: "sticky", left: 0, background: T.panelBg, cursor: spec ? "help" : "default" }}
                  onMouseEnter={(e) => spec && setHover({ x: e.clientX, y: e.clientY, text: `${spec.name} [${spec.unit}] · ${spec.tier}\n\n${spec.procedure}` })}
                  onMouseLeave={() => setHover(null)}
                >
                  {o}
                  {spec && <span style={{ color: T.textMuted, marginLeft: 6, fontSize: 9 }}>{spec.tier}</span>}
                </td>
                {arms.map((a) => {
                  const m = a.store.get(o);
                  const v = m?.value;
                  const undef = typeof v === "number" && !Number.isFinite(v);
                  return (
                    <td key={a.name}
                      onMouseEnter={(e) => m && setHover({
                        x: e.clientX, y: e.clientY,
                        text: [
                          `${o} = ${fmt(v)} ${m.unit}`,
                          m.note ? `note: ${m.note}` : "",
                          `floor used: ${m.report.floorUsed.toExponential(3)}`,
                          m.report.band ? `band: ${m.report.band[0]}–${m.report.band[1]} Hz` : "",
                          `seed ${m.report.seed} · ${m.report.nSamples} samples · dt ${m.report.dt}s`,
                        ].filter(Boolean).join("\n"),
                      })}
                      onMouseLeave={() => setHover(null)}
                      style={{
                        textAlign: "right", padding: "5px 10px",
                        color: v == null ? T.textMuted : undef ? T.textMuted : T.text,
                        fontStyle: undef ? "italic" : "normal",
                        background: shade(o, v),
                        fontVariantNumeric: "tabular-nums", cursor: "help",
                      }}>
                      {fmt(v)}
                      {m?.unit && !undef && typeof v === "number" && (
                        <span style={{ color: T.textMuted, marginLeft: 3, fontSize: 9 }}>{m.unit}</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>

      {hover && (
        <div style={{
          position: "fixed", left: Math.min(hover.x + 12, window.innerWidth - 420),
          top: hover.y + 14, maxWidth: 400, padding: "8px 11px",
          background: T.panelBg, border: `1px solid ${T.border}`, borderRadius: 4,
          color: T.text, fontFamily: MONO, fontSize: 10.5, lineHeight: 1.55,
          zIndex: 60, whiteSpace: "pre-wrap", boxShadow: "0 8px 26px rgba(0,0,0,0.3)",
        }}>{hover.text}</div>
      )}
    </div>
  );
}
