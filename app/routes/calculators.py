"""
app/routes/calculators.py

Pure-math calculator endpoints — no DB required.
All inputs come in via POST body, results returned immediately.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Literal
import math

router = APIRouter(prefix="/calculators", tags=["calculators"])


# ─────────────────────────────────────────────────────────────
# 1. DEBT PAYOFF — Snowball vs. Avalanche
# ─────────────────────────────────────────────────────────────

class DebtItem(BaseModel):
    name: str
    balance: float = Field(gt=0)
    apr: float = Field(ge=0, description="Annual percentage rate as decimal, e.g. 0.2499")
    minimum_payment: float = Field(gt=0)

class DebtPayoffRequest(BaseModel):
    debts: list[DebtItem]
    extra_monthly_payment: float = Field(default=0, ge=0)

class PayoffDebtResult(BaseModel):
    name: str
    months_to_payoff: int
    total_interest: float
    payoff_order: int

class DebtPayoffResponse(BaseModel):
    method: str
    total_months: int
    total_interest: float
    total_paid: float
    monthly_payment: float
    payoff_order: list[PayoffDebtResult]

def _amortize(balance: float, apr: float, monthly_payment: float) -> tuple[int, float]:
    """Returns (months, total_interest) for a single debt."""
    if apr == 0:
        months = math.ceil(balance / monthly_payment)
        return months, 0.0
    monthly_rate = apr / 12
    if monthly_payment <= balance * monthly_rate:
        # Payment doesn't cover interest — never pays off
        return 9999, float("inf")
    months = math.ceil(
        -math.log(1 - (balance * monthly_rate) / monthly_payment) / math.log(1 + monthly_rate)
    )
    total_paid = monthly_payment * months
    total_interest = total_paid - balance
    return months, max(0.0, total_interest)

def _run_payoff(debts: list[DebtItem], extra: float, method: Literal["snowball", "avalanche"]) -> DebtPayoffResponse:
    # Sort order
    sorted_debts = sorted(
        debts,
        key=lambda d: d.balance if method == "snowball" else d.apr,
    )
    total_min = sum(d.minimum_payment for d in debts)
    monthly_budget = total_min + extra

    remaining = {d.name: d.balance for d in sorted_debts}
    interest_paid = {d.name: 0.0 for d in sorted_debts}
    payoff_month = {}
    month = 0
    max_months = 600  # 50 year cap

    while any(b > 0.01 for b in remaining.values()) and month < max_months:
        month += 1
        # Accrue interest
        for d in sorted_debts:
            if remaining[d.name] > 0:
                remaining[d.name] += remaining[d.name] * (d.apr / 12)

        # Pay minimums on all
        available = monthly_budget
        for d in sorted_debts:
            if remaining[d.name] > 0:
                pay = min(d.minimum_payment, remaining[d.name])
                interest_paid[d.name] += max(0, pay - (d.balance * d.apr / 12 if d.apr else 0))
                remaining[d.name] -= pay
                available -= pay
                if remaining[d.name] < 0:
                    remaining[d.name] = 0

        # Apply extra to first non-zero debt in sorted order
        for d in sorted_debts:
            if remaining[d.name] > 0 and available > 0:
                pay = min(available, remaining[d.name])
                remaining[d.name] -= pay
                available -= pay
                if remaining[d.name] < 0:
                    remaining[d.name] = 0

        # Record payoffs
        for d in sorted_debts:
            if remaining[d.name] <= 0.01 and d.name not in payoff_month:
                payoff_month[d.name] = month

    # Recalculate total interest simply
    total_interest = 0.0
    results = []
    for i, d in enumerate(sorted_debts):
        _, ti = _amortize(d.balance, d.apr, d.minimum_payment + (extra if i == 0 else 0))
        total_interest += ti
        results.append(PayoffDebtResult(
            name=d.name,
            months_to_payoff=payoff_month.get(d.name, month),
            total_interest=round(ti, 2),
            payoff_order=i + 1,
        ))

    total_paid = sum(d.balance for d in debts) + total_interest
    return DebtPayoffResponse(
        method=method,
        total_months=month,
        total_interest=round(total_interest, 2),
        total_paid=round(total_paid, 2),
        monthly_payment=round(monthly_budget, 2),
        payoff_order=results,
    )

@router.post("/debt-payoff/snowball", response_model=DebtPayoffResponse)
def debt_payoff_snowball(req: DebtPayoffRequest):
    """Snowball method: pay smallest balance first."""
    return _run_payoff(req.debts, req.extra_monthly_payment, "snowball")

@router.post("/debt-payoff/avalanche", response_model=DebtPayoffResponse)
def debt_payoff_avalanche(req: DebtPayoffRequest):
    """Avalanche method: pay highest APR first."""
    return _run_payoff(req.debts, req.extra_monthly_payment, "avalanche")


# ─────────────────────────────────────────────────────────────
# 2. SETTLEMENT ESTIMATOR
# ─────────────────────────────────────────────────────────────

class SettlementRequest(BaseModel):
    balance: float = Field(gt=0)
    apr: float = Field(ge=0)
    minimum_payment: float = Field(gt=0)
    settlement_percent: float = Field(default=0.50, ge=0.10, le=0.90,
        description="Fraction of balance to settle for, e.g. 0.50 = 50 cents on the dollar")
    can_pay_lump_sum: bool = True

class SettlementResponse(BaseModel):
    settlement_amount: float
    savings_vs_full_payoff: float
    months_to_payoff_minimum: int
    total_cost_minimum: float
    total_interest_minimum: float
    credit_impact: str
    tax_note: str
    recommendation: str

@router.post("/settlement", response_model=SettlementResponse)
def settlement_estimator(req: SettlementRequest):
    months, interest = _amortize(req.balance, req.apr, req.minimum_payment)
    total_minimum = req.balance + interest
    settlement_amount = round(req.balance * req.settlement_percent, 2)
    savings = round(total_minimum - settlement_amount, 2)
    forgiven = req.balance - settlement_amount
    recommendation = (
        "Settlement may be your best option given delinquency status — "
        "the savings outweigh the credit impact if you can pay the lump sum."
        if req.can_pay_lump_sum and savings > 1000
        else "Consider a hardship payment plan first — settlement has lasting credit impact."
    )
    return SettlementResponse(
        settlement_amount=settlement_amount,
        savings_vs_full_payoff=savings,
        months_to_payoff_minimum=months,
        total_cost_minimum=round(total_minimum, 2),
        total_interest_minimum=round(interest, 2),
        credit_impact="Account marked 'Settled' — stays on credit report 7 years.",
        tax_note=f"Forgiven amount ~${forgiven:,.0f} may be reported as income (IRS Form 1099-C). Consult a tax advisor.",
        recommendation=recommendation,
    )


# ─────────────────────────────────────────────────────────────
# 3. MINIMUM PAYMENT TRAP
# ─────────────────────────────────────────────────────────────

class MinPaymentRequest(BaseModel):
    balance: float = Field(gt=0)
    apr: float = Field(gt=0)
    minimum_payment: float = Field(gt=0)
    accelerated_payment: float = Field(default=0, ge=0,
        description="Additional monthly amount above minimum")

class MinPaymentResponse(BaseModel):
    months_minimum_only: int
    years_minimum_only: float
    total_interest_minimum: float
    total_paid_minimum: float
    months_accelerated: int
    years_accelerated: float
    total_interest_accelerated: float
    total_paid_accelerated: float
    interest_saved: float
    time_saved_months: int

@router.post("/minimum-payment-trap", response_model=MinPaymentResponse)
def minimum_payment_trap(req: MinPaymentRequest):
    m_min, i_min = _amortize(req.balance, req.apr, req.minimum_payment)
    m_acc, i_acc = _amortize(req.balance, req.apr, req.minimum_payment + req.accelerated_payment)
    return MinPaymentResponse(
        months_minimum_only=m_min,
        years_minimum_only=round(m_min / 12, 1),
        total_interest_minimum=round(i_min, 2),
        total_paid_minimum=round(req.balance + i_min, 2),
        months_accelerated=m_acc,
        years_accelerated=round(m_acc / 12, 1),
        total_interest_accelerated=round(i_acc, 2),
        total_paid_accelerated=round(req.balance + i_acc, 2),
        interest_saved=round(i_min - i_acc, 2),
        time_saved_months=m_min - m_acc,
    )


# ─────────────────────────────────────────────────────────────
# 4. CONSOLIDATION BREAK-EVEN
# ─────────────────────────────────────────────────────────────

class ConsolidationRequest(BaseModel):
    debts: list[DebtItem]
    new_loan_apr: float = Field(ge=0)
    new_loan_term_months: int = Field(gt=0)
    origination_fee_percent: float = Field(default=0.03, ge=0,
        description="Loan origination fee as decimal, e.g. 0.03 = 3%")

class ConsolidationResponse(BaseModel):
    total_current_balance: float
    loan_amount_with_fee: float
    new_monthly_payment: float
    total_paid_current: float
    total_paid_consolidated: float
    total_interest_current: float
    total_interest_consolidated: float
    net_savings: float
    break_even_months: int
    recommendation: str

@router.post("/consolidation", response_model=ConsolidationResponse)
def consolidation_breakeven(req: ConsolidationRequest):
    total_balance = sum(d.balance for d in req.debts)
    origination = total_balance * req.origination_fee_percent
    loan_amount = total_balance + origination

    # New loan payment
    r = req.new_loan_apr / 12
    n = req.new_loan_term_months
    if r == 0:
        new_payment = loan_amount / n
    else:
        new_payment = loan_amount * (r * (1 + r) ** n) / ((1 + r) ** n - 1)

    # Current total interest (each debt separately, paying minimums)
    current_total_interest = 0.0
    current_total_paid = 0.0
    for d in req.debts:
        _, i = _amortize(d.balance, d.apr, d.minimum_payment)
        current_total_interest += i
        current_total_paid += d.balance + i

    consolidated_interest = (new_payment * n) - total_balance
    consolidated_total = loan_amount + consolidated_interest
    savings = current_total_paid - consolidated_total

    # Break-even: months until cumulative savings > origination fee
    current_monthly_total = sum(d.minimum_payment for d in req.debts)
    monthly_saving = current_monthly_total - new_payment
    break_even = math.ceil(origination / monthly_saving) if monthly_saving > 0 else 9999

    recommendation = (
        f"Consolidation saves ~${savings:,.0f} over the loan term. Break-even at month {break_even}."
        if savings > 0
        else "Consolidation costs more than your current plan — the new APR or term is unfavorable."
    )

    return ConsolidationResponse(
        total_current_balance=round(total_balance, 2),
        loan_amount_with_fee=round(loan_amount, 2),
        new_monthly_payment=round(new_payment, 2),
        total_paid_current=round(current_total_paid, 2),
        total_paid_consolidated=round(consolidated_total, 2),
        total_interest_current=round(current_total_interest, 2),
        total_interest_consolidated=round(consolidated_interest, 2),
        net_savings=round(savings, 2),
        break_even_months=break_even,
        recommendation=recommendation,
    )


# ─────────────────────────────────────────────────────────────
# 5. BALANCE TRANSFER
# ─────────────────────────────────────────────────────────────

class BalanceTransferRequest(BaseModel):
    balance: float = Field(gt=0)
    current_apr: float = Field(gt=0)
    current_minimum_payment: float = Field(gt=0)
    promo_apr: float = Field(default=0.0, ge=0)
    promo_months: int = Field(gt=0)
    transfer_fee_percent: float = Field(default=0.03, ge=0)
    post_promo_apr: float = Field(ge=0)

class BalanceTransferResponse(BaseModel):
    transfer_fee: float
    total_balance_after_fee: float
    interest_current_during_promo: float
    interest_transfer_during_promo: float
    interest_saved_during_promo: float
    remaining_balance_after_promo: float
    required_monthly_to_clear_in_promo: float
    total_saved_vs_staying: float
    recommendation: str

@router.post("/balance-transfer", response_model=BalanceTransferResponse)
def balance_transfer(req: BalanceTransferRequest):
    fee = req.balance * req.transfer_fee_percent
    new_balance = req.balance + fee

    # Interest on current card during promo period
    _, i_current_full = _amortize(req.balance, req.current_apr, req.current_minimum_payment)
    # Approximate interest during just the promo window
    promo_rate_current = req.current_apr / 12
    i_current_promo = req.balance * promo_rate_current * req.promo_months

    # Interest on transferred balance during promo
    promo_rate_transfer = req.promo_apr / 12
    i_transfer_promo = new_balance * promo_rate_transfer * req.promo_months

    interest_saved = i_current_promo - i_transfer_promo - fee

    # Remaining balance if paying minimum during promo
    remaining = new_balance
    for _ in range(req.promo_months):
        remaining += remaining * promo_rate_transfer
        remaining -= req.current_minimum_payment
        remaining = max(remaining, 0)

    required_monthly = (new_balance / req.promo_months) if req.promo_months > 0 else new_balance

    recommendation = (
        f"Transfer saves ~${max(interest_saved, 0):,.0f} during the promo period. "
        f"Pay ${required_monthly:,.0f}/month to clear the balance before promo ends."
        if interest_saved > 0
        else "The transfer fee may outweigh the interest savings — compare carefully before transferring."
    )

    return BalanceTransferResponse(
        transfer_fee=round(fee, 2),
        total_balance_after_fee=round(new_balance, 2),
        interest_current_during_promo=round(i_current_promo, 2),
        interest_transfer_during_promo=round(i_transfer_promo, 2),
        interest_saved_during_promo=round(max(interest_saved, 0), 2),
        remaining_balance_after_promo=round(remaining, 2),
        required_monthly_to_clear_in_promo=round(required_monthly, 2),
        total_saved_vs_staying=round(max(interest_saved, 0), 2),
        recommendation=recommendation,
    )


# ─────────────────────────────────────────────────────────────
# 6. HARDSHIP IMPACT (Score Impact Simulator)
# ─────────────────────────────────────────────────────────────

class HardshipImpactRequest(BaseModel):
    current_resilience_score: float = Field(ge=0, le=100)
    option: Literal["forbearance", "settlement", "default", "payment_plan", "deferment"]
    months_delinquent: int = Field(default=0, ge=0)
    balance: float = Field(gt=0)
    total_debt: float = Field(gt=0)

class HardshipImpactResponse(BaseModel):
    option: str
    score_impact: float
    projected_score: float
    recovery_months: int
    credit_report_note: str
    risk_level: str
    pros: list[str]
    cons: list[str]

HARDSHIP_IMPACTS = {
    "forbearance": {
        "impact": 0,
        "recovery": 0,
        "credit_note": "No negative reporting during approved forbearance period.",
        "risk": "low",
        "pros": ["No credit impact", "Payments paused", "Account stays current"],
        "cons": ["Interest may still accrue", "Limited to 1-3 months typically", "Must reapply after period ends"],
    },
    "deferment": {
        "impact": 0,
        "recovery": 0,
        "credit_note": "Account reported as current during deferment.",
        "risk": "low",
        "pros": ["No credit impact", "Account stays current", "Often available for student loans and medical"],
        "cons": ["Interest accrues on some loan types", "Temporary — underlying debt remains"],
    },
    "payment_plan": {
        "impact": -5,
        "recovery": 6,
        "credit_note": "Account may show reduced payment arrangement — minor impact.",
        "risk": "low",
        "pros": ["Keeps account from going delinquent", "Creditor relationship preserved", "Predictable payments"],
        "cons": ["Small score dip", "Credit limit may be reduced", "Interest continues"],
    },
    "settlement": {
        "impact": -25,
        "recovery": 24,
        "credit_note": "Account marked 'Settled for Less Than Full Amount' — remains 7 years.",
        "risk": "high",
        "pros": ["Eliminates debt at a discount", "Stops collections activity", "Definitive resolution"],
        "cons": ["Major score drop", "7-year credit report entry", "Potential tax liability (1099-C)", "May affect future loan eligibility"],
    },
    "default": {
        "impact": -40,
        "recovery": 36,
        "credit_note": "Charge-off reported — severe and long-lasting credit damage (7 years).",
        "risk": "critical",
        "pros": ["Debt may eventually be discharged", "Stops minimum payment pressure"],
        "cons": ["Catastrophic score drop", "Collections and lawsuits likely", "Wage garnishment risk", "7-year credit report entry", "Future credit very difficult to obtain"],
    },
}

@router.post("/hardship-impact", response_model=HardshipImpactResponse)
def hardship_impact(req: HardshipImpactRequest):
    cfg = HARDSHIP_IMPACTS[req.option]
    # Delinquency modifier — already delinquent accounts have less additional impact from settlement
    delinq_modifier = min(req.months_delinquent * 2, 15) if req.option in ("settlement", "default") else 0
    adjusted_impact = cfg["impact"] + delinq_modifier  # impact is negative, modifier reduces it (less additional harm)
    projected = max(0.0, min(100.0, req.current_resilience_score + adjusted_impact))

    return HardshipImpactResponse(
        option=req.option.replace("_", " ").title(),
        score_impact=round(adjusted_impact, 1),
        projected_score=round(projected, 1),
        recovery_months=cfg["recovery"],
        credit_report_note=cfg["credit_note"],
        risk_level=cfg["risk"],
        pros=cfg["pros"],
        cons=cfg["cons"],
    )
