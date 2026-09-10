"""Flight Search Tool.

Reads flights.json, filters by source -> destination, and can suggest the
cheapest or fastest option as described in the project workflow (Step 2).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.utils import load_json_dataset, normalize


class FlightSearchInput(BaseModel):
    """Input schema for the flight search tool."""

    source: str = Field(..., description="Departure city, e.g. 'Delhi'")
    destination: str = Field(..., description="Arrival city, e.g. 'Goa'")
    sort_by: Literal["price", "duration"] = Field(
        default="price",
        description="Rank results by 'price' (cheapest first) or "
        "'duration' (fastest first).",
    )
    max_results: int = Field(
        default=5, ge=1, le=30, description="Maximum number of flights to return."
    )


def _flight_duration_minutes(flight: dict) -> float:
    """Compute flight duration in minutes from ISO timestamps."""
    try:
        dep = datetime.fromisoformat(flight["departure_time"])
        arr = datetime.fromisoformat(flight["arrival_time"])
        return (arr - dep).total_seconds() / 60.0
    except (KeyError, ValueError):
        return float("inf")


@tool("search_flights", args_schema=FlightSearchInput)
def search_flights(
    source: str,
    destination: str,
    sort_by: str = "price",
    max_results: int = 5,
) -> dict:
    """Search available flights between two cities and rank them.

    Use this tool whenever the user needs to travel from one city to
    another. It filters the flights dataset by exact source/destination
    match (case-insensitive) and sorts by cheapest price or shortest
    duration.
    """
    try:
        flights = load_json_dataset("flights.json")
    except (FileNotFoundError, ValueError) as exc:
        return {"error": str(exc)}

    src, dst = normalize(source), normalize(destination)
    matches = [
        f for f in flights
        if normalize(f.get("from", "")) == src and normalize(f.get("to", "")) == dst
    ]

    if not matches:
        return {
            "error": (
                f"No direct flights found from '{source}' to '{destination}'. "
                "Try checking city spelling or consider a connecting route."
            ),
            "results": [],
        }

    for f in matches:
        f["duration_minutes"] = _flight_duration_minutes(f)

    if sort_by == "duration":
        matches.sort(key=lambda f: f["duration_minutes"])
    else:
        matches.sort(key=lambda f: f.get("price", float("inf")))

    top = matches[:max_results]
    return {
        "source": source,
        "destination": destination,
        "sort_by": sort_by,
        "count": len(top),
        "results": top,
        "cheapest": min(matches, key=lambda f: f.get("price", float("inf"))),
        "fastest": min(matches, key=lambda f: f["duration_minutes"]),
    }
