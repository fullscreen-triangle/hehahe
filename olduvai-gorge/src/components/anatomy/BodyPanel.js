import dynamic from "next/dynamic";
import { motion, AnimatePresence } from "framer-motion";
import { useBody } from "@/lib/bodyState";
import { REGIONS, COMPARTMENT } from "./bodyRegions";
import HumanBody from "./HumanBody";

const BodyGLB = dynamic(() => import("./BodyGLB"), { ssr: false });

const GLB_OPTIONS = [
  { file: "model_huma_anatom.glb",                         label: "full anatomy" },
  { file: "walker.glb",                                    label: "walking" },
  { file: "bust.glb",                                      label: "bust" },
  { file: "thorax_and_abdomen_a_few_important_muscles.glb",label: "thorax & abdomen" },
  { file: "upper-body-explosion.glb",                      label: "upper body (exploded)" },
  { file: "windows_3d_viewer_flexing_arm.glb",             label: "flexing arm" },
  { file: "foot__ankle.glb",                               label: "foot & ankle" },
  { file: "FastRun.glb",                                   label: "fast run" },
  { file: "crouched_to_sprinting.glb",                     label: "crouch → sprint" },
  { file: "idle_to_sprint.glb",                            label: "idle → sprint" },
  { file: "run_to_flip.glb",                               label: "run → flip" },
  { file: "laying.glb",                                    label: "laying" },
  { file: "xbot_multiple_animations.glb",                  label: "xbot animations" },
];

/**
 * The cross-page anatomy tool. Lives in _app.js so it's present
 * everywhere. Slides out from the right edge; three tabs: Surface
 * SVG, Internal SVG, and 3D GLB viewer.
 *
 * Activation state lives in the BodyState context; any page can push
 * per-compartment intensities that light up the relevant parts.
 */
export default function BodyPanel() {
  const {
    compartments, setCompartment,
    panelOpen, setPanelOpen,
    view, setView,
    hover, focusGLB, setFocusGLB,
  } = useBody();

  const hoverMeta = hover ? REGIONS[hover] : null;

  return (
    <>
      {/* Handle — always visible */}
      <motion.button
        onClick={() => setPanelOpen(!panelOpen)}
        className="fixed right-0 top-1/2 -translate-y-1/2 z-40 bg-darkSoft border border-darkBorder border-r-0 px-2 py-3 mono text-[10px] uppercase tracking-widest text-muted hover:text-primary transition-colors"
        style={{ writingMode: "vertical-rl" }}
        aria-label="Toggle anatomy panel"
      >
        {panelOpen ? "close anatomy ›" : "‹ anatomy"}
      </motion.button>

      <AnimatePresence>
        {panelOpen && (
          <motion.aside
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", stiffness: 260, damping: 30 }}
            className="fixed right-0 top-0 bottom-0 z-40 w-[420px] sm:w-full bg-dark/95 backdrop-blur-md border-l border-darkBorder flex flex-col"
          >
            <header className="px-5 py-4 border-b border-darkBorder flex items-center justify-between">
              <div>
                <div className="mono text-[10px] uppercase tracking-[0.3em] text-primary/80">
                  body tracker
                </div>
                <div className="mono text-sm text-light mt-1">
                  live compartment readout
                </div>
              </div>
              <button
                onClick={() => setPanelOpen(false)}
                className="mono text-xs text-muted hover:text-light"
                aria-label="Close"
              >
                ✕
              </button>
            </header>

            {/* Tabs */}
            <div className="flex border-b border-darkBorder">
              {["surface", "internal", "3d"].map((v) => (
                <button
                  key={v}
                  onClick={() => setView(v)}
                  className={`flex-1 py-3 mono text-[10px] uppercase tracking-widest transition-colors ${
                    view === v
                      ? "text-primary border-b border-primary bg-darkSoft"
                      : "text-muted hover:text-light"
                  }`}
                >
                  {v}
                </button>
              ))}
            </div>

            {/* Viewport */}
            <div className="relative flex-1 min-h-0 overflow-hidden">
              {view === "surface" && (
                <div className="absolute inset-0 flex items-center justify-center p-2">
                  <HumanBody side="surface" />
                </div>
              )}
              {view === "internal" && (
                <div className="absolute inset-0 flex items-center justify-center p-2">
                  <HumanBody side="internal" />
                </div>
              )}
              {view === "3d" && (
                <div className="absolute inset-0">
                  <BodyGLB glb={focusGLB || "model_huma_anatom.glb"} />
                  <div className="absolute top-2 left-2 right-2 flex flex-wrap gap-1">
                    {GLB_OPTIONS.slice(0, 6).map((o) => (
                      <button
                        key={o.file}
                        onClick={() => setFocusGLB(o.file)}
                        className={`mono text-[9px] uppercase tracking-wider px-2 py-1 border transition-colors ${
                          (focusGLB || "model_huma_anatom.glb") === o.file
                            ? "border-primary text-primary bg-dark/70"
                            : "border-darkBorder text-muted hover:text-light bg-dark/70"
                        }`}
                      >
                        {o.label}
                      </button>
                    ))}
                  </div>
                  <details className="absolute bottom-12 left-2 mono text-[10px] bg-dark/80 border border-darkBorder px-2 py-1">
                    <summary className="text-muted cursor-pointer">more models</summary>
                    <div className="flex flex-col gap-1 mt-2">
                      {GLB_OPTIONS.slice(6).map((o) => (
                        <button
                          key={o.file}
                          onClick={() => setFocusGLB(o.file)}
                          className={`text-left ${
                            focusGLB === o.file ? "text-primary" : "text-light hover:text-primary"
                          }`}
                        >
                          {o.label}
                        </button>
                      ))}
                    </div>
                  </details>
                </div>
              )}
            </div>

            {/* Hover info */}
            <div className="px-5 py-3 border-t border-darkBorder min-h-[72px]">
              {hoverMeta ? (
                <>
                  <div className="flex items-center gap-2 mb-1">
                    <span
                      className="inline-block w-2 h-2 rounded-full"
                      style={{
                        backgroundColor:
                          COMPARTMENT[hoverMeta.compartment]?.colour,
                      }}
                    />
                    <span className="mono text-xs uppercase tracking-wider text-light">
                      {hoverMeta.name}
                    </span>
                    <span
                      className="mono text-[10px] uppercase tracking-widest"
                      style={{
                        color: COMPARTMENT[hoverMeta.compartment]?.colour,
                      }}
                    >
                      {COMPARTMENT[hoverMeta.compartment]?.label}
                    </span>
                  </div>
                  <div className="mono text-[11px] text-muted leading-snug">
                    {hoverMeta.info}
                  </div>
                  {hoverMeta.glb && view !== "3d" && (
                    <button
                      onClick={() => {
                        setFocusGLB(hoverMeta.glb);
                        setView("3d");
                      }}
                      className="mono text-[10px] text-primary hover:underline mt-2"
                    >
                      open in 3D →
                    </button>
                  )}
                </>
              ) : (
                <div className="mono text-[10px] uppercase tracking-widest text-muted">
                  hover any region — or drag the 3D model
                </div>
              )}
            </div>

            {/* Compartment sliders */}
            <div className="px-5 py-4 border-t border-darkBorder">
              <div className="mono text-[10px] uppercase tracking-widest text-muted mb-3">
                compartment activation
              </div>
              <div className="space-y-2">
                {Object.entries(COMPARTMENT).map(([key, meta]) => (
                  <label key={key} className="flex items-center gap-2">
                    <span className="mono text-[10px] uppercase tracking-wider text-light w-20">
                      {meta.label}
                    </span>
                    <input
                      type="range"
                      min={0}
                      max={1}
                      step={0.01}
                      value={compartments[key] ?? 0}
                      onChange={(e) =>
                        setCompartment(key, parseFloat(e.target.value))
                      }
                      className="flex-1"
                      style={{ accentColor: meta.colour }}
                    />
                    <span
                      className="mono text-[9px] w-8 text-right"
                      style={{ color: meta.colour }}
                    >
                      {(compartments[key] ?? 0).toFixed(2)}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>
    </>
  );
}
