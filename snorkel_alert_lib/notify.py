"""Notification helpers for Pushover and Telegram."""

import requests

from .config import PUSHOVER_API_TOKEN, PUSHOVER_USER_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from .ratings import score_to_emoji, score_to_label


def format_pushover(forecast: dict) -> tuple:
    """Format Pushover notification with scores."""
    lines = []

    lines.append("SNORKELLING (Next 3 Days)")

    dates = forecast.get("dates", [])[:3]
    date_labels = forecast.get("date_labels", [])[:3]
    snorkel_data = forecast.get("snorkel", {})

    for date, label in zip(dates, date_labels):
        day_spots = []
        best_time = None

        for spot, days in snorkel_data.items():
            if date in days:
                score = days[date].get("score", 5)
                time = days[date].get("best_time", "")

                if score >= 6:
                    short_name = (
                        spot.replace(" Pool", "")
                        .replace(" Bay", "")
                        .replace(" Reef", "")
                        .replace(" Wreck", "")
                        .replace(" Lagoon", "")
                    )
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
                spots_str += f" +{len(day_spots) - 3}"

            lines.append(f"{emoji} {label}: {rating} {best_score}/10{time_str}")
            lines.append(f"   {spots_str}")
        else:
            lines.append(f"\U0001f534 {label}: No good spots")

    lines.append("")
    lines.append("SUNBATHING (Next 3 Days)")

    sunbathing_data = forecast.get("sunbathing", {})

    for date, label in zip(dates, date_labels):
        day_spots = []

        for spot, days in sunbathing_data.items():
            if date in days:
                score = days[date].get("score", 5)
                if score >= 6:
                    short_name = spot.replace(" Beach", "").replace(" Bay", "")
                    day_spots.append((short_name, score, days[date]))

        day_spots.sort(key=lambda x: x[1], reverse=True)

        if day_spots:
            best_name, best_score, best_data = day_spots[0]
            emoji = score_to_emoji(best_score)
            rating = score_to_label(best_score)

            temp_max = best_data.get("temp_max") or best_data.get("temp")
            temp_min = best_data.get("temp_min") or best_data.get("temp")
            wind_max = best_data.get("wind_max") or best_data.get("wind")
            detail = f"{temp_max}°/{temp_min}° {wind_max}km/h"

            spots_str = ", ".join([s[0] for s in day_spots[:3]])
            if len(day_spots) > 3:
                spots_str += f" +{len(day_spots) - 3}"

            lines.append(f"{emoji} {label}: {rating} {best_score}/10 ({detail})")
            lines.append(f"   {spots_str}")
        else:
            lines.append(f"\U0001f534 {label}: No good spots")

    lines.append("")
    today = forecast.get("today", {})
    temp = today.get("temp_max", "?")
    wind = today.get("wind_speed", "?")
    wind_dir = today.get("wind_direction", "")

    lines.append(f"TODAY: {temp}°C, {wind}km/h {wind_dir}")

    water = forecast.get("water_temp_c", "?")
    lines.append(f"\U0001f30a Water: {water}°C")

    errors = forecast.get("errors", [])
    if errors:
        lines.append(f"\u26a0\ufe0f Missing: {len(errors)} beaches")

    top_picks = forecast.get("top_picks", {})
    best_snorkel = top_picks.get("best_snorkel", {})
    if best_snorkel and not best_snorkel.get("viable", True):
        note = best_snorkel.get(
            "note", "Conditions are below the calm-water threshold for snorkelling."
        )
        lines.append(f"SNORKEL: No viable picks — {note}")

    best_beach = top_picks.get("best_sunbathing", {})
    if best_beach and not best_beach.get("viable", True):
        note = best_beach.get(
            "note", "Conditions are below the comfortable range for sunbathing."
        )
        lines.append(f"BEACH: No viable picks — {note}")

    return "\U0001f93f Snorkel Alert v6", "\n".join(lines)


def send_pushover(title: str, message: str):
    """Send Pushover notification."""
    if not PUSHOVER_USER_KEY or not PUSHOVER_API_TOKEN:
        print("  \u26a0\ufe0f Pushover not configured")
        return

    try:
        resp = requests.post(
            "https://api.pushover.net/1/messages.json",
            data={
                "token": PUSHOVER_API_TOKEN,
                "user": PUSHOVER_USER_KEY,
                "title": title,
                "message": message,
                "html": 0,
            },
            timeout=30,
        )
        resp.raise_for_status()
        print("  \U0001f4f1 Pushover sent \u2705")
    except Exception as e:
        print(f"  \u274c Pushover failed: {e}")


def send_telegram(message: str):
    """Send Telegram notification."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"},
            timeout=30,
        )
        print("  \U0001f4f1 Telegram sent \u2705")
    except Exception as e:
        print(f"  \u274c Telegram failed: {e}")
