"""Lightweight tests for the deterministic (non-LLM) tools.

These don't require an API key and can run in any environment, verifying
the core data-filtering logic described in the project workflow.

Run with:  python -m pytest tests/ -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.tools.flight_tool import search_flights
from src.tools.hotel_tool import search_hotels
from src.tools.places_tool import search_places
from src.tools.budget_tool import estimate_budget
from src.agent import _extract_text


def test_search_flights_finds_known_route():
    result = search_flights.invoke(
        {"source": "Hyderabad", "destination": "Delhi", "sort_by": "price"}
    )
    assert "error" not in result
    assert result["count"] >= 1
    assert all(f["from"] == "Hyderabad" for f in result["results"])


def test_search_flights_unknown_route_returns_error():
    result = search_flights.invoke({"source": "Atlantis", "destination": "Narnia"})
    assert "error" in result
    assert result["results"] == []


def test_search_hotels_filters_by_city_and_stars():
    result = search_hotels.invoke({"city": "Goa", "min_stars": 4})
    assert "error" not in result
    assert all(h["stars"] >= 4 for h in result["results"])
    assert all(h["city"] == "Goa" for h in result["results"])


def test_search_hotels_amenity_filter():
    result = search_hotels.invoke({"city": "Goa", "required_amenities": ["spa", "pool"]})
    assert "error" not in result
    for h in result["results"]:
        amenities = {a.lower() for a in h["amenities"]}
        assert {"spa", "pool"}.issubset(amenities)


def test_search_places_by_type_and_rating():
    result = search_places.invoke({"city": "Goa", "min_rating": 4.0})
    assert "error" not in result
    assert all(p["rating"] >= 4.0 for p in result["results"])


def test_estimate_budget_math():
    result = estimate_budget.invoke(
        {
            "flight_price": 4800,
            "hotel_price_per_night": 3200,
            "num_nights": 2,
            "daily_expense_estimate": 1250,
            "num_travelers": 1,
        }
    )
    assert result["flight_cost_total"] == 4800
    assert result["hotel_cost_total"] == 6400
    assert result["food_and_local_travel_total"] == 2500
    assert result["estimated_total_budget"] == 13700


def test_extract_text_handles_plain_string():
    assert _extract_text("Hello world") == "Hello world"


def test_extract_text_handles_gemini_style_content_blocks():
    """Regression test: Gemini (and some other providers) can return
    AIMessage.content as a list of blocks instead of a plain string,
    which previously crashed the Streamlit app's regex parser with
    'TypeError: expected string or bytes-like object, got list'.
    """
    blocks = [{"type": "text", "text": "Hello "}, {"type": "text", "text": "world"}]
    assert _extract_text(blocks) == "Hello world"


def test_extract_text_skips_non_text_blocks():
    blocks = [{"type": "text", "text": "Answer: 42"}, {"type": "executable_code", "code": "x=1"}]
    assert _extract_text(blocks) == "Answer: 42"


def test_extract_text_handles_empty_and_none():
    assert _extract_text([]) == ""
    assert _extract_text(None) == ""


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))
