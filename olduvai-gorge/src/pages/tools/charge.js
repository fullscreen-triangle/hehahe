import Head from "next/head";
import Link from "next/link";
import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import { computeCharges } from "@/lib/chargeModel";
import { useBody } from "@/lib/bodyState";

const AnatomyGlow = dynamic(
  () => import("@/components/compute/AnatomyGlow"),
  { ssr: false }
);

function NumberField({ label, unit, value, onChange, min, max, step }) {
  return (
    <label className="block">
      <div className="mono text-xs uppercase tracking-wider text-muted mb-1">
        {label} <span className="text-primary/60">{unit}</span>
      </div>
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
        className="w-full bg-darkSoft border border-darkBorder text-light mono text-sm px-3 py-2 focus:outline-none focus:border-primary"
      />
    </label>
  );
}

function SliderField({ label, unit, value, onChange, min, max, step }) {
  return (
    <label className="block">
      <div className="flex justify-between mb-1">
        <span className="mono text-xs uppercase tracking-wider text-muted">
          {label} <span className="text-primary/60">{unit}</span>
        </span>
        <span className="mono text-xs text-light">{value.toFixed(step < 1 ? 2 : 0)}</span>
      </div>
      <input
        type="range"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full accent-primary"
      />
    </label>
  );
}

function QReadout({ label, val, unit, colour, target, ratio }) {
  return (
    <div className="border border-darkBorder bg-darkSoft/60 p-4">
      <div className="mono text-[10px] uppercase tracking-widest text-muted mb-1">
        {label}
      </div>
      <div className="flex items-baseline gap-2">
        <span className="mono text-2xl" style={{ color: colour }}>
          {val.toFixed(1)}
        </span>
        <span className="mono text-xs text-muted">{unit}</span>
      </div>
      {target && (
        <div className="mono text-[10px] text-muted mt-1">
          target ~ {target}
        </div>
      )}
      {ratio !== undefined && (
        <div className="mono text-[10px] text-primary mt-1">
          ratio {ratio.toFixed(3)}
        </div>
      )}
    </div>
  );
}

export default function ChargeCalculator() {
  const [subject, setSubject] = useState({
    mass_kg: 83,
    height_cm: 185,
    age_yr: 30,
    sex: "m",
    hr_bpm: 86,
    rmssd_ms: 59.1,
    cadence_spm: 166,
    step_length_m: 1.12,
    peak_force_N: 1920,
  });

  const update = (key) => (v) => setSubject((s) => ({ ...s, [key]: v }));

  const res = useMemo(() => computeCharges(subject), [subject]);
  const Q = res.Q_mC_per_s;

  // Push component charges into the global body state so the persistent
  // anatomy panel lights up in sync with this page's computation.
  // Normalisation matches the reference maxima used by AnatomyGlow.
  const { setAll, setPanelOpen } = useBody();
  useEffect(() => {
    setAll({
      thought:    Math.min(1, Q.thought / 300),
      motor:      Math.min(1, Q.motor / 400),
      perception: Math.min(1, Q.perception / 150),
      dream:      Math.min(1, Q.dream / 200),
      baseline:   Math.min(1, Q.baseline / 300),
      cardiac:    0.4 + 0.4 * Math.min(1, (subject.hr_bpm - 50) / 60),
      respiratory: 0.3,
      visceral:   0.2,
    });
  }, [Q.thought, Q.motor, Q.perception, Q.dream, Q.baseline, subject.hr_bpm, setAll]);

  // Auto-open the anatomy panel once so the user sees the connection.
  useEffect(() => {
    setPanelOpen(true);
  }, [setPanelOpen]);

  return (
    <>
      <Head>
        <title>Charge Calculator — Olduvai</title>
      </Head>

      <section className="pt-24 pb-12 px-8 sm:px-4 max-w-6xl mx-auto">
        <Link
          href="/tools"
          className="mono text-xs uppercase tracking-widest text-muted hover:text-primary transition-colors"
        >
          ← Tools
        </Link>
        <h1 className="text-3xl font-semibold text-light mt-4 mb-2">
          Charge Calculator
        </h1>
        <p className="mono text-sm text-muted max-w-2xl">
          Subject parameters flow into the shader uniforms; the glowing
          silhouette is the computation. Numbers below are direct texel
          equivalents of what the GPU is rendering.
        </p>
      </section>

      <section className="px-8 sm:px-4 max-w-6xl mx-auto grid grid-cols-12 gap-6 md:grid-cols-1">
        {/* Inputs */}
        <div className="col-span-4 lg:col-span-12 space-y-3">
          <h2 className="mono text-xs uppercase tracking-widest text-muted mb-2">
            01 · Body
          </h2>
          <div className="grid grid-cols-2 gap-3">
            <NumberField label="mass" unit="kg" value={subject.mass_kg} onChange={update("mass_kg")} min={30} max={200} step={0.5} />
            <NumberField label="height" unit="cm" value={subject.height_cm} onChange={update("height_cm")} min={120} max={220} step={1} />
            <NumberField label="age" unit="yr" value={subject.age_yr} onChange={update("age_yr")} min={1} max={100} step={1} />
            <label className="block">
              <div className="mono text-xs uppercase tracking-wider text-muted mb-1">sex</div>
              <select
                value={subject.sex}
                onChange={(e) => update("sex")(e.target.value)}
                className="w-full bg-darkSoft border border-darkBorder text-light mono text-sm px-3 py-2 focus:outline-none focus:border-primary"
              >
                <option value="m">male</option>
                <option value="f">female</option>
              </select>
            </label>
          </div>

          <h2 className="mono text-xs uppercase tracking-widest text-muted mt-6 mb-2">
            02 · Autonomic
          </h2>
          <SliderField label="resting HR" unit="bpm" value={subject.hr_bpm} onChange={update("hr_bpm")} min={40} max={110} step={1} />
          <SliderField label="RMSSD" unit="ms" value={subject.rmssd_ms} onChange={update("rmssd_ms")} min={10} max={120} step={1} />

          <h2 className="mono text-xs uppercase tracking-widest text-muted mt-6 mb-2">
            03 · Locomotion
          </h2>
          <SliderField label="cadence" unit="steps/min" value={subject.cadence_spm} onChange={update("cadence_spm")} min={0} max={220} step={1} />
          <SliderField label="step length" unit="m" value={subject.step_length_m} onChange={update("step_length_m")} min={0} max={2.0} step={0.01} />
          <SliderField label="peak force" unit="N" value={subject.peak_force_N} onChange={update("peak_force_N")} min={0} max={4000} step={10} />
        </div>

        {/* GPU glow — this IS the computation display */}
        <div className="col-span-5 lg:col-span-12 h-[520px] border border-darkBorder bg-darkSoft/30 relative">
          <AnatomyGlow q={Q} />
          <div className="absolute top-2 left-2 mono text-[10px] uppercase tracking-widest text-muted">
            render ≡ compute
          </div>
        </div>

        {/* Q readouts */}
        <div className="col-span-3 lg:col-span-12 space-y-3">
          <h2 className="mono text-xs uppercase tracking-widest text-muted mb-2">
            04 · Component charges
          </h2>
          <QReadout label="Q_thought" val={Q.thought} unit="mC/s" colour="#B63E96" target="100–150" />
          <QReadout label="Q_motor" val={Q.motor} unit="mC/s" colour="#58E6D9" target="250–350" />
          <QReadout label="Q_perception" val={Q.perception} unit="mC/s" colour="#F0A830" target="50–100" />
          <QReadout label="Q_dream" val={Q.dream} unit="mC/s" colour="#B63E96" ratio={res.dream_thought_ratio} />
          <QReadout label="Q_baseline" val={Q.baseline} unit="mC/s" colour="#8a8aa0" />

          <div className="mono text-[10px] text-muted mt-4 pt-4 border-t border-darkBorder">
            <div>BMR {res.bmr.kcalPerDay.toFixed(0)} kcal/day · {res.bmr.watt.toFixed(1)} W</div>
            <div>Brain {res.brain.total.toFixed(2)} W (base/cog 50/50)</div>
            <div>κ = {res.cardiac.kappa.toFixed(4)} (ref 0.060)</div>
            <div>f_perc = {res.cardiac.frac.toFixed(2)}</div>
          </div>
        </div>
      </section>

      <section className="px-8 sm:px-4 max-w-6xl mx-auto mt-12 pb-24">
        <div className="border border-darkBorder bg-darkSoft/60 p-6">
          <div className="mono text-xs uppercase tracking-widest text-primary mb-2">
            Framework prediction
          </div>
          <div className="mono text-sm text-light leading-relaxed">
            Q_dream / Q_thought = √0.95 ≈ 0.975 regardless of subject parameters,
            because both components share the cortical capacitance and differ
            only by the REM sleep-stage metabolic multiplier. Your current value:{" "}
            <span className="text-primary">{res.dream_thought_ratio.toFixed(3)}</span>.
          </div>
        </div>
      </section>
    </>
  );
}
