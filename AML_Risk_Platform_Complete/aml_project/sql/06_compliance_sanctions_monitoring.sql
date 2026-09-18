-- ============================================================================
-- Step 5: COMPLIANCE AND SANCTIONS MONITORING
-- ============================================================================

DROP TABLE IF EXISTS bank_compliance_profiles;
CREATE TABLE bank_compliance_profiles AS
SELECT
    b.bank_id,
    b.name,
    b.region,
    b.compliance_score,
    COUNT(s.sanction_id)                                              AS sanctioned_account_count,
    SUM(CASE WHEN s.reason = 'Money Laundering'      THEN 1 ELSE 0 END) AS ml_sanction_count,
    SUM(CASE WHEN s.reason = 'Fraud'                 THEN 1 ELSE 0 END) AS fraud_sanction_count,
    SUM(CASE WHEN s.reason = 'Compliance Violation'  THEN 1 ELSE 0 END) AS compliance_violation_count,
    CASE WHEN b.compliance_score < 0.6 THEN 'Below Threshold'
         WHEN b.compliance_score < 0.75 THEN 'Watch'
         ELSE 'Adequate'
    END AS compliance_status
FROM banks b
LEFT JOIN sanctions s ON s.bank_id = b.bank_id
GROUP BY b.bank_id, b.name, b.region, b.compliance_score;

-- ----------------------------------------------------------------------------
-- Compliance-monitoring KPIs
-- ----------------------------------------------------------------------------
SELECT
    SUM(sanctioned_account_count)                                                     AS total_sanctioned_accounts,
    ROUND(AVG(compliance_score), 3)                                                    AS avg_compliance_score,
    ROUND(100.0 * SUM(CASE WHEN compliance_status = 'Below Threshold' THEN 1 ELSE 0 END)
                 / COUNT(*), 2)                                                        AS compliance_gap_pct
FROM bank_compliance_profiles;

-- Region-level compliance rollup (feeds the compliance dashboard map)
SELECT
    region,
    COUNT(*)                                    AS bank_count,
    ROUND(AVG(compliance_score), 3)             AS avg_compliance_score,
    SUM(sanctioned_account_count)               AS total_sanctioned_accounts,
    SUM(CASE WHEN compliance_status = 'Below Threshold' THEN 1 ELSE 0 END) AS banks_below_threshold
FROM bank_compliance_profiles
GROUP BY region
ORDER BY avg_compliance_score ASC;
