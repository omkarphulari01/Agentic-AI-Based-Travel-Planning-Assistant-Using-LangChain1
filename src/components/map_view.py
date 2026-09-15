"""Interactive Map Component using Folium and Streamlit.

Visualizes:
- Flight / Route path from source city to destination city.
- Hotel pin with nightly rate and star rating.
- Color-coded pins for each day's sightseeing attractions.
"""

from __future__ import annotations

import folium
from src.utils import get_city_coordinates


DAY_COLORS = ["green", "blue", "purple", "orange", "darkred", "cadetblue", "darkgreen"]


def create_itinerary_map(
    source: str,
    destination: str,
    hotel_info: str | None = None,
    itinerary_days: list[tuple[str, list[str]]] | None = None,
) -> folium.Map:
    """Construct an interactive Folium map for the trip."""
    src_coords = get_city_coordinates(source) or (28.6139, 77.2090)
    dst_coords = get_city_coordinates(destination) or (15.2993, 74.1240)

    # Center map midway between source and destination or focused on destination
    mid_lat = (src_coords[0] + dst_coords[0]) / 2.0
    mid_lon = (src_coords[1] + dst_coords[1]) / 2.0

    m = folium.Map(
        location=[dst_coords[0], dst_coords[1]],
        zoom_start=11,
        tiles="OpenStreetMap",
        control_scale=True,
    )


    # 1. Source Origin Marker
    folium.Marker(
        location=list(src_coords),
        popup=f"<b>🛫 Departure: {source.title()}</b>",
        tooltip=f"Origin: {source.title()}",
        icon=folium.Icon(color="red", icon="plane", prefix="fa"),
    ).add_to(m)

    # 2. Destination Marker
    folium.Marker(
        location=list(dst_coords),
        popup=f"<b>🎯 Destination: {destination.title()}</b>",
        tooltip=f"Destination: {destination.title()}",
        icon=folium.Icon(color="darkblue", icon="flag", prefix="fa"),
    ).add_to(m)

    # 3. Route Line connecting Source and Destination
    folium.PolyLine(
        locations=[list(src_coords), list(dst_coords)],
        color="#3b82f6",
        weight=3.5,
        opacity=0.8,
        dash_array="8, 12",
        tooltip=f"Travel Route: {source.title()} ➔ {destination.title()}",
    ).add_to(m)

    # 4. Hotel Marker (slightly offset from destination center)
    hotel_coords = [dst_coords[0] + 0.008, dst_coords[1] - 0.008]
    hotel_text = hotel_info or f"Hotel in {destination.title()}"
    folium.Marker(
        location=hotel_coords,
        popup=f"<b>🏨 Accommodation:</b><br>{hotel_text}",
        tooltip=f"Hotel: {hotel_text.split('(')[0].strip()}",
        icon=folium.Icon(color="pink", icon="bed", prefix="fa"),
    ).add_to(m)

    # 5. Day-wise Attraction Pins
    if itinerary_days:
        offsets = [
            (0.015, 0.012), (-0.012, 0.018), (0.022, -0.015),
            (-0.018, -0.020), (0.009, 0.025), (-0.025, 0.010),
            (0.030, 0.005), (-0.015, 0.032), (0.018, -0.028),
        ]
        offset_idx = 0
        for day_idx, (day_label, places) in enumerate(itinerary_days):
            color = DAY_COLORS[day_idx % len(DAY_COLORS)]
            for place in places:
                off_lat, off_lon = offsets[offset_idx % len(offsets)]
                place_lat = dst_coords[0] + off_lat
                place_lon = dst_coords[1] + off_lon
                offset_idx += 1

                folium.Marker(
                    location=[place_lat, place_lon],
                    popup=f"<b>{day_label}:</b><br>{place}",
                    tooltip=f"{day_label}: {place}",
                    icon=folium.Icon(color=color, icon="map-marker", prefix="fa"),
                ).add_to(m)

    return m
