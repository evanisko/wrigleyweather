from __future__ import annotations

from weather_pipeline import (
    build_today_forecast_document,
    build_weather_document,
    write_today_forecast_json,
    write_weather_json,
)


def main() -> None:
    document = build_weather_document()
    forecast_document = build_today_forecast_document()
    weather_output_path = write_weather_json(document)
    forecast_output_path = write_today_forecast_json(forecast_document)
    print(f"Wrote {weather_output_path}")
    print(f"Wrote {forecast_output_path}")


if __name__ == "__main__":
    main()
