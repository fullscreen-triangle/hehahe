import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import * as d3 from "d3";
import * as THREE from "three";

// ═══════════════════════════════════════════════════════════════════
// DESIGN TOKENS
// ═══════════════════════════════════════════════════════════════════
const T = {
  bg:         "#1a1b26",
  editorBg:   "#16161e",
  panelBg:    "#1f2028",
  surfaceBg:  "#24283b",
  border:     "#2f3348",
  text:       "#c0caf5",
  textDim:    "#565f89",
  textMuted:  "#3b4261",
  keyword:    "#7aa2f7",
  string:     "#9ece6a",
  comment:    "#565f89",
  number:     "#ff9e64",
  type:       "#bb9af7",
  fn:         "#7dcfff",
  accent:     "#e0af68",
  closed:     "#73daca",
  open:       "#f7768e",
  reflex:     "#bb9af7",
  spinal:     "#7dcfff",
  supra:      "#ff9e64",
  gridLine:   "#292e42",
  gridText:   "#3b4261",
  trace1:     "#7aa2f7",
  trace2:     "#f7768e",
  trace3:     "#9ece6a",
  trace4:     "#e0af68",
};

// ═══════════════════════════════════════════════════════════════════
// MOCK DATA — derived from the implementation paper's actual results
// ═══════════════════════════════════════════════════════════════════

const SAMPLE_VVS = `module postural_ablation;
import soleus_reflex;

compartment spinal_in  { capacitance: 3.0e-8 F; stratum: spinal; }
compartment cortex     { capacitance: 1.0e-3 F; stratum: supraspinal; }

circuit postural_loop {
  floor    : derived(resting_cut(spinal_in));
  outbound : cortex -> spinal_in -> alpha_mn -> nmj -> fibre;
  return   : fibre -> spindle -> ia_afferent -> spinal_in -> cortex;

  element descend   conducts cortex      -> spinal_in   delay 12.0 ms;
  element premotor  conducts spinal_in   -> alpha_mn    delay 2.0 ms;
  element mn_axon   conducts alpha_mn    -> nmj         delay 5.0 ms;
  element endplate  conducts nmj         -> fibre       delay 0.8 ms;
  element ec_couple conducts fibre       -> spindle     delay 15.0 ms;
  element mechano   conducts spindle     -> ia_afferent delay 3.0 ms;
  element ia_axon   conducts ia_afferent -> spinal_in   delay 8.0 ms
                                                        gain 1.0;
  element ascend    conducts spinal_in   -> cortex      delay 14.0 ms;
}

experiment deafferentation {
  intact  : postural_loop;

  lesion attenuated : postural_loop with ia_axon scaling 0.1;
  lesion severed    : postural_loop without element(ia_axon);
  lesion abolished  : postural_loop without return(fibre);

  observe : cop_rms, divergence_time, band_power(reflex),
            band_power(supraspinal), coupling_index;
}`;

const EXPERIMENT_RESULTS = {
  arms: [
    { name: "intact", closure: "closed", closureColor: T.closed },
    { name: "attenuated", closure: "closed", closureColor: T.closed },
    { name: "severed", closure: "open", closureColor: T.open },
    { name: "abolished", closure: "open", closureColor: T.open },
  ],
  observables: [
    { arm: "intact",     obs: "cop_rms",        value: 3.74,  unit: "mm" },
    { arm: "intact",     obs: "divergence_time", value: null,  unit: "s" },
    { arm: "intact",     obs: "band_power_reflex", value: 0.241, unit: "" },
    { arm: "intact",     obs: "band_power_supra",  value: 0.0123, unit: "" },
    { arm: "intact",     obs: "coupling_index",    value: 0.052, unit: "" },
    { arm: "attenuated", obs: "cop_rms",        value: 8.21,  unit: "mm" },
    { arm: "attenuated", obs: "divergence_time", value: null,  unit: "s" },
    { arm: "attenuated", obs: "band_power_reflex", value: 0.198, unit: "" },
    { arm: "attenuated", obs: "band_power_supra",  value: 0.0189, unit: "" },
    { arm: "attenuated", obs: "coupling_index",    value: 0.041, unit: "" },
    { arm: "severed",    obs: "cop_rms",        value: 52.1,  unit: "mm" },
    { arm: "severed",    obs: "divergence_time", value: 3.95,  unit: "s" },
    { arm: "severed",    obs: "band_power_reflex", value: 0.089, unit: "" },
    { arm: "severed",    obs: "band_power_supra",  value: 0.031, unit: "" },
    { arm: "severed",    obs: "coupling_index",    value: 0.011, unit: "" },
    { arm: "abolished",  obs: "cop_rms",        value: 58.3,  unit: "mm" },
    { arm: "abolished",  obs: "divergence_time", value: 2.81,  unit: "s" },
    { arm: "abolished",  obs: "band_power_reflex", value: 0.042, unit: "" },
    { arm: "abolished",  obs: "band_power_supra",  value: 0.038, unit: "" },
    { arm: "abolished",  obs: "coupling_index",    value: 0.006, unit: "" },
  ],
  circuit: {
    nodes: [
      { id: "cortex",      stratum: "supraspinal", x: 0.5, y: 0.05 },
      { id: "spinal_in",   stratum: "spinal",      x: 0.5, y: 0.25 },
      { id: "alpha_mn",    stratum: "reflex",       x: 0.3, y: 0.45 },
      { id: "nmj",         stratum: "reflex",       x: 0.2, y: 0.6 },
      { id: "fibre",       stratum: "reflex",       x: 0.3, y: 0.8 },
      { id: "spindle",     stratum: "reflex",       x: 0.7, y: 0.8 },
      { id: "ia_afferent", stratum: "reflex",       x: 0.8, y: 0.6 },
    ],
    outbound: ["cortex","spinal_in","alpha_mn","nmj","fibre"],
    ret: ["fibre","spindle","ia_afferent","spinal_in","cortex"],
    elements: [
      { from: "cortex",     to: "spinal_in",   name: "descend",   delay: 12.0, phase: "outbound" },
      { from: "spinal_in",  to: "alpha_mn",    name: "premotor",  delay: 2.0,  phase: "outbound" },
      { from: "alpha_mn",   to: "nmj",         name: "mn_axon",   delay: 5.0,  phase: "outbound" },
      { from: "nmj",        to: "fibre",       name: "endplate",  delay: 0.8,  phase: "outbound" },
      { from: "fibre",      to: "spindle",     name: "ec_couple", delay: 15.0, phase: "return" },
      { from: "spindle",    to: "ia_afferent", name: "mechano",   delay: 3.0,  phase: "return" },
      { from: "ia_afferent",to: "spinal_in",   name: "ia_axon",   delay: 8.0,  phase: "return" },
      { from: "spinal_in",  to: "cortex",      name: "ascend",    delay: 14.0, phase: "return" },
    ],
  },
  // Spectral data per arm
  spectra: (() => {
    const arms = ["intact","attenuated","severed","abolished"];
    const data = [];
    for (const arm of arms) {
      const isOpen = arm === "severed" || arm === "abolished";
      const isAtten = arm === "attenuated";
      for (let i = 0; i < 200; i++) {
        const f = 0.05 + (i / 200) * 4.95;
        let psd;
        if (isOpen) {
          psd = 0.003 / (f ** 1.2) + 0.0001 * Math.random();
        } else if (isAtten) {
          psd = 0.08 / (f ** 1.6) + 0.004 * Math.exp(-((f - 0.8) ** 2) / 0.08) + 0.0002 * Math.random();
        } else {
          psd = 0.12 / (f ** 1.5)
            + 0.008 * Math.exp(-((f - 0.7) ** 2) / 0.06)
            + 0.003 * Math.exp(-((f - 1.8) ** 2) / 0.3)
            + 0.0002 * Math.random();
        }
        data.push({ arm, freq: f, psd });
      }
    }
    return data;
  })(),
  // Phase portrait data (closed vs open)
  phase: (() => {
    const pts = [];
    for (let i = 0; i < 600; i++) {
      const t = i * 0.02;
      const s = 0.4 * Math.sin(2 * Math.PI * 0.7 * t + 0.3 * Math.sin(1.8 * t))
              + 0.15 * Math.sin(2 * Math.PI * 1.8 * t)
              + 0.06 * Math.sin(2 * Math.PI * 5.2 * t);
      const ds = 0.4 * 2 * Math.PI * 0.7 * Math.cos(2 * Math.PI * 0.7 * t + 0.3 * Math.sin(1.8 * t))
               + 0.15 * 2 * Math.PI * 1.8 * Math.cos(2 * Math.PI * 1.8 * t)
               + 0.06 * 2 * Math.PI * 5.2 * Math.cos(2 * Math.PI * 5.2 * t);
      pts.push({ t, s, ds, type: "closed" });
    }
    for (let i = 0; i < 200; i++) {
      const t = i * 0.02;
      const s = 0.1 * t * t + 0.2 * Math.sin(3 * t) * Math.exp(-0.3 * t);
      const ds = 0.2 * t + 0.2 * (3 * Math.cos(3 * t) * Math.exp(-0.3 * t) - 0.3 * Math.sin(3 * t) * Math.exp(-0.3 * t));
      pts.push({ t, s, ds, type: "open" });
    }
    return pts;
  })(),
  aperture: [
    { arm: "intact",     status: "closed", message: null },
    { arm: "attenuated", status: "closed", message: "ia_axon scaled to 0.1 — closure preserved (Prop. 5.1)" },
    { arm: "severed",    status: "open",   message: "APERTURE: element ia_axon removed. Circulation fibre → spindle → ia_afferent → spinal_in has no return. Prediction: perturbation admits no closed redistribution (Cor. 2.8)." },
    { arm: "abolished",  status: "open",   message: "APERTURE: return phase from fibre removed entirely. Outbound cortex → … → fibre has no return. Prediction: movement fails to resolve, not increased variance about preserved trajectory." },
  ],
  diagnostics: [
    { level: "info",    msg: "Module postural_ablation loaded" },
    { level: "info",    msg: "Import soleus_reflex resolved" },
    { level: "info",    msg: "Circuit postural_loop: floor β = 0.0042 > 0 ✓" },
    { level: "info",    msg: "Stratum containment: all elements adjacent ✓" },
    { level: "info",    msg: "Compartment consistency: no mixed indices ✓" },
    { level: "warn",    msg: "Arm severed: closure index = open" },
    { level: "warn",    msg: "Arm abolished: closure index = open" },
    { level: "info",    msg: "Experiment deafferentation: 4 arms, 20 observations" },
    { level: "success", msg: "All 20 observations discharged in 24 steps" },
  ],
};

// ═══════════════════════════════════════════════════════════════════
// SYNTAX HIGHLIGHTER for .vvs
// ═══════════════════════════════════════════════════════════════════
const KEYWORDS = new Set([
  "circuit","outbound","return","compartment","capacitance","element",
  "conducts","stratum","delay","gain","floor","derived","event","type",
  "experiment","intact","lesion","observe","without","with","scaling",
  "noise","across","compare","report","let","module","import","reflex",
  "spinal","supraspinal","reroute","through","phase","template",
  "bilateral","antagonist","agonist","shared","failure",
]);

function highlightVVS(code) {
  const lines = code.split("\n");
  return lines.map((line, li) => {
    const parts = [];
    let i = 0;
    while (i < line.length) {
      if (line.substring(i, i + 2) === "--") {
        parts.push(<span key={`${li}-${i}`} style={{ color: T.comment, fontStyle: "italic" }}>{line.substring(i)}</span>);
        i = line.length;
      } else if (line[i] === '"') {
        let j = i + 1;
        while (j < line.length && line[j] !== '"') j++;
        parts.push(<span key={`${li}-${i}`} style={{ color: T.string }}>{line.substring(i, j + 1)}</span>);
        i = j + 1;
      } else if (/[0-9]/.test(line[i]) && (i === 0 || !/[A-Za-z_]/.test(line[i - 1]))) {
        let j = i;
        while (j < line.length && /[0-9.eE\-+]/.test(line[j])) j++;
        while (j < line.length && /[a-zA-Z/]/.test(line[j])) j++;
        parts.push(<span key={`${li}-${i}`} style={{ color: T.number }}>{line.substring(i, j)}</span>);
        i = j;
      } else if (/[A-Za-z_]/.test(line[i])) {
        let j = i;
        while (j < line.length && /[A-Za-z0-9_]/.test(line[j])) j++;
        const word = line.substring(i, j);
        if (KEYWORDS.has(word)) {
          parts.push(<span key={`${li}-${i}`} style={{ color: T.keyword, fontWeight: 600 }}>{word}</span>);
        } else {
          parts.push(<span key={`${li}-${i}`} style={{ color: T.text }}>{word}</span>);
        }
        i = j;
      } else if (line.substring(i, i + 2) === "->") {
        parts.push(<span key={`${li}-${i}`} style={{ color: T.accent }}>-&gt;</span>);
        i += 2;
      } else {
        parts.push(<span key={`${li}-${i}`} style={{ color: T.textDim }}>{line[i]}</span>);
        i++;
      }
    }
    return parts;
  });
}

// ═══════════════════════════════════════════════════════════════════
// EDITOR COMPONENT
// ═══════════════════════════════════════════════════════════════════
function VVSEditor({ code, onChange }) {
  const textareaRef = useRef(null);
  const preRef = useRef(null);
  const lineCount = code.split("\n").length;
  const highlighted = useMemo(() => highlightVVS(code), [code]);

  const syncScroll = () => {
    if (textareaRef.current && preRef.current) {
      preRef.current.scrollTop = textareaRef.current.scrollTop;
      preRef.current.scrollLeft = textareaRef.current.scrollLeft;
    }
  };

  return (
    <div style={{ position: "relative", height: "100%", background: T.editorBg, fontFamily: "'Cascadia Code', 'Fira Code', 'JetBrains Mono', monospace", fontSize: 13, lineHeight: "20px" }}>
      <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: 48, background: T.editorBg, borderRight: `1px solid ${T.border}`, zIndex: 2, overflow: "hidden" }}>
        <div style={{ paddingTop: 12 }}>
          {Array.from({ length: lineCount }, (_, i) => (
            <div key={i} style={{ height: 20, textAlign: "right", paddingRight: 12, color: T.textMuted, fontSize: 11, userSelect: "none" }}>
              {i + 1}
            </div>
          ))}
        </div>
      </div>
      <pre ref={preRef} style={{ position: "absolute", left: 48, top: 0, right: 0, bottom: 0, margin: 0, padding: 12, overflow: "auto", whiteSpace: "pre", pointerEvents: "none", zIndex: 1 }}>
        {highlighted.map((lineParts, i) => (
          <div key={i} style={{ height: 20 }}>{lineParts.length ? lineParts : " "}</div>
        ))}
      </pre>
      <textarea
        ref={textareaRef}
        value={code}
        onChange={e => onChange(e.target.value)}
        onScroll={syncScroll}
        spellCheck={false}
        style={{
          position: "absolute", left: 48, top: 0, right: 0, bottom: 0,
          margin: 0, padding: 12, border: "none", outline: "none",
          background: "transparent", color: "transparent", caretColor: T.text,
          fontFamily: "inherit", fontSize: "inherit", lineHeight: "inherit",
          resize: "none", whiteSpace: "pre", overflow: "auto", zIndex: 3,
        }}
      />
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// CIRCUIT TOPOLOGY (D3)
// ═══════════════════════════════════════════════════════════════════
function CircuitView({ data, selectedArm }) {
  const svgRef = useRef(null);
  const { nodes, elements } = data.circuit;
  const armData = data.arms.find(a => a.name === selectedArm);
  const aperture = data.aperture.find(a => a.arm === selectedArm);
  const isOpen = aperture?.status === "open";

  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();
    const w = svgRef.current.clientWidth || 500;
    const h = svgRef.current.clientHeight || 400;
    const g = svg.append("g");

    const stratumColor = s => s === "supraspinal" ? T.supra : s === "spinal" ? T.spinal : T.reflex;
    const stratumY = s => s === "supraspinal" ? 0.12 : s === "spinal" ? 0.35 : 0.7;

    // stratum bands
    const bands = [
      { label: "supraspinal", y1: 0, y2: 0.22, color: T.supra },
      { label: "spinal", y1: 0.22, y2: 0.48, color: T.spinal },
      { label: "reflex", y1: 0.48, y2: 1.0, color: T.reflex },
    ];
    bands.forEach(b => {
      g.append("rect")
        .attr("x", 0).attr("y", b.y1 * h).attr("width", w).attr("height", (b.y2 - b.y1) * h)
        .attr("fill", b.color).attr("opacity", 0.04);
      g.append("text")
        .attr("x", 14).attr("y", b.y1 * h + 18)
        .attr("fill", b.color).attr("opacity", 0.4).attr("font-size", 10)
        .attr("font-family", "inherit")
        .text(b.label);
    });

    // edges
    elements.forEach(el => {
      const from = nodes.find(n => n.id === el.from);
      const to = nodes.find(n => n.id === el.to);
      if (!from || !to) return;
      const isSevered = isOpen && el.name === "ia_axon" && selectedArm === "severed";
      const isReturnRemoved = isOpen && el.phase === "return" && selectedArm === "abolished";
      const dim = isSevered || isReturnRemoved;
      g.append("line")
        .attr("x1", from.x * w).attr("y1", from.y * h)
        .attr("x2", to.x * w).attr("y2", to.y * h)
        .attr("stroke", dim ? T.open : el.phase === "outbound" ? T.trace1 : T.trace3)
        .attr("stroke-width", dim ? 1 : 2)
        .attr("stroke-dasharray", dim ? "4,4" : "none")
        .attr("opacity", dim ? 0.4 : 0.8);

      // delay label
      const mx = (from.x + to.x) / 2 * w;
      const my = (from.y + to.y) / 2 * h;
      g.append("text")
        .attr("x", mx + 8).attr("y", my - 4)
        .attr("fill", dim ? T.textMuted : T.textDim).attr("font-size", 9)
        .attr("font-family", "inherit")
        .text(`${el.delay}ms`);
    });

    // arrow markers
    elements.forEach(el => {
      const from = nodes.find(n => n.id === el.from);
      const to = nodes.find(n => n.id === el.to);
      if (!from || !to) return;
      const isSevered = isOpen && el.name === "ia_axon" && selectedArm === "severed";
      const isReturnRemoved = isOpen && el.phase === "return" && selectedArm === "abolished";
      if (isSevered || isReturnRemoved) return;
      const dx = to.x * w - from.x * w;
      const dy = to.y * h - from.y * h;
      const len = Math.sqrt(dx * dx + dy * dy);
      const ux = dx / len;
      const uy = dy / len;
      const ax = to.x * w - ux * 18;
      const ay = to.y * h - uy * 18;
      const col = el.phase === "outbound" ? T.trace1 : T.trace3;
      g.append("polygon")
        .attr("points", `${ax},${ay} ${ax - ux * 6 + uy * 3},${ay - uy * 6 - ux * 3} ${ax - ux * 6 - uy * 3},${ay - uy * 6 + ux * 3}`)
        .attr("fill", col).attr("opacity", 0.8);
    });

    // nodes
    nodes.forEach(n => {
      g.append("circle")
        .attr("cx", n.x * w).attr("cy", n.y * h).attr("r", 14)
        .attr("fill", T.surfaceBg).attr("stroke", stratumColor(n.stratum))
        .attr("stroke-width", 2);
      g.append("text")
        .attr("x", n.x * w).attr("y", n.y * h + 4)
        .attr("text-anchor", "middle").attr("fill", T.text)
        .attr("font-size", 8).attr("font-family", "inherit")
        .text(n.id.length > 8 ? n.id.substring(0, 7) + "…" : n.id);
    });

  }, [data, selectedArm, isOpen, nodes, elements]);

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <div style={{ padding: "8px 12px", borderBottom: `1px solid ${T.border}`, display: "flex", gap: 8, alignItems: "center" }}>
        {data.arms.map(a => (
          <span key={a.name} style={{
            padding: "2px 10px", borderRadius: 3, fontSize: 11, cursor: "pointer",
            background: selectedArm === a.name ? T.surfaceBg : "transparent",
            color: a.closureColor, border: `1px solid ${selectedArm === a.name ? a.closureColor : "transparent"}`,
          }} onClick={() => {}}>
            {a.closure === "open" ? "◇" : "●"} {a.name}
          </span>
        ))}
      </div>
      {aperture?.message && (
        <div style={{ padding: "6px 12px", background: isOpen ? `${T.open}11` : `${T.closed}11`, borderBottom: `1px solid ${T.border}`, fontSize: 11, color: isOpen ? T.open : T.closed, fontFamily: "monospace" }}>
          {aperture.message}
        </div>
      )}
      <svg ref={svgRef} style={{ flex: 1, width: "100%" }} />
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// SPECTRAL VIEW with D3 CROSSFILTER
// ═══════════════════════════════════════════════════════════════════
function SpectralView({ data }) {
  const psdRef = useRef(null);
  const barRef = useRef(null);
  const [brushRange, setBrushRange] = useState(null);
  const [selectedArms, setSelectedArms] = useState(new Set(data.arms.map(a => a.name)));

  const armColors = { intact: T.trace1, attenuated: T.trace3, severed: T.open, abolished: T.accent };
  const bandRanges = { supraspinal: [0.05, 0.3], spinal: [0.3, 1.0], reflex: [1.0, 3.0] };

  // PSD chart
  useEffect(() => {
    if (!psdRef.current) return;
    const svg = d3.select(psdRef.current);
    svg.selectAll("*").remove();
    const margin = { top: 12, right: 16, bottom: 32, left: 52 };
    const w = (psdRef.current.clientWidth || 460) - margin.left - margin.right;
    const h = (psdRef.current.clientHeight || 220) - margin.top - margin.bottom;
    const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);

    const x = d3.scaleLog().domain([0.05, 5]).range([0, w]);
    const y = d3.scaleLog().domain([0.0001, 0.2]).range([h, 0]);

    // grid
    g.append("g").call(d3.axisBottom(x).ticks(5, ".2f").tickSize(-h))
      .attr("transform", `translate(0,${h})`).call(g => {
        g.selectAll("line").attr("stroke", T.gridLine);
        g.selectAll("text").attr("fill", T.gridText).attr("font-size", 9);
        g.select(".domain").attr("stroke", T.border);
      });
    g.append("g").call(d3.axisLeft(y).ticks(4, ".0e").tickSize(-w))
      .call(g => {
        g.selectAll("line").attr("stroke", T.gridLine);
        g.selectAll("text").attr("fill", T.gridText).attr("font-size", 9);
        g.select(".domain").attr("stroke", T.border);
      });

    // band shading
    Object.entries(bandRanges).forEach(([name, [f0, f1]]) => {
      const col = name === "supraspinal" ? T.supra : name === "spinal" ? T.spinal : T.reflex;
      g.append("rect")
        .attr("x", x(f0)).attr("y", 0)
        .attr("width", x(f1) - x(f0)).attr("height", h)
        .attr("fill", col).attr("opacity", 0.06);
    });

    // brush range highlight
    if (brushRange) {
      g.append("rect")
        .attr("x", x(brushRange[0])).attr("y", 0)
        .attr("width", x(brushRange[1]) - x(brushRange[0])).attr("height", h)
        .attr("fill", T.accent).attr("opacity", 0.12);
    }

    // traces
    const grouped = d3.group(data.spectra, d => d.arm);
    grouped.forEach((pts, arm) => {
      if (!selectedArms.has(arm)) return;
      const line = d3.line()
        .x(d => x(d.freq)).y(d => y(Math.max(0.0001, d.psd)))
        .curve(d3.curveBasis);
      g.append("path")
        .datum(pts)
        .attr("d", line)
        .attr("fill", "none")
        .attr("stroke", armColors[arm])
        .attr("stroke-width", 1.5)
        .attr("opacity", 0.85);
    });

    // labels
    g.append("text").attr("x", w / 2).attr("y", h + 28)
      .attr("text-anchor", "middle").attr("fill", T.textDim).attr("font-size", 10).text("Frequency (Hz)");
    g.append("text").attr("x", -h / 2).attr("y", -38)
      .attr("text-anchor", "middle").attr("fill", T.textDim).attr("font-size", 10)
      .attr("transform", "rotate(-90)").text("PSD");

    // brush
    const brush = d3.brushX()
      .extent([[0, 0], [w, h]])
      .on("end", (event) => {
        if (!event.selection) { setBrushRange(null); return; }
        setBrushRange([x.invert(event.selection[0]), x.invert(event.selection[1])]);
      });
    g.append("g").call(brush).selectAll("rect").attr("fill", T.accent).attr("opacity", 0.08);

  }, [data.spectra, selectedArms, brushRange]);

  // Bar chart — band power filtered by brush
  useEffect(() => {
    if (!barRef.current) return;
    const svg = d3.select(barRef.current);
    svg.selectAll("*").remove();
    const margin = { top: 12, right: 16, bottom: 48, left: 52 };
    const w = (barRef.current.clientWidth || 460) - margin.left - margin.right;
    const h = (barRef.current.clientHeight || 180) - margin.top - margin.bottom;
    const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);

    const bandNames = Object.keys(bandRanges);
    const filteredBands = brushRange
      ? bandNames.filter(b => {
          const [f0, f1] = bandRanges[b];
          return f0 < brushRange[1] && f1 > brushRange[0];
        })
      : bandNames;

    const barData = [];
    data.arms.forEach(arm => {
      if (!selectedArms.has(arm.name)) return;
      filteredBands.forEach(band => {
        const obs = data.observables.find(o => o.arm === arm.name && o.obs === `band_power_${band === "supraspinal" ? "supra" : band}`);
        if (obs) barData.push({ arm: arm.name, band, value: obs.value });
      });
    });

    const x0 = d3.scaleBand().domain([...selectedArms]).range([0, w]).padding(0.2);
    const x1 = d3.scaleBand().domain(filteredBands).range([0, x0.bandwidth()]).padding(0.08);
    const y = d3.scaleLinear().domain([0, d3.max(barData, d => d.value) || 0.3]).nice().range([h, 0]);

    g.append("g").attr("transform", `translate(0,${h})`)
      .call(d3.axisBottom(x0).tickSize(0))
      .call(g => { g.selectAll("text").attr("fill", T.textDim).attr("font-size", 10); g.select(".domain").attr("stroke", T.border); });
    g.append("g").call(d3.axisLeft(y).ticks(4).tickSize(-w))
      .call(g => { g.selectAll("line").attr("stroke", T.gridLine); g.selectAll("text").attr("fill", T.gridText).attr("font-size", 9); g.select(".domain").attr("stroke", T.border); });

    const bandColor = b => b === "supraspinal" ? T.supra : b === "spinal" ? T.spinal : T.reflex;

    barData.forEach(d => {
      g.append("rect")
        .attr("x", x0(d.arm) + x1(d.band))
        .attr("y", y(d.value))
        .attr("width", x1.bandwidth())
        .attr("height", h - y(d.value))
        .attr("fill", bandColor(d.band))
        .attr("opacity", 0.75)
        .attr("rx", 2);
    });

    g.append("text").attr("x", w / 2).attr("y", h + 38)
      .attr("text-anchor", "middle").attr("fill", T.textDim).attr("font-size", 10).text("Band power by arm");

  }, [data, selectedArms, brushRange]);

  const toggleArm = (arm) => {
    setSelectedArms(prev => {
      const next = new Set(prev);
      if (next.has(arm)) next.delete(arm); else next.add(arm);
      return next;
    });
  };

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <div style={{ padding: "6px 12px", borderBottom: `1px solid ${T.border}`, display: "flex", gap: 12, alignItems: "center" }}>
        <span style={{ fontSize: 10, color: T.textDim, marginRight: 4 }}>ARMS</span>
        {data.arms.map(a => (
          <label key={a.name} style={{ fontSize: 11, color: selectedArms.has(a.name) ? armColors[a.name] : T.textMuted, cursor: "pointer", display: "flex", alignItems: "center", gap: 4 }}>
            <input type="checkbox" checked={selectedArms.has(a.name)} onChange={() => toggleArm(a.name)} style={{ accentColor: armColors[a.name] }} />
            {a.name}
          </label>
        ))}
        {brushRange && (
          <span style={{ fontSize: 10, color: T.accent, marginLeft: "auto" }}>
            Brush: {brushRange[0].toFixed(2)}–{brushRange[1].toFixed(2)} Hz
            <span style={{ cursor: "pointer", marginLeft: 6 }} onClick={() => setBrushRange(null)}>✕</span>
          </span>
        )}
      </div>
      <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        <svg ref={psdRef} style={{ flex: 1, width: "100%", minHeight: 200 }} />
        <svg ref={barRef} style={{ height: 180, width: "100%" }} />
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// PHASE PORTRAIT (Three.js)
// ═══════════════════════════════════════════════════════════════════
function PhaseView({ data }) {
  const mountRef = useRef(null);
  const frameRef = useRef(null);

  useEffect(() => {
    const el = mountRef.current;
    if (!el) return;
    const w = el.clientWidth || 500;
    const h = el.clientHeight || 400;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(T.panelBg);

    const camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 100);
    camera.position.set(3, 2, 4);
    camera.lookAt(0, 0, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(w, h);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    el.appendChild(renderer.domElement);

    // axis lines
    const axisMat = new THREE.LineBasicMaterial({ color: T.border });
    [[[0, 0, 0], [2.5, 0, 0]], [[0, 0, 0], [0, 2, 0]], [[0, 0, 0], [0, 0, 2.5]]].forEach(([a, b]) => {
      const geo = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(...a), new THREE.Vector3(...b)]);
      scene.add(new THREE.Line(geo, axisMat));
    });

    // grid floor
    const gridGeo = new THREE.BufferGeometry();
    const gridPts = [];
    for (let i = -2; i <= 2; i += 0.5) {
      gridPts.push(-2, 0, i, 2, 0, i, i, 0, -2, i, 0, 2);
    }
    gridGeo.setAttribute("position", new THREE.Float32BufferAttribute(gridPts, 3));
    scene.add(new THREE.LineSegments(gridGeo, new THREE.LineBasicMaterial({ color: T.gridLine, transparent: true, opacity: 0.3 })));

    // closed trajectory
    const closedPts = data.phase.filter(p => p.type === "closed");
    const closedGeo = new THREE.BufferGeometry();
    const closedPos = new Float32Array(closedPts.length * 3);
    const closedCol = new Float32Array(closedPts.length * 3);
    const cScale = d3.scaleSequential(d3.interpolateViridis).domain([0, closedPts.length]);
    closedPts.forEach((p, i) => {
      closedPos[i * 3] = p.s * 2;
      closedPos[i * 3 + 1] = p.ds * 0.15;
      closedPos[i * 3 + 2] = (p.t / 12) * 4 - 2;
      const c = new THREE.Color(cScale(i));
      closedCol[i * 3] = c.r;
      closedCol[i * 3 + 1] = c.g;
      closedCol[i * 3 + 2] = c.b;
    });
    closedGeo.setAttribute("position", new THREE.Float32BufferAttribute(closedPos, 3));
    closedGeo.setAttribute("color", new THREE.Float32BufferAttribute(closedCol, 3));
    scene.add(new THREE.Line(closedGeo, new THREE.LineBasicMaterial({ vertexColors: true, linewidth: 1 })));

    // open trajectory
    const openPts = data.phase.filter(p => p.type === "open");
    const openGeo = new THREE.BufferGeometry();
    const openPos = new Float32Array(openPts.length * 3);
    openPts.forEach((p, i) => {
      openPos[i * 3] = p.s * 0.3;
      openPos[i * 3 + 1] = p.ds * 0.15;
      openPos[i * 3 + 2] = (p.t / 4) * 4 - 2;
    });
    openGeo.setAttribute("position", new THREE.Float32BufferAttribute(openPos, 3));
    scene.add(new THREE.Line(openGeo, new THREE.LineBasicMaterial({ color: T.open, linewidth: 1 })));

    // ambient
    scene.add(new THREE.AmbientLight(0xffffff, 0.6));

    // rotation
    let angle = 0;
    let isDragging = false;
    let lastX = 0;

    const onDown = e => { isDragging = true; lastX = e.clientX || e.touches?.[0]?.clientX || 0; };
    const onMove = e => { if (!isDragging) return; const x = e.clientX || e.touches?.[0]?.clientX || 0; angle += (x - lastX) * 0.005; lastX = x; };
    const onUp = () => { isDragging = false; };
    renderer.domElement.addEventListener("mousedown", onDown);
    renderer.domElement.addEventListener("mousemove", onMove);
    renderer.domElement.addEventListener("mouseup", onUp);
    renderer.domElement.addEventListener("touchstart", onDown);
    renderer.domElement.addEventListener("touchmove", onMove);
    renderer.domElement.addEventListener("touchend", onUp);

    const animate = () => {
      frameRef.current = requestAnimationFrame(animate);
      if (!isDragging) angle += 0.003;
      camera.position.set(5 * Math.sin(angle), 2.5, 5 * Math.cos(angle));
      camera.lookAt(0, 0, 0);
      renderer.render(scene, camera);
    };
    animate();

    return () => {
      cancelAnimationFrame(frameRef.current);
      renderer.dispose();
      if (el.contains(renderer.domElement)) el.removeChild(renderer.domElement);
    };
  }, [data.phase]);

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <div style={{ padding: "6px 12px", borderBottom: `1px solid ${T.border}`, fontSize: 10, color: T.textDim }}>
        <span style={{ color: T.trace1 }}>● closed trajectory</span>
        <span style={{ marginLeft: 16, color: T.open }}>● open trajectory (diverges)</span>
        <span style={{ marginLeft: 16, color: T.textMuted }}>drag to rotate</span>
      </div>
      <div ref={mountRef} style={{ flex: 1 }} />
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// RESULTS TABLE
// ═══════════════════════════════════════════════════════════════════
function ResultsView({ data }) {
  const obsByArm = d3.group(data.observables, d => d.arm);
  const obsNames = [...new Set(data.observables.map(d => d.obs))];
  return (
    <div style={{ height: "100%", overflow: "auto", padding: 12 }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, fontFamily: "monospace" }}>
        <thead>
          <tr style={{ borderBottom: `1px solid ${T.border}` }}>
            <th style={{ textAlign: "left", padding: "6px 8px", color: T.textDim, fontWeight: 500 }}>observable</th>
            {data.arms.map(a => (
              <th key={a.name} style={{ textAlign: "right", padding: "6px 8px", color: a.closureColor, fontWeight: 500 }}>
                {a.closure === "open" ? "◇" : "●"} {a.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {obsNames.map(obs => (
            <tr key={obs} style={{ borderBottom: `1px solid ${T.border}22` }}>
              <td style={{ padding: "4px 8px", color: T.text }}>{obs}</td>
              {data.arms.map(a => {
                const d = data.observables.find(o => o.arm === a.name && o.obs === obs);
                return (
                  <td key={a.name} style={{ textAlign: "right", padding: "4px 8px", color: d?.value == null ? T.textMuted : T.text, fontVariantNumeric: "tabular-nums" }}>
                    {d?.value == null ? "—" : typeof d.value === "number" ? d.value.toFixed(d.value < 0.1 ? 4 : 2) : d.value}
                    {d?.unit ? <span style={{ color: T.textMuted, marginLeft: 2 }}>{d.unit}</span> : null}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// APERTURE REPORT VIEW
// ═══════════════════════════════════════════════════════════════════
function ApertureView({ data }) {
  return (
    <div style={{ height: "100%", overflow: "auto", padding: 16 }}>
      {data.aperture.map((a, i) => (
        <div key={i} style={{
          marginBottom: 12, padding: "10px 14px", borderRadius: 4,
          border: `1px solid ${a.status === "open" ? T.open : T.closed}33`,
          background: a.status === "open" ? `${T.open}08` : `${T.closed}08`,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <span style={{ color: a.status === "open" ? T.open : T.closed, fontWeight: 600, fontSize: 13 }}>
              {a.status === "open" ? "◇ OPEN" : "● CLOSED"}
            </span>
            <span style={{ color: T.text, fontSize: 13 }}>{a.arm}</span>
          </div>
          {a.message && (
            <div style={{ color: a.status === "open" ? T.open : T.closed, fontSize: 11, fontFamily: "monospace", lineHeight: 1.5, opacity: 0.85 }}>
              {a.message}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// DIAGNOSTICS FOOTER
// ═══════════════════════════════════════════════════════════════════
function DiagnosticsBar({ diagnostics }) {
  const icons = { info: "○", warn: "△", success: "✓", error: "✕" };
  const colors = { info: T.textDim, warn: T.accent, success: T.closed, error: T.open };
  return (
    <div style={{ height: 120, borderTop: `1px solid ${T.border}`, background: T.editorBg, overflow: "auto", padding: "6px 12px", fontFamily: "monospace", fontSize: 11, lineHeight: 1.7 }}>
      {diagnostics.map((d, i) => (
        <div key={i} style={{ color: colors[d.level] }}>
          <span style={{ marginRight: 6 }}>{icons[d.level]}</span>
          {d.msg}
        </div>
      ))}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// MAIN IDE
// ═══════════════════════════════════════════════════════════════════
const TABS = [
  { id: "circuit",  label: "Circuit" },
  { id: "spectra",  label: "Spectra" },
  { id: "phase",    label: "Phase" },
  { id: "results",  label: "Results" },
  { id: "aperture", label: "Aperture" },
];

export default function VitruviusIDE() {
  const [code, setCode] = useState(SAMPLE_VVS);
  const [activeTab, setActiveTab] = useState("circuit");
  const [selectedArm, setSelectedArm] = useState("intact");
  const [hasRun, setHasRun] = useState(false);
  const [splitPos, setSplitPos] = useState(0.42);
  const [isDraggingSplit, setIsDraggingSplit] = useState(false);
  const containerRef = useRef(null);
  const data = EXPERIMENT_RESULTS;

  const handleRun = () => setHasRun(true);

  useEffect(() => {
    if (!isDraggingSplit) return;
    const onMove = e => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width;
      setSplitPos(Math.max(0.2, Math.min(0.7, x)));
    };
    const onUp = () => setIsDraggingSplit(false);
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => { window.removeEventListener("mousemove", onMove); window.removeEventListener("mouseup", onUp); };
  }, [isDraggingSplit]);

  return (
    <div ref={containerRef} style={{ width: "100%", height: "100vh", display: "flex", flexDirection: "column", background: T.bg, color: T.text, fontFamily: "'Inter', -apple-system, sans-serif", overflow: "hidden" }}>
      {/* Title bar */}
      <div style={{ height: 36, background: T.editorBg, borderBottom: `1px solid ${T.border}`, display: "flex", alignItems: "center", padding: "0 12px", gap: 12, flexShrink: 0 }}>
        <span style={{ fontSize: 12, fontWeight: 600, color: T.keyword, letterSpacing: 1 }}>VITRUVIUS</span>
        <span style={{ fontSize: 11, color: T.textDim }}>postural_ablation.vvs</span>
        <div style={{ flex: 1 }} />
        <button onClick={handleRun} style={{
          background: hasRun ? T.closed : T.keyword, color: T.editorBg, border: "none",
          padding: "3px 14px", borderRadius: 3, fontSize: 11, fontWeight: 600, cursor: "pointer",
          fontFamily: "inherit",
        }}>
          {hasRun ? "✓ Run complete" : "▶ Run experiment"}
        </button>
      </div>

      {/* Main area */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        {/* Editor */}
        <div style={{ width: `${splitPos * 100}%`, minWidth: 200, overflow: "hidden" }}>
          <VVSEditor code={code} onChange={setCode} />
        </div>

        {/* Splitter */}
        <div
          onMouseDown={() => setIsDraggingSplit(true)}
          style={{ width: 4, background: isDraggingSplit ? T.keyword : T.border, cursor: "col-resize", flexShrink: 0, transition: "background 0.15s" }}
        />

        {/* Output */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          {hasRun ? (
            <>
              {/* Tab bar */}
              <div style={{ display: "flex", borderBottom: `1px solid ${T.border}`, background: T.editorBg, flexShrink: 0 }}>
                {TABS.map(tab => (
                  <button key={tab.id} onClick={() => setActiveTab(tab.id)} style={{
                    padding: "7px 16px", border: "none", borderBottom: `2px solid ${activeTab === tab.id ? T.keyword : "transparent"}`,
                    background: "transparent", color: activeTab === tab.id ? T.text : T.textDim,
                    fontSize: 11, fontWeight: activeTab === tab.id ? 600 : 400, cursor: "pointer", fontFamily: "inherit",
                  }}>
                    {tab.label}
                  </button>
                ))}
                {activeTab === "circuit" && (
                  <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", padding: "0 8px", gap: 6 }}>
                    {data.arms.map(a => (
                      <span key={a.name} onClick={() => setSelectedArm(a.name)} style={{
                        padding: "1px 8px", borderRadius: 3, fontSize: 10, cursor: "pointer",
                        background: selectedArm === a.name ? T.surfaceBg : "transparent",
                        color: a.closureColor, border: `1px solid ${selectedArm === a.name ? a.closureColor + "66" : "transparent"}`,
                      }}>
                        {a.name}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Tab content */}
              <div style={{ flex: 1, overflow: "hidden" }}>
                {activeTab === "circuit" && <CircuitView data={data} selectedArm={selectedArm} />}
                {activeTab === "spectra" && <SpectralView data={data} />}
                {activeTab === "phase" && <PhaseView data={data} />}
                {activeTab === "results" && <ResultsView data={data} />}
                {activeTab === "aperture" && <ApertureView data={data} />}
              </div>
            </>
          ) : (
            <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 12 }}>
              <div style={{ fontSize: 48, opacity: 0.15 }}>◇</div>
              <div style={{ fontSize: 13, color: T.textMuted }}>Press <span style={{ color: T.keyword, fontWeight: 600 }}>▶ Run experiment</span> to compile and execute</div>
              <div style={{ fontSize: 11, color: T.textMuted, maxWidth: 320, textAlign: "center", lineHeight: 1.5 }}>
                Static analyses (closure, compartment, stratum, floor) run at compile time. Backend integration runs on execution.
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Diagnostics */}
      {hasRun && <DiagnosticsBar diagnostics={data.diagnostics} />}
    </div>
  );
}