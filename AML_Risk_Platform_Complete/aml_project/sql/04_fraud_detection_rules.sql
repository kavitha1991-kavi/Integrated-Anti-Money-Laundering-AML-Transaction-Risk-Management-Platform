-- ============================================================================
-- Step 3: RULE-BASED FRAUD DETECTION SYSTEM
-- Two-tier rule design (standard AML practice: transactional behaviour is
-- scored separately from watchlist/sanctions status, which is a hard
-- compliance signal rather than just "one more point"):
--
--   BEHAVIOURAL SCORE (0-4) -- one point each:
--     R1 Large single transaction (> $9,000, just under the $10k CTR
--        threshold, a classic proxy for potential "structuring")
--     R2 Unusually high transaction frequency for that customer (>=4 txns)
--     R3 Cross-border / high-risk transaction location (source is_high_risk)
--     R4 Transacting bank's compliance score is below the 0.6 threshold
--
--   SANCTIONS FLAG (0-1):
--     R5 Customer or transacting bank has ANY sanctions-list history
--        (Fraud / Money Laundering / Compliance Violation)
--
--   fraud_score = behavioural_score + sanctions_flag   (range 0-5)
--
-- NOTE ON THIS DATASET: the supplied sanctions.csv covers an unusually large
-- share of the customer/bank population (~85% of transactions touch a
-- sanctioned customer or bank), far denser than a real-world watchlist. That
-- alone would make sanctions history a near-useless discriminator if it were
-- weighted equally with the other rules (an earlier version of this script
-- did this) -- it would flag ~74% of all transactions. Down-weighting it to
-- a single point, and requiring it to combine with genuine behavioural
-- signals to raise severity, keeps the rule engine meaningful on this data,
-- and the same logic scales correctly to production data where sanctions
-- coverage is sparse.
-- ============================================================================

DROP TABLE IF EXISTS flagged_transactions;
CREATE TABLE flagged_transactions AS
SELECT
    t.transaction_id,
    t.customer_id,
    c.name           AS customer_name,
    c.region          AS customer_region,
    c.risk_level      AS customer_stated_risk,
    t.bank_id,
    bk.name           AS bank_name,
    bk.compliance_score,
    t.amount,
    t.txn_date,
    t.location,
    tf.flag_large_amount,
    tf.flag_high_frequency_customer,
    t.is_high_risk                                                        AS flag_high_risk_location,
    tf.flag_low_compliance_bank,
    (CASE WHEN tf.flag_sanctioned_customer = 1 OR tf.flag_sanctioned_bank = 1 THEN 1 ELSE 0 END) AS sanctions_flag,
    (tf.flag_large_amount + tf.flag_high_frequency_customer + t.is_high_risk + tf.flag_low_compliance_bank) AS behavioural_score,
    (tf.flag_large_amount + tf.flag_high_frequency_customer + t.is_high_risk + tf.flag_low_compliance_bank
     + CASE WHEN tf.flag_sanctioned_customer = 1 OR tf.flag_sanctioned_bank = 1 THEN 1 ELSE 0 END) AS fraud_score,
    CASE
        WHEN (tf.flag_large_amount + tf.flag_high_frequency_customer + t.is_high_risk + tf.flag_low_compliance_bank
              + CASE WHEN tf.flag_sanctioned_customer = 1 OR tf.flag_sanctioned_bank = 1 THEN 1 ELSE 0 END) >= 4 THEN 'Critical'
        WHEN (tf.flag_large_amount + tf.flag_high_frequency_customer + t.is_high_risk + tf.flag_low_compliance_bank
              + CASE WHEN tf.flag_sanctioned_customer = 1 OR tf.flag_sanctioned_bank = 1 THEN 1 ELSE 0 END) = 3 THEN 'High'
        ELSE 'Medium'
    END AS severity,
    (tf.flag_large_amount + tf.flag_high_frequency_customer + t.is_high_risk + tf.flag_low_compliance_bank
     + CASE WHEN tf.flag_sanctioned_customer = 1 OR tf.flag_sanctioned_bank = 1 THEN 1 ELSE 0 END) >= 3 AS requires_analyst_review
FROM transactions t
JOIN transaction_flags tf ON tf.transaction_id = t.transaction_id
JOIN customers c ON c.customer_id = t.customer_id
JOIN banks bk    ON bk.bank_id = t.bank_id
WHERE (tf.flag_large_amount + tf.flag_high_frequency_customer + t.is_high_risk + tf.flag_low_compliance_bank
       + CASE WHEN tf.flag_sanctioned_customer = 1 OR tf.flag_sanctioned_bank = 1 THEN 1 ELSE 0 END) >= 2   -- flag threshold
ORDER BY fraud_score DESC, t.amount DESC;

-- ----------------------------------------------------------------------------
-- Fraud-detection KPIs
-- ----------------------------------------------------------------------------
SELECT
    (SELECT COUNT(*) FROM flagged_transactions)                                    AS flagged_transaction_count,
    (SELECT COUNT(*) FROM transactions)                                            AS total_transactions,
    ROUND(100.0 * (SELECT COUNT(*) FROM flagged_transactions) /
                  (SELECT COUNT(*) FROM transactions), 2)                          AS flagged_rate_pct,
    (SELECT COUNT(*) FROM flagged_transactions WHERE requires_analyst_review)      AS requires_review_count,
    (SELECT COUNT(*) FROM flagged_transactions WHERE severity = 'Critical')        AS critical_count,
    (SELECT COUNT(*) FROM flagged_transactions WHERE severity = 'High')            AS high_count,
    (SELECT COUNT(*) FROM flagged_transactions WHERE severity = 'Medium')          AS medium_count;

-- Note on "False Positive Rate" / "Detection Accuracy" KPIs required by the
-- brief: this dataset has no analyst-reviewed ground-truth outcome column
-- (e.g. confirmed_fraud Y/N), so these two KPIs cannot be computed from data
-- alone. The pipeline outputs `flagged_transactions` with a `severity` band
-- and a `requires_analyst_review` flag so compliance officers can
-- review/disposition each case; once a disposition column is captured (see
-- reports/fraud_disposition_log_template.csv produced by the Python
-- pipeline) both KPIs become simple ratios:
--   false_positive_rate = cleared_on_review / flagged_transaction_count
--   detection_accuracy  = confirmed_fraud    / flagged_transaction_count
