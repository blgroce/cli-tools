"""Query TCEQ ArcGIS for water districts (MUD, drainage, etc.) at a given point."""
from __future__ import annotations

from typing import Any

import requests

from .config import (
    TCEQ_WATER_DISTRICTS_URL,
    HCAD_MUD_URL,
    FBCAD_MUD_URL,
    DISTRICT_TYPES_OF_INTEREST,
)


def _spatial_query(url: str, lat: float, lon: float, out_fields: str = "*") -> list[dict]:
    """Run a point-in-polygon spatial query against an ArcGIS MapServer."""
    params = {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": out_fields,
        "returnGeometry": "false",
        "f": "json",
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return [f.get("attributes", {}) for f in data.get("features", [])]


def query_tceq_districts(lat: float, lon: float) -> list[dict[str, Any]]:
    """Query statewide TCEQ water district boundaries.

    Returns normalized district records filtered to types of interest.
    """
    fields = "NAME,TYPE_DESCRIPTION,DISTRICT_ID,COUNTY,STATUS_DESCRIPTION,Area_Acres"
    raw = _spatial_query(TCEQ_WATER_DISTRICTS_URL, lat, lon, fields)

    results = []
    for attrs in raw:
        dist_type = attrs.get("TYPE_DESCRIPTION", "")
        if dist_type not in DISTRICT_TYPES_OF_INTEREST:
            continue
        results.append({
            "name": attrs.get("NAME"),
            "type": dist_type,
            "districtId": attrs.get("DISTRICT_ID"),
            "county": attrs.get("COUNTY"),
            "status": attrs.get("STATUS_DESCRIPTION", ""),
            "isActive": "Active" in (attrs.get("STATUS_DESCRIPTION") or ""),
            "acres": attrs.get("Area_Acres"),
        })

    # Sort: MUDs first, then active before inactive
    type_order = {"Municipal Utility District": 0}
    results.sort(key=lambda d: (
        type_order.get(d["type"], 1),
        0 if d["isActive"] else 1,
        d["name"] or "",
    ))
    return results


def query_hcad_muds(lat: float, lon: float) -> list[dict[str, Any]]:
    """Query Harris County-specific MUD boundaries (more current than TCEQ)."""
    try:
        raw = _spatial_query(HCAD_MUD_URL, lat, lon, "*")
    except Exception:
        return []

    return [
        {
            "name": attrs.get("name") or attrs.get("NAME"),
            "type": "Municipal Utility District",
            "source": "HCAD",
        }
        for attrs in raw
    ]


def query_fbcad_muds(lat: float, lon: float) -> list[dict[str, Any]]:
    """Query Fort Bend County-specific MUD boundaries."""
    try:
        raw = _spatial_query(FBCAD_MUD_URL, lat, lon, "*")
    except Exception:
        return []

    return [
        {
            "name": attrs.get("NAME") or attrs.get("name"),
            "type": "Municipal Utility District",
            "source": "FBCAD",
        }
        for attrs in raw
    ]


def lookup_districts(lat: float, lon: float) -> dict[str, Any]:
    """Full district lookup: TCEQ statewide + county-specific if applicable.

    Returns a dict with:
      - districts: list of all districts found
      - mud: the primary MUD name (or null)
      - hasMud: boolean
    """
    districts = query_tceq_districts(lat, lon)

    # Also try county-specific layers for more current data
    county_muds = query_hcad_muds(lat, lon) + query_fbcad_muds(lat, lon)
    if county_muds:
        # Add county-specific MUDs not already in TCEQ results
        tceq_names = {d["name"] for d in districts}
        for cm in county_muds:
            if cm["name"] and cm["name"] not in tceq_names:
                districts.insert(0, {
                    **cm,
                    "districtId": None,
                    "county": None,
                    "status": "Active (county source)",
                    "isActive": True,
                    "acres": None,
                })

    muds = [d for d in districts if d["type"] == "Municipal Utility District" and d["isActive"]]
    primary_mud = muds[0]["name"] if muds else None

    return {
        "districts": districts,
        "mud": primary_mud,
        "hasMud": primary_mud is not None,
        "coordinates": {"latitude": lat, "longitude": lon},
    }
