"""
Shared helpers for the AML pipeline scripts.
All scripts operate on a single SQLite database file: aml_platform.db
(SQLite is used so the whole pipeline runs end-to-end without a live DB
server; every .sql file under sql/ is portable ANSI SQL and can be pointed
at Postgres/MySQL instead -- see sql/01_schema.sql notes.)
"""
import sqlite3
import pathlib

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "aml_platform.db"
SQL_DIR = BASE_DIR / "sql"
DATA_MART_DIR = BASE_DIR / "data_marts"
REPORTS_DIR = BASE_DIR / "reports"
RAW_DATA_DIR = BASE_DIR / "raw_data"

DATA_MART_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def run_script(conn, filename):
    """Execute every statement in a .sql file (DDL/DML). Any bare SELECT
    statements included for ad-hoc review are executed but their results
    are not captured here -- see each step's script for the same KPIs
    re-derived and printed/exported in Python."""
    sql_text = (SQL_DIR / filename).read_text()
    conn.executescript(sql_text)
    conn.commit()


def export_table(conn, table_name, out_name=None):
    import pandas as pd
    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    out_name = out_name or f"{table_name}.csv"
    df.to_csv(DATA_MART_DIR / out_name, index=False)
    return df
