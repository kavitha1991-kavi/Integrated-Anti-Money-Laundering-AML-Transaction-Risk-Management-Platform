# Integrated-Anti-Money-Laundering-AML-Transaction-Risk-Management-Platform

The main objectives of this project are:
Integrate customer, bank, transaction, and sanctions data into a structured analytical platform.
Validate and clean the source data before analysis.
Perform feature engineering at transaction, customer, bank, and regional levels.
Develop rule-based transaction fraud and risk detection.
Create customer risk scores and risk segments.
Monitor bank compliance scores and sanctions information.
Calculate composite bank risk scores.
Generate KPIs and threshold-based alerts.
Build an interactive dashboard for monitoring AML and transaction risk.
Produce analytical outputs that can be imported into Power BI or Tableau.
Technologies and Tools Used
Programming & Data Analysis
Python
Pandas – data cleaning, transformation, aggregation, and feature engineering
Matplotlib – report visualizations
SQLite3 – database connectivity and processing
SMTP / smtplib – email alert integration
Database & SQL
SQL
SQLite
Primary Keys
Foreign Keys
Indexes
Data validation
Aggregations
Feature engineering
Analytical queries

The SQL scripts are written using portable SQL so that the database layer can be migrated to systems such as PostgreSQL or MySQL with minimal changes.

Dashboard & Visualization
HTML
CSS
JavaScript
Chart.js
Interactive tables
CSV data marts
Power BI / Tableau-ready outputs

The project includes a self-contained dashboard.html that can be opened directly in a browser without requiring a server or external runtime dependency.

Key Features and Functionalities
1. Data Integration and Data Quality

The platform loads four CSV datasets into SQL staging tables and performs data-quality checks.

The validation process includes:

Missing-value checks
Duplicate detection
Primary-key validation
Business-key validation
Date-format standardization
Referential-integrity checks
Foreign-key validation
IQR-based transaction outlier detection

The supplied datasets achieved:

100% data completeness
100% date consistency
0 duplicate keys
0 orphaned foreign keys
0 IQR transaction outliers

Feature engineering then creates customer-level, bank-level, region-level, and transaction-level analytical datasets.

2. Transaction Risk Monitoring

The platform monitors transaction risk using transaction-level and regional information.

Because the source data does not contain latitude and longitude, geographic analysis is performed using four available regions:

North
South
East
West

Each region is analyzed using:

Transaction count
Average transaction amount
Percentage of high-risk transactions

The regional analysis provides a practical alternative to a geographic map using the data available in the source datasets.

3. Rule-Based Fraud Detection

A rule-based fraud detection framework was developed to identify potentially suspicious transactions.

The candidate rules include:

Large single transactions
High transaction frequency
High-risk transaction locations
Low bank compliance scores
Customer sanctions history
Bank sanctions history

The final fraud score separates transactional behavior from the sanctions flag.

The behavioural score ranges from 0–4, while the sanctions flag contributes 0 or 1 additional point, producing a total fraud score between 0 and 5.

Risk thresholds
Fraud Score	Action
>= 2	Watchlist
>= 3	Analyst Review

Results from the supplied dataset:

600 of 1,000 transactions (60%) were flagged for the watchlist.
146 transactions (14.6%) required analyst review.
14 were classified as Critical.
132 were classified as High.
4. Customer Risk Profiling

The platform calculates a composite customer risk score on a 0–100 scale.

The score incorporates:

High-risk transaction count
Large-transaction count
Sanctions count
Stated customer risk level

Customers are then assigned to:

Low
Medium
High

The computed risk segment is compared with the customer's stated risk level as a sense-check rather than treating the stated level as ground truth.

Key result:

101 customers were classified as high risk.
Segmentation agreement with the stated risk level was 57.6%.
Profile completeness was 64%.
5. Compliance and Sanctions Monitoring

The platform combines bank compliance scores with sanctions information.

Each bank is analyzed using:

Compliance score
Number of sanctioned accounts
Sanctions reason
Sanctions history

Compliance is classified into:

Adequate
Watch
Below Threshold

Key results:

1,000 sanctioned accounts
Average bank compliance score: 0.751
199 of 1,010 banks (19.7%) were below the 0.60 compliance threshold.
6. Bank Risk Analysis

A composite bank risk score from 0–100 is calculated using:

Inverse compliance score
Sanctioned-account count
High-risk transaction share

This allows banks to be analyzed based on multiple risk indicators rather than a single metric.

Key results:

113 of 1,010 banks (11.2%) had a risk score of 50 or higher.
Average bank risk score: 29.17
The highest score in the supplied dataset was 78.4, shared by Bank 508 and Bank 651.
7. KPI Reporting and Alerts

The platform combines outputs from the different analytical modules into a unified reporting layer.

It generates:

KPI summary
Fraud alerts
Compliance alerts
Timestamped alert logs

Two threshold-based alert categories are generated:

Critical-severity fraud alerts
Banks below the compliance threshold

Email alerting is implemented using Python's smtplib. SMTP credentials can be supplied to enable live email notifications; otherwise, the system records the alert that would have been sent.

Interactive Dashboard

The project includes a self-contained interactive dashboard:

dashboard.html

The dashboard contains six main views:

Overview
Risk Monitoring
Fraud Detection
Customer Profiling
Compliance & Sanctions
Bank Comparison

Dashboard tables support:

Search
Filtering
Column sorting

The dashboard provides a centralized view of AML KPIs, active alerts, fraud risk, customer risk, compliance information, and bank risk.

My Role and Contributions

I worked on the project across the complete data analytics and risk-management workflow.

Data Engineering & Data Preparation
Integrated customer, bank, transaction, and sanctions datasets.
Loaded raw CSV files into SQLite staging tables.
Performed data-quality validation and cleaning.
Checked missing values, duplicates, date formats, and referential integrity.
Performed transaction outlier analysis using the IQR method.
SQL Development
Designed the relational database structure.
Implemented primary keys, foreign keys, and indexes.
Developed SQL queries for data cleaning and feature engineering.
Created analytical tables and data marts.
Designed SQL logic for fraud detection, customer profiling, compliance analysis, and bank risk analysis.
Python Development
Used Pandas for data processing and transformation.
Built the end-to-end pipeline.
Implemented transaction risk and fraud-scoring logic.
Developed customer and bank risk calculations.
Generated KPI summaries and analytical outputs.
Created the PDF fraud detection report.
Implemented SMTP-based alerting functionality.
Dashboard & Reporting
Developed the interactive HTML dashboard.
Created visualizations for AML and transaction-risk KPIs.
Added searchable, filterable, and sortable analytical tables.
Generated CSV data marts suitable for Power BI and Tableau.
Produced the final fraud detection report and alert logs.

The project structure and deliverables include the pipeline, SQL scripts, Python modules, SQLite database, data marts, reports, alert logs, and dashboard
