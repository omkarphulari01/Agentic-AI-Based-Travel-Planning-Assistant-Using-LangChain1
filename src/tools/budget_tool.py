"""Budget Estimation Tool.

Sums flight cost + hotel cost (price_per_night x nights) + a per-day local
expense estimate (food, local transport, activities), as described in
Step 2 of the project workflow.
"""

from __future__ import annotations

from typing import Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

DEFAULT_DAILY_EXPENSE_INR = 1500.0


class BudgetEstimateInput(BaseModel):
    """Input schema for the budget estimation tool."""

    flight_price: float = Field(..., description="Round-trip or one-way flight cost in INR.")
    hotel_price_per_night: float = Field(..., description="Hotel cost per night in INR.")
    num_nights: int = Field(..., ge=1, description="Number of nights the trip lasts.")
    daily_expense_estimate: Optional[float] = Field(
        default=None,
        description="Estimated food/local-travel/activities cost per day in INR. "
        f"Defaults to {DEFAULT_DAILY_EXPENSE_INR} if not provided.",
    )
    num_travelers: int = Field(
        default=1, ge=1, description="Number of travelers to scale hotel/food costs for."
    )


@tool("estimate_budget", args_schema=BudgetEstimateInput)
def estimate_budget(
    flight_price: float,
    hotel_price_per_night: float,
    num_nights: int,
    daily_expense_estimate: Optional[float] = None,
    num_travelers: int = 1,
) -> dict:
    """Estimate total trip cost from flight, hotel, and daily-expense inputs.

    Use this tool once a flight and hotel have been selected and the trip
    length is known, to produce the 'Budget Breakdown' section of the
    itinerary. Assumes one flight ticket and one shared hotel room by
    default; pass num_travelers to scale food/local-expense costs.
    """
    if daily_expense_estimate is None:
        daily_expense_estimate = DEFAULT_DAILY_EXPENSE_INR

    flight_total = flight_price * num_travelers
    hotel_total = hotel_price_per_night * num_nights
    daily_total = daily_expense_estimate * num_nights * num_travelers
    grand_total = flight_total + hotel_total + daily_total

    return {
        "num_travelers": num_travelers,
        "num_nights": num_nights,
        "flight_cost_total": round(flight_total, 2),
        "hotel_cost_total": round(hotel_total, 2),
        "food_and_local_travel_total": round(daily_total, 2),
        "estimated_total_budget": round(grand_total, 2),
        "currency": "INR",
    }
