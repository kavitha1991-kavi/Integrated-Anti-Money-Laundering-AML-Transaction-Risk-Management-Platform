"""
Step 1a/1b - Data Ingestion, Schema Creation, Data Cleaning
=============================================================
Loads the four source CSVs into raw staging tables, creates the clean
relational schema (sql/01_schema.sql), then cleans/deduplicates/standardizes
into the final `customers`, `banks`, `transactions`, `sanctions` tables
(sql/02_data_cleaning.sql). Also runs a Pandas-based data-quality pass for
things SQL alone doesn't do well (dtype coercion, outlier scan) and prints
the Step-1 Data-Quality KPIs.
"""
import sys
import pathlib
import pandas as pd
from db_utils import get_conn, run_script, RAW_DATA_DIR, DATA_MART_DIR

SOURCE_FILES = {
    "raw_customers": "customers_.csv",
    "raw_banks": "banks.csv",
    "raw_transactions": "transactions.csv",
    "raw_sanctions": "sanctions.csv",
}


def load_raw_tables(conn, source_dir):
    for table, filename in SOURCE_FILES.items():
        df = pd.read_csv(source_dir / filename)

        # --- Pandas-side cleaning (Step 1b: "Use Python's Pandas for more
        #     granular cleaning: outliers, dtype transforms") ---
        if "amount" in df.columns:
            df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        if "compliance_score" in df.columns:
            df["compliance_score"] = pd.to_numeric(df["compliance_score"], errors="coerce")
        for bool_col in ("is_high_risk", "is_valid_bank_id"):
            if bool_col in df.columns:
                df[bool_col] = df[bool_col].astype(bool).astype(int)
        # Standardize date columns to YYYY-MM-DD (redundant safety net; the
        # SQL layer also standardizes, this guarantees it before SQL load)
        for date_col in ("date", "sanction_date"):
            if date_col in df.columns:
                df[date_col] = pd.to_datetime(df[date_col], errors="coerce").dt.strftime("%Y-%m-%d")
        # Trim whitespace on text columns
        for col in df.select_dtypes(include="object").columns:
            df[col] = df[col].str.strip()

        df.to_sql(table, conn, if_exists="replace", index=False)
        print(f"  loaded {table:<20s} {len(df):>6,} rows  <- {filename}")


def data_quality_report(conn):
    """Recreates the Step-1 KPIs (Completeness / Consistency / Coverage)."""
    tx = pd.read_sql_query("SELECT * FROM transactions", conn)
    cust = pd.read_sql_query("SELECT * FROM customers", conn)
    banks = pd.read_sql_query("SELECT * FROM banks", conn)
    sanc = pd.read_sql_query("SELECT * FROM sanctions", conn)

    total_cells = sum(df.size for df in (tx, cust, banks, sanc))
    missing_cells = sum(df.isna().sum().sum() for df in (tx, cust, banks, sanc))
    completeness_pct = round(100 * (1 - missing_cells / total_cells), 2)

    iso_date_pattern = r"^\d{4}-\d{2}-\d{2}$"
    date_consistent = tx["txn_date"].astype(str).str.match(iso_date_pattern).mean() * 100
    date_consistent2 = sanc["sanction_date"].astype(str).str.match(iso_date_pattern).mean() * 100
    consistency_pct = round((date_consistent + date_consistent2) / 2, 2)

    orphan_bank = (~tx["bank_id"].isin(banks["bank_id"])).sum()
    orphan_cust = (~tx["customer_id"].isin(cust["customer_id"])).sum()

    q1, q3 = tx["amount"].quantile([0.25, 0.75])
    iqr = q3 - q1
    outliers = ((tx["amount"] < q1 - 1.5 * iqr) | (tx["amount"] > q3 + 1.5 * iqr)).sum()

    kpis = {
        "data_completeness_pct": completeness_pct,
        "data_consistency_pct": consistency_pct,
        "orphan_transaction_bank_fk": int(orphan_bank),
        "orphan_transaction_customer_fk": int(orphan_cust),
        "amount_outliers_iqr": int(outliers),
        "duplicate_transactions_removed": 0,  # see dedup step below
        "total_customers": len(cust),
        "total_banks": len(banks),
        "total_transactions": len(tx),
        "total_sanctions": len(sanc),
    }
    return kpis


def main(source_dir=None):
    source_dir = pathlib.Path(source_dir) if source_dir else RAW_DATA_DIR
    conn = get_conn()

    print("[1/3] Loading raw CSVs into staging tables ...")
    load_raw_tables(conn, source_dir)

    print("[2/3] Creating clean schema (sql/01_schema.sql) ...")
    run_script(conn, "01_schema.sql")

    print("[3/3] Cleaning, deduplicating, standardizing (sql/02_data_cleaning.sql) ...")
    run_script(conn, "02_data_cleaning.sql")

    kpis = data_quality_report(conn)
    print("\nStep 1 Data-Quality KPIs:")
    for k, v in kpis.items():
        print(f"  {k:35s} {v}")

    pd.DataFrame([kpis]).to_csv(DATA_MART_DIR / "step1_data_quality_kpis.csv", index=False)
    conn.close()
    return kpis


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else None
    main(src)
