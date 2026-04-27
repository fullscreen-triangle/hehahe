/**
 * Browser port of olduvai-gorge/publications/charge-quantification/
 * validation/analyze_charge.py — the deterministic subject → Q mapping.
 *
 * This is the PHYSIOLOGICAL computation. The GPU visualisation that
 * accompanies it (anatomical glow per compartment) is driven by these
 * numbers — but per the framework, the visualisation is itself a
 * computation, not a display.
 */

const J_PER_KCAL = 4184;
const SEC_PER_HR = 3600;

// Capacitance constants (F) — Attwell & Laughlin 2001 + Kandel 2013.
export const C_BRAIN = 1.0e-3;
export const C_MOTOR = 1.41e-4;
export const C_PERC = 5.0e-4;

// Attwell–Laughlin / Harris et al. 50/50 split of brain metabolism.
export const FRAC_BASELINE = 0.5;
export const FRAC_COGNITION = 0.5;

// Sleep-stage metabolic multipliers (Jung et al. 2011).
export const SLEEP_MULT = { deep: 0.85, light: 0.9, REM: 0.95, awake: 1.0 };

// Koch 2004 baseline + cardiac-coupling clipping band.
export const KAPPA_REF = 0.06;
export const FRAC_PERCEPTION_REF = 0.4;
export const FRAC_PERCEPTION_MIN = 0.2;
export const FRAC_PERCEPTION_MAX = 0.6;

export function mifflinStJeor({ mass_kg, height_cm, age_yr, sex = "m" }) {
  const s = sex === "f" ? -161 : 5;
  const kcalPerDay = 10 * mass_kg + 6.25 * height_cm - 5 * age_yr + s;
  return {
    kcalPerDay,
    watt: (kcalPerDay * J_PER_KCAL) / (24 * SEC_PER_HR),
    kcalPerHr: kcalPerDay / 24,
  };
}

export function brainBudget(bmrWatt) {
  const total = 0.2 * bmrWatt;
  return {
    total,
    baseline: FRAC_BASELINE * total,
    cognition: FRAC_COGNITION * total,
  };
}

export function cardiacCoupling({ hr_bpm, rmssd_ms }) {
  const fcard = hr_bpm / 60;
  const tau = rmssd_ms / 1000;
  const kappa = fcard * tau;
  const frac = clamp(
    FRAC_PERCEPTION_REF * (kappa / KAPPA_REF),
    FRAC_PERCEPTION_MIN,
    FRAC_PERCEPTION_MAX
  );
  return { fcard, tau, kappa, frac };
}

export function locomotionPower({ peak_force_N, step_length_m, cadence_spm }) {
  if (!peak_force_N || !step_length_m || !cadence_spm) return 0;
  const perStepJ = 0.5 * peak_force_N * step_length_m;
  const stepsPerSec = cadence_spm / 60;
  const raw = perStepJ * stepsPerSec;
  // Framework applies a ~10% capture efficiency, then caps at 300 W.
  return Math.min(raw * 0.1, 300);
}

export function energyToCharge(power_W, C_F, dt_s = 1) {
  return Math.sqrt(2 * C_F * power_W * dt_s);
}

/**
 * Single-call computation of the full charge phenotype.
 * Returns everything needed both for the display numbers and for
 * the shader uniforms of the anatomical glow.
 */
export function computeCharges(inputs) {
  const bmr = mifflinStJeor(inputs);
  const brain = brainBudget(bmr.watt);
  const cardiac = cardiacCoupling(inputs);
  const P_perc = cardiac.frac * brain.cognition;
  const P_th = brain.cognition; // full cognitive slice
  const P_dr = SLEEP_MULT.REM * brain.cognition;
  const P_loc = locomotionPower(inputs);

  const Q = {
    baseline: energyToCharge(brain.baseline, C_BRAIN) * 1000,
    motor: energyToCharge(P_loc, C_MOTOR) * 1000,
    perception: energyToCharge(P_perc, C_PERC) * 1000,
    thought: energyToCharge(P_th, C_BRAIN) * 1000,
    dream: energyToCharge(P_dr, C_BRAIN) * 1000,
  };

  return {
    bmr,
    brain,
    cardiac,
    power_W: {
      baseline: brain.baseline,
      motor: P_loc,
      perception: P_perc,
      thought: P_th,
      dream: P_dr,
    },
    Q_mC_per_s: Q,
    dream_thought_ratio: Q.dream / Q.thought,
  };
}

export function clamp(v, lo, hi) {
  return Math.max(lo, Math.min(hi, v));
}
