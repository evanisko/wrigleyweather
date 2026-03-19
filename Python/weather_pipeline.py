from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


WRIGLEY_LAT = 41.9484
WRIGLEY_LON = -87.6553
USER_AGENT = "WrigleyWeather/1.0 (static-site generator)"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "weather.json"


def fetch_json(url: str) -> dict:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/geo+json, application/json",
        },
    )
    with urlopen(request, timeout=15) as response:
        return json.load(response)


def celsius_to_fahrenheit(value: float | None) -> int | None:
    if value is None:
        return None
    return round((value * 9 / 5) + 32)


def kilometers_to_miles(value: float | None) -> int | None:
    if value is None:
        return None
    return round(value * 0.621371)


def direction_to_cardinal(degrees: float | None) -> str:
    if degrees is None:
        return "Variable"
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    index = round(degrees / 45) % len(directions)
    return directions[index]


def safe_round(value: float | None, fallback: int | None = None) -> int | None:
    if value is None:
        return fallback
    return round(value)


def compute_comfort(temp_f: int | None, humidity: int | None, rain_chance: int | None) -> str:
    if temp_f is None or humidity is None or rain_chance is None:
        return "Fair"

    score = 100
    if temp_f < 45 or temp_f > 90:
        score -= 30
    elif temp_f < 55 or temp_f > 84:
        score -= 15

    if humidity > 80:
        score -= 20
    elif humidity > 65:
        score -= 10

    if rain_chance > 60:
        score -= 25
    elif rain_chance > 30:
        score -= 10

    if score >= 85:
        return "Excellent"
    if score >= 65:
        return "Good"
    if score >= 45:
        return "Fair"
    return "Rough"


def build_forecast(periods: list[dict]) -> list[dict]:
    forecast_days: list[dict] = []

    for index, period in enumerate(periods):
        if not period.get("isDaytime"):
            continue

        low_temp = period.get("temperature")
        if index + 1 < len(periods) and not periods[index + 1].get("isDaytime"):
            low_temp = periods[index + 1].get("temperature", low_temp)

        start_time = period.get("startTime", "")
        try:
            label = datetime.fromisoformat(start_time).strftime("%a")
        except ValueError:
            label = period.get("name", "Day")

        forecast_days.append(
            {
                "date": start_time,
                "label": label,
                "summary": period.get("shortForecast", "Forecast unavailable"),
                "highF": period.get("temperature"),
                "lowF": low_temp,
            }
        )

        if len(forecast_days) == 3:
            break

    return forecast_days


def build_weather_document() -> dict:
    points = fetch_json(f"https://api.weather.gov/points/{WRIGLEY_LAT},{WRIGLEY_LON}")
    point_props = points["properties"]

    stations = fetch_json(point_props["observationStations"])
    station_url = stations["observationStations"][0]
    station_id = station_url.rstrip("/").split("/")[-1]

    observation = fetch_json(f"{station_url}/observations/latest")
    forecast = fetch_json(point_props["forecast"])
    forecast_hourly = fetch_json(point_props["forecastHourly"])

    observation_props = observation["properties"]
    hourly_periods = forecast_hourly["properties"]["periods"]
    next_hour = hourly_periods[0] if hourly_periods else {}

    temperature_f = celsius_to_fahrenheit(observation_props["temperature"]["value"])
    heat_index_f = celsius_to_fahrenheit(observation_props["heatIndex"]["value"])
    wind_chill_f = celsius_to_fahrenheit(observation_props["windChill"]["value"])
    humidity_percent = safe_round(observation_props["relativeHumidity"]["value"])
    wind_speed_mph = kilometers_to_miles(observation_props["windSpeed"]["value"])
    wind_direction_cardinal = direction_to_cardinal(observation_props["windDirection"]["value"])
    rain_chance_percent = safe_round(
        next_hour.get("probabilityOfPrecipitation", {}).get("value"),
        0,
    ) or 0
    feels_like_f = heat_index_f or wind_chill_f or temperature_f

    if heat_index_f is None:
        heat_index_f = feels_like_f
    if wind_chill_f is None:
        wind_chill_f = feels_like_f

    return {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "location": {
            "name": "Wrigley Field",
            "city": "Chicago, IL",
            "timezone": "America/Chicago",
            "latitude": WRIGLEY_LAT,
            "longitude": WRIGLEY_LON,
        },
        "source": {
            "name": "National Weather Service",
            "providerUrl": "https://api.weather.gov",
            "observationStationId": station_id,
        },
        "current": {
            "updatedAt": observation_props.get("timestamp"),
            "summary": observation_props.get("textDescription") or next_hour.get("shortForecast"),
            "temperatureF": temperature_f,
            "feelsLikeF": feels_like_f,
            "heatIndexF": heat_index_f,
            "windChillF": wind_chill_f,
            "humidityPercent": humidity_percent,
            "rainChancePercent": rain_chance_percent,
            "comfort": compute_comfort(temperature_f, humidity_percent, rain_chance_percent),
            "wind": {
                "speedMph": wind_speed_mph,
                "directionCardinal": wind_direction_cardinal,
                "label": (
                    f"{wind_speed_mph} mph {wind_direction_cardinal}"
                    if wind_speed_mph is not None
                    else f"Calm {wind_direction_cardinal}"
                ),
            },
        },
        "forecast": build_forecast(forecast["properties"]["periods"]),
    }


def write_weather_json(document: dict, output_path: Path = DATA_PATH) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=output_path.parent,
        prefix=".weather.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        json.dump(document, handle, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        temp_path = Path(handle.name)

    os.replace(temp_path, output_path)
    return output_path
