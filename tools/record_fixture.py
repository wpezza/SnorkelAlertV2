#!/usr/bin/env python3
"""Record raw API data for regression fixtures."""

import argparse
import json
from datetime import datetime
from pathlib import Path

from snorkel_alert_lib.config import SNORKEL_SPOTS, SUNBATHING_SPOTS
from snorkel_alert_lib.fetching import fetch_all_data, fetch_water_temp, DataCache


def build_spot_map():
    all_spots = {}
    for spot in SNORKEL_SPOTS + SUNBATHING_SPOTS:
        if spot["name"] not in all_spots:
            all_spots[spot["name"]] = spot
    return all_spots


def main():
    parser = argparse.ArgumentParser(description="Record raw API snapshot")
    parser.add_argument("--output", default="fixtures/raw_latest.json", help="Output path")
    parser.add_argument("--use-cache", action="store_true", help="Use cache fallback")
    parser.add_argument("--cache-dir", default=".cache", help="Cache directory")
    parser.add_argument("--cache-ttl-hours", type=int, default=36)
    args = parser.parse_args()

    cache = DataCache(Path(args.cache_dir)) if args.use_cache else None
    spots = build_spot_map()

    raw_data, errors, cache_hits = fetch_all_data(
        spots,
        cache=cache,
        cache_ttl_hours=args.cache_ttl_hours,
        use_cache=args.use_cache,
    )
    water_temp = fetch_water_temp()

    payload = {
        "generated_at": datetime.now().isoformat(),
        "water_temp": water_temp,
        "errors": errors,
        "cache_hits": cache_hits,
        "raw_data": raw_data,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2))
    print(f"Saved fixture to {output_path}")


if __name__ == "__main__":
    main()
