"""Shared utility helpers: JSON loading, path resolution, dynamic geocoding, and web search.

Keeping this logic in one module avoids repeating file I/O and error
handling in every tool (DRY, PEP 8 friendly, easy to unit test).
"""

from __future__ import annotations

import json
import logging
import os
import re
from functools import lru_cache
from typing import Any

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path handling
# ---------------------------------------------------------------------------

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(_PROJECT_ROOT, "data")


@lru_cache(maxsize=None)
def load_json_dataset(filename: str) -> list[dict[str, Any]]:
    """Load and cache a JSON dataset from the ``data/`` directory."""
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Dataset '{filename}' not found at {path}. "
            "Make sure flights.json, hotels.json and places.json live in the "
            "'data/' folder."
        )
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Could not parse '{filename}' as valid JSON: {exc}") from exc


# ---------------------------------------------------------------------------
# City -> coordinates lookup (with live Open-Meteo fallback for global cities)
# ---------------------------------------------------------------------------

CITY_COORDINATES: dict[str, tuple[float, float]] = {
    "delhi": (28.6139, 77.2090),
    "mumbai": (19.0760, 72.8777),
    "bangalore": (12.9716, 77.5946),
    "bengaluru": (12.9716, 77.5946),
    "chennai": (13.0827, 80.2707),
    "hyderabad": (17.3850, 78.4867),
    "kolkata": (22.5726, 88.3639),
    "jaipur": (26.9124, 75.7873),
    "goa": (15.2993, 74.1240),
    "dubai": (25.0772, 55.3093),
    "london": (51.5074, -0.1278),
    "paris": (48.8566, 2.3522),
    "tokyo": (35.6762, 139.6503),
    "new york": (40.7128, -74.0060),
    "singapore": (1.3521, 103.8198),
    "bangkok": (13.7563, 100.5018),
    "manali": (32.2396, 77.1887),
    "shimla": (31.1048, 77.1734),
    "udaipur": (24.5854, 73.7125),
    "varanasi": (25.3176, 82.9739),
    "kerala": (10.8505, 76.2711),
    "kochi": (9.9312, 76.2673),
    "srinagar": (34.0837, 74.7973),
    "agra": (27.1767, 78.0081),
}


@lru_cache(maxsize=128)
def get_city_coordinates(city: str) -> tuple[float, float] | None:
    """Return (latitude, longitude) for a city.
    
    Checks known dictionary first, then dynamically queries Open-Meteo
    Geocoding API to support any city in the world in real-time.
    """
    clean_city = city.strip().lower()
    if clean_city in CITY_COORDINATES:
        return CITY_COORDINATES[clean_city]

    # Live geocoding via Open-Meteo free geocoding API
    try:
        url = "https://geocoding-api.open-meteo.com/v1/search"
        params = {"name": city.strip(), "count": 1, "language": "en", "format": "json"}
        resp = requests.get(url, params=params, timeout=4)
        if resp.status_code == 200:
            data = resp.json()
            if "results" in data and data["results"]:
                res = data["results"][0]
                coords = (float(res["latitude"]), float(res["longitude"]))
                CITY_COORDINATES[clean_city] = coords
                return coords
    except Exception as exc:
        logger.debug("Live geocoding error for %s: %s", city, exc)

    return None


def normalize(value: str) -> str:
    """Lowercase + strip a string for case-insensitive comparisons."""
    return value.strip().lower()


@lru_cache(maxsize=128)
def _cached_web_search(query: str, max_results: int = 5) -> str:
    """Execute live web search and return JSON string for caching."""
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        ddgs = DDGS(timeout=3.5)
        results = list(ddgs.text(query, max_results=max_results))
        items = [
            {
                "title": r.get("title", ""),
                "snippet": r.get("body", ""),
                "link": r.get("href", ""),
            }
            for r in results if r
        ]
        return json.dumps(items)
    except Exception as exc:
        logger.debug("Live web search error for %s: %s", query, exc)
        return "[]"


def perform_live_web_search(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """Query live real-time information using DuckDuckGo with sub-second caching."""
    cached_json = _cached_web_search(query.strip(), max_results)
    try:
        return json.loads(cached_json)
    except Exception:
        return []


def search_live_route_recommendations(source: str, destination: str) -> list[dict[str, str]]:
    """Search for the best ways to travel between two cities (Flight, Train, Road)."""
    query = f"best way to travel from {source} to {destination} flight vs train vs bus route options"
    return perform_live_web_search(query, max_results=3)


