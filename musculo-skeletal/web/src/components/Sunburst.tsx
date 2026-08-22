/**
 * Sunburst navigation over the parameter tree, with the anatomical reference
 * figure at its centre.
 *
 * The design commitment: this REPLACES click-through. Every parameter the
 * tool knows about is visible as an arc at once, so reaching a leaf is a
 * single hover rather than a descent through menus. Clicking an arc zooms the
 * ring to that subtree; the centre figure is never covered, because the
 * centre is the whole point -- whatever arc you are on, the body shows where
 * that quantity lives.
 *
 * The figure is not decoration. It is driven from `heatFromNode`, so it is a
 * heatmap of the currently focused subtree, and a parameter that is not
 * localised paints nothing rather than being assigned somewhere plausible.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import * as d3 from "d3";
import { AnatomyFigure, HeatLegend, viewOf } from "./AnatomyFigure";
import { heatFromNode, leafCount, type ParamNode } from "../lang/parameters";
import type { Theme } from "../theme";

interface Props {
  theme: Theme;
  root: ParamNode;
  size?: number;
  /** radius reserved for the centre figure */
  centreRadius?: number;
  onSelect?: (node: ParamNode, path: string[]) => void;
}

type HNode = d3.HierarchyRectangularNode<ParamNode>;

export function Sunburst({ theme, root, size = 520, centreRadius = 92, onSelect }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  /** Held in a ref so the draw effect does not depend on the callback's
   *  identity. An inline `onSelect` is a new function every render, and
   *  including it in the effect deps made the ring tear down and rebind on
   *  every hover -- which destroyed the very handler that set the hover. */
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;
  const [focusPath, setFocusPath] = useState<string[]>([]);
  const [hover, setHover] = useState<HNode | null>(null);

  /** Lay the tree out once per data change. Arc angle is leaf count, so the
   *  ring is a map of the tree's shape rather than of any one metric --
   *  sizing by value would make parameters vanish when their value is 0. */
  const hierarchy = useMemo(() => {
    const h = d3.hierarchy<ParamNode>(root, (d) => d.children)
      .sum((d) => (d.children?.length ? 0 : 1))
      .sort((a, b) => (b.value ?? 0) - (a.value ?? 0));
    return d3.partition<ParamNode>().size([2 * Math.PI, 1])(h) as HNode;
  }, [root]);

  /** The node the ring is currently rooted at. */
  const focus = useMemo(() => {
    let cur: HNode = hierarchy;
    for (const seg of focusPath) {
      const next = (cur.children ?? []).find((c) => c.data.name === seg);
      if (!next) break;
      cur = next as HNode;
    }
    return cur;
  }, [hierarchy, focusPath]);

  const shown = hover ?? focus;
  const heat = useMemo(() => heatFromNode(shown.data), [shown]);
  const heatValues = Object.values(heat);
  const view = useMemo(() => {
    const regions = Object.keys(heat);
    for (const r of regions) {
      const v = viewOf(r);
      if (v === "organs") return "organs" as const;
    }
    return "body" as const;
  }, [heat]);

  useEffect(() => {
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();
    if (!svgRef.current) return;

    const R = size / 2;
    const g = svg.append("g").attr("transform", `translate(${R},${R})`);

    // Rings run from the centre figure's edge outward. Depth is measured
    // relative to the focus so zooming re-uses the full radius.
    const maxDepth = Math.max(1, d3.max(focus.descendants(), (d) => d.depth - focus.depth) ?? 1);
    const ringW = (R - centreRadius - 6) / maxDepth;

    const x = d3.scaleLinear().domain([focus.x0, focus.x1]).range([0, 2 * Math.PI]);

    const arc = d3.arc<HNode>()
      .startAngle((d) => Math.max(0, Math.min(2 * Math.PI, x(d.x0))))
      .endAngle((d) => Math.max(0, Math.min(2 * Math.PI, x(d.x1))))
      .padAngle(0.004)
      .padRadius(centreRadius)
      .innerRadius((d) => centreRadius + (d.depth - focus.depth - 1) * ringW)
      .outerRadius((d) => centreRadius + (d.depth - focus.depth) * ringW - 1.5);

    const nodes = focus.descendants().filter((d) => d.depth > focus.depth) as HNode[];

    // Colour by first-level branch so a subtree reads as one family.
    const branches = (hierarchy.children ?? []).map((c) => c.data.name);
    const palette = theme.series?.length
      ? theme.series
      : ["#7aa2f7", "#9ece6a", "#e0af68", "#bb9af7", "#7dcfff", "#f7768e"];
    const branchOf = (d: HNode) => {
      let cur: HNode = d;
      while (cur.depth > 1 && cur.parent) cur = cur.parent as HNode;
      return cur.data.name;
    };
    const colour = (d: HNode) => {
      const i = Math.max(0, branches.indexOf(branchOf(d)));
      const base = d3.color(palette[i % palette.length]) ?? d3.color("#7aa2f7")!;
      // Fade with depth so outer leaves do not overwhelm their parents.
      const rel = d.depth - focus.depth;
      return base.copy({ opacity: Math.max(0.35, 1 - (rel - 1) * 0.22) }).toString();
    };

    g.selectAll("path")
      .data(nodes)
      .join("path")
      .attr("d", arc as never)
      .attr("fill", (d) => colour(d))
      .attr("stroke", theme.panelBg)
      .attr("stroke-width", 0.8)
      .style("cursor", "pointer")
      .on("mouseenter", (_e, d) => setHover(d))
      .on("mouseleave", () => setHover(null))
      .on("click", (_e, d) => {
        const path: string[] = [];
        let cur: HNode | null = d;
        while (cur && cur.parent) { path.unshift(cur.data.name); cur = cur.parent as HNode; }
        if (d.children?.length) setFocusPath(path);
        onSelectRef.current?.(d.data, path);
      })
      .append("title")
      .text((d) => labelOf(d));

    // Arc labels, only where the arc is big enough to hold one.
    g.selectAll("text")
      .data(nodes.filter((d) => {
        const a = x(d.x1) - x(d.x0);
        const r = centreRadius + (d.depth - focus.depth - 0.5) * ringW;
        return a * r > 34 && a > 0.05;
      }))
      .join("text")
      .attr("transform", (d) => {
        const ang = ((x(d.x0) + x(d.x1)) / 2) * 180 / Math.PI - 90;
        const r = centreRadius + (d.depth - focus.depth - 0.5) * ringW;
        return `rotate(${ang}) translate(${r},0) rotate(${ang > 90 ? 180 : 0})`;
      })
      .attr("text-anchor", "middle")
      .attr("dy", "0.32em")
      .attr("font-size", 8.5)
      .attr("font-family", "ui-monospace, monospace")
      .attr("fill", theme.text)
      .attr("pointer-events", "none")
      .text((d) => truncate(d.data.name, ringW / 4.6));

  }, [hierarchy, focus, size, centreRadius, theme]);

  const crumbs = ["all", ...focusPath];

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
      {/* breadcrumb: zooming must be reversible and visible */}
      <div style={{ display: "flex", gap: 4, flexWrap: "wrap", fontSize: 10, fontFamily: "monospace", minHeight: 16 }}>
        {crumbs.map((c, i) => (
          <span key={i}>
            <span
              onClick={() => setFocusPath(focusPath.slice(0, i))}
              style={{
                cursor: "pointer",
                color: i === crumbs.length - 1 ? theme.text : theme.textDim,
                textDecoration: i === crumbs.length - 1 ? "none" : "underline",
              }}
            >{c}</span>
            {i < crumbs.length - 1 && <span style={{ color: theme.textMuted }}> ›</span>}
          </span>
        ))}
      </div>

      <div style={{ position: "relative", width: size, height: size }}>
        <svg ref={svgRef} width={size} height={size} style={{ display: "block" }} />
        {/* The figure sits in the hole and is never covered by an arc. */}
        <div style={{
          position: "absolute", left: "50%", top: "50%",
          transform: "translate(-50%,-50%)",
          width: centreRadius * 1.7, height: centreRadius * 1.7,
          display: "flex", alignItems: "center", justifyContent: "center",
          pointerEvents: "none",
        }}>
          <AnatomyFigure
            theme={theme}
            heat={heat}
            view={view}
            width={centreRadius * 1.05}
            height={centreRadius * 1.75}
            unit={shown.data.unit}
            // The hole is large enough for the illustration to read, and it
            // is what makes the centre an anatomical reference rather than an
            // abstract silhouette. Kept faint so the heat stays dominant.
            backdrop
            backdropOpacity={0.32}
          />
        </div>
      </div>

      {/* readout for whatever is under the cursor, or the focus */}
      <div style={{
        width: size, minHeight: 54, padding: "6px 10px", borderRadius: 4,
        background: theme.surfaceBg, border: `1px solid ${theme.border}`,
        fontSize: 11, lineHeight: 1.5,
      }}>
        <div style={{ fontFamily: "monospace", color: theme.text, fontWeight: 600 }}>
          {shown.data.name}
          {shown.data.value !== undefined && (
            <span style={{ color: theme.accent, marginLeft: 8 }}>
              {fmt(shown.data.value)}{shown.data.unit ? ` ${shown.data.unit}` : ""}
            </span>
          )}
          {shown.data.region === null && (
            <span style={{ color: theme.textMuted, marginLeft: 8, fontSize: 10 }}>
              not localised
            </span>
          )}
        </div>
        {shown.data.description && (
          <div style={{ color: theme.textDim, fontSize: 10 }}>{shown.data.description}</div>
        )}
        {shown.data.derivation && (
          <div style={{ color: theme.textMuted, fontSize: 9.5, fontFamily: "monospace" }}>
            {shown.data.derivation}
          </div>
        )}
        {!shown.data.description && !shown.data.value && (
          <div style={{ color: theme.textMuted, fontSize: 10 }}>
            {leafCount(shown.data)} parameters
          </div>
        )}
      </div>

      {heatValues.length > 0 && (
        <HeatLegend
          theme={theme}
          lo={Math.min(...heatValues)}
          hi={Math.max(...heatValues)}
          unit={shown.data.unit}
          width={size * 0.5}
        />
      )}
    </div>
  );
}

function labelOf(d: HNode): string {
  const parts = [d.data.name];
  if (d.data.value !== undefined) parts.push(`${fmt(d.data.value)}${d.data.unit ? " " + d.data.unit : ""}`);
  if (d.data.region) parts.push(`@ ${d.data.region}`);
  return parts.join("  ");
}

function truncate(s: string, chars: number): string {
  const n = Math.max(3, Math.floor(chars));
  return s.length <= n ? s : s.slice(0, n - 1) + "…";
}

function fmt(v: number): string {
  if (v === 0) return "0";
  const a = Math.abs(v);
  if (a >= 1e4 || a < 1e-3) return v.toExponential(3);
  return v.toPrecision(4).replace(/\.?0+$/, "");
}
