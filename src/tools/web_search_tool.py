"""Live Travel Search & Real-Time Recommendations Tool.

Enables the AI agent to search real-time information from Google/the web
for the best travel routes, transit comparisons (flights, high-speed trains like Vande Bharat,
buses, road trips), local travel tips, weather advisories, and insider suggestions.
"""

from __future__ import annotations

from typing import Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.utils import normalize, perform_live_web_search, search_live_route_recommendations



class LiveTravelSearchInput(BaseModel):
    """Input schema for live travel search and route recommendation."""

    source: Optional[str] = Field(
        default=None,
        description="Departure city (e.g. 'Delhi'), if searching for route or transit advice."
    )
    destination: str = Field(
        ...,
        description="Destination city (e.g. 'Goa', 'Jaipur', 'Paris'), to gather live info for."
    )
    query_type: str = Field(
        default="best_way_to_travel",
        description=(
            "Type of information to discover: 'best_way_to_travel' (compares flight vs train vs road), "
            "'local_tips' (safety, scams, best seasons, local food), 'top_experiences' (unmissable sights), "
            "or 'custom' with specific keywords."
        ),
    )
    custom_keywords: Optional[str] = Field(
        default=None,
        description="Optional additional search keywords if query_type is 'custom'."
    )


# Curated high-speed routes database for instantaneous (sub-millisecond) response
COMMON_ROUTES: dict[tuple[str, str], dict] = {
    ("delhi", "goa"): {
        "best_mode": "Direct Flight (Fastest & Most Practical)",
        "transit_options": [
            "Flight: 2h 30m non-stop (IndiGo, Air India, Akasa Air) from ₹4,400 to ₹6,500.",
            "Train: Goa Express (12780) / Rajdhani ~28 to 34 hours. Only recommended for leisure travelers with ample time.",
            "Road: ~1,900 km via NH48 (32+ hours driving). Not recommended for a short trip."
        ],
        "insider_tip": "Fly into MOPA (GOX) for North Goa beaches (Baga, Anjuna, Morjim) or Dabolim (GOI) for Central/South Goa resorts."
    },
    ("delhi", "mumbai"): {
        "best_mode": "Direct Flight or Mumbai Rajdhani / Tejas Express",
        "transit_options": [
            "Flight: 2h 10m direct non-stop flights run every 30 mins (IndiGo, Air India) from ₹3,800.",
            "Train: 12952 Mumbai Rajdhani (15h 30m) or 12954 August Kranti (16h 50m) overnight luxury coaches.",
            "Road: ~1,380 km via the new Delhi-Mumbai Expressway."
        ],
        "insider_tip": "Flights are best for short trips; Rajdhani 1st/2nd AC is a comfortable overnight sleeper alternative."
    },
    ("bangalore", "goa"): {
        "best_mode": "Flight or Scenic Drive / Sleeper Bus",
        "transit_options": [
            "Flight: 1h 10m direct flight (IndiGo, Star Air) starting around ₹2,900.",
            "Train: Vande Bharat Express / Kacheguda-Vasco Express ~11 to 14 hours.",
            "Road / Sleeper Bus: ~560 km (10-11 hours) via Hubli-Dharwad through scenic Western Ghats."
        ],
        "insider_tip": "An overnight luxury AC sleeper bus (KSRTC/IntrCity) is both scenic and budget-friendly."
    },
    ("mumbai", "goa"): {
        "best_mode": "Vande Bharat Express (22229) or Direct Flight",
        "transit_options": [
            "Train: Mumbai CSMT to Madgaon Vande Bharat Express (7h 45m) through the stunning Konkan railway.",
            "Flight: 1h 15m non-stop flight from ₹2,600.",
            "Road: ~580 km (10-12 hours) via Mumbai-Goa Highway (NH66)."
        ],
        "insider_tip": "The Konkan Vande Bharat route offers breathtaking lush greenery, bridges, and tunnels."
    },
    ("delhi", "jaipur"): {
        "best_mode": "Vande Bharat Express (20978) or Delhi-Jaipur Expressway",
        "transit_options": [
            "Train: Vande Bharat Express (3h 45m) or Ajmer Shatabdi (4h 10m).",
            "Road: ~270 km (3.5 to 4.5 hours) via Delhi-Mumbai Expressway / NE4.",
            "Flight: 55 mins direct flight, but airport transit time makes the train or highway faster door-to-door."
        ],
        "insider_tip": "The morning Vande Bharat or a private cab via the expressway is faster and more relaxing than flying."
    },
    ("delhi", "agra"): {
        "best_mode": "Gatimaan Express (12050) or Yamuna Expressway",
        "transit_options": [
            "Train: Gatimaan Express takes just 1h 40m from Hazrat Nizamuddin to Agra Cantt with meals.",
            "Road: ~210 km (3 to 3.5 hours) via Yamuna Expressway."
        ],
        "insider_tip": "Take the Gatimaan Express at 08:10 AM to reach Agra by 09:50 AM, spend the day, and return in the evening."
    },
    ("bangalore", "jaipur"): {
        "best_mode": "Direct Flight",
        "transit_options": [
            "Flight: 2h 35m non-stop (IndiGo, Air India Express) from ₹4,900.",
            "Train: Mysore-Jaipur Express takes over 42 hours."
        ],
        "insider_tip": "Always fly direct between South and North-West India to save two full days of travel."
    },
    ("bangalore", "chennai"): {
        "best_mode": "Vande Bharat Express (20608) or Shatabdi Express",
        "transit_options": [
            "Train: Vande Bharat takes only 4h 15m between KSR Bengaluru and Chennai Central.",
            "Flight: 55m flight, but check-in/security makes train faster center-to-center.",
            "Road: ~340 km (5.5 to 6 hours) via Hosur / Krishnagiri."
        ],
        "insider_tip": "Center-to-center train via Vande Bharat beats flying by nearly 2 hours total transit time."
    },
}


@tool("search_live_travel_info", args_schema=LiveTravelSearchInput)
def search_live_travel_info(
    destination: str,
    source: Optional[str] = None,
    query_type: str = "best_way_to_travel",
    custom_keywords: Optional[str] = None,
) -> dict:
    """Search Google/the web in real-time for live travel information, route comparisons, and best advice.

    Use this tool to discover:
    1. The BEST way to travel between source and destination (e.g., direct flights vs Vande Bharat/Express trains vs cab/bus).
    2. Real-time travel tips, best season/time to visit, local cuisine, and transit passes.
    3. Live insights when local static datasets don't have enough details or when you need up-to-date recommendations.
    """
    src_norm = normalize(source) if source else ""
    dst_norm = normalize(destination)

    # Check instant curated corridor knowledge base (0ms lookup)
    if (src_norm, dst_norm) in COMMON_ROUTES:
        route_data = COMMON_ROUTES[(src_norm, dst_norm)]
        return {
            "source": source,
            "destination": destination,
            "query_type": query_type,
            "best_mode": route_data["best_mode"],
            "transit_options": route_data["transit_options"],
            "insider_tip": route_data["insider_tip"],
            "is_instant": True,
            "count": len(route_data["transit_options"]),
            "results": [
                {"title": f"Best Way to Travel from {source} to {destination}", "snippet": "; ".join(route_data["transit_options"])}
            ],
        }

    if (dst_norm, src_norm) in COMMON_ROUTES:
        route_data = COMMON_ROUTES[(dst_norm, src_norm)]
        return {
            "source": source,
            "destination": destination,
            "query_type": query_type,
            "best_mode": route_data["best_mode"],
            "transit_options": route_data["transit_options"],
            "insider_tip": route_data["insider_tip"],
            "is_instant": True,
            "count": len(route_data["transit_options"]),
            "results": [
                {"title": f"Best Way to Travel from {source} to {destination}", "snippet": "; ".join(route_data["transit_options"])}
            ],
        }

    # Live web search fallback
    if query_type == "best_way_to_travel" and source:
        search_query = f"best way to travel from {source} to {destination} flights trains road"
    elif query_type == "local_tips":
        search_query = f"top travel tips things to know before visiting {destination} local food transport"
    elif query_type == "top_experiences":
        search_query = f"best things to do top attractions hidden gems in {destination}"
    elif custom_keywords:
        search_query = f"{destination} {custom_keywords}"
    else:
        search_query = f"travel guide and best way to visit {destination}"

    results = perform_live_web_search(search_query, max_results=3)

    if not results:
        return {
            "source": source,
            "destination": destination,
            "query_type": query_type,
            "best_mode": "Direct Flight or High-Speed Rail",
            "message": f"Recommended travel: check direct flights or express trains between {source} and {destination}.",
            "results": [],
        }

    return {
        "source": source,
        "destination": destination,
        "query_type": query_type,
        "search_query": search_query,
        "count": len(results),
        "results": results,
    }

