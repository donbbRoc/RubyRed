#!/usr/bin/env python3
"""
Standalone script to create 10 banking tables in DB2 for IBM i under library TUNERLIB1.
Usage: python3 banking_sql_queries.py
"""

import sys

try:
    import ibm_db
except ImportError:
    print("ERROR: ibm_db module not found. Install it with: pip3 install ibm_db")
    sys.exit(1)

SCHEMA = "TUNERLIB1"
DB_CONN_STRING = "*LOCAL"
DB_USER = "adubey"
DB_PASSWORD = "adubey"

# =============================================================================
# Table 1: CUSTOMERS
# =============================================================================
create_customers_table = f'''CREATE TABLE {SCHEMA}.CUSTOMERS (
    ID BIGINT NOT NULL GENERATED ALWAYS AS IDENTITY (START WITH 1, INCREMENT BY 1),
    FIRST_NAME VARCHAR(100) NOT NULL,
    LAST_NAME VARCHAR(100) NOT NULL,
    EMAIL VARCHAR(255),
    PHONE VARCHAR(20),
    DATE_OF_BIRTH DATE,
    ADDRESS VARCHAR(500),
    CITY VARCHAR(100),
    STATE VARCHAR(50),
    POSTAL_CODE VARCHAR(20),
    COUNTRY VARCHAR(50) DEFAULT 'US',
    STATUS VARCHAR(20) DEFAULT 'ACTIVE',
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UPDATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ID)
)'''

# =============================================================================
# Table 2: ACCOUNTS (with indexes and constraints)
# =============================================================================
create_accounts_table = f'''CREATE TABLE {SCHEMA}.ACCOUNTS (
    ID BIGINT NOT NULL GENERATED ALWAYS AS IDENTITY (START WITH 1, INCREMENT BY 1),
    ACCOUNT_NUMBER VARCHAR(20) NOT NULL,
    CUSTOMER_ID BIGINT NOT NULL,
    ACCOUNT_TYPE VARCHAR(20) NOT NULL,
    BALANCE DECIMAL(15, 2) DEFAULT 0.00,
    CURRENCY VARCHAR(3) DEFAULT 'USD',
    STATUS VARCHAR(20) DEFAULT 'ACTIVE',
    OPENED_DATE TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CLOSED_DATE TIMESTAMP,
    PRIMARY KEY (ID),
    CONSTRAINT FK_ACCT_CUST FOREIGN KEY (CUSTOMER_ID)
        REFERENCES {SCHEMA}.CUSTOMERS (ID)
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT UQ_ACCT_NUM UNIQUE (ACCOUNT_NUMBER)
)'''

create_accounts_idx_customer = f'''CREATE INDEX IDX_ACCT_CUST ON {SCHEMA}.ACCOUNTS (CUSTOMER_ID)'''

create_accounts_idx_type = f'''CREATE INDEX IDX_ACCT_TYPE ON {SCHEMA}.ACCOUNTS (ACCOUNT_TYPE, STATUS)'''

# =============================================================================
# Table 3: TRANSACTIONS (with indexes and constraints)
# =============================================================================
create_transactions_table = f'''CREATE TABLE {SCHEMA}.TRANSACTIONS (
    ID BIGINT NOT NULL GENERATED ALWAYS AS IDENTITY (START WITH 1, INCREMENT BY 1),
    ACCOUNT_ID BIGINT NOT NULL,
    TRANSACTION_TYPE VARCHAR(20) NOT NULL,
    AMOUNT DECIMAL(15, 2) NOT NULL,
    CURRENCY VARCHAR(3) DEFAULT 'USD',
    DESCRIPTION VARCHAR(500),
    REFERENCE_NUMBER VARCHAR(50),
    STATUS VARCHAR(20) DEFAULT 'COMPLETED',
    TRANSACTION_DATE TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ID),
    CONSTRAINT FK_TXN_ACCT FOREIGN KEY (ACCOUNT_ID)
        REFERENCES {SCHEMA}.ACCOUNTS (ID)
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)'''

create_transactions_idx_account = f'''CREATE INDEX IDX_TXN_ACCT ON {SCHEMA}.TRANSACTIONS (ACCOUNT_ID)'''

create_transactions_idx_date = f'''CREATE INDEX IDX_TXN_DATE ON {SCHEMA}.TRANSACTIONS (TRANSACTION_DATE)'''

create_transactions_idx_ref = f'''CREATE UNIQUE INDEX IDX_TXN_REF ON {SCHEMA}.TRANSACTIONS (REFERENCE_NUMBER)'''

# =============================================================================
# Table 4: BRANCHES
# =============================================================================
create_branches_table = f'''CREATE TABLE {SCHEMA}.BRANCHES (
    ID BIGINT NOT NULL GENERATED ALWAYS AS IDENTITY (START WITH 1, INCREMENT BY 1),
    BRANCH_CODE VARCHAR(10) NOT NULL,
    BRANCH_NAME VARCHAR(200) NOT NULL,
    ADDRESS VARCHAR(500),
    CITY VARCHAR(100),
    STATE VARCHAR(50),
    POSTAL_CODE VARCHAR(20),
    PHONE VARCHAR(20),
    MANAGER_NAME VARCHAR(200),
    STATUS VARCHAR(20) DEFAULT 'ACTIVE',
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ID)
)'''

# =============================================================================
# Table 5: EMPLOYEES
# =============================================================================
create_employees_table = f'''CREATE TABLE {SCHEMA}.EMPLOYEES (
    ID BIGINT NOT NULL GENERATED ALWAYS AS IDENTITY (START WITH 1, INCREMENT BY 1),
    EMPLOYEE_NUMBER VARCHAR(20) NOT NULL,
    FIRST_NAME VARCHAR(100) NOT NULL,
    LAST_NAME VARCHAR(100) NOT NULL,
    EMAIL VARCHAR(255),
    PHONE VARCHAR(20),
    BRANCH_ID BIGINT,
    DESIGNATION VARCHAR(100),
    HIRE_DATE DATE,
    STATUS VARCHAR(20) DEFAULT 'ACTIVE',
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ID)
)'''

# =============================================================================
# Table 6: LOANS (with indexes and constraints)
# =============================================================================
create_loans_table = f'''CREATE TABLE {SCHEMA}.LOANS (
    ID BIGINT NOT NULL GENERATED ALWAYS AS IDENTITY (START WITH 1, INCREMENT BY 1),
    LOAN_NUMBER VARCHAR(20) NOT NULL,
    CUSTOMER_ID BIGINT NOT NULL,
    ACCOUNT_ID BIGINT NOT NULL,
    LOAN_TYPE VARCHAR(30) NOT NULL,
    PRINCIPAL_AMOUNT DECIMAL(15, 2) NOT NULL,
    INTEREST_RATE DECIMAL(5, 2) NOT NULL,
    TERM_MONTHS INTEGER NOT NULL,
    MONTHLY_PAYMENT DECIMAL(15, 2),
    OUTSTANDING_BALANCE DECIMAL(15, 2),
    STATUS VARCHAR(20) DEFAULT 'ACTIVE',
    DISBURSEMENT_DATE TIMESTAMP,
    MATURITY_DATE TIMESTAMP,
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ID),
    CONSTRAINT FK_LOAN_CUST FOREIGN KEY (CUSTOMER_ID)
        REFERENCES {SCHEMA}.CUSTOMERS (ID)
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT FK_LOAN_ACCT FOREIGN KEY (ACCOUNT_ID)
        REFERENCES {SCHEMA}.ACCOUNTS (ID)
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT UQ_LOAN_NUM UNIQUE (LOAN_NUMBER)
)'''

create_loans_idx_customer = f'''CREATE INDEX IDX_LOAN_CUST ON {SCHEMA}.LOANS (CUSTOMER_ID)'''

create_loans_idx_status = f'''CREATE INDEX IDX_LOAN_STATUS ON {SCHEMA}.LOANS (STATUS, LOAN_TYPE)'''

# =============================================================================
# Table 7: LOAN_PAYMENTS
# =============================================================================
create_loan_payments_table = f'''CREATE TABLE {SCHEMA}.LOAN_PAYMENTS (
    ID BIGINT NOT NULL GENERATED ALWAYS AS IDENTITY (START WITH 1, INCREMENT BY 1),
    LOAN_ID BIGINT NOT NULL,
    PAYMENT_AMOUNT DECIMAL(15, 2) NOT NULL,
    PRINCIPAL_PORTION DECIMAL(15, 2),
    INTEREST_PORTION DECIMAL(15, 2),
    PAYMENT_DATE TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    STATUS VARCHAR(20) DEFAULT 'COMPLETED',
    PRIMARY KEY (ID)
)'''

# =============================================================================
# Table 8: BENEFICIARIES
# =============================================================================
create_beneficiaries_table = f'''CREATE TABLE {SCHEMA}.BENEFICIARIES (
    ID BIGINT NOT NULL GENERATED ALWAYS AS IDENTITY (START WITH 1, INCREMENT BY 1),
    CUSTOMER_ID BIGINT NOT NULL,
    BENEFICIARY_NAME VARCHAR(200) NOT NULL,
    BANK_NAME VARCHAR(200),
    ACCOUNT_NUMBER VARCHAR(30),
    ROUTING_NUMBER VARCHAR(20),
    RELATIONSHIP VARCHAR(50),
    STATUS VARCHAR(20) DEFAULT 'ACTIVE',
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ID)
)'''

# =============================================================================
# Table 9: CARDS (with indexes and constraints)
# =============================================================================
create_cards_table = f'''CREATE TABLE {SCHEMA}.CARDS (
    ID BIGINT NOT NULL GENERATED ALWAYS AS IDENTITY (START WITH 1, INCREMENT BY 1),
    CARD_NUMBER VARCHAR(20) NOT NULL,
    ACCOUNT_ID BIGINT NOT NULL,
    CUSTOMER_ID BIGINT NOT NULL,
    CARD_TYPE VARCHAR(20) NOT NULL,
    EXPIRY_DATE DATE NOT NULL,
    CREDIT_LIMIT DECIMAL(15, 2),
    STATUS VARCHAR(20) DEFAULT 'ACTIVE',
    ISSUED_DATE TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ID),
    CONSTRAINT FK_CARD_ACCT FOREIGN KEY (ACCOUNT_ID)
        REFERENCES {SCHEMA}.ACCOUNTS (ID)
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT FK_CARD_CUST FOREIGN KEY (CUSTOMER_ID)
        REFERENCES {SCHEMA}.CUSTOMERS (ID)
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT UQ_CARD_NUM UNIQUE (CARD_NUMBER)
)'''

create_cards_idx_account = f'''CREATE INDEX IDX_CARD_ACCT ON {SCHEMA}.CARDS (ACCOUNT_ID)'''

create_cards_idx_customer = f'''CREATE INDEX IDX_CARD_CUST ON {SCHEMA}.CARDS (CUSTOMER_ID)'''

create_cards_idx_expiry = f'''CREATE INDEX IDX_CARD_EXPIRY ON {SCHEMA}.CARDS (EXPIRY_DATE, STATUS)'''

# =============================================================================
# Table 10: AUDIT_LOG
# =============================================================================
create_audit_log_table = f'''CREATE TABLE {SCHEMA}.AUDIT_LOG (
    ID BIGINT NOT NULL GENERATED ALWAYS AS IDENTITY (START WITH 1, INCREMENT BY 1),
    TABLE_NAME VARCHAR(100) NOT NULL,
    RECORD_ID BIGINT,
    ACTION VARCHAR(20) NOT NULL,
    PERFORMED_BY VARCHAR(255),
    OLD_VALUE CLOB(1M) CCSID 1208,
    NEW_VALUE CLOB(1M) CCSID 1208,
    ACTION_TIMESTAMP TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ID)
)'''


# =============================================================================
# Ordered list of all table creation statements
# =============================================================================
banking_tables = [
    create_customers_table,
    create_accounts_table,
    create_transactions_table,
    create_branches_table,
    create_employees_table,
    create_loans_table,
    create_loan_payments_table,
    create_beneficiaries_table,
    create_cards_table,
    create_audit_log_table,
]

# Indexes and constraints (applied after table creation)
banking_indexes = [
    # ACCOUNTS indexes
    create_accounts_idx_customer,
    create_accounts_idx_type,
    # TRANSACTIONS indexes
    create_transactions_idx_account,
    create_transactions_idx_date,
    create_transactions_idx_ref,
    # LOANS indexes
    create_loans_idx_customer,
    create_loans_idx_status,
    # CARDS indexes
    create_cards_idx_account,
    create_cards_idx_customer,
    create_cards_idx_expiry,
]


def main():
    print(f"Connecting to DB2 as {DB_USER}...")
    try:
        conn = ibm_db.connect(DB_CONN_STRING, DB_USER, DB_PASSWORD)
    except Exception as e:
        print(f"ERROR: Failed to connect to DB2: {e}")
        sys.exit(1)

    if not conn:
        print("ERROR: Failed to connect to DB2 (no connection returned).")
        sys.exit(1)

    # Set the current schema so FK references resolve correctly
    ibm_db.exec_immediate(conn, f"SET SCHEMA {SCHEMA}")
    print("Connected successfully.\n")

    # --- Create tables ---
    table_names = [
        "CUSTOMERS", "ACCOUNTS", "TRANSACTIONS", "BRANCHES", "EMPLOYEES",
        "LOANS", "LOAN_PAYMENTS", "BENEFICIARIES", "CARDS", "AUDIT_LOG",
    ]
    tables_created = 0

    print("=" * 60)
    print("CREATING TABLES")
    print("=" * 60)

    tables_skipped = 0

    for name, sql in zip(table_names, banking_tables):
        try:
            ibm_db.exec_immediate(conn, sql)
            tables_created += 1
            print(f"  [OK] {SCHEMA}.{name}")
        except Exception as e:
            error_msg = str(e)
            if "SQL0601" in error_msg or "SQLCODE=-601" in error_msg:
                tables_skipped += 1
                print(f"  [SKIP] {SCHEMA}.{name} (already exists)")
            else:
                print(f"  [FAIL] {SCHEMA}.{name}: {e}")
                ibm_db.close(conn)
                sys.exit(1)

    print(f"\nTables created: {tables_created}, skipped: {tables_skipped}, total: {len(banking_tables)}\n")

    # --- Create indexes ---
    index_names = [
        "IDX_ACCT_CUST", "IDX_ACCT_TYPE",
        "IDX_TXN_ACCT", "IDX_TXN_DATE", "IDX_TXN_REF",
        "IDX_LOAN_CUST", "IDX_LOAN_STATUS",
        "IDX_CARD_ACCT", "IDX_CARD_CUST", "IDX_CARD_EXPIRY",
    ]
    indexes_created = 0

    print("=" * 60)
    print("CREATING INDEXES")
    print("=" * 60)

    indexes_skipped = 0

    for name, sql in zip(index_names, banking_indexes):
        try:
            ibm_db.exec_immediate(conn, sql)
            indexes_created += 1
            print(f"  [OK] {name}")
        except Exception as e:
            error_msg = str(e)
            if "SQL0601" in error_msg or "SQLCODE=-601" in error_msg:
                indexes_skipped += 1
                print(f"  [SKIP] {name} (already exists)")
            else:
                print(f"  [FAIL] {name}: {e}")
                ibm_db.close(conn)
                sys.exit(1)

    print(f"\nIndexes created: {indexes_created}, skipped: {indexes_skipped}, total: {len(banking_indexes)}\n")

    # --- Commit and close ---
    ibm_db.commit(conn)
    ibm_db.close(conn)

    print("=" * 60)
    print("ALL DONE — 10 tables and 10 indexes created successfully.")
    print("=" * 60)


if __name__ == "__main__":
    main()
