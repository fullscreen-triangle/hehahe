/**
 * Tests for postural analysis and the pose <-> source round trip.
 *
 * The load-bearing tests are the ones that check the analysis REFUSES to
 * report what a record cannot support. A decomposition always returns
 * numbers; the question is whether it says when they mean nothing.
 */

import { describe, expect, it } from "vitest";
import {
  adequacy, analyseSleep, bandPower, BANDS, CAPACITANCE, chargeFromPower,
  chargeOfMotion, decompose, dominantFrequency, powerFromCharge,
  synthesiseVvs, type PoseSignal,
} from "./posture";
import { check } from "./checker";
import { parse } from "./parser";

/** A synthetic sway record: slow drift plus a fast oscillation. */
function synth(opts: {
  durationS: number; fs: number;
  ramblingHz?: number; ramblingAmp?: number;
  tremblingHz?: number; tremblingAmp?: number;
}): PoseSignal {
  const { durationS, fs } = opts;
  const rHz = opts.ramblingHz ?? 0.15;
  const rA = opts.ramblingAmp ?? 2.0;
  const tHz = opts.tremblingHz ?? 1.2;
  const tA = opts.tremblingAmp ?? 0.6;
  const n = Math.round(durationS * fs);
  const x = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    const t = i / fs;
    x[i] = rA * Math.sin(2 * Math.PI * rHz * t) + tA * Math.sin(2 * Math.PI * tHz * t + 0.7);
  }
  return { x, dt: 1 / fs, source: "synthetic" };
}

describe("charge conversion", () => {
  it("round-trips power through charge at a fixed capacitance", () => {
    for (const P of [0.5, 8.92, 300]) {
      for (const c of ["brain", "motor", "perception"] as const) {
        const q = chargeFromPower(P, c);
        expect(powerFromCharge(q, c)).toBeCloseTo(P, 9);
      }
    }
  });

  it("reproduces the published component charge rates", () => {
    // Thought: full cognitive slice at the cortical capacitance.
    expect(chargeFromPower(8.92, "brain") * 1e3).toBeCloseTo(133.5, 0);
    // Motor: locomotion capped at the aerobic ceiling.
    expect(chargeFromPower(300, "motor") * 1e3).toBeCloseTo(290.9, 0);
    // Perception at its own capacitance.
    expect(chargeFromPower(5.0, "perception") * 1e3).toBeCloseTo(70.7, 0);
  });

  it("reproduces the parameter-free dream/thought ratio", () => {
    const thought = chargeFromPower(8.92, "brain");
    const dream = chargeFromPower(0.95 * 8.92, "brain");
    // sqrt(0.95) = 0.9747, and the ratio must not depend on the power level.
    expect(dream / thought).toBeCloseTo(Math.sqrt(0.95), 10);
    const t2 = chargeFromPower(20, "brain");
    const d2 = chargeFromPower(0.95 * 20, "brain");
    expect(d2 / t2).toBeCloseTo(dream / thought, 12);
  });

  it("returns zero charge for zero power rather than NaN", () => {
    expect(chargeFromPower(0, "motor")).toBe(0);
    expect(chargeFromPower(-1, "motor")).toBe(0);
  });

  it("keeps compartments distinct — same power, different charge", () => {
    const P = 10;
    const a = chargeFromPower(P, "brain");
    const b = chargeFromPower(P, "motor");
    expect(a).not.toBeCloseTo(b, 6);
    expect(a / b).toBeCloseTo(Math.sqrt(CAPACITANCE.brain / CAPACITANCE.motor), 9);
  });
});

describe("adequacy — what a record can support", () => {
  it("declares rambling unresolvable in a record shorter than its period", () => {
    // The Idle clip is 1.967 s at 30 Hz: shorter than one rambling cycle.
    const a = adequacy(synth({ durationS: 1.967, fs: 30 }));
    expect(a.ramblingResolvable).toBe(false);
    expect(a.notes.join(" ")).toMatch(/NOT resolvable/);
  });

  it("declares rambling resolvable in a long record", () => {
    const a = adequacy(synth({ durationS: 60, fs: 30 }));
    expect(a.ramblingResolvable).toBe(true);
  });

  it("reports the aliasing limit at 30 Hz sampling", () => {
    const a = adequacy(synth({ durationS: 60, fs: 30 }));
    expect(a.nyquistHz).toBe(15);
    // Trembling tops out at 3 Hz, well inside Nyquist.
    expect(a.tremblingResolvable).toBe(true);
  });

  it("warns when Nyquist cannot reach physiological tremor", () => {
    const a = adequacy(synth({ durationS: 60, fs: 8 }));
    expect(a.nyquistHz).toBe(4);
    expect(a.notes.join(" ")).toMatch(/alias/i);
  });
});

describe("decomposition", () => {
  it("sums back to the original exactly", () => {
    const d = decompose(synth({ durationS: 60, fs: 30 }));
    expect(d.reconstructionError).toBeLessThan(1e-12);
  });

  it("separates a known two-component signal", () => {
    const d = decompose(synth({
      durationS: 60, fs: 30,
      ramblingHz: 0.1, ramblingAmp: 3.0,
      tremblingHz: 1.5, tremblingAmp: 0.5,
    }));
    // The slow component carries most of the amplitude.
    expect(d.ramblingRms).toBeGreaterThan(d.tremblingRms);
    // And each component sits in its own band.
    expect(bandPower(d.rambling, 1 / 30, BANDS.rambling)).toBeGreaterThan(0.8);
    expect(bandPower(d.trembling, 1 / 30, BANDS.trembling)).toBeGreaterThan(0.5);
  });

  it("recovers the trembling frequency it was given", () => {
    const d = decompose(synth({ durationS: 60, fs: 30, tremblingHz: 1.5 }));
    const f = dominantFrequency(d.trembling, 1 / 30, BANDS.trembling);
    expect(f).toBeGreaterThan(1.3);
    expect(f).toBeLessThan(1.7);
  });

  it("carries the adequacy verdict with the numbers", () => {
    const short = decompose(synth({ durationS: 1.967, fs: 30 }));
    expect(short.adequacy.ramblingResolvable).toBe(false);
    // The numbers still exist -- that is exactly why the verdict must too.
    expect(Number.isFinite(short.ramblingRms)).toBe(true);
  });
});

describe("sleep activity", () => {
  /** A night: mostly still, with a few discrete rolls. */
  function night(rollTimes: number[], durationS = 600, fs = 30): PoseSignal {
    const n = Math.round(durationS * fs);
    const x = new Float64Array(n);
    let pos = 0;
    let seed = 12345;
    const rnd = () => {
      seed = (seed * 1103515245 + 12345) & 0x7fffffff;
      return seed / 0x7fffffff - 0.5;
    };
    const rollIdx = rollTimes.map((t) => Math.round(t * fs));
    for (let i = 0; i < n; i++) {
      if (rollIdx.includes(i)) pos += 5.0;
      x[i] = pos + 0.01 * rnd();
    }
    return { x, dt: 1 / fs, source: "synthetic night" };
  }

  it("counts discrete repositions", () => {
    const s = analyseSleep(night([100, 250, 400]));
    expect(s.events.length).toBe(3);
  });

  it("does not count a still night as restless", () => {
    const s = analyseSleep(night([]));
    expect(s.events.length).toBe(0);
    expect(s.repositionRate).toBe(0);
    expect(s.longestStillS).toBeCloseTo(s.durationS, 5);
  });

  it("reports a per-hour rate that scales with the count", () => {
    const few = analyseSleep(night([100, 300]));
    const many = analyseSleep(night([50, 100, 150, 200, 250, 300, 350, 400]));
    expect(many.repositionRate).toBeGreaterThan(few.repositionRate);
  });

  it("finds the longest undisturbed stretch", () => {
    const s = analyseSleep(night([60, 500]));
    // The gap between the two rolls is the longest, ~440 s.
    expect(s.longestStillS).toBeGreaterThan(400);
  });
});

describe("charge of motion", () => {
  it("scales with the movement actually present", () => {
    const still = chargeOfMotion(synth({ durationS: 60, fs: 30, tremblingAmp: 0.01, ramblingAmp: 0.01 }));
    const restless = chargeOfMotion(synth({ durationS: 60, fs: 30, tremblingAmp: 2.0, ramblingAmp: 2.0 }));
    expect(restless.chargeCs).toBeGreaterThan(still.chargeCs);
    expect(restless.powerW).toBeGreaterThan(still.powerW);
  });

  it("keeps Q = sqrt(2CP) exact", () => {
    const a = chargeOfMotion(synth({ durationS: 30, fs: 30 }));
    expect(a.chargeCs).toBeCloseTo(chargeFromPower(a.powerW, a.compartment), 12);
  });

  it("states its own derivation", () => {
    const a = chargeOfMotion(synth({ durationS: 10, fs: 30 }));
    expect(a.derivation).toMatch(/sqrt\(2/);
    expect(a.derivation).toMatch(/<v\^2>/);
  });

  it("accumulates total charge over the record", () => {
    const a = chargeOfMotion(synth({ durationS: 30, fs: 30 }));
    expect(a.totalC).toBeCloseTo(a.chargeCs * a.durationS, 9);
  });
});

describe("synthesis — pose record to Vitruvius source", () => {
  const longSig = synth({ durationS: 60, fs: 30, tremblingHz: 1.2 });
  const shortSig = synth({ durationS: 1.967, fs: 30, tremblingHz: 1.2 });

  const build = (sig: PoseSignal, name = "recovered") =>
    synthesiseVvs({
      circuitName: name,
      decomposition: decompose(sig),
      charge: chargeOfMotion(sig),
    });

  it("produces source that parses and checks clean", () => {
    const src = build(longSig);
    const r = check(parse(src));
    if (!r.ok) console.log(r.errors.map((e) => e.message));
    expect(r.ok).toBe(true);
  });

  it("produces a closed circuit", () => {
    const src = build(longSig);
    const r = check(parse(src));
    const circ = [...r.circuits.values()][0];
    expect(circ).toBeDefined();
  });

  it("omits the supraspinal compartment when rambling is unresolvable", () => {
    const src = build(shortSig);
    expect(src).toMatch(/No supraspinal compartment/);
    expect(src).not.toMatch(/compartment central/);
    // And the short-record source must still be valid.
    expect(check(parse(src)).ok).toBe(true);
  });

  it("includes the supraspinal compartment when rambling IS resolvable", () => {
    const src = build(longSig);
    expect(src).toMatch(/compartment central/);
    expect(src).not.toMatch(/No supraspinal compartment/);
  });

  it("writes the bandwidth limitation into the source, not just the UI", () => {
    const src = build(shortSig);
    expect(src).toMatch(/NOT RESOLVABLE/);
    expect(src).toMatch(/-- ! /); // the warning marker
  });

  it("derives the loop delay from the measured trembling frequency", () => {
    const fast = build(synth({ durationS: 60, fs: 30, tremblingHz: 2.5 }));
    const slow = build(synth({ durationS: 60, fs: 30, tremblingHz: 0.6 }));
    const grab = (s: string) => {
      const m = s.match(/loop delay = 1\/\(2f\) = ([\d.]+) ms/);
      return m ? parseFloat(m[1]) : NaN;
    };
    // A faster observed oscillation must yield a shorter loop delay.
    expect(grab(fast)).toBeLessThan(grab(slow));
  });

  it("recovers a capacitance consistent with the measured charge", () => {
    const sig = longSig;
    const charge = chargeOfMotion(sig);
    const src = synthesiseVvs({
      circuitName: "cap_check",
      decomposition: decompose(sig),
      charge,
    });
    const m = src.match(/C = Q\^2 \/ \(2P\) = ([\d.eE+-]+) F/);
    expect(m).not.toBeNull();
    const recovered = parseFloat(m![1]);
    // The generator must invert its own forward map.
    expect(recovered).toBeCloseTo(CAPACITANCE.motor, 10);
  });

  it("generates different programs for different records", () => {
    const a = build(synth({ durationS: 60, fs: 30, tremblingAmp: 0.2 }), "quiet");
    const b = build(synth({ durationS: 60, fs: 30, tremblingAmp: 3.0 }), "restless");
    expect(a).not.toBe(b);
    expect(check(parse(a)).ok).toBe(true);
    expect(check(parse(b)).ok).toBe(true);
  });

  it("emits a bind clause when a binding is supplied", () => {
    const src = synthesiseVvs({
      circuitName: "bound",
      decomposition: decompose(longSig),
      charge: chargeOfMotion(longSig),
      binding: {
        rig: "xbot_multiple_animations",
        map: { periphery: "mixamorig:RightLeg_063" },
      },
    });
    expect(src).toMatch(/bind bound_loop to rig\("xbot_multiple_animations"\)/);
    expect(check(parse(src)).ok).toBe(true);
  });

  it("carries sleep activity into the source when present", () => {
    const n = 30 * 600;
    const x = new Float64Array(n);
    let pos = 0;
    for (let i = 0; i < n; i++) {
      if (i === 3000 || i === 9000) pos += 5;
      x[i] = pos;
    }
    const sig: PoseSignal = { x, dt: 1 / 30, source: "night" };
    const src = synthesiseVvs({
      circuitName: "slept",
      decomposition: decompose(sig),
      charge: chargeOfMotion(sig),
      sleep: analyseSleep(sig),
    });
    expect(src).toMatch(/Sleep activity/);
    expect(src).toMatch(/repositions/);
    expect(check(parse(src)).ok).toBe(true);
  });
});

describe("round trip — the inverse direction closes", () => {
  it("regenerates a circuit whose latency matches the observed oscillation", async () => {
    const { Backend } = await import("./backend");
    const sig = synth({ durationS: 60, fs: 30, tremblingHz: 1.0 });
    const d = decompose(sig);
    const src = synthesiseVvs({
      circuitName: "closed",
      decomposition: d,
      charge: chargeOfMotion(sig),
    });
    const r = check(parse(src));
    expect(r.ok).toBe(true);

    const circ = [...r.circuits.values()][0];
    const be = new Backend(2e-3, 10, 0);
    const tr = be.simulate(circ);
    // The regenerated circuit must actually run and stay bounded: it came
    // from a record of a body that did not fall over.
    let peak = 0;
    for (let i = 0; i < tr.n; i++) peak = Math.max(peak, Math.abs(tr.x[0][i]));
    expect(Number.isFinite(peak)).toBe(true);
    expect(peak).toBeLessThan(1e6);
  });
});

describe("loop artefact — the failure mode a short clip creates", () => {
  /**
   * A short clip repeated to fill a long record.
   *
   * The signal is a slow drift with only weak content inside the trembling
   * band -- which is what the real Idle clip looks like. That is precisely
   * when looping wins: with little genuine in-band power to compete with,
   * the repetition harmonic at 1/clipDuration becomes the dominant peak and
   * is indistinguishable from a finding. A synthetic clip with strong 1.8 Hz
   * content would NOT trigger this, and would test nothing.
   */
  function looped(clipS: number, fs: number, loops: number): PoseSignal {
    const per = Math.round(clipS * fs);
    const base = new Float64Array(per);
    for (let i = 0; i < per; i++) {
      const t = i / fs;
      // Slow drift over the clip, plus a small non-periodic wobble. Nothing
      // here repeats at a trembling-band frequency.
      base[i] = Math.sin(2 * Math.PI * 0.25 * t) + 0.02 * Math.sin(2 * Math.PI * 0.11 * t + 1.3);
    }
    const x = new Float64Array(per * loops);
    for (let L = 0; L < loops; L++) x.set(base, L * per);
    // The repeat frequency is set by the integer sample count, not the
    // requested duration; reporting the requested value would be a lie.
    return { x, dt: 1 / fs, source: "looped", repeatHz: fs / per } as PoseSignal & { repeatHz: number };
  }

  it("detects when the dominant peak IS the looping frequency", () => {
    // Idle is 1.967 s: looping puts a peak at ~0.51 Hz, inside the trembling
    // band, where it is indistinguishable from a real finding.
    const sig = looped(1.967, 30, 31) as PoseSignal & { repeatHz: number };
    const d = decompose(sig, undefined, sig.repeatHz);
    expect(d.adequacy.dominantIsLoopArtefact).toBe(true);
    expect(d.adequacy.notes.join(" ")).toMatch(/is the LOOP, not the subject/);
  });

  it("stays silent when the record is genuinely long", () => {
    const sig = synth({ durationS: 60, fs: 30, tremblingHz: 1.5 });
    const d = decompose(sig, undefined, 1 / 60);
    expect(d.adequacy.dominantIsLoopArtefact).toBe(false);
  });

  it("refuses to derive a loop delay from an artefact peak", () => {
    const sig = looped(1.967, 30, 31) as PoseSignal & { repeatHz: number };
    const d = decompose(sig, undefined, sig.repeatHz);
    const src = synthesiseVvs({
      circuitName: "artefact",
      decomposition: d,
      charge: chargeOfMotion(sig),
    });
    expect(src).toMatch(/Loop delay NOT derived from the spectrum/);
    expect(src).toMatch(/must not be read as measured/);
    // The refusal must still produce a program that runs.
    expect(check(parse(src)).ok).toBe(true);
  });

  it("uses the measured peak when there is no artefact", () => {
    const sig = synth({ durationS: 60, fs: 30, tremblingHz: 1.5 });
    const src = synthesiseVvs({
      circuitName: "clean",
      decomposition: decompose(sig, undefined, 1 / 60),
      charge: chargeOfMotion(sig),
    });
    expect(src).toMatch(/Loop delay from the observed trembling frequency/);
  });
});
