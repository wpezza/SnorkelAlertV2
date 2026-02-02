#!/usr/bin/env python3
"""
🌊 SNORKEL ALERT V6.0 - Perth Beach Forecast
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Major upgrades:
- Directional shelter weighting + shoreline-aware offshore winds
- Best-time window via rolling average
- Optional cache fallback for API outages
- Modularized code with compatibility mode

Author: Claude & Will
Version: 6.0.0
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from snorkel_alert_lib.config import VERSION, SNORKEL_SPOTS, SUNBATHING_SPOTS
from snorkel_alert_lib.fetching import DataCache, fetch_all_data, fetch_water_temp
from snorkel_alert_lib.forecast import generate_forecast
from snorkel_alert_lib.notify import format_pushover, send_pushover
from snorkel_alert_lib.dashboard import generate_dashboard


def build_spot_map():
    """Combine snorkel and sunbathing spots, de-duplicated by name."""
    all_spots = {}
    for spot in SNORKEL_SPOTS + SUNBATHING_SPOTS:
        if spot["name"] not in all_spots:
            all_spots[spot["name"]] = spot
    return all_spots


def parse_args():
    parser = argparse.ArgumentParser(description="Snorkel Alert forecast generator")
    parser.add_argument("--mode", choices=["v5", "v6"], default="v6", help="Rating mode")
    parser.add_argument("--compat", action="store_true", help="Alias for --mode v5")
    parser.add_argument("--use-cache", action="store_true", help="Use cached data if fetch fails")
    parser.add_argument("--cache-dir", default=".cache", help="Cache directory")
    parser.add_argument("--cache-ttl-hours", type=int, default=36, help="Cache TTL in hours")
    parser.add_argument("--history-days", type=int, default=180, help="History retention in days")
    return parser.parse_args()


def _write_history(docs_dir: Path, forecast: dict, retain_days: int):
    history_dir = docs_dir / "history"
    history_dir.mkdir(exist_ok=True)

    date_str = forecast.get("today", {}).get("date") or datetime.now().strftime("%Y-%m-%d")
    history_path = history_dir / f"forecast-{date_str}.json"
    history_path.write_text(json.dumps(forecast, indent=2))

    cutoff = datetime.now().date().toordinal() - retain_days
    for path in history_dir.glob("forecast-*.json"):
        stem = path.stem.replace("forecast-", "")
        try:
            day = datetime.strptime(stem, "%Y-%m-%d").date()
        except ValueError:
            continue
        if day.toordinal() < cutoff:
            path.unlink()


def main():
    args = parse_args()
    mode = "v5" if args.compat else args.mode

    print(
        f"""
╔═══════════════════════════════════════════════════════════════════╗
║  🌊 SNORKEL ALERT v{VERSION} - Perth Beach Forecast               ║
║  Ratings calibrated from real experience                          ║
╚═══════════════════════════════════════════════════════════════════╝
"""
    )
    print(f"📅 {datetime.now().strftime('%A %-d %B %Y, %-I:%M%p')} AWST\n")

    cache = DataCache(Path(args.cache_dir)) if args.use_cache else None

    print("━━━ FETCHING DATA ━━━")
    print("  (with retry logic and optional cache fallback)\n")

    all_spots = build_spot_map()
    raw_data, errors, cache_hits = fetch_all_data(
        all_spots,
        cache=cache,
        cache_ttl_hours=args.cache_ttl_hours,
        use_cache=args.use_cache,
    )

    if not raw_data:
        print("❌ No data fetched, aborting")
        return

    print("\n  🌡️ Fetching water temperature...", end=" ", flush=True)
    water_temp = fetch_water_temp()
    print(f"{water_temp}°C ✅" if water_temp else "❌")

    if errors:
        print(f"\n  ⚠️ Failed to fetch: {', '.join(errors)}")

    print(f"\n  ✅ Successfully fetched {len(raw_data)}/{len(raw_data) + len(errors)} beaches")

    if cache_hits:
        print(f"  📦 Cache used for: {', '.join(cache_hits)}")

    print("\n━━━ CALCULATING RATINGS ━━━")
    print("  🧮 Processing local ratings...", end=" ", flush=True)

    try:
        forecast = generate_forecast(raw_data, water_temp, errors, mode=mode, cache_hits=cache_hits)
        print("✅")
    except Exception as e:
        print(f"❌ {e}")
        import traceback

        traceback.print_exc()
        return

    print(f"\n{'═' * 60}")
    print(f"\n{forecast.get('summary', 'No summary')}\n")
    print(f"🌡️ Water: {forecast.get('water_temp_c', '?')}°C")

    top = forecast.get("top_picks", {})
    if top.get("best_snorkel", {}).get("spot"):
        p = top["best_snorkel"]
        time_str = f" @ {p.get('time', '')}" if p.get("time") else ""
        print(f"🤿 Best snorkel: {p['spot']} ({p['score']}/10 on {p['day']}{time_str})")
    if top.get("best_sunbathing", {}).get("spot"):
        p = top["best_sunbathing"]
        print(f"☀️ Best sunbathing: {p['spot']} ({p['score']}/10 on {p['day']})")

    print("\n━━━ NOTIFICATIONS ━━━")
    title, message = format_pushover(forecast)
    print(f"\n{title}\n{message}\n")
    send_pushover(title, message)

    print("\n━━━ DASHBOARD ━━━")
    try:
        base_dir = Path(__file__).resolve().parent
        docs_dir = base_dir / "docs"
        docs_dir.mkdir(exist_ok=True)
        html = generate_dashboard(forecast)
        (docs_dir / "index.html").write_text(html)
        (docs_dir / "forecast.json").write_text(json.dumps(forecast, indent=2))
        _write_history(docs_dir, forecast, args.history_days)
        print("  📊 Dashboard saved to docs/index.html ✅")
    except Exception as e:
        print(f"  ❌ Dashboard failed: {e}")

    print(f"\n{'═' * 60}")
    print("✅ COMPLETE\n")


if __name__ == "__main__":
    main()
