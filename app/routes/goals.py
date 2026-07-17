from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.services.goal_service import GoalService
from app.schemas.goal import GoalCreate, GoalUpdate

router = APIRouter(prefix="/goals", tags=["goals"])

@router.post("/")
def create_goal(
    goal: GoalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return GoalService.create_goal(db, current_user.id, goal)

@router.get("/")
def get_goals(
    status: str = "active",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return GoalService.get_user_goals(db, current_user.id, status)

@router.get("/dashboard")
def get_goal_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return GoalService.get_goal_dashboard(db, current_user.id)

@router.get("/{goal_id}/timeline")
def get_goal_timeline(
    goal_id: int,
    monthly_savings: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    goal = GoalService.get_goal_by_id(db, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return GoalService.calculate_goal_timeline(goal, monthly_savings)

@router.get("/{goal_id}/scenarios")
def get_scenarios(
    goal_id: int,
    monthly_income: float,
    current_debt_payments: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    goal = GoalService.get_goal_by_id(db, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return GoalService.generate_scenarios(goal, monthly_income, current_debt_payments)

@router.put("/{goal_id}")
def update_goal(
    goal_id: int,
    update: GoalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    goal = GoalService.update_goal(db, goal_id, update)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal
