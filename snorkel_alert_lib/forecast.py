"""Forecast assembly and Claude summary."""

from datetime import datetime, timedelta

try:
    import anthropic
except ModuleNotFoundError:
    anthropic = None

from .compass import deg_to_compass
from .config import ANTHROPIC_API_KEY, VERSION, SNORKEL_SPOTS, SUNBATHING_SPOTS
from .ratings import process_all_ratings, score_to_label


def get_ordinal(n: int) -> str:
    """Get ordinal suffix for a number (1st, 2nd, 3rd, etc)."""
    if 11 <= n % 100 <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def _first(seq, default):
    if isinstance(seq, list) and seq:
        return seq[0]
    return default


def _daily_value(daily, date, key, default=None):
    if not daily:
        return default
    times = daily.get("time", [])
    if not times or date not in times:
        return default
    idx = times.index(date)
    values = daily.get(key, [])
    if idx >= len(values):
        return default
    return values[idx]


def _detail_note(items):
    if not items:
        return ""
    return " (" + ", ".join(items) + ")"


def _snorkel_note(wave_avg, wind_speed, score):
    if wave_avg is None and wind_speed is None:
        return "Forecast data is limited, so snorkelling conditions are uncertain."

    details = []
    if wave_avg is not None:
        details.append(f"waves ~{wave_avg:.1f}m")
    if wind_speed is not None:
        details.append(f"winds ~{wind_speed:.0f} km/h")

    detail_str = _detail_note(details)

    if wave_avg is not None and wave_avg >= 0.7 and wind_speed is not None and wind_speed >= 18:
        return f"Waves and wind are strong, making the water choppy and visibility poor{detail_str}."
    if wave_avg is not None and wave_avg >= 0.7:
        return f"Waves are too large for calm snorkelling{detail_str}."
    if wind_speed is not None and wind_speed >= 18:
        return f"Winds are strong, so the water will be choppy and less clear{detail_str}."
    if score is not None and score < 4.5:
        return f"Conditions are below the calm-water threshold for snorkelling{detail_str}."
    return f"Conditions are below the calm-water threshold for snorkelling{detail_str}."


def _beach_note(wind_speed, temp, score):
    if wind_speed is None and temp is None:
        return "Forecast data is limited, so beach comfort is uncertain."

    details = []
    if temp is not None:
        details.append(f"air ~{temp:.0f}°C")
    if wind_speed is not None:
        details.append(f"wind ~{wind_speed:.0f} km/h")

    detail_str = _detail_note(details)

    if wind_speed is not None and wind_speed >= 25:
        return f"Strong winds will make it uncomfortable on the beach{detail_str}."
    if temp is not None and (temp < 22 or temp > 36):
        return f"Temperatures are outside the comfortable range for sunbathing{detail_str}."
    if score is not None and score < 4.5:
        return f"Conditions are below the comfortable range for sunbathing{detail_str}."
    return f"Conditions are below the comfortable range for sunbathing{detail_str}."


def generate_forecast(raw_data: dict, water_temp: float, errors: list, mode="v6", cache_hits=None) -> dict:
    """Generate forecast using local ratings + Claude for summary."""
    now = datetime.now()
    snorkel_ratings, beach_ratings = process_all_ratings(
        raw_data, SNORKEL_SPOTS, SUNBATHING_SPOTS, mode=mode
    )

    dates = [(now + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    date_labels = [
        (now + timedelta(days=i)).strftime("%a %-d") + get_ordinal((now + timedelta(days=i)).day)
        for i in range(7)
    ]

    forecast = {
        "water_temp_c": water_temp,
        "dates": dates,
        "date_labels": date_labels,
        "today": {"date": dates[0], "date_label": date_labels[0]},
        "snorkel": {},
        "sunbathing": {},
        "top_picks": {},
        "errors": errors,
        "meta": {
            "version": VERSION,
            "mode": mode,
            "generated_at": now.isoformat(),
            "cache_hits": cache_hits or [],
        },
    }

    best_snorkel = {
        "score": 0,
        "spot": None,
        "day": None,
        "time": None,
        "why": None,
        "wave_avg": None,
        "wind": None,
    }

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
                    "best_time": d.get("best_time", "06:00-10:00"),
                }

                if score > best_snorkel["score"]:
                    best_snorkel = {
                        "score": score,
                        "spot": spot_name,
                        "day": date_labels[dates.index(date)],
                        "time": d.get("best_time", "06:00-10:00"),
                        "why": f"{d.get('wave_avg', 0.5):.1f}m waves, {d['conditions'][0]['wind'] if d['conditions'] else 15:.0f}km/h wind",
                        "wave_avg": d.get("wave_avg", 0.5),
                        "wind": d["conditions"][0]["wind"] if d["conditions"] else 15,
                    }

    best_beach = {"score": 0, "spot": None, "day": None, "why": None, "temp": None, "wind": None}

    for spot_name, daily_data in beach_ratings.items():
        forecast["sunbathing"][spot_name] = {}
        spot_daily = raw_data.get(spot_name, {}).get("weather", {}).get("daily", {})

        for date in dates:
            if date in daily_data:
                d = daily_data[date]
                score = d.get("beach_avg", 5)
                label = score_to_label(score)

                temp = d["conditions"][0]["temp"] if d["conditions"] else 28
                wind = d["conditions"][0]["wind"] if d["conditions"] else 15
                temp_max = _daily_value(spot_daily, date, "temperature_2m_max", temp)
                temp_min = _daily_value(spot_daily, date, "temperature_2m_min", temp)
                wind_max = _daily_value(spot_daily, date, "wind_speed_10m_max", wind)

                forecast["sunbathing"][spot_name][date] = {
                    "rating": label,
                    "score": score,
                    "temp": round(temp) if temp else 28,
                    "wind": round(wind) if wind else 15,
                    "temp_max": round(temp_max) if temp_max is not None else None,
                    "temp_min": round(temp_min) if temp_min is not None else None,
                    "wind_max": round(wind_max) if wind_max is not None else None,
                }

                if score > best_beach["score"]:
                    best_beach = {
                        "score": score,
                        "spot": spot_name,
                        "day": date_labels[dates.index(date)],
                        "why": f"{temp:.0f}°C, {wind:.0f}km/h wind",
                        "temp": temp,
                        "wind": wind,
                    }

    snorkel_viable = best_snorkel["score"] >= 4.5
    if not snorkel_viable:
        best_snorkel["spot"] = "No viable picks"
        best_snorkel["day"] = None
        best_snorkel["time"] = None
        best_snorkel["why"] = None
        best_snorkel["note"] = _snorkel_note(best_snorkel.get("wave_avg"), best_snorkel.get("wind"), best_snorkel["score"])
    else:
        best_snorkel["note"] = ""

    beach_viable = best_beach["score"] >= 4.5
    if not beach_viable:
        best_beach["spot"] = "No viable picks"
        best_beach["day"] = None
        best_beach["why"] = None
        best_beach["note"] = _beach_note(best_beach.get("wind"), best_beach.get("temp"), best_beach["score"])
    else:
        best_beach["note"] = ""

    best_snorkel["viable"] = snorkel_viable
    best_beach["viable"] = beach_viable

    forecast["top_picks"] = {
        "best_snorkel": best_snorkel,
        "best_sunbathing": best_beach,
        "hidden_gem": {
            "spot": "Hamersley Pool" if "Hamersley Pool" in snorkel_ratings else "Watermans Bay",
            "day": best_snorkel.get("day", date_labels[0]),
            "time": best_snorkel.get("time", "06:00-10:00"),
            "why": "Same conditions as Mettams, fewer people",
        },
    }
    if not snorkel_viable:
        forecast["top_picks"]["hidden_gem"] = {
            "spot": "No viable picks",
            "day": None,
            "time": None,
            "why": best_snorkel.get("note"),
        }

    try:
        if not ANTHROPIC_API_KEY or anthropic is None:
            raise RuntimeError("Anthropic not available")

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        snorkel_line = (
            f"Best snorkel: {best_snorkel['spot']} on {best_snorkel['day']} (score {best_snorkel['score']}/10) - {best_snorkel['why']}"
            if snorkel_viable
            else f"Snorkel outlook: No viable picks — {best_snorkel.get('note')}"
        )
        beach_line = (
            f"Best beach: {best_beach['spot']} on {best_beach['day']} (score {best_beach['score']}/10) - {best_beach['why']}"
            if beach_viable
            else f"Beach outlook: No viable picks — {best_beach.get('note')}"
        )

        summary_prompt = f"""You are a professional beach forecaster for Perth, WA. Write a 2-3 sentence summary of conditions.

{snorkel_line}
{beach_line}
Water temp: {water_temp}°C
Errors: {len(errors)} beaches failed to fetch

Be factual and professional. Mention specific conditions and best days. No superlatives or flowery language.
Example: "Good snorkelling conditions expected at Mettams Pool on Tuesday with 0.4m waves and light 10km/h winds. Beach conditions best at Cottesloe Wednesday with 30°C and minimal wind."

Respond with ONLY the summary text, nothing else."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{"role": "user", "content": summary_prompt}],
        )

        forecast["summary"] = response.content[0].text.strip()
    except Exception:
        snorkel_summary = (
            f"Best snorkelling at {best_snorkel['spot']} ({best_snorkel['score']}/10). "
            if snorkel_viable
            else f"No viable snorkelling picks — {best_snorkel.get('note')} "
        )
        beach_summary = (
            f"Best beach day at {best_beach['spot']} ({best_beach['score']}/10). "
            if beach_viable
            else f"No viable beach picks — {best_beach.get('note')} "
        )
        forecast["summary"] = f"{snorkel_summary}{beach_summary}Water temperature {water_temp}°C."

    if raw_data:
        first_spot = list(raw_data.values())[0]
        weather = first_spot.get("weather", {})
        daily = weather.get("daily", {})

        forecast["today"]["temp_max"] = _first(daily.get("temperature_2m_max"), 30)
        forecast["today"]["wind_speed"] = _first(daily.get("wind_speed_10m_max"), 15)
        forecast["today"]["wind_direction"] = deg_to_compass(
            _first(daily.get("wind_direction_10m_dominant"), 0)
        )
        forecast["today"]["description"] = (
            "Sunny" if _first(daily.get("uv_index_max"), 5) > 5 else "Partly cloudy"
        )

    return forecast
