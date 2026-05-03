from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.debt import BalanceTransfer
from app.schemas.balance_transfer import BalanceTransferCreate, BalanceTransferUpdate
from app.services.debt_service import DebtService
from app.services.strategy_service import StrategyService


class BalanceTransferService:
    """Business logic for balance transfer strategy"""

    @staticmethod
    def create_balance_transfer(
            db: Session,
            user_id: int,
            bt: BalanceTransferCreate
    ) -> BalanceTransfer:
        """Create new balance transfer offer"""

        db_bt = BalanceTransfer(
            user_id=user_id,
            card_name=bt.card_name,
            intro_apr=bt.intro_apr,
            regular_apr=bt.regular_apr,
            promo_months=bt.promo_months,
            balance_transfer_fee=bt.balance_transfer_fee,
            credit_limit=bt.credit_limit
        )

        db.add(db_bt)
        db.commit()
        db.refresh(db_bt)
        return db_bt

    @staticmethod
    def get_user_balance_transfers(
            db: Session,
            user_id: int
    ) -> List[BalanceTransfer]:
        """Get all balance transfer offers for user"""

        return db.query(BalanceTransfer).filter(
            BalanceTransfer.user_id == user_id
        ).all()

    @staticmethod
    def calculate_balance_transfer_strategy(
            debts: List,
            transfer_amount: float,
            promo_months: int,
            balance_transfer_fee: float = 0.03,
            regular_apr: float = 0.0,
            monthly_payment: float = None
    ) -> Dict:
        """
        Calculate balance transfer strategy

        Logic:
        1. User transfers balance to 0% card
        2. Pay 0% for promo period
        3. Then regular APR kicks in
        4. Compare to current payoff strategy
        """

        # Calculate transfer fee
        transfer_fee = transfer_amount * balance_transfer_fee
        total_owed_on_card = transfer_amount + transfer_fee

        # Phase 1: 0% promo period
        remaining_balance_phase1 = total_owed_on_card

        if monthly_payment:
            # User specifies monthly payment
            months_in_phase1 = 0

            for month in range(1, promo_months + 1):
                if remaining_balance_phase1 <= 0:
                    break

                remaining_balance_phase1 -= monthly_payment
                months_in_phase1 = month
        else:
            # Calculate payment to pay off in promo period
            monthly_payment = total_owed_on_card / promo_months
            months_in_phase1 = promo_months
            remaining_balance_phase1 = 0

        # Phase 2: Regular APR (if balance remains)
        months_in_phase2 = 0
        total_interest_phase2 = 0

        if remaining_balance_phase1 > 0:
            # Balance carries over to regular APR
            current_balance = remaining_balance_phase1
            monthly_rate = regular_apr / 12

            while current_balance > 0 and months_in_phase2 < 360:
                months_in_phase2 += 1

                # Add interest
                interest = current_balance * monthly_rate
                total_interest_phase2 += interest
                current_balance += interest

                # Make payment
                if monthly_payment:
                    current_balance -= monthly_payment
                else:
                    # Pay minimally (1% of remaining balance + interest)
                    min_payment = max(interest + 10, current_balance * 0.01)
                    current_balance -= min_payment

        total_months = months_in_phase1 + months_in_phase2
        total_interest = 0 + total_interest_phase2  # Phase 1 is 0% (no interest)

        return {
            "strategy": "Balance Transfer",
            "transfer_amount": round(transfer_amount, 2),
            "transfer_fee": round(transfer_fee, 2),
            "total_owed": round(total_owed_on_card, 2),
            "monthly_payment": round(monthly_payment, 2) if monthly_payment else None,
            "promo_months": promo_months,
            "promo_apr": 0.0,
            "regular_apr": regular_apr,
            "total_months": total_months,
            "total_years": round(total_months / 12, 1),
            "total_interest": round(total_interest, 2),
            "credit_impact": "Immediate: -5 points (hard inquiry), Then: +50-100 (lower utilization)",
            "pros": [
                f"0% APR for {promo_months} months saves interest",
                "Pay only principal during promo period",
                "Lower utilization ratio improves credit"
            ],
            "cons": [
                f"{balance_transfer_fee * 100}% transfer fee upfront",
                f"Regular APR ({regular_apr * 100}%) after promo ends",
                "Hard inquiry hurts credit short-term",
                "Need good credit to qualify"
            ]
        }

    @staticmethod
    def compare_with_current_strategy(
            debts: List,
            current_monthly_payment: float,
            transfer_amount: float,
            promo_months: int,
            balance_transfer_fee: float = 0.03,
            regular_apr: float = 0.0
    ) -> Dict:
        """Compare balance transfer to current Avalanche strategy"""

        # Get current strategy
        current = StrategyService._simulate_payoff_accurate(
            debts,
            current_monthly_payment
        )

        # Get balance transfer strategy
        bt = BalanceTransferService.calculate_balance_transfer_strategy(
            debts,
            transfer_amount,
            promo_months,
            balance_transfer_fee,
            regular_apr,
            current_monthly_payment
        )

        # Compare
        interest_saved = current.get("total_interest", 0) - bt["total_interest"]
        months_saved = current.get("total_months", 0) - bt["total_months"]

        # Recommendation
        if interest_saved > 500:
            recommendation = f"Balance transfer saves ${interest_saved:.2f}! Consider it."
        elif interest_saved > 0:
            recommendation = f"Balance transfer saves some interest (${interest_saved:.2f}), but modest gain."
        else:
            recommendation = "Balance transfer doesn't save money. Stick with Avalanche."

        return {
            "current_strategy": current,
            "balance_transfer_strategy": bt,
            "interest_saved": round(interest_saved, 2),
            "months_saved": months_saved,
            "recommendation": recommendation,
            "should_use_bt": interest_saved > 200  # Threshold for recommending
        }
