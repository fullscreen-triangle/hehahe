/**
 * Extract the anatomy SVG geometry from public/anatomy/index.html into a
 * data module the React app can render directly.
 *
 * The source template is jQuery-driven and paints its regions over two PNG
 * photographs (600 KB). For a small always-visible heatmap that is the wrong
 * dependency: we want the outlines only, at any size, with fill under our
 * own control. The path `d` attributes ARE that geometry, so this pulls them
 * out and drops everything else.
 *
 * Generated, never hand-edited. Re-run after changing the template:
 *
 *   node scripts/extract-anatomy.mjs --write
 */

import { readFileSync, writeFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const SRC = join(HERE, "..", "public", "anatomy", "index.html");
const OUT = join(HERE, "..", "src", "data", "anatomy.json");

const html = readFileSync(SRC, "utf8");

/** Split the document into its two views. */
function viewBlocks(s) {
  const out = [];
  const re = /<div id="(base[ab])">([\s\S]*?)(?=<div id="base[ab]">|<\/body>)/g;
  let m;
  while ((m = re.exec(s))) out.push({ id: m[1], body: m[2] });
  return out;
}

/** viewBox of the first svg in a block. */
function viewBox(block) {
  const m = block.match(/viewBox="([^"]+)"/);
  if (!m) return [0, 0, 800, 1360];
  return m[1].trim().split(/\s+/).map(Number);
}

const views = {};
for (const { id, body } of viewBlocks(html)) {
  const paths = [];
  const re = /<path\s+id="(ana\d+)"\s+class="([^"]+)"[^>]*\sd="([^"]+)"/g;
  let m;
  while ((m = re.exec(body))) {
    paths.push({ id: m[1], region: m[2], d: m[3] });
  }
  // Navigation overlays (.gob/.goa) are template chrome, not anatomy.
  views[id === "basea" ? "body" : "organs"] = {
    viewBox: viewBox(body),
    paths: paths.filter((p) => p.region !== "gob" && p.region !== "goa"),
  };
}

const total = Object.values(views).reduce((n, v) => n + v.paths.length, 0);

for (const [name, v] of Object.entries(views)) {
  console.log(`${name}: ${v.paths.length} regions, viewBox ${v.viewBox.join(" ")}`);
  console.log(`  ${v.paths.map((p) => p.region).join(", ")}`);
}
console.log(`\ntotal ${total} regions`);

if (process.argv.includes("--write")) {
  writeFileSync(OUT, JSON.stringify(views, null, 2) + "\n", "utf8");
  const bytes = readFileSync(OUT).length;
  console.log(`wrote ${OUT} (${(bytes / 1024).toFixed(1)} KB)`);
}
