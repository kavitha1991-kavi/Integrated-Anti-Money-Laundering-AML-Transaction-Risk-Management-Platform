-- ============================================================================
-- Step 1b: DATA CLEANING & QUALITY CHECKS
-- Run AFTER 01_schema.sql and after raw CSVs are loaded into staging tables
-- (raw_customers, raw_banks, raw_transactions, raw_sanctions) with identical
-- columns to the CSVs. The Python loader (01_ingest_and_clean.py) performs
-- the load; these queries are the SQL-side validation/cleaning logic.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1) NULL / MISSING VALUE CHECK -- one row per table x column
-- ----------------------------------------------------------------------------
SELECT 'customers' AS table_name, 'customer_id' AS column_name, COUNT(*) AS null_count FROM raw_customers WHERE customer_id IS NULL
UNION ALL SELECT 'customers','name',        COUNT(*) FROM raw_customers WHERE name        IS NULL OR TRIM(name) = ''
UNION ALL SELECT 'customers','email',       COUNT(*) FROM raw_customers WHERE email       IS NULL OR TRIM(email) = ''
UNION ALL SELECT 'customers','phone',       COUNT(*) FROM raw_customers WHERE phone       IS NULL OR TRIM(phone) = ''
UNION ALL SELECT 'customers','region',      COUNT(*) FROM raw_customers WHERE region      IS NULL OR TRIM(region) = ''
UNION ALL SELECT 'customers','risk_level',  COUNT(*) FROM raw_customers WHERE risk_level  IS NULL OR TRIM(risk_level) = ''
UNION ALL SELECT 'banks','bank_id',         COUNT(*) FROM raw_banks WHERE bank_id IS NULL
UNION ALL SELECT 'banks','name',            COUNT(*) FROM raw_banks WHERE name IS NULL OR TRIM(name) = ''
UNION ALL SELECT 'banks','region',          COUNT(*) FROM raw_banks WHERE region IS NULL OR TRIM(region) = ''
UNION ALL SELECT 'banks','compliance_score',COUNT(*) FROM raw_banks WHERE compliance_score IS NULL
UNION ALL SELECT 'transactions','transaction_id', COUNT(*) FROM raw_transactions WHERE transaction_id IS NULL
UNION ALL SELECT 'transactions','customer_id',     COUNT(*) FROM raw_transactions WHERE customer_id IS NULL
UNION ALL SELECT 'transactions','bank_id',         COUNT(*) FROM raw_transactions WHERE bank_id IS NULL
UNION ALL SELECT 'transactions','amount',          COUNT(*) FROM raw_transactions WHERE amount IS NULL
UNION ALL SELECT 'transactions','date',            COUNT(*) FROM raw_transactions WHERE date IS NULL OR TRIM(date) = ''
UNION ALL SELECT 'sanctions','sanction_id',   COUNT(*) FROM raw_sanctions WHERE sanction_id IS NULL
UNION ALL SELECT 'sanctions','bank_id',       COUNT(*) FROM raw_sanctions WHERE bank_id IS NULL
UNION ALL SELECT 'sanctions','customer_id',   COUNT(*) FROM raw_sanctions WHERE customer_id IS NULL
UNION ALL SELECT 'sanctions','sanction_date', COUNT(*) FROM raw_sanctions WHERE sanction_date IS NULL OR TRIM(sanction_date) = '';

-- ----------------------------------------------------------------------------
-- 2) DEDUPLICATION -- exact duplicate rows and duplicate primary keys
-- ----------------------------------------------------------------------------
-- 2a. Duplicate primary keys (should be zero; if not, keep first occurrence)
SELECT transaction_id, COUNT(*) c FROM raw_transactions GROUP BY transaction_id HAVING c > 1;
SELECT customer_id,    COUNT(*) c FROM raw_customers    GROUP BY customer_id    HAVING c > 1;
SELECT bank_id,        COUNT(*) c FROM raw_banks        GROUP BY bank_id        HAVING c > 1;
SELECT sanction_id,    COUNT(*) c FROM raw_sanctions    GROUP BY sanction_id    HAVING c > 1;

-- 2b. Full-row duplicates (safety net beyond PK dupes)
SELECT customer_id, bank_id, amount, date, location, COUNT(*) AS dup_count
FROM raw_transactions
GROUP BY customer_id, bank_id, amount, date, location
HAVING dup_count > 1;

-- 2c. De-duplicated INSERTs into the clean tables.
--     Parent tables (customers, banks) MUST load before child tables
--     (transactions, sanctions) since foreign keys are enforced.
INSERT INTO customers SELECT DISTINCT customer_id, name, email, phone, region, risk_level FROM raw_customers;
INSERT INTO banks     SELECT DISTINCT bank_id, name, region, compliance_score FROM raw_banks;

-- (keeps the lowest transaction_id per duplicate group)
INSERT INTO transactions (transaction_id, customer_id, bank_id, amount, currency,
                           txn_date, location, is_high_risk, is_valid_bank_id)
SELECT transaction_id, customer_id, bank_id, amount, COALESCE(NULLIF(TRIM(currency),''), 'USD'),
       -- 3) STANDARDIZE DATE FORMAT to YYYY-MM-DD
       CASE
           WHEN date LIKE '____-__-__' THEN date                                   -- already ISO
           WHEN date LIKE '__/__/____' THEN substr(date,7,4)||'-'||substr(date,1,2)||'-'||substr(date,4,2)  -- MM/DD/YYYY
           ELSE date
       END AS txn_date,
       location, is_high_risk, is_valid_bank_id
FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY transaction_id ORDER BY transaction_id) rn
    FROM raw_transactions
    WHERE customer_id IS NOT NULL AND bank_id IS NOT NULL AND amount IS NOT NULL
      AND customer_id IN (SELECT customer_id FROM customers)
      AND bank_id IN (SELECT bank_id FROM banks)
) WHERE rn = 1;

INSERT INTO sanctions
SELECT sanction_id, bank_id, customer_id,
       CASE WHEN sanction_date LIKE '____-__-__' THEN sanction_date ELSE sanction_date END,
       reason, is_valid_bank_id
FROM raw_sanctions
WHERE customer_id IN (SELECT customer_id FROM customers)
  AND bank_id IN (SELECT bank_id FROM banks);

-- ----------------------------------------------------------------------------
-- 4) REFERENTIAL INTEGRITY -- orphan foreign keys (bank/customer not on file)
--    Checked against the RAW staging data (rows failing this check are the
--    ones excluded by the WHERE clause in step 2c above, so the clean
--    `transactions` table is guaranteed orphan-free by construction).
-- ----------------------------------------------------------------------------
SELECT rt.transaction_id, rt.bank_id
FROM raw_transactions rt LEFT JOIN banks b ON rt.bank_id = b.bank_id
WHERE b.bank_id IS NULL;

SELECT rt.transaction_id, rt.customer_id
FROM raw_transactions rt LEFT JOIN customers c ON rt.customer_id = c.customer_id
WHERE c.customer_id IS NULL;

-- ----------------------------------------------------------------------------
-- 5) OUTLIER CHECK on transaction amount (IQR method)
-- ----------------------------------------------------------------------------
WITH q AS (
    SELECT amount,
           NTILE(4) OVER (ORDER BY amount) AS qtile
    FROM transactions
),
bounds AS (
    SELECT
        (SELECT MAX(amount) FROM q WHERE qtile = 1) AS q1,
        (SELECT MIN(amount) FROM q WHERE qtile = 4) AS q3
)
SELECT t.transaction_id, t.amount
FROM transactions t, bounds
WHERE t.amount < bounds.q1 - 1.5 * (bounds.q3 - bounds.q1)
   OR t.amount > bounds.q3 + 1.5 * (bounds.q3 - bounds.q1);

-- ----------------------------------------------------------------------------
-- 6) DATA-QUALITY KPI SUMMARY (feeds the Step-1 "Data Completeness /
--    Consistency / Feature Coverage" KPIs used by the platform)
-- ----------------------------------------------------------------------------
SELECT
    (SELECT COUNT(*) FROM transactions) AS total_transactions,
    ROUND(100.0 * (SELECT COUNT(*) FROM transactions WHERE amount IS NOT NULL AND txn_date IS NOT NULL
                                                        AND customer_id IS NOT NULL AND bank_id IS NOT NULL)
                 / (SELECT COUNT(*) FROM transactions), 2) AS data_completeness_pct,
    ROUND(100.0 * (SELECT COUNT(*) FROM transactions WHERE txn_date LIKE '____-__-__')
                 / (SELECT COUNT(*) FROM transactions), 2) AS date_format_consistency_pct;
