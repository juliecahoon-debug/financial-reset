from typing import List, Dict, Optional
from app.models.debt import Debt, DebtStatus
from app.schemas.strategy import (
    StrategyType, DebtPayoffProjection, StrategyProjection,
    StrategyComparison, FinancialScore, StrategyRecommendation
)
from app.services.debt_service import DebtService


class StrategyService:
    """Business logic for debt optimization strategies"""

    @staticmethod
    def _simulate_payoff_accurate(
            debts: List[Debt],
            monthly_payment: float,
            strategy: StrategyType = StrategyType.AVALANCHE
    ) -> Dict:
        """
        ACCURATE payoff simulation using proper debt prioritization

        Algorithm:
        1. Each month: Calculate interest on ALL debts
        2. Pay minimum on ALL debts
        3. Put remaining toward focus debt (based on strategy)
        4. When focus debt paid off, move to next
        5. Continue until all debts paid or max months reached

        Max timeline: 7 years (84 months) - realistic for personal debt

        Returns: {
            "total_months": int,
            "total_interest": float,
            "debt_details": List[Dict],
            "error": Optional[str],
            "insufficient_payment": bool
        }
        """

        if not debts or monthly_payment <= 0:
            return {
                "total_months": 0,
                "total_interest": 0,
                "debt_details": [],
                "error": "No debts or invalid payment",
                "insufficient_payment": False
            }

        # Initialize tracking
        debt_state = {}
        for debt in debts:
            debt_state[debt.id] = {
                "balance": debt.balance,
                "original_balance": debt.balance,
                "apr": debt.interest_rate,
                "minimum": debt.minimum_payment or 50,  # Default minimum if not set
                "total_interest": 0.0,
                "months_paid": 0,
                "paid_off_month": None
            }

        # Determine order based on strategy
        if strategy == StrategyType.AVALANCHE:
            # Sort by APR (highest first)
            debt_order = sorted(debts, key=lambda d: d.interest_rate, reverse=True)
        else:  # SNOWBALL
            # Sort by balance (lowest first)
            debt_order = sorted(debts, key=lambda d: d.balance)

        debt_ids_ordered = [d.id for d in debt_order]
        current_focus_index = 0
        month = 0
        max_months = 84  # 7 years - realistic maximum for personal debt payoff

        # Simulation loop
        while month < max_months:
            month += 1

            # Step 1: Calculate and apply interest to all active debts
            total_interest_this_month = 0
            for debt_id in debt_ids_ordered:
                if debt_state[debt_id]["balance"] > 0:
                    # Calculate monthly interest rate
                    monthly_rate = debt_state[debt_id]["apr"] / 100 / 12
                    interest = debt_state[debt_id]["balance"] * monthly_rate

                    # Apply interest
                    debt_state[debt_id]["balance"] += interest
                    debt_state[debt_id]["total_interest"] += interest
                    total_interest_this_month += interest

            # Step 2: Calculate total minimum payments needed
            total_minimum = 0
            for debt_id in debt_ids_ordered:
                if debt_state[debt_id]["balance"] > 0:
                    total_minimum += min(debt_state[debt_id]["balance"], debt_state[debt_id]["minimum"])

            # Check if payment is sufficient for minimums
            if monthly_payment < total_minimum:
                return {
                    "total_months": 0,
                    "total_interest": 0,
                    "debt_details": [],
                    "error": f"Monthly payment of ${monthly_payment:.2f} is less than minimum required ${total_minimum:.2f}",
                    "insufficient_payment": True
                }

            # Step 3: Pay minimum on all debts
            for debt_id in debt_ids_ordered:
                if debt_state[debt_id]["balance"] > 0:
                    minimum_payment = min(debt_state[debt_id]["balance"], debt_state[debt_id]["minimum"])
                    debt_state[debt_id]["balance"] -= minimum_payment

            # Step 4: Apply extra payment to focus debt
            remaining_payment = monthly_payment - total_minimum

            # Find next unpaid focus debt
            while current_focus_index < len(debt_ids_ordered):
                focus_debt_id = debt_ids_ordered[current_focus_index]
                if debt_state[focus_debt_id]["balance"] > 0:
                    break
                current_focus_index += 1

            # Pay remaining toward focus debt
            if current_focus_index < len(debt_ids_ordered):
                focus_debt_id = debt_ids_ordered[current_focus_index]
                extra_payment = min(debt_state[focus_debt_id]["balance"], remaining_payment)
                debt_state[focus_debt_id]["balance"] -= extra_payment

            # Step 5: Track when each debt is paid off
            for debt_id in debt_ids_ordered:
                if debt_state[debt_id]["balance"] <= 0.01 and debt_state[debt_id]["paid_off_month"] is None:
                    debt_state[debt_id]["balance"] = 0
                    debt_state[debt_id]["paid_off_month"] = month

            # Step 6: Check if all debts paid off
            all_paid = all(debt_state[d_id]["balance"] <= 0 for d_id in debt_ids_ordered)
            if all_paid:
                break

        # Check if hit max months without paying off all debt
        insufficient_payment = any(debt_state[d_id]["balance"] > 0 for d_id in debt_ids_ordered)

        # Build results
        debt_details = []
        for idx, debt in enumerate(debt_order):
            debt_details.append({
                "debt_id": debt.id,
                "debt_name": debt.name,
                "payoff_order": idx + 1,
                "months_to_payoff": debt_state[debt.id]["paid_off_month"] or max_months,
                "total_interest_paid": round(debt_state[debt.id]["total_interest"], 2),
                "original_balance": debt_state[debt.id]["original_balance"]
            })

        # Calculate totals
        total_interest = sum(debt_state[d_id]["total_interest"] for d_id in debt_ids_ordered)
        total_months = max((debt_state[d_id]["paid_off_month"] or max_months) for d_id in debt_ids_ordered)

        return {
            "total_months": total_months,
            "total_interest": round(total_interest, 2),
            "debt_details": debt_details,
            "error": None,
            "insufficient_payment": insufficient_payment
        }

    @staticmethod
    def get_avalanche_strategy(debts: List[Debt], monthly_payment: float) -> StrategyProjection:
        """
        Avalanche strategy: Pay highest APR first (minimize interest)
        Most mathematically optimal
        """
        if not debts:
            return StrategyProjection(
                strategy_type=StrategyType.AVALANCHE,
                total_months=0,
                total_years=0,
                total_interest_paid=0,
                total_amount_paid=0,
                monthly_payment_needed=0,
                debt_payoff_order=[]
            )

        result = StrategyService._simulate_payoff_accurate(debts, monthly_payment, StrategyType.AVALANCHE)

        if result["error"]:
            return StrategyProjection(
                strategy_type=StrategyType.AVALANCHE,
                total_months=0,
                total_years=0,
                total_interest_paid=0,
                total_amount_paid=0,
                monthly_payment_needed=0,
                debt_payoff_order=[],
            )

        total_debt = sum(d.balance for d in debts)
        total_months = result["total_months"]
        total_interest = result["total_interest"]
        total_amount_paid = total_debt + total_interest

        payoff_order = [
            DebtPayoffProjection(
                debt_id=detail["debt_id"],
                debt_name=detail["debt_name"],
                months_to_payoff=detail["months_to_payoff"],
                total_interest_paid=detail["total_interest_paid"],
                payoff_order=detail["payoff_order"]
            )
            for detail in result["debt_details"]
        ]

        return StrategyProjection(
            strategy_type=StrategyType.AVALANCHE,
            total_months=total_months,
            total_years=round(total_months / 12, 1),
            total_interest_paid=total_interest,
            total_amount_paid=round(total_amount_paid, 2),
            monthly_payment_needed=monthly_payment,
            debt_payoff_order=payoff_order
        )

    @staticmethod
    def get_snowball_strategy(debts: List[Debt], monthly_payment: float) -> StrategyProjection:
        """
        Snowball strategy: Pay lowest balance first (quick wins, psychological boost)
        Pays more interest but motivational
        """
        if not debts:
            return StrategyProjection(
                strategy_type=StrategyType.SNOWBALL,
                total_months=0,
                total_years=0,
                total_interest_paid=0,
                total_amount_paid=0,
                monthly_payment_needed=0,
                debt_payoff_order=[]
            )

        result = StrategyService._simulate_payoff_accurate(debts, monthly_payment, StrategyType.SNOWBALL)

        if result["error"]:
            return StrategyProjection(
                strategy_type=StrategyType.SNOWBALL,
                total_months=0,
                total_years=0,
                total_interest_paid=0,
                total_amount_paid=0,
                monthly_payment_needed=0,
                debt_payoff_order=[],
            )

        total_debt = sum(d.balance for d in debts)
        total_months = result["total_months"]
        total_interest = result["total_interest"]
        total_amount_paid = total_debt + total_interest

        payoff_order = [
            DebtPayoffProjection(
                debt_id=detail["debt_id"],
                debt_name=detail["debt_name"],
                months_to_payoff=detail["months_to_payoff"],
                total_interest_paid=detail["total_interest_paid"],
                payoff_order=detail["payoff_order"]
            )
            for detail in result["debt_details"]
        ]

        return StrategyProjection(
            strategy_type=StrategyType.SNOWBALL,
            total_months=total_months,
            total_years=round(total_months / 12, 1),
            total_interest_paid=total_interest,
            total_amount_paid=round(total_amount_paid, 2),
            monthly_payment_needed=monthly_payment,
            debt_payoff_order=payoff_order
        )

    @staticmethod
    def compare_strategies(debts: List[Debt], monthly_payment: float) -> StrategyComparison:
        """Compare Avalanche vs Snowball strategies"""
        avalanche = StrategyService.get_avalanche_strategy(debts, monthly_payment)
        snowball = StrategyService.get_snowball_strategy(debts, monthly_payment)

        # Determine which is better (Avalanche usually saves more interest)
        recommended = (
            StrategyType.AVALANCHE
            if avalanche.total_interest_paid <= snowball.total_interest_paid
            else StrategyType.SNOWBALL
        )

        savings = {
            "interest_saved": round(
                abs(snowball.total_interest_paid - avalanche.total_interest_paid), 2
            ),
            "months_saved": abs(snowball.total_months - avalanche.total_months),
            "better_strategy": recommended
        }

        return StrategyComparison(
            avalanche=avalanche,
            snowball=snowball,
            recommended=recommended,
            savings=savings
        )

    @staticmethod
    def get_insufficient_payment_recommendations(
            debts: List[Debt],
            monthly_payment: float,
            monthly_income: float
    ) -> dict:
        """
        When payment is too low, suggest alternatives
        """
        total_debt = DebtService.get_total_debt(debts)
        total_minimums = DebtService.get_total_monthly_payment(debts)
        weighted_apr = DebtService.get_weighted_apr(debts)

        # Calculate what payment would be needed for 7 years (84 months)
        # This is approximate - would need to simulate to be exact
        min_for_7_years = (total_debt / 84) + (total_debt * weighted_apr / 100 / 2)

        recommendations = {
            "status": "insufficient_payment",
            "message": "Your monthly payment is too low to pay off debt in 7 years",
            "current_payment": monthly_payment,
            "total_debt": round(total_debt, 2),
            "total_minimum_payments": round(total_minimums, 2),
            "minimum_needed_7_years": round(min_for_7_years, 2),
            "shortfall_monthly": round(min_for_7_years - monthly_payment, 2),
            "suggested_actions": [
                {
                    "type": "balance_transfer",
                    "title": "Balance Transfer to 0% Card",
                    "description": "Move high-APR credit cards to 0% promotional rate (6-18 months)",
                    "best_for": "Credit cards @ 18%+ APR",
                    "potential_savings": "Up to 50% interest saved during promo",
                    "credit_score_needed": 700,
                    "status": "available_soon",
                    "impact": "High"
                },
                {
                    "type": "consolidation",
                    "title": "Debt Consolidation Loan",
                    "description": "Combine multiple debts into 1 loan with lower APR",
                    "best_for": "Mixed debt (cards + personal loans)",
                    "potential_savings": f"${round((weighted_apr - 8) * total_debt / 100 / 12, 0)}/month in interest",
                    "credit_score_needed": 650,
                    "status": "available_soon",
                    "impact": "High"
                },
                {
                    "type": "hardship_plan",
                    "title": "Hardship Program Negotiation",
                    "description": "Call creditors to negotiate lower interest or payment",
                    "best_for": "Any debt, works with bad credit",
                    "potential_savings": "2-5% APR reduction",
                    "credit_score_needed": "None",
                    "status": "available_now",
                    "impact": "Medium"
                },
                {
                    "type": "increase_income",
                    "title": "Increase Income (Gig Work)",
                    "description": "DoorDash, TaskRabbit, Instacart to boost monthly payment",
                    "best_for": "Quick income boost",
                    "potential_additional_income": "Varies by location ($500-2,000/month possible)",
                    "credit_score_needed": "None",
                    "status": "available_now",
                    "impact": "Medium"
                },
                {
                    "type": "increase_payment",
                    "title": "Increase Monthly Payment",
                    "description": "Allocate more money toward debt payoff",
                    "best_for": "If you can afford it",
                    "impact_on_timeline": f"${round(min_for_7_years - monthly_payment, 2)}/month extra = 7 years payoff",
                    "credit_score_needed": "None",
                    "status": "available_now",
                    "impact": "Highest"
                }
            ]
        }

        return recommendations

    @staticmethod
    def calculate_financial_score(debts: List[Debt], monthly_income: float) -> FinancialScore:
        """Calculate user's financial health score (0-100)"""

        total_debt = DebtService.get_total_debt(debts)
        average_apr = DebtService.get_weighted_apr(debts)

        # Debt-to-income ratio
        if monthly_income <= 0:
            debt_to_income = 999
        else:
            debt_to_income = total_debt / monthly_income

        # Urgency score (0-100)
        # Factors: debt-to-income ratio, average APR
        urgency_score = 0

        if debt_to_income > 10:
            urgency_score = 90
        elif debt_to_income > 5:
            urgency_score = 75
        elif debt_to_income > 3:
            urgency_score = 60
        elif debt_to_income > 1:
            urgency_score = 40
        elif debt_to_income > 0.5:
            urgency_score = 20
        else:
            urgency_score = 10

        # Adjust by APR (high APR = more urgent)
        if average_apr > 20:
            urgency_score = min(100, urgency_score + 20)
        elif average_apr > 15:
            urgency_score = min(100, urgency_score + 10)

        # Determine urgency level
        if urgency_score >= 80:
            urgency_level = "Critical"
        elif urgency_score >= 60:
            urgency_level = "High"
        elif urgency_score >= 40:
            urgency_level = "Moderate"
        elif urgency_score >= 20:
            urgency_level = "Low"
        else:
            urgency_level = "Healthy"

        # Calculate payment capacity
        monthly_payment_capacity = monthly_income * 0.25  # Can dedicate ~25% to debt
        minimum_total = DebtService.get_total_monthly_payment(debts)

        # Months to debt free with minimum payments
        if monthly_income > 0:
            months_minimum = int(total_debt / (monthly_income * 0.1)) if monthly_income > 0 else 999
        else:
            months_minimum = 999

        return FinancialScore(
            debt_to_income_ratio=round(debt_to_income, 2),
            urgency_score=urgency_score,
            urgency_level=urgency_level,
            total_debt=round(total_debt, 2),
            total_monthly_income=monthly_income,
            average_interest_rate=round(average_apr, 2),
            monthly_payment_capacity=round(monthly_payment_capacity, 2),
            months_to_debt_free_minimum=months_minimum,
            recommended_monthly_payment=round(max(monthly_payment_capacity, minimum_total), 2)
        )

    @staticmethod
    def get_recommendation(
            debts: List[Debt],
            monthly_income: float,
            available_monthly_payment: float
    ) -> StrategyRecommendation:
        """Get personalized strategy recommendation"""

        if not debts or monthly_income <= 0:
            return StrategyRecommendation(
                recommended_strategy=StrategyType.AVALANCHE,
                reason="Insufficient data",
                monthly_payment_suggested=0,
                timeline_months=0,
                total_interest_with_strategy=0,
                urgency_assessment="Unable to assess"
            )

        # Calculate financial score
        score = StrategyService.calculate_financial_score(debts, monthly_income)

        # Compare strategies
        comparison = StrategyService.compare_strategies(debts, available_monthly_payment)

        # Determine recommendation
        if score.urgency_score >= 80:
            # Critical: recommend maximum payment with Avalanche
            recommended = StrategyType.AVALANCHE
            reason = "Critical financial urgency: Focus on paying interest efficiently with Avalanche strategy"
            strategy_proj = comparison.avalanche
        elif score.urgency_score >= 60:
            # High urgency: use recommended strategy
            recommended = comparison.recommended
            reason = "High debt burden: Recommend the strategy that saves most interest"
            strategy_proj = comparison.avalanche if recommended == StrategyType.AVALANCHE else comparison.snowball
        else:
            # Low urgency: can use either, suggest Snowball for motivation
            recommended = StrategyType.SNOWBALL
            reason = "Manageable debt level: Choose Snowball for quick wins and motivation"
            strategy_proj = comparison.snowball

        return StrategyRecommendation(
            recommended_strategy=recommended,
            reason=reason,
            monthly_payment_suggested=available_monthly_payment,
            timeline_months=strategy_proj.total_months,
            total_interest_with_strategy=strategy_proj.total_interest_paid,
            urgency_assessment=f"Urgency Level: {score.urgency_level} ({score.urgency_score}/100)"
        )