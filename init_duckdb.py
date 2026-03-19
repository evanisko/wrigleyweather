from __future__ import annotations

import re
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parent
DATABASE_PATH = PROJECT_ROOT / "analytics.duckdb"
CSV_CONFIG = {
    "gamedayweather": "gamedayweather.csv",
    "gamestats": "gamestats.csv",
}


def create_connection() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DATABASE_PATH))


def create_schemas(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute("CREATE SCHEMA IF NOT EXISTS raw")
    conn.execute("CREATE SCHEMA IF NOT EXISTS analytics")


def clean_identifier(name: str) -> str:
    cleaned = re.sub(r"[^0-9a-zA-Z]+", "_", name.strip().lower())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if not cleaned:
        cleaned = "column"
    if cleaned[0].isdigit():
        cleaned = f"col_{cleaned}"
    return cleaned


def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def resolve_csv_path(filename: str) -> Path:
    direct_path = PROJECT_ROOT / filename
    if direct_path.exists():
        return direct_path

    matches = sorted(
        path
        for path in PROJECT_ROOT.rglob("*")
        if path.is_file() and path.name.lower() == filename.lower()
    )
    if matches:
        print(f"Using fallback CSV path for {filename}: {matches[0].relative_to(PROJECT_ROOT)}")
        return matches[0]

    raise FileNotFoundError(
        f"Could not find {filename!r} in {PROJECT_ROOT} or its subdirectories."
    )


def get_csv_columns(
    conn: duckdb.DuckDBPyConnection, csv_path: Path
) -> list[tuple[str, str]]:
    describe_sql = """
        DESCRIBE
        SELECT *
        FROM read_csv_auto(?, HEADER = TRUE, NULLSTR = 'NULL')
    """
    return [(row[0], row[1]) for row in conn.execute(describe_sql, [str(csv_path)]).fetchall()]


def build_select_list(columns: list[tuple[str, str]]) -> str:
    select_parts: list[str] = []
    used_names: dict[str, int] = {}

    for original_name, inferred_type in columns:
        cleaned_name = clean_identifier(original_name)
        duplicate_count = used_names.get(cleaned_name, 0)
        used_names[cleaned_name] = duplicate_count + 1
        if duplicate_count:
            cleaned_name = f"{cleaned_name}_{duplicate_count + 1}"

        quoted_original = quote_identifier(original_name)
        quoted_cleaned = quote_identifier(cleaned_name)
        expression = quoted_original

        if inferred_type.upper() == "VARCHAR":
            lowered_name = cleaned_name.lower()
            if lowered_name == "date" or lowered_name.endswith("_date"):
                expression = (
                    f"COALESCE("
                    f"TRY_STRPTIME({quoted_original}, '%Y/%m/%d'), "
                    f"TRY_STRPTIME({quoted_original}, '%Y-%m-%d')"
                    f")::DATE"
                )
            elif "timestamp" in lowered_name or "datetime" in lowered_name:
                expression = (
                    f"COALESCE("
                    f"TRY_STRPTIME({quoted_original}, '%Y/%m/%d %H:%M:%S'), "
                    f"TRY_STRPTIME({quoted_original}, '%Y-%m-%d %H:%M:%S'), "
                    f"TRY_STRPTIME({quoted_original}, '%Y/%m/%d %H:%M'), "
                    f"TRY_STRPTIME({quoted_original}, '%Y-%m-%d %H:%M')"
                    f")"
                )

        select_parts.append(f"{expression} AS {quoted_cleaned}")

    return ",\n    ".join(select_parts)


def print_schema(
    conn: duckdb.DuckDBPyConnection, schema_name: str, table_name: str
) -> None:
    rows = conn.execute(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = ? AND table_name = ?
        ORDER BY ordinal_position
        """,
        [schema_name, table_name],
    ).fetchall()

    print(f"\nSchema for {schema_name}.{table_name}:")
    for column_name, data_type in rows:
        print(f"  - {column_name}: {data_type}")


def print_query_results(
    conn: duckdb.DuckDBPyConnection, label: str, query: str
) -> None:
    result = conn.execute(query)
    columns = [description[0] for description in result.description]
    rows = result.fetchall()

    print(f"\n{label}")
    print(" | ".join(columns))
    for row in rows:
        print(" | ".join("" if value is None else str(value) for value in row))


def load_csv_to_table(
    conn: duckdb.DuckDBPyConnection, schema_name: str, table_name: str, csv_filename: str
) -> None:
    csv_path = resolve_csv_path(csv_filename)
    columns = get_csv_columns(conn, csv_path)
    select_list = build_select_list(columns)

    create_sql = f"""
        CREATE OR REPLACE TABLE {quote_identifier(schema_name)}.{quote_identifier(table_name)} AS
        SELECT
            {select_list}
        FROM read_csv_auto(?, HEADER = TRUE, NULLSTR = 'NULL')
    """
    conn.execute(create_sql, [str(csv_path)])

    row_count = conn.execute(
        f"SELECT COUNT(*) FROM {quote_identifier(schema_name)}.{quote_identifier(table_name)}"
    ).fetchone()[0]
    print(
        f"\nLoaded {row_count} rows into {schema_name}.{table_name} "
        f"from {csv_path.relative_to(PROJECT_ROOT)}"
    )
    print_schema(conn, schema_name, table_name)


def validate_tables(conn: duckdb.DuckDBPyConnection) -> None:
    for table_name in CSV_CONFIG:
        qualified_table = f"raw.{table_name}"
        print_query_results(
            conn,
            f"Validation row count for {qualified_table}",
            f"SELECT COUNT(*) AS row_count FROM {qualified_table}",
        )
        print_query_results(
            conn,
            f"Sample rows from {qualified_table}",
            f"SELECT * FROM {qualified_table} LIMIT 5",
        )

    table_names = set(CSV_CONFIG)
    if {"gamedayweather", "gamestats"}.issubset(table_names):
        print_query_results(
            conn,
            "Sample join on date",
            """
            SELECT
                gs.date,
                gs.home_team,
                gs.visiting_team,
                gs.home_score,
                gs.visiting_score,
                gw.temperature_2m_max,
                gw.precipitation_sum,
                gw.windspeed_10m_max
            FROM raw.gamestats AS gs
            INNER JOIN raw.gamedayweather AS gw
                ON gs.date = gw.date
            ORDER BY gs.date
            LIMIT 5
            """,
        )


def main() -> None:
    conn = create_connection()
    try:
        create_schemas(conn)
        for table_name, csv_filename in CSV_CONFIG.items():
            load_csv_to_table(conn, "raw", table_name, csv_filename)
        validate_tables(conn)
        print(f"\nDuckDB database ready at {DATABASE_PATH}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
