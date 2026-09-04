#!/usr/bin/env python3
"""
Inserts sample data into all 20 tables (10 banking in TUNERLIB1, 10 IT company in TUNERLIB2).

Distribution per set of 10 tables:
  - 3 tables:  10,000 rows each
  - 3 tables:     500 rows each
  - 4 tables:      10 rows each

Banking (TUNERLIB1):
  10,000: CUSTOMERS, ACCOUNTS, TRANSACTIONS
     500: LOANS, CARDS, BENEFICIARIES
      10: BRANCHES, EMPLOYEES, LOAN_PAYMENTS, AUDIT_LOG

IT Company (TUNERLIB2):
  10,000: IT_EMPLOYEES, TIMESHEETS, TICKETS
     500: PROJECTS, PROJECT_ASSIGNMENTS, SKILLS
      10: DEPARTMENTS, ASSETS, LEAVES, RELEASE_LOG

Usage: python3 insert_sample_data.py
"""

import sys
import random
import string
from datetime import datetime, timedelta
import time

try:
    import ibm_db
except ImportError:
    print("ERROR: ibm_db module not found. Install it with: pip3 install ibm_db")
    sys.exit(1)

DB_CONN_STRING = "*LOCAL"
DB_USER = "adubey"
DB_PASSWORD = "adubey"
BANK = "TUNERLIB1"
IT = "TUNERLIB2"

# Unique prefix per run to avoid duplicate key collisions on re-runs
RUN_ID = datetime.now().strftime('%m%d%H%M%S')


# =============================================================================
# Helper functions
# =============================================================================

def rs(n):
    """Random alphabetic string."""
    return ''.join(random.choices(string.ascii_letters, k=n))

def rand_email():
    return f"{rs(8).lower()}@{rs(5).lower()}.com"

def rand_phone():
    return f"{random.randint(100,999)}-{random.randint(100,999)}-{random.randint(1000,9999)}"

def rand_date(y1=2020, y2=2025):
    start = datetime(y1, 1, 1)
    days = (datetime(y2, 12, 31) - start).days
    return (start + timedelta(days=random.randint(0, days))).strftime('%Y-%m-%d')

def rand_future_date():
    return rand_date(2026, 2030)

def rand_dec(lo, hi):
    return round(random.uniform(lo, hi), 2)


def bulk_insert(conn, sql, gen_fn, count, label, batch=1000):
    """Prepare statement once, execute for each row, commit in batches."""
    stmt = ibm_db.prepare(conn, sql)
    if not stmt:
        print(f"  [FAIL] {label}: prepare failed — {ibm_db.stmt_errormsg()}")
        return
    done = 0
    for i in range(count):
        params = gen_fn(i)
        result = ibm_db.execute(stmt, params)
        if not result:
            print(f"  [FAIL] {label} row {i}: {ibm_db.stmt_errormsg()}")
            return
        done += 1
        if done % batch == 0:
            ibm_db.commit(conn)
            if count >= 1000:
                print(f"    {label}: {done}/{count}...")
    ibm_db.commit(conn)
    print(f"  [OK] {label}: {done} rows inserted")


# =============================================================================
# BANKING TABLES (TUNERLIB1) — insert in FK-dependency order
# =============================================================================

ACCOUNT_TYPES = ['CHECKING', 'SAVINGS', 'MONEY_MARKET', 'CD']
TXN_TYPES = ['DEPOSIT', 'WITHDRAWAL', 'TRANSFER', 'PAYMENT', 'FEE']
LOAN_TYPES = ['MORTGAGE', 'AUTO', 'PERSONAL', 'STUDENT', 'BUSINESS']
CARD_TYPES = ['DEBIT', 'CREDIT', 'PREPAID']
RELATIONSHIPS = ['SPOUSE', 'PARENT', 'CHILD', 'SIBLING', 'FRIEND', 'BUSINESS']
DESIGNATIONS = ['TELLER', 'MANAGER', 'VP', 'ANALYST', 'OFFICER']
STATES = ['NY', 'CA', 'TX', 'FL', 'IL', 'PA', 'OH', 'GA', 'NC', 'MI']
ACTIONS = ['INSERT', 'UPDATE', 'DELETE']


def insert_banking_data(conn):
    print("\n" + "=" * 60)
    print(f"INSERTING DATA INTO {BANK} (Banking)")
    print("=" * 60)

    # ---- CUSTOMERS: 10,000 rows (no FK) ----
    sql = (f"INSERT INTO {BANK}.CUSTOMERS "
           f"(FIRST_NAME, LAST_NAME, EMAIL, PHONE, DATE_OF_BIRTH, "
           f"ADDRESS, CITY, STATE, POSTAL_CODE) "
           f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)")
    def gen_customer(i):
        return (rs(8), rs(10), rand_email(), rand_phone(),
                rand_date(1960, 2000), rs(20), rs(10),
                random.choice(STATES), str(random.randint(10000, 99999)))
    bulk_insert(conn, sql, gen_customer, 10000, f"{BANK}.CUSTOMERS")

    # ---- BRANCHES: 10 rows (no FK) ----
    sql = (f"INSERT INTO {BANK}.BRANCHES "
           f"(BRANCH_CODE, BRANCH_NAME, ADDRESS, CITY, STATE, POSTAL_CODE, PHONE, MANAGER_NAME) "
           f"VALUES (?, ?, ?, ?, ?, ?, ?, ?)")
    def gen_branch(i):
        return (f"BR{i+1:04d}", f"Branch {rs(6)}", rs(25), rs(10),
                random.choice(STATES), str(random.randint(10000, 99999)),
                rand_phone(), f"{rs(6)} {rs(8)}")
    bulk_insert(conn, sql, gen_branch, 10, f"{BANK}.BRANCHES")

    # ---- EMPLOYEES: 10 rows (no FK constraint) ----
    sql = (f"INSERT INTO {BANK}.EMPLOYEES "
           f"(EMPLOYEE_NUMBER, FIRST_NAME, LAST_NAME, EMAIL, PHONE, "
           f"BRANCH_ID, DESIGNATION, HIRE_DATE) "
           f"VALUES (?, ?, ?, ?, ?, ?, ?, ?)")
    def gen_employee(i):
        return (f"BEMP{i+1:06d}", rs(8), rs(10), rand_email(), rand_phone(),
                random.randint(1, 10), random.choice(DESIGNATIONS), rand_date(2015, 2024))
    bulk_insert(conn, sql, gen_employee, 10, f"{BANK}.EMPLOYEES")

    # ---- ACCOUNTS: 10,000 rows (FK → CUSTOMERS) ----
    sql = (f"INSERT INTO {BANK}.ACCOUNTS "
           f"(ACCOUNT_NUMBER, CUSTOMER_ID, ACCOUNT_TYPE, BALANCE, CURRENCY) "
           f"VALUES (?, ?, ?, ?, ?)")
    def gen_account(i):
        return (f"A{RUN_ID}{i+1:06d}", random.randint(1, 10000),
                random.choice(ACCOUNT_TYPES), rand_dec(100, 500000), 'USD')
    bulk_insert(conn, sql, gen_account, 10000, f"{BANK}.ACCOUNTS")

    # ---- TRANSACTIONS: 10,000 rows (FK → ACCOUNTS) ----
    sql = (f"INSERT INTO {BANK}.TRANSACTIONS "
           f"(ACCOUNT_ID, TRANSACTION_TYPE, AMOUNT, DESCRIPTION, REFERENCE_NUMBER) "
           f"VALUES (?, ?, ?, ?, ?)")
    def gen_txn(i):
        return (random.randint(1, 10000), random.choice(TXN_TYPES),
                rand_dec(1, 50000), rs(30), f"R{RUN_ID}{i+1:06d}")
    bulk_insert(conn, sql, gen_txn, 10000, f"{BANK}.TRANSACTIONS")

    # ---- LOANS: 500 rows (FK → CUSTOMERS, ACCOUNTS) ----
    sql = (f"INSERT INTO {BANK}.LOANS "
           f"(LOAN_NUMBER, CUSTOMER_ID, ACCOUNT_ID, LOAN_TYPE, PRINCIPAL_AMOUNT, "
           f"INTEREST_RATE, TERM_MONTHS, MONTHLY_PAYMENT, OUTSTANDING_BALANCE) "
           f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)")
    def gen_loan(i):
        principal = rand_dec(5000, 500000)
        rate = rand_dec(2, 15)
        months = random.choice([12, 24, 36, 60, 120, 240, 360])
        monthly = round(principal / months * (1 + rate / 100), 2)
        return (f"L{RUN_ID}{i+1:06d}", random.randint(1, 10000), random.randint(1, 10000),
                random.choice(LOAN_TYPES), principal, rate, months,
                monthly, rand_dec(1000, principal))
    bulk_insert(conn, sql, gen_loan, 500, f"{BANK}.LOANS")

    # ---- CARDS: 500 rows (FK → ACCOUNTS, CUSTOMERS) ----
    sql = (f"INSERT INTO {BANK}.CARDS "
           f"(CARD_NUMBER, ACCOUNT_ID, CUSTOMER_ID, CARD_TYPE, EXPIRY_DATE, CREDIT_LIMIT) "
           f"VALUES (?, ?, ?, ?, ?, ?)")
    def gen_card(i):
        return (f"C{RUN_ID}{i+1:06d}", random.randint(1, 10000), random.randint(1, 10000),
                random.choice(CARD_TYPES), rand_future_date(), rand_dec(1000, 100000))
    bulk_insert(conn, sql, gen_card, 500, f"{BANK}.CARDS")

    # ---- BENEFICIARIES: 500 rows (no FK constraint) ----
    sql = (f"INSERT INTO {BANK}.BENEFICIARIES "
           f"(CUSTOMER_ID, BENEFICIARY_NAME, BANK_NAME, ACCOUNT_NUMBER, ROUTING_NUMBER, RELATIONSHIP) "
           f"VALUES (?, ?, ?, ?, ?, ?)")
    def gen_bene(i):
        return (random.randint(1, 10000), f"{rs(8)} {rs(10)}",
                f"{rs(6)} Bank", f"BEN{i+1:010d}",
                str(random.randint(100000000, 999999999)), random.choice(RELATIONSHIPS))
    bulk_insert(conn, sql, gen_bene, 500, f"{BANK}.BENEFICIARIES")

    # ---- LOAN_PAYMENTS: 10 rows (no FK constraint) ----
    sql = (f"INSERT INTO {BANK}.LOAN_PAYMENTS "
           f"(LOAN_ID, PAYMENT_AMOUNT, PRINCIPAL_PORTION, INTEREST_PORTION) "
           f"VALUES (?, ?, ?, ?)")
    def gen_lp(i):
        amt = rand_dec(500, 5000)
        principal_part = round(amt * 0.7, 2)
        interest_part = round(amt - principal_part, 2)
        return (random.randint(1, 500), amt, principal_part, interest_part)
    bulk_insert(conn, sql, gen_lp, 10, f"{BANK}.LOAN_PAYMENTS")

    # ---- AUDIT_LOG: 10 rows (no FK) ----
    sql = (f"INSERT INTO {BANK}.AUDIT_LOG "
           f"(TABLE_NAME, RECORD_ID, ACTION, PERFORMED_BY) "
           f"VALUES (?, ?, ?, ?)")
    tables_list = ['CUSTOMERS', 'ACCOUNTS', 'TRANSACTIONS', 'LOANS', 'CARDS']
    def gen_audit(i):
        return (random.choice(tables_list), random.randint(1, 1000),
                random.choice(ACTIONS), rs(10))
    bulk_insert(conn, sql, gen_audit, 10, f"{BANK}.AUDIT_LOG")


# =============================================================================
# IT COMPANY TABLES (TUNERLIB2) — insert in FK-dependency order
# =============================================================================

DEPT_NAMES = ['Engineering', 'QA', 'DevOps', 'Product', 'Design',
              'Data Science', 'Security', 'Support', 'HR', 'Finance']
IT_DESIGNATIONS = ['Developer', 'Sr Developer', 'Lead', 'Architect', 'Manager',
                   'QA Engineer', 'DevOps Engineer', 'Analyst', 'Director', 'Intern']
PRIORITIES = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
PROJ_STATUSES = ['PLANNING', 'ACTIVE', 'ON_HOLD', 'COMPLETED']
TICKET_TYPES = ['BUG', 'FEATURE', 'TASK', 'IMPROVEMENT']
SEVERITIES = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
TICKET_STATUSES = ['OPEN', 'IN_PROGRESS', 'REVIEW', 'CLOSED']
ASSET_TYPES = ['LAPTOP', 'MONITOR', 'KEYBOARD', 'HEADSET', 'PHONE', 'SERVER']
ASSET_MAKES = ['Dell', 'Apple', 'Lenovo', 'HP', 'Logitech']
LEAVE_TYPES = ['ANNUAL', 'SICK', 'PERSONAL', 'MATERNITY', 'PATERNITY']
SKILLS_LIST = ['Python', 'Java', 'SQL', 'JavaScript', 'Go', 'Rust', 'C++',
               'Kubernetes', 'Docker', 'AWS', 'Azure', 'React', 'Angular']
PROFICIENCIES = ['BEGINNER', 'INTERMEDIATE', 'ADVANCED', 'EXPERT']
ENVIRONMENTS = ['DEV', 'STAGING', 'QA', 'PRODUCTION']
ROLES = ['Developer', 'Tester', 'Lead', 'Reviewer', 'Scrum Master']


def insert_it_data(conn):
    print("\n" + "=" * 60)
    print(f"INSERTING DATA INTO {IT} (IT Company)")
    print("=" * 60)

    # ---- DEPARTMENTS: 10 rows (no FK) ----
    sql = (f"INSERT INTO {IT}.DEPARTMENTS "
           f"(DEPT_CODE, DEPT_NAME, DESCRIPTION, LOCATION) "
           f"VALUES (?, ?, ?, ?)")
    def gen_dept(i):
        name = DEPT_NAMES[i] if i < len(DEPT_NAMES) else f"Dept{rs(4)}"
        return (f"D{i+1:04d}", name, f"{name} department", rs(15))
    bulk_insert(conn, sql, gen_dept, 10, f"{IT}.DEPARTMENTS")

    # ---- IT_EMPLOYEES: 10,000 rows (FK → DEPARTMENTS) ----
    sql = (f"INSERT INTO {IT}.IT_EMPLOYEES "
           f"(EMPLOYEE_CODE, FIRST_NAME, LAST_NAME, EMAIL, PHONE, "
           f"DEPARTMENT_ID, DESIGNATION, HIRE_DATE, SALARY) "
           f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)")
    def gen_it_emp(i):
        return (f"E{RUN_ID}{i+1:06d}", rs(8), rs(10), rand_email(), rand_phone(),
                random.randint(1, 10), random.choice(IT_DESIGNATIONS),
                rand_date(2015, 2025), rand_dec(40000, 200000))
    bulk_insert(conn, sql, gen_it_emp, 10000, f"{IT}.IT_EMPLOYEES")

    # ---- PROJECTS: 500 rows (FK → DEPARTMENTS, IT_EMPLOYEES) ----
    sql = (f"INSERT INTO {IT}.PROJECTS "
           f"(PROJECT_CODE, PROJECT_NAME, CLIENT_NAME, DESCRIPTION, "
           f"START_DATE, END_DATE, BUDGET, STATUS, PRIORITY, "
           f"DEPARTMENT_ID, PROJECT_MANAGER_ID) "
           f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)")
    def gen_project(i):
        return (f"P{RUN_ID}{i+1:04d}", f"Project {rs(8)}", f"{rs(6)} Corp",
                f"Description for project {i+1}", rand_date(2022, 2024),
                rand_date(2025, 2027), rand_dec(50000, 5000000),
                random.choice(PROJ_STATUSES), random.choice(PRIORITIES),
                random.randint(1, 10), random.randint(1, 500))
    bulk_insert(conn, sql, gen_project, 500, f"{IT}.PROJECTS")

    # ---- PROJECT_ASSIGNMENTS: 500 rows (no FK constraint) ----
    sql = (f"INSERT INTO {IT}.PROJECT_ASSIGNMENTS "
           f"(PROJECT_ID, EMPLOYEE_ID, ROLE, ALLOCATION_PERCENT, START_DATE, END_DATE) "
           f"VALUES (?, ?, ?, ?, ?, ?)")
    def gen_assign(i):
        return (random.randint(1, 500), random.randint(1, 10000),
                random.choice(ROLES), random.choice([25, 50, 75, 100]),
                rand_date(2023, 2024), rand_date(2025, 2026))
    bulk_insert(conn, sql, gen_assign, 500, f"{IT}.PROJECT_ASSIGNMENTS")

    # ---- TIMESHEETS: 10,000 rows (FK → IT_EMPLOYEES, PROJECTS) ----
    sql = (f"INSERT INTO {IT}.TIMESHEETS "
           f"(EMPLOYEE_ID, PROJECT_ID, WORK_DATE, HOURS_WORKED, TASK_DESCRIPTION) "
           f"VALUES (?, ?, ?, ?, ?)")
    def gen_ts(i):
        return (random.randint(1, 10000), random.randint(1, 500),
                rand_date(2024, 2025), rand_dec(1, 12), rs(30))
    bulk_insert(conn, sql, gen_ts, 10000, f"{IT}.TIMESHEETS")

    # ---- TICKETS: 10,000 rows (FK → PROJECTS, IT_EMPLOYEES) ----
    sql = (f"INSERT INTO {IT}.TICKETS "
           f"(TICKET_NUMBER, PROJECT_ID, TITLE, TICKET_TYPE, SEVERITY, "
           f"STATUS, ASSIGNED_TO, REPORTED_BY, DUE_DATE) "
           f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)")
    def gen_ticket(i):
        return (f"T{RUN_ID}{i+1:06d}", random.randint(1, 500),
                f"{rs(15)} {rs(10)}", random.choice(TICKET_TYPES),
                random.choice(SEVERITIES), random.choice(TICKET_STATUSES),
                random.randint(1, 10000), random.randint(1, 10000),
                rand_future_date())
    bulk_insert(conn, sql, gen_ticket, 10000, f"{IT}.TICKETS")

    # ---- ASSETS: 10 rows (no FK) ----
    sql = (f"INSERT INTO {IT}.ASSETS "
           f"(ASSET_TAG, ASSET_TYPE, MAKE, MODEL, SERIAL_NUMBER, "
           f"PURCHASE_DATE, PURCHASE_COST, WARRANTY_EXPIRY) "
           f"VALUES (?, ?, ?, ?, ?, ?, ?, ?)")
    def gen_asset(i):
        return (f"AST{i+1:06d}", random.choice(ASSET_TYPES),
                random.choice(ASSET_MAKES), f"Model-{rs(4)}",
                f"SN{random.randint(100000, 999999)}", rand_date(2022, 2025),
                rand_dec(500, 5000), rand_future_date())
    bulk_insert(conn, sql, gen_asset, 10, f"{IT}.ASSETS")

    # ---- LEAVES: 10 rows (no FK constraint) ----
    sql = (f"INSERT INTO {IT}.LEAVES "
           f"(EMPLOYEE_ID, LEAVE_TYPE, START_DATE, END_DATE, TOTAL_DAYS, REASON) "
           f"VALUES (?, ?, ?, ?, ?, ?)")
    def gen_leave(i):
        days = random.randint(1, 10)
        return (random.randint(1, 10000), random.choice(LEAVE_TYPES),
                rand_date(2025, 2025), rand_date(2025, 2025),
                float(days), rs(20))
    bulk_insert(conn, sql, gen_leave, 10, f"{IT}.LEAVES")

    # ---- SKILLS: 500 rows (no FK constraint) ----
    sql = (f"INSERT INTO {IT}.SKILLS "
           f"(EMPLOYEE_ID, SKILL_NAME, PROFICIENCY, YEARS_EXPERIENCE, CERTIFIED) "
           f"VALUES (?, ?, ?, ?, ?)")
    def gen_skill(i):
        return (random.randint(1, 10000), random.choice(SKILLS_LIST),
                random.choice(PROFICIENCIES), random.randint(1, 15),
                random.randint(0, 1))
    bulk_insert(conn, sql, gen_skill, 500, f"{IT}.SKILLS")

    # ---- RELEASE_LOG: 10 rows (no FK constraint) ----
    sql = (f"INSERT INTO {IT}.RELEASE_LOG "
           f"(PROJECT_ID, VERSION, RELEASE_DATE, ENVIRONMENT) "
           f"VALUES (?, ?, ?, ?)")
    def gen_release(i):
        return (random.randint(1, 500), f"v{random.randint(1,9)}.{random.randint(0,9)}.{i}",
                rand_date(2024, 2025), random.choice(ENVIRONMENTS))
    bulk_insert(conn, sql, gen_release, 10, f"{IT}.RELEASE_LOG")


# =============================================================================
# Main
# =============================================================================

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

    print("Connected successfully.\n")

    try:
        # Banking tables
        ibm_db.exec_immediate(conn, f"SET SCHEMA {BANK}")
        insert_banking_data(conn)

        # IT Company tables
        ibm_db.exec_immediate(conn, f"SET SCHEMA {IT}")
        insert_it_data(conn)

    except Exception as e:
        print(f"\nERROR: {e}")
        ibm_db.close(conn)
        sys.exit(1)

    ibm_db.close(conn)

    print("\n" + "=" * 60)
    print("ALL DONE — Sample data inserted into all 20 tables.")
    print("")
    print("Banking (TUNERLIB1):   10K x3  |  500 x3  |  10 x4")
    print("IT Company (TUNERLIB2): 10K x3  |  500 x3  |  10 x4")
    print("Total rows: ~63,060")
    print(f"Run ID: {RUN_ID}")
    print("=" * 60)


if __name__ == "__main__":
    main()
