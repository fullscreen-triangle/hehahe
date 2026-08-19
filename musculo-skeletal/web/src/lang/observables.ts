/**
 * The observable registry.
 *
 * Every observable the language admits is declared here with the procedure
 * that computes it. An observable without a defined measurement procedure
 * is a promise, not a result, so the checker rejects any name absent from
 * this table -- which is what stops `conscious_overhead` looking as
 * legitimate as `loop_latency`.
 */

export interface ObsSpec {
  name: string;
  unit: string;
  arity: number;
  procedure: string;
  requiresEventType?: boolean;
  requiresAntagonist?: boolean;
  openOnly?: boolean;
  /** Which analysis discharges it: static needs no backend. */
  tier: "static" | "temporal" | "spectral" | "estimation" | "coupled";
}

const S = (s: ObsSpec): [string, ObsSpec] => [s.name, s];

export const OBSERVABLES = new Map<string, ObsSpec>([
  S({
    name: "closure_index", unit: "categorical", arity: 0, tier: "static",
    procedure:
      "Decide whether every declared outbound path has a closing return phase " +
      "realised by surviving elements. Returns 'closed' or 'open'.",
  }),
  S({
    name: "aperture_list", unit: "list", arity: 0, tier: "static",
    procedure:
      "Enumerate the circulations left without a return phase, each with the " +
      "outbound phase now unclosed and the cause.",
  }),
  S({
    name: "resting_cut_weight", unit: "conductance", arity: 0, tier: "static",
    procedure:
      "Total weight of the minimum cut separating the floor's reference " +
      "compartment from the medium.",
  }),
  S({
    name: "floor_value", unit: "conductance", arity: 0, tier: "static",
    procedure: "The circuit's irreducible residual beta, from its declared floor spec.",
  }),
  S({
    name: "loop_latency", unit: "s", arity: 0, tier: "static",
    procedure:
      "Sum of the declared delays of the elements realising the outbound and " +
      "return paths of the circulation.",
  }),
  S({
    name: "divergence_time", unit: "s", arity: 0, tier: "temporal", openOnly: true,
    procedure:
      "Time at which an open circuit's state leaves the bounded region. " +
      "Defined only for open circuits; undefined when the circuit is closed.",
  }),
  S({
    name: "tonic_rate", unit: "Hz", arity: 0, tier: "temporal",
    procedure:
      "Mean discharge rate of the circulation at rest, from the reciprocal of " +
      "the loop traversal time damped by loop gain.",
  }),
  S({
    name: "oscillation_frequency", unit: "Hz", arity: 0, tier: "spectral",
    procedure: "Dominant frequency of the bounded limit cycle by peak-picking the spectrum.",
  }),
  S({
    name: "oscillation_amplitude", unit: "a.u.", arity: 0, tier: "temporal",
    procedure: "Root-mean-square excursion of the limit cycle about its centre.",
  }),
  S({
    name: "cop_rms", unit: "mm", arity: 0, tier: "temporal",
    procedure: "Root-mean-square displacement of the centre of pressure over the window.",
  }),
  S({
    name: "force_amplitude", unit: "N", arity: 0, tier: "static",
    procedure:
      "Peak force from the outbound phase: product of outbound gains scaled by " +
      "the terminal compartment's capacitance via Q = sqrt(2 C P). Independent " +
      "of whether the return phase closes.",
  }),
  S({
    name: "force_output", unit: "N", arity: 0, tier: "static",
    procedure: "Mean force over the duty cycle, from outbound integrity alone.",
  }),
  S({
    name: "band_power", unit: "fraction", arity: 1, tier: "spectral",
    procedure:
      "Fraction of total spectral power in the named stratum's band. " +
      "Bands: reflex 1-3 Hz, spinal 0.3-1 Hz, supraspinal 0.05-0.3 Hz.",
  }),
  S({
    name: "coupling_index", unit: "dimensionless", arity: 0, tier: "spectral",
    procedure:
      "Zero-lag cross-correlation between the slow component and the envelope " +
      "of the fast component. Healthy range 0.3-0.6.",
  }),
  S({
    name: "kappa", unit: "fraction", arity: 1, tier: "estimation", requiresEventType: true,
    procedure:
      "Type-averaged catalytic power of the named event type. Requires a " +
      "declared type with at least two instances (Rule IV); an instance-specific " +
      "estimate is an algebraic identity and cannot fail.",
  }),
  S({
    name: "type_separation", unit: "fraction", arity: 0, tier: "estimation",
    procedure:
      "eta = Var_between / (Var_between + Var_within) over declared event types. " +
      "Near zero means the typing does not separate and any composed estimate is " +
      "uninterpretable.",
  }),
  S({
    name: "composition_residual", unit: "fraction", arity: 0, tier: "estimation",
    procedure:
      "Discrepancy between the type-averaged multiplicative prediction and the " +
      "measured net power. Non-degenerate by construction.",
  }),
  S({
    name: "cocontraction_ratio", unit: "fraction", arity: 1, tier: "coupled", requiresAntagonist: true,
    procedure:
      "Temporal overlap of activation in the agonist and antagonist circuits of a " +
      "declared pair, coupled through their shared compartments.",
  }),
  S({
    name: "joint_stiffness", unit: "N/m", arity: 1, tier: "coupled", requiresAntagonist: true,
    procedure:
      "Mechanical stiffness at the shared joint, emergent from the two coupled " +
      "limit cycles rather than commanded.",
  }),
]);

export const STRATUM_BANDS: Record<string, [number, number]> = {
  reflex: [1.0, 3.0],
  spinal: [0.3, 1.0],
  supraspinal: [0.05, 0.3],
};
