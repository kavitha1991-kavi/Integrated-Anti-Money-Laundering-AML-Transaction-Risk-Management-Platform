"""
Step 3 - Rule-Based Fraud Detection System
=============================================
Runs sql/04_fraud_detection_rules.sql (6 weighted AML rules -> fraud_score
0-6 -> severity band), exports flagged_transactions.csv, produces a
multi-page PDF report for the AML team, and writes a disposition-log
template so False-Positive-Rate / Detection-Accuracy KPIs can be tracked
once analysts review the flags (see note in the .sql file).

In production this script would be scheduled (e.g. cron / Airflow) to run
hourly or daily against newly-loaded transactions, per the brief's
"Automate Detection Using Python" step.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd

from db_utils import get_conn, run_script, export_table, DATA_MART_DIR, REPORTS_DIR


def build_pdf_report(flagged: pd.DataFrame, total_txns: int):
    pdf_path = REPORTS_DIR / "AML_Fraud_Detection_Report.pdf"
    with PdfPages(pdf_path) as pdf:

        # --- Page 1: cover / KPI summary ---
        fig, ax = plt.subplots(figsize=(8.5, 11))
        ax.axis("off")
        flagged_rate = round(100 * len(flagged) / total_txns, 2)
        review_count = int(flagged["requires_analyst_review"].sum()) if "requires_analyst_review" in flagged else (
            (flagged.severity != "Medium").sum()
        )
        lines = [
            "AML Fraud Detection Report",
            "Integrated AML & Transaction Risk Management Platform",
            "",
            f"Total transactions scanned:      {total_txns:,}",
            f"Flagged for the watchlist:       {len(flagged):,}  ({flagged_rate}%)",
            f"  Requiring analyst review:      {review_count:,} (Critical + High severity)",
            f"  Critical severity:             {(flagged.severity == 'Critical').sum():,}",
            f"  High severity:                 {(flagged.severity == 'High').sum():,}",
            f"  Medium severity (monitor only):{(flagged.severity == 'Medium').sum():,}",
            "",
            "Detection rules applied:",
            "  Behavioural score (0-4, one point each):",
            "    R1  Large single transaction (> $9,000)",
            "    R2  High transaction frequency for the customer (>= 4 txns)",
            "    R3  High-risk transaction location (source is_high_risk flag)",
            "    R4  Transacting bank compliance score < 0.6",
            "  Sanctions flag (0-1):",
            "    R5  Customer or transacting bank has sanctions-list history",
            "  fraud_score = behavioural score + sanctions flag  (range 0-5)",
            "",
            "Flag threshold: fraud_score >= 2. Review threshold: fraud_score >= 3.",
            "(Sanctions coverage in this dataset is unusually broad -- ~85% of",
            " transactions touch a sanctioned party -- so it is deliberately",
            " weighted lower than the behavioural signals; see sql/04_fraud_",
            " detection_rules.sql for the full rationale.)",
            "",
            "Note: False Positive Rate and Detection Accuracy require analyst",
            "disposition data not present in the source files. A disposition",
            "log template (reports/fraud_disposition_log_template.csv) is",
            "included so these KPIs can be tracked once reviews are logged.",
        ]
        ax.text(0.05, 0.95, "\n".join(lines), va="top", ha="left", fontsize=11, family="monospace")
        pdf.savefig(fig)
        plt.close(fig)

        # --- Page 2: severity distribution + fraud score histogram ---
        fig, axes = plt.subplots(1, 2, figsize=(11, 6))
        flagged["severity"].value_counts().reindex(["Critical", "High", "Medium", "Low"]).dropna().plot(
            kind="bar", ax=axes[0], color=["#b91c1c", "#ea580c", "#d97706", "#65a30d"][: flagged["severity"].nunique()]
        )
        axes[0].set_title("Flagged Transactions by Severity")
        axes[0].set_xlabel("Severity")
        axes[0].set_ylabel("Count")

        flagged["fraud_score"].value_counts().sort_index().plot(kind="bar", ax=axes[1], color="#1d4ed8")
        axes[1].set_title("Flagged Transactions by Fraud Score")
        axes[1].set_xlabel("Fraud Score (rules triggered)")
        axes[1].set_ylabel("Count")
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        # --- Page 3: amount distribution + top regions ---
        fig, axes = plt.subplots(1, 2, figsize=(11, 6))
        axes[0].hist(flagged["amount"], bins=20, color="#7c3aed")
        axes[0].set_title("Flagged Transaction Amount Distribution")
        axes[0].set_xlabel("Amount (USD)")
        axes[0].set_ylabel("Count")

        flagged["customer_region"].value_counts().plot(kind="bar", ax=axes[1], color="#0891b2")
        axes[1].set_title("Flagged Transactions by Customer Region")
        axes[1].set_xlabel("Region")
        axes[1].set_ylabel("Count")
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        # --- Page 4: top 20 highest-risk flagged transactions table ---
        fig, ax = plt.subplots(figsize=(11, 8.5))
        ax.axis("off")
        top20 = flagged.sort_values(["fraud_score", "amount"], ascending=False).head(20)
        table_cols = ["transaction_id", "customer_name", "bank_name", "amount", "fraud_score", "severity"]
        tbl = ax.table(
            cellText=top20[table_cols].round(2).values,
            colLabels=table_cols,
            loc="center",
            cellLoc="center",
        )
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(8)
        tbl.scale(1, 1.5)
        ax.set_title("Top 20 Highest-Risk Flagged Transactions", pad=20)
        pdf.savefig(fig)
        plt.close(fig)

    print(f"  wrote PDF report -> {pdf_path}")


def main():
    conn = get_conn()
    print("Running sql/04_fraud_detection_rules.sql ...")
    run_script(conn, "04_fraud_detection_rules.sql")

    flagged = export_table(conn, "flagged_transactions")
    total_txns = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    print(f"  exported flagged_transactions {len(flagged):,} rows -> data_marts/flagged_transactions.csv")
    print(f"  flagged rate: {round(100*len(flagged)/total_txns,2)}%  "
          f"(requires analyst review: {int(flagged['requires_analyst_review'].sum())})")

    build_pdf_report(flagged, total_txns)

    # Disposition-log template for analysts to fill in (drives false-positive
    # rate / detection-accuracy KPIs once reviewed)
    disp = flagged[["transaction_id", "customer_id", "bank_id", "amount", "fraud_score", "severity"]].copy()
    disp["reviewed_by"] = ""
    disp["review_date"] = ""
    disp["disposition"] = ""  # analyst fills: Confirmed Fraud / Cleared / Escalated
    disp.to_csv(REPORTS_DIR / "fraud_disposition_log_template.csv", index=False)
    print(f"  wrote disposition log template -> reports/fraud_disposition_log_template.csv")

    conn.close()


if __name__ == "__main__":
    main()
