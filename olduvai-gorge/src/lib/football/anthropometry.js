/**
 * Anthropometric baselines for footballer biomechanics.
 *
 * Source: `public/data/continent_averages.json` — per-continent average
 * height, weight, segment masses and lengths, originally from upward/.
 *
 * For each detected player we know almost nothing from a single video
 * frame: only the pose landmarks and roughly the team. To compute
 * speed, stride length, ground-reaction force, vertical oscillation
 * etc., we need scalars (body mass, leg length) that don't come from
 * the camera. The framework's accounting fills these from a
 * continent-average profile that the user can switch.
 *
 * Default profile is South America (FIFA-era footballer demographic
 * skew is well-approximated by South America / Europe averages).
 */

let _cache = null;
let _loadPromise = null;

/** Async loader for the continent-average JSON. */
export async function loadAnthropometry() {
  if (_cache) return _cache;
  if (_loadPromise) return _loadPromise;
  _loadPromise = fetch("/data/continent_averages.json")
    .then((r) => r.json())
    .then((data) => {
      _cache = data;
      _loadPromise = null;
      return data;
    });
  return _loadPromise;
}

/** Synchronous accessor — returns the cached data or null. */
export function anthropometryCache() {
  return _cache;
}

/** Names of continents available as default profiles. */
export const CONTINENT_OPTIONS = [
  "South America",
  "Europe",
  "Africa",
  "North America",
  "Asia",
  "Oceania",
];

/** Fallback profile used if the JSON has not loaded yet. */
export const FALLBACK_PROFILE = {
  Age: 24.4,
  Height: 180.43,
  Weight: 71.0,
  bmi: 21.82,
  lean_body_mass: 57.87,
  skeletal_muscle_mass: 38.91,
  thigh_mass: 7.1,
  leg_mass: 3.3,
  foot_mass: 1.03,
  total_leg_mass: 11.43,
  leg_length: 87.51,            // cm
  thigh_length: 44.2,
  shank_length: 44.39,
  foot_length: 27.43,
};

/**
 * Return the anthropometric profile for a continent, falling back to
 * South America (or the embedded FALLBACK if nothing is loaded).
 */
export function profileFor(continent = "South America") {
  if (!_cache) return FALLBACK_PROFILE;
  return _cache[continent] ?? _cache["South America"] ?? FALLBACK_PROFILE;
}

/**
 * Convenience: derived quantities from a profile.
 *   massKg            — body mass in kg
 *   legLengthM        — total leg length in metres (cm → m)
 *   strideUpperM      — typical max stride at sprint, ≈ 2.5 × leg length
 *   weightN           — body weight in newtons (mg)
 */
export function derivedFromProfile(profile) {
  const massKg = profile?.Weight ?? 71;
  const legLengthM = (profile?.leg_length ?? 87) / 100;
  return {
    massKg,
    legLengthM,
    strideUpperM: 2.5 * legLengthM,
    weightN: massKg * 9.81,
  };
}
