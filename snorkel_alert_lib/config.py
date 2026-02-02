"""Configuration and spot definitions."""

import os

VERSION = "6.0.0"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
PUSHOVER_USER_KEY = os.getenv("PUSHOVER_USER_KEY", "")
PUSHOVER_API_TOKEN = os.getenv("PUSHOVER_API_TOKEN", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

DEFAULT_SHORE_NORMAL_DEG = 270  # Perth metro beaches generally face west.

CALIBRATIONS = [
    {
        "spot": "Mettams Pool",
        "date": "2026-02-02",
        "waves": "0.44-0.50m",
        "wind": "9-15 km/h",
        "score": 8,
        "notes": "Reef-enclosed lagoon, calm snorkel conditions.",
    },
    {
        "spot": "Watermans Bay",
        "date": "unknown",
        "waves": "unknown",
        "wind": "unknown",
        "score": 8,
        "notes": "Field visit: conditions amazing, around 8/10.",
    },
]

# Each location has:
# - shelter_from: wind/swell directions it's protected from
# - shelter_factor: 0.0-1.0 natural protection level (reef, headland, etc)
# - shore_normal_deg: shoreline orientation (direction out to sea)

SNORKEL_SPOTS = [
    {
        "name": "Mettams Pool",
        "lat": -31.8195,
        "lon": 115.7517,
        "shelter_from": ["W", "SW", "NW"],
        "shelter_factor": 0.8,
        "shore_normal_deg": 270,
        "notes": "Best snorkelling in Perth. Reef-enclosed lagoon, sheltered from W/SW/NW swell. Shallow, beginners welcome.",
    },
    {
        "name": "Hamersley Pool",
        "lat": -31.8150,
        "lon": 115.7510,
        "shelter_from": ["W", "SW", "NW"],
        "shelter_factor": 0.8,
        "shore_normal_deg": 270,
        "notes": "600m north of Mettams. Same conditions, fewer crowds. Reef-enclosed tidal pool.",
    },
    {
        "name": "Watermans Bay",
        "lat": -31.8456,
        "lon": 115.7537,
        "shelter_from": ["W", "SW"],
        "shelter_factor": 0.6,
        "shore_normal_deg": 270,
        "notes": "Partial reef shelter. Quieter than Mettams, good for families.",
    },
    {
        "name": "North Cottesloe",
        "lat": -31.9856,
        "lon": 115.7517,
        "shelter_from": ["E", "NE", "SE"],
        "shelter_factor": 0.3,
        "shore_normal_deg": 270,
        "notes": "Peters Pool area. Good reef snorkelling. Exposed to SW swell.",
    },
    {
        "name": "Boyinaboat Reef",
        "lat": -31.8234,
        "lon": 115.7389,
        "shelter_from": ["W", "SW", "NW", "N"],
        "shelter_factor": 0.7,
        "shore_normal_deg": 270,
        "notes": "Hillarys. Underwater trail with plaques. 6m deep. Marina provides shelter.",
    },
    {
        "name": "Omeo Wreck",
        "lat": -32.1056,
        "lon": 115.7631,
        "shelter_from": ["W", "SW"],
        "shelter_factor": 0.5,
        "shore_normal_deg": 270,
        "notes": "Coogee Maritime Trail. Historic shipwreck 25m from shore. 2.5-5m deep.",
    },
    {
        "name": "Point Peron",
        "lat": -32.2722,
        "lon": 115.6917,
        "shelter_from": ["W", "SW", "NW"],
        "shelter_factor": 0.6,
        "shore_normal_deg": 270,
        "notes": "Rockingham. Garden Island blocks swell. Caves, overhangs, sea life.",
    },
    {
        "name": "Burns Beach",
        "lat": -31.7281,
        "lon": 115.7261,
        "shelter_from": ["W"],
        "shelter_factor": 0.3,
        "shore_normal_deg": 270,
        "notes": "Rocky reef offshore. Less crowded. Better for experienced snorkellers.",
    },
    {
        "name": "Yanchep Lagoon",
        "lat": -31.5469,
        "lon": 115.6350,
        "shelter_from": ["W", "SW", "NW"],
        "shelter_factor": 0.7,
        "shore_normal_deg": 270,
        "notes": "60km north of Perth. Protected lagoon, clear water. Good visibility 10-30m.",
    },
]

SUNBATHING_SPOTS = [
    {
        "name": "Cottesloe",
        "lat": -31.9939,
        "lon": 115.7522,
        "shelter_from": ["E", "NE", "SE"],
        "shelter_factor": 0.3,
        "shore_normal_deg": 270,
        "notes": "Iconic Perth beach. Busy weekends. Great sunset. Exposed to SW swell.",
    },
    {
        "name": "North Cottesloe",
        "lat": -31.9856,
        "lon": 115.7517,
        "shelter_from": ["E", "NE", "SE"],
        "shelter_factor": 0.3,
        "shore_normal_deg": 270,
        "notes": "Quieter than main Cottesloe. Good facilities.",
    },
    {
        "name": "Swanbourne",
        "lat": -31.9672,
        "lon": 115.7583,
        "shelter_from": [],
        "shelter_factor": 0.2,
        "shore_normal_deg": 270,
        "notes": "Nudist section to north, dogs to south. Quiet, less crowded.",
    },
    {
        "name": "City Beach",
        "lat": -31.9389,
        "lon": 115.7583,
        "shelter_from": [],
        "shelter_factor": 0.3,
        "shore_normal_deg": 270,
        "notes": "Family friendly. Groynes provide some protection. Good cafe.",
    },
    {
        "name": "Floreat",
        "lat": -31.9283,
        "lon": 115.7561,
        "shelter_from": [],
        "shelter_factor": 0.2,
        "shore_normal_deg": 270,
        "notes": "Quiet beach with boardwalk. Kiosk. Less crowded than City Beach.",
    },
    {
        "name": "Scarborough",
        "lat": -31.8939,
        "lon": 115.7569,
        "shelter_from": [],
        "shelter_factor": 0.1,
        "shore_normal_deg": 270,
        "notes": "Popular surf beach. Young crowd, nightlife. Often windy.",
    },
    {
        "name": "Trigg",
        "lat": -31.8717,
        "lon": 115.7564,
        "shelter_from": [],
        "shelter_factor": 0.1,
        "shore_normal_deg": 270,
        "notes": "Surf beach with reef. Island views. Cafe. Exposed.",
    },
    {
        "name": "Sorrento",
        "lat": -31.8261,
        "lon": 115.7522,
        "shelter_from": [],
        "shelter_factor": 0.2,
        "shore_normal_deg": 270,
        "notes": "Nice cafes at the Quay. Good sunset spot.",
    },
    {
        "name": "Hillarys",
        "lat": -31.8069,
        "lon": 115.7383,
        "shelter_from": ["W", "SW", "NW", "N"],
        "shelter_factor": 0.8,
        "shore_normal_deg": 270,
        "notes": "Marina breakwater provides excellent shelter. Family friendly. AQWA nearby.",
    },
    {
        "name": "Leighton",
        "lat": -32.0264,
        "lon": 115.7511,
        "shelter_from": [],
        "shelter_factor": 0.2,
        "shore_normal_deg": 270,
        "notes": "Popular dog beach. Kite surfing. Can be windy.",
    },
    {
        "name": "South Beach",
        "lat": -32.0731,
        "lon": 115.7558,
        "shelter_from": [],
        "shelter_factor": 0.2,
        "shore_normal_deg": 270,
        "notes": "Fremantle. Dogs allowed. Grassy areas. South Freo cafe strip.",
    },
    {
        "name": "Bathers Beach",
        "lat": -32.0561,
        "lon": 115.7467,
        "shelter_from": ["W", "SW", "NW", "N", "S"],
        "shelter_factor": 0.9,
        "shore_normal_deg": 270,
        "notes": "Fremantle harbour. Historic area. Cafes and bars. Very sheltered.",
    },
]

WEBCAMS = [
    {
        "name": "Swanbourne",
        "url": "https://www.transport.wa.gov.au/imarine/swanbourne-beach-cam.asp",
        "icon": "🏖️",
    },
    {
        "name": "Trigg Point",
        "url": "https://www.transport.wa.gov.au/imarine/trigg-point-cam.asp",
        "icon": "🌊",
    },
    {
        "name": "Fremantle",
        "url": "https://www.transport.wa.gov.au/imarine/fremantle-fishing-boat-harbour-cam.asp",
        "icon": "⚓",
    },
    {
        "name": "Cottesloe",
        "url": "https://www.surf-forecast.com/breaks/Cottesloe-Beach/webcams/latest",
        "icon": "🏄",
    },
]
