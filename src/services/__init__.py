"""Services package."""
from .booking_service import (
    get_flight_booking_links,
    get_hotel_booking_links,
    get_train_booking_links,
    get_bus_booking_links,
)
try:
    from .export_service import generate_itinerary_pdf, generate_itinerary_ics
except ImportError:
    generate_itinerary_pdf = None
    generate_itinerary_ics = None

__all__ = [
    "get_flight_booking_links",
    "get_hotel_booking_links",
    "get_train_booking_links",
    "get_bus_booking_links",
    "generate_itinerary_pdf",
    "generate_itinerary_ics",
]
