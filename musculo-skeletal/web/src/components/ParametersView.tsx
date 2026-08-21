/**
 * The parameters view: a sunburst over everything the tool knows about the
 * subject and the run, with the anatomical reference figure at its centre.
 *
 * The sunburst replaces click-through navigation. Every parameter is an arc,
 * visible at once; hovering reads it out and lights the body where it lives.
 */

import { useMemo, useState } from "react";
import { Sunburst } from "./Sunburst";
import { buildParamTree } from "../lang/paramTree";
import { analyseSubject, type BspModel, type Sex, type Subject } from "../lang/bsp";
import type { ParamNode } from "../lang/parameters";
import type { ArmResult } from "../lang/runtime";
import type { Theme } from "../theme";

interface Props {
  theme: Theme;
  arms: ArmResult[];
  subject: Subject;
  onSubjectChange: (s: Subject) => void;
}

export function ParametersView({ theme, arms, subject, onSubjectChange }: Props) {
  const [picked, setPicked] = useState<{ node: ParamNode; path: string[] } | null>(null);

  const error = useMemo(() => {
    try {
      analyseSubject(subject);
      return null;
    } catch (e) {
      return (e as Error).message;
    }
  }, [subject]);

  const tree = useMemo(() => {
    if (error) return { name: "parameters", children: [] } as ParamNode;
    return buildParamTree({ subject, arms });
  }, [subject, arms, error]);

  return (
    <div style={{ height: "100%", display: "flex", overflow: "hidden" }}>
      <div style={{
        width: 250, flexShrink: 0, borderRight: `1px solid ${theme.border}`,
        padding: 12, overflow: "auto", background: theme.panelBg,
      }}>
        <div style={{ fontSize: 9.5, letterSpacing: 1, fontWeight: 700, color: theme.textDim, marginBottom: 8 }}>
          SUBJECT
        </div>

        <Field theme={theme} label={`mass ${subject.massKg} kg`}>
          <input type="range" min={35} max={140} step={1} value={subject.massKg}
            onChange={(e) => onSubjectChange({ ...subject, massKg: +e.target.value })}
            style={{ width: "100%", accentColor: theme.keyword }} />
        </Field>
        <Field theme={theme} label={`stature ${subject.statureM.toFixed(2)} m`}>
          <input type="range" min={1.4} max={2.1} step={0.01} value={subject.statureM}
            onChange={(e) => onSubjectChange({ ...subject, statureM: +e.target.value })}
            style={{ width: "100%", accentColor: theme.keyword }} />
        </Field>
        <Field theme={theme} label="sex">
          <div style={{ display: "flex", gap: 4 }}>
            {(["male", "female"] as Sex[]).map((s) => (
              <button key={s} onClick={() => onSubjectChange({ ...subject, sex: s })} style={{
                ...btn(theme), flex: 1,
                background: subject.sex === s ? theme.surfaceBg : "transparent",
                color: subject.sex === s ? theme.text : theme.textDim,
              }}>{s}</button>
            ))}
          </div>
        </Field>
        <Field theme={theme} label="model">
          <div style={{ display: "flex", gap: 4 }}>
            {(["deLeva", "dempster"] as BspModel[]).map((m) => (
              <button key={m} onClick={() => onSubjectChange({ ...subject, model: m })} style={{
                ...btn(theme), flex: 1,
                background: subject.model === m ? theme.surfaceBg : "transparent",
                color: subject.model === m ? theme.text : theme.textDim,
              }}>{m}</button>
            ))}
          </div>
        </Field>

        {error && (
          <div style={{
            marginTop: 10, padding: "7px 9px", borderRadius: 4, fontSize: 10.5,
            fontFamily: "monospace", lineHeight: 1.5,
            background: `${theme.open}0e`, color: theme.open,
            border: `1px solid ${theme.open}22`,
          }}>{error}</div>
        )}

        <div style={{ fontSize: 10, color: theme.textMuted, marginTop: 12, lineHeight: 1.55 }}>
          de Leva (1996) adjusts Zatsiorsky–Seluyanov and has male and female
          tables. Dempster (1955), as tabulated by Winter, comes from eight
          elderly male cadavers and has no female data at all. Their segment
          definitions differ, so the two are never mixed.
        </div>

        {picked && (
          <div style={{ marginTop: 14, paddingTop: 12, borderTop: `1px solid ${theme.border}` }}>
            <div style={{ fontSize: 9.5, letterSpacing: 1, fontWeight: 700, color: theme.textDim, marginBottom: 6 }}>
              SELECTED
            </div>
            <div style={{ fontSize: 10, fontFamily: "monospace", color: theme.textDim, lineHeight: 1.5 }}>
              {picked.path.join(" › ")}
            </div>
            {picked.node.derivation && (
              <div style={{ fontSize: 9.5, fontFamily: "monospace", color: theme.textMuted, marginTop: 4, lineHeight: 1.5 }}>
                {picked.node.derivation}
              </div>
            )}
          </div>
        )}
      </div>

      <div style={{ flex: 1, minWidth: 0, overflow: "auto", display: "flex", justifyContent: "center", padding: 16 }}>
        {error ? (
          <div style={{ alignSelf: "center", maxWidth: 380, textAlign: "center", fontSize: 12, color: theme.textMuted, lineHeight: 1.6 }}>
            No parameters: the chosen model does not cover this subject.
          </div>
        ) : (
          <Sunburst
            theme={theme}
            root={tree}
            size={560}
            onSelect={(node, path) => setPicked({ node, path })}
          />
        )}
      </div>
    </div>
  );
}

const btn = (t: Theme) => ({
  background: "transparent", border: `1px solid ${t.border}`, color: t.text,
  padding: "3px 8px", borderRadius: 3, fontSize: 11, cursor: "pointer",
  fontFamily: "inherit" as const,
});

function Field({ theme, label, children }: { theme: Theme; label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 9 }}>
      <div style={{ fontSize: 10, color: theme.textDim, marginBottom: 3 }}>{label}</div>
      {children}
    </div>
  );
}
