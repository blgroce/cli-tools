"""Geocode addresses to lat/lon coordinates."""
from __future__ import annotations

import requests

from .config import CENSUS_GEOCODER_URL, NOMINATIM_URL, NOMINATIM_USER_AGENT


def _geocode_nominatim(address: str) -> tuple[float, float] | None:
    """Try Nominatim (OpenStreetMap) first."""
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

    Tries Nominatim first, falls back to US Census geocoder.
    Returns None if both fail.
    """
    result = _geocode_nominatim(address)
    if result:
        return result
    return _geocode_census(address)
