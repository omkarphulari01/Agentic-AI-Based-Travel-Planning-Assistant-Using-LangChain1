"""Streamlit interface for the Agentic AI Travel Planning Assistant.

Run locally with:
    streamlit run app.py

On Streamlit Community Cloud, add your key under
App settings -> Secrets, e.g.:
    ANTHROPIC_API_KEY = "sk-ant-..."
(.env files are gitignored and never make it to a deployed app, so the
key must be provided as a Streamlit secret or pasted in the sidebar.)
"""

from __future__ import annotations

import io
import os
import re
from contextlib import redirect_stdout
from datetime import date, timedelta

import streamlit as st
from dotenv import load_dotenv

from src.utils import CITY_COORDINATES
from src.agent import plan_trip

# ---------------------------------------------------------------------------
# Secrets / API key wiring
# ---------------------------------------------------------------------------
# Locally, python-dotenv picks up a .env file. On Streamlit Cloud there is
# no .env (it's gitignored), so credentials come from st.secrets instead.
# We copy anything relevant into os.environ so src/agent.py's plain
# os.getenv() calls keep working unchanged in both environments.
load_dotenv()

for _key in ("ANTHROPIC_API_KEY", "ANTHROPIC_MODEL", "OPENAI_API_KEY", "OPENAI_MODEL"):
    try:
        if _key in st.secrets and st.secrets[_key]:
            os.environ[_key] = str(st.secrets[_key])
    except Exception:
        # st.secrets raises if no secrets.toml exists at all (e.g. first
        # local run) - that's fine, just fall back to .env / manual entry.
        break

CITIES = sorted(c.title() for c in CITY_COORDINATES)

# ---------------------------------------------------------------------------
# Page config + styling
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Travel Planner",
    page_icon="🧭",
    layout="centered",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp { background: radial-gradient(1200px 600px at 50% -10%, #1a2440 0%, #0b0f19 55%); }
    .hero-title {
        font-size: 2.4rem; font-weight: 800; line-height: 1.15;
        background: linear-gradient(90deg, #ffb86b, #ff7ab6 45%, #7cc5ff 90%);
        -webkit-background-clip: text; background-clip: text; color: transparent;
        margin-bottom: 0.2rem;
    }
    .hero-sub { color: #9aa4c0; font-size: 1.02rem; margin-bottom: 1.4rem; }
    .day-badge {
        display: inline-block; background: linear-gradient(90deg,#ff7ab6,#7cc5ff);
        color: #0b0f19; font-weight: 700; padding: 2px 10px; border-radius: 999px;
        font-size: 0.8rem; margin-right: 8px;
    }
    .place-chip {
        display: inline-block; background: #1c2440; border: 1px solid #2c3660;
        border-radius: 10px; padding: 6px 12px; margin: 4px 6px 4px 0; font-size: 0.92rem;
    }
    .metric-card {
        background: #131a2e; border: 1px solid #232c4d; border-radius: 14px;
        padding: 14px 16px; text-align: center;
    }
    .metric-label { color: #8b95b8; font-size: 0.82rem; text-transform: uppercase; letter-spacing: .04em; }
    .metric-value { font-size: 1.35rem; font-weight: 800; color: #f2f4fb; }
    .total-card {
        background: linear-gradient(90deg, rgba(255,184,107,.16), rgba(124,197,255,.16));
        border: 1px solid #3a4a86; border-radius: 14px; padding: 16px; text-align: center;
    }
    .total-value { font-size: 1.9rem; font-weight: 900; color: #ffe6c9; }
    .weather-chip {
        background: #131a2e; border: 1px solid #232c4d; border-radius: 14px;
        padding: 10px; text-align: center;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sidebar: connection status + manual key entry (fallback for quick testing)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Model connection")
    has_key = bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY"))

    if has_key:
        provider = "Claude (Anthropic)" if os.getenv("ANTHROPIC_API_KEY") else "OpenAI"
        st.success(f"✅ Connected — using {provider}")
    else:
        st.error("⚠️ No API key configured")
        with st.expander("Fix this", expanded=True):
            st.markdown(
                "**Deployed on Streamlit Cloud?** Go to your app → "
                "**Settings → Secrets** and add:\n\n"
                "```toml\nANTHROPIC_API_KEY = \"sk-ant-...\"\n```\n"
                "then reboot the app.\n\n"
                "**Running locally?** Copy `.env.example` to `.env` and "
                "fill in your key.\n\n"
                "**Just testing right now?** Paste a key below "
                "(session-only, never saved)."
            )
            pasted_key = st.text_input("Anthropic or OpenAI API key", type="password")
            if pasted_key:
                if pasted_key.startswith("sk-ant"):
                    os.environ["ANTHROPIC_API_KEY"] = pasted_key
                else:
                    os.environ["OPENAI_API_KEY"] = pasted_key
                st.rerun()

    st.divider()
    st.markdown("### ℹ️ About")
    st.caption(
        "This agent autonomously calls tools for flights, hotels, "
        "places, live weather, and budget — then assembles a full "
        "itinerary. Data: local JSON datasets + free Open-Meteo API."
    )

# ---------------------------------------------------------------------------
# Hero header
# ---------------------------------------------------------------------------
st.markdown('<div class="hero-title">🧭 Agentic AI Travel Planning Assistant</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-sub">An autonomous LangChain agent that searches flights, hotels, and '
    'attractions, checks live weather, and builds a budgeted day-by-day itinerary.</div>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Trip request form
# ---------------------------------------------------------------------------
with st.container(border=True):
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

        submitted = st.form_submit_button("Plan my trip ✈️", use_container_width=True)

# ---------------------------------------------------------------------------
# Itinerary parsing helpers
# ---------------------------------------------------------------------------
SECTION_HEADERS = [
    "Flight Selected:",
    "Hotel Booked:",
    "Weather:",
    "Itinerary:",
    "Estimated Total Budget:",
    "Why We Picked This:",
]

WEATHER_EMOJI = [
    (r"thunder|storm", "⛈️"),
    (r"snow", "❄️"),
    (r"rain|drizzle|shower", "🌧️"),
    (r"fog", "🌫️"),
    (r"overcast|cloud", "☁️"),
    (r"clear|sun", "☀️"),
]


def weather_icon(condition: str) -> str:
    cond = (condition or "").lower()
    for pattern, emoji in WEATHER_EMOJI:
        if re.search(pattern, cond):
            return emoji
    return "🌤️"


def parse_itinerary(text: str) -> dict:
    """Split the agent's structured itinerary text into labeled sections.

    Falls back gracefully (returns just {'title': text}) if the agent
    replied with something other than the expected format, e.g. a
    clarifying question.
    """
    pattern = "(" + "|".join(re.escape(h) for h in SECTION_HEADERS) + ")"
    parts = re.split(pattern, text)
    sections = {"title": parts[0].strip()}
    it = iter(parts[1:])
    for header, body in zip(it, it):
        sections[header.rstrip(":")] = body.strip()
    return sections


def money(value: str) -> str:
    """Pull the first ₹-prefixed (or plain) number out of a text chunk."""
    match = re.search(r"₹\s?[\d,]+(\.\d+)?", value)
    return match.group(0) if match else value.strip()


def render_itinerary(text: str) -> None:
    sections = parse_itinerary(text)

    if len(sections) <= 1:
        # Agent didn't return the structured format (e.g. asked a
        # clarifying question) - just show the raw reply.
        st.info(sections["title"])
        return

    if sections["title"]:
        st.markdown(f"#### {sections['title']}")

    # --- Flight & Hotel side by side -------------------------------------------------
    col_f, col_h = st.columns(2)
    with col_f:
        with st.container(border=True):
            st.markdown("**✈️ Flight Selected**")
            st.write(sections.get("Flight Selected", "—"))
    with col_h:
        with st.container(border=True):
            st.markdown("**🏨 Hotel Booked**")
            st.write(sections.get("Hotel Booked", "—"))

    # --- Weather ------------------------------------------------------------
    weather_raw = sections.get("Weather", "")
    day_lines = [l.strip("- ").strip() for l in weather_raw.splitlines() if l.strip()]
    if day_lines:
        st.markdown("**🌦️ Weather**")
        cols = st.columns(len(day_lines))
        for col, line in zip(cols, day_lines):
            label, _, rest = line.partition(":")
            with col:
                st.markdown(
                    f'<div class="weather-chip">{weather_icon(rest)}<br>'
                    f'<b>{label.strip()}</b><br><span style="color:#9aa4c0;font-size:.85rem">'
                    f"{rest.strip()}</span></div>",
                    unsafe_allow_html=True,
                )

    # --- Day-wise itinerary ---------------------------------------------------------
    itinerary_raw = sections.get("Itinerary", "")
    day_plan_lines = [l.strip() for l in itinerary_raw.splitlines() if l.strip()]
    if day_plan_lines:
        st.markdown("**🗺️ Day-wise Itinerary**")
        tab_labels = [l.split(":")[0].strip() for l in day_plan_lines]
        tabs = st.tabs(tab_labels)
        for tab, line in zip(tabs, day_plan_lines):
            _, _, places = line.partition(":")
            with tab:
                chips = "".join(
                    f'<span class="place-chip">📍 {p.strip()}</span>'
                    for p in places.split(",") if p.strip()
                )
                st.markdown(chips or "—", unsafe_allow_html=True)

    # --- Budget ---------------------------------------------------------------------
    budget_raw = sections.get("Estimated Total Budget", "")
    if budget_raw:
        st.markdown("**💰 Budget Breakdown**")
        flight_m = re.search(r"Flight:\s*(₹?[\d,]+)", budget_raw)
        hotel_m = re.search(r"Hotel:\s*(₹?[\d,]+)", budget_raw)
        food_m = re.search(r"Food.*?:\s*(₹?[\d,]+)", budget_raw)
        total_m = re.search(r"Total Cost:\s*(₹?[\d,]+)", budget_raw)

        b1, b2, b3, b4 = st.columns(4)
        for col, label, val in [
            (b1, "Flight", flight_m.group(1) if flight_m else "—"),
            (b2, "Hotel", hotel_m.group(1) if hotel_m else "—"),
            (b3, "Food & Travel", food_m.group(1) if food_m else "—"),
        ]:
            with col:
                st.markdown(
                    f'<div class="metric-card"><div class="metric-label">{label}</div>'
                    f'<div class="metric-value">{val}</div></div>',
                    unsafe_allow_html=True,
                )
        with b4:
            st.markdown(
                f'<div class="total-card"><div class="metric-label">Total</div>'
                f'<div class="total-value">{total_m.group(1) if total_m else "—"}</div></div>',
                unsafe_allow_html=True,
            )

    # --- Reasoning --------------------------------------------------------------------
    reasoning = sections.get("Why We Picked This")
    if reasoning:
        with st.expander("🧠 Why the agent picked this"):
            st.markdown(reasoning)


# ---------------------------------------------------------------------------
# Run the agent
# ---------------------------------------------------------------------------
if submitted:
    if source == destination:
        st.error("Source and destination must be different cities.")
    elif not (os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")):
        st.error("⚠️ No API key configured — see the sidebar for how to fix this.")
    else:
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

        steps = ["🔎 Searching flights", "🏨 Finding hotels", "🗺️ Discovering places",
                 "🌦️ Checking weather", "💰 Estimating budget", "📝 Writing your itinerary"]
        with st.status("Planning your trip...", expanded=True) as status:
            for step in steps:
                st.write(step)
            log_buffer = io.StringIO()
            try:
                with redirect_stdout(log_buffer):
                    itinerary = plan_trip(user_query, verbose=show_reasoning)
                status.update(label="Done! ✅", state="complete", expanded=False)
            except RuntimeError as exc:
                status.update(label="Configuration error", state="error")
                st.error(f"Configuration error: {exc}")
                itinerary = None
            except Exception as exc:  # noqa: BLE001 - top-level UI error boundary
                status.update(label="Something went wrong", state="error")
                st.error(f"Something went wrong while planning your trip: {exc}")
                itinerary = None

        if itinerary:
            render_itinerary(itinerary)

            with st.expander("📄 Raw agent output"):
                st.code(itinerary, language="markdown")

            if show_reasoning and log_buffer.getvalue().strip():
                with st.expander("🔍 Agent reasoning / tool calls"):
                    st.text(log_buffer.getvalue())

st.divider()
st.caption(
    "Data sources: local flights.json / hotels.json / places.json datasets, "
    "plus live weather from the free Open-Meteo API."
)
