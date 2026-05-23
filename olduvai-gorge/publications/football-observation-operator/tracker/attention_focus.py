"""
Attention-focus solver — the core of the specialised ball tracker.

Each detected player contributes an attention ray
        L_i = { p_i + t f_i : t >= 0 }
where p_i is the player's pitch position and f_i is the unit vector of
the player's torso orientation. The ball's location is taken to be the
point that minimises the weighted sum of squared perpendicular
distances from the rays:

        b*  =  argmin_b  sum_i  w_i * d_perp(b, L_i)^2

This file implements:

  1. ``solve_focus_point`` — closed-form weighted least-squares solve
     of the perpendicular-distance objective, including an in-front-of-
     player constraint via iterative re-weighting.

  2. ``robust_focus_point`` — IRLS wrapper using Huber weights, robust
     against off-ball runners pointing away from the play.

  3. ``attention_density`` — Bayesian-style attention density at any
     query point given the player rays; used for confidence and for
     visualisation.

No CV is performed here; the inputs are already pitch-metric positions
and unit facing vectors. The CV layer lives in ``detector.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

import numpy as np


# ──────────────────────────────────────────────────────────────────────
# Data carriers
# ──────────────────────────────────────────────────────────────────────

@dataclass
class AttentionRay:
    """One player's attention contribution to the focus solver.

    Attributes
    ----------
    position : np.ndarray, shape (2,)
        Player pitch position (metres).
    facing : np.ndarray, shape (2,)
        Unit vector of torso facing direction in the pitch plane.
    weight : float
        Engagement weight in [0, 1]. The framework's role-binding
        layer sets this: low weight for off-ball runners, high
        weight for defenders facing the play.
    """
    position: np.ndarray
    facing: np.ndarray
    weight: float = 1.0


@dataclass
class FocusEstimate:
    """Output of the focus solver."""
    point: np.ndarray            # (2,) pitch-metric focus point
    confidence: float            # 0..1 confidence based on ray convergence
    n_supporting: int            # number of rays with significant weight
    residual_rms: float          # RMS perpendicular distance from the solution
    iterations: int              # IRLS iterations actually performed


# ──────────────────────────────────────────────────────────────────────
# Single-shot weighted least-squares solve
# ──────────────────────────────────────────────────────────────────────

def _orthogonal_projector(f: np.ndarray) -> np.ndarray:
    """Return the 2x2 projector orthogonal to the unit vector f."""
    f = f / max(float(np.linalg.norm(f)), 1e-12)
    return np.eye(2) - np.outer(f, f)


def solve_focus_point(rays: Iterable[AttentionRay],
                      ridge: float = 1e-3
                      ) -> FocusEstimate:
    """Closed-form weighted least squares for the focus point.

    Minimises
        J(b) = sum_i w_i * || (I - f_i f_i^T) (b - p_i) ||^2
    in closed form. A tiny ridge term keeps the system non-singular
    when all rays are nearly parallel.

    Behind-player rays (b is behind p_i in the −f_i half-plane) carry
    no information; this is handled by the iterative reweighting in
    ``robust_focus_point`` rather than here.
    """
    A = np.zeros((2, 2))
    rhs = np.zeros(2)
    n_eff = 0
    for r in rays:
        if r.weight <= 0:
            continue
        M = _orthogonal_projector(r.facing)
        A += r.weight * M
        rhs += r.weight * (M @ r.position)
        n_eff += 1
    A = A + ridge * np.eye(2)
    if n_eff == 0 or np.linalg.det(A) < 1e-12:
        return FocusEstimate(point=np.array([0.0, 0.0]),
                             confidence=0.0,
                             n_supporting=0,
                             residual_rms=float("inf"),
                             iterations=0)
    b = np.linalg.solve(A, rhs)
    # Residual RMS
    residuals = []
    for r in rays:
        if r.weight <= 0:
            continue
        d = b - r.position
        d_perp = d - (d @ r.facing) * r.facing
        residuals.append(np.linalg.norm(d_perp))
    rms = float(np.sqrt(np.mean(np.square(residuals)))) if residuals else 0.0
    conf = _confidence_from_residual(rms)
    return FocusEstimate(point=b, confidence=conf,
                         n_supporting=n_eff,
                         residual_rms=rms,
                         iterations=1)


def _confidence_from_residual(rms_m: float,
                              scale_m: float = 4.0) -> float:
    """Map RMS perpendicular distance (metres) to a confidence in [0,1]."""
    return float(np.exp(-(rms_m / scale_m) ** 2))


# ──────────────────────────────────────────────────────────────────────
# Robust IRLS solve with in-front-of-player constraint
# ──────────────────────────────────────────────────────────────────────

def robust_focus_point(rays: List[AttentionRay],
                       max_iter: int = 8,
                       huber_k_m: float = 3.0,
                       drop_behind_player: bool = True,
                       ridge: float = 1e-3
                       ) -> FocusEstimate:
    """Iteratively reweighted least squares for the focus point.

    The Huber-style reweighting handles three failure modes that a
    plain least-squares solve does not:

    1. Off-ball runners pointing at the goal, not the ball. Their
       perpendicular distance is large, so the Huber weight collapses
       their contribution.
    2. Players who happen to face away from the converged focus
       point. With ``drop_behind_player=True`` we set their effective
       weight to zero on the second pass; this implements the
       in-front-of-player constraint.
    3. Detection-level noise in the torso vector. Huber damps the tail.

    Parameters
    ----------
    rays : list of AttentionRay
        Per-player attention rays. Initial weights come from the
        role-binding layer; this function only modulates them.
    max_iter : int
        Maximum IRLS iterations. Typically converges in 3-5.
    huber_k_m : float
        Huber threshold in metres of perpendicular distance.
    drop_behind_player : bool
        Whether to zero rays for which the current focus estimate
        sits behind the player.
    ridge : float
        Tikhonov ridge to keep the normal-equations well-conditioned.
    """
    if not rays:
        return FocusEstimate(point=np.array([0.0, 0.0]),
                             confidence=0.0,
                             n_supporting=0,
                             residual_rms=float("inf"),
                             iterations=0)

    rays_work = [AttentionRay(position=np.asarray(r.position, dtype=float),
                              facing=np.asarray(r.facing, dtype=float),
                              weight=float(r.weight))
                 for r in rays]

    prev_b = None
    last_estimate = solve_focus_point(rays_work, ridge=ridge)
    for it in range(max_iter):
        b = last_estimate.point
        if prev_b is not None and np.linalg.norm(b - prev_b) < 1e-4:
            break
        prev_b = b
        for r in rays_work:
            d = b - r.position
            in_front = (d @ r.facing) > 0.0
            if drop_behind_player and not in_front:
                r.weight = 0.0
                continue
            d_perp = d - (d @ r.facing) * r.facing
            dist = float(np.linalg.norm(d_perp))
            huber = 1.0 if dist <= huber_k_m else huber_k_m / dist
            base = max(r.weight, 1e-9)
            r.weight = base * huber
        last_estimate = solve_focus_point(rays_work, ridge=ridge)
        last_estimate = FocusEstimate(point=last_estimate.point,
                                      confidence=last_estimate.confidence,
                                      n_supporting=last_estimate.n_supporting,
                                      residual_rms=last_estimate.residual_rms,
                                      iterations=it + 1)
    return last_estimate


# ──────────────────────────────────────────────────────────────────────
# Bayesian attention density (for visualisation and confidence maps)
# ──────────────────────────────────────────────────────────────────────

def attention_density(query: np.ndarray,
                      rays: Iterable[AttentionRay],
                      sigma_angle_rad: float = 0.30,
                      drop_behind_player: bool = True
                      ) -> float:
    """Evaluate the product-of-Gaussians attention density at ``query``.

    Each ray contributes a Gaussian factor with standard deviation
    ``sigma_angle_rad`` on the angle between (query - p_i) and f_i,
    plus a zero contribution when ``query`` is behind the player and
    ``drop_behind_player`` is True.

    Returns a single non-normalised density value; the relative values
    across a grid are what matter for visualisation.
    """
    log_p = 0.0
    n = 0
    for r in rays:
        if r.weight <= 0:
            continue
        d = query - r.position
        norm = float(np.linalg.norm(d))
        if norm < 1e-6:
            continue
        dot = float(d @ r.facing) / norm
        if drop_behind_player and dot <= 0:
            return 0.0
        # Angle between d and f_i
        theta = float(np.arccos(np.clip(dot, -1.0, 1.0)))
        log_p += -0.5 * (theta / sigma_angle_rad) ** 2 * r.weight
        n += 1
    return float(np.exp(log_p)) if n > 0 else 0.0


def attention_density_grid(rays: List[AttentionRay],
                           xmin: float, xmax: float,
                           ymin: float, ymax: float,
                           nx: int = 80, ny: int = 60,
                           sigma_angle_rad: float = 0.30
                           ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Evaluate the attention density on a grid for heatmap rendering."""
    xs = np.linspace(xmin, xmax, nx)
    ys = np.linspace(ymin, ymax, ny)
    Z = np.zeros((ny, nx))
    for j, y in enumerate(ys):
        for i, x in enumerate(xs):
            Z[j, i] = attention_density(np.array([x, y]), rays,
                                        sigma_angle_rad=sigma_angle_rad)
    return xs, ys, Z


# ──────────────────────────────────────────────────────────────────────
# Convenience: solve focus from raw arrays (no dataclass wrapping)
# ──────────────────────────────────────────────────────────────────────

def solve_from_arrays(positions: np.ndarray,
                      facings: np.ndarray,
                      weights: Optional[np.ndarray] = None,
                      **kwargs) -> FocusEstimate:
    """Convenience wrapper.

    Parameters
    ----------
    positions : (N, 2)
    facings   : (N, 2) — assumed unit vectors
    weights   : (N,) or None — defaults to ones
    """
    positions = np.asarray(positions, dtype=float)
    facings = np.asarray(facings, dtype=float)
    if weights is None:
        weights = np.ones(positions.shape[0], dtype=float)
    rays = [AttentionRay(position=positions[i],
                         facing=facings[i],
                         weight=float(weights[i]))
            for i in range(positions.shape[0])]
    return robust_focus_point(rays, **kwargs)
