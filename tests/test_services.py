"""Tests for Booking Links, PDF & iCalendar Export, and Map Services."""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.services.booking_service import (
    get_flight_booking_links,
    get_hotel_booking_links,
    get_train_booking_links,
    get_bus_booking_links,
)
from src.services.export_service import generate_itinerary_pdf, generate_itinerary_ics
from src.components.map_view import create_itinerary_map


SAMPLE_ITINERARY = """Your 3-Day Trip to Goa (2026-03-20 to 2026-03-23)

Flight Selected:
- IndiGo (₹4,850) – Departs Delhi at 06:30

Hotel Booked:
- Royal Heritage (₹1,232/night, 5-star)

Weather:
- Day 1: Clear sky (31°C)
- Day 2: Mainly clear (32°C)
- Day 3: Partly cloudy (30°C)

Best Way to Travel & Route Tips:
- Direct flights (2h 30m) are recommended. Vande Bharat train from Mumbai is also a scenic alternative.

Itinerary:
Day 1: Baga Beach, Fort Aguada
Day 2: Calangute Beach, Basilica of Bom Jesus
Day 3: Dudhsagar Falls, Anjuna Flea Market

Estimated Total Budget:
- Flight: ₹4,850
- Hotel: ₹3,696
- Food & Travel: ₹4,500
-------------------------------------
Total Cost: ₹13,046

Why We Picked This:
- Fastest flight with IndiGo and luxurious beachfront stay.
"""


def test_flight_booking_links():
    links = get_flight_booking_links("Delhi", "Goa", date(2026, 3, 20))
    assert len(links) >= 3
    names = [l["name"] for l in links]
    assert "Google Flights" in names
    assert "MakeMyTrip" in names
    assert "google.com/travel/flights" in links[0]["url"]


def test_hotel_booking_links():
    links = get_hotel_booking_links("Goa", "Royal Heritage", date(2026, 3, 20))
    assert len(links) >= 3
    names = [l["name"] for l in links]
    assert "Booking.com" in names
    assert "booking.com" in links[0]["url"]


def test_train_booking_links():
    links = get_train_booking_links("Delhi", "Goa", date(2026, 3, 20))
    assert len(links) >= 2
    names = [l["name"] for l in links]
    assert any("IRCTC" in n or "ConfirmTkt" in n for n in names)
    assert "confirmtkt.com" in links[0]["url"]


def test_bus_booking_links():
    links = get_bus_booking_links("Delhi", "Goa", date(2026, 3, 20))
    assert len(links) >= 2
    names = [l["name"] for l in links]
    assert "RedBus" in names
    assert "redbus.in" in links[0]["url"]


def test_generate_itinerary_pdf():
    pdf_bytes = generate_itinerary_pdf(
        itinerary_text=SAMPLE_ITINERARY,
        source="Delhi",
        destination="Goa",
        start_date=date(2026, 3, 20),
        num_days=3,
    )
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 500
    assert pdf_bytes.startswith(b"%PDF")


def test_generate_itinerary_ics():
    ics_bytes = generate_itinerary_ics(
        itinerary_text=SAMPLE_ITINERARY,
        source="Delhi",
        destination="Goa",
        start_date=date(2026, 3, 20),
        num_days=3,
    )
    assert isinstance(ics_bytes, bytes)
    assert len(ics_bytes) > 200
    ics_text = ics_bytes.decode("utf-8")
    assert "BEGIN:VCALENDAR" in ics_text
    assert "BEGIN:VEVENT" in ics_text
    assert "END:VCALENDAR" in ics_text


def test_create_itinerary_map():
    itinerary_days = [
        ("Day 1", ["Baga Beach", "Fort Aguada"]),
        ("Day 2", ["Calangute Beach", "Basilica of Bom Jesus"]),
    ]
    folium_map = create_itinerary_map(
        source="Delhi",
        destination="Goa",
        hotel_info="Royal Heritage (₹1,232/night, 5-star)",
        itinerary_days=itinerary_days,
    )
    assert folium_map is not None
    html = folium_map._repr_html_()
    assert "leaflet" in html.lower()


def test_parse_env_keys():
    from src.agent import _parse_env_keys

    # Test Python list format as seen in screenshots
    raw_py = '''GOOGLE_API_KEYS = [
      "demo_mock_google_api_key_sample_alpha_12345",
      "demo_mock_google_api_key_sample_beta_67890"
    ]'''
    keys = _parse_env_keys(raw_py)
    assert len(keys) == 2
    assert keys[0] == "demo_mock_google_api_key_sample_alpha_12345"
    assert keys[1] == "demo_mock_google_api_key_sample_beta_67890"

    # Test comma-separated string
    raw_csv = "key_one_12345678, key_two_87654321"
    keys_csv = _parse_env_keys(raw_csv)
    assert keys_csv == ["key_one_12345678", "key_two_87654321"]

