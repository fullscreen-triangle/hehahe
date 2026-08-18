"""Vitruvius: a language for musculoskeletal circuit experiments.

Reference implementation in Python. The production targets are TypeScript
and Rust; this exists so that experiments can be run and results inspected
now, and so that the specification's claims are executable rather than
merely stated.

Typical use::

    from vitruvius import run_source, report

    result = run_source(open("experiment.vvs").read())
    print(report(result))

The pipeline is: tokenize -> parse -> check -> run.

  * `checker` implements the four non-standard typing rules and the
    aperture analysis; all of it is computed from the declaration alone,
    without consulting a backend.
  * `backend` discharges observables numerically, honouring the totality
    obligation: an open circuit yields a divergence time, not an exception.
"""

from .ast_nodes import Program, Quantity
from .backend import Backend, Measurement
from .checker import CheckError, CheckResult, Diagnostic, check
from .circuit import Circuit, Closure, Compartment, Element
from .lexer import LexError, tokenize
from .observables import OBSERVABLES, describe
from .parser import ParseError, parse
from .report import report, summary_table
from .runtime import (
    ArmResult, ExperimentResult, RunResult, Runtime, run_file, run_source,
)

__version__ = "0.1.0"

__all__ = [
    "ArmResult",
    "Backend",
    "CheckError",
    "CheckResult",
    "Circuit",
    "Closure",
    "Compartment",
    "Diagnostic",
    "Element",
    "ExperimentResult",
    "LexError",
    "Measurement",
    "OBSERVABLES",
    "ParseError",
    "Program",
    "Quantity",
    "RunResult",
    "Runtime",
    "check",
    "describe",
    "parse",
    "report",
    "run_file",
    "run_source",
    "summary_table",
    "tokenize",
]
