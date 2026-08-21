/**
 * Sampling a pose stream out of a GLB animation clip.
 *
 * An animation clip is a body-sway record: joint transforms sampled at a
 * fixed rate by whoever authored the motion. That makes it the same class of
 * signal a waist IMU or a force plate produces, and the postural
 * decomposition applies to it without reinterpretation.
 *
 * Clips are short. `Idle` is 1.967 s, `Walking` 0.867 s. Looping is the only
 * way to reach a record long enough for the slow bands -- and looping is not
 * free: it injects a periodicity at the clip rate that was never in the
 * subject. `sampleClip` therefore reports how many loops it used, and
 * `loopArtefactHz` names the frequency the looping put there, so a peak at
 * that frequency can be recognised as an artefact rather than a finding.
 */

import * as THREE from "three";
import type { PoseSignal } from "./posture";

/**
 * Resolve a joint by the name the MANIFEST uses.
 *
 * three.js sanitises node names on import: `PropertyBinding.sanitizeNodeName`
 * STRIPS the characters that are illegal in an animation property path rather
 * than substituting them, so the GLB's `mixamorig:Hips_01` becomes
 * `mixamorigHips_01` in the loaded scene while the manifest -- read straight
 * out of the container -- keeps the colon. A direct `getObjectByName` fails on
 * exactly the rigs that need it most, and fails silently enough to look like
 * an empty signal rather than a lookup bug.
 *
 * Matching therefore compares names with separators removed on BOTH sides. A
 * genuinely absent joint still returns undefined, so the caller can fail
 * loudly instead of sampling zeros.
 */
const normaliseJointName = (s: string) => s.replace(/[\s.:_-]/g, "").toLowerCase();

export function findJoint(root: THREE.Object3D, name: string): THREE.Object3D | undefined {
  const direct = root.getObjectByName(name);
  if (direct) return direct;
  const want = normaliseJointName(name);
  let found: THREE.Object3D | undefined;
  root.traverse((o) => {
    if (found) return;
    if (normaliseJointName(o.name) === want) found = o;
  });
  return found;
}

/** Closest names by normalised prefix overlap, for a useful error message. */
function nearest(target: string, pool: string[], k = 3): string[] {
  const want = normaliseJointName(target);
  return pool
    .map((p) => {
      const n = normaliseJointName(p);
      let i = 0;
      while (i < n.length && i < want.length && n[i] === want[i]) i++;
      return { p, score: i };
    })
    .sort((a, b) => b.score - a.score)
    .slice(0, k)
    .map((x) => x.p);
}

export interface ClipSampleOptions {
  /** joint whose motion is read */
  jointName: string;
  /** which axis of the joint's world position; "mag" for the magnitude */
  axis?: "x" | "y" | "z" | "mag";
  /** samples per second */
  rateHz?: number;
  /** total record length; the clip is looped to reach it */
  durationS?: number;
}

export interface ClipSample extends PoseSignal {
  clipName: string;
  jointName: string;
  axis: string;
  clipDurationS: number;
  /** how many times the clip was repeated to fill the record */
  loops: number;
  /** frequency the looping introduces; a peak here is an artefact */
  loopArtefactHz: number;
  /** true when the record is one pass or less: no looping artefact */
  singlePass: boolean;
}

/**
 * Read a joint's motion out of a clip as a uniformly sampled signal.
 *
 * The clip is evaluated through a real AnimationMixer against a real object
 * graph, so interpolation, quaternion handling, and parent transforms are
 * whatever three.js actually does at render time -- not a reimplementation
 * that could drift from what the viewer shows.
 */
export function sampleClip(
  root: THREE.Object3D,
  clip: THREE.AnimationClip,
  opts: ClipSampleOptions,
): ClipSample {
  const rate = opts.rateHz ?? 30;
  const axis = opts.axis ?? "mag";
  const duration = opts.durationS ?? clip.duration;
  const n = Math.max(2, Math.round(duration * rate));
  const dt = 1 / rate;

  // Work on a private clone. The loaded scene is cached and shared with the
  // 3-D views, and driving a mixer over it mutates transforms that another
  // component is mid-render on. Cloning also means `uncacheClip` below
  // cannot disturb an AnimationMixer someone else owns.
  const scene = root.clone(true);

  const target = findJoint(scene, opts.jointName);
  if (!target) {
    const available = [] as string[];
    scene.traverse((o) => { if (o.name) available.push(o.name); });
    throw new Error(
      `Joint "${opts.jointName}" is not in this rig. ` +
        `Sampling a joint that does not exist would silently return zeros. ` +
        `The rig has ${available.length} named nodes; nearest by name: ` +
        `${nearest(opts.jointName, available).join(", ")}.`,
    );
  }

  const mixer = new THREE.AnimationMixer(scene);
  const action = mixer.clipAction(clip);
  action.play();

  const x = new Float64Array(n);
  const world = new THREE.Vector3();

  // Step the mixer forward in fixed increments rather than seeking, so the
  // sampled trajectory is the one the mixer actually produces under
  // playback, including its loop wrap behaviour.
  mixer.setTime(0);
  for (let i = 0; i < n; i++) {
    const t = i * dt;
    mixer.setTime(t % clip.duration);
    scene.updateMatrixWorld(true);
    target.getWorldPosition(world);
    x[i] =
      axis === "x" ? world.x
      : axis === "y" ? world.y
      : axis === "z" ? world.z
      : Math.hypot(world.x, world.y, world.z);
  }

  action.stop();
  mixer.uncacheClip(clip);

  const loops = duration / clip.duration;

  return {
    x,
    dt,
    source: `${clip.name}/${opts.jointName}/${axis}`,
    clipName: clip.name,
    jointName: opts.jointName,
    axis,
    clipDurationS: clip.duration,
    loops,
    loopArtefactHz: clip.duration > 0 ? 1 / clip.duration : 0,
    singlePass: loops <= 1.0000001,
  };
}

/**
 * Detrend a looped record by removing its per-loop mean.
 *
 * Useful when a clip has net translation (Walking moves the hips forward
 * every cycle): without this the record is dominated by a ramp that is
 * locomotion, not sway, and the rambling estimate becomes a measure of how
 * far the character walked.
 */
export function removeLoopDrift(s: ClipSample): ClipSample {
  const perLoop = Math.max(1, Math.round(s.clipDurationS / s.dt));
  const out = new Float64Array(s.x.length);
  for (let start = 0; start < s.x.length; start += perLoop) {
    const end = Math.min(s.x.length, start + perLoop);
    let mu = 0;
    for (let i = start; i < end; i++) mu += s.x[i];
    mu /= Math.max(1, end - start);
    for (let i = start; i < end; i++) out[i] = s.x[i] - mu;
  }
  return { ...s, x: out, source: s.source + "/detrended" };
}
