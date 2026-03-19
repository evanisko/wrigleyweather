from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / ".local.nosync" / "analytics.duckdb"
OUTPUT_PATH = PROJECT_ROOT / "data" / "analytics.json"
DATE_COLUMN_CANDIDATES = (
    "date",
    "game_date",
    "observation_date",
    "record_date",
    "timestamp",
    "datetime",
)
TEMPERATURE_COLUMN_CANDIDATES = (
    "temperature_2m_mean_fahrenheit",
    "temperature_2m_max_fahrenheit",
    "temperature_2m_mean",
    "avg_temp",
    "temperature",
    "temp",
)
WIND_COLUMN_CANDIDATES = (
    "windspeed_10m_max_mph",
    "windspeed_10m_max",
    "avg_wind_speed",
    "wind_speed",
    "windspeed",
)
PRECIPITATION_COLUMN_CANDIDATES = (
    "precipitation_sum_inches",
    "precipitation_sum",
    "precipitation",
    "precip",
    "rain_sum_inches",
    "rain_sum",
)
SERIES_LIMIT = 120


def get_connection() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DATABASE_PATH), read_only=True)


def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def list_tables(conn: duckdb.DuckDBPyConnection) -> list[dict[str, str]]:
    rows = conn.execute(
        """
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
        ORDER BY
            CASE
                WHEN table_schema = 'raw' THEN 0
                WHEN table_schema = 'analytics' THEN 1
                WHEN table_schema = 'main' THEN 2
                ELSE 3
            END,
            table_name
        """
    ).fetchall()
    return [{"schema": schema, "name": table} for schema, table in rows]


def get_table_columns(
    conn: duckdb.DuckDBPyConnection, schema_name: str, table_name: str
) -> list[dict[str, str]]:
    rows = conn.execute(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = ? AND table_name = ?
        ORDER BY ordinal_position
        """,
        [schema_name, table_name],
    ).fetchall()
    return [{"name": name, "type": data_type} for name, data_type in rows]


def find_column(columns: list[dict[str, str]], candidates: tuple[str, ...]) -> str | None:
    names = [column["name"] for column in columns]
    lowered_lookup = {name.lower(): name for name in names}

    for candidate in candidates:
        if candidate in lowered_lookup:
            return lowered_lookup[candidate]

    for candidate in candidates:
        for name in names:
            if candidate in name.lower():
                return name

    return None


def detect_source_table(conn: duckdb.DuckDBPyConnection) -> tuple[dict[str, Any], dict[str, str]]:
    best_match: dict[str, Any] | None = None

    for table in list_tables(conn):
        columns = get_table_columns(conn, table["schema"], table["name"])
        row_count = conn.execute(
            f"SELECT COUNT(*) FROM {quote_identifier(table['schema'])}.{quote_identifier(table['name'])}"
        ).fetchone()[0]

        detected_columns = {
            "date": find_column(columns, DATE_COLUMN_CANDIDATES),
            "temperature": find_column(columns, TEMPERATURE_COLUMN_CANDIDATES),
            "wind_speed": find_column(columns, WIND_COLUMN_CANDIDATES),
            "precipitation": find_column(columns, PRECIPITATION_COLUMN_CANDIDATES),
        }
        score = sum(1 for value in detected_columns.values() if value) * 10 + min(row_count, 9)

        candidate = {
            "schema": table["schema"],
            "table": table["name"],
            "row_count": row_count,
            "columns": columns,
            "score": score,
        }
        if best_match is None or candidate["score"] > best_match["score"]:
            best_match = candidate
            best_match["detected_columns"] = detected_columns

    if best_match is None:
        raise RuntimeError(f"No user tables found in {DATABASE_PATH}")

    return best_match, best_match["detected_columns"]


def fetch_summary(
    conn: duckdb.DuckDBPyConnection,
    schema_name: str,
    table_name: str,
    date_column: str | None,
) -> dict[str, Any]:
    qualified_table = f"{quote_identifier(schema_name)}.{quote_identifier(table_name)}"
    if date_column:
        row = conn.execute(
            f"""
            SELECT
                COUNT(*) AS record_count,
                MIN({quote_identifier(date_column)}) AS date_min,
                MAX({quote_identifier(date_column)}) AS date_max
            FROM {qualified_table}
            """
        ).fetchone()
        return {
            "record_count": row[0],
            "date_min": row[1].isoformat() if row[1] else None,
            "date_max": row[2].isoformat() if row[2] else None,
        }

    row_count = conn.execute(f"SELECT COUNT(*) FROM {qualified_table}").fetchone()[0]
    return {
        "record_count": row_count,
        "date_min": None,
        "date_max": None,
    }


def fetch_average_metric(
    conn: duckdb.DuckDBPyConnection,
    schema_name: str,
    table_name: str,
    column_name: str | None,
) -> float | None:
    if not column_name:
        return None

    qualified_table = f"{quote_identifier(schema_name)}.{quote_identifier(table_name)}"
    value = conn.execute(
        f"""
        SELECT AVG({quote_identifier(column_name)})
        FROM {qualified_table}
        WHERE {quote_identifier(column_name)} IS NOT NULL
        """
    ).fetchone()[0]
    return round(float(value), 2) if value is not None else None


def fetch_precipitation_days(
    conn: duckdb.DuckDBPyConnection,
    schema_name: str,
    table_name: str,
    precipitation_column: str | None,
) -> int | None:
    if not precipitation_column:
        return None

    qualified_table = f"{quote_identifier(schema_name)}.{quote_identifier(table_name)}"
    value = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM {qualified_table}
        WHERE COALESCE({quote_identifier(precipitation_column)}, 0) > 0
        """
    ).fetchone()[0]
    return int(value)


def build_series(
    conn: duckdb.DuckDBPyConnection,
    schema_name: str,
    table_name: str,
    date_column: str | None,
    value_column: str | None,
) -> list[dict[str, Any]]:
    if not date_column or not value_column:
        return []

    qualified_table = f"{quote_identifier(schema_name)}.{quote_identifier(table_name)}"
    rows = conn.execute(
        f"""
        SELECT
            {quote_identifier(date_column)} AS point_date,
            AVG({quote_identifier(value_column)}) AS point_value
        FROM {qualified_table}
        WHERE {quote_identifier(date_column)} IS NOT NULL
          AND {quote_identifier(value_column)} IS NOT NULL
        GROUP BY 1
        ORDER BY 1
        LIMIT {SERIES_LIMIT}
        """
    ).fetchall()

    return [
        {
            "date": point_date.isoformat() if hasattr(point_date, "isoformat") else str(point_date),
            "value": round(float(point_value), 2) if point_value is not None else None,
        }
        for point_date, point_value in rows
    ]


def build_payload(
    conn: duckdb.DuckDBPyConnection,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    source_table, detected_columns = detect_source_table(conn)
    schema_name = source_table["schema"]
    table_name = source_table["table"]

    summary = fetch_summary(conn, schema_name, table_name, detected_columns["date"])
    avg_temp = fetch_average_metric(conn, schema_name, table_name, detected_columns["temperature"])
    avg_wind = fetch_average_metric(conn, schema_name, table_name, detected_columns["wind_speed"])
    precip_days = fetch_precipitation_days(
        conn, schema_name, table_name, detected_columns["precipitation"]
    )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "cards": [
            {
                "id": "avg_temp",
                "title": "Average Temperature",
                "value": avg_temp,
                "unit": "F",
                "description": "Placeholder average temperature metric",
            },
            {
                "id": "avg_wind_speed",
                "title": "Average Wind Speed",
                "value": avg_wind,
                "unit": "mph",
                "description": "Placeholder average wind speed metric",
            },
            {
                "id": "precip_days",
                "title": "Precipitation Days",
                "value": precip_days,
                "unit": "days",
                "description": "Placeholder count of days with precipitation",
            },
        ],
        "series": {
            "temperature_over_time": build_series(
                conn,
                schema_name,
                table_name,
                detected_columns["date"],
                detected_columns["temperature"],
            ),
            "wind_speed_over_time": build_series(
                conn,
                schema_name,
                table_name,
                detected_columns["date"],
                detected_columns["wind_speed"],
            ),
        },
        "metadata": {
            "source": "duckdb",
            "notes": [
                "Placeholder analytics layer",
                "Schema can be extended later",
            ],
            "database_path": str(DATABASE_PATH.name),
            "source_table": f"{schema_name}.{table_name}",
            # Best-effort mapping keeps the scaffold usable even if upstream names evolve.
            "detected_columns": detected_columns,
        },
    }

    return payload, source_table, detected_columns


def write_json_output(payload: dict[str, Any], output_path: Path = OUTPUT_PATH) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    return output_path


def main() -> None:
    conn = get_connection()
    try:
        payload, source_table, detected_columns = build_payload(conn)
        output_path = write_json_output(payload)
    finally:
        conn.close()

    print(
        "Generated analytics JSON at "
        f"{output_path} using {source_table['schema']}.{source_table['table']} "
        f"with columns {detected_columns}"
    )


if __name__ == "__main__":
    main()
