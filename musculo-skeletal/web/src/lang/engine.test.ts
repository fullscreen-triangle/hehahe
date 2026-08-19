/**
 * The TypeScript engine must agree with the Python reference implementation.
 *
 * These are not UI tests. They assert that the specification's properties
 * hold in this port, and that the headline results reproduce the numbers
 * recorded in the manuscript.
 */

import { describe, expect, it } from "vitest";
import PROGRAMS from "../data/programs.json";
import { Backend } from "./backend";
import {
  closureIndex, reroute, withNoise, withScaling, withoutElement, withoutReturn,
} from "./circuit";
import { check } from "./checker";
import { parse } from "./parser";
import { Runtime, allArms, compile } from "./runtime";

const PROG = PROGRAMS as Record<string, string>;

const run = (name: string, seed = 0, duration = 20) => {
  const c = compile(PROG[name]);
  expect(c.parseError, `${name} parse`).toBeUndefined();
  expect(c.checked!.errors, `${name} errors`).toHaveLength(0);
  return new Runtime(c.program!, c.checked!, new Backend(2e-3, duration, seed)).run();
};

const MINIMAL = `
module m;
compartment a { capacitance: 1.0e-8 F; stratum: reflex; }
compartment b { capacitance: 2.0e-8 F; stratum: reflex; }
compartment c { capacitance: 3.0e-8 F; stratum: reflex; }
circuit loop {
  floor    : derived(resting_cut(a));
  outbound : a -> b;
  return   : b -> c -> a;
  element f conducts a -> b delay 5.0 ms;
  element g conducts b -> c delay 5.0 ms;
  element h conducts c -> a delay 5.0 ms gain 1.0;
}
experiment e { intact : loop; observe : closure_index, loop_latency; }
`;

const build = (src = MINIMAL) => {
  const prog = parse(src);
  return { prog, res: check(prog) };
};

describe("grammar", () => {
  it("parses and checks a minimal program", () => {
    const { res } = build();
    expect(res.ok).toBe(true);
    expect(res.circuits.has("loop")).toBe(true);
  });

  it("rejects a circuit declaration missing its return phase", () => {
    const src = MINIMAL.replace("  return   : b -> c -> a;\n", "");
    expect(() => parse(src)).toThrow();
  });
});

describe("closure", () => {
  it("a declared circuit is closed", () => {
    const { res } = build();
    expect(closureIndex(res.circuits.get("loop")!)).toBe("closed");
  });

  it("attenuation preserves closure at every positive factor", () => {
    const { res } = build();
    const base = res.circuits.get("loop")!;
    for (const f of [0.9, 0.5, 0.1, 1e-6, 1e-12]) {
      expect(closureIndex(withScaling(base, "h", f)), `factor ${f}`).toBe("closed");
    }
  });

  it("severance opens the circulation", () => {
    const { res } = build();
    expect(closureIndex(withoutElement(res.circuits.get("loop")!, "h"))).toBe("open");
  });

  it("scaling by zero is rejected: severance is a different operator", () => {
    const { res } = build();
    expect(() => withScaling(res.circuits.get("loop")!, "h", 0)).toThrow();
  });
});

describe("lesion algebra", () => {
  it("is order independent over every permutation", () => {
    const { res } = build();
    const base = res.circuits.get("loop")!;
    const ops = [
      (c: any) => withoutElement(c, "g"),
      (c: any) => withScaling(c, "h", 0.4),
      (c: any) => withNoise(c, "reflex", "spinal", 0.2),
    ];
    const perms = [
      [0, 1, 2], [0, 2, 1], [1, 0, 2], [1, 2, 0], [2, 0, 1], [2, 1, 0],
    ];
    const seen = new Set<string>();
    for (const p of perms) {
      let c: any = base;
      for (const i of p) c = ops[i](c);
      seen.add(JSON.stringify({
        el: [...c.elements].map(([k, e]: any) => [k, e.gain]).sort(),
        cl: closureIndex(c),
        nz: c.noiseEdges.length,
      }));
    }
    expect(seen.size).toBe(1);
  });

  it("removal is idempotent and total", () => {
    const { res } = build();
    const base = res.circuits.get("loop")!;
    const once = withoutElement(base, "g");
    expect([...withoutElement(once, "g").elements].length).toBe([...once.elements].length);
    expect([...withoutElement(base, "absent").elements].length).toBe([...base.elements].length);
  });
});

describe("reroute (E3)", () => {
  it("is the only operator that restores closure", () => {
    const { res } = build();
    const opened = withoutReturn(res.circuits.get("loop")!, "b");
    expect(closureIndex(opened)).toBe("open");
    expect(closureIndex(reroute(opened, "b", ["b", "c", "a"]))).toBe("closed");
  });

  it("a reroute that misses the outbound origin stays open", () => {
    const { res } = build();
    const opened = withoutReturn(res.circuits.get("loop")!, "b");
    expect(closureIndex(reroute(opened, "b", ["b", "c"]))).toBe("open");
  });
});

describe("typing rules", () => {
  it("Rule II rejects non-adjacent strata", () => {
    const { res } = build(`
      module m;
      compartment lo { capacitance: 1.0e-8 F; stratum: reflex; }
      compartment hi { capacitance: 1.0e-3 F; stratum: supraspinal; }
      circuit bad {
        floor : derived(resting_cut(lo));
        outbound : lo -> hi;
        return : hi -> lo;
        element up conducts lo -> hi delay 5.0 ms;
        element dn conducts hi -> lo delay 5.0 ms;
      }
      experiment e { intact : bad; observe : closure_index; }
    `);
    expect(res.ok).toBe(false);
    expect(res.errors.some((d) => d.rule === "T-Stratum")).toBe(true);
  });

  it("Rule III warns on the unfalsifiable floor estimator", () => {
    const { res } = build(MINIMAL.replace("derived(resting_cut(a))", "derived(sample_minimum)"));
    expect(res.warnings.some((d) => d.message.includes("sample_minimum"))).toBe(true);
  });

  it("Rule IV rejects an untyped kappa", () => {
    const { res } = build(MINIMAL.replace("closure_index, loop_latency", "kappa"));
    expect(res.ok).toBe(false);
  });

  it("rejects an observable with no measurement procedure", () => {
    const { res } = build(MINIMAL.replace("closure_index, loop_latency", "conscious_overhead"));
    expect(res.ok).toBe(false);
    expect(res.errors.some((d) => d.rule === "unknown-observable")).toBe(true);
  });

  it("an open circuit warns but does not reject", () => {
    const { res } = build(MINIMAL.replace(
      "experiment e { intact : loop;",
      "experiment e { intact : loop; lesion cut : loop without element(h);",
    ));
    expect(res.ok).toBe(true);
    expect(res.warnings.some((d) => d.rule === "aperture")).toBe(true);
  });
});

describe("backend obligations", () => {
  it("(B1) an open circuit yields a divergence time, not a throw", () => {
    const src = MINIMAL
      .replace("closure_index, loop_latency", "closure_index, divergence_time")
      .replace("experiment e { intact : loop;",
               "experiment e { intact : loop; lesion cut : loop without element(h);");
    const c = compile(src);
    const r = new Runtime(c.program!, c.checked!, new Backend(2e-3, 12, 0)).run();
    const cut = allArms(r.experiments[0]).find((a) => a.name === "cut")!;
    expect(cut.closure).toBe("open");
    expect(Number.isFinite(cut.store.get("divergence_time")!.value as number)).toBe(true);
  });

  it("(B4) is deterministic modulo seed", () => {
    const a = run("01_stroke_umn_lmn", 7, 8);
    const b = run("01_stroke_umn_lmn", 7, 8);
    const va = allArms(a.experiments[0])[0].store.get("loop_latency")!.value;
    const vb = allArms(b.experiments[0])[0].store.get("loop_latency")!.value;
    expect(va).toBe(vb);
  });
});

describe("shipped programs match the reference implementation", () => {
  const expected: Record<string, { arms: number; open: number; warnings: number }> = {
    "01_stroke_umn_lmn": { arms: 7, open: 3, warnings: 3 },
    "02_spinal_cord_injury": { arms: 8, open: 4, warnings: 5 },
    "03_nerve_block_phases": { arms: 6, open: 3, warnings: 4 },
    "04_tmr_reroute": { arms: 4, open: 1, warnings: 1 },
    "05_tremor_classification": { arms: 4, open: 0, warnings: 0 },
    "06_cocontraction": { arms: 2, open: 0, warnings: 0 },
    "08_myasthenia": { arms: 8, open: 2, warnings: 2 },
    "09_rehabilitation": { arms: 4, open: 3, warnings: 3 },
    "10_gait_asymmetry": { arms: 4, open: 0, warnings: 0 },
  };

  for (const [name, e] of Object.entries(expected)) {
    it(`${name} reproduces arm and closure counts`, () => {
      const r = run(name, 0, 8);
      const arms = r.experiments.flatMap(allArms);
      expect(arms.length, "arms").toBe(e.arms);
      expect(arms.filter((a) => a.closure === "open").length, "open").toBe(e.open);
      expect(r.checked.warnings.length, "warnings").toBe(e.warnings);
    });
  }
});

describe("headline findings", () => {
  it("UMN lesion spares the segmental loop; LMN lesion does not", () => {
    const r = run("01_stroke_umn_lmn");
    const byExp = (n: string) => r.experiments.find((x) => x.name === n)!;

    const umn = allArms(byExp("cortical_lesion_supraspinal")).find((a) => a.name === "umn")!;
    expect(umn.closure).toBe("open");

    const seg = allArms(byExp("cortical_lesion_segmental"))[0];
    expect(seg.closure).toBe("closed");
    expect(seg.store.get("tonic_rate")!.value as number).toBeGreaterThan(0);

    const lmn = allArms(byExp("anterior_horn_segmental")).find((a) => a.name === "lmn")!;
    expect(lmn.closure).toBe("open");
    expect(Number.isFinite(lmn.store.get("tonic_rate")!.value as number)).toBe(false);
  });

  it("proprioceptive block preserves force exactly while opening the loop", () => {
    const r = run("03_nerve_block_phases");
    const phases = r.experiments[0].phases;
    const at = (n: string) => phases.find((p) => p.name === n)!.arms[0];

    const base = at("baseline").store.get("force_output")!.value as number;
    const prop = at("proprioceptive_loss");
    const motor = at("motor_block");

    expect(prop.closure).toBe("open");
    expect(prop.store.get("force_output")!.value).toBe(base);
    expect(motor.store.get("force_output")!.value as number).toBeLessThan(base * 0.01);
  });

  it("reroute restores closure through a longer path", () => {
    const r = run("04_tmr_reroute");
    const arms = Object.fromEntries(allArms(r.experiments[0]).map((a) => [a.name, a]));
    expect(arms.amputated.closure).toBe("open");
    expect(arms.tmr.closure).toBe("closed");
    expect(arms.mirror.closure).toBe("closed");
    const lat = (n: string) => arms[n].store.get("loop_latency")!.value as number;
    expect(lat("tmr")).toBeGreaterThan(lat("intact"));
  });

  it("prosthetic force scales as the square root of capacitance", () => {
    const r = run("10_gait_asymmetry");
    const f = (i: number) => allArms(r.experiments[i])[0].store.get("force_output")!.value as number;
    expect(f(1) / f(0)).toBeCloseTo(Math.sqrt(0.9 / 1.8), 6);
  });

  it("SCI spares circulations that do not cross the level", () => {
    const r = run("02_spinal_cord_injury");
    const byExp = (n: string) => r.experiments.find((x) => x.name === n)!;
    const complete = allArms(byExp("t6_complete_lower_limb")).find((a) => a.name === "complete")!;
    expect(complete.closure).toBe("open");
    expect(allArms(byExp("t6_below_lesion_reflex"))[0].closure).toBe("closed");
    expect(allArms(byExp("t6_above_lesion_function"))[0].closure).toBe("closed");
  });
});
