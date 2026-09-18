-- ============================================================================
-- Step 4: CUSTOMER RISK PROFILING AND SEGMENTATION
-- Composite risk score (0-100) blends behavioural signals with the stated
-- risk_level, then buckets customers into Low / Medium / High segments.
-- ============================================================================

DROP TABLE IF EXISTS customer_risk_profiles;
CREATE TABLE customer_risk_profiles AS
WITH scored AS (
    SELECT
        cf.customer_id,
        cf.name,
        cf.region,
        cf.stated_risk_level,
        cf.txn_frequency,
        cf.avg_txn_amount,
        cf.total_txn_amount,
        cf.high_risk_txn_count,
        cf.large_txn_count,
        cf.sanction_count,
        -- Component scores, each normalized to 0-25 points:
        MIN(25, cf.high_risk_txn_count * 10)                                   AS score_high_risk_txns,
        MIN(25, cf.large_txn_count * 12)                                       AS score_large_txns,
        MIN(25, cf.sanction_count * 25)                                        AS score_sanctions,
        CASE cf.stated_risk_level
            WHEN 'High' THEN 25 WHEN 'Medium' THEN 12 ELSE 0
        END                                                                    AS score_stated_level
    FROM customer_features cf
)
SELECT
    *,
    (score_high_risk_txns + score_large_txns + score_sanctions + score_stated_level) AS composite_risk_score,
    CASE
        WHEN (score_high_risk_txns + score_large_txns + score_sanctions + score_stated_level) >= 60 THEN 'High'
        WHEN (score_high_risk_txns + score_large_txns + score_sanctions + score_stated_level) >= 30 THEN 'Medium'
        ELSE 'Low'
    END AS computed_segment
FROM scored;

-- ----------------------------------------------------------------------------
-- Customer-profiling KPIs
-- ----------------------------------------------------------------------------
SELECT
    (SELECT COUNT(*) FROM customer_risk_profiles WHERE computed_segment = 'High') AS high_risk_customer_count,
    ROUND(100.0 * SUM(CASE WHEN computed_segment = stated_risk_level THEN 1 ELSE 0 END)
                 / COUNT(*), 2)                                                    AS segmentation_agreement_pct,
    ROUND(100.0 * SUM(CASE WHEN txn_frequency > 0 THEN 1 ELSE 0 END) / COUNT(*), 2) AS profile_completeness_pct
FROM customer_risk_profiles;
