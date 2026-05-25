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

const VideoPoseTracker = dynamic(
  () => import("@/components/football/VideoPoseTracker"),
  { ssr: false }
);

const DualBodyPanel = dynamic(
  () => import("@/components/football/DualBodyPanel"),
  { ssr: false }
);

const BallStatsCard = dynamic(
  () => import("@/components/football/BallStatsCard"),
  { ssr: false }
);

export default function FootballTool() {
  const [mode, setMode] = useState("synthetic");    // "synthetic" | "video"
  const [videoUrl, setVideoUrl] = useState("");
  const [videoSrc, setVideoSrc] = useState("");
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

  // Animation loop — synthetic mode only
  useEffect(() => {
    if (mode !== "synthetic") return;
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
  }, [running, mode]);

  // Video-mode aggregated state
  const [videoFrame, setVideoFrame] = useState(null);
  const handleVideoFrame = useMemo(() => (info) => {
    setVideoFrame(info);
  }, []);

  // Team-level aggregation from the per-frame player list.
  const teamSummaries = useMemo(() => {
    if (!videoFrame?.players) {
      return { teamA: null, teamB: null };
    }
    const t0 = videoFrame.players.filter((p) => p.team === 0);
    const t1 = videoFrame.players.filter((p) => p.team === 1);
    const mk = (players, idx) => {
      const valid = players.filter((p) => p.metrics?.valid);
      const mean = (k) => valid.length === 0
        ? 0 : valid.reduce((s, p) => s + (p.metrics[k] || 0), 0) / valid.length;
      const meanSpeed = mean("speedMps");
      // Minimum same-team separation (in image-normalised units).
      let minSep = Infinity;
      for (let i = 0; i < players.length; i++) {
        for (let j = i + 1; j < players.length; j++) {
          const d = Math.hypot(
            players[i].position[0] - players[j].position[0],
            players[i].position[1] - players[j].position[1]);
          if (d < minSep) minSep = d;
        }
      }
      return {
        nPlayers: players.length,
        meanSpeed,
        meanStride: mean("strideM"),
        meanOsc:    mean("verticalOscCm"),
        meanGrf:    mean("grfBW"),
        motor:      Math.min(1, meanSpeed / 9),
        cardiac:    Math.min(1, mean("grfBW") / 3),
        minSeparation: Number.isFinite(minSep) ? minSep : null,
        color: videoFrame.teamColors?.[idx] ?? (idx === 0 ? "#58E6D9" : "#F0A830"),
        label: `Team ${idx === 0 ? "A" : "B"}`,
      };
    };
    return { teamA: mk(t0, 0), teamB: mk(t1, 1) };
  }, [videoFrame]);

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

      {/* Mode toggle */}
      <section className="px-8 sm:px-4 max-w-6xl mx-auto mb-4">
        <div className="flex items-center gap-2 flex-wrap">
          <ModeButton active={mode === "synthetic"} onClick={() => setMode("synthetic")}>
            synthetic scene
          </ModeButton>
          <ModeButton active={mode === "video"} onClick={() => setMode("video")}>
            real video
          </ModeButton>
        </div>
        {mode === "video" && (
          <VideoSourceInput
            videoUrl={videoUrl}
            setVideoUrl={setVideoUrl}
            setVideoSrc={setVideoSrc}
          />
        )}
      </section>

      {/* Viewport */}
      <section className="px-8 sm:px-4 max-w-6xl mx-auto">
        {mode === "synthetic" ? (
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
        ) : (
          <DualBodyPanel
            teamA={teamSummaries.teamA}
            teamB={teamSummaries.teamB}
            ballMetrics={videoFrame?.ballMetrics}
          >
            <div className="border border-darkBorder bg-black flex-1">
              {videoSrc ? (
                <VideoPoseTracker
                  src={videoSrc}
                  onFrameUpdate={handleVideoFrame}
                  detectionHz={12}
                />
              ) : (
                <div className="aspect-video flex items-center justify-center mono text-xs uppercase tracking-widest text-muted">
                  pick a sample clip above, paste a direct .mp4 URL, or upload a file
                </div>
              )}
            </div>
            <div className="mt-3">
              <BallStatsCard ballMetrics={videoFrame?.ballMetrics} />
            </div>
          </DualBodyPanel>
        )}

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

function ModeButton({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`mono text-xs uppercase tracking-wider px-3 py-2 border transition-colors ${
        active
          ? "border-primary text-primary bg-darkSoft"
          : "border-darkBorder text-muted hover:text-light"
      }`}
    >
      {children}
    </button>
  );
}

const SAMPLE_CLIP_GROUPS = [
  {
    label: "football",
    clips: [
      { label: "Match 2 · 1080p", src: "/football/m2-res_1080p.mp4" },
      { label: "Match 2 · 720p",  src: "/football/m2-res_720p.mp4"  },
      { label: "Match 2 · 470p",  src: "/football/m2-res_470p.mp4"  },
      { label: "Match 2 · 360p",  src: "/football/m2-res_360p.mp4"  },
      { label: "Match 2 · 1372p", src: "/football/m2-res_1372p.mp4" },
      { label: "Match 3 · 1080p", src: "/football/m3-res_1080p.mp4" },
      { label: "Match 4 · 1080p", src: "/football/m4-res_1080p.mp4" },
    ],
  },
  {
    label: "sprint / single-athlete",
    clips: [
      { label: "Bolt 100 m",          src: "/videos/bolt-force-motion_annotated.mp4" },
      { label: "Powell start",        src: "/videos/powell-start_annotated.mp4" },
      { label: "Drogba header",       src: "/videos/drogba-header_annotated.mp4" },
      { label: "Beijing bird's-eye",  src: "/videos/beijing_annotated.mp4" },
      { label: "Struggle",            src: "/videos/struggle_annotated.mp4" },
    ],
  },
];

function VideoSourceInput({ videoUrl, setVideoUrl, setVideoSrc }) {
  const inputRef = useRef(null);
  const [warn, setWarn] = useState("");

  const tryLoad = (url) => {
    const u = url.trim();
    if (!u) return;
    if (/youtube\.com|youtu\.be|tiktok\.com|instagram\.com|facebook\.com\/watch/i.test(u)) {
      setWarn("YouTube / TikTok / Instagram embeds are sandboxed: browsers cannot read their pixels (CORS + iframe). Use a direct .mp4 URL, upload a file, or pick a sample clip below.");
      return;
    }
    setWarn("");
    setVideoSrc(u);
  };

  return (
    <div className="flex flex-col gap-2 w-full mt-2">
      <div className="flex items-center gap-2 flex-wrap">
        <input
          type="text"
          placeholder="direct .mp4 URL …"
          value={videoUrl}
          onChange={(e) => setVideoUrl(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") tryLoad(videoUrl); }}
          className="flex-1 min-w-[16rem] bg-darkSoft border border-darkBorder text-light mono text-xs px-3 py-2 focus:outline-none focus:border-primary"
        />
        <button
          onClick={() => tryLoad(videoUrl)}
          className="mono text-xs uppercase tracking-wider px-3 py-2 border border-primary text-primary hover:bg-primary hover:text-dark transition-colors"
        >
          load
        </button>
        <input
          ref={inputRef}
          type="file"
          accept="video/*"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (!f) return;
            const url = URL.createObjectURL(f);
            setVideoSrc(url);
            setVideoUrl(f.name);
            setWarn("");
          }}
        />
        <button
          onClick={() => inputRef.current?.click()}
          className="mono text-xs uppercase tracking-wider px-3 py-2 border border-darkBorder text-muted hover:text-light"
        >
          upload file
        </button>
      </div>

      {warn && (
        <div className="mono text-[11px] text-warm border border-warm/40 bg-warm/10 px-3 py-2">
          {warn}
        </div>
      )}

      {SAMPLE_CLIP_GROUPS.map((group) => (
        <div key={group.label} className="flex items-center gap-2 flex-wrap">
          <span className="mono text-[10px] uppercase tracking-widest text-muted min-w-[10rem]">
            {group.label} →
          </span>
          {group.clips.map((c) => (
            <button
              key={c.src}
              onClick={() => {
                setWarn("");
                setVideoUrl(c.label);
                setVideoSrc(c.src);
              }}
              className="mono text-[10px] uppercase tracking-wider px-2 py-1 border border-darkBorder text-muted hover:border-primary hover:text-primary transition-colors"
            >
              {c.label}
            </button>
          ))}
        </div>
      ))}
    </div>
  );
}

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
          least-squares 2×2 solve). In synthetic mode the red dot is the
          ground-truth ball; the gap between them is the team&apos;s reaction
          lag — a quantity the framework exposes that direct ball tracking
          cannot.
        </li>
        <li>
          In <strong>real video</strong> mode the entire pipeline runs in the
          browser via MediaPipe BlazePose loaded from CDN: pose detection
          per frame → torso vector per person from world-coordinate shoulders
          and hips → same attention-focus solver. Three football match clips
          ship at 1080p in the picker; m2 also has 360p/470p/720p/1372p
          variants for resolution experiments. Detection is best when
          players are at least ~50 pixels tall — m2 at 1080p gives roughly
          that on the dominant ball-side cluster; the deep-background players
          will partially miss. The sprint and technique clips in the second
          row are easier targets where the pose pipeline is fully reliable.
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
