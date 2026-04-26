import Head from "next/head";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { loadMotion, MOTION_LIBRARY } from "@/lib/poseData";
import { useBody } from "@/lib/bodyState";
import PoseOverlay from "@/components/motion/PoseOverlay";

export default function MotionTool() {
  const [selected, setSelected] = useState(MOTION_LIBRARY[0]);
  const [motionData, setMotionData] = useState(null);
  const [frameIdx, setFrameIdx] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [videoSize, setVideoSize] = useState({ w: 1280, h: 720 });

  const videoRef = useRef(null);
  const { setAll, setPanelOpen, setFocusGLB, setView } = useBody();

  useEffect(() => {
    setPanelOpen(true);
  }, [setPanelOpen]);

  // Default the 3D anatomy panel to the walker model for this tool —
  // a body-in-motion paired with a body-in-motion.
  useEffect(() => {
    setFocusGLB("walker.glb");
  }, [setFocusGLB]);

  // Load the selected motion data
  useEffect(() => {
    let alive = true;
    setMotionData(null);
    setFrameIdx(0);
    loadMotion(selected).then((m) => {
      if (alive) setMotionData(m);
    });
    return () => {
      alive = false;
    };
  }, [selected]);

  // Sync frame index from the playing video
  useEffect(() => {
    const v = videoRef.current;
    if (!v || !motionData) return;
    let raf;
    const tick = () => {
      if (!v.paused && motionData.frames.length > 0) {
        const fps = motionData.info?.fps ?? 30;
        const idx = Math.min(
          motionData.frames.length - 1,
          Math.floor(v.currentTime * fps)
        );
        setFrameIdx(idx);
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [motionData]);

  const currentFrame = motionData?.frames?.[frameIdx];

  // Drive body activation from current frame's derived signals.
  useEffect(() => {
    if (!currentFrame?.derived) return;
    const d = currentFrame.derived;
    setAll({
      motor:       d.motorIntensity,
      thought:     0.25 + 0.35 * d.perceptionLoad, // active focus during motion
      perception:  0.4 + 0.5 * d.perceptionLoad,
      cardiac:     0.3 + 0.6 * d.cardiacLoad,
      respiratory: 0.3 + 0.5 * d.cardiacLoad,
      baseline:    0.45,
      visceral:    0.2,
    });
  }, [currentFrame, setAll]);

  const togglePlay = () => {
    const v = videoRef.current;
    if (!v) return;
    if (v.paused) {
      v.play();
      setPlaying(true);
    } else {
      v.pause();
      setPlaying(false);
    }
  };

  const onLoaded = () => {
    const v = videoRef.current;
    if (v) setVideoSize({ w: v.videoWidth || 1280, h: v.videoHeight || 720 });
  };

  return (
    <>
      <Head>
        <title>Motion Analysis — Olduvai</title>
      </Head>

      <section className="pt-24 pb-8 px-8 sm:px-4 max-w-6xl mx-auto">
        <Link
          href="/tools"
          className="mono text-xs uppercase tracking-widest text-muted hover:text-primary transition-colors"
        >
          ← Tools
        </Link>
        <h1 className="text-3xl font-semibold text-light mt-4 mb-2">
          Motion Analysis
        </h1>
        <p className="mono text-sm text-muted max-w-2xl">
          Annotated video plays alongside its pose track; per-frame
          joint and landmark deltas drive the cross-page anatomy panel
          on the right. The body lights up at the same instants that
          the runner's joints actually fire.
        </p>
      </section>

      {/* Library row */}
      <section className="px-8 sm:px-4 max-w-6xl mx-auto mb-4">
        <div className="flex flex-wrap gap-2">
          {MOTION_LIBRARY.map((m) => (
            <button
              key={m.id}
              onClick={() => {
                setSelected(m);
                setPlaying(false);
              }}
              className={`mono text-[10px] uppercase tracking-wider px-3 py-2 border transition-colors ${
                selected.id === m.id
                  ? "border-primary text-primary bg-darkSoft"
                  : "border-darkBorder text-muted hover:text-light"
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>
      </section>

      {/* Video + overlay */}
      <section className="px-8 sm:px-4 max-w-6xl mx-auto">
        <div
          className="relative bg-black border border-darkBorder"
          style={{ aspectRatio: `${videoSize.w} / ${videoSize.h}` }}
        >
          <video
            ref={videoRef}
            src={selected.video}
            onLoadedMetadata={onLoaded}
            playsInline
            className="absolute inset-0 w-full h-full object-contain"
          />
          <PoseOverlay
            width={videoSize.w}
            height={videoSize.h}
            frame={currentFrame}
            schema={motionData?.schema}
          />
          <div className="absolute top-2 left-2 mono text-[10px] uppercase tracking-widest text-light bg-dark/70 px-2 py-1 backdrop-blur">
            {selected.label} · frame {frameIdx + 1}
            {motionData ? ` / ${motionData.frames.length}` : ""}
          </div>
          <div className="absolute top-2 right-2 mono text-[10px] uppercase tracking-widest text-muted bg-dark/70 px-2 py-1 backdrop-blur">
            {selected.note}
          </div>
        </div>

        {/* Transport */}
        <div className="flex items-center gap-3 mt-3">
          <button
            onClick={togglePlay}
            className="mono text-xs uppercase tracking-wider px-4 py-2 border border-primary text-primary hover:bg-primary hover:text-dark transition-colors"
          >
            {playing ? "pause" : "play"}
          </button>
          <input
            type="range"
            min={0}
            max={motionData ? motionData.frames.length - 1 : 0}
            value={frameIdx}
            onChange={(e) => {
              const idx = parseInt(e.target.value);
              setFrameIdx(idx);
              const v = videoRef.current;
              const fps = motionData?.info?.fps ?? 30;
              if (v) v.currentTime = idx / fps;
            }}
            className="flex-1 accent-primary"
          />
          <span className="mono text-xs text-muted w-32 text-right">
            t = {currentFrame ? currentFrame.t.toFixed(2) : "—"} s
          </span>
        </div>

        {/* Per-frame derived signals */}
        {currentFrame?.derived && (
          <div className="grid grid-cols-4 gap-3 mt-6 sm:grid-cols-2">
            <DerivedReadout label="motor" value={currentFrame.derived.motorIntensity} colour="#58E6D9" />
            <DerivedReadout label="balance load" value={currentFrame.derived.balanceLoad} colour="#F0A830" />
            <DerivedReadout label="cardiac" value={currentFrame.derived.cardiacLoad} colour="#E6395A" />
            <DerivedReadout label="perception" value={currentFrame.derived.perceptionLoad} colour="#B63E96" />
          </div>
        )}

        {/* Optional bolt-schema biomechanics readout */}
        {currentFrame?.joints && (
          <div className="mt-6 border border-darkBorder bg-darkSoft/60 p-4">
            <div className="mono text-[10px] uppercase tracking-widest text-muted mb-3">
              joint angles
            </div>
            <div className="grid grid-cols-5 gap-3 sm:grid-cols-3">
              {Object.entries(currentFrame.joints).map(([k, v]) => (
                <div key={k} className="mono text-xs">
                  <div className="text-muted uppercase tracking-wider">{k}</div>
                  <div className="text-primary text-base">{v.toFixed(1)}°</div>
                </div>
              ))}
            </div>
            {currentFrame.grf && (
              <div className="grid grid-cols-3 gap-3 mt-4 pt-4 border-t border-darkBorder/60 sm:grid-cols-2">
                <Stat label="GRF vertical" v={currentFrame.grf.vertical} unit="N" />
                <Stat label="GRF horizontal" v={currentFrame.grf.horizontal} unit="N" />
                <Stat label="impact force" v={currentFrame.grf.impact_force} unit="N" />
              </div>
            )}
          </div>
        )}

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="mono text-[11px] text-muted leading-relaxed mt-6 max-w-2xl"
        >
          The right-side anatomy panel reads from this page in real
          time. Open it (handle on the right edge) and swap to the 3D
          tab — the walking model glows at intensities matching the
          motion you're scrubbing through. Rendering is computing.
        </motion.div>
      </section>
      <div className="h-24" />
    </>
  );
}

function DerivedReadout({ label, value, colour }) {
  return (
    <div className="border border-darkBorder bg-darkSoft/60 p-3">
      <div className="mono text-[10px] uppercase tracking-widest text-muted mb-2">
        {label}
      </div>
      <div className="h-1 bg-darkBorder mb-1">
        <div
          className="h-full transition-[width] duration-100"
          style={{ width: `${value * 100}%`, backgroundColor: colour }}
        />
      </div>
      <div className="mono text-xs" style={{ color: colour }}>
        {(value * 100).toFixed(0)}%
      </div>
    </div>
  );
}

function Stat({ label, v, unit }) {
  return (
    <div className="mono text-xs">
      <div className="text-muted uppercase tracking-wider">{label}</div>
      <div className="text-light">
        {v?.toFixed(1)} <span className="text-muted">{unit}</span>
      </div>
    </div>
  );
}
