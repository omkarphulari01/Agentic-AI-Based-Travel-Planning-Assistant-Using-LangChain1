"""1-Click Direct Booking Service.

Generates pre-filled search and booking URLs for:
- Flights: Google Flights, MakeMyTrip, Skyscanner
- Hotels: Booking.com, Agoda
- Trains: IRCTC / ConfirmTkt, MakeMyTrip Trains
- Buses: RedBus, Zingbus
"""

from __future__ import annotations

import urllib.parse
from datetime import date


def get_flight_booking_links(source: str, destination: str, travel_date: str | date | None = None) -> list[dict[str, str]]:
    """Generate direct 1-click booking URLs for flights."""
    date_str = str(travel_date) if travel_date else ""
    src_enc = urllib.parse.quote_plus(source.strip())
    dst_enc = urllib.parse.quote_plus(destination.strip())

    google_flights_url = (
        f"https://www.google.com/travel/flights?q=Flights+to+{dst_enc}+from+{src_enc}"
        + (f"+on+{date_str}" if date_str else "")
    )

    makemytrip_url = (
        f"https://www.makemytrip.com/flight/search?itinerary={src_enc}-{dst_enc}-{date_str}&tripType=O&paxType=A-1_C-0_I-0&intl=false&cabinClass=E"
        if date_str else f"https://www.makemytrip.com/flights/"
    )

    skyscanner_url = f"https://www.skyscanner.co.in/transport/flights/{src_enc}/{dst_enc}/"

    return [
        {"name": "Google Flights", "url": google_flights_url, "icon": "✈️", "color": "#4285F4"},
        {"name": "MakeMyTrip", "url": makemytrip_url, "icon": "🛫", "color": "#E41B17"},
        {"name": "Skyscanner", "url": skyscanner_url, "icon": "🌐", "color": "#0770E3"},
    ]


def get_hotel_booking_links(city: str, hotel_name: str | None = None, check_in_date: str | date | None = None) -> list[dict[str, str]]:
    """Generate direct 1-click booking URLs for hotels."""
    query = f"{hotel_name} {city}" if hotel_name else city
    q_enc = urllib.parse.quote_plus(query.strip())
    city_enc = urllib.parse.quote_plus(city.strip())

    booking_url = f"https://www.booking.com/searchresults.html?ss={q_enc}"
    agoda_url = f"https://www.agoda.com/search?city={city_enc}"
    google_hotels_url = f"https://www.google.com/travel/hotels?q=hotels+in+{q_enc}"

    return [
        {"name": "Booking.com", "url": booking_url, "icon": "🏨", "color": "#003580"},
        {"name": "Agoda", "url": agoda_url, "icon": "🛏️", "color": "#5392F9"},
        {"name": "Google Hotels", "url": google_hotels_url, "icon": "📍", "color": "#34A853"},
    ]


def get_train_booking_links(source: str, destination: str, travel_date: str | date | None = None) -> list[dict[str, str]]:
    """Generate direct 1-click booking URLs for trains (Vande Bharat / Express / IRCTC)."""
    src_enc = urllib.parse.quote_plus(source.strip())
    dst_enc = urllib.parse.quote_plus(destination.strip())
    date_str = str(travel_date) if travel_date else ""

    confirmtkt_url = f"https://www.confirmtkt.com/trains/{src_enc}-to-{dst_enc}-train-tickets"
    irctc_url = f"https://www.irctc.co.in/nget/train-search"
    mmt_trains_url = f"https://www.makemytrip.com/railways/"

    return [
        {"name": "ConfirmTkt (IRCTC)", "url": confirmtkt_url, "icon": "🚆", "color": "#FF9900"},
        {"name": "IRCTC Official", "url": irctc_url, "icon": "🎫", "color": "#283593"},
        {"name": "MakeMyTrip Trains", "url": mmt_trains_url, "icon": "🚄", "color": "#D32F2F"},
    ]


def get_bus_booking_links(source: str, destination: str, travel_date: str | date | None = None) -> list[dict[str, str]]:
    """Generate direct 1-click booking URLs for luxury sleeper & AC buses."""
    src_slug = source.strip().lower().replace(" ", "-")
    dst_slug = destination.strip().lower().replace(" ", "-")

    redbus_url = f"https://www.redbus.in/bus-tickets/{src_slug}-to-{dst_slug}"
    zingbus_url = f"https://www.zingbus.com/bus-tickets/{src_slug}-to-{dst_slug}"
    abhibus_url = f"https://www.abhibus.com/bus_search/{src_slug}/{dst_slug}"

    return [
        {"name": "RedBus", "url": redbus_url, "icon": "🚌", "color": "#D84E55"},
        {"name": "Zingbus", "url": zingbus_url, "icon": "🚍", "color": "#FFA000"},
        {"name": "AbhiBus", "url": abhibus_url, "icon": "🚎", "color": "#1976D2"},
    ]


def generate_booking_links(
    source: str,
    destination: str,
    start_date: str | date | None = None,
    end_date: str | date | None = None,
    hotel_name: str | None = None,
) -> dict[str, list[dict[str, str]]]:
    """Convenience helper returning all categorized 1-click booking links."""
    return {
        "Flights": [
            {"label": item["name"], "url": item["url"], "icon": item["icon"]}
            for item in get_flight_booking_links(source, destination, start_date)
        ],
        "Hotels": [
            {"label": item["name"], "url": item["url"], "icon": item["icon"]}
            for item in get_hotel_booking_links(destination, hotel_name, start_date)
        ],
        "Trains": [
            {"label": item["name"], "url": item["url"], "icon": item["icon"]}
            for item in get_train_booking_links(source, destination, start_date)
        ],
        "Buses": [
            {"label": item["name"], "url": item["url"], "icon": item["icon"]}
            for item in get_bus_booking_links(source, destination, start_date)
        ],
    }

