from typing import List, Dict
from app.models.debt import Debt, DebtStatus, DebtType
from app.schemas.dashboard import (
    DebtBreakdown, DashboardSummary, EmergencyFundRecommendation,
    CashFlowAnalysis, FinancialHealthMetrics
)
from app.services.debt_service import DebtService
from app.services.strategy_service import StrategyService
from datetime import datetime, timedelta
from collections import defaultdict


class DashboardService:
    """Business logic for financial dashboard"""

    @staticmethod
    def get_dashboard_summary(debts: List[Debt], monthly_income: float) -> DashboardSummary:
        """Get complete financial dashboard summary"""

        total_debt = DebtService.get_total_debt(debts)
        total_payments = DebtService.get_total_monthly_payment(debts)
        average_apr = DebtService.get_weighted_apr(debts)

        # Calculate metrics
        debt_to_income = total_debt / monthly_income if monthly_income > 0 else 0
        available_cash = monthly_income - total_payments

        # Financial score
        score = StrategyService.calculate_financial_score(debts, monthly_income)

        # Debt breakdowns
        breakdown_by_type = DashboardService._get_breakdown_by_type(debts)
        breakdown_by_status = DashboardService._get_breakdown_by_status(debts)

        # Debt counts
        all_debts = debts
        active_debts = [d for d in debts if d.status == DebtStatus.ACTIVE]
        paid_off_debts = [d for d in debts if d.status == DebtStatus.PAID_OFF]

        # APR stats
        active_aprs = [d.interest_rate for d in active_debts]
        highest_apr = max(active_aprs) if active_aprs else 0
        lowest_apr = min(active_aprs) if active_aprs else 0

        # Payoff timelines
        months_minimum = int(total_debt / (total_payments + 0.01)) if total_payments > 0 else 999
        months_recommended = 84  # 7 years target

        return DashboardSummary(
            total_debt=round(total_debt, 2),
            total_assets=0,
            net_worth=0,
            monthly_income=monthly_income,
            total_monthly_payments=round(total_payments, 2),
            available_monthly_cash=round(available_cash, 2),
            debt_to_income_ratio=round(debt_to_income, 2),
            urgency_score=score.urgency_score,
            urgency_level=score.urgency_level,
            total_debts_count=len(all_debts),
            active_debts_count=len(active_debts),
            paid_off_debts_count=len(paid_off_debts),
            average_apr=round(average_apr, 2),
            highest_apr=round(highest_apr, 2),
            lowest_apr=round(lowest_apr, 2),
            months_to_debt_free_minimum=months_minimum,
            months_to_debt_free_recommended=months_recommended,
            debt_breakdown_by_type=breakdown_by_type,
            debt_breakdown_by_status=breakdown_by_status
        )

    @staticmethod
    def _get_breakdown_by_type(debts: List[Debt]) -> List[DebtBreakdown]:
        """Get debt breakdown by type"""
        breakdown = defaultdict(lambda: {
            "count": 0,
            "total_balance": 0,
            "total_minimum": 0,
            "total_apr": 0
        })

        for debt in debts:
            debt_type = debt.debt_type.value if hasattr(debt.debt_type, 'value') else str(debt.debt_type)
            breakdown[debt_type]["count"] += 1
            breakdown[debt_type]["total_balance"] += debt.balance
            breakdown[debt_type]["total_minimum"] += debt.minimum_payment or 0
            breakdown[debt_type]["total_apr"] += debt.interest_rate

        result = []
        for debt_type, data in breakdown.items():
            avg_apr = data["total_apr"] / data["count"] if data["count"] > 0 else 0
            result.append(DebtBreakdown(
                debt_type=debt_type,
                count=data["count"],
                total_balance=round(data["total_balance"], 2),
                total_minimum_payment=round(data["total_minimum"], 2),
                average_apr=round(avg_apr, 2)
            ))

        return sorted(result, key=lambda x: x.total_balance, reverse=True)

    @staticmethod
    def _get_breakdown_by_status(debts: List[Debt]) -> List[dict]:
        """Get debt breakdown by status"""
        breakdown = defaultdict(lambda: {
            "count": 0,
            "total_balance": 0
        })

        for debt in debts:
            status = debt.status.value if hasattr(debt.status, 'value') else str(debt.status)
            breakdown[status]["count"] += 1
            breakdown[status]["total_balance"] += debt.balance

        result = []
        for status, data in breakdown.items():
            result.append({
                "status": status,
                "count": data["count"],
                "total_balance": round(data["total_balance"], 2)
            })

        return sorted(result, key=lambda x: x["total_balance"], reverse=True)

    @staticmethod
    def get_emergency_fund_recommendation(monthly_income: float,
                                          monthly_expenses: float) -> EmergencyFundRecommendation:
        """
        Recommend emergency fund size
        Standard recommendation: 3-6 months of expenses
        """
        current_emergency_fund = 0  # For now, user hasn't provided this

        # Calculate recommended amount (using 6 months of expenses as target)
        recommended_months = 6
        recommended_amount = monthly_expenses * recommended_months

        # Determine priority based on current fund
        if current_emergency_fund == 0:
            priority = "Critical"
            reason = "No emergency fund exists. This is your top priority before aggressive debt payoff."
        elif current_emergency_fund < monthly_expenses:
            priority = "Critical"
            reason = "Emergency fund covers less than 1 month of expenses. This should be your priority."
        elif current_emergency_fund < monthly_expenses * 3:
            priority = "High"
            reason = "Emergency fund covers 1-3 months. Build to 3-6 months for better security."
        elif current_emergency_fund < monthly_expenses * 6:
            priority = "Moderate"
            reason = "Emergency fund covers 3-6 months. Good progress, but aim for 6 months."
        else:
            priority = "Low"
            reason = "Emergency fund is well-established. Focus on debt payoff."

        return EmergencyFundRecommendation(
            current_emergency_fund=current_emergency_fund,
            recommended_amount=round(recommended_amount, 2),
            months_of_expenses=recommended_months,
            savings_needed=round(recommended_amount - current_emergency_fund, 2),
            priority=priority,
            reason=reason
        )

    @staticmethod
    def get_cash_flow_analysis(monthly_income: float, total_debt_payments: float) -> CashFlowAnalysis:
        """Analyze monthly cash flow"""

        remaining = monthly_income - total_debt_payments

        # Determine health
        if remaining > monthly_income * 0.25:
            health = "Positive"
            recommendations = [
                "Great cash flow! Consider allocating extra funds to debt payoff.",
                "Build an emergency fund (3-6 months of expenses).",
                "Once debt-free, invest for long-term wealth building."
            ]
        elif remaining > monthly_income * 0.10:
            health = "Tight"
            recommendations = [
                "Cash flow is manageable but tight. Track spending carefully.",
                "Look for ways to reduce expenses.",
                "Consider increasing income through gig work or side hustle."
            ]
        else:
            health = "Negative"
            recommendations = [
                "Cash flow is negative! Urgent action needed.",
                "Explore debt consolidation or refinancing.",
                "Negotiate hardship plans with creditors.",
                "Seek professional credit counseling."
            ]

        return CashFlowAnalysis(
            monthly_income=monthly_income,
            fixed_debt_payments=round(total_debt_payments, 2),
            remaining_after_debt=round(remaining, 2),
            cash_flow_health=health,
            recommendations=recommendations
        )

    @staticmethod
    def get_financial_health_metrics(debts: List[Debt], monthly_income: float) -> FinancialHealthMetrics:
        """Calculate comprehensive financial health metrics"""

        total_debt = DebtService.get_total_debt(debts)
        total_payments = DebtService.get_total_monthly_payment(debts)
        average_apr = DebtService.get_weighted_apr(debts)
        active_debts = [d for d in debts if d.status == DebtStatus.ACTIVE]

        # Calculate ratios
        debt_to_income = total_debt / monthly_income if monthly_income > 0 else 100
        payment_to_income = total_payments / monthly_income if monthly_income > 0 else 100

        # Estimate payoff months
        if total_payments > 0:
            months = int(total_debt / total_payments) if total_debt > 0 else 0
        else:
            months = 999

        # Calculate health score (0-100)
        health_score = 100

        # Deduct for debt metrics
        if debt_to_income > 5:
            health_score -= 30
        elif debt_to_income > 3:
            health_score -= 20
        elif debt_to_income > 1:
            health_score -= 10

        # Deduct for APR
        if average_apr > 20:
            health_score -= 15
        elif average_apr > 15:
            health_score -= 10
        elif average_apr > 10:
            health_score -= 5

        # Deduct for payment burden
        if payment_to_income > 0.5:
            health_score -= 20
        elif payment_to_income > 0.25:
            health_score -= 10

        # Add bonus for multiple debts paid off
        if len(debts) > len(active_debts):
            health_score += 10

        health_score = max(0, min(100, health_score))

        # Convert to letter grade
        if health_score >= 90:
            rating = "A"
        elif health_score >= 80:
            rating = "B"
        elif health_score >= 70:
            rating = "C"
        elif health_score >= 60:
            rating = "D"
        else:
            rating = "F"

        return FinancialHealthMetrics(
            debt_to_income=round(debt_to_income, 2),
            payment_to_income=round(payment_to_income, 2),
            apr_average=round(average_apr, 2),
            debt_count=len(debts),
            payment_months=months,
            urgency_score=DashboardService._calculate_urgency(debt_to_income, average_apr),
            overall_health_score=health_score,
            health_rating=rating
        )

    @staticmethod
    def _calculate_urgency(debt_to_income: float, average_apr: float) -> int:
        """Calculate urgency score (0-100)"""
        score = 0

        if debt_to_income > 10:
            score = 90
        elif debt_to_income > 5:
            score = 75
        elif debt_to_income > 3:
            score = 60
        elif debt_to_income > 1:
            score = 40
        elif debt_to_income > 0.5:
            score = 20
        else:
            score = 10

        # Adjust by APR
        if average_apr > 20:
            score = min(100, score + 20)
        elif average_apr > 15:
            score = min(100, score + 10)

        return score
