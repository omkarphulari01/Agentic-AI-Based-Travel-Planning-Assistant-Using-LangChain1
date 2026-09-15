# 🧭 Agentic AI-Based Travel Planning Assistant (LangChain)

An autonomous AI travel agent that plans realistic, budgeted, day-by-day trip
itineraries by reasoning over flight, hotel, and attraction data and a live
weather API — built with **LangChain**, **Vercel Serverless Functions**, and **Google Gemini / Claude / GPT**.

This implements the capstone brief end-to-end: LangChain tools for flights,
hotels, places, weather, and budget; a tool-calling agent that autonomously
decides which tools to call and in what order; a modern responsive Web SPA UI, and a CLI.

---

## ✨ Features

| Requirement (from project brief)            | Implementation |
|---------------------------------------------|----------------|
| Netlify Serverless Backend                  | `netlify/functions/plan.py` — Serverless AI agent with 6-key Google Gemini failover rotation |
| Modern Web UI (Netlify)                     | `public/` (`index.html`, `style.css`, `app.js`) — Luxury glassmorphic responsive SPA |
| Interactive Map                             | `Leaflet.js` & `Folium` — visual route lines, hotel marker & day-wise attraction pins |
| Multi-Modal Transport                       | Flights, Trains (Vande Bharat / Express), and Luxury Sleeper Buses |
| 1-Click Booking Action Bar                  | Instant links for Google Flights, MakeMyTrip, Skyscanner, Booking.com, Agoda, IRCTC, RedBus |
| Export & Calendar Sync                      | Instant `.ics` calendar sync & styled printable PDF generation |
| Fast Corridor Knowledge Base                | Built-in high-speed corridors (Delhi-Goa, Delhi-Mumbai, etc.) for instant lookup |
| Flight & Transit Search Tool                | `src/tools/flight_tool.py` & `src/tools/web_search_tool.py` |
| Hotel Recommendation Tool                   | `src/tools/hotel_tool.py` — filters `hotels.json` & live fallback |
| Places Discovery Tool                       | `src/tools/places_tool.py` — filters `places.json` & POIs |
| Weather Lookup Tool                         | `src/tools/weather_tool.py` — live daily forecast via Open-Meteo |
| Budget Estimation Tool                      | `src/tools/budget_tool.py` — flight/transit + hotel×nights + daily expenses |
| Vercel Serverless Backend                   | `api/plan.py` — Serverless Python function |
| Local Server Simulator                      | `dev_server.py` |

---

## 📁 Project Structure

```
travel-planning-assistant/
├── netlify.toml                # Netlify deployment configuration & redirects
├── netlify/
│   └── functions/
│       ├── plan.py             # Serverless Python function (AI trip planning API)
│       └── requirements.txt    # Netlify lambda dependencies
├── public/                     # Netlify static publish folder (Modern Web UI)
│   ├── index.html              # Single-page application structure
│   ├── css/style.css           # Luxury dark glassmorphism styling
│   └── js/app.js               # Leaflet map, .ics calendar, and streaming controller
├── dev_server.py               # Local server simulating serverless environment (port 8888)
├── cli.py                      # Command-line interface
├── requirements.txt
├── data/                       # Offline fallback datasets (flights, hotels, places)
├── src/                        # Core agent, services, and search tools
│   ├── agent.py                # LangChain agent + 6-key Google Gemini rotation pool
│   ├── services/
│   │   ├── booking_service.py  # 1-click booking links generator
│   │   └── export_service.py   # PDF and Calendar (.ics) export engine
│   └── tools/                  # Flight, Hotel, Places, Weather, Budget, Web Search tools
└── tests/
    ├── test_netlify_function.py # Tests for Netlify serverless endpoints
    ├── test_services.py        # Tests for booking, PDF, and calendar exports
    └── test_tools.py           # Unit tests for search tools
```

---

## ☁️ Deploying to Netlify

Deploying this application to **Netlify** takes under 2 minutes:

### Option 1: Connect Git Repository (Recommended)
1. Push this repository to **GitHub** (or GitLab / Bitbucket).
2. Go to your [Netlify Dashboard](https://app.netlify.com) and click **"Add new site" > "Import an existing project"**.
3. Select your repository.
4. Netlify will automatically detect the settings from [`netlify.toml`](./netlify.toml):
   - **Publish directory:** `public`
   - **Functions directory:** `netlify/functions`
5. Click **"Environment variables"** and add:
   - `GOOGLE_API_KEYS` = your comma-separated Google Gemini API keys (or use the built-in 6-key pool)
6. Click **Deploy Site**! Your web app and serverless API are live!

### Option 2: Deploy via Netlify CLI
```bash
# Install Netlify CLI globally
npm install -g netlify-cli

# Login and deploy
ntl login
ntl init
ntl deploy --prod
```

### Local Testing with Simulator
You can preview the exact environment locally without pushing:
```bash
python dev_server.py
```
Open **http://localhost:8888** in your browser.

---

## ▲ Deploying to Vercel

Deploying to **Vercel** is seamless:

1. Push your changes to **GitHub**.
2. Go to your [Vercel Dashboard](https://vercel.com/new) and import your repository.
3. Vercel reads [`vercel.json`](./vercel.json) and [`.vercelignore`](./.vercelignore):
   - **Frontend:** Automatically serves the glassmorphic web UI in `public/`
   - **Backend API:** Deploys `api/plan.py` as a Python Serverless Function on `/api/plan`
4. In **Project Settings → Environment Variables**, add:
   - `GOOGLE_API_KEYS` = your Google Gemini API key(s)
5. Click **Deploy**!

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
   Edit `.env` and set **one** of these (checked in this order):
   - `GOOGLE_API_KEY` — **genuinely free**, no credit card, no expiry. Get
     one at [aistudio.google.com/apikey](https://aistudio.google.com/apikey).
     Uses Gemini 2.5 Flash by default. **Recommended if you just want to
     run this project without paying for anything.**
   - `ANTHROPIC_API_KEY` — Claude (paid, used only if `GOOGLE_API_KEY` isn't set)
   - `OPENAI_API_KEY` — GPT (paid, used only if neither of the above is set)

   No key is required for the Weather tool — Open-Meteo is free and keyless.

   > **Why does the LLM need a key if the project brief says "no API key
   > required"?** That line in the brief refers specifically to the
   > **Weather** API (Open-Meteo) — and this project honors that exactly;
   > `get_weather_forecast` never needs any credentials. The *agent's
   > reasoning* is a separate thing: an "agentic AI" system is, by
   > definition, powered by an LLM, and every LLM provider requires some
   > form of API key to call it. Google's Gemini free tier is the closest
   > thing to "no key needed" in practice — it's free forever with no card
   > on file, just a Google account.

4. **Run the tests** (fast, no API key required — they only exercise the
   local dataset tools):
   ```bash
   python -m pytest tests/ -v
   ```

5. **Run the local Web UI server**
   ```bash
   python dev_server.py
   ```
   Open **http://localhost:8888** in your browser.

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
- **Swap the LLM provider**: `src/agent.py::get_llm()` checks
  `GOOGLE_API_KEY` → `ANTHROPIC_API_KEY` → `OPENAI_API_KEY` in that order —
  add another `elif` branch for a different provider (e.g. Groq).
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
