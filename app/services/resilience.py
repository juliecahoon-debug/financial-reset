from sqlalchemy.orm import Session
from app.models.debt import Debt


async def calculate_resilience_score(user_id: int, db: Session) -> dict:
    """
    Calculate resilience score and all 7 component scores for a user.
    Returns dict with total_score, financial_state, scores, and raw data.

    Weights:
        Emergency Buffer      25%
        Debt Service Ratio    20%
        Income Stability      20%
        Insurance Coverage    15%
        Concentration Risk    10%
        Credit Access         10%
        Recovery Velocity     10%

    TODO: Replace PLACEHOLDER values with live Plaid data once
          Plaid scaffolding is wired (link-token / exchange endpoints).
    """

    try:
        # ── DIMENSION 1: EMERGENCY BUFFER (25%) ──────────────────────────────
        # How many months of expenses covered by liquid savings?
        # Data: Plaid (bank/savings balances) + Plaid (monthly spend estimate)
        savings = 3000          # TODO: replace with Plaid balance
        monthly_expenses = 2000 # TODO: replace with Plaid spend average

        emergency_buffer_months = savings / monthly_expenses if monthly_expenses > 0 else 0
        emergency_buffer_score = min(100.0, (emergency_buffer_months / 6) * 100)

        # ── DIMENSION 2: DEBT SERVICE RATIO (20%) ────────────────────────────
        # What % of take-home income goes to debt payments?
        # Data: Plaid (income) + Debts table (monthly_payment)
        debts = db.query(Debt).filter(
            Debt.user_id == user_id,
            Debt.is_active == True  # noqa: E712
        ).all()

        total_monthly_debt = sum(
            float(d.monthly_payment) for d in debts if d.monthly_payment is not None
        )

        monthly_income = 4000  # TODO: replace with Plaid income

        debt_service_ratio = (
            (total_monthly_debt / monthly_income) * 100 if monthly_income > 0 else 0
        )

        # 100% if ≤20% of income; 0% if ≥50%; linear between
        if debt_service_ratio <= 20:
            debt_service_ratio_score = 100.0
        elif debt_service_ratio >= 50:
            debt_service_ratio_score = 0.0
        else:
            debt_service_ratio_score = 100.0 - ((debt_service_ratio - 20) / 30) * 100

        # ── DIMENSION 3: INCOME STABILITY (20%) ──────────────────────────────
        # Coefficient of variation of past 6 months income
        # Data: Plaid (income transactions, last 6 months)
        income_stability_percent = 5.0   # TODO: replace with Plaid CV calculation
        # 100% if <5% variation; 0% if >50%; linear between
        if income_stability_percent <= 5:
            income_stability_score = 100.0
        elif income_stability_percent >= 50:
            income_stability_score = 0.0
        else:
            income_stability_score = 100.0 - ((income_stability_percent - 5) / 45) * 100

        # ── DIMENSION 4: INSURANCE COVERAGE (15%) ────────────────────────────
        # health + auto + home/renters + disability + life
        # Data: user input (5 yes/no flags)
        insurance_coverage_percent = 0.0   # TODO: collect via onboarding question
        insurance_coverage_score = insurance_coverage_percent  # 1:1 mapping

        # ── DIMENSION 5: CONCENTRATION RISK (10%) ────────────────────────────
        # Over-reliance on single income stream?
        # Data: Plaid (distinct income sources)
        num_income_sources = 1             # TODO: replace with Plaid income sources count
        concentration_risk_ratio = float(min(num_income_sources, 3))

        if num_income_sources >= 2:
            concentration_risk_score = 100.0
        else:
            concentration_risk_score = 50.0

        # ── DIMENSION 6: CREDIT ACCESS (10%) ─────────────────────────────────
        # Available credit headroom
        # Data: Plaid (credit card limits + balances)
        available_credit = 10000.0   # TODO: replace with Plaid credit data
        total_credit_limit = 25000.0 # TODO: replace with Plaid credit data

        credit_utilization_percent = (
            (1 - (available_credit / total_credit_limit)) * 100
            if total_credit_limit > 0 else 0
        )

        # Best at ≤30% utilization; worst at ≥80%
        if credit_utilization_percent <= 30:
            credit_access_score = 100.0
        elif credit_utilization_percent >= 80:
            credit_access_score = 0.0
        else:
            credit_access_score = 100.0 - ((credit_utilization_percent - 30) / 50) * 100

        # ── DIMENSION 7: RECOVERY VELOCITY (10%) ─────────────────────────────
        # How quickly can they recover from a $1,000 financial shock?
        monthly_surplus = monthly_income - total_monthly_debt
        recovery_capacity = savings + monthly_surplus

        recovery_months = 1000 / recovery_capacity if recovery_capacity > 0 else 100.0

        if recovery_months <= 1:
            recovery_velocity_score = 100.0
        elif recovery_months >= 12:
            recovery_velocity_score = 0.0
        else:
            recovery_velocity_score = 100.0 - ((recovery_months - 1) / 11) * 100

        # ── WEIGHTED TOTAL ────────────────────────────────────────────────────
        weights = {
            "emergency_buffer":    0.25,
            "debt_service_ratio":  0.20,
            "income_stability":    0.20,
            "insurance_coverage":  0.15,
            "concentration_risk":  0.10,
            "credit_access":       0.10,
            "recovery_velocity":   0.10,
        }

        total_score = (
            emergency_buffer_score    * weights["emergency_buffer"]    +
            debt_service_ratio_score  * weights["debt_service_ratio"]  +
            income_stability_score    * weights["income_stability"]     +
            insurance_coverage_score  * weights["insurance_coverage"]   +
            concentration_risk_score  * weights["concentration_risk"]   +
            credit_access_score       * weights["credit_access"]        +
            recovery_velocity_score   * weights["recovery_velocity"]
        )

        # ── FINANCIAL STATE ───────────────────────────────────────────────────
        if total_score >= 80:
            financial_state = "thriving"
        elif total_score >= 60:
            financial_state = "stable"
        elif total_score >= 40:
            financial_state = "strained"
        elif total_score >= 20:
            financial_state = "stressed"
        else:
            financial_state = "in_crisis"

        return {
            "success": True,
            "total_score": round(total_score, 1),
            "financial_state": financial_state,
            "scores": {
                "emergency_buffer":   round(emergency_buffer_score, 1),
                "debt_service_ratio": round(debt_service_ratio_score, 1),
                "income_stability":   round(income_stability_score, 1),
                "insurance_coverage": round(insurance_coverage_score, 1),
                "concentration_risk": round(concentration_risk_score, 1),
                "credit_access":      round(credit_access_score, 1),
                "recovery_velocity":  round(recovery_velocity_score, 1),
            },
            "raw": {
                "emergency_buffer_months":     round(emergency_buffer_months, 1),
                "debt_service_ratio_percent":  round(debt_service_ratio, 1),
                "income_stability_percent":    round(income_stability_percent, 1),
                "insurance_coverage_percent":  round(insurance_coverage_percent, 1),
                "concentration_risk_ratio":    round(concentration_risk_ratio, 2),
                "credit_utilization_percent":  round(credit_utilization_percent, 1),
                "recovery_months":             round(recovery_months, 1),
            },
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }
