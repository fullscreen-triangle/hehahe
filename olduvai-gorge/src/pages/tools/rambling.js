import Head from "next/head";
import Link from "next/link";
import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { useBody } from "@/lib/bodyState";

const RamblingCanvas = dynamic(
  () => import("@/components/compute/RamblingCanvas"),
  { ssr: false }
);

export default function RamblingTool() {
  const [params, setParams] = useState({
    cutoffHz: 0.4,
    ramAmp: 0.7,
    tremAmp: 0.35,
    noise: 0.15,
    sampleHz: 50,
  });

  // While this tool is open, the body's "balance" theme dominates:
  // postural control is mainly motor + perception coupling.
  const { setAll } = useBody();
  useEffect(() => {
    setAll({
      motor: 0.55,
      perception: 0.55,
      thought: 0.25,
      baseline: 0.45,
      cardiac: 0.5,
    });
  }, [setAll]);

  const update = (key) => (e) =>
    setParams((p) => ({ ...p, [key]: parseFloat(e.target.value) }));

  return (
    <>
      <Head>
        <title>Rambling / Trembling — Olduvai</title>
      </Head>

      <section className="pt-24 pb-4 px-8 sm:px-4 max-w-5xl mx-auto">
        <Link
          href="/tools"
          className="mono text-xs uppercase tracking-widest text-muted hover:text-primary transition-colors"
        >
          ← Tools
        </Link>
        <h1 className="text-3xl font-semibold text-light mt-4 mb-2">
          Rambling / Trembling
        </h1>
        <p className="mono text-sm text-muted max-w-2xl">
          Live decomposition of a synthesised centre-of-pressure trace
          into the slow supraspinal <em>rambling</em> drift and the
          fast peripheral <em>trembling</em> oscillation. The buffer
          you see is the filter state — there is no precomputed plot.
        </p>
      </section>

      <section className="px-8 sm:px-4 max-w-5xl mx-auto">
        <div className="relative bg-darkSoft border border-darkBorder h-[440px] sm:h-[320px]">
          <RamblingCanvas params={params} />
          <div className="absolute top-2 left-3 mono text-[10px] uppercase tracking-widest text-light">
            CoP · raw / rambling / trembling
          </div>
          <div className="absolute bottom-2 right-3 mono text-[10px] uppercase tracking-widest text-muted text-right">
            <div><span className="text-primary">●</span> raw CoP</div>
            <div><span style={{ color: "#F0A830" }}>●</span> rambling (LP at f_c)</div>
            <div><span style={{ color: "#B63E96" }}>●</span> trembling (residual)</div>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 mt-6 md:grid-cols-1">
          <Slider label="cutoff f_c" unit="Hz" v={params.cutoffHz} onChange={update("cutoffHz")} min={0.05} max={2} step={0.01} />
          <Slider label="rambling amp" v={params.ramAmp} onChange={update("ramAmp")} min={0} max={1.5} step={0.01} />
          <Slider label="trembling amp" v={params.tremAmp} onChange={update("tremAmp")} min={0} max={1.5} step={0.01} />
          <Slider label="noise" v={params.noise} onChange={update("noise")} min={0} max={0.6} step={0.01} />
          <Slider label="sample rate" unit="Hz" v={params.sampleHz} onChange={update("sampleHz")} min={20} max={200} step={1} />
          <PresetButtons setParams={setParams} />
        </div>

        <div className="mt-8 border border-darkBorder bg-darkSoft/60 p-5">
          <div className="mono text-xs uppercase tracking-widest text-primary mb-2">
            Framework note
          </div>
          <div className="mono text-sm text-light leading-relaxed mb-2">
            The two components correspond to two timescales of a single
            closed postural circuit:
          </div>
          <ul className="mono text-sm text-muted leading-relaxed list-disc pl-5 space-y-1">
            <li><span style={{ color: "#F0A830" }}>rambling</span> — supraspinal drift, &lt; f_c, dominant in cognitive-load conditions.</li>
            <li><span style={{ color: "#B63E96" }}>trembling</span> — peripheral oscillation, &gt; f_c, dominant in aging and Parkinson&apos;s.</li>
            <li>raw = rambling + trembling exactly — reconstruction error is at numerical precision.</li>
          </ul>
        </div>
      </section>
      <div className="h-24" />
    </>
  );
}

function Slider({ label, unit, v, onChange, min, max, step }) {
  return (
    <label className="block">
      <div className="flex justify-between mb-1">
        <span className="mono text-[10px] uppercase tracking-wider text-muted">
          {label} {unit && <span className="text-primary/60">{unit}</span>}
        </span>
        <span className="mono text-[10px] text-light">
          {v.toFixed(step < 0.1 ? 2 : 1)}
        </span>
      </div>
      <input
        type="range"
        value={v}
        min={min}
        max={max}
        step={step}
        onChange={onChange}
        className="w-full accent-primary"
      />
    </label>
  );
}

function PresetButtons({ setParams }) {
  const presets = {
    healthy: { cutoffHz: 0.4, ramAmp: 0.7, tremAmp: 0.35, noise: 0.15, sampleHz: 50 },
    cognitiveLoad: { cutoffHz: 0.4, ramAmp: 1.4, tremAmp: 0.45, noise: 0.2, sampleHz: 50 },
    aging: { cutoffHz: 0.4, ramAmp: 0.85, tremAmp: 0.65, noise: 0.25, sampleHz: 50 },
    parkinson: { cutoffHz: 0.4, ramAmp: 0.45, tremAmp: 1.05, noise: 0.3, sampleHz: 50 },
  };
  return (
    <div>
      <div className="mono text-[10px] uppercase tracking-wider text-muted mb-1">
        presets
      </div>
      <div className="flex flex-wrap gap-1">
        {Object.entries(presets).map(([k, v]) => (
          <button
            key={k}
            onClick={() => setParams(v)}
            className="mono text-[10px] uppercase tracking-wider px-2 py-1 border border-darkBorder text-muted hover:text-primary hover:border-primary transition-colors"
          >
            {k}
          </button>
        ))}
      </div>
    </div>
  );
}
