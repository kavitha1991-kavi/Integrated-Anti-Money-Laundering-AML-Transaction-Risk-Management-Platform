"""
Step 5 - Compliance and Sanctions Monitoring
===============================================
Runs sql/06_compliance_sanctions_monitoring.sql, exports the per-bank
compliance profile and the regional compliance rollup, and prints the
compliance KPIs.
"""
import pandas as pd
from db_utils import get_conn, run_script, export_table, DATA_MART_DIR


def main():
    conn = get_conn()
    print("Running sql/06_compliance_sanctions_monitoring.sql ...")
    run_script(conn, "06_compliance_sanctions_monitoring.sql")

    df = export_table(conn, "bank_compliance_profiles")
    print(f"  exported bank_compliance_profiles {len(df):,} rows -> data_marts/bank_compliance_profiles.csv")

    region_rollup = pd.read_sql_query(
        """
        SELECT region, COUNT(*) AS bank_count, ROUND(AVG(compliance_score),3) AS avg_compliance_score,
               SUM(sanctioned_account_count) AS total_sanctioned_accounts,
               SUM(CASE WHEN compliance_status='Below Threshold' THEN 1 ELSE 0 END) AS banks_below_threshold
        FROM bank_compliance_profiles GROUP BY region ORDER BY avg_compliance_score ASC
        """,
        conn,
    )
    region_rollup.to_csv(DATA_MART_DIR / "compliance_region_rollup.csv", index=False)
    print(f"  exported compliance_region_rollup -> data_marts/compliance_region_rollup.csv")

    total_sanctioned = int(df["sanctioned_account_count"].sum())
    avg_score = round(df["compliance_score"].mean(), 3)
    gap_pct = round(100 * (df["compliance_status"] == "Below Threshold").mean(), 2)

    print(f"\nStep 5 KPIs:")
    print(f"  Total sanctioned accounts:    {total_sanctioned}")
    print(f"  Avg compliance score:         {avg_score}")
    print(f"  Compliance gap (below 0.6):   {gap_pct}%")
    conn.close()


if __name__ == "__main__":
    main()
