import { useEffect, useMemo, useRef } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import { vertexShader, stepShader, displayShader } from "@/shaders/chargeField";

/**
 * GPU charge-field. The framebuffer IS the state buffer.
 * No CPU-side simulation exists; what you see is what is computed.
 *
 * Props:
 *   resolution: int — simulation grid size (square). 256 is a good default.
 *   injectOnPointer: bool — mouse/touch adds local charge when true.
 *   seed: {intensity, diffuse, relax, decay} — physics tuning.
 *   fullscreen: bool — stretch to fill parent (default true).
 */
export default function ChargeFieldCanvas({
  resolution = 256,
  injectOnPointer = true,
  seed = {},
  fullscreen = true,
  className = "",
}) {
  return (
    <div
      className={`${fullscreen ? "absolute inset-0" : "relative w-full h-full"} ${className}`}
    >
      <Canvas
        orthographic
        camera={{ position: [0, 0, 1], zoom: 1 }}
        dpr={[1, 2]}
        gl={{ antialias: false, preserveDrawingBuffer: false }}
      >
        <FieldSim
          resolution={resolution}
          injectOnPointer={injectOnPointer}
          seed={seed}
        />
      </Canvas>
    </div>
  );
}

function FieldSim({ resolution, injectOnPointer, seed }) {
  const { gl, size } = useThree();
  const meshRef = useRef();

  // Two ping-pong float targets that hold the simulation state.
  const targets = useMemo(() => {
    const opts = {
      minFilter: THREE.LinearFilter,
      magFilter: THREE.LinearFilter,
      format: THREE.RGBAFormat,
      type: THREE.HalfFloatType,
      wrapS: THREE.ClampToEdgeWrapping,
      wrapT: THREE.ClampToEdgeWrapping,
      depthBuffer: false,
      stencilBuffer: false,
    };
    return [
      new THREE.WebGLRenderTarget(resolution, resolution, opts),
      new THREE.WebGLRenderTarget(resolution, resolution, opts),
    ];
  }, [resolution]);

  // Offscreen full-viewport scene used ONLY to run the physics step into
  // the back buffer — this is the computation.
  const stepMaterial = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader,
        fragmentShader: stepShader,
        uniforms: {
          uState:   { value: null },
          uRes:     { value: new THREE.Vector2(resolution, resolution) },
          uTime:    { value: 0 },
          uDt:      { value: 0.016 },
          uCursor:  { value: new THREE.Vector2(-1, -1) },
          uInject:  { value: seed.inject ?? 0.0 },
          uDiffuse: { value: seed.diffuse ?? 0.15 },
          uRelax:   { value: seed.relax ?? 0.45 },
          uDecay:   { value: seed.decay ?? 0.003 },
        },
      }),
    [resolution, seed.inject, seed.diffuse, seed.relax, seed.decay]
  );

  // On-screen material displays the current state buffer.
  const displayMaterial = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader,
        fragmentShader: displayShader,
        uniforms: {
          uState:     { value: null },
          uTime:      { value: 0 },
          uIntensity: { value: seed.intensity ?? 1.0 },
        },
      }),
    [seed.intensity]
  );

  // Seed a weak random field once so there's something to evolve.
  useEffect(() => {
    const w = resolution;
    const data = new Float32Array(w * w * 4);
    for (let i = 0; i < w * w; i++) {
      const x = (i % w) / w - 0.5;
      const y = Math.floor(i / w) / w - 0.5;
      const r = Math.sqrt(x * x + y * y);
      const seedRho =
        0.45 * Math.sin(r * 30.0) * Math.exp(-r * 4.0) +
        0.1 * (Math.random() - 0.5);
      data[i * 4 + 0] = seedRho;   // rho
      data[i * 4 + 1] = 0.0;       // phi
      data[i * 4 + 2] = 0.0;       // J
      data[i * 4 + 3] = 0.5;       // order
    }
    const seedTex = new THREE.DataTexture(
      data,
      w,
      w,
      THREE.RGBAFormat,
      THREE.FloatType
    );
    seedTex.needsUpdate = true;

    // Blit seed -> targets[0]
    const blitScene = new THREE.Scene();
    const blitMat = new THREE.MeshBasicMaterial({ map: seedTex });
    const blitMesh = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), blitMat);
    blitScene.add(blitMesh);
    const cam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);

    gl.setRenderTarget(targets[0]);
    gl.render(blitScene, cam);
    gl.setRenderTarget(null);

    seedTex.dispose();
    blitMat.dispose();
    blitMesh.geometry.dispose();
  }, [gl, targets, resolution]);

  // Offscreen simulation scene (one quad, one material, one camera).
  const simScene = useMemo(() => {
    const s = new THREE.Scene();
    s.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), stepMaterial));
    return s;
  }, [stepMaterial]);
  const simCam = useMemo(
    () => new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1),
    []
  );

  // Cursor → normalized UV for injection.
  const pointer = useRef(new THREE.Vector2(-1, -1));
  const pointerInside = useRef(false);

  useEffect(() => {
    if (!injectOnPointer) return;
    const el = gl.domElement;
    const onMove = (e) => {
      const rect = el.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width;
      const y = 1.0 - (e.clientY - rect.top) / rect.height;
      pointer.current.set(x, y);
      pointerInside.current = true;
    };
    const onOut = () => (pointerInside.current = false);
    const onTouch = (e) => {
      if (e.touches.length === 0) return;
      const t = e.touches[0];
      const rect = el.getBoundingClientRect();
      pointer.current.set(
        (t.clientX - rect.left) / rect.width,
        1.0 - (t.clientY - rect.top) / rect.height
      );
      pointerInside.current = true;
    };
    el.addEventListener("pointermove", onMove);
    el.addEventListener("pointerleave", onOut);
    el.addEventListener("touchmove", onTouch, { passive: true });
    el.addEventListener("touchend", onOut);
    return () => {
      el.removeEventListener("pointermove", onMove);
      el.removeEventListener("pointerleave", onOut);
      el.removeEventListener("touchmove", onTouch);
      el.removeEventListener("touchend", onOut);
    };
  }, [gl, injectOnPointer]);

  const swap = useRef(0);

  useFrame((state, delta) => {
    // === THIS IS THE COMPUTATION ===
    // Read from targets[swap], write to targets[1 - swap].
    const read = targets[swap.current];
    const write = targets[1 - swap.current];

    stepMaterial.uniforms.uState.value = read.texture;
    stepMaterial.uniforms.uTime.value = state.clock.elapsedTime;
    stepMaterial.uniforms.uDt.value = Math.min(delta, 1 / 30);
    if (injectOnPointer && pointerInside.current) {
      stepMaterial.uniforms.uCursor.value.copy(pointer.current);
      stepMaterial.uniforms.uInject.value = seed.inject ?? 0.9;
    } else {
      stepMaterial.uniforms.uCursor.value.set(-1, -1);
      stepMaterial.uniforms.uInject.value = 0.0;
    }

    gl.setRenderTarget(write);
    gl.render(simScene, simCam);
    gl.setRenderTarget(null);

    swap.current = 1 - swap.current;

    // === THIS IS THE OBSERVATION ===
    // The display reads the same buffer the physics just wrote.
    displayMaterial.uniforms.uState.value = write.texture;
    displayMaterial.uniforms.uTime.value = state.clock.elapsedTime;
    if (meshRef.current) {
      meshRef.current.material = displayMaterial;
    }
  }, 0);

  // Full-viewport display quad in the on-screen canvas.
  return (
    <mesh ref={meshRef}>
      <planeGeometry args={[2, 2]} />
      {/* Material is swapped in on each frame. Placeholder here. */}
      <shaderMaterial
        vertexShader={vertexShader}
        fragmentShader={displayShader}
        uniforms={{
          uState:     { value: null },
          uTime:      { value: 0 },
          uIntensity: { value: 1 },
        }}
      />
    </mesh>
  );
}
