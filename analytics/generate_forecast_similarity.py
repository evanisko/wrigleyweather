from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / ".local.nosync" / "analytics.duckdb"
FORECAST_PATH = PROJECT_ROOT / "data" / "today_forecast.json"
OUTPUT_PATH = PROJECT_ROOT / "data" / "forecast_similarity.json"
TEMP_THRESHOLD = 5
WIND_SPEED_THRESHOLD = 5
WIND_DIRECTION_THRESHOLD = 22


def get_connection() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DATABASE_PATH), read_only=True)


def round_or_none(value: Any) -> float | None:
    return round(float(value), 2) if value is not None else None


def load_forecast() -> dict[str, Any]:
    payload = json.loads(FORECAST_PATH.read_text(encoding="utf-8"))
    today_forecast = payload.get("todayForecast", {})

    if (
        today_forecast.get("highTemperatureF") is None
        or today_forecast.get("windSpeedMph") is None
        or today_forecast.get("windDirectionDegrees") is None
    ):
        raise RuntimeError("today_forecast.json is missing required forecast inputs")

    return payload


def fetch_similarity_metrics(
    conn: duckdb.DuckDBPyConnection,
    target_temp: int,
    target_wind_speed: int,
    target_wind_direction: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows = conn.execute(
        """
        WITH matched_games AS (
            SELECT
                gs.date,
                gw.temperature_2m_mean_fahrenheit AS historical_temperature_f,
                gw.windspeed_10m_max_mph AS historical_wind_speed_mph,
                gw.wind_direction_10m_dominant AS historical_wind_direction_degrees,
                gs.home_score + gs.visiting_score AS total_runs,
                gs.home_home_runs + gs.visiting_home_runs AS total_home_runs,
                gs.game_time_minutes,
                ABS(gw.temperature_2m_mean_fahrenheit - ?) AS temperature_delta,
                ABS(gw.windspeed_10m_max_mph - ?) AS wind_speed_delta,
                LEAST(
                    ABS(gw.wind_direction_10m_dominant - ?),
                    360 - ABS(gw.wind_direction_10m_dominant - ?)
                ) AS wind_direction_delta
            FROM raw.gamestats AS gs
            INNER JOIN raw.gamedayweather AS gw
                ON gs.date = gw.date
            WHERE ABS(gw.temperature_2m_mean_fahrenheit - ?) <= ?
              AND ABS(gw.windspeed_10m_max_mph - ?) <= ?
              AND LEAST(
                    ABS(gw.wind_direction_10m_dominant - ?),
                    360 - ABS(gw.wind_direction_10m_dominant - ?)
                  ) <= ?
        )
        SELECT
            COUNT(*) AS matched_game_count,
            AVG(total_runs) AS avg_runs,
            AVG(total_home_runs) AS avg_home_runs,
            AVG(game_time_minutes) AS avg_game_time_minutes
        FROM matched_games
        """,
        [
            target_temp,
            target_wind_speed,
            target_wind_direction,
            target_wind_direction,
            target_temp,
            TEMP_THRESHOLD,
            target_wind_speed,
            WIND_SPEED_THRESHOLD,
            target_wind_direction,
            target_wind_direction,
            WIND_DIRECTION_THRESHOLD,
        ],
    ).fetchone()

    sample_rows = conn.execute(
        """
        SELECT
            gs.date,
            gw.temperature_2m_mean_fahrenheit AS historical_temperature_f,
            gw.windspeed_10m_max_mph AS historical_wind_speed_mph,
            gw.wind_direction_10m_dominant AS historical_wind_direction_degrees,
            gs.home_score + gs.visiting_score AS total_runs,
            gs.home_home_runs + gs.visiting_home_runs AS total_home_runs,
            gs.game_time_minutes,
            ABS(gw.temperature_2m_mean_fahrenheit - ?) AS temperature_delta,
            ABS(gw.windspeed_10m_max_mph - ?) AS wind_speed_delta,
            LEAST(
                ABS(gw.wind_direction_10m_dominant - ?),
                360 - ABS(gw.wind_direction_10m_dominant - ?)
            ) AS wind_direction_delta
        FROM raw.gamestats AS gs
        INNER JOIN raw.gamedayweather AS gw
            ON gs.date = gw.date
        WHERE ABS(gw.temperature_2m_mean_fahrenheit - ?) <= ?
          AND ABS(gw.windspeed_10m_max_mph - ?) <= ?
          AND LEAST(
                ABS(gw.wind_direction_10m_dominant - ?),
                360 - ABS(gw.wind_direction_10m_dominant - ?)
              ) <= ?
        ORDER BY gs.date DESC
        LIMIT 10
        """,
        [
            target_temp,
            target_wind_speed,
            target_wind_direction,
            target_wind_direction,
            target_temp,
            TEMP_THRESHOLD,
            target_wind_speed,
            WIND_SPEED_THRESHOLD,
            target_wind_direction,
            target_wind_direction,
            WIND_DIRECTION_THRESHOLD,
        ],
    ).fetchall()

    summary = {
        "matched_game_count": int(rows[0]),
        "averages": {
            "runs": round_or_none(rows[1]),
            "home_runs": round_or_none(rows[2]),
            "game_time_minutes": round_or_none(rows[3]),
        },
    }

    matches = [
        {
            "date": row[0].isoformat(),
            "historical_temperature_f": round_or_none(row[1]),
            "historical_wind_speed_mph": round_or_none(row[2]),
            "historical_wind_direction_degrees": int(row[3]),
            "total_runs": int(row[4]),
            "total_home_runs": int(row[5]),
            "game_time_minutes": int(row[6]),
            "temperature_delta": round_or_none(row[7]),
            "wind_speed_delta": round_or_none(row[8]),
            "wind_direction_delta": round_or_none(row[9]),
        }
        for row in sample_rows
    ]

    return summary, matches


def build_payload() -> dict[str, Any]:
    forecast_payload = load_forecast()
    today_forecast = forecast_payload["todayForecast"]

    conn = get_connection()
    try:
        summary, matches = fetch_similarity_metrics(
            conn,
            today_forecast["highTemperatureF"],
            today_forecast["windSpeedMph"],
            today_forecast["windDirectionDegrees"],
        )
    finally:
        conn.close()

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "forecast_path": str(FORECAST_PATH.relative_to(PROJECT_ROOT)),
            "database_path": str(DATABASE_PATH.relative_to(PROJECT_ROOT)),
            "joined_tables": ["raw.gamestats", "raw.gamedayweather"],
        },
        "forecast_input": today_forecast,
        "criteria": {
            "temperature_f": {"target": today_forecast["highTemperatureF"], "tolerance": TEMP_THRESHOLD},
            "wind_speed_mph": {
                "target": today_forecast["windSpeedMph"],
                "tolerance": WIND_SPEED_THRESHOLD,
            },
            "wind_direction_degrees": {
                "target": today_forecast["windDirectionDegrees"],
                "tolerance": WIND_DIRECTION_THRESHOLD,
            },
        },
        "results": summary,
        "matches": matches,
    }


def write_output(payload: dict[str, Any]) -> Path:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return OUTPUT_PATH


def main() -> None:
    payload = build_payload()
    output_path = write_output(payload)
    print(f"Generated forecast similarity JSON at {output_path}")


if __name__ == "__main__":
    main()
