"""
Step 4 - Customer Risk Profiling and Segmentation
====================================================
Runs sql/05_customer_risk_profiling.sql to compute a composite 0-100 risk
score per customer and a computed Low/Medium/High segment, then exports the
result and prints the profiling KPIs.
"""
from db_utils import get_conn, run_script, export_table


def main():
    conn = get_conn()
    print("Running sql/05_customer_risk_profiling.sql ...")
    run_script(conn, "05_customer_risk_profiling.sql")

    df = export_table(conn, "customer_risk_profiles")
    print(f"  exported customer_risk_profiles {len(df):,} rows -> data_marts/customer_risk_profiles.csv")

    high_risk_count = (df["computed_segment"] == "High").sum()
    agreement_pct = round(100 * (df["computed_segment"] == df["stated_risk_level"]).mean(), 2)
    completeness_pct = round(100 * (df["txn_frequency"] > 0).mean(), 2)

    print(f"\nStep 4 KPIs:")
    print(f"  High-risk customer count:     {high_risk_count}")
    print(f"  Segmentation agreement w/ stated risk_level: {agreement_pct}%")
    print(f"  Profile completeness rate:    {completeness_pct}%")
    conn.close()


if __name__ == "__main__":
    main()
