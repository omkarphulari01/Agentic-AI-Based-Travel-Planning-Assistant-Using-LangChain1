"""Hotel Recommendation Tool.

Reads hotels.json and filters by city, minimum star rating, maximum
nightly price, and desired amenities (Step 2 of the project workflow).
"""

from __future__ import annotations

from typing import List, Literal, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.utils import load_json_dataset, normalize


class HotelSearchInput(BaseModel):
    """Input schema for the hotel recommendation tool."""

    city: str = Field(..., description="City to search hotels in, e.g. 'Goa'")
    min_stars: int = Field(
        default=0, ge=0, le=5, description="Minimum star rating (0-5)."
    )
    max_price_per_night: Optional[float] = Field(
        default=None, description="Optional maximum nightly price in INR."
    )
    required_amenities: Optional[List[str]] = Field(
        default=None,
        description="Optional list of amenities that must all be present, "
        "e.g. ['wifi', 'pool'].",
    )
    sort_by: Literal["price", "stars"] = Field(
        default="price",
        description="Rank results by 'price' (cheapest first) or "
        "'stars' (highest rated first).",
    )
    max_results: int = Field(default=5, ge=1, le=30)


@tool("search_hotels", args_schema=HotelSearchInput)
def search_hotels(
    city: str,
    min_stars: int = 0,
    max_price_per_night: Optional[float] = None,
    required_amenities: Optional[List[str]] = None,
    sort_by: str = "price",
    max_results: int = 5,
) -> dict:
    """Find and rank hotels in a given city.

    Use this tool to recommend accommodation once the destination city is
    known. Supports filtering by star rating, nightly budget, and required
    amenities (wifi, pool, gym, spa, breakfast, parking).
    """
    try:
        hotels = load_json_dataset("hotels.json")
    except (FileNotFoundError, ValueError) as exc:
        return {"error": str(exc)}

    city_norm = normalize(city)
    amenities_required = {normalize(a) for a in (required_amenities or [])}

    matches = []
    for h in hotels:
        if normalize(h.get("city", "")) != city_norm:
            continue
        if h.get("stars", 0) < min_stars:
            continue
        if max_price_per_night is not None and h.get("price_per_night", 0) > max_price_per_night:
            continue
        hotel_amenities = {normalize(a) for a in h.get("amenities", [])}
        if amenities_required and not amenities_required.issubset(hotel_amenities):
            continue
        matches.append(h)

    if not matches:
        return {
            "error": (
                f"No hotels found in '{city}' matching the given filters. "
                "Try relaxing star rating, budget, or amenity requirements."
            ),
            "results": [],
        }

    if sort_by == "stars":
        matches.sort(key=lambda h: (-h.get("stars", 0), h.get("price_per_night", 0)))
    else:
        matches.sort(key=lambda h: h.get("price_per_night", float("inf")))

    top = matches[:max_results]
    return {
        "city": city,
        "filters": {
            "min_stars": min_stars,
            "max_price_per_night": max_price_per_night,
            "required_amenities": required_amenities,
        },
        "count": len(top),
        "results": top,
        "cheapest": min(matches, key=lambda h: h.get("price_per_night", float("inf"))),
        "best_rated": max(matches, key=lambda h: h.get("stars", 0)),
    }
