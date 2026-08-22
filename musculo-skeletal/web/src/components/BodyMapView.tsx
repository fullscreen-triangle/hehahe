/**
 * The body map: the anatomy illustration at full size, as a browsable
 * reference and as a heatmap.
 *
 * The small figure in the corner of every results page and at the centre of
 * the sunburst answers "where is this?" at a glance. This is the same
 * geometry given room to be read: both the surface view and the organ view,
 * over the template's own photographic plates, with the template's own
 * region labels.
 *
 * Clicking a region selects it, and the panel then says what the tool knows
 * about that region -- which segment of the anthropometry covers it, what its
 * mass and inertia are, and which circuit compartments bind there. That is
 * the point of having the illustration in the project rather than beside it:
 * the picture is an index into the model, not a decoration.
 */

import { useMemo, useState } from "react";
import {
  AnatomyFigure, HeatLegend, allRegions, heatColour, regionLabel, resolveRegion,
} from "./AnatomyFigure";
import { analyseSubject, type Subject } from "../lang/bsp";
import type { ArmResult } from "../lang/runtime";
import type { Theme } from "../theme";

type ViewName = "body" | "organs";

/** What the figure is coloured by. */
type Metric = "mass" | "inertia" | "length" | "none";

const METRICS: { id: Metric; label: string; unit: string }[] = [
  { id: "mass", label: "segment mass", unit: "kg" },
  { id: "inertia", label: "moment of inertia", unit: "kg m2" },
  { id: "length", label: "segment length", unit: "m" },
  { id: "none", label: "outline only", unit: "" },
];

interface Props {
  theme: Theme;
  subject: Subject;
  arms: ArmResult[];
}

export function BodyMapView({ theme, subject, arms }: Props) {
  const [view, setView] = useState<ViewName>("body");
  const [metric, setMetric] = useState<Metric>("mass");
  const [backdrop, setBackdrop] = useState(true);
  const [picked, setPicked] = useState<string | null>(null);

  const segments = useMemo(() => {
    try {
      return analyseSubject(subject);
    } catch {
      return [];
    }
  }, [subject]);

  /** region -> value, for the chosen metric. */
  const heat = useMemo(() => {
    if (metric === "none") return {};
    const out: Record<string, number> = {};
    for (const s of segments) {
      if (!s.region) continue;
      const v =
        metric === "mass" ? s.massKg
        : metric === "inertia" ? s.inertiaCmKgM2
        : s.lengthM;
      if (v === null || v === undefined || !Number.isFinite(v)) continue;
      out[s.region] = Math.max(out[s.region] ?? 0, v);
    }
    return out;
  }, [segments, metric]);

  /**
   * Compartments of the loaded program that bind to each region.
   *
   * A circuit names compartments; the anthropometry names segments; the
   * illustration names regions. This is where the three meet, and a region
   * with no compartment is as informative as one with several.
   */
  const compartmentsByRegion = useMemo(() => {
    const out: Record<string, string[]> = {};
    const seen = new Set<string>();
    for (const a of arms) {
      for (const name of a.circuit.compartments.keys()) {
        if (seen.has(name)) continue;
        seen.add(name);
        const r = resolveRegion(name, view);
        if (!r) continue;
        (out[r] ??= []).push(name);
      }
    }
    return out;
  }, [arms, view]);

  const values = Object.values(heat);
  const unit = METRICS.find((m) => m.id === metric)?.unit ?? "";

  const pickedSegments = picked ? segments.filter((s) => s.region === picked) : [];
  const pickedCompartments = picked ? compartmentsByRegion[picked] ?? [] : [];

  // Regions the illustration has but the anthropometry does not cover.
  const uncovered = useMemo(() => {
    const covered = new Set(segments.map((s) => s.region).filter(Boolean) as string[]);
    return allRegions(view).filter((r) => !covered.has(r));
  }, [segments, view]);

  return (
    <div style={{ height: "100%", display: "flex", overflow: "hidden" }}>
      {/* the illustration */}
      <div style={{
        flex: 1, minWidth: 0, overflow: "auto", display: "flex",
        alignItems: "flex-start", justifyContent: "center", padding: 16,
      }}>
        <AnatomyFigure
          theme={theme}
          heat={heat}
          view={view}
          width={430}
          height={730}
          backdrop={backdrop}
          selected={picked ? [picked] : []}
          onPick={(r) => setPicked((cur) => (cur === r ? null : r))}
          unit={unit}
        />
      </div>

      {/* controls and the readout */}
      <div style={{
        width: 300, flexShrink: 0, borderLeft: `1px solid ${theme.border}`,
        background: theme.panelBg, overflow: "auto", padding: 12,
      }}>
        <Section theme={theme} title="VIEW">
          <div style={{ display: "flex", gap: 4 }}>
            {(["body", "organs"] as ViewName[]).map((v) => (
              <button key={v} onClick={() => { setView(v); setPicked(null); }} style={{
                ...btn(theme), flex: 1,
                background: view === v ? theme.surfaceBg : "transparent",
                color: view === v ? theme.text : theme.textDim,
              }}>{v}</button>
            ))}
          </div>
          <label style={{
            display: "flex", gap: 6, alignItems: "center", marginTop: 8,
            fontSize: 11, color: theme.textDim, cursor: "pointer",
          }}>
            <input type="checkbox" checked={backdrop}
              onChange={(e) => setBackdrop(e.target.checked)}
              style={{ accentColor: theme.keyword }} />
            illustration backdrop
          </label>
        </Section>

        <Section theme={theme} title="COLOUR BY">
          {METRICS.map((m) => (
            <button key={m.id} onClick={() => setMetric(m.id)} style={{
              display: "block", width: "100%", textAlign: "left",
              padding: "4px 8px", marginBottom: 3, borderRadius: 4,
              border: "none", cursor: "pointer", fontFamily: "inherit", fontSize: 11,
              background: metric === m.id ? theme.surfaceBg : "transparent",
              color: metric === m.id ? theme.text : theme.textDim,
            }}>{m.label}</button>
          ))}
          {values.length > 0 && (
            <div style={{ marginTop: 8 }}>
              <HeatLegend theme={theme} lo={Math.min(...values)} hi={Math.max(...values)}
                unit={unit} width={264} />
            </div>
          )}
        </Section>

        <Section theme={theme} title="REGION">
          {!picked ? (
            <div style={{ fontSize: 11, color: theme.textMuted, lineHeight: 1.6 }}>
              Click a region to see what the model knows about it.
            </div>
          ) : (
            <>
              <div style={{
                fontFamily: "monospace", fontSize: 12, color: theme.text,
                fontWeight: 600, marginBottom: 2,
              }}>
                {regionLabel(picked) ?? picked}
              </div>
              <div style={{ fontFamily: "monospace", fontSize: 10, color: theme.textMuted, marginBottom: 8 }}>
                {picked}
              </div>

              {pickedSegments.length ? (
                pickedSegments.map((s) => (
                  <div key={s.segment} style={{ marginBottom: 8 }}>
                    <div style={{ fontSize: 10.5, color: theme.accent, fontFamily: "monospace" }}>
                      {s.segment}{s.paired ? " (per side)" : ""}
                    </div>
                    <Row theme={theme} k="mass" v={`${s.massKg.toFixed(3)} kg`} />
                    <Row theme={theme} k="length"
                      v={Number.isFinite(s.lengthM) ? `${s.lengthM.toFixed(4)} m` : "—"} />
                    <Row theme={theme} k="length from" v={s.lengthSource} />
                    <Row theme={theme} k="CM from prox"
                      v={Number.isFinite(s.cmFromProximalM) ? `${s.cmFromProximalM.toFixed(4)} m` : "—"} />
                    <Row theme={theme} k="I about CM"
                      v={s.inertiaCmKgM2 === null ? "—" : `${s.inertiaCmKgM2.toExponential(3)} kg m2`} />
                    <div style={{ fontSize: 9.5, color: theme.textMuted, marginTop: 2, lineHeight: 1.45 }}>
                      {s.endpoints[0]} → {s.endpoints[1]}
                    </div>
                  </div>
                ))
              ) : (
                <div style={{ fontSize: 10.5, color: theme.textMuted, lineHeight: 1.55, marginBottom: 8 }}>
                  No anthropometric segment covers this region. The
                  illustration is finer than the segment model: it separates
                  parts the {subject.model} table treats as one, or does not
                  treat at all.
                </div>
              )}

              <div style={{ fontSize: 10, color: theme.textDim, marginTop: 6 }}>
                circuit compartments here
              </div>
              {pickedCompartments.length ? (
                <div style={{ fontFamily: "monospace", fontSize: 10.5, color: theme.text }}>
                  {pickedCompartments.join(", ")}
                </div>
              ) : (
                <div style={{ fontSize: 10.5, color: theme.textMuted }}>
                  none in the loaded program
                </div>
              )}
            </>
          )}
        </Section>

        <Section theme={theme} title="COVERAGE">
          <Row theme={theme} k="regions" v={String(allRegions(view).length)} />
          <Row theme={theme} k="with a segment"
            v={String(allRegions(view).length - uncovered.length)} />
          <div style={{ fontSize: 9.5, color: theme.textMuted, marginTop: 6, lineHeight: 1.5 }}>
            The illustration draws {allRegions(view).length} regions in this
            view; the {subject.model} table covers{" "}
            {allRegions(view).length - uncovered.length}. The remainder are
            drawn as outlines and carry no value, which is the honest state
            rather than a gap to be filled by interpolation.
          </div>
        </Section>
      </div>
    </div>
  );
}

const btn = (t: Theme) => ({
  background: "transparent", border: `1px solid ${t.border}`, color: t.text,
  padding: "3px 8px", borderRadius: 3, fontSize: 11, cursor: "pointer",
  fontFamily: "inherit" as const,
});

function Section({ theme, title, children }: {
  theme: Theme; title: string; children: React.ReactNode;
}) {
  return (
    <div style={{ marginBottom: 14, paddingBottom: 12, borderBottom: `1px solid ${theme.border}` }}>
      <div style={{
        fontSize: 9.5, letterSpacing: 1, fontWeight: 700,
        color: theme.textDim, marginBottom: 7,
      }}>{title}</div>
      {children}
    </div>
  );
}

function Row({ theme, k, v }: { theme: Theme; k: string; v: string }) {
  return (
    <div style={{
      display: "flex", justifyContent: "space-between", gap: 8,
      fontFamily: "monospace", fontSize: 10.5, padding: "1px 0",
    }}>
      <span style={{ color: theme.textDim }}>{k}</span>
      <span style={{ color: theme.text, textAlign: "right" }}>{v}</span>
    </div>
  );
}
