import { useEffect, useRef, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, useGLTF, Environment, Bounds, Center } from "@react-three/drei";
import * as THREE from "three";
import { useBody } from "@/lib/bodyState";
import { COMPARTMENT } from "./bodyRegions";

/**
 * GLB viewer that tints mesh materials by the current compartment
 * activation. The tint IS the readout — there is no second canvas,
 * just the 3D anatomy breathing with the current state.
 *
 * Available GLBs live under /public/models/; pick via props.glb.
 */
export default function BodyGLB({ glb = "model_huma_anatom.glb" }) {
  return (
    <Canvas
      camera={{ position: [0, 1.2, 3.2], fov: 35 }}
      dpr={[1, 2]}
      gl={{ antialias: true }}
    >
      <color attach="background" args={["#0a0a0f"]} />

      <ambientLight intensity={0.35} />
      <directionalLight position={[5, 5, 5]} intensity={0.9} />
      <directionalLight position={[-5, 3, -2]} intensity={0.5} color="#58E6D9" />
      <directionalLight position={[0, -3, 2]} intensity={0.35} color="#B63E96" />

      <Bounds fit clip observe margin={1.2}>
        <Center>
          <GLBModel url={`/models/${glb}`} />
        </Center>
      </Bounds>

      <OrbitControls makeDefault enableDamping dampingFactor={0.08} minDistance={0.5} maxDistance={12} />
    </Canvas>
  );
}

function GLBModel({ url }) {
  const { scene, animations } = useGLTF(url);
  const { compartments } = useBody();
  const ref = useRef();
  const originalMats = useRef(new WeakMap());
  const mixerRef = useRef(null);

  // Set up the animation mixer if the GLB has clips.
  useEffect(() => {
    if (!scene) return;
    if (animations && animations.length > 0) {
      mixerRef.current = new THREE.AnimationMixer(scene);
      animations.forEach((clip) => mixerRef.current.clipAction(clip).play());
    }
    return () => {
      if (mixerRef.current) mixerRef.current.stopAllAction();
      mixerRef.current = null;
    };
  }, [scene, animations]);

  // Traverse and cache originals; clone materials so we can tint per-instance.
  useEffect(() => {
    if (!scene) return;
    scene.traverse((child) => {
      if (child.isMesh && child.material) {
        if (!originalMats.current.has(child)) {
          const mat = Array.isArray(child.material)
            ? child.material.map((m) => m.clone())
            : child.material.clone();
          originalMats.current.set(child, mat);
          child.material = mat;
        }
      }
    });
  }, [scene]);

  // Tint the whole body mass subtly by the dominant compartment. A
  // compartment-aware segmentation per mesh is not available without
  // per-GLB metadata; instead we drive a global emissive tint whose
  // colour = weighted sum of compartment colours and whose strength =
  // max(compartment activation).
  useFrame((state, delta) => {
    if (mixerRef.current) mixerRef.current.update(delta);

    if (!scene) return;
    const total = Object.values(compartments).reduce((s, v) => s + v, 0) || 1;
    const col = new THREE.Color(0, 0, 0);
    const tmp = new THREE.Color();
    let maxAct = 0;
    Object.entries(compartments).forEach(([name, v]) => {
      if (!COMPARTMENT[name]) return;
      tmp.set(COMPARTMENT[name].colour);
      col.r += (tmp.r * v) / total;
      col.g += (tmp.g * v) / total;
      col.b += (tmp.b * v) / total;
      if (v > maxAct) maxAct = v;
    });
    const strength = 0.15 + 0.55 * maxAct;

    scene.traverse((child) => {
      if (child.isMesh && child.material) {
        const mats = Array.isArray(child.material) ? child.material : [child.material];
        mats.forEach((m) => {
          if (m.emissive) {
            m.emissive.copy(col);
            m.emissiveIntensity = strength;
          }
        });
      }
    });
  });

  return <primitive ref={ref} object={scene} />;
}

// Pre-load common GLBs so tab switches are instant.
useGLTF.preload("/models/model_huma_anatom.glb");
useGLTF.preload("/models/bust.glb");
