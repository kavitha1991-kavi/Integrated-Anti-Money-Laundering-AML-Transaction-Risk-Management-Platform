"""
Step 6 - Bank Risk Comparison and Analysis
=============================================
Runs sql/07_bank_risk_comparison.sql to build a composite bank_risk_score
(0-100) per bank and a rank, exports the full comparison table, and prints
the top-10 riskiest banks + comparison KPIs.
"""
from db_utils import get_conn, run_script, export_table


def main():
    conn = get_conn()
    print("Running sql/07_bank_risk_comparison.sql ...")
    run_script(conn, "07_bank_risk_comparison.sql")

    df = export_table(conn, "bank_risk_comparison_ranked")
    print(f"  exported bank_risk_comparison_ranked {len(df):,} rows -> data_marts/bank_risk_comparison_ranked.csv")

    high_risk_banks = (df["bank_risk_score"] >= 50).sum()
    avg_score = round(df["bank_risk_score"].mean(), 2)

    print(f"\nStep 6 KPIs:")
    print(f"  High-risk bank count (score>=50): {high_risk_banks}")
    print(f"  Avg bank risk score:              {avg_score}")
    print("\nTop 10 riskiest banks:")
    top10 = df.sort_values("risk_rank").head(10)[
        ["risk_rank", "bank_id", "name", "region", "compliance_score", "sanctioned_account_count", "bank_risk_score"]
    ]
    print(top10.to_string(index=False))
    conn.close()


if __name__ == "__main__":
    main()
