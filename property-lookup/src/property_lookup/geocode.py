"""Geocode addresses to lat/lon coordinates."""
from __future__ import annotations

import requests

from .config import NOMINATIM_URL, NOMINATIM_USER_AGENT


def geocode_address(address: str) -> tuple[float, float] | None:
    """Geocode an address to (latitude, longitude) via Nominatim.

    Returns None if geocoding fails.
    """
    resp = requests.get(
        NOMINATIM_URL,
        params={"q": address, "format": "json", "limit": 1, "countrycodes": "us"},
        headers={"User-Agent": NOMINATIM_USER_AGENT},
        timeout=10,
    )
    resp.raise_for_status()
    results = resp.json()
    if not results:
        return None
    return float(results[0]["lat"]), float(results[0]["lon"])
