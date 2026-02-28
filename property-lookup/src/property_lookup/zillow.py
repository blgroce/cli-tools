"""Zillow property data via Apify actors."""
from __future__ import annotations

import re
from typing import Any

from apify_client import ApifyClient

from .config import (
    APIFY_API_KEY,
    ZILLOW_DETAIL_ACTOR,
    ZILLOW_SEARCH_ACTOR,
    APIFY_TIMEOUT_SECS,
)


class ZillowError(Exception):
    pass


def _get_client() -> ApifyClient:
    if not APIFY_API_KEY:
        raise ZillowError("APIFY_API_KEY not set. Source ~/assistant/.env first.")
    return ApifyClient(token=APIFY_API_KEY)


def _extract_zpid_from_url(url: str) -> str | None:
    """Extract ZPID from a Zillow homedetails URL."""
    match = re.search(r"/(\d+)_zpid", url)
    return match.group(1) if match else None


def _normalize_zillow_data(item: dict[str, Any]) -> dict[str, Any]:
    """Normalize raw Zillow detail response to a clean structure."""
    addr = item.get("address") or {}
    reso = item.get("resoFacts") or {}

    # Extract schools
    schools = []
    for s in (item.get("schools") or []):
        schools.append({
            "name": s.get("name"),
            "type": s.get("type"),
            "rating": s.get("rating"),
            "distance": s.get("distance"),
        })

    # Extract price history (last 10)
    price_history = []
    for ph in (item.get("priceHistory") or [])[:10]:
        price_history.append({
            "date": ph.get("date"),
            "price": ph.get("price"),
            "event": ph.get("event"),
            "pricePerSqft": ph.get("pricePerSquareFoot"),
        })

    # Extract photo URLs (largest jpeg, max 10)
    photos = []
    for p in (item.get("originalPhotos") or item.get("responsivePhotos") or [])[:10]:
        sources = (p.get("mixedSources") or {}).get("jpeg") or []
        if sources:
            photos.append(sources[-1].get("url"))

    # Agent info from attributionInfo
    attr = item.get("attributionInfo") or {}

    return {
        "property": {
            "address": addr.get("streetAddress"),
            "city": addr.get("city"),
            "state": addr.get("state"),
            "zip": addr.get("zipcode"),
            "county": item.get("county"),
            "subdivision": addr.get("subdivision"),
            "parcelId": item.get("parcelId"),
            "latitude": item.get("latitude"),
            "longitude": item.get("longitude"),
        },
        "details": {
            "beds": item.get("bedrooms"),
            "baths": item.get("bathrooms"),
            "sqft": item.get("livingArea"),
            "lotSize": item.get("lotSize"),
            "yearBuilt": item.get("yearBuilt"),
            "homeType": item.get("homeType"),
            "homeStatus": item.get("homeStatus"),
            "description": item.get("description"),
        },
        "financials": {
            "price": item.get("price"),
            "zestimate": item.get("zestimate"),
            "rentZestimate": item.get("rentZestimate"),
            "hoaFeeMonthly": item.get("monthlyHoaFee"),
            "taxRate": item.get("propertyTaxRate"),
            "taxAssessedValue": reso.get("taxAssessedValue"),
            "taxAnnualAmount": reso.get("taxAnnualAmount"),
            "annualInsurance": item.get("annualHomeownersInsurance"),
        },
        "agent": {
            "agentName": attr.get("agentName"),
            "agentPhone": attr.get("agentPhoneNumber"),
            "agentLicense": attr.get("agentLicenseNumber"),
            "brokerName": attr.get("brokerName"),
            "mlsId": item.get("mlsid"),
            "mlsName": attr.get("mlsName"),
        },
        "schools": schools,
        "priceHistory": price_history,
        "photos": photos,
        "zpid": item.get("zpid"),
        "url": f"https://www.zillow.com{item.get('hdpUrl', '')}",
    }


def lookup_by_zpid(zpid: str | int) -> dict[str, Any]:
    """Look up full property details by Zillow ZPID."""
    client = _get_client()
    url = f"https://www.zillow.com/homedetails/{zpid}_zpid/"

    run = client.actor(ZILLOW_DETAIL_ACTOR).call(
        run_input={"startUrls": [{"url": url}]},
        timeout_secs=APIFY_TIMEOUT_SECS,
    )

    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    if not items:
        raise ZillowError(f"No data returned for ZPID {zpid}")

    item = items[0]
    if not item.get("isValid", True) is True and item.get("invalidReason"):
        raise ZillowError(f"Invalid result: {item.get('invalidReason')}")

    return _normalize_zillow_data(item)


def lookup_by_url(zillow_url: str) -> dict[str, Any]:
    """Look up full property details by Zillow URL."""
    client = _get_client()

    run = client.actor(ZILLOW_DETAIL_ACTOR).call(
        run_input={"startUrls": [{"url": zillow_url}]},
        timeout_secs=APIFY_TIMEOUT_SECS,
    )

    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    if not items:
        raise ZillowError(f"No data returned for URL: {zillow_url}")

    item = items[0]
    if item.get("isValid") is False:
        raise ZillowError(f"Invalid result: {item.get('invalidReason', 'unknown')}")

    return _normalize_zillow_data(item)


def search_by_address(address: str) -> dict[str, Any]:
    """Search Zillow for a property by address, then pull full details.

    Two-step process:
    1. Area search to find the ZPID
    2. Detail scrape for full data
    """
    client = _get_client()

    # Build a tight search URL. The scraper needs a Zillow URL with searchQueryState.
    # We'll construct a search that should return the property.
    # The search actor uses map bounds, so we need to geocode first to create bounds.
    from .geocode import geocode_address

    coords = geocode_address(address)
    if not coords:
        raise ZillowError(
            f"Could not geocode address: {address}. "
            "Try using --zpid or --url instead."
        )

    lat, lon = coords
    # Create tight bounding box (~0.5 mile radius)
    delta = 0.008  # ~0.5 miles
    bounds = {
        "west": lon - delta,
        "east": lon + delta,
        "south": lat - delta,
        "north": lat + delta,
    }

    search_url = (
        f"https://www.zillow.com/homes/{lat},{lon}_rb/"
        f"?searchQueryState=%7B%22mapBounds%22%3A%7B"
        f"%22west%22%3A{bounds['west']}%2C"
        f"%22east%22%3A{bounds['east']}%2C"
        f"%22south%22%3A{bounds['south']}%2C"
        f"%22north%22%3A{bounds['north']}"
        f"%7D%2C%22filterState%22%3A%7B%7D%7D"
    )

    run = client.actor(ZILLOW_SEARCH_ACTOR).call(
        run_input={
            "searchUrls": [{"url": search_url}],
            "maxItems": 50,
        },
        timeout_secs=APIFY_TIMEOUT_SECS,
    )

    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    if not items:
        raise ZillowError(f"No Zillow listings found near: {address}")

    # Find the best match by address similarity
    addr_lower = address.lower().split(",")[0].strip()
    best_match = None
    best_score = 0

    for item in items:
        item_addr = (item.get("addressStreet") or item.get("address") or "").lower()
        # Simple word overlap scoring
        addr_words = set(addr_lower.split())
        item_words = set(item_addr.split())
        overlap = len(addr_words & item_words)
        if overlap > best_score:
            best_score = overlap
            best_match = item

    if not best_match or best_score < 2:
        # Return the closest one with a warning
        best_match = items[0]

    zpid = best_match.get("zpid")
    if not zpid:
        raise ZillowError("Found listings but no ZPID available")

    # Now get full details
    return lookup_by_zpid(str(zpid))
