"""Places / POI Discovery Tool.

Reads places.json and recommends attractions filtered by city, type, and
minimum rating (Step 2 of the project workflow).
"""

from __future__ import annotations

from typing import Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.utils import load_json_dataset, normalize


class PlacesSearchInput(BaseModel):
    """Input schema for the places discovery tool."""

    city: str = Field(..., description="City to find attractions in, e.g. 'Goa'")
    place_type: Optional[str] = Field(
        default=None,
        description="Optional category filter, e.g. 'beach', 'fort', 'temple', "
        "'museum', 'park', 'market', 'lake', 'monument'.",
    )
    min_rating: float = Field(
        default=0.0, ge=0.0, le=5.0, description="Minimum rating out of 5."
    )
    max_results: int = Field(default=10, ge=1, le=40)


@tool("search_places", args_schema=PlacesSearchInput)
def search_places(
    city: str,
    place_type: Optional[str] = None,
    min_rating: float = 0.0,
    max_results: int = 10,
) -> dict:
    """Discover top-rated attractions/POIs in a city for building an itinerary.

    Use this tool once the destination is known, to pick attractions for
    each day of the trip. Results are sorted by rating (highest first).
    """
    try:
        places = load_json_dataset("places.json")
    except (FileNotFoundError, ValueError) as exc:
        return {"error": str(exc)}

    city_norm = normalize(city)
    type_norm = normalize(place_type) if place_type else None

    matches = [
        p for p in places
        if normalize(p.get("city", "")) == city_norm
        and p.get("rating", 0) >= min_rating
        and (type_norm is None or normalize(p.get("type", "")) == type_norm)
    ]

    if not matches:
        return {
            "error": (
                f"No places found in '{city}' matching the given filters. "
                "Try removing the place_type filter or lowering min_rating."
            ),
            "results": [],
        }

    matches.sort(key=lambda p: p.get("rating", 0), reverse=True)
    top = matches[:max_results]

    return {
        "city": city,
        "filters": {"place_type": place_type, "min_rating": min_rating},
        "count": len(top),
        "results": top,
    }
