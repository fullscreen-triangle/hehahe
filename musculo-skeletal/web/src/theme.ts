/** Design tokens. Two themes; the light one is what the manuscript uses. */

export interface Theme {
  bg: string; editorBg: string; panelBg: string; surfaceBg: string;
  border: string; borderSoft: string;
  text: string; textDim: string; textMuted: string;
  keyword: string; string: string; comment: string; number: string;
  type: string; fn: string; punct: string;
  accent: string; closed: string; open: string;
  reflex: string; spinal: string; supra: string;
  gridLine: string; gridText: string;
  error: string; warn: string; note: string; ok: string;
  series: string[];
}

export const DARK: Theme = {
  bg: "#1a1b26", editorBg: "#16161e", panelBg: "#1f2028", surfaceBg: "#24283b",
  border: "#2f3348", borderSoft: "#242739",
  text: "#c0caf5", textDim: "#7c85ad", textMuted: "#4b5273",
  keyword: "#7aa2f7", string: "#9ece6a", comment: "#5b6389", number: "#ff9e64",
  type: "#bb9af7", fn: "#7dcfff", punct: "#7c85ad",
  accent: "#e0af68", closed: "#73daca", open: "#f7768e",
  reflex: "#bb9af7", spinal: "#7dcfff", supra: "#ff9e64",
  gridLine: "#292e42", gridText: "#5b6389",
  error: "#f7768e", warn: "#e0af68", note: "#7dcfff", ok: "#73daca",
  series: ["#7aa2f7", "#f7768e", "#9ece6a", "#e0af68", "#bb9af7", "#7dcfff"],
};

/**
 * Light palette.
 *
 * Retained but no longer wired to anything: the app pins itself to DARK, and
 * a light variant that nothing renders is a variant nobody checks. Kept so
 * the Theme shape stays exercised by a second instance, and so re-enabling a
 * toggle is an edit rather than a rewrite.
 */
export const LIGHT: Theme = {
  bg: "#f4f5f8", editorBg: "#ffffff", panelBg: "#ffffff", surfaceBg: "#eef1f6",
  border: "#d5dae4", borderSoft: "#e6eaf1",
  text: "#1f2430", textDim: "#5b6478", textMuted: "#93a0b5",
  keyword: "#1b6ca8", string: "#3f7a2e", comment: "#93a0b5", number: "#b35a00",
  type: "#7a3fa8", fn: "#0f7a8a", punct: "#5b6478",
  accent: "#b8860b", closed: "#1b6ca8", open: "#c1442e",
  reflex: "#7a3fa8", spinal: "#0f7a8a", supra: "#b35a00",
  gridLine: "#e2e7ef", gridText: "#93a0b5",
  error: "#c1442e", warn: "#b8860b", note: "#0f7a8a", ok: "#1b6ca8",
  series: ["#1b6ca8", "#c1442e", "#3f7a2e", "#b8860b", "#7a3fa8", "#0f7a8a"],
};

export const MONO =
  "'Cascadia Code','JetBrains Mono','Fira Code',ui-monospace,SFMono-Regular,Menlo,monospace";
export const SANS =
  "'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif";
