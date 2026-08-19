/**
 * Three-dimensional state-space view: (state, d(state)/dt, time) for each
 * selected arm, plotted from the real integrator.
 *
 * A closed circulation traces a bounded tube and never approaches a fixed
 * point; an open one leaves the region. That contrast is the geometric
 * content of "no static equilibrium", so it is worth seeing rotated rather
 * than projected.
 */

import { useEffect, useRef } from "react";
import * as THREE from "three";
import type { Backend } from "../lang/backend";
import type { ArmResult } from "../lang/runtime";
import { SANS, type Theme } from "../theme";

interface Props {
  arms: ArmResult[];
  backend: Backend;
  theme: Theme;
  selected: Set<string>;
}

export function PhaseView({ arms, backend, theme: T, selected }: Props) {
  const mount = useRef<HTMLDivElement>(null);
  const frame = useRef<number>(0);

  useEffect(() => {
    const el = mount.current;
    if (!el) return;
    const w = el.clientWidth || 600;
    const h = el.clientHeight || 420;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(T.panelBg);

    const camera = new THREE.PerspectiveCamera(42, w / h, 0.1, 200);
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(w, h);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    el.appendChild(renderer.domElement);

    // axes + floor grid
    const axisMat = new THREE.LineBasicMaterial({ color: new THREE.Color(T.border) });
    const axes: [number[], number[]][] = [
      [[-2.4, 0, 0], [2.4, 0, 0]],
      [[0, -1.6, 0], [0, 1.6, 0]],
      [[0, 0, -2.4], [0, 0, 2.4]],
    ];
    for (const [a, b] of axes) {
      const geo = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(...(a as [number, number, number])),
        new THREE.Vector3(...(b as [number, number, number])),
      ]);
      scene.add(new THREE.Line(geo, axisMat));
    }
    const gridPts: number[] = [];
    for (let i = -2; i <= 2; i += 0.5) {
      gridPts.push(-2, -1.6, i, 2, -1.6, i, i, -1.6, -2, i, -1.6, 2);
    }
    const gg = new THREE.BufferGeometry();
    gg.setAttribute("position", new THREE.Float32BufferAttribute(gridPts, 3));
    scene.add(new THREE.LineSegments(gg, new THREE.LineBasicMaterial({
      color: new THREE.Color(T.gridLine), transparent: true, opacity: 0.45,
    })));

    // trajectories
    const chosen = arms.filter((a) => selected.has(a.name));
    chosen.forEach((arm, idx) => {
      const raw = backend.sum(arm.circuit);

      /**
       * The raw trace is integrator-step noise on top of the loop dynamics,
       * and its point-to-point derivative is almost pure noise. Plotting it
       * directly fills the volume and hides the structure the view exists
       * to show, so smooth before differentiating and decimate to a
       * legible number of vertices.
       */
      const SMOOTH = 24;
      const smoothed = new Float64Array(raw.length);
      let acc = 0;
      for (let i = 0; i < raw.length; i++) {
        acc += raw[i];
        if (i >= SMOOTH) acc -= raw[i - SMOOTH];
        smoothed[i] = acc / Math.min(i + 1, SMOOTH);
      }

      const STRIDE = Math.max(1, Math.floor(smoothed.length / 1400));
      const n = Math.floor(smoothed.length / STRIDE);
      const dt = backend.dt * STRIDE;

      // Normalise each arm to its own scale so a diverging arm does not
      // flatten the others into a line.
      let peak = 1e-9, dpeak = 1e-9;
      const v = new Float64Array(n), d = new Float64Array(n);
      for (let i = 0; i < n; i++) {
        v[i] = smoothed[i * STRIDE];
        peak = Math.max(peak, Math.abs(v[i]));
      }
      for (let i = 1; i < n; i++) {
        d[i] = (v[i] - v[i - 1]) / dt;
        dpeak = Math.max(dpeak, Math.abs(d[i]));
      }

      const pos = new Float32Array(n * 3);
      const col = new Float32Array(n * 3);
      const base = new THREE.Color(
        arm.closure === "open" ? T.open : T.series[idx % T.series.length],
      );
      for (let i = 0; i < n; i++) {
        pos[i * 3] = (v[i] / peak) * 2.1;
        pos[i * 3 + 1] = (d[i] / dpeak) * 1.4;
        pos[i * 3 + 2] = (i / n) * 4.4 - 2.2;
        const shade = 0.45 + 0.55 * (i / n);
        col[i * 3] = base.r * shade;
        col[i * 3 + 1] = base.g * shade;
        col[i * 3 + 2] = base.b * shade;
      }
      const geo = new THREE.BufferGeometry();
      geo.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
      geo.setAttribute("color", new THREE.Float32BufferAttribute(col, 3));
      scene.add(new THREE.Line(geo, new THREE.LineBasicMaterial({
        vertexColors: true, transparent: true,
        opacity: arm.closure === "open" ? 0.95 : 0.8,
      })));
    });

    scene.add(new THREE.AmbientLight(0xffffff, 0.7));

    let angle = 0.6;
    let elev = 0.42;
    let drag = false;
    let lx = 0, ly = 0;

    const down = (e: MouseEvent) => { drag = true; lx = e.clientX; ly = e.clientY; };
    const move = (e: MouseEvent) => {
      if (!drag) return;
      angle += (e.clientX - lx) * 0.006;
      elev = Math.max(-1.2, Math.min(1.4, elev + (e.clientY - ly) * 0.005));
      lx = e.clientX; ly = e.clientY;
    };
    const up = () => { drag = false; };
    let dist = 7.5;
    const wheel = (e: WheelEvent) => {
      e.preventDefault();
      dist = Math.max(3.5, Math.min(16, dist + e.deltaY * 0.006));
    };

    const dom = renderer.domElement;
    dom.addEventListener("mousedown", down);
    window.addEventListener("mousemove", move);
    window.addEventListener("mouseup", up);
    dom.addEventListener("wheel", wheel, { passive: false });

    const animate = () => {
      frame.current = requestAnimationFrame(animate);
      if (!drag) angle += 0.0022;
      camera.position.set(
        dist * Math.cos(elev) * Math.sin(angle),
        dist * Math.sin(elev),
        dist * Math.cos(elev) * Math.cos(angle),
      );
      camera.lookAt(0, 0, 0);
      renderer.render(scene, camera);
    };
    animate();

    return () => {
      cancelAnimationFrame(frame.current);
      dom.removeEventListener("mousedown", down);
      window.removeEventListener("mousemove", move);
      window.removeEventListener("mouseup", up);
      dom.removeEventListener("wheel", wheel);
      renderer.dispose();
      if (el.contains(dom)) el.removeChild(dom);
    };
  }, [arms, selected, backend, T]);

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <div style={{
        padding: "6px 12px", borderBottom: `1px solid ${T.borderSoft}`,
        fontSize: 10, color: T.textMuted, fontFamily: SANS,
        display: "flex", gap: 14,
      }}>
        <span>x: state</span>
        <span>y: d(state)/dt</span>
        <span>z: time</span>
        <span style={{ marginLeft: "auto" }}>drag to rotate · scroll to zoom</span>
      </div>
      <div ref={mount} style={{ flex: 1, minHeight: 0 }} />
    </div>
  );
}
