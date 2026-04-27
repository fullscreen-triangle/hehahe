import Head from "next/head";
import Link from "next/link";
import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import { useBody } from "@/lib/bodyState";

const PartitionCanvas = dynamic(
  () => import("@/components/compute/PartitionCanvas"),
  { ssr: false }
);

export default function PartitionTool() {
  const [n, setN] = useState(3);
  const [l, setL] = useState(1);
  const [m, setM] = useState(0);
  const [intensity, setIntensity] = useState(1);

  // Make sure (l, m) are valid for the chosen n.
  const validL = Math.min(l, n - 1);
  const validM = Math.max(-validL, Math.min(validL, m));

  const C_n = 2 * n * n;

  const { setAll } = useBody();
  useEffect(() => {
    // The partition tool is the most "thought-y" page — it's about
    // the indexing of cognitive states themselves.
    setAll({
      thought: 0.85,
      perception: 0.3,
      motor: 0.15,
      baseline: 0.4,
      cardiac: 0.45,
    });
  }, [setAll]);

  const labelOrbital = (n, l) => {
    const letters = ["s", "p", "d", "f", "g", "h"];
    return `${n}${letters[l] ?? "?"}`;
  };

  return (
    <>
      <Head>
        <title>Partition Coordinates — Olduvai</title>
      </Head>

      <section className="pt-24 pb-4 px-8 sm:px-4 max-w-5xl mx-auto">
        <Link
          href="/tools"
          className="mono text-xs uppercase tracking-widest text-muted hover:text-primary transition-colors"
        >
          ← Tools
        </Link>
        <h1 className="text-3xl font-semibold text-light mt-4 mb-2">
          Partition Coordinates
        </h1>
        <p className="mono text-sm text-muted max-w-2xl">
          Partition cells (n, ℓ, m, s) span the framework&apos;s state
          space. Each cell&apos;s spatial form is the probability density
          of the corresponding hydrogen-like orbital — raymarched on
          the GPU. The display field IS the partition cell.
        </p>
      </section>

      <section className="px-8 sm:px-4 max-w-5xl mx-auto">
        <div className="relative bg-darkSoft border border-darkBorder h-[520px] sm:h-[400px]">
          <PartitionCanvas n={n} l={validL} m={validM} intensity={intensity} />
          <div className="absolute top-2 left-3 mono text-[10px] uppercase tracking-widest text-light">
            {labelOrbital(n, validL)} · m = {validM} · C(n) = 2n² = {C_n}
          </div>
          <div className="absolute bottom-2 right-3 mono text-[10px] uppercase tracking-widest text-muted text-right">
            <div>density · |ψ|²</div>
            <div className="text-primary/70">render ≡ compute</div>
          </div>
        </div>

        {/* Quantum-number controls */}
        <div className="grid grid-cols-4 gap-4 mt-6 md:grid-cols-2 sm:grid-cols-1">
          <NumPicker label="n (principal)" value={n} options={[1, 2, 3, 4, 5]} onChange={(v) => {
            setN(v);
            if (l > v - 1) setL(v - 1);
          }} />
          <NumPicker label="ℓ (angular)" value={validL} options={Array.from({ length: n }, (_, i) => i)} onChange={(v) => {
            setL(v);
            if (Math.abs(m) > v) setM(0);
          }} />
          <NumPicker label="m (magnetic)" value={validM} options={Array.from({ length: 2 * validL + 1 }, (_, i) => i - validL)} onChange={setM} />
          <label className="block">
            <div className="flex justify-between mb-1">
              <span className="mono text-[10px] uppercase tracking-wider text-muted">intensity</span>
              <span className="mono text-[10px] text-light">{intensity.toFixed(2)}</span>
            </div>
            <input
              type="range"
              min={0.2}
              max={3}
              step={0.05}
              value={intensity}
              onChange={(e) => setIntensity(parseFloat(e.target.value))}
              className="w-full accent-primary"
            />
          </label>
        </div>

        {/* Capacity table */}
        <div className="mt-8 border border-darkBorder bg-darkSoft/60 p-5">
          <div className="mono text-xs uppercase tracking-widest text-primary mb-3">
            C(n) = 2n²
          </div>
          <div className="grid grid-cols-7 gap-2 mono text-xs sm:grid-cols-4">
            {[1, 2, 3, 4, 5, 6, 7].map((nn) => (
              <button
                key={nn}
                onClick={() => {
                  setN(nn);
                  if (l > nn - 1) setL(nn - 1);
                }}
                className={`p-2 border transition-colors ${
                  n === nn
                    ? "border-primary text-primary bg-darkSoft"
                    : "border-darkBorder text-muted hover:text-light"
                }`}
              >
                <div>n = {nn}</div>
                <div className="text-light text-base">{2 * nn * nn}</div>
              </button>
            ))}
          </div>
        </div>

        <div className="mt-6 mono text-[11px] text-muted leading-relaxed max-w-2xl">
          The framework&apos;s capacity law derives from finite phase-space
          partitioning under categorical exclusion. Each (n, ℓ, m, s)
          cell is a distinguishable state; the spatial density is the
          probability of finding the system in that cell. Higher n
          cells nest inside lower ones, and the C(n) count is exact
          for n = 1…7 by direct enumeration.
        </div>
      </section>
      <div className="h-24" />
    </>
  );
}

function NumPicker({ label, value, options, onChange }) {
  return (
    <div>
      <div className="mono text-[10px] uppercase tracking-wider text-muted mb-1">
        {label}
      </div>
      <div className="flex flex-wrap gap-1">
        {options.map((opt) => (
          <button
            key={opt}
            onClick={() => onChange(opt)}
            className={`mono text-xs w-9 h-9 border transition-colors ${
              value === opt
                ? "border-primary text-primary bg-darkSoft"
                : "border-darkBorder text-muted hover:text-light"
            }`}
          >
            {opt}
          </button>
        ))}
      </div>
    </div>
  );
}
