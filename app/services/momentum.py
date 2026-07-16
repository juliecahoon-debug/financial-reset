from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.resilience import ResilienceScore
from app.models.momentum import MomentumCalculation


def _get_score_near(db: Session, user_id: int, days_ago: int, window: int = 5) -> ResilienceScore | None:
    """
    Find the most recent ResilienceScore within a ±window day band around `days_ago`.
    Uses a looser window so a user who calculates weekly still gets historical comparisons.
    """
    now = datetime.utcnow()
    return (
        db.query(ResilienceScore)
        .filter(
            ResilienceScore.user_id == user_id,
            ResilienceScore.calculated_at <= now - timedelta(days=days_ago),
            ResilienceScore.calculated_at >= now - timedelta(days=days_ago + window),
        )
        .order_by(ResilienceScore.calculated_at.desc())
        .first()
    )


async def calculate_momentum(user_id: int, db: Session) -> dict:
    """
    Calculate momentum (rate of change) in the user's Resilience Score.

    Compares current score to 30-day, 90-day, and 6-month snapshots.
    Returns direction, velocity (points/month), and a 30-day projection.
    """
    try:
        now = datetime.utcnow()

        # ── CURRENT SCORE ─────────────────────────────────────────────────────
        current = (
            db.query(ResilienceScore)
            .filter(ResilienceScore.user_id == user_id)
            .order_by(ResilienceScore.calculated_at.desc())
            .first()
        )

        if not current:
            return {
                "success": False,
                "error": "No resilience score found. Call POST /resilience/calculate first.",
            }

        current_value = current.total_score

        # ── HISTORICAL SNAPSHOTS ──────────────────────────────────────────────
        snap_30 = _get_score_near(db, user_id, days_ago=30)
        snap_90 = _get_score_near(db, user_id, days_ago=90)
        snap_6m = _get_score_near(db, user_id, days_ago=180)

        # ── MOMENTUM DELTAS ───────────────────────────────────────────────────
        momentum_30 = round(current_value - snap_30.total_score, 1) if snap_30 else None
        momentum_90 = round(current_value - snap_90.total_score, 1) if snap_90 else None
        momentum_6m = round(current_value - snap_6m.total_score, 1) if snap_6m else None

        # ── DIRECTION (primary: 30-day; fallback: 90-day) ────────────────────
        primary = momentum_30 if momentum_30 is not None else momentum_90
        if primary is None:
            direction = "unknown"
        elif primary > 2:
            direction = "improving"
        elif primary < -2:
            direction = "declining"
        else:
            direction = "stable"

        # ── VELOCITY (points per month) ───────────────────────────────────────
        # Prefer 90-day trend (more reliable); fall back to 30-day
        if momentum_90 is not None:
            velocity = round(momentum_90 / 3, 2)   # 90 days ≈ 3 months
        elif momentum_30 is not None:
            velocity = round(momentum_30, 2)         # treat as ~1 month
        else:
            velocity = 0.0

        # ── 30-DAY PROJECTION ─────────────────────────────────────────────────
        projected = round(max(0.0, min(100.0, current_value + velocity)), 1)

        # ── PERSIST ───────────────────────────────────────────────────────────
        record = MomentumCalculation(
            user_id=user_id,
            current_resilience_score=current_value,
            score_30_days_ago=snap_30.total_score if snap_30 else None,
            score_90_days_ago=snap_90.total_score if snap_90 else None,
            score_6_months_ago=snap_6m.total_score if snap_6m else None,
            momentum_30_days=momentum_30,
            momentum_90_days=momentum_90,
            momentum_6_months=momentum_6m,
            direction=direction,
            velocity_points_per_month=velocity,
            projected_score_30_days=projected,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        return {
            "success": True,
            "current_score": round(current_value, 1),
            "momentum_30_days": momentum_30,
            "momentum_90_days": momentum_90,
            "momentum_6_months": momentum_6m,
            "direction": direction,
            "velocity_points_per_month": velocity,
            "projected_score_30_days": projected,
            "calculated_at": record.calculated_at,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
