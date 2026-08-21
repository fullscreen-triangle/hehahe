/**
 * Establish the body segment parameters for a subject.
 *
 * This is the setup step everything downstream reads: instead of carrying
 * hard-coded constants (an "effective moving mass" of 8 kg, a motor
 * capacitance chosen once), a subject's mass and stature are expanded through
 * a published anthropometric model into per-segment masses, lengths, centres
 * of mass, and moments of inertia.
 *
 *   node scripts/set-body-parameters.mjs --mass 83 --stature 1.85 --sex male
 *   node scripts/set-body-parameters.mjs --model dempster --write
 *
 * Options:
 *   --mass KG        body mass (default 83)
 *   --stature M      stature in metres (default 1.85)
 *   --sex male|female
 *   --model deLeva|dempster
 *   --length seg=M   measured segment length; repeatable, overrides scaling
 *   --write          write src/data/subject.json
 *   --json           print the record instead of the table
 *
 * The tables themselves live in src/lang/bsp.ts with their citations. This
 * script only drives them, so there is one source of truth for the numbers.
 */

import { writeFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { register } from "node:module";
import { pathToFileURL } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const OUT = join(HERE, "..", "src", "data", "subject.json");

// ── argument parsing ────────────────────────────────────────────────

const argv = process.argv.slice(2);
const flag = (name, fallback) => {
  const i = argv.indexOf(`--${name}`);
  return i >= 0 && argv[i + 1] && !argv[i + 1].startsWith("--") ? argv[i + 1] : fallback;
};
const has = (name) => argv.includes(`--${name}`);

const segmentLengthsM = {};
for (let i = 0; i < argv.length; i++) {
  if (argv[i] !== "--length") continue;
  const spec = argv[i + 1] ?? "";
  const [seg, val] = spec.split("=");
  if (!seg || !val || !Number.isFinite(+val)) {
    console.error(`--length expects seg=metres, got "${spec}"`);
    process.exit(2);
  }
  segmentLengthsM[seg] = +val;
}

const subject = {
  massKg: +flag("mass", 83),
  statureM: +flag("stature", 1.85),
  sex: flag("sex", "male"),
  model: flag("model", "deLeva"),
  ...(Object.keys(segmentLengthsM).length ? { segmentLengthsM } : {}),
};

for (const [k, v] of [["massKg", subject.massKg], ["statureM", subject.statureM]]) {
  if (!Number.isFinite(v) || v <= 0) {
    console.error(`${k} must be a positive number, got ${v}`);
    process.exit(2);
  }
}
if (!["male", "female"].includes(subject.sex)) {
  console.error(`--sex must be male or female, got "${subject.sex}"`);
  process.exit(2);
}
if (!["deLeva", "dempster"].includes(subject.model)) {
  console.error(`--model must be deLeva or dempster, got "${subject.model}"`);
  process.exit(2);
}

// ── load the TypeScript tables ──────────────────────────────────────
//
// The tables live in bsp.ts so the app and this script cannot drift apart.
// Rather than duplicate them here, transpile on the fly.

let bsp;
try {
  register("ts-node/esm", pathToFileURL("./"));
  bsp = await import(pathToFileURL(join(HERE, "..", "src", "lang", "bsp.ts")).href);
} catch {
  // ts-node is not a dependency of this project. Fall back to a tiny
  // transpile: bsp.ts is plain data plus functions, with type-only imports,
  // so stripping types with esbuild (already present via vite) is enough.
  const esbuild = await import("esbuild");
  const built = await esbuild.build({
    entryPoints: [join(HERE, "..", "src", "lang", "bsp.ts")],
    bundle: true,
    format: "esm",
    write: false,
    platform: "node",
    logLevel: "silent",
  });
  const code = built.outputFiles[0].text;
  const url = "data:text/javascript;base64," + Buffer.from(code).toString("base64");
  bsp = await import(url);
}

const { analyseSubject, massClosure, REFERENCE_SAMPLE } = bsp;

// ── run ─────────────────────────────────────────────────────────────

let segments;
try {
  segments = analyseSubject(subject);
} catch (e) {
  console.error(`\n${e.message}\n`);
  process.exit(1);
}

const closure = massClosure(subject.model, subject.sex);
const ref = REFERENCE_SAMPLE[subject.model]?.[subject.sex];

const record = {
  schema: "vitruvius-subject/1",
  subject,
  reference: ref ?? null,
  massClosure: closure,
  segments: segments.map((s) => ({
    segment: s.segment,
    endpoints: s.endpoints,
    region: s.region,
    paired: s.paired,
    massKg: s.massKg,
    totalMassKg: s.totalMassKg,
    lengthM: Number.isFinite(s.lengthM) ? s.lengthM : null,
    lengthSource: s.lengthSource,
    cmFromProximalM: Number.isFinite(s.cmFromProximalM) ? s.cmFromProximalM : null,
    inertiaCmKgM2: s.inertiaCmKgM2,
    inertiaProximalKgM2: s.inertiaProximalKgM2,
  })),
};

if (has("json")) {
  console.log(JSON.stringify(record, null, 2));
} else {
  const n = (v, d = 4) => (v === null || v === undefined || !Number.isFinite(v) ? "—" : v.toFixed(d));
  console.log(`\nSubject: ${subject.massKg} kg, ${subject.statureM} m, ${subject.sex}`);
  console.log(`Model:   ${subject.model}` + (ref ? `  (reference sample ${ref.massKg} kg, ${ref.statureM} m, n=${ref.n})` : ""));
  console.log("");
  console.log(
    "segment".padEnd(14) + "mass kg".padStart(9) + "len m".padStart(8) +
    "src".padStart(11) + "CM m".padStart(8) + "I_cm".padStart(11) + "  region",
  );
  console.log("-".repeat(76));
  for (const s of record.segments) {
    console.log(
      s.segment.padEnd(14) +
        n(s.massKg, 3).padStart(9) +
        n(s.lengthM, 4).padStart(8) +
        s.lengthSource.padStart(11) +
        n(s.cmFromProximalM, 4).padStart(8) +
        (s.inertiaCmKgM2 === null ? "—" : s.inertiaCmKgM2.toExponential(2)).padStart(11) +
        "  " + (s.region ?? "—"),
    );
  }
  console.log("-".repeat(76));
  const summed = record.segments
    .filter((s) => !["upper trunk", "middle trunk", "lower trunk", "thorax", "abdomen", "pelvis"].includes(s.segment))
    .reduce((a, s) => a + s.totalMassKg, 0);
  console.log(
    `mass closure: ${(closure * 100).toFixed(2)}% of body mass  ` +
      `(${summed.toFixed(2)} of ${subject.massKg} kg)`,
  );
  const noLength = record.segments.filter((s) => s.lengthSource === "unavailable");
  if (noLength.length) {
    console.log(
      `\n${noLength.length} segment(s) have no length source and therefore no ` +
        `inertia: ${noLength.map((s) => s.segment).join(", ")}.`,
    );
    console.log(`Supply one with --length <segment>=<metres> if you have measured it.`);
  }
}

if (has("write")) {
  writeFileSync(OUT, JSON.stringify(record, null, 2) + "\n", "utf8");
  console.log(`\nwrote ${OUT}`);
}
