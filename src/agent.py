"""Agentic core: builds a LangChain tool-calling agent that autonomously
plans a trip using the Flight, Hotel, Places, Weather, and Budget tools.

Supports Google Gemini (with multi-key pool & automatic failover rotation),
Anthropic (Claude), or OpenAI as the underlying LLM.
"""

from __future__ import annotations

import logging
import os
import re
import threading
from typing import Callable

from langchain.agents import create_agent

from src.tools import ALL_TOOLS

logger = logging.getLogger(__name__)

# Default pool of Google API keys - loaded from environment variables
GOOGLE_API_KEYS: list[str] = []

# Thread-safe global key rotation tracker
_KEY_LOCK = threading.Lock()
_KEY_STATE = {"current_index": 0}


def _parse_env_keys(raw: str) -> list[str]:
    """Clean and extract individual API keys from raw environment strings.

    Supports comma-separated strings, newline-separated strings, Python list syntax,
    or JSON array syntax.
    """
    if not raw or not raw.strip():
        return []
    cleaned = raw.strip()
    if "=" in cleaned and "[" in cleaned:
        cleaned = cleaned.split("=", 1)[1].strip()
    cleaned = cleaned.strip("[]()")

    keys: list[str] = []
    for item in re.split(r"[,;\n\r]+", cleaned):
        token = item.strip().strip("\"' \t")
        if token and len(token) > 10 and not token.startswith("#"):
            keys.append(token)
    return keys


def get_google_api_keys() -> list[str]:
    """Return the list of configured Google API keys from env or defaults."""
    env_keys_raw = os.getenv("GOOGLE_API_KEYS", "")
    if env_keys_raw.strip():
        keys = _parse_env_keys(env_keys_raw)
        if keys:
            return keys
    single_key = os.getenv("GOOGLE_API_KEY", "")
    if single_key.strip():
        keys = _parse_env_keys(single_key)
        if keys:
            return keys
    return list(GOOGLE_API_KEYS)


def get_active_google_key() -> str | None:
    """Get the currently active Google API key from the pool."""
    keys = get_google_api_keys()
    if not keys:
        return None
    with _KEY_LOCK:
        idx = _KEY_STATE["current_index"] % len(keys)
        return keys[idx]


def rotate_to_next_google_key() -> tuple[str, int, int]:
    """Rotate to the next Google API key in the pool.

    Returns:
        (new_key, key_index_1_based, total_keys)
    """
    keys = get_google_api_keys()
    if not keys:
        raise RuntimeError("No Google API keys configured.")
    with _KEY_LOCK:
        _KEY_STATE["current_index"] = (_KEY_STATE["current_index"] + 1) % len(keys)
        idx = _KEY_STATE["current_index"]
        key = keys[idx]
        return key, idx + 1, len(keys)


def get_google_key_pool_status() -> dict:
    """Return status details of the Google API keys pool."""
    keys = get_google_api_keys()
    with _KEY_LOCK:
        current_idx = _KEY_STATE["current_index"] % len(keys) if keys else 0
    return {
        "total_keys": len(keys),
        "current_index": current_idx + 1,
        "masked_current_key": f"{keys[current_idx][:6]}...{keys[current_idx][-4:]}" if keys else "None",
    }


SYSTEM_PROMPT = """\
You are an expert AI travel-planning agent. You help users design realistic,
budget-aware, day-by-day trip itineraries by autonomously calling the tools
available to you:

- search_flights: find and rank flights between two cities (with real-time web discovery fallback)
- search_hotels: find and rank hotels in the destination city (with real-time web discovery fallback)
- search_places: find top-rated attractions/POIs in the destination city (with real-time web discovery fallback)
- get_weather_forecast: fetch live daily weather forecast for any global city
- estimate_budget: total up flight + hotel + daily expenses
- search_live_travel_info: search real-time Google/web information for best travel ways, transit comparisons (flight vs high-speed train/Vande Bharat vs road), and insider tips

PERFORMANCE & PARALLEL EXECUTION:
To ensure ultra-fast processing, call all independent search tools IN PARALLEL on your very first turn:
Invoke `search_flights`, `search_hotels`, `search_places`, `get_weather_forecast`, and `search_live_travel_info` SIMULTANEOUSLY in a single step.
Once you receive their outputs, immediately call `estimate_budget` (or calculate it directly) and generate the final itinerary. Do NOT make separate sequential round-trips for each tool.

WORKFLOW you must follow for every trip-planning request:
1. Identify source city, destination city, trip start date, and number of
   days from the user's message. If something critical is missing (e.g. no
   destination), ask a single concise clarifying question instead of
   guessing.
2. In your FIRST turn, issue parallel tool calls for:
   - search_flights(source, destination)
   - search_hotels(destination, min_stars, ...)
   - search_places(destination, ...)
   - get_weather_forecast(destination, start_date, num_days)
   - search_live_travel_info(destination=destination, source=source)
3. In your SECOND turn, call estimate_budget using the selected flight and hotel prices.
4. Assemble everything into a FINAL structured itinerary in this exact
   layout (use the real numbers/names from the tool results, in INR ₹):


Your {num_days}-Day Trip to {destination} ({date_range})

Flight Selected:
- <Airline> (₹<price>) – Departs <source> at <HH:MM>

Hotel Booked:
- <Hotel name> (₹<price_per_night>/night, <stars>-star)

Weather:
- Day 1: <condition> (<temp>°C)
- Day 2: ...

Best Way to Travel & Route Tips:
- <Comparison of direct flights, express train/Vande Bharat, or road options, duration, and top insider recommendation>

Itinerary:
Day 1: <Place A>, <Place B>
Day 2: ...

Estimated Total Budget:
- Flight: ₹<flight_cost_total>
- Hotel: ₹<hotel_cost_total>
- Food & Travel: ₹<food_and_local_travel_total>
-------------------------------------
Total Cost: ₹<estimated_total_budget>

Why We Picked This:
- <1-3 short bullet points justifying the flight/hotel/places choices>

RULES:
- Never fabricate flight, hotel, or place data — only use what the tools
  return. If a tool returns an error or no results, tell the user plainly
  and suggest an alternative (different city name, relaxed filters, etc.).
- If live weather isn't available for the requested date, say so instead
  of inventing a forecast.
- Keep the tone helpful and concise. Always end with the structured
  itinerary format above once you have enough information.
"""



def get_llm(google_api_key: str | None = None):
    """Instantiate the chat model based on available environment variables or key pool.

    Checks providers in this order:
      1. Google Gemini (using active key in key pool or provided key)
      2. ANTHROPIC_API_KEY -> Claude
      3. OPENAI_API_KEY   -> GPT
    """
    key = google_api_key or get_active_google_key()
    if key:
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=os.getenv("GOOGLE_MODEL", "gemini-3.5-flash-lite"),
            api_key=key,
            temperature=0.2,
        )
    if os.getenv("ANTHROPIC_API_KEY"):
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
            temperature=0.2,
        )
    if os.getenv("OPENAI_API_KEY"):
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.2,
        )
    raise RuntimeError(
        "No LLM API key found. Set GOOGLE_API_KEYS (or GOOGLE_API_KEY), "
        "ANTHROPIC_API_KEY, or OPENAI_API_KEY in your environment "
        "(see .env.example)."
    )


def build_agent_executor(verbose: bool = False, google_api_key: str | None = None):
    """Construct the tool-calling agent (LangGraph-based, LangChain >= 1.0)
    with all five travel tools attached.
    """
    llm = get_llm(google_api_key=google_api_key)
    return create_agent(
        model=llm,
        tools=ALL_TOOLS,
        system_prompt=SYSTEM_PROMPT,
        debug=verbose,
    )


def _extract_text(content) -> str:
    """Normalize a chat model's message content into a plain string."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        pieces = []
        for item in content:
            if isinstance(item, str):
                pieces.append(item)
            elif isinstance(item, dict):
                text_piece = item.get("text")
                if isinstance(text_piece, str):
                    pieces.append(text_piece)
        return "".join(p for p in pieces if p)
    return str(content) if content is not None else ""


def plan_trip(
    user_query: str,
    verbose: bool = False,
    status_callback: Callable[[str], None] | None = None,
) -> str:
    """Run the agent end-to-end on a natural-language trip request.

    If token exhaustion, quota limit (429 / ResourceExhausted), or API errors
    occur, automatically rotates through the configured GOOGLE_API_KEYS pool
    one after another until a successful response is generated.

    Args:
        user_query: e.g. "Plan a 3-day trip from Delhi to Goa starting 2026-02-12"
        verbose: If True, prints the agent's intermediate tool-calling steps.
        status_callback: Optional callable to report key rotation status updates.

    Returns:
        The agent's final structured itinerary as plain text.
    """
    # If other non-Google providers are explicitly preferred without Google keys
    if not get_google_api_keys() and (os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")):
        executor = build_agent_executor(verbose=verbose)
        result = executor.invoke({"messages": [{"role": "user", "content": user_query}]})
        final_message = result["messages"][-1]
        return _extract_text(getattr(final_message, "content", final_message))

    keys_pool = get_google_api_keys()
    num_keys = len(keys_pool)
    with _KEY_LOCK:
        start_idx = _KEY_STATE["current_index"] % num_keys

    last_error: Exception | None = None

    for attempt in range(num_keys):
        current_idx = (start_idx + attempt) % num_keys
        current_key = keys_pool[current_idx]

        with _KEY_LOCK:
            _KEY_STATE["current_index"] = current_idx

        masked_key = f"{current_key[:6]}...{current_key[-4:]}"
        if attempt > 0:
            msg = f"[Key Pool] Switched to Google API key #{current_idx + 1}/{num_keys} ({masked_key})"
            logger.info(msg)
            if status_callback:
                status_callback(f"🔄 Switched to Google API key #{current_idx + 1}/{num_keys} ({masked_key})")

        try:
            executor = build_agent_executor(verbose=verbose, google_api_key=current_key)
            result = executor.invoke({"messages": [{"role": "user", "content": user_query}]})
            final_message = result["messages"][-1]
            return _extract_text(getattr(final_message, "content", final_message))
        except Exception as exc:
            last_error = exc
            err_str = str(exc)
            logger.warning(
                "Google API key #%d (%s) failed with: %s",
                current_idx + 1,
                masked_key,
                err_str,
            )
            continue

    raise RuntimeError(
        f"All {num_keys} Google API keys exhausted or returned errors. Last error encountered: {last_error}"
    )
