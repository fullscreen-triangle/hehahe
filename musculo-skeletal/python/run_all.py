"""Run every experiment and write results to JSON.

    python run_all.py [--seed N] [--duration S] [--outdir results]

Writes one file per .vvs program, plus a combined index and a flat
observations table for downstream analysis.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from vitruvius import Backend, check, parse
from vitruvius.runtime import Runtime
from vitruvius.serialize import dump, result_to_dict

HERE = Path(__file__).resolve().parent


def run_one(path: Path, backend: Backend) -> tuple[dict, object]:
    prog = parse(path.read_text(encoding="utf-8"))
    checked = check(prog)
    if not checked.ok:
        raise SystemExit(
            f"{path.name} failed to typecheck:\n"
            + "\n".join(str(d) for d in checked.errors)
        )
    result = Runtime(prog, checked, backend).run()
    return result_to_dict(result, str(path), backend), result


def flatten(name: str, d: dict) -> list[dict]:
    """One row per (experiment, phase, arm, observable)."""
    rows: list[dict] = []
    for x in d["experiments"]:
        groups = (
            [(p["phase"], p["arms"]) for p in x.get("phases", [])]
            if x["phased"]
            else [(None, x.get("arms", []))]
        )
        for phase, arms in groups:
            for arm in arms:
                for obs, m in arm["observations"].items():
                    rows.append(
                        {
                            "program": name,
                            "experiment": x["experiment"],
                            "phase": phase,
                            "arm": arm["arm"],
                            "closure_index": arm["closure_index"],
                            "lesions": "; ".join(arm["lesions_applied"]) or None,
                            "observable": obs,
                            "value": m["value"],
                            "unit": m["unit"],
                            "undefined": m.get("undefined", False),
                            "note": m.get("note"),
                            "floor_used": m["backend_report"]["floor_used"],
                            "seed": m["backend_report"]["seed"],
                        }
                    )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--duration", type=float, default=60.0)
    ap.add_argument("--outdir", default="results")
    args = ap.parse_args()

    outdir = HERE / args.outdir
    outdir.mkdir(parents=True, exist_ok=True)

    files = sorted((HERE / "experiments").glob("*.vvs"))
    index: list[dict] = []
    all_rows: list[dict] = []

    for f in files:
        backend = Backend(seed=args.seed, duration=args.duration)
        d, result = run_one(f, backend)

        stem = f.stem
        out = outdir / f"{stem}.json"
        out.write_text(json.dumps(d, indent=2), encoding="utf-8")

        rows = flatten(stem, d)
        all_rows.extend(rows)

        n_arms = sum(
            len(x.get("arms", [])) + sum(len(p["arms"]) for p in x.get("phases", []))
            for x in d["experiments"]
        )
        n_open = sum(1 for r in rows if r["closure_index"] == "open")
        index.append(
            {
                "program": stem,
                "file": str(out.relative_to(HERE)),
                "n_experiments": len(d["experiments"]),
                "n_arms": n_arms,
                "n_observations": len(rows),
                "n_warnings": d["static_analysis"]["n_warnings"],
                "circuits": list(d["static_analysis"]["circuits"]),
            }
        )
        print(f"{stem:<28} {len(d['experiments']):>2} experiment(s)  "
              f"{n_arms:>2} arm(s)  {len(rows):>3} observation(s)  -> {out.name}")

    (outdir / "index.json").write_text(
        json.dumps({"programs": index, "seed": args.seed,
                    "duration_s": args.duration}, indent=2),
        encoding="utf-8",
    )
    (outdir / "observations.json").write_text(
        json.dumps(all_rows, indent=2), encoding="utf-8"
    )

    # A flat CSV as well, since most downstream tools want one.
    import csv

    with (outdir / "observations.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(all_rows[0]))
        w.writeheader()
        w.writerows(all_rows)

    print(f"\n{len(files)} program(s), {len(all_rows)} observation(s)")
    print(f"wrote {outdir.relative_to(HERE)}/index.json, observations.json, "
          f"observations.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
