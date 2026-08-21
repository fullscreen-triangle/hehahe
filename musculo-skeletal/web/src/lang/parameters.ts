/**
 * The parameter tree.
 *
 * Every quantity the tool can report about a subject or a run is a leaf in
 * one hierarchy: anthropometry, segment inertia, circuit structure, measured
 * observables, charge. The sunburst renders this tree directly, so adding a
 * parameter here makes it navigable without touching the chart.
 *
 * Each leaf carries the anatomical region it belongs to, which is what lets
 * the reference figure at the centre of the sunburst act as a heatmap: hover
 * or select any arc and the body lights up where that quantity lives.
 * A leaf with `region: null` is deliberately not localised -- whole-body
 * mass, for instance -- and painting nothing is the correct answer.
 */

export interface ParamNode {
  name: string;
  /** shown in the readout; keep to one line */
  description?: string;
  unit?: string;
  /** anatomical region this quantity belongs to; null = not localised */
  region?: string | null;
  /** leaf value, when the tree is built against a subject/run */
  value?: number;
  /** how the value was obtained, for auditability */
  derivation?: string;
  children?: ParamNode[];
}

/** Sum of leaves under a node, for arc sizing when no explicit value exists. */
export function leafCount(n: ParamNode): number {
  if (!n.children?.length) return 1;
  return n.children.reduce((s, c) => s + leafCount(c), 0);
}

/** Every leaf under a node, depth-first. */
export function leaves(n: ParamNode): ParamNode[] {
  if (!n.children?.length) return [n];
  return n.children.flatMap(leaves);
}

/** Regions touched by a node's subtree, deduplicated. */
export function regionsOf(n: ParamNode): string[] {
  const out = new Set<string>();
  for (const l of leaves(n)) if (l.region) out.add(l.region);
  return [...out];
}

/**
 * Heat map from a subtree: each region gets the value of the leaf that
 * mentions it. Where several leaves share a region the largest wins, because
 * the figure answers "where is this biggest", not "what is the total".
 */
export function heatFromNode(n: ParamNode): Record<string, number> {
  const out: Record<string, number> = {};
  for (const l of leaves(n)) {
    if (!l.region || l.value === undefined || !Number.isFinite(l.value)) continue;
    out[l.region] = Math.max(out[l.region] ?? -Infinity, l.value);
  }
  return out;
}

/** Find a node by its path of names, for linking a result to an arc. */
export function findByPath(root: ParamNode, path: string[]): ParamNode | null {
  let cur: ParamNode | undefined = root;
  for (const seg of path) {
    cur = cur?.children?.find((c) => c.name === seg);
    if (!cur) return null;
  }
  return cur ?? null;
}
