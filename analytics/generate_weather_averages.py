from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / ".local.nosync" / "analytics.duckdb"
OUTPUT_PATH = PROJECT_ROOT / "data" / "weather_averages.json"
SOURCE_SCHEMA = "raw"
SOURCE_TABLE = "gamedayweather"

DATE_COLUMN = "date"
TEMPERATURE_COLUMN = "temperature_2m_mean_fahrenheit"
WIND_SPEED_COLUMN = "windspeed_10m_max_mph"
HUMIDITY_COLUMN_CANDIDATES = (
    "relative_humidity_2m_mean",
    "relative_humidity_2m_avg",
    "relative_humidity_mean",
    "relative_humidity",
    "humidity",
)
MONTH_NAMES = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}


def get_connection() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DATABASE_PATH), read_only=True)


def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def qualified_table() -> str:
    return f"{quote_identifier(SOURCE_SCHEMA)}.{quote_identifier(SOURCE_TABLE)}"


def get_column_names(conn: duckdb.DuckDBPyConnection) -> list[str]:
    rows = conn.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = ? AND table_name = ?
        ORDER BY ordinal_position
        """,
        [SOURCE_SCHEMA, SOURCE_TABLE],
    ).fetchall()
    return [row[0] for row in rows]


def find_optional_column(
    available_columns: list[str], candidates: tuple[str, ...]
) -> str | None:
    lowered_lookup = {column.lower(): column for column in available_columns}
    for candidate in candidates:
        if candidate in lowered_lookup:
            return lowered_lookup[candidate]
    return None


def round_or_none(value: Any) -> float | None:
    return round(float(value), 2) if value is not None else None


def fetch_overall_averages(
    conn: duckdb.DuckDBPyConnection, humidity_column: str | None
) -> dict[str, float | None]:
    humidity_sql = (
        f"AVG({quote_identifier(humidity_column)}) AS avg_humidity"
        if humidity_column
        else "NULL AS avg_humidity"
    )
    row = conn.execute(
        f"""
        SELECT
            AVG({quote_identifier(TEMPERATURE_COLUMN)}) AS avg_temperature,
            AVG({quote_identifier(WIND_SPEED_COLUMN)}) AS avg_wind_speed,
            {humidity_sql}
        FROM {qualified_table()}
        """
    ).fetchone()

    return {
        "temperature": round_or_none(row[0]),
        "wind_speed": round_or_none(row[1]),
        "humidity": round_or_none(row[2]),
    }


def fetch_monthly_averages(
    conn: duckdb.DuckDBPyConnection, humidity_column: str | None
) -> list[dict[str, Any]]:
    humidity_sql = (
        f"AVG({quote_identifier(humidity_column)}) AS avg_humidity"
        if humidity_column
        else "NULL AS avg_humidity"
    )
    rows = conn.execute(
        f"""
        SELECT
            EXTRACT(MONTH FROM {quote_identifier(DATE_COLUMN)}) AS month_number,
            AVG({quote_identifier(TEMPERATURE_COLUMN)}) AS avg_temperature,
            AVG({quote_identifier(WIND_SPEED_COLUMN)}) AS avg_wind_speed,
            {humidity_sql},
            COUNT(*) AS record_count
        FROM {qualified_table()}
        WHERE {quote_identifier(DATE_COLUMN)} IS NOT NULL
        GROUP BY 1
        ORDER BY 1
        """
    ).fetchall()

    return [
        {
            "month_number": int(month_number),
            "month": MONTH_NAMES[int(month_number)],
            "averages": {
                "temperature": round_or_none(avg_temperature),
                "wind_speed": round_or_none(avg_wind_speed),
                "humidity": round_or_none(avg_humidity),
            },
            "record_count": int(record_count),
        }
        for month_number, avg_temperature, avg_wind_speed, avg_humidity, record_count in rows
    ]


def build_payload() -> dict[str, Any]:
    conn = get_connection()
    try:
        available_columns = get_column_names(conn)
        humidity_column = find_optional_column(available_columns, HUMIDITY_COLUMN_CANDIDATES)
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": {
                "database_path": DATABASE_PATH.name,
                "table": f"{SOURCE_SCHEMA}.{SOURCE_TABLE}",
            },
            "metrics": {
                "all_days": fetch_overall_averages(conn, humidity_column),
                "by_month": fetch_monthly_averages(conn, humidity_column),
            },
            "metadata": {
                "columns": {
                    "date": DATE_COLUMN,
                    "temperature": TEMPERATURE_COLUMN,
                    "wind_speed": WIND_SPEED_COLUMN,
                    "humidity": humidity_column,
                },
                "notes": [
                    "Monthly averages are grouped across all years in the weather table.",
                    "Humidity is null when no humidity column exists in the local DuckDB file.",
                ],
            },
        }
    finally:
        conn.close()

    return payload


def write_output(payload: dict[str, Any]) -> Path:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    return OUTPUT_PATH


def main() -> None:
    payload = build_payload()
    output_path = write_output(payload)
    print(f"Generated weather averages JSON at {output_path}")


if __name__ == "__main__":
    main()
