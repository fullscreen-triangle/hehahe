"""
Billboard-to-pitch homography solver.

Pitch-perimeter advertising panels are planar, of standard height
(~1 m), of known geometric dimensions, and carry high-contrast content
suitable for feature-based homography estimation. Solving the planar
homography that rectifies the visible panel content to its known
canonical layout simultaneously:

  (1) Recovers the pitch ground-plane → image projection (the panel
      base coincides with the touch-line by stadium construction),
      yielding metric pitch coordinates for any visible ground point.

  (2) Provides player/spectator segmentation: any visible lower body
      on the pitch side of the rectified panel line is a player; any
      torso/upper body above the panel is a spectator whose lower
      body is occluded by the panel.

  (3) Calibrates the tracker internally: image-to-world scale at each
      point gives expected player heights, expected speed magnitudes,
      and per-region detection-confidence priors.

This module does not include feature extraction or panel content
recognition — it accepts image↔world point correspondences from an
upstream component and produces the homography, plus inverse-map
utilities for pitch ↔ image conversion.

Pure NumPy. No OpenCV required.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import numpy as np


# ──────────────────────────────────────────────────────────────────────
# Data types
# ──────────────────────────────────────────────────────────────────────

@dataclass
class PointCorrespondence:
    """One image-plane point ↔ world-plane point match.

    image : (u, v) in image pixels
    world : (X, Y) in metres on the ground plane.
            For points on the touch-line at the panel base, Y is the
            touch-line coordinate of the panel feature.
    """
    image: Tuple[float, float]
    world: Tuple[float, float]


@dataclass
class HomographyResult:
    """The fitted homography plus diagnostic information.

    H : 3x3 matrix mapping homogeneous image points to homogeneous
        world points (so world = H @ image when properly normalised).
    H_inv : 3x3 matrix mapping world → image.
    rms_reproj_px : RMS image-plane reprojection error in pixels.
    rms_reproj_m : RMS world-plane reprojection error in metres.
    n_correspondences : number of points used in the fit.
    """
    H: np.ndarray
    H_inv: np.ndarray
    rms_reproj_px: float
    rms_reproj_m: float
    n_correspondences: int


# ──────────────────────────────────────────────────────────────────────
# Direct Linear Transform (DLT) — pure NumPy
# ──────────────────────────────────────────────────────────────────────

def _normalise_points(pts: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Hartley normalisation: shift centroid to origin, scale so mean
    distance = sqrt(2). Returns (normalised, T) where T is the 3x3
    similarity that achieves the normalisation."""
    centroid = pts.mean(axis=0)
    shifted = pts - centroid
    mean_dist = np.mean(np.linalg.norm(shifted, axis=1))
    if mean_dist < 1e-9:
        return pts.copy(), np.eye(3)
    scale = np.sqrt(2.0) / mean_dist
    T = np.array([[scale, 0.0, -scale * centroid[0]],
                  [0.0, scale, -scale * centroid[1]],
                  [0.0, 0.0, 1.0]])
    pts_h = np.hstack([pts, np.ones((pts.shape[0], 1))])
    norm = (T @ pts_h.T).T
    return norm[:, :2], T


def solve_homography_dlt(
    correspondences: Sequence[PointCorrespondence],
) -> HomographyResult:
    """Direct Linear Transform with Hartley normalisation.

    The system is built such that ``H @ image = world``. At least 4
    non-collinear correspondences are required; more are recommended
    to reduce sensitivity to noise.
    """
    if len(correspondences) < 4:
        raise ValueError("Need at least 4 correspondences for homography.")

    img_pts = np.array([c.image for c in correspondences], dtype=float)
    world_pts = np.array([c.world for c in correspondences], dtype=float)

    img_norm, T_img = _normalise_points(img_pts)
    world_norm, T_world = _normalise_points(world_pts)

    # Build the 2N x 9 system.
    n = len(correspondences)
    A = np.zeros((2 * n, 9))
    for i in range(n):
        u, v = img_norm[i]
        X, Y = world_norm[i]
        A[2 * i] = [-u, -v, -1.0, 0.0, 0.0, 0.0, u * X, v * X, X]
        A[2 * i + 1] = [0.0, 0.0, 0.0, -u, -v, -1.0, u * Y, v * Y, Y]
    _, _, Vt = np.linalg.svd(A)
    h = Vt[-1]
    H_norm = h.reshape(3, 3)

    # Denormalise: H = T_world^{-1} @ H_norm @ T_img
    H = np.linalg.inv(T_world) @ H_norm @ T_img

    # Reprojection errors.
    pts_h = np.hstack([img_pts, np.ones((n, 1))])
    proj = (H @ pts_h.T).T
    proj_world = proj[:, :2] / proj[:, 2:3]
    err_world = world_pts - proj_world
    rms_world = float(np.sqrt(np.mean(np.sum(err_world ** 2, axis=1))))

    H_inv = np.linalg.inv(H)
    world_h = np.hstack([world_pts, np.ones((n, 1))])
    back = (H_inv @ world_h.T).T
    back_img = back[:, :2] / back[:, 2:3]
    err_img = img_pts - back_img
    rms_img = float(np.sqrt(np.mean(np.sum(err_img ** 2, axis=1))))

    return HomographyResult(H=H, H_inv=H_inv,
                            rms_reproj_px=rms_img,
                            rms_reproj_m=rms_world,
                            n_correspondences=n)


# ──────────────────────────────────────────────────────────────────────
# Coordinate conversion utilities
# ──────────────────────────────────────────────────────────────────────

def image_to_pitch(image_xy: np.ndarray, H: np.ndarray) -> np.ndarray:
    """Apply the homography to convert image pixels to pitch metres.

    Accepts either a single (u, v) or an (N, 2) array. Returns an
    array of the same shape with world coordinates.
    """
    image_xy = np.asarray(image_xy, dtype=float)
    single = image_xy.ndim == 1
    pts = image_xy.reshape(-1, 2)
    ones = np.ones((pts.shape[0], 1))
    h = np.hstack([pts, ones])
    proj = (H @ h.T).T
    out = proj[:, :2] / proj[:, 2:3]
    return out[0] if single else out


def pitch_to_image(pitch_xy: np.ndarray, H_inv: np.ndarray) -> np.ndarray:
    """Inverse map: pitch metres → image pixels."""
    return image_to_pitch(pitch_xy, H_inv)


# ──────────────────────────────────────────────────────────────────────
# Billboard line and player/spectator segmentation
# ──────────────────────────────────────────────────────────────────────

@dataclass
class BillboardCalibration:
    """A solved homography plus the geometry of the billboard panel
    used to derive it.

    Useful for the segmentation step: anything visible above the
    panel-top image line is a spectator (their lower body is occluded
    by the panel); anything visible below the panel-top line and on
    the pitch side is a player.
    """
    homography: HomographyResult
    panel_height_m: float          # standard ~1.0 m
    panel_top_image_line: np.ndarray   # (a, b, c) coefficients: a*u + b*v + c = 0
    pitch_xmin: float
    pitch_xmax: float
    pitch_ymin: float
    pitch_ymax: float

    def is_pitch_side(self, image_xy: np.ndarray) -> bool:
        """Return True if the image point lies on the pitch side
        of the billboard-top image line (i.e. below the panel)."""
        u, v = image_xy
        a, b, c = self.panel_top_image_line
        return (a * u + b * v + c) > 0


def calibrate_from_billboard(
    correspondences: Sequence[PointCorrespondence],
    panel_height_m: float = 1.0,
    pitch_extent: Tuple[float, float, float, float] = (-30.0, 30.0, -20.0, 20.0),
) -> BillboardCalibration:
    """Compose a homography solve with derived calibration geometry.

    ``correspondences`` are panel-feature points (corner brackets,
    pre-known logo anchors, etc.) with world coordinates expressed
    on the touch-line ground plane.

    The panel-top image line is computed by projecting two
    well-separated points on the panel top edge — assumed at world
    height ``panel_height_m`` — into the image. (This requires a
    second homography stage that accounts for height; we use the
    simpler approximation that the panel top is parallel to the
    panel base in the image, which is true for a roughly horizontal
    camera and a non-zoomed view.)
    """
    homography = solve_homography_dlt(correspondences)

    img_pts = np.array([c.image for c in correspondences], dtype=float)
    # Take the two image points with extremal u-coordinate as the
    # left/right anchors and shift them upward by an empirical pixel
    # offset corresponding to the panel height. For a fully calibrated
    # system one would project (X, Y, panel_height_m) through a 3D
    # camera matrix; for the planar approximation we use the median
    # in-image vertical spread of correspondences as the panel-height
    # proxy.
    panel_vertical_proxy = max(8.0, 0.2 * (img_pts[:, 1].max()
                                            - img_pts[:, 1].min()))
    left_anchor = img_pts[np.argmin(img_pts[:, 0])]
    right_anchor = img_pts[np.argmax(img_pts[:, 0])]
    panel_top_left = left_anchor + np.array([0.0, -panel_vertical_proxy])
    panel_top_right = right_anchor + np.array([0.0, -panel_vertical_proxy])
    dx = panel_top_right[0] - panel_top_left[0]
    dy = panel_top_right[1] - panel_top_left[1]
    # Line in image coords: (y - y0)*dx - (x - x0)*dy = 0
    a = -dy
    b = dx
    c = dy * panel_top_left[0] - dx * panel_top_left[1]
    line = np.array([a, b, c], dtype=float)
    # Orient so that the pitch side returns positive value.
    pitch_centre_image = pitch_to_image(np.array([0.0, 0.0]), homography.H_inv)
    if a * pitch_centre_image[0] + b * pitch_centre_image[1] + c < 0:
        line = -line

    return BillboardCalibration(
        homography=homography,
        panel_height_m=panel_height_m,
        panel_top_image_line=line,
        pitch_xmin=pitch_extent[0],
        pitch_xmax=pitch_extent[1],
        pitch_ymin=pitch_extent[2],
        pitch_ymax=pitch_extent[3],
    )


# ──────────────────────────────────────────────────────────────────────
# Robust homography update (RANSAC-style)
# ──────────────────────────────────────────────────────────────────────

def solve_homography_ransac(
    correspondences: Sequence[PointCorrespondence],
    n_iter: int = 200,
    threshold_px: float = 3.0,
    min_inliers: int = 4,
    seed: Optional[int] = 0,
) -> Tuple[HomographyResult, List[int]]:
    """RANSAC wrapper around DLT.

    Returns the best homography and the list of inlier indices.
    Used for live frames where panel feature matches may include
    occlusion noise from passing players.
    """
    rng = np.random.default_rng(seed)
    corrs = list(correspondences)
    n = len(corrs)
    if n < 4:
        raise ValueError("Need at least 4 correspondences.")

    best_inliers: List[int] = []
    best_H: Optional[HomographyResult] = None
    for _ in range(n_iter):
        idx = rng.choice(n, size=4, replace=False)
        sample = [corrs[int(i)] for i in idx]
        try:
            H_try = solve_homography_dlt(sample)
        except Exception:
            continue
        # Compute inliers.
        img_pts = np.array([c.image for c in corrs], dtype=float)
        world_pts = np.array([c.world for c in corrs], dtype=float)
        proj = image_to_pitch(img_pts, H_try.H)
        back = pitch_to_image(world_pts, H_try.H_inv)
        # Use image-plane reprojection for thresholding.
        err = np.linalg.norm(img_pts - back, axis=1)
        inliers = [i for i, e in enumerate(err) if e <= threshold_px]
        if len(inliers) > len(best_inliers):
            best_inliers = inliers
            best_H = H_try
    if best_H is None or len(best_inliers) < min_inliers:
        raise RuntimeError("RANSAC failed to find a consensus homography.")

    # Refit on inliers.
    refit = solve_homography_dlt([corrs[i] for i in best_inliers])
    return refit, best_inliers
