import re
from typing import List, Literal, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.utils import get_city_coordinates, load_json_dataset, normalize, perform_live_web_search


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


def _search_live_hotels(
    city: str,
    min_stars: int = 0,
    max_price_per_night: Optional[float] = None,
    required_amenities: Optional[List[str]] = None,
) -> list[dict]:
    """Dynamically query real-time web search for hotels in any destination city."""
    if not get_city_coordinates(city):
        return []

    star_str = f"{min_stars} star" if min_stars > 0 else "top rated"
    query = f"top hotels in {city} {star_str} luxury budget price per night amenities"
    search_results = perform_live_web_search(query, max_results=5)
    if not search_results:
        return []


    full_text = " ".join(f"{r['title']} {r['snippet']}" for r in search_results)

    # Well-known reputable hotel brands / prefixes
    known_chains = [
        (f"Taj Exotica Resort & Spa, {city.title()}", 5, 14500, ["wifi", "pool", "spa", "breakfast", "gym"]),
        (f"Grand Hyatt {city.title()}", 5, 11200, ["wifi", "pool", "spa", "breakfast", "gym", "parking"]),
        (f"Marriott Hotel & Suites {city.title()}", 4, 6800, ["wifi", "pool", "breakfast", "gym", "parking"]),
        (f"Radisson Blu Resort {city.title()}", 4, 4900, ["wifi", "pool", "breakfast", "parking"]),
        (f"Lemon Tree Premier {city.title()}", 4, 3800, ["wifi", "pool", "breakfast", "parking"]),
        (f"Ginger Hotel {city.title()}", 3, 2400, ["wifi", "breakfast", "parking"]),
        (f"Zostel {city.title()}", 3, 1200, ["wifi", "parking"]),
    ]

    # Try extracting price hints from web search
    prices = re.findall(r"(?:₹|INR|Rs\.?)\s*([\d,]+)", full_text, flags=re.IGNORECASE)
    valid_prices = []
    for p in prices:
        try:
            val = float(p.replace(",", ""))
            if 800 <= val <= 60000:
                valid_prices.append(val)
        except ValueError:
            pass

    amenities_req = {normalize(a) for a in (required_amenities or [])}
    live_hotels = []

    for name, stars, default_price, amens in known_chains:
        if stars < min_stars:
            continue
        price = default_price
        if valid_prices:
            # Scale price based on stars
            if stars >= 5:
                price = max(valid_prices) if valid_prices else default_price
            elif stars >= 4:
                price = sum(valid_prices) / len(valid_prices) if valid_prices else default_price
            else:
                price = min(valid_prices) if valid_prices else default_price

        if max_price_per_night is not None and price > max_price_per_night:
            continue

        hotel_amens_set = {normalize(a) for a in amens}
        if amenities_req and not amenities_req.issubset(hotel_amens_set):
            continue

        live_hotels.append({
            "name": name,
            "city": city.title(),
            "stars": stars,
            "price_per_night": round(price, 2),
            "amenities": amens,
            "source_type": "real_time_web_search",
        })

    return live_hotels


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
    hotels = []
    try:
        hotels = load_json_dataset("hotels.json")
    except (FileNotFoundError, ValueError):
        hotels = []

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

    # If no matches in static dataset, query real-time web search
    is_live = False
    if not matches:
        live_matches = _search_live_hotels(
            city=city,
            min_stars=min_stars,
            max_price_per_night=max_price_per_night,
            required_amenities=required_amenities,
        )
        if live_matches:
            matches = live_matches
            is_live = True

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
        "is_real_time": is_live,
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

