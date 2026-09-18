"""
Step 1c - Feature Engineering
==============================
Runs sql/03_feature_engineering.sql to build customer/bank/region-level
features and transaction-level risk flags, then exports each as a CSV data
mart (for Power BI / Tableau / the bundled HTML dashboard to consume).
"""
from db_utils import get_conn, run_script, export_table


def main():
    conn = get_conn()
    print("Running sql/03_feature_engineering.sql ...")
    run_script(conn, "03_feature_engineering.sql")

    for table in ("customer_features", "bank_features", "region_features", "transaction_flags"):
        df = export_table(conn, table)
        print(f"  exported {table:<20s} {len(df):>6,} rows -> data_marts/{table}.csv")

    coverage = conn.execute(
        "SELECT ROUND(100.0*SUM(CASE WHEN txn_frequency>0 THEN 1 ELSE 0 END)/COUNT(*),2) FROM customer_features"
    ).fetchone()[0]
    print(f"\nFeature coverage KPI: {coverage}% of customers have a populated feature set")
    conn.close()


if __name__ == "__main__":
    main()
