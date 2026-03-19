#!/usr/bin/env python3

from __future__ import annotations

import csv
from pathlib import Path


WMO_CODES = {
    "0": "Clear sky",
    "1": "Mainly clear",
    "2": "Partly cloudy",
    "3": "Overcast",
    "45": "Fog",
    "48": "Depositing rime fog",
    "51": "Light drizzle",
    "53": "Moderate drizzle",
    "55": "Dense drizzle",
    "56": "Light freezing drizzle",
    "57": "Dense freezing drizzle",
    "61": "Slight rain",
    "63": "Moderate rain",
    "65": "Heavy rain",
    "66": "Light freezing rain",
    "67": "Heavy freezing rain",
    "71": "Slight snow fall",
    "73": "Moderate snow fall",
    "75": "Heavy snow fall",
    "77": "Snow grains",
    "80": "Slight rain showers",
    "81": "Moderate rain showers",
    "82": "Violent rain showers",
    "85": "Slight snow showers",
    "86": "Heavy snow showers",
    "95": "Thunderstorm",
    "96": "Thunderstorm with slight hail",
    "99": "Thunderstorm with heavy hail",
}

TEMPERATURE_COLUMNS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "apparent_temperature_max",
    "apparent_temperature_min",
]

PRECIP_COLUMNS = [
    "precipitation_sum",
    "rain_sum",
]

SNOW_COLUMNS = [
    "snowfall_sum",
]

WIND_COLUMNS = [
    "windspeed_10m_max",
    "windgusts_10m_max",
]

BASEBALL_WIND_LABELS = [
    "In from Left Center Field",
    "In from Center",
    "In from Right-Center Field",
    "In from Right Field",
    "In from Right Field",
    "Cross from Right Field Corner",
    "Out to Left Field",
    "Out to Left Field",
    "Out to Left Center Field",
    "Out to Dead Center Field",
    "Out to Right Center Field",
    "Out to Right Field",
    "Out to Right Field",
    "Cross from Left Field Corner",
    "In from Left Field",
    "In from Left Field",
]


def celsius_to_fahrenheit(value: str) -> str:
    return f"{(float(value) * 9 / 5) + 32:.1f}" if value else ""


def mm_to_inches(value: str) -> str:
    return f"{float(value) / 25.4:.3f}" if value else ""


def cm_to_inches(value: str) -> str:
    return f"{float(value) / 2.54:.3f}" if value else ""


def kmh_to_mph(value: str) -> str:
    return f"{float(value) * 0.621371:.1f}" if value else ""


def degrees_to_cardinal(value: str) -> str:
    if not value:
        return ""

    degrees = float(value) % 360
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    index = int((degrees + 22.5) // 45) % len(directions)
    return directions[index]


def degrees_to_baseball_direction(value: str) -> str:
    if not value:
        return ""

    degrees = float(value) % 360
    index = int((degrees + 11.25) // 22.5) % len(BASEBALL_WIND_LABELS)
    return BASEBALL_WIND_LABELS[index]


def build_output_header(source_header: list[str]) -> list[str]:
    header: list[str] = []

    for column in source_header:
        header.append(column)

        if column == "weather_code":
            header.append("weather_code_description")
        elif column in TEMPERATURE_COLUMNS:
            header.append(f"{column}_fahrenheit")
        elif column in PRECIP_COLUMNS or column in SNOW_COLUMNS:
            header.append(f"{column}_inches")
        elif column in WIND_COLUMNS:
            header.append(f"{column}_mph")
        elif column == "wind_direction_10m_dominant":
            header.append("wind_direction_10m_dominant_cardinal")
            header.append("wind_direction_10m_dominant_baseball")

    return header


def build_output_row(row: dict[str, str], source_header: list[str]) -> list[str]:
    output: list[str] = []

    for column in source_header:
        value = row[column]
        output.append(value)

        if column == "weather_code":
            output.append(WMO_CODES.get(value, "Unknown"))
        elif column in TEMPERATURE_COLUMNS:
            output.append(celsius_to_fahrenheit(value))
        elif column in PRECIP_COLUMNS:
            output.append(mm_to_inches(value))
        elif column in SNOW_COLUMNS:
            output.append(cm_to_inches(value))
        elif column in WIND_COLUMNS:
            output.append(kmh_to_mph(value))
        elif column == "wind_direction_10m_dominant":
            output.append(degrees_to_cardinal(value))
            output.append(degrees_to_baseball_direction(value))

    return output


def main() -> None:
    source = Path("gl2020_25/GameDayWeather With Wind Direction.csv")
    destination = Path("gl2020_25/GameDayWeather Transformed.csv")

    with source.open(newline="", encoding="utf-8") as infile:
        reader = csv.DictReader(infile)
        source_header = reader.fieldnames
        if not source_header:
            raise SystemExit("Source CSV has no header")

        output_header = build_output_header(source_header)
        rows = [build_output_row(row, source_header) for row in reader]

    with destination.open("w", newline="", encoding="utf-8") as outfile:
        writer = csv.writer(outfile)
        writer.writerow(output_header)
        writer.writerows(rows)

    print(destination)
    print(len(rows))


if __name__ == "__main__":
    main()
