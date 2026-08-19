/**
 * Aperture report.
 *
 * An open circuit is a diagnostic, not an error: it is the model of
 * deafferentation and simulating it is the point. What the language refuses
 * is silence, so this view states, for every arm, which circulation was
 * opened and what the framework predicts as a consequence -- before any
 * numbers are read.
 */

import type { ArmResult } from "../lang/runtime";
import { MONO, SANS, type Theme } from "../theme";

interface Props { arms: ArmResult[]; theme: Theme; }

export function ApertureView({ arms, theme: T }: Props) {
  return (
    <div style={{ height: "100%", overflow: "auto", padding: 14, fontFamily: SANS }}>
      {arms.map((a) => {
        const open = a.closure === "open";
        const col = open ? T.open : T.closed;
        return (
          <div key={a.name} style={{
            marginBottom: 12, borderRadius: 5,
            border: `1px solid ${col}44`, background: `${col}0d`,
            overflow: "hidden",
          }}>
            <div style={{
              display: "flex", alignItems: "center", gap: 10,
              padding: "8px 13px", borderBottom: a.apertures.length ? `1px solid ${col}26` : "none",
            }}>
              <span style={{ color: col, fontWeight: 700, fontSize: 12, letterSpacing: 0.5 }}>
                {open ? "◇ OPEN" : "● CLOSED"}
              </span>
              <span style={{ color: T.text, fontSize: 12.5, fontFamily: MONO }}>{a.name}</span>
              <span style={{ marginLeft: "auto", color: T.textMuted, fontSize: 10 }}>
                record {a.record}
              </span>
            </div>

            {a.provenance.length > 0 && (
              <div style={{
                padding: "6px 13px", fontFamily: MONO, fontSize: 10.5,
                color: T.textDim, borderBottom: a.apertures.length ? `1px solid ${col}18` : "none",
              }}>
                {a.provenance.map((p, i) => (
                  <div key={i}><span style={{ color: T.textMuted }}>applied </span>{p}</div>
                ))}
              </div>
            )}

            {a.apertures.length === 0 ? (
              <div style={{ padding: "7px 13px", fontSize: 11, color: T.textDim }}>
                {a.provenance.length
                  ? "Every declared outbound path is still matched by a closing return. The manipulation was parametric: it changed the solution, not the constraint set."
                  : "Circulation intact."}
              </div>
            ) : (
              a.apertures.map((msg, i) => (
                <div key={i} style={{
                  padding: "8px 13px", fontFamily: MONO, fontSize: 10.5,
                  lineHeight: 1.6, color: col,
                }}>{msg}</div>
              ))
            )}
          </div>
        );
      })}
    </div>
  );
}
