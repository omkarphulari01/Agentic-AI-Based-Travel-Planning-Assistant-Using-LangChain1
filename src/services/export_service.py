"""Export Service: PDF and Google Calendar (.ics) Generation.

Allows travelers to download their personalized itinerary as:
1. A PDF summary using ReportLab.
2. A standard .ics iCalendar file (compatible with Google Calendar, Apple Calendar, Outlook).
"""

from __future__ import annotations

import io
import re
from datetime import date, datetime, time, timedelta
from typing import Optional

from icalendar import Calendar, Event
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def generate_itinerary_pdf(
    itinerary_text: str,
    source: str,
    destination: str,
    start_date: date | str,
    num_days: int,
    total_budget: Optional[str] = None,
) -> bytes:
    """Compile the itinerary text into a clean, printable PDF document."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TripTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "TripSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=14,
    )
    h2_style = ParagraphStyle(
        "TripH2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#0f766e"),
        spaceBefore=10,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "TripBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#334155"),
    )

    story = []

    # Title & Subtitle
    story.append(Paragraph(f"🧭 {num_days}-Day Trip to {destination.title()}", title_style))
    story.append(Paragraph(f"Origin: {source.title()} | Start Date: {start_date} | Total Length: {num_days} Days", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#cbd5e1"), spaceAfter=14))

    # Process itinerary text lines into sections
    lines = itinerary_text.splitlines()
    for line in lines:
        stripped = line.strip()
        if not stripped:
            story.append(Spacer(1, 4))
            continue

        if stripped.endswith(":") or stripped.startswith("Your ") or stripped.startswith("Day "):
            story.append(Spacer(1, 6))
            story.append(Paragraph(f"<b>{stripped}</b>", h2_style))
        elif stripped.startswith("- "):
            story.append(Paragraph(f"• {stripped[2:]}", body_style))
        elif stripped.startswith("-------------------------------------"):
            story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#e2e8f0"), spaceBefore=4, spaceAfter=4))
        else:
            story.append(Paragraph(stripped, body_style))

    doc.build(story)
    return buffer.getvalue()


def generate_itinerary_ics(
    itinerary_text: str,
    source: str,
    destination: str,
    start_date: date | str,
    num_days: int,
) -> bytes:
    """Generate an iCalendar (.ics) file compatible with Google Calendar and Apple Calendar."""
    if isinstance(start_date, str):
        try:
            base_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            base_date = date.today() + timedelta(days=7)
    else:
        base_date = start_date

    cal = Calendar()
    cal.add("prodid", "-//AI Travel Planning Assistant//EN")
    cal.add("version", "2.0")

    # 1. Flight Departure Event
    flight_match = re.search(r"Flight Selected:\s*\n-?\s*([^\n]+)", itinerary_text)
    flight_summary = flight_match.group(1) if flight_match else f"Flight from {source} to {destination}"

    ev_flight = Event()
    ev_flight.add("summary", f"✈️ Flight to {destination}: {flight_summary}")
    ev_flight.add("description", f"Flight departed from {source} to {destination}.")
    ev_flight.add("dtstart", datetime.combine(base_date, time(7, 0)))
    ev_flight.add("dtend", datetime.combine(base_date, time(10, 0)))
    ev_flight.add("location", f"{source} International Airport")
    cal.add_component(ev_flight)

    # 2. Hotel Check-In Event
    hotel_match = re.search(r"Hotel Booked:\s*\n-?\s*([^\n]+)", itinerary_text)
    hotel_summary = hotel_match.group(1) if hotel_match else f"Hotel in {destination}"

    ev_hotel = Event()
    ev_hotel.add("summary", f"🏨 Hotel Check-In: {hotel_summary}")
    ev_hotel.add("description", f"Stay in {destination} for {num_days} days.")
    ev_hotel.add("dtstart", datetime.combine(base_date, time(12, 0)))
    ev_hotel.add("dtend", datetime.combine(base_date + timedelta(days=num_days), time(11, 0)))
    ev_hotel.add("location", f"{destination.title()}")
    cal.add_component(ev_hotel)

    # 3. Day-by-Day Sightseeing Events
    day_matches = re.findall(r"Day\s*(\d+)\s*:\s*([^\n]+)", itinerary_text, flags=re.IGNORECASE)
    for day_num_str, places_str in day_matches:
        day_idx = int(day_num_str) - 1
        current_day = base_date + timedelta(days=day_idx)

        ev_day = Event()
        ev_day.add("summary", f"📍 Day {day_num_str} Sights in {destination}: {places_str}")
        ev_day.add("description", f"Scheduled visits: {places_str}")
        ev_day.add("dtstart", datetime.combine(current_day, time(10, 0)))
        ev_day.add("dtend", datetime.combine(current_day, time(18, 0)))
        ev_day.add("location", f"{places_str}, {destination.title()}")
        cal.add_component(ev_day)

    return cal.to_ical()
