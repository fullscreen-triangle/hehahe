"""JSON serialisation of run results.

Every value a run produces is recorded, together with what the backend was
obliged to disclose: the floor it used, the band an observable was computed
over, the seed, and the sample count. A results file is therefore
self-describing -- a reader can tell what was measured, under what
conditions, and what the static analysis said before any numerics ran.
"""

from __future__ import annotations

import json
import math
import platform
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from .backend import Backend, Measurement
from .circuit import Circuit
from .runtime import ArmResult, ExperimentResult, RunResult

SCHEMA_VERSION = "vitruvius-results/1"


def _num(v):
    """JSON has no NaN; record it as null with the reason preserved."""
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


def measurement_to_dict(m: Measurement) -> dict:
    d = {
        "value": _num(m.value),
        "unit": m.unit,
        "backend_report": {
            "floor_used": _num(m.report.floor_used),
            "band_hz": list(m.report.band) if m.report.band else None,
            "seed": m.report.seed,
            "n_samples": m.report.n_samples,
            "dt_s": m.report.dt,
        },
    }
    if m.note:
        d["note"] = m.note
    if isinstance(m.value, float) and math.isnan(m.value):
        d["undefined"] = True
    return d


def circuit_to_dict(c: Circuit) -> dict:
    return {
        "name": c.name,
        "closure_index": c.closure_index().value,
        "floor": _num(c.floor()),
        "loop_delay_s": _num(c.loop_delay()),
        "outbound": list(c.outbound),
        "return": list(c.ret),
        "compartments": {
            k: {"capacitance_F": v.capacitance, "stratum": v.stratum}
            for k, v in sorted(c.compartments.items())
        },
        "elements": {
            k: {
                "src": e.src,
                "dst": e.dst,
                "delay_s": e.delay,
                "gain": e.gain,
            }
            for k, e in sorted(c.elements.items())
        },
        "noise_edges": [
            {"from_stratum": a, "to_stratum": b, "amplitude": amp}
            for a, b, amp in c.noise_edges
        ],
    }


def arm_to_dict(a: ArmResult, include_circuit: bool = True) -> dict:
    d = {
        "arm": a.name,
        "closure_index": a.closure,
        "committed_record": a.record,
        "lesions_applied": list(a.provenance),
        "apertures": list(a.apertures),
        "observations": {k: measurement_to_dict(m) for k, m in a.store.items()},
    }
    if include_circuit:
        d["circuit"] = circuit_to_dict(a.circuit)
    return d


def experiment_to_dict(x: ExperimentResult, include_circuits: bool = True) -> dict:
    d = {"experiment": x.name, "phased": x.phased}
    if x.phased:
        d["phases"] = [
            {
                "phase": p.name,
                "arms": [arm_to_dict(a, include_circuits) for a in p.arms],
            }
            for p in x.phases
        ]
    else:
        d["arms"] = [arm_to_dict(a, include_circuits) for a in x.arms]
    return d


def _provenance(source: str | None, backend: Backend | None) -> dict:
    prov = {
        "schema": SCHEMA_VERSION,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
    }
    if source:
        prov["source_file"] = str(source)
        try:
            import hashlib

            prov["source_sha256"] = hashlib.sha256(
                Path(source).read_bytes()
            ).hexdigest()[:16]
        except OSError:
            pass
    if backend is not None:
        prov["backend"] = {
            "kind": "continuous-reference",
            "seed": backend.seed,
            "dt_s": backend.dt,
            "duration_s": backend.duration,
        }
    try:
        prov["git_commit"] = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL, text=True,
        ).strip()
    except Exception:
        pass
    return prov


def result_to_dict(r: RunResult, source: str | None = None,
                   backend: Backend | None = None,
                   include_circuits: bool = True) -> dict:
    out = {
        "provenance": _provenance(source, backend),
        "diagnostics": [
            {
                "severity": d.severity,
                "rule": d.rule,
                "message": d.message,
                "line": d.line,
            }
            for d in (r.checked.diagnostics if r.checked else [])
        ],
        "experiments": [
            experiment_to_dict(x, include_circuits) for x in r.experiments
        ],
    }
    if r.checked is not None:
        out["static_analysis"] = {
            "typechecks": r.checked.ok,
            "n_errors": len(r.checked.errors),
            "n_warnings": len(r.checked.warnings),
            "circuits": {
                name: {
                    "closure_index": c.closure_index().value,
                    "floor": _num(c.floor()),
                    "n_elements": len(c.elements),
                }
                for name, c in sorted(r.checked.circuits.items())
            },
            "event_types": {k: list(v) for k, v in r.checked.event_types.items()},
        }
    return out


def dump(r: RunResult, path: str, source: str | None = None,
         backend: Backend | None = None, include_circuits: bool = True) -> str:
    d = result_to_dict(r, source, backend, include_circuits)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(d, indent=2), encoding="utf-8")
    return path
