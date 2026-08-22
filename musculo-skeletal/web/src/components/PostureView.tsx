/**
 * Posture view: read a rig's motion as a sway record, decompose it, account
 * for the charge it carries, and generate the Vitruvius source that would
 * reproduce it.
 *
 * This is the direction the tool did not previously have. Everywhere else the
 * program is the input and the model is the output. Here a pose stream is the
 * input and a program is the output -- which means the model can be posed or
 * animated and the code that explains it falls out.
 *
 * The panel's job is as much refusal as reporting. A 2-second clip produces a
 * rambling number, and it is meaningless; a looped clip produces a spectral
 * peak, and it belongs to the loop. Both are surfaced before any result.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { removeLoopDrift, sampleClip, type ClipSample } from "../lang/clip";
import {
  analyseSleep, BANDS, bandPower, chargeOfMotion, decompose, dominantFrequency,
  synthesiseVvs, type ChargeAccount, type Decomposition, type SleepAnalysis,
} from "../lang/posture";
import { getRig } from "../lang/binding";
import type { Theme } from "../theme";

const CACHE = new Map<string, Promise<{ scene: THREE.Group; clips: THREE.AnimationClip[] }>>();

function loadRig(name: string) {
  const hit = CACHE.get(name);
  if (hit) return hit;
  const p = new Promise<{ scene: THREE.Group; clips: THREE.AnimationClip[] }>((res, rej) => {
    new GLTFLoader().load(
      // Root-absolute, not relative: a relative URL resolves against the
      // current path, so it would break the moment the app is served from
      // anywhere but the domain root. Vite rewrites this against `base` at
      // build time.
      `${import.meta.env.BASE_URL}models/${name}.glb`,
      (g) => res({ scene: g.scene as THREE.Group, clips: g.animations }),
      undefined,
      rej,
    );
  });
  CACHE.set(name, p);
  return p;
}

type Mode = "posture" | "sleep";

interface Props {
  theme: Theme;
  onGenerate: (source: string) => void;
}

export function PostureView({ theme, onGenerate }: Props) {
  const [rigName, setRigName] = useState("xbot_multiple_animations");
  const [clips, setClips] = useState<THREE.AnimationClip[]>([]);
  const [root, setRoot] = useState<THREE.Group | null>(null);
  const [clipName, setClipName] = useState<string>("");
  const [jointName, setJointName] = useState("mixamorig:Hips_01");
  const [axis, setAxis] = useState<"x" | "y" | "z" | "mag">("z");
  const [durationS, setDurationS] = useState(2);
  const [detrend, setDetrend] = useState(false);
  const [mode, setMode] = useState<Mode>("posture");
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  const rig = getRig(rigName);
  const bindable = rig?.bindable ?? false;

  useEffect(() => {
    if (!bindable) return;
    setStatus("loading");
    let dead = false;
    loadRig(rigName)
      .then(({ scene, clips: cs }) => {
        if (dead) return;
        setRoot(scene);
        setClips(cs);
        setClipName((c) => (cs.some((x) => x.name === c) ? c : (cs[0]?.name ?? "")));
        setStatus("ready");
      })
      .catch((e) => {
        if (dead) return;
        setError(String(e?.message ?? e));
        setStatus("error");
      });
    return () => { dead = true; };
  }, [rigName, bindable]);

  const clip = clips.find((c) => c.name === clipName);

  /** Sample the clip, then run the whole analysis chain. Pure given inputs. */
  const analysis = useMemo(() => {
    if (!root || !clip) return null;
    try {
      let sample: ClipSample = sampleClip(root, clip, {
        jointName, axis, rateHz: 30, durationS,
      });
      if (detrend) sample = removeLoopDrift(sample);

      // The repeat frequency is what the sampling actually produced, which
      // is set by the clip duration -- pass it so the decomposition can tell
      // a real peak from the repetition.
      const artefactHz = sample.singlePass ? undefined : sample.loopArtefactHz;
      const d = decompose(sample, undefined, artefactHz);
      const charge = chargeOfMotion(sample);
      const sleep = mode === "sleep" ? analyseSleep(sample) : undefined;
      return { sample, d, charge, sleep };
    } catch (e) {
      return { error: String((e as Error)?.message ?? e) } as const;
    }
  }, [root, clip, jointName, axis, durationS, detrend, mode]);

  const generate = useCallback(() => {
    if (!analysis || "error" in analysis) return;
    const src = synthesiseVvs({
      circuitName: sanitise(`${clipName}_${axis}`),
      decomposition: analysis.d,
      charge: analysis.charge,
      sleep: analysis.sleep,
      binding: { rig: rigName, map: { periphery: jointName } },
    });
    onGenerate(src);
  }, [analysis, clipName, axis, rigName, jointName, onGenerate]);

  if (!bindable) {
    return (
      <Empty theme={theme}>
        Rig <b>{rigName}</b> has no skin, so it carries no joint motion to read.
        A pose record needs an animated rig.
      </Empty>
    );
  }

  const err = analysis && "error" in analysis ? analysis.error : null;
  const ok = analysis && !("error" in analysis) ? analysis : null;

  return (
    <div style={{ height: "100%", display: "flex", overflow: "hidden" }}>
      {/* controls + readout */}
      <div style={{
        width: 340, flexShrink: 0, borderRight: `1px solid ${theme.border}`,
        overflow: "auto", padding: 12, background: theme.panelBg,
      }}>
        <Section theme={theme} title="RECORD">
          <Field theme={theme} label="rig">
            <select value={rigName} onChange={(e) => setRigName(e.target.value)} style={sel(theme)}>
              {["xbot_multiple_animations", "windows_3d_viewer_flexing_arm"].map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </Field>
          <Field theme={theme} label="clip">
            <select value={clipName} onChange={(e) => setClipName(e.target.value)} style={sel(theme)}>
              {clips.map((c) => (
                <option key={c.name} value={c.name}>
                  {c.name} ({c.duration.toFixed(2)}s)
                </option>
              ))}
            </select>
          </Field>
          <Field theme={theme} label="joint">
            <select value={jointName} onChange={(e) => setJointName(e.target.value)} style={sel(theme)}>
              {(rig?.joints ?? [])
                .filter((j) => !/Hand|Thumb|Index|Middle|Ring|Pinky|Eye/.test(j.name))
                .map((j) => <option key={j.name} value={j.name}>{j.name}</option>)}
            </select>
          </Field>
          <Field theme={theme} label="axis">
            <select value={axis} onChange={(e) => setAxis(e.target.value as typeof axis)} style={sel(theme)}>
              <option value="z">z (anterior-posterior)</option>
              <option value="x">x (medial-lateral)</option>
              <option value="y">y (vertical)</option>
              <option value="mag">magnitude</option>
            </select>
          </Field>
          <Field theme={theme} label={`duration ${durationS.toFixed(1)}s`}>
            <input
              type="range" min={1} max={120} step={1}
              value={durationS}
              onChange={(e) => setDurationS(+e.target.value)}
              style={{ width: "100%", accentColor: theme.keyword }}
            />
          </Field>
          <label style={{ fontSize: 11, color: theme.textDim, display: "flex", gap: 6, alignItems: "center", marginTop: 4 }}>
            <input type="checkbox" checked={detrend} onChange={(e) => setDetrend(e.target.checked)}
              style={{ accentColor: theme.keyword }} />
            remove per-loop drift
          </label>
          <div style={{ display: "flex", gap: 4, marginTop: 8 }}>
            {(["posture", "sleep"] as Mode[]).map((m) => (
              <button key={m} onClick={() => setMode(m)} style={{
                ...btn(theme),
                background: mode === m ? theme.surfaceBg : "transparent",
                color: mode === m ? theme.text : theme.textDim,
              }}>{m}</button>
            ))}
          </div>
        </Section>

        {status === "loading" && <Note theme={theme}>Loading {rigName}…</Note>}
        {status === "error" && <Note theme={theme} bad>Load failed: {error}</Note>}
        {err && <Note theme={theme} bad>{err}</Note>}

        {ok && (
          <>
            {/* Adequacy comes FIRST. Numbers that a record cannot support
                must not be read before the caveat that voids them. */}
            <Section theme={theme} title="WHAT THIS RECORD CAN SUPPORT">
              <Row theme={theme} k="sample rate" v={`${ok.d.adequacy.sampleRateHz.toFixed(1)} Hz`} />
              <Row theme={theme} k="nyquist" v={`${ok.d.adequacy.nyquistHz.toFixed(1)} Hz`} />
              <Row theme={theme} k="duration" v={`${ok.d.adequacy.durationS.toFixed(2)} s`} />
              <Row theme={theme} k="resolvable to" v={`${ok.d.adequacy.lowestResolvableHz.toFixed(3)} Hz`} />
              <Row theme={theme} k="loops" v={ok.sample.singlePass ? "single pass" : `${ok.sample.loops.toFixed(1)}×`}
                colour={ok.sample.singlePass ? theme.closed : theme.accent} />
              <Row theme={theme} k="rambling" v={ok.d.adequacy.ramblingResolvable ? "resolvable" : "NOT resolvable"}
                colour={ok.d.adequacy.ramblingResolvable ? theme.closed : theme.open} />
              {ok.d.adequacy.notes.map((n, i) => (
                <div key={i} style={{
                  marginTop: 6, padding: "6px 8px", borderRadius: 4, fontSize: 10,
                  lineHeight: 1.45, fontFamily: "monospace",
                  background: `${theme.open}0e`, color: theme.open,
                  border: `1px solid ${theme.open}22`,
                }}>{n}</div>
              ))}
            </Section>

            {mode === "posture" ? (
              <Section theme={theme} title="RAMBLING / TREMBLING">
                <Row theme={theme} k="trembling RMS" v={ok.d.tremblingRms.toExponential(3)} />
                <Row theme={theme} k="rambling RMS"
                  v={ok.d.adequacy.ramblingResolvable ? ok.d.ramblingRms.toExponential(3) : "—"}
                  colour={ok.d.adequacy.ramblingResolvable ? undefined : theme.textMuted} />
                <Row theme={theme} k="coupling index"
                  v={ok.d.adequacy.ramblingResolvable ? ok.d.couplingIndex.toFixed(3) : "—"}
                  colour={ok.d.adequacy.ramblingResolvable ? undefined : theme.textMuted} />
                <Row theme={theme} k="trembling band"
                  v={bandPower(ok.d.trembling, ok.sample.dt, BANDS.trembling).toFixed(3)} />
                <Row theme={theme} k="dominant f"
                  v={ok.d.adequacy.dominantIsLoopArtefact
                    ? "ARTEFACT"
                    : `${dominantFrequency(ok.d.trembling, ok.sample.dt, BANDS.trembling).toFixed(3)} Hz`}
                  colour={ok.d.adequacy.dominantIsLoopArtefact ? theme.open : undefined} />
                <Row theme={theme} k="reconstruction" v={ok.d.reconstructionError.toExponential(1)} />
              </Section>
            ) : (
              ok.sleep && (
                <Section theme={theme} title="SLEEP ACTIVITY">
                  <Row theme={theme} k="repositions" v={String(ok.sleep.repositions)} />
                  <Row theme={theme} k="arousals" v={String(ok.sleep.arousals)}
                    colour={ok.sleep.arousals > 0 ? theme.accent : undefined} />
                  <Row theme={theme} k="rate" v={`${ok.sleep.repositionRate.toFixed(1)} /h`} />
                  <Row theme={theme} k="longest still" v={`${ok.sleep.longestStillS.toFixed(1)} s`} />
                  <Row theme={theme} k="wake fraction" v={`${(ok.sleep.wakeFraction * 100).toFixed(1)}%`} />
                </Section>
              )
            )}

            <Section theme={theme} title="CHARGE">
              <div style={{ fontSize: 10, color: theme.textMuted, marginBottom: 6, lineHeight: 1.5 }}>
                Q = √(2CP) at the motor compartment. Power is the kinetic cost
                of the motion actually present — crude, but it scales with the
                movement rather than being assumed.
              </div>
              <Row theme={theme} k="power" v={`${ok.charge.powerW.toExponential(3)} W`} />
              <Row theme={theme} k="charge rate" v={`${(ok.charge.chargeCs * 1e3).toFixed(3)} mC/s`} />
              <Row theme={theme} k="total" v={`${ok.charge.totalC.toExponential(3)} C`} />
              <Row theme={theme} k="capacitance" v={`${ok.charge.compartment}`} />
            </Section>

            <button onClick={generate} style={{
              ...btn(theme), width: "100%", padding: "7px 0", marginTop: 4,
              background: theme.keyword, color: theme.editorBg,
              border: "none", fontWeight: 600,
            }}>
              Generate .vvs from this record
            </button>
            <div style={{ fontSize: 10, color: theme.textMuted, marginTop: 6, lineHeight: 1.5 }}>
              Writes a circuit whose capacitance comes from the measured charge
              and whose loop delay comes from the measured band — then loads it
              into the editor so it can be run against the record it came from.
            </div>
          </>
        )}
      </div>

      {/* trace */}
      <div style={{ flex: 1, minWidth: 0, padding: 12, overflow: "hidden" }}>
        {ok ? (
          <TraceStack theme={theme} sample={ok.sample} d={ok.d} sleep={ok.sleep} mode={mode} />
        ) : (
          <Empty theme={theme}>Select a clip to read its motion.</Empty>
        )}
      </div>
    </div>
  );
}

// ── trace rendering ──────────────────────────────────────────────────

function TraceStack({ theme, sample, d, sleep, mode }: {
  theme: Theme; sample: ClipSample; d: Decomposition;
  sleep?: SleepAnalysis; mode: Mode;
}) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const cv = ref.current;
    if (!cv) return;
    const dpr = Math.min(window.devicePixelRatio, 2);
    const w = cv.clientWidth;
    const h = cv.clientHeight;
    cv.width = w * dpr;
    cv.height = h * dpr;
    const g = cv.getContext("2d")!;
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, w, h);

    const rows: { label: string; data: Float64Array; colour: string; dim?: boolean }[] =
      mode === "sleep"
        ? [{ label: "pose", data: sample.x, colour: theme.series?.[0] ?? theme.keyword }]
        : [
            { label: "pose", data: sample.x, colour: theme.series?.[0] ?? theme.keyword },
            {
              label: d.adequacy.ramblingResolvable ? "rambling" : "rambling (unresolvable)",
              data: d.rambling,
              colour: theme.accent,
              dim: !d.adequacy.ramblingResolvable,
            },
            { label: "trembling", data: d.trembling, colour: theme.open },
          ];

    const pad = 34;
    const rowH = (h - pad) / rows.length;

    rows.forEach((r, ri) => {
      const y0 = pad + ri * rowH;
      const yMid = y0 + rowH / 2;
      let lo = Infinity;
      let hi = -Infinity;
      for (let i = 0; i < r.data.length; i++) {
        lo = Math.min(lo, r.data[i]);
        hi = Math.max(hi, r.data[i]);
      }
      const span = hi - lo || 1;
      const scale = (rowH * 0.38) / (span / 2);

      g.strokeStyle = theme.gridLine;
      g.lineWidth = 1;
      g.beginPath();
      g.moveTo(pad, yMid);
      g.lineTo(w - 8, yMid);
      g.stroke();

      g.strokeStyle = r.colour;
      g.globalAlpha = r.dim ? 0.35 : 1;
      g.lineWidth = 1.2;
      g.beginPath();
      const mid = (lo + hi) / 2;
      for (let i = 0; i < r.data.length; i++) {
        const x = pad + ((w - pad - 8) * i) / Math.max(1, r.data.length - 1);
        const y = yMid - (r.data[i] - mid) * scale;
        i === 0 ? g.moveTo(x, y) : g.lineTo(x, y);
      }
      g.stroke();
      g.globalAlpha = 1;

      g.fillStyle = r.dim ? theme.textMuted : r.colour;
      g.font = "10px ui-monospace, monospace";
      g.fillText(r.label, pad + 2, y0 + 11);
    });

    // Loop boundaries: the artefact is visible here as repetition.
    if (!sample.singlePass) {
      const perLoop = sample.clipDurationS / sample.dt;
      g.strokeStyle = theme.accent;
      g.globalAlpha = 0.25;
      g.setLineDash([3, 3]);
      for (let k = perLoop; k < sample.x.length; k += perLoop) {
        const x = pad + ((w - pad - 8) * k) / Math.max(1, sample.x.length - 1);
        g.beginPath();
        g.moveTo(x, pad);
        g.lineTo(x, h);
        g.stroke();
      }
      g.setLineDash([]);
      g.globalAlpha = 1;
    }

    // Sleep events.
    if (mode === "sleep" && sleep) {
      for (const e of sleep.events) {
        const x = pad + ((w - pad - 8) * (e.t / sleep.durationS));
        g.strokeStyle = e.kind === "arousal" ? theme.open : theme.accent;
        g.lineWidth = 1.5;
        g.beginPath();
        g.moveTo(x, pad);
        g.lineTo(x, h);
        g.stroke();
      }
    }

    g.fillStyle = theme.textDim;
    g.font = "10px ui-monospace, monospace";
    g.fillText(
      `${sample.clipName} / ${sample.jointName} / ${sample.axis}` +
        (sample.singlePass ? "  (single pass)" : `  (looped ${sample.loops.toFixed(1)}× — dashes mark repeats)`),
      pad + 2, 14,
    );
  }, [sample, d, sleep, mode, theme]);

  return <canvas ref={ref} style={{ width: "100%", height: "100%", display: "block" }} />;
}

// ── presentational helpers ───────────────────────────────────────────

const sanitise = (s: string) => s.toLowerCase().replace(/[^a-z0-9_]+/g, "_").replace(/^_+|_+$/g, "") || "record";

const btn = (t: Theme) => ({
  background: "transparent", border: `1px solid ${t.border}`, color: t.text,
  padding: "3px 10px", borderRadius: 3, fontSize: 11, cursor: "pointer",
  fontFamily: "inherit" as const,
});

const sel = (t: Theme) => ({
  width: "100%", background: t.surfaceBg, color: t.text,
  border: `1px solid ${t.border}`, borderRadius: 3, padding: "3px 6px",
  fontSize: 11, fontFamily: "inherit" as const,
});

function Section({ theme, title, children }: { theme: Theme; title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 14, paddingBottom: 12, borderBottom: `1px solid ${theme.border}` }}>
      <div style={{ fontSize: 9.5, letterSpacing: 1, fontWeight: 700, color: theme.textDim, marginBottom: 7 }}>
        {title}
      </div>
      {children}
    </div>
  );
}

function Field({ theme, label, children }: { theme: Theme; label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 6 }}>
      <div style={{ fontSize: 10, color: theme.textDim, marginBottom: 2 }}>{label}</div>
      {children}
    </div>
  );
}

function Row({ theme, k, v, colour }: { theme: Theme; k: string; v: string; colour?: string }) {
  return (
    <div style={{
      display: "flex", justifyContent: "space-between", gap: 8,
      fontFamily: "monospace", fontSize: 11, padding: "1px 0",
    }}>
      <span style={{ color: theme.textDim }}>{k}</span>
      <span style={{ color: colour ?? theme.text, textAlign: "right" }}>{v}</span>
    </div>
  );
}

function Note({ theme, children, bad }: { theme: Theme; children: React.ReactNode; bad?: boolean }) {
  return (
    <div style={{
      padding: "7px 9px", borderRadius: 4, fontSize: 11, marginBottom: 10,
      fontFamily: "monospace", lineHeight: 1.45,
      background: bad ? `${theme.open}0e` : `${theme.textDim}0e`,
      color: bad ? theme.open : theme.textDim,
      border: `1px solid ${bad ? theme.open : theme.border}22`,
    }}>{children}</div>
  );
}

function Empty({ theme, children }: { theme: Theme; children: React.ReactNode }) {
  return (
    <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", padding: 32 }}>
      <div style={{ maxWidth: 380, textAlign: "center", fontSize: 12, color: theme.textMuted, lineHeight: 1.65 }}>
        {children}
      </div>
    </div>
  );
}
