from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.dependencies import get_current_user
from app.services.goal_service import GoalService
from app.services.debt_service import DebtService
from app.schemas.goal import (
    GoalCreate, GoalUpdate, GoalResponse, GoalTimeline,
    ScenarioComparison, GoalDashboard
)

router = APIRouter(prefix="/goals", tags=["goals"])


@router.post("/create", response_model=GoalResponse)
async def create_goal(
        goal: GoalCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Create new financial goal"""

    db_goal = GoalService.create_goal(db, current_user.id, goal)
    return db_goal


@router.get("/list", response_model=list[GoalResponse])
async def get_goals(
        status: str = Query(None, description="Filter by status (active, achieved, paused, cancelled)"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get user's financial goals"""

    goals = GoalService.get_user_goals(db, current_user.id, status)
    return goals


@router.get("/{goal_id}/timeline", response_model=GoalTimeline)
async def get_goal_timeline(
        goal_id: int,
        monthly_income: float = Query(..., gt=0, description="Monthly income"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get goal timeline with debt payoff integration"""

    goal = GoalService.get_goal_by_id(db, goal_id)

    if not goal or goal.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Goal not found")

    debts = DebtService.get_active_debts(db, current_user.id)
    timeline = GoalService.calculate_goal_timeline(db, current_user.id, goal, monthly_income * 0.25, debts)

    return timeline


@router.get("/{goal_id}/scenarios", response_model=list[dict])
async def get_goal_scenarios(
        goal_id: int,
        monthly_income: float = Query(..., gt=0, description="Monthly income"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get what-if scenarios for goal"""

    goal = GoalService.get_goal_by_id(db, goal_id)

    if not goal or goal.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Goal not found")

    debts = DebtService.get_active_debts(db, current_user.id)
    scenarios = GoalService.generate_scenarios(db, current_user.id, goal, monthly_income, debts)

    return scenarios


@router.get("/dashboard/complete", response_model=GoalDashboard)
async def get_goal_dashboard(
        monthly_income: float = Query(..., gt=0, description="Monthly income"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get complete goal dashboard with all goals and timelines"""

    dashboard = GoalService.get_goal_dashboard(db, current_user.id, monthly_income)
    return dashboard


@router.patch("/{goal_id}", response_model=GoalResponse)
async def update_goal(
        goal_id: int,
        update_data: GoalUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Update goal"""

    goal = GoalService.get_goal_by_id(db, goal_id)

    if not goal or goal.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Goal not found")

    updated = GoalService.update_goal(db, goal_id, update_data)
    return updated


@router.delete("/{goal_id}")
async def delete_goal(
        goal_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Delete goal"""

    goal = GoalService.get_goal_by_id(db, goal_id)

    if not goal or goal.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Goal not found")

    db.delete(goal)
    db.commit()

    return {"message": "Goal deleted"}
