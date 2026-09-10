"""Agentic core: builds a LangChain tool-calling agent that autonomously
plans a trip using the Flight, Hotel, Places, Weather, and Budget tools.

Supports Anthropic (Claude) or OpenAI as the underlying LLM, selected via
environment variables, so the project isn't locked to a single provider.
"""

from __future__ import annotations

import os

from langchain.agents import create_agent

from src.tools import ALL_TOOLS

SYSTEM_PROMPT = """\
You are an expert AI travel-planning agent. You help users design realistic,
budget-aware, day-by-day trip itineraries by autonomously calling the tools
available to you:

- search_flights: find and rank flights between two cities
- search_hotels: find and rank hotels in the destination city
- search_places: find top-rated attractions/POIs in the destination city
- get_weather_forecast: fetch a live daily forecast for the destination
- estimate_budget: total up flight + hotel + daily expenses

WORKFLOW you must follow for every trip-planning request:
1. Identify source city, destination city, trip start date, and number of
   days from the user's message. If something critical is missing (e.g. no
   destination), ask a single concise clarifying question instead of
   guessing.
2. Call search_flights to find a flight from source -> destination. Prefer
   the cheapest option unless the user asked to prioritize speed.
3. Call search_hotels for the destination city, respecting any stated
   budget, star rating, or amenity preferences.
4. Call search_places for the destination city to gather enough attractions
   to fill each day (roughly 2 per day), preferring higher-rated places and
   variety of types.
5. Call get_weather_forecast for the destination and trip dates.
6. Call estimate_budget using the selected flight price, hotel
   price_per_night, and number of nights (and num_travelers if given).
7. Assemble everything into a FINAL structured itinerary in this exact
   layout (use the real numbers/names from the tool results, in INR ₹):

Your {num_days}-Day Trip to {destination} ({date_range})

Flight Selected:
- <Airline> (₹<price>) – Departs <source> at <HH:MM>

Hotel Booked:
- <Hotel name> (₹<price_per_night>/night, <stars>-star)

Weather:
- Day 1: <condition> (<temp>°C)
- Day 2: ...

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


def get_llm():
    """Instantiate the chat model based on available environment variables.

    Checks providers in this order and uses whichever key is set first:
      1. GOOGLE_API_KEY  -> Gemini (genuinely free tier via Google AI Studio,
         no credit card needed — the easiest zero-cost option for this
         project; see README "Free API key options")
      2. ANTHROPIC_API_KEY -> Claude
      3. OPENAI_API_KEY   -> GPT

    Raises a clear error if none are configured.
    """
    if os.getenv("GOOGLE_API_KEY"):
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=os.getenv("GOOGLE_MODEL", "gemini-2.5-flash"),
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
        "No LLM API key found. Set GOOGLE_API_KEY (free — see README), "
        "ANTHROPIC_API_KEY, or OPENAI_API_KEY in your environment "
        "(see .env.example)."
    )


def build_agent_executor(verbose: bool = False):
    """Construct the tool-calling agent (LangGraph-based, LangChain >= 1.0)
    with all five travel tools attached.

    The `verbose` flag enables LangGraph debug logging of each step
    (model call -> tool call -> tool result -> ...), which is useful for
    demonstrating the agent's multi-step reasoning ("Why we selected
    this?") during a live demo.
    """
    llm = get_llm()
    return create_agent(
        model=llm,
        tools=ALL_TOOLS,
        system_prompt=SYSTEM_PROMPT,
        debug=verbose,
    )


def _extract_text(content) -> str:
    """Normalize a chat model's message content into a plain string.

    Different providers (and even different Gemini model generations)
    represent `AIMessage.content` differently: sometimes a plain string,
    sometimes a list of content blocks (e.g. `{"type": "text", "text": ...}`
    dicts, tool/code blocks, etc). This flattens any of those shapes down
    to the text a user should actually read.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        pieces = []
        for item in content:
            if isinstance(item, str):
                pieces.append(item)
            elif isinstance(item, dict):
                # Covers {"type": "text", "text": "..."} and similar shapes;
                # silently skip non-text blocks (tool calls, code, etc).
                text_piece = item.get("text")
                if isinstance(text_piece, str):
                    pieces.append(text_piece)
        return "".join(p for p in pieces if p)
    return str(content) if content is not None else ""


def plan_trip(user_query: str, verbose: bool = False) -> str:
    """Run the agent end-to-end on a natural-language trip request.

    Args:
        user_query: e.g. "Plan a 3-day trip from Delhi to Goa starting 2026-02-12
            with a budget hotel and good beaches."
        verbose: If True, prints the agent's intermediate tool-calling steps.

    Returns:
        The agent's final structured itinerary as plain text.
    """
    executor = build_agent_executor(verbose=verbose)
    result = executor.invoke({"messages": [{"role": "user", "content": user_query}]})
    final_message = result["messages"][-1]
    return _extract_text(getattr(final_message, "content", final_message))
