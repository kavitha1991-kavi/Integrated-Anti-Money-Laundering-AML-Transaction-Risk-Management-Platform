# Integrated AML & Transaction Risk Management Platform

A complete, runnable implementation of the brief: data integration and
cleaning, feature engineering, a rule-based fraud detection engine,
customer risk profiling, compliance/sanctions monitoring, bank risk
comparison, and a unified dashboard — built with SQL, Python, and a
self-contained interactive HTML dashboard.

## Quick start

```bash
cd python
python3 run_pipeline.py                 # uses ../raw_data/*.csv by default
# or point it at a different folder of the same 4 source CSVs:
python3 run_pipeline.py /path/to/csv/folder
```

This single command:
1. loads the 4 source CSVs into a SQLite database (`aml_platform.db`)
2. cleans, deduplicates, and standardizes them (`sql/01`–`02`)
3. builds customer/bank/region features and risk flags (`sql/03`)
4. runs the rule-based fraud detection engine (`sql/04`)
5. computes customer risk profiles & segments (`sql/05`)
6. computes bank compliance profiles (`sql/06`)
7. ranks banks by composite risk (`sql/07`)
8. writes a unified KPI summary and generates threshold alerts
9. rebuilds `dashboard.html`, the interactive front-end

**Open `dashboard.html` directly in any browser** — it's a single file with
no server and no internet connection required (Chart.js is bundled inline).

**Open `reports/AML_Fraud_Detection_Report.pdf`** for the print-ready fraud
summary that would go to an AML team.

## Requirements

Python 3.9+, `pandas`, `matplotlib`, and (only if you need to rebuild the
dashboard's bundled Chart.js from scratch) `npm`. Everything else is
standard library (`sqlite3`, `smtplib`, `json`).

## Folder structure

```
sql/                          Portable ANSI SQL, organized by project step
  01_schema.sql                 table DDL, PKs, FKs, indexes
  02_data_cleaning.sql           null/dup checks, dedup, date standardization
  03_feature_engineering.sql     customer/bank/region features, risk flags
  04_fraud_detection_rules.sql   the rule engine (see below)
  05_customer_risk_profiling.sql composite risk score + segmentation
  06_compliance_sanctions_monitoring.sql
  07_bank_risk_comparison.sql

python/                       ETL + analysis, one script per project step
  db_utils.py                    shared SQLite connection/export helpers
  01_ingest_and_clean.py .. 07_unified_kpis_and_alerts.py
  08_build_dashboard_data.py     bundles data marts into dashboard_data.json
  09_build_dashboard.py          assembles dashboard.html
  run_pipeline.py                runs everything, in order

raw_data/                     the 4 source CSVs (customers, banks,
                               transactions, sanctions) -- pipeline input

data_marts/                   pipeline OUTPUT: every intermediate and final
                               table as CSV, ready to import into Power BI /
                               Tableau / Excel if you have them, plus
                               kpi_summary.csv/json and dashboard_data.json

reports/                      AML_Fraud_Detection_Report.pdf, the analyst
                               disposition-log template, and alerts_log.csv

aml_platform.db               the SQLite database (browse with any SQLite
                               client, e.g. DB Browser for SQLite, if you
                               want to run your own ad-hoc queries)

dashboard.html                 the unified dashboard (open this)
dashboard_template.html /
dashboard.js                   dashboard source (edit these, then run
                                python/09_build_dashboard.py to rebuild)
```

## Design notes & judgment calls

**Why SQLite, not Power BI/Tableau/a live SQL server.** The brief calls for
Python + SQL + Power BI/Tableau, but none of those (a licensed BI tool or a
running database server) are available in this environment. SQLite gives a
real, runnable SQL layer with proper PKs/FKs/indexes; every `.sql` file is
portable ANSI SQL, callable against Postgres/MySQL with the small changes
noted at the bottom of `01_schema.sql`. In place of Power BI/Tableau, every
step's output is exported as a clean CSV data mart under `data_marts/` —
point Power BI or Tableau's "Get Data > CSV/Folder" at that folder and the
visuals in the brief (map, filters, conditional formatting) can be rebuilt
there directly. The bundled `dashboard.html` is a working substitute in the
meantime: six linked views, live filters, sortable tables, and
severity/compliance color-coding, matching the brief's Steps 2 and 4–7.

**Why the fraud rules are weighted the way they are.** The supplied
`sanctions.csv` covers an unusually large share of the customer/bank
population (~85% of transactions touch a sanctioned party) — much denser
than any real-world watchlist. An equally-weighted 6-rule score (an earlier
draft) flagged 74% of all transactions, which isn't useful for an AML team.
The engine instead scores transactional behaviour (large amount, high
frequency, high-risk location, low bank compliance) as one 0–4 tier, and
sanctions history as a separate, lower-weighted flag — standard AML
practice, since a watchlist hit is normally a hard compliance control, not
just one more point in a blended score. This drops the actionable "requires
analyst review" rate to a realistic 14.6%. Full rationale is documented in
`sql/04_fraud_detection_rules.sql`.

**KPIs that can't be computed from this data.** False Positive Rate and
Detection Accuracy need an analyst's confirmed/cleared disposition per
flagged transaction, which doesn't exist in the source files. Rather than
fabricate a number, the pipeline outputs
`reports/fraud_disposition_log_template.csv` — once compliance staff log
outcomes there, both KPIs become a one-line ratio. Alert Timeliness has the
same gap (no incident-response timestamp in the source data); the alerting
step (`07_unified_kpis_and_alerts.py`) writes `reports/alerts_log.csv` with
a timestamp per alert going forward, which is what that KPI would be
measured against.

**Email alerts are stubbed, not faked.** `send_email_alert()` in
`07_unified_kpis_and_alerts.py` is a real `smtplib` implementation — pass it
SMTP credentials and it sends. With none configured (none exist in this
environment) it logs what it would have sent to `reports/alerts_log.csv`
instead of silently pretending to succeed.

## Re-running with your own data

Drop replacement `customers_.csv`, `banks.csv`, `transactions.csv`,
`sanctions.csv` (same column names as documented in
`Meta_Data_for_AML.xlsx`) into a folder and run
`python3 run_pipeline.py /path/to/that/folder`. Everything downstream
(features, fraud flags, profiles, dashboard) regenerates automatically.
