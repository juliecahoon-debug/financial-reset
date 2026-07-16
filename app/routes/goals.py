from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.dependencies import get_current_user
from app.services.debt_service import DebtService
from app.services.goal_service import GoalService
from app.schemas.goal import (
    GoalCreate, GoalUpdate, GoalResponse, GoalTimeline, GoalDashboard
)

router = APIRouter(prefix="/goals", tags=["goals"])


def _get_owned_goal(db: Session, goal_id: int, user_id: int):
    goal = GoalService.get_goal_by_id(db, goal_id)
    if not goal or goal.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    return goal


@router.post("/", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
async def create_goal(
        goal: GoalCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Create a new financial goal."""
    return GoalService.create_goal(db, current_user.id, goal)


@router.get("/", response_model=list[GoalResponse])
async def get_user_goals(
        goal_status: Optional[str] = Query("active"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """List the current user's goals."""
    return GoalService.get_user_goals(db, current_user.id, goal_status)


@router.get("/dashboard", response_model=GoalDashboard)
async def get_goal_dashboard(
        monthly_income: float = Query(..., ge=0),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get the complete goal dashboard."""
    return GoalService.get_goal_dashboard(db, current_user.id, monthly_income)


@router.get("/{goal_id}", response_model=GoalResponse)
async def get_goal(
        goal_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get a single goal."""
    return _get_owned_goal(db, goal_id, current_user.id)


@router.put("/{goal_id}", response_model=GoalResponse)
async def update_goal(
        goal_id: int,
        goal_update: GoalUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Update a goal."""
    _get_owned_goal(db, goal_id, current_user.id)
    return GoalService.update_goal(db, goal_id, goal_update)


@router.get("/{goal_id}/timeline", response_model=GoalTimeline)
async def get_goal_timeline(
        goal_id: int,
        monthly_debt_payment: float = Query(..., ge=0),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Calculate the goal timeline accounting for debt payoff."""
    goal = _get_owned_goal(db, goal_id, current_user.id)
    debts = DebtService.get_active_debts(db, current_user.id)
    return GoalService.calculate_goal_timeline(
        db, current_user.id, goal, monthly_debt_payment, debts
    )


@router.post("/{goal_id}/scenarios")
async def generate_scenarios(
        goal_id: int,
        monthly_income: float = Query(..., ge=0),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Generate what-if scenarios for a goal."""
    goal = _get_owned_goal(db, goal_id, current_user.id)
    debts = DebtService.get_active_debts(db, current_user.id)
    return GoalService.generate_scenarios(db, current_user.id, goal, monthly_income, debts)
