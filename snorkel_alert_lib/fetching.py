"""Fetching helpers with retry and optional caching."""

import json
import random
import time
import re
from datetime import datetime, timedelta
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

SESSION = None


def create_session() -> requests.Session:
    """Create a requests session with retry logic."""
    session = requests.Session()

    retry_strategy = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )

    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


def get_session() -> requests.Session:
    global SESSION
    if SESSION is None:
        SESSION = create_session()
    return SESSION


class DataCache:
    """Simple JSON cache for API responses."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, key: str) -> Path:
        safe_key = re.sub(r"[^A-Za-z0-9_.-]+", "_", key)
        return self.cache_dir / f"{safe_key}.json"

    def get(self, key: str, ttl_hours: int):
        path = self._path_for(key)
        if not path.exists():
            return None

        try:
            payload = json.loads(path.read_text())
        except Exception:
            return None

        timestamp = payload.get("timestamp")
        if not timestamp:
            return None

        try:
            ts = datetime.fromisoformat(timestamp)
        except Exception:
            return None

        if datetime.utcnow() - ts > timedelta(hours=ttl_hours):
            return None

        return payload.get("data")

    def set(self, key: str, data):
        path = self._path_for(key)
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
        }
        path.write_text(json.dumps(payload))


def fetch_with_retry(url: str, params: dict, max_retries: int = 3) -> dict:
    """Fetch data with retry logic and rate limiting protection."""
    session = get_session()

    for attempt in range(max_retries):
        try:
            delay = 0.5 + random.random()
            time.sleep(delay)

            resp = session.get(url, params=params, timeout=45)

            if resp.status_code == 429:
                wait_time = int(resp.headers.get("Retry-After", 30))
                print(f"\u23f3 Rate limited, waiting {wait_time}s...", end=" ", flush=True)
                time.sleep(wait_time)
                continue

            resp.raise_for_status()
            return resp.json()

        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5
                print(f"\u23f3 Timeout, retry in {wait_time}s...", end=" ", flush=True)
                time.sleep(wait_time)
            else:
                raise

        except requests.exceptions.RequestException:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 3
                print(f"\u23f3 Error, retry in {wait_time}s...", end=" ", flush=True)
                time.sleep(wait_time)
            else:
                raise

    raise Exception("Max retries exceeded")


def fetch_marine_data(lat: float, lon: float) -> dict:
    """Fetch marine data from Open-Meteo."""
    return fetch_with_retry(
        "https://marine-api.open-meteo.com/v1/marine",
        {
            "latitude": lat,
            "longitude": lon,
            "hourly": [
                "wave_height",
                "wave_direction",
                "wave_period",
                "wind_wave_height",
                "wind_wave_direction",
                "swell_wave_height",
                "swell_wave_direction",
                "swell_wave_period",
                "sea_surface_temperature",
            ],
            "daily": ["wave_height_max", "swell_wave_height_max"],
            "timezone": "Australia/Perth",
            "forecast_days": 7,
        },
    )


def fetch_weather_data(lat: float, lon: float) -> dict:
    """Fetch weather data from Open-Meteo."""
    return fetch_with_retry(
        "https://api.open-meteo.com/v1/forecast",
        {
            "latitude": lat,
            "longitude": lon,
            "hourly": [
                "temperature_2m",
                "apparent_temperature",
                "wind_speed_10m",
                "wind_direction_10m",
                "wind_gusts_10m",
                "cloud_cover",
                "uv_index",
                "relative_humidity_2m",
            ],
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "wind_speed_10m_max",
                "wind_direction_10m_dominant",
                "sunrise",
                "sunset",
                "uv_index_max",
            ],
            "timezone": "Australia/Perth",
            "forecast_days": 7,
        },
    )


def fetch_water_temp() -> float:
    """Fetch water temperature."""
    try:
        data = fetch_with_retry(
            "https://marine-api.open-meteo.com/v1/marine",
            {
                "latitude": -31.9939,
                "longitude": 115.7522,
                "hourly": ["sea_surface_temperature"],
                "timezone": "Australia/Perth",
                "forecast_days": 1,
            },
        )
        temps = [t for t in data.get("hourly", {}).get("sea_surface_temperature", []) if t]
        return round(sum(temps) / len(temps), 1) if temps else None
    except Exception:
        return None


def _fetch_or_cache(fetch_fn, cache, cache_key, cache_ttl_hours, use_cache):
    """Fetch data, falling back to cache if allowed."""
    try:
        data = fetch_fn()
        if cache:
            cache.set(cache_key, data)
        return data, False
    except Exception:
        if cache and use_cache:
            cached = cache.get(cache_key, cache_ttl_hours)
            if cached is not None:
                return cached, True
        raise


def fetch_all_data(spots: dict, cache=None, cache_ttl_hours: int = 36, use_cache: bool = False):
    """Fetch data for all beaches. Returns (data_dict, errors_list, cache_hits)."""
    all_data = {}
    errors = []
    cache_hits = []

    total = len(spots)

    for i, (name, spot) in enumerate(spots.items()):
        print(f"  \U0001f4cd {name} ({i + 1}/{total})...", end=" ", flush=True)

        marine_key = f"marine_{spot['lat']}_{spot['lon']}"
        weather_key = f"weather_{spot['lat']}_{spot['lon']}"

        try:
            marine, marine_cached = _fetch_or_cache(
                lambda: fetch_marine_data(spot["lat"], spot["lon"]),
                cache,
                marine_key,
                cache_ttl_hours,
                use_cache,
            )
            weather, weather_cached = _fetch_or_cache(
                lambda: fetch_weather_data(spot["lat"], spot["lon"]),
                cache,
                weather_key,
                cache_ttl_hours,
                use_cache,
            )

            if marine_cached or weather_cached:
                cache_hits.append(name)
                print("\U0001f4e6", end=" ")

            all_data[name] = {
                "lat": spot["lat"],
                "lon": spot["lon"],
                "notes": spot.get("notes", ""),
                "shelter_from": spot.get("shelter_from", []),
                "shelter_factor": spot.get("shelter_factor", 0),
                "shore_normal_deg": spot.get("shore_normal_deg"),
                "marine": marine,
                "weather": weather,
            }
            print("\u2705")
        except Exception as e:
            print(f"\u274c {str(e)[:50]}")
            errors.append(name)

    return all_data, errors, cache_hits
