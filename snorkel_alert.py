import difflib

def normalize_forecast_keys(forecast: dict) -> dict:
    """Map Claude spot keys back to canonical names using fuzzy matching."""
    canonical_snorkel = [s["name"] for s in SNORKEL_SPOTS]
    canonical_sun = [s["name"] for s in SUNBATHING_SPOTS]

    def remap(section_name: str, canonical: list[str]):
        section = forecast.get(section_name, {})
        if not isinstance(section, dict):
            forecast[section_name] = {}
            return

        new_section = {}
        for k, v in section.items():
            if k in canonical:
                new_section[k] = v
                continue

            match = difflib.get_close_matches(k, canonical, n=1, cutoff=0.72)
            if match:
                new_section[match[0]] = v
            else:
                # keep unmatched keys so you can inspect them in forecast.json
                new_section[k] = v

        forecast[section_name] = new_section

    remap("snorkel", canonical_snorkel)
    remap("sunbathing", canonical_sun)
    return forecast
