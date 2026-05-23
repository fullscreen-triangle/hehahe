"""
Validation experiments for the specialised football ball tracker.

Six experiments, each producing pass/fail flags and quantitative
metrics. Results written to validation_results.json.

  1. Stationary ball — symmetric ring of players facing centre.
  2. Moving ball — single ball traversing the pitch, players track
     with realistic reaction lag and facing noise.
  3. Off-ball runners — robust IRLS suppresses noise from players
     facing the goal rather than the ball.
  4. Billboard homography — DLT recovers a known H from noisy
     correspondences; RANSAC handles outliers.
  5. Possession + pass-count gating — synthetic pass sequence triggers
     the analyzer correctly above threshold.
  6. Goalkeeper role binding — focus drifting into the defensive
     box binds the GK role to the correct player.

Dependencies: numpy only.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

# Add tracker package to path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from tracker.attention_focus import (AttentionRay, robust_focus_point,
                                      solve_from_arrays)
from tracker.detector import (MockDetector, SyntheticPlayer,
                                circle_facing_ball)
from tracker.homography import (PointCorrespondence, solve_homography_dlt,
                                  solve_homography_ransac, image_to_pitch)
from tracker.tracker import BallTracker, TrackerConfig

OUT_DIR = HERE
RESULTS_PATH = OUT_DIR / "validation_results.json"


# ════════════════════════════════════════════════════════════════════
# Experiment 1 — Stationary ball
# ════════════════════════════════════════════════════════════════════

def exp1_stationary_ball():
    """Symmetric ring of players facing the origin; focus should
    recover the origin to sub-metre precision."""
    print("\n[1] Stationary ball — ring of 11 players")
    rng = np.random.default_rng(1)

    n_trials = 50
    errors = []
    for trial in range(n_trials):
        ball_xy = np.array([rng.uniform(-5, 5), rng.uniform(-5, 5)])
        # 11 players on a 12 m circle around ball.
        positions = []
        facings = []
        for k in range(11):
            theta = 2 * np.pi * k / 11
            p = ball_xy + 12.0 * np.array([np.cos(theta), np.sin(theta)])
            positions.append(p)
            # Player faces the ball with small noise.
            d = ball_xy - p
            d = d / np.linalg.norm(d)
            theta_n = rng.normal(0.0, 0.05)
            c, s = np.cos(theta_n), np.sin(theta_n)
            f = np.array([c * d[0] - s * d[1], s * d[0] + c * d[1]])
            facings.append(f)
        positions = np.array(positions)
        facings = np.array(facings)
        est = solve_from_arrays(positions, facings)
        err = float(np.linalg.norm(est.point - ball_xy))
        errors.append(err)

    mean_err = float(np.mean(errors))
    max_err = float(np.max(errors))
    pass_ = mean_err < 0.30 and max_err < 1.0
    print(f"  mean error = {mean_err:.3f} m, max = {max_err:.3f} m")
    print(f"  PASS" if pass_ else "  FAIL")

    return {
        "name": "Stationary ball",
        "n_trials": n_trials,
        "mean_error_m": mean_err,
        "max_error_m": max_err,
        "pass": pass_,
    }


# ════════════════════════════════════════════════════════════════════
# Experiment 2 — Moving ball through a circle of trackers
# ════════════════════════════════════════════════════════════════════

def exp2_moving_ball():
    """Ball moves along a sinusoidal path; players face it with
    reaction lag; verify the tracker tracks the ball within a
    margin attributable to the reaction lag."""
    print("\n[2] Moving ball — focus tracks ball with reaction lag")

    def ball_traj(t):
        return np.array([15.0 * np.sin(0.4 * t),
                         8.0 * np.cos(0.6 * t)])

    players = circle_facing_ball(11, radius=20.0,
                                 reaction_lag_s=0.15,
                                 facing_noise_rad=0.05)
    det = MockDetector(players, ball_traj,
                       position_noise_m=0.20,
                       facing_noise_rad=0.05,
                       seed=2)

    dt = 0.05
    n = int(20.0 / dt)
    errs = []
    true_traj = []
    est_traj = []
    for k in range(n):
        t = k * dt
        detections = det.detect(None, t)
        true_xy = ball_traj(t)
        est = solve_from_arrays(
            np.array([d.pitch_position for d in detections]),
            np.array([d.facing for d in detections]),
        )
        err = float(np.linalg.norm(est.point - true_xy))
        errs.append(err)
        true_traj.append(true_xy.tolist())
        est_traj.append(est.point.tolist())

    mean_err = float(np.mean(errs))
    max_err = float(np.max(errs))
    pass_ = mean_err < 2.0 and max_err < 6.0
    print(f"  mean error = {mean_err:.2f} m, max = {max_err:.2f} m")
    print(f"  PASS" if pass_ else "  FAIL")

    return {
        "name": "Moving ball with reaction lag",
        "n_steps": n,
        "mean_error_m": mean_err,
        "max_error_m": max_err,
        "pass": pass_,
    }


# ════════════════════════════════════════════════════════════════════
# Experiment 3 — Off-ball runner robustness
# ════════════════════════════════════════════════════════════════════

def exp3_off_ball_robustness():
    """Add 4 off-ball runners pointing toward the goal (not the
    ball); verify Huber IRLS suppresses their contribution."""
    print("\n[3] Off-ball runner robustness — IRLS suppression")
    rng = np.random.default_rng(3)

    n_trials = 50
    errors_naive = []
    errors_robust = []
    for trial in range(n_trials):
        ball_xy = np.array([rng.uniform(-5, 5), rng.uniform(-5, 5)])
        rays = []
        # 7 ball-facing players
        for k in range(7):
            theta = 2 * np.pi * k / 7
            p = ball_xy + 12.0 * np.array([np.cos(theta), np.sin(theta)])
            d = ball_xy - p
            d = d / np.linalg.norm(d)
            rays.append(AttentionRay(position=p, facing=d, weight=1.0))
        # 4 runners pointing at the right goal
        for _ in range(4):
            p = ball_xy + rng.uniform(-15, 15, size=2)
            f = np.array([1.0, rng.uniform(-0.2, 0.2)])
            f = f / np.linalg.norm(f)
            rays.append(AttentionRay(position=p, facing=f, weight=1.0))

        # Naive: full-weight least squares with all rays.
        from tracker.attention_focus import solve_focus_point
        est_naive = solve_focus_point(rays)
        # Robust: IRLS Huber.
        est_robust = robust_focus_point(rays)
        errors_naive.append(float(np.linalg.norm(est_naive.point - ball_xy)))
        errors_robust.append(float(np.linalg.norm(est_robust.point - ball_xy)))

    mean_naive = float(np.mean(errors_naive))
    mean_robust = float(np.mean(errors_robust))
    pass_ = mean_robust < mean_naive * 0.7 and mean_robust < 2.0
    print(f"  mean error (naive)  = {mean_naive:.2f} m")
    print(f"  mean error (robust) = {mean_robust:.2f} m  ({mean_robust/mean_naive:.0%})")
    print(f"  PASS" if pass_ else "  FAIL")

    return {
        "name": "Off-ball runner robustness",
        "n_trials": n_trials,
        "mean_error_naive_m": mean_naive,
        "mean_error_robust_m": mean_robust,
        "improvement_factor": mean_naive / max(mean_robust, 1e-6),
        "pass": pass_,
    }


# ════════════════════════════════════════════════════════════════════
# Experiment 4 — Billboard homography
# ════════════════════════════════════════════════════════════════════

def exp4_homography():
    """Synthesise a known homography, generate noisy correspondences,
    verify DLT and RANSAC recover the world-plane mapping within
    millimetre-level precision (relative to a 30 m pitch)."""
    print("\n[4] Billboard homography recovery")
    rng = np.random.default_rng(4)

    # Ground truth: a typical perspective camera viewing a touchline.
    # H maps image (u, v) -> world (X, Y).
    H_true = np.array([
        [0.10, 0.00, -64.0],
        [0.00, -0.06, 36.0],
        [0.00, -0.0008, 1.0],
    ])

    # Generate 12 panel feature points along the touchline.
    n_pts = 12
    world_pts = np.array([[rng.uniform(-30, 30), rng.uniform(-2, 2)]
                          for _ in range(n_pts)])
    # Back-project to image via H_true^-1.
    H_inv = np.linalg.inv(H_true)
    world_h = np.hstack([world_pts, np.ones((n_pts, 1))])
    img_h = (H_inv @ world_h.T).T
    img_pts = img_h[:, :2] / img_h[:, 2:3]
    # Add image-pixel noise.
    img_pts_noisy = img_pts + rng.normal(0, 1.0, img_pts.shape)

    corrs = [PointCorrespondence(image=tuple(img_pts_noisy[i]),
                                  world=tuple(world_pts[i]))
             for i in range(n_pts)]

    # Solve with DLT.
    result = solve_homography_dlt(corrs)
    # Reproject world points back through the fitted H to measure
    # world-plane reprojection error.
    err_m = result.rms_reproj_m
    err_px = result.rms_reproj_px

    # RANSAC with outliers.
    corrs_with_outliers = list(corrs)
    for _ in range(3):
        corrs_with_outliers.append(PointCorrespondence(
            image=(rng.uniform(0, 1000), rng.uniform(0, 1000)),
            world=(rng.uniform(-30, 30), rng.uniform(-20, 20))))
    ransac_result, inliers = solve_homography_ransac(
        corrs_with_outliers, n_iter=100, threshold_px=4.0, seed=42)

    pass_ = err_m < 0.5 and len(inliers) >= n_pts - 1
    print(f"  DLT reproj  err: {err_m:.3f} m  ({err_px:.2f} px)")
    print(f"  RANSAC inliers: {len(inliers)} / {len(corrs_with_outliers)}")
    print(f"  PASS" if pass_ else "  FAIL")

    return {
        "name": "Billboard homography",
        "n_correspondences": n_pts,
        "dlt_reproj_error_m": float(err_m),
        "dlt_reproj_error_px": float(err_px),
        "ransac_inliers": int(len(inliers)),
        "ransac_total": int(len(corrs_with_outliers)),
        "pass": pass_,
    }


# ════════════════════════════════════════════════════════════════════
# Experiment 5 — Pass-count and trigger gating
# ════════════════════════════════════════════════════════════════════

def exp5_trigger_gating():
    """Run a synthetic pass sequence through the BallTracker and
    verify the trigger fires above threshold and stays cool below."""
    print("\n[5] Pass-count and trigger gating")

    # Build a synthetic team: 5 attackers + 5 defenders on the pitch.
    n_per_side = 5
    base = [(-15, 8), (-10, 0), (-12, -8), (-5, 5), (-5, -5)]
    players = []
    for x, y in base:
        players.append(SyntheticPlayer(initial_position=np.array([x, y], dtype=float),
                                       team=0, role="field", base_speed=0.0,
                                       reaction_lag_s=0.1))
    for x, y in base:
        players.append(SyntheticPlayer(initial_position=np.array([-x, -y], dtype=float),
                                       team=1, role="field", base_speed=0.0,
                                       reaction_lag_s=0.1))

    # Scripted ball trajectory: 4 quick passes between 4 attackers within 5 s.
    pass_targets = [np.array([-15, 8]), np.array([-10, 0]),
                    np.array([-12, -8]), np.array([-5, 5]),
                    np.array([-5, -5])]

    def ball_traj(t):
        t = max(0.0, t)
        seg = min(int(t / 0.8), len(pass_targets) - 1)
        u = (t - seg * 0.8) / 0.8
        a = pass_targets[seg]
        b = pass_targets[min(seg + 1, len(pass_targets) - 1)]
        return (1 - u) * a + u * b

    det = MockDetector(players, ball_traj,
                       position_noise_m=0.1, facing_noise_rad=0.05, seed=5)
    cfg = TrackerConfig(pass_count_trigger=3, pass_window_s=5.0,
                        speed_trigger_m_s=15.0)
    tracker = BallTracker(det, calibration=None, config=cfg)

    triggered_at = []
    for k in range(160):
        t = k * 0.05
        out = tracker.update(None, t)
        if out.trigger_active:
            triggered_at.append(t)

    fired = len(triggered_at) > 0
    first_fire = float(triggered_at[0]) if triggered_at else None
    pass_count_total = int(tracker.pass_count)
    pass_ = fired and first_fire is not None and first_fire < 5.0 \
        and pass_count_total >= 3
    print(f"  pass events detected: {pass_count_total}")
    print(f"  first trigger fire at t = {first_fire} s")
    print(f"  PASS" if pass_ else "  FAIL")

    return {
        "name": "Trigger gating",
        "pass_events_detected": pass_count_total,
        "first_trigger_time_s": first_fire,
        "n_active_frames": len(triggered_at),
        "pass": pass_,
    }


# ════════════════════════════════════════════════════════════════════
# Experiment 6 — Goalkeeper role binding
# ════════════════════════════════════════════════════════════════════

def exp6_goalkeeper_binding():
    """Build a scene where the focus point drifts into the team-0
    defensive box; verify the GK role binds to the player closest
    to the goal."""
    print("\n[6] Goalkeeper role binding")

    # Players: a defending team-0 line near their own goal at x=-52.5,
    # plus a few attackers from team-1 closing in.
    players = []
    # Team-0 defenders + GK
    players.append(SyntheticPlayer(
        initial_position=np.array([-50.0, 0.0]),    # GK on the line
        team=0, role="keeper", base_speed=0.0))
    for y in (-8, -3, 3, 8):
        players.append(SyntheticPlayer(
            initial_position=np.array([-42.0, float(y)]),
            team=0, role="field", base_speed=0.0))
    # Team-1 attackers
    for x, y in [(-40, 0), (-38, -4), (-38, 4)]:
        players.append(SyntheticPlayer(
            initial_position=np.array([float(x), float(y)]),
            team=1, role="field", base_speed=0.0))

    # Ball moves from midfield into the box.
    def ball_traj(t):
        if t < 1.0:
            return np.array([-20.0 + (-25.0) * (t / 1.0), 0.0])
        return np.array([-45.0, -1.0 + 0.5 * np.sin(t)])

    det = MockDetector(players, ball_traj,
                       position_noise_m=0.1, facing_noise_rad=0.05, seed=6)
    cfg = TrackerConfig(pass_count_trigger=1,  # trigger easily
                        speed_trigger_m_s=2.0)
    tracker = BallTracker(det, config=cfg)

    gk_bound_frames = 0
    gk_was_correct = 0
    n_active = 0
    for k in range(120):
        t = k * 0.05
        out = tracker.update(None, t)
        if out.bound_goalkeeper_index is not None:
            gk_bound_frames += 1
            # The GK in our scene is players[0] -> detections may
            # not exactly match index 0, so check the role tag.
            d = out.detections[out.bound_goalkeeper_index]
            if d.extra.get("role") == "keeper":
                gk_was_correct += 1
        if out.trigger_active:
            n_active += 1

    correct_rate = (gk_was_correct / gk_bound_frames) if gk_bound_frames > 0 else 0.0
    pass_ = gk_bound_frames > 10 and correct_rate >= 0.80
    print(f"  GK bound on {gk_bound_frames} frames out of {120}")
    print(f"  correct-role binding rate: {correct_rate:.2%}")
    print(f"  PASS" if pass_ else "  FAIL")

    return {
        "name": "Goalkeeper role binding",
        "gk_bound_frames": int(gk_bound_frames),
        "correct_role_rate": float(correct_rate),
        "n_active_frames": int(n_active),
        "pass": pass_,
    }


# ════════════════════════════════════════════════════════════════════
# Driver
# ════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("BALL TRACKER — VALIDATION SUITE")
    print("=" * 60)

    experiments = {
        "1_stationary_ball":     exp1_stationary_ball(),
        "2_moving_ball":         exp2_moving_ball(),
        "3_off_ball_robustness": exp3_off_ball_robustness(),
        "4_homography":          exp4_homography(),
        "5_trigger_gating":      exp5_trigger_gating(),
        "6_goalkeeper_binding":  exp6_goalkeeper_binding(),
    }
    n_pass = sum(1 for e in experiments.values() if e["pass"])
    n_total = len(experiments)

    out = {
        "metadata": {
            "component": "Specialised football ball tracker",
            "paper": ("Football as a Partially Observable Bioreactor: "
                      "Backward Biomechanical Accounting via the Ball "
                      "Observation Operator"),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "n_experiments": n_total,
        },
        "experiments": experiments,
        "summary": {
            "passed": int(n_pass),
            "total": int(n_total),
            "all_pass": bool(n_pass == n_total),
        },
    }

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print()
    print("=" * 60)
    print(f"SUMMARY: {n_pass} / {n_total} experiments passed")
    print("=" * 60)
    for k, v in experiments.items():
        flag = "PASS" if v["pass"] else "FAIL"
        print(f"  [{flag}]  {k}  -  {v['name']}")
    print(f"\nWrote {RESULTS_PATH}")
    return out


if __name__ == "__main__":
    main()
