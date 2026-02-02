#!/usr/bin/env python3
"""
🌊 SNORKEL ALERT V5.0 - Perth Beach Forecast
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Major upgrade: Ratings calibrated from real experience.
Calibration: Mettams Pool, 2 Feb 2026 - 8/10 with 0.44-0.50m waves, 9-15 km/h wind

Key changes from v4.1:
- Location-aware shelter system (each spot has shelter_from directions and shelter_factor)
- Numeric 0-10 ratings instead of Perfect/Good/OK/Poor
- Effective wave height calculation (adjusted for shelter)
- Offshore vs onshore wind consideration
- Separate snorkel and beach ratings
- Combined score weighted by location type

Author: Claude & Will
Version: 5.0.0
"""

import os
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path
import time
import random
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import anthropic

# =============================================================================
# CONFIG
# =============================================================================

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
PUSHOVER_USER_KEY = os.getenv("PUSHOVER_USER_KEY", "")
PUSHOVER_API_TOKEN = os.getenv("PUSHOVER_API_TOKEN", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# =============================================================================
# HTTP SESSION WITH RETRY LOGIC
# =============================================================================

def create_session() -> requests.Session:
    """Create a requests session with retry logic."""
    session = requests.Session()
    
    retry_strategy = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    
    return session

SESSION = create_session()

# =============================================================================
# BEACHES WITH SHELTER CHARACTERISTICS
# =============================================================================
# Each location has:
# - shelter_from: wind/swell directions it's protected from
# - shelter_factor: 0.0-1.0 how much natural protection (reef, headland, etc)

SNORKEL_SPOTS = [
    {
        "name": "Mettams Pool", "lat": -31.8195, "lon": 115.7517,
        "shelter_from": ["W", "SW", "NW"], "shelter_factor": 0.8,
        "notes": "Best snorkelling in Perth. Reef-enclosed lagoon, sheltered from W/SW/NW swell. Shallow, beginners welcome."
    },
    {
        "name": "Hamersley Pool", "lat": -31.8150, "lon": 115.7510,
        "shelter_from": ["W", "SW", "NW"], "shelter_factor": 0.8,
        "notes": "600m north of Mettams. Same conditions, fewer crowds. Reef-enclosed tidal pool."
    },
    {
        "name": "Watermans Bay", "lat": -31.8456, "lon": 115.7537,
        "shelter_from": ["W", "SW"], "shelter_factor": 0.6,
        "notes": "Partial reef shelter. Quieter than Mettams, good for families."
    },
    {
        "name": "North Cottesloe", "lat": -31.9856, "lon": 115.7517,
        "shelter_from": ["E", "NE", "SE"], "shelter_factor": 0.3,
        "notes": "Peters Pool area. Good reef snorkelling. Exposed to SW swell."
    },
    {
        "name": "Boyinaboat Reef", "lat": -31.8234, "lon": 115.7389,
        "shelter_from": ["W", "SW", "NW", "N"], "shelter_factor": 0.7,
        "notes": "Hillarys. Underwater trail with plaques. 6m deep. Marina provides shelter."
    },
    {
        "name": "Omeo Wreck", "lat": -32.1056, "lon": 115.7631,
        "shelter_from": ["W", "SW"], "shelter_factor": 0.5,
        "notes": "Coogee Maritime Trail. Historic shipwreck 25m from shore. 2.5-5m deep."
    },
    {
        "name": "Point Peron", "lat": -32.2722, "lon": 115.6917,
        "shelter_from": ["W", "SW", "NW"], "shelter_factor": 0.6,
        "notes": "Rockingham. Garden Island blocks swell. Caves, overhangs, sea life."
    },
    {
        "name": "Burns Beach", "lat": -31.7281, "lon": 115.7261,
        "shelter_from": ["W"], "shelter_factor": 0.3,
        "notes": "Rocky reef offshore. Less crowded. Better for experienced snorkellers."
    },
    {
        "name": "Yanchep Lagoon", "lat": -31.5469, "lon": 115.6350,
        "shelter_from": ["W", "SW", "NW"], "shelter_factor": 0.7,
        "notes": "60km north of Perth. Protected lagoon, clear water. Good visibility 10-30m."
    },
]

SUNBATHING_SPOTS = [
    {
        "name": "Cottesloe", "lat": -31.9939, "lon": 115.7522,
        "shelter_from": ["E", "NE", "SE"], "shelter_factor": 0.3,
        "notes": "Iconic Perth beach. Busy weekends. Great sunset. Exposed to SW swell."
    },
    {
        "name": "North Cottesloe", "lat": -31.9856, "lon": 115.7517,
        "shelter_from": ["E", "NE", "SE"], "shelter_factor": 0.3,
        "notes": "Quieter than main Cottesloe. Good facilities."
    },
    {
        "name": "Swanbourne", "lat": -31.9672, "lon": 115.7583,
        "shelter_from": [], "shelter_factor": 0.2,
        "notes": "Nudist section to north, dogs to south. Quiet, less crowded."
    },
    {
        "name": "City Beach", "lat": -31.9389, "lon": 115.7583,
        "shelter_from": [], "shelter_factor": 0.3,
        "notes": "Family friendly. Groynes provide some protection. Good cafe."
    },
    {
        "name": "Floreat", "lat": -31.9283, "lon": 115.7561,
        "shelter_from": [], "shelter_factor": 0.2,
        "notes": "Quiet beach with boardwalk. Kiosk. Less crowded than City Beach."
    },
    {
        "name": "Scarborough", "lat": -31.8939, "lon": 115.7569,
        "shelter_from": [], "shelter_factor": 0.1,
        "notes": "Popular surf beach. Young crowd, nightlife. Often windy."
    },
    {
        "name": "Trigg", "lat": -31.8717, "lon": 115.7564,
        "shelter_from": [], "shelter_factor": 0.1,
        "notes": "Surf beach with reef. Island views. Cafe. Exposed."
    },
    {
        "name": "Sorrento", "lat": -31.8261, "lon": 115.7522,
        "shelter_from": [], "shelter_factor": 0.2,
        "notes": "Nice cafes at the Quay. Good sunset spot."
    },
    {
        "name": "Hillarys", "lat": -31.8069, "lon": 115.7383,
        "shelter_from": ["W", "SW", "NW", "N"], "shelter_factor": 0.8,
        "notes": "Marina breakwater provides excellent shelter. Family friendly. AQWA nearby."
    },
    {
        "name": "Leighton", "lat": -32.0264, "lon": 115.7511,
        "shelter_from": [], "shelter_factor": 0.2,
        "notes": "Popular dog beach. Kite surfing. Can be windy."
    },
    {
        "name": "South Beach", "lat": -32.0731, "lon": 115.7558,
        "shelter_from": [], "shelter_factor": 0.2,
        "notes": "Fremantle. Dogs allowed. Grassy areas. South Freo cafe strip."
    },
    {
        "name": "Bathers Beach", "lat": -32.0561, "lon": 115.7467,
        "shelter_from": ["W", "SW", "NW", "N", "S"], "shelter_factor": 0.9,
        "notes": "Fremantle harbour. Historic area. Cafes and bars. Very sheltered."
    },
]

WEBCAMS = [
    {"name": "Swanbourne", "url": "https://www.transport.wa.gov.au/imarine/swanbourne-beach-cam.asp", "icon": "🏖️"},
    {"name": "Trigg Point", "url": "https://www.transport.wa.gov.au/imarine/trigg-point-cam.asp", "icon": "🌊"},
    {"name": "Fremantle", "url": "https://www.transport.wa.gov.au/imarine/fremantle-fishing-boat-harbour-cam.asp", "icon": "⚓"},
    {"name": "Cottesloe", "url": "https://www.surf-forecast.com/breaks/Cottesloe-Beach/webcams/latest", "icon": "🏄"},
]

# =============================================================================
# COMPASS HELPERS
# =============================================================================

COMPASS_POINTS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                  "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]

COMPASS_TO_DEG = {point: i * 22.5 for i, point in enumerate(COMPASS_POINTS)}

def deg_to_compass(deg):
    """Convert degrees to compass direction."""
    if deg is None:
        return ""
    return COMPASS_POINTS[int((deg + 11.25) % 360 / 22.5)]

def compass_to_deg(compass):
    """Convert compass direction to degrees."""
    return COMPASS_TO_DEG.get(compass, 0)

def is_sheltered_from(shelter_from, direction_deg):
    """Check if location is sheltered from a given wind/swell direction."""
    if not shelter_from or direction_deg is None:
        return False
    
    direction = deg_to_compass(direction_deg)
    
    for shelter_dir in shelter_from:
        shelter_deg = compass_to_deg(shelter_dir)
        diff = abs(direction_deg - shelter_deg)
        if diff > 180:
            diff = 360 - diff
        if diff <= 30:
            return True
    return False

# =============================================================================
# RATING SYSTEM - CALIBRATED FROM REAL EXPERIENCE
# =============================================================================
#
# Calibration: Mettams Pool, 2 Feb 2026
# - Conditions: 0.44-0.50m waves, 9-15 km/h wind (NNE->W), 25-28°C, sea 24-25°C
# - Experience: 8/10 - calm sea for snorkelling, pleasant minimal wind for sunbathing

def calculate_snorkel_rating(wave_height, swell_height, wind_wave_height, wind_speed, 
                              wind_dir_deg, swell_dir_deg, swell_period, sea_temp, 
                              air_temp, spot):
    """
    Calculate snorkel rating 0-10 based on conditions and shelter.
    Calibrated from real experience: 0.45m waves + 12 km/h wind = 8/10
    """
    score = 10.0
    
    shelter_factor = spot.get('shelter_factor', 0)
    shelter_from = spot.get('shelter_from', [])
    
    # 1. EFFECTIVE WAVE HEIGHT (max 4 points deduction)
    effective_swell = swell_height or 0
    if is_sheltered_from(shelter_from, swell_dir_deg):
        effective_swell = effective_swell * (1 - shelter_factor * 0.7)
    
    effective_wave = (wind_wave_height or 0) + effective_swell
    
    if effective_wave < 0.2:
        wave_penalty = 0
    elif effective_wave < 0.35:
        wave_penalty = 0.5
    elif effective_wave < 0.5:
        wave_penalty = 1.0  # 8/10 territory
    elif effective_wave < 0.7:
        wave_penalty = 2.0
    elif effective_wave < 1.0:
        wave_penalty = 3.0
    else:
        wave_penalty = 4.0
    
    score -= wave_penalty
    
    # 2. WIND (max 3 points deduction)
    wind = wind_speed or 0
    is_offshore = 45 <= (wind_dir_deg or 0) <= 135  # E, NE, SE quadrant
    
    if wind < 8:
        wind_penalty = 0
    elif wind < 12:
        wind_penalty = 0.3
    elif wind < 18:
        wind_penalty = 0.8 if is_offshore else 1.5
    elif wind < 25:
        wind_penalty = 1.5 if is_offshore else 2.5
    else:
        wind_penalty = 2.5 if is_offshore else 3.0
    
    score -= wind_penalty
    
    # 3. SWELL PERIOD (max 1 point deduction)
    period = swell_period or 8
    if period >= 10:
        score -= 0
    elif period >= 8:
        score -= 0.3
    elif period >= 6:
        score -= 0.6
    else:
        score -= 1.0
    
    # 4. SEA TEMPERATURE (max 1 point deduction)
    sea = sea_temp or 24
    if 23 <= sea <= 27:
        score -= 0
    elif 21 <= sea <= 29:
        score -= 0.5
    else:
        score -= 1.0
    
    # 5. AIR TEMPERATURE (max 1 point deduction)
    air = air_temp or 28
    if 25 <= air <= 32:
        score -= 0
    elif 22 <= air <= 35:
        score -= 0.3
    elif 20 <= air <= 38:
        score -= 0.6
    else:
        score -= 1.0
    
    return max(0, min(10, round(score, 1))), round(effective_wave, 2)


def calculate_beach_rating(wind_speed, gusts, air_temp, feels_like, cloud, uv, humidity):
    """
    Calculate beach/sunbathing rating 0-10.
    Calibrated: 9-15 km/h wind = "minimal wind, very pleasant"
    """
    score = 10.0
    
    wind = wind_speed or 0
    gust = gusts or wind
    
    # 1. WIND (max 4 points)
    if wind < 10:
        wind_penalty = 0
    elif wind < 15:
        wind_penalty = 0.5
    elif wind < 20:
        wind_penalty = 1.5
    elif wind < 28:
        wind_penalty = 2.5
    else:
        wind_penalty = 4.0
    
    if gust > wind * 1.8:
        wind_penalty += 0.5
    
    score -= wind_penalty
    
    # 2. TEMPERATURE (max 3 points)
    feels = feels_like or air_temp or 28
    if 26 <= feels <= 32:
        score -= 0
    elif 24 <= feels <= 34:
        score -= 0.5
    elif 22 <= feels <= 36:
        score -= 1.5
    elif 20 <= feels <= 38:
        score -= 2.5
    else:
        score -= 3.0
    
    # 3. UV (max 1.5 points)
    uv_val = uv or 5
    if uv_val <= 6:
        score -= 0
    elif uv_val <= 8:
        score -= 0.3
    elif uv_val <= 10:
        score -= 0.7
    else:
        score -= 1.5
    
    # 4. CLOUD (max 1.5 points)
    cloud_val = cloud or 0
    if 10 <= cloud_val <= 40:
        score -= 0
    elif cloud_val <= 60:
        score -= 0.5
    elif cloud_val <= 80:
        score -= 1.0
    else:
        score -= 1.5
    
    return max(0, min(10, round(score, 1)))


def score_to_label(score):
    """Convert numeric score to text label."""
    if score >= 9:
        return "Perfect"
    elif score >= 7.5:
        return "Great"
    elif score >= 6:
        return "Good"
    elif score >= 4.5:
        return "OK"
    elif score >= 3:
        return "Poor"
    else:
        return "Bad"


def score_to_emoji(score):
    """Convert numeric score to emoji."""
    if score >= 9:
        return "⭐"
    elif score >= 7.5:
        return "🟢"
    elif score >= 6:
        return "🟢"
    elif score >= 4.5:
        return "🟡"
    else:
        return "🔴"

# =============================================================================
# DATA FETCHING WITH RATE LIMITING PROTECTION
# =============================================================================

def fetch_with_retry(url: str, params: dict, max_retries: int = 3) -> dict:
    """Fetch data with retry logic and rate limiting protection."""
    for attempt in range(max_retries):
        try:
            delay = 0.5 + random.random()
            time.sleep(delay)
            
            resp = SESSION.get(url, params=params, timeout=45)
            
            if resp.status_code == 429:
                wait_time = int(resp.headers.get("Retry-After", 30))
                print(f"⏳ Rate limited, waiting {wait_time}s...", end=" ", flush=True)
                time.sleep(wait_time)
                continue
            
            resp.raise_for_status()
            return resp.json()
            
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5
                print(f"⏳ Timeout, retry in {wait_time}s...", end=" ", flush=True)
                time.sleep(wait_time)
            else:
                raise
                
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 3
                print(f"⏳ Error, retry in {wait_time}s...", end=" ", flush=True)
                time.sleep(wait_time)
            else:
                raise
    
    raise Exception("Max retries exceeded")


def fetch_marine_data(lat: float, lon: float) -> dict:
    """Fetch marine data from Open-Meteo."""
    return fetch_with_retry("https://marine-api.open-meteo.com/v1/marine", {
        "latitude": lat, "longitude": lon,
        "hourly": ["wave_height", "wave_direction", "wave_period",
                   "wind_wave_height", "wind_wave_direction",
                   "swell_wave_height", "swell_wave_direction", "swell_wave_period",
                   "sea_surface_temperature"],
        "daily": ["wave_height_max", "swell_wave_height_max"],
        "timezone": "Australia/Perth",
        "forecast_days": 7
    })


def fetch_weather_data(lat: float, lon: float) -> dict:
    """Fetch weather data from Open-Meteo."""
    return fetch_with_retry("https://api.open-meteo.com/v1/forecast", {
        "latitude": lat, "longitude": lon,
        "hourly": ["temperature_2m", "apparent_temperature", "wind_speed_10m", 
                   "wind_direction_10m", "wind_gusts_10m", "cloud_cover", 
                   "uv_index", "relative_humidity_2m"],
        "daily": ["temperature_2m_max", "temperature_2m_min", "wind_speed_10m_max",
                  "wind_direction_10m_dominant", "sunrise", "sunset", "uv_index_max"],
        "timezone": "Australia/Perth",
        "forecast_days": 7
    })


def fetch_water_temp() -> float:
    """Fetch water temperature."""
    try:
        data = fetch_with_retry("https://marine-api.open-meteo.com/v1/marine", {
            "latitude": -31.9939, "longitude": 115.7522,
            "hourly": ["sea_surface_temperature"],
            "timezone": "Australia/Perth",
            "forecast_days": 1
        })
        temps = [t for t in data.get("hourly", {}).get("sea_surface_temperature", []) if t]
        return round(sum(temps) / len(temps), 1) if temps else None
    except:
        return None


def fetch_all_data() -> tuple:
    """Fetch data for all beaches. Returns (data_dict, errors_list)."""
    all_data = {}
    errors = []
    
    # Combine all spots (avoid duplicates by name)
    all_spots = {}
    for s in SNORKEL_SPOTS:
        all_spots[s["name"]] = s
    for s in SUNBATHING_SPOTS:
        if s["name"] not in all_spots:
            all_spots[s["name"]] = s
    
    total = len(all_spots)
    
    for i, (name, spot) in enumerate(all_spots.items()):
        print(f"  📍 {name} ({i+1}/{total})...", end=" ", flush=True)
        try:
            marine = fetch_marine_data(spot["lat"], spot["lon"])
            weather = fetch_weather_data(spot["lat"], spot["lon"])
            all_data[name] = {
                "lat": spot["lat"],
                "lon": spot["lon"],
                "notes": spot["notes"],
                "shelter_from": spot.get("shelter_from", []),
                "shelter_factor": spot.get("shelter_factor", 0),
                "marine": marine,
                "weather": weather
            }
            print("✅")
            
        except Exception as e:
            print(f"❌ {str(e)[:50]}")
            errors.append(name)
    
    return all_data, errors

# =============================================================================
# LOCAL RATING CALCULATION
# =============================================================================

def calculate_ratings_for_spot(spot_data: dict, spot_info: dict, hours: list = None) -> dict:
    """
    Calculate ratings for a spot using local algorithm (not Claude).
    Returns dict with ratings for each day.
    """
    if hours is None:
        hours = list(range(6, 15))  # 6am to 2pm
    
    marine = spot_data.get("marine", {})
    weather = spot_data.get("weather", {})
    
    mh = marine.get("hourly", {})
    wh = weather.get("hourly", {})
    
    # Get time list and figure out days
    times = wh.get("time", [])
    
    # Group by date
    daily_ratings = {}
    
    for i, t in enumerate(times):
        date = t.split("T")[0]
        hour = int(t.split("T")[1].split(":")[0])
        
        if hour not in hours:
            continue
        
        if date not in daily_ratings:
            daily_ratings[date] = {
                "snorkel_scores": [],
                "beach_scores": [],
                "effective_waves": [],
                "best_hour": None,
                "best_snorkel_score": 0,
                "conditions": []
            }
        
        # Get values
        wave_height = mh.get("wave_height", [None] * len(times))[i]
        swell_height = mh.get("swell_wave_height", [None] * len(times))[i]
        wind_wave_height = mh.get("wind_wave_height", [None] * len(times))[i]
        swell_dir = mh.get("swell_wave_direction", [None] * len(times))[i]
        swell_period = mh.get("swell_wave_period", [None] * len(times))[i]
        sea_temp = mh.get("sea_surface_temperature", [None] * len(times))[i]
        
        temp = wh.get("temperature_2m", [None] * len(times))[i]
        feels = wh.get("apparent_temperature", [None] * len(times))[i]
        wind = wh.get("wind_speed_10m", [None] * len(times))[i]
        wind_dir = wh.get("wind_direction_10m", [None] * len(times))[i]
        gusts = wh.get("wind_gusts_10m", [None] * len(times))[i]
        cloud = wh.get("cloud_cover", [None] * len(times))[i]
        uv = wh.get("uv_index", [None] * len(times))[i]
        humidity = wh.get("relative_humidity_2m", [None] * len(times))[i]
        
        # Calculate ratings
        snorkel_score, effective_wave = calculate_snorkel_rating(
            wave_height, swell_height, wind_wave_height, wind, wind_dir,
            swell_dir, swell_period, sea_temp, temp, spot_info
        )
        
        beach_score = calculate_beach_rating(wind, gusts, temp, feels, cloud, uv, humidity)
        
        daily_ratings[date]["snorkel_scores"].append(snorkel_score)
        daily_ratings[date]["beach_scores"].append(beach_score)
        daily_ratings[date]["effective_waves"].append(effective_wave)
        daily_ratings[date]["conditions"].append({
            "hour": hour,
            "snorkel": snorkel_score,
            "beach": beach_score,
            "wave": effective_wave,
            "wind": wind,
            "temp": temp
        })
        
        # Track best hour
        if snorkel_score > daily_ratings[date]["best_snorkel_score"]:
            daily_ratings[date]["best_snorkel_score"] = snorkel_score
            daily_ratings[date]["best_hour"] = hour
    
    # Calculate daily averages and best times
    for date, data in daily_ratings.items():
        if data["snorkel_scores"]:
            data["snorkel_avg"] = round(sum(data["snorkel_scores"]) / len(data["snorkel_scores"]), 1)
            data["beach_avg"] = round(sum(data["beach_scores"]) / len(data["beach_scores"]), 1)
            data["wave_avg"] = round(sum(data["effective_waves"]) / len(data["effective_waves"]), 2)
            
            # Find best time window (consecutive hours with best scores)
            conditions = data["conditions"]
            best_start = conditions[0]["hour"] if conditions else 6
            best_end = best_start + 3
            
            # Simple: find when scores start dropping significantly
            for i, c in enumerate(conditions):
                if c["snorkel"] < data["snorkel_avg"] - 1:
                    best_end = c["hour"]
                    break
                best_end = c["hour"] + 1
            
            data["best_time"] = f"{best_start:02d}:00-{min(best_end, 14):02d}:00"
    
    return daily_ratings


def process_all_ratings(raw_data: dict) -> dict:
    """Process ratings for all spots."""
    snorkel_ratings = {}
    beach_ratings = {}
    
    # Get spot info lookup
    spot_info = {}
    for s in SNORKEL_SPOTS + SUNBATHING_SPOTS:
        spot_info[s["name"]] = s
    
    for name, data in raw_data.items():
        info = spot_info.get(name, {"shelter_from": [], "shelter_factor": 0})
        ratings = calculate_ratings_for_spot(data, info)
        
        # Check if it's a snorkel spot
        is_snorkel = name in [s["name"] for s in SNORKEL_SPOTS]
        is_beach = name in [s["name"] for s in SUNBATHING_SPOTS]
        
        if is_snorkel:
            snorkel_ratings[name] = ratings
        if is_beach:
            beach_ratings[name] = ratings
    
    return snorkel_ratings, beach_ratings

# =============================================================================
# CLAUDE ANALYSIS (SIMPLIFIED - uses pre-calculated ratings)
# =============================================================================

def get_ordinal(n: int) -> str:
    """Get ordinal suffix for a number (1st, 2nd, 3rd, etc)."""
    if 11 <= n <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def generate_forecast(raw_data: dict, water_temp: float, errors: list) -> dict:
    """Generate forecast using local ratings + Claude for summary."""
    
    # Calculate ratings locally
    snorkel_ratings, beach_ratings = process_all_ratings(raw_data)
    
    # Get dates
    dates = [(datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    date_labels = [(datetime.now() + timedelta(days=i)).strftime("%a %-d") +
                   get_ordinal((datetime.now() + timedelta(days=i)).day) for i in range(7)]
    
    # Build forecast structure
    forecast = {
        "water_temp_c": water_temp,
        "dates": dates,
        "date_labels": date_labels,
        "today": {
            "date": dates[0],
            "date_label": date_labels[0]
        },
        "snorkel": {},
        "sunbathing": {},
        "top_picks": {},
        "errors": errors
    }
    
    # Process snorkel spots
    best_snorkel = {"score": 0, "spot": None, "day": None, "time": None, "why": None}
    
    for spot_name, daily_data in snorkel_ratings.items():
        forecast["snorkel"][spot_name] = {}
        
        for date in dates:
            if date in daily_data:
                d = daily_data[date]
                score = d.get("snorkel_avg", 5)
                label = score_to_label(score)
                
                forecast["snorkel"][spot_name][date] = {
                    "rating": label,
                    "score": score,
                    "waves": d.get("wave_avg", 0.5),
                    "wind": d["conditions"][0]["wind"] if d["conditions"] else 15,
                    "best_time": d.get("best_time", "06:00-10:00")
                }
                
                # Track best snorkel
                if score > best_snorkel["score"]:
                    best_snorkel = {
                        "score": score,
                        "spot": spot_name,
                        "day": date_labels[dates.index(date)],
                        "time": d.get("best_time", "06:00-10:00"),
                        "why": f"{d.get('wave_avg', 0.5):.1f}m waves, {d['conditions'][0]['wind'] if d['conditions'] else 15:.0f}km/h wind"
                    }
    
    # Process beach spots
    best_beach = {"score": 0, "spot": None, "day": None, "why": None}
    
    for spot_name, daily_data in beach_ratings.items():
        forecast["sunbathing"][spot_name] = {}
        
        for date in dates:
            if date in daily_data:
                d = daily_data[date]
                score = d.get("beach_avg", 5)
                label = score_to_label(score)
                
                temp = d["conditions"][0]["temp"] if d["conditions"] else 28
                wind = d["conditions"][0]["wind"] if d["conditions"] else 15
                
                forecast["sunbathing"][spot_name][date] = {
                    "rating": label,
                    "score": score,
                    "temp": round(temp) if temp else 28,
                    "wind": round(wind) if wind else 15
                }
                
                # Track best beach
                if score > best_beach["score"]:
                    best_beach = {
                        "score": score,
                        "spot": spot_name,
                        "day": date_labels[dates.index(date)],
                        "why": f"{temp:.0f}°C, {wind:.0f}km/h wind"
                    }
    
    # Set top picks
    forecast["top_picks"] = {
        "best_snorkel": best_snorkel,
        "best_sunbathing": best_beach,
        "hidden_gem": {
            "spot": "Hamersley Pool" if "Hamersley Pool" in snorkel_ratings else "Watermans Bay",
            "day": best_snorkel.get("day", date_labels[0]),
            "time": best_snorkel.get("time", "06:00-10:00"),
            "why": "Same conditions as Mettams, fewer people"
        }
    }
    
    # Generate summary using Claude
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        
        summary_prompt = f"""You are a professional beach forecaster for Perth, WA. Write a 2-3 sentence summary of conditions.

Best snorkel: {best_snorkel['spot']} on {best_snorkel['day']} (score {best_snorkel['score']}/10) - {best_snorkel['why']}
Best beach: {best_beach['spot']} on {best_beach['day']} (score {best_beach['score']}/10) - {best_beach['why']}
Water temp: {water_temp}°C
Errors: {len(errors)} beaches failed to fetch

Be factual and professional. Mention specific conditions and best days. No superlatives or flowery language.
Example: "Good snorkelling conditions expected at Mettams Pool on Tuesday with 0.4m waves and light 10km/h winds. Beach conditions best at Cottesloe Wednesday with 30°C and minimal wind."

Respond with ONLY the summary text, nothing else."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{"role": "user", "content": summary_prompt}]
        )
        
        forecast["summary"] = response.content[0].text.strip()
        
    except Exception as e:
        # Fallback summary
        forecast["summary"] = f"Best snorkelling at {best_snorkel['spot']} ({best_snorkel['score']}/10). Best beach day at {best_beach['spot']} ({best_beach['score']}/10). Water temperature {water_temp}°C."
    
    # Add today's weather
    if raw_data:
        first_spot = list(raw_data.values())[0]
        weather = first_spot.get("weather", {})
        daily = weather.get("daily", {})
        
        forecast["today"]["temp_max"] = daily.get("temperature_2m_max", [30])[0]
        forecast["today"]["wind_speed"] = daily.get("wind_speed_10m_max", [15])[0]
        forecast["today"]["wind_direction"] = deg_to_compass(daily.get("wind_direction_10m_dominant", [0])[0])
        forecast["today"]["description"] = "Sunny" if daily.get("uv_index_max", [5])[0] > 5 else "Partly cloudy"
    
    return forecast

# =============================================================================
# NOTIFICATIONS
# =============================================================================

def format_pushover(forecast: dict) -> tuple:
    """Format Pushover notification with scores."""
    lines = []
    
    lines.append("SNORKELLING (Next 3 Days)")
    
    dates = forecast.get("dates", [])[:3]
    date_labels = forecast.get("date_labels", [])[:3]
    snorkel_data = forecast.get("snorkel", {})
    
    for date, label in zip(dates, date_labels):
        # Find best spots for this day
        day_spots = []
        best_time = None
        
        for spot, days in snorkel_data.items():
            if date in days:
                score = days[date].get("score", 5)
                time = days[date].get("best_time", "")
                
                if score >= 6:  # Good or better
                    short_name = spot.replace(" Pool", "").replace(" Bay", "").replace(" Reef", "").replace(" Wreck", "").replace(" Lagoon", "")
                    day_spots.append((short_name, score))
                    if not best_time and time:
                        best_time = time
        
        day_spots.sort(key=lambda x: x[1], reverse=True)
        
        if day_spots:
            best_score = day_spots[0][1]
            emoji = score_to_emoji(best_score)
            rating = score_to_label(best_score)
            time_str = f" ({best_time})" if best_time else ""
            
            spots_str = ", ".join([s[0] for s in day_spots[:3]])
            if len(day_spots) > 3:
                spots_str += f" +{len(day_spots)-3}"
            
            lines.append(f"{emoji} {label}: {rating} {best_score}/10{time_str}")
            lines.append(f"   {spots_str}")
        else:
            lines.append(f"🔴 {label}: No good spots")
    
    # Today's weather
    lines.append("")
    today = forecast.get("today", {})
    temp = today.get("temp_max", "?")
    wind = today.get("wind_speed", "?")
    wind_dir = today.get("wind_direction", "")
    
    lines.append(f"TODAY: {temp}°C, {wind}km/h {wind_dir}")
    
    # Water temp
    water = forecast.get("water_temp_c", "?")
    lines.append(f"🌊 Water: {water}°C")
    
    # Errors
    errors = forecast.get("errors", [])
    if errors:
        lines.append(f"⚠️ Missing: {len(errors)} beaches")
    
    return "🤿 Snorkel Alert v5", "\n".join(lines)


def send_pushover(title: str, message: str):
    """Send Pushover notification."""
    if not PUSHOVER_USER_KEY or not PUSHOVER_API_TOKEN:
        print("  ⚠️ Pushover not configured")
        return
    
    try:
        resp = requests.post("https://api.pushover.net/1/messages.json", data={
            "token": PUSHOVER_API_TOKEN,
            "user": PUSHOVER_USER_KEY,
            "title": title,
            "message": message,
            "html": 0
        }, timeout=30)
        resp.raise_for_status()
        print("  📱 Pushover sent ✅")
    except Exception as e:
        print(f"  ❌ Pushover failed: {e}")


def send_telegram(message: str):
    """Send Telegram notification."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}, timeout=30)
        print("  📱 Telegram sent ✅")
    except Exception as e:
        print(f"  ❌ Telegram failed: {e}")

# =============================================================================
# DASHBOARD
# =============================================================================

def generate_dashboard(forecast: dict) -> str:
    """Generate HTML dashboard with numeric scores."""
    
    now = datetime.now()
    updated = now.strftime("%A %-d %B %Y, %-I:%M%p").replace("AM", "am").replace("PM", "pm")
    
    dates = forecast.get("dates", [])
    date_labels = forecast.get("date_labels", [])
    snorkel = forecast.get("snorkel", {})
    sunbathing = forecast.get("sunbathing", {})
    top_picks = forecast.get("top_picks", {})
    errors = forecast.get("errors", [])
    
    # Determine weekends
    weekends = []
    for i, d in enumerate(dates):
        dt = datetime.strptime(d, "%Y-%m-%d")
        if dt.weekday() >= 5:
            weekends.append(i)
    
    def rating_cell(data: dict, show_type: str = "snorkel") -> str:
        """Generate a table cell with score."""
        score = data.get("score", 5)
        emoji = score_to_emoji(score)
        
        if show_type == "snorkel":
            best_time = data.get("best_time", "")
            waves = data.get("waves", 0.5)
            if score >= 6 and best_time:
                detail = best_time
            else:
                detail = f"{waves:.1f}m"
        else:
            temp = data.get("temp", 28)
            wind = data.get("wind", 15)
            detail = f"{temp}° {wind}k"
        
        # Color based on score
        if score >= 9:
            css_class = "perfect"
        elif score >= 7.5:
            css_class = "great"
        elif score >= 6:
            css_class = "good"
        elif score >= 4.5:
            css_class = "ok"
        else:
            css_class = "poor"
        
        return f'<td class="rating-cell {css_class}"><span class="score">{score}</span><span class="icon">{emoji}</span><span class="detail">{detail}</span></td>'
    
    # Build snorkel table rows
    snorkel_rows = ""
    for spot in [s["name"] for s in SNORKEL_SPOTS]:
        if spot not in snorkel:
            continue
        cells = ""
        for date in dates:
            if date in snorkel[spot]:
                cells += rating_cell(snorkel[spot][date], "snorkel")
            else:
                cells += '<td class="rating-cell">-</td>'
        snorkel_rows += f'<tr><td class="beach-name">{spot}</td>{cells}</tr>\n'
    
    # Build sunbathing table rows
    sunbathing_rows = ""
    for spot in [s["name"] for s in SUNBATHING_SPOTS]:
        if spot not in sunbathing:
            continue
        cells = ""
        for date in dates:
            if date in sunbathing[spot]:
                cells += rating_cell(sunbathing[spot][date], "sunbathing")
            else:
                cells += '<td class="rating-cell">-</td>'
        sunbathing_rows += f'<tr><td class="beach-name">{spot}</td>{cells}</tr>\n'
    
    # Build header row
    header_cells = ""
    for i, label in enumerate(date_labels):
        weekend_class = "weekend" if i in weekends else ""
        weekend_star = "★ " if i in weekends else ""
        header_cells += f'<th class="{weekend_class}">{weekend_star}{label}</th>'
    
    # Error banner
    error_html = ""
    if errors:
        error_html = f'<div class="error-banner">⚠️ Missing data for: {", ".join(errors)}</div>'
    
    # Top picks
    best_snorkel = top_picks.get("best_snorkel", {})
    best_sunbathing = top_picks.get("best_sunbathing", {})
    hidden_gem = top_picks.get("hidden_gem", {})
    
    snorkel_time = best_snorkel.get("time", "")
    snorkel_detail = f"{best_snorkel.get('day', '')} {snorkel_time} — {best_snorkel.get('why', '')}"
    gem_time = hidden_gem.get("time", "")
    gem_detail = f"{hidden_gem.get('day', '')} {gem_time} — {hidden_gem.get('why', '')}"
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🌊 Snorkel Alert v5 - Perth Beach Forecast</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🌊</text></svg>">
    <style>
        :root {{
            --ocean: #0a1628;
            --ocean-mid: #1a3a5c;
            --seafoam: #4ecdc4;
            --perfect: #ffd700;
            --great: #22c55e;
            --good: #22c55e;
            --ok: #f59e0b;
            --poor: #ef4444;
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(180deg, var(--ocean) 0%, var(--ocean-mid) 100%);
            min-height: 100vh;
            color: white;
            line-height: 1.5;
        }}
        
        .container {{ max-width: 1100px; margin: 0 auto; padding: 20px; }}
        
        header {{ text-align: center; padding: 30px 20px; }}
        .logo {{ font-size: 2.2rem; font-weight: 700; margin-bottom: 5px; }}
        .tagline {{ opacity: 0.6; font-size: 0.95rem; }}
        .updated {{ margin-top: 8px; font-size: 0.8rem; opacity: 0.4; }}
        
        .summary-card {{
            background: rgba(255,255,255,0.08);
            border-radius: 12px;
            padding: 20px 24px;
            margin: 20px 0;
            font-size: 1rem;
            line-height: 1.6;
        }}
        
        .water-temp {{
            display: inline-block;
            margin-top: 12px;
            padding: 6px 12px;
            background: rgba(78,205,196,0.2);
            border-radius: 20px;
            font-size: 0.9rem;
        }}
        
        .error-banner {{
            background: rgba(239,68,68,0.2);
            border: 1px solid rgba(239,68,68,0.4);
            border-radius: 8px;
            padding: 10px 16px;
            margin: 15px 0;
            font-size: 0.85rem;
        }}
        
        .top-picks {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 12px;
            margin: 20px 0;
        }}
        
        .pick-card {{
            background: rgba(255,255,255,0.06);
            border-radius: 10px;
            padding: 16px;
        }}
        
        .pick-card.snorkel {{ border-left: 3px solid var(--seafoam); }}
        .pick-card.sunbathing {{ border-left: 3px solid var(--perfect); }}
        .pick-card.gem {{ border-left: 3px solid var(--great); }}
        
        .pick-label {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.6; margin-bottom: 4px; }}
        .pick-spot {{ font-size: 1.1rem; font-weight: 600; margin-bottom: 2px; }}
        .pick-score {{ font-size: 1.5rem; font-weight: 700; color: var(--seafoam); }}
        .pick-detail {{ font-size: 0.85rem; opacity: 0.7; }}
        
        .section-title {{
            font-size: 1.1rem;
            font-weight: 600;
            margin: 30px 0 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .table-container {{ overflow-x: auto; margin: 0 -20px; padding: 0 20px; }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
            background: rgba(255,255,255,0.03);
            border-radius: 10px;
            overflow: hidden;
        }}
        
        th, td {{
            padding: 10px 8px;
            text-align: center;
            border-bottom: 1px solid rgba(255,255,255,0.06);
        }}
        
        th {{
            background: rgba(255,255,255,0.05);
            font-weight: 600;
            font-size: 0.8rem;
        }}
        
        th.weekend {{
            background: rgba(255,215,0,0.15);
            color: var(--perfect);
        }}
        
        .beach-name {{
            text-align: left;
            font-weight: 500;
            white-space: nowrap;
            padding-left: 12px;
        }}
        
        .rating-cell {{ min-width: 70px; position: relative; }}
        
        .rating-cell .score {{
            display: block;
            font-size: 1.1rem;
            font-weight: 700;
        }}
        
        .rating-cell .icon {{
            display: block;
            font-size: 0.8rem;
            margin-top: 2px;
        }}
        
        .rating-cell .detail {{
            display: block;
            font-size: 0.65rem;
            opacity: 0.6;
            margin-top: 2px;
        }}
        
        .rating-cell.perfect {{ background: rgba(255,215,0,0.15); }}
        .rating-cell.perfect .score {{ color: var(--perfect); }}
        
        .rating-cell.great {{ background: rgba(34,197,94,0.12); }}
        .rating-cell.great .score {{ color: var(--great); }}
        
        .rating-cell.good {{ background: rgba(34,197,94,0.08); }}
        .rating-cell.good .score {{ color: var(--good); }}
        
        .rating-cell.ok {{ background: rgba(245,158,11,0.08); }}
        .rating-cell.ok .score {{ color: var(--ok); }}
        
        .rating-cell.poor {{ background: rgba(239,68,68,0.08); }}
        .rating-cell.poor .score {{ color: var(--poor); }}
        
        .legend {{
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            margin: 12px 0 25px;
            font-size: 0.8rem;
            opacity: 0.7;
        }}
        
        .legend-item {{ display: flex; align-items: center; gap: 4px; }}
        
        .webcams {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 10px;
            margin: 15px 0;
        }}
        
        .webcam-link {{
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 15px 10px;
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            text-decoration: none;
            color: white;
            transition: background 0.2s;
        }}
        
        .webcam-link:hover {{ background: rgba(255,255,255,0.1); }}
        .webcam-icon {{ font-size: 1.5rem; margin-bottom: 5px; }}
        .webcam-name {{ font-size: 0.85rem; }}
        
        footer {{
            text-align: center;
            padding: 30px;
            font-size: 0.8rem;
            opacity: 0.4;
        }}
        
        footer a {{ color: var(--seafoam); }}
        
        @media (max-width: 600px) {{
            .logo {{ font-size: 1.8rem; }}
            .top-picks {{ grid-template-columns: 1fr; }}
            table {{ font-size: 0.75rem; }}
            th, td {{ padding: 8px 4px; }}
            .rating-cell {{ min-width: 50px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">🌊 Snorkel Alert v5</div>
            <div class="tagline">Perth Beach Forecast — Ratings from 0-10</div>
            <div class="updated">Updated {updated} AWST</div>
        </header>
        
        <div class="summary-card">
            {forecast.get("summary", "")}
            <div class="water-temp">🌡️ Water temperature: {forecast.get("water_temp_c", "?")}°C</div>
        </div>
        
        {error_html}
        
        <div class="top-picks">
            <div class="pick-card snorkel">
                <div class="pick-label">🤿 Best Snorkelling</div>
                <div class="pick-spot">{best_snorkel.get("spot", "N/A")}</div>
                <div class="pick-score">{best_snorkel.get("score", "?")}/10</div>
                <div class="pick-detail">{snorkel_detail}</div>
            </div>
            <div class="pick-card sunbathing">
                <div class="pick-label">☀️ Best Sunbathing</div>
                <div class="pick-spot">{best_sunbathing.get("spot", "N/A")}</div>
                <div class="pick-score">{best_sunbathing.get("score", "?")}/10</div>
                <div class="pick-detail">{best_sunbathing.get("day", "")} — {best_sunbathing.get("why", "")}</div>
            </div>
            <div class="pick-card gem">
                <div class="pick-label">💎 Hidden Gem</div>
                <div class="pick-spot">{hidden_gem.get("spot", "N/A")}</div>
                <div class="pick-detail">{gem_detail}</div>
            </div>
        </div>
        
        <div class="section-title">🤿 Snorkelling Conditions</div>
        <div class="legend">
            <span class="legend-item">9-10 ⭐ Perfect</span>
            <span class="legend-item">7.5-9 🟢 Great</span>
            <span class="legend-item">6-7.5 🟢 Good</span>
            <span class="legend-item">4.5-6 🟡 OK</span>
            <span class="legend-item">&lt;4.5 🔴 Poor</span>
            <span class="legend-item">★ Weekend</span>
        </div>
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th></th>
                        {header_cells}
                    </tr>
                </thead>
                <tbody>
                    {snorkel_rows}
                </tbody>
            </table>
        </div>
        
        <div class="section-title">☀️ Sunbathing Conditions</div>
        <div class="legend">
            <span class="legend-item">Format: score/10 • temp° wind(km/h)</span>
        </div>
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th></th>
                        {header_cells}
                    </tr>
                </thead>
                <tbody>
                    {sunbathing_rows}
                </tbody>
            </table>
        </div>
        
        <div class="section-title">📹 Live Webcams</div>
        <div class="webcams">
            {"".join(f'<a href="{w["url"]}" target="_blank" class="webcam-link"><span class="webcam-icon">{w["icon"]}</span><span class="webcam-name">{w["name"]}</span></a>' for w in WEBCAMS)}
        </div>
        
        <footer>
            Built with 🤿 by Snorkel Alert v5.0<br>
            Ratings calibrated from real experience at Mettams Pool
        </footer>
    </div>
</body>
</html>"""
    
    return html

# =============================================================================
# MAIN
# =============================================================================

def main():
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║  🌊 SNORKEL ALERT V5.0 - Perth Beach Forecast                     ║
║  Ratings calibrated from real experience                          ║
╚═══════════════════════════════════════════════════════════════════╝
""")
    print(f"📅 {datetime.now().strftime('%A %-d %B %Y, %-I:%M%p')} AWST\n")
    
    # 1. Fetch all data
    print("━━━ FETCHING DATA ━━━")
    print("  (with retry logic and rate limiting protection)\n")
    raw_data, errors = fetch_all_data()
    
    if not raw_data:
        print("❌ No data fetched, aborting")
        return
    
    print(f"\n  🌡️ Fetching water temperature...", end=" ", flush=True)
    water_temp = fetch_water_temp()
    print(f"{water_temp}°C ✅" if water_temp else "❌")
    
    if errors:
        print(f"\n  ⚠️ Failed to fetch: {', '.join(errors)}")
    
    print(f"\n  ✅ Successfully fetched {len(raw_data)}/{len(raw_data) + len(errors)} beaches")
    
    # 2. Generate forecast (local ratings + Claude summary)
    print("\n━━━ CALCULATING RATINGS ━━━")
    print("  🧮 Processing local ratings...", end=" ", flush=True)
    
    try:
        forecast = generate_forecast(raw_data, water_temp, errors)
        print("✅")
    except Exception as e:
        print(f"❌ {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 3. Display summary
    print(f"\n{'═'*60}")
    print(f"\n{forecast.get('summary', 'No summary')}\n")
    print(f"🌡️ Water: {forecast.get('water_temp_c', '?')}°C")
    
    top = forecast.get("top_picks", {})
    if top.get("best_snorkel", {}).get("spot"):
        p = top["best_snorkel"]
        time_str = f" @ {p.get('time', '')}" if p.get('time') else ""
        print(f"🤿 Best snorkel: {p['spot']} ({p['score']}/10 on {p['day']}{time_str})")
    if top.get("best_sunbathing", {}).get("spot"):
        p = top["best_sunbathing"]
        print(f"☀️ Best sunbathing: {p['spot']} ({p['score']}/10 on {p['day']})")
    
    # 4. Send notifications
    print("\n━━━ NOTIFICATIONS ━━━")
    title, message = format_pushover(forecast)
    print(f"\n{title}\n{message}\n")
    send_pushover(title, message)
    
    # 5. Generate dashboard
    print("\n━━━ DASHBOARD ━━━")
    try:
        Path("docs").mkdir(exist_ok=True)
        html = generate_dashboard(forecast)
        Path("docs/index.html").write_text(html)
        Path("docs/forecast.json").write_text(json.dumps(forecast, indent=2))
        print("  📊 Dashboard saved to docs/index.html ✅")
    except Exception as e:
        print(f"  ❌ Dashboard failed: {e}")
    
    print(f"\n{'═'*60}")
    print("✅ COMPLETE\n")


if __name__ == "__main__":
    main()
