#!/usr/bin/env python3
"""
🌊 SNORKEL ALERT V3.1 - Perth Beach Intelligence System
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Fixed webcam section - now uses clickable links to official WA Gov webcams.

Author: Claude & Will
Version: 3.1.0
"""

import os
import json
import requests
import smtplib
import io
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional, Tuple
from pathlib import Path
import time
import random
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


# =============================================================================
# 🎛️ CONFIGURATION
# =============================================================================

class Config:
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    PUSHOVER_USER_KEYS = os.getenv("PUSHOVER_USER_KEY", "")
    PUSHOVER_API_TOKEN = os.getenv("PUSHOVER_API_TOKEN", "")
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_IDS = os.getenv("TELEGRAM_CHAT_IDS", "")
    
    ENABLE_PUSHOVER = os.getenv("ENABLE_PUSHOVER", "true").lower() == "true"
    ENABLE_TELEGRAM = os.getenv("ENABLE_TELEGRAM", "false").lower() == "true"
    ENABLE_GO_NOW_ALERTS = os.getenv("ENABLE_GO_NOW_ALERTS", "true").lower() == "true"
    ENABLE_VISUAL_CARDS = os.getenv("ENABLE_VISUAL_CARDS", "true").lower() == "true"
    ENABLE_WEBCAMS = os.getenv("ENABLE_WEBCAMS", "true").lower() == "true"
    
    ALERT_MODE = os.getenv("ALERT_MODE", "scheduled")
    DOCS_DIR = Path("docs")


# =============================================================================
# 🏖️ BEACH DATABASE
# =============================================================================

PERTH_BEACHES = [
    {"name": "Bathers Beach", "area": "Fremantle", "lat": -32.0561, "lon": 115.7467, "type": "beach", "shelter": ["E", "NE"], "crowd_factor": 0.6, "maps_url": "https://maps.google.com/?q=-32.0561,115.7467"},
    {"name": "South Beach", "area": "Fremantle", "lat": -32.0731, "lon": 115.7558, "type": "beach", "shelter": ["E"], "crowd_factor": 0.5, "maps_url": "https://maps.google.com/?q=-32.0731,115.7558"},
    {"name": "Leighton Beach", "area": "North Fremantle", "lat": -32.0264, "lon": 115.7511, "type": "beach", "shelter": ["E", "SE"], "crowd_factor": 0.5, "maps_url": "https://maps.google.com/?q=-32.0264,115.7511"},
    {"name": "Cottesloe Beach", "area": "Cottesloe", "lat": -31.9939, "lon": 115.7522, "type": "both", "shelter": ["E", "NE"], "crowd_factor": 0.9, "maps_url": "https://maps.google.com/?q=-31.9939,115.7522"},
    {"name": "North Cottesloe", "area": "Cottesloe", "lat": -31.9856, "lon": 115.7517, "type": "snorkel", "shelter": ["E", "NE", "SE"], "crowd_factor": 0.6, "maps_url": "https://maps.google.com/?q=-31.9856,115.7517"},
    {"name": "Swanbourne Beach", "area": "Swanbourne", "lat": -31.9672, "lon": 115.7583, "type": "beach", "shelter": ["E"], "crowd_factor": 0.3, "maps_url": "https://maps.google.com/?q=-31.9672,115.7583"},
    {"name": "City Beach", "area": "City Beach", "lat": -31.9389, "lon": 115.7583, "type": "beach", "shelter": ["E", "SE"], "crowd_factor": 0.7, "maps_url": "https://maps.google.com/?q=-31.9389,115.7583"},
    {"name": "Floreat Beach", "area": "Floreat", "lat": -31.9283, "lon": 115.7561, "type": "beach", "shelter": ["E"], "crowd_factor": 0.4, "maps_url": "https://maps.google.com/?q=-31.9283,115.7561"},
    {"name": "Scarborough Beach", "area": "Scarborough", "lat": -31.8939, "lon": 115.7569, "type": "beach", "shelter": ["E"], "crowd_factor": 0.85, "maps_url": "https://maps.google.com/?q=-31.8939,115.7569"},
    {"name": "Trigg Beach", "area": "Trigg", "lat": -31.8717, "lon": 115.7564, "type": "beach", "shelter": ["E", "SE"], "crowd_factor": 0.6, "maps_url": "https://maps.google.com/?q=-31.8717,115.7564"},
    {"name": "Mettams Pool", "area": "Trigg", "lat": -31.8195, "lon": 115.7517, "type": "snorkel", "shelter": ["W", "SW", "NW"], "crowd_factor": 0.8, "maps_url": "https://maps.google.com/?q=-31.8195,115.7517"},
    {"name": "Watermans Bay", "area": "Watermans", "lat": -31.8456, "lon": 115.7537, "type": "snorkel", "shelter": ["W", "SW"], "crowd_factor": 0.4, "maps_url": "https://maps.google.com/?q=-31.8456,115.7537"},
    {"name": "Sorrento Beach", "area": "Sorrento", "lat": -31.8261, "lon": 115.7522, "type": "beach", "shelter": ["E"], "crowd_factor": 0.6, "maps_url": "https://maps.google.com/?q=-31.8261,115.7522"},
    {"name": "Hillarys Beach", "area": "Hillarys", "lat": -31.8069, "lon": 115.7383, "type": "beach", "shelter": ["S", "SW"], "crowd_factor": 0.7, "maps_url": "https://maps.google.com/?q=-31.8069,115.7383"},
    {"name": "Boyinaboat Reef", "area": "Hillarys", "lat": -31.8234, "lon": 115.7389, "type": "snorkel", "shelter": ["S", "SE", "E"], "crowd_factor": 0.5, "maps_url": "https://maps.google.com/?q=-31.8234,115.7389"},
]

# Official WA Government webcams (links to pages, not images)
WEBCAMS = [
    {
        "name": "Swanbourne Beach",
        "url": "https://www.transport.wa.gov.au/marine/charts-warnings-current-conditions/coast-cams/swanbourne",
        "description": "Official WA Gov cam - updates every minute",
        "icon": "🏖️"
    },
    {
        "name": "Trigg Point", 
        "url": "https://www.transport.wa.gov.au/marine/charts-warnings-current-conditions/coast-cams/trigg-point",
        "description": "Official WA Gov cam - great for checking swell",
        "icon": "🌊"
    },
    {
        "name": "Fremantle Harbour",
        "url": "https://www.transport.wa.gov.au/marine/charts-warnings-current-conditions/coast-cams/fremantle-fishing-boat-harbour",
        "description": "Official WA Gov cam - harbour conditions",
        "icon": "⚓"
    },
    {
        "name": "Cottesloe (Surfcam)",
        "url": "https://www.surf-forecast.com/breaks/Cottesloe-Beach/webcams/latest",
        "description": "Surf-forecast.com - may have ads",
        "icon": "🏄"
    },
    {
        "name": "Scarborough (Surfcam)",
        "url": "https://www.surf-forecast.com/breaks/Scarborough_2/webcams/latest",
        "description": "Surf-forecast.com - may have ads", 
        "icon": "🏄"
    },
]


# =============================================================================
# 🌊 DATA FETCHERS
# =============================================================================

class MarineDataFetcher:
    _session = None

    @classmethod
    def _get_session(cls):
        if cls._session is None:
            s = requests.Session()
            retry = Retry(total=5, backoff_factor=1.2, status_forcelist=(429, 500, 502, 503, 504))
            adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
            s.mount("https://", adapter)
            s.mount("http://", adapter)
            cls._session = s
        return cls._session

    @classmethod
    def fetch_current_conditions(cls, lat: float, lon: float) -> dict:
        session = cls._get_session()
        marine_url = "https://marine-api.open-meteo.com/v1/marine"
        weather_url = "https://api.open-meteo.com/v1/forecast"
        
        time.sleep(random.uniform(0.1, 0.3))
        
        marine_resp = session.get(marine_url, params={
            "latitude": lat, "longitude": lon,
            "hourly": ["wave_height", "wave_direction"],
            "timezone": "Australia/Perth", "forecast_days": 1
        }, timeout=30)
        marine_resp.raise_for_status()
        marine = marine_resp.json()
        
        weather_resp = session.get(weather_url, params={
            "latitude": lat, "longitude": lon,
            "hourly": ["wind_speed_10m", "wind_direction_10m", "temperature_2m"],
            "timezone": "Australia/Perth", "forecast_days": 1
        }, timeout=30)
        weather_resp.raise_for_status()
        weather = weather_resp.json()
        
        hour_idx = datetime.now().hour
        return {
            "wave_height": marine["hourly"]["wave_height"][hour_idx],
            "wave_direction": marine["hourly"]["wave_direction"][hour_idx],
            "wind_speed": weather["hourly"]["wind_speed_10m"][hour_idx],
            "wind_direction": weather["hourly"]["wind_direction_10m"][hour_idx],
            "temperature": weather["hourly"]["temperature_2m"][hour_idx],
        }

    @classmethod
    def fetch_forecast(cls, lat: float, lon: float, days: int = 7) -> dict:
        session = cls._get_session()
        time.sleep(random.uniform(0.2, 0.5))
        
        marine_resp = session.get("https://marine-api.open-meteo.com/v1/marine", params={
            "latitude": lat, "longitude": lon,
            "hourly": ["wave_height", "wave_direction", "wave_period"],
            "daily": ["wave_height_max"],
            "timezone": "Australia/Perth", "forecast_days": days
        }, timeout=60)
        marine_resp.raise_for_status()
        
        time.sleep(random.uniform(0.1, 0.3))
        
        weather_resp = session.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": lat, "longitude": lon,
            "hourly": ["temperature_2m", "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m", "uv_index"],
            "daily": ["sunrise", "sunset", "uv_index_max", "temperature_2m_max"],
            "timezone": "Australia/Perth", "forecast_days": days
        }, timeout=60)
        weather_resp.raise_for_status()
        
        return {"marine": marine_resp.json(), "weather": weather_resp.json()}

    @staticmethod
    def fetch_water_temperature(lat: float, lon: float) -> Optional[float]:
        try:
            resp = requests.get("https://marine-api.open-meteo.com/v1/marine", params={
                "latitude": lat, "longitude": lon,
                "hourly": ["sea_surface_temperature"],
                "timezone": "Australia/Perth", "forecast_days": 1
            }, timeout=10)
            temps = [t for t in resp.json().get("hourly", {}).get("sea_surface_temperature", []) if t]
            return round(sum(temps) / len(temps), 1) if temps else None
        except:
            return None


# =============================================================================
# 🧠 ANALYSIS ENGINE
# =============================================================================

class BeachAnalyzer:
    @staticmethod
    def calculate_shelter_score(beach: dict, wind_dir: float, swell_dir: float) -> float:
        def deg_to_compass(deg):
            return ["N", "NE", "E", "SE", "S", "SW", "W", "NW"][int((deg + 22.5) % 360 / 45)]
        
        shelter = beach.get("shelter", [])
        score = 0.5
        if deg_to_compass(wind_dir or 0) in shelter: score += 0.3
        if deg_to_compass(swell_dir or 270) in shelter: score += 0.2
        return min(score, 1.0)
    
    @staticmethod
    def rate_conditions(wave_height: float, wind_speed: float, shelter_score: float) -> Tuple[str, int]:
        effective_wave = wave_height * (1 - shelter_score * 0.5)
        effective_wind = wind_speed * (1 - shelter_score * 0.3)
        
        score = 100
        if effective_wave > 0.5: score -= 60
        elif effective_wave > 0.4: score -= 40
        elif effective_wave > 0.3: score -= 20
        elif effective_wave > 0.2: score -= 10
        
        if effective_wind > 20: score -= 40
        elif effective_wind > 15: score -= 25
        elif effective_wind > 12: score -= 15
        elif effective_wind > 8: score -= 5
        
        score = max(0, min(100, score))
        
        if score >= 80: return "Perfect", score
        elif score >= 60: return "Good", score
        elif score >= 40: return "OK", score
        else: return "Poor", score
    
    @classmethod
    def check_go_now_conditions(cls, beaches: list) -> Optional[dict]:
        perfect_spots = []
        for beach in beaches:
            if beach["type"] not in ["snorkel", "both"]:
                continue
            try:
                conditions = MarineDataFetcher.fetch_current_conditions(beach["lat"], beach["lon"])
                shelter = cls.calculate_shelter_score(beach, conditions.get("wind_direction", 0), conditions.get("wave_direction", 270))
                rating, score = cls.rate_conditions(conditions.get("wave_height", 0.5), conditions.get("wind_speed", 15), shelter)
                if rating == "Perfect" and score >= 85:
                    perfect_spots.append({"beach": beach, "conditions": conditions, "score": score})
            except Exception as e:
                print(f"  ⚠️ Couldn't check {beach['name']}: {e}")
        
        return max(perfect_spots, key=lambda x: x["score"]) if perfect_spots else None


# =============================================================================
# 🤖 CLAUDE INTELLIGENCE
# =============================================================================

class ClaudeForecaster:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY) if ANTHROPIC_AVAILABLE else None
    
    def generate_forecast(self, beach_data: list, water_temp: float) -> dict:
        if not self.client:
            return {"headline": "Perth Beach Forecast", "week_summary": "", "water_temp_feel": "N/A", "days": [], "week_top_picks": {}, "alerts": []}
        
        prompt = f"""You're Perth's beach forecaster. Create a 7-day forecast.

DATA: {json.dumps(beach_data, indent=2)}
WATER TEMP: {water_temp}°C

RESPOND IN THIS EXACT JSON FORMAT:
{{"headline": "6-10 word summary", "week_summary": "2-3 sentences", "water_temp_feel": "e.g., 'Refreshing - boardies fine'", "days": [{{"date": "YYYY-MM-DD", "day_name": "Monday", "is_weekend": false, "snorkel_rating": "Perfect/Good/OK/Poor", "snorkel_score": 85, "beach_rating": "Good", "beach_score": 70, "best_snorkel_spot": "Beach name", "best_snorkel_time": "6am-9am", "best_beach_spot": "Beach name", "uv_warning": null, "one_liner": "Advice"}}], "week_top_picks": {{"best_snorkel": {{"day": "Day", "spot": "Beach", "time": "Window", "why": "Reason"}}, "best_beach": {{"day": "Day", "spot": "Beach", "time": "Window", "why": "Reason"}}, "hidden_gem": {{"day": "Day", "spot": "Beach", "why": "Reason"}}}}, "alerts": [], "fun_fact": "Beach fact"}}"""

        message = self.client.messages.create(model="claude-sonnet-4-20250514", max_tokens=2500, messages=[{"role": "user", "content": prompt}])
        response_text = message.content[0].text
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        return json.loads(response_text.strip())


# =============================================================================
# 📱 NOTIFICATIONS
# =============================================================================

class NotificationManager:
    @staticmethod
    def send_pushover(title: str, message: str, priority: int = 0) -> bool:
        if not Config.ENABLE_PUSHOVER or not Config.PUSHOVER_USER_KEYS or not Config.PUSHOVER_API_TOKEN:
            return False
        
        for user_key in [k.strip() for k in Config.PUSHOVER_USER_KEYS.split(",") if k.strip()]:
            try:
                requests.post("https://api.pushover.net/1/messages.json", data={
                    "token": Config.PUSHOVER_API_TOKEN, "user": user_key,
                    "title": title, "message": message, "priority": priority, "html": 1
                }, timeout=30).raise_for_status()
                print(f"   ✅ Pushover sent to {user_key[:8]}...")
            except Exception as e:
                print(f"   ❌ Pushover failed: {e}")
        return True
    
    @staticmethod
    def send_telegram(message: str) -> bool:
        if not Config.ENABLE_TELEGRAM or not Config.TELEGRAM_BOT_TOKEN or not Config.TELEGRAM_CHAT_IDS:
            return False
        
        for chat_id in [c.strip() for c in Config.TELEGRAM_CHAT_IDS.split(",") if c.strip()]:
            try:
                requests.post(f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendMessage", 
                    data={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}, timeout=30).raise_for_status()
                print(f"   ✅ Telegram sent to {chat_id}")
            except Exception as e:
                print(f"   ❌ Telegram failed: {e}")
        return True
    
    @classmethod
    def send_go_now_alert(cls, spot_data: dict):
        beach = spot_data["beach"]
        conditions = spot_data["conditions"]
        title = f"🚨 GO NOW: {beach['name']} is PERFECT!"
        message = f"""<b>DROP EVERYTHING!</b> 🏃‍♂️

🤿 <b>{beach['name']}</b> is glassy right now!

• Waves: {conditions.get('wave_height', 'N/A')}m
• Wind: {conditions.get('wind_speed', 'N/A')} km/h
• Temp: {conditions.get('temperature', 'N/A')}°C

📍 <a href="{beach.get('maps_url', '')}">Get directions</a>

⏰ Go before the sea breeze arrives!"""
        
        print("\n🚨 SENDING GO NOW ALERT!")
        if Config.ENABLE_PUSHOVER: cls.send_pushover(title, message, priority=1)
        if Config.ENABLE_TELEGRAM: cls.send_telegram(message)
    
    @classmethod
    def send_forecast(cls, forecast: dict):
        print("\n📱 Sending forecast...")
        
        week = forecast.get("week_top_picks", {}) or {}
        lines = []
        if week.get("best_snorkel", {}).get("spot"):
            lines.append(f"Best snorkel: {week['best_snorkel'].get('day', '')} – {week['best_snorkel']['spot']} 🤿")
        if week.get("best_beach", {}).get("spot"):
            lines.append(f"Best beach: {week['best_beach'].get('day', '')} – {week['best_beach']['spot']} ☀️")
        if forecast.get("water_temp_feel"):
            lines.append(f"Water: {forecast['water_temp_feel']} 🌡️")
        
        title = "🤿 Snorkel Forecast"
        message = "\n".join(lines) if lines else forecast.get("headline", "Check the dashboard!")
        
        if Config.ENABLE_PUSHOVER: cls.send_pushover(title, message)
        if Config.ENABLE_TELEGRAM: cls.send_telegram(f"🌊 <b>{forecast.get('headline', 'Perth Beach Forecast')}</b>\n\n{message}")


# =============================================================================
# 🗓️ CALENDAR LINKS
# =============================================================================

class CalendarManager:
    @staticmethod
    def get_calendar_links(forecast: dict) -> list:
        links = []
        for day in forecast.get("days", []):
            if day.get("snorkel_rating") == "Perfect":
                spot_name = day.get("best_snorkel_spot", "")
                beach = next((b for b in PERTH_BEACHES if b["name"] == spot_name), None)
                if beach:
                    date = day.get("date", "")
                    title = f"🤿 Snorkelling @ {spot_name}".replace(" ", "+")
                    start = f"{date.replace('-', '')}T060000"
                    end = f"{date.replace('-', '')}T090000"
                    link = f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={title}&dates={start}/{end}&ctz=Australia/Perth"
                    links.append({"day": day.get("day_name"), "date": date, "spot": spot_name, "link": link})
        return links


# =============================================================================
# 📊 DASHBOARD
# =============================================================================

class DashboardGenerator:
    @staticmethod
    def generate(forecast: dict, calendar_links: list) -> str:
        now = datetime.now()
        generated_time = now.strftime("%A %d %B %Y, %I:%M %p")
        
        # Calendar section
        calendar_html = ""
        if calendar_links:
            calendar_html = '<div class="section"><h2>📅 Add Perfect Days to Calendar</h2><div class="calendar-links">'
            for link in calendar_links:
                calendar_html += f'<a href="{link["link"]}" target="_blank" class="cal-btn">📅 {link["day"]} - {link["spot"]}</a>'
            calendar_html += '</div></div>'
        
        # Webcam section
        webcam_html = ""
        if Config.ENABLE_WEBCAMS and WEBCAMS:
            webcam_html = '<div class="section"><h2>📹 Live Webcams</h2><p class="hint">Click to view live beach conditions</p><div class="webcam-grid">'
            for cam in WEBCAMS:
                webcam_html += f'''
                <a href="{cam['url']}" target="_blank" class="webcam-card">
                    <span class="webcam-icon">{cam['icon']}</span>
                    <span class="webcam-name">{cam['name']}</span>
                    <span class="webcam-desc">{cam['description']}</span>
                </a>'''
            webcam_html += '</div></div>'
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🌊 Snorkel Alert - Perth Beach Forecast</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🌊</text></svg>">
    <style>
        :root {{ --ocean: #0a1628; --ocean-mid: #1a3a5c; --seafoam: #4ecdc4; --sun: #ffe66d; --coral: #ff6b6b; }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: linear-gradient(180deg, var(--ocean), var(--ocean-mid)); min-height: 100vh; color: white; }}
        .container {{ max-width: 1000px; margin: 0 auto; padding: 20px; }}
        header {{ text-align: center; padding: 30px 20px; }}
        .logo {{ font-size: 2.5rem; margin-bottom: 5px; }}
        .tagline {{ opacity: 0.6; font-size: 0.9rem; }}
        .updated {{ margin-top: 10px; font-size: 0.8rem; opacity: 0.4; }}
        
        .card {{ background: rgba(255,255,255,0.1); border-radius: 16px; padding: 20px; margin: 15px 0; }}
        .headline {{ font-size: 1.5rem; text-align: center; margin-bottom: 10px; }}
        .summary {{ text-align: center; opacity: 0.8; font-size: 0.95rem; }}
        .water-temp {{ text-align: center; color: var(--seafoam); margin-top: 10px; }}
        
        .section {{ margin: 25px 0; }}
        .section h2 {{ font-size: 1.2rem; margin-bottom: 15px; opacity: 0.9; }}
        .hint {{ font-size: 0.85rem; opacity: 0.6; margin-bottom: 10px; }}
        
        .days-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 12px; }}
        .day-card {{ background: rgba(255,255,255,0.08); border-radius: 12px; padding: 15px; }}
        .day-card.weekend {{ border: 1px solid var(--sun); }}
        .day-card.perfect {{ border: 1px solid #00c853; box-shadow: 0 0 15px rgba(0,200,83,0.2); }}
        .day-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }}
        .day-name {{ font-weight: 600; }}
        .badge {{ padding: 2px 6px; border-radius: 6px; font-size: 0.65rem; font-weight: 600; }}
        .badge.weekend {{ background: var(--sun); color: var(--ocean); }}
        .badge.perfect {{ background: #00c853; }}
        .ratings {{ display: flex; gap: 8px; margin: 8px 0; }}
        .rating {{ flex: 1; padding: 8px; border-radius: 8px; text-align: center; font-size: 0.85rem; }}
        .rating.snorkel {{ background: rgba(78,205,196,0.2); }}
        .rating.beach {{ background: rgba(255,230,109,0.2); }}
        .day-details {{ font-size: 0.8rem; opacity: 0.8; }}
        .tip {{ background: rgba(255,255,255,0.08); padding: 8px; border-radius: 6px; margin-top: 8px; font-size: 0.75rem; }}
        
        .picks-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }}
        .pick-card {{ background: rgba(78,205,196,0.15); border-radius: 12px; padding: 15px; }}
        .pick-card.beach {{ background: rgba(255,230,109,0.15); }}
        .pick-card.gem {{ background: rgba(255,107,107,0.15); }}
        .pick-type {{ font-size: 0.75rem; opacity: 0.7; }}
        .pick-spot {{ font-size: 1.1rem; font-weight: 600; margin: 3px 0; }}
        .pick-when {{ color: var(--seafoam); font-size: 0.85rem; }}
        
        .calendar-links {{ display: flex; flex-wrap: wrap; gap: 10px; }}
        .cal-btn {{ display: inline-block; background: rgba(78,205,196,0.2); border: 1px solid var(--seafoam); color: white; padding: 10px 16px; border-radius: 8px; text-decoration: none; font-size: 0.9rem; transition: all 0.2s; }}
        .cal-btn:hover {{ background: var(--seafoam); color: var(--ocean); }}
        
        .webcam-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }}
        .webcam-card {{ display: flex; flex-direction: column; align-items: center; background: rgba(255,255,255,0.08); border-radius: 12px; padding: 20px; text-decoration: none; color: white; transition: all 0.2s; }}
        .webcam-card:hover {{ background: rgba(255,255,255,0.15); transform: translateY(-2px); }}
        .webcam-icon {{ font-size: 2rem; margin-bottom: 8px; }}
        .webcam-name {{ font-weight: 600; margin-bottom: 4px; }}
        .webcam-desc {{ font-size: 0.75rem; opacity: 0.6; text-align: center; }}
        
        footer {{ text-align: center; padding: 30px; opacity: 0.4; font-size: 0.8rem; }}
        footer a {{ color: var(--seafoam); }}
        
        @media (max-width: 600px) {{
            .logo {{ font-size: 2rem; }}
            .headline {{ font-size: 1.2rem; }}
            .days-grid, .picks-grid, .webcam-grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">🌊 Snorkel Alert</div>
            <div class="tagline">Perth's smartest beach forecast</div>
            <div class="updated">Updated {generated_time} AWST</div>
        </header>
        
        <div class="card">
            <div class="headline">{forecast.get('headline', 'Loading...')}</div>
            <div class="summary">{forecast.get('week_summary', '')}</div>
            <div class="water-temp">🌡️ Water: {forecast.get('water_temp_feel', 'N/A')}</div>
        </div>
        
        {calendar_html}
        
        <div class="section">
            <h2>🏆 Top Picks</h2>
            <div class="picks-grid">
"""
        
        week = forecast.get("week_top_picks", {}) or {}
        if week.get("best_snorkel", {}).get("spot"):
            pick = week["best_snorkel"]
            html += f'<div class="pick-card"><div class="pick-type">🤿 Best Snorkelling</div><div class="pick-spot">{pick.get("spot", "")}</div><div class="pick-when">{pick.get("day", "")} • {pick.get("time", "")}</div></div>'
        if week.get("best_beach", {}).get("spot"):
            pick = week["best_beach"]
            html += f'<div class="pick-card beach"><div class="pick-type">☀️ Best Beach</div><div class="pick-spot">{pick.get("spot", "")}</div><div class="pick-when">{pick.get("day", "")}</div></div>'
        if week.get("hidden_gem", {}).get("spot"):
            pick = week["hidden_gem"]
            html += f'<div class="pick-card gem"><div class="pick-type">💎 Hidden Gem</div><div class="pick-spot">{pick.get("spot", "")}</div><div class="pick-when">{pick.get("day", "")}</div></div>'
        
        html += '''
            </div>
        </div>
        
        <div class="section">
            <h2>📅 7-Day Forecast</h2>
            <div class="days-grid">
'''
        
        for day in forecast.get("days", []):
            is_weekend = day.get("is_weekend", False)
            is_perfect = day.get("snorkel_rating") == "Perfect"
            card_class = "day-card" + (" weekend" if is_weekend else "") + (" perfect" if is_perfect else "")
            badges = ""
            if is_perfect: badges += '<span class="badge perfect">PERFECT</span>'
            if is_weekend: badges += '<span class="badge weekend">WEEKEND</span>'
            
            html += f'''
                <div class="{card_class}">
                    <div class="day-header"><span class="day-name">{day.get("day_name", "")}</span><div>{badges}</div></div>
                    <div class="ratings">
                        <div class="rating snorkel">🤿 {day.get("snorkel_rating", "N/A")}</div>
                        <div class="rating beach">☀️ {day.get("beach_rating", "N/A")}</div>
                    </div>
                    <div class="day-details">🤿 {day.get("best_snorkel_spot", "N/A")}<br>☀️ {day.get("best_beach_spot", "N/A")}</div>
                    <div class="tip">💡 {day.get("one_liner", "")}</div>
                </div>
'''
        
        html += f'''
            </div>
        </div>
        
        {webcam_html}
        
        <footer>Built with 🤿 by Snorkel Alert V3 • <a href="https://github.com/wpezza/SnorkleAlert">GitHub</a></footer>
    </div>
</body>
</html>
'''
        return html


# =============================================================================
# 🚀 MAIN
# =============================================================================

def run_go_now_check():
    print("🚨 GO NOW CHECK\n")
    snorkel_beaches = [b for b in PERTH_BEACHES if b["type"] in ["snorkel", "both"]]
    perfect_spot = BeachAnalyzer.check_go_now_conditions(snorkel_beaches)
    
    if perfect_spot:
        print(f"🎉 PERFECT: {perfect_spot['beach']['name']} (score: {perfect_spot['score']})")
        NotificationManager.send_go_now_alert(perfect_spot)
    else:
        print("😴 No perfect conditions right now")


def run_scheduled_forecast():
    print("🌊 SNORKEL ALERT V3\n")
    print(f"📅 {datetime.now().strftime('%A %d %B %Y, %I:%M %p AWST')}\n")
    
    # Fetch data
    print("━━━ FETCHING DATA ━━━")
    all_beach_data = []
    for beach in PERTH_BEACHES:
        print(f"  📍 {beach['name']}...", end=" ", flush=True)
        try:
            raw = MarineDataFetcher.fetch_forecast(beach["lat"], beach["lon"])
            beach_forecast = {"name": beach["name"], "area": beach.get("area", ""), "type": beach["type"], "days": []}
            
            for day_idx, date_str in enumerate(raw["weather"]["daily"]["time"][:7]):
                day_date = datetime.strptime(date_str, "%Y-%m-%d")
                morning = range(day_idx * 24 + 6, day_idx * 24 + 12)
                
                def avg(data, idx): 
                    vals = [data[i] for i in idx if i < len(data) and data[i] is not None]
                    return round(sum(vals) / len(vals), 2) if vals else None
                
                wave = avg(raw["marine"]["hourly"]["wave_height"], morning)
                wind = avg(raw["weather"]["hourly"]["wind_speed_10m"], morning)
                wind_dir = avg(raw["weather"]["hourly"].get("wind_direction_10m", []), morning)
                wave_dir = avg(raw["marine"]["hourly"].get("wave_direction", []), morning)
                temp = avg(raw["weather"]["hourly"]["temperature_2m"], morning)
                
                shelter = BeachAnalyzer.calculate_shelter_score(beach, wind_dir or 0, wave_dir or 270)
                snorkel_rating, snorkel_score = BeachAnalyzer.rate_conditions(wave or 0.5, wind or 15, shelter)
                beach_rating, beach_score = BeachAnalyzer.rate_conditions(wave or 0.5, wind or 15, shelter * 0.7)
                
                beach_forecast["days"].append({
                    "date": date_str, "day_name": day_date.strftime("%A"), "is_weekend": day_date.weekday() >= 5,
                    "wave_height": wave, "wind_speed": wind, "temperature": temp,
                    "snorkel_rating": snorkel_rating, "snorkel_score": snorkel_score,
                    "beach_rating": beach_rating, "beach_score": beach_score
                })
            
            all_beach_data.append(beach_forecast)
            print("✅")
        except Exception as e:
            print(f"❌ {e}")
    
    # Water temp
    print("\n  🌡️ Water temperature...", end=" ", flush=True)
    water_temp = MarineDataFetcher.fetch_water_temperature(-31.9939, 115.7522)
    print(f"✅ {water_temp}°C" if water_temp else "⚠️ N/A")
    
    # Generate forecast
    print("\n━━━ GENERATING FORECAST ━━━")
    print("  🤖 Asking Claude...", end=" ", flush=True)
    try:
        forecast = ClaudeForecaster().generate_forecast(all_beach_data, water_temp or 22)
        print("✅")
    except Exception as e:
        print(f"❌ {e}")
        return
    
    # Summary
    print(f"\n{'═'*50}")
    print(f"🎯 {forecast.get('headline', 'N/A')}")
    print(forecast.get('week_summary', ''))
    
    # Notifications
    NotificationManager.send_forecast(forecast)
    
    # Dashboard
    print("\n━━━ GENERATING DASHBOARD ━━━")
    try:
        Config.DOCS_DIR.mkdir(exist_ok=True)
        calendar_links = CalendarManager.get_calendar_links(forecast)
        html = DashboardGenerator.generate(forecast, calendar_links)
        (Config.DOCS_DIR / "index.html").write_text(html)
        (Config.DOCS_DIR / "forecast.json").write_text(json.dumps({"generated_at": datetime.now().isoformat(), "forecast": forecast}, indent=2))
        print("  📊 Dashboard saved ✅")
    except Exception as e:
        print(f"  ❌ {e}")
    
    print(f"\n{'═'*50}")
    print("✅ COMPLETE\n")


def main():
    if Config.ALERT_MODE == "go_now":
        run_go_now_check()
    else:
        run_scheduled_forecast()


if __name__ == "__main__":
    main()
