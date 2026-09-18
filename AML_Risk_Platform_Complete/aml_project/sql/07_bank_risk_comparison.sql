-- ============================================================================
-- Step 6: BANK RISK COMPARISON AND ANALYSIS
-- ============================================================================

DROP TABLE IF EXISTS bank_risk_comparison;
CREATE TABLE bank_risk_comparison AS
SELECT
    bf.bank_id,
    bf.name,
    bf.region,
    bf.compliance_score,
    bf.txn_frequency,
    bf.avg_txn_amount,
    bf.total_txn_amount,
    bf.high_risk_txn_count,
    ROUND(100.0 * bf.high_risk_txn_count / NULLIF(bf.txn_frequency,0), 2) AS high_risk_txn_pct,
    bf.sanctioned_account_count,
    -- Composite bank risk score (0-100): inverse compliance + sanctions + high-risk txn share
    ROUND(
        (1 - bf.compliance_score) * 40
        + MIN(30, bf.sanctioned_account_count * 10)
        + MIN(30, COALESCE(100.0 * bf.high_risk_txn_count / NULLIF(bf.txn_frequency,0), 0) * 0.3)
    , 1) AS bank_risk_score
FROM bank_features bf;

DROP TABLE IF EXISTS bank_risk_comparison_ranked;
CREATE TABLE bank_risk_comparison_ranked AS
SELECT *,
       RANK() OVER (ORDER BY bank_risk_score DESC) AS risk_rank
FROM bank_risk_comparison;

-- ----------------------------------------------------------------------------
-- Bank-comparison KPIs
-- ----------------------------------------------------------------------------
SELECT
    (SELECT COUNT(*) FROM bank_risk_comparison WHERE bank_risk_score >= 50)      AS high_risk_bank_count,
    ROUND(AVG(bank_risk_score), 2)                                                AS avg_bank_risk_score,
    (SELECT bank_id FROM bank_risk_comparison ORDER BY bank_risk_score DESC LIMIT 1) AS riskiest_bank_id
FROM bank_risk_comparison;

-- Top 10 riskiest banks (for the comparison dashboard bar/bubble chart)
SELECT bank_id, name, region, compliance_score, sanctioned_account_count,
       high_risk_txn_pct, bank_risk_score, risk_rank
FROM bank_risk_comparison_ranked
ORDER BY risk_rank
LIMIT 10;
