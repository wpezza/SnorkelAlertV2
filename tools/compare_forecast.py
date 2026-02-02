#!/usr/bin/env python3
"""Compare forecast output against a baseline file."""

import argparse
import json
from pathlib import Path

from snorkel_alert_lib.forecast import generate_forecast


def main():
    parser = argparse.ArgumentParser(description="Compare forecast vs baseline")
    parser.add_argument("--fixture", required=True, help="Fixture JSON file")
    parser.add_argument("--baseline", required=True, help="Baseline forecast JSON file")
    parser.add_argument("--mode", choices=["v5", "v6"], default="v6")
    parser.add_argument("--write", action="store_true", help="Write baseline from fixture")
    args = parser.parse_args()

    fixture_path = Path(args.fixture)
    baseline_path = Path(args.baseline)

    fixture = json.loads(fixture_path.read_text())
    raw_data = fixture.get("raw_data", {})
    water_temp = fixture.get("water_temp")
    errors = fixture.get("errors", [])

    forecast = generate_forecast(raw_data, water_temp, errors, mode=args.mode)

    if args.write:
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(json.dumps(forecast, indent=2))
        print(f"Baseline written to {baseline_path}")
        return

    baseline = json.loads(baseline_path.read_text())

    issues = []
    max_score_diff = 0
    diff_samples = []

    for section in ["snorkel", "sunbathing"]:
        base_spots = baseline.get(section, {})
        new_spots = forecast.get(section, {})

        for spot, base_days in base_spots.items():
            if spot not in new_spots:
                issues.append(f"Missing spot in {section}: {spot}")
                continue

            for date, base_vals in base_days.items():
                new_vals = new_spots.get(spot, {}).get(date)
                if not new_vals:
                    issues.append(f"Missing date in {section} for {spot}: {date}")
                    continue

                base_score = base_vals.get("score")
                new_score = new_vals.get("score")
                if base_score is None or new_score is None:
                    continue

                diff = abs(base_score - new_score)
                if diff > max_score_diff:
                    max_score_diff = diff
                if diff >= 0.5:
                    diff_samples.append(f"{section} {spot} {date}: {base_score} -> {new_score}")

    if issues:
        print("Issues found:")
        for issue in issues:
            print(f"- {issue}")
    else:
        print("Spot/date coverage matches baseline.")

    print(f"Max score delta: {max_score_diff}")
    if diff_samples:
        print("Sample diffs (>=0.5):")
        for sample in diff_samples[:10]:
            print(f"- {sample}")


if __name__ == "__main__":
    main()
