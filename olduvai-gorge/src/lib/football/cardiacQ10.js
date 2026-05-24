/**
 * Cardiac Q10 decomposition — port of the PPG paper's HR-component
 * separation into JS for the football tool's body-panel cardiac
 * compartment driver.
 *
 * Source: publications/sources/layered-optical-ppg.tex,
 *   §3.2 (vasodilation→temperature) and §4.2 (Q10 metabolic
 *   decomposition).
 *
 *   HR_obs = HR_int + ΔHR_met + ΔHR_O2 + ΔHR_auto
 *
 * with thermal metabolic drive
 *   ΔHR_met = α_T · (T_skin − T_rest) · HR_int,     α_T ≈ 0.08 K⁻¹
 * hypoxic chemoreflex
 *   ΔHR_O2 = β_O2 · (1 − S_O2) · HR_int,            β_O2 ≈ 0.15
 * and autonomic residual
 *   ΔHR_auto = HR_obs − HR_int − ΔHR_met − ΔHR_O2
 *
 * The football framework's cardiac compartment binds to ΔHR_auto, not
 * raw HR — see memory note `football_tool_design.md`. The autonomic
 * residual is the only HR component that tracks tactical neural state.
 */

export const HR_REST_DEFAULT = 60.0;
export const T_REST_C = 33.0;
export const ALPHA_T_PER_K = 0.08;
export const BETA_O2 = 0.15;
export const SO2_REF = 0.97;
export const Q10 = 2.3;

/** Map vasodilation factor η ∈ [0.6, 1.6] to skin temperature in °C. */
export function vasodilationToSkinTemp(eta) {
  const T = 33.0 + 4.0 * (eta - 1.0);
  return Math.max(27.0, Math.min(37.0, T));
}

/** Full PCHR decomposition. */
export function decomposeHR({ HR_obs, T_skin_C = T_REST_C, S_O2 = SO2_REF, HR_int = HR_REST_DEFAULT }) {
  const dHR_met = ALPHA_T_PER_K * (T_skin_C - T_REST_C) * HR_int;
  const dHR_O2  = BETA_O2 * Math.max(0, SO2_REF - S_O2) * HR_int;
  const dHR_auto = HR_obs - HR_int - dHR_met - dHR_O2;
  return {
    HR_obs,
    HR_int,
    dHR_met,
    dHR_O2,
    dHR_auto,
    T_skin_C,
    S_O2,
  };
}

/**
 * Match-environment thermal correction for Q_motor.
 *
 * A player running in ambient T_env contributes an inflated baseline
 * metabolism due to the Q10 effect on cellular respiration. The
 * "tactical" Q_motor signal — the part that reflects neural drive
 * rather than thermal acceleration of metabolism — is recovered by
 * dividing observed Q_motor by the Q10 factor.
 */
export function q10ThermalCorrection(Q_motor_observed, T_env_C, T_ref_C = T_REST_C) {
  const factor = Math.pow(Q10, (T_env_C - T_ref_C) / 10.0);
  return Q_motor_observed / factor;
}

/**
 * Normalised autonomic activation in [0, 1] suitable for the body
 * panel's cardiac compartment slider. Clamps to the typical match
 * range (−30 .. +120 bpm of autonomic residual).
 */
export function autonomicActivation(dHR_auto) {
  const minBpm = -30;
  const maxBpm = 120;
  return Math.max(0, Math.min(1, (dHR_auto - minBpm) / (maxBpm - minBpm)));
}
