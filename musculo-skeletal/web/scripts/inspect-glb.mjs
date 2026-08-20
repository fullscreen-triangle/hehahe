/**
 * Extract rig manifests from the GLB files in public/models.
 *
 * The manifests are generated, never hand-written: a hand-written joint list
 * silently rots when a model is replaced, and a binding checked against a
 * stale manifest would report agreement it never verified. Run this after
 * adding or replacing any model.
 *
 *   node scripts/inspect-glb.mjs            # report
 *   node scripts/inspect-glb.mjs --write    # regenerate src/data/rigs.json
 */

import { readFileSync, writeFileSync, readdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const MODELS = join(HERE, "..", "public", "models");
const OUT = join(HERE, "..", "src", "data", "rigs.json");

/** Read the JSON chunk out of a GLB container. */
function readGlbJson(path) {
  const buf = readFileSync(path);
  const magic = buf.toString("ascii", 0, 4);
  if (magic !== "glTF") throw new Error(`${path}: not a GLB (magic=${magic})`);
  let off = 12;
  while (off < buf.length) {
    const len = buf.readUInt32LE(off);
    const type = buf.toString("ascii", off + 4, off + 8);
    off += 8;
    if (type === "JSON") return JSON.parse(buf.toString("utf8", off, off + len));
    off += len;
  }
  throw new Error(`${path}: no JSON chunk`);
}

/** Tissue prefix of a joint name, if the rig is tissue-layered. */
function tissueOf(name) {
  for (const t of ["bone", "vein", "muscle"]) {
    if (name.startsWith(t + "_") || name.startsWith(t + ".")) return t;
  }
  return null;
}

/** Anatomical segment: the joint name with tissue prefix and Blender-style
 *  `.N_N` suffix stripped, so the three tissue chains share segment names. */
function segmentOf(name) {
  const base = name.split(".")[0];
  const t = tissueOf(name);
  return t ? base.slice(t.length + 1) : base;
}

function analyse(file) {
  const path = join(MODELS, file);
  const j = readGlbJson(path);
  const nodes = j.nodes ?? [];
  const skins = j.skins ?? [];
  const anims = j.animations ?? [];

  const parent = new Map();
  nodes.forEach((n, i) => (n.children ?? []).forEach((c) => parent.set(c, i)));

  const joints = skins.length ? skins[0].joints : [];
  const jointSet = new Set(joints);

  // Rest-pose world positions, so anatomical distance is computable.
  const world = new Map();
  const worldOf = (i) => {
    if (world.has(i)) return world.get(i);
    const t = nodes[i].translation ?? [0, 0, 0];
    const p = parent.get(i);
    const base = p === undefined ? [0, 0, 0] : worldOf(p);
    const w = [base[0] + t[0], base[1] + t[1], base[2] + t[2]];
    world.set(i, w);
    return w;
  };

  const jointList = joints.map((idx) => {
    const n = nodes[idx];
    const name = n.name ?? `node${idx}`;
    const p = parent.get(idx);
    return {
      node: idx,
      name,
      parent: p !== undefined && jointSet.has(p) ? nodes[p].name : null,
      tissue: tissueOf(name),
      segment: segmentOf(name),
      rest: (n.translation ?? [0, 0, 0]).map((v) => +v.toFixed(4)),
      world: worldOf(idx).map((v) => +v.toFixed(4)),
    };
  });

  // Tissue co-registration: do the chains describe the same skeleton?
  const bySegment = new Map();
  for (const jt of jointList) {
    if (!jt.tissue) continue;
    if (!bySegment.has(jt.segment)) bySegment.set(jt.segment, {});
    bySegment.get(jt.segment)[jt.tissue] = jt.rest;
  }
  let maxDrift = 0;
  let coregistered = 0;
  for (const [, byTissue] of bySegment) {
    const vs = Object.values(byTissue);
    if (vs.length < 2) continue;
    coregistered++;
    for (const a of vs)
      for (const b of vs)
        for (let k = 0; k < 3; k++) maxDrift = Math.max(maxDrift, Math.abs(a[k] - b[k]));
  }

  const animations = anims.map((a) => {
    let duration = 0;
    for (const s of a.samplers ?? []) {
      const acc = j.accessors[s.input];
      if (acc?.max?.length) duration = Math.max(duration, acc.max[0]);
    }
    const targets = new Set();
    for (const c of a.channels ?? []) {
      const tn = c.target?.node;
      if (tn !== undefined) targets.add(nodes[tn].name ?? `node${tn}`);
    }
    return { name: a.name ?? "<unnamed>", duration: +duration.toFixed(3), targets: targets.size };
  });

  return {
    file,
    bytes: readFileSync(path).length,
    meshes: (j.meshes ?? []).map((m) => m.name ?? "<unnamed>"),
    jointCount: joints.length,
    joints: jointList,
    tissues: [...new Set(jointList.map((x) => x.tissue).filter(Boolean))],
    segments: [...bySegment.keys()],
    coregistration: { segments: coregistered, maxRestDrift: +maxDrift.toFixed(6) },
    animations,
    bindable: joints.length > 0,
  };
}

const files = readdirSync(MODELS).filter((f) => f.endsWith(".glb")).sort();
const rigs = {};
for (const f of files) {
  const r = analyse(f);
  rigs[f.replace(/\.glb$/, "")] = r;

  console.log("=".repeat(72));
  console.log(`${f}  (${(r.bytes / 1e6).toFixed(1)} MB)`);
  console.log(`  joints=${r.jointCount}  meshes=${r.meshes.length}  animations=${r.animations.length}`);
  if (r.tissues.length) {
    console.log(`  tissue chains: ${r.tissues.join(", ")}`);
    console.log(
      `  co-registration: ${r.coregistration.segments} segments, ` +
        `max rest drift ${r.coregistration.maxRestDrift}` +
        (r.coregistration.maxRestDrift === 0 ? "  (exactly co-registered)" : ""),
    );
  }
  for (const a of r.animations) {
    console.log(`  clip '${a.name}'  ${a.duration}s  ${a.targets} targets`);
  }
  if (!r.bindable) console.log("  NOT BINDABLE — no skin; usable only as static backdrop");
}

if (process.argv.includes("--write")) {
  writeFileSync(OUT, JSON.stringify(rigs, null, 2) + "\n", "utf8");
  console.log(`\nwrote ${OUT}`);
}
