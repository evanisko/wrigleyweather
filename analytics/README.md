# Analytics Layer

This folder contains a lightweight placeholder analytics layer for the static site.
It reads from the local DuckDB database, calculates a few generic metrics, and writes
frontend-ready JSON for the UI to consume.

## Run it

```bash
python3 analytics/generate_analytics.py
python3 analytics/generate_weather_averages.py
python3 analytics/generate_baseball_averages.py
python3 analytics/generate_forecast_similarity.py
```

## Output

The generators write analytics JSON to:

- `data/analytics.json`
- `data/weather_averages.json`
- `data/ball_averages.json`
- `data/today_forecast.json`
- `data/forecast_similarity.json`

## What it does

- connects to `.local.nosync/analytics.duckdb`
- inspects available tables and columns before choosing a source table
- calculates simple placeholder metrics such as record count, date range, average temperature,
  average wind speed, precipitation day count, and basic time-series arrays
- falls back to `null` values or empty arrays if expected columns are not present

## Extend it later

Add new helper functions in `generate_analytics.py` and append new cards or series to the
payload once you know which additional DuckDB columns should power them.

`generate_weather_averages.py` is a dedicated weather summary export. It reads
`raw.gamedayweather` and writes all-days and month-by-month averages for frontend use.

`generate_baseball_averages.py` reads `raw.gamestats`, writes baseball averages into
`main.ball_averages` and `main.ball_averages_monthly`, and exports a frontend-ready
JSON payload.

The DuckDB file now lives in `.local.nosync/analytics.duckdb` to avoid macOS
`fileproviderd` locking issues in synced `Documents` folders.

`generate_forecast_similarity.py` reads `data/today_forecast.json`, compares today's
forecast against the joined historical weather/baseball data, and exports matched-game
averages for frontend use.
