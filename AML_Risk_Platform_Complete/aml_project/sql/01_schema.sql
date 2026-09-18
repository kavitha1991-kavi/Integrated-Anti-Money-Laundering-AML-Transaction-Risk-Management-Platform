-- ============================================================================
-- Step 1a: SCHEMA CREATION
-- Integrated AML & Transaction Risk Management Platform
-- Engine: written for SQLite (used to run this project end-to-end locally).
--         Portable to PostgreSQL/MySQL with trivial changes (see notes).
-- ============================================================================

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS sanctions;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS banks;

-- ----------------------------------------------------------------------------
-- CUSTOMERS  (Primary Key: customer_id)
-- ----------------------------------------------------------------------------
CREATE TABLE customers (
    customer_id   INTEGER PRIMARY KEY,
    name          TEXT NOT NULL,
    email         TEXT,
    phone         TEXT,
    region        TEXT NOT NULL,             -- North / South / East / West
    risk_level    TEXT NOT NULL               -- Low / Medium / High (stated risk)
        CHECK (risk_level IN ('Low','Medium','High'))
);

-- ----------------------------------------------------------------------------
-- BANKS  (Primary Key: bank_id)
-- ----------------------------------------------------------------------------
CREATE TABLE banks (
    bank_id            INTEGER PRIMARY KEY,
    name               TEXT NOT NULL,
    region             TEXT NOT NULL,
    compliance_score   REAL NOT NULL           -- 0.5 - 1.0 scale
        CHECK (compliance_score BETWEEN 0 AND 1)
);

-- ----------------------------------------------------------------------------
-- TRANSACTIONS (Primary Key: transaction_id; FKs -> customers, banks)
-- ----------------------------------------------------------------------------
CREATE TABLE transactions (
    transaction_id   INTEGER PRIMARY KEY,
    customer_id      INTEGER NOT NULL,
    bank_id          INTEGER NOT NULL,
    amount           REAL NOT NULL CHECK (amount >= 0),
    currency         TEXT NOT NULL DEFAULT 'USD',
    txn_date         TEXT NOT NULL,            -- standardized YYYY-MM-DD
    location         TEXT,
    is_high_risk     INTEGER NOT NULL DEFAULT 0,   -- 0/1 (source-provided flag)
    is_valid_bank_id INTEGER NOT NULL DEFAULT 1,   -- 0/1 referential-integrity flag
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (bank_id)     REFERENCES banks(bank_id)
);

CREATE INDEX idx_txn_customer ON transactions(customer_id);
CREATE INDEX idx_txn_bank     ON transactions(bank_id);
CREATE INDEX idx_txn_date     ON transactions(txn_date);
CREATE INDEX idx_txn_amount   ON transactions(amount);

-- ----------------------------------------------------------------------------
-- SANCTIONS (Primary Key: sanction_id; FKs -> banks, customers)
-- ----------------------------------------------------------------------------
CREATE TABLE sanctions (
    sanction_id       INTEGER PRIMARY KEY,
    bank_id           INTEGER NOT NULL,
    customer_id       INTEGER NOT NULL,
    sanction_date     TEXT NOT NULL,           -- standardized YYYY-MM-DD
    reason            TEXT NOT NULL,           -- Fraud / Money Laundering / Compliance Violation
    is_valid_bank_id  INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (bank_id)     REFERENCES banks(bank_id),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE INDEX idx_sanctions_bank     ON sanctions(bank_id);
CREATE INDEX idx_sanctions_customer ON sanctions(customer_id);

-- Notes for Postgres/MySQL portability:
--   * INTEGER PRIMARY KEY (SQLite rowid alias) -> use SERIAL/AUTO_INCREMENT if
--     you want DB-generated IDs; here IDs are supplied by the source files.
--   * BOOLEAN: SQLite has no native BOOLEAN type, so is_high_risk /
--     is_valid_bank_id are stored as INTEGER 0/1. In Postgres use BOOLEAN;
--     in MySQL use TINYINT(1).
