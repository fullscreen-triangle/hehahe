import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import * as THREE from "three";

/*
═══════════════════════════════════════════════════════════════════════
  VITRUVIUS 3D ANATOMY VIEW
  
  Architecture:
  
  1. COMPARTMENT_MESH_MAP maps each .vvs compartment identifier to a
     mesh in the scene. In this prototype the meshes are procedural
     (cylinders, spheres). In production, replace buildProceduralAnatomy()
     with a GLTFLoader call and point each entry's `meshName` at the
     corresponding GLB group name.
  
  2. PATHWAY_MAP defines the outbound and return paths as sequences of
     compartment ids. The AnimationSystem draws particles along these
     paths. When a path is severed (closure_index = open), the
     particles stop at the cut point and the downstream mesh stops
     oscillating.
  
  3. ARM_STATES holds the experiment results per arm: which elements
     are present, what the tonic rate is, what the coupling index is.
     These drive the animation parameters.
  
  4. The animation loop runs three systems:
     - PulseSystem: particles flowing along outbound/return paths
     - OscillationSystem: each compartment mesh oscillates at its
       tonic rate (closed) or diverges (open)
     - CouplingSystem: phase relationship between strata
═══════════════════════════════════════════════════════════════════════
*/

// ─── Design tokens ──────────────────────────────────────────────────
const T = {
  bg:       "#111318",
  panel:    "#1a1d27",
  border:   "#2a2e3d",
  text:     "#c0caf5",
  dim:      "#565f89",
  muted:    "#3b4261",
  keyword:  "#7aa2f7",
  closed:   "#73daca",
  open:     "#f7768e",
  outbound: "#7aa2f7",
  ret:      "#9ece6a",
  supra:    "#ff9e64",
  spinal:   "#7dcfff",
  reflex:   "#bb9af7",
  muscle:   "#c53b53",
  bone:     "#d5cebd",
  nerve:    "#e0d68a",
  skin:     "#2a2420",
};

// ─── Compartment → Mesh mapping ─────────────────────────────────────
// In production: replace `build` functions with GLB mesh name references
//   meshName: "Soleus_Muscle"  ← name of the mesh group in the GLB
//   transform: applied after loading to align with circuit topology
const COMPARTMENTS = {
  cortex:      { label: "Motor cortex",    stratum: "supraspinal", color: T.supra  },
  spinal_in:   { label: "Spinal cord L5",  stratum: "spinal",      color: T.spinal },
  alpha_mn:    { label: "α-motor neuron",  stratum: "reflex",      color: T.reflex },
  nmj:         { label: "NMJ",             stratum: "reflex",      color: T.reflex },
  fibre:       { label: "Soleus fibre",    stratum: "reflex",      color: T.muscle },
  spindle:     { label: "Muscle spindle",  stratum: "reflex",      color: T.nerve  },
  ia_afferent: { label: "Ia afferent",     stratum: "reflex",      color: T.nerve  },
};

const OUTBOUND_PATH = ["cortex","spinal_in","alpha_mn","nmj","fibre"];
const RETURN_PATH   = ["fibre","spindle","ia_afferent","spinal_in","cortex"];

// ─── Experiment arms ────────────────────────────────────────────────
const ARMS = [
  {
    id: "intact", label: "Intact",
    closure: "closed", tonicRate: 15.7,
    coupling: 0.052, copRms: 3.74,
    severedElements: [], scaledElements: {},
    description: "Both phases intact. Bounded oscillation at 15.7 Hz.",
  },
  {
    id: "attenuated", label: "Attenuated (×0.1)",
    closure: "closed", tonicRate: 8.3,
    coupling: 0.041, copRms: 8.21,
    severedElements: [], scaledElements: { ia_axon: 0.1 },
    description: "Return gain reduced to 0.1. Loop stays closed — wider oscillation, lower rate.",
  },
  {
    id: "severed", label: "Severed (ia_axon)",
    closure: "open", tonicRate: 0,
    coupling: 0.011, copRms: 52.1,
    severedElements: ["ia_axon"], scaledElements: {},
    returnCutAt: "ia_afferent",  // particles stop here
    description: "Return element removed. Circuit open — perturbation cannot close. Movement fails to resolve.",
  },
  {
    id: "abolished", label: "Abolished (return)",
    closure: "open", tonicRate: 0,
    coupling: 0.006, copRms: 58.3,
    severedElements: ["ec_couple","mechano","ia_axon","ascend"], scaledElements: {},
    returnCutAt: "fibre",
    description: "Entire return phase removed. No afferent path exists. Immediate divergence.",
  },
];

// ─── Element → edge mapping (which compartments each element connects) ──
const ELEMENTS = [
  { id: "descend",   from: "cortex",      to: "spinal_in",   phase: "outbound" },
  { id: "premotor",  from: "spinal_in",   to: "alpha_mn",    phase: "outbound" },
  { id: "mn_axon",   from: "alpha_mn",    to: "nmj",         phase: "outbound" },
  { id: "endplate",  from: "nmj",         to: "fibre",       phase: "outbound" },
  { id: "ec_couple", from: "fibre",       to: "spindle",     phase: "return" },
  { id: "mechano",   from: "spindle",     to: "ia_afferent", phase: "return" },
  { id: "ia_axon",   from: "ia_afferent", to: "spinal_in",   phase: "return" },
  { id: "ascend",    from: "spinal_in",   to: "cortex",      phase: "return" },
];


// ═══════════════════════════════════════════════════════════════════
// Procedural anatomy builder
// Replace this entire function with GLTFLoader for production
// ═══════════════════════════════════════════════════════════════════
function buildProceduralAnatomy(scene) {
  const meshes = {};
  const pathPoints = {};

  // Positions in 3D space (right-handed, Y up)
  const positions = {
    cortex:      new THREE.Vector3(0, 4.2, 0),
    spinal_in:   new THREE.Vector3(0, 2.8, 0),
    alpha_mn:    new THREE.Vector3(-0.3, 2.2, 0),
    nmj:         new THREE.Vector3(-0.6, 1.2, 0),
    fibre:       new THREE.Vector3(-0.5, 0.4, 0.1),
    spindle:     new THREE.Vector3(-0.3, 0.5, 0.3),
    ia_afferent: new THREE.Vector3(0.2, 1.5, 0.2),
  };
  pathPoints.positions = positions;

  const mat = (color, emissive = 0x000000) => new THREE.MeshPhongMaterial({
    color, emissive, transparent: true, opacity: 0.85,
    shininess: 30, side: THREE.DoubleSide,
  });

  // ── Skeleton / reference anatomy (static, dim) ──
  // Spine
  const spineGeo = new THREE.CylinderGeometry(0.08, 0.06, 3.2, 8);
  const spine = new THREE.Mesh(spineGeo, mat(T.bone, 0x111111));
  spine.position.set(0, 2.8, 0);
  scene.add(spine);

  // Pelvis hint
  const pelvisGeo = new THREE.CylinderGeometry(0.5, 0.4, 0.15, 12);
  const pelvis = new THREE.Mesh(pelvisGeo, mat(T.bone, 0x0a0a0a));
  pelvis.position.set(0, 1.1, 0);
  scene.add(pelvis);

  // Femur
  const femurGeo = new THREE.CylinderGeometry(0.05, 0.04, 1.4, 6);
  const femur = new THREE.Mesh(femurGeo, mat(T.bone, 0x0a0a0a));
  femur.position.set(-0.35, 0.35, 0);
  femur.rotation.z = 0.08;
  scene.add(femur);

  // Tibia
  const tibiaGeo = new THREE.CylinderGeometry(0.04, 0.035, 1.2, 6);
  const tibia = new THREE.Mesh(tibiaGeo, mat(T.bone, 0x0a0a0a));
  tibia.position.set(-0.45, -0.55, 0);
  scene.add(tibia);

  // Head sphere (cortex region)
  const headGeo = new THREE.SphereGeometry(0.28, 16, 12);
  const head = new THREE.Mesh(headGeo, mat(T.supra, 0x1a0a00));
  head.position.copy(positions.cortex);
  scene.add(head);
  meshes.cortex = head;

  // Spinal segment
  const spSegGeo = new THREE.SphereGeometry(0.12, 10, 8);
  const spSeg = new THREE.Mesh(spSegGeo, mat(T.spinal, 0x001020));
  spSeg.position.copy(positions.spinal_in);
  scene.add(spSeg);
  meshes.spinal_in = spSeg;

  // Motor neuron
  const mnGeo = new THREE.SphereGeometry(0.07, 8, 6);
  const mn = new THREE.Mesh(mnGeo, mat(T.reflex, 0x100020));
  mn.position.copy(positions.alpha_mn);
  scene.add(mn);
  meshes.alpha_mn = mn;

  // NMJ
  const nmjGeo = new THREE.SphereGeometry(0.05, 8, 6);
  const nmjMesh = new THREE.Mesh(nmjGeo, mat(T.reflex, 0x100020));
  nmjMesh.position.copy(positions.nmj);
  scene.add(nmjMesh);
  meshes.nmj = nmjMesh;

  // Muscle fibre (soleus — the main animated piece)
  const fibreGeo = new THREE.CylinderGeometry(0.12, 0.08, 0.7, 8);
  const fibreMesh = new THREE.Mesh(fibreGeo, mat(T.muscle, 0x200010));
  fibreMesh.position.copy(positions.fibre);
  fibreMesh.rotation.z = 0.15;
  scene.add(fibreMesh);
  meshes.fibre = fibreMesh;

  // Spindle
  const spindleGeo = new THREE.CylinderGeometry(0.02, 0.02, 0.18, 6);
  const spindleMesh = new THREE.Mesh(spindleGeo, mat(T.nerve, 0x202000));
  spindleMesh.position.copy(positions.spindle);
  spindleMesh.rotation.z = 0.5;
  scene.add(spindleMesh);
  meshes.spindle = spindleMesh;

  // Ia afferent node
  const iaGeo = new THREE.SphereGeometry(0.05, 8, 6);
  const iaMesh = new THREE.Mesh(iaGeo, mat(T.nerve, 0x202000));
  iaMesh.position.copy(positions.ia_afferent);
  scene.add(iaMesh);
  meshes.ia_afferent = iaMesh;

  return { meshes, pathPoints };
}


// ═══════════════════════════════════════════════════════════════════
// Pathway renderer — draws nerve paths and animated pulses
// ═══════════════════════════════════════════════════════════════════
function buildPathways(scene, positions) {
  const pathObjects = { outbound: [], ret: [] };
  const curveObjects = { outbound: null, ret: null };

  const buildCurve = (ids, color, yOffset) => {
    const pts = ids.map(id => {
      const p = positions[id].clone();
      p.z += yOffset;
      return p;
    });
    const curve = new THREE.CatmullRomCurve3(pts, false, "catmullrom", 0.3);
    const tubeGeo = new THREE.TubeGeometry(curve, 48, 0.012, 6, false);
    const tubeMat = new THREE.MeshPhongMaterial({
      color, transparent: true, opacity: 0.5, emissive: color, emissiveIntensity: 0.15,
    });
    const tube = new THREE.Mesh(tubeGeo, tubeMat);
    scene.add(tube);
    return { curve, tube, pts, mat: tubeMat };
  };

  curveObjects.outbound = buildCurve(OUTBOUND_PATH, T.outbound, -0.15);
  curveObjects.ret = buildCurve(RETURN_PATH, T.ret, 0.15);

  return curveObjects;
}


// ═══════════════════════════════════════════════════════════════════
// Pulse particle system
// ═══════════════════════════════════════════════════════════════════
function createPulses(scene, curve, color, count = 8) {
  const pulses = [];
  const geo = new THREE.SphereGeometry(0.025, 6, 4);
  for (let i = 0; i < count; i++) {
    const mat = new THREE.MeshPhongMaterial({
      color, emissive: color, emissiveIntensity: 0.6,
      transparent: true, opacity: 0.9,
    });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.userData.phase = i / count;
    scene.add(mesh);
    pulses.push(mesh);
  }
  return pulses;
}


// ═══════════════════════════════════════════════════════════════════
// Main component
// ═══════════════════════════════════════════════════════════════════
export default function VitruviusAnatomyView() {
  const mountRef = useRef(null);
  const frameRef = useRef(null);
  const sceneRef = useRef(null);
  const [activeArm, setActiveArm] = useState("intact");
  const [isPlaying, setIsPlaying] = useState(true);
  const [showLabels, setShowLabels] = useState(true);
  const [time, setTime] = useState(0);

  const arm = ARMS.find(a => a.id === activeArm);

  useEffect(() => {
    const el = mountRef.current;
    if (!el) return;

    const w = el.clientWidth || 800;
    const h = el.clientHeight || 600;

    // ── Scene ──
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(T.bg);
    scene.fog = new THREE.Fog(T.bg, 8, 18);

    // ── Camera ──
    const camera = new THREE.PerspectiveCamera(40, w / h, 0.1, 50);
    camera.position.set(3.5, 3, 5);
    camera.lookAt(0, 2, 0);

    // ── Renderer ──
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(w, h);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    el.appendChild(renderer.domElement);

    // ── Lights ──
    const amb = new THREE.AmbientLight(0x404060, 0.5);
    scene.add(amb);
    const key = new THREE.DirectionalLight(0xffeedd, 0.8);
    key.position.set(3, 5, 4);
    key.castShadow = true;
    scene.add(key);
    const rim = new THREE.DirectionalLight(0x4466aa, 0.3);
    rim.position.set(-3, 2, -2);
    scene.add(rim);

    // ── Grid floor ──
    const gridGeo = new THREE.BufferGeometry();
    const gridPts = [];
    for (let i = -4; i <= 4; i += 0.5) {
      gridPts.push(-4, -0.8, i, 4, -0.8, i, i, -0.8, -4, i, -0.8, 4);
    }
    gridGeo.setAttribute("position", new THREE.Float32BufferAttribute(gridPts, 3));
    scene.add(new THREE.LineSegments(gridGeo, new THREE.LineBasicMaterial({
      color: T.border, transparent: true, opacity: 0.2,
    })));

    // ── Build anatomy ──
    const { meshes, pathPoints } = buildProceduralAnatomy(scene);

    // ── Build pathways ──
    const curves = buildPathways(scene, pathPoints.positions);

    // ── Pulses ──
    const outboundPulses = createPulses(scene, curves.outbound.curve, T.outbound, 6);
    const returnPulses = createPulses(scene, curves.ret.curve, T.ret, 6);

    // ── Stratum labels (sprite text) ──
    const labelSprites = [];
    if (true) {
      const makeLabel = (text, position, color) => {
        const canvas = document.createElement("canvas");
        canvas.width = 256;
        canvas.height = 48;
        const ctx = canvas.getContext("2d");
        ctx.font = "600 20px Inter, sans-serif";
        ctx.fillStyle = color;
        ctx.globalAlpha = 0.5;
        ctx.fillText(text, 4, 32);
        const tex = new THREE.CanvasTexture(canvas);
        tex.minFilter = THREE.LinearFilter;
        const spriteMat = new THREE.SpriteMaterial({ map: tex, transparent: true });
        const sprite = new THREE.Sprite(spriteMat);
        sprite.position.copy(position);
        sprite.scale.set(1.5, 0.3, 1);
        scene.add(sprite);
        labelSprites.push(sprite);
        return sprite;
      };
      makeLabel("SUPRASPINAL", new THREE.Vector3(1.2, 4.2, 0), T.supra);
      makeLabel("SPINAL", new THREE.Vector3(1.0, 2.8, 0), T.spinal);
      makeLabel("REFLEX", new THREE.Vector3(1.0, 1.2, 0), T.reflex);
    }

    // ── Compartment labels ──
    const compLabels = [];
    Object.entries(COMPARTMENTS).forEach(([id, comp]) => {
      const pos = pathPoints.positions[id];
      if (!pos) return;
      const canvas = document.createElement("canvas");
      canvas.width = 200;
      canvas.height = 36;
      const ctx = canvas.getContext("2d");
      ctx.font = "500 14px Inter, sans-serif";
      ctx.fillStyle = comp.color;
      ctx.globalAlpha = 0.7;
      ctx.fillText(comp.label, 2, 22);
      const tex = new THREE.CanvasTexture(canvas);
      tex.minFilter = THREE.LinearFilter;
      const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true }));
      sprite.position.set(pos.x + 0.4, pos.y + 0.15, pos.z);
      sprite.scale.set(1.0, 0.2, 1);
      scene.add(sprite);
      compLabels.push(sprite);
    });

    // Store refs for animation
    sceneRef.current = {
      scene, camera, renderer, meshes, curves,
      outboundPulses, returnPulses, pathPoints,
      labelSprites, compLabels,
    };

    // ── Mouse rotation ──
    let angle = 0.6;
    let elevation = 0.35;
    let dragging = false;
    let lastMouse = [0, 0];
    const radius = 6;

    const onDown = e => {
      dragging = true;
      lastMouse = [e.clientX || 0, e.clientY || 0];
    };
    const onMove = e => {
      if (!dragging) return;
      const dx = (e.clientX || 0) - lastMouse[0];
      const dy = (e.clientY || 0) - lastMouse[1];
      angle += dx * 0.005;
      elevation = Math.max(-0.3, Math.min(1.2, elevation - dy * 0.005));
      lastMouse = [e.clientX || 0, e.clientY || 0];
    };
    const onUp = () => { dragging = false; };

    renderer.domElement.addEventListener("mousedown", onDown);
    renderer.domElement.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);

    // ── Resize ──
    const onResize = () => {
      const nw = el.clientWidth;
      const nh = el.clientHeight;
      camera.aspect = nw / nh;
      camera.updateProjectionMatrix();
      renderer.setSize(nw, nh);
    };
    window.addEventListener("resize", onResize);

    // ── Animation state (mutable, read by the loop) ──
    const animState = { armId: "intact", playing: true, clock: 0 };
    sceneRef.current.animState = animState;

    // ── Animation loop ──
    let prevT = performance.now();

    const animate = (now) => {
      frameRef.current = requestAnimationFrame(animate);
      const dt = Math.min((now - prevT) / 1000, 0.05);
      prevT = now;

      if (animState.playing) animState.clock += dt;
      const t = animState.clock;

      const currentArm = ARMS.find(a => a.id === animState.armId) || ARMS[0];
      const isClosed = currentArm.closure === "closed";
      const rate = currentArm.tonicRate;

      // ── Camera orbit ──
      if (!dragging) angle += 0.001;
      camera.position.set(
        radius * Math.cos(elevation) * Math.sin(angle),
        2.2 + radius * Math.sin(elevation),
        radius * Math.cos(elevation) * Math.cos(angle),
      );
      camera.lookAt(0, 2, 0);

      // ── Muscle oscillation ──
      const fibreMesh = meshes.fibre;
      if (fibreMesh) {
        if (isClosed && rate > 0) {
          // Bounded oscillation — the limit cycle of Corollary 2.4
          const amp = 0.08 * (rate / 15.7);
          const scaleY = 1 + amp * Math.sin(2 * Math.PI * rate * t * 0.05);
          const scaleX = 1 - amp * 0.3 * Math.sin(2 * Math.PI * rate * t * 0.05);
          fibreMesh.scale.set(scaleX, scaleY, scaleX);
          fibreMesh.material.emissive.setHex(0x200010);
          fibreMesh.material.opacity = 0.85;
        } else {
          // Open — divergence. The muscle doesn't oscillate; it drifts.
          const drift = Math.min(t * 0.15, 1.5);
          fibreMesh.scale.set(1 + drift * 0.3, 1 - drift * 0.2, 1 + drift * 0.3);
          fibreMesh.material.emissive.setHex(0x401010);
          fibreMesh.material.opacity = Math.max(0.3, 0.85 - drift * 0.3);
        }
      }

      // ── Cortex oscillation (supraspinal rhythm) ──
      if (meshes.cortex) {
        const cortexAmp = isClosed ? 0.03 : 0.01;
        const cortexRate = 0.3; // supraspinal band ~0.3 Hz
        meshes.cortex.scale.setScalar(1 + cortexAmp * Math.sin(2 * Math.PI * cortexRate * t));
      }

      // ── Spinal node ──
      if (meshes.spinal_in) {
        const spAmp = isClosed ? 0.05 : 0.02;
        meshes.spinal_in.scale.setScalar(1 + spAmp * Math.sin(2 * Math.PI * 1.2 * t));
      }

      // ── Motor neuron flash (firing) ──
      if (meshes.alpha_mn) {
        if (isClosed && rate > 0) {
          const flash = Math.pow(Math.max(0, Math.sin(2 * Math.PI * rate * t * 0.05)), 8);
          meshes.alpha_mn.material.emissiveIntensity = 0.1 + flash * 0.8;
          meshes.alpha_mn.material.emissive.setHex(0x5020aa);
        } else {
          meshes.alpha_mn.material.emissiveIntensity = 0.05;
          meshes.alpha_mn.material.emissive.setHex(0x100020);
        }
      }

      // ── Outbound pulses (always active — motor output preserved) ──
      outboundPulses.forEach(p => {
        p.userData.phase = (p.userData.phase + dt * 0.3) % 1;
        const pt = curves.outbound.curve.getPoint(p.userData.phase);
        p.position.copy(pt);
        const glow = 0.5 + 0.5 * Math.sin(p.userData.phase * Math.PI);
        p.material.opacity = glow * 0.9;
        p.scale.setScalar(0.6 + glow * 0.4);
      });

      // ── Return pulses (active only when closed) ──
      const returnActive = isClosed;
      const cutFraction = (() => {
        if (!currentArm.returnCutAt) return 1.0;
        const cutIdx = RETURN_PATH.indexOf(currentArm.returnCutAt);
        if (cutIdx < 0) return 1.0;
        return cutIdx / (RETURN_PATH.length - 1);
      })();

      returnPulses.forEach(p => {
        if (returnActive) {
          p.userData.phase = (p.userData.phase + dt * 0.3) % 1;
          const pt = curves.ret.curve.getPoint(p.userData.phase);
          p.position.copy(pt);
          const glow = 0.5 + 0.5 * Math.sin(p.userData.phase * Math.PI);
          p.material.opacity = glow * 0.9;
          p.material.color.setStyle(T.ret);
          p.material.emissive.setStyle(T.ret);
          p.visible = true;
        } else {
          // Pulses stop at the cut point and fade
          if (p.userData.phase > cutFraction) {
            // Stuck at cut
            const pt = curves.ret.curve.getPoint(cutFraction);
            p.position.copy(pt);
            p.material.opacity = 0.15 + 0.1 * Math.sin(t * 3);
            p.material.color.setStyle(T.open);
            p.material.emissive.setStyle(T.open);
          } else {
            p.userData.phase = (p.userData.phase + dt * 0.3);
            if (p.userData.phase > cutFraction) p.userData.phase = cutFraction;
            const pt = curves.ret.curve.getPoint(p.userData.phase);
            p.position.copy(pt);
            p.material.opacity = 0.6;
            p.material.color.setStyle(T.open);
            p.material.emissive.setStyle(T.open);
          }
          p.visible = true;
        }
      });

      // ── Return path tube opacity ──
      if (curves.ret.mat) {
        curves.ret.mat.opacity = returnActive ? 0.5 : 0.12;
        curves.ret.mat.color.setStyle(returnActive ? T.ret : T.open);
        curves.ret.mat.emissive.setStyle(returnActive ? T.ret : T.open);
        curves.ret.mat.emissiveIntensity = returnActive ? 0.15 : 0.05;
      }

      // ── Spindle activity ──
      if (meshes.spindle) {
        if (isClosed) {
          meshes.spindle.rotation.z = 0.5 + 0.2 * Math.sin(2 * Math.PI * rate * t * 0.05);
          meshes.spindle.material.opacity = 0.85;
        } else {
          meshes.spindle.material.opacity = 0.3;
        }
      }

      // Update time display
      setTime(t);

      renderer.render(scene, camera);
    };

    frameRef.current = requestAnimationFrame(animate);

    return () => {
      cancelAnimationFrame(frameRef.current);
      renderer.dispose();
      window.removeEventListener("mouseup", onUp);
      window.removeEventListener("resize", onResize);
      if (el.contains(renderer.domElement)) el.removeChild(renderer.domElement);
    };
  }, []);

  // ── Sync arm/play state to animation ──
  useEffect(() => {
    if (sceneRef.current?.animState) {
      sceneRef.current.animState.armId = activeArm;
      sceneRef.current.animState.clock = 0; // reset on arm change
    }
  }, [activeArm]);

  useEffect(() => {
    if (sceneRef.current?.animState) {
      sceneRef.current.animState.playing = isPlaying;
    }
  }, [isPlaying]);

  // ── Label visibility ──
  useEffect(() => {
    if (!sceneRef.current) return;
    sceneRef.current.compLabels?.forEach(s => { s.visible = showLabels; });
    sceneRef.current.labelSprites?.forEach(s => { s.visible = showLabels; });
  }, [showLabels]);

  return (
    <div style={{ width: "100%", height: "100vh", display: "flex", flexDirection: "column", background: T.bg, color: T.text, fontFamily: "'Inter', system-ui, sans-serif" }}>

      {/* ── Header ── */}
      <div style={{ height: 40, background: T.panel, borderBottom: `1px solid ${T.border}`, display: "flex", alignItems: "center", padding: "0 16px", gap: 16, flexShrink: 0 }}>
        <span style={{ fontSize: 12, fontWeight: 700, color: T.keyword, letterSpacing: 1.5 }}>VITRUVIUS</span>
        <span style={{ fontSize: 11, color: T.dim }}>3D Anatomy View</span>
        <div style={{ flex: 1 }} />
        <label style={{ fontSize: 11, color: T.dim, display: "flex", alignItems: "center", gap: 4, cursor: "pointer" }}>
          <input type="checkbox" checked={showLabels} onChange={e => setShowLabels(e.target.checked)} style={{ accentColor: T.keyword }} />
          Labels
        </label>
        <button onClick={() => setIsPlaying(p => !p)} style={{
          background: "transparent", border: `1px solid ${T.border}`, color: T.text,
          padding: "3px 12px", borderRadius: 3, fontSize: 11, cursor: "pointer", fontFamily: "inherit",
        }}>
          {isPlaying ? "⏸ Pause" : "▶ Play"}
        </button>
      </div>

      {/* ── Main ── */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>

        {/* 3D viewport */}
        <div ref={mountRef} style={{ flex: 1, position: "relative" }}>
          {/* Time overlay */}
          <div style={{ position: "absolute", top: 12, left: 12, fontSize: 11, color: T.dim, fontFamily: "monospace", zIndex: 2, pointerEvents: "none" }}>
            t = {time.toFixed(2)}s
          </div>
        </div>

        {/* ── Side panel ── */}
        <div style={{ width: 280, background: T.panel, borderLeft: `1px solid ${T.border}`, display: "flex", flexDirection: "column", flexShrink: 0, overflow: "auto" }}>

          {/* Arm selector */}
          <div style={{ padding: 12, borderBottom: `1px solid ${T.border}` }}>
            <div style={{ fontSize: 10, color: T.dim, marginBottom: 8, fontWeight: 600, letterSpacing: 1 }}>EXPERIMENT ARM</div>
            {ARMS.map(a => (
              <button key={a.id} onClick={() => setActiveArm(a.id)} style={{
                display: "block", width: "100%", textAlign: "left",
                padding: "6px 10px", marginBottom: 4, borderRadius: 4, border: "none",
                background: activeArm === a.id ? `${a.closure === "open" ? T.open : T.closed}15` : "transparent",
                color: activeArm === a.id ? (a.closure === "open" ? T.open : T.closed) : T.dim,
                cursor: "pointer", fontSize: 12, fontFamily: "inherit",
                borderLeft: activeArm === a.id ? `3px solid ${a.closure === "open" ? T.open : T.closed}` : "3px solid transparent",
              }}>
                <span style={{ fontWeight: 600 }}>{a.closure === "open" ? "◇" : "●"} {a.label}</span>
              </button>
            ))}
          </div>

          {/* Observables */}
          <div style={{ padding: 12, borderBottom: `1px solid ${T.border}` }}>
            <div style={{ fontSize: 10, color: T.dim, marginBottom: 8, fontWeight: 600, letterSpacing: 1 }}>OBSERVABLES</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: "4px 12px", fontSize: 12, fontFamily: "monospace" }}>
              <span style={{ color: T.dim }}>closure</span>
              <span style={{ color: arm.closure === "open" ? T.open : T.closed, fontWeight: 600, textAlign: "right" }}>{arm.closure}</span>
              <span style={{ color: T.dim }}>tonic_rate</span>
              <span style={{ color: T.text, textAlign: "right" }}>{arm.tonicRate > 0 ? `${arm.tonicRate} Hz` : "—"}</span>
              <span style={{ color: T.dim }}>coupling</span>
              <span style={{ color: T.text, textAlign: "right" }}>{arm.coupling.toFixed(3)}</span>
              <span style={{ color: T.dim }}>cop_rms</span>
              <span style={{ color: T.text, textAlign: "right" }}>{arm.copRms.toFixed(1)} mm</span>
            </div>
          </div>

          {/* Aperture report */}
          <div style={{ padding: 12, borderBottom: `1px solid ${T.border}` }}>
            <div style={{ fontSize: 10, color: T.dim, marginBottom: 8, fontWeight: 600, letterSpacing: 1 }}>APERTURE REPORT</div>
            <div style={{
              padding: "8px 10px", borderRadius: 4, fontSize: 11, lineHeight: 1.5,
              background: arm.closure === "open" ? `${T.open}10` : `${T.closed}08`,
              color: arm.closure === "open" ? T.open : T.closed,
              border: `1px solid ${arm.closure === "open" ? T.open : T.closed}22`,
              fontFamily: "monospace",
            }}>
              {arm.description}
            </div>
          </div>

          {/* Circuit legend */}
          <div style={{ padding: 12 }}>
            <div style={{ fontSize: 10, color: T.dim, marginBottom: 8, fontWeight: 600, letterSpacing: 1 }}>PATHWAYS</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 11 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div style={{ width: 20, height: 3, background: T.outbound, borderRadius: 2 }} />
                <span style={{ color: T.outbound }}>Outbound (efferent)</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div style={{ width: 20, height: 3, background: arm.closure === "open" ? T.open : T.ret, borderRadius: 2, opacity: arm.closure === "open" ? 0.4 : 1 }} />
                <span style={{ color: arm.closure === "open" ? T.open : T.ret }}>
                  Return (afferent){arm.closure === "open" ? " — severed" : ""}
                </span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div style={{ width: 8, height: 8, borderRadius: "50%", background: T.outbound }} />
                <span style={{ color: T.dim }}>Outbound pulse</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div style={{ width: 8, height: 8, borderRadius: "50%", background: arm.closure === "open" ? T.open : T.ret }} />
                <span style={{ color: T.dim }}>
                  Return pulse{arm.closure === "open" ? " (blocked)" : ""}
                </span>
              </div>
            </div>
          </div>

          {/* GLB integration note */}
          <div style={{ padding: 12, marginTop: "auto", borderTop: `1px solid ${T.border}` }}>
            <div style={{ fontSize: 9, color: T.muted, lineHeight: 1.5 }}>
              Procedural geometry. Replace buildProceduralAnatomy() with GLTFLoader and map COMPARTMENT entries to GLB mesh group names.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}