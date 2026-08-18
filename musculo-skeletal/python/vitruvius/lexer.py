"""Lexer for Vitruvius (.vvs).

Token classes follow Definition 3.1 of the specification, extended with the
keywords required by the E1/E3/E4/E6 extensions (template, reroute, through,
phase, from, bilateral, antagonist, agonist, shared).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto


class Tok(Enum):
    KEYWORD = auto()
    IDENT = auto()
    NUMBER = auto()
    QUANTITY = auto()
    STRING = auto()
    PUNCT = auto()
    ARROW = auto()
    EOF = auto()


KEYWORDS = frozenset(
    {
        # core (spec Definition 3.1)
        "circuit", "compartment", "capacitance", "element", "conducts",
        "outbound", "return", "stratum", "delay", "gain", "floor",
        "derived", "event", "type", "experiment", "intact", "lesion",
        "observe", "without", "with", "scaling", "noise", "across",
        "compare", "report", "let", "module", "import",
        "reflex", "spinal", "supraspinal",
        # E1 templates
        "template",
        # E3 reroute
        "reroute", "through",
        # E4 phases
        "phase", "from",
        # E6 antagonist pairs
        "antagonist", "agonist", "shared",
    }
)

# Unit suffixes recognised directly after a numeric literal.
UNITS = ("ms", "s", "Hz", "uF", "mF", "nF", "pF", "F", "N", "mm", "m", "W", "C")

STRATA = ("reflex", "spinal", "supraspinal")


@dataclass(frozen=True)
class Token:
    kind: Tok
    text: str
    line: int
    col: int
    value: object = None
    unit: str | None = None

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"{self.kind.name}({self.text!r})@{self.line}:{self.col}"


class LexError(Exception):
    def __init__(self, msg: str, line: int, col: int):
        super().__init__(f"{msg} at line {line}, col {col}")
        self.line = line
        self.col = col


_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
# Longest-match on the unit alternation so `mF` is not lexed as `m` then `F`.
_NUM_RE = re.compile(
    r"(?P<num>[0-9]+(?:\.[0-9]*)?(?:[eE][-+]?[0-9]+)?)"
    r"(?:\s*(?P<unit>" + "|".join(sorted(UNITS, key=len, reverse=True)) + r")\b)?"
)

PUNCT = frozenset("{}()[],;:=.")


def tokenize(src: str) -> list[Token]:
    """Return the token stream for `src`, ending with a single EOF token."""
    toks: list[Token] = []
    i, line, bol = 0, 1, 0
    n = len(src)

    while i < n:
        ch = src[i]

        if ch == "\n":
            line += 1
            i += 1
            bol = i
            continue
        if ch in " \t\r":
            i += 1
            continue

        # Comments run from `--` to end of line. Guard against `->`.
        if ch == "-" and src.startswith("--", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
            continue

        col = i - bol + 1

        if src.startswith("->", i):
            toks.append(Token(Tok.ARROW, "->", line, col))
            i += 2
            continue

        if ch == '"':
            j = i + 1
            buf = []
            while j < n and src[j] != '"':
                if src[j] == "\\" and j + 1 < n:
                    buf.append(src[j + 1])
                    j += 2
                    continue
                if src[j] == "\n":
                    raise LexError("unterminated string", line, col)
                buf.append(src[j])
                j += 1
            if j >= n:
                raise LexError("unterminated string", line, col)
            toks.append(Token(Tok.STRING, "".join(buf), line, col, value="".join(buf)))
            i = j + 1
            continue

        if ch.isdigit() or (ch == "." and i + 1 < n and src[i + 1].isdigit()):
            m = _NUM_RE.match(src, i)
            if not m:
                raise LexError("malformed number", line, col)
            raw = m.group("num")
            unit = m.group("unit")
            val = float(raw)
            kind = Tok.QUANTITY if unit else Tok.NUMBER
            toks.append(Token(kind, m.group(0), line, col, value=val, unit=unit))
            i = m.end()
            continue

        if ch.isalpha() or ch == "_":
            m = _IDENT_RE.match(src, i)
            assert m is not None
            word = m.group(0)
            kind = Tok.KEYWORD if word in KEYWORDS else Tok.IDENT
            toks.append(Token(kind, word, line, col))
            i = m.end()
            continue

        if ch in PUNCT:
            toks.append(Token(Tok.PUNCT, ch, line, col))
            i += 1
            continue

        raise LexError(f"unexpected character {ch!r}", line, col)

    toks.append(Token(Tok.EOF, "", line, i - bol + 1))
    return toks
