/**
 * Vitruvius IDE.
 *
 * The program is compiled by the real lexer, parser, and checker on every
 * keystroke (debounced), so the static analyses -- closure, compartment,
 * stratum, floor -- are live before anything is run. Execution is a separate
 * act, because that is the architecture the language commits to: diagnostics
 * cost a parse, integration costs a run.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnatomyView } from "./components/AnatomyView";
import { BodyMapView } from "./components/BodyMapView";
import { ApertureView } from "./components/ApertureView";
import { CircuitView } from "./components/CircuitView";
import { CompareView } from "./components/CompareView";
import { Editor } from "./components/Editor";
import { PhaseView } from "./components/PhaseView";
import { ParametersView } from "./components/ParametersView";
import { PostureView } from "./components/PostureView";
import { AnatomyFigure } from "./components/AnatomyFigure";
import { analyseSubject, type Subject } from "./lang/bsp";
import { ResultsView } from "./components/ResultsView";
import { SpectraView } from "./components/SpectraView";
import { Backend } from "./lang/backend";
import { apertureReport, apertures, closureIndex } from "./lang/circuit";
import { OBSERVABLES } from "./lang/observables";
import {
  Runtime, allArms, compile, evalCircuitExpr, type ArmResult,
  type CompileResult, type ExperimentResult, type RunResult,
} from "./lang/runtime";
import PROGRAMS from "./data/programs.json";
import { DARK, LIGHT, MONO, SANS, type Theme } from "./theme";

type TabId = "circuit" | "bodymap" | "anatomy" | "posture" | "parameters" | "spectra" | "phase" | "results" | "compare" | "aperture";

const TABS: { id: TabId; label: string; needsRun: boolean }[] = [
  { id: "circuit", label: "Circuit", needsRun: false },
  { id: "bodymap", label: "Body map", needsRun: false },
  { id: "anatomy", label: "Anatomy", needsRun: false },
  { id: "posture", label: "Posture", needsRun: false },
  { id: "parameters", label: "Parameters", needsRun: false },
  { id: "spectra", label: "Spectra", needsRun: true },
  { id: "phase", label: "State space", needsRun: true },
  { id: "results", label: "Results", needsRun: true },
  { id: "compare", label: "Compare", needsRun: true },
  { id: "aperture", label: "Aperture", needsRun: false },
];

/** Tabs that show results and therefore carry the reference figure. */
const RESULT_TABS = new Set<TabId>(["spectra", "phase", "results", "compare", "aperture"]);

// Tabs that are themselves anatomical. A second small body drawn over them
// competes with the view rather than orienting the reader.
const ANATOMICAL_TABS = new Set<TabId>(["bodymap", "anatomy", "posture", "parameters"]);

const PROG = PROGRAMS as Record<string, string>;
const PROG_NAMES = Object.keys(PROG).sort();

export default function App() {
  const [dark, setDark] = useState(true);
  const T: Theme = dark ? DARK : LIGHT;

  const [progName, setProgName] = useState(PROG_NAMES[0]);
  const [code, setCode] = useState(PROG[PROG_NAMES[0]] ?? "");
  const [compiled, setCompiled] = useState<CompileResult>(() => compile(code));
  const [run, setRun] = useState<RunResult | null>(null);
  const [running, setRunning] = useState(false);
  const [tab, setTab] = useState<TabId>("circuit");
  const [expIdx, setExpIdx] = useState(0);
  const [armName, setArmName] = useState("intact");
  const [selectedArms, setSelectedArms] = useState<Set<string>>(new Set());
  const [split, setSplit] = useState(0.40);
  const [dragging, setDragging] = useState(false);
  const [animate, setAnimate] = useState(true);
  const [seed, setSeed] = useState(0);
  const [duration, setDuration] = useState(20);
  const [showDiag, setShowDiag] = useState(true);
  /** The subject the anthropometry is built from. Every downstream mass and
   *  inertia scales from this rather than from a hard-coded constant. */
  const [subject, setSubject] = useState<Subject>({
    massKg: 83, statureM: 1.85, sex: "male", model: "deLeva",
  });
  const shellRef = useRef<HTMLDivElement>(null);

  // Debounced compile on edit: static analyses are live.
  useEffect(() => {
    const id = setTimeout(() => setCompiled(compile(code)), 220);
    return () => clearTimeout(id);
  }, [code]);

  // Editing invalidates a previous run.
  useEffect(() => { setRun(null); }, [code, seed, duration]);

  const diagnostics = compiled.checked?.diagnostics ?? [];
  const errors = compiled.checked?.errors ?? [];
  const warnings = compiled.checked?.warnings ?? [];

  const experiments: ExperimentResult[] = run?.experiments ?? [];
  const current = experiments[expIdx];

  /**
   * Arms are available before a run: the checker already built every
   * circuit, and closure is decided from the declaration alone. Only the
   * observation store needs the backend.
   */
  const arms: ArmResult[] = useMemo(() => {
    if (current) return allArms(current);
    const ck = compiled.checked;
    const x = compiled.program?.experiments[expIdx];
    if (!ck || !x) return [];

    const mk = (name: string, expr: any): ArmResult | null => {
      const c = evalCircuitExpr(expr, ck);
      if (!c) return null;
      return {
        name, circuit: c, closure: closureIndex(c),
        apertures: apertures(c).map(apertureReport),
        store: new Map(), record: 0, provenance: [...c.provenance],
      };
    };

    const out: ArmResult[] = [];
    const intact = mk("intact", x.intact);
    if (intact) out.push(intact);
    const groups = x.phases.length
      ? x.phases.flatMap((p) => p.lesions)
      : x.lesions;
    for (const l of groups) {
      const a = mk(l.name, l.expr);
      if (a) out.push(a);
    }
    return out;
  }, [current, compiled, expIdx]);

  useEffect(() => {
    if (arms.length && !arms.find((a) => a.name === armName)) setArmName(arms[0].name);
    if (arms.length) {
      setSelectedArms((prev) => {
        const valid = new Set([...prev].filter((n) => arms.some((a) => a.name === n)));
        // Default to every arm: a comparison view showing one series is
        // not a comparison.
        return valid.size === arms.length ? valid : new Set(arms.map((a) => a.name));
      });
    }
  }, [arms, armName]);

  const doRun = useCallback(() => {
    if (!compiled.program || !compiled.checked) return;
    setRunning(true);
    // Yield so the button state paints before the integrator blocks.
    setTimeout(() => {
      try {
        const backend = new Backend(2e-3, duration, seed);
        const r = new Runtime(compiled.program!, compiled.checked!, backend).run();
        setRun(r);
        setExpIdx((i) => Math.min(i, Math.max(0, r.experiments.length - 1)));
        setTab((t) => (t === "circuit" || t === "aperture" ? t : "results"));
      } finally {
        setRunning(false);
      }
    }, 10);
  }, [compiled, seed, duration]);

  // Ctrl/Cmd+Enter runs.
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") { e.preventDefault(); doRun(); }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [doRun]);

  // Splitter drag.
  useEffect(() => {
    if (!dragging) return;
    const move = (e: MouseEvent) => {
      const r = shellRef.current?.getBoundingClientRect();
      if (!r) return;
      setSplit(Math.max(0.2, Math.min(0.72, (e.clientX - r.left) / r.width)));
    };
    const up = () => setDragging(false);
    window.addEventListener("mousemove", move);
    window.addEventListener("mouseup", up);
    return () => { window.removeEventListener("mousemove", move); window.removeEventListener("mouseup", up); };
  }, [dragging]);

  const loadProgram = (name: string) => {
    setProgName(name);
    setCode(PROG[name] ?? "");
    setRun(null);
    setExpIdx(0);
  };

  const exportJson = () => {
    if (!run) return;
    const payload = {
      provenance: {
        schema: "vitruvius-results/1",
        program: progName,
        seed, durationS: duration,
        elapsedMs: Math.round(run.elapsedMs),
        steps: run.steps,
      },
      diagnostics: diagnostics.map((d) => ({
        severity: d.severity, rule: d.rule, message: d.message, line: d.span?.line ?? null,
      })),
      experiments: run.experiments.map((x) => ({
        experiment: x.name,
        phased: x.phased,
        arms: allArms(x).map((a) => ({
          arm: a.name,
          closureIndex: a.closure,
          committedRecord: a.record,
          lesionsApplied: a.provenance,
          apertures: a.apertures,
          observations: Object.fromEntries([...a.store].map(([k, m]) => [k, {
            value: typeof m.value === "number" && !Number.isFinite(m.value) ? null : m.value,
            unit: m.unit,
            undefined: typeof m.value === "number" && !Number.isFinite(m.value),
            note: m.note ?? null,
            backendReport: {
              floorUsed: m.report.floorUsed, bandHz: m.report.band,
              seed: m.report.seed, nSamples: m.report.nSamples, dtS: m.report.dt,
            },
          }])),
        })),
      })),
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${progName}.results.json`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const btn = (active: boolean): React.CSSProperties => ({
    background: active ? T.keyword : T.surfaceBg,
    color: active ? (dark ? T.editorBg : "#fff") : T.textDim,
    border: `1px solid ${active ? T.keyword : T.border}`,
    padding: "3px 12px", borderRadius: 3, fontSize: 11, fontWeight: 600,
    cursor: "pointer", fontFamily: SANS,
  });

  const sel: React.CSSProperties = {
    background: T.surfaceBg, color: T.text, border: `1px solid ${T.border}`,
    borderRadius: 3, fontSize: 11, padding: "3px 6px", fontFamily: MONO,
  };

  const intactCircuit = current
    ? compiled.checked?.circuits.get(
        (compiled.program?.experiments[expIdx]?.intact as any)?.name ?? "",
      ) ?? null
    : null;

  /** The binding declared in the source, for the circuit the selected arm
   *  derives from. Anatomy is only available when the program asks for it. */
  const bindSpec = useMemo(() => {
    const binds = compiled.program?.binds ?? [];
    if (!binds.length) return null;
    const base = selectedArmCircuitName(arms, armName);
    const b = binds.find((x) => x.circuit === base) ?? binds[0];
    return {
      rig: b.rig,
      circuit: b.circuit,
      map: b.map,
      conductionVelocity: b.conductionVelocity,
      unitsPerMetre: b.unitsPerMetre,
    };
  }, [compiled.program, arms, armName]);

  /** Segment mass per region, for the corner reference figure. This is the
   *  one quantity that is always defined regardless of what has been run, so
   *  the figure orients the reader even before a run. */
  const segmentHeat = useMemo(() => {
    try {
      const out: Record<string, number> = {};
      for (const seg of analyseSubject(subject)) {
        if (!seg.region) continue;
        out[seg.region] = Math.max(out[seg.region] ?? 0, seg.massKg);
      }
      return out;
    } catch {
      return {};
    }
  }, [subject]);

  const selectedArm = arms.find((a) => a.name === armName) ?? arms[0];

  return (
    <div style={{
      width: "100vw", height: "100vh", display: "flex", flexDirection: "column",
      background: T.bg, color: T.text, fontFamily: SANS, overflow: "hidden",
    }}>
      {/* title bar */}
      <div style={{
        height: 38, background: T.editorBg, borderBottom: `1px solid ${T.border}`,
        display: "flex", alignItems: "center", padding: "0 12px", gap: 12, flexShrink: 0,
      }}>
        {/* Back to the landing page. The IDE is reachable directly, so a
            visitor can arrive here without ever seeing what the tool is. */}
        <a
          href="./index.html"
          title="About Vitruvius"
          style={{
            fontSize: 12, fontWeight: 700, color: T.keyword, letterSpacing: 1.4,
            textDecoration: "none",
          }}
        >
          VITRUVIUS
        </a>
        <select value={progName} onChange={(e) => loadProgram(e.target.value)} style={sel}>
          {PROG_NAMES.map((n) => <option key={n} value={n}>{n}.vvs</option>)}
        </select>

        <span style={{
          fontSize: 10.5, fontFamily: MONO,
          color: errors.length ? T.error : warnings.length ? T.warn : T.ok,
        }}>
          {compiled.parseError
            ? "parse error"
            : errors.length
            ? `${errors.length} error${errors.length > 1 ? "s" : ""}`
            : `typechecks · ${warnings.length} warning${warnings.length === 1 ? "" : "s"}`}
        </span>

        <div style={{ flex: 1 }} />

        <label style={{ fontSize: 10.5, color: T.textDim, display: "flex", gap: 5, alignItems: "center" }}>
          seed
          <input type="number" value={seed} onChange={(e) => setSeed(+e.target.value)}
            style={{ ...sel, width: 52 }} />
        </label>
        <label style={{ fontSize: 10.5, color: T.textDim, display: "flex", gap: 5, alignItems: "center" }}>
          dur
          <input type="number" value={duration} min={2} max={90}
            onChange={(e) => setDuration(Math.max(2, +e.target.value))}
            style={{ ...sel, width: 48 }} />s
        </label>

        <button onClick={() => setDark((d) => !d)} style={{ ...btn(false), padding: "3px 9px" }}>
          {dark ? "☾" : "☀"}
        </button>
        {run && <button onClick={exportJson} style={btn(false)}>Export JSON</button>}
        <button onClick={doRun} disabled={!compiled.checked || !!compiled.parseError || running}
          style={{
            ...btn(true),
            opacity: !compiled.checked || compiled.parseError ? 0.45 : 1,
            cursor: !compiled.checked || compiled.parseError ? "not-allowed" : "pointer",
          }}>
          {running ? "Running…" : run ? "↻ Re-run  ⌘↵" : "▶ Run  ⌘↵"}
        </button>
      </div>

      {/* main */}
      <div ref={shellRef} style={{ flex: 1, display: "flex", overflow: "hidden", minHeight: 0 }}>
        <div style={{ width: `${split * 100}%`, minWidth: 240, overflow: "hidden" }}>
          <Editor code={code} onChange={setCode} diagnostics={diagnostics} theme={T}
            parseError={compiled.parseError} parseLine={compiled.parseLine} />
        </div>

        <div onMouseDown={() => setDragging(true)} style={{
          width: 4, background: dragging ? T.keyword : T.border,
          cursor: "col-resize", flexShrink: 0,
        }} />

        <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", background: T.panelBg, minWidth: 0 }}>
          {/* tab bar */}
          <div style={{
            display: "flex", alignItems: "center", borderBottom: `1px solid ${T.border}`,
            background: T.editorBg, flexShrink: 0, gap: 2, paddingRight: 8,
          }}>
            {TABS.map((t) => {
              const disabled = t.needsRun && !run;
              return (
                <button key={t.id} disabled={disabled} onClick={() => setTab(t.id)} style={{
                  padding: "8px 14px", border: "none",
                  borderBottom: `2px solid ${tab === t.id ? T.keyword : "transparent"}`,
                  background: "transparent",
                  color: disabled ? T.textMuted : tab === t.id ? T.text : T.textDim,
                  fontSize: 11, fontWeight: tab === t.id ? 600 : 400,
                  cursor: disabled ? "not-allowed" : "pointer", fontFamily: SANS,
                }}>{t.label}</button>
              );
            })}

            {experiments.length > 1 && (
              <select value={expIdx} onChange={(e) => setExpIdx(+e.target.value)}
                style={{ ...sel, marginLeft: 8 }}>
                {experiments.map((x, i) => <option key={x.name} value={i}>{x.name}</option>)}
              </select>
            )}

            <div style={{ flex: 1 }} />

            {tab === "circuit" && (
              <>
                <label style={{ fontSize: 10, color: T.textDim, display: "flex", gap: 4, alignItems: "center" }}>
                  <input type="checkbox" checked={animate} onChange={() => setAnimate((a) => !a)}
                    style={{ accentColor: T.keyword, width: 12, height: 12 }} />
                  flow
                </label>
                {arms.map((a) => (
                  <span key={a.name} onClick={() => setArmName(a.name)} style={{
                    padding: "2px 9px", borderRadius: 3, fontSize: 10, cursor: "pointer",
                    fontFamily: MONO,
                    background: armName === a.name ? T.surfaceBg : "transparent",
                    color: a.closure === "open" ? T.open : T.closed,
                    border: `1px solid ${armName === a.name ? (a.closure === "open" ? T.open : T.closed) + "77" : "transparent"}`,
                  }}>{a.closure === "open" ? "◇" : "●"} {a.name}</span>
                ))}
              </>
            )}
          </div>

          {/* content */}
          <div style={{ flex: 1, overflow: "hidden", minHeight: 0, position: "relative" }}>
            {/* Reference figure, top right of every RESULTS page.
                Not on Parameters (which has its own, larger, at the sunburst
                centre) nor on Anatomy/Posture (which are already anatomical),
                because a second small body there would compete rather than
                orient. */}
            {RESULT_TABS.has(tab) && !ANATOMICAL_TABS.has(tab) && (
              <div style={{
                position: "absolute", top: 8, right: 10, zIndex: 5,
                padding: "5px 7px", borderRadius: 5,
                background: `${T.panelBg}e8`, border: `1px solid ${T.border}`,
                pointerEvents: "none",
              }}>
                <AnatomyFigure
                  theme={T}
                  heat={segmentHeat}
                  width={52}
                  height={88}
                  caption="segment mass"
                  unit="kg"
                />
              </div>
            )}
            {!run && tab !== "circuit" && tab !== "aperture" && tab !== "anatomy" && tab !== "posture" && tab !== "parameters" && tab !== "bodymap" ? (
              <Placeholder T={T} hasErrors={!!errors.length || !!compiled.parseError} />
            ) : !run && !arms.length ? (
              <Placeholder T={T} hasErrors={!!errors.length || !!compiled.parseError}
                note="Static analyses are already complete. Run to discharge observables." />
            ) : tab === "circuit" && selectedArm ? (
              <CircuitView arm={selectedArm} intact={intactCircuit} theme={T} animate={animate} />
            ) : tab === "bodymap" ? (
              <BodyMapView theme={T} subject={subject} arms={arms} />
            ) : tab === "anatomy" ? (
              <AnatomyView
                theme={T}
                arms={arms.map((a) => ({
                  name: a.name,
                  closure: a.closure,
                  circuit: a.circuit,
                  divergenceTime:
                    (a.store?.get("divergence_time")?.value as number | null) ?? null,
                }))}
                selectedArm={armName}
                onSelectArm={setArmName}
                bindSpec={bindSpec}
                backend={run?.backend ?? new Backend(2e-3, duration, seed)}
              />
            ) : tab === "parameters" ? (
              <ParametersView theme={T} arms={arms} subject={subject} onSubjectChange={setSubject} />
            ) : tab === "posture" ? (
              <PostureView
                theme={T}
                onGenerate={(src) => {
                  // The generated program replaces the editor contents and the
                  // view switches to Circuit, so the record's own claim can be
                  // run immediately against the record it came from.
                  setCode(src);
                  setRun(null);
                  setExpIdx(0);
                  setTab("circuit");
                }}
              />
            ) : tab === "spectra" && run ? (
              <SpectraView arms={arms} backend={run.backend} theme={T}
                selected={selectedArms}
                onToggle={(n) => setSelectedArms((p) => {
                  const s = new Set(p); s.has(n) ? s.delete(n) : s.add(n); return s;
                })} />
            ) : tab === "phase" && run ? (
              <PhaseView arms={arms} backend={run.backend} theme={T} selected={selectedArms} />
            ) : tab === "results" ? (
              <ResultsView arms={arms} theme={T} />
            ) : tab === "compare" ? (
              <CompareView arms={arms} theme={T} />
            ) : tab === "aperture" ? (
              <ApertureView arms={arms} theme={T} />
            ) : (
              <Placeholder T={T} hasErrors={false} />
            )}
          </div>
        </div>
      </div>

      {/* diagnostics */}
      <div style={{
        borderTop: `1px solid ${T.border}`, background: T.editorBg, flexShrink: 0,
        height: showDiag ? 132 : 26, display: "flex", flexDirection: "column",
      }}>
        <div style={{
          height: 26, display: "flex", alignItems: "center", gap: 12,
          padding: "0 12px", fontSize: 10.5, color: T.textDim, cursor: "pointer",
          borderBottom: showDiag ? `1px solid ${T.borderSoft}` : "none",
        }} onClick={() => setShowDiag((s) => !s)}>
          <span style={{ fontWeight: 600 }}>{showDiag ? "▾" : "▸"} DIAGNOSTICS</span>
          <span style={{ color: T.error }}>● {errors.length}</span>
          <span style={{ color: T.warn }}>▲ {warnings.length}</span>
          <span style={{ color: T.note }}>○ {diagnostics.filter((d) => d.severity === "note").length}</span>
          {run && (
            <span style={{ marginLeft: "auto", fontFamily: MONO, color: T.textMuted }}>
              {run.steps} steps · {Math.round(run.elapsedMs)} ms · seed {seed}
            </span>
          )}
        </div>
        {showDiag && (
          <div style={{ flex: 1, overflow: "auto", padding: "5px 12px", fontFamily: MONO, fontSize: 10.5, lineHeight: 1.65 }}>
            {compiled.parseError && (
              <div style={{ color: T.error }}>● parse: {compiled.parseError}</div>
            )}
            {diagnostics.length === 0 && !compiled.parseError && (
              <div style={{ color: T.ok }}>
                ✓ closure, compartment, stratum, and floor analyses pass; no apertures declared
              </div>
            )}
            {diagnostics.map((d, i) => (
              <div key={i} style={{
                color: d.severity === "error" ? T.error : d.severity === "warning" ? T.warn : T.note,
              }}>
                <span style={{ marginRight: 6 }}>
                  {d.severity === "error" ? "●" : d.severity === "warning" ? "▲" : "○"}
                </span>
                {d.span && <span style={{ color: T.textMuted }}>L{d.span.line} </span>}
                <span style={{ opacity: 0.75 }}>{d.rule}</span>: {d.message}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function Placeholder({ T, hasErrors, note }: { T: Theme; hasErrors: boolean; note?: string }) {
  return (
    <div style={{
      height: "100%", display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center", gap: 10, padding: 24,
    }}>
      <div style={{ fontSize: 44, opacity: 0.13, color: T.text }}>◇</div>
      <div style={{ fontSize: 12.5, color: T.textDim }}>
        {hasErrors ? "Fix the errors below, then run." : "Press ▶ Run (⌘↵) to discharge observables."}
      </div>
      <div style={{ fontSize: 11, color: T.textMuted, maxWidth: 380, textAlign: "center", lineHeight: 1.6 }}>
        {note ??
          "Closure, compartment, stratum, and floor analyses are computed from the declaration alone and are already live. Integration is what the run adds."}
      </div>
    </div>
  );
}

/** The circuit a lesioned arm derives from, so a binding declared on the base
 *  circuit applies to every arm of the experiment.
 *
 *  `cloneCircuit` carries `name` through every lesion operator unchanged --
 *  provenance records the operators applied, not the base -- so the name is
 *  what identifies the circuit a binding was declared against. */
function selectedArmCircuitName(arms: ArmResult[], armName: string): string {
  const a = arms.find((x) => x.name === armName) ?? arms[0];
  return a ? a.circuit.name : "";
}
