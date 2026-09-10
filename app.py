"""Streamlit interface for the Agentic AI Travel Planning Assistant.

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import io
from contextlib import redirect_stdout
from datetime import date, timedelta

import streamlit as st
from dotenv import load_dotenv

from src.utils import CITY_COORDINATES
from src.agent import plan_trip

load_dotenv()

st.set_page_config(page_title="AI Travel Planner", page_icon="🧭", layout="centered")

CITIES = sorted(c.title() for c in CITY_COORDINATES)

st.title("🧭 Agentic AI Travel Planning Assistant")
st.caption(
    "An autonomous LangChain agent that searches flights, hotels, and "
    "attractions, checks live weather, and builds a budgeted day-by-day "
    "itinerary."
)

with st.form("trip_form"):
    col1, col2 = st.columns(2)
    with col1:
        source = st.selectbox("From", CITIES, index=CITIES.index("Delhi"))
    with col2:
        destination = st.selectbox("To", CITIES, index=CITIES.index("Goa"))

    col3, col4, col5 = st.columns(3)
    with col3:
        start_date = st.date_input("Start date", value=date.today() + timedelta(days=7))
    with col4:
        num_days = st.number_input("Trip length (days)", min_value=1, max_value=14, value=3)
    with col5:
        num_travelers = st.number_input("Travelers", min_value=1, max_value=10, value=1)

    col6, col7 = st.columns(2)
    with col6:
        min_stars = st.slider("Minimum hotel stars", 0, 5, 3)
    with col7:
        max_budget = st.number_input(
            "Max hotel price/night (₹, 0 = no limit)", min_value=0, value=0, step=500
        )

    amenities = st.multiselect(
        "Preferred hotel amenities",
        ["wifi", "pool", "gym", "spa", "breakfast", "parking"],
    )
    preferences = st.text_area(
        "Anything else? (place types, pace, activities...)",
        placeholder="e.g. I love beaches and historic forts, keep it relaxed.",
    )
    show_reasoning = st.checkbox("Show agent's tool-calling steps", value=False)

    submitted = st.form_submit_button("Plan my trip ✈️")

if submitted:
    if source == destination:
        st.error("Source and destination must be different cities.")
    else:
        end_date = start_date + timedelta(days=int(num_days) - 1)
        query_parts = [
            f"Plan a {num_days}-day trip from {source} to {destination} "
            f"starting {start_date.isoformat()} for {num_travelers} traveler(s).",
            f"Hotel preference: minimum {min_stars} stars",
        ]
        if max_budget:
            query_parts.append(f"max ₹{max_budget} per night")
        if amenities:
            query_parts.append(f"must have amenities: {', '.join(amenities)}")
        if preferences.strip():
            query_parts.append(f"Additional preferences: {preferences.strip()}")
        user_query = ". ".join(query_parts)

        with st.spinner("Agent is searching flights, hotels, places, and weather..."):
            log_buffer = io.StringIO()
            try:
                with redirect_stdout(log_buffer):
                    itinerary = plan_trip(user_query, verbose=show_reasoning)
            except RuntimeError as exc:
                st.error(f"Configuration error: {exc}")
                itinerary = None
            except Exception as exc:  # noqa: BLE001 - top-level UI error boundary
                st.error(f"Something went wrong while planning your trip: {exc}")
                itinerary = None

        if itinerary:
            st.success("Here's your itinerary!")
            st.markdown(f"### {source} → {destination}: {start_date} to {end_date}")
            st.code(itinerary, language="markdown")

            if show_reasoning and log_buffer.getvalue().strip():
                with st.expander("🔍 Agent reasoning / tool calls"):
                    st.text(log_buffer.getvalue())

st.divider()
st.caption(
    "Data sources: local flights.json / hotels.json / places.json datasets, "
    "plus live weather from the free Open-Meteo API."
)
