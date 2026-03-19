#!/usr/bin/env python3

from __future__ import annotations

import csv
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen


LATITUDE = 41.9484
LONGITUDE = -87.6553
TIMEZONE = "America/Chicago"
DAILY_FIELDS = [
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "apparent_temperature_max",
    "apparent_temperature_min",
    "precipitation_sum",
    "rain_sum",
    "snowfall_sum",
    "precipitation_hours",
    "windspeed_10m_max",
    "windgusts_10m_max",
]


def load_dates(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8") as infile:
        reader = csv.DictReader(infile)
        return [row["date"] for row in reader if row.get("date")]


def to_iso(date_value: str) -> str:
    year, month, day = date_value.split("/")
    return f"{year}-{month}-{day}"


def fetch_weather(start_date: str, end_date: str) -> dict:
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "start_date": start_date,
        "end_date": end_date,
        "daily": ",".join(DAILY_FIELDS),
        "timezone": TIMEZONE,
    }
    url = f"https://archive-api.open-meteo.com/v1/archive?{urlencode(params)}"
    with urlopen(url) as response:
        return json.load(response)


def build_daily_lookup(payload: dict) -> dict[str, dict[str, object]]:
    daily = payload["daily"]
    times = daily["time"]
    lookup: dict[str, dict[str, object]] = {}

    for index, iso_date in enumerate(times):
        lookup[iso_date] = {field: daily[field][index] for field in DAILY_FIELDS}

    return lookup


def main() -> None:
    source = Path("gl2020_25/Wrigley Game Dates.csv")
    destination = Path("gl2020_25/GameDayWeather.csv")

    dates = load_dates(source)
    if not dates:
        raise SystemExit("No dates found in source CSV")

    iso_dates = [to_iso(date_value) for date_value in dates]
    payload = fetch_weather(min(iso_dates), max(iso_dates))
    weather_by_date = build_daily_lookup(payload)

    fieldnames = ["date", *DAILY_FIELDS]

    with destination.open("w", newline="", encoding="utf-8") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        for original_date, iso_date in zip(dates, iso_dates):
            row = {"date": original_date}
            row.update(weather_by_date[iso_date])
            writer.writerow(row)

    print(destination)
    print(len(dates))


if __name__ == "__main__":
    main()
