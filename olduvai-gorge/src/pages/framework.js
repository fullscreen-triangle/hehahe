import Head from "next/head";
import Link from "next/link";
import dynamic from "next/dynamic";

const ChargeFieldCanvas = dynamic(
  () => import("@/components/compute/ChargeFieldCanvas"),
  { ssr: false }
);

function Axiom({ n, title, children }) {
  return (
    <div className="border border-darkBorder bg-darkSoft/60 p-6">
      <div className="mono text-xs uppercase tracking-widest text-primary mb-2">
        Axiom {n}
      </div>
      <h3 className="text-xl font-semibold text-light mb-3">{title}</h3>
      <div className="mono text-sm text-muted leading-relaxed">{children}</div>
    </div>
  );
}

function Claim({ label, formula, note }) {
  return (
    <div className="flex items-start gap-4 py-3 border-b border-darkBorder/60 last:border-b-0">
      <div className="mono text-xs uppercase tracking-wider text-primary min-w-[8rem]">
        {label}
      </div>
      <div className="flex-1">
        <div className="mono text-sm text-light">{formula}</div>
        {note && <div className="mono text-xs text-muted mt-1">{note}</div>}
      </div>
    </div>
  );
}

export default function Framework() {
  return (
    <>
      <Head>
        <title>Framework — Olduvai</title>
      </Head>

      <div className="fixed inset-0 -z-10 opacity-40">
        <ChargeFieldCanvas
          resolution={192}
          injectOnPointer={false}
          seed={{ intensity: 0.7, diffuse: 0.1, relax: 0.4, decay: 0.004 }}
        />
      </div>

      <article className="relative pt-28 pb-24 px-8 sm:px-4 max-w-5xl mx-auto">
        <header className="mb-12 text-center">
          <div className="mono text-xs uppercase tracking-[0.3em] text-primary/80 mb-4">
            theoretical foundations
          </div>
          <h1 className="text-4xl sm:text-3xl font-semibold text-light mb-4">
            A closed non-grounded charge circuit, from bounded phase space.
          </h1>
          <p className="mono text-sm text-muted max-w-2xl mx-auto leading-relaxed">
            Three axioms, one capacity law, and a charge-conservation
            accounting that spans molecular dynamics, motor control, and
            cognition.
          </p>
        </header>

        {/* Three axioms */}
        <section className="mb-16">
          <h2 className="mono text-xs uppercase tracking-widest text-muted mb-6">
            01 · Axioms
          </h2>
          <div className="grid grid-cols-3 gap-4 md:grid-cols-1">
            <Axiom n={1} title="Bounded phase space">
              The accessible configuration space of any biological system
              has finite measure μ(Ω) &lt; ∞. Membranes close the volume;
              Poincaré recurrence follows.
            </Axiom>
            <Axiom n={2} title="Categorical exclusion">
              At any time t the system occupies exactly one categorical
              state from a finite set. States are mutually exclusive and
              countable.
            </Axiom>
            <Axiom n={3} title="Finite resolution">
              Every measurement partitions Ω into distinguishable cells
              with a minimum volume δ &gt; 0. Perfect observation is
              forbidden; observation is categorical.
            </Axiom>
          </div>
        </section>

        {/* Capacity law */}
        <section className="mb-16">
          <h2 className="mono text-xs uppercase tracking-widest text-muted mb-6">
            02 · Capacity
          </h2>
          <div className="border border-darkBorder bg-darkSoft/60 p-8 text-center">
            <div className="mono text-3xl text-primary mb-3">C(n) = 2n²</div>
            <p className="mono text-sm text-muted max-w-xl mx-auto">
              Distinguishable states at partition level n. Derived from
              angular-momentum indexing (ℓ, m) with spin doubling; exact
              for n = 1…7 by direct enumeration.
            </p>
          </div>
        </section>

        {/* Core operations */}
        <section className="mb-16">
          <h2 className="mono text-xs uppercase tracking-widest text-muted mb-6">
            03 · Core operations
          </h2>
          <div className="border border-darkBorder bg-darkSoft/60 p-6">
            <Claim
              label="Closed BC"
              formula="∮ J·dA = 0"
              note="No external charge ground. Total charge is conserved inside the circuit."
            />
            <Claim
              label="Continuity"
              formula="∂ρ/∂t = −∇·J,   J = −σ∇φ"
              note="Charge density evolves by local redistribution; sub-systems couple capacitively."
            />
            <Claim
              label="Energy → charge"
              formula="Q = √(2·C·P·Δt)"
              note="Metabolic power converts to charge rate via sub-system aggregate capacitance."
            />
            <Claim
              label="Variance floor"
              formula="σ²_min ∝ K⁻¹"
              note="Coupling K above the Kuramoto threshold sets the minimum residual noise."
            />
            <Claim
              label="Zero-work apertures"
              formula="W_aperture = 0"
              note="Categorical selectivity via hard-wall geometry requires no thermodynamic work — resolving Maxwell's demon."
            />
          </div>
        </section>

        {/* Compartments */}
        <section className="mb-16">
          <h2 className="mono text-xs uppercase tracking-widest text-muted mb-6">
            04 · Capacitive compartments
          </h2>
          <div className="grid grid-cols-4 gap-3 md:grid-cols-2 sm:grid-cols-1">
            {[
              { name: "C_brain", val: "1.0 mF", note: "cortex aggregate" },
              { name: "C_motor", val: "141 μF", note: "motor + sarcolemma" },
              { name: "C_perception", val: "500 μF", note: "sensory subnet" },
              { name: "C_cardiac", val: "~20 μF", note: "heart muscle" },
            ].map((c) => (
              <div
                key={c.name}
                className="border border-darkBorder bg-darkSoft/60 p-4"
              >
                <div className="mono text-xs uppercase tracking-wider text-primary mb-1">
                  {c.name}
                </div>
                <div className="mono text-2xl text-light mb-1">{c.val}</div>
                <div className="mono text-xs text-muted">{c.note}</div>
              </div>
            ))}
          </div>
        </section>

        {/* Orthogonal conditions */}
        <section className="mb-16">
          <h2 className="mono text-xs uppercase tracking-widest text-muted mb-6">
            05 · Orthogonal conditions
          </h2>
          <p className="mono text-sm text-muted leading-relaxed mb-4">
            Four behavioural states span the component charge subspace:
          </p>
          <div className="mono text-xs grid grid-cols-5 gap-2 text-center border border-darkBorder bg-darkSoft/60 p-4">
            <div className="text-muted"></div>
            <div className="text-primary">baseline</div>
            <div className="text-primary">motor</div>
            <div className="text-primary">perception</div>
            <div className="text-primary">thought</div>

            <div className="text-light">Deep sleep</div>
            <div>0.85</div>
            <div>0</div>
            <div>0</div>
            <div>0</div>

            <div className="text-light">REM</div>
            <div>0.95</div>
            <div>0</div>
            <div>0</div>
            <div>1</div>

            <div className="text-light">Running</div>
            <div>0.90</div>
            <div>1</div>
            <div>1</div>
            <div>0.1</div>

            <div className="text-light">Wakeful rest</div>
            <div>1.00</div>
            <div>0.1</div>
            <div>1</div>
            <div>1</div>
          </div>
          <p className="mono text-xs text-muted mt-3">
            Condition number κ(M) = 6.8; inversion yields component charges
            from observed per-state metabolic rates.
          </p>
        </section>

        {/* Scales */}
        <section className="mb-16">
          <h2 className="mono text-xs uppercase tracking-widest text-muted mb-6">
            06 · Scale coverage
          </h2>
          <div className="mono text-xs text-muted leading-relaxed">
            The framework applies from 10⁻¹⁰ m (quantum transitions) to 10⁷ m
            (satellite-relative kinematics in autonomous-vehicle control).
            Across scales, the same machinery — closed BC, partition coordinates,
            variance minimisation — delivers working predictions. Specifically:
            synaptic charge budgets (10⁻⁹ m), muscle-fibre charge circulation
            (10⁻³ m), whole-body posture (10⁰ m), and high-velocity intent
            decomposition in driving (10² m).
          </div>
        </section>

        <footer className="text-center mt-20">
          <Link
            href="/tools"
            className="mono text-sm uppercase tracking-wider px-6 py-3 border border-primary text-primary hover:bg-primary hover:text-dark transition-colors"
          >
            Run the tools →
          </Link>
        </footer>
      </article>
    </>
  );
}
