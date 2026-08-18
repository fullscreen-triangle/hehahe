"""Command-line driver.

    python -m vitruvius run experiments/01_stroke_umn_lmn.vvs
    python -m vitruvius check experiments/02_spinal_cord_injury.vvs
    python -m vitruvius table experiments/05_tremor_classification.vvs \
        --observables closure_index coupling_index type_separation
    python -m vitruvius observables
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .backend import Backend
from .checker import check
from .observables import OBSERVABLES
from .parser import parse
from .report import report, summary_table
from .runtime import Runtime


def _load(path: str):
    src = Path(path).read_text(encoding="utf-8")
    prog = parse(src)
    return prog, check(prog)


def cmd_check(args) -> int:
    _, res = _load(args.file)
    for d in res.diagnostics:
        print(d)
    if res.ok:
        n = len(res.circuits)
        print(f"\nok: {n} circuit(s) typecheck"
              f"{'' if not res.warnings else f', {len(res.warnings)} warning(s)'}")
        return 0
    print(f"\nfailed: {len(res.errors)} error(s)")
    return 1


def cmd_run(args) -> int:
    prog, res = _load(args.file)
    if not res.ok:
        for d in res.errors:
            print(d)
        return 1
    backend = Backend(seed=args.seed, duration=args.duration)
    print(report(Runtime(prog, res, backend).run()))
    return 0


def cmd_table(args) -> int:
    prog, res = _load(args.file)
    if not res.ok:
        for d in res.errors:
            print(d)
        return 1
    backend = Backend(seed=args.seed, duration=args.duration)
    result = Runtime(prog, res, backend).run()

    obs = args.observables
    if not obs:
        seen: list[str] = []
        for x in result.experiments:
            for arm in x.all_arms():
                for k in arm.store:
                    if k not in seen:
                        seen.append(k)
        obs = seen[:6]
    print(summary_table(result, obs))
    return 0


def cmd_observables(args) -> int:
    for name in sorted(OBSERVABLES):
        s = OBSERVABLES[name]
        arity = f"/{s.arity}" if s.arity else ""
        print(f"{name}{arity}  [{s.unit}]")
        for line in _wrap(s.procedure, 72):
            print(f"    {line}")
        print()
    return 0


def _wrap(text: str, width: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="vitruvius",
        description="Run musculoskeletal circuit experiments written in .vvs",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    for name, fn, needs_file in (
        ("check", cmd_check, True),
        ("run", cmd_run, True),
        ("table", cmd_table, True),
        ("observables", cmd_observables, False),
    ):
        p = sub.add_parser(name)
        p.set_defaults(fn=fn)
        if needs_file:
            p.add_argument("file")
            p.add_argument("--seed", type=int, default=0)
            p.add_argument("--duration", type=float, default=60.0)
        if name == "table":
            p.add_argument("--observables", nargs="*", default=None)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
