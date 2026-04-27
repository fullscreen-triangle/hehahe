import { createContext, useContext, useState, useMemo, useCallback } from "react";
import { COMPARTMENT_TO_REGIONS } from "@/components/anatomy/bodyRegions";

/**
 * Global body-activation store.
 *
 * Every page can push per-compartment activation intensities into this
 * store, and the persistent BodyPanel listens. This is the "tool for
 * tracking whatever is happening to which part of the body": the
 * anatomy is a live readout of the current page's computation.
 *
 * Shape:
 *   compartments: { motor, thought, perception, baseline, cardiac, ... }
 *                 each ∈ [0, 1], where 1 = fully saturated glow
 *   regions: optional per-region override; falls back to compartment value
 *   hover: path-id currently hovered (set by BodyPanel itself)
 */

const DEFAULT_COMPARTMENTS = {
  motor: 0.25,
  thought: 0.25,
  perception: 0.25,
  baseline: 0.45,
  cardiac: 0.6,
  respiratory: 0.35,
  visceral: 0.2,
};

const BodyCtx = createContext(null);

export function BodyProvider({ children }) {
  const [compartments, setCompartments] = useState(DEFAULT_COMPARTMENTS);
  const [regions, setRegions] = useState({}); // per-region override
  const [hover, setHover] = useState(null);
  const [panelOpen, setPanelOpen] = useState(false);
  const [view, setView] = useState("surface"); // surface | internal | 3d
  const [focusGLB, setFocusGLB] = useState(null);

  const setCompartment = useCallback((k, v) => {
    setCompartments((prev) => ({ ...prev, [k]: v }));
  }, []);

  const setAll = useCallback((obj) => {
    setCompartments((prev) => ({ ...prev, ...obj }));
  }, []);

  // Resolve the activation value for a specific region id.
  const regionIntensity = useCallback(
    (id) => {
      if (regions[id] !== undefined) return regions[id];
      // Look up the compartment
      for (const [compName, ids] of Object.entries(COMPARTMENT_TO_REGIONS)) {
        if (ids.includes(id)) return compartments[compName] ?? 0;
      }
      return 0;
    },
    [regions, compartments]
  );

  const value = useMemo(
    () => ({
      compartments,
      setCompartment,
      setAll,
      regions,
      setRegions,
      hover,
      setHover,
      panelOpen,
      setPanelOpen,
      view,
      setView,
      focusGLB,
      setFocusGLB,
      regionIntensity,
    }),
    [compartments, regions, hover, panelOpen, view, focusGLB, setCompartment, setAll, regionIntensity]
  );

  return <BodyCtx.Provider value={value}>{children}</BodyCtx.Provider>;
}

export function useBody() {
  const ctx = useContext(BodyCtx);
  if (!ctx) throw new Error("useBody must be used inside <BodyProvider>");
  return ctx;
}
