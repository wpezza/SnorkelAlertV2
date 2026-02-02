"""Dashboard HTML generation."""

from datetime import datetime

from .config import SNORKEL_SPOTS, SUNBATHING_SPOTS, WEBCAMS, VERSION
from .ratings import score_to_emoji


def generate_dashboard(forecast: dict) -> str:
    """Generate HTML dashboard with numeric scores."""

    now = datetime.now()
    updated = now.strftime("%A %-d %B %Y, %-I:%M%p").replace("AM", "am").replace("PM", "pm")

    dates = forecast.get("dates", [])
    date_labels = forecast.get("date_labels", [])
    snorkel = forecast.get("snorkel", {})
    sunbathing = forecast.get("sunbathing", {})
    top_picks = forecast.get("top_picks", {})
    errors = forecast.get("errors", [])

    weekends = []
    for i, d in enumerate(dates):
        dt = datetime.strptime(d, "%Y-%m-%d")
        if dt.weekday() >= 5:
            weekends.append(i)

    def rating_cell(data: dict, show_type: str = "snorkel") -> str:
        """Generate a table cell with score."""
        score = data.get("score", 5)
        emoji = score_to_emoji(score)

        if show_type == "snorkel":
            best_time = data.get("best_time", "")
            waves = data.get("waves", 0.5)
            if best_time:
                detail = best_time
            else:
                detail = f"{waves:.1f}m"
        else:
            temp_max = data.get("temp_max")
            temp_min = data.get("temp_min")
            wind_max = data.get("wind_max")
            if temp_max is None or temp_min is None:
                temp = data.get("temp", 28)
                temp_max = temp if temp_max is None else temp_max
                temp_min = temp if temp_min is None else temp_min
            if wind_max is None:
                wind_max = data.get("wind", 15)
            detail = f"🌡️ {temp_max}°/{temp_min}°  🌬️ {wind_max} km/h"

        if score >= 9:
            css_class = "perfect"
        elif score >= 7.5:
            css_class = "great"
        elif score >= 6:
            css_class = "good"
        elif score >= 4.5:
            css_class = "ok"
        else:
            css_class = "poor"

        return (
            f'<td class="rating-cell {css_class}">'
            f'<span class="score">{score}</span>'
            f'<span class="icon">{emoji}</span>'
            f'<span class="detail">{detail}</span>'
            f'</td>'
        )

    snorkel_rows = ""
    for spot in [s["name"] for s in SNORKEL_SPOTS]:
        if spot not in snorkel:
            continue
        cells = ""
        for date in dates:
            if date in snorkel[spot]:
                cells += rating_cell(snorkel[spot][date], "snorkel")
            else:
                cells += '<td class="rating-cell">-</td>'
        snorkel_rows += f'<tr><td class="beach-name">{spot}</td>{cells}</tr>\n'

    sunbathing_rows = ""
    for spot in [s["name"] for s in SUNBATHING_SPOTS]:
        if spot not in sunbathing:
            continue
        cells = ""
        for date in dates:
            if date in sunbathing[spot]:
                cells += rating_cell(sunbathing[spot][date], "sunbathing")
            else:
                cells += '<td class="rating-cell">-</td>'
        sunbathing_rows += f'<tr><td class="beach-name">{spot}</td>{cells}</tr>\n'

    header_cells = ""
    for i, label in enumerate(date_labels):
        weekend_class = "weekend" if i in weekends else ""
        weekend_star = "\u2605 " if i in weekends else ""
        header_cells += f'<th class="{weekend_class}">{weekend_star}{label}</th>'

    error_html = ""
    if errors:
        error_html = f'<div class="error-banner">\u26a0\ufe0f Missing data for: {", ".join(errors)}</div>'

    best_snorkel = top_picks.get("best_snorkel", {})
    best_sunbathing = top_picks.get("best_sunbathing", {})
    hidden_gem = top_picks.get("hidden_gem", {})

    snorkel_viable = best_snorkel.get("viable", True)
    snorkel_time = best_snorkel.get("time", "")
    if snorkel_viable:
        snorkel_detail = (
            f"{best_snorkel.get('day', '')} {snorkel_time} — {best_snorkel.get('why', '')}".strip()
        )
    else:
        snorkel_detail = best_snorkel.get("note", "")

    snorkel_score_display = (
        f"{best_snorkel.get('score', '?')}/10" if snorkel_viable else "—"
    )
    gem_time = hidden_gem.get("time", "")
    gem_detail = f"{hidden_gem.get('day', '')} {gem_time} — {hidden_gem.get('why', '')}".strip()

    beach_viable = best_sunbathing.get("viable", True)
    beach_score_display = (
        f"{best_sunbathing.get('score', '?')}/10" if beach_viable else "—"
    )
    if beach_viable:
        best_sunbathing_detail = (
            f"{best_sunbathing.get('day', '')} — {best_sunbathing.get('why', '')}"
        )
    else:
        best_sunbathing_detail = best_sunbathing.get("note", "")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>\U0001f30a Snorkel Alert v6 - Perth Beach Forecast</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>\U0001f30a</text></svg>">
    <style>
        :root {{
            --ocean: #0a1628;
            --ocean-mid: #1a3a5c;
            --seafoam: #4ecdc4;
            --perfect: #ffd700;
            --great: #22c55e;
            --good: #22c55e;
            --ok: #f59e0b;
            --poor: #ef4444;
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(180deg, var(--ocean) 0%, var(--ocean-mid) 100%);
            min-height: 100vh;
            color: white;
            line-height: 1.5;
        }}

        .container {{ max-width: 1100px; margin: 0 auto; padding: 20px; }}

        header {{ text-align: center; padding: 30px 20px; }}
        .logo {{ font-size: 2.2rem; font-weight: 700; margin-bottom: 5px; }}
        .tagline {{ opacity: 0.6; font-size: 0.95rem; }}
        .updated {{ margin-top: 8px; font-size: 0.8rem; opacity: 0.4; }}

        .summary-card {{
            background: rgba(255,255,255,0.08);
            border-radius: 12px;
            padding: 20px 24px;
            margin: 20px 0;
            font-size: 1rem;
            line-height: 1.6;
        }}

        .water-temp {{
            display: inline-block;
            margin-top: 12px;
            padding: 6px 12px;
            background: rgba(78,205,196,0.2);
            border-radius: 20px;
            font-size: 0.9rem;
        }}

        .error-banner {{
            background: rgba(239,68,68,0.2);
            border: 1px solid rgba(239,68,68,0.4);
            border-radius: 8px;
            padding: 10px 16px;
            margin: 15px 0;
            font-size: 0.85rem;
        }}

        .top-picks {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 12px;
            margin: 20px 0;
        }}

        .pick-card {{
            background: rgba(255,255,255,0.06);
            border-radius: 10px;
            padding: 16px;
        }}

        .pick-card.snorkel {{ border-left: 3px solid var(--seafoam); }}
        .pick-card.sunbathing {{ border-left: 3px solid var(--perfect); }}
        .pick-card.gem {{ border-left: 3px solid var(--great); }}

        .pick-label {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.6; margin-bottom: 4px; }}
        .pick-spot {{ font-size: 1.1rem; font-weight: 600; margin-bottom: 2px; }}
        .pick-score {{ font-size: 1.5rem; font-weight: 700; color: var(--seafoam); }}
        .pick-detail {{ font-size: 0.85rem; opacity: 0.7; }}

        .section-title {{
            font-size: 1.1rem;
            font-weight: 600;
            margin: 30px 0 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .table-container {{ overflow-x: auto; margin: 0 -20px; padding: 0 20px; }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
            background: rgba(255,255,255,0.03);
            border-radius: 10px;
            overflow: hidden;
        }}

        th, td {{
            padding: 10px 8px;
            text-align: center;
            border-bottom: 1px solid rgba(255,255,255,0.06);
        }}

        th {{
            background: rgba(255,255,255,0.05);
            font-weight: 600;
            font-size: 0.8rem;
        }}

        th.weekend {{
            background: rgba(255,215,0,0.15);
            color: var(--perfect);
        }}

        .beach-name {{
            text-align: left;
            font-weight: 500;
            white-space: nowrap;
            padding-left: 12px;
        }}

        .rating-cell {{ min-width: 70px; position: relative; }}

        .rating-cell .score {{
            display: block;
            font-size: 1.1rem;
            font-weight: 700;
        }}

        .rating-cell .icon {{
            display: block;
            font-size: 0.8rem;
            margin-top: 2px;
        }}

        .rating-cell .detail {{
            display: block;
            font-size: 0.65rem;
            opacity: 0.6;
            margin-top: 2px;
        }}

        .rating-cell.perfect {{ background: rgba(255,215,0,0.15); }}
        .rating-cell.perfect .score {{ color: var(--perfect); }}

        .rating-cell.great {{ background: rgba(34,197,94,0.12); }}
        .rating-cell.great .score {{ color: var(--great); }}

        .rating-cell.good {{ background: rgba(34,197,94,0.08); }}
        .rating-cell.good .score {{ color: var(--good); }}

        .rating-cell.ok {{ background: rgba(245,158,11,0.08); }}
        .rating-cell.ok .score {{ color: var(--ok); }}

        .rating-cell.poor {{ background: rgba(239,68,68,0.08); }}
        .rating-cell.poor .score {{ color: var(--poor); }}

        .legend {{
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            margin: 12px 0 25px;
            font-size: 0.8rem;
            opacity: 0.7;
        }}

        .legend-item {{ display: flex; align-items: center; gap: 4px; }}

        .webcams {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 10px;
            margin: 15px 0;
        }}

        .webcam-link {{
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 15px 10px;
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            text-decoration: none;
            color: white;
            transition: background 0.2s;
        }}

        .webcam-link:hover {{ background: rgba(255,255,255,0.1); }}
        .webcam-icon {{ font-size: 1.5rem; margin-bottom: 5px; }}
        .webcam-name {{ font-size: 0.85rem; }}

        footer {{
            text-align: center;
            padding: 30px;
            font-size: 0.8rem;
            opacity: 0.4;
        }}

        footer a {{ color: var(--seafoam); }}

        @media (max-width: 600px) {{
            .logo {{ font-size: 1.8rem; }}
            .top-picks {{ grid-template-columns: 1fr; }}
            table {{ font-size: 0.75rem; }}
            th, td {{ padding: 8px 4px; }}
            .rating-cell {{ min-width: 50px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">\U0001f30a Snorkel Alert v6</div>
            <div class="tagline">Perth Beach Forecast — Ratings from 0-10</div>
            <div class="updated">Updated {updated} AWST</div>
        </header>

        <div class="summary-card">
            {forecast.get("summary", "")}
            <div class="water-temp">\U0001f321\ufe0f Water temperature: {forecast.get("water_temp_c", "?")}°C</div>
        </div>

        {error_html}

        <div class="top-picks">
            <div class="pick-card snorkel">
                <div class="pick-label">\U0001f93f Best Snorkelling</div>
                <div class="pick-spot">{best_snorkel.get("spot", "N/A")}</div>
                <div class="pick-score">{snorkel_score_display}</div>
                <div class="pick-detail">{snorkel_detail}</div>
            </div>
            <div class="pick-card sunbathing">
                <div class="pick-label">\u2600\ufe0f Best Sunbathing</div>
                <div class="pick-spot">{best_sunbathing.get("spot", "N/A")}</div>
                <div class="pick-score">{beach_score_display}</div>
                <div class="pick-detail">{best_sunbathing_detail}</div>
            </div>
            <div class="pick-card gem">
                <div class="pick-label">\U0001f48e Hidden Gem</div>
                <div class="pick-spot">{hidden_gem.get("spot", "N/A")}</div>
                <div class="pick-detail">{gem_detail}</div>
            </div>
        </div>

        <div class="section-title">\U0001f93f Snorkelling Conditions</div>
        <div class="legend">
            <span class="legend-item">9-10 🤿 Perfect</span>
            <span class="legend-item">7.5-9 ⭐ Great</span>
            <span class="legend-item">6-7.5 \U0001f7e2 Good</span>
            <span class="legend-item">4.5-6 \U0001f7e1 OK</span>
            <span class="legend-item">&lt;4.5 \U0001f534 Poor</span>
            <span class="legend-item">\u2605 Weekend</span>
        </div>
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th></th>
                        {header_cells}
                    </tr>
                </thead>
                <tbody>
                    {snorkel_rows}
                </tbody>
            </table>
        </div>

        <div class="section-title">\u2600\ufe0f Sunbathing Conditions</div>
        <div class="legend">
            <span class="legend-item">Format: 🌡️ max/min • 🌬️ wind(km/h)</span>
        </div>
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th></th>
                        {header_cells}
                    </tr>
                </thead>
                <tbody>
                    {sunbathing_rows}
                </tbody>
            </table>
        </div>

        <div class="section-title">\U0001f4f9 Live Webcams</div>
        <div class="webcams">
            {"".join(f'<a href="{w["url"]}" target="_blank" class="webcam-link"><span class="webcam-icon">{w["icon"]}</span><span class="webcam-name">{w["name"]}</span></a>' for w in WEBCAMS)}
        </div>

        <footer>
            Built with \U0001f93f by Snorkel Alert v{VERSION}<br>
            Ratings calibrated from real experience at Mettams Pool
        </footer>
    </div>
</body>
</html>"""

    return html
