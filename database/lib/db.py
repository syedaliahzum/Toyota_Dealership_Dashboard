"""
database.lib.db

Database utility module for Toyota service center operations.

Features:
- MySQL connection pooling (mysql-connector-python)
- run_query / run_query_many helpers with transaction management
- CSV reading and cleaning helpers (pandas)
- Data insertion helpers for technician_reports, daily_cpus_reports, repeat_repairs
- Data retrieval helpers for denormalized tables and lightweight summaries

Configuration is defined in DB_CONFIG near the top of the file. This module intentionally uses the official
mysql-connector-python driver and pandas for CSV handling.

Usage examples:
>>> from database.lib.db import test_connection, run_query
>>> test_connection()
>>> run_query("SELECT * FROM daily_cpus_reports", commit=False)
"""
from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from decimal import Decimal
from datetime import datetime, date, time
from typing import Any, Dict, List, Optional, Tuple, Union
import re

import pandas as pd
import mysql.connector
from mysql.connector import Error as MySQLError
from mysql.connector.pooling import MySQLConnectionPool
import os


# ---------------------------
# Utility: Column name normalization
# ---------------------------
def normalize_column_name(col: str) -> str:
    """Normalize a column name by standardizing spaces, underscores, newlines, and punctuation.
    
    This helps match CSV columns (which may use spaces, dots, newlines: 'No. of\nJobs') 
    to expected column names (which use underscores: 'no_of_jobs').
    """
    # Replace newlines and tabs with spaces
    normalized = re.sub(r'[\n\r\t]+', ' ', col)
    # Replace periods with spaces (to preserve word separation before converting to underscores)
    normalized = normalized.replace('.', ' ')
    # Replace dashes with spaces
    normalized = normalized.replace('-', ' ')
    # Replace forward slashes with spaces (for SA/TA -> sa_ta)
    normalized = normalized.replace('/', ' ')
    # Replace spaces with underscores
    normalized = normalized.replace(' ', '_')
    # Remove any multiple consecutive underscores
    normalized = re.sub(r'_+', '_', normalized)
    # Remove trailing/leading underscores and colons
    normalized = normalized.strip('_:- ').lower()
    return normalized

# ---------------------------
# Configuration
# ---------------------------
DB_CONFIG: Dict[str, Any] = {
    "host": "localhost",
    "user": "root",
    "password": "root",
    "database": "toyota_service",
    "charset": "utf8mb4",
    "use_unicode": True,
    "allow_local_infile": True,
}
POOL_NAME = "toyota_pool"
POOL_SIZE = 10
POOL_RESET_SESSION = True

# Allow overriding DB_CONFIG via environment variables for safer credential handling.
DB_CONFIG.update({
    k: v for k, v in {
        "host": os.environ.get("DB_HOST"),
        "user": os.environ.get("DB_USER"),
        "password": os.environ.get("DB_PASSWORD"),
        "database": os.environ.get("DB_NAME"),
        "port": os.environ.get("DB_PORT"),
    }.items() if v is not None
})

# ---------------------------
# Logging
# ---------------------------
logger = logging.getLogger("database.lib.db")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# ---------------------------
# Connection pool (singleton)
# ---------------------------
_connection_pool: Optional[MySQLConnectionPool] = None
_pool_lock = threading.Lock()

\

# Denormalized table column lists (match database/schema.sql)
TECHNICIAN_REPORTS_COLUMNS = [
    "sr",
    "ro_no",
    "mileage",
    "msi",
    "no_of_jobs",
    "reg_no",
    "variant",
    "customer_name",
    "service_adviser",
    "technician_name",
    "bay",
    "operations",
    "creation_time",
    "p_start_time",
    "p_end_time",
    "p_lead_time",
    "gatepass_time",
    "overall_lead_time",
    "remarks",
]

DAILY_CPUS_REPORTS_COLUMNS = [
    "service_date",
    "chassis_number",
    "ro_no",
    "service_nature",
    "campaign_type",
    "customer_source",
    "customer_name",
    "customer_cnic",
    "customer_ntn",
    "customer_dob",
    "customer_mobile_no",
    "customer_landline_number",
    "customer_mobile_no2",
    "customer_email",
    "customer_type",
    "house_no",
    "street_no",
    "city_of_residence",
    "postal_code",
    "insurance_status",
    "insurance_company",
    "insurance_expiry_date",
    "labour_sales",
    "parts_sales",
    "sublet_sales",
    "odometer_reading",
    "vehicle_type",
    "model_year",
    "reg_no",
    "service_sub_category",
    "vehicle_make",
    "receiving_date_time",
    "delivery_date_time",
    "promised_date_time",
    "prefered_date_time_for_psfu",
    "voc",
    "sa_ta_instructions",
    "job_performed_by_technicians",
    "controller_remarks",
    "service_avisor_name",
    "technical_advisor_name",
    "job_controller_name",
    "technician_name",
    "vehicle_variant",
    "imc_vehic",
    "status",
]

# ---------------------------
# Connection helpers
# ---------------------------

def get_connection_pool() -> MySQLConnectionPool:
    """Lazy-initialize and return a MySQLConnectionPool singleton.

    Returns:
        MySQLConnectionPool: initialized pool

    Raises:
        MySQLError: if pool creation fails
    """
    global _connection_pool
    if _connection_pool is None:
        with _pool_lock:
            if _connection_pool is None:
                try:
                    logger.info("Initializing MySQL connection pool: %s (size=%s)", POOL_NAME, POOL_SIZE)
                    
                    # Create a copy of DB_CONFIG to avoid modifying the original
                    config = DB_CONFIG.copy()
                    
                    # Try to create pool with auth_plugin first, fallback if not supported
                    try:
                        config['auth_plugin'] = 'mysql_native_password'
                        _connection_pool = MySQLConnectionPool(
                            pool_name=POOL_NAME,
                            pool_size=POOL_SIZE,
                            pool_reset_session=POOL_RESET_SESSION,
                            **config,
                        )
                    except TypeError:
                        # auth_plugin parameter not supported in this version
                        logger.debug("auth_plugin parameter not supported, retrying without it")
                        config.pop('auth_plugin', None)
                        _connection_pool = MySQLConnectionPool(
                            pool_name=POOL_NAME,
                            pool_size=POOL_SIZE,
                            pool_reset_session=POOL_RESET_SESSION,
                            **config,
                        )
                except MySQLError as e:
                    logger.critical("Failed to create connection pool: %s", e)
                    raise
    return _connection_pool


@contextmanager
def get_connection():
    """Context manager that yields a connection from the pool and returns it when done.

    Usage:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(...)
    """
    pool = get_connection_pool()
    conn = None
    try:
        conn = pool.get_connection()
        yield conn
    except MySQLError as e:
        logger.error("Database connection error: %s", e)
        raise
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                logger.exception("Error closing connection")


# ---------------------------
# Core query functions
# ---------------------------

def run_query(sql: str, params: Optional[Tuple] = None, fetch: bool = True, commit: bool = True) -> Union[List[Dict[str, Any]], int]:
    """Execute a parameterized SQL query using a pooled connection.

    Args:
        sql: SQL string with %s placeholders
        params: tuple/list of parameters
        fetch: whether to fetch results (for SELECT)
        commit: whether to commit (for INSERT/UPDATE/DELETE)

    Returns:
        For fetch=True: list of row dicts. Otherwise: number of affected rows.

    Raises:
        MySQLError on failures (after rollback)
    """
    results: List[Dict[str, Any]] = []
    with get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(sql, params or ())
            if fetch:
                results = cursor.fetchall()
            if commit:
                conn.commit()
            if fetch:
                return results
            return cursor.rowcount
        except MySQLError as e:
            logger.error("Query execution failed: %s | SQL: %s | Params: %s", e, sql, params)
            try:
                conn.rollback()
            except Exception:
                logger.exception("Rollback failed")
            raise
        finally:
            try:
                cursor.close()
            except Exception:
                pass


def run_query_many(sql: str, params_list: List[Tuple]) -> int:
    """Execute many parameter sets using executemany for bulk operations.

    Args:
        sql: SQL string with %s placeholders
        params_list: list of parameter tuples

    Returns:
        Number of affected rows (sum of rowcounts)
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.executemany(sql, params_list)
            conn.commit()
            return cursor.rowcount
        except MySQLError as e:
            logger.error("Bulk execution failed: %s | SQL: %s", e, sql)
            try:
                conn.rollback()
            except Exception:
                logger.exception("Rollback failed during bulk")
            raise
        finally:
            try:
                cursor.close()
            except Exception:
                pass


# ---------------------------
# CSV and parsing helpers
# ---------------------------

def read_csv_file(file_path: str, encoding: str = "utf-8") -> pd.DataFrame:
    """Read a CSV into a pandas DataFrame with basic cleanup.

    Args:
        file_path: path to CSV
        encoding: file encoding

    Returns:
        DataFrame
    """
    try:
        df = pd.read_csv(file_path, encoding=encoding)
        df.columns = df.columns.str.strip()
        logger.info("Read CSV %s with %s rows", file_path, len(df))
        return df
    except FileNotFoundError as e:
        logger.error("CSV file not found: %s", file_path)
        raise
    except pd.errors.ParserError as e:
        logger.error("CSV parse error for %s: %s", file_path, e)
        raise


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize DataFrame for DB insertion.

    Operations:
    - Strip whitespace from string columns
    - Replace NaN with None
    - Normalize column names to snake_case-ish (handles newlines, dots, spaces)
    """
    df = df.copy()
    # Normalize column names using the centralized function
    df.columns = [normalize_column_name(c) for c in df.columns]

    # Strip strings
    for col in df.select_dtypes(include=[object]).columns:
        df[col] = df[col].astype(str).str.strip().replace({'nan': None})

    # Replace NaN with None
    df = df.where(pd.notnull(df), None)
    return df


def dataframe_to_dict_list(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Convert DataFrame to list of dicts with basic type normalization."""
    records = df.to_dict(orient="records")
    # Convert numpy types to native python types
    cleaned: List[Dict[str, Any]] = []
    for r in records:
        nr: Dict[str, Any] = {}
        for k, v in r.items():
            if pd.isna(v):
                nr[k] = None
            elif isinstance(v, (pd.Timestamp, datetime)):
                nr[k] = v.to_pydatetime() if isinstance(v, pd.Timestamp) else v
            elif isinstance(v, Decimal):
                nr[k] = v
            else:
                nr[k] = v
        cleaned.append(nr)
    return cleaned


def parse_time_string(time_str: Optional[str]) -> Optional[time]:
    if time_str is None:
        return None
    s = str(time_str).strip()
    if not s:
        return None
    formats = ["%H:%M:%S", "%H:%M", "%I:%M %p", "%H:%M:%S.%f"]
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).time()
        except Exception:
            continue
    logger.debug("Unparseable time string: %s", time_str)
    return None


def parse_date_string(date_str: Optional[str]) -> Optional[date]:
    if date_str is None:
        return None
    s = str(date_str).strip()
    if not s:
        return None
    formats = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue
    logger.debug("Unparseable date string: %s", date_str)
    return None


def parse_datetime_string(dt_str: Optional[str]) -> Optional[datetime]:
    if dt_str is None:
        return None
    s = str(dt_str).strip()
    if not s:
        return None
    formats = [
        "%Y-%m-%d %H:%M:%S.%f",  # Handles milliseconds (e.g., 2025-11-04 09:21:00.142)
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d-%m-%Y %H:%M:%S",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    logger.debug("Unparseable datetime string: %s", dt_str)
    return None


# ---------------------------
# Insert helpers
# ---------------------------

# Normalized table functions removed per denormalized schema migration.


def insert_repeat_repairs(repeat_repairs_data: List[Dict[str, Any]]) -> int:
    if not repeat_repairs_data:
        return 0
    sql = "INSERT INTO repeat_repairs (date, total_vehicle_delivered, repeat_repair_count, repeat_repair_percentage) VALUES (%s,%s,%s,%s) ON DUPLICATE KEY UPDATE total_vehicle_delivered=VALUES(total_vehicle_delivered), repeat_repair_count=VALUES(repeat_repair_count), repeat_repair_percentage=VALUES(repeat_repair_percentage)"
    params_list = []
    for d in repeat_repairs_data:
        dt = d.get("date")
        if isinstance(dt, str):
            dt = parse_date_string(dt)
        pct = d.get("repeat_repair_percentage")
        if pct is None:
            pct = 0
        params_list.append((dt, d.get("total_vehicle_delivered"), d.get("repeat_repair_count"), Decimal(str(pct))))
    return run_query_many(sql, params_list)
    return run_query_many(sql, params_list)


def insert_technician_reports(tech_reports: List[Dict[str, Any]]) -> int:
    """Bulk insert into denormalized technician_reports table.

    Expects dicts matching TECHNICIAN_REPORTS_COLUMNS keys. 'created_at' and 'id' are handled by DB.
    """
    if not tech_reports:
        return 0
    
    # ===== VALIDATE AND CLEAN RO_NO BEFORE INSERTION =====
    # Ensure ro_no is not stored as decimal in varchar (e.g., "237270.0" should be "237270")
    cleaned_reports = []
    for report in tech_reports:
        cleaned_report = report.copy()
        if 'ro_no' in cleaned_report and cleaned_report['ro_no'] is not None:
            ro_no_val = str(cleaned_report['ro_no']).strip()
            # If it looks like a decimal (ends with .0, .00, etc), remove the decimal part
            if '.' in ro_no_val:
                try:
                    # Convert to float then to int to remove trailing .0
                    as_float = float(ro_no_val)
                    as_int = int(as_float)
                    # Only clean if it was a whole number (e.g., 237270.0)
                    if as_float == as_int:
                        cleaned_report['ro_no'] = str(as_int)
                except (ValueError, TypeError):
                    # Keep original value if conversion fails
                    pass
        cleaned_reports.append(cleaned_report)
    
    cols = TECHNICIAN_REPORTS_COLUMNS
    columns_sql = ",".join(cols)
    placeholders = ",".join(["%s"] * len(cols))
    sql = f"INSERT INTO technician_reports ({columns_sql}) VALUES ({placeholders})"

    params_list: List[Tuple] = []
    for d in cleaned_reports:
        row: List[Any] = []
        for c in cols:
            v = d.get(c)
            if c in ("creation_time", "p_start_time", "p_end_time", "p_lead_time", "gatepass_time", "overall_lead_time") and isinstance(v, str):
                v = parse_time_string(v)
            if c in ("mileage", "no_of_jobs") and v is not None:
                try:
                    v = int(v)
                except Exception:
                    v = None
            row.append(v)
        params_list.append(tuple(row))
    return run_query_many(sql, params_list)


def insert_daily_cpus_reports(daily_reports: List[Dict[str, Any]]) -> int:
    """Bulk insert into denormalized daily_cpus_reports table.

    Expects dicts matching DAILY_CPUS_REPORTS_COLUMNS keys. 'created_at' and 'id' are handled by DB.
    Uses a straightforward INSERT; repeat runs may create duplicates unless deduped upstream.
    """
    if not daily_reports:
        return 0
    
    # ===== VALIDATE AND CLEAN RO_NO BEFORE INSERTION =====
    # Ensure ro_no is not stored as decimal in varchar (e.g., "237270.0" should be "237270")
    cleaned_reports = []
    for report in daily_reports:
        cleaned_report = report.copy()
        if 'ro_no' in cleaned_report and cleaned_report['ro_no'] is not None:
            ro_no_val = str(cleaned_report['ro_no']).strip()
            # If it looks like a decimal (ends with .0, .00, etc), remove the decimal part
            if '.' in ro_no_val:
                try:
                    # Convert to float then to int to remove trailing .0
                    as_float = float(ro_no_val)
                    as_int = int(as_float)
                    # Only clean if it was a whole number (e.g., 237270.0)
                    if as_float == as_int:
                        cleaned_report['ro_no'] = str(as_int)
                except (ValueError, TypeError):
                    # Keep original value if conversion fails
                    pass
        cleaned_reports.append(cleaned_report)
    
    cols = DAILY_CPUS_REPORTS_COLUMNS
    columns_sql = ",".join(cols)
    placeholders = ",".join(["%s"] * len(cols))
    sql = f"INSERT INTO daily_cpus_reports ({columns_sql}) VALUES ({placeholders})"

    params_list: List[Tuple] = []
    for d in cleaned_reports:
        row: List[Any] = []
        for c in cols:
            v = d.get(c)
            if c in ("service_date", "customer_dob", "insurance_expiry_date") and isinstance(v, str):
                v = parse_date_string(v)
            if c in ("receiving_date_time", "delivery_date_time", "promised_date_time", "prefered_date_time_for_psfu") and isinstance(v, str):
                v = parse_datetime_string(v)
            if c in ("labour_sales", "parts_sales", "sublet_sales") and v is not None:
                try:
                    v = Decimal(str(v))
                except Exception:
                    v = None
            if c == "odometer_reading" and v is not None:
                try:
                    v = int(v)
                except Exception:
                    v = None
            row.append(v)
        params_list.append(tuple(row))
    return run_query_many(sql, params_list)


# ---------------------------
# Retrieval helpers for denormalized tables
# ---------------------------

def _build_where_clause(filters: Optional[Dict[str, Any]]) -> Tuple[str, List[Any]]:
    """Build a simple WHERE clause from a dict of equality filters.

    Returns (clause_sql, params_list) where clause_sql is like " WHERE a=%s AND b=%s" or empty string.
    """
    if not filters:
        return ("", [])
    clauses: List[str] = []
    params: List[Any] = []
    # NOTE: caller must pass only validated/allowed filter keys. This helper will perform no
    # additional escaping of column names. To prevent unsafe SQL, callers should use
    # allowed_columns (see fetch_technician_reports / fetch_daily_cpus_reports) and validate keys
    # before calling this function. Here we assume keys are safe column names.
    for k, v in filters.items():
        clauses.append(f"{k} = %s")
        params.append(v)
    return (" WHERE " + " AND ".join(clauses), params)


def fetch_technician_reports(filters: Optional[Dict[str, Any]] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Fetch rows from `technician_reports` with optional equality filters and limit."""
    base = "SELECT * FROM technician_reports"
    # allowlist: only permit known columns from the denormalized schema
    allowed = set(TECHNICIAN_REPORTS_COLUMNS)
    # validate filter keys
    if filters:
        invalid = [k for k in filters.keys() if k not in allowed]
        if invalid:
            raise ValueError(f"Invalid filter keys for technician_reports: {invalid}")
    where_sql, params = _build_where_clause(filters)
    sql = base + where_sql
    if limit:
        sql += f" LIMIT {int(limit)}"
    logger.debug("fetch_technician_reports SQL: %s | params=%s", sql, params)
    return run_query(sql, params=tuple(params), fetch=True, commit=False)


def fetch_daily_cpus_reports(filters: Optional[Dict[str, Any]] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Fetch rows from `daily_cpus_reports` with optional equality filters and limit."""
    base = "SELECT * FROM daily_cpus_reports"
    # allowlist: only permit known columns from the denormalized schema
    allowed = set(DAILY_CPUS_REPORTS_COLUMNS)
    if filters:
        invalid = [k for k in filters.keys() if k not in allowed]
        if invalid:
            raise ValueError(f"Invalid filter keys for daily_cpus_reports: {invalid}")
    where_sql, params = _build_where_clause(filters)
    sql = base + where_sql
    if limit:
        sql += f" LIMIT {int(limit)}"
    logger.debug("fetch_daily_cpus_reports SQL: %s | params=%s", sql, params)
    return run_query(sql, params=tuple(params), fetch=True, commit=False)


def fetch_technician_reports_by_date_range(start_date: date, end_date: date, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Fetch technician reports joined with service_date from daily_cpus_reports via ro_no within a date range."""
    sql = (
        "SELECT t.*, d.service_date FROM technician_reports t "
        "LEFT JOIN daily_cpus_reports d ON t.ro_no = d.ro_no "
        "WHERE d.service_date BETWEEN %s AND %s ORDER BY d.service_date DESC"
    )
    if limit:
        sql += f" LIMIT {int(limit)}"
    logger.debug("fetch_technician_reports_by_date_range SQL: %s | params=(%s,%s)", sql, start_date, end_date)
    return run_query(sql, params=(start_date, end_date), fetch=True, commit=False)


def fetch_daily_cpus_summary(service_date: date) -> Dict[str, Any]:
    """Aggregate basic summary metrics for a given service_date from daily_cpus_reports."""
    sql = (
        "SELECT COUNT(DISTINCT ro_no) AS ro_count, COUNT(*) AS rows, "
        "COALESCE(SUM(labour_sales),0) AS total_labour_sales, COALESCE(SUM(parts_sales),0) AS total_parts_sales, "
        "COALESCE(SUM(sublet_sales),0) AS total_sublet_sales "
        "FROM daily_cpus_reports WHERE service_date = %s"
    )
    rows = run_query(sql, params=(service_date,), fetch=True, commit=False)
    return rows[0] if rows else {}

# keep fetch_repeat_repairs (defined below) for repeat metrics retrieval


def fetch_repeat_repairs(start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[Dict[str, Any]]:
    """Retrieve rows from `repeat_repairs` optionally filtered by date range, ordered desc."""
    sql = "SELECT * FROM repeat_repairs"
    params: List[Any] = []
    if start_date or end_date:
        clauses: List[str] = []
        if start_date:
            clauses.append("date >= %s"); params.append(start_date)
        if end_date:
            clauses.append("date <= %s"); params.append(end_date)
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY date DESC"
    return run_query(sql, params=tuple(params), fetch=True, commit=False)


# ---------------------------
# Utilities
# ---------------------------

def test_connection() -> bool:
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            _ = cursor.fetchone()
            cursor.close()
        logger.info("Database connection test succeeded")
        return True
    except Exception as e:
        logger.exception("Database connection test failed: %s", e)
        return False


def ensure_database_exists() -> None:
    """If the configured database doesn't exist, attempt to create it.

    This tries to connect; if a ProgrammingError 1049 (Unknown database) occurs,
    it will connect without the database and run CREATE DATABASE IF NOT EXISTS.
    Requires that the configured user has privileges to create databases.
    """
    db_name = DB_CONFIG.get("database")
    if not db_name:
        logger.debug("No database configured; skipping ensure_database_exists")
        return
    # Try to connect directly with the configured database first
    connect_kwargs = {
        "host": DB_CONFIG.get("host"),
        "user": DB_CONFIG.get("user"),
        "password": DB_CONFIG.get("password"),
    }
    if DB_CONFIG.get("port"):
        try:
            connect_kwargs["port"] = int(DB_CONFIG.get("port"))
        except Exception:
            pass
    if DB_CONFIG.get("charset"):
        connect_kwargs["charset"] = DB_CONFIG.get("charset")
    if DB_CONFIG.get("use_unicode") is not None:
        connect_kwargs["use_unicode"] = DB_CONFIG.get("use_unicode")

    try:
        # attempt to connect to the target database; if it exists this will succeed
        conn = mysql.connector.connect(database=db_name, **connect_kwargs)
        conn.close()
        logger.info("Database '%s' already exists and is reachable", db_name)
        return
    except MySQLError as e:
        # If error indicates unknown database (errno 1049), try to create it
        err_no = getattr(e, "errno", None)
        if err_no != 1049:
            logger.exception("Unexpected error while checking database: %s", e)
            raise

    logger.info("Attempting to create database if missing: %s", db_name)
    # Connect without specifying database and create it
    try:
        no_db_kwargs = connect_kwargs.copy()
        # remove port if it's None already handled above
        conn = mysql.connector.connect(**no_db_kwargs)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("Database ensured: %s", db_name)
        # Clear any existing pool so it will be recreated with the new DB
        global _connection_pool
        _connection_pool = None
    except MySQLError as e:
        logger.exception("Failed to ensure database exists: %s", e)
        raise


def close_pool() -> None:
    global _connection_pool
    if _connection_pool is not None:
        try:
            # mysql-connector pool does not expose close_all; connections close when program ends
            _connection_pool = None
            logger.info("Connection pool reference cleared")
        except Exception:
            logger.exception("Error closing pool")


def execute_sql_file(file_path: str) -> int:
    """Execute semicolon-separated SQL statements from a file.

    Returns number of successfully executed statements.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as fh:
            content = fh.read()
    except Exception as e:
        logger.error("Failed to read SQL file %s: %s", file_path, e)
        raise

    # Remove block comments (/* ... */) and strip single-line '--' comments
    try:
        content = re.sub(r"/\*.*?\*/", "", content, flags=re.S)
    except Exception:
        # fallback: leave content as-is
        pass

    cleaned_lines: List[str] = []
    for line in content.splitlines():
        s = line.strip()
        # skip SQL single-line comments that start with --
        if not s:
            continue
        if s.startswith("--"):
            continue
        cleaned_lines.append(line)

    cleaned = "\n".join(cleaned_lines)
    statements = [s.strip() for s in cleaned.split(";") if s.strip()]
    executed = 0
    for stmt in statements:
        try:
            run_query(stmt, fetch=False, commit=True)
            executed += 1
        except Exception:
            logger.exception("Failed to execute statement: %s", stmt)
            continue
    logger.info("Executed %s statements from %s", executed, file_path)
    return executed


def process_database_files(daily_csv_path: str, tech_csv_path: str, repeat_xlsx_path: str = None) -> Dict[str, Any]:
    """
    Main orchestration function that processes input files and performs all database operations.
    
    This is the single entry point for all database operations. It:
    1. Auto-locates schema.sql in the database directory
    2. Ensures database and tables exist (via schema.sql)
    3. Loads daily CPUs reports from CSV
    4. Loads technician reports from CSV
    5. Loads repeat repair data from XLSX (optional)
    
    Args:
        daily_csv_path (str): Path to daily CPUs CSV file
        tech_csv_path (str): Path to technician reports CSV file
        repeat_xlsx_path (str, optional): Path to repeat repair XLSX file
    
    Returns:
        Dict with keys:
            - "success" (bool): True if all operations completed without critical errors
            - "status" (str): Human-readable status message
            - "data" (dict): Statistics about inserted rows:
                - "daily_cpus_reports" (int): Number of daily records inserted
                - "technician_reports" (int): Number of technician records inserted
                - "repeat_repairs" (int): Number of repeat repair records inserted
                - "tables_created" (int): Number of SQL statements executed
            - "error" (str or None): Error message if success=False
    """
    result = {
        "success": False,
        "status": "",
        "data": {
            "daily_cpus_reports": 0,
            "technician_reports": 0,
            "repeat_repairs": 0,
            "tables_created": 0,
        },
        "error": None,
    }
    
    try:
        from pathlib import Path
        
        # Auto-locate schema.sql in database directory
        db_dir = Path(__file__).resolve().parent.parent  # Navigate from lib/db.py to database/
        schema_sql_path = db_dir / "schema.sql"
        if not schema_sql_path.exists():
            raise FileNotFoundError(f"Schema SQL file not found at: {schema_sql_path}")
        
        logger.info("Starting database processing: daily_csv=%s, tech_csv=%s", 
                    daily_csv_path, tech_csv_path)
        logger.info("Auto-located schema at: %s", schema_sql_path)
        
        # Step 1: Test database connection
        logger.info("Testing database connection...")
        if not test_connection():
            raise RuntimeError("Database connection test failed")
        logger.info("✓ Database connection successful")
        
        # Step 2: Ensure database exists
        logger.info("Ensuring database exists...")
        try:
            ensure_database_exists()
            logger.info("✓ Database ready")
        except Exception as e:
            logger.warning("Database creation attempted (may already exist): %s", e)
        
        # Step 3: Execute schema SQL to create tables
        logger.info("Creating/updating database schema from %s", schema_sql_path)
        try:
            tables_created = execute_sql_file(str(schema_sql_path))
            result["data"]["tables_created"] = tables_created
            logger.info("✓ Schema executed: %d statements", tables_created)
        except Exception as e:
            raise RuntimeError(f"Failed to execute schema SQL: {e}")
        
        # Step 4: Load daily CPUs reports
        logger.info("Loading daily CPUs reports from %s", daily_csv_path)
        try:
            daily_path = Path(daily_csv_path)
            if not daily_path.exists():
                raise FileNotFoundError(f"Daily CSV file not found: {daily_csv_path}")
            
            # Read CSV with column mapping
            df = pd.read_csv(str(daily_path), dtype=object)
            
            # Match columns to expected schema
            norm_map = {normalize_column_name(c): c for c in df.columns}
            mapping = {}
            for expected in DAILY_CPUS_REPORTS_COLUMNS:
                key = normalize_column_name(expected)
                if key in norm_map:
                    mapping[expected] = norm_map[key]
                # Handle special mappings (e.g., service_advisor_name -> service_avisor_name)
                elif expected == "service_advisor_name":
                    special_key = normalize_column_name("service_avisor_name")
                    if special_key in norm_map:
                        mapping[expected] = norm_map[special_key]
            
            # Build records
            records = []
            for _, row in df.iterrows():
                rec = {c: None for c in DAILY_CPUS_REPORTS_COLUMNS}
                for exp_col, src_col in mapping.items():
                    val = row.get(src_col)
                    if pd.isna(val):
                        val = None
                    rec[exp_col] = val
                records.append(rec)
            
            if records:
                inserted = insert_daily_cpus_reports(records)
                result["data"]["daily_cpus_reports"] = inserted
                logger.info("✓ Inserted %d daily CPUs reports", inserted)
            else:
                logger.warning("No records found in daily CPUs CSV")
        except Exception as e:
            logger.exception("Failed to load daily CPUs reports")
            result["error"] = f"Daily CPUs load error: {e}"
            return result
        
        # Step 5: Load technician reports
        logger.info("Loading technician reports from %s", tech_csv_path)
        try:
            tech_path = Path(tech_csv_path)
            if not tech_path.exists():
                raise FileNotFoundError(f"Technician CSV file not found: {tech_csv_path}")
            
            # Read CSV with column mapping
            df = pd.read_csv(str(tech_path), dtype=object)
            
            # Match columns to expected schema
            norm_map = {normalize_column_name(c): c for c in df.columns}
            mapping = {}
            for expected in TECHNICIAN_REPORTS_COLUMNS:
                key = normalize_column_name(expected)
                if key in norm_map:
                    mapping[expected] = norm_map[key]
            
            # Build records
            records = []
            for _, row in df.iterrows():
                rec = {c: None for c in TECHNICIAN_REPORTS_COLUMNS}
                for exp_col, src_col in mapping.items():
                    val = row.get(src_col)
                    if pd.isna(val):
                        val = None
                    rec[exp_col] = val
                records.append(rec)
            
            if records:
                inserted = insert_technician_reports(records)
                result["data"]["technician_reports"] = inserted
                logger.info("✓ Inserted %d technician reports", inserted)
            else:
                logger.warning("No records found in technician CSV")
        except Exception as e:
            logger.exception("Failed to load technician reports")
            result["error"] = f"Technician reports load error: {e}"
            return result
        
        # Step 6: Load repeat repair data from XLSX or CSV (optional)
        if repeat_xlsx_path:
            logger.info("Loading repeat repair data from %s", repeat_xlsx_path)
            try:
                repeat_path = Path(repeat_xlsx_path)
                if not repeat_path.exists():
                    logger.warning("Repeat repair file not found: %s (skipping)", repeat_xlsx_path)
                else:
                    # Detect file format and read accordingly
                    file_ext = repeat_path.suffix.lower()
                    
                    if file_ext == '.csv':
                        # Read CSV format
                        df = pd.read_csv(str(repeat_path), dtype=object)
                    else:
                        # Try to read XLSX - try to read "All Tables" sheet first, then first sheet
                        try:
                            df = pd.read_excel(str(repeat_path), sheet_name="All Tables", dtype=object)
                        except Exception:
                            # If "All Tables" sheet doesn't exist, read first sheet
                            df = pd.read_excel(str(repeat_path), sheet_name=0, dtype=object)
                    
                    # Parse and validate repeat repair records
                    parsed_records = []
                    for rec in df.fillna('').to_dict(orient='records'):
                        # Extract date field (handle various column names)
                        d_raw = rec.get('Date') or rec.get('date') or rec.get('SERVICE_DATE')
                        total = rec.get('Total Vehicle Delivered') or rec.get('total_vehicle_delivered')
                        repeat_count = rec.get('Repeat Repair Count') or rec.get('repeat_repair_count')
                        pct = rec.get('Repeat Repair %age') or rec.get('repeat_repair_percentage')
                        
                        # Parse date
                        d_parsed = None
                        if isinstance(d_raw, str) and d_raw:
                            d_parsed = parse_date_string(d_raw)
                            if d_parsed is None:
                                try:
                                    ts = pd.to_datetime(d_raw, dayfirst=False, errors='coerce')
                                    if not pd.isna(ts):
                                        d_parsed = ts.date()
                                except Exception:
                                    pass
                        
                        if d_parsed is None:
                            continue
                        
                        # Coerce numeric fields
                        try:
                            total_i = int(str(total)) if total not in (None, '') else None
                        except Exception:
                            total_i = None
                        
                        try:
                            repeat_i = int(str(repeat_count)) if repeat_count not in (None, '') else None
                        except Exception:
                            repeat_i = None
                        
                        try:
                            pct_d = Decimal(str(pct)) if pct not in (None, '') else Decimal('0')
                        except Exception:
                            pct_d = Decimal('0')
                        
                        parsed_records.append({
                            'date': d_parsed,
                            'total_vehicle_delivered': total_i,
                            'repeat_repair_count': repeat_i,
                            'repeat_repair_percentage': pct_d,
                        })
                    
                    if parsed_records:
                        inserted = insert_repeat_repairs(parsed_records)
                        result["data"]["repeat_repairs"] = inserted
                        logger.info("✓ Inserted %d repeat repair records from XLSX", inserted)
                    else:
                        logger.warning("No valid records found in repeat repair XLSX")
            except Exception as e:
                logger.exception("Failed to load repeat repair data")
                result["error"] = f"Repeat repair load error: {e}"
                return result
        else:
            logger.info("Repeat repair XLSX path not provided (skipping)")
        
        # All steps completed successfully
        result["success"] = True
        result["status"] = "All database operations completed successfully"
        logger.info("✓✓✓ Database processing complete: %s", result["data"])
        
    except Exception as e:
        logger.exception("Unhandled error in process_database_files")
        result["success"] = False
        result["status"] = "Database processing failed"
        result["error"] = str(e)
    
    return result
