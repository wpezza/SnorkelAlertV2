# 🌊 Snorkel Alert v6.0

Perth beach forecast with **calibrated ratings** based on real experience.

## What's New in v6

### Directional Shelter + Shoreline Offshore
- Shelter weighting now scales by direction (full vs partial protection)
- Offshore winds are computed using shoreline orientation per spot

### Best-Time Window
- Uses a rolling 3-hour average to select the best snorkel window

### Morning-Weighted Scoring
- Daily scores weight morning hours higher to reflect calmer conditions before the Fremantle Doctor

### Reliability Improvements
- Optional cache fallback for API outages
- Safer handling of missing hourly data

### Compatibility Mode
- `--mode v5` or `--compat` reproduces the v5 rating logic

### Regression Fixtures
- Scripts added to capture raw API snapshots and compare outputs

## Real-World Calibration
Ratings are calibrated from actual beach visits:
- **Mettams Pool, 2 Feb 2026**: 0.44-0.50m waves, 9-15 km/h wind → 8/10
- **Watermans Bay (field note)**: conditions amazing, ~8/10

## Rating Algorithm (v6)

### Snorkel Rating (10 points, deduct for issues)

| Factor | Deduction |
|--------|-----------|
| Effective waves >0.5m | 1-4 pts |
| Wind >15 km/h (worse if onshore) | 0.3-3 pts |
| Short swell period <8s | 0.3-1 pt |
| Sea temp outside 23-27°C | 0.5-1 pt |
| Air temp outside 25-32°C | 0.3-1 pt |

### Beach Rating (10 points)

| Factor | Deduction |
|--------|-----------|
| Wind >15 km/h | 0.5-4 pts |
| Feels like outside 26-32°C | 0.5-3 pts |
| UV >8 | 0.3-1.5 pts |
| Cloud >60% | 0.5-1.5 pts |

## Setup

1. Fork this repo
2. Add secrets in Settings → Secrets:
   - `ANTHROPIC_API_KEY` (required for summary generation)
   - `PUSHOVER_USER_KEY` (optional)
   - `PUSHOVER_API_TOKEN` (optional)
3. Enable GitHub Pages (Settings → Pages → Source: **gh-pages**)
4. Run manually or wait for 5am daily

## GitHub Pages Troubleshooting

If `https://username.github.io/RepoName` redirects to GitHub instead of loading:
- Ensure Pages is set to **Deploy from branch: gh-pages / (root)**.
- Confirm the workflow is generating `docs/index.html` (not the placeholder redirect).
- If you prefer **main/docs**, remove the gh-pages deploy step and set Pages to `main` + `/docs`.

## Forecast History

Each run saves a snapshot in `docs/history/forecast-YYYY-MM-DD.json` and keeps the most recent 180 days by default.
You can change retention with `--history-days 90` (or any number of days).

## Files

```
snorkel-alert-v6/
├── snorkel_alert.py           # Main script (CLI)
├── snorkel_alert_lib/         # Modularized code
├── tools/                     # Fixture/compare scripts
├── fixtures/                  # Regression fixtures
├── .github/workflows/
│   └── forecast.yml           # GitHub Actions
├── docs/
│   ├── index.html             # Dashboard (generated)
│   └── forecast.json          # Raw data (generated)
└── README.md
```

## Data Sources

- **Weather**: [Open-Meteo](https://open-meteo.com/) (free, no API key)
- **Marine**: [Open-Meteo Marine](https://marine-api.open-meteo.com/) (free, no API key)
- **Summary**: Claude Sonnet (requires API key)

## Cost

~$0.01/day for Claude API (summary only, ~200 tokens)

---

Built with 🤿 by Claude & Will
