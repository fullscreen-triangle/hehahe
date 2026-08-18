"""Formatting of run results.

The reporting discipline follows the specification: an aperture is a
diagnostic and is always shown; a fractional estimate is shown together
with the type separation that determines whether it can be interpreted.
"""

from __future__ import annotations

import math

from .runtime import ArmResult, ExperimentResult, RunResult


def _fmt(v: object) -> str:
    if isinstance(v, float):
        if math.isnan(v):
            return "--"
        if v != 0 and (abs(v) < 1e-3 or abs(v) >= 1e5):
            return f"{v:.3e}"
        return f"{v:.4g}"
    if isinstance(v, list):
        return f"{len(v)} item(s)"
    return str(v)


def arm_lines(arm: ArmResult, indent: str = "    ") -> list[str]:
    out = [f"{indent}{arm.name}  [{arm.closure}]  record={arm.record}"]

    if arm.provenance:
        out.append(f"{indent}  applied: {'; '.join(arm.provenance)}")

    for ap in arm.apertures:
        out.append(f"{indent}  ! {ap}")

    for key, m in arm.store.items():
        if key in ("aperture_list",):
            continue
        line = f"{indent}  {key:<28} {_fmt(m.value)}"
        if m.unit and m.unit not in ("categorical", "list"):
            line += f" {m.unit}"
        if m.note:
            line += f"   ({m.note})"
        out.append(line)

    return out


def experiment_lines(x: ExperimentResult) -> list[str]:
    out = [f"experiment {x.name}" + ("  [phased]" if x.phased else "")]

    if not x.phased:
        for arm in x.arms:
            out.extend(arm_lines(arm))
        return out

    for ph in x.phases:
        out.append(f"  phase {ph.name}")
        for arm in ph.arms:
            out.extend(arm_lines(arm, indent="      "))
    return out


def report(result: RunResult) -> str:
    out: list[str] = []

    if result.checked is not None:
        errs = result.checked.errors
        warns = result.checked.warnings
        notes = [d for d in result.checked.diagnostics if d.severity == "note"]
        if errs or warns or notes:
            out.append("diagnostics")
            for d in errs + warns + notes:
                out.append(f"  {d}")
            out.append("")

    for x in result.experiments:
        out.extend(experiment_lines(x))
        out.append("")

    return "\n".join(out)


def summary_table(result: RunResult, observables: list[str]) -> str:
    """Compact table: one row per arm, one column per named observable."""
    rows: list[tuple[str, str, str, list[str]]] = []

    for x in result.experiments:
        for arm in x.all_arms():
            vals = []
            for o in observables:
                m = arm.store.get(o)
                vals.append(_fmt(m.value) if m else "--")
            rows.append((x.name, arm.name, arm.closure, vals))

    if not rows:
        return "(no results)"

    w_exp = max(len("experiment"), max(len(r[0]) for r in rows))
    w_arm = max(len("arm"), max(len(r[1]) for r in rows))
    w_cls = max(len("closure"), max(len(r[2]) for r in rows))
    w_val = [
        max(len(o), max((len(r[3][i]) for r in rows), default=0))
        for i, o in enumerate(observables)
    ]

    head = (
        f"{'experiment':<{w_exp}}  {'arm':<{w_arm}}  {'closure':<{w_cls}}  "
        + "  ".join(f"{o:>{w_val[i]}}" for i, o in enumerate(observables))
    )
    sep = "-" * len(head)
    lines = [head, sep]

    for exp, arm, cls, vals in rows:
        lines.append(
            f"{exp:<{w_exp}}  {arm:<{w_arm}}  {cls:<{w_cls}}  "
            + "  ".join(f"{v:>{w_val[i]}}" for i, v in enumerate(vals))
        )

    return "\n".join(lines)
