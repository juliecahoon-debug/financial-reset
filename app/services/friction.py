from sqlalchemy.orm import Session
from app.models.debt import Debt, DebtStatus
from app.models.friction import FrictionPoint


# Severity ranking for sorting
_SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _make_point(
    friction_type: str,
    severity: str,
    description: str,
    impact: float,
    action: str,
    improvement: float,
    current_value: float | None = None,
    threshold: float | None = None,
) -> dict:
    return {
        "type": friction_type,
        "severity": severity,
        "description": description,
        "impact_on_resilience": impact,
        "recommended_action": action,
        "estimated_improvement": improvement,
        "current_value": current_value,
        "threshold": threshold,
    }


async def calculate_friction_points(user_id: int, db: Session) -> dict:
    """
    Identify friction points (obstacles) preventing the user's financial progress.

    Evaluates 8 friction dimensions, ranks by severity + impact,
    persists each to friction_points table, and returns the top 5.

    TODO: Replace PLACEHOLDER values with live Plaid data once
          Plaid scaffolding is wired.
    """
    try:
        friction: list[dict] = []

        # ── FETCH DEBTS ───────────────────────────────────────────────────────
        debts = db.query(Debt).filter(
            Debt.user_id == user_id,
            Debt.is_active == True,  # noqa: E712
        ).all()

        # Shared inputs (Plaid placeholders)
        monthly_income = 4000.0    # TODO: replace with Plaid income
        savings = 3000.0           # TODO: replace with Plaid balance
        monthly_expenses = 2000.0  # TODO: replace with Plaid spend average

        total_monthly_debt = sum(
            float(d.monthly_payment) for d in debts if d.monthly_payment is not None
        )
        total_principal = sum(
            float(d.current_principal) for d in debts if d.current_principal is not None
        )

        # ── FRICTION 1: HIGH DEBT LOAD ────────────────────────────────────────
        # Debt payments > 50% of income = critical; > 35% = high
        dti = (total_monthly_debt / monthly_income * 100) if monthly_income > 0 else 0

        if dti > 50:
            friction.append(_make_point(
                "high_debt_load", "critical",
                f"Debt payments are {dti:.1f}% of income (threshold: 50%)",
                impact=20,
                action="Prioritize debt paydown or increase income",
                improvement=20,
                current_value=round(dti, 1), threshold=50.0,
            ))
        elif dti > 35:
            friction.append(_make_point(
                "high_debt_load", "high",
                f"Debt payments are {dti:.1f}% of income (threshold: 35%)",
                impact=10,
                action="Consider balance transfer or consolidation to reduce monthly payment",
                improvement=10,
                current_value=round(dti, 1), threshold=35.0,
            ))

        # ── FRICTION 2: LOW EMERGENCY BUFFER ─────────────────────────────────
        # < 1 month = critical; < 3 months = high
        buffer_months = savings / monthly_expenses if monthly_expenses > 0 else 0

        if buffer_months < 1:
            friction.append(_make_point(
                "low_emergency_buffer", "critical",
                f"Only {buffer_months:.1f} months of expenses saved (threshold: 1 month)",
                impact=15,
                action="Build emergency fund immediately — target $1,000 starter fund first",
                improvement=25,
                current_value=round(buffer_months, 1), threshold=1.0,
            ))
        elif buffer_months < 3:
            friction.append(_make_point(
                "low_emergency_buffer", "high",
                f"Only {buffer_months:.1f} months of expenses saved (threshold: 3 months)",
                impact=10,
                action="Gradually build to 6 months — automate $X/month to savings",
                improvement=15,
                current_value=round(buffer_months, 1), threshold=3.0,
            ))

        # ── FRICTION 3: HIGH INTEREST RATES ──────────────────────────────────
        # Average APR > 15% = high; > 24% = critical
        avg_apr = (
            sum(float(d.interest_rate) for d in debts) / len(debts)
            if debts else 0
        )

        if avg_apr > 24:
            friction.append(_make_point(
                "high_interest_rates", "critical",
                f"Average APR is {avg_apr:.1f}% — costing significantly more each month",
                impact=15,
                action="Refinance or use balance transfer to a 0% intro APR card",
                improvement=12,
                current_value=round(avg_apr, 1), threshold=24.0,
            ))
        elif avg_apr > 15:
            friction.append(_make_point(
                "high_interest_rates", "high",
                f"Average APR is {avg_apr:.1f}% (threshold: 15%)",
                impact=8,
                action="Explore refinance or balance transfer options",
                improvement=8,
                current_value=round(avg_apr, 1), threshold=15.0,
            ))

        # ── FRICTION 4: LATE PAYMENTS ─────────────────────────────────────────
        # Any delinquent accounts
        DELINQUENT_STATUSES = {
            DebtStatus.DELINQ_30,
            DebtStatus.DELINQ_60,
            DebtStatus.DELINQ_90,
            DebtStatus.DELINQ_120,
        }
        late_count = sum(
            1 for d in debts if d.status in DELINQUENT_STATUSES
        )

        if late_count > 2:
            friction.append(_make_point(
                "late_payments", "critical",
                f"{late_count} accounts are past due",
                impact=25,
                action="Contact creditors immediately — ask about hardship programs",
                improvement=30,
                current_value=float(late_count), threshold=0.0,
            ))
        elif late_count > 0:
            friction.append(_make_point(
                "late_payments", "high",
                f"{late_count} account(s) past due",
                impact=15,
                action="Bring past-due accounts current before next payment cycle",
                improvement=20,
                current_value=float(late_count), threshold=0.0,
            ))

        # ── FRICTION 5: NO LIQUID SAVINGS ────────────────────────────────────
        # < $500 in savings = critical
        if savings < 500:
            friction.append(_make_point(
                "no_liquid_savings", "critical",
                f"Only ${savings:.0f} in liquid savings",
                impact=18,
                action="Pause extra debt payments temporarily and build a $500 cash cushion",
                improvement=20,
                current_value=savings, threshold=500.0,
            ))
        elif savings < 1000:
            friction.append(_make_point(
                "no_liquid_savings", "medium",
                f"Less than $1,000 in liquid savings (${savings:.0f})",
                impact=8,
                action="Build savings to $1,000 before aggressively paying down debt",
                improvement=10,
                current_value=savings, threshold=1000.0,
            ))

        # ── FRICTION 6: HIGH CREDIT UTILIZATION ──────────────────────────────
        # > 80% utilization = critical; > 50% = high
        # TODO: replace with Plaid credit data
        available_credit = 10000.0
        total_credit_limit = 25000.0
        utilization = (
            (1 - available_credit / total_credit_limit) * 100
            if total_credit_limit > 0 else 0
        )

        if utilization > 80:
            friction.append(_make_point(
                "high_credit_utilization", "critical",
                f"Credit utilization is {utilization:.1f}% (threshold: 80%)",
                impact=15,
                action="Pay down balances — every 10% reduction improves your score",
                improvement=12,
                current_value=round(utilization, 1), threshold=80.0,
            ))
        elif utilization > 50:
            friction.append(_make_point(
                "high_credit_utilization", "high",
                f"Credit utilization is {utilization:.1f}% (threshold: 50%)",
                impact=8,
                action="Target <30% utilization for optimal credit access",
                improvement=8,
                current_value=round(utilization, 1), threshold=50.0,
            ))

        # ── FRICTION 7: DECLINING INCOME ─────────────────────────────────────
        # TODO: implement with Plaid income trend data
        # Placeholder — no friction added until Plaid is wired
        income_declining = False   # TODO: calculate from Plaid income history

        if income_declining:
            friction.append(_make_point(
                "declining_income", "high",
                "Income has been declining over the past 90 days",
                impact=12,
                action="Review income sources and explore supplemental income options",
                improvement=15,
            ))

        # ── FRICTION 8: UNSTABLE EMPLOYMENT ──────────────────────────────────
        # TODO: implement with user input (employment type)
        # Placeholder — no friction added until user input is collected
        gig_only = False  # TODO: collect via onboarding

        if gig_only:
            friction.append(_make_point(
                "unstable_employment", "medium",
                "Income appears to be primarily gig or contract-based",
                impact=8,
                action="Build larger emergency buffer (9-12 months) to offset income variability",
                improvement=8,
            ))

        # ── RANK AND TRIM ─────────────────────────────────────────────────────
        # Sort by severity first, then impact descending; return top 5
        friction_sorted = sorted(
            friction,
            key=lambda x: (_SEVERITY_RANK.get(x["severity"], 9), -x["impact_on_resilience"]),
        )[:5]

        # ── PERSIST TO DB ─────────────────────────────────────────────────────
        for point in friction_sorted:
            record = FrictionPoint(
                user_id=user_id,
                friction_type=point["type"],
                severity=point["severity"],
                description=point["description"],
                impact_on_resilience=point["impact_on_resilience"],
                current_value=point.get("current_value"),
                threshold=point.get("threshold"),
                recommended_action=point["recommended_action"],
                estimated_improvement=point["estimated_improvement"],
            )
            db.add(record)
        db.commit()

        return {
            "success": True,
            "friction_points": friction_sorted,
            "total_friction_impact": round(sum(p["impact_on_resilience"] for p in friction_sorted), 1),
            "total_improvement_potential": round(sum(p["estimated_improvement"] for p in friction_sorted), 1),
            "critical_count": sum(1 for p in friction_sorted if p["severity"] == "critical"),
            "high_count": sum(1 for p in friction_sorted if p["severity"] == "high"),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
