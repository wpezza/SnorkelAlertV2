#!/usr/bin/env python3
"""
🌊 SNORKEL ALERT V4.1 - Perth Beach Forecast
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Simplified version - fetches raw API data, Claude does all analysis.
Professional tone, table-based dashboard.

v4.1 Changes:
- Added retry logic with exponential backoff
- Added delays between API requests to avoid rate limiting
- Added session reuse for better connection handling
- Added best time (24h format) for snorkelling

Author: Claude & Will
Version: 4.1.0
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
        total=5,                      # 5 retries
        backoff_factor=2,             # 2, 4, 8, 16, 32 seconds
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False
    )
    
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,
        pool_maxsize=10
    )
    
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    
    return session

# Global session
SESSION = create_session()

# =============================================================================
# BEACHES
# =============================================================================

SNORKEL_SPOTS = [
    {"name": "Mettams Pool", "lat": -31.8195, "lon": 115.7517, 
     "notes": "Best snorkelling in Perth. Protected reef lagoon, sheltered from W/SW/NW swell. Shallow, beginners welcome. Gets busy weekends."},
    {"name": "Hamersley Pool", "lat": -31.8150, "lon": 115.7510,
     "notes": "600m north of Mettams. Same conditions, fewer crowds. Reef-enclosed tidal pool."},
    {"name": "Watermans Bay", "lat": -31.8456, "lon": 115.7537,
     "notes": "Quiet snorkelling spot. Sheltered from W/SW. Less crowded than Mettams."},
    {"name": "North Cottesloe", "lat": -31.9856, "lon": 115.7517,
     "notes": "Peters Pool area. Good reef snorkelling. Sheltered from E/NE/SE winds."},
    {"name": "Boyinaboat Reef", "lat": -31.8234, "lon": 115.7389,
     "notes": "Hillarys. Underwater trail with plaques. 6m deep. Needs calm conditions."},
    {"name": "Omeo Wreck", "lat": -32.1056, "lon": 115.7631,
     "notes": "Coogee Maritime Trail. Historic shipwreck 25m from shore. 2.5-5m deep."},
    {"name": "Point Peron", "lat": -32.2722, "lon": 115.6917,
     "notes": "Rockingham. Caves, overhangs, sea life. Rock pools good for beginners."},
    {"name": "Burns Beach", "lat": -31.7281, "lon": 115.7261,
     "notes": "Rocky reef offshore. Less crowded. Better for experienced snorkellers."},
    {"name": "Yanchep Lagoon", "lat": -31.5469, "lon": 115.6350,
     "notes": "60km north of Perth. Protected lagoon, clear water. Good visibility 10-30m."},
]

SUNBATHING_SPOTS = [
    {"name": "Cottesloe", "lat": -31.9939, "lon": 115.7522,
     "notes": "Iconic Perth beach. Busy weekends. Great sunset. Sheltered from E/NE."},
    {"name": "North Cottesloe", "lat": -31.9856, "lon": 115.7517,
     "notes": "Quieter than main Cottesloe. Good facilities."},
    {"name": "Swanbourne", "lat": -31.9672, "lon": 115.7583,
     "notes": "Nudist section to north, dogs to south. Quiet, less crowded."},
    {"name": "City Beach", "lat": -31.9389, "lon": 115.7583,
     "notes": "Family friendly. Protected swimming between groynes. Good cafe."},
    {"name": "Floreat", "lat": -31.9283, "lon": 115.7561,
     "notes": "Quiet beach with boardwalk. Kiosk. Less crowded than City Beach."},
    {"name": "Scarborough", "lat": -31.8939, "lon": 115.7569,
     "notes": "Popular surf beach. Young crowd, nightlife. Can be windy."},
    {"name": "Trigg", "lat": -31.8717, "lon": 115.7564,
     "notes": "Surf beach with reef. Island views. Cafe."},
    {"name": "Sorrento", "lat": -31.8261, "lon": 115.7522,
     "notes": "Nice cafes at the Quay. Good sunset spot."},
    {"name": "Hillarys", "lat": -31.8069, "lon": 115.7383,
     "notes": "Near boat harbour. Calm, family friendly. AQWA nearby."},
    {"name": "Leighton", "lat": -32.0264, "lon": 115.7511,
     "notes": "Popular dog beach. Kite surfing. Can be windy."},
    {"name": "South Beach", "lat": -32.0731, "lon": 115.7558,
     "notes": "Fremantle. Dogs allowed. Grassy areas. South Freo cafe strip."},
    {"name": "Bathers Beach", "lat": -32.0561, "lon": 115.7467,
     "notes": "Fremantle. Historic area. Cafes and bars. Sheltered from E/NE."},
]

WEBCAMS = [
    {"name": "Swanbourne", "url": "https://www.transport.wa.gov.au/imarine/swanbourne-beach-cam.asp", "icon": "🏖️"},
    {"name": "Trigg Point", "url": "https://www.transport.wa.gov.au/imarine/trigg-point-cam.asp", "icon": "🌊"},
    {"name": "Fremantle", "url": "https://www.transport.wa.gov.au/imarine/fremantle-fishing-boat-harbour-cam.asp", "icon": "⚓"},
    {"name": "Cottesloe", "url": "https://www.surf-forecast.com/breaks/Cottesloe-Beach/webcams/latest", "icon": "🏄"},
]

# =============================================================================
# DATA FETCHING WITH RATE LIMITING PROTECTION
# =============================================================================

def fetch_with_retry(url: str, params: dict, max_retries: int = 3) -> dict:
    """Fetch data with retry logic and rate limiting protection."""
    
    for attempt in range(max_retries):
        try:
            # Add jitter delay to avoid rate limiting (0.5-1.5 seconds)
            delay = 0.5 + random.random()
            time.sleep(delay)
            
            resp = SESSION.get(url, params=params, timeout=45)
            
            # Check for rate limiting
            if resp.status_code == 429:
                wait_time = int(resp.headers.get("Retry-After", 30))
                print(f"⏳ Rate limited, waiting {wait_time}s...", end=" ", flush=True)
                time.sleep(wait_time)
                continue
            
            resp.raise_for_status()
            return resp.json()
            
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5  # 5, 10, 15 seconds
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
        "hourly": ["wave_height", "wave_direction", "swell_wave_height"],
        "daily": ["wave_height_max"],
        "timezone": "Australia/Perth",
        "forecast_days": 7
    })

def fetch_weather_data(lat: float, lon: float) -> dict:
    """Fetch weather data from Open-Meteo."""
    return fetch_with_retry("https://api.open-meteo.com/v1/forecast", {
        "latitude": lat, "longitude": lon,
        "hourly": ["temperature_2m", "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m"],
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

def fetch_all_data() -> tuple[dict, list]:
    """Fetch data for all beaches. Returns (data_dict, errors_list)."""
    all_data = {}
    errors = []
    
    # Combine all spots (avoid duplicates by name)
    all_spots = {s["name"]: s for s in SNORKEL_SPOTS + SUNBATHING_SPOTS}
    
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
                "marine": marine,
                "weather": weather
            }
            print("✅")
            
        except Exception as e:
            print(f"❌ {str(e)[:50]}")
            errors.append(name)
    
    return all_data, errors

# =============================================================================
# CLAUDE ANALYSIS
# =============================================================================

def get_ordinal(n: int) -> str:
    """Get ordinal suffix for a number (1st, 2nd, 3rd, etc)."""
    if 11 <= n <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")

def generate_forecast(raw_data: dict, water_temp: float, errors: list) -> dict:
    """Send raw data to Claude for analysis."""
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    # Get dates for next 7 days
    dates = [(datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    date_labels = [(datetime.now() + timedelta(days=i)).strftime("%a %-d") + 
                   get_ordinal((datetime.now() + timedelta(days=i)).day) for i in range(7)]
    
    prompt = f"""You are a professional beach and marine conditions forecaster for Perth, Western Australia.

Analyze this raw weather data and create a 7-day forecast.

## RAW DATA
{json.dumps(raw_data, indent=2)}

## WATER TEMPERATURE
{water_temp}°C

## DATES
{json.dumps(list(zip(dates, date_labels)), indent=2)}

## RATING CRITERIA

SNORKELLING (must meet BOTH wave AND wind criteria):
- ⭐ Perfect: waves <0.15m AND wind <8 km/h (glassy, mirror-flat conditions)
- 🟢 Good: waves <0.3m AND wind <12 km/h
- 🟡 OK: waves <0.5m AND wind <18 km/h
- 🔴 Poor: waves >0.5m OR wind >18 km/h

SUNBATHING (consider temp AND wind):
- ⭐ Perfect: temp 28-34°C AND wind <8 km/h
- 🟢 Good: temp 25-36°C AND wind <12 km/h
- 🟡 OK: temp 22-38°C AND wind <18 km/h
- 🔴 Poor: temp <22°C or >38°C OR wind >18 km/h

## BEST TIME CALCULATION
For snorkelling, analyze the hourly data and find the best window (usually early morning before sea breeze). 
Return as 24-hour format range, e.g., "06:00-09:00" or "07:00-10:00".
The sea breeze (Fremantle Doctor) typically arrives between 11:00-14:00 in summer.

## SNORKEL SPOTS
Mettams Pool, Hamersley Pool, Watermans Bay, North Cottesloe, Boyinaboat Reef, Omeo Wreck, Point Peron, Burns Beach, Yanchep Lagoon

## SUNBATHING SPOTS
Cottesloe, North Cottesloe, Swanbourne, City Beach, Floreat, Scarborough, Trigg, Sorrento, Hillarys, Leighton, South Beach, Bathers Beach

## IMPORTANT
- Use morning data (6am-12pm) for ratings - this is when people go
- Be factual and professional - no flowery language
- Include specific numbers (wave heights, wind speeds, temperatures)
- Consider shelter notes for each beach
- Include best_time in 24h format for snorkelling entries

## RESPONSE FORMAT (strict JSON)
{{
    "summary": "2-3 sentences. Professional, factual. Mention specific conditions and best days. No superlatives or flowery language.",
    "water_temp_c": {water_temp},
    "today": {{
        "date": "{dates[0]}",
        "date_label": "{date_labels[0]}",
        "temp_max": 32,
        "wind_speed": 12,
        "wind_direction": "E",
        "description": "Sunny, light easterly winds"
    }},
    "dates": ["{dates[0]}", "{dates[1]}", "{dates[2]}", "{dates[3]}", "{dates[4]}", "{dates[5]}", "{dates[6]}"],
    "date_labels": ["{date_labels[0]}", "{date_labels[1]}", "{date_labels[2]}", "{date_labels[3]}", "{date_labels[4]}", "{date_labels[5]}", "{date_labels[6]}"],
    "snorkel": {{
        "Mettams Pool": {{
            "{dates[0]}": {{"rating": "Perfect", "waves": 0.1, "wind": 6, "best_time": "06:00-09:00"}},
            "{dates[1]}": {{"rating": "Good", "waves": 0.2, "wind": 10, "best_time": "06:00-10:00"}},
            ... (all 7 days)
        }},
        ... (all 9 snorkel spots)
    }},
    "sunbathing": {{
        "Cottesloe": {{
            "{dates[0]}": {{"rating": "Perfect", "temp": 32, "wind": 6}},
            "{dates[1]}": {{"rating": "Good", "temp": 30, "wind": 10}},
            ... (all 7 days)
        }},
        ... (all 12 sunbathing spots)
    }},
    "top_picks": {{
        "best_snorkel": {{"day": "{date_labels[0]}", "spot": "Mettams Pool", "time": "06:00-09:00", "why": "0.1m swell, 6km/h wind"}},
        "best_sunbathing": {{"day": "{date_labels[1]}", "spot": "Cottesloe", "why": "33°C, 5km/h wind"}},
        "hidden_gem": {{"day": "{date_labels[0]}", "spot": "Watermans Bay", "time": "06:00-09:00", "why": "Same conditions as Mettams, fewer people"}}
    }}
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    text = response.content[0].text
    
    # Extract JSON
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    
    forecast = json.loads(text.strip())
    forecast["errors"] = errors
    
    return forecast

# =============================================================================
# NOTIFICATIONS
# =============================================================================

def format_pushover(forecast: dict) -> tuple[str, str]:
    """Format Pushover notification with best times."""
    
    lines = []
    
    # Snorkelling next 3 days
    lines.append("SNORKELLING (Next 3 Days)")
    
    dates = forecast.get("dates", [])[:3]
    date_labels = forecast.get("date_labels", [])[:3]
    snorkel_data = forecast.get("snorkel", {})
    
    has_good_conditions = False
    
    for i, (date, label) in enumerate(zip(dates, date_labels)):
        # Find best spots for this day
        perfect_spots = []
        good_spots = []
        best_time = None
        
        for spot, days in snorkel_data.items():
            if date in days:
                rating = days[date].get("rating", "")
                spot_time = days[date].get("best_time", "")
                
                # Get best time from first perfect/good spot
                if not best_time and spot_time and rating in ["Perfect", "Good"]:
                    best_time = spot_time
                
                short_name = spot.replace(" Pool", "").replace(" Bay", "").replace(" Reef", "").replace(" Wreck", "").replace(" Lagoon", "")
                
                if rating == "Perfect":
                    perfect_spots.append(short_name)
                elif rating == "Good":
                    good_spots.append(short_name)
        
        time_str = f" ({best_time})" if best_time else ""
        
        if perfect_spots:
            has_good_conditions = True
            spots_str = ", ".join(perfect_spots[:3])
            if len(perfect_spots) > 3:
                spots_str += f" +{len(perfect_spots)-3}"
            lines.append(f"⭐ {label}: Perfect{time_str}")
            lines.append(f"   {spots_str}")
        elif good_spots:
            has_good_conditions = True
            spots_str = ", ".join(good_spots[:3])
            if len(good_spots) > 3:
                spots_str += f" +{len(good_spots)-3}"
            lines.append(f"🟢 {label}: Good{time_str}")
            lines.append(f"   {spots_str}")
        else:
            # Check if any OK
            ok_spots = [s for s, d in snorkel_data.items() if date in d and d[date].get("rating") == "OK"]
            if ok_spots:
                lines.append(f"🟡 {label}: OK conditions")
            else:
                lines.append(f"🔴 {label}: Poor conditions")
    
    if not has_good_conditions:
        lines = ["SNORKELLING (Next 3 Days)", "🔴 No good conditions - check back later"]
    
    # Today's weather
    lines.append("")
    today = forecast.get("today", {})
    today_label = today.get("date_label", "Today")
    temp = today.get("temp_max", "?")
    wind = today.get("wind_speed", "?")
    wind_dir = today.get("wind_direction", "")
    desc = today.get("description", "")
    
    lines.append(f"TODAY ({today_label})")
    lines.append(f"{temp}°C, {wind}km/h {wind_dir}, {desc.lower()}")
    
    # Errors
    errors = forecast.get("errors", [])
    if errors:
        lines.append("")
        if len(errors) <= 2:
            lines.append(f"⚠️ Missing: {', '.join(errors)}")
        else:
            lines.append(f"⚠️ Missing data: {len(errors)} beaches")
    
    return "🤿 Snorkel Alert", "\n".join(lines)

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
    """Generate HTML dashboard with tables."""
    
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
        """Generate a table cell for a rating."""
        rating = data.get("rating", "?")
        
        icon = {"Perfect": "⭐", "Good": "🟢", "OK": "🟡", "Poor": "🔴"}.get(rating, "❓")
        
        if show_type == "snorkel":
            waves = data.get("waves", "?")
            best_time = data.get("best_time", "")
            # Show time for Perfect/Good, waves for OK/Poor
            if rating in ["Perfect", "Good"] and best_time:
                detail = best_time
            else:
                detail = f"{waves}m"
        else:
            temp = data.get("temp", "?")
            wind = data.get("wind", "?")
            detail = f"{temp}° {wind}k"
        
        rating_class = rating.lower() if rating in ["Perfect", "Good", "OK", "Poor"] else ""
        
        return f'<td class="rating-cell {rating_class}"><span class="icon">{icon}</span><span class="detail">{detail}</span></td>'
    
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
    
    # Top picks with time
    best_snorkel = top_picks.get("best_snorkel", {})
    best_sunbathing = top_picks.get("best_sunbathing", {})
    hidden_gem = top_picks.get("hidden_gem", {})
    
    # Format snorkel pick with time
    snorkel_time = best_snorkel.get("time", "")
    snorkel_detail = f"{best_snorkel.get('day', '')} {snorkel_time} — {best_snorkel.get('why', '')}"
    
    gem_time = hidden_gem.get("time", "")
    gem_detail = f"{hidden_gem.get('day', '')} {gem_time} — {hidden_gem.get('why', '')}"
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🌊 Snorkel Alert - Perth Beach Forecast</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🌊</text></svg>">
    <style>
        :root {{
            --ocean: #0a1628;
            --ocean-mid: #1a3a5c;
            --seafoam: #4ecdc4;
            --sand: #f4e4c1;
            --perfect: #ffd700;
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
        
        .container {{
            max-width: 1100px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        header {{
            text-align: center;
            padding: 30px 20px;
        }}
        
        .logo {{
            font-size: 2.2rem;
            font-weight: 700;
            margin-bottom: 5px;
        }}
        
        .tagline {{
            opacity: 0.6;
            font-size: 0.95rem;
        }}
        
        .updated {{
            margin-top: 8px;
            font-size: 0.8rem;
            opacity: 0.4;
        }}
        
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
        .pick-card.gem {{ border-left: 3px solid var(--good); }}
        
        .pick-label {{
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            opacity: 0.6;
            margin-bottom: 4px;
        }}
        
        .pick-spot {{
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 2px;
        }}
        
        .pick-detail {{
            font-size: 0.85rem;
            opacity: 0.7;
        }}
        
        .section-title {{
            font-size: 1.1rem;
            font-weight: 600;
            margin: 30px 0 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .table-container {{
            overflow-x: auto;
            margin: 0 -20px;
            padding: 0 20px;
        }}
        
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
        
        .rating-cell {{
            min-width: 70px;
        }}
        
        .rating-cell .icon {{
            display: block;
            font-size: 1.1rem;
        }}
        
        .rating-cell .detail {{
            display: block;
            font-size: 0.7rem;
            opacity: 0.6;
            margin-top: 2px;
        }}
        
        .rating-cell.perfect {{ background: rgba(255,215,0,0.1); }}
        .rating-cell.good {{ background: rgba(34,197,94,0.1); }}
        .rating-cell.ok {{ background: rgba(245,158,11,0.08); }}
        .rating-cell.poor {{ background: rgba(239,68,68,0.08); }}
        
        .legend {{
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            margin: 12px 0 25px;
            font-size: 0.8rem;
            opacity: 0.7;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 4px;
        }}
        
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
        
        .webcam-link:hover {{
            background: rgba(255,255,255,0.1);
        }}
        
        .webcam-icon {{
            font-size: 1.5rem;
            margin-bottom: 5px;
        }}
        
        .webcam-name {{
            font-size: 0.85rem;
        }}
        
        footer {{
            text-align: center;
            padding: 30px;
            font-size: 0.8rem;
            opacity: 0.4;
        }}
        
        footer a {{
            color: var(--seafoam);
        }}
        
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
            <div class="logo">🌊 Snorkel Alert</div>
            <div class="tagline">Perth Beach Forecast</div>
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
                <div class="pick-detail">{snorkel_detail}</div>
            </div>
            <div class="pick-card sunbathing">
                <div class="pick-label">☀️ Best Sunbathing</div>
                <div class="pick-spot">{best_sunbathing.get("spot", "N/A")}</div>
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
            <span class="legend-item">⭐ Perfect (glassy, &lt;0.15m, &lt;8km/h) - shows best time</span>
            <span class="legend-item">🟢 Good - shows best time</span>
            <span class="legend-item">🟡 OK - shows wave height</span>
            <span class="legend-item">🔴 Poor</span>
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
            <span class="legend-item">⭐ Perfect (28-34°C, &lt;8km/h)</span>
            <span class="legend-item">🟢 Good</span>
            <span class="legend-item">🟡 OK</span>
            <span class="legend-item">🔴 Poor</span>
            <span class="legend-item">Format: temp° wind(km/h)</span>
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
            Built with 🤿 by Snorkel Alert v4.1
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
╔═══════════════════════════════════════════════════════════╗
║  🌊 SNORKEL ALERT V4.1 - Perth Beach Forecast             ║
╚═══════════════════════════════════════════════════════════╝
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
    
    # 2. Claude analysis
    print("\n━━━ ANALYSING WITH CLAUDE ━━━")
    print("  🤖 Generating forecast...", end=" ", flush=True)
    
    try:
        forecast = generate_forecast(raw_data, water_temp, errors)
        print("✅")
    except Exception as e:
        print(f"❌ {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 3. Display summary
    print(f"\n{'═'*55}")
    print(f"\n{forecast.get('summary', 'No summary')}\n")
    print(f"🌡️ Water: {forecast.get('water_temp_c', '?')}°C")
    
    top = forecast.get("top_picks", {})
    if top.get("best_snorkel", {}).get("spot"):
        p = top["best_snorkel"]
        time_str = f" @ {p.get('time', '')}" if p.get('time') else ""
        print(f"🤿 Best snorkel: {p['spot']} ({p['day']}{time_str})")
    if top.get("best_sunbathing", {}).get("spot"):
        p = top["best_sunbathing"]
        print(f"☀️ Best sunbathing: {p['spot']} ({p['day']})")
    
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
    
    print(f"\n{'═'*55}")
    print("✅ COMPLETE\n")

if __name__ == "__main__":
    main()
