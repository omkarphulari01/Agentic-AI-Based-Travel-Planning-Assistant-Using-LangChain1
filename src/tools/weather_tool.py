"""Weather Lookup Tool.

Calls the free Open-Meteo API (no API key required) to fetch a daily
forecast for a supported Indian city, as specified in the project's
data-sources section.

API reference: https://open-meteo.com/en/docs
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

import requests
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.utils import CITY_COORDINATES, get_city_coordinates

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT_SECONDS = 10

# WMO weather interpretation codes -> short human-readable label.
# https://open-meteo.com/en/docs#weathervariables
WEATHER_CODE_LABELS = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


class WeatherForecastInput(BaseModel):
    """Input schema for the weather forecast tool."""

    city: str = Field(
        ...,
        description=(
            "City to check the forecast for. Supported: "
            + ", ".join(sorted(c.title() for c in CITY_COORDINATES))
        ),
    )
    start_date: str = Field(
        ..., description="Trip start date in YYYY-MM-DD format."
    )
    num_days: int = Field(
        default=3, ge=1, le=16, description="Number of days to forecast (max 16)."
    )


@tool("get_weather_forecast", args_schema=WeatherForecastInput)
def get_weather_forecast(city: str, start_date: str, num_days: int = 3) -> dict:
    """Fetch a daily weather forecast for a city using the free Open-Meteo API.

    Use this tool to fill in the 'Weather for Each Day' section of the
    itinerary. Open-Meteo's forecast API only covers roughly the next 16
    days; if the requested trip is further in the future, this tool
    returns a note explaining that live data isn't available for that
    date and the agent should say so rather than invent numbers.
    """
    coords = get_city_coordinates(city)
    if coords is None:
        return {
            "error": (
                f"'{city}' is not in the supported city list: "
                f"{', '.join(sorted(c.title() for c in CITY_COORDINATES))}."
            )
        }
    latitude, longitude = coords

    try:
        trip_start = datetime.strptime(start_date, "%Y-%m-%d").date()
    except ValueError:
        return {"error": f"start_date '{start_date}' must be in YYYY-MM-DD format."}

    today = date.today()
    days_ahead = (trip_start - today).days
    if days_ahead > 16:
        return {
            "note": (
                f"Requested date {start_date} is {days_ahead} days from today. "
                "Open-Meteo's free forecast only reliably covers ~16 days ahead, "
                "so live weather isn't available yet for this trip. Plan "
                "accordingly and re-check closer to the travel date."
            ),
            "city": city,
            "forecast": [],
        }

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": "temperature_2m_max,temperature_2m_min,weathercode,precipitation_probability_max",
        "timezone": "auto",
        "forecast_days": 16,
    }

    try:
        response = requests.get(OPEN_METEO_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
    except requests.exceptions.RequestException as exc:
        return {"error": f"Weather API request failed: {exc}"}
    except ValueError as exc:
        return {"error": f"Weather API returned invalid JSON: {exc}"}

    daily = payload.get("daily", {})
    dates = daily.get("time", [])
    highs = daily.get("temperature_2m_max", [])
    lows = daily.get("temperature_2m_min", [])
    codes = daily.get("weathercode", [])
    rain_prob = daily.get("precipitation_probability_max", [])

    forecast = []
    for i, day_str in enumerate(dates):
        day_date = datetime.strptime(day_str, "%Y-%m-%d").date()
        if day_date < trip_start or day_date >= trip_start + timedelta(days=num_days):
            continue
        code = codes[i] if i < len(codes) else None
        forecast.append(
            {
                "date": day_str,
                "condition": WEATHER_CODE_LABELS.get(code, "Unknown"),
                "temp_max_c": highs[i] if i < len(highs) else None,
                "temp_min_c": lows[i] if i < len(lows) else None,
                "rain_probability_pct": rain_prob[i] if i < len(rain_prob) else None,
            }
        )

    if not forecast:
        return {
            "note": "No forecast data returned for the requested date range.",
            "city": city,
            "forecast": [],
        }

    return {"city": city, "latitude": latitude, "longitude": longitude, "forecast": forecast}
