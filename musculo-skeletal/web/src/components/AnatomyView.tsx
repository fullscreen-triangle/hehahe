/**
 * Anatomy view: a circulation rendered on a rig it is bound to.
 *
 * The design commitment here is that joint motion is driven by the ARM'S
 * INTEGRATED TRACE, not by a summary statistic. A viewer that renders
 * `scale = 1 + amp·sin(2π·rate·t)` shows you a number the results table
 * already gave you. Reading the state array means the geometry can show
 * something the table cannot: that a closed circuit oscillates about a
 * centre indefinitely while an open one leaves anatomical range at a
 * particular time.
 *
 * That range violation is an INDEPENDENT witness. The engine reports
 * `divergence_time` from the trace; the rig reports when the joint exceeds
 * limits derived from its own rest pose. Two quantities, computed from
 * different things, displayed together — and they can disagree.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import {
  checkBinding, getRig, jointGraph, type BindReport, type BindSpec,
} from "../lang/binding";
import type { Circuit } from "../lang/circuit";
import type { Backend, Trace } from "../lang/backend";
import type { Theme } from "../theme";

// ── model loading, cached across mounts ─────────────────────────────

const CACHE = new Map<string, Promise<THREE.Group>>();

function loadRig(name: string): Promise<THREE.Group> {
  const hit = CACHE.get(name);
  if (hit) return hit;
  const p = new Promise<THREE.Group>((resolve, reject) => {
    new GLTFLoader().load(
      `models/${name}.glb`,
      (gltf) => {
        // Keep the animation clips with the scene; the gait clock needs them.
        (gltf.scene as THREE.Group & { animations?: THREE.AnimationClip[] }).animations =
          gltf.animations;
        resolve(gltf.scene as THREE.Group);
      },
      undefined,
      reject,
    );
  });
  CACHE.set(name, p);
  return p;
}

// ── joint range, derived from the rig itself ────────────────────────

/**
 * Anatomical range for a joint, in radians. Derived from the rig's own rest
 * pose rather than declared: a joint whose child sits far away is a long
 * segment and a small rotation moves its tip a long way, so its tolerable
 * angular excursion is smaller. This is crude, but it is crude in a way the
 * program cannot influence, which is what makes it an independent witness.
 */
function jointRange(segmentLength: number): number {
  if (!Number.isFinite(segmentLength) || segmentLength <= 0) return Math.PI / 2;
  // Longer segments get tighter angular limits; clamp to a plausible band.
  return Math.max(0.15, Math.min(Math.PI / 2, 2.0 / (1 + segmentLength)));
}

export interface AnatomyArm {
  name: string;
  closure: string;
  circuit: Circuit;
  divergenceTime: number | null;
}

interface Props {
  theme: Theme;
  arms: AnatomyArm[];
  selectedArm: string;
  onSelectArm: (name: string) => void;
  bindSpec: BindSpec | null;
  backend: Backend;
}

interface RangeEvent {
  joint: string;
  time: number;
  peak: number;
  limit: number;
}

export function AnatomyView({
  theme, arms, selectedArm, onSelectArm, bindSpec, backend,
}: Props) {
  const mountRef = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const [playing, setPlaying] = useState(true);
  const [clock, setClock] = useState(0);
  const [tissue, setTissue] = useState<string>("muscle");
  const [rangeEvents, setRangeEvents] = useState<RangeEvent[]>([]);

  const arm = arms.find((a) => a.name === selectedArm) ?? arms[0];

  // The bind report is pure and cheap; recompute whenever either side moves.
  const report: BindReport | null = useMemo(() => {
    if (!bindSpec || !arm) return null;
    return checkBinding(arm.circuit, bindSpec);
  }, [bindSpec, arm]);

  const rig = bindSpec ? getRig(bindSpec.rig) : undefined;

  // The trace that drives the rig. This is the actual integrated state.
  const trace: Trace | null = useMemo(() => {
    if (!arm) return null;
    try {
      return backend.simulate(arm.circuit);
    } catch {
      return null;
    }
  }, [arm, backend]);

  // Mutable state the animation loop reads without re-subscribing.
  const live = useRef({
    armName: "", playing: true, tissue: "muscle", tick: 0, published: 0, gain: 1,
    trace: null as Trace | null, bindSpec: null as BindSpec | null,
    rangeHits: new Map<string, RangeEvent>(),
  });
  live.current.armName = arm?.name ?? "";
  live.current.playing = playing;
  live.current.tissue = tissue;
  live.current.trace = trace;
  live.current.bindSpec = bindSpec;

  /**
   * Angular gain, calibrated so that REST occupies a fixed fraction of the
   * joint's range and everything above rest is the arm's own behaviour.
   *
   * A fixed constant would decide the range question by fiat: pick it large
   * and every arm leaves range, pick it small and none does. Calibrating on
   * the settled early excursion instead fixes the resting amplitude at a
   * tenth of range, so the joint can only leave range if the trajectory
   * grows by more than 10x over its own resting scale.
   *
   * That threshold is not free either, so it is stated rather than hidden:
   * the intact circuit here grows 1.25x over 20 s (bounded oscillation about
   * a centre, as a closed circulation must), while the severed one grows
   * 4.1x before the integrator saturates. Neither crosses 10x, so on THIS
   * program the anatomical witness does not fire -- and reporting that
   * honestly is the point. A witness that fired whenever the engine already
   * said "open" would be reporting the engine, not the anatomy.
   */
  const restFraction = 0.1;

  /** Peak excursion late in the trace relative to its resting scale. This is
   *  the quantity the range test thresholds, so it is reported whether or not
   *  the threshold is crossed -- a test that only speaks when it fires hides
   *  how close it came. */
  const growth = useMemo(() => {
    if (!trace) return null;
    const w = Math.max(1, Math.floor(1.0 / trace.dt));
    const peakIn = (a: number, b: number) => {
      let p = 0;
      for (let i = Math.max(0, a); i < Math.min(trace.n, b); i++) {
        p = Math.max(p, Math.abs(trace.x[0][i]));
      }
      return p;
    };
    const rest = peakIn(0, w);
    const late = peakIn(trace.n - w, trace.n);
    if (!rest) return null;
    return { rest, late, ratio: late / rest };
  }, [trace]);

  live.current.gain = useMemo(() => {
    if (!trace) return 1;
    const w = Math.min(trace.n, Math.max(1, Math.floor(1.0 / trace.dt)));
    let peak = 0;
    for (let i = 0; i < w; i++) peak = Math.max(peak, Math.abs(trace.x[0][i]));
    if (!Number.isFinite(peak) || peak <= 0) return 1;
    // Rest sits at `restFraction` of a right angle; the joint's own limit
    // (from its rest pose) decides how much further it may go.
    return (restFraction * (Math.PI / 2)) / peak;
  }, [trace]);

  useEffect(() => {
    const el = mountRef.current;
    if (!el || !bindSpec || !rig?.bindable) return;

    let disposed = false;
    let frame = 0;
    setStatus("loading");
    setError(null);

    const w = el.clientWidth || 800;
    const h = el.clientHeight || 600;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(theme.panelBg);

    const camera = new THREE.PerspectiveCamera(40, w / h, 0.1, 500);
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(w, h);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    el.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;

    scene.add(new THREE.AmbientLight(0xffffff, 0.75));
    const key = new THREE.DirectionalLight(0xffffff, 1.1);
    key.position.set(3, 6, 4);
    scene.add(key);
    const rim = new THREE.DirectionalLight(0x88aaff, 0.4);
    rim.position.set(-4, 2, -3);
    scene.add(rim);

    let mixer: THREE.AnimationMixer | null = null;
    let boundNodes = new Map<string, THREE.Object3D>();
    let restQuat = new Map<string, THREE.Quaternion>();
    let limits = new Map<string, number>();
    let markers: THREE.Mesh[] = [];

    loadRig(bindSpec.rig)
      .then((src) => {
        if (disposed) return;
        // Clone so multiple views can share one cached load.
        const root = src.clone(true);
        scene.add(root);

        // Frame the model.
        const box = new THREE.Box3().setFromObject(root);
        const size = box.getSize(new THREE.Vector3());
        const centre = box.getCenter(new THREE.Vector3());
        const span = Math.max(size.x, size.y, size.z) || 1;
        camera.position.set(centre.x + span * 0.9, centre.y + span * 0.4, centre.z + span * 1.2);
        camera.far = span * 20;
        camera.updateProjectionMatrix();
        controls.target.copy(centre);
        controls.update();

        // Resolve bound joints by name, and record rest orientation so the
        // trace drives a DEVIATION from rest rather than an absolute pose.
        const byName = new Map<string, THREE.Object3D>();
        root.traverse((o) => byName.set(o.name, o));

        const g = jointGraph(rig);
        for (const [comp, jointName] of Object.entries(bindSpec.map)) {
          const node = byName.get(jointName);
          if (!node) continue;
          boundNodes.set(comp, node);
          restQuat.set(comp, node.quaternion.clone());

          // Segment length from the manifest's rest translations.
          const jt = g.byName.get(jointName);
          const child = rig.joints.find((x) => x.parent === jointName);
          const segLen = child
            ? Math.hypot(...child.rest)
            : jt
              ? Math.hypot(...jt.rest)
              : 1;
          limits.set(comp, jointRange(segLen / (bindSpec.unitsPerMetre ?? 100)));

          // A small marker at each bound joint, so the binding is visible.
          const m = new THREE.Mesh(
            new THREE.SphereGeometry(span * 0.012, 12, 8),
            new THREE.MeshBasicMaterial({ color: theme.accent }),
          );
          node.add(m);
          markers.push(m);
        }

        const clips =
          (root as THREE.Group & { animations?: THREE.AnimationClip[] }).animations ??
          (src as THREE.Group & { animations?: THREE.AnimationClip[] }).animations ??
          [];
        if (clips.length) mixer = new THREE.AnimationMixer(root);

        setStatus("ready");
      })
      .catch((e) => {
        if (disposed) return;
        setError(String(e?.message ?? e));
        setStatus("error");
      });

    let prev = performance.now();
    const tmpQ = new THREE.Quaternion();
    const axis = new THREE.Vector3(0, 0, 1);

    const animate = (now: number) => {
      frame = requestAnimationFrame(animate);
      // Clamp the step, but do not let a slow frame slow the physics: the
      // trace advances in wall-clock seconds so that a divergence time
      // measured here is comparable with the engine's. Software rasterisers
      // (headless CI, machines without a GPU) render a 33k-vertex skinned
      // mesh at single-digit frame rates; tying the clock to frame delivery
      // would make the same program report different divergence times on
      // different hardware, which is exactly the backend-dependence the
      // language is built to avoid.
      const dt = Math.min((now - prev) / 1000, 0.25);
      prev = now;

      const L = live.current;
      if (L.playing) {
        L.tick += dt;
      }
      const t = L.tick;
      mixer?.update(L.playing ? dt : 0);

      const tr = L.trace;
      if (tr && boundNodes.size) {
        // Index into the integrated trace. The trace is the arm's actual
        // state; when it diverges, the joint diverges with it.
        const idx = Math.min(tr.n - 1, Math.floor(t / tr.dt));
        for (const [comp, node] of boundNodes) {
          const rest = restQuat.get(comp);
          if (!rest) continue;
          // Column by stratum would be ideal; reflex is the fast one and is
          // what a limb joint follows.
          const v = tr.x[0][idx] ?? 0;
          const limit = limits.get(comp) ?? Math.PI / 2;
          const angle = v * (L.gain || 1);
          tmpQ.setFromAxisAngle(axis, angle);
          node.quaternion.copy(rest).multiply(tmpQ);

          if (Math.abs(angle) > limit && !L.rangeHits.has(comp)) {
            L.rangeHits.set(comp, {
              joint: comp, time: t, peak: Math.abs(angle), limit,
            });
            setRangeEvents([...L.rangeHits.values()]);
          }
        }
      }

      // Publishing the clock to React on every frame re-renders the whole
      // side panel 60 times a second and starves the loop that draws the
      // scene. 10 Hz is well past what a readout needs.
      if (t - (L.published ?? 0) >= 0.1) {
        L.published = t;
        setClock(t);
      }
      controls.update();
      renderer.render(scene, camera);
    };
    frame = requestAnimationFrame(animate);

    const onResize = () => {
      const nw = el.clientWidth, nh = el.clientHeight;
      if (!nw || !nh) return;
      camera.aspect = nw / nh;
      camera.updateProjectionMatrix();
      renderer.setSize(nw, nh);
    };
    window.addEventListener("resize", onResize);

    return () => {
      disposed = true;
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", onResize);
      controls.dispose();
      for (const m of markers) {
        m.parent?.remove(m);
        m.geometry.dispose();
        (m.material as THREE.Material).dispose();
      }
      renderer.dispose();
      if (el.contains(renderer.domElement)) el.removeChild(renderer.domElement);
    };
  }, [bindSpec?.rig, rig, theme.panelBg, theme.accent]);

  // Reset the clock and the range record when the arm changes: a range
  // violation belongs to one arm and must not carry over.
  useEffect(() => {
    live.current.tick = 0;
    live.current.published = 0;
    live.current.rangeHits.clear();
    setRangeEvents([]);
  }, [selectedArm]);

  if (!bindSpec) {
    return (
      <Empty theme={theme}>
        No binding declared. Add a <code>bind</code> clause to attach a circuit
        to a rig — the rig then contributes an adjacency and a tissue index
        the program does not have, and the two can disagree.
      </Empty>
    );
  }
  if (!rig?.bindable) {
    return (
      <Empty theme={theme}>
        Rig <b>{bindSpec.rig}</b> carries no skin, so there are no joints to
        bind to. It can serve only as a static backdrop.
      </Empty>
    );
  }

  const errs = report?.diagnostics.filter((d) => d.severity === "error") ?? [];
  const warns = report?.diagnostics.filter((d) => d.severity === "warning") ?? [];
  const infos = report?.diagnostics.filter((d) => d.severity === "info") ?? [];

  return (
    <div style={{ height: "100%", display: "flex", overflow: "hidden" }}>
      <div style={{ flex: 1, position: "relative", minWidth: 0 }}>
        <div ref={mountRef} style={{ position: "absolute", inset: 0 }} />

        <div style={{
          position: "absolute", top: 10, left: 12, fontFamily: "monospace",
          fontSize: 11, color: theme.textDim, pointerEvents: "none",
        }}>
          t = {clock.toFixed(2)} s
          {arm?.divergenceTime != null && Number.isFinite(arm.divergenceTime) && (
            <span style={{ color: theme.open, marginLeft: 12 }}>
              engine divergence {arm.divergenceTime.toFixed(2)} s
            </span>
          )}
        </div>

        {status === "loading" && (
          <Overlay theme={theme}>Loading {bindSpec.rig}…</Overlay>
        )}
        {status === "error" && (
          <Overlay theme={theme}>Failed to load rig: {error}</Overlay>
        )}

        <div style={{
          position: "absolute", bottom: 10, left: 12, display: "flex", gap: 6,
        }}>
          <button
            onClick={() => setPlaying((p) => !p)}
            style={btn(theme)}
          >
            {playing ? "Pause" : "Play"}
          </button>
          <button
            onClick={() => {
              live.current.tick = 0;
              live.current.published = 0;
              live.current.rangeHits.clear();
              setRangeEvents([]);
            }}
            style={btn(theme)}
          >
            Reset
          </button>
        </div>
      </div>

      <div style={{
        width: 320, flexShrink: 0, borderLeft: `1px solid ${theme.border}`,
        background: theme.panelBg, overflow: "auto", padding: 12,
        fontSize: 12,
      }}>
        <Section theme={theme} title="ARM">
          {arms.map((a) => (
            <button
              key={a.name}
              onClick={() => onSelectArm(a.name)}
              style={{
                display: "block", width: "100%", textAlign: "left",
                padding: "5px 9px", marginBottom: 3, borderRadius: 4,
                border: "none", cursor: "pointer", fontFamily: "inherit",
                fontSize: 12,
                background: a.name === selectedArm
                  ? (a.closure === "open" ? `${theme.open}18` : `${theme.closed}18`)
                  : "transparent",
                color: a.closure === "open" ? theme.open : theme.closed,
                borderLeft: `3px solid ${a.name === selectedArm
                  ? (a.closure === "open" ? theme.open : theme.closed) : "transparent"}`,
              }}
            >
              {a.closure === "open" ? "◇" : "●"} {a.name}
            </button>
          ))}
        </Section>

        <Section theme={theme} title="BINDING">
          <Row theme={theme} k="rig" v={bindSpec.rig} />
          <Row theme={theme} k="bound" v={`${report?.bound ?? 0} / ${(report?.bound ?? 0) + (report?.unbound.length ?? 0)}`} />
          <Row
            theme={theme}
            k="consistent"
            v={report?.consistent ? "yes" : "no"}
            colour={report?.consistent ? theme.closed : theme.open}
          />
        </Section>

        {rig.tissues.length > 1 && (
          <Section theme={theme} title="TISSUE LAYER">
            <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
              {rig.tissues.map((t) => (
                <button
                  key={t}
                  onClick={() => setTissue(t)}
                  style={{
                    ...btn(theme),
                    background: t === tissue ? theme.surfaceBg : "transparent",
                    color: t === tissue ? theme.text : theme.textDim,
                  }}
                >
                  {t}
                </button>
              ))}
            </div>
            <div style={{ fontSize: 10, color: theme.textMuted, marginTop: 6, lineHeight: 1.5 }}>
              The rig's {rig.tissues.length} chains are exactly co-registered
              (max rest drift {rig.coregistration.maxRestDrift}). They are a
              tissue index, <b>not</b> strata — tissue is not a latency axis.
            </div>
          </Section>
        )}

        {(errs.length > 0 || warns.length > 0 || infos.length > 0) && (
          <Section theme={theme} title="BIND DIAGNOSTICS">
            {[...errs, ...warns, ...infos].map((d, i) => (
              <div key={i} style={{
                padding: "6px 8px", marginBottom: 4, borderRadius: 4,
                fontSize: 10.5, lineHeight: 1.45, fontFamily: "monospace",
                background: d.severity === "error" ? `${theme.open}0e`
                  : d.severity === "warning" ? `${theme.accent}0e` : `${theme.textDim}0e`,
                color: d.severity === "error" ? theme.open
                  : d.severity === "warning" ? theme.accent : theme.textDim,
                border: `1px solid ${d.severity === "error" ? theme.open
                  : d.severity === "warning" ? theme.accent : theme.border}22`,
              }}>
                <b>{d.check}</b> {d.message}
              </div>
            ))}
          </Section>
        )}

        {growth && (
          <Section theme={theme} title="ANATOMICAL RANGE">
            <div style={{ fontSize: 10, color: theme.textMuted, marginBottom: 6, lineHeight: 1.5 }}>
              Excursion late in the trace against its own resting scale.
              Rest is pinned at {(restFraction * 100).toFixed(0)}% of range,
              so the joint leaves range only if this exceeds{" "}
              {(1 / restFraction).toFixed(0)}×.
            </div>
            <Row theme={theme} k="resting peak" v={growth.rest.toExponential(2)} />
            <Row theme={theme} k="late peak" v={growth.late.toExponential(2)} />
            <Row
              theme={theme}
              k="growth"
              v={`${growth.ratio.toFixed(2)}×`}
              colour={growth.ratio >= 1 / restFraction ? theme.open : theme.closed}
            />
            <Row
              theme={theme}
              k="leaves range"
              v={rangeEvents.length ? "yes" : "no"}
              colour={rangeEvents.length ? theme.open : theme.closed}
            />
          </Section>
        )}

        {rangeEvents.length > 0 && (
          <Section theme={theme} title="RANGE VIOLATION">
            <div style={{ fontSize: 10, color: theme.textMuted, marginBottom: 6, lineHeight: 1.5 }}>
              Computed from the rig's rest pose, independently of the engine.
              Compare with the engine's divergence time above — they are two
              different measurements and need not agree.
            </div>
            {rangeEvents.map((r) => (
              <Row
                key={r.joint}
                theme={theme}
                k={r.joint}
                v={`left range at ${r.time.toFixed(2)} s`}
                colour={theme.open}
              />
            ))}
          </Section>
        )}

        {report && report.spans.length > 0 && (
          <Section theme={theme} title="SPAN (B4)">
            <div style={{ fontSize: 10, color: theme.textMuted, marginBottom: 6, lineHeight: 1.5 }}>
              Delay predicted from anatomical distance at{" "}
              {bindSpec.conductionVelocity} m/s, against the delay the program
              declares. Neither is the arbiter.
            </div>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 10.5, fontFamily: "monospace" }}>
              <thead>
                <tr style={{ color: theme.textDim }}>
                  <th style={{ textAlign: "left", paddingBottom: 3 }}>element</th>
                  <th style={{ textAlign: "right" }}>dist</th>
                  <th style={{ textAlign: "right" }}>pred</th>
                  <th style={{ textAlign: "right" }}>decl</th>
                  <th style={{ textAlign: "right" }}>ratio</th>
                </tr>
              </thead>
              <tbody>
                {report.spans.map((s) => (
                  <tr key={s.element} style={{ color: theme.text }}>
                    <td>{s.element}</td>
                    <td style={{ textAlign: "right" }}>{(s.distance * 100).toFixed(1)}cm</td>
                    <td style={{ textAlign: "right" }}>{(s.predicted * 1e3).toFixed(1)}</td>
                    <td style={{ textAlign: "right" }}>{(s.declared * 1e3).toFixed(1)}</td>
                    <td style={{
                      textAlign: "right",
                      color: s.ratio > 3 || s.ratio < 1 / 3 ? theme.accent : theme.text,
                    }}>
                      {s.ratio.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Section>
        )}
      </div>
    </div>
  );
}

// ── small presentational helpers ────────────────────────────────────

const btn = (theme: Theme) => ({
  background: "transparent",
  border: `1px solid ${theme.border}`,
  color: theme.text,
  padding: "3px 10px",
  borderRadius: 3,
  fontSize: 11,
  cursor: "pointer",
  fontFamily: "inherit",
});

function Section({ theme, title, children }: {
  theme: Theme; title: string; children: React.ReactNode;
}) {
  return (
    <div style={{ marginBottom: 14, paddingBottom: 12, borderBottom: `1px solid ${theme.border}` }}>
      <div style={{
        fontSize: 9.5, letterSpacing: 1, fontWeight: 700,
        color: theme.textDim, marginBottom: 7,
      }}>
        {title}
      </div>
      {children}
    </div>
  );
}

function Row({ theme, k, v, colour }: {
  theme: Theme; k: string; v: string; colour?: string;
}) {
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

function Empty({ theme, children }: { theme: Theme; children: React.ReactNode }) {
  return (
    <div style={{
      height: "100%", display: "flex", alignItems: "center",
      justifyContent: "center", padding: 32,
    }}>
      <div style={{
        maxWidth: 380, textAlign: "center", fontSize: 12,
        color: theme.textMuted, lineHeight: 1.65,
      }}>
        {children}
      </div>
    </div>
  );
}

function Overlay({ theme, children }: { theme: Theme; children: React.ReactNode }) {
  return (
    <div style={{
      position: "absolute", inset: 0, display: "flex",
      alignItems: "center", justifyContent: "center",
      color: theme.textDim, fontSize: 12, pointerEvents: "none",
    }}>
      {children}
    </div>
  );
}
