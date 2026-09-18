"""
Builds data_marts/dashboard_data.json -- a single, size-trimmed bundle of
everything the HTML dashboard needs, so the dashboard has no server
dependency and no live DB connection (it's a static file that can be opened
directly, emailed, or hosted anywhere).
"""
import json
import pandas as pd
from db_utils import DATA_MART_DIR, REPORTS_DIR


def main():
    kpis = pd.read_csv(DATA_MART_DIR / "kpi_summary.csv").iloc[0].to_dict()

    region = pd.read_csv(DATA_MART_DIR / "region_features.csv")
    comp_region = pd.read_csv(DATA_MART_DIR / "compliance_region_rollup.csv")

    flagged = pd.read_csv(DATA_MART_DIR / "flagged_transactions.csv")[
        ["transaction_id", "customer_name", "bank_name", "customer_region",
         "customer_stated_risk", "amount", "txn_date", "fraud_score", "severity",
         "requires_analyst_review", "sanctions_flag"]
    ]

    cust = pd.read_csv(DATA_MART_DIR / "customer_risk_profiles.csv")[
        ["customer_id", "name", "region", "stated_risk_level", "computed_segment",
         "composite_risk_score", "txn_frequency", "avg_txn_amount", "sanction_count"]
    ].fillna(0)

    banks = pd.read_csv(DATA_MART_DIR / "bank_risk_comparison_ranked.csv")[
        ["bank_id", "name", "region", "compliance_score", "txn_frequency",
         "sanctioned_account_count", "high_risk_txn_pct", "bank_risk_score", "risk_rank"]
    ].fillna(0)

    bank_compliance = pd.read_csv(DATA_MART_DIR / "bank_compliance_profiles.csv")[
        ["bank_id", "name", "region", "compliance_score", "sanctioned_account_count",
         "ml_sanction_count", "fraud_sanction_count", "compliance_violation_count", "compliance_status"]
    ]

    alerts = pd.read_csv(REPORTS_DIR / "alerts_log.csv")

    bundle = {
        "kpis": kpis,
        "region": region.to_dict(orient="records"),
        "complianceRegion": comp_region.to_dict(orient="records"),
        "flagged": flagged.to_dict(orient="records"),
        "customers": cust.to_dict(orient="records"),
        "banks": banks.sort_values("risk_rank").to_dict(orient="records"),
        "bankCompliance": bank_compliance.to_dict(orient="records"),
        "alerts": alerts.to_dict(orient="records"),
    }

    out_path = DATA_MART_DIR / "dashboard_data.json"
    with open(out_path, "w") as f:
        json.dump(bundle, f, default=str)
    print(f"wrote {out_path} ({out_path.stat().st_size/1024:.1f} KB)")


if __name__ == "__main__":
    main()
