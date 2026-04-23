import Head from "next/head";
import Link from "next/link";
import dynamic from "next/dynamic";
import { motion } from "framer-motion";

const ChargeFieldCanvas = dynamic(
  () => import("@/components/compute/ChargeFieldCanvas"),
  { ssr: false }
);

export default function Home() {
  return (
    <>
      <Head>
        <title>Olduvai — Closed-Circuit Charge Framework</title>
      </Head>

      {/* The charge field IS the hero. The framebuffer is the state;
          what you observe is the computation. */}
      <div className="fixed inset-0 -z-10">
        <ChargeFieldCanvas
          resolution={256}
          seed={{ intensity: 1.1, diffuse: 0.14, relax: 0.45, decay: 0.0025 }}
        />
      </div>

      <section className="relative min-h-screen flex flex-col items-center justify-center px-8 pt-24 pb-16 sm:px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.9, ease: "easeOut" }}
          className="max-w-4xl text-center"
        >
          <div className="mono text-xs uppercase tracking-[0.3em] text-primary/80 mb-4">
            rendering · computing · observation
          </div>
          <h1 className="text-5xl sm:text-3xl md:text-4xl font-semibold leading-tight text-light mb-6">
            The body is a <span className="text-primary">closed non-grounded circuit</span>,<br />
            and what you see is the field that computes itself.
          </h1>
          <p className="mono text-sm text-muted max-w-2xl mx-auto mb-10 leading-relaxed">
            A theoretical framework for biomechanics, autonomous control, and
            consciousness grounded in a single axiom: bounded phase space with
            no external ground. Every pixel above is both the rendered output
            and the simulation state — move your cursor to inject charge and
            watch the circuit redistribute it.
          </p>

          <div className="flex items-center justify-center gap-4 sm:flex-col">
            <Link
              href="/framework"
              className="mono text-sm uppercase tracking-wider px-6 py-3 border border-primary text-primary hover:bg-primary hover:text-dark transition-colors"
            >
              Read the framework →
            </Link>
            <Link
              href="/tools"
              className="mono text-sm uppercase tracking-wider px-6 py-3 border border-darkBorder text-light hover:border-light transition-colors"
            >
              Run the tools
            </Link>
          </div>
        </motion.div>

        {/* Tiny legend pinned to bottom-left */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.2, duration: 0.8 }}
          className="absolute bottom-6 left-6 mono text-[10px] uppercase tracking-widest text-muted lg:hidden"
        >
          <div>ρ(x,t) charge density</div>
          <div>J = −∇φ current</div>
          <div>R local coherence</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.2, duration: 0.8 }}
          className="absolute bottom-6 right-6 mono text-[10px] uppercase tracking-widest text-muted lg:hidden text-right"
        >
          <div>closed BC · no ground</div>
          <div>Q = √(2CP)</div>
          <div>observation ≡ computation</div>
        </motion.div>
      </section>
    </>
  );
}
