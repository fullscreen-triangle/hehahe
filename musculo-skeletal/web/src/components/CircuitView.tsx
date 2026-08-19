/**
 * Circuit topology with stratum bands, phase-animated charge flow, and a
 * severed-edge overlay.
 *
 * Layout is derived from the circuit itself: compartments are placed by
 * stratum (vertical) and by position along the circulation (horizontal), so
 * the picture changes when the program does rather than being hand-placed.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import * as d3 from "d3";
import type { Circuit } from "../lang/circuit";
import { closureIndex, stratumOf } from "../lang/circuit";
import type { ArmResult } from "../lang/runtime";
import { MONO, SANS, type Theme } from "../theme";

const BANDS = [
  { name: "supraspinal", y0: 0.02, y1: 0.30 },
  { name: "spinal", y0: 0.30, y1: 0.56 },
  { name: "reflex", y0: 0.56, y1: 0.98 },
] as const;

interface Props {
  arm: ArmResult;
  intact: Circuit | null;
  theme: Theme;
  animate: boolean;
}

export function CircuitView({ arm, intact, theme: T, animate }: Props) {
  const ref = useRef<SVGSVGElement>(null);
  const [size, setSize] = useState({ w: 800, h: 460 });
  const [hovered, setHovered] = useState<string | null>(null);

  useEffect(() => {
    const el = ref.current?.parentElement;
    if (!el) return;
    const ro = new ResizeObserver(() => {
      setSize({ w: el.clientWidth, h: el.clientHeight });
    });
    ro.observe(el);
    setSize({ w: el.clientWidth, h: el.clientHeight });
    return () => ro.disconnect();
  }, []);

  /** Layout: stratum sets y, position along the circulation sets x. */
  const layout = useMemo(() => {
    const c = arm.circuit;
    const order = [...c.outbound, ...c.ret.slice(1)];
    const seen: string[] = [];
    for (const n of order) if (!seen.includes(n)) seen.push(n);
    for (const n of c.compartments.keys()) if (!seen.includes(n)) seen.push(n);

    const byStratum = new Map<string, string[]>();
    for (const n of seen) {
      const s = stratumOf(c, n) ?? "reflex";
      if (!byStratum.has(s)) byStratum.set(s, []);
      byStratum.get(s)!.push(n);
    }

    const pos = new Map<string, { x: number; y: number }>();
    for (const b of BANDS) {
      const members = byStratum.get(b.name) ?? [];
      const mid = (b.y0 + b.y1) / 2;
      members.forEach((n, i) => {
        const t = members.length === 1 ? 0.5 : i / (members.length - 1);
        // Fan the reflex stratum into an arc so the loop reads as a loop.
        const wobble = b.name === "reflex"
          ? Math.sin(t * Math.PI) * (b.y1 - b.y0) * 0.34
          : 0;
        pos.set(n, { x: 0.1 + t * 0.8, y: mid + wobble - (b.name === "reflex" ? 0.06 : 0) });
      });
    }
    return pos;
  }, [arm]);

  /** Elements the lesion removed, relative to the intact circuit. */
  const removed = useMemo(() => {
    if (!intact) return [] as { src: string; dst: string; name: string }[];
    const out: { src: string; dst: string; name: string }[] = [];
    for (const [k, e] of intact.elements) {
      if (!arm.circuit.elements.has(k)) out.push({ src: e.src, dst: e.dst, name: e.name });
    }
    return out;
  }, [arm, intact]);

  useEffect(() => {
    const svg = d3.select(ref.current);
    svg.selectAll("*").remove();
    const { w, h } = size;
    if (w < 40 || h < 40) return;

    const c = arm.circuit;
    const g = svg.append("g");
    const bandColor = (n: string) =>
      n === "supraspinal" ? T.supra : n === "spinal" ? T.spinal : T.reflex;

    // stratum bands
    for (const b of BANDS) {
      g.append("rect")
        .attr("x", 0).attr("y", b.y0 * h)
        .attr("width", w).attr("height", (b.y1 - b.y0) * h)
        .attr("fill", bandColor(b.name)).attr("opacity", 0.045);
      g.append("text")
        .attr("x", 10).attr("y", b.y0 * h + 14)
        .attr("fill", bandColor(b.name)).attr("opacity", 0.65)
        .attr("font-size", 9.5).attr("font-family", SANS)
        .attr("letter-spacing", 0.6)
        .text(b.name.toUpperCase());
    }

    const P = (n: string) => {
      const p = layout.get(n);
      return p ? { x: p.x * w, y: p.y * h } : { x: w / 2, y: h / 2 };
    };

    const onOutbound = new Set<string>();
    for (let i = 0; i + 1 < c.outbound.length; i++) onOutbound.add(`${c.outbound[i]}>${c.outbound[i + 1]}`);

    const edge = (
      a: { x: number; y: number }, b: { x: number; y: number }, bow: number,
    ) => {
      const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
      const dx = b.x - a.x, dy = b.y - a.y;
      const len = Math.hypot(dx, dy) || 1;
      const nx = -dy / len, ny = dx / len;
      return `M${a.x},${a.y} Q${mx + nx * bow},${my + ny * bow} ${b.x},${b.y}`;
    };

    // severed edges first, beneath
    for (const r of removed) {
      const a = P(r.src), b = P(r.dst);
      g.append("path")
        .attr("d", edge(a, b, 26))
        .attr("fill", "none").attr("stroke", T.open)
        .attr("stroke-width", 1.4).attr("stroke-dasharray", "3,4")
        .attr("opacity", 0.55);
      const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
      g.append("text")
        .attr("x", mx).attr("y", my - 6).attr("text-anchor", "middle")
        .attr("fill", T.open).attr("font-size", 13).attr("font-weight", 700)
        .text("✕");
    }

    // live elements
    for (const e of c.elements.values()) {
      const a = P(e.src), b = P(e.dst);
      const out = onOutbound.has(`${e.src}>${e.dst}`);
      const col = out ? T.series[0] : T.series[2];
      const bow = out ? -24 : 24;
      const dim = e.gain < 0.5;

      const path = g.append("path")
        .attr("d", edge(a, b, bow))
        .attr("fill", "none")
        .attr("stroke", col)
        .attr("stroke-width", dim ? 1.1 : 2)
        .attr("opacity", hovered && hovered !== e.name ? 0.22 : dim ? 0.5 : 0.85)
        .attr("stroke-dasharray", dim ? "5,3" : "none")
        .style("cursor", "pointer");

      path.on("mouseenter", () => setHovered(e.name))
        .on("mouseleave", () => setHovered(null));

      if (animate && closureIndex(c) === "closed") {
        const node = path.node() as SVGPathElement;
        const L = node.getTotalLength();
        g.append("circle")
          .attr("r", 3).attr("fill", col).attr("opacity", 0.95)
          .append("animateMotion")
          .attr("dur", `${Math.max(1.2, e.delay * 120)}s`)
          .attr("repeatCount", "indefinite")
          .attr("path", edge(a, b, bow));
      }

      if (hovered === e.name || (!hovered && !dim)) {
        const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
        const dx = b.x - a.x, dy = b.y - a.y;
        const len = Math.hypot(dx, dy) || 1;
        g.append("text")
          .attr("x", mx + (-dy / len) * bow * 0.62)
          .attr("y", my + (dx / len) * bow * 0.62)
          .attr("text-anchor", "middle")
          .attr("fill", hovered === e.name ? T.text : T.textMuted)
          .attr("font-size", hovered === e.name ? 10 : 8.5)
          .attr("font-family", MONO)
          .text(hovered === e.name
            ? `${e.name} ${(e.delay * 1e3).toFixed(1)}ms ×${e.gain.toFixed(2)}`
            : `${(e.delay * 1e3).toFixed(1)}`);
      }
    }

    // nodes
    for (const [name] of c.compartments) {
      const p = P(name);
      const s = stratumOf(c, name) ?? "reflex";
      const cap = c.compartments.get(name)!.capacitance;
      const r = 9 + Math.min(7, Math.log10(cap / 1e-9) * 1.5);

      g.append("circle")
        .attr("cx", p.x).attr("cy", p.y).attr("r", r + 4)
        .attr("fill", T.panelBg).attr("opacity", 0.9);
      g.append("circle")
        .attr("cx", p.x).attr("cy", p.y).attr("r", r)
        .attr("fill", T.surfaceBg)
        .attr("stroke", bandColor(s)).attr("stroke-width", 2);
      g.append("text")
        .attr("x", p.x).attr("y", p.y + r + 12)
        .attr("text-anchor", "middle")
        .attr("fill", T.textDim).attr("font-size", 9).attr("font-family", MONO)
        .text(name);
    }
  }, [arm, size, layout, removed, hovered, animate, T]);

  return <svg ref={ref} width={size.w} height={size.h} style={{ display: "block" }} />;
}
