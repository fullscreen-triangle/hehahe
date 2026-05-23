"""
Specialised football ball tracker.

Public API:
    AttentionRay, FocusEstimate, robust_focus_point, solve_from_arrays
    PointCorrespondence, HomographyResult, solve_homography_dlt,
        solve_homography_ransac, BillboardCalibration, calibrate_from_billboard,
        image_to_pitch, pitch_to_image
    PlayerDetection, PlayerDetector, MockDetector, SyntheticPlayer,
        circle_facing_ball, two_team_formation
    TrackerConfig, FrameOutput, BallTracker
"""

from .attention_focus import (
    AttentionRay,
    FocusEstimate,
    robust_focus_point,
    solve_focus_point,
    solve_from_arrays,
    attention_density,
    attention_density_grid,
)
from .homography import (
    PointCorrespondence,
    HomographyResult,
    BillboardCalibration,
    solve_homography_dlt,
    solve_homography_ransac,
    calibrate_from_billboard,
    image_to_pitch,
    pitch_to_image,
)
from .detector import (
    PlayerDetection,
    PlayerDetector,
    MockDetector,
    SyntheticPlayer,
    circle_facing_ball,
    two_team_formation,
)
from .tracker import TrackerConfig, FrameOutput, BallTracker

__all__ = [
    "AttentionRay", "FocusEstimate", "robust_focus_point",
    "solve_focus_point", "solve_from_arrays",
    "attention_density", "attention_density_grid",
    "PointCorrespondence", "HomographyResult", "BillboardCalibration",
    "solve_homography_dlt", "solve_homography_ransac",
    "calibrate_from_billboard", "image_to_pitch", "pitch_to_image",
    "PlayerDetection", "PlayerDetector", "MockDetector",
    "SyntheticPlayer", "circle_facing_ball", "two_team_formation",
    "TrackerConfig", "FrameOutput", "BallTracker",
]
