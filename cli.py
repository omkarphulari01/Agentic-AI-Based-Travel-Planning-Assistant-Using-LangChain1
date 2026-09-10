#!/usr/bin/env python3
"""Command-line interface for the Agentic AI Travel Planning Assistant.

Usage:
    python cli.py "Plan a 3-day trip from Delhi to Goa starting 2026-02-12"
    python cli.py            # interactive mode, prompts for input
"""

from __future__ import annotations

import sys

from dotenv import load_dotenv

from src.agent import plan_trip

load_dotenv()


def main() -> None:
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        print("Agentic AI Travel Planning Assistant (CLI)")
        print("Describe your trip (source, destination, dates, preferences):\n")
        query = input("> ").strip()

    if not query:
        print("No query provided. Exiting.")
        return

    print("\nPlanning your trip... (the agent may call several tools)\n")
    try:
        itinerary = plan_trip(query, verbose=True)
    except RuntimeError as exc:
        print(f"\nConfiguration error: {exc}")
        return
    except Exception as exc:  # noqa: BLE001 - top-level CLI error boundary
        print(f"\nSomething went wrong while planning your trip: {exc}")
        return

    print("\n" + "=" * 60)
    print(itinerary)
    print("=" * 60)


if __name__ == "__main__":
    main()
