from typing import List, Dict
from app.schemas.spending import (
    SpendingCategory, BudgetCategory, BudgetRecommendation,
    SpendingBreakdown, UserSpendingAnalysis, SavingsPotential,
    SavingsPotentialAnalysis, SpendingEstimate
)


class SpendingService:
    """Business logic for spending analysis and budgeting"""

    # 50/30/20 Rule: 50% needs, 30% wants, 20% savings+debt
    BUDGET_50_30_20 = {
        "needs": 0.50,
        "wants": 0.30,
        "savings_debt": 0.20
    }

    # Category mappings
    NEEDS_CATEGORIES = [
        SpendingCategory.HOUSING,
        SpendingCategory.UTILITIES,
        SpendingCategory.GROCERIES,
        SpendingCategory.TRANSPORTATION,
        SpendingCategory.INSURANCE,
        SpendingCategory.HEALTHCARE
    ]

    WANTS_CATEGORIES = [
        SpendingCategory.DINING,
        SpendingCategory.ENTERTAINMENT,
        SpendingCategory.SHOPPING,
        SpendingCategory.SUBSCRIPTIONS,
        SpendingCategory.PERSONAL_CARE
    ]

    DEBT_SAVINGS_CATEGORIES = [
        SpendingCategory.DEBT_PAYMENTS,
        SpendingCategory.SAVINGS
    ]

    @staticmethod
    def get_budget_recommendation(monthly_income: float) -> BudgetRecommendation:
        """
        Generate budget recommendation using 50/30/20 rule
        50% needs (housing, utilities, groceries)
        30% wants (dining, entertainment, shopping)
        20% savings + debt payoff
        """

        needs_budget = monthly_income * SpendingService.BUDGET_50_30_20["needs"]
        wants_budget = monthly_income * SpendingService.BUDGET_50_30_20["wants"]
        savings_debt_budget = monthly_income * SpendingService.BUDGET_50_30_20["savings_debt"]

        # Detailed categories
        categories = [
            BudgetCategory(
                category=SpendingCategory.HOUSING,
                recommended_amount=monthly_income * 0.28,
                recommended_percentage=28,
                notes="Mortgage/rent should be ~28% of income"
            ),
            BudgetCategory(
                category=SpendingCategory.UTILITIES,
                recommended_amount=monthly_income * 0.08,
                recommended_percentage=8,
                notes="Gas, electric, water, internet"
            ),
            BudgetCategory(
                category=SpendingCategory.TRANSPORTATION,
                recommended_amount=monthly_income * 0.10,
                recommended_percentage=10,
                notes="Car payment, gas, insurance, public transit"
            ),
            BudgetCategory(
                category=SpendingCategory.GROCERIES,
                recommended_amount=monthly_income * 0.06,
                recommended_percentage=6,
                notes="Food shopping (not restaurants)"
            ),
            BudgetCategory(
                category=SpendingCategory.INSURANCE,
                recommended_amount=monthly_income * 0.04,
                recommended_percentage=4,
                notes="Health, auto, renters insurance"
            ),
            BudgetCategory(
                category=SpendingCategory.DINING,
                recommended_amount=monthly_income * 0.10,
                recommended_percentage=10,
                notes="Restaurants, food delivery"
            ),
            BudgetCategory(
                category=SpendingCategory.ENTERTAINMENT,
                recommended_amount=monthly_income * 0.10,
                recommended_percentage=10,
                notes="Movies, games, hobbies"
            ),
            BudgetCategory(
                category=SpendingCategory.SHOPPING,
                recommended_amount=monthly_income * 0.05,
                recommended_percentage=5,
                notes="Clothes, non-essentials"
            ),
            BudgetCategory(
                category=SpendingCategory.SUBSCRIPTIONS,
                recommended_amount=monthly_income * 0.03,
                recommended_percentage=3,
                notes="Netflix, gym, software"
            ),
            BudgetCategory(
                category=SpendingCategory.DEBT_PAYMENTS,
                recommended_amount=savings_debt_budget * 0.70,
                recommended_percentage=14,
                notes="Debt payoff (aggressive)"
            ),
            BudgetCategory(
                category=SpendingCategory.SAVINGS,
                recommended_amount=savings_debt_budget * 0.30,
                recommended_percentage=6,
                notes="Emergency fund, retirement"
            ),
        ]

        return BudgetRecommendation(
            monthly_income=monthly_income,
            budget_model="50/30/20",
            needs_budget=round(needs_budget, 2),
            needs_percentage=50,
            wants_budget=round(wants_budget, 2),
            wants_percentage=30,
            savings_debt_budget=round(savings_debt_budget, 2),
            savings_debt_percentage=20,
            categories=categories,
            notes="This follows the proven 50/30/20 budgeting rule for financial health"
        )

    @staticmethod
    def estimate_spending(monthly_income: float) -> SpendingEstimate:
        """
        Estimate monthly spending based on income
        Uses average percentages for typical household
        """

        return SpendingEstimate(
            monthly_income=monthly_income,
            estimated_housing=round(monthly_income * 0.28, 2),
            estimated_utilities=round(monthly_income * 0.08, 2),
            estimated_transportation=round(monthly_income * 0.10, 2),
            estimated_groceries=round(monthly_income * 0.06, 2),
            estimated_dining=round(monthly_income * 0.10, 2),
            estimated_entertainment=round(monthly_income * 0.08, 2),
            estimated_subscriptions=round(monthly_income * 0.03, 2),
            estimated_other=round(monthly_income * 0.07, 2),
            total_estimated=round(monthly_income * 0.80, 2),
            remaining_for_debt=round(monthly_income * 0.20, 2),
            recommended_debt_payment=round(monthly_income * 0.15, 2)
        )

    @staticmethod
    def analyze_user_spending(
            monthly_income: float,
            spending_by_category: Dict[str, float]
    ) -> UserSpendingAnalysis:
        """
        Analyze user's actual spending against income
        """

        total_spending = sum(spending_by_category.values())
        spending_percentage = (total_spending / monthly_income * 100) if monthly_income > 0 else 0

        # Get recommendation
        recommendation = SpendingService.get_budget_recommendation(monthly_income)

        # Build breakdown
        breakdown = []
        for category_str, amount in spending_by_category.items():
            try:
                category = SpendingCategory(category_str)

                # Find recommended amount
                recommended = next(
                    (c.recommended_amount for c in recommendation.categories if c.category == category),
                    amount
                )

                percentage = (amount / monthly_income * 100) if monthly_income > 0 else 0
                vs_recommended = amount - recommended

                status = "Good" if vs_recommended <= 0 else "Over"

                breakdown.append(SpendingBreakdown(
                    category=category,
                    amount=round(amount, 2),
                    percentage=round(percentage, 1),
                    vs_recommended=round(vs_recommended, 2),
                    status=status
                ))
            except ValueError:
                continue

        # Calculate spending types
        discretionary = sum(
            spending_by_category.get(cat.value, 0)
            for cat in SpendingService.WANTS_CATEGORIES
        )
        essential = sum(
            spending_by_category.get(cat.value, 0)
            for cat in SpendingService.NEEDS_CATEGORIES
        )
        debt = sum(
            spending_by_category.get(cat.value, 0)
            for cat in SpendingService.DEBT_SAVINGS_CATEGORIES
        )

        return UserSpendingAnalysis(
            monthly_income=monthly_income,
            total_monthly_spending=round(total_spending, 2),
            spending_percentage=round(spending_percentage, 1),
            remaining_after_spending=round(monthly_income - total_spending, 2),
            discretionary_spending=round(discretionary, 2),
            essential_spending=round(essential, 2),
            debt_payments=round(debt, 2),
            breakdown_by_category=breakdown
        )

    @staticmethod
    def calculate_savings_potential(
            monthly_income: float,
            spending_by_category: Dict[str, float]
    ) -> SavingsPotentialAnalysis:
        """
        Calculate where user can save money
        """

        recommendation = SpendingService.get_budget_recommendation(monthly_income)

        opportunities = []
        total_potential = 0

        for rec_category in recommendation.categories:
            actual_spending = spending_by_category.get(rec_category.category.value, 0)
            recommended = rec_category.recommended_amount

            if actual_spending > recommended:
                savings = actual_spending - recommended
                total_potential += savings

                # Determine difficulty
                if rec_category.category in [SpendingCategory.SHOPPING, SpendingCategory.ENTERTAINMENT]:
                    difficulty = "Easy"
                    tips = [
                        f"Cut {rec_category.category.value} from ${actual_spending:.2f} to ${recommended:.2f}",
                        "This is discretionary spending - easiest to cut",
                        f"Potential savings: ${savings:.2f}/month or ${savings * 12:.2f}/year"
                    ]
                elif rec_category.category in [SpendingCategory.DINING, SpendingCategory.SUBSCRIPTIONS]:
                    difficulty = "Medium"
                    tips = [
                        f"Reduce {rec_category.category.value} from ${actual_spending:.2f} to ${recommended:.2f}",
                        "Look for free alternatives or negotiate better rates",
                        f"Potential savings: ${savings:.2f}/month"
                    ]
                else:
                    difficulty = "Hard"
                    tips = [
                        f"Reducing {rec_category.category.value} is challenging",
                        "Consider larger changes (move, job change, etc)",
                        f"Limited savings potential: ${savings:.2f}/month"
                    ]

                opportunities.append(SavingsPotential(
                    category=rec_category.category,
                    current_spending=round(actual_spending, 2),
                    recommended_spending=round(recommended, 2),
                    potential_savings=round(savings, 2),
                    savings_percentage=round(savings / actual_spending * 100, 1) if actual_spending > 0 else 0,
                    difficulty=difficulty,
                    tips=tips
                ))

        # Sort by potential savings (highest first)
        opportunities.sort(key=lambda x: x.potential_savings, reverse=True)

        total_current = sum(spending_by_category.values())
        total_recommended = sum(c.recommended_amount for c in recommendation.categories)

        impact_months = int(total_potential * 12 / total_potential) if total_potential > 0 else 0

        return SavingsPotentialAnalysis(
            total_current_spending=round(total_current, 2),
            total_recommended_spending=round(total_recommended, 2),
            total_potential_savings=round(total_potential, 2),
            savings_percentage=round(total_potential / total_current * 100, 1) if total_current > 0 else 0,
            top_savings_opportunities=opportunities[:5],  # Top 5 opportunities
            monthly_recommendation=f"You could save ${total_potential:.2f}/month by following the 50/30/20 budget",
            impact_on_debt_payoff=f"${total_potential:.2f}/month extra could pay off your debt {int(total_potential / 100)} months faster" if total_potential > 0 else "No significant savings found"
        )
