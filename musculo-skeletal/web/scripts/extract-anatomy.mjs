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
const ANATOMY = join(HERE, "..", "public", "anatomy");
const SRC = join(ANATOMY, "index.html");
const SETTINGS = join(ANATOMY, "anatomy-settings.js");
const OUT = join(HERE, "..", "src", "data", "anatomy.json");

const html = readFileSync(SRC, "utf8");

/**
 * Display labels from the template's own settings file.
 *
 * The template carries a human label for every region ("RIGHT EYE", not
 * "right-eye"). Regenerating those from the CSS class would lose the
 * distinctions the author drew, so they are read from the source rather than
 * derived -- and a region whose label is missing is reported, not silently
 * given a prettified class name.
 */
function labels() {
  let js;
  try {
    js = readFileSync(SETTINGS, "utf8");
  } catch {
    console.warn("  anatomy-settings.js not readable; labels will be absent");
    return {};
  }
  const out = {};
  // "ana12":{ ... "hover": "PUBIS", ...
  const re = /"(ana\d+)"\s*:\s*\{[^}]*?"hover"\s*:\s*"([^"]*)"/g;
  let m;
  while ((m = re.exec(js))) {
    // Strip any markup the template allows in a tooltip.
    out[m[1]] = m[2].replace(/<[^>]*>/g, "").trim();
  }
  return out;
}

const LABELS = labels();

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
    paths.push({
      id: m[1],
      region: m[2],
      d: m[3],
      label: LABELS[m[1]] ?? null,
    });
  }
  // Navigation overlays (.gob/.goa) are template chrome, not anatomy.
  views[id === "basea" ? "body" : "organs"] = {
    viewBox: viewBox(body),
    // The template's own backdrop for this view. The SVG regions are painted
    // over a photographic plate; carrying the reference lets the app show
    // the full illustration where there is room for it, while the outlines
    // alone remain usable at thumbnail size.
    image: (body.match(/xlink:href="([^"]+)"/) ?? [])[1] ?? null,
    paths: paths.filter((p) => p.region !== "gob" && p.region !== "goa"),
  };
}

const total = Object.values(views).reduce((n, v) => n + v.paths.length, 0);

for (const [name, v] of Object.entries(views)) {
  console.log(`${name}: ${v.paths.length} regions, viewBox ${v.viewBox.join(" ")}`);
  console.log(`  ${v.paths.map((p) => p.region).join(", ")}`);
  const unlabelled = v.paths.filter((p) => !p.label).map((p) => p.region);
  if (unlabelled.length) {
    console.log(`  ${unlabelled.length} without a label: ${unlabelled.join(", ")}`);
  }
  console.log(`  backdrop: ${v.image ?? "none"}`);
}
console.log(`\ntotal ${total} regions`);

if (process.argv.includes("--write")) {
  writeFileSync(OUT, JSON.stringify(views, null, 2) + "\n", "utf8");
  const bytes = readFileSync(OUT).length;
  console.log(`wrote ${OUT} (${(bytes / 1024).toFixed(1)} KB)`);
}
