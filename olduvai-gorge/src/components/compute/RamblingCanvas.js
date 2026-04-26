import { useEffect, useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";

/**
 * Rambling/trembling decomposition rendered as a compute pass.
 *
 * State texture: 1 × N × RGBA32F where each texel x corresponds to
 * a sample of the simulated CoP signal:
 *   R = raw CoP        (mm, floating)
 *   G = rambling       (low-pass component)
 *   B = trembling      (raw - rambling)
 *   A = phase scratch
 *
 * The simulation generates a fresh sample at the rightmost texel each
 * frame, scrolls the buffer leftward, and applies a single-pole IIR
 * low-pass to update G in place — the cheap shader analogue of the
 * paper's 4th-order Butterworth at 0.4 Hz. The display pass reads
 * this same buffer and draws three traces.
 */

export default function RamblingCanvas({ params }) {
  return (
    <div className="absolute inset-0">
      <Canvas
        orthographic
        camera={{ position: [0, 0, 1], zoom: 1 }}
        dpr={[1, 2]}
        gl={{ antialias: false }}
      >
        <RamblingSim params={params} />
      </Canvas>
    </div>
  );
}

const N_SAMPLES = 1024;

function RamblingSim({ params }) {
  const meshRef = useRef();

  // CPU-side ring buffer holding the raw + rambling + trembling values.
  // We update it on each frame and write into a DataTexture, which the
  // display shader samples. The simulation IS the buffer; the texture
  // is the renderable form of that simulation state.
  const buffer = useMemo(() => {
    const arr = new Float32Array(N_SAMPLES * 4);
    return arr;
  }, []);

  const tex = useMemo(() => {
    const t = new THREE.DataTexture(
      buffer,
      N_SAMPLES,
      1,
      THREE.RGBAFormat,
      THREE.FloatType
    );
    t.needsUpdate = true;
    t.minFilter = THREE.LinearFilter;
    t.magFilter = THREE.LinearFilter;
    t.wrapS = THREE.ClampToEdgeWrapping;
    return t;
  }, [buffer]);

  const display = useMemo(() => {
    return new THREE.ShaderMaterial({
      vertexShader: /* glsl */ `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = vec4(position.xy, 0.0, 1.0);
        }
      `,
      fragmentShader: /* glsl */ `
        precision highp float;
        varying vec2 vUv;
        uniform sampler2D uState;

        // Map a normalised value v ∈ [-1, 1] to a vertical band centred at y0.
        float traceMask(float y, float v, float y0, float thickness) {
          float pos = y0 - v * 0.18;
          float d = abs(y - pos);
          return smoothstep(thickness + 0.003, 0.0, d);
        }

        void main() {
          float x = vUv.x;
          vec4 s = texture2D(uState, vec2(x, 0.5));
          // s.r = raw CoP, s.g = rambling, s.b = trembling, scaled to ±1
          // by the simulation already.

          float y = vUv.y;

          // Three rows: raw at top, rambling middle, trembling bottom.
          float raw = traceMask(y, s.r, 0.78, 0.012);
          float ram = traceMask(y, s.g, 0.50, 0.012);
          float tre = traceMask(y, s.b, 0.22, 0.012);

          vec3 col = vec3(0.039, 0.039, 0.059);
          col += raw * vec3(0.345, 0.902, 0.851); // cyan: raw
          col += ram * vec3(0.941, 0.659, 0.188); // amber: rambling (low freq)
          col += tre * vec3(0.714, 0.243, 0.588); // violet: trembling (high freq)

          // Faint baselines
          if (abs(y - 0.78) < 0.0015) col += vec3(0.07);
          if (abs(y - 0.50) < 0.0015) col += vec3(0.07);
          if (abs(y - 0.22) < 0.0015) col += vec3(0.07);

          // Vignette
          col *= smoothstep(1.0, 0.4, abs(vUv.x - 0.5) * 1.6);

          gl_FragColor = vec4(col, 1.0);
        }
      `,
      uniforms: {
        uState: { value: tex },
      },
    });
  }, [tex]);

  // Synthesis state held in refs so we don't re-allocate per frame.
  const phase = useRef(0);
  const filtered = useRef(0);
  const scrollAcc = useRef(0);

  useFrame((state, delta) => {
    // Sliding-window approach: shift the entire buffer one sample left,
    // compute a new sample at the right edge.
    // Use sub-sample accumulation so the visualisation runs at a
    // consistent ~50 samples/sec regardless of frame rate.
    scrollAcc.current += delta * (params.sampleHz ?? 50);
    let nNew = Math.floor(scrollAcc.current);
    scrollAcc.current -= nNew;
    nNew = Math.min(nNew, 8); // cap catch-up

    if (nNew > 0) {
      // shift left
      buffer.copyWithin(0, nNew * 4);
      // generate new samples at the right edge
      for (let i = 0; i < nNew; i++) {
        phase.current += delta / Math.max(1e-3, nNew);
        const t = state.clock.elapsedTime + i * 0.02;

        // Synthesise a CoP-like signal: slow drift (rambling) +
        // higher-frequency oscillation (trembling) + noise.
        const slowAmp = params.ramAmp ?? 0.7;
        const fastAmp = params.tremAmp ?? 0.35;
        const noise = (Math.random() - 0.5) * (params.noise ?? 0.15);

        const slow =
          slowAmp *
          (Math.sin(t * 0.18 * 2 * Math.PI) +
            0.4 * Math.sin(t * 0.32 * 2 * Math.PI + 1.0));
        const fast =
          fastAmp *
          (Math.sin(t * 1.4 * 2 * Math.PI + 0.7) +
            0.5 * Math.sin(t * 2.6 * 2 * Math.PI));

        const raw = slow + fast + noise;

        // Single-pole IIR low-pass on raw, cutoff ≈ params.cutoffHz
        const fs = params.sampleHz ?? 50;
        const fc = params.cutoffHz ?? 0.4;
        const alpha = 1.0 - Math.exp(-2.0 * Math.PI * fc / fs);
        filtered.current += alpha * (raw - filtered.current);

        const idx = (N_SAMPLES - nNew + i) * 4;
        buffer[idx + 0] = raw;
        buffer[idx + 1] = filtered.current;
        buffer[idx + 2] = raw - filtered.current;
        buffer[idx + 3] = 0;
      }
      tex.needsUpdate = true;
    }
  });

  return (
    <mesh ref={meshRef}>
      <planeGeometry args={[2, 2]} />
      <primitive object={display} attach="material" />
    </mesh>
  );
}
