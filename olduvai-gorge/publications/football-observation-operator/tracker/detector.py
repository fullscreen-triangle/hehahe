"""
Player-detector interface.

The framework's specialised tracker is parametrised over a player
detector. The detector's job is to emit, per frame:

  * each detected player's image-plane position (or bounding box),
  * each detected player's torso-orientation vector in the pitch plane,
  * (optionally) a coarse team label, jersey colour, or other tag.

The downstream attention-focus solver does NOT depend on any specific
detector implementation. Real detectors will wrap a CNN such as
YOLOv8-pose or BlazePose with a small custom head producing a torso
yaw. For development and validation we provide ``MockDetector`` which
returns ground-truth annotated detections from a synthetic scene.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

import numpy as np


# ──────────────────────────────────────────────────────────────────────
# Data types
# ──────────────────────────────────────────────────────────────────────

@dataclass
class PlayerDetection:
    """One detected player at a single frame.

    All angles and positions are in the pitch metric frame (after the
    detector has applied the homography). The ``facing`` field is a
    unit vector in the pitch plane; ``confidence`` is the detector's
    own confidence in [0, 1].
    """
    pitch_position: np.ndarray          # (2,) — metres
    facing: np.ndarray                  # (2,) — unit vector
    confidence: float = 1.0
    team: Optional[int] = None          # 0 / 1 / None
    bbox_image: Optional[Tuple[float, float, float, float]] = None
    extra: dict = field(default_factory=dict)


# ──────────────────────────────────────────────────────────────────────
# Abstract base class
# ──────────────────────────────────────────────────────────────────────

class PlayerDetector(ABC):
    """Abstract base class for any player detector backend."""

    @abstractmethod
    def detect(self, frame, t_seconds: float) -> List[PlayerDetection]:
        """Process one frame and return the list of player detections.

        ``frame`` may be an image array (real CV backends) or any
        opaque object (synthetic detectors that ignore pixels).
        """


# ──────────────────────────────────────────────────────────────────────
# Mock detector: synthetic players with scripted dynamics
# ──────────────────────────────────────────────────────────────────────

@dataclass
class SyntheticPlayer:
    """One player in a synthetic scene.

    The player position is updated according to its own velocity
    field and the position of the synthetic ball; the player's facing
    direction tracks the ball with a small angular noise and a
    configurable reaction lag.
    """
    initial_position: np.ndarray
    team: int = 0
    role: str = "field"                 # "field", "keeper", "runner"
    base_speed: float = 6.0             # m/s
    reaction_lag_s: float = 0.20
    facing_noise_rad: float = 0.05
    facing_bias_to_ball: float = 1.0    # 1.0 = look at ball, 0.0 = look at goal
    goal_direction: np.ndarray = field(default_factory=lambda: np.array([1.0, 0.0]))

    # Working state (overwritten during simulation).
    _position: np.ndarray = field(default=None, repr=False)
    _facing_target_history: list = field(default_factory=list, repr=False)


class MockDetector(PlayerDetector):
    """Synthetic detector with controllable player dynamics.

    The class advances the positions and facings of a configured
    population of synthetic players given a moving "true" ball
    trajectory, and emits per-frame ``PlayerDetection`` records. It is
    used by the validation suite to verify the attention-focus solver
    on data with known ground truth.

    Use:
        det = MockDetector(players, ball_trajectory)
        for t in times:
            detections = det.detect(None, t)
    """

    def __init__(self,
                 players: Sequence[SyntheticPlayer],
                 ball_trajectory_fn,
                 detection_dropout: float = 0.0,
                 position_noise_m: float = 0.0,
                 facing_noise_rad: float = 0.0,
                 seed: int = 0):
        """
        Parameters
        ----------
        players : sequence of SyntheticPlayer
            The synthetic team(s).
        ball_trajectory_fn : callable t -> np.ndarray (2,)
            Function returning the true ball position at time t.
        detection_dropout : float
            Probability of dropping any one player's detection on a
            given frame (simulates occlusion).
        position_noise_m : float
            Std of additive Gaussian noise on detected position.
        facing_noise_rad : float
            Std of additive Gaussian noise on detected facing angle.
        seed : int
            RNG seed.
        """
        self.players = list(players)
        for p in self.players:
            p._position = np.asarray(p.initial_position, dtype=float).copy()
            p._facing_target_history = []
        self.ball_traj = ball_trajectory_fn
        self.detection_dropout = float(detection_dropout)
        self.position_noise_m = float(position_noise_m)
        self.facing_noise_rad = float(facing_noise_rad)
        self.rng = np.random.default_rng(seed)
        self._t_prev: Optional[float] = None

    # ------------------------------------------------------------------

    def _update_player_kinematics(self, p: SyntheticPlayer,
                                  t: float, dt: float, ball_xy: np.ndarray):
        """Move the player one step toward a target derived from the
        ball and the player's role."""
        if p.role == "runner":
            # Runners chase the goal, not the ball.
            target = p._position + p.goal_direction * 100.0
        elif p.role == "keeper":
            target = p._position + 0.1 * (ball_xy - p._position)
        else:
            target = ball_xy

        direction = target - p._position
        norm = np.linalg.norm(direction)
        if norm > 1e-6:
            direction = direction / norm
        speed = p.base_speed
        p._position = p._position + direction * speed * dt

    def _facing_for_player(self, p: SyntheticPlayer, t: float,
                           ball_xy: np.ndarray) -> np.ndarray:
        """Compute the torso facing direction with reaction lag."""
        # Record the ball position at this frame; the player's actual
        # facing target is the lagged position.
        p._facing_target_history.append((t, ball_xy.copy()))
        # Trim old history.
        keep_from = t - max(p.reaction_lag_s, 0.0) * 1.5 - 0.5
        p._facing_target_history = [(tt, b) for tt, b in p._facing_target_history
                                    if tt >= keep_from]
        target_t = max(0.0, t - p.reaction_lag_s)
        # Interpolate to target_t.
        if len(p._facing_target_history) == 0:
            target_xy = ball_xy
        else:
            best = p._facing_target_history[0]
            for tt, b in p._facing_target_history:
                if tt <= target_t:
                    best = (tt, b)
                else:
                    break
            target_xy = best[1]

        if p.facing_bias_to_ball < 1.0:
            target_xy = (p.facing_bias_to_ball * target_xy
                         + (1.0 - p.facing_bias_to_ball)
                         * (p._position + p.goal_direction * 50.0))
        vec = target_xy - p._position
        norm = float(np.linalg.norm(vec))
        if norm < 1e-6:
            return np.array([1.0, 0.0])
        f = vec / norm
        # Player-intrinsic facing noise
        theta_n = self.rng.normal(0.0, p.facing_noise_rad)
        c, s = np.cos(theta_n), np.sin(theta_n)
        return np.array([c * f[0] - s * f[1], s * f[0] + c * f[1]])

    # ------------------------------------------------------------------

    def detect(self, frame, t_seconds: float) -> List[PlayerDetection]:
        if self._t_prev is None:
            dt = 0.0
        else:
            dt = max(0.0, t_seconds - self._t_prev)
        self._t_prev = t_seconds

        ball_xy = np.asarray(self.ball_traj(t_seconds), dtype=float)
        detections: List[PlayerDetection] = []
        for p in self.players:
            self._update_player_kinematics(p, t_seconds, dt, ball_xy)
            facing = self._facing_for_player(p, t_seconds, ball_xy)

            # Add detector-level noise.
            pos = p._position.copy()
            if self.position_noise_m > 0:
                pos = pos + self.rng.normal(0.0, self.position_noise_m, size=2)
            if self.facing_noise_rad > 0:
                theta = self.rng.normal(0.0, self.facing_noise_rad)
                c, s = np.cos(theta), np.sin(theta)
                facing = np.array([c * facing[0] - s * facing[1],
                                   s * facing[0] + c * facing[1]])

            # Dropout.
            if self.detection_dropout > 0 and self.rng.random() < self.detection_dropout:
                continue

            detections.append(PlayerDetection(
                pitch_position=pos,
                facing=facing,
                confidence=1.0,
                team=p.team,
                extra={"role": p.role},
            ))
        return detections


# ──────────────────────────────────────────────────────────────────────
# Helper builders for synthetic scenes
# ──────────────────────────────────────────────────────────────────────

def circle_facing_ball(n: int, radius: float = 12.0,
                       team: int = 0,
                       reaction_lag_s: float = 0.15,
                       facing_noise_rad: float = 0.05,
                       ) -> List[SyntheticPlayer]:
    """Place ``n`` players on a circle around the origin, each
    configured to face whatever ball trajectory the MockDetector
    advances. Used for stationary-ball validation."""
    players = []
    for i in range(n):
        theta = 2 * np.pi * i / n
        pos = radius * np.array([np.cos(theta), np.sin(theta)])
        players.append(SyntheticPlayer(
            initial_position=pos,
            team=team,
            role="field",
            reaction_lag_s=reaction_lag_s,
            facing_noise_rad=facing_noise_rad,
            base_speed=0.0,  # stationary
        ))
    return players


def two_team_formation(n_per_team: int = 11) -> List[SyntheticPlayer]:
    """Place two opposing 4-3-3 formations on the pitch."""
    players: List[SyntheticPlayer] = []
    # Team 0 (left to right attack), positions in (x, y)
    formation = [(-30, 0), (-22, -10), (-22, 10), (-22, 0),
                 (-10, -8), (-10, 8), (-10, 0),
                 (5, -12), (5, 12), (15, -4), (15, 4)][:n_per_team]
    for x, y in formation:
        players.append(SyntheticPlayer(
            initial_position=np.array([x, y], dtype=float),
            team=0, role="field",
            goal_direction=np.array([1.0, 0.0]),
        ))
    for x, y in formation:
        players.append(SyntheticPlayer(
            initial_position=np.array([-x, -y], dtype=float),
            team=1, role="field",
            goal_direction=np.array([-1.0, 0.0]),
        ))
    return players
