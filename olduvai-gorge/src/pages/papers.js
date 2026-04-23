import Head from "next/head";
import dynamic from "next/dynamic";

const ChargeFieldCanvas = dynamic(
  () => import("@/components/compute/ChargeFieldCanvas"),
  { ssr: false }
);

const PAPERS = [
  {
    n: "I",
    title: "The Musculoskeletal System as a Closed Non-Grounded Charge Circuit",
    subtitle:
      "Derivation from Hodgkin–Huxley, Kirchhoff's laws, and the sliding-filament mechanism",
    summary:
      "Establishes the closed non-grounded circuit as the correct model of the neuromuscular system. Derives Q_motor ≈ 290 mC/s from first principles; explains the deafferentation paradox as a circuit break rather than a feedback loss; predicts and validates motor-unit latency and the whole-muscle charge budget.",
    file: "/papers/derivation-of-musculo-skeletal-system.pdf",
    date: "2026",
  },
  {
    n: "II",
    title:
      "Rambling and Trembling as Distinct Components of the Closed Postural Control Circuit",
    subtitle: "Multi-sensor wearable validation of a hierarchical decomposition",
    summary:
      "Interprets the rambling/trembling decomposition of the center-of-pressure signal as two time scales of a single closed circuit. Simulator matches empirical dual-task, aging, Parkinson's, and ataxia signatures; multi-sensor consistency across CoP, IMU, EMG, and pressure insole is shown.",
    file: "/papers/rambling-trembling-wearable-sensors.pdf",
    date: "2026",
  },
  {
    n: "III",
    title:
      "Continuous Charge Subtraction for Thought and Muscle Movement",
    subtitle:
      "Orthogonal behavioural conditions, activity–sleep mirror law, and single-subject longitudinal wearable validation",
    summary:
      "Introduces the four-condition spanning theorem and the mirror-law identifiability criterion. Validates the subtraction on 86 nights + four runs of real data: Q_thought = 133.5 mC/s, Q_motor = 290.9 mC/s, Q_dream/Q_thought = 0.975 against the framework prediction √0.95.",
    file: "/papers/orthogonal-charge-quantification.pdf",
    date: "2026",
  },
];

export default function Papers() {
  return (
    <>
      <Head>
        <title>Papers — Olduvai</title>
      </Head>

      <div className="fixed inset-0 -z-10 opacity-25">
        <ChargeFieldCanvas
          resolution={192}
          injectOnPointer={false}
          seed={{ intensity: 0.6, diffuse: 0.1, relax: 0.4, decay: 0.004 }}
        />
      </div>

      <section className="relative pt-28 pb-24 px-8 sm:px-4 max-w-5xl mx-auto">
        <header className="mb-12">
          <div className="mono text-xs uppercase tracking-[0.3em] text-primary/80 mb-4">
            publications
          </div>
          <h1 className="text-4xl sm:text-3xl font-semibold text-light mb-4">
            Papers
          </h1>
          <p className="mono text-sm text-muted max-w-2xl leading-relaxed">
            Three companion papers that together specify the closed-circuit
            framework from the muscle to the cognitive slice, validate it on
            a single-subject longitudinal record, and separate thought from
            motor charge via orthogonal-conditions subtraction.
          </p>
        </header>

        <div className="space-y-5">
          {PAPERS.map((p) => (
            <a
              key={p.n}
              href={p.file}
              target="_blank"
              rel="noreferrer"
              className="block border border-darkBorder bg-darkSoft/60 hover:border-primary transition-colors p-6 group"
            >
              <div className="flex items-start gap-6 md:flex-col md:gap-3">
                <div className="mono text-5xl text-primary/40 group-hover:text-primary transition-colors md:text-3xl">
                  {p.n}
                </div>
                <div className="flex-1">
                  <div className="flex items-baseline justify-between gap-4 mb-2 md:flex-col md:gap-1">
                    <h3 className="text-xl font-semibold text-light leading-snug">
                      {p.title}
                    </h3>
                    <span className="mono text-xs uppercase tracking-widest text-muted">
                      {p.date}
                    </span>
                  </div>
                  <div className="mono text-xs uppercase tracking-wider text-primary/70 mb-3">
                    {p.subtitle}
                  </div>
                  <p className="mono text-sm text-muted leading-relaxed">
                    {p.summary}
                  </p>
                  <div className="mono text-xs uppercase tracking-wider text-primary mt-4 group-hover:text-light transition-colors">
                    open PDF →
                  </div>
                </div>
              </div>
            </a>
          ))}
        </div>
      </section>
    </>
  );
}
