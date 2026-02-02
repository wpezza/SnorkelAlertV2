Fixtures for regression checks.

Workflow:
1) Record a raw API snapshot:
   python tools/record_fixture.py --output fixtures/raw_latest.json

2) Generate a baseline forecast from that snapshot:
   python tools/compare_forecast.py --fixture fixtures/raw_latest.json --baseline fixtures/forecast_baseline.json --write

3) After changes, compare against the baseline:
   python tools/compare_forecast.py --fixture fixtures/raw_latest.json --baseline fixtures/forecast_baseline.json
