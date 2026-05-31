from pathlib import Path
import sqlite3
import subprocess
import sys

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_FILE = PROJECT_ROOT / "db" / "roaming_lab.db"
RUN_PROJECT_FILE = PROJECT_ROOT / "run_project.py"
MARKDOWN_REPORT = PROJECT_ROOT / "reports" / "validation_test_report.md"


st.set_page_config(
    page_title="Roaming Billing CDR Validation Lab",
    layout="wide",
)


def database_exists() -> bool:
    return DB_FILE.exists()


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    return conn


def read_sql(query: str, params: tuple = ()) -> pd.DataFrame:
    if not database_exists():
        return pd.DataFrame()

    with get_connection() as conn:
        return pd.read_sql_query(query, conn, params=params)


def get_table_count(table_name: str) -> int:
    if not database_exists():
        return 0

    try:
        df = read_sql(f"SELECT COUNT(*) AS count FROM {table_name}")
        if df.empty:
            return 0
        return int(df.iloc[0]["count"])
    except Exception:
        return 0


def get_latest_rows(table_name: str, limit: int = 50) -> pd.DataFrame:
    if not database_exists():
        return pd.DataFrame()

    try:
        return read_sql(
            f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT ?",
            (limit,),
        )
    except Exception:
        return pd.DataFrame()


def run_pipeline(input_path: str) -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, str(RUN_PROJECT_FILE), "--input", input_path],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )

    output = ""

    if result.stdout:
        output += result.stdout

    if result.stderr:
        output += "\nSTDERR:\n" + result.stderr

    return result.returncode == 0, output


st.title("Roaming Billing CDR Validation Lab")

st.write(
    "A local dashboard for mock roaming CDR validation, tariff-based billing checks, "
    "reconciliation summaries, SQLite persistence, and technical reporting."
)

st.divider()

with st.sidebar:
    st.header("Pipeline Control")

    input_path = st.text_input(
        "Input CDR CSV path",
        value="data/mock_roaming_cdrs.csv",
        help="Path relative to the project root.",
    )

    run_button = st.button("Run Validation Pipeline")

    st.divider()

    st.header("Project Files")
    st.write(f"Database: `{DB_FILE.relative_to(PROJECT_ROOT)}`")
    st.write(f"Report: `{MARKDOWN_REPORT.relative_to(PROJECT_ROOT)}`")

if run_button:
    with st.spinner("Running pipeline..."):
        success, output = run_pipeline(input_path)

    if success:
        st.success("Pipeline completed successfully.")
    else:
        st.error("Pipeline failed.")

    with st.expander("Pipeline output", expanded=True):
        st.code(output)

st.subheader("System Health")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Database Exists", "Yes" if DB_FILE.exists() else "No")

with col2:
    st.metric("CDR Records", get_table_count("cdr_records"))

with col3:
    st.metric("Validation Issues", get_table_count("validation_issues"))

with col4:
    st.metric("Billing Results", get_table_count("billing_results"))

st.divider()

if not database_exists():
    st.warning(
        "Database not found. Run the pipeline first using the sidebar button "
        "or run: python run_project.py --input data/mock_roaming_cdrs.csv"
    )
    st.stop()

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    [
        "Run History",
        "Validation Issues",
        "Billing Results",
        "Billing Summary",
        "Reconciliation Summary",
        "Markdown Report",
    ]
)

with tab1:
    st.subheader("Run History")

    df = read_sql(
        """
        SELECT *
        FROM run_history
        ORDER BY run_timestamp_utc DESC
        LIMIT 20
        """
    )

    if df.empty:
        st.info("No run history found.")
    else:
        st.dataframe(df, use_container_width=True)

with tab2:
    st.subheader("Latest Validation Issues")

    limit = st.slider(
        "Validation issue rows",
        min_value=10,
        max_value=500,
        value=50,
        step=10,
        key="validation_limit",
    )

    df = get_latest_rows("validation_issues", limit)

    if df.empty:
        st.info("No validation issues found.")
    else:
        st.dataframe(df, use_container_width=True)

        if "rule_id" in df.columns:
            st.write("Issues by rule")
            rule_counts = df["rule_id"].value_counts().reset_index()
            rule_counts.columns = ["rule_id", "count"]
            st.bar_chart(rule_counts.set_index("rule_id"))

with tab3:
    st.subheader("Latest Billing Results")

    limit = st.slider(
        "Billing result rows",
        min_value=10,
        max_value=500,
        value=50,
        step=10,
        key="billing_limit",
    )

    df = get_latest_rows("billing_results", limit)

    if df.empty:
        st.info("No billing results found.")
    else:
        st.dataframe(df, use_container_width=True)

        if "billing_status" in df.columns:
            st.write("Billing results by status")
            status_counts = df["billing_status"].value_counts().reset_index()
            status_counts.columns = ["billing_status", "count"]
            st.bar_chart(status_counts.set_index("billing_status"))

with tab4:
    st.subheader("Billing Summary")

    df = get_latest_rows("billing_summary", 200)

    if df.empty:
        st.info("No billing summary found.")
    else:
        st.dataframe(df, use_container_width=True)

with tab5:
    st.subheader("Reconciliation Summary")

    df = get_latest_rows("reconciliation_summary", 200)

    if df.empty:
        st.info("No reconciliation summary found.")
    else:
        st.dataframe(df, use_container_width=True)

with tab6:
    st.subheader("Markdown Validation Report")

    if not MARKDOWN_REPORT.exists():
        st.info("Markdown report not found.")
    else:
        report_text = MARKDOWN_REPORT.read_text(encoding="utf-8")
        st.markdown(report_text)