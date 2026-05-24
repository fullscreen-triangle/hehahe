import Head from "next/head";
import Link from "next/link";
import dynamic from "next/dynamic";

const ChargeFieldCanvas = dynamic(
  () => import("@/components/compute/ChargeFieldCanvas"),
  { ssr: false }
);

const TOOLS = [
  {
    slug: "charge",
    title: "Charge Calculator",
    status: "ready",
    blurb:
      "Port of analyze_charge.py to the browser. Enter body and autonomic parameters; Q_thought, Q_motor, Q_perception, and Q_dream are computed entirely on the GPU — the glowing silhouette IS the calculation, and the cross-page anatomy panel lights up with you.",
  },
  {
    slug: "motion",
    title: "Motion Analysis",
    status: "ready",
    blurb:
      "Annotated sprint and skill videos paired with their per-frame pose tracks. Joint-angle and landmark deltas drive the body panel in real time — Bolt, Powell, Drogba, Beijing. The walking GLB in the panel breathes with the motion.",
  },
  {
    slug: "football",
    title: "Football Observation Operator",
    status: "ready",
    blurb:
      "22 synthetic players on a regulation pitch; a fragment shader evaluates the per-pixel attention density Σ wᵢ exp(−½(θᵢ/σ)²) and the brightest pixel is the inferred ball. The white dot is the JS-side algebraic inverse, the red is ground truth — the gap is reaction lag. The right-side anatomy panel's cardiac compartment binds to ΔHR_auto (Q10 autonomic residual, not raw HR) and Q_motor is thermally corrected for ambient.",
  },
  {
    slug: "rambling",
    title: "Rambling / Trembling",
    status: "ready",
    blurb:
      "Live decomposition of a synthesised CoP trace into supraspinal rambling and peripheral trembling. The displayed traces are texel reads of the filter state; presets reproduce healthy, dual-task, aging, and Parkinson's signatures.",
  },
  {
    slug: "partition",
    title: "Partition Coordinates",
    status: "ready",
    blurb:
      "Hydrogen-like orbital density |ψ_(n,ℓ,m)|² raymarched on the GPU. Each (n, ℓ, m, s) cell is a partition coordinate of the framework; C(n) = 2n² is the count of independent cells at level n.",
  },
  {
    slug: "circuit",
    title: "Closed-Circuit Poke",
    status: "ready",
    blurb:
      "The hero field, isolated. Move your cursor to inject charge and watch the continuity equation redistribute it under closed boundary conditions. There is no external ground — nothing escapes.",
  },
];

export default function ToolsIndex() {
  return (
    <>
      <Head>
        <title>Tools — Olduvai</title>
      </Head>

      <div className="fixed inset-0 -z-10 opacity-30">
        <ChargeFieldCanvas
          resolution={192}
          injectOnPointer={false}
          seed={{ intensity: 0.6, diffuse: 0.1, relax: 0.4, decay: 0.004 }}
        />
      </div>

      <section className="relative pt-28 pb-24 px-8 sm:px-4 max-w-5xl mx-auto">
        <header className="mb-12">
          <div className="mono text-xs uppercase tracking-[0.3em] text-primary/80 mb-4">
            interactive
          </div>
          <h1 className="text-4xl sm:text-3xl font-semibold text-light mb-4">
            Tools
          </h1>
          <p className="mono text-sm text-muted max-w-2xl leading-relaxed">
            Each tool is a GPU computation whose output frame is also its
            state buffer. Rendering is not a decoration; it is the next tick
            of the simulation.
          </p>
        </header>

        <div className="grid grid-cols-2 gap-4 md:grid-cols-1">
          {TOOLS.map((t) => {
            const ready = t.status === "ready";
            const card = (
              <div
                className={`border bg-darkSoft/60 p-6 h-full transition-all ${
                  ready
                    ? "border-darkBorder hover:border-primary cursor-pointer"
                    : "border-darkBorder opacity-60"
                }`}
              >
                <div className="flex justify-between items-start mb-3">
                  <h3 className="text-xl font-semibold text-light">{t.title}</h3>
                  <span
                    className={`mono text-[10px] uppercase tracking-widest px-2 py-1 ${
                      ready
                        ? "bg-primary/10 text-primary border border-primary/40"
                        : "bg-darkBorder/50 text-muted border border-darkBorder"
                    }`}
                  >
                    {t.status}
                  </span>
                </div>
                <p className="mono text-sm text-muted leading-relaxed">
                  {t.blurb}
                </p>
                {ready && (
                  <div className="mono text-xs uppercase tracking-wider text-primary mt-4">
                    open →
                  </div>
                )}
              </div>
            );
            return ready ? (
              <Link key={t.slug} href={`/tools/${t.slug}`}>
                {card}
              </Link>
            ) : (
              <div key={t.slug}>{card}</div>
            );
          })}
        </div>
      </section>
    </>
  );
}
