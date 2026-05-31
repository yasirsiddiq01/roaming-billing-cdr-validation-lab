from pathlib import Path
import csv
import re
import sqlite3
from datetime import datetime, timezone


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DB_DIR = PROJECT_ROOT / "db"
DB_FILE = DB_DIR / "roaming_lab.db"

INPUT_CDR_FILE = PROJECT_ROOT / "data" / "mock_roaming_cdrs.csv"

REPORTS = {
    "cdr_records": INPUT_CDR_FILE,
    "validation_issues": PROJECT_ROOT / "reports" / "validation_issues.csv",
    "billing_results": PROJECT_ROOT / "reports" / "billing_results.csv",
    "billing_summary": PROJECT_ROOT / "reports" / "billing_summary.csv",
    "reconciliation_summary": PROJECT_ROOT / "reports" / "reconciliation_summary.csv",
}

MARKDOWN_REPORT = PROJECT_ROOT / "reports" / "validation_test_report.md"


def sanitize_column_name(name: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9_]+", "_", name.strip().lower())
    clean = clean.strip("_")

    if not clean:
        clean = "unnamed_column"

    if clean[0].isdigit():
        clean = f"col_{clean}"

    return clean


def make_unique_columns(columns: list[str]) -> list[str]:
    seen = {}
    unique = []

    for column in columns:
        base = sanitize_column_name(column)
        count = seen.get(base, 0)

        if count == 0:
            unique.append(base)
        else:
            unique.append(f"{base}_{count + 1}")

        seen[base] = count + 1

    return unique


def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def create_run_history_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS run_history (
            run_id TEXT PRIMARY KEY,
            run_timestamp_utc TEXT NOT NULL,
            input_file TEXT NOT NULL,
            database_file TEXT NOT NULL,
            markdown_report_file TEXT,
            notes TEXT
        )
        """
    )


def insert_run_history(conn: sqlite3.Connection, run_id: str) -> None:
    conn.execute(
        """
        INSERT INTO run_history (
            run_id,
            run_timestamp_utc,
            input_file,
            database_file,
            markdown_report_file,
            notes
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            datetime.now(timezone.utc).isoformat(),
            str(INPUT_CDR_FILE.relative_to(PROJECT_ROOT)),
            str(DB_FILE.relative_to(PROJECT_ROOT)),
            str(MARKDOWN_REPORT.relative_to(PROJECT_ROOT))
            if MARKDOWN_REPORT.exists()
            else "",
            "Roaming billing CDR validation lab run",
        ),
    )


def get_existing_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(
        f"PRAGMA table_info({quote_identifier(table_name)})"
    ).fetchall()

    return {row[1] for row in rows}


def ensure_table(
    conn: sqlite3.Connection,
    table_name: str,
    csv_columns: list[str],
) -> list[str]:
    sanitized_columns = make_unique_columns(csv_columns)

    base_columns = [
        "id INTEGER PRIMARY KEY AUTOINCREMENT",
        "run_id TEXT NOT NULL",
    ]

    data_columns = [
        f"{quote_identifier(column)} TEXT" for column in sanitized_columns
    ]

    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {quote_identifier(table_name)} (
            {", ".join(base_columns + data_columns)}
        )
        """
    )

    existing_columns = get_existing_columns(conn, table_name)

    for column in sanitized_columns:
        if column not in existing_columns:
            conn.execute(
                f"""
                ALTER TABLE {quote_identifier(table_name)}
                ADD COLUMN {quote_identifier(column)} TEXT
                """
            )

    return sanitized_columns


def import_csv_to_table(
    conn: sqlite3.Connection,
    table_name: str,
    csv_path: Path,
    run_id: str,
) -> int:
    if not csv_path.exists():
        print(f"Skipped missing file: {csv_path.relative_to(PROJECT_ROOT)}")
        return 0

    with csv_path.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames:
            print(f"Skipped empty CSV: {csv_path.relative_to(PROJECT_ROOT)}")
            return 0

        original_columns = reader.fieldnames
        sanitized_columns = ensure_table(conn, table_name, original_columns)

        quoted_columns = ["run_id"] + sanitized_columns
        placeholders = ", ".join(["?"] * len(quoted_columns))

        insert_sql = f"""
            INSERT INTO {quote_identifier(table_name)}
            ({", ".join(quote_identifier(column) for column in quoted_columns)})
            VALUES ({placeholders})
        """

        row_count = 0

        for row in reader:
            values = [run_id]

            for original_column in original_columns:
                values.append(row.get(original_column, ""))

            conn.execute(insert_sql, values)
            row_count += 1

    return row_count


def create_table_counts_view(conn: sqlite3.Connection) -> None:
    conn.execute("DROP VIEW IF EXISTS latest_table_counts")

    conn.execute(
        """
        CREATE VIEW latest_table_counts AS
        SELECT 'cdr_records' AS table_name, COUNT(*) AS row_count FROM cdr_records
        UNION ALL
        SELECT 'validation_issues', COUNT(*) FROM validation_issues
        UNION ALL
        SELECT 'billing_results', COUNT(*) FROM billing_results
        UNION ALL
        SELECT 'billing_summary', COUNT(*) FROM billing_summary
        UNION ALL
        SELECT 'reconciliation_summary', COUNT(*) FROM reconciliation_summary
        UNION ALL
        SELECT 'run_history', COUNT(*) FROM run_history
        """
    )


def main() -> None:
    DB_DIR.mkdir(exist_ok=True)

    run_id = datetime.now(timezone.utc).strftime("run_%Y%m%d_%H%M%S")

    with sqlite3.connect(DB_FILE) as conn:
        create_run_history_table(conn)
        insert_run_history(conn, run_id)

        imported_counts = {}

        for table_name, csv_path in REPORTS.items():
            count = import_csv_to_table(conn, table_name, csv_path, run_id)
            imported_counts[table_name] = count

        create_table_counts_view(conn)
        conn.commit()

    print(f"SQLite database updated: {DB_FILE.relative_to(PROJECT_ROOT)}")
    print(f"Run ID: {run_id}")

    for table_name, count in imported_counts.items():
        print(f"Stored {count} rows in table: {table_name}")

    print("Stored run metadata in table: run_history")


if __name__ == "__main__":
    main()