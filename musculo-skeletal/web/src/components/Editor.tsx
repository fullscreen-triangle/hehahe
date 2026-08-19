/**
 * Editor with syntax highlighting, diagnostic gutter markers, inline
 * squiggles, hover explanations, and keyword/observable completion.
 *
 * The diagnostics come from the real checker, so a squiggle under an
 * observable means that observable is genuinely absent from the registry,
 * not that a mock said so.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Diagnostic } from "../lang/checker";
import { KEYWORDS, tokenizeForHighlight } from "../lang/lexer";
import { OBSERVABLES } from "../lang/observables";
import { MONO, type Theme } from "../theme";

const LH = 20;
const PAD = 10;
const GUTTER = 52;

interface Props {
  code: string;
  onChange: (s: string) => void;
  diagnostics: Diagnostic[];
  theme: Theme;
  parseError?: string;
  parseLine?: number;
}

function tokenColor(kind: string, text: string, T: Theme) {
  switch (kind) {
    case "comment": return T.comment;
    case "string": return T.string;
    case "number":
    case "quantity": return T.number;
    case "keyword": return T.keyword;
    case "arrow": return T.accent;
    case "punct": return T.punct;
    default:
      return OBSERVABLES.has(text) ? T.fn : T.text;
  }
}

export function Editor({ code, onChange, diagnostics, theme: T, parseError, parseLine }: Props) {
  const taRef = useRef<HTMLTextAreaElement>(null);
  const preRef = useRef<HTMLPreElement>(null);
  const gutRef = useRef<HTMLDivElement>(null);
  const [scroll, setScroll] = useState(0);
  const [cursorLine, setCursorLine] = useState(1);
  const [hover, setHover] = useState<{ x: number; y: number; text: string } | null>(null);
  const [complete, setComplete] = useState<{ items: string[]; index: number } | null>(null);

  const lines = useMemo(() => code.split("\n"), [code]);

  /** Diagnostics grouped by line, worst severity first. */
  const byLine = useMemo(() => {
    const m = new Map<number, Diagnostic[]>();
    for (const d of diagnostics) {
      if (!d.span) continue;
      const arr = m.get(d.span.line) ?? [];
      arr.push(d);
      m.set(d.span.line, arr);
    }
    if (parseError && parseLine) {
      const arr = m.get(parseLine) ?? [];
      arr.push({ severity: "error", rule: "parse", message: parseError });
      m.set(parseLine, arr);
    }
    for (const [, arr] of m) {
      arr.sort((a, b) =>
        (a.severity === "error" ? 0 : a.severity === "warning" ? 1 : 2) -
        (b.severity === "error" ? 0 : b.severity === "warning" ? 1 : 2));
    }
    return m;
  }, [diagnostics, parseError, parseLine]);

  const highlighted = useMemo(() => {
    const toks = tokenizeForHighlight(code);
    const perLine = new Map<number, typeof toks>();
    for (const t of toks) {
      const arr = perLine.get(t.line) ?? [];
      arr.push(t);
      perLine.set(t.line, arr);
    }
    return lines.map((raw, i) => {
      const ln = i + 1;
      const ts = perLine.get(ln) ?? [];
      if (!ts.length) return [<span key="e">{raw || " "}</span>];
      const out: JSX.Element[] = [];
      let col = 0;
      for (const t of ts) {
        const start = t.col - 1;
        if (start > col) out.push(<span key={`g${col}`}>{raw.slice(col, start)}</span>);
        const body = raw.slice(start, start + (t.end - t.start));
        out.push(
          <span key={`t${start}`} style={{
            color: tokenColor(t.kind, t.text, T),
            fontWeight: t.kind === "keyword" ? 600 : 400,
            fontStyle: t.kind === "comment" ? "italic" : "normal",
          }}>{body}</span>,
        );
        col = start + (t.end - t.start);
      }
      if (col < raw.length) out.push(<span key="tail">{raw.slice(col)}</span>);
      return out;
    });
  }, [code, lines, T]);

  const sync = useCallback(() => {
    const ta = taRef.current;
    if (!ta) return;
    setScroll(ta.scrollTop);
    if (preRef.current) {
      preRef.current.scrollTop = ta.scrollTop;
      preRef.current.scrollLeft = ta.scrollLeft;
    }
    if (gutRef.current) gutRef.current.scrollTop = ta.scrollTop;
  }, []);

  const updateCursor = useCallback(() => {
    const ta = taRef.current;
    if (!ta) return;
    setCursorLine(code.slice(0, ta.selectionStart).split("\n").length);
  }, [code]);

  /** Completion over keywords and registry observables. */
  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    const ta = e.currentTarget;

    if (complete) {
      if (e.key === "ArrowDown") { e.preventDefault(); setComplete({ ...complete, index: (complete.index + 1) % complete.items.length }); return; }
      if (e.key === "ArrowUp") { e.preventDefault(); setComplete({ ...complete, index: (complete.index - 1 + complete.items.length) % complete.items.length }); return; }
      if (e.key === "Enter" || e.key === "Tab") {
        e.preventDefault();
        const pick = complete.items[complete.index];
        const pos = ta.selectionStart;
        const before = code.slice(0, pos);
        const m = /[A-Za-z_][A-Za-z0-9_]*$/.exec(before);
        const from = m ? pos - m[0].length : pos;
        onChange(code.slice(0, from) + pick + code.slice(pos));
        setComplete(null);
        return;
      }
      if (e.key === "Escape") { setComplete(null); return; }
    }

    if (e.key === "Tab") {
      e.preventDefault();
      const pos = ta.selectionStart;
      onChange(code.slice(0, pos) + "  " + code.slice(ta.selectionEnd));
      requestAnimationFrame(() => { ta.selectionStart = ta.selectionEnd = pos + 2; });
      return;
    }

    if (e.ctrlKey && e.key === " ") {
      e.preventDefault();
      const pos = ta.selectionStart;
      const m = /[A-Za-z_][A-Za-z0-9_]*$/.exec(code.slice(0, pos));
      const prefix = m ? m[0] : "";
      const pool = [...KEYWORDS, ...OBSERVABLES.keys()];
      const items = pool.filter((k) => k.startsWith(prefix)).sort().slice(0, 10);
      if (items.length) setComplete({ items, index: 0 });
    }
  };

  const onInput = (v: string) => {
    onChange(v);
    setComplete(null);
  };

  const sevColor = (s: string) =>
    s === "error" ? T.error : s === "warning" ? T.warn : T.note;

  return (
    <div style={{ position: "relative", height: "100%", background: T.editorBg, overflow: "hidden" }}>
      {/* gutter */}
      <div ref={gutRef} style={{
        position: "absolute", left: 0, top: 0, bottom: 0, width: GUTTER,
        background: T.editorBg, borderRight: `1px solid ${T.borderSoft}`,
        overflow: "hidden", zIndex: 2,
      }}>
        <div style={{ paddingTop: PAD, transform: `translateY(${-scroll}px)` }}>
          {lines.map((_, i) => {
            const ln = i + 1;
            const ds = byLine.get(ln);
            const worst = ds?.[0];
            return (
              <div key={i} style={{
                height: LH, display: "flex", alignItems: "center",
                justifyContent: "flex-end", paddingRight: 8, gap: 5,
                fontFamily: MONO, fontSize: 11,
                color: ln === cursorLine ? T.text : T.textMuted,
                background: ln === cursorLine ? T.surfaceBg : "transparent",
              }}>
                {worst && (
                  <span
                    onMouseEnter={(e) => setHover({
                      x: e.clientX, y: e.clientY,
                      text: ds!.map((d) => `${d.severity.toUpperCase()} ${d.rule}: ${d.message}`).join("\n\n"),
                    })}
                    onMouseLeave={() => setHover(null)}
                    style={{ color: sevColor(worst.severity), cursor: "help", fontSize: 10 }}
                  >
                    {worst.severity === "error" ? "●" : worst.severity === "warning" ? "▲" : "○"}
                  </span>
                )}
                <span>{ln}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* highlight layer */}
      <pre ref={preRef} style={{
        position: "absolute", left: GUTTER, top: 0, right: 0, bottom: 0,
        margin: 0, padding: `${PAD}px 12px`, overflow: "hidden",
        whiteSpace: "pre", pointerEvents: "none", zIndex: 1,
        fontFamily: MONO, fontSize: 13, lineHeight: `${LH}px`,
      }}>
        {highlighted.map((parts, i) => {
          const ds = byLine.get(i + 1);
          const worst = ds?.[0];
          return (
            <div key={i} style={{
              height: LH,
              borderBottom: worst
                ? `1.5px solid ${sevColor(worst.severity)}66`
                : "1.5px solid transparent",
              background: i + 1 === cursorLine ? `${T.surfaceBg}88` : "transparent",
            }}>
              {parts}
            </div>
          );
        })}
      </pre>

      {/* input layer */}
      <textarea
        ref={taRef}
        value={code}
        onChange={(e) => onInput(e.target.value)}
        onScroll={sync}
        onKeyUp={updateCursor}
        onClick={updateCursor}
        onKeyDown={onKeyDown}
        spellCheck={false}
        style={{
          position: "absolute", left: GUTTER, top: 0, right: 0, bottom: 0,
          margin: 0, padding: `${PAD}px 12px`, border: "none", outline: "none",
          background: "transparent", color: "transparent", caretColor: T.text,
          fontFamily: MONO, fontSize: 13, lineHeight: `${LH}px`,
          resize: "none", whiteSpace: "pre", overflow: "auto", zIndex: 3,
          tabSize: 2,
        }}
      />

      {/* completion popup */}
      {complete && (
        <div style={{
          position: "absolute", left: GUTTER + 24, top: PAD + cursorLine * LH,
          background: T.panelBg, border: `1px solid ${T.border}`, borderRadius: 4,
          zIndex: 10, minWidth: 200, boxShadow: "0 6px 20px rgba(0,0,0,0.28)",
        }}>
          {complete.items.map((it, i) => {
            const spec = OBSERVABLES.get(it);
            return (
              <div key={it} style={{
                padding: "4px 10px", fontFamily: MONO, fontSize: 12,
                background: i === complete.index ? T.surfaceBg : "transparent",
                color: spec ? T.fn : T.keyword,
                display: "flex", justifyContent: "space-between", gap: 12,
              }}>
                <span>{it}</span>
                {spec && <span style={{ color: T.textMuted, fontSize: 10 }}>{spec.unit}</span>}
              </div>
            );
          })}
        </div>
      )}

      {hover && (
        <div style={{
          position: "fixed", left: Math.min(hover.x + 12, window.innerWidth - 460),
          top: hover.y + 14, maxWidth: 440, padding: "8px 11px",
          background: T.panelBg, border: `1px solid ${T.border}`, borderRadius: 4,
          color: T.text, fontFamily: MONO, fontSize: 11, lineHeight: 1.5,
          zIndex: 60, whiteSpace: "pre-wrap", boxShadow: "0 8px 26px rgba(0,0,0,0.3)",
        }}>
          {hover.text}
        </div>
      )}
    </div>
  );
}
