/**
 * Spectral view: PSD per arm with a linked frequency brush, and band powers
 * that recompute from the brushed range.
 *
 * Both charts read the real backend, so brushing is not filtering a mock
 * table -- it re-integrates the periodogram over the selected band.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import * as d3 from "d3";
import type { Backend } from "../lang/backend";
import { STRATUM_BANDS } from "../lang/observables";
import type { ArmResult } from "../lang/runtime";
import { MONO, SANS, type Theme } from "../theme";

interface Props {
  arms: ArmResult[];
  backend: Backend;
  theme: Theme;
  selected: Set<string>;
  onToggle: (name: string) => void;
}

export function SpectraView({ arms, backend, theme: T, selected, onToggle }: Props) {
  const psdRef = useRef<SVGSVGElement>(null);
  const barRef = useRef<SVGSVGElement>(null);
  const [brush, setBrush] = useState<[number, number] | null>(null);
  const [size, setSize] = useState({ w: 700, h: 460 });

  useEffect(() => {
    const el = psdRef.current?.parentElement?.parentElement;
    if (!el) return;
    const ro = new ResizeObserver(() => setSize({ w: el.clientWidth, h: el.clientHeight }));
    ro.observe(el);
    setSize({ w: el.clientWidth, h: el.clientHeight });
    return () => ro.disconnect();
  }, []);

  const spectra = useMemo(
    () => arms.map((a) => ({ arm: a.name, closure: a.closure, ...backend.psd(a.circuit, 140) })),
    [arms, backend],
  );

  const color = (i: number) => T.series[i % T.series.length];

  // PSD
  useEffect(() => {
    const svg = d3.select(psdRef.current);
    svg.selectAll("*").remove();
    const W = size.w, H = Math.max(180, size.h * 0.58);
    const m = { top: 14, right: 16, bottom: 34, left: 58 };
    const w = W - m.left - m.right, h = H - m.top - m.bottom;
    if (w < 30 || h < 30) return;

    const g = svg.attr("width", W).attr("height", H)
      .append("g").attr("transform", `translate(${m.left},${m.top})`);

    const all = spectra.flatMap((s) => s.p).filter((v) => v > 0);
    const lo = Math.max(d3.min(all) ?? 1e-9, 1e-12);
    const hi = d3.max(all) ?? 1;

    const x = d3.scaleLog().domain([0.05, 5]).range([0, w]);
    const y = d3.scaleLog().domain([lo, hi]).range([h, 0]).nice();

    for (const [name, [f0, f1]] of Object.entries(STRATUM_BANDS)) {
      const c = name === "supraspinal" ? T.supra : name === "spinal" ? T.spinal : T.reflex;
      g.append("rect").attr("x", x(f0)).attr("y", 0)
        .attr("width", x(f1) - x(f0)).attr("height", h)
        .attr("fill", c).attr("opacity", 0.07);
      g.append("text").attr("x", (x(f0) + x(f1)) / 2).attr("y", 11)
        .attr("text-anchor", "middle").attr("fill", c).attr("opacity", 0.8)
        .attr("font-size", 8).attr("font-family", SANS)
        .text(name.slice(0, 6).toUpperCase());
    }

    g.append("g").attr("transform", `translate(0,${h})`)
      .call(d3.axisBottom(x).ticks(5, "~g").tickSize(-h))
      .call((s) => {
        s.selectAll("line").attr("stroke", T.gridLine);
        s.selectAll("text").attr("fill", T.gridText).attr("font-size", 9);
        s.select(".domain").attr("stroke", T.border);
      });
    g.append("g").call(d3.axisLeft(y).ticks(4, "~e").tickSize(-w))
      .call((s) => {
        s.selectAll("line").attr("stroke", T.gridLine);
        s.selectAll("text").attr("fill", T.gridText).attr("font-size", 9);
        s.select(".domain").attr("stroke", T.border);
      });

    if (brush) {
      g.append("rect").attr("x", x(brush[0])).attr("y", 0)
        .attr("width", Math.max(1, x(brush[1]) - x(brush[0]))).attr("height", h)
        .attr("fill", T.accent).attr("opacity", 0.14);
    }

    spectra.forEach((s, i) => {
      if (!selected.has(s.arm)) return;
      const pts = s.f.map((f, k) => ({ f, p: Math.max(s.p[k], lo) }));
      const line = d3.line<{ f: number; p: number }>()
        .x((d) => x(d.f)).y((d) => y(d.p)).curve(d3.curveBasis);
      g.append("path").datum(pts).attr("d", line)
        .attr("fill", "none")
        .attr("stroke", s.closure === "open" ? T.open : color(i))
        .attr("stroke-width", 1.6)
        .attr("stroke-dasharray", s.closure === "open" ? "4,3" : "none")
        .attr("opacity", 0.9);
    });

    g.append("text").attr("x", w / 2).attr("y", h + 28)
      .attr("text-anchor", "middle").attr("fill", T.textDim)
      .attr("font-size", 10).attr("font-family", SANS).text("frequency (Hz)");
    g.append("text").attr("x", -h / 2).attr("y", -44).attr("transform", "rotate(-90)")
      .attr("text-anchor", "middle").attr("fill", T.textDim)
      .attr("font-size", 10).attr("font-family", SANS).text("power spectral density");

    const br = d3.brushX().extent([[0, 0], [w, h]]).on("end", (ev: any) => {
      if (!ev.selection) { setBrush(null); return; }
      setBrush([x.invert(ev.selection[0]), x.invert(ev.selection[1])]);
    });
    g.append("g").call(br as any)
      .selectAll(".selection").attr("fill", T.accent).attr("opacity", 0.1)
      .attr("stroke", T.accent);
  }, [spectra, selected, brush, size, T]);

  // Band powers, recomputed over the brushed range
  useEffect(() => {
    const svg = d3.select(barRef.current);
    svg.selectAll("*").remove();
    const W = size.w, H = Math.max(140, size.h * 0.40);
    const m = { top: 14, right: 16, bottom: 34, left: 58 };
    const w = W - m.left - m.right, h = H - m.top - m.bottom;
    if (w < 30 || h < 30) return;

    const g = svg.attr("width", W).attr("height", H)
      .append("g").attr("transform", `translate(${m.left},${m.top})`);

    const bands = Object.entries(STRATUM_BANDS).filter(([, [f0, f1]]) =>
      !brush || (f0 < brush[1] && f1 > brush[0]));

    const rows: { arm: string; band: string; v: number; closure: string }[] = [];
    for (const s of spectra) {
      if (!selected.has(s.arm)) continue;
      let total = 0;
      const seg: number[] = [];
      for (let i = 1; i < s.f.length; i++) {
        const a = ((s.p[i] + s.p[i - 1]) / 2) * (s.f[i] - s.f[i - 1]);
        seg.push(a); total += a;
      }
      for (const [name, [f0, f1]] of bands) {
        const lo = brush ? Math.max(f0, brush[0]) : f0;
        const hi = brush ? Math.min(f1, brush[1]) : f1;
        let acc = 0;
        for (let i = 1; i < s.f.length; i++) {
          if (s.f[i] >= lo && s.f[i] <= hi) acc += seg[i - 1];
        }
        rows.push({ arm: s.arm, band: name, v: total > 0 ? acc / total : 0, closure: s.closure });
      }
    }

    const armNames = [...new Set(rows.map((r) => r.arm))];
    const x0 = d3.scaleBand().domain(armNames).range([0, w]).padding(0.22);
    const x1 = d3.scaleBand().domain(bands.map(([n]) => n)).range([0, x0.bandwidth()]).padding(0.1);
    const y = d3.scaleLinear().domain([0, Math.max(0.05, d3.max(rows, (r) => r.v) ?? 0.3)]).nice().range([h, 0]);

    g.append("g").attr("transform", `translate(0,${h})`).call(d3.axisBottom(x0).tickSize(0))
      .call((s) => {
        s.selectAll("text").attr("fill", T.textDim).attr("font-size", 9.5).attr("font-family", MONO);
        s.select(".domain").attr("stroke", T.border);
      });
    g.append("g").call(d3.axisLeft(y).ticks(4).tickSize(-w))
      .call((s) => {
        s.selectAll("line").attr("stroke", T.gridLine);
        s.selectAll("text").attr("fill", T.gridText).attr("font-size", 9);
        s.select(".domain").attr("stroke", T.border);
      });

    const bc = (b: string) => b === "supraspinal" ? T.supra : b === "spinal" ? T.spinal : T.reflex;
    for (const r of rows) {
      g.append("rect")
        .attr("x", (x0(r.arm) ?? 0) + (x1(r.band) ?? 0))
        .attr("y", y(r.v)).attr("width", x1.bandwidth())
        .attr("height", Math.max(0, h - y(r.v)))
        .attr("fill", bc(r.band)).attr("rx", 2)
        .attr("opacity", r.closure === "open" ? 0.45 : 0.85);
    }

    g.append("text").attr("x", -h / 2).attr("y", -44).attr("transform", "rotate(-90)")
      .attr("text-anchor", "middle").attr("fill", T.textDim)
      .attr("font-size", 10).attr("font-family", SANS)
      .text(brush ? "band power (brushed)" : "band power (fraction)");
  }, [spectra, selected, brush, size, T]);

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", overflow: "hidden" }}>
      <div style={{
        padding: "6px 12px", borderBottom: `1px solid ${T.borderSoft}`,
        display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap",
        fontFamily: SANS, fontSize: 11,
      }}>
        <span style={{ color: T.textMuted, fontSize: 10, letterSpacing: 0.5 }}>ARMS</span>
        {arms.map((a, i) => (
          <label key={a.name} style={{
            display: "flex", alignItems: "center", gap: 5, cursor: "pointer",
            color: selected.has(a.name) ? (a.closure === "open" ? T.open : color(i)) : T.textMuted,
          }}>
            <input type="checkbox" checked={selected.has(a.name)}
              onChange={() => onToggle(a.name)}
              style={{ accentColor: a.closure === "open" ? T.open : color(i), width: 12, height: 12 }} />
            {a.name}
          </label>
        ))}
        {brush && (
          <span style={{ marginLeft: "auto", color: T.accent, fontFamily: MONO, fontSize: 10 }}>
            {brush[0].toFixed(2)}–{brush[1].toFixed(2)} Hz
            <span onClick={() => setBrush(null)} style={{ cursor: "pointer", marginLeft: 6 }}>✕</span>
          </span>
        )}
      </div>
      <div style={{ flex: 1, overflow: "auto" }}>
        <svg ref={psdRef} />
        <svg ref={barRef} />
      </div>
    </div>
  );
}
