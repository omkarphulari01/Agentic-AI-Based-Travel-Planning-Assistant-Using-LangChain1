"""Shared utility helpers: JSON loading, path resolution, and city metadata.

Keeping this logic in one module avoids repeating file I/O and error
handling in every tool (DRY, PEP 8 friendly, easy to unit test).
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any


# ---------------------------------------------------------------------------
# Path handling
# ---------------------------------------------------------------------------

# Resolve the data directory relative to this file so the project works
# regardless of the current working directory it is launched from.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(_PROJECT_ROOT, "data")


@lru_cache(maxsize=None)
def load_json_dataset(filename: str) -> list[dict[str, Any]]:
    """Load and cache a JSON dataset from the ``data/`` directory.

    Args:
        filename: Name of the JSON file (e.g. ``"flights.json"``).

    Returns:
        The parsed list of records.

    Raises:
        FileNotFoundError: If the dataset file does not exist.
        ValueError: If the file cannot be parsed as JSON.
    """
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
# City -> coordinates lookup (needed for the Open-Meteo weather API, which
# requires latitude/longitude rather than a city name).
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
}


def get_city_coordinates(city: str) -> tuple[float, float] | None:
    """Return (latitude, longitude) for a supported city, else ``None``."""
    return CITY_COORDINATES.get(city.strip().lower())


def normalize(value: str) -> str:
    """Lowercase + strip a string for case-insensitive comparisons."""
    return value.strip().lower()
