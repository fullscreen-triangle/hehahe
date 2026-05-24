import { useEffect, useMemo, useRef } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import { PITCH_X, PITCH_Y } from "@/lib/football/syntheticScene";

/**
 * Attention-field GPU compute.
 *
 * A single fragment shader pass evaluates the per-pixel attention
 * density Σᵢ wᵢ · exp(−½(θᵢ/σ)²) over the pitch image plane, where
 * θᵢ is the angle between (pixel − pᵢ) and the player's facing
 * vector fᵢ. The rendered framebuffer IS the attention field —
 * brighter pixels = more players looking there. The brightest pixel
 * is the ball position (the framework's "observation operator" made
 * literal: rendering = computing = observation).
 *
 * Up to 32 players are passed in as uniform arrays. Player markers
 * and the focus dot are drawn as a second instanced overlay layer.
 *
 * Props:
 *   scene: { detections: [...], ball: [x,y], t }     latest scene step
 *   focus: [x,y] in pitch metres                    JS-computed focus point
 *   showRays: bool                                  draw attention rays
 *   showGroundTruth: bool                           draw the real ball
 */

const MAX_PLAYERS = 32;

const vert = /* glsl */ `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = vec4(position.xy, 0.0, 1.0);
  }
`;

const frag = /* glsl */ `
  precision highp float;
  varying vec2 vUv;
  uniform int   uNplayers;
  uniform vec2  uPlayerPos[${MAX_PLAYERS}];
  uniform vec2  uPlayerFacing[${MAX_PLAYERS}];
  uniform float uPlayerWeight[${MAX_PLAYERS}];
  uniform vec2  uPitchHalf;     // (PITCH_X/2, PITCH_Y/2)
  uniform float uSigmaRad;      // angular sigma for attention density
  uniform float uIntensity;

  // Map vUv (0..1, 0..1) to pitch coordinates (-PITCH_X/2..+PITCH_X/2).
  vec2 uvToPitch(vec2 uv) {
    return (uv * 2.0 - 1.0) * uPitchHalf;
  }

  // Three-stop palette: cool void → cyan → violet → amber.
  vec3 palette(float v) {
    vec3 c0 = vec3(0.02, 0.06, 0.05);
    vec3 c1 = vec3(0.345, 0.902, 0.851);
    vec3 c2 = vec3(0.714, 0.243, 0.588);
    vec3 c3 = vec3(0.941, 0.659, 0.188);
    if (v < 0.5) return mix(c0, c1, v * 2.0);
    if (v < 0.85) return mix(c1, c2, (v - 0.5) / 0.35);
    return mix(c2, c3, (v - 0.85) / 0.15);
  }

  void main() {
    vec2 q = uvToPitch(vUv);

    // Pitch background: a faint green base + lighter midfield line.
    vec3 pitch = vec3(0.06, 0.16, 0.08);
    float midline = smoothstep(0.6, 0.0, abs(q.x));
    pitch += vec3(0.0, 0.04, 0.0) * midline;

    // Attention density sum.
    float logP = 0.0;
    int   n    = 0;
    for (int i = 0; i < ${MAX_PLAYERS}; i++) {
      if (i >= uNplayers) break;
      vec2 d = q - uPlayerPos[i];
      float r = length(d);
      if (r < 1e-3) continue;
      vec2 f = normalize(uPlayerFacing[i]);
      float cosTheta = dot(d, f) / r;
      if (cosTheta <= 0.0) continue;     // skip behind-player rays
      float theta = acos(clamp(cosTheta, -1.0, 1.0));
      logP += -0.5 * (theta * theta) / (uSigmaRad * uSigmaRad)
              * uPlayerWeight[i];
      n++;
    }
    float density = (n > 0) ? exp(logP) : 0.0;
    float v = clamp(density * uIntensity, 0.0, 1.0);
    v = pow(v, 0.55);

    vec3 col = mix(pitch, palette(v), v);

    gl_FragColor = vec4(col, 1.0);
  }
`;

// ────────────────────────────────────────────────────────────────────

export default function AttentionFieldCanvas({
  scene,
  focus,
  intensity = 1.0,
  sigmaRad = 0.30,
  className = "",
}) {
  return (
    <div className={`relative w-full h-full ${className}`}>
      <Canvas
        orthographic
        camera={{ position: [0, 0, 1], zoom: 1 }}
        dpr={[1, 2]}
        gl={{ antialias: true, preserveDrawingBuffer: false }}
      >
        <FieldPass
          scene={scene}
          focus={focus}
          intensity={intensity}
          sigmaRad={sigmaRad}
        />
        <OverlayLayer scene={scene} focus={focus} />
      </Canvas>
    </div>
  );
}

function FieldPass({ scene, focus, intensity, sigmaRad }) {
  const meshRef = useRef();

  const material = useMemo(() => {
    return new THREE.ShaderMaterial({
      vertexShader: vert,
      fragmentShader: frag,
      uniforms: {
        uNplayers: { value: 0 },
        uPlayerPos: {
          value: Array.from({ length: MAX_PLAYERS }, () => new THREE.Vector2()),
        },
        uPlayerFacing: {
          value: Array.from({ length: MAX_PLAYERS }, () => new THREE.Vector2()),
        },
        uPlayerWeight: { value: new Float32Array(MAX_PLAYERS) },
        uPitchHalf: { value: new THREE.Vector2(PITCH_X / 2, PITCH_Y / 2) },
        uSigmaRad: { value: sigmaRad },
        uIntensity: { value: intensity },
      },
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useFrame(() => {
    if (!scene?.detections) return;
    const u = material.uniforms;
    const n = Math.min(scene.detections.length, MAX_PLAYERS);
    u.uNplayers.value = n;
    u.uSigmaRad.value = sigmaRad;
    u.uIntensity.value = intensity;
    for (let i = 0; i < n; i++) {
      const d = scene.detections[i];
      u.uPlayerPos.value[i].set(d.position[0], d.position[1]);
      u.uPlayerFacing.value[i].set(d.facing[0], d.facing[1]);
      u.uPlayerWeight.value[i] = d.weight ?? 1;
    }
  });

  return (
    <mesh ref={meshRef}>
      <planeGeometry args={[2, 2]} />
      <primitive object={material} attach="material" />
    </mesh>
  );
}

// Player markers, facing arrows, focus dot, ground-truth ball.
// All drawn via the same orthographic camera in pitch-aspect-fitted UV.
function OverlayLayer({ scene, focus }) {
  const ref = useRef();
  const { size } = useThree();

  useFrame(() => {
    if (!ref.current || !scene?.detections) return;
    // Rebuild geometry each frame; small scene, cheap.
    const positions = [];
    const colours = [];

    const aspect = (PITCH_X / 2);
    const aspectY = (PITCH_Y / 2);

    // Players as triangles pointing in facing direction.
    for (const d of scene.detections) {
      const px = d.position[0] / aspect;
      const py = d.position[1] / aspectY;
      const fx = d.facing[0];
      const fy = d.facing[1];
      const fn = Math.hypot(fx, fy) || 1;
      const ux = fx / fn, uy = fy / fn;
      const vx = -uy, vy = ux;
      const L = 0.025;          // triangle half-length in NDC
      const W = 0.012;
      // Tip
      positions.push(px + ux * L, py + uy * L, 0);
      // Back-left
      positions.push(px - ux * L * 0.5 + vx * W, py - uy * L * 0.5 + vy * W, 0);
      // Back-right
      positions.push(px - ux * L * 0.5 - vx * W, py - uy * L * 0.5 - vy * W, 0);
      const col = d.team === 0 ? [0.34, 0.90, 0.85] : [0.94, 0.66, 0.19];
      for (let k = 0; k < 3; k++) colours.push(...col, 1);
    }
    const geom = ref.current.geometry;
    geom.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
    geom.setAttribute("color", new THREE.Float32BufferAttribute(colours, 4));
    geom.attributes.position.needsUpdate = true;
    geom.attributes.color.needsUpdate = true;
  });

  return (
    <>
      <mesh ref={ref}>
        <bufferGeometry />
        <meshBasicMaterial vertexColors transparent />
      </mesh>
      <FocusDot focus={focus} ball={scene?.ball} />
    </>
  );
}

function FocusDot({ focus, ball }) {
  const focusRef = useRef();
  const ballRef = useRef();

  useFrame(() => {
    const aspectX = PITCH_X / 2;
    const aspectY = PITCH_Y / 2;
    if (focus && focusRef.current) {
      focusRef.current.position.set(focus[0] / aspectX, focus[1] / aspectY, 0);
    }
    if (ball && ballRef.current) {
      ballRef.current.position.set(ball[0] / aspectX, ball[1] / aspectY, 0);
    }
  });

  return (
    <>
      <mesh ref={focusRef}>
        <circleGeometry args={[0.018, 32]} />
        <meshBasicMaterial color="#ffffff" transparent opacity={0.95} />
      </mesh>
      <mesh ref={ballRef}>
        <circleGeometry args={[0.012, 32]} />
        <meshBasicMaterial color="#e6395a" />
      </mesh>
    </>
  );
}
