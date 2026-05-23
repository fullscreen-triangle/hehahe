# Specialised Football Ball Tracker

Reference implementation for the **observation-operator** layer of the
companion paper *"Football as a Partially Observable Bioreactor:
Backward Biomechanical Accounting via the Ball Observation Operator."*

## Specialisation

This tracker does not detect the ball directly. The ball is, by the
sport's definition, the point where collective attention converges; we
estimate it from **player torso orientations** + **pitch-perimeter
billboard homography**, never from a small-object detector on the ball
itself.

The estimated ball location at any instant is the weighted fixed point

```
    b* = argmin_b  Σᵢ wᵢ · d⊥(b, Lᵢ)²
```

where each player contributes an attention ray `Lᵢ = {pᵢ + t·fᵢ}` from
their pitch position `pᵢ` in their torso facing direction `fᵢ`.
Closed-form solve, robust IRLS with Huber weighting, in-front-of-player
constraint, role-binding hooks, event-gated heavy-analysis triggers.

## Module layout

```
tracker/
├── attention_focus.py   # weighted ray-intersection solver (the core)
├── homography.py        # billboard ↔ pitch homography (DLT + RANSAC)
├── detector.py          # PlayerDetector abstract + MockDetector
├── tracker.py           # BallTracker orchestrator (event gating, GK binding)
├── validate_tracker.py  # 6-experiment validation suite (writes JSON)
└── __init__.py
```

## Validation

```bash
python validate_tracker.py
```

Six experiments cover the core claims:

| # | Experiment | Result |
|---|---|---|
| 1 | Stationary ball — ring of 11 players | mean error 0.30 m |
| 2 | Moving ball with reaction lag | mean 1.21 m, max 4.17 m |
| 3 | Off-ball runner robustness (IRLS) | naive 1.93 m → robust 0.23 m (8× improvement) |
| 4 | Billboard homography (DLT + RANSAC) | reproj 0.18 m / 1.24 px |
| 5 | Pass count and trigger gating | 4 passes detected, trigger fired correctly |
| 6 | Goalkeeper role binding | 100% correct role binding in defensive box |

Output: `validation_results.json` with per-experiment metrics and a
`pass: true/false` summary flag.

## Usage

### Quick start (synthetic scene)

```python
import numpy as np
from tracker import (
    BallTracker, MockDetector, TrackerConfig,
    circle_facing_ball,
)

# Build a synthetic scene: 11 players in a ring, ball oscillating.
players = circle_facing_ball(11, radius=15.0)
def ball_traj(t):
    return np.array([10 * np.sin(0.5 * t), 6 * np.cos(0.5 * t)])
det = MockDetector(players, ball_traj,
                   position_noise_m=0.1, facing_noise_rad=0.05)
tracker = BallTracker(det, config=TrackerConfig())

# Feed frames.
for k in range(400):
    t = k * 0.05
    out = tracker.update(None, t)
    print(f"t={t:5.2f}  focus={out.focus_point}  "
          f"speed={out.focus_velocity_m_s:.1f} m/s  "
          f"bearer={out.bearer_index}  "
          f"trigger={out.trigger_active}")
```

### Plugging in a real video detector

```python
from tracker import PlayerDetector, PlayerDetection

class YOLOPoseDetector(PlayerDetector):
    def __init__(self, model, homography):
        self.model = model
        self.H = homography  # solved from billboard correspondences

    def detect(self, frame, t_seconds):
        out = self.model(frame)
        detections = []
        for box, kps in zip(out.boxes, out.keypoints):
            image_xy = box.center_bottom()           # foot midpoint
            pitch_xy = apply_homography(image_xy, self.H)
            facing = torso_yaw_from_keypoints(kps)   # unit vec in pitch
            detections.append(PlayerDetection(
                pitch_position=pitch_xy,
                facing=facing,
                confidence=box.conf,
            ))
        return detections
```

The tracker is detector-agnostic; any backend that emits
`PlayerDetection` records works.

## API surface

### Attention solver

```python
from tracker import (AttentionRay, robust_focus_point,
                     solve_focus_point, solve_from_arrays)

# Each player → an AttentionRay.
rays = [AttentionRay(position=p, facing=f, weight=w) for ...]
estimate = robust_focus_point(rays)   # IRLS with Huber + in-front guard
# estimate.point, estimate.confidence, estimate.residual_rms, ...
```

### Billboard homography

```python
from tracker import (PointCorrespondence,
                     solve_homography_dlt, solve_homography_ransac,
                     calibrate_from_billboard,
                     image_to_pitch, pitch_to_image)

corrs = [PointCorrespondence(image=(u, v), world=(X, Y)) for ...]
H = solve_homography_dlt(corrs)           # 4+ correspondences
H_robust, inliers = solve_homography_ransac(corrs)  # with outliers

pitch_xy = image_to_pitch((u, v), H.H)
image_xy = pitch_to_image((X, Y), H.H_inv)
```

### Tracker

```python
from tracker import BallTracker, TrackerConfig

cfg = TrackerConfig(
    pass_count_trigger=3,
    pass_window_s=5.0,
    speed_trigger_m_s=12.0,
    cooldown_s=2.0,
)
tracker = BallTracker(detector, calibration=billboard_cal, config=cfg)
out = tracker.update(frame, t_seconds)  # FrameOutput dataclass
```

`FrameOutput` carries: `focus_point` (pitch metres), `focus_confidence`,
`focus_velocity_m_s`, `bearer_index`, `pass_count_in_window`,
`trigger_active`, `goalkeeper_role_active_team`,
`bound_goalkeeper_index`, `duels`, `detections`.

## Two-tier compute model

- **Ambient (always on, cheap).** Player detection → torso facings →
  attention-focus solve → possession attribution → pass counter →
  focus speed. Drives the on-screen ball card.
- **Active (event-gated, expensive).** Fires when
  `passes_in_window ≥ N` *or* `focus_velocity ≥ v_thresh`. Runs the
  heavy pipeline (foot-contact extraction, biomechanical accounting,
  R_ens estimation, full role binding). Cools down after each fire.

The trigger gate is implemented in `tracker.py:_evaluate_triggers`;
config knobs in `TrackerConfig`.

## Role-binding hooks

The framework's lazy role-materialisation idea is implemented for the
goalkeeper case in `_role_bind_goalkeeper`. Extension to other roles
(striker, playmaker, sweeper) follows the same pattern: a categorical
trigger (the morphism flow heads toward a particular object) plus a
spatial trigger (the focus point reaches the relevant region of the
pitch). When both fire, the role is bound to the player whose position
and facing best satisfy the role's activation conditions.

## What this is not

- **Not a generic ball detector.** It estimates the attention-focus
  point. Almost always identical to the ball position; when they
  diverge (deflection, reaction lag), the gap is itself a measurable
  signal — see the parent paper §3.
- **Not a tactical-prediction engine.** It produces a per-frame
  biomechanical ledger; downstream analysis decides what to do with it.
- **Not a person-identification system.** Players are categorical
  objects in a role category. The tracker binds roles to bodies on
  demand; jersey-colour or face-recognition layers can sit on top of
  it but are not part of the framework.
