"""Geocode addresses to lat/lon coordinates."""
from __future__ import annotations

import requests

from .config import (
    CENSUS_GEOCODER_URL,
    GOOGLE_GEOCODING_KEY,
    GOOGLE_GEOCODING_URL,
    NOMINATIM_URL,
    NOMINATIM_USER_AGENT,
)


def _geocode_google(address: str) -> tuple[float, float] | None:
    """Try Google Geocoding API first (best fuzzy matching)."""
    if not GOOGLE_GEOCODING_KEY:
        return None
    resp = requests.get(
        GOOGLE_GEOCODING_URL,
        params={"address": address, "key": GOOGLE_GEOCODING_KEY},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "OK" or not data.get("results"):
        return None
    loc = data["results"][0]["geometry"]["location"]
    return float(loc["lat"]), float(loc["lng"])


def _geocode_nominatim(address: str) -> tuple[float, float] | None:
    """Try Nominatim (OpenStreetMap)."""
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


def _geocode_census(address: str) -> tuple[float, float] | None:
    """Fallback to US Census Bureau geocoder."""
    resp = requests.get(
        CENSUS_GEOCODER_URL,
        params={
            "address": address,
            "benchmark": "Public_AR_Current",
            "format": "json",
        },
        timeout=10,
    )
    resp.raise_for_status()
    matches = resp.json().get("result", {}).get("addressMatches", [])
    if not matches:
        return None
    coords = matches[0]["coordinates"]
    return float(coords["y"]), float(coords["x"])


def geocode_address(address: str) -> tuple[float, float] | None:
    """Geocode an address to (latitude, longitude).

    Tries Google first, falls back to Nominatim, then US Census.
    Returns None if all fail.
    """
    for geocoder in (_geocode_google, _geocode_nominatim, _geocode_census):
        try:
            result = geocoder(address)
            if result:
                return result
        except Exception:
            continue
    return None
