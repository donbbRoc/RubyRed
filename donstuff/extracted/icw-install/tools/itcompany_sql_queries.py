#!/usr/bin/env python3
"""
Standalone script to create 10 IT company tables in DB2 for IBM i under library TUNERLIB1.
Usage: python3 itcompany_sql_queries.py
"""

import sys

try:
    import ibm_db
except ImportError:
    print("ERROR: ibm_db module not found. Install it with: pip3 install ibm_db")
    sys.exit(1)

SCHEMA = "TUNERLIB2"
DB_CONN_STRING = "*LOCAL"
DB_USER = "adubey"
DB_PASSWORD = "adubey"

# =============================================================================
# Table 1: DEPARTMENTS
# =============================================================================
create_departments_table = f'''CREATE TABLE {SCHEMA}.DEPARTMENTS (
    ID BIGINT NOT NULL GENERATED ALWAYS AS IDENTITY (START WITH 1, INCREMENT BY 1),
    DEPT_CODE VARCHAR(10) NOT NULL,
    DEPT_NAME VARCHAR(200) NOT NULL,
    DESCRIPTION VARCHAR(500),
    MANAGER_ID BIGINT,
    LOCATION VARCHAR(200),
    STATUS VARCHAR(20) DEFAULT 'ACTIVE',
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ID)
)'''

# =============================================================================
# Table 2: EMPLOYEES (with indexes and constraints)
# =============================================================================
create_employees_table = f'''CREATE TABLE {SCHEMA}.IT_EMPLOYEES (
    ID BIGINT NOT NULL GENERATED ALWAYS AS IDENTITY (START WITH 1, INCREMENT BY 1),
    EMPLOYEE_CODE VARCHAR(20) NOT NULL,
    FIRST_NAME VARCHAR(100) NOT NULL,
    LAST_NAME VARCHAR(100) NOT NULL,
    EMAIL VARCHAR(255),
    PHONE VARCHAR(20),
    DEPARTMENT_ID BIGINT NOT NULL,
    DESIGNATION VARCHAR(100),
    HIRE_DATE DATE,
    SALARY DECIMAL(12, 2),
    REPORTING_TO BIGINT,
    STATUS VARCHAR(20) DEFAULT 'ACTIVE',
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UPDATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ID),
    CONSTRAINT FK_EMP_DEPT FOREIGN KEY (DEPARTMENT_ID)
        REFERENCES {SCHEMA}.DEPARTMENTS (ID)
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT UQ_EMP_CODE UNIQUE (EMPLOYEE_CODE)
)'''

create_employees_idx_dept = f'''CREATE INDEX IDX_EMP_DEPT ON {SCHEMA}.IT_EMPLOYEES (DEPARTMENT_ID)'''

create_employees_idx_status = f'''CREATE INDEX IDX_EMP_STATUS ON {SCHEMA}.IT_EMPLOYEES (STATUS, DESIGNATION)'''

# =============================================================================
# Table 3: PROJECTS (with indexes and constraints)
# =============================================================================
create_projects_table = f'''CREATE TABLE {SCHEMA}.PROJECTS (
    ID BIGINT NOT NULL GENERATED ALWAYS AS IDENTITY (START WITH 1, INCREMENT BY 1),
    PROJECT_CODE VARCHAR(20) NOT NULL,
    PROJECT_NAME VARCHAR(200) NOT NULL,
    CLIENT_NAME VARCHAR(200),
    DESCRIPTION VARCHAR(1000),
    START_DATE DATE,
    END_DATE DATE,
    BUDGET DECIMAL(15, 2),
    STATUS VARCHAR(20) DEFAULT 'PLANNING',
    PRIORITY VARCHAR(10) DEFAULT 'MEDIUM',
    DEPARTMENT_ID BIGINT,
    PROJECT_MANAGER_ID BIGINT,
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ID),
    CONSTRAINT FK_PROJ_DEPT FOREIGN KEY (DEPARTMENT_ID)
        REFERENCES {SCHEMA}.DEPARTMENTS (ID)
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT FK_PROJ_MGR FOREIGN KEY (PROJECT_MANAGER_ID)
        REFERENCES {SCHEMA}.IT_EMPLOYEES (ID)
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT UQ_PROJ_CODE UNIQUE (PROJECT_CODE)
)'''

create_projects_idx_dept = f'''CREATE INDEX IDX_PROJ_DEPT ON {SCHEMA}.PROJECTS (DEPARTMENT_ID)'''

create_projects_idx_status = f'''CREATE INDEX IDX_PROJ_STATUS ON {SCHEMA}.PROJECTS (STATUS, PRIORITY)'''

create_projects_idx_dates = f'''CREATE INDEX IDX_PROJ_DATES ON {SCHEMA}.PROJECTS (START_DATE, END_DATE)'''

# =============================================================================
# Table 4: PROJECT_ASSIGNMENTS
# =============================================================================
create_project_assignments_table = f'''CREATE TABLE {SCHEMA}.PROJECT_ASSIGNMENTS (
    ID BIGINT NOT NULL GENERATED ALWAYS AS IDENTITY (START WITH 1, INCREMENT BY 1),
    PROJECT_ID BIGINT NOT NULL,
    EMPLOYEE_ID BIGINT NOT NULL,
    ROLE VARCHAR(50),
    ALLOCATION_PERCENT INTEGER DEFAULT 100,
    START_DATE DATE,
    END_DATE DATE,
    STATUS VARCHAR(20) DEFAULT 'ACTIVE',
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ID)
)'''

# =============================================================================
# Table 5: TIMESHEETS (with indexes and constraints)
# =============================================================================
create_timesheets_table = f'''CREATE TABLE {SCHEMA}.TIMESHEETS (
    ID BIGINT NOT NULL GENERATED ALWAYS AS IDENTITY (START WITH 1, INCREMENT BY 1),
    EMPLOYEE_ID BIGINT NOT NULL,
    PROJECT_ID BIGINT NOT NULL,
    WORK_DATE DATE NOT NULL,
    HOURS_WORKED DECIMAL(4, 2) NOT NULL,
    TASK_DESCRIPTION VARCHAR(500),
    STATUS VARCHAR(20) DEFAULT 'SUBMITTED',
    APPROVED_BY BIGINT,
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ID),
    CONSTRAINT FK_TS_EMP FOREIGN KEY (EMPLOYEE_ID)
        REFERENCES {SCHEMA}.IT_EMPLOYEES (ID)
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT FK_TS_PROJ FOREIGN KEY (PROJECT_ID)
        REFERENCES {SCHEMA}.PROJECTS (ID)
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)'''

create_timesheets_idx_emp = f'''CREATE INDEX IDX_TS_EMP ON {SCHEMA}.TIMESHEETS (EMPLOYEE_ID)'''

create_timesheets_idx_proj = f'''CREATE INDEX IDX_TS_PROJ ON {SCHEMA}.TIMESHEETS (PROJECT_ID)'''

create_timesheets_idx_date = f'''CREATE INDEX IDX_TS_DATE ON {SCHEMA}.TIMESHEETS (WORK_DATE)'''

# =============================================================================
# Table 6: TICKETS (with indexes and constraints)
# =============================================================================
create_tickets_table = f'''CREATE TABLE {SCHEMA}.TICKETS (
    ID BIGINT NOT NULL GENERATED ALWAYS AS IDENTITY (START WITH 1, INCREMENT BY 1),
    TICKET_NUMBER VARCHAR(20) NOT NULL,
    PROJECT_ID BIGINT NOT NULL,
    TITLE VARCHAR(300) NOT NULL,
    DESCRIPTION CLOB(1M) CCSID 1208,
    TICKET_TYPE VARCHAR(20) NOT NULL,
    SEVERITY VARCHAR(10) DEFAULT 'MEDIUM',
    STATUS VARCHAR(20) DEFAULT 'OPEN',
    ASSIGNED_TO BIGINT,
    REPORTED_BY BIGINT NOT NULL,
    DUE_DATE DATE,
    RESOLVED_AT TIMESTAMP,
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UPDATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ID),
    CONSTRAINT FK_TKT_PROJ FOREIGN KEY (PROJECT_ID)
        REFERENCES {SCHEMA}.PROJECTS (ID)
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT FK_TKT_ASSIGNEE FOREIGN KEY (ASSIGNED_TO)
        REFERENCES {SCHEMA}.IT_EMPLOYEES (ID)
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT FK_TKT_REPORTER FOREIGN KEY (REPORTED_BY)
        REFERENCES {SCHEMA}.IT_EMPLOYEES (ID)
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT UQ_TKT_NUM UNIQUE (TICKET_NUMBER)
)'''

create_tickets_idx_proj = f'''CREATE INDEX IDX_TKT_PROJ ON {SCHEMA}.TICKETS (PROJECT_ID)'''

create_tickets_idx_assignee = f'''CREATE INDEX IDX_TKT_ASSIGNEE ON {SCHEMA}.TICKETS (ASSIGNED_TO)'''

create_tickets_idx_status = f'''CREATE INDEX IDX_TKT_STATUS ON {SCHEMA}.TICKETS (STATUS, SEVERITY)'''

# =============================================================================
# Table 7: ASSETS
# =============================================================================
create_assets_table = f'''CREATE TABLE {SCHEMA}.ASSETS (
    ID BIGINT NOT NULL GENERATED ALWAYS AS IDENTITY (START WITH 1, INCREMENT BY 1),
    ASSET_TAG VARCHAR(30) NOT NULL,
    ASSET_TYPE VARCHAR(50) NOT NULL,
    MAKE VARCHAR(100),
    MODEL VARCHAR(100),
    SERIAL_NUMBER VARCHAR(100),
    ASSIGNED_TO BIGINT,
    PURCHASE_DATE DATE,
    PURCHASE_COST DECIMAL(12, 2),
    WARRANTY_EXPIRY DATE,
    STATUS VARCHAR(20) DEFAULT 'AVAILABLE',
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ID)
)'''

# =============================================================================
# Table 8: LEAVES
# =============================================================================
create_leaves_table = f'''CREATE TABLE {SCHEMA}.LEAVES (
    ID BIGINT NOT NULL GENERATED ALWAYS AS IDENTITY (START WITH 1, INCREMENT BY 1),
    EMPLOYEE_ID BIGINT NOT NULL,
    LEAVE_TYPE VARCHAR(30) NOT NULL,
    START_DATE DATE NOT NULL,
    END_DATE DATE NOT NULL,
    TOTAL_DAYS DECIMAL(4, 1) NOT NULL,
    REASON VARCHAR(500),
    STATUS VARCHAR(20) DEFAULT 'PENDING',
    APPROVED_BY BIGINT,
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ID)
)'''

# =============================================================================
# Table 9: SKILLS
# =============================================================================
create_skills_table = f'''CREATE TABLE {SCHEMA}.SKILLS (
    ID BIGINT NOT NULL GENERATED ALWAYS AS IDENTITY (START WITH 1, INCREMENT BY 1),
    EMPLOYEE_ID BIGINT NOT NULL,
    SKILL_NAME VARCHAR(100) NOT NULL,
    PROFICIENCY VARCHAR(20) DEFAULT 'INTERMEDIATE',
    YEARS_EXPERIENCE INTEGER,
    CERTIFIED SMALLINT DEFAULT 0,
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ID)
)'''

# =============================================================================
# Table 10: RELEASE_LOG
# =============================================================================
create_release_log_table = f'''CREATE TABLE {SCHEMA}.RELEASE_LOG (
    ID BIGINT NOT NULL GENERATED ALWAYS AS IDENTITY (START WITH 1, INCREMENT BY 1),
    PROJECT_ID BIGINT NOT NULL,
    VERSION VARCHAR(30) NOT NULL,
    RELEASE_DATE TIMESTAMP,
    RELEASE_NOTES CLOB(1M) CCSID 1208,
    DEPLOYED_BY BIGINT,
    ENVIRONMENT VARCHAR(30) NOT NULL,
    STATUS VARCHAR(20) DEFAULT 'DEPLOYED',
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ID)
)'''


# =============================================================================
# Ordered list of all table creation statements
# =============================================================================
it_tables = [
    create_departments_table,
    create_employees_table,
    create_projects_table,
    create_project_assignments_table,
    create_timesheets_table,
    create_tickets_table,
    create_assets_table,
    create_leaves_table,
    create_skills_table,
    create_release_log_table,
]

# Indexes (applied after table creation)
it_indexes = [
    # IT_EMPLOYEES indexes
    create_employees_idx_dept,
    create_employees_idx_status,
    # PROJECTS indexes
    create_projects_idx_dept,
    create_projects_idx_status,
    create_projects_idx_dates,
    # TIMESHEETS indexes
    create_timesheets_idx_emp,
    create_timesheets_idx_proj,
    create_timesheets_idx_date,
    # TICKETS indexes
    create_tickets_idx_proj,
    create_tickets_idx_assignee,
    create_tickets_idx_status,
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
        "DEPARTMENTS", "IT_EMPLOYEES", "PROJECTS", "PROJECT_ASSIGNMENTS",
        "TIMESHEETS", "TICKETS", "ASSETS", "LEAVES", "SKILLS", "RELEASE_LOG",
    ]
    tables_created = 0
    tables_skipped = 0

    print("=" * 60)
    print("CREATING TABLES")
    print("=" * 60)

    for name, sql in zip(table_names, it_tables):
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

    print(f"\nTables created: {tables_created}, skipped: {tables_skipped}, total: {len(it_tables)}\n")

    # --- Create indexes ---
    index_names = [
        "IDX_EMP_DEPT", "IDX_EMP_STATUS",
        "IDX_PROJ_DEPT", "IDX_PROJ_STATUS", "IDX_PROJ_DATES",
        "IDX_TS_EMP", "IDX_TS_PROJ", "IDX_TS_DATE",
        "IDX_TKT_PROJ", "IDX_TKT_ASSIGNEE", "IDX_TKT_STATUS",
    ]
    indexes_created = 0
    indexes_skipped = 0

    print("=" * 60)
    print("CREATING INDEXES")
    print("=" * 60)

    for name, sql in zip(index_names, it_indexes):
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

    print(f"\nIndexes created: {indexes_created}, skipped: {indexes_skipped}, total: {len(it_indexes)}\n")

    # --- Commit and close ---
    ibm_db.commit(conn)
    ibm_db.close(conn)

    print("=" * 60)
    print("ALL DONE — 10 tables and 11 indexes created successfully.")
    print("=" * 60)


if __name__ == "__main__":
    main()
