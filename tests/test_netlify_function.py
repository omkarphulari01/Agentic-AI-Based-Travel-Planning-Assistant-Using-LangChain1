"""Unit test for Netlify Serverless Function handler."""

import json
from netlify.functions.plan import handler


def test_netlify_handler_options():
    """Verify OPTIONS pre-flight request handles CORS properly."""
    event = {
        "httpMethod": "OPTIONS",
        "headers": {},
        "body": "",
    }
    response = handler(event, None)
    assert response["statusCode"] == 200
    assert response["headers"]["Access-Control-Allow-Origin"] == "*"
    body = json.loads(response["body"])
    assert body["status"] == "ok"


def test_netlify_handler_post_structure():
    """Verify POST request returns itinerary, map coordinates, and booking links."""
    event = {
        "httpMethod": "POST",
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "origin": "Delhi",
            "destination": "Goa",
            "start_date": "2026-03-15",
            "end_date": "2026-03-18",
            "budget": 20000,
            "travelers": 2,
            "transport_mode": "All Options (Recommended)",
            "interests": "Beaches and Seafood",
        }),
    }
    response = handler(event, None)
    assert response["statusCode"] == 200
    assert response["headers"]["Access-Control-Allow-Origin"] == "*"
    
    data = json.loads(response["body"])
    assert data["success"] is True
    assert "itinerary" in data and len(data["itinerary"]) > 50
    assert "booking_links" in data
    assert "Flights" in data["booking_links"]
    assert "Hotels" in data["booking_links"]
    assert "Trains" in data["booking_links"]
    assert "Buses" in data["booking_links"]

    # Verify map coordinates
    assert "map_data" in data
    assert "origin" in data["map_data"]
    assert data["map_data"]["origin"]["name"] == "Delhi"
    assert "destination" in data["map_data"]
    assert data["map_data"]["destination"]["name"] == "Goa"
    assert "hotel" in data["map_data"]
    assert "attractions" in data["map_data"]
