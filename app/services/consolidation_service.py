from typing import List, Dict
from sqlalchemy.orm import Session
from app.models.debt import ConsolidationLoan
from app.services.debt_service import DebtService
from app.services.strategy_service import StrategyService


class ConsolidationService:
    """Business logic for debt consolidation strategy"""

    @staticmethod
    def calculate_consolidation_payoff(
            debts: List,
            consolidation_apr: float,
            loan_term_months: int,
            origination_fee: float = 0.02
    ) -> Dict:
        """
        Calculate debt consolidation strategy

        Logic:
        1. Combine all debts into one loan
        2. Pay fixed monthly payment
        3. Calculate total interest
        4. Compare to current strategy
        """

        # Total debt to consolidate
        total_debt = sum(d.balance for d in debts)

        # Calculate origination fee
        orig_fee = total_debt * origination_fee
        total_loan_amount = total_debt + orig_fee

        # Calculate monthly payment (fixed rate loan)
        # Formula: M = P * [r(1+r)^n] / [(1+r)^n - 1]
        # where P = principal, r = monthly rate, n = months

        monthly_rate = consolidation_apr / 12

        if monthly_rate == 0:
            # 0% APR (hypothetical)
            monthly_payment = total_loan_amount / loan_term_months
            total_interest = 0
        else:
            # Standard loan formula
            numerator = monthly_rate * (1 + monthly_rate) ** loan_term_months
            denominator = (1 + monthly_rate) ** loan_term_months - 1
            monthly_payment = total_loan_amount * (numerator / denominator)

            # Calculate total interest
            total_paid = monthly_payment * loan_term_months
            total_interest = total_paid - total_loan_amount

        return {
            "strategy": "Debt Consolidation",
            "total_debt": round(total_debt, 2),
            "origination_fee": round(orig_fee, 2),
            "total_loan_amount": round(total_loan_amount, 2),
            "consolidation_apr": consolidation_apr,
            "loan_term_months": loan_term_months,
            "loan_term_years": round(loan_term_months / 12, 1),
            "monthly_payment": round(monthly_payment, 2),
            "total_paid": round(total_loan_amount + total_interest, 2),
            "total_interest": round(total_interest, 2),
            "credit_impact": "Initial: -10 to -15 points (hard inquiry, new account), Then: +100-150 (longer timeline, single payment)",
            "pros": [
                f"Single monthly payment (${monthly_payment:.2f})",
                f"Fixed rate of {consolidation_apr * 100}% - no surprises",
                "Simpler to manage (one debt instead of many)",
                "May lower overall interest if APR is good"
            ],
            "cons": [
                f"{origination_fee * 100}% origination fee (${orig_fee:.2f})",
                f"Need credit score typically 620+ to qualify",
                f"Takes {loan_term_months} months to pay off",
                "Hard inquiry temporarily hurts credit"
            ]
        }

    @staticmethod
    def compare_loan_terms(
            debts: List,
            consolidation_apr: float,
            monthly_payment_current: float
    ) -> List[Dict]:
        """Compare different loan term options (36, 60, 84 months)"""

        terms = [36, 60, 84]
        comparisons = []

        for term in terms:
            result = ConsolidationService.calculate_consolidation_payoff(
                debts,
                consolidation_apr,
                term
            )
            comparisons.append(result)

        return comparisons

    @staticmethod
    def compare_with_current_strategy(
            debts: List,
            current_monthly_payment: float,
            consolidation_apr: float,
            loan_term_months: int = 60
    ) -> Dict:
        """Compare consolidation with current Avalanche strategy"""

        # Current strategy
        current = StrategyService._simulate_payoff_accurate(
            debts,
            current_monthly_payment
        )

        # Consolidation strategy
        consolidation = ConsolidationService.calculate_consolidation_payoff(
            debts,
            consolidation_apr,
            loan_term_months
        )

        # Compare
        interest_saved = current.get("total_interest", 0) - consolidation["total_interest"]
        months_saved = current.get("total_months", 0) - consolidation["loan_term_months"]

        # Recommendation
        if interest_saved > 1000:
            recommendation = f"Consolidation saves ${interest_saved:.2f}! Strong candidate."
        elif interest_saved > 500:
            recommendation = f"Consolidation saves ${interest_saved:.2f}. Worth considering."
        elif interest_saved > 0:
            recommendation = f"Small savings (${interest_saved:.2f}). Marginal benefit."
        else:
            recommendation = f"Consolidation costs ${abs(interest_saved):.2f} more. Don't do it."

        return {
            "current_strategy": current,
            "consolidation_strategy": consolidation,
            "interest_saved": round(interest_saved, 2),
            "months_impact": months_saved,
            "recommendation": recommendation,
            "should_consolidate": interest_saved > 500
        }
