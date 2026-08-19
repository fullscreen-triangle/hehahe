/**
 * Cross-arm comparison: the view that answers "what did this lesion do".
 *
 * Two panels. The first is a slope chart of every numeric observable from a
 * chosen reference arm to each other arm, on a per-observable normalised
 * scale, so quantities in different units can be read together. The second
 * separates arms by closure index against a chosen observable, which is the
 * question the language exists to make askable: did this manipulation change
 * the topology, or only the numbers?
 */

import { useEffect, useMemo, useRef, useState } from "react";
import * as d3 from "d3";
import type { ArmResult } from "../lang/runtime";
import { OBSERVABLES } from "../lang/observables";
import { MONO, SANS, type Theme } from "../theme";

interface Props { arms: ArmResult[]; theme: Theme; }

export function CompareView({ arms, theme: T }: Props) {
  const slopeRef = useRef<SVGSVGElement>(null);
  const scatterRef = useRef<SVGSVGElement>(null);
  const [ref0, setRef0] = useState(arms[0]?.name ?? "");
  const [size, setSize] = useState({ w: 700, h: 460 });
  const [hover, setHover] = useState<{ x: number; y: number; text: string } | null>(null);

  useEffect(() => {
    if (!arms.find((a) => a.name === ref0)) setRef0(arms[0]?.name ?? "");
  }, [arms, ref0]);

  useEffect(() => {
    const el = slopeRef.current?.parentElement?.parentElement;
    if (!el) return;
    const ro = new ResizeObserver(() => setSize({ w: el.clientWidth, h: el.clientHeight }));
    ro.observe(el);
    setSize({ w: el.clientWidth, h: el.clientHeight });
    return () => ro.disconnect();
  }, []);

  /** Observables numeric and finite in at least two arms. */
  const numeric = useMemo(() => {
    const names: string[] = [];
    for (const a of arms) for (const k of a.store.keys()) if (!names.includes(k)) names.push(k);
    return names.filter((n) => {
      let c = 0;
      for (const a of arms) {
        const v = a.store.get(n)?.value;
        if (typeof v === "number" && Number.isFinite(v)) c++;
      }
      return c >= 2;
    });
  }, [arms]);

  const [scatterObs, setScatterObs] = useState("");
  useEffect(() => {
    if (!numeric.includes(scatterObs)) setScatterObs(numeric[0] ?? "");
  }, [numeric, scatterObs]);

  // slope chart
  useEffect(() => {
    const svg = d3.select(slopeRef.current);
    svg.selectAll("*").remove();
    const W = size.w, H = Math.max(200, size.h * 0.56);
    const m = { top: 20, right: 130, bottom: 30, left: 130 };
    const w = W - m.left - m.right, h = H - m.top - m.bottom;
    if (w < 40 || h < 40 || !ref0) return;

    const g = svg.attr("width", W).attr("height", H)
      .append("g").attr("transform", `translate(${m.left},${m.top})`);

    const others = arms.filter((a) => a.name !== ref0);
    if (!others.length) return;

    const x = d3.scalePoint().domain([ref0, ...others.map((a) => a.name)]).range([0, w]).padding(0.12);
    const y = d3.scaleLinear().domain([0, 1]).range([h, 0]);

    // axis rails
    for (const nm of [ref0, ...others.map((a) => a.name)]) {
      const px = x(nm)!;
      const arm = arms.find((a) => a.name === nm)!;
      g.append("line").attr("x1", px).attr("x2", px).attr("y1", 0).attr("y2", h)
        .attr("stroke", T.gridLine).attr("stroke-width", 1);
      g.append("text").attr("x", px).attr("y", h + 20).attr("text-anchor", "middle")
        .attr("fill", arm.closure === "open" ? T.open : T.closed)
        .attr("font-size", 10).attr("font-family", MONO)
        .text(`${arm.closure === "open" ? "◇" : "●"} ${nm}`);
    }

    const refArm = arms.find((a) => a.name === ref0)!;
    // Right-edge labels are placed after all lines, then pushed apart so
    // that observables with similar values remain individually readable.
    const labelSlots: { y: number; obs: string; col: string; nm: string }[] = [];

    numeric.forEach((obs, i) => {
      const vals = arms.map((a) => {
        const v = a.store.get(obs)?.value;
        return typeof v === "number" && Number.isFinite(v) ? v : null;
      });
      const fin = vals.filter((v): v is number => v !== null);
      const lo = Math.min(...fin), hi = Math.max(...fin);
      const norm = (v: number) => (hi === lo ? 0.5 : (v - lo) / (hi - lo));

      const col = T.series[i % T.series.length];
      const pts: { nm: string; v: number }[] = [];
      for (const a of [refArm, ...others]) {
        const v = a.store.get(obs)?.value;
        if (typeof v === "number" && Number.isFinite(v)) pts.push({ nm: a.name, v });
      }
      if (pts.length < 2) return;

      const line = d3.line<{ nm: string; v: number }>()
        .x((d) => x(d.nm)!).y((d) => y(norm(d.v)));

      g.append("path").datum(pts).attr("d", line)
        .attr("fill", "none").attr("stroke", col).attr("stroke-width", 1.6)
        .attr("opacity", 0.75)
        .style("cursor", "pointer")
        .on("mouseenter", (e: MouseEvent) => setHover({
          x: e.clientX, y: e.clientY,
          text: `${obs}\n` + pts.map((p) => `  ${p.nm}: ${p.v.toPrecision(5)}`).join("\n"),
        }))
        .on("mouseleave", () => setHover(null));

      for (const p of pts) {
        g.append("circle").attr("cx", x(p.nm)!).attr("cy", y(norm(p.v)))
          .attr("r", 3).attr("fill", col).attr("opacity", 0.9);
      }

      labelSlots.push({ y: y(norm(pts[pts.length - 1].v)), obs, col, nm: pts[pts.length - 1].nm });
    });

    labelSlots.sort((a, b) => a.y - b.y);
    const MINGAP = 11;
    for (let i = 1; i < labelSlots.length; i++) {
      if (labelSlots[i].y - labelSlots[i - 1].y < MINGAP) {
        labelSlots[i].y = labelSlots[i - 1].y + MINGAP;
      }
    }
    for (const L of labelSlots) {
      g.append("line")
        .attr("x1", x(L.nm)! + 3).attr("y1", L.y)
        .attr("x2", x(L.nm)! + 9).attr("y2", L.y)
        .attr("stroke", L.col).attr("opacity", 0.5);
      g.append("text").attr("x", x(L.nm)! + 12).attr("y", L.y + 3)
        .attr("fill", L.col).attr("font-size", 8.5).attr("font-family", MONO)
        .text(L.obs.length > 22 ? L.obs.slice(0, 21) + "…" : L.obs);
    }

    g.append("text").attr("x", -m.left + 6).attr("y", -8)
      .attr("fill", T.textMuted).attr("font-size", 9.5).attr("font-family", SANS)
      .text("each observable normalised to its own range across arms");
  }, [arms, ref0, numeric, size, T]);

  // closure-vs-value scatter
  useEffect(() => {
    const svg = d3.select(scatterRef.current);
    svg.selectAll("*").remove();
    const W = size.w, H = Math.max(160, size.h * 0.40);
    const m = { top: 18, right: 20, bottom: 42, left: 74 };
    const w = W - m.left - m.right, h = H - m.top - m.bottom;
    if (w < 40 || h < 40 || !scatterObs) return;

    const g = svg.attr("width", W).attr("height", H)
      .append("g").attr("transform", `translate(${m.left},${m.top})`);

    const rows = arms.map((a) => ({
      name: a.name,
      closure: a.closure,
      v: a.store.get(scatterObs)?.value,
    })).filter((r) => typeof r.v === "number" && Number.isFinite(r.v)) as
      { name: string; closure: string; v: number }[];
    if (!rows.length) return;

    const x = d3.scaleLinear()
      .domain(d3.extent(rows, (r) => r.v) as [number, number]).nice().range([0, w]);
    const y = d3.scalePoint().domain(["closed", "open"]).range([h * 0.25, h * 0.75]).padding(0.5);

    g.append("g").attr("transform", `translate(0,${h})`)
      .call(d3.axisBottom(x).ticks(6, "~g").tickSize(-h))
      .call((s) => {
        s.selectAll("line").attr("stroke", T.gridLine);
        s.selectAll("text").attr("fill", T.gridText).attr("font-size", 9);
        s.select(".domain").attr("stroke", T.border);
      });
    g.append("g").call(d3.axisLeft(y).tickSize(0))
      .call((s) => {
        s.selectAll("text").attr("fill", T.textDim).attr("font-size", 10).attr("font-family", MONO);
        s.select(".domain").attr("stroke", "none");
      });

    // Arms with near-identical values would print their names on top of one
    // another, so stack the labels instead.
    const placed: { x: number; y: number }[] = [];
    for (const r of [...rows].sort((a, b) => a.v - b.v)) {
      const col = r.closure === "open" ? T.open : T.closed;
      const cx = x(r.v), cy = y(r.closure)!;
      g.append("circle").attr("cx", cx).attr("cy", cy)
        .attr("r", 6.5).attr("fill", col).attr("opacity", 0.85)
        .attr("stroke", T.panelBg).attr("stroke-width", 1.5);

      let ly = cy - 13;
      while (placed.some((p) => Math.abs(p.x - cx) < 62 && Math.abs(p.y - ly) < 11)) ly -= 11;
      placed.push({ x: cx, y: ly });
      g.append("text").attr("x", cx).attr("y", ly)
        .attr("text-anchor", "middle").attr("fill", T.textDim)
        .attr("font-size", 9).attr("font-family", MONO).text(r.name);
    }

    g.append("text").attr("x", w / 2).attr("y", h + 34)
      .attr("text-anchor", "middle").attr("fill", T.textDim)
      .attr("font-size", 10).attr("font-family", SANS).text(scatterObs);
  }, [arms, scatterObs, size, T]);

  const sel: React.CSSProperties = {
    background: T.surfaceBg, color: T.text, border: `1px solid ${T.border}`,
    borderRadius: 3, fontSize: 11, padding: "2px 6px", fontFamily: MONO,
  };

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", overflow: "hidden" }}>
      <div style={{
        padding: "6px 12px", borderBottom: `1px solid ${T.borderSoft}`,
        display: "flex", gap: 14, alignItems: "center", fontFamily: SANS, fontSize: 11,
        color: T.textDim,
      }}>
        <label style={{ display: "flex", gap: 6, alignItems: "center" }}>
          reference
          <select value={ref0} onChange={(e) => setRef0(e.target.value)} style={sel}>
            {arms.map((a) => <option key={a.name} value={a.name}>{a.name}</option>)}
          </select>
        </label>
        <label style={{ display: "flex", gap: 6, alignItems: "center", marginLeft: "auto" }}>
          split by
          <select value={scatterObs} onChange={(e) => setScatterObs(e.target.value)} style={sel}>
            {numeric.map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </label>
      </div>
      <div style={{ flex: 1, overflow: "auto" }}>
        <svg ref={slopeRef} />
        <svg ref={scatterRef} />
      </div>
      {hover && (
        <div style={{
          position: "fixed", left: Math.min(hover.x + 12, window.innerWidth - 300),
          top: hover.y + 14, padding: "7px 10px", background: T.panelBg,
          border: `1px solid ${T.border}`, borderRadius: 4, color: T.text,
          fontFamily: MONO, fontSize: 10.5, whiteSpace: "pre", zIndex: 60,
          boxShadow: "0 8px 24px rgba(0,0,0,0.3)",
        }}>{hover.text}</div>
      )}
    </div>
  );
}
