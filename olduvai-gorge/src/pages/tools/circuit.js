import Head from "next/head";
import Link from "next/link";
import dynamic from "next/dynamic";
import { useState } from "react";

const ChargeFieldCanvas = dynamic(
  () => import("@/components/compute/ChargeFieldCanvas"),
  { ssr: false }
);

export default function CircuitPoke() {
  const [params, setParams] = useState({
    diffuse: 0.14,
    relax: 0.45,
    decay: 0.0025,
    intensity: 1.1,
  });

  const update = (key) => (e) =>
    setParams((p) => ({ ...p, [key]: parseFloat(e.target.value) }));

  return (
    <>
      <Head>
        <title>Closed-Circuit Poke — Olduvai</title>
      </Head>

      <div className="fixed inset-0 -z-10">
        <ChargeFieldCanvas
          key={`${params.diffuse}-${params.relax}-${params.decay}-${params.intensity}`}
          resolution={320}
          seed={params}
        />
      </div>

      <section className="relative pt-24 px-8 sm:px-4 max-w-5xl mx-auto">
        <Link
          href="/tools"
          className="mono text-xs uppercase tracking-widest text-muted hover:text-primary transition-colors"
        >
          ← Tools
        </Link>
        <h1 className="text-3xl font-semibold text-light mt-4 mb-2">
          Closed-Circuit Poke
        </h1>
        <p className="mono text-sm text-muted max-w-2xl">
          Move your cursor anywhere on the screen to inject charge. The
          continuity equation ∂ρ/∂t = −∇·J runs on the GPU under closed
          boundary conditions — there is no external ground and nothing
          leaves the circuit.
        </p>
      </section>

      <section className="fixed bottom-6 left-6 right-6 z-10 flex items-end justify-center gap-6 pointer-events-none lg:flex-col lg:items-start">
        <div className="pointer-events-auto bg-darkSoft/80 backdrop-blur border border-darkBorder p-4 w-full max-w-md">
          <div className="mono text-[10px] uppercase tracking-widest text-muted mb-3">
            physics uniforms
          </div>
          <div className="space-y-2">
            <Slider label="diffuse" value={params.diffuse} onChange={update("diffuse")} min={0} max={0.5} step={0.005} />
            <Slider label="relax" value={params.relax} onChange={update("relax")} min={0} max={1} step={0.02} />
            <Slider label="decay" value={params.decay} onChange={update("decay")} min={0} max={0.05} step={0.0005} />
            <Slider label="intensity" value={params.intensity} onChange={update("intensity")} min={0.1} max={2.5} step={0.05} />
          </div>
        </div>
      </section>
    </>
  );
}

function Slider({ label, value, onChange, min, max, step }) {
  return (
    <label className="block">
      <div className="flex justify-between">
        <span className="mono text-[10px] uppercase tracking-wider text-muted">
          {label}
        </span>
        <span className="mono text-[10px] text-primary">
          {value.toFixed(step < 0.01 ? 4 : step < 1 ? 3 : 2)}
        </span>
      </div>
      <input
        type="range"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={onChange}
        className="w-full accent-primary"
      />
    </label>
  );
}
