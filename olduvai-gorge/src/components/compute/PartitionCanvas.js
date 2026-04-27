import { useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";

/**
 * Partition-coordinate visualiser.
 *
 * Draws hydrogen-like orbital probability density |ψ_{n,ℓ,m}|² by
 * raymarching the volumetric scalar field on the GPU. The user picks
 * (n, ℓ, m); the displayed glow is the spatial form of the partition
 * cell. C(n) = 2n² is the count of independent (ℓ, m, s) combinations
 * available at level n.
 *
 * Real spherical harmonics are used so the orbitals look the way
 * everyone draws them.
 */
export default function PartitionCanvas({ n, l, m, intensity = 1 }) {
  return (
    <div className="absolute inset-0">
      <Canvas
        orthographic
        camera={{ position: [0, 0, 1], zoom: 1 }}
        dpr={[1, 2]}
        gl={{ antialias: false }}
      >
        <Quad n={n} l={l} m={m} intensity={intensity} />
      </Canvas>
    </div>
  );
}

function Quad({ n, l, m, intensity }) {
  const material = useMemo(() => {
    return new THREE.ShaderMaterial({
      vertexShader: /* glsl */ `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = vec4(position.xy, 0.0, 1.0);
        }
      `,
      fragmentShader: ORBITAL_FS,
      uniforms: {
        uN: { value: n },
        uL: { value: l },
        uM: { value: m },
        uTime: { value: 0 },
        uIntensity: { value: intensity },
        uAspect: { value: 1 },
      },
    });
    // The material is constructed once and its uniforms are mutated
    // each frame from the latest props — we deliberately do NOT
    // recreate the material on every n/l/m/intensity change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Update uniforms every frame so prop changes propagate without
  // rebuilding the material.
  useFrame((state) => {
    material.uniforms.uN.value = n;
    material.uniforms.uL.value = l;
    material.uniforms.uM.value = m;
    material.uniforms.uIntensity.value = intensity;
    material.uniforms.uTime.value = state.clock.elapsedTime;
    material.uniforms.uAspect.value = state.size.width / state.size.height;
  });

  return (
    <mesh>
      <planeGeometry args={[2, 2]} />
      <primitive object={material} attach="material" />
    </mesh>
  );
}

const ORBITAL_FS = /* glsl */ `
  precision highp float;
  varying vec2 vUv;
  uniform int uN;
  uniform int uL;
  uniform int uM;
  uniform float uTime;
  uniform float uIntensity;
  uniform float uAspect;

  // Bohr radius in plot units. Scale grows with n.
  float a0(int n) { return 0.07 * float(n) * float(n); }

  // Real spherical harmonic (l, m) evaluated at unit vector dir.
  // Implemented for l = 0..3, m = -l..l. Higher l falls back to s.
  float realSphericalY(int l, int m, vec3 d) {
    float x = d.x; float y = d.y; float z = d.z;
    if (l == 0) return 1.0;
    if (l == 1) {
      if (m == -1) return y;
      if (m ==  0) return z;
      if (m ==  1) return x;
    }
    if (l == 2) {
      if (m == -2) return x*y;
      if (m == -1) return y*z;
      if (m ==  0) return 0.5*(3.0*z*z - 1.0);
      if (m ==  1) return x*z;
      if (m ==  2) return 0.5*(x*x - y*y);
    }
    if (l == 3) {
      if (m == -3) return y*(3.0*x*x - y*y);
      if (m == -2) return x*y*z;
      if (m == -1) return y*(5.0*z*z - 1.0);
      if (m ==  0) return z*(5.0*z*z - 3.0);
      if (m ==  1) return x*(5.0*z*z - 1.0);
      if (m ==  2) return z*(x*x - y*y);
      if (m ==  3) return x*(x*x - 3.0*y*y);
    }
    return 1.0;
  }

  // Approximate hydrogenic radial part, simplified.
  float radial(int n, int l, float r) {
    float a = a0(n);
    float rho = r / a;
    float decay = exp(-rho / float(n));
    if (n == 1) return decay;
    if (n == 2) {
      if (l == 0) return (2.0 - rho) * decay;
      return rho * decay;
    }
    if (n == 3) {
      if (l == 0) return (27.0 - 18.0*rho + 2.0*rho*rho) * decay / 27.0;
      if (l == 1) return rho * (6.0 - rho) * decay / 6.0;
      return rho * rho * decay / 9.0;
    }
    if (n == 4) {
      if (l == 0) return (1.0 - 0.75*rho + 0.125*rho*rho - rho*rho*rho/192.0) * decay;
      if (l == 1) return rho * (1.0 - rho/4.0) * decay;
      if (l == 2) return rho * rho * decay / 3.0;
      return rho * rho * rho * decay / 27.0;
    }
    return decay;
  }

  // Probability density |psi|^2 at point p (with center at origin).
  float density(vec3 p) {
    float r = length(p);
    if (r < 1e-4) r = 1e-4;
    vec3 d = p / r;
    float R = radial(uN, uL, r);
    float Y = realSphericalY(uL, uM, d);
    return R * R * Y * Y;
  }

  // Raymarch the density and accumulate.
  vec4 raymarch(vec3 ro, vec3 rd) {
    float t = 0.0;
    float total = 0.0;
    float maxT = 5.0;
    for (int i = 0; i < 64; i++) {
      vec3 p = ro + rd * t;
      float d = density(p);
      total += d * 0.06;
      t += 0.085;
      if (t > maxT) break;
    }
    return vec4(total);
  }

  vec3 palette(float v) {
    vec3 void0  = vec3(0.039, 0.039, 0.059);
    vec3 cyan   = vec3(0.345, 0.902, 0.851);
    vec3 violet = vec3(0.714, 0.243, 0.588);
    vec3 amber  = vec3(0.941, 0.659, 0.188);
    if (v < 0.5) return mix(void0, cyan, v * 2.0);
    if (v < 0.85) return mix(cyan, violet, (v - 0.5) / 0.35);
    return mix(violet, amber, (v - 0.85) / 0.15);
  }

  void main() {
    vec2 p = vUv - 0.5;
    p.x *= uAspect;

    // Slowly rotating camera around y axis so the structure reads.
    float ang = uTime * 0.18;
    float c = cos(ang); float s = sin(ang);
    mat3 rotY = mat3(c, 0.0, s,
                     0.0, 1.0, 0.0,
                     -s, 0.0, c);

    vec3 ro = rotY * vec3(0.0, 0.05, -2.0);
    vec3 rd = rotY * normalize(vec3(p, 1.5));

    vec4 acc = raymarch(ro, rd);

    float v = clamp(acc.r * 25.0 * uIntensity, 0.0, 1.0);
    v = pow(v, 0.7);
    vec3 col = palette(v);

    // Vignette
    col *= smoothstep(0.95, 0.2, length(vUv - 0.5));

    gl_FragColor = vec4(col, 1.0);
  }
`;
