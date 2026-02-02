"""Rating calculations for snorkel and beach conditions."""

from .compass import is_sheltered_from, shelter_weight, is_offshore_v5, is_offshore_v6
from .config import DEFAULT_SHORE_NORMAL_DEG


def safe_get(seq, idx, default=None):
    """Safe list access for uneven API arrays."""
    try:
        return seq[idx]
    except Exception:
        return default


def score_to_label(score):
    """Convert numeric score to text label."""
    if score >= 9:
        return "Perfect"
    if score >= 7.5:
        return "Great"
    if score >= 6:
        return "Good"
    if score >= 4.5:
        return "OK"
    if score >= 3:
        return "Poor"
    return "Bad"


def score_to_emoji(score):
    """Convert numeric score to emoji."""
    if score >= 9:
        return "🤿"
    if score >= 7.5:
        return "⭐"
    if score >= 6:
        return "🟢"
    if score >= 4.5:
        return "🟡"
    return "🔴"


def _snorkel_rating_v5(
    wave_height,
    swell_height,
    wind_wave_height,
    wind_speed,
    wind_dir_deg,
    swell_dir_deg,
    swell_period,
    sea_temp,
    air_temp,
    spot,
):
    """Legacy snorkel rating logic (v5)."""
    score = 10.0

    shelter_factor = spot.get("shelter_factor", 0)
    shelter_from = spot.get("shelter_from", [])

    effective_swell = swell_height or 0
    if is_sheltered_from(shelter_from, swell_dir_deg):
        effective_swell = effective_swell * (1 - shelter_factor * 0.7)

    effective_wave = (wind_wave_height or 0) + effective_swell

    if effective_wave < 0.2:
        wave_penalty = 0
    elif effective_wave < 0.35:
        wave_penalty = 0.5
    elif effective_wave < 0.5:
        wave_penalty = 1.0
    elif effective_wave < 0.7:
        wave_penalty = 2.0
    elif effective_wave < 1.0:
        wave_penalty = 3.0
    else:
        wave_penalty = 4.0

    score -= wave_penalty

    wind = wind_speed or 0
    is_offshore = is_offshore_v5(wind_dir_deg)

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

    period = swell_period or 8
    if period >= 10:
        score -= 0
    elif period >= 8:
        score -= 0.3
    elif period >= 6:
        score -= 0.6
    else:
        score -= 1.0

    sea = sea_temp or 24
    if 23 <= sea <= 27:
        score -= 0
    elif 21 <= sea <= 29:
        score -= 0.5
    else:
        score -= 1.0

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


def _snorkel_rating_v6(
    wave_height,
    swell_height,
    wind_wave_height,
    wind_speed,
    wind_dir_deg,
    swell_dir_deg,
    swell_period,
    sea_temp,
    air_temp,
    spot,
):
    """Improved snorkel rating logic with directional shelter and offshore calc."""
    score = 10.0

    shelter_factor = spot.get("shelter_factor", 0)
    shelter_from = spot.get("shelter_from", [])
    shore_normal = spot.get("shore_normal_deg", DEFAULT_SHORE_NORMAL_DEG)

    effective_swell = swell_height or 0
    swell_weight = shelter_weight(shelter_from, swell_dir_deg)
    if swell_weight:
        effective_swell = effective_swell * (1 - shelter_factor * 0.7 * swell_weight)

    effective_wave = (wind_wave_height or 0) + effective_swell

    if effective_wave < 0.2:
        wave_penalty = 0
    elif effective_wave < 0.35:
        wave_penalty = 0.5
    elif effective_wave < 0.5:
        wave_penalty = 1.0
    elif effective_wave < 0.7:
        wave_penalty = 2.0
    elif effective_wave < 1.0:
        wave_penalty = 3.0
    else:
        wave_penalty = 4.0

    score -= wave_penalty

    wind = wind_speed or 0
    wind_weight = shelter_weight(shelter_from, wind_dir_deg)
    if wind_weight:
        wind = wind * (1 - shelter_factor * 0.4 * wind_weight)

    is_offshore = is_offshore_v6(wind_dir_deg, shore_normal)

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

    period = swell_period or 8
    if period >= 10:
        score -= 0
    elif period >= 8:
        score -= 0.3
    elif period >= 6:
        score -= 0.6
    else:
        score -= 1.0

    sea = sea_temp or 24
    if 23 <= sea <= 27:
        score -= 0
    elif 21 <= sea <= 29:
        score -= 0.5
    else:
        score -= 1.0

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


def calculate_snorkel_rating(
    wave_height,
    swell_height,
    wind_wave_height,
    wind_speed,
    wind_dir_deg,
    swell_dir_deg,
    swell_period,
    sea_temp,
    air_temp,
    spot,
    mode="v6",
):
    if mode == "v5":
        return _snorkel_rating_v5(
            wave_height,
            swell_height,
            wind_wave_height,
            wind_speed,
            wind_dir_deg,
            swell_dir_deg,
            swell_period,
            sea_temp,
            air_temp,
            spot,
        )
    return _snorkel_rating_v6(
        wave_height,
        swell_height,
        wind_wave_height,
        wind_speed,
        wind_dir_deg,
        swell_dir_deg,
        swell_period,
        sea_temp,
        air_temp,
        spot,
    )


def calculate_beach_rating(wind_speed, gusts, air_temp, feels_like, cloud, uv, humidity):
    """Calculate beach/sunbathing rating 0-10."""
    score = 10.0

    wind = wind_speed or 0
    gust = gusts or wind

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

    uv_val = uv or 5
    if uv_val <= 6:
        score -= 0
    elif uv_val <= 8:
        score -= 0.3
    elif uv_val <= 10:
        score -= 0.7
    else:
        score -= 1.5

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


def morning_weight(hour):
    """Weight mornings higher to reflect calmer conditions before the sea breeze."""
    if hour <= 7:
        return 1.1
    if hour <= 9:
        return 1.25
    if hour <= 12:
        return 1.4
    if hour <= 13:
        return 0.9
    return 0.7


def weighted_average(conditions, key, precision=1):
    total = 0.0
    weight_total = 0.0
    for item in conditions:
        value = item.get(key)
        if value is None:
            continue
        weight = morning_weight(item.get("hour", 0))
        total += value * weight
        weight_total += weight
    if weight_total == 0:
        return None
    return round(total / weight_total, precision)


def best_time_window(conditions, window=3, default_start=6, max_end=14):
    """Pick the best consecutive window by average snorkel score."""
    if not conditions:
        return f"{default_start:02d}:00-{min(default_start + window, max_end):02d}:00"

    ordered = sorted(conditions, key=lambda c: c.get("hour", 0))
    if len(ordered) < window:
        start = ordered[0].get("hour", default_start)
        return f"{start:02d}:00-{min(start + window, max_end):02d}:00"

    best_avg = -1
    best_start = ordered[0].get("hour", default_start)

    for i in range(0, len(ordered) - window + 1):
        slice_ = ordered[i : i + window]
        start_hour = slice_[0].get("hour", default_start)
        end_hour = slice_[-1].get("hour", start_hour)
        if end_hour - start_hour != window - 1:
            continue

        avg = sum(c.get("snorkel", 0) for c in slice_) / window
        if avg > best_avg:
            best_avg = avg
            best_start = start_hour

    best_end = min(best_start + window, max_end)
    return f"{best_start:02d}:00-{best_end:02d}:00"


def calculate_ratings_for_spot(spot_data: dict, spot_info: dict, hours: list = None, mode="v6") -> dict:
    """Calculate ratings for a spot using local algorithm."""
    if hours is None:
        hours = list(range(6, 15))

    marine = spot_data.get("marine", {})
    weather = spot_data.get("weather", {})

    mh = marine.get("hourly", {})
    wh = weather.get("hourly", {})

    times = wh.get("time", [])

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
                "conditions": [],
            }

        wave_height = safe_get(mh.get("wave_height", []), i)
        swell_height = safe_get(mh.get("swell_wave_height", []), i)
        wind_wave_height = safe_get(mh.get("wind_wave_height", []), i)
        swell_dir = safe_get(mh.get("swell_wave_direction", []), i)
        swell_period = safe_get(mh.get("swell_wave_period", []), i)
        sea_temp = safe_get(mh.get("sea_surface_temperature", []), i)

        temp = safe_get(wh.get("temperature_2m", []), i)
        feels = safe_get(wh.get("apparent_temperature", []), i)
        wind = safe_get(wh.get("wind_speed_10m", []), i)
        wind_dir = safe_get(wh.get("wind_direction_10m", []), i)
        gusts = safe_get(wh.get("wind_gusts_10m", []), i)
        cloud = safe_get(wh.get("cloud_cover", []), i)
        uv = safe_get(wh.get("uv_index", []), i)
        humidity = safe_get(wh.get("relative_humidity_2m", []), i)

        snorkel_score, effective_wave = calculate_snorkel_rating(
            wave_height,
            swell_height,
            wind_wave_height,
            wind,
            wind_dir,
            swell_dir,
            swell_period,
            sea_temp,
            temp,
            spot_info,
            mode=mode,
        )

        beach_score = calculate_beach_rating(wind, gusts, temp, feels, cloud, uv, humidity)

        daily_ratings[date]["snorkel_scores"].append(snorkel_score)
        daily_ratings[date]["beach_scores"].append(beach_score)
        daily_ratings[date]["effective_waves"].append(effective_wave)
        daily_ratings[date]["conditions"].append(
            {
                "hour": hour,
                "snorkel": snorkel_score,
                "beach": beach_score,
                "wave": effective_wave,
                "wind": wind,
                "temp": temp,
            }
        )

        if snorkel_score > daily_ratings[date]["best_snorkel_score"]:
            daily_ratings[date]["best_snorkel_score"] = snorkel_score
            daily_ratings[date]["best_hour"] = hour

    for date, data in daily_ratings.items():
        if data["snorkel_scores"]:
            if mode == "v5":
                data["snorkel_avg"] = round(sum(data["snorkel_scores"]) / len(data["snorkel_scores"]), 1)
                data["beach_avg"] = round(sum(data["beach_scores"]) / len(data["beach_scores"]), 1)
                data["wave_avg"] = round(sum(data["effective_waves"]) / len(data["effective_waves"]), 2)
            else:
                data["snorkel_avg"] = weighted_average(data["conditions"], "snorkel", precision=1)
                data["beach_avg"] = weighted_average(data["conditions"], "beach", precision=1)
                data["wave_avg"] = weighted_average(data["conditions"], "wave", precision=2)

            if mode == "v5":
                conditions = data["conditions"]
                best_start = conditions[0]["hour"] if conditions else 6
                best_end = best_start + 3

                for c in conditions:
                    if c["snorkel"] < data["snorkel_avg"] - 1:
                        best_end = c["hour"]
                        break
                    best_end = c["hour"] + 1

                data["best_time"] = f"{best_start:02d}:00-{min(best_end, 14):02d}:00"
            else:
                data["best_time"] = best_time_window(data["conditions"], window=3)

    return daily_ratings


def process_all_ratings(raw_data: dict, snorkel_spots: list, sunbathing_spots: list, mode="v6") -> dict:
    """Process ratings for all spots."""
    snorkel_ratings = {}
    beach_ratings = {}

    spot_info = {}
    for spot in snorkel_spots + sunbathing_spots:
        spot_info[spot["name"]] = spot

    snorkel_names = {s["name"] for s in snorkel_spots}
    beach_names = {s["name"] for s in sunbathing_spots}

    for name, data in raw_data.items():
        info = spot_info.get(name, {"shelter_from": [], "shelter_factor": 0})
        ratings = calculate_ratings_for_spot(data, info, mode=mode)

        if name in snorkel_names:
            snorkel_ratings[name] = ratings
        if name in beach_names:
            beach_ratings[name] = ratings

    return snorkel_ratings, beach_ratings
