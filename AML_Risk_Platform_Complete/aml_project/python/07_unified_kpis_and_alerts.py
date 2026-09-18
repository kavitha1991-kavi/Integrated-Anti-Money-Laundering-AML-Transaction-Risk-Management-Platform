"""
Step 7 - Unified Monitoring and Reporting System
===================================================
Pulls together the KPIs produced by every prior step into one
kpi_summary.csv/json (what the "unified platform" surfaces on a landing
page), and implements the alerting logic described in the brief: when a
threshold is breached (e.g. new Critical-severity fraud flags, a bank's
compliance score drops below the gap threshold), generate an alert record.

Actually emailing is stubbed out (no mail server / credentials in this
environment) -- `send_email_alert()` shows exactly how to wire it up with
smtplib once SMTP credentials are available; alerts are written to
reports/alerts_log.csv either way so they're visible without email.
"""
import json
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timezone

import pandas as pd

from db_utils import get_conn, DATA_MART_DIR, REPORTS_DIR

COMPLIANCE_GAP_THRESHOLD = 0.6
CRITICAL_FRAUD_ALERT_MIN = 1  # alert if any Critical-severity flags exist


def send_email_alert(subject: str, body: str, to_addr: str = "aml-team@example.com",
                      smtp_host: str = None, smtp_user: str = None, smtp_pass: str = None):
    """Reference implementation only. Wire in real SMTP settings to activate;
    left disabled here since no mail credentials are configured."""
    if not smtp_host:
        print(f"  [alert - email disabled, would send] subject={subject!r} to={to_addr}")
        return False
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_addr
    with smtplib.SMTP(smtp_host, 587) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, [to_addr], msg.as_string())
    return True


def build_kpi_summary(conn):
    total_txns = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    flagged = pd.read_sql_query("SELECT * FROM flagged_transactions", conn)
    cust_risk = pd.read_sql_query("SELECT * FROM customer_risk_profiles", conn)
    bank_comp = pd.read_sql_query("SELECT * FROM bank_compliance_profiles", conn)
    bank_risk = pd.read_sql_query("SELECT * FROM bank_risk_comparison_ranked", conn)
    dq = pd.read_csv(DATA_MART_DIR / "step1_data_quality_kpis.csv").iloc[0]

    kpis = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),

        # Step 1 - Data quality
        "data_completeness_pct": float(dq["data_completeness_pct"]),
        "data_consistency_pct": float(dq["data_consistency_pct"]),

        # Step 2 / 3 - Risk monitoring & fraud detection
        "total_transactions": int(total_txns),
        "flagged_transaction_count": int(len(flagged)),
        "flagged_rate_pct": round(100 * len(flagged) / total_txns, 2),
        "critical_flags": int((flagged["severity"] == "Critical").sum()),
        "high_flags": int((flagged["severity"] == "High").sum()),

        # Step 4 - Customer profiling
        "high_risk_customer_count": int((cust_risk["computed_segment"] == "High").sum()),
        "segmentation_agreement_pct": round(
            100 * (cust_risk["computed_segment"] == cust_risk["stated_risk_level"]).mean(), 2
        ),

        # Step 5 - Compliance & sanctions
        "total_sanctioned_accounts": int(bank_comp["sanctioned_account_count"].sum()),
        "avg_bank_compliance_score": round(float(bank_comp["compliance_score"].mean()), 3),
        "compliance_gap_pct": round(100 * (bank_comp["compliance_status"] == "Below Threshold").mean(), 2),

        # Step 6 - Bank comparison
        "high_risk_bank_count": int((bank_risk["bank_risk_score"] >= 50).sum()),
        "avg_bank_risk_score": round(float(bank_risk["bank_risk_score"].mean()), 2),
    }
    return kpis, flagged, bank_comp


def generate_alerts(kpis, flagged, bank_comp):
    alerts = []
    if kpis["critical_flags"] >= CRITICAL_FRAUD_ALERT_MIN:
        alerts.append({
            "alert_type": "CRITICAL_FRAUD_FLAGS",
            "message": f"{kpis['critical_flags']} transaction(s) reached Critical fraud severity.",
            "severity": "Critical",
        })
    below = bank_comp[bank_comp["compliance_status"] == "Below Threshold"]
    if len(below) > 0:
        alerts.append({
            "alert_type": "BANKS_BELOW_COMPLIANCE_THRESHOLD",
            "message": f"{len(below)} bank(s) below the {COMPLIANCE_GAP_THRESHOLD} compliance-score threshold.",
            "severity": "High",
        })
    for a in alerts:
        a["generated_at_utc"] = kpis["generated_at_utc"]
        send_email_alert(subject=f"[AML Platform] {a['alert_type']}", body=a["message"])
    return alerts


def main():
    conn = get_conn()
    kpis, flagged, bank_comp = build_kpi_summary(conn)

    pd.DataFrame([kpis]).to_csv(DATA_MART_DIR / "kpi_summary.csv", index=False)
    with open(DATA_MART_DIR / "kpi_summary.json", "w") as f:
        json.dump(kpis, f, indent=2)
    print("Unified KPI summary:")
    for k, v in kpis.items():
        print(f"  {k:35s} {v}")

    alerts = generate_alerts(kpis, flagged, bank_comp)
    pd.DataFrame(alerts).to_csv(REPORTS_DIR / "alerts_log.csv", index=False)
    print(f"\nGenerated {len(alerts)} alert(s) -> reports/alerts_log.csv")
    conn.close()


if __name__ == "__main__":
    main()
