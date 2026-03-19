from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / ".local.nosync" / "analytics.duckdb"
OUTPUT_PATH = PROJECT_ROOT / "data" / "ball_averages.json"
SOURCE_SCHEMA = "raw"
SOURCE_TABLE = "gamestats"
TARGET_SCHEMA = "main"
OVERALL_TABLE = "ball_averages"
MONTHLY_TABLE = "ball_averages_monthly"
DATE_COLUMN = "date"
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


def create_connection(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DATABASE_PATH), read_only=read_only)


def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def qualified_table(schema_name: str, table_name: str) -> str:
    return f"{quote_identifier(schema_name)}.{quote_identifier(table_name)}"


def round_or_none(value: Any) -> float | None:
    return round(float(value), 2) if value is not None else None


def create_target_tables(conn: duckdb.DuckDBPyConnection) -> None:
    source_table = qualified_table(SOURCE_SCHEMA, SOURCE_TABLE)
    overall_table = qualified_table(TARGET_SCHEMA, OVERALL_TABLE)
    monthly_table = qualified_table(TARGET_SCHEMA, MONTHLY_TABLE)

    conn.execute(
        f"""
        CREATE OR REPLACE TABLE {overall_table} AS
        SELECT
            COUNT(*) AS game_count,
            ROUND(AVG(home_score + visiting_score), 2) AS avg_runs,
            ROUND(AVG(home_home_runs + visiting_home_runs), 2) AS avg_home_runs,
            ROUND(AVG(home_home_runs), 2) AS avg_home_team_home_runs,
            ROUND(AVG(visiting_home_runs), 2) AS avg_visiting_team_home_runs,
            ROUND(AVG(game_time_minutes), 2) AS avg_game_time_minutes
        FROM {source_table}
        """
    )

    conn.execute(
        f"""
        CREATE OR REPLACE TABLE {monthly_table} AS
        SELECT
            EXTRACT(MONTH FROM {quote_identifier(DATE_COLUMN)})::INTEGER AS month_number,
            COUNT(*) AS game_count,
            ROUND(AVG(home_score + visiting_score), 2) AS avg_runs,
            ROUND(AVG(home_home_runs + visiting_home_runs), 2) AS avg_home_runs,
            ROUND(AVG(home_home_runs), 2) AS avg_home_team_home_runs,
            ROUND(AVG(visiting_home_runs), 2) AS avg_visiting_team_home_runs,
            ROUND(AVG(game_time_minutes), 2) AS avg_game_time_minutes
        FROM {source_table}
        WHERE {quote_identifier(DATE_COLUMN)} IS NOT NULL
        GROUP BY 1
        ORDER BY 1
        """
    )


def fetch_overall_averages(conn: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    row = conn.execute(
        f"SELECT * FROM {qualified_table(TARGET_SCHEMA, OVERALL_TABLE)}"
    ).fetchone()
    return {
        "game_count": int(row[0]),
        "averages": {
            "runs": round_or_none(row[1]),
            "home_runs": round_or_none(row[2]),
            "home_team_home_runs": round_or_none(row[3]),
            "visiting_team_home_runs": round_or_none(row[4]),
            "game_time_minutes": round_or_none(row[5]),
        },
    }


def fetch_monthly_averages(conn: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    rows = conn.execute(
        f"SELECT * FROM {qualified_table(TARGET_SCHEMA, MONTHLY_TABLE)} ORDER BY month_number"
    ).fetchall()
    return [
        {
            "month_number": int(month_number),
            "month": MONTH_NAMES[int(month_number)],
            "game_count": int(game_count),
            "averages": {
                "runs": round_or_none(avg_runs),
                "home_runs": round_or_none(avg_home_runs),
                "home_team_home_runs": round_or_none(avg_home_team_home_runs),
                "visiting_team_home_runs": round_or_none(avg_visiting_team_home_runs),
                "game_time_minutes": round_or_none(avg_game_time_minutes),
            },
        }
        for (
            month_number,
            game_count,
            avg_runs,
            avg_home_runs,
            avg_home_team_home_runs,
            avg_visiting_team_home_runs,
            avg_game_time_minutes,
        ) in rows
    ]


def fetch_summary(conn: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    row = conn.execute(
        f"""
        SELECT
            COUNT(*) AS game_count,
            MIN({quote_identifier(DATE_COLUMN)}) AS date_min,
            MAX({quote_identifier(DATE_COLUMN)}) AS date_max
        FROM {qualified_table(SOURCE_SCHEMA, SOURCE_TABLE)}
        """
    ).fetchone()
    return {
        "game_count": int(row[0]),
        "date_min": row[1].isoformat() if row[1] else None,
        "date_max": row[2].isoformat() if row[2] else None,
    }


def build_payload(conn: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "database_path": DATABASE_PATH.name,
            "table": f"{SOURCE_SCHEMA}.{SOURCE_TABLE}",
        },
        "summary": fetch_summary(conn),
        "metrics": {
            "all_games": fetch_overall_averages(conn),
            "by_month": fetch_monthly_averages(conn),
        },
        "metadata": {
            "duckdb_tables": {
                "overall": f"{TARGET_SCHEMA}.{OVERALL_TABLE}",
                "monthly": f"{TARGET_SCHEMA}.{MONTHLY_TABLE}",
            },
            "notes": [
                "Monthly averages are grouped across all years in the baseball data table.",
                "Runs are calculated as home_score + visiting_score.",
                "Home runs are calculated as home_home_runs + visiting_home_runs.",
            ],
        },
    }


def write_output(payload: dict[str, Any]) -> Path:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    return OUTPUT_PATH


def main() -> None:
    conn = create_connection()
    try:
        create_target_tables(conn)
        payload = build_payload(conn)
        output_path = write_output(payload)
    finally:
        conn.close()

    print(
        "Generated baseball averages in "
        f"{TARGET_SCHEMA}.{OVERALL_TABLE}, {TARGET_SCHEMA}.{MONTHLY_TABLE}, "
        f"and {output_path}"
    )


if __name__ == "__main__":
    main()
