"""Vercel Python WSGI / ASGI Serverless Entrypoint.

Handles /api and /api/plan requests with full WSGI compliance, CORS support,
and automated trip planning using LangChain and Google Gemini.
"""

from __future__ import annotations

import io
import json
import logging
import os
import re
import sys

# Ensure project root is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv
load_dotenv()

from src.agent import plan_trip
from src.services.booking_service import generate_booking_links
from src.utils import get_city_coordinates

logger = logging.getLogger(__name__)


def _extract_hotel_and_places(itinerary_text: str, destination: str) -> tuple[str, list[dict]]:
    """Extract hotel name and sightseeing places from itinerary markdown."""
    hotel_name = f"Recommended Hotel in {destination.title()}"
    hotel_match = re.search(r"(?:Hotel|Stay|Accommodation)[:\s*]+([^\n\r,]+)", itinerary_text, re.IGNORECASE)
    if hotel_match:
        cand = hotel_match.group(1).strip(" *`_")
        if len(cand) > 3 and "search" not in cand.lower():
            hotel_name = cand

    # Extract day-by-day sightseeing spots
    attractions = []
    lines = itinerary_text.splitlines()
    current_day = "Day 1"
    for line in lines:
        day_m = re.search(r"(\bDay\s*\d+\b)", line, re.IGNORECASE)
        if day_m:
            current_day = day_m.group(1).title()

        spot_m = re.search(
            r"^[\s*\-•]+\s*([A-Za-z0-9\s']+(?:Fort|Beach|Temple|Palace|Market|Museum|Sanctuary|Falls|Garden|Lake|Point|Caves|Ghat|Bazaar))",
            line,
            re.IGNORECASE,
        )
        if spot_m:
            spot_name = spot_m.group(1).strip(" *`_")
            if spot_name and spot_name not in [a["name"] for a in attractions]:
                attractions.append({
                    "day": current_day,
                    "name": spot_name,
                    "detail": line.strip(" *`#-•"),
                })

    if not attractions:
        default_spots = [
            f"Historic Heritage Walk in {destination.title()}",
            f"Scenic Viewpoint / Beach in {destination.title()}",
            f"Famous Cultural Site & Architecture",
            f"Vibrant Local Market & Food Street",
        ]
        for i, s in enumerate(default_spots, 1):
            attractions.append({
                "day": f"Day {min(i, 3)}",
                "name": s,
                "detail": f"Must-see local attraction during your visit to {destination.title()}",
            })

    return hotel_name, attractions[:8]


def app(environ: dict, start_response) -> list[bytes]:
    """Standard WSGI Application Callable for Vercel Functions."""
    method = environ.get("REQUEST_METHOD", "GET").upper()

    cors_headers = [
        ("Content-Type", "application/json"),
        ("Access-Control-Allow-Origin", "*"),
        ("Access-Control-Allow-Methods", "POST, GET, OPTIONS"),
        ("Access-Control-Allow-Headers", "Content-Type, Authorization"),
    ]

    # 1. CORS Pre-flight
    if method == "OPTIONS":
        start_response("200 OK", cors_headers)
        return [b'{"status":"ok"}']

    # 2. Health check GET
    if method == "GET":
        start_response("200 OK", cors_headers)
        return [json.dumps({"status": "running", "service": "travel-planner-api"}).encode("utf-8")]

    # 3. Trip Planning POST
    if method == "POST":
        try:
            try:
                content_length = int(environ.get("CONTENT_LENGTH", 0))
            except (ValueError, TypeError):
                content_length = 0

            wsgi_input = environ.get("wsgi.input")
            if wsgi_input and content_length > 0:
                raw_body = wsgi_input.read(content_length).decode("utf-8")
                payload = json.loads(raw_body) if raw_body.strip() else {}
            else:
                payload = {}

            origin = payload.get("origin", "").strip() or "Delhi"
            destination = payload.get("destination", "").strip() or "Goa"
            start_date = payload.get("start_date", "").strip() or "2026-03-15"
            end_date = payload.get("end_date", "").strip() or "2026-03-18"
            budget = payload.get("budget", 25000)
            travelers = payload.get("travelers", 1)
            transport_mode = payload.get("transport_mode", "All Options (Recommended)")
            interests = payload.get("interests", "Beaches, Sightseeing, Local Food")

            # Construct query prompt
            query = (
                f"Plan a realistic trip from {origin} to {destination} from {start_date} to {end_date} "
                f"for {travelers} traveler(s) with total budget INR {budget}. "
                f"Transportation Mode Preference: {transport_mode}. "
                f"Interests: {interests}. "
                f"Provide flight/train/bus transit options, hotel recommendation, daily schedule, and cost breakdown."
            )

            # Generate plan using agentic reasoning with automatic key rotation
            itinerary = plan_trip(query)

            # Generate 1-click booking links
            booking_links = generate_booking_links(
                source=origin,
                destination=destination,
                start_date=start_date,
                end_date=end_date,
            )

            # Resolve coordinates for Leaflet map
            src_coords = get_city_coordinates(origin) or (28.6139, 77.2090)
            dst_coords = get_city_coordinates(destination) or (15.2993, 74.1240)

            hotel_name, attractions = _extract_hotel_and_places(itinerary, destination)

            hotel_data = {
                "name": hotel_name,
                "lat": dst_coords[0] + 0.012,
                "lon": dst_coords[1] - 0.015,
            }

            sample_offsets = [
                (0.025, 0.018), (-0.030, 0.022), (0.015, -0.035),
                (-0.020, -0.028), (0.040, -0.010), (-0.015, 0.040),
                (0.032, 0.035), (-0.042, -0.015),
            ]

            map_attractions = []
            for i, attr in enumerate(attractions):
                off = sample_offsets[i % len(sample_offsets)]
                map_attractions.append({
                    "day": attr["day"],
                    "name": attr["name"],
                    "detail": attr["detail"],
                    "lat": dst_coords[0] + off[0],
                    "lon": dst_coords[1] + off[1],
                })

            response_body = {
                "success": True,
                "itinerary": itinerary,
                "booking_links": booking_links,
                "map_data": {
                    "origin": {
                        "name": origin.title(),
                        "lat": src_coords[0],
                        "lon": src_coords[1],
                    },
                    "destination": {
                        "name": destination.title(),
                        "lat": dst_coords[0],
                        "lon": dst_coords[1],
                    },
                    "hotel": hotel_data,
                    "attractions": map_attractions,
                },
                "trip_summary": {
                    "origin": origin,
                    "destination": destination,
                    "start_date": start_date,
                    "end_date": end_date,
                    "budget": budget,
                    "travelers": travelers,
                    "transport_mode": transport_mode,
                },
            }

            start_response("200 OK", cors_headers)
            return [json.dumps(response_body).encode("utf-8")]

        except Exception as exc:
            logger.exception("Error processing plan request: %s", exc)
            start_response("500 Internal Server Error", cors_headers)
            return [json.dumps({"success": False, "error": str(exc)}).encode("utf-8")]

    start_response("405 Method Not Allowed", cors_headers)
    return [b'{"error":"Method Not Allowed"}']


# Aliases for Vercel discovery
handler = app
application = app

__all__ = ["app", "handler", "application"]
