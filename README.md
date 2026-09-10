# 🧭 Agentic AI-Based Travel Planning Assistant (LangChain)

An autonomous AI travel agent that plans realistic, budgeted, day-by-day trip
itineraries by reasoning over flight, hotel, and attraction data and a live
weather API — built with **LangChain**, **Streamlit**, and **Claude / GPT**.

This implements the capstone brief end-to-end: LangChain tools for flights,
hotels, places, weather, and budget; a tool-calling agent that autonomously
decides which tools to call and in what order; and both a CLI and a
Streamlit UI.

---

## ✨ Features

| Requirement (from project brief)            | Implementation |
|---------------------------------------------|----------------|
| Flight Search Tool                          | `src/tools/flight_tool.py` — filters `flights.json` by route, ranks by price or duration |
| Hotel Recommendation Tool                   | `src/tools/hotel_tool.py` — filters `hotels.json` by city, stars, price, amenities |
| Places Discovery Tool                       | `src/tools/places_tool.py` — filters `places.json` by city, type, rating |
| Weather Lookup Tool                         | `src/tools/weather_tool.py` — live daily forecast via free [Open-Meteo](https://open-meteo.com) API |
| Budget Estimation Tool                      | `src/tools/budget_tool.py` — flight + hotel×nights + daily expenses |
| Agentic reasoning (tool-calling agent)      | `src/agent.py` — LangChain `create_agent` (tool-calling loop) |
| Structured itinerary output                 | Agent's system prompt enforces the exact output format from the brief |
| Justification ("why we selected this")      | Agent prompt requires a short reasoning section |
| Streamlit UI                                | `app.py` |
| CLI                                          | `cli.py` |
| Clean, modular, documented code             | Package layout below, docstrings + type hints throughout |
| Error handling                               | Every tool and the CLI/UI wrap failures in try/except and return readable messages |

---

## 📁 Project Structure

```
travel-planning-assistant/
├── app.py                  # Streamlit UI
├── cli.py                  # Command-line interface
├── requirements.txt
├── .env.example            # Copy to .env and add your API key
├── .gitignore
├── data/
│   ├── flights.json
│   ├── hotels.json
│   └── places.json
├── src/
│   ├── __init__.py
│   ├── agent.py             # Builds the LangChain tool-calling agent
│   ├── utils.py              # JSON loading + city→coordinates helper
│   └── tools/
│       ├── __init__.py
│       ├── flight_tool.py
│       ├── hotel_tool.py
│       ├── places_tool.py
│       ├── weather_tool.py
│       └── budget_tool.py
└── tests/
    └── test_tools.py         # Unit tests for the deterministic tools (no API key needed)
```

---

## 🚀 Setup

1. **Clone and enter the project**
   ```bash
   git clone <your-repo-url>
   cd travel-planning-assistant
   ```

2. **Create a virtual environment and install dependencies**
   ```bash
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Add your LLM API key**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and set **either**:
   - `ANTHROPIC_API_KEY` (Claude — used by default if present), or
   - `OPENAI_API_KEY` (used only if the Anthropic key isn't set)

   No key is required for the Weather tool — Open-Meteo is free and keyless.

4. **Run the tests** (fast, no API key required — they only exercise the
   local dataset tools):
   ```bash
   python -m pytest tests/ -v
   ```

5. **Run the Streamlit app**
   ```bash
   streamlit run app.py
   ```

6. **...or use the CLI**
   ```bash
   python cli.py "Plan a 3-day trip from Delhi to Goa starting 2026-02-12 for 2 people, 4-star hotel with a pool"
   ```

---

## 🧠 How the agent reasons

`src/agent.py` builds a LangChain **tool-calling agent** (`create_agent`)
around a system prompt that lays out an explicit workflow:

1. Parse source, destination, dates, and preferences from the request.
2. Call `search_flights` → pick the best flight (cheapest by default).
3. Call `search_hotels` → pick a hotel matching stated stars/budget/amenities.
4. Call `search_places` → gather ~2 attractions per day.
5. Call `get_weather_forecast` → live forecast for the trip dates.
6. Call `estimate_budget` → totals flight + hotel + daily expenses.
7. Assemble everything into the structured itinerary format specified in
   the project brief, plus a short "Why We Picked This" justification.

The agent will **not fabricate data** — if a tool returns no results or an
error (e.g. unsupported city, no direct flight, forecast too far in the
future), it says so and asks for a workable alternative instead of guessing.

### Supported cities
Delhi, Mumbai, Bangalore, Chennai, Hyderabad, Kolkata, Jaipur, Goa
(matches the cities present in the sample datasets and the Open-Meteo
coordinate lookup table in `src/utils.py`). Add more cities by extending
`CITY_COORDINATES` in `src/utils.py` and the corresponding dataset rows.

---

## 🔧 Extending the project

- **More cities/data**: add rows to `data/*.json` and a coordinate entry in
  `src/utils.py`; no code changes needed elsewhere.
- **Swap the LLM provider**: `src/agent.py::get_llm()` picks Anthropic or
  OpenAI automatically based on which API key is set — add another
  `elif` branch for a different provider.
- **Persist itineraries to a database**: the tool outputs are plain dicts,
  so they can be written straight into a SQL table (e.g. `trips`,
  `trip_days`, `trip_costs`) if you want to add a persistence layer per the
  general project guidelines.
- **Multi-day trip logic**: currently the agent decides day groupings from
  the `search_places` results itself; for stricter control you could add a
  dedicated "itinerary builder" tool that deterministically splits N places
  across N days.

---

## ⚠️ Known limitations

- The sample datasets are small and only cover 8 Indian cities and limited
  routes — some source/destination pairs won't have a direct flight.
- Open-Meteo's free forecast only reliably covers ~16 days ahead; trips
  further out will get a note instead of invented weather.
- This is a reference/demo implementation, not a production booking system
  — no real payments or reservations are made.
