"""Constants, API endpoints, and configuration."""

import os

# --- API Keys ---
APIFY_API_KEY = os.environ.get("APIFY_API_KEY", "")
GOOGLE_GEOCODING_KEY = os.environ.get("GOOGLE_GEOCODING_KEY", "")

# --- Apify Actors ---
ZILLOW_DETAIL_ACTOR = "maxcopell/zillow-detail-scraper"
ZILLOW_SEARCH_ACTOR = "maxcopell/zillow-scraper"

# --- ArcGIS Endpoints ---
TCEQ_WATER_DISTRICTS_URL = (
    "https://harcags.harcresearch.org/arcgisserver/rest/services"
    "/Boundaries/TCEQ_Water_Districts/MapServer/0/query"
)
HCAD_MUD_URL = (
    "https://www.gis.hctx.net/arcgis/rest/services"
    "/HCAD/HCAD_MUD/MapServer/0/query"
)
FBCAD_MUD_URL = (
    "https://gisweb.fortbendcountytx.gov/arcgis/rest/services"
    "/General/Water_Districts/MapServer/4/query"
)

# --- Geocoding ---
GOOGLE_GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_USER_AGENT = "property-lookup/0.1 (BCG Ventures)"
CENSUS_GEOCODER_URL = (
    "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
)

# --- TCEQ District Types We Care About ---
DISTRICT_TYPES_OF_INTEREST = {
    "Municipal Utility District",
    "Drainage District",
    "Water Control & Improvement District",
    "River Authority",
    "Regional District",
    "Fresh Water Supply District",
    "Special Utility District",
    "Municipal Management District",
}

# --- Zillow Output Fields (normalized keys) ---
ZILLOW_PROPERTY_FIELDS = [
    "address", "city", "state", "zip", "county", "subdivision",
    "parcelId", "latitude", "longitude",
]
ZILLOW_DETAIL_FIELDS = [
    "beds", "baths", "sqft", "lotSize", "yearBuilt", "homeType", "description",
]
ZILLOW_FINANCIAL_FIELDS = [
    "price", "zestimate", "rentZestimate", "hoaFeeMonthly",
    "taxRate", "taxAssessedValue", "annualInsurance",
]
ZILLOW_AGENT_FIELDS = [
    "agentName", "agentPhone", "agentLicense", "brokerName", "mlsId",
]

# --- Apify Timeouts ---
APIFY_TIMEOUT_SECS = 120
