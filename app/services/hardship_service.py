from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models.debt import Debt, HardshipPlan
from app.models.user import User

# TODO: Phase 2 - Credit Card Hardship Program Database
# Many credit card issuers offer hardship programs (payment reduction, deferment, etc)
# Currently recommending generic settlement, but should:
# - Build creditor database (Chase, Amex, Discover, etc)
# - Store hardship program details (types, eligibility, approval rates)
# - Match users to creditor-specific programs based on:
#   * Which bank issued their card
#   * Their risk profile (days late, payment history)
#   * Available programs for their situation
# This will allow SMARTER recommendations than generic settlement advice


class HardshipService:
    """Business logic for hardship relief plans"""

    @staticmethod
    def get_hardship_options(debt: Debt) -> List[Dict]:
        """Get available hardship options for a specific debt"""

        options = []

        # Get debt type as string (handle both Enum and string)
        if hasattr(debt.debt_type, 'value'):
            debt_type = debt.debt_type.value.upper()
        else:
            debt_type = str(debt.debt_type).upper()

        # CONVERT PERCENTAGE TO DECIMAL (12.0% → 0.12)
        interest_rate = debt.interest_rate / 100 if debt.interest_rate > 1 else debt.interest_rate

        # CREDIT CARDS: Only settlement
        if "CREDIT_CARD" in debt_type or "CREDITCARD" in debt_type:
            options.append({
                "plan_type": "settlement",
                "name": "Debt Settlement Negotiation",
                "description": "Negotiate to pay a lump sum (typically 40-60% of balance) to clear debt. WARNING: Severe credit and tax consequences. Only consider after contacting creditor about hardship programs FIRST.",
                "settlement_percentage": 0.50,
                "settlement_amount": debt.balance * 0.50,
                "pros": [
                    f"Pay only ${debt.balance * 0.50:.2f} instead of ${debt.balance:.2f}",
                    f"Save ${debt.balance * 0.50:.2f}",
                    "Get out of debt faster (one lump payment)",
                    "Stop interest accrual immediately"
                ],
                "cons": [
                    "Requires lump sum payment (need cash reserves)",
                    "SEVERE credit damage (-100 to -150 points immediately)",
                    "Settled debt stays on credit report for 7 YEARS",
                    "May owe taxes on forgiven amount (e.g., $1,000 forgiven = ~$220 tax bill)",
                    "Creditor may refuse to settle",
                    "Damages payment history, makes future borrowing expensive",
                    "Only resort after all other options exhausted"
                ],

                "credit_impact": "❌ SEVERE negative impact (-100 to -150 points). Takes 3-5 years to recover.",
                "timeline": "Immediate settlement if approved, removed from credit after 7 years",
                "estimated_interest_cost": 0,
                "estimated_total_cost": debt.balance * 0.50,
                "availability": "Credit cards only"
            })

            return options

        # STUDENT LOANS: Deferment, forbearance, income-driven repayment
        if "STUDENT_LOAN" in debt_type or "STUDENTLOAN" in debt_type:
            # Deferment
            options.append({
                "plan_type": "deferment",
                "name": "Student Loan Deferment",
                "description": "Pause payments while you finish school or handle hardship (no interest accrual on subsidized loans)",
                "duration_months": 12,
                "new_monthly_payment": 0,
                "pros": [
                    "No payments for up to 3 years",
                    "No interest accrual on subsidized loans",
                    "Available for students, residency, economic hardship",
                    "Can be approved multiple times"
                ],
                "cons": [
                    "Interest accrues on unsubsidized loans",
                    "Small credit impact (-20 to -30 points)",
                    "Delayed repayment means longer debt payoff",
                    "Must reapply for each deferment period"
                ],
                "credit_impact": "⚠️ Minor impact (-20 to -30 points). Recovers quickly after payments resume.",
                "timeline": "Up to 3 years deferment, then resume standard payments",
                "estimated_interest_cost": 0,  # Subsidized loans
                "estimated_total_cost": 0,
                "availability": "Federal student loans only"
            })

            # Forbearance
            options.append({
                "plan_type": "forbearance",
                "name": "Income-Driven Repayment Plan",
                "description": "Pay based on your income (10-20% of discretionary income)",
                "duration_months": 12,
                "new_monthly_payment": max(debt.minimum_payment * 0.50, 10),
                "original_monthly_payment": debt.minimum_payment,
                "pros": [
                    "Payments based on income (often 10-20% of discretionary)",
                    "Low monthly payments during hardship",
                    "Forgiveness after 20-25 years",
                    "No credit damage"
                ],
                "cons": [
                    "Interest continues to accrue",
                    "Longer repayment timeline (20-25 years)",
                    "May owe taxes on forgiven amount",
                    "Annual recertification required"
                ],
                "credit_impact": "✓ No negative impact. Good for credit building.",
                "timeline": "20-25 years until forgiveness",
                "estimated_interest_cost": round(debt.balance * interest_rate * 2, 2),  # Rough estimate
                "estimated_total_cost": round(debt.balance * interest_rate * 2, 2),
                "availability": "Federal student loans only"
            })

            return options

        # PERSONAL LOANS: Settlement, forbearance
        if "PERSONAL_LOAN" in debt_type or "PERSONALLOAN" in debt_type:
            # Forbearance
            reduced_payment = max(debt.minimum_payment * 0.50, 50)
            forbearance_months = 6

            balance = debt.balance
            interest_cost = 0
            for month in range(forbearance_months):
                monthly_interest = balance * (interest_rate / 12)
                interest_cost += monthly_interest
                balance += monthly_interest
                balance -= reduced_payment

                # Stop if paid off
                if balance <= 0:
                    balance = 0
                    break

            options.append({
                "plan_type": "forbearance",
                "name": "Reduced Payment Plan (Hardship)",
                "description": "Work with lender to reduce payments temporarily",
                "duration_months": forbearance_months,
                "new_monthly_payment": round(reduced_payment, 2),
                "original_monthly_payment": debt.minimum_payment,
                "pros": [
                    f"Reduce payments by 50% (${debt.minimum_payment:.2f} → ${reduced_payment:.2f})",
                    "Temporary relief during hardship",
                    "Usually no credit damage if approved",
                    "Can extend if needed"
                ],
                "cons": [
                    f"Interest continues to accrue (~${interest_cost:.2f})",
                    "Longer payoff timeline",
                    "Lender approval required",
                    "May report as deferred account"
                ],
                "credit_impact": "⚠️ Minimal impact (-10 to -20 points) if approved.",
                "timeline": f"{forbearance_months} months at reduced rate, then standard payments resume",
                "estimated_interest_cost": round(interest_cost, 2),
                "estimated_total_cost": round(interest_cost, 2),
                "availability": "Depends on lender - contact for approval"
            })

            # Settlement
            options.append({
                "plan_type": "settlement",
                "name": "Debt Settlement",
                "description": "Negotiate lump sum payment to clear debt",
                "settlement_percentage": 0.65,
                "settlement_amount": debt.balance * 0.65,
                "pros": [
                    f"Pay only ${debt.balance * 0.65:.2f} instead of ${debt.balance:.2f}",
                    f"Save ${debt.balance * 0.35:.2f}",
                    "Faster debt payoff",
                    "Single payment closes account"
                ],
                "cons": [
                    "Requires lump sum (must have cash)",
                    "Moderate credit damage (-60 to -100 points)",
                    "Settled debt on credit for 7 years",
                    "May be taxable income"
                ],
                "credit_impact": "⚠️ Moderate-High impact (-60 to -100 points). Takes 2-3 years to recover.",
                "timeline": "Immediate settlement, 7 years on credit report",
                "estimated_interest_cost": 0,
                "estimated_total_cost": debt.balance * 0.65,
                "availability": "Available if you can negotiate"
            })

            return options

        # AUTO LOANS: Payment deferral, loan modification
        if "AUTO_LOAN" in debt_type or "AUTOLOAN" in debt_type:
            options.append({
                "plan_type": "forbearance",
                "name": "Payment Deferral/Forbearance",
                "description": "Skip or reduce payments to avoid repossession",
                "duration_months": 3,
                "new_monthly_payment": 0,
                "original_monthly_payment": debt.minimum_payment,
                "pros": [
                    "Skip payments to avoid repossession",
                    "Usually 2-3 month deferral available",
                    "Payments added to end of loan",
                    "Keep your vehicle"
                ],
                "cons": [
                    "Interest continues to accrue",
                    "Deferred payments added to balance",
                    "May impact credit (-50 to -75 points)",
                    "Limited to 1-2 deferrals per loan"
                ],
                "credit_impact": "⚠️ Moderate impact (-50 to -75 points). Recovers after regular payments resume.",
                "timeline": "3 months deferral, payments added to loan end",
                "estimated_interest_cost": round(debt.balance * interest_rate * 0.25, 2),
                "estimated_total_cost": round(debt.balance * interest_rate * 0.25, 2),
                "availability": "Contact lender immediately"
            })

            # Loan modification
            options.append({
                "plan_type": "loan_modification",
                "name": "Loan Modification",
                "description": "Extend loan term to lower monthly payment",
                "duration_months": 12,
                "new_monthly_payment": debt.minimum_payment * 0.85,
                "original_monthly_payment": debt.minimum_payment,
                "pros": [
                    f"Lower monthly payment (${debt.minimum_payment * 0.85:.2f})",
                    "Extends loan by 12-24 months",
                    "Keep vehicle",
                    "Avoid repossession"
                ],
                "cons": [
                    "Pay more total interest",
                    "Longer payoff timeline",
                    "Small credit impact (-20 to -30 points)",
                    "Lender approval required"
                ],
                "credit_impact": "⚠️ Minor impact (-20 to -30 points).",
                "timeline": "Extended term, lower payments",
                "estimated_interest_cost": round(debt.balance * interest_rate * 0.5, 2),
                "estimated_total_cost": round(debt.balance * interest_rate * 0.5, 2),
                "availability": "Ask lender about options"
            })

            return options

        # MORTGAGES: Forbearance, loan modification, refinancing
        if "MORTGAGE" in debt_type:
            options.append({
                "plan_type": "forbearance",
                "name": "Mortgage Forbearance",
                "description": "Temporarily reduce or pause mortgage payments",
                "duration_months": 6,
                "new_monthly_payment": debt.minimum_payment * 0.50,
                "original_monthly_payment": debt.minimum_payment,
                "pros": [
                    "Reduce payments 30-50%",
                    "Avoid foreclosure",
                    "Can be 3-12 months",
                    "Payments can be added to loan end"
                ],
                "cons": [
                    "Interest may accrue",
                    "Credit impact (-50 to -100 points)",
                    "Requires repayment plan after forbearance ends",
                    "May trigger due-on-sale clause"
                ],
                "credit_impact": "⚠️ Moderate-High impact (-50 to -100 points). Recovers after forbearance ends.",
                "timeline": "3-12 months forbearance, then resume payments",
                "estimated_interest_cost": round(debt.balance * interest_rate * 0.5, 2),
                "estimated_total_cost": round(debt.balance * interest_rate * 0.5, 2),
                "availability": "Contact lender or HUD-approved counselor"
            })

            return options

        # DEFAULT: Return empty (unknown debt type)
        return options

    @staticmethod
    def recommend_hardship_plan(
            user: User,
            debt: Debt,
            monthly_cash_available: float
    ) -> Dict:
        """Recommend best hardship plan based on user situation"""

        options = HardshipService.get_hardship_options(debt)

        # Get debt type as uppercase string
        if hasattr(debt.debt_type, 'value'):
            debt_type = debt.debt_type.value.upper()
        else:
            debt_type = str(debt.debt_type).upper()

        # Define thresholds for all debt types (as percentage of minimum payment)
        critical_threshold = debt.minimum_payment * 0.25  # 25% of minimum
        difficult_threshold = debt.minimum_payment * 0.75  # 75% of minimum
        manageable_threshold = debt.minimum_payment * 1.5  # 150% of minimum

        recommendation = {
            "situation": "",
            "recommended_plan": "",
            "reason": "",
            "options": options
        }

        # CREDIT CARDS: Settlement only
        if "CREDIT_CARD" in debt_type or "CREDITCARD" in debt_type:
            if monthly_cash_available <= critical_threshold:
                recommendation["situation"] = "CRITICAL - Severe hardship"
                recommendation["recommended_plan"] = "settlement"
                recommendation[
                    "reason"] = f"You cannot make meaningful payments (${monthly_cash_available:.2f}/month < 25% of minimum ${debt.minimum_payment:.2f}). Settlement is your primary option. Consult creditor about any hardship programs first. Only pursue if you can negotiate within 30 days and have lump sum available."

            elif monthly_cash_available < difficult_threshold:
                recommendation["situation"] = "DIFFICULT - Severe payment struggles"
                recommendation["recommended_plan"] = "settlement"
                recommendation[
                    "reason"] = f"You can only pay 25-75% of minimum (${monthly_cash_available:.2f}/${debt.minimum_payment:.2f}). Settlement is realistic option. Negotiate quickly - creditors more willing when accounts recent. Have lump sum ready."

            elif monthly_cash_available <= manageable_threshold:
                recommendation["situation"] = "MANAGEABLE - Tight but making payments"
                recommendation["recommended_plan"] = "continue_payments"
                recommendation[
                    "reason"] = f"You can afford 75-150% of minimum (${monthly_cash_available:.2f}/${debt.minimum_payment:.2f}). BEST: Continue payments to rebuild credit. Contact creditor about hardship programs (many offer payment reduction/deferment). Settlement damages credit 7 years unnecessarily."

            else:
                recommendation["situation"] = "STRONG - Good payment capacity"
                recommendation["recommended_plan"] = "continue_payments"
                recommendation[
                    "reason"] = f"You can afford 150%+ of minimum (${monthly_cash_available:.2f}/${debt.minimum_payment:.2f}). BEST: Continue payments - debt-free in 18-24 months with zero credit damage. If struggling, contact creditor about hardship programs. Settlement would damage credit 7 years unnecessarily."

            return recommendation

        # STUDENT LOANS: Deferment/forbearance available
        if "STUDENT_LOAN" in debt_type or "STUDENTLOAN" in debt_type:
            if monthly_cash_available <= critical_threshold:
                recommendation["situation"] = "CRITICAL - Very limited income"
                recommendation["recommended_plan"] = "deferment"
                recommendation[
                    "reason"] = "Apply for deferment immediately. Federal student loans offer deferment during hardship."

            elif monthly_cash_available < difficult_threshold:
                recommendation["situation"] = "DIFFICULT - Can't afford minimum"
                recommendation["recommended_plan"] = "deferment"
                recommendation[
                    "reason"] = f"Can't afford minimum (${debt.minimum_payment:.2f}). Deferment or income-driven repayment reduces/pauses payments."

            else:
                recommendation["situation"] = "MANAGEABLE - Some cash flow"
                recommendation["recommended_plan"] = "forbearance"
                recommendation[
                    "reason"] = f"Income-driven repayment adjusts payments based on income (10-20% discretionary). Forgiveness after 20-25 years."

            return recommendation

        # PERSONAL LOANS: Forbearance/settlement available
        if "PERSONAL_LOAN" in debt_type or "PERSONALLOAN" in debt_type:
            if monthly_cash_available <= critical_threshold:
                recommendation["situation"] = "CRITICAL - Very limited income"
                recommendation["recommended_plan"] = "settlement"
                recommendation["reason"] = "Need immediate relief. Settlement negotiation with lender is best option."

            elif monthly_cash_available < difficult_threshold:
                recommendation["situation"] = "DIFFICULT - Can't afford minimum"
                recommendation["recommended_plan"] = "forbearance"
                recommendation[
                    "reason"] = f"Can't afford minimum (${debt.minimum_payment:.2f}). Contact lender about forbearance/hardship plan."

            elif monthly_cash_available <= manageable_threshold:
                recommendation["situation"] = "MANAGEABLE - Barely covering minimum"
                recommendation["recommended_plan"] = "forbearance"
                recommendation[
                    "reason"] = f"Covering minimum with no cushion. Forbearance reduces payments temporarily."

            else:
                settlement_amount = debt.balance * 0.65
                months_to_save = settlement_amount / monthly_cash_available

                recommendation["situation"] = "STRONG - Good cash flow"

                if months_to_save <= 12:
                    recommendation["recommended_plan"] = "settlement"
                    recommendation[
                        "reason"] = f"Could save for settlement in {months_to_save:.0f} months (${settlement_amount:.2f}). Consider settlement for faster payoff."
                else:
                    recommendation["recommended_plan"] = "continue_payments"
                    recommendation[
                        "reason"] = f"With ${monthly_cash_available:.2f}/month, continue regular payments. Debt-free faster than settlement."

            return recommendation

        # AUTO LOANS: Forbearance/modification available
        if "AUTO_LOAN" in debt_type or "AUTOLOAN" in debt_type:
            if monthly_cash_available <= critical_threshold:
                recommendation["situation"] = "CRITICAL - Risk of repossession"
                recommendation["recommended_plan"] = "forbearance"
                recommendation[
                    "reason"] = "Contact lender IMMEDIATELY. Payment deferral prevents repossession. Act within days."

            elif monthly_cash_available < difficult_threshold:
                recommendation["situation"] = "DIFFICULT - Can't afford minimum"
                recommendation["recommended_plan"] = "forbearance"
                recommendation[
                    "reason"] = f"Can't afford minimum (${debt.minimum_payment:.2f}). Request payment deferral to avoid repossession."

            elif monthly_cash_available <= manageable_threshold:
                recommendation["situation"] = "MANAGEABLE - Tight on payments"
                recommendation["recommended_plan"] = "forbearance"
                recommendation[
                    "reason"] = f"Barely covering payments. Loan modification extends term and lowers payment."

            else:
                recommendation["situation"] = "STRONG - Good cash flow"
                recommendation["recommended_plan"] = "continue_payments"
                recommendation[
                    "reason"] = f"With ${monthly_cash_available:.2f}/month, continue payments. Build equity and avoid repossession risk."

            return recommendation

        # MORTGAGES: Forbearance/modification available
        if "MORTGAGE" in debt_type:
            if monthly_cash_available < debt.minimum_payment * 0.5:
                recommendation["situation"] = "CRITICAL - Risk of foreclosure"
                recommendation["recommended_plan"] = "forbearance"
                recommendation[
                    "reason"] = "Contact lender IMMEDIATELY. Forbearance prevents foreclosure. HUD counselor can help."

            elif monthly_cash_available < debt.minimum_payment:
                recommendation["situation"] = "DIFFICULT - Can't afford full payment"
                recommendation["recommended_plan"] = "forbearance"
                recommendation[
                    "reason"] = f"Short on mortgage (${debt.minimum_payment:.2f}). Forbearance temporarily reduces/pauses payments."

            else:
                recommendation["situation"] = "MANAGEABLE - Covering payments"
                recommendation["recommended_plan"] = "continue_payments"
                recommendation["reason"] = f"Covering payments. Continue to maintain equity and credit."

            return recommendation

        # DEFAULT
        recommendation["situation"] = "UNKNOWN - Debt type not recognized"
        recommendation["recommended_plan"] = "contact_creditor"
        recommendation["reason"] = "Contact creditor directly about available hardship options."

        return recommendation

    @staticmethod
    def calculate_deferment_impact(
            debt: Debt,
            deferment_months: int = 6
    ) -> Dict:
        """Calculate impact of deferment on debt"""

        # Convert percentage to decimal (12.0 → 0.12)
        interest_rate = debt.interest_rate / 100 if debt.interest_rate > 1 else debt.interest_rate

        balance = debt.balance
        total_interest = 0

        for month in range(deferment_months):
            monthly_interest = balance * (interest_rate / 12)
            total_interest += monthly_interest
            balance += monthly_interest

        new_balance = balance

        return {
            "plan_type": "deferment",
            "deferment_months": deferment_months,
            "current_balance": debt.balance,
            "balance_after_deferment": round(new_balance, 2),
            "interest_accrued": round(total_interest, 2),
            "total_increase": round(total_interest, 2),
            "credit_impact": "50-100 point drop initially, recovers over 12 months with on-time payments",
            "recovery_timeline": "12-24 months to recover to current score"
        }

    @staticmethod
    def calculate_forbearance_impact(
            debt: Debt,
            reduced_payment: float,
            forbearance_months: int = 12
    ) -> Dict:
        """Calculate impact of forbearance on debt"""

        # Convert percentage to decimal
        interest_rate = debt.interest_rate / 100 if debt.interest_rate > 1 else debt.interest_rate

        balance = debt.balance
        total_interest = 0

        for month in range(forbearance_months):
            monthly_interest = balance * (interest_rate / 12)
            total_interest += monthly_interest
            balance += monthly_interest
            balance -= reduced_payment

            # Don't let balance go negative
            if balance < 0:
                balance = 0
                break

        new_balance = max(balance, 0)

        return {
            "plan_type": "forbearance",
            "forbearance_months": forbearance_months,
            "original_payment": debt.minimum_payment,
            "reduced_payment": reduced_payment,
            "monthly_savings": round(debt.minimum_payment - reduced_payment, 2),
            "current_balance": debt.balance,
            "balance_after_forbearance": round(new_balance, 2),
            "interest_accrued": round(total_interest, 2),
            "total_increase": round(total_interest, 2),
            "credit_impact": "20-50 point drop initially, recovers quickly with on-time payments",
            "recovery_timeline": "6-12 months to full recovery"
        }

    @staticmethod
    def calculate_settlement_impact(
            debt: Debt,
            settlement_percentage: float = 0.50
    ) -> Dict:
        """Calculate impact of settlement negotiation"""

        settlement_amount = debt.balance * settlement_percentage
        amount_forgiven = debt.balance - settlement_amount

        return {
            "plan_type": "settlement",
            "current_balance": debt.balance,
            "settlement_amount": round(settlement_amount, 2),
            "amount_forgiven": round(amount_forgiven, 2),
            "savings": round(amount_forgiven, 2),
            "settlement_percentage": f"{settlement_percentage * 100:.0f}%",
            "credit_impact": "100-150 point drop, stays on credit for 7 years",
            "recovery_timeline": "3-5 years to recover, removed from credit after 7 years",
            "tax_implications": f"Forgiven ${amount_forgiven:.2f} may be taxable income - consult tax professional",
            "requirements": f"Need ~${settlement_amount:.2f} lump sum payment"
        }

    @staticmethod
    def create_hardship_plan(
            db: Session,
            user_id: int,
            debt_id: int,
            plan_type: str,
            reason: str,
            **kwargs
    ) -> HardshipPlan:
        """Create hardship plan for user"""

        debt = db.query(Debt).filter(
            Debt.id == debt_id,
            Debt.user_id == user_id
        ).first()

        if not debt:
            raise ValueError("Debt not found")

        # Calculate impact based on plan type
        if plan_type == "deferment":
            impact = HardshipService.calculate_deferment_impact(
                debt,
                kwargs.get("deferment_months", 6)
            )
            total_cost = impact["interest_accrued"]

        elif plan_type == "forbearance":
            impact = HardshipService.calculate_forbearance_impact(
                debt,
                kwargs.get("reduced_payment_amount", debt.minimum_payment * 0.5),
                kwargs.get("forbearance_months", 12)
            )
            total_cost = impact["interest_accrued"]

        elif plan_type == "settlement":
            impact = HardshipService.calculate_settlement_impact(
                debt,
                kwargs.get("settlement_percentage", 0.50)
            )
            total_cost = impact["settlement_amount"]

        else:
            raise ValueError("Invalid plan type")

        hardship_plan = HardshipPlan(
            user_id=user_id,
            debt_id=debt_id,
            plan_type=plan_type,
            reason_for_hardship=reason,
            deferment_months=kwargs.get("deferment_months"),
            reduced_payment_amount=kwargs.get("reduced_payment_amount"),
            forbearance_months=kwargs.get("forbearance_months"),
            settlement_percentage=kwargs.get("settlement_percentage"),
            settlement_amount=kwargs.get("settlement_amount"),
            credit_impact=impact.get("credit_impact"),
            total_cost=total_cost,
            status="created"
        )

        db.add(hardship_plan)
        db.commit()
        db.refresh(hardship_plan)

        return hardship_plan
