/**
 * Lexer for Vitruvius (.vvs).
 *
 * Ported from the Python reference implementation. Token positions are
 * retained because the editor turns diagnostics into gutter markers and
 * inline underlines, which requires knowing where a construct starts and
 * ends rather than merely that it exists.
 */

export type TokKind =
  | "keyword"
  | "ident"
  | "number"
  | "quantity"
  | "string"
  | "punct"
  | "arrow"
  | "comment"
  | "eof";

export interface Token {
  kind: TokKind;
  text: string;
  line: number; // 1-based
  col: number; // 1-based
  start: number; // absolute offset
  end: number;
  value?: number;
  unit?: string;
}

export const KEYWORDS = new Set([
  // core
  "circuit", "compartment", "capacitance", "element", "conducts",
  "outbound", "return", "stratum", "delay", "gain", "floor", "derived",
  "event", "type", "experiment", "intact", "lesion", "observe", "without",
  "with", "scaling", "noise", "across", "compare", "report", "let",
  "module", "import", "reflex", "spinal", "supraspinal",
  // E1 templates
  "template",
  // E3 reroute
  "reroute", "through",
  // E4 phases
  "phase", "from",
  // E6 antagonists
  "antagonist", "agonist", "shared",
]);

export const STRATA = ["reflex", "spinal", "supraspinal"] as const;
export type Stratum = (typeof STRATA)[number];

const UNITS = [
  "ms", "s", "Hz", "uF", "mF", "nF", "pF", "F", "N", "mm", "m", "W", "C",
];
// Longest-first so `mF` is not lexed as `m` then `F`.
const UNIT_RE = new RegExp(
  "^(" + [...UNITS].sort((a, b) => b.length - a.length).join("|") + ")\\b",
);

const PUNCT = new Set("{}()[],;:=.");

export class LexError extends Error {
  constructor(msg: string, public line: number, public col: number) {
    super(`${msg} at line ${line}, col ${col}`);
  }
}

export function tokenize(src: string): Token[] {
  const toks: Token[] = [];
  let i = 0;
  let line = 1;
  let bol = 0;
  const n = src.length;

  const push = (
    kind: TokKind,
    start: number,
    end: number,
    extra: Partial<Token> = {},
  ) => {
    toks.push({
      kind,
      text: src.slice(start, end),
      line,
      col: start - bol + 1,
      start,
      end,
      ...extra,
    });
  };

  while (i < n) {
    const ch = src[i];

    if (ch === "\n") {
      line++;
      i++;
      bol = i;
      continue;
    }
    if (ch === " " || ch === "\t" || ch === "\r") {
      i++;
      continue;
    }

    // Comments run to end of line. Guard against `->`.
    if (ch === "-" && src.startsWith("--", i)) {
      const j = src.indexOf("\n", i);
      const end = j < 0 ? n : j;
      push("comment", i, end);
      i = end;
      continue;
    }

    if (src.startsWith("->", i)) {
      push("arrow", i, i + 2);
      i += 2;
      continue;
    }

    if (ch === '"') {
      let j = i + 1;
      while (j < n && src[j] !== '"') {
        if (src[j] === "\n") throw new LexError("unterminated string", line, i - bol + 1);
        j++;
      }
      if (j >= n) throw new LexError("unterminated string", line, i - bol + 1);
      push("string", i, j + 1);
      i = j + 1;
      continue;
    }

    if (/[0-9]/.test(ch) || (ch === "." && /[0-9]/.test(src[i + 1] ?? ""))) {
      const m = /^[0-9]+(?:\.[0-9]*)?(?:[eE][-+]?[0-9]+)?/.exec(src.slice(i));
      if (!m) throw new LexError("malformed number", line, i - bol + 1);
      let j = i + m[0].length;
      const value = parseFloat(m[0]);

      // Optional unit suffix, possibly after whitespace.
      let k = j;
      while (k < n && (src[k] === " " || src[k] === "\t")) k++;
      const um = UNIT_RE.exec(src.slice(k));
      if (um) {
        push("quantity", i, k + um[0].length, { value, unit: um[1] });
        i = k + um[0].length;
      } else {
        push("number", i, j, { value });
        i = j;
      }
      continue;
    }

    if (/[A-Za-z_]/.test(ch)) {
      let j = i;
      while (j < n && /[A-Za-z0-9_]/.test(src[j])) j++;
      const word = src.slice(i, j);
      push(KEYWORDS.has(word) ? "keyword" : "ident", i, j);
      i = j;
      continue;
    }

    if (PUNCT.has(ch)) {
      push("punct", i, i + 1);
      i++;
      continue;
    }

    throw new LexError(`unexpected character '${ch}'`, line, i - bol + 1);
  }

  toks.push({
    kind: "eof",
    text: "",
    line,
    col: i - bol + 1,
    start: i,
    end: i,
  });
  return toks;
}

/** Tokens including comments, for the syntax highlighter. */
export function tokenizeForHighlight(src: string): Token[] {
  try {
    return tokenize(src);
  } catch {
    // Highlighting must survive a partially typed program.
    const out: Token[] = [];
    let i = 0;
    let line = 1;
    let bol = 0;
    while (i < src.length) {
      const ch = src[i];
      if (ch === "\n") {
        line++;
        i++;
        bol = i;
        continue;
      }
      if (/\s/.test(ch)) {
        i++;
        continue;
      }
      if (src.startsWith("--", i)) {
        const j = src.indexOf("\n", i);
        const end = j < 0 ? src.length : j;
        out.push({ kind: "comment", text: src.slice(i, end), line, col: i - bol + 1, start: i, end });
        i = end;
        continue;
      }
      if (/[A-Za-z_]/.test(ch)) {
        let j = i;
        while (j < src.length && /[A-Za-z0-9_]/.test(src[j])) j++;
        const w = src.slice(i, j);
        out.push({ kind: KEYWORDS.has(w) ? "keyword" : "ident", text: w, line, col: i - bol + 1, start: i, end: j });
        i = j;
        continue;
      }
      i++;
    }
    return out;
  }
}
