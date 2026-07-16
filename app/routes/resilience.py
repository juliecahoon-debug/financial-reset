from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.resilience import ResilienceScore
from app.services.resilience import calculate_resilience_score
from app.services.momentum import calculate_momentum
from app.services.friction import calculate_friction_points

router = APIRouter(prefix="/resilience", tags=["resilience"])


@router.post("/calculate")
async def calculate_score(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Calculate (or recalculate) the resilience score for the authenticated user.

    1. Fetches financial data from the DB (+ Plaid placeholders)
    2. Scores all 7 dimensions
    3. Weights and sums to a 0-100 total
    4. Persists the result to resilience_scores
    5. Returns the score, breakdown, and trend vs. previous calculation
    """
    # Fetch previous score for trend comparison
    previous = (
        db.query(ResilienceScore)
        .filter(ResilienceScore.user_id == current_user.id)
        .order_by(ResilienceScore.calculated_at.desc())
        .first()
    )

    result = await calculate_resilience_score(current_user.id, db)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    # Persist new score
    score_record = ResilienceScore(
        user_id=current_user.id,
        total_score=result["total_score"],
        financial_state=result["financial_state"],
        # Dimension scores
        emergency_buffer_score=result["scores"]["emergency_buffer"],
        debt_service_ratio_score=result["scores"]["debt_service_ratio"],
        income_stability_score=result["scores"]["income_stability"],
        insurance_coverage_score=result["scores"]["insurance_coverage"],
        concentration_risk_score=result["scores"]["concentration_risk"],
        credit_access_score=result["scores"]["credit_access"],
        recovery_velocity_score=result["scores"]["recovery_velocity"],
        # Raw values
        emergency_buffer_months=result["raw"]["emergency_buffer_months"],
        debt_service_ratio_percent=result["raw"]["debt_service_ratio_percent"],
        income_stability_percent=result["raw"]["income_stability_percent"],
        insurance_coverage_percent=result["raw"]["insurance_coverage_percent"],
        concentration_risk_ratio=result["raw"]["concentration_risk_ratio"],
        credit_utilization_percent=result["raw"]["credit_utilization_percent"],
        recovery_months=result["raw"]["recovery_months"],
    )
    db.add(score_record)
    db.commit()
    db.refresh(score_record)

    # Trend vs. previous
    trend = None
    if previous:
        diff = result["total_score"] - previous.total_score
        if diff > 0.5:
            trend = "improving"
        elif diff < -0.5:
            trend = "declining"
        else:
            trend = "stable"

    return {
        "total_score": result["total_score"],
        "financial_state": result["financial_state"],
        "scores": result["scores"],
        "raw_data": result["raw"],
        "previous_score": round(previous.total_score, 1) if previous else None,
        "trend": trend,
        "calculated_at": score_record.calculated_at,
    }


@router.get("/current")
async def get_current_score(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the most recently calculated resilience score for the authenticated user."""
    score = (
        db.query(ResilienceScore)
        .filter(ResilienceScore.user_id == current_user.id)
        .order_by(ResilienceScore.calculated_at.desc())
        .first()
    )

    if not score:
        raise HTTPException(
            status_code=404,
            detail="No resilience score found. Call POST /resilience/calculate first.",
        )

    return {
        "total_score": score.total_score,
        "financial_state": score.financial_state,
        "scores": {
            "emergency_buffer":   score.emergency_buffer_score,
            "debt_service_ratio": score.debt_service_ratio_score,
            "income_stability":   score.income_stability_score,
            "insurance_coverage": score.insurance_coverage_score,
            "concentration_risk": score.concentration_risk_score,
            "credit_access":      score.credit_access_score,
            "recovery_velocity":  score.recovery_velocity_score,
        },
        "raw_data": {
            "emergency_buffer_months":    score.emergency_buffer_months,
            "debt_service_ratio_percent": score.debt_service_ratio_percent,
            "income_stability_percent":   score.income_stability_percent,
            "insurance_coverage_percent": score.insurance_coverage_percent,
            "concentration_risk_ratio":   score.concentration_risk_ratio,
            "credit_utilization_percent": score.credit_utilization_percent,
            "recovery_months":            score.recovery_months,
        },
        "calculated_at": score.calculated_at,
    }


@router.get("/momentum")
async def get_momentum(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return momentum (rate of change) for the authenticated user's Resilience Score.
    Compares current score to 30-day, 90-day, and 6-month snapshots.
    Also persists the calculation to momentum_calculations for trend history.
    """
    result = await calculate_momentum(current_user.id, db)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/friction")
async def get_friction(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Identify friction points (obstacles) blocking financial progress
    for the authenticated user. Returns top 5 by severity + impact,
    with recommended actions and estimated resilience improvement.
    """
    result = await calculate_friction_points(current_user.id, db)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/history")
async def get_score_history(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return up to `limit` past resilience scores for the authenticated user (newest first)."""
    scores = (
        db.query(ResilienceScore)
        .filter(ResilienceScore.user_id == current_user.id)
        .order_by(ResilienceScore.calculated_at.desc())
        .limit(min(limit, 50))
        .all()
    )

    return [
        {
            "id": s.id,
            "total_score": s.total_score,
            "financial_state": s.financial_state,
            "calculated_at": s.calculated_at,
        }
        for s in scores
    ]
