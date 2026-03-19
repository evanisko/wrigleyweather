# Analytics Layer

This folder contains a lightweight placeholder analytics layer for the static site.
It reads from the local DuckDB database, calculates a few generic metrics, and writes
frontend-ready JSON for the UI to consume.

## Run it

```bash
python3 analytics/generate_analytics.py
```

## Output

The generator writes analytics JSON to `data/analytics.json`.

## What it does

- connects to `analytics.duckdb`
- inspects available tables and columns before choosing a source table
- calculates simple placeholder metrics such as record count, date range, average temperature,
  average wind speed, precipitation day count, and basic time-series arrays
- falls back to `null` values or empty arrays if expected columns are not present

## Extend it later

Add new helper functions in `generate_analytics.py` and append new cards or series to the
payload once you know which additional DuckDB columns should power them.
