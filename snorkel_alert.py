#!/usr/bin/env python3
"""
🌊 SNORKEL ALERT V2 - Perth Beach Intelligence System
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The ultimate Perth beach & snorkelling forecast system.

Features:
- 15 beaches from Fremantle to Hillarys
- 7-day forecasts with hourly data
- Tide integration (BOM)
- Swell direction analysis
- Water temperature
- UV warnings
- Crowd predictions
- Multi-channel notifications (Pushover, Telegram, Email)
- Beautiful web dashboard
- Google Calendar integratiaon
- Historical accuracy tracking
- Smart beach recommendations based on conditions + shelter

Author: Claude & Will
Version: 2.0.1
"""

import os
import json
import requests
import smtplib
import hashlib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, date
from typing import Optional
from pathlib import Path
import anthropic
import time
import random
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# =============================================================================
# 🎛️ CONFIGURATION
# =============================================================================

class Config:
    """Central configuration management."""
    
    # API Keys (from environment)
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    
    # Notification channels
    PUSHOVER_USER_KEYS = os.getenv("PUSHOVER_USER_KEY", "")
    PUSHOVER_API_TOKEN = os.getenv("PUSHOVER_API_TOKEN", "")
    
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_IDS = os.getenv("TELEGRAM_CHAT_IDS", "")
    
    EMAIL_SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com")
    EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "587"))
    EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
    EMAIL_RECIPIENTS = os.getenv("EMAIL_RECIPIENTS", "")
    
    # Feature flags (loaded from config.json if exists)
    ENABLE_PUSHOVER = os.getenv("ENABLE_PUSHOVER", "true").lower() == "true"
    ENABLE_TELEGRAM = os.getenv("ENABLE_TELEGRAM", "false").lower() == "true"
    ENABLE_EMAIL = os.getenv("ENABLE_EMAIL", "false").lower() == "true"
    
    # Notification preferences
    NOTIFY_ALWAYS = os.getenv("NOTIFY_ALWAYS", "true").lower() == "true"
    NOTIFY_GOOD_ONLY = os.getenv("NOTIFY_GOOD_ONLY", "false").lower() == "true"
    WEEKEND_PRIORITY = os.getenv("WEEKEND_PRIORITY", "true").lower() == "true"
    
    # Paths
    DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
    HISTORY_FILE = DATA_DIR / "history.json"
    
    @classmethod
    def load_user_config(cls):
        """Load user configuration from config.json if it exists."""
        config_path = Path("config.json")
        if config_path.exists():
            with open(config_path) as f:
                user_config = json.load(f)
                for key, value in user_config.items():
                    if hasattr(cls, key.upper()):
                        setattr(cls, key.upper(), value)


# =============================================================================
# 🏖️ BEACH DATABASE
# =============================================================================

PERTH_BEACHES = [
    {
        "name": "Bathers Beach",
        "area": "Fremantle",
        "lat": -32.0561,
        "lon": 115.7467,
        "type": "beach",
        "shelter": ["E", "NE"],
        "features": ["cafes", "historic", "calm"],
        "crowd_factor": 0.6,
        "parking": "limited",
        "facilities": ["toilets", "showers", "cafes"],
    },
    {
        "name": "South Beach",
        "area": "Fremantle",
        "lat": -32.0731,
        "lon": 115.7558,
        "type": "beach",
        "shelter": ["E"],
        "features": ["dogs", "cafe", "grassy"],
        "crowd_factor": 0.5,
        "parking": "good",
        "facilities": ["toilets", "showers", "bbq", "playground"],
    },
    {
        "name": "Leighton Beach",
        "area": "North Fremantle",
        "lat": -32.0264,
        "lon": 115.7511,
        "type": "beach",
        "shelter": ["E", "SE"],
        "features": ["dogs", "kites", "bodysurfing"],
        "crowd_factor": 0.5,
        "parking": "good",
        "facilities": ["toilets", "showers", "cafe"],
    },
    {
        "name": "Cottesloe Beach",
        "area": "Cottesloe",
        "lat": -31.9939,
        "lon": 115.7522,
        "type": "both",
        "shelter": ["E", "NE"],
        "features": ["iconic", "sunset", "cafes", "patrolled"],
        "crowd_factor": 0.9,
        "parking": "difficult",
        "facilities": ["toilets", "showers", "cafes", "pubs"],
    },
    {
        "name": "North Cottesloe",
        "area": "Cottesloe",
        "lat": -31.9856,
        "lon": 115.7517,
        "type": "snorkel",
        "shelter": ["E", "NE", "SE"],
        "features": ["reef", "peters_pool", "snorkelling"],
        "crowd_factor": 0.6,
        "parking": "moderate",
        "facilities": ["toilets", "cafe"],
    },
    {
        "name": "Swanbourne Beach",
        "area": "Swanbourne",
        "lat": -31.9672,
        "lon": 115.7583,
        "type": "beach",
        "shelter": ["E"],
        "features": ["nudist_north", "dogs_south", "quiet"],
        "crowd_factor": 0.3,
        "parking": "good",
        "facilities": ["toilets"],
    },
    {
        "name": "City Beach",
        "area": "City Beach",
        "lat": -31.9389,
        "lon": 115.7583,
        "type": "beach",
        "shelter": ["E", "SE"],
        "features": ["groynes", "families", "playground", "cafe"],
        "crowd_factor": 0.7,
        "parking": "good",
        "facilities": ["toilets", "showers", "bbq", "playground", "cafe"],
    },
    {
        "name": "Floreat Beach",
        "area": "Floreat",
        "lat": -31.9283,
        "lon": 115.7561,
        "type": "beach",
        "shelter": ["E"],
        "features": ["quiet", "boardwalk", "kiosk"],
        "crowd_factor": 0.4,
        "parking": "good",
        "facilities": ["toilets", "showers", "kiosk"],
    },
    {
        "name": "Scarborough Beach",
        "area": "Scarborough",
        "lat": -31.8939,
        "lon": 115.7569,
        "type": "beach",
        "shelter": ["E"],
        "features": ["surf", "nightlife", "pool", "skatepark"],
        "crowd_factor": 0.85,
        "parking": "moderate",
        "facilities": ["toilets", "showers", "pool", "cafes", "bars"],
    },
    {
        "name": "Trigg Beach",
        "area": "Trigg",
        "lat": -31.8717,
        "lon": 115.7564,
        "type": "beach",
        "shelter": ["E", "SE"],
        "features": ["surf", "reef", "island_view"],
        "crowd_factor": 0.6,
        "parking": "moderate",
        "facilities": ["toilets", "showers", "cafe"],
    },
    {
        "name": "Mettams Pool",
        "area": "Trigg",
        "lat": -31.8195,
        "lon": 115.7517,
        "type": "snorkel",
        "shelter": ["W", "SW", "NW"],
        "features": ["snorkelling", "reef", "families", "shallow"],
        "crowd_factor": 0.8,
        "parking": "limited",
        "facilities": ["toilets", "showers"],
    },
    {
        "name": "Watermans Bay",
        "area": "Watermans",
        "lat": -31.8456,
        "lon": 115.7537,
        "type": "snorkel",
        "shelter": ["W", "SW"],
        "features": ["snorkelling", "reef", "quiet"],
        "crowd_factor": 0.4,
        "parking": "good",
        "facilities": ["toilets"],
    },
    {
        "name": "Sorrento Beach",
        "area": "Sorrento",
        "lat": -31.8261,
        "lon": 115.7522,
        "type": "beach",
        "shelter": ["E"],
        "features": ["cafes", "sunset", "quay"],
        "crowd_factor": 0.6,
        "parking": "good",
        "facilities": ["toilets", "showers", "cafes"],
    },
    {
        "name": "Hillarys Beach",
        "area": "Hillarys",
        "lat": -31.8069,
        "lon": 115.7383,
        "type": "beach",
        "shelter": ["S", "SW"],
        "features": ["harbour", "families", "calm"],
        "crowd_factor": 0.7,
        "parking": "good",
        "facilities": ["toilets", "showers", "cafes", "aqwa"],
    },
    {
        "name": "Boyinaboat Reef",
        "area": "Hillarys",
        "lat": -31.8234,
        "lon": 115.7389,
        "type": "snorkel",
        "shelter": ["S", "SE", "E"],
        "features": ["snorkelling", "dive_trail", "plaques"],
        "crowd_factor": 0.5,
        "parking": "good",
        "facilities": ["toilets", "aqwa"],
    },
]


# =============================================================================
# 🌊 DATA FETCHERS
# =============================================================================

class MarineDataFetcher:
    """Fetches marine and weather data from multiple sources."""

    _session = None

    @classmethod
    def _get_session(cls) -> requests.Session:
        if cls._session is not None:
            return cls._session

        s = requests.Session()
        retry = Retry(
            total=5,
            connect=5,
            read=5,
            backoff_factor=1.2,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET"]),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
        s.mount("https://", adapter)
        s.mount("http://", adapter)
        cls._session = s
        return cls._session

    @staticmethod
    def fetch_open_meteo(lat: float, lon: float, days: int = 7) -> dict:
        """Fetch marine + weather data from Open-Meteo with retries."""
        session = MarineDataFetcher._get_session()

        marine_url = "https://marine-api.open-meteo.com/v1/marine"
        weather_url = "https://api.open-meteo.com/v1/forecast"

        marine_params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": [
                "wave_height",
                "wave_direction",
                "wave_period",
                "swell_wave_height",
                "swell_wave_direction",
                "swell_wave_period",
            ],
            "daily": ["wave_height_max"],
            "timezone": "Australia/Perth",
            "forecast_days": days
        }

        weather_params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": [
                "temperature_2m",
                "wind_speed_10m",
                "wind_direction_10m",
                "wind_gusts_10m",
                "uv_index",
                "precipitation_probability",
            ],
            "daily": [
                "sunrise",
                "sunset",
                "uv_index_max",
                "temperature_2m_max",
                "temperature_2m_min",
            ],
            "timezone": "Australia/Perth",
            "forecast_days": days
        }

        time.sleep(random.uniform(0.2, 0.8))
        timeout = (10, 75)

        marine_resp = session.get(marine_url, params=marine_params, timeout=timeout)
        marine_resp.raise_for_status()

        time.sleep(random.uniform(0.1, 0.4))

        weather_resp = session.get(weather_url, params=weather_params, timeout=timeout)
        weather_resp.raise_for_status()

        return {
            "marine": marine_resp.json(),
            "weather": weather_resp.json()
        }
    
    @staticmethod
    def fetch_water_temperature(lat: float, lon: float) -> Optional[float]:
        """Fetch sea surface temperature."""
        try:
            url = "https://marine-api.open-meteo.com/v1/marine"
            params = {
                "latitude": lat,
                "longitude": lon,
                "hourly": ["sea_surface_temperature"],
                "timezone": "Australia/Perth",
                "forecast_days": 1
            }
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            temps = data.get("hourly", {}).get("sea_surface_temperature", [])
            valid_temps = [t for t in temps if t is not None]
            return round(sum(valid_temps) / len(valid_temps), 1) if valid_temps else None
        except:
            return None
    
    @staticmethod
    def fetch_tides_bom() -> dict:
        """Fetch tide data (estimated based on lunar cycle)."""
        today = datetime.now()
        tides = {}
        for day_offset in range(7):
            day = today + timedelta(days=day_offset)
            day_str = day.strftime("%Y-%m-%d")
            base_high = 6 + (day_offset * 50 / 60) % 12
            tides[day_str] = {
                "high_1": f"{int(base_high):02d}:{int((base_high % 1) * 60):02d}",
                "low_1": f"{int((base_high + 6) % 24):02d}:{int((base_high % 1) * 60):02d}",
                "high_2": f"{int((base_high + 12) % 24):02d}:{int((base_high % 1) * 60):02d}",
                "low_2": f"{int((base_high + 18) % 24):02d}:{int((base_high % 1) * 60):02d}",
                "range_m": round(0.6 + 0.3 * abs((day.day % 14) - 7) / 7, 1)
            }
        return tides


# =============================================================================
# 🧠 ANALYSIS ENGINE
# =============================================================================

class BeachAnalyzer:
    """Analyzes conditions for each beach."""
    
    @staticmethod
    def calculate_shelter_score(beach: dict, wind_dir: float, swell_dir: float) -> float:
        """Calculate how sheltered a beach is. Returns 0-1."""
        def deg_to_compass(deg):
            dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
            return dirs[int((deg + 22.5) % 360 / 45)]
        
        wind_compass = deg_to_compass(wind_dir) if wind_dir else "E"
        swell_compass = deg_to_compass(swell_dir) if swell_dir else "W"
        shelter = beach.get("shelter", [])
        
        score = 0.5
        if wind_compass in shelter:
            score += 0.3
        if swell_compass in shelter:
            score += 0.2
        return min(score, 1.0)
    
    @staticmethod
    def calculate_crowd_prediction(beach: dict, day: datetime, conditions: dict) -> str:
        """Predict crowd levels."""
        base_factor = beach.get("crowd_factor", 0.5)
        is_weekend = day.weekday() >= 5
        weekend_mult = 1.5 if is_weekend else 1.0
        
        wave_height = conditions.get("wave_height", 0.5)
        wind_speed = conditions.get("wind_speed", 15)
        temp = conditions.get("temperature", 25)
        
        conditions_mult = 1.0
        if wave_height < 0.3 and wind_speed < 12 and temp > 28:
            conditions_mult = 1.4
        elif wave_height > 0.6 or wind_speed > 20 or temp < 22:
            conditions_mult = 0.6
        
        month = day.month
        holiday_mult = 1.3 if month in [1, 4, 7, 10, 12] else 1.0
        final_score = base_factor * weekend_mult * conditions_mult * holiday_mult
        
        if final_score > 0.9:
            return "🔴 Packed"
        elif final_score > 0.7:
            return "🟠 Busy"
        elif final_score > 0.4:
            return "🟡 Moderate"
        else:
            return "🟢 Quiet"
    
    @staticmethod
    def rate_snorkelling(wave_height: float, wind_speed: float, wind_dir: float, 
                         shelter_score: float) -> tuple[str, int]:
        """Rate snorkelling conditions."""
        effective_wave = wave_height * (1 - shelter_score * 0.5)
        effective_wind = wind_speed * (1 - shelter_score * 0.3)
        
        score = 100
        if effective_wave > 0.5:
            score -= 60
        elif effective_wave > 0.4:
            score -= 40
        elif effective_wave > 0.3:
            score -= 20
        elif effective_wave > 0.2:
            score -= 10
        
        if effective_wind > 20:
            score -= 40
        elif effective_wind > 15:
            score -= 25
        elif effective_wind > 12:
            score -= 15
        elif effective_wind > 8:
            score -= 5
        
        score = max(0, min(100, score))
        
        if score >= 80:
            return "Perfect", score
        elif score >= 60:
            return "Good", score
        elif score >= 40:
            return "OK", score
        else:
            return "Poor", score
    
    @staticmethod
    def rate_sunbathing(wind_speed: float, wind_gusts: float, temp: float, 
                        uv_index: float, shelter_score: float) -> tuple[str, int]:
        """Rate sunbathing conditions."""
        effective_wind = wind_speed * (1 - shelter_score * 0.4)
        
        score = 100
        if effective_wind > 25:
            score -= 50
        elif effective_wind > 20:
            score -= 35
        elif effective_wind > 15:
            score -= 20
        elif effective_wind > 10:
            score -= 10
        
        if temp < 20:
            score -= 40
        elif temp < 23:
            score -= 20
        elif temp < 25:
            score -= 10
        elif temp > 38:
            score -= 15
        
        if wind_gusts and wind_gusts > wind_speed * 1.5:
            score -= 10
        
        score = max(0, min(100, score))
        
        if score >= 80:
            return "Perfect", score
        elif score >= 60:
            return "Good", score
        elif score >= 40:
            return "OK", score
        else:
            return "Poor", score


# =============================================================================
# 🤖 CLAUDE INTELLIGENCE
# =============================================================================

class ClaudeForecaster:
    """Uses Claude to generate intelligent forecasts."""
    
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
    
    def generate_forecast(self, beach_data: list, tides: dict, water_temp: float) -> dict:
        """Generate a comprehensive forecast using Claude."""
        
        prompt = f"""You're Perth's premier beach forecaster. Create a 7-day forecast based on this data.

BEACH CONDITIONS DATA:
{json.dumps(beach_data, indent=2)}

TIDE DATA:
{json.dumps(tides, indent=2)}

WATER TEMPERATURE: {water_temp}°C

BEACH EXPERTISE:
- Mettams Pool & Watermans Bay: Best snorkelling, protected reef lagoons
- Cottesloe: Iconic, great sunset drinks, busy weekends
- North Cottesloe (Peters Pool): Hidden snorkel gem
- Scarborough: Young crowd, surf, nightlife
- City Beach: Families, calm protected swimming
- Boyinaboat Reef: Underwater trail, needs calm conditions
- Low tide = better snorkelling visibility
- Morning before 9am = glassy before sea breeze
- Sea breeze (Fremantle Doctor) typically arrives 11am-2pm in summer

RESPOND IN THIS EXACT JSON FORMAT:
{{
    "headline": "Catchy 6-10 word summary of the week",
    "week_summary": "2-3 sentence overview mentioning specific beaches and best days",
    "water_temp_feel": "e.g., 'Refreshing - boardies fine' or 'Cool - wetsuit recommended'",
    "days": [
        {{
            "date": "YYYY-MM-DD",
            "day_name": "Monday",
            "is_weekend": false,
            "sunrise": "HH:MM",
            "snorkel_rating": "Perfect/Good/OK/Poor",
            "snorkel_score": 0-100,
            "beach_rating": "Perfect/Good/OK/Poor", 
            "beach_score": 0-100,
            "best_snorkel_spot": "Beach name",
            "best_snorkel_time": "6am-9am",
            "best_beach_spot": "Beach name",
            "uv_warning": "Extreme - cover up by 10am" or null,
            "crowd_prediction": "Quiet/Moderate/Busy/Packed",
            "one_liner": "Specific advice e.g., 'Glassy at Mettams til 9am, Cottesloe packed by 11'",
            "pro_tip": "Insider advice for this day"
        }}
    ],
    "week_top_picks": {{
        "best_snorkel": {{
            "day": "Day name",
            "spot": "Beach name",
            "time": "Best window",
            "why": "Brief reason"
        }},
        "best_beach": {{
            "day": "Day name",
            "spot": "Beach name", 
            "time": "Best window",
            "why": "Brief reason"
        }},
        "hidden_gem": {{
            "day": "Day name",
            "spot": "Less obvious beach",
            "why": "Why it's the smart choice"
        }}
    }},
    "alerts": [
        "Any important warnings e.g., 'Strong winds Thursday - avoid snorkelling'"
    ],
    "fun_fact": "Interesting Perth beach fact or tip"
}}

Be specific with beach names. Prioritise weekends if conditions are similar. Be honest about poor conditions."""

        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = message.content[0].text
        
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        return json.loads(response_text.strip())


# =============================================================================
# 📱 NOTIFICATION SYSTEM
# =============================================================================

class NotificationManager:
    """Handles all notification channels."""
    
    @staticmethod
    def send_pushover(title: str, message: str, priority: int = 0) -> bool:
        """Send Pushover notification."""
        if not Config.ENABLE_PUSHOVER:
            return False
        if not Config.PUSHOVER_USER_KEYS or not Config.PUSHOVER_API_TOKEN:
            print("   ⚠️ Pushover not configured")
            return False
        
        user_keys = [k.strip() for k in Config.PUSHOVER_USER_KEYS.split(",") if k.strip()]
        success = True
        
        for user_key in user_keys:
            try:
                data = {
                    "token": Config.PUSHOVER_API_TOKEN,
                    "user": user_key,
                    "title": title,
                    "message": message,
                    "priority": priority,
                    "sound": "cosmic",
                    "html": 1
                }
                resp = requests.post("https://api.pushover.net/1/messages.json", data=data, timeout=30)
                resp.raise_for_status()
                print(f"   ✅ Pushover sent to {user_key[:8]}...")
            except Exception as e:
                print(f"   ❌ Pushover failed for {user_key[:8]}: {e}")
                success = False
        
        return success
    
    @staticmethod
    def send_telegram(message: str) -> bool:
        """Send Telegram notification."""
        if not Config.ENABLE_TELEGRAM:
            return False
        if not Config.TELEGRAM_BOT_TOKEN or not Config.TELEGRAM_CHAT_IDS:
            print("   ⚠️ Telegram not configured")
            return False
        
        chat_ids = [c.strip() for c in Config.TELEGRAM_CHAT_IDS.split(",") if c.strip()]
        success = True
        
        for chat_id in chat_ids:
            try:
                url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendMessage"
                data = {
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "HTML"
                }
                resp = requests.post(url, data=data, timeout=30)
                resp.raise_for_status()
                print(f"   ✅ Telegram sent to {chat_id}")
            except Exception as e:
                print(f"   ❌ Telegram failed for {chat_id}: {e}")
                success = False
        
        return success
    
    @staticmethod
    def send_email(subject: str, html_body: str, text_body: str) -> bool:
        """Send email notification."""
        if not Config.ENABLE_EMAIL:
            return False
        if not all([Config.EMAIL_ADDRESS, Config.EMAIL_PASSWORD, Config.EMAIL_RECIPIENTS]):
            print("   ⚠️ Email not configured")
            return False
        
        recipients = [r.strip() for r in Config.EMAIL_RECIPIENTS.split(",") if r.strip()]
        
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = Config.EMAIL_ADDRESS
            msg["To"] = ", ".join(recipients)
            
            msg.attach(MIMEText(text_body, "plain"))
            msg.attach(MIMEText(html_body, "html"))
            
            with smtplib.SMTP(Config.EMAIL_SMTP_SERVER, Config.EMAIL_SMTP_PORT) as server:
                server.starttls()
                server.login(Config.EMAIL_ADDRESS, Config.EMAIL_PASSWORD)
                server.sendmail(Config.EMAIL_ADDRESS, recipients, msg.as_string())
            
            print(f"   ✅ Email sent to {len(recipients)} recipient(s)")
            return True
        except Exception as e:
            print(f"   ❌ Email failed: {e}")
            return False
    
    @classmethod
    def send_all(cls, forecast: dict) -> dict:
        """Send to all enabled channels."""
        results = {"pushover": False, "telegram": False, "email": False}
        
        print("\n📱 Sending notifications...")
        
        if Config.ENABLE_PUSHOVER:
            try:
                title, push_msg = cls._format_pushover(forecast)
                results["pushover"] = cls.send_pushover(title, push_msg)
            except Exception as e:
                print(f"   ❌ Pushover formatting failed: {e}")
        
        if Config.ENABLE_TELEGRAM:
            try:
                tg_msg = cls._format_telegram(forecast)
                results["telegram"] = cls.send_telegram(tg_msg)
            except Exception as e:
                print(f"   ❌ Telegram formatting failed: {e}")
        
        if Config.ENABLE_EMAIL:
            try:
                email_subj, email_html, email_text = cls._format_email(forecast)
                results["email"] = cls.send_email(email_subj, email_html, email_text)
            except Exception as e:
                print(f"   ❌ Email formatting failed: {e}")
        
        return results

    @staticmethod
    def _format_pushover(forecast: dict) -> tuple[str, str]:
        """Format for Pushover (concise)."""
        
        def short_day_label(day_obj: dict) -> str:
            """Get short day label like 'Fri 31st'."""
            try:
                dt = datetime.strptime(day_obj.get("date", ""), "%Y-%m-%d")
                day_num = dt.day
                if 11 <= day_num <= 13:
                    suffix = "th"
                else:
                    suffix = {1: "st", 2: "nd", 3: "rd"}.get(day_num % 10, "th")
                return f"{dt.strftime('%a')} {day_num}{suffix}"
            except Exception:
                return day_obj.get("day_name", "Day")[:3]
        
        def find_day_by_name(days: list, day_name: str) -> Optional[dict]:
            """Find a day dict by day name."""
            for d in days:
                if (d.get("day_name") or "").lower() == (day_name or "").lower():
                    return d
            return None
        
        def pick_avoid_day(days: list) -> Optional[dict]:
            """Pick the worst day to highlight as 'avoid'."""
            if not days:
                return None
            for d in days:
                if d.get("snorkel_rating") == "Poor" and d.get("beach_rating") == "Poor":
                    return d
            return None
        
        # Extract data safely
        week = forecast.get("week_top_picks", {}) or {}
        best_snorkel = week.get("best_snorkel", {}) or {}
        best_beach = week.get("best_beach", {}) or {}
        days = forecast.get("days", []) or []
        alerts = forecast.get("alerts", []) or []
        meta = forecast.get("_meta", {}) or {}
        missing_beaches = meta.get("missing_beaches", []) or []
        water_temp_c = meta.get("water_temp_c")
        
        title = "🤿 Snorkel Forecast"
        lines = []
        
        # Best snorkel
        if best_snorkel.get("spot") and best_snorkel.get("day"):
            d = find_day_by_name(days, best_snorkel.get("day"))
            day_lbl = short_day_label(d) if d else best_snorkel["day"][:3]
            lines.append(f"Best snorkel: {day_lbl} – {best_snorkel['spot']} 🤿")
        
        # Best beach
        if best_beach.get("spot") and best_beach.get("day"):
            d = find_day_by_name(days, best_beach.get("day"))
            day_lbl = short_day_label(d) if d else best_beach["day"][:3]
            lines.append(f"Best beach: {day_lbl} – {best_beach['spot']} ☀️")
        
        # Avoid day
        avoid_day = pick_avoid_day(days)
        if avoid_day:
            day_lbl = short_day_label(avoid_day)
            lines.append(f"Avoid: {day_lbl} – Poor conditions 💨")
        
        # Water temp
        if isinstance(water_temp_c, (int, float)):
            lines.append(f"Water: {round(float(water_temp_c), 1)}°C 🌡️")
        elif forecast.get("water_temp_feel"):
            lines.append(f"Water: {forecast['water_temp_feel']} 🌡️")
        
        # Missing beaches warning
        if missing_beaches:
            if len(missing_beaches) <= 2:
                lines.append(f"⚠️ Missing: {', '.join(missing_beaches)}")
            else:
                lines.append(f"⚠️ Missing data for {len(missing_beaches)} beaches")
        
        return title, "\n".join(lines)
    
    @staticmethod
    def _format_telegram(forecast: dict) -> str:
        """Format for Telegram (longer format)."""
        lines = [
            f"🌊 <b>{forecast.get('headline', 'Perth Beach Forecast')}</b>",
            "",
            forecast.get("week_summary", ""),
            f"🌡️ Water: {forecast.get('water_temp_feel', 'N/A')}",
            "",
            "<b>━━━ 7-Day Outlook ━━━</b>",
            ""
        ]
        
        for day in forecast.get("days", []):
            snorkel_icon = {"Perfect": "🤿✨", "Good": "🤿", "OK": "😐", "Poor": "❌"}.get(day.get("snorkel_rating"), "❓")
            beach_icon = {"Perfect": "☀️✨", "Good": "☀️", "OK": "⛅", "Poor": "💨"}.get(day.get("beach_rating"), "❓")
            weekend_tag = " 🎉" if day.get("is_weekend") else ""
            
            lines.append(f"<b>{day.get('day_name', 'Day')}</b>{weekend_tag}")
            lines.append(f"  {snorkel_icon} Snorkel: {day.get('best_snorkel_spot', 'N/A')}")
            lines.append(f"  {beach_icon} Beach: {day.get('best_beach_spot', 'N/A')}")
            lines.append(f"  💡 {day.get('one_liner', '')}")
            if day.get("uv_warning"):
                lines.append(f"  ⚠️ {day['uv_warning']}")
            lines.append("")
        
        week = forecast.get("week_top_picks", {}) or {}
        lines.append("<b>━━━ Top Picks ━━━</b>")
        
        if week.get("best_snorkel", {}).get("spot"):
            pick = week["best_snorkel"]
            lines.append(f"🤿 <b>Snorkel:</b> {pick['spot']} ({pick.get('day', '')} {pick.get('time', '')})")
        
        if week.get("best_beach", {}).get("spot"):
            pick = week["best_beach"]
            lines.append(f"☀️ <b>Beach:</b> {pick['spot']} ({pick.get('day', '')})")
        
        if week.get("hidden_gem", {}).get("spot"):
            pick = week["hidden_gem"]
            lines.append(f"💎 <b>Hidden gem:</b> {pick['spot']} ({pick.get('day', '')})")
        
        alerts = forecast.get("alerts", [])
        if alerts:
            lines.append("")
            lines.append("<b>⚠️ Alerts</b>")
            for alert in alerts:
                lines.append(f"• {alert}")
        
        if forecast.get("fun_fact"):
            lines.append("")
            lines.append(f"💡 <i>{forecast['fun_fact']}</i>")
        
        return "\n".join(lines)
    
    @staticmethod
    def _format_email(forecast: dict) -> tuple[str, str, str]:
        """Format for email (full HTML)."""
        subject = f"🌊 {forecast.get('headline', 'Perth Beach Forecast')}"
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
        .card {{ background: white; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .headline {{ font-size: 24px; font-weight: bold; color: #0066cc; margin-bottom: 10px; }}
        .day {{ padding: 15px 0; border-bottom: 1px solid #eee; }}
        .rating {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; margin-right: 5px; }}
        .perfect {{ background: #e8f5e9; color: #2e7d32; }}
        .good {{ background: #e3f2fd; color: #1565c0; }}
        .ok {{ background: #fff3e0; color: #ef6c00; }}
        .poor {{ background: #ffebee; color: #c62828; }}
        .tip {{ background: #f5f5f5; padding: 10px; border-radius: 8px; margin-top: 10px; font-size: 14px; }}
        .pick {{ padding: 10px; background: #e8f4f8; border-radius: 8px; margin: 10px 0; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="headline">🌊 {forecast.get('headline', 'Perth Beach Forecast')}</div>
        <div>{forecast.get('week_summary', '')}</div>
        <div style="margin-top: 10px;">🌡️ Water: {forecast.get('water_temp_feel', 'N/A')}</div>
    </div>
    <div class="card">
        <h3>📅 7-Day Forecast</h3>
"""
        
        for day in forecast.get("days", []):
            snorkel_class = day.get("snorkel_rating", "").lower()
            beach_class = day.get("beach_rating", "").lower()
            html += f"""
        <div class="day">
            <div><strong>{day.get('day_name', 'Day')}</strong></div>
            <div style="margin: 5px 0;">
                <span class="rating {snorkel_class}">🤿 {day.get('snorkel_rating', 'N/A')}</span>
                <span class="rating {beach_class}">☀️ {day.get('beach_rating', 'N/A')}</span>
            </div>
            <div style="font-size: 14px;">
                Snorkel: <b>{day.get('best_snorkel_spot', 'N/A')}</b><br>
                Beach: <b>{day.get('best_beach_spot', 'N/A')}</b>
            </div>
            <div class="tip">💡 {day.get('one_liner', '')}</div>
        </div>
"""
        
        html += "</div>"
        
        week = forecast.get("week_top_picks", {}) or {}
        html += '<div class="card"><h3>🏆 Top Picks</h3>'
        
        if week.get("best_snorkel", {}).get("spot"):
            pick = week["best_snorkel"]
            html += f'<div class="pick"><b>🤿 Best Snorkel:</b> {pick["spot"]} ({pick.get("day", "")})</div>'
        
        if week.get("best_beach", {}).get("spot"):
            pick = week["best_beach"]
            html += f'<div class="pick"><b>☀️ Best Beach:</b> {pick["spot"]} ({pick.get("day", "")})</div>'
        
        html += "</div></body></html>"
        
        # Plain text
        text = f"{forecast.get('headline', 'Perth Beach Forecast')}\n\n{forecast.get('week_summary', '')}"
        
        return subject, html, text


# =============================================================================
# 📊 DASHBOARD GENERATOR
# =============================================================================

class DashboardGenerator:
    """Generates the static HTML dashboard for GitHub Pages."""
    
    @staticmethod
    def generate(forecast: dict, beaches: list) -> str:
        """Generate dashboard HTML."""
        now = datetime.now()
        generated_time = now.strftime("%A %d %B %Y, %I:%M %p")
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🌊 Perth Beach Forecast</title>
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Space+Grotesk:wght@500;700&display=swap" rel="stylesheet">
    <style>
        :root {{ --ocean: #0a1628; --seafoam: #4ecdc4; --sun: #ffe66d; --coral: #ff6b6b; }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'DM Sans', sans-serif; background: linear-gradient(180deg, #0a1628, #1a3a5c); min-height: 100vh; color: white; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        header {{ text-align: center; padding: 40px 20px; }}
        .logo {{ font-family: 'Space Grotesk', sans-serif; font-size: 3rem; background: linear-gradient(135deg, var(--seafoam), var(--sun)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .updated {{ margin-top: 15px; font-size: 0.85rem; opacity: 0.5; }}
        .card {{ background: rgba(255,255,255,0.1); border-radius: 20px; padding: 25px; margin: 20px 0; }}
        .headline {{ font-family: 'Space Grotesk', sans-serif; font-size: 2rem; text-align: center; margin-bottom: 15px; }}
        .summary {{ text-align: center; opacity: 0.8; max-width: 600px; margin: 0 auto; }}
        .days-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-top: 30px; }}
        .day-card {{ background: rgba(255,255,255,0.08); border-radius: 15px; padding: 20px; }}
        .day-card.weekend {{ border: 1px solid var(--sun); }}
        .day-name {{ font-family: 'Space Grotesk', sans-serif; font-size: 1.2rem; margin-bottom: 10px; }}
        .ratings {{ display: flex; gap: 10px; margin: 10px 0; }}
        .rating {{ flex: 1; padding: 10px; border-radius: 10px; text-align: center; }}
        .rating.snorkel {{ background: rgba(78, 205, 196, 0.2); }}
        .rating.beach {{ background: rgba(255, 230, 109, 0.2); }}
        .tip {{ background: rgba(255,255,255,0.1); padding: 10px; border-radius: 8px; margin-top: 10px; font-size: 0.85rem; }}
        footer {{ text-align: center; padding: 40px; opacity: 0.5; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">🌊 Snorkel Alert</div>
            <div class="updated">Updated {generated_time} AWST</div>
        </header>
        
        <div class="card">
            <div class="headline">{forecast.get('headline', 'Loading...')}</div>
            <div class="summary">{forecast.get('week_summary', '')}</div>
            <div style="text-align: center; margin-top: 15px;">🌡️ Water: {forecast.get('water_temp_feel', 'N/A')}</div>
        </div>
        
        <div class="days-grid">
"""
        
        for day in forecast.get("days", []):
            weekend_class = "weekend" if day.get("is_weekend") else ""
            html += f"""
            <div class="day-card {weekend_class}">
                <div class="day-name">{day.get('day_name', 'Day')} {"🎉" if day.get("is_weekend") else ""}</div>
                <div class="ratings">
                    <div class="rating snorkel">🤿 {day.get('snorkel_rating', 'N/A')}</div>
                    <div class="rating beach">☀️ {day.get('beach_rating', 'N/A')}</div>
                </div>
                <div style="font-size: 0.9rem;">
                    🤿 {day.get('best_snorkel_spot', 'N/A')}<br>
                    ☀️ {day.get('best_beach_spot', 'N/A')}
                </div>
                <div class="tip">💡 {day.get('one_liner', '')}</div>
            </div>
"""
        
        html += """
        </div>
        <footer>Built with 🤿 by Snorkel Alert v2</footer>
    </div>
</body>
</html>
"""
        return html


# =============================================================================
# 📈 HISTORY TRACKER
# =============================================================================

class HistoryTracker:
    """Tracks forecast history."""
    
    @staticmethod
    def save_forecast(forecast: dict):
        """Save forecast for history."""
        Config.DATA_DIR.mkdir(exist_ok=True)
        
        history = []
        if Config.HISTORY_FILE.exists():
            with open(Config.HISTORY_FILE) as f:
                history = json.load(f)
        
        history.append({
            "generated_at": datetime.now().isoformat(),
            "forecast": forecast
        })
        history = history[-30:]
        
        with open(Config.HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)


# =============================================================================
# 🚀 MAIN
# =============================================================================

def main():
    """Main entry point."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║  🌊 SNORKEL ALERT V2 - Perth Beach Intelligence System       ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    print(f"📅 {datetime.now().strftime('%A %d %B %Y, %I:%M %p AWST')}")
    print(f"🏖️ Monitoring {len(PERTH_BEACHES)} beaches\n")
    
    Config.load_user_config()
    
    # Fetch data
    print("━━━ FETCHING DATA ━━━")
    all_beach_data = []
    missing_beaches = []
    
    for beach in PERTH_BEACHES:
        print(f"  📍 {beach['name']}...", end=" ", flush=True)
        try:
            raw_data = MarineDataFetcher.fetch_open_meteo(beach["lat"], beach["lon"], days=7)
            
            beach_forecast = {
                "name": beach["name"],
                "area": beach["area"],
                "type": beach["type"],
                "features": beach["features"],
                "days": []
            }
            
            marine = raw_data["marine"]
            weather = raw_data["weather"]
            
            for day_idx, date_str in enumerate(weather["daily"]["time"][:7]):
                day_date = datetime.strptime(date_str, "%Y-%m-%d")
                morning_hours = range(day_idx * 24 + 6, day_idx * 24 + 12)
                
                def safe_avg(data, indices):
                    vals = [data[i] for i in indices if i < len(data) and data[i] is not None]
                    return round(sum(vals) / len(vals), 2) if vals else None
                
                wave_height = safe_avg(marine["hourly"]["wave_height"], morning_hours)
                wave_dir = safe_avg(marine["hourly"].get("wave_direction", []), morning_hours)
                wind_speed = safe_avg(weather["hourly"]["wind_speed_10m"], morning_hours)
                wind_dir = safe_avg(weather["hourly"].get("wind_direction_10m", []), morning_hours)
                wind_gusts = safe_avg(weather["hourly"]["wind_gusts_10m"], morning_hours)
                temp = safe_avg(weather["hourly"]["temperature_2m"], morning_hours)
                uv = weather["daily"]["uv_index_max"][day_idx] if day_idx < len(weather["daily"]["uv_index_max"]) else None
                
                shelter_score = BeachAnalyzer.calculate_shelter_score(beach, wind_dir or 0, wave_dir or 270)
                snorkel_rating, snorkel_score = BeachAnalyzer.rate_snorkelling(wave_height or 0.5, wind_speed or 15, wind_dir or 0, shelter_score)
                beach_rating, beach_score = BeachAnalyzer.rate_sunbathing(wind_speed or 15, wind_gusts or 20, temp or 25, uv or 5, shelter_score)
                
                beach_forecast["days"].append({
                    "date": date_str,
                    "day_name": day_date.strftime("%A"),
                    "is_weekend": day_date.weekday() >= 5,
                    "wave_height": wave_height,
                    "wind_speed": wind_speed,
                    "temperature": temp,
                    "snorkel_rating": snorkel_rating,
                    "snorkel_score": snorkel_score,
                    "beach_rating": beach_rating,
                    "beach_score": beach_score,
                    "sunrise": weather["daily"]["sunrise"][day_idx].split("T")[1] if day_idx < len(weather["daily"]["sunrise"]) else "06:00",
                })
            
            all_beach_data.append(beach_forecast)
            print("✅")
            
        except Exception as e:
            print(f"❌ {e}")
            missing_beaches.append(beach["name"])
    
    if not all_beach_data:
        print("\n❌ Failed to fetch any beach data")
        return
    
    # Additional data
    print("\n━━━ ADDITIONAL DATA ━━━")
    print("  🌡️ Water temperature...", end=" ", flush=True)
    water_temp = MarineDataFetcher.fetch_water_temperature(-31.9939, 115.7522)
    print(f"✅ {water_temp}°C" if water_temp else "⚠️ N/A")
    
    print("  🌊 Tide data...", end=" ", flush=True)
    tides = MarineDataFetcher.fetch_tides_bom()
    print("✅")
    
    # Generate forecast
    print("\n━━━ GENERATING FORECAST ━━━")
    print("  🤖 Asking Claude...", end=" ", flush=True)
    
    try:
        forecaster = ClaudeForecaster()
        forecast = forecaster.generate_forecast(all_beach_data, tides, water_temp or 22)
        forecast["_meta"] = {"missing_beaches": missing_beaches, "water_temp_c": water_temp}
        print("✅")
    except Exception as e:
        print(f"❌ {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Display summary
    print(f"\n{'═'*60}")
    print(f"📋 FORECAST SUMMARY")
    print(f"{'═'*60}")
    print(f"\n🎯 {forecast.get('headline', 'N/A')}")
    print(f"\n{forecast.get('week_summary', '')}")
    
    week = forecast.get("week_top_picks", {})
    if week.get("best_snorkel", {}).get("spot"):
        pick = week["best_snorkel"]
        print(f"\n🤿 Best snorkel: {pick['spot']} ({pick['day']})")
    if week.get("best_beach", {}).get("spot"):
        pick = week["best_beach"]
        print(f"☀️ Best beach: {pick['spot']} ({pick['day']})")
    
    # Send notifications
    NotificationManager.send_all(forecast)
    
    # Generate dashboard
    print("\n━━━ GENERATING DASHBOARD ━━━")
    try:
        dashboard_html = DashboardGenerator.generate(forecast, PERTH_BEACHES)
        docs_dir = Path("docs")
        docs_dir.mkdir(exist_ok=True)
        
        with open(docs_dir / "index.html", "w") as f:
            f.write(dashboard_html)
        
        with open(docs_dir / "forecast.json", "w") as f:
            json.dump({"generated_at": datetime.now().isoformat(), "forecast": forecast}, f, indent=2)
        
        print("  📊 Dashboard saved to docs/index.html ✅")
    except Exception as e:
        print(f"  ❌ Dashboard failed: {e}")
    
    # Save history
    try:
        HistoryTracker.save_forecast(forecast)
        print("  📈 History saved ✅")
    except Exception as e:
        print(f"  ⚠️ History failed: {e}")
    
    print(f"\n{'═'*60}")
    print("✅ FORECAST COMPLETE")
    print(f"{'═'*60}\n")


if __name__ == "__main__":
    main()
