from __future__ import annotations

from math import pow
from typing import Dict


def monthly_mortgage_payment(principal: float, annual_rate: float, years: int) -> float:
    r = (annual_rate / 100) / 12
    n = years * 12
    if r == 0:
        return principal / n
    factor = pow(1 + r, n)
    return principal * (r * factor) / (factor - 1)


def heuristic_affordability(
    annual_income: float,
    monthly_debt: float,
    down_payment: float,
    interest_rate: float,
    loan_term_years: int,
) -> Dict:
    monthly_income = annual_income / 12
    # Conservative DTI target for housing+debt.
    target_total_dti = 0.43
    max_housing_payment = max((monthly_income * target_total_dti) - monthly_debt, 0)

    if max_housing_payment <= 0:
        return {
            "max_affordable_home_price": int(max(down_payment, 0)),
            "estimated_monthly_payment_limit": 0,
            "debt_to_income_ratio": round((monthly_debt / monthly_income) if monthly_income else 1, 3),
            "confidence": "medium",
            "rationale": "Existing debt already consumes conservative DTI limits.",
        }

    low, high = 50000.0, 2500000.0
    for _ in range(40):
        mid = (low + high) / 2
        principal = max(mid - down_payment, 0)
        pmt = monthly_mortgage_payment(principal, interest_rate, loan_term_years)
        # Add coarse tax/insurance reserve.
        all_in = pmt + (mid * 0.0012)
        if all_in <= max_housing_payment:
            low = mid
        else:
            high = mid

    max_price = int(low)
    dti = (monthly_debt + max_housing_payment) / monthly_income if monthly_income else 1
    return {
        "max_affordable_home_price": max_price,
        "estimated_monthly_payment_limit": int(max_housing_payment),
        "debt_to_income_ratio": round(dti, 3),
        "confidence": "medium",
        "rationale": "Heuristic used 43% total DTI with a tax/insurance reserve.",
    }
