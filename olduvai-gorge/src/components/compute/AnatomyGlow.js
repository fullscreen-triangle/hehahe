import { useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";

/**
 * Anatomical glow shader. The silhouette glows at intensities
 * proportional to the four Q components — the rendered pixels ARE
 * the Q readout, not a decoration of a separate calculation.
 *
 * Props:
 *   q: { thought, motor, perception, dream, baseline }   mC/s values
 */
export default function AnatomyGlow({ q }) {
  return (
    <div className="relative w-full h-full">
      <Canvas
        orthographic
        camera={{ position: [0, 0, 1], zoom: 1 }}
        dpr={[1, 2]}
        gl={{ antialias: false }}
      >
        <Glow q={q} />
      </Canvas>
    </div>
  );
}

function Glow({ q }) {
  const matRef = useRef();

  const material = useMemo(() => {
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
        uniform float uTime;
        uniform float uQthought;   // normalized 0..1
        uniform float uQmotor;
        uniform float uQperc;
        uniform float uQdream;
        uniform float uAspect;

        // SDF primitives
        float sdCircle(vec2 p, float r) { return length(p) - r; }
        float sdCapsule(vec2 p, vec2 a, vec2 b, float r) {
          vec2 pa = p - a, ba = b - a;
          float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
          return length(pa - ba*h) - r;
        }

        float glow(float d, float intensity, float radius) {
          return intensity * exp(-max(d, 0.0) * radius);
        }

        void main() {
          vec2 p = (vUv - 0.5);
          p.x *= uAspect;

          // Humanoid silhouette (schematic, not anatomical):
          //   head  at (0, 0.36)
          //   torso vertical capsule (0, 0.18) .. (0, -0.05)
          //   arms  from shoulders
          //   legs  from hips

          float dHead  = sdCircle(p - vec2(0.0, 0.36), 0.085);
          float dTorso = sdCapsule(p, vec2(0.0, 0.22), vec2(0.0, -0.02), 0.07);
          float dArmL  = sdCapsule(p, vec2(-0.07, 0.18), vec2(-0.17, -0.02), 0.022);
          float dArmR  = sdCapsule(p, vec2( 0.07, 0.18), vec2( 0.17, -0.02), 0.022);
          float dLegL  = sdCapsule(p, vec2(-0.04, -0.04), vec2(-0.09, -0.38), 0.028);
          float dLegR  = sdCapsule(p, vec2( 0.04, -0.04), vec2( 0.09, -0.38), 0.028);
          float dHeart = sdCircle(p - vec2(-0.018, 0.13), 0.025);

          // Compartment glows
          vec3 col = vec3(0.035, 0.035, 0.055);

          // Head = thought (violet) + dream (tinted cyan at back of head)
          float headThought = glow(dHead, uQthought, 80.0);
          float headDream   = glow(dHead + 0.02, uQdream,  60.0);
          col += headThought * vec3(0.714, 0.243, 0.588) * 1.4;
          col += headDream   * vec3(0.345, 0.902, 0.851) * 0.55;

          // Torso = perception (amber) + baseline (soft white)
          float torsoPerc = glow(dTorso, uQperc, 60.0);
          col += torsoPerc * vec3(0.941, 0.659, 0.188) * 1.2;

          // Heart pulse (at cardiac frequency) — pure coherence marker
          float pulse = 0.5 + 0.5 * sin(uTime * 6.28 * 1.2);
          float dH = glow(dHeart, 0.6 * pulse + 0.3, 120.0);
          col += dH * vec3(0.9, 0.3, 0.35);

          // Arms + legs = motor (cyan)
          float armL = glow(dArmL, uQmotor, 90.0);
          float armR = glow(dArmR, uQmotor, 90.0);
          float legL = glow(dLegL, uQmotor, 90.0);
          float legR = glow(dLegR, uQmotor, 90.0);
          col += (armL + armR + legL + legR)
               * vec3(0.345, 0.902, 0.851) * 1.3;

          // Tonemap + vignette
          col = col / (1.0 + col);
          float vig = smoothstep(0.95, 0.2, length(vUv - 0.5));
          col *= vig;

          gl_FragColor = vec4(col, 1.0);
        }
      `,
      uniforms: {
        uTime:     { value: 0 },
        uQthought: { value: 0 },
        uQmotor:   { value: 0 },
        uQperc:    { value: 0 },
        uQdream:   { value: 0 },
        uAspect:   { value: 1 },
      },
    });
  }, []);

  // Normalize Q values (mC/s) into 0..1 by typical healthy maxima.
  const norm = useMemo(() => ({
    thought: q.thought / 300,
    motor:   q.motor   / 400,
    perc:    q.perception / 150,
    dream:   q.dream   / 200,
  }), [q]);

  useFrame((state) => {
    material.uniforms.uTime.value = state.clock.elapsedTime;
    // Smooth interpolation so sliders animate.
    const lerp = (from, to, rate = 0.2) => from + (to - from) * rate;
    const u = material.uniforms;
    u.uQthought.value = lerp(u.uQthought.value, norm.thought);
    u.uQmotor.value   = lerp(u.uQmotor.value,   norm.motor);
    u.uQperc.value    = lerp(u.uQperc.value,    norm.perc);
    u.uQdream.value   = lerp(u.uQdream.value,   norm.dream);
    u.uAspect.value   = state.size.width / state.size.height;
  });

  return (
    <mesh ref={matRef}>
      <planeGeometry args={[2, 2]} />
      <primitive object={material} attach="material" />
    </mesh>
  );
}
