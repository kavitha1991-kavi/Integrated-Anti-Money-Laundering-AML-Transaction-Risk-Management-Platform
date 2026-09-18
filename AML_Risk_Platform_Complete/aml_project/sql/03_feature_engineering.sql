-- ============================================================================
-- Step 1c: FEATURE ENGINEERING
-- Builds customer-level, bank-level and region-level features on top of the
-- cleaned transactions/customers/banks/sanctions tables.
-- ============================================================================

DROP TABLE IF EXISTS customer_features;
CREATE TABLE customer_features AS
SELECT
    c.customer_id,
    c.name,
    c.region,
    c.risk_level                                             AS stated_risk_level,
    COUNT(t.transaction_id)                                  AS txn_frequency,
    ROUND(AVG(t.amount), 2)                                  AS avg_txn_amount,
    ROUND(COALESCE(SUM(t.amount), 0), 2)                     AS total_txn_amount,
    ROUND(MAX(t.amount), 2)                                  AS max_txn_amount,
    SUM(CASE WHEN t.is_high_risk = 1 THEN 1 ELSE 0 END)      AS high_risk_txn_count,
    SUM(CASE WHEN t.amount > 9000 THEN 1 ELSE 0 END)         AS large_txn_count,          -- near CTR ($10k) threshold
    (SELECT COUNT(*) FROM sanctions s WHERE s.customer_id = c.customer_id) AS sanction_count,
    MIN(t.txn_date)                                          AS first_txn_date,
    MAX(t.txn_date)                                          AS last_txn_date
FROM customers c
LEFT JOIN transactions t ON t.customer_id = c.customer_id
GROUP BY c.customer_id, c.name, c.region, c.risk_level;

-- ----------------------------------------------------------------------------
-- Bank-level features
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS bank_features;
CREATE TABLE bank_features AS
SELECT
    b.bank_id,
    b.name,
    b.region,
    b.compliance_score,
    COUNT(t.transaction_id)                                 AS txn_frequency,
    ROUND(AVG(t.amount), 2)                                 AS avg_txn_amount,
    ROUND(COALESCE(SUM(t.amount), 0), 2)                    AS total_txn_amount,
    SUM(CASE WHEN t.is_high_risk = 1 THEN 1 ELSE 0 END)     AS high_risk_txn_count,
    (SELECT COUNT(*) FROM sanctions s WHERE s.bank_id = b.bank_id)              AS sanctioned_account_count,
    (SELECT COUNT(DISTINCT s.customer_id) FROM sanctions s WHERE s.bank_id = b.bank_id) AS distinct_sanctioned_customers
FROM banks b
LEFT JOIN transactions t ON t.bank_id = b.bank_id
GROUP BY b.bank_id, b.name, b.region, b.compliance_score;

-- ----------------------------------------------------------------------------
-- Region-level rollups (feeds the risk-map dashboard, Step 2)
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS region_features;
CREATE TABLE region_features AS
SELECT
    c.region,
    COUNT(t.transaction_id)                                  AS txn_count,
    ROUND(AVG(t.amount), 2)                                  AS avg_txn_amount,
    SUM(CASE WHEN t.is_high_risk = 1 THEN 1 ELSE 0 END)      AS high_risk_txn_count,
    ROUND(100.0 * SUM(CASE WHEN t.is_high_risk = 1 THEN 1 ELSE 0 END)
                 / NULLIF(COUNT(t.transaction_id), 0), 2)    AS high_risk_txn_pct
FROM customers c
JOIN transactions t ON t.customer_id = c.customer_id
GROUP BY c.region;

-- ----------------------------------------------------------------------------
-- Risk indicator flags at the transaction level (used by fraud rules, Step 3)
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS transaction_flags;
CREATE TABLE transaction_flags AS
SELECT
    t.transaction_id,
    t.customer_id,
    t.bank_id,
    t.amount,
    t.txn_date,
    t.location,
    t.is_high_risk,
    CASE WHEN t.amount > 9000 THEN 1 ELSE 0 END                                  AS flag_large_amount,
    CASE WHEN cf.txn_frequency >= 4 THEN 1 ELSE 0 END                            AS flag_high_frequency_customer,
    CASE WHEN c.risk_level = 'High' THEN 1 ELSE 0 END                            AS flag_high_risk_customer,
    CASE WHEN bf.compliance_score < 0.6 THEN 1 ELSE 0 END                        AS flag_low_compliance_bank,
    CASE WHEN cf.sanction_count > 0 THEN 1 ELSE 0 END                            AS flag_sanctioned_customer,
    CASE WHEN bf.sanctioned_account_count > 0 THEN 1 ELSE 0 END                  AS flag_sanctioned_bank
FROM transactions t
JOIN customers c        ON c.customer_id = t.customer_id
JOIN customer_features cf ON cf.customer_id = t.customer_id
JOIN bank_features bf     ON bf.bank_id = t.bank_id;

-- ----------------------------------------------------------------------------
-- Feature-coverage KPI: % of customers with a fully populated feature set
-- ----------------------------------------------------------------------------
SELECT
    ROUND(100.0 * SUM(CASE WHEN txn_frequency > 0 THEN 1 ELSE 0 END) / COUNT(*), 2) AS feature_coverage_pct
FROM customer_features;
