import Head from "next/head";
import Link from "next/link";
import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";
import { SyntheticScene, PITCH_X, PITCH_Y } from "@/lib/football/syntheticScene";
import { robustFocusPoint } from "@/lib/football/attentionFocus";
import {
  decomposeHR,
  vasodilationToSkinTemp,
  autonomicActivation,
  q10ThermalCorrection,
} from "@/lib/football/cardiacQ10";
import { useBody } from "@/lib/bodyState";

const AttentionFieldCanvas = dynamic(
  () => import("@/components/compute/AttentionFieldCanvas"),
  { ssr: false }
);

export default function FootballTool() {
  const [running, setRunning] = useState(true);
  const [sigmaRad, setSigmaRad] = useState(0.30);
  const [intensity, setIntensity] = useState(1.0);
  const [ambientC, setAmbientC] = useState(22.0);   // pitch ambient for Q10
  const [HR_obs, setHR_obs] = useState(155);        // simulated player HR
  const [vaso, setVaso] = useState(1.15);           // vasodilation factor

  const sceneRef = useRef(null);
  const [snapshot, setSnapshot] = useState(null);
  const [focus, setFocus] = useState([0, 0]);
  const [stats, setStats] = useState({
    focusSpeed: 0,
    focusErrM: 0,
    nPlayers: 0,
  });

  // Build scene once
  useEffect(() => {
    sceneRef.current = new SyntheticScene({ seed: 17 });
    setSnapshot(sceneRef.current.step(0.001));
  }, []);

  // Animation loop
  useEffect(() => {
    if (!sceneRef.current) return;
    let raf;
    let lastT = performance.now();
    let lastFocus = focus;
    const tick = () => {
      const now = performance.now();
      const dt = Math.min(0.05, (now - lastT) / 1000);
      lastT = now;
      if (running) {
        const snap = sceneRef.current.step(dt);
        const est = robustFocusPoint(
          snap.detections.map((d) => ({
            position: d.position,
            facing: d.facing,
            weight: d.weight,
          }))
        );
        const newFocus = est.point;
        const focusSpeed = Math.hypot(
          newFocus[0] - lastFocus[0],
          newFocus[1] - lastFocus[1]
        ) / Math.max(dt, 1e-3);
        const focusErr = Math.hypot(
          newFocus[0] - snap.ball[0],
          newFocus[1] - snap.ball[1]
        );
        setSnapshot(snap);
        setFocus(newFocus);
        setStats({
          focusSpeed,
          focusErrM: focusErr,
          nPlayers: snap.detections.length,
        });
        lastFocus = newFocus;
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [running]);

  // PCHR decomposition + body-state binding (cardiac drives off ΔHR_auto)
  const cardiacState = useMemo(() => {
    const T_skin = vasodilationToSkinTemp(vaso);
    const pchr = decomposeHR({ HR_obs, T_skin_C: T_skin, S_O2: 0.96 });
    const cardiacAct = autonomicActivation(pchr.dHR_auto);
    // Q_motor thermal correction example
    const Q_motor_observed = 290.9;  // mC/s from paper 3
    const Q_motor_corr = q10ThermalCorrection(Q_motor_observed, ambientC);
    return { T_skin, pchr, cardiacAct, Q_motor_observed, Q_motor_corr };
  }, [HR_obs, vaso, ambientC]);

  const { setAll, setPanelOpen } = useBody();
  useEffect(() => {
    setPanelOpen(true);
    setAll({
      motor: Math.min(1, stats.focusSpeed / 25),         // fast play -> high motor
      cardiac: cardiacState.cardiacAct,                  // ΔHR_auto, not raw HR
      thought: 0.35 + 0.3 * Math.min(1, stats.focusSpeed / 20),
      perception: 0.55,
      respiratory: 0.4 + 0.4 * cardiacState.cardiacAct,
      baseline: 0.45,
      visceral: 0.2,
    });
  }, [stats.focusSpeed, cardiacState.cardiacAct, setAll, setPanelOpen]);

  return (
    <>
      <Head>
        <title>Football Observation Operator — Olduvai</title>
      </Head>

      <section className="pt-24 pb-4 px-8 sm:px-4 max-w-6xl mx-auto">
        <Link
          href="/tools"
          className="mono text-xs uppercase tracking-widest text-muted hover:text-primary transition-colors"
        >
          ← Tools
        </Link>
        <h1 className="text-3xl font-semibold text-light mt-4 mb-2">
          Football Observation Operator
        </h1>
        <p className="mono text-sm text-muted max-w-2xl">
          22 synthetic players on a 105&nbsp;×&nbsp;68&nbsp;m pitch. Each
          player&apos;s torso faces a lagged ball trajectory; a fragment
          shader evaluates the per-pixel attention density Σᵢ&nbsp;wᵢ&nbsp;exp(−½(θᵢ/σ)²)
          and the brightest pixel is the inferred ball. The rendered
          framebuffer IS the computation — the observation operator
          made literal.
        </p>
      </section>

      {/* Attention field shader canvas (aspect-locked to pitch ratio) */}
      <section className="px-8 sm:px-4 max-w-6xl mx-auto">
        <div
          className="relative border border-darkBorder bg-black"
          style={{ aspectRatio: `${PITCH_X} / ${PITCH_Y}` }}
        >
          <AttentionFieldCanvas
            scene={snapshot}
            focus={focus}
            sigmaRad={sigmaRad}
            intensity={intensity}
          />
          <Legend stats={stats} />
        </div>

        {/* Controls + readouts */}
        <div className="grid grid-cols-2 gap-6 mt-6 md:grid-cols-1">
          <ControlsCard
            running={running}
            setRunning={setRunning}
            sigmaRad={sigmaRad}
            setSigmaRad={setSigmaRad}
            intensity={intensity}
            setIntensity={setIntensity}
            vaso={vaso}
            setVaso={setVaso}
            HR_obs={HR_obs}
            setHR_obs={setHR_obs}
            ambientC={ambientC}
            setAmbientC={setAmbientC}
          />
          <CardiacCard cardiac={cardiacState} stats={stats} />
        </div>

        <FrameworkNote />
      </section>
      <div className="h-24" />
    </>
  );
}

// ────────────────────────────────────────────────────────────────────

function Legend({ stats }) {
  return (
    <div className="absolute top-2 left-2 mono text-[10px] uppercase tracking-widest text-light bg-dark/70 px-2 py-1 backdrop-blur">
      render ≡ compute · {stats.nPlayers} players ·
      focus err = {stats.focusErrM.toFixed(2)} m
    </div>
  );
}

function ControlsCard({
  running, setRunning, sigmaRad, setSigmaRad, intensity, setIntensity,
  vaso, setVaso, HR_obs, setHR_obs, ambientC, setAmbientC,
}) {
  return (
    <div className="border border-darkBorder bg-darkSoft/60 p-5">
      <div className="mono text-[10px] uppercase tracking-widest text-muted mb-3">
        controls
      </div>
      <button
        onClick={() => setRunning((v) => !v)}
        className={`mono text-xs uppercase tracking-wider px-4 py-2 border transition-colors ${
          running
            ? "border-primary text-primary bg-darkSoft"
            : "border-darkBorder text-muted hover:text-light"
        }`}
      >
        {running ? "pause" : "play"}
      </button>
      <div className="grid grid-cols-2 gap-3 mt-4 sm:grid-cols-1">
        <Slider label="σ angular" v={sigmaRad} set={setSigmaRad}
                min={0.1} max={1.0} step={0.01} fmt={(v) => v.toFixed(2)} unit="rad" />
        <Slider label="intensity" v={intensity} set={setIntensity}
                min={0.3} max={3.0} step={0.05} fmt={(v) => v.toFixed(2)} />
        <Slider label="ambient" v={ambientC} set={setAmbientC}
                min={5} max={40} step={0.5} fmt={(v) => v.toFixed(1)} unit="°C" />
        <Slider label="HR_obs" v={HR_obs} set={setHR_obs}
                min={60} max={200} step={1} fmt={(v) => v.toFixed(0)} unit="bpm" />
        <Slider label="vasodilation η" v={vaso} set={setVaso}
                min={0.6} max={1.6} step={0.01} fmt={(v) => v.toFixed(2)} />
      </div>
    </div>
  );
}

function Slider({ label, v, set, min, max, step, fmt, unit }) {
  return (
    <label className="block">
      <div className="flex justify-between mb-1">
        <span className="mono text-[10px] uppercase tracking-wider text-muted">
          {label} {unit && <span className="text-primary/60">{unit}</span>}
        </span>
        <span className="mono text-[10px] text-light">{fmt(v)}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={v}
        onChange={(e) => set(parseFloat(e.target.value))}
        className="w-full accent-primary"
      />
    </label>
  );
}

function CardiacCard({ cardiac, stats }) {
  const { pchr, T_skin, cardiacAct, Q_motor_observed, Q_motor_corr } = cardiac;
  return (
    <div className="border border-darkBorder bg-darkSoft/60 p-5">
      <div className="mono text-[10px] uppercase tracking-widest text-muted mb-3">
        PCHR decomposition (PPG paper Q10 method)
      </div>
      <div className="grid grid-cols-4 gap-3">
        <Readout label="HR_obs" v={pchr.HR_obs.toFixed(0)} unit="bpm" colour="#cfcfe2" />
        <Readout label="ΔHR_met" v={pchr.dHR_met.toFixed(1)} unit="bpm" colour="#F0A830" />
        <Readout label="ΔHR_O₂" v={pchr.dHR_O2.toFixed(1)} unit="bpm" colour="#4FD1C5" />
        <Readout label="ΔHR_auto" v={pchr.dHR_auto.toFixed(1)} unit="bpm" colour="#E6395A" />
      </div>
      <div className="mono text-[10px] text-muted leading-relaxed mt-4">
        T_skin = {T_skin.toFixed(1)}&nbsp;°C · cardiac compartment binds to
        ΔHR_auto / max range = <span className="text-primary">{(cardiacAct * 100).toFixed(0)}%</span><br />
        Q_motor observed = {Q_motor_observed.toFixed(0)} mC/s · Q10-corrected for
        ambient = <span className="text-primary">{Q_motor_corr.toFixed(0)}</span> mC/s<br />
        focus speed (proxy for ball velocity) = <span className="text-primary">{stats.focusSpeed.toFixed(1)}</span> m/s
      </div>
    </div>
  );
}

function Readout({ label, v, unit, colour }) {
  return (
    <div className="border border-darkBorder/60 bg-dark/40 p-2 text-center">
      <div className="mono text-[9px] uppercase tracking-wider text-muted">
        {label}
      </div>
      <div className="mono text-base" style={{ color: colour }}>
        {v}
        <span className="text-muted text-[10px]"> {unit}</span>
      </div>
    </div>
  );
}

function FrameworkNote() {
  return (
    <div className="mt-8 border border-darkBorder bg-darkSoft/60 p-5">
      <div className="mono text-xs uppercase tracking-widest text-primary mb-2">
        Framework note
      </div>
      <ul className="mono text-sm text-muted leading-relaxed list-disc pl-5 space-y-2">
        <li>
          The bright pixel is not detected — it is <em>computed</em> by the
          shader from player torso orientations. No ball CV anywhere in
          this pipeline.
        </li>
        <li>
          The white dot is the JS-side algebraic inverse (weighted
          least-squares 2×2 solve). The red dot is the ground-truth ball.
          Divergence between them is the team&apos;s reaction lag — a measurable
          quantity the framework exposes that direct ball tracking cannot.
        </li>
        <li>
          The right-side anatomy panel&apos;s <span className="text-warm">cardiac</span> compartment
          drives on <span className="text-warm">ΔHR_auto</span> (the PPG paper&apos;s Q10
          autonomic residual), not raw HR. Slide HR_obs above 150 with ambient at
          22 °C and watch the residual stay tactical-meaningful; raise ambient to
          35 °C and watch the metabolic component absorb most of the elevation.
        </li>
        <li>
          The Q10 thermal correction also recovers the &quot;tactical&quot; Q_motor by
          dividing observed Q_motor by exp((T_env − 33)/10 · ln 2.3) — without
          this, two identical performances in different weather look different
          in the ledger.
        </li>
      </ul>
    </div>
  );
}
