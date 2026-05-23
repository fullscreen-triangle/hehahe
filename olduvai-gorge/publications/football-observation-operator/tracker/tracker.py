"""
BallTracker — the public orchestrator.

Wires together the detector (player positions + torso vectors), the
billboard homography (optional, for image-side input), and the
attention-focus solver. Maintains a short history of focus estimates
so that derived signals can be exposed:

  * ``focus_velocity``  : speed of the focus point in m/s.
  * ``pass_count``       : monotonic counter of detected passes.
  * ``reaction_lag``    : optional gap between the attention focus and
                          a separately-tracked visual ball, when one
                          is supplied.

The tracker is event-gated: it always runs the cheap attention-focus
solve on every frame, but exposes flags
(``trigger_active``, ``goalkeeper_role_active``) that downstream
biomechanical extraction can use to decide whether to run.

This module does NOT carry CV — the detector is responsible for
emitting per-frame ``PlayerDetection`` records in pitch-metric
coordinates. To run against a real video, plug in a CV-backed
detector.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, List, Optional, Sequence, Tuple

import numpy as np

from .attention_focus import (AttentionRay, FocusEstimate, robust_focus_point)
from .detector import PlayerDetection, PlayerDetector
from .homography import BillboardCalibration


# ──────────────────────────────────────────────────────────────────────
# Tracker configuration
# ──────────────────────────────────────────────────────────────────────

@dataclass
class TrackerConfig:
    """Configurable thresholds for the event-gating layer."""
    pass_window_s: float = 5.0
    pass_count_trigger: int = 3            # passes_in_window >= this -> active
    speed_trigger_m_s: float = 12.0        # focus speed >= this -> active
    speed_smoothing_s: float = 0.25
    cooldown_s: float = 2.0
    goalkeeper_disk_radius_m: float = 16.5  # six-yard / 16m box-ish
    goal_left_x: float = -52.5             # half-pitch length, FIFA
    goal_right_x: float = 52.5
    # Weights for the attention solver per player role/team.
    weight_ball_bearer: float = 0.3        # bearer looks down, less informative
    weight_default: float = 1.0
    weight_off_ball_runner: float = 0.4    # heuristic
    # Possession attribution
    possession_proximity_m: float = 2.0


@dataclass
class FrameOutput:
    """Per-frame public output of the tracker."""
    t_seconds: float
    focus_point: np.ndarray              # (2,) pitch metric coords
    focus_confidence: float
    focus_velocity_m_s: float
    n_supporting: int
    bearer_index: Optional[int]          # index into the current detections
    pass_count_in_window: int
    trigger_active: bool
    goalkeeper_role_active_team: Optional[int]   # 0, 1, or None
    bound_goalkeeper_index: Optional[int]
    duels: List[Tuple[int, int]]         # list of (attacker_i, defender_i) pairs
    detections: List[PlayerDetection]


# ──────────────────────────────────────────────────────────────────────
# Main tracker
# ──────────────────────────────────────────────────────────────────────

class BallTracker:
    """The framework's specialised ball tracker.

    Public surface
    --------------
    update(frame, t) -> FrameOutput
        Feed a new frame and timestamp; receive the per-frame output.

    pass_count
        Monotonic count of detected passes since construction.

    focus_history
        Deque of (t, focus_point) tuples for recent frames.
    """

    def __init__(self,
                 detector: PlayerDetector,
                 calibration: Optional[BillboardCalibration] = None,
                 config: Optional[TrackerConfig] = None,
                 history_len: int = 240):
        self.detector = detector
        self.calibration = calibration
        self.cfg = config or TrackerConfig()
        self.focus_history: Deque[Tuple[float, np.ndarray]] = deque(maxlen=history_len)
        self.pass_event_times: Deque[float] = deque(maxlen=64)
        self.pass_count = 0
        self._prev_bearer: Optional[int] = None
        self._last_trigger_t: Optional[float] = None

    # ------------------------------------------------------------------

    def _per_player_weights(self,
                            detections: List[PlayerDetection],
                            ball_bearer_idx: Optional[int]
                            ) -> np.ndarray:
        """Assign weights to each detected player for the focus solve.

        The ball-bearer's contribution is dampened because his torso
        is biased toward his feet or his passing target rather than
        the ball itself. Field players default to weight 1.0.
        """
        cfg = self.cfg
        weights = np.full(len(detections), cfg.weight_default, dtype=float)
        if ball_bearer_idx is not None and 0 <= ball_bearer_idx < len(detections):
            weights[ball_bearer_idx] = cfg.weight_ball_bearer
        for i, d in enumerate(detections):
            if d.extra.get("role") == "runner":
                weights[i] = cfg.weight_off_ball_runner
        return weights

    # ------------------------------------------------------------------

    def _focus_velocity(self, t_now: float) -> float:
        """Compute the instantaneous focus-point velocity (m/s) by
        finite difference over a short smoothing window."""
        if len(self.focus_history) < 2:
            return 0.0
        cfg = self.cfg
        window_start = t_now - cfg.speed_smoothing_s
        relevant = [(tt, p) for tt, p in self.focus_history if tt >= window_start]
        if len(relevant) < 2:
            return 0.0
        t0, p0 = relevant[0]
        t1, p1 = relevant[-1]
        if t1 - t0 < 1e-4:
            return 0.0
        return float(np.linalg.norm(p1 - p0) / (t1 - t0))

    # ------------------------------------------------------------------

    def _attribute_possession(self,
                              detections: List[PlayerDetection],
                              focus_point: np.ndarray,
                              focus_confidence: float
                              ) -> Optional[int]:
        """Nearest-player-to-focus possession attribution.

        Returns the index of the closest player within the proximity
        radius, or None if the focus is contested (no player within
        radius) or confidence is too low.
        """
        if focus_confidence < 0.15 or not detections:
            return None
        distances = np.array([np.linalg.norm(d.pitch_position - focus_point)
                              for d in detections])
        best = int(np.argmin(distances))
        if distances[best] <= self.cfg.possession_proximity_m:
            return best
        return None

    # ------------------------------------------------------------------

    def _detect_pass(self, bearer: Optional[int], t: float) -> bool:
        """Detect a pass event as a change in the possessing player.

        Pass semantics: a pass is the transition between two known
        bearers, even if there is an interval of no-possession (ball
        in flight) in between. The last *known* bearer is remembered
        across intervals where ``bearer is None``.
        """
        if bearer is None:
            # Ball in flight — preserve last known bearer.
            return False
        if self._prev_bearer is None:
            # First-ever possession assignment — not a pass.
            self._prev_bearer = bearer
            return False
        if bearer == self._prev_bearer:
            return False
        # Possession transferred from a known previous bearer to a
        # different known bearer — this is a pass.
        self.pass_event_times.append(t)
        self.pass_count += 1
        self._prev_bearer = bearer
        return True

    def _count_passes_in_window(self, t: float) -> int:
        """Count passes within the configured trailing window."""
        w = self.cfg.pass_window_s
        while self.pass_event_times and (t - self.pass_event_times[0]) > w:
            self.pass_event_times.popleft()
        return len(self.pass_event_times)

    # ------------------------------------------------------------------

    def _evaluate_triggers(self, t: float,
                           passes_in_window: int,
                           focus_speed: float) -> bool:
        """Decide whether the heavy-analysis trigger is active."""
        cfg = self.cfg
        fire = (passes_in_window >= cfg.pass_count_trigger
                or focus_speed >= cfg.speed_trigger_m_s)
        if fire:
            self._last_trigger_t = t
            return True
        if self._last_trigger_t is not None and (t - self._last_trigger_t) <= cfg.cooldown_s:
            return True
        return False

    # ------------------------------------------------------------------

    def _role_bind_goalkeeper(self,
                              detections: List[PlayerDetection],
                              focus_point: np.ndarray,
                              focus_velocity_vec: np.ndarray
                              ) -> Tuple[Optional[int], Optional[int]]:
        """Materialise the goalkeeper role on demand.

        Spatial gate: focus point is inside one of the two goal disks.
        If so, bind the role to the defending-team player closest to
        the goal mouth whose torso faces the focus.

        Returns (defending_team_id, player_index) or (None, None).
        """
        cfg = self.cfg
        # Which goal disk does the focus sit in?
        if focus_point[0] <= cfg.goal_left_x + cfg.goalkeeper_disk_radius_m:
            defending_team = 0
            goal_x = cfg.goal_left_x
        elif focus_point[0] >= cfg.goal_right_x - cfg.goalkeeper_disk_radius_m:
            defending_team = 1
            goal_x = cfg.goal_right_x
        else:
            return None, None

        goal_mouth = np.array([goal_x, 0.0])
        best_idx = None
        best_score = float("inf")
        for i, d in enumerate(detections):
            if d.team is not None and d.team != defending_team:
                continue
            dist_to_goal = float(np.linalg.norm(d.pitch_position - goal_mouth))
            if dist_to_goal > cfg.goalkeeper_disk_radius_m * 1.5:
                continue
            # Alignment of facing with focus direction
            to_focus = focus_point - d.pitch_position
            tn = float(np.linalg.norm(to_focus))
            if tn < 1e-3:
                align = 1.0
            else:
                align = float((d.facing @ to_focus) / tn)
            score = dist_to_goal - 2.0 * align
            if score < best_score:
                best_score = score
                best_idx = i
        return defending_team, best_idx

    # ------------------------------------------------------------------

    def _detect_duels(self,
                      detections: List[PlayerDetection],
                      focus_point: np.ndarray,
                      pair_radius_m: float = 2.5
                      ) -> List[Tuple[int, int]]:
        """Detect cognate-pair (attacker, defender) duels.

        Pair criterion: two players from different teams both within
        ``pair_radius_m`` of the focus point.
        """
        pairs: List[Tuple[int, int]] = []
        near = [i for i, d in enumerate(detections)
                if np.linalg.norm(d.pitch_position - focus_point) <= pair_radius_m]
        for i_a in near:
            for i_b in near:
                if i_a >= i_b:
                    continue
                ta = detections[i_a].team
                tb = detections[i_b].team
                if ta is None or tb is None or ta == tb:
                    continue
                pairs.append((i_a, i_b))
        return pairs

    # ------------------------------------------------------------------

    def update(self, frame, t_seconds: float) -> FrameOutput:
        detections = self.detector.detect(frame, t_seconds)
        if not detections:
            empty = FrameOutput(
                t_seconds=t_seconds,
                focus_point=np.array([0.0, 0.0]),
                focus_confidence=0.0,
                focus_velocity_m_s=0.0,
                n_supporting=0,
                bearer_index=None,
                pass_count_in_window=self._count_passes_in_window(t_seconds),
                trigger_active=False,
                goalkeeper_role_active_team=None,
                bound_goalkeeper_index=None,
                duels=[],
                detections=detections,
            )
            self.focus_history.append((t_seconds, empty.focus_point))
            return empty

        # Bootstrap with uniform weights, then refine with the
        # previous frame's bearer guess.
        rays = [AttentionRay(position=d.pitch_position,
                             facing=d.facing,
                             weight=self.cfg.weight_default)
                for d in detections]
        bootstrap = robust_focus_point(rays)

        bearer_idx = self._attribute_possession(detections,
                                                bootstrap.point,
                                                bootstrap.confidence)

        weights = self._per_player_weights(detections, bearer_idx)
        rays = [AttentionRay(position=d.pitch_position,
                             facing=d.facing,
                             weight=float(weights[i]))
                for i, d in enumerate(detections)]
        focus = robust_focus_point(rays)

        # Update history; computing focus velocity.
        self.focus_history.append((t_seconds, focus.point))
        focus_speed = self._focus_velocity(t_seconds)

        # Pass detection + windowed count.
        self._detect_pass(bearer_idx, t_seconds)
        passes_in_window = self._count_passes_in_window(t_seconds)

        # Event gating.
        triggered = self._evaluate_triggers(t_seconds,
                                            passes_in_window,
                                            focus_speed)

        # Role binding (gated by trigger to save compute).
        gk_team: Optional[int] = None
        gk_idx: Optional[int] = None
        if triggered:
            # Focus velocity vector for spatial trigger refinements.
            vel_vec = self._focus_velocity_vector(t_seconds)
            gk_team, gk_idx = self._role_bind_goalkeeper(detections,
                                                         focus.point,
                                                         vel_vec)

        # Duel detection (cheap; always on).
        duels = self._detect_duels(detections, focus.point)

        return FrameOutput(
            t_seconds=t_seconds,
            focus_point=focus.point,
            focus_confidence=focus.confidence,
            focus_velocity_m_s=focus_speed,
            n_supporting=focus.n_supporting,
            bearer_index=bearer_idx,
            pass_count_in_window=passes_in_window,
            trigger_active=triggered,
            goalkeeper_role_active_team=gk_team,
            bound_goalkeeper_index=gk_idx,
            duels=duels,
            detections=detections,
        )

    # ------------------------------------------------------------------

    def _focus_velocity_vector(self, t_now: float) -> np.ndarray:
        """Same as ``_focus_velocity`` but returns the vector."""
        if len(self.focus_history) < 2:
            return np.array([0.0, 0.0])
        cfg = self.cfg
        window_start = t_now - cfg.speed_smoothing_s
        relevant = [(tt, p) for tt, p in self.focus_history if tt >= window_start]
        if len(relevant) < 2:
            return np.array([0.0, 0.0])
        t0, p0 = relevant[0]
        t1, p1 = relevant[-1]
        if t1 - t0 < 1e-4:
            return np.array([0.0, 0.0])
        return (p1 - p0) / (t1 - t0)
