from typing import List, Dict, Optional
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from app.models.debt import Goal, Scenario
from app.schemas.goal import (
    GoalCreate, GoalUpdate, GoalResponse, GoalTimeline,
    ScenarioComparison, GoalDashboard
)
from app.services.debt_service import DebtService
from app.services.strategy_service import StrategyService


class GoalService:
    """Business logic for goal planning and scenario modeling"""

    @staticmethod
    def create_goal(db: Session, user_id: int, goal: GoalCreate) -> Goal:
        """Create new financial goal"""

        db_goal = Goal(
            user_id=user_id,
            goal_type=goal.goal_type,
            name=goal.name,
            description=goal.description,
            target_amount=goal.target_amount,
            current_savings=goal.current_savings,
            target_date=goal.target_date,
            priority=goal.priority,
            annual_return_rate=goal.annual_return_rate
        )

        db.add(db_goal)
        db.commit()
        db.refresh(db_goal)
        return db_goal

    @staticmethod
    def get_user_goals(db: Session, user_id: int, status: Optional[str] = "active") -> List[Goal]:
        """Get user's goals"""

        query = db.query(Goal).filter(Goal.user_id == user_id)

        if status:
            query = query.filter(Goal.status == status)

        return query.order_by(Goal.priority).all()

    @staticmethod
    def get_goal_by_id(db: Session, goal_id: int) -> Optional[Goal]:
        """Get goal by ID"""
        return db.query(Goal).filter(Goal.id == goal_id).first()

    @staticmethod
    def update_goal(db: Session, goal_id: int, update_data: GoalUpdate) -> Optional[Goal]:
        """Update goal"""

        goal = GoalService.get_goal_by_id(db, goal_id)

        if not goal:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(goal, key, value)

        db.commit()
        db.refresh(goal)
        return goal

    @staticmethod
    def calculate_goal_timeline(
            db: Session,
            user_id: int,
            goal: Goal,
            monthly_debt_payment: float,
            debts: List = None
    ) -> GoalTimeline:
        """
        Calculate timeline for goal considering debt payoff first

        Logic:
        1. Calculate when debt will be paid off
        2. Calculate when goal can start being funded
        3. Calculate interest earned on savings
        4. Show final goal amount
        """

        if debts is None:
            debts = DebtService.get_active_debts(db, user_id)

        # Get debt payoff timeline
        total_debt = DebtService.get_total_debt(debts)

        if total_debt > 0:
            # Simulate payoff
            result = StrategyService._simulate_payoff_accurate(debts, monthly_debt_payment)
            debt_payoff_months = result.get("total_months", 84)
        else:
            debt_payoff_months = 0

        # Calculate goal timeline
        months_to_goal = 0
        goal_completion_month = 0
        total_amount_invested = 0
        total_interest_earned = 0
        final_goal_amount = goal.current_savings

        # After debt paid off, start funding goal
        remaining_goal = goal.target_amount - goal.current_savings

        if remaining_goal > 0:
            # Calculate monthly allocation available after debt payoff
            # Assume user can allocate 20% of income to goals (placeholder)
            monthly_income = 4000  # Would come from user input
            monthly_goal_allocation = monthly_income * 0.20

            # Calculate months needed (with interest)
            current_amount = goal.current_savings
            monthly_rate = goal.annual_return_rate / 12
            month = 0

            while current_amount < goal.target_amount and month < 360:  # Max 30 years
                month += 1

                # Add interest on current amount
                interest = current_amount * monthly_rate
                current_amount += interest
                total_interest_earned += interest

                # Add monthly allocation (only after debt paid off)
                if month > debt_payoff_months:
                    current_amount += monthly_goal_allocation
                    total_amount_invested += monthly_goal_allocation

            goal_completion_month = debt_payoff_months + month
            final_goal_amount = current_amount
        else:
            goal_completion_month = 0
            final_goal_amount = goal.current_savings

        # Convert months to dates
        today = date.today()
        debt_payoff_date = today + timedelta(days=debt_payoff_months * 30)
        goal_start_date = debt_payoff_date
        goal_completion_date = today + timedelta(days=goal_completion_month * 30)

        return GoalTimeline(
            goal=GoalResponse.from_orm(goal),
            debt_payoff_month=debt_payoff_months,
            debt_payoff_date=debt_payoff_date,
            goal_start_month=debt_payoff_months,
            goal_start_date=goal_start_date,
            goal_completion_month=goal_completion_month,
            goal_completion_date=goal_completion_date,
            monthly_allocation=monthly_income * 0.20,
            total_months=goal_completion_month,
            total_years=round(goal_completion_month / 12, 1),
            total_amount_invested=round(total_amount_invested, 2),
            estimated_interest_earned=round(total_interest_earned, 2),
            final_goal_amount=round(final_goal_amount, 2)
        )

    @staticmethod
    def generate_scenarios(
            db: Session,
            user_id: int,
            goal: Goal,
            monthly_income: float,
            debts: List = None
    ) -> List[Scenario]:
        """
        Generate what-if scenarios for goal achievement

        Scenarios:
        1. Conservative: Minimum payment on debt, then goal
        2. Moderate: Moderate debt payment, split allocation
        3. Aggressive: Maximum debt payment, then heavy goal funding
        """

        if debts is None:
            debts = DebtService.get_active_debts(db, user_id)

        total_debt = DebtService.get_total_debt(debts)

        scenarios = []

        # Conservative scenario
        conservative_debt_payment = monthly_income * 0.15
        scenarios.append(GoalService._calculate_scenario(
            db, user_id, goal, conservative_debt_payment, monthly_income, debts,
            name="Conservative",
            goal_allocation=monthly_income * 0.10
        ))

        # Moderate scenario
        moderate_debt_payment = monthly_income * 0.30
        scenarios.append(GoalService._calculate_scenario(
            db, user_id, goal, moderate_debt_payment, monthly_income, debts,
            name="Moderate",
            goal_allocation=monthly_income * 0.15
        ))

        # Aggressive scenario
        aggressive_debt_payment = monthly_income * 0.50
        scenarios.append(GoalService._calculate_scenario(
            db, user_id, goal, aggressive_debt_payment, monthly_income, debts,
            name="Aggressive",
            goal_allocation=monthly_income * 0.20
        ))

        return scenarios

    @staticmethod
    def _calculate_scenario(
            db: Session,
            user_id: int,
            goal: Goal,
            monthly_debt_payment: float,
            monthly_income: float,
            debts: List,
            name: str,
            goal_allocation: float
    ) -> dict:
        """Calculate single scenario with debt interest, net benefit, and recommendations"""

        # Simulate debt payoff
        result = StrategyService._simulate_payoff_accurate(debts, monthly_debt_payment)
        debt_payoff_months = result.get("total_months", 84)
        total_interest_paid_on_debt = result.get("total_interest", 0)

        # Calculate goal achievement
        remaining_goal = goal.target_amount - goal.current_savings
        current_amount = goal.current_savings
        monthly_rate = goal.annual_return_rate / 12
        month = 0
        total_invested = 0
        total_interest_earned = 0

        while current_amount < goal.target_amount and month < 360:
            month += 1

            # Interest on current amount
            interest = current_amount * monthly_rate
            current_amount += interest
            total_interest_earned += interest

            # Goal allocation (only after debt paid)
            if month > debt_payoff_months:
                current_amount += goal_allocation
                total_invested += goal_allocation

        goal_completion_month = debt_payoff_months + month

        # Calculate net financial benefit
        # Positive = you gain money, Negative = you lose money
        net_financial_benefit = total_interest_earned - total_interest_paid_on_debt

        # Determine credit impact level (qualitative, not quantitative)
        if debt_payoff_months == 0:
            credit_impact_level = "None"
            credit_impact_explanation = "Debt remains unpaid. No credit improvement expected."
            credit_score_disclaimer = "⚠️ Unpaid debt negatively impacts credit scores. Monitor your credit at annualcreditreport.com."
        elif debt_payoff_months <= 12:
            credit_impact_level = "Very High"
            credit_impact_explanation = "Quick debt payoff (within 12 months) combined with on-time payments are factors credit bureaus consider when calculating credit scores."
            credit_score_disclaimer = "⚠️ Actual credit score changes vary by individual. Results depend on your complete credit profile. Verify at annualcreditreport.com."
        elif debt_payoff_months <= 30:
            credit_impact_level = "High"
            credit_impact_explanation = "Debt payoff and consistent on-time payments are positive factors that credit bureaus consider. Actual impact varies by individual circumstances."
            credit_score_disclaimer = "⚠️ Actual credit score changes vary by individual. Results depend on your complete credit profile. Verify at annualcreditreport.com."
        else:
            credit_impact_level = "Moderate"
            credit_impact_explanation = "Extended payoff timeline with on-time payments provides steady positive factors for credit scores. Actual impact varies by individual."
            credit_score_disclaimer = "⚠️ Actual credit score changes vary by individual. Results depend on your complete credit profile. Verify at annualcreditreport.com."

        # Generate recommendation and rating based on payoff speed
        if debt_payoff_months == 0 or debt_payoff_months > 60:
            recommendation = "Slowest path. Debt lingers for years, costs the most. Not recommended."
            rating = "😕"
            priority = 3
        elif debt_payoff_months > 30:
            recommendation = "Balanced approach. Good for most people. Moderate speed and cost."
            rating = "😊"
            priority = 2
        else:
            recommendation = f"Fastest path! Debt-free in {debt_payoff_months} months. Credit boost + financial freedom. Recommended! 🎉"
            rating = "🚀"
            priority = 1

        return {
            "name": name,
            "priority": priority,
            "monthly_debt_payment": round(monthly_debt_payment, 2),
            "debt_payoff_months": debt_payoff_months,
            "monthly_goal_allocation": round(goal_allocation, 2),
            "annual_return_rate": goal.annual_return_rate,
            "total_months_to_goal": goal_completion_month,
            "total_months_to_goal_years": round(goal_completion_month / 12, 1),
            "total_invested": round(total_invested, 2),
            "total_interest_earned_on_savings": round(total_interest_earned, 2),
            "estimated_debt_interest_cost": round(total_interest_paid_on_debt, 2),
            "net_financial_benefit": round(net_financial_benefit, 2),
            "final_goal_amount": round(current_amount, 2),
            "credit_impact_level": credit_impact_level,
            "credit_impact_explanation": credit_impact_explanation,
            "credit_score_disclaimer": credit_score_disclaimer,
            "recommendation": recommendation,
            "rating": rating
        }

    @staticmethod
    def get_goal_dashboard(
            db: Session,
            user_id: int,
            monthly_income: float
    ) -> GoalDashboard:
        """Get complete goal dashboard"""

        goals = GoalService.get_user_goals(db, user_id)
        debts = DebtService.get_active_debts(db, user_id)

        timelines = []
        total_monthly = 0
        total_target = 0
        total_savings = 0

        for goal in goals:
            timeline = GoalService.calculate_goal_timeline(
                db, user_id, goal, monthly_income * 0.25, debts
            )
            timelines.append(timeline)
            total_monthly += timeline.monthly_allocation
            total_target += goal.target_amount
            total_savings += goal.current_savings

        # Calculate when ALL goals are achievable
        max_completion_months = max(
            [t.goal_completion_month for t in timelines],
            default=0
        )
        overall_timeline = {
            "all_goals_complete_months": max_completion_months,
            "all_goals_complete_years": round(max_completion_months / 12, 1),
            "all_goals_complete_date": (
                    date.today() + timedelta(days=max_completion_months * 30)
            ).isoformat()
        }

        return GoalDashboard(
            goals=[GoalResponse.from_orm(g) for g in goals],
            timeline=timelines,
            overall_timeline=overall_timeline,
            total_monthly_allocation=round(total_monthly, 2),
            total_target_amount=round(total_target, 2),
            total_current_savings=round(total_savings, 2)
        )
