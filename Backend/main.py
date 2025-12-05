"""
Toyota PDF Processing API - Main Application

FastAPI application for uploading, converting, and cleaning Toyota service reports.
Supports three types of reports with automatic processing and validation.

Author: Toyota Service Analytics Team
Version: 4.0.0
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime
import logging
import traceback

# Import configuration
from Backend.config import UPLOAD_DIR, CLEANED_DIR, ALLOWED_ORIGINS

# Import worker module
from Backend.workers.convertandclean import process_reports
from Backend.workers.sync_from_csv_folder import main as sync_database

# ============================================================================
# PLACEHOLDER FUNCTION - REPLACE WITH YOUR DATABASE QUERY FUNCTION
# ============================================================================

def get_jobs_overview():
    """
    API 1 Helper Function: Get jobs overview with technician performance metrics.

    Retrieves all jobs (no date restriction) with technician efficiency rankings.

    Returns:
        Dictionary with keys:
        {
            "num_total_jobs": int,  # Total jobs (all time)
            "total_technicians": int,  # Total number of unique technicians
            "job_data": [  # Array of objects with technician rankings
                {
                    "position": int,
                    "technician": str,
                    "efficiency_percent": float,
                    "on_time": int,
                    "total_jobs": int
                },
                ...
            ]
        }
    """
    try:
        from database.lib.db import run_query
        from datetime import date
        import calendar
        
        # Get all data for the entire database
        # Use a very old date and future date to capture all records
        from_date = date(2000, 1, 1)
        to_date = date(2099, 12, 31)
        
        # Query total jobs (all time)
        total_query = "SELECT COUNT(DISTINCT ro_no) as total FROM daily_cpus_reports"
        total_result = run_query(total_query, fetch=True, commit=False)
        num_total_jobs = total_result[0]['total'] if total_result and total_result[0].get('total') else 0
        
        # Query total technicians (exclude NULL and 'Unassigned')
        tech_query = "SELECT COUNT(DISTINCT technician_name) as total FROM daily_cpus_reports WHERE technician_name IS NOT NULL AND technician_name != 'Unassigned'"
        tech_result = run_query(tech_query, fetch=True, commit=False)
        total_technicians = tech_result[0]['total'] if tech_result and tech_result[0].get('total') else 0
        
        # Query technician efficiency rankings (exclude NULL and 'Unassigned')
        performance_query = '''
            SELECT 
                technician_name,
                COUNT(DISTINCT ro_no) as total_jobs,
                SUM(CASE WHEN status IN ('On-time', 'on-time', 'on_time') THEN 1 ELSE 0 END) as on_time_jobs,
                ROUND(
                    (SUM(CASE WHEN status IN ('On-time', 'on-time', 'on_time') THEN 1 ELSE 0 END) * 100.0) / 
                    COUNT(DISTINCT ro_no), 
                    2
                ) as efficiency_percent
            FROM daily_cpus_reports
            WHERE technician_name IS NOT NULL AND technician_name != 'Unassigned'
            GROUP BY technician_name
            ORDER BY efficiency_percent DESC, total_jobs DESC
        '''
        performance_result = run_query(performance_query, fetch=True, commit=False)
        
        # Format as table with position ranking
        job_data = []
        if performance_result:
            job_data = [
                {
                    "position": idx + 1,
                    "technician": str(r.get('technician_name', 'Unknown')),
                    "efficiency_percent": float(r.get('efficiency_percent', 0.0)),
                    "on_time": int(r.get('on_time_jobs', 0)),
                    "total_jobs": int(r.get('total_jobs', 0))
                }
                for idx, r in enumerate(performance_result)
            ]
        
        return {
            "num_total_jobs": num_total_jobs,
            "total_technicians": total_technicians,
            "job_data": job_data
        }
    
    except Exception as e:
        logger.error(f"Error in get_jobs_overview: {str(e)}")
        # Return empty structure on error
        return {
            "num_total_jobs": 0,
            "total_technicians": 0,
            "job_data": []
        }


def get_technician_performance(name: str, start_date: str, end_date: str):
    """
    API 2 Helper Function: Get specific technician's performance metrics.

    Retrieves performance stats for a technician within a date range.

    Args:
        name: Technician name
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        Dictionary with keys:
        {
            "late_jobs": int,      # Number of late jobs
            "ontime_jobs": int,    # Number of on-time jobs
            "grace_jobs": int,     # Number of grace period jobs
            "total_jobs": int      # Total jobs for this technician
        }
    """
    try:
        from database.lib.db import run_query
        from datetime import datetime as dt
        
        # Parse dates
        start_dt = dt.strptime(start_date, "%Y-%m-%d").date()
        end_dt = dt.strptime(end_date, "%Y-%m-%d").date()
        
        # Query technician performance stats within date range
        # Only retrieve stats if technician_name is not NULL or 'Unassigned'
        stats_query = '''
            SELECT
                COUNT(DISTINCT ro_no) as total,
                SUM(CASE WHEN status='Late' THEN 1 ELSE 0 END) as late,
                SUM(CASE WHEN status IN ('On-time', 'on-time', 'on_time') THEN 1 ELSE 0 END) as ontime,
                SUM(CASE WHEN status='Grace' THEN 1 ELSE 0 END) as grace
            FROM daily_cpus_reports
            WHERE DATE(service_date) BETWEEN %s AND %s
            AND technician_name = %s
            AND technician_name IS NOT NULL
            AND technician_name != 'Unassigned'
        '''
        stats_result = run_query(stats_query, (start_dt, end_dt, name), fetch=True, commit=False)
        
        stats = stats_result[0] if stats_result and stats_result[0] else {}
        
        return {
            "late_jobs": int(stats.get('late') or 0),
            "ontime_jobs": int(stats.get('ontime') or 0),
            "grace_jobs": int(stats.get('grace') or 0),
            "total_jobs": int(stats.get('total') or 0)
        }
    
    except Exception as e:
        logger.error(f"Error in get_technician_performance: {str(e)}")
        return {
            "late_jobs": 0,
            "ontime_jobs": 0,
            "grace_jobs": 0,
            "total_jobs": 0
        }


def get_msi_data(category: str):
    """
    API MSI Helper Function: Get MSI data for a given category.

    Retrieves most/least used operations and performance metrics for an MSI category.
    Combines data from daily_cpus_reports and technician_reports by matching RO numbers.

    Args:
        category: The MSI category to analyze.

    Returns:
        Dictionary with keys:
        {
            "most_used_operation": str,
            "least_used_operation": str,
            "avg_no_of_operations": int,
            "performance_table": [
                {
                    "name": str,
                    "ontime": int,
                    "grace": int,
                    "late": int
                },
                ...
            ]
        }
    """
    try:
        from database.lib.db import run_query
        
        logger.info(f"[get_msi_data] Starting MSI data retrieval for category: '{category}'")
        logger.info(f"[get_msi_data] Step 1: Preparing to query most/least used operations")
        
        # Query 1: Get most and least used operations for this MSI category
        operations_query = '''
            SELECT 
                t.operations,
                COUNT(*) as count
            FROM technician_reports t
            INNER JOIN daily_cpus_reports d ON t.ro_no = d.ro_no
            WHERE UPPER(t.msi) = UPPER(%s)
            AND t.technician_name IS NOT NULL
            GROUP BY t.operations
            ORDER BY count DESC
        '''
        logger.debug(f"[get_msi_data] Query 1 (Operations): {operations_query[:100]}...")
        
        ops_result = run_query(operations_query, (category,), fetch=True, commit=False)
        logger.info(f"[get_msi_data] Query 1 Result: Found {len(ops_result) if ops_result else 0} operations")
        
        most_used_operation = "Unknown"
        least_used_operation = "Unknown"
        
        if ops_result and len(ops_result) > 0:
            most_used_operation = str(ops_result[0].get('operations', 'Unknown'))
            logger.info(f"[get_msi_data] Step 1.1: Most used operation = '{most_used_operation}' (count: {ops_result[0].get('count', 0)})")
            
            if len(ops_result) > 1:
                least_used_operation = str(ops_result[-1].get('operations', 'Unknown'))
                logger.info(f"[get_msi_data] Step 1.2: Least used operation = '{least_used_operation}' (count: {ops_result[-1].get('count', 0)})")
            else:
                least_used_operation = most_used_operation
                logger.info(f"[get_msi_data] Step 1.2: Only 1 operation found, setting least = most")
        else:
            logger.warning(f"[get_msi_data] Step 1: No operations found for category '{category}'")
        
        logger.info(f"[get_msi_data] Step 2: Preparing to query average operations count")
        
        # Query 2: Calculate average number of operations for this MSI category
        avg_query = '''
            SELECT 
                AVG(t.no_of_jobs) as avg_operations
            FROM technician_reports t
            INNER JOIN daily_cpus_reports d ON t.ro_no = d.ro_no
            WHERE UPPER(t.msi) = UPPER(%s)
            AND t.technician_name IS NOT NULL
        '''
        logger.debug(f"[get_msi_data] Query 2 (Average): {avg_query[:100]}...")
        
        avg_result = run_query(avg_query, (category,), fetch=True, commit=False)
        logger.info(f"[get_msi_data] Query 2 Result: Retrieved average operations data")
        
        avg_no_of_operations = int(avg_result[0].get('avg_operations', 0) or 0) if avg_result and avg_result[0] else 0
        logger.info(f"[get_msi_data] Step 2.1: Average operations = {avg_no_of_operations}")
        
        logger.info(f"[get_msi_data] Step 3: Preparing to query operation performance with RO matching")
        
        # Query 3: Get operation performance for this MSI category
        # Group by operations to show performance metrics per operation
        performance_query = '''
            SELECT 
                t.operations,
                SUM(CASE WHEN d.status IN ('On-time', 'on-time', 'on_time', 'On-Time', 'On_time', 'ON-TIME', 'ON_TIME') THEN 1 ELSE 0 END) as ontime,
                SUM(CASE WHEN d.status='Grace' THEN 1 ELSE 0 END) as grace,
                SUM(CASE WHEN d.status='Late' THEN 1 ELSE 0 END) as late
            FROM technician_reports t
            INNER JOIN daily_cpus_reports d ON t.ro_no = d.ro_no
            WHERE UPPER(t.msi) = UPPER(%s)
            AND t.technician_name IS NOT NULL
            GROUP BY t.operations
            ORDER BY ontime DESC
        '''
        logger.debug(f"[get_msi_data] Query 3 (Performance): {performance_query[:100]}...")
        logger.info(f"[get_msi_data] Step 3.1: Using INNER JOIN on ro_no for RO matching")
        
        perf_result = run_query(performance_query, (category,), fetch=True, commit=False)
        logger.info(f"[get_msi_data] Query 3 Result: Found {len(perf_result) if perf_result else 0} operations")
        
        performance_table = []
        if perf_result:
            logger.info(f"[get_msi_data] Step 3.2: Processing {len(perf_result)} operation records")
            performance_table = []
            for idx, r in enumerate(perf_result):
                operation_name = str(r.get('operations', 'Unknown'))
                ontime = int(r.get('ontime', 0) or 0)
                grace = int(r.get('grace', 0) or 0)
                late = int(r.get('late', 0) or 0)
                
                logger.debug(f"[get_msi_data] Step 3.2.{idx+1}: {operation_name} - On-time: {ontime}, Grace: {grace}, Late: {late}")
                
                performance_table.append({
                    "name": operation_name,
                    "ontime": ontime,
                    "grace": grace,
                    "late": late
                })
            logger.info(f"[get_msi_data] Step 3.3: Processed {len(performance_table)} technician records into performance table")
        else:
            logger.warning(f"[get_msi_data] Step 3: No technician performance data found for category '{category}'")
        
        logger.info(f"[get_msi_data] Step 4: Preparing final response")
        final_response = {
            "most_used_operation": most_used_operation,
            "least_used_operation": least_used_operation,
            "avg_no_of_operations": avg_no_of_operations,
            "performance_table": performance_table
        }
        logger.info(f"[get_msi_data] Completed successfully:")
        logger.info(f"  - Most Used Operation: {most_used_operation}")
        logger.info(f"  - Least Used Operation: {least_used_operation}")
        logger.info(f"  - Average Operations: {avg_no_of_operations}")
        logger.info(f"  - Performance Table Size: {len(performance_table)} technicians")
        logger.info(f"[get_msi_data] Total execution time completed for category '{category}'")
        
        return final_response
    
    except Exception as e:
        logger.error(f"[get_msi_data] ERROR in get_msi_data for category '{category}': {str(e)}")
        logger.error(f"[get_msi_data] Exception type: {type(e).__name__}")
        logger.exception(f"[get_msi_data] Full exception traceback:")
        return {
            "most_used_operation": "Unknown",
            "least_used_operation": "Unknown",
            "avg_no_of_operations": 0,
            "performance_table": []
        }


def get_rework_rate_data():
    """
    API Rework Rate Helper Function: Get rework rate metrics and monthly breakdown.

    Retrieves repeat repair data with monthly breakdown statistics.
    Uses repeat_repairs table which tracks vehicles delivered and rework counts.

    Returns:
        Dictionary with keys:
        {
            "rework_rate": float,  # Percentage of vehicles that required rework
            "first_time_fix_rate": float,  # Percentage of vehicles fixed on first attempt
            "total_rework": int,  # Total number of rework vehicles
            "total_vehicles": int,  # Total number of vehicles delivered
            "rework_by_month": [  # Monthly breakdown table
                {
                    "month": str,  # Month in YYYY-MM format
                    "rework_count": int,  # Number of rework vehicles in that month
                    "vehicles_delivered": int  # Total vehicles delivered in that month
                },
                ...
            ]
        }
    """
    try:
        from database.lib.db import run_query
        
        # Query aggregated data from repeat_repairs table
        # This table already has rework percentages calculated
        total_query = '''
            SELECT 
                SUM(total_vehicle_delivered) as total_vehicles,
                SUM(repeat_repair_count) as total_rework,
                AVG(repeat_repair_percentage) as avg_rework_percentage
            FROM repeat_repairs
            WHERE date IS NOT NULL
        '''
        total_result = run_query(total_query, fetch=True, commit=False)
        
        total_vehicles = int(total_result[0].get('total_vehicles') or 0) if total_result and total_result[0] else 0
        total_rework = int(total_result[0].get('total_rework') or 0) if total_result and total_result[0] else 0
        
        # Calculate rates based on vehicles
        rework_rate = round((total_rework / total_vehicles * 100), 2) if total_vehicles > 0 else 0.0
        first_time_fix_rate = round(100 - rework_rate, 2)
        
        # Query monthly rework breakdown with vehicle count
        monthly_query = '''
            SELECT
                DATE_FORMAT(date, '%Y-%m') as month,
                SUM(repeat_repair_count) as rework_count,
                SUM(total_vehicle_delivered) as vehicles_delivered
            FROM repeat_repairs
            WHERE date IS NOT NULL
            GROUP BY DATE_FORMAT(date, '%Y-%m')
            ORDER BY month DESC
            LIMIT 12
        '''
        monthly_result = run_query(monthly_query, fetch=True, commit=False)
        
        rework_by_month = []
        if monthly_result:
            rework_by_month = [
                {
                    "month": str(r.get('month', '')),
                    "rework_count": int(r.get('rework_count', 0) or 0),
                    "vehicles_delivered": int(r.get('vehicles_delivered', 0) or 0)
                }
                for r in monthly_result
            ]
        
        return {
            "rework_rate": rework_rate,
            "first_time_fix_rate": first_time_fix_rate,
            "total_rework": total_rework,
            "total_vehicles": total_vehicles,
            "rework_by_month": rework_by_month
        }
    
    except Exception as e:
        logger.error(f"Error in get_rework_rate_data: {str(e)}")
        return {
            "rework_rate": 0.0,
            "first_time_fix_rate": 100.0,
            "total_rework": 0,
            "total_vehicles": 0,
            "rework_by_month": []
        }


def get_rework_rate_by_date(start_date: str, end_date: str):
    """
    API Rework Rate By Date Helper Function: Get daily rework counts within a date range.

    Retrieves repeat repair data filtered by date range.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        Dictionary with keys:
        {
            "rework_data": [  # Daily rework breakdown table
                {
                    "date": str,  # Date in YYYY-MM-DD format
                    "rework_count": int  # Number of rework jobs on that date
                },
                ...
            ]
        }
    """
    try:
        from database.lib.db import run_query
        from datetime import datetime as dt

        # Parse dates
        start_dt = dt.strptime(start_date, "%Y-%m-%d").date()
        end_dt = dt.strptime(end_date, "%Y-%m-%d").date()

        # Query daily rework counts within date range
        rework_query = '''
            SELECT
                DATE(date) as date,
                SUM(repeat_repair_count) as rework_count
            FROM repeat_repairs
            WHERE DATE(date) BETWEEN %s AND %s
            GROUP BY DATE(date)
            ORDER BY date ASC
        '''
        rework_result = run_query(rework_query, (start_dt, end_dt), fetch=True, commit=False)

        rework_data = []
        if rework_result:
            rework_data = [
                {
                    "date": str(r.get('date', '')),
                    "rework_count": int(r.get('rework_count', 0) or 0)
                }
                for r in rework_result
            ]

        return {
            "rework_data": rework_data
        }

    except Exception as e:
        logger.error(f"Error in get_rework_rate_by_date: {str(e)}")
        return {
            "rework_data": []
        }




def get_msi_late_last_30_days():
    """
    API MSI Helper Function: Get most late MSI categories in the last 30 days.

    Retrieves MSI categories sorted by their late job percentage in the last 30 days.

    Returns:
        Dictionary with keys:
        {
            "data": [
                {
                    "msi": str,
                    "late_count": int,
                    "total_count": int,
                    "late_percentage": float
                },
                ...
            ]
        }
    """
    try:
        from database.lib.db import run_query
        from datetime import datetime, timedelta
        
        # Calculate date 30 days ago
        thirty_days_ago = (datetime.now() - timedelta(days=30)).date()
        
        logger.info(f"[get_msi_late_last_30_days] Fetching MSI late data from {thirty_days_ago} to today")
        
        # Query MSI data grouped by category, sorted by late percentage
        query = '''
            SELECT
                t.msi,
                COUNT(DISTINCT d.ro_no) as total_count,
                SUM(CASE WHEN d.status = 'Late' THEN 1 ELSE 0 END) as late_count,
                ROUND(
                    (SUM(CASE WHEN d.status = 'Late' THEN 1 ELSE 0 END) * 100.0) / 
                    COUNT(DISTINCT d.ro_no),
                    2
                ) as late_percentage
            FROM daily_cpus_reports d
            LEFT JOIN technician_reports t ON d.ro_no = t.ro_no
            WHERE DATE(d.service_date) >= %s
            AND t.msi IS NOT NULL
            GROUP BY t.msi
            ORDER BY late_percentage DESC, late_count DESC
        '''
        
        result = run_query(query, (thirty_days_ago,), fetch=True, commit=False)
        
        data = []
        if result:
            data = [
                {
                    "msi": str(r.get('msi', 'Unknown')),
                    "late_count": int(r.get('late_count', 0) or 0),
                    "total_count": int(r.get('total_count', 0) or 0),
                    "late_percentage": float(r.get('late_percentage', 0) or 0)
                }
                for r in result
            ]
            logger.info(f"[get_msi_late_last_30_days] Found {len(data)} MSI categories with late jobs")
        else:
            logger.warning(f"[get_msi_late_last_30_days] No data found for last 30 days")
        
        return {"data": data}
    
    except Exception as e:
        logger.error(f"[get_msi_late_last_30_days] ERROR: {str(e)}")
        logger.exception(f"[get_msi_late_last_30_days] Exception traceback:")
        return {"data": []}


def get_msi_monthly_data(category: str):
    """
    API MSI Helper Function: Get monthly data for a specific MSI category.

    Retrieves monthly breakdown of on-time, grace, and late jobs for an MSI category.

    Args:
        category: The MSI category to analyze.

    Returns:
        Dictionary with keys:
        {
            "monthly_data": [
                {
                    "month": str,
                    "on_time": int,
                    "grace": int,
                    "late": int,
                    "total": int
                },
                ...
            ]
        }
    """
    try:
        from database.lib.db import run_query
        
        logger.info(f"[get_msi_monthly_data] Fetching monthly data for MSI category: '{category}'")
        
        # Query monthly data for the category
        query = '''
            SELECT
                DATE_FORMAT(d.service_date, '%Y-%m') as month,
                SUM(CASE WHEN d.status IN ('On-time', 'on-time', 'on_time', 'On-Time', 'On_time', 'ON-TIME', 'ON_TIME') THEN 1 ELSE 0 END) as on_time,
                SUM(CASE WHEN d.status = 'Grace' THEN 1 ELSE 0 END) as grace,
                SUM(CASE WHEN d.status = 'Late' THEN 1 ELSE 0 END) as late,
                COUNT(DISTINCT d.ro_no) as total
            FROM daily_cpus_reports d
            LEFT JOIN technician_reports t ON d.ro_no = t.ro_no
            WHERE UPPER(t.msi) = UPPER(%s)
            AND t.technician_name IS NOT NULL
            GROUP BY DATE_FORMAT(d.service_date, '%Y-%m')
            ORDER BY month DESC
        '''
        
        result = run_query(query, (category,), fetch=True, commit=False)
        
        monthly_data = []
        if result:
            monthly_data = [
                {
                    "month": str(r.get('month', '')),
                    "on_time": int(r.get('on_time', 0) or 0),
                    "grace": int(r.get('grace', 0) or 0),
                    "late": int(r.get('late', 0) or 0),
                    "total": int(r.get('total', 0) or 0)
                }
                for r in result
            ]
            logger.info(f"[get_msi_monthly_data] Found {len(monthly_data)} months of data for '{category}'")
        else:
            logger.warning(f"[get_msi_monthly_data] No monthly data found for category '{category}'")
        
        return {"monthly_data": monthly_data}
    
    except Exception as e:
        logger.error(f"[get_msi_monthly_data] ERROR for category '{category}': {str(e)}")
        logger.exception(f"[get_msi_monthly_data] Exception traceback:")
        return {"monthly_data": []}


def get_top_5_late_cars():
    """
    API MSI Helper Function: Get top 5 cars with most late status count.

    Retrieves the top 5 car variants (vehicles) that have the most late job counts across all records.
    Each variant appears only once with aggregated metrics across all MSI categories.

    Returns:
        Dictionary with keys:
        {
            "data": [
                {
                    "variant": str,
                    "late_count": int,
                    "total_count": int,
                    "msi": str  # Most common MSI for this variant
                },
                ...
            ]
        }
    """
    try:
        from database.lib.db import run_query
        
        logger.info(f"[get_top_5_late_cars] Fetching top 5 cars with most late status")
        
        # Query top 5 UNIQUE cars (by variant) with most late jobs
        # Group by variant only to ensure uniqueness
        # Get the most common MSI for each variant as a representative value
        query = '''
            SELECT
                t.variant,
                (SELECT t2.msi 
                 FROM daily_cpus_reports d2
                 LEFT JOIN technician_reports t2 ON d2.ro_no = t2.ro_no
                 WHERE t2.variant = t.variant
                 AND t2.msi IS NOT NULL
                 GROUP BY t2.msi
                 ORDER BY COUNT(*) DESC
                 LIMIT 1) as msi,
                COUNT(DISTINCT d.ro_no) as total_count,
                SUM(CASE WHEN d.status = 'Late' THEN 1 ELSE 0 END) as late_count
            FROM daily_cpus_reports d
            LEFT JOIN technician_reports t ON d.ro_no = t.ro_no
            WHERE t.variant IS NOT NULL
            GROUP BY t.variant
            ORDER BY late_count DESC, total_count DESC
            LIMIT 5
        '''
        
        result = run_query(query, fetch=True, commit=False)
        
        data = []
        if result:
            data = [
                {
                    "variant": str(r.get('variant', 'Unknown')),
                    "late_count": int(r.get('late_count', 0) or 0),
                    "total_count": int(r.get('total_count', 0) or 0),
                    "msi": str(r.get('msi', 'Unknown'))
                }
                for r in result
            ]
            logger.info(f"[get_top_5_late_cars] Found {len(data)} unique cars with late jobs")
        else:
            logger.warning(f"[get_top_5_late_cars] No data found")
        
        return {"data": data}
    
    except Exception as e:
        logger.error(f"[get_top_5_late_cars] ERROR: {str(e)}")
        logger.exception(f"[get_top_5_late_cars] Exception traceback:")
        return {"data": []}


def get_job_records(
    page_number: int,
    receiving_date_time: str = None,
    delivery_date_time: str = None,
    promised_date_time: str = None,
    technician_name: str = None
):
    """
    API Job Records Helper Function: Get paginated job records with optional filtering.

    Retrieves paginated job records from daily_cpus_reports with optional date and technician filters.
    Each page contains 100 records. Page numbering starts from 1.

    Args:
        page_number: Page number (1-based indexing). Page 1 returns records 1-100, page 2 returns 101-200, etc.
        receiving_date_time: Optional receiving date filter (YYYY-MM-DD)
        delivery_date_time: Optional delivery date filter (YYYY-MM-DD)
        promised_date_time: Optional promised date filter (YYYY-MM-DD)
        technician_name: Optional technician name filter

    Returns:
        Dictionary with keys:
        {
            "job_records": [  # Array of job record objects (max 100 per page)
                {
                    "service_date": str,
                    "chassis_no": str,
                    "ro_no": str,
                    "service_nature": str,
                    "receiving_date_time": str,
                    "delivery_date_time": str,
                    "promised_date_time": str,
                    "technician_name": str,
                    "vehicle_variant": str
                },
                ...
            ],
            "no_of_rows": int,  # Number of rows returned (up to 100)
            "total_records": int  # Total records matching the filters
        }

    Example implementation:
        from database.lib.db import run_query
        from datetime import datetime as dt

        # Build WHERE clause based on provided filters
        where_clauses = []
        params = []

        if receiving_date_time:
            where_clauses.append("DATE(receiving_date_time) = %s")
            params.append(dt.strptime(receiving_date_time, "%Y-%m-%d").date())

        if delivery_date_time:
            where_clauses.append("DATE(delivery_date_time) = %s")
            params.append(dt.strptime(delivery_date_time, "%Y-%m-%d").date())

        if promised_date_time:
            where_clauses.append("DATE(promised_date_time) = %s")
            params.append(dt.strptime(promised_date_time, "%Y-%m-%d").date())

        if technician_name:
            where_clauses.append("technician_name = %s")
            params.append(technician_name)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Query job records
        query = f'''
            SELECT
                DATE(service_date) as service_date,
                chassis_number as chassis_no,
                ro_no,
                service_nature,
                receiving_date_time,
                delivery_date_time,
                promised_date_time,
                technician_name,
                vehicle_variant
            FROM daily_cpus_reports
            WHERE {where_sql}
            ORDER BY service_date DESC
            LIMIT %s
        '''
        params.append(page_number)

        result = run_query(query, tuple(params), fetch=True, commit=False)

        job_records = []
        if result:
            job_records = [
                {
                    "service_date": str(r.get('service_date', '')),
                    "chassis_no": str(r.get('chassis_no', '')),
                    "ro_no": int(r.get('ro_no', 0)),
                    "service_nature": str(r.get('service_nature', '')),
                    "receiving_date_time": str(r.get('receiving_date_time', '')),
                    "delivery_date_time": str(r.get('delivery_date_time', '')),
                    "promised_date_time": str(r.get('promised_date_time', '')),
                    "technician_name": str(r.get('technician_name', '')),
                    "vehicle_variant": str(r.get('vehicle_variant', ''))
                }
                for r in result
            ]

        return {
            "job_records": job_records,
            "no_of_rows": len(job_records)
        }
    """
    try:
        from database.lib.db import run_query
        from datetime import datetime as dt
        
        logger.info(f"Starting get_job_records with page_number={page_number}")
        logger.info(f"Filters - receiving_date_time={receiving_date_time}, delivery_date_time={delivery_date_time}, "
                   f"promised_date_time={promised_date_time}, technician_name={technician_name}")
        
        # Build WHERE clause based on provided filters
        where_clauses = []
        params = []
        
        if receiving_date_time:
            where_clauses.append("DATE(d.receiving_date_time) = %s")
            params.append(dt.strptime(receiving_date_time, "%Y-%m-%d").date())
            logger.debug(f"Added receiving_date_time filter: {receiving_date_time}")
        
        if delivery_date_time:
            where_clauses.append("DATE(d.delivery_date_time) = %s")
            params.append(dt.strptime(delivery_date_time, "%Y-%m-%d").date())
            logger.debug(f"Added delivery_date_time filter: {delivery_date_time}")
        
        if promised_date_time:
            where_clauses.append("DATE(d.promised_date_time) = %s")
            params.append(dt.strptime(promised_date_time, "%Y-%m-%d").date())
            logger.debug(f"Added promised_date_time filter: {promised_date_time}")
        
        if technician_name:
            where_clauses.append("d.technician_name LIKE %s")
            params.append(f"%{technician_name}%")
            logger.debug(f"Added technician_name LIKE filter: {technician_name}")
        
        # Always exclude NULL and 'Unassigned' technician names
        where_clauses.append("d.technician_name IS NOT NULL")
        where_clauses.append("d.technician_name != 'Unassigned'")
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        # Calculate pagination: 100 records per page
        page_size = 100
        offset = (page_number - 1) * page_size
        logger.info(f"Pagination: page_number={page_number}, offset={offset}, page_size={page_size}")
        
        # Query job records from database with pagination
        # Use LEFT JOIN to include all records from daily_cpus_reports (with optional technician data)
        # Note: Removed COUNT(*) query for performance (saves ~300ms per request)
        query = f'''
            SELECT
                DATE(d.service_date) as service_date,
                d.chassis_number as chassis_no,
                d.ro_no,
                d.service_nature,
                d.receiving_date_time,
                d.delivery_date_time,
                d.promised_date_time,
                d.technician_name,
                d.vehicle_variant
            FROM daily_cpus_reports d
            LEFT JOIN technician_reports t ON d.ro_no = t.ro_no
            WHERE {where_sql}
            ORDER BY d.service_date DESC
            LIMIT %s OFFSET %s
        '''
        params.append(page_size)
        params.append(offset)
        
        logger.debug(f"Executing query with params: {params}")
        result = run_query(query, tuple(params), fetch=True, commit=False)
        
        job_records = []
        if result:
            logger.info(f"Query returned {len(result)} records")
            job_records = [
                {
                    "service_date": str(r.get('service_date', '')),
                    "chassis_no": str(r.get('chassis_no', '')),
                    "ro_no": str(r.get('ro_no', '')),
                    "service_nature": str(r.get('service_nature', '')),
                    "receiving_date_time": str(r.get('receiving_date_time', '')),
                    "delivery_date_time": str(r.get('delivery_date_time', '')),
                    "promised_date_time": str(r.get('promised_date_time', '')),
                    "technician_name": str(r.get('technician_name', '')),
                    "vehicle_variant": str(r.get('vehicle_variant', ''))
                }
                for r in result
            ]
        else:
            logger.info("Query returned no records")
        
        logger.info(f"Successfully retrieved {len(job_records)} job records")
        
        return {
            "job_records": job_records,
            "no_of_rows": len(job_records)
        }

    except Exception as e:
        logger.error(f"Error in get_job_records: {str(e)}")
        logger.error(f"Exception details: {traceback.format_exc()}")
        return {
            "job_records": [],
            "no_of_rows": 0,
            "total_records": 0
        }


# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# FASTAPI APP INITIALIZATION
# ============================================================================

app = FastAPI(
    title="Toyota PDF Processing API",
    description="""
    ## Toyota Service Reports Processing API
    
    This API processes three types of Toyota service reports:
    
    ### 📋 Supported Reports:
    
    1. **Technician Report (TimeSheet)** - Required
       - Conversion: ConvertAPI
       - Cleaning: Removes invalid RO/Reg numbers, zero jobs, duplicates
       - Output: `{original_name}_cleaned.csv`
    
    2. **Daily Report** - Required
       - Conversion: pdfplumber
       - Cleaning: Removes duplicates, adds status column (Late/On-time/Grace)
       - Output: `{original_name}_cleaned.csv`
    
    3. **Rework Report (Repeat Repair)** - Optional
       - Conversion: pdfplumber
       - Cleaning: Removes rows with "Total" or month names
       - Output: `{original_name}_cleaned.xlsx`
    
    ### 🔄 Workflow:
    1. Upload PDF files via `/upload-reports` endpoint
    2. Files are validated (type, size, format)
    3. Automatic conversion and cleaning
    4. Data automatically synced to database
    5. All files (PDFs + cleaned CSV/XLSX) automatically deleted after database sync

    ### 📊 Features:
    - Automatic validation and error handling
    - Detailed processing statistics
    - Progress tracking and logging
    - Automatic database synchronization
    - Complete file cleanup (all PDFs and cleaned files removed after database sync)
    """,
    version="4.0.0",
    contact={
        "name": "Toyota Service Analytics",
        "email": "support@toyota-analytics.com"
    },
    license_info={
        "name": "Proprietary",
    }
)

# ============================================================================
# CORS MIDDLEWARE
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# DIRECTORY SETUP
# ============================================================================

# Ensure required directories exist
UPLOAD_DIR.mkdir(exist_ok=True, parents=True)
CLEANED_DIR.mkdir(exist_ok=True, parents=True)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Maximum file size: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes

# Allowed PDF content types
ALLOWED_PDF_TYPES = ["application/pdf"]

# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

def validate_pdf(file: UploadFile) -> tuple[bool, str]:
    """
    Validate if the uploaded file is a valid PDF.
    
    Args:
        file: Uploaded file object
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check content type
    if file.content_type not in ALLOWED_PDF_TYPES:
        return False, f"Invalid file type: {file.content_type}. Only PDF files are allowed."

    # Check file extension
    if not file.filename.lower().endswith('.pdf'):
        return False, "Invalid file extension. Only .pdf files are allowed."

    return True, ""


def validate_file_size(file: UploadFile) -> tuple[bool, str]:
    """
    Validate file size is within limits.
    
    Args:
        file: Uploaded file object
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Read file content to check size
    file.file.seek(0, 2)  # Seek to end of file
    file_size = file.file.tell()
    file.file.seek(0)  # Reset file pointer to beginning

    if file_size == 0:
        return False, "File is empty."

    if file_size > MAX_FILE_SIZE:
        size_mb = file_size / (1024 * 1024)
        return False, f"File size ({size_mb:.2f}MB) exceeds maximum allowed size (10MB)."

    return True, ""


async def save_uploaded_file(file: UploadFile, destination: Path) -> dict:
    """
    Save uploaded file to destination path.
    
    Args:
        file: Uploaded file object
        destination: Path to save file
        
    Returns:
        Dictionary with file information
    """
    try:
        # Ensure destination directory exists
        destination.parent.mkdir(exist_ok=True, parents=True)
        
        # Save file
        with destination.open("wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Get file info
        file_info = {
            "original_filename": file.filename,
            "saved_filename": destination.name,
            "path": str(destination),
            "size_bytes": destination.stat().st_size,
            "size_kb": round(destination.stat().st_size / 1024, 2),
            "size_mb": round(destination.stat().st_size / (1024 * 1024), 2),
            "uploaded_at": datetime.now().isoformat()
        }
        
        logger.info(f"File saved: {destination.name} ({file_info['size_mb']:.2f}MB)")
        return file_info
        
    except Exception as e:
        logger.error(f"Failed to save file {file.filename}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """
    Root endpoint - API information and health check.
    """
    return {
        "message": "Toyota PDF Processing API",
        "version": "4.0.0",
        "status": "running",
        "description": "Upload, convert, and clean Toyota service reports",
        "endpoints": {
            "upload": "POST /upload-reports - Upload and process PDF reports",
            "processed_files": "GET /processed-files - List all cleaned files",
            "download": "GET /download/{filename} - Download a cleaned file",
            "jobs_overview": "GET /jobs-overview - Get jobs overview (total jobs, technicians, job data)",
            "technician_performance": "GET /technician-performance - Get technician performance metrics",
            "msi": "GET /msi - Get MSI data for a category",
            "rework_rate": "GET /rework-rate - Get rework rate metrics and monthly breakdown",
            "rework_rate_by_date": "GET /rework-rate-by-date - Get daily rework counts by date range",
            "health": "GET /health - Health check",
            "docs": "GET /docs - Interactive API documentation",
            "redoc": "GET /redoc - Alternative API documentation"
        },
        "supported_reports": {
            "technician_report": {
                "name": "Technician Report (TimeSheet)",
                "required": True,
                "conversion": "ConvertAPI",
                "output_format": "CSV",
                "output_pattern": "{name}_cleaned.csv",
                "database_sync": True
            },
            "daily_report": {
                "name": "Daily Service Report",
                "required": True,
                "conversion": "pdfplumber",
                "output_format": "CSV",
                "output_pattern": "{name}_cleaned.csv",
                "database_sync": True
            },
            "rework_report": {
                "name": "Rework Report (Repeat Repair)",
                "required": False,
                "conversion": "pdfplumber",
                "output_format": "XLSX",
                "output_pattern": "{name}_cleaned.xlsx",
                "database_sync": True
            }
        },
        "limitations": {
            "max_file_size": "10MB",
            "allowed_formats": ["PDF"],
            "max_concurrent_uploads": "Unlimited"
        }
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint - verify API is operational.
    """
    # Check if directories exist and are writable
    upload_ok = UPLOAD_DIR.exists() and os.access(UPLOAD_DIR, os.W_OK)
    cleaned_ok = CLEANED_DIR.exists() and os.access(CLEANED_DIR, os.W_OK)
    
    health_status = {
        "status": "healthy" if (upload_ok and cleaned_ok) else "degraded",
        "timestamp": datetime.now().isoformat(),
        "version": "4.0.0",
        "directories": {
            "upload_dir": {
                "path": str(UPLOAD_DIR),
                "exists": UPLOAD_DIR.exists(),
                "writable": upload_ok
            },
            "cleaned_dir": {
                "path": str(CLEANED_DIR),
                "exists": CLEANED_DIR.exists(),
                "writable": cleaned_ok
            }
        }
    }
    
    status_code = status.HTTP_200_OK if health_status["status"] == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return JSONResponse(
        status_code=status_code,
        content=health_status
    )


@app.get("/processed-files")
async def list_processed_files():
    """
    List all processed/cleaned files in the output directory.
    
    Returns information about all cleaned files including:
    - File name and type
    - File size
    - Last modified timestamp
    - Download URL
    """
    if not CLEANED_DIR.exists():
        return {
            "message": "No processed files found. Upload reports first.",
            "output_directory": str(CLEANED_DIR),
            "files": [],
            "count": 0
        }

    # Get all files in cleaned directory
    all_files = []
    
    for file_path in CLEANED_DIR.iterdir():
        if file_path.is_file():
            # Determine file type
            file_type = "unknown"
            if "_cleaned.csv" in file_path.name:
                if "timesheet" in file_path.name.lower() or "technician" in file_path.name.lower():
                    file_type = "technician_report"
                elif "daily" in file_path.name.lower():
                    file_type = "daily_report"
                else:
                    file_type = "csv_report"
            elif "_cleaned.xlsx" in file_path.name:
                file_type = "rework_report"
            
            all_files.append({
                "type": file_type,
                "filename": file_path.name,
                "path": str(file_path),
                "size_bytes": file_path.stat().st_size,
                "size_kb": round(file_path.stat().st_size / 1024, 2),
                "size_mb": round(file_path.stat().st_size / (1024 * 1024), 2),
                "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                "download_url": f"/download/{file_path.name}"
            })
    
    # Sort by modified date (newest first)
    all_files.sort(key=lambda x: x["modified"], reverse=True)

    return {
        "message": f"Found {len(all_files)} processed file(s)",
        "output_directory": str(CLEANED_DIR),
        "count": len(all_files),
        "files": all_files,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/download/{filename}")
async def download_file(filename: str):
    """
    Download a cleaned/processed file.
    
    Args:
        filename: Name of the file to download
        
    Returns:
        File download response
    """
    file_path = CLEANED_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {filename}"
        )
    
    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file: {filename}"
        )
    
    # Determine media type
    media_type = "application/octet-stream"
    if filename.endswith(".csv"):
        media_type = "text/csv"
    elif filename.endswith(".xlsx"):
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    
    logger.info(f"File downloaded: {filename}")
    
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename
    )


@app.post("/upload-reports", status_code=status.HTTP_201_CREATED)
async def upload_reports(
    technicianreport: UploadFile = File(..., description="Technician/TimeSheet report PDF (required)"),
    dailyreport: UploadFile = File(..., description="Daily report PDF (required)"),
    reworkreport: Optional[UploadFile] = File(None, description="Repeat Repair/Rework report PDF (optional)")
):
    """
    Upload and process Toyota service reports.
    
    ### Required Files:
    - **technicianreport**: Technician/TimeSheet report PDF
    - **dailyreport**: Daily service report PDF
    
    ### Optional Files:
    - **reworkreport**: Repeat Repair/Rework report PDF
    
    ### Processing Steps:
    1. Validate all uploaded files (type, size, format)
    2. Save files to upload directory
    3. Convert PDFs to XLSX/CSV format
    4. Clean and process data
    5. Save cleaned files with `_cleaned` suffix
    6. Automatically sync cleaned data to database
    7. Remove ALL files (PDFs and cleaned CSV/XLSX) after successful database sync

    ### Returns:
    - Upload confirmation with file details
    - Processing results and statistics
    - Database synchronization status (includes list of deleted PDF files)
    - Download URLs for cleaned files (note: all files are removed after database sync)
    - Error details if processing fails
    """
    uploaded_files = []
    temp_files = []  # Track files for cleanup on error
    
    try:
        logger.info("Starting file upload process...")
        
        # ===== VALIDATE TECHNICIAN REPORT =====
        logger.info("Validating technician report...")
        
        if not technicianreport.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Technician report is required"
            )

        is_valid, error_msg = validate_pdf(technicianreport)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Technician report validation failed: {error_msg}"
            )

        is_valid, error_msg = validate_file_size(technicianreport)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Technician report size validation failed: {error_msg}"
            )

        # ===== VALIDATE DAILY REPORT =====
        logger.info("Validating daily report...")
        
        if not dailyreport.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Daily report is required"
            )

        is_valid, error_msg = validate_pdf(dailyreport)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Daily report validation failed: {error_msg}"
            )

        is_valid, error_msg = validate_file_size(dailyreport)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Daily report size validation failed: {error_msg}"
            )

        # ===== VALIDATE REWORK REPORT (if provided) =====
        if reworkreport and reworkreport.filename:
            logger.info("Validating rework report...")
            
            is_valid, error_msg = validate_pdf(reworkreport)
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Rework report validation failed: {error_msg}"
                )

            is_valid, error_msg = validate_file_size(reworkreport)
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Rework report size validation failed: {error_msg}"
                )

        # ===== SAVE TECHNICIAN REPORT =====
        logger.info(f"Saving technician report: {technicianreport.filename}")
        technician_path = UPLOAD_DIR / technicianreport.filename
        tech_info = await save_uploaded_file(technicianreport, technician_path)
        tech_info["type"] = "technician_report"
        uploaded_files.append(tech_info)
        temp_files.append(technician_path)

        # ===== SAVE DAILY REPORT =====
        logger.info(f"Saving daily report: {dailyreport.filename}")
        daily_path = UPLOAD_DIR / dailyreport.filename
        daily_info = await save_uploaded_file(dailyreport, daily_path)
        daily_info["type"] = "daily_report"
        uploaded_files.append(daily_info)
        temp_files.append(daily_path)

        # ===== SAVE REWORK REPORT (if provided) =====
        rework_path = None
        if reworkreport and reworkreport.filename:
            logger.info(f"Saving rework report: {reworkreport.filename}")
            rework_path = UPLOAD_DIR / reworkreport.filename
            rework_info = await save_uploaded_file(reworkreport, rework_path)
            rework_info["type"] = "rework_report"
            uploaded_files.append(rework_info)
            temp_files.append(rework_path)

        # ===== PROCESS REPORTS =====
        logger.info("Starting PDF processing and cleaning...")
        print("\n" + "="*80)
        print("PROCESSING UPLOADED REPORTS")
        print("="*80)

        try:
            # Call the processing function from worker module
            processing_results = process_reports(
                technician_pdf_path=technician_path,
                daily_pdf_path=daily_path,
                rework_pdf_path=rework_path,
                output_dir=CLEANED_DIR
            )

            # ===== SYNC TO DATABASE =====
            db_sync_result = None
            if processing_results.get("success"):
                try:
                    logger.info("Starting database synchronization...")
                    print("\n" + "="*80)
                    print("SYNCING CLEANED FILES TO DATABASE")
                    print("="*80)

                    db_sync_exit_code = sync_database()

                    if db_sync_exit_code == 0:
                        logger.info("Database synchronization completed successfully")

                        # Delete uploaded PDF files after successful database sync
                        logger.info("Cleaning up uploaded PDF files...")
                        deleted_pdfs = []
                        for pdf_path in [technician_path, daily_path, rework_path]:
                            if pdf_path and pdf_path.exists():
                                try:
                                    pdf_path.unlink()
                                    deleted_pdfs.append(pdf_path.name)
                                    logger.info(f"Deleted uploaded file: {pdf_path.name}")
                                except Exception as e:
                                    logger.error(f"Failed to delete {pdf_path.name}: {e}")

                        if deleted_pdfs:
                            logger.info(f"Successfully deleted {len(deleted_pdfs)} uploaded PDF file(s)")

                        db_sync_result = {
                            "success": True,
                            "message": "Data successfully loaded into database and all files removed",
                            "deleted_pdfs": deleted_pdfs
                        }
                    else:
                        logger.error("Database synchronization failed - possible wrong file format or corrupted data")
                        # Clean up uploaded PDFs on DB sync failure
                        for pdf_path in [technician_path, daily_path, rework_path]:
                            if pdf_path and pdf_path.exists():
                                try:
                                    pdf_path.unlink()
                                    logger.info(f"Cleaned up file after DB failure: {pdf_path.name}")
                                except Exception as e:
                                    logger.error(f"Failed to cleanup {pdf_path.name}: {e}")

                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Something went wrong with the files."
                        )
                except HTTPException:
                    raise
                except Exception as db_error:
                    logger.error(f"Database synchronization error: {str(db_error)}")
                    # Clean up uploaded PDFs on exception
                    for pdf_path in [technician_path, daily_path, rework_path]:
                        if pdf_path and pdf_path.exists():
                            try:
                                pdf_path.unlink()
                                logger.info(f"Cleaned up file after error: {pdf_path.name}")
                            except Exception as e:
                                logger.error(f"Failed to cleanup {pdf_path.name}: {e}")

                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Something went wrong with the files."
                    )
            else:
                logger.error("File processing/cleaning failed - files may be incorrect or corrupted")
                # Log specific error messages for debugging
                error_messages = processing_results.get("errors", [])
                if error_messages:
                    logger.error(f"Processing errors: {', '.join(error_messages)}")

                # Clean up uploaded PDFs on processing failure
                for pdf_path in [technician_path, daily_path, rework_path]:
                    if pdf_path and pdf_path.exists():
                        try:
                            pdf_path.unlink()
                            logger.info(f"Cleaned up file after processing failure: {pdf_path.name}")
                        except Exception as e:
                            logger.error(f"Failed to cleanup {pdf_path.name}: {e}")

                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Something went wrong with the files."
                )

            # Build response with detailed information
            response_data = {
                "message": "Reports uploaded and processed successfully" if processing_results.get("success") else "Reports uploaded but some processing failed",
                "status": "success" if processing_results.get("success") else "partial_success",
                "uploaded_files": uploaded_files,
                "processing_summary": {
                    "success": processing_results.get("success", False),
                    "total_operations": processing_results.get("total_operations", 0),
                    "successful_operations": processing_results.get("success_count", 0),
                    "failed_operations": processing_results.get("error_count", 0),
                },
                "database_sync": db_sync_result,
                "processed_files": {},
                "download_urls": {},
                "errors": processing_results.get("errors", []),
                "output_directory": str(CLEANED_DIR),
                "timestamp": datetime.now().isoformat()
            }

            # Add processed file information and download URLs
            for report_type, report_data in processing_results.get("processed_files", {}).items():
                response_data["processed_files"][report_type] = {
                    "input_file": report_data.get("input_file"),
                    "output_file": report_data.get("output_file"),
                    "initial_rows": report_data.get("initial_rows") or report_data.get("initial_rows") or report_data.get("total_original_rows"),
                    "final_rows": report_data.get("final_rows") or report_data.get("total_remaining_rows"),
                    "processing_stats": report_data.get("statistics") or report_data.get("status_distribution") or report_data.get("sheet_results")
                }

                # Add download URL
                if report_data.get("output_file"):
                    output_filename = Path(report_data["output_file"]).name
                    response_data["download_urls"][report_type] = f"/download/{output_filename}"

            logger.info(f"Processing completed: {response_data['processing_summary']['successful_operations']}/{response_data['processing_summary']['total_operations']} successful")

            return JSONResponse(
                status_code=status.HTTP_201_CREATED,
                content=response_data
            )

        except Exception as e:
            # Processing failed - generic error handler
            error_trace = traceback.format_exc()
            logger.error(f"Processing error: {error_trace}")

            # Clean up uploaded PDFs on unexpected error
            for pdf_path in temp_files:
                if pdf_path and pdf_path.exists():
                    try:
                        pdf_path.unlink()
                        logger.info(f"Cleaned up file after unexpected error: {pdf_path.name}")
                    except Exception as cleanup_error:
                        logger.error(f"Failed to cleanup {pdf_path.name}: {cleanup_error}")

            # Return simple error message to frontend
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Something went wrong with the files."
            )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except Exception as e:
        # Unexpected error - cleanup uploaded files
        logger.error(f"Unexpected error during upload: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Clean up any uploaded files
        for file_path in temp_files:
            if file_path and file_path.exists():
                try:
                    file_path.unlink()
                    logger.info(f"Cleaned up file: {file_path}")
                except Exception as cleanup_error:
                    logger.error(f"Failed to cleanup file {file_path}: {cleanup_error}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during upload: {str(e)}"
        )
    
    finally:
        # Close file handles
        await technicianreport.close()
        await dailyreport.close()
        if reworkreport:
            await reworkreport.close()


# Background task: Run cleaning pipeline
def run_cleaning_pipeline(task_id: str):
    global file_metadata  # Ensure file_metadata is accessible

    try:
        logging.info(f"Starting cleaning pipeline for task: {task_id}")
        output_dir = CLEANED_DIR

        # Extract file paths from metadata
        technician_pdf = None
        daily_pdf = None
        rework_pdf = None

        for file_id, metadata in file_metadata.items():
            if metadata["status"] == "uploaded":
                file_type = metadata.get("type")
                input_path = Path(metadata["path"])

                if file_type == "technician":
                    technician_pdf = input_path
                elif file_type == "daily":
                    daily_pdf = input_path
                elif file_type == "rework":
                    rework_pdf = input_path

        # Call the process_reports function
        if technician_pdf and daily_pdf:
            results = process_reports(
                technician_pdf_path=technician_pdf,
                daily_pdf_path=daily_pdf,
                rework_pdf_path=rework_pdf,
                output_dir=output_dir
            )

            # Update metadata with results
            for file_type, file_info in results.get("processed_files", {}).items():
                for file_id, metadata in file_metadata.items():
                    if metadata.get("type") == file_type:
                        metadata["status"] = "processed"
                        metadata["cleaned_path"] = file_info.get("cleaned_file")

            logging.info("Cleaning pipeline completed successfully.")

            # Run database synchronization
            logging.info("Starting database synchronization...")
            sync_exit_code = sync_database()
            if sync_exit_code == 0:
                logging.info("Database synchronization completed successfully.")
            else:
                logging.error("Database synchronization failed.")
        else:
            logging.error("Required files (technician and daily) are missing.")
    except Exception as e:
        logging.error(f"Processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@app.delete("/cleanup")
async def cleanup_files():
    """
    Clean up all uploaded and processed files.

    WARNING: This will delete all files in upload and cleaned directories.
    Use with caution!
    """
    try:
        upload_count = 0
        cleaned_count = 0

        # Clean upload directory
        if UPLOAD_DIR.exists():
            for file_path in UPLOAD_DIR.iterdir():
                if file_path.is_file():
                    file_path.unlink()
                    upload_count += 1

        # Clean cleaned directory
        if CLEANED_DIR.exists():
            for file_path in CLEANED_DIR.iterdir():
                if file_path.is_file():
                    file_path.unlink()
                    cleaned_count += 1

        logger.info(f"Cleanup completed: {upload_count} uploaded files, {cleaned_count} cleaned files deleted")

        return {
            "message": "Cleanup completed successfully",
            "deleted": {
                "uploaded_files": upload_count,
                "cleaned_files": cleaned_count,
                "total": upload_count + cleaned_count
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cleanup failed: {str(e)}"
        )


@app.get("/jobs-overview")
async def jobs_overview_api():
    """
    API 1: Get jobs overview (all jobs, no date filtering).

    Returns total jobs count, total number of technicians, and detailed job data for all records.

    ### Query Parameters:
    - None (returns all jobs)

    ### Returns:
    - **num_total_jobs**: Total number of jobs (all time)
    - **total_technicians**: Total number of unique technicians
    - **job_data**: 2D array with 5 columns: [RO No, Reg No, Customer Name, Service Date, Status]

    ### Example:
    ```
    GET /jobs-overview
    ```
    """
    try:
        logger.info("Fetching jobs overview (all jobs)")

        # Call the helper function to get data
        # IMPLEMENT get_jobs_overview() function above to query your database
        data = get_jobs_overview()

        num_total_jobs = data["num_total_jobs"]
        total_technicians = data["total_technicians"]
        job_data = data["job_data"]

        logger.info(f"Successfully retrieved overview: {num_total_jobs} jobs, {total_technicians} technicians")

        return {
            "success": True,
            "num_total_jobs": num_total_jobs,
            "total_technicians": total_technicians,
            "job_data": job_data,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching jobs overview: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch jobs overview: {str(e)}"
        )


@app.get("/technician-performance")
async def technician_performance_api(
    name: str,
    start_date: str,
    end_date: str
):
    """
    API 2: Get specific technician's performance metrics.

    Returns late, on-time, grace, and total job counts for a specific technician.

    ### Query Parameters:
    - **name**: Technician name (string)
    - **start_date**: Start date in YYYY-MM-DD format
    - **end_date**: End date in YYYY-MM-DD format

    ### Returns:
    - **late_jobs**: Number of late jobs
    - **ontime_jobs**: Number of on-time jobs
    - **grace_jobs**: Number of grace period jobs
    - **total_jobs**: Total jobs for this technician

    ### Example:
    ```
    GET /technician-performance?name=John%20Doe&start_date=2024-01-01&end_date=2024-01-31
    ```
    """
    try:
        # Validate date format
        from datetime import datetime as dt
        try:
            start_dt = dt.strptime(start_date, "%Y-%m-%d").date()
            end_dt = dt.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD format."
            )

        if start_dt > end_dt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date must be before or equal to end_date"
            )

        logger.info(f"Fetching performance for technician: {name}, date range: {start_date} to {end_date}")

        # Call the helper function to get data
        # IMPLEMENT get_technician_performance() function above to query your database
        data = get_technician_performance(name, start_date, end_date)

        late_jobs = data["late_jobs"]
        ontime_jobs = data["ontime_jobs"]
        grace_jobs = data["grace_jobs"]
        total_jobs = data["total_jobs"]

        logger.info(f"Successfully retrieved performance for {name}: {total_jobs} total jobs")

        return {
            "success": True,
            "technician_name": name,
            "date_range": {
                "start_date": start_date,
                "end_date": end_date
            },
            "late_jobs": late_jobs,
            "ontime_jobs": ontime_jobs,
            "grace_jobs": grace_jobs,
            "total_jobs": total_jobs,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching technician performance: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch technician performance: {str(e)}"
        )


@app.get("/msi")
async def msi_api(category: str):
    """
    API MSI: Get Most/Least used operations and performance for a category.

    Returns most used operation, least used operation, average number of operations,
    and a performance table for a given category.

    ### Query Parameters:
    - **category**: The category to analyze (string)

    ### Returns:
    - **most_used_operation**: Most frequently performed operation in the category.
    - **least_used_operation**: Least frequently performed operation in the category.
    - **avg_no_of_operations**: Average number of operations for the category.
    - **performance_table**: A table of technician performance metrics.
        - **name**: Technician name
        - **ontime**: Number of on-time jobs
        - **grace**: Number of grace period jobs
        - **late**: Number of late jobs

    ### Example:
    ```
    GET /msi?category=maintenance
    ```
    """
    try:
        logger.info(f"Fetching MSI data for category: {category}")

        # Call the helper function to get data
        # IMPLEMENT get_msi_data() function to query your database
        data = get_msi_data(category)

        logger.info(f"Successfully retrieved MSI data for category: {category}")

        return {
            "success": True,
            "category": category,
            "most_used_operation": data["most_used_operation"],
            "least_used_operation": data["least_used_operation"],
            "avg_no_of_operations": data["avg_no_of_operations"],
            "performance_table": data["performance_table"],
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching MSI data for category {category}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch MSI data: {str(e)}"
        )


@app.get("/msi-late-last-30-days")
async def msi_late_last_30_days_api():
    """
    API MSI Late Last 30 Days: Get MSI categories with highest late percentage in last 30 days.

    Returns MSI categories sorted by their late job percentage in the last 30 days.

    ### Query Parameters:
    - None (returns last 30 days data)

    ### Returns:
    - **data**: Array of MSI categories with:
        - **msi**: MSI category name (string)
        - **late_count**: Number of late jobs (int)
        - **total_count**: Total jobs in category (int)
        - **late_percentage**: Percentage of late jobs (float)

    ### Example:
    ```
    GET /msi-late-last-30-days
    ```
    """
    try:
        logger.info("Fetching most late MSI categories for last 30 days")

        # Call the helper function to get data
        data = get_msi_late_last_30_days()

        logger.info(f"Successfully retrieved late MSI data: {len(data['data'])} categories")

        return {
            "success": True,
            "time_period": "Last 30 days",
            "data": data["data"],
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching late MSI data: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch late MSI data: {str(e)}"
        )


@app.get("/msi-monthly")
async def msi_monthly_api(category: str):
    """
    API MSI Monthly: Get monthly breakdown for an MSI category.

    Returns monthly data for on-time, grace, and late jobs for a given MSI category.

    ### Query Parameters:
    - **category**: The MSI category to analyze (string)

    ### Returns:
    - **category**: The requested MSI category (string)
    - **monthly_data**: Array of monthly data with:
        - **month**: Month in YYYY-MM format (string)
        - **on_time**: Number of on-time jobs (int)
        - **grace**: Number of grace period jobs (int)
        - **late**: Number of late jobs (int)
        - **total**: Total jobs in month (int)

    ### Example:
    ```
    GET /msi-monthly?category=GR
    ```
    """
    try:
        logger.info(f"Fetching monthly MSI data for category: {category}")

        # Call the helper function to get data
        data = get_msi_monthly_data(category)

        logger.info(f"Successfully retrieved monthly MSI data for {category}: {len(data['monthly_data'])} months")

        return {
            "success": True,
            "category": category,
            "monthly_data": data["monthly_data"],
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching monthly MSI data for {category}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch monthly MSI data: {str(e)}"
        )


@app.get("/top-5-late-cars")
async def top_5_late_cars_api():
    """
    API Top 5 Late Cars: Get top 5 cars (RO numbers) with most late status count.

    Returns the top 5 RO numbers that have the highest late job counts across all service records.

    ### Query Parameters:
    - None

    ### Returns:
    - **data**: Array of top 5 cars with:
        - **ro_no**: RO (Repair Order) number / Car ID (string)
        - **late_count**: Number of late jobs (int)
        - **total_count**: Total jobs for this car (int)
        - **msi**: MSI category (string)

    ### Example:
    ```
    GET /top-5-late-cars
    ```
    """
    try:
        logger.info("Fetching top 5 cars with most late status")

        # Call the helper function to get data
        data = get_top_5_late_cars()

        logger.info(f"Successfully retrieved top 5 late cars: {len(data['data'])} cars")

        return {
            "success": True,
            "data": data["data"],
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching top 5 late cars: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch top 5 late cars: {str(e)}"
        )


@app.get("/rework-rate")
async def rework_rate_api():
    """
    API Rework Rate: Get rework rate metrics and monthly breakdown.

    Returns rework rate percentage, first time fix rate, total counts, and monthly rework data.
    Data is based on vehicles delivered from the repeat_repairs table.

    ### Query Parameters:
    - None (returns all rework data)

    ### Returns:
    - **rework_rate**: Percentage of vehicles that required rework (float)
    - **first_time_fix_rate**: Percentage of vehicles fixed on first attempt (float)
    - **total_rework**: Total number of vehicles that required rework (int)
    - **total_vehicles**: Total number of vehicles delivered (int)
    - **rework_by_month**: Monthly breakdown table with columns:
        - **month**: Month in YYYY-MM format (string)
        - **rework_count**: Number of rework vehicles in that month (int)
        - **vehicles_delivered**: Total vehicles delivered in that month (int)

    ### Example:
    ```
    GET /rework-rate
    ```

    ### Response Example:
    ```json
    {
        "success": true,
        "rework_rate": 1.5,
        "first_time_fix_rate": 98.5,
        "total_rework": 172,
        "total_vehicles": 11472,
        "rework_by_month": [
            {"month": "2025-11", "rework_count": 0, "vehicles_delivered": 1},
            {"month": "2025-10", "rework_count": 5, "vehicles_delivered": 150}
        ],
        "timestamp": "2025-01-17T12:30:00"
    }
    ```
    """
    try:
        logger.info("Fetching rework rate data")

        # Call the helper function to get data
        data = get_rework_rate_data()

        rework_rate = data["rework_rate"]
        first_time_fix_rate = data["first_time_fix_rate"]
        total_rework = data["total_rework"]
        total_vehicles = data["total_vehicles"]
        rework_by_month = data["rework_by_month"]

        logger.info(f"Successfully retrieved rework rate data: {rework_rate}% rework rate, {total_rework}/{total_vehicles} vehicles")

        return {
            "success": True,
            "rework_rate": rework_rate,
            "first_time_fix_rate": first_time_fix_rate,
            "total_rework": total_rework,
            "total_vehicles": total_vehicles,
            "rework_by_month": rework_by_month,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching rework rate data: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch rework rate data: {str(e)}"
        )


@app.get("/rework-rate-by-date")
async def rework_rate_by_date_api(
    start_date: str,
    end_date: str
):
    """
    API Rework Rate By Date: Get daily rework counts within a date range.

    Returns a table of dates and their corresponding rework counts for the specified period.

    ### Query Parameters:
    - **start_date**: Start date in YYYY-MM-DD format (string)
    - **end_date**: End date in YYYY-MM-DD format (string)

    ### Returns:
    - **rework_data**: Daily breakdown table with columns:
        - **date**: Date in YYYY-MM-DD format (string)
        - **rework_count**: Number of rework jobs on that date (int)

    ### Example:
    ```
    GET /rework-rate-by-date?start_date=2024-01-01&end_date=2024-01-31
    ```

    ### Response Example:
    ```json
    {
        "success": true,
        "date_range": {
            "start_date": "2024-01-01",
            "end_date": "2024-01-31"
        },
        "total_days": 31,
        "total_rework_count": 45,
        "rework_data": [
            {"date": "2024-01-01", "rework_count": 2},
            {"date": "2024-01-02", "rework_count": 1},
            {"date": "2024-01-03", "rework_count": 3}
        ],
        "timestamp": "2025-01-17T12:30:00"
    }
    ```
    """
    try:
        # Validate date format
        from datetime import datetime as dt
        try:
            start_dt = dt.strptime(start_date, "%Y-%m-%d").date()
            end_dt = dt.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD format."
            )

        if start_dt > end_dt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date must be before or equal to end_date"
            )

        logger.info(f"Fetching rework rate by date: {start_date} to {end_date}")

        # Call the helper function to get data
        # IMPLEMENT get_rework_rate_by_date() function above to query your database
        data = get_rework_rate_by_date(start_date, end_date)

        rework_data = data["rework_data"]

        # Calculate summary statistics
        total_days = (end_dt - start_dt).days + 1
        total_rework_count = sum(item["rework_count"] for item in rework_data)

        logger.info(f"Successfully retrieved rework data for date range: {len(rework_data)} days with data, {total_rework_count} total reworks")

        return {
            "success": True,
            "date_range": {
                "start_date": start_date,
                "end_date": end_date
            },
            "total_days": total_days,
            "total_rework_count": total_rework_count,
            "rework_data": rework_data,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching rework rate by date: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch rework rate by date: {str(e)}"
        )


@app.get("/job-records")
async def job_records_api(
    page_number: int,
    receiving_date_time: Optional[str] = None,
    delivery_date_time: Optional[str] = None,
    promised_date_time: Optional[str] = None,
    technician_name: Optional[str] = None
):
    """
    API Job Records: Get paginated job records with optional filtering.

    Returns paginated job records (100 per page) with optional filters for dates and technician.
    Page numbering starts from 1 (page 1 returns records 1-100, page 2 returns 101-200, etc.).
    All parameters except page_number are optional.

    ### Query Parameters:
    - **page_number** (required): Page number (1-based, starting from 1). Each page contains 100 records.
    - **receiving_date_time** (optional): Filter by receiving date (YYYY-MM-DD format)
    - **delivery_date_time** (optional): Filter by delivery date (YYYY-MM-DD format)
    - **promised_date_time** (optional): Filter by promised date (YYYY-MM-DD format)
    - **technician_name** (optional): Filter by technician name (partial match supported)

    ### Returns:
    - **success**: Boolean indicating successful retrieval
    - **filters_applied**: Dictionary showing which filters were applied
    - **no_of_rows**: Number of rows returned in this page (max 100)
    - **total_records**: Total number of records matching all filters
    - **job_records**: Array of job record objects with columns:
        - **service_date**: Service date (string, YYYY-MM-DD)
        - **chassis_no**: Chassis number (string)
        - **ro_no**: Repair order number (string)
        - **service_nature**: Type of service (string)
        - **receiving_date_time**: When vehicle was received (string, datetime)
        - **delivery_date_time**: When vehicle was delivered (string, datetime)
        - **promised_date_time**: Promised delivery time (string, datetime)
        - **technician_name**: Assigned technician (string)
        - **vehicle_variant**: Vehicle model variant (string)
    - **timestamp**: Response timestamp

    ### Pagination Examples:
    ```
    # Get page 1 (first 100 records)
    GET /job-records?page_number=1

    # Get page 2 (records 101-200)
    GET /job-records?page_number=2

    # Get page 1 for specific technician
    GET /job-records?page_number=1&technician_name=tariq

    # Get page 1 with date filters
    GET /job-records?page_number=1&receiving_date_time=2025-05-22&delivery_date_time=2025-06-18
    ```

    ### Response Example:
    ```json
    {
        "success": true,
        "filters_applied": {
            "receiving_date_time": null,
            "delivery_date_time": null,
            "promised_date_time": null,
            "technician_name": "tariq"
        },
        "no_of_rows": 24,
        "total_records": 24,
        "job_records": [
            {
                "service_date": "2025-06-15",
                "chassis_no": "CH123456",
                "ro_no": "RO2500150",
                "service_nature": "Regular Service",
                "receiving_date_time": "2025-06-14 09:30:00",
                "delivery_date_time": "2025-06-15 17:45:00",
                "promised_date_time": "2025-06-16 10:00:00",
                "technician_name": "Muhammad Tariq",
                "vehicle_variant": "Fortuner"
            }
        ],
        "timestamp": "2025-11-18T15:45:00"
    }
    ```
    """
    try:
        logger.info(f"Fetching job records: page_number={page_number}, filters=[receiving={receiving_date_time}, "
                   f"delivery={delivery_date_time}, promised={promised_date_time}, technician={technician_name}]")

        # Validate page_number
        if page_number <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="page_number must be a positive integer (starting from 1)"
            )

        if page_number > 10000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="page_number cannot exceed 10000 pages (100 records per page)"
            )

        # Validate date formats if provided
        from datetime import datetime as dt
        if receiving_date_time:
            try:
                dt.strptime(receiving_date_time, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid receiving_date_time format. Use YYYY-MM-DD format."
                )

        if delivery_date_time:
            try:
                dt.strptime(delivery_date_time, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid delivery_date_time format. Use YYYY-MM-DD format."
                )

        if promised_date_time:
            try:
                dt.strptime(promised_date_time, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid promised_date_time format. Use YYYY-MM-DD format."
                )

        # Call the helper function to get data
        data = get_job_records(
            page_number=page_number,
            receiving_date_time=receiving_date_time,
            delivery_date_time=delivery_date_time,
            promised_date_time=promised_date_time,
            technician_name=technician_name
        )

        job_records = data["job_records"]
        no_of_rows = data["no_of_rows"]
        total_records = data.get("total_records", 0)

        logger.info(f"Successfully retrieved {no_of_rows} job records (out of {total_records} total)")

        return {
            "success": True,
            "filters_applied": {
                "receiving_date_time": receiving_date_time,
                "delivery_date_time": delivery_date_time,
                "promised_date_time": promised_date_time,
                "technician_name": technician_name
            },
            "no_of_rows": no_of_rows,
            "total_records": total_records,
            "job_records": job_records,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching job records: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch job records: {str(e)}"
        )


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler for uncaught errors.
    """
    logger.error(f"Uncaught exception: {str(exc)}")
    logger.error(traceback.format_exc())
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "message": "An internal server error occurred",
            "error": str(exc),
            "timestamp": datetime.now().isoformat(),
            "detail": "Check server logs for more information"
        }
    )


# ============================================================================
# APPLICATION STARTUP/SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """
    Application startup event - initialize resources.
    """
    logger.info("="*80)
    logger.info("Toyota PDF Processing API - Starting Up")
    logger.info("="*80)
    logger.info(f"Version: 4.0.0")
    logger.info(f"Upload Directory: {UPLOAD_DIR}")
    logger.info(f"Cleaned Directory: {CLEANED_DIR}")
    logger.info("="*80)


@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown event - cleanup resources.
    """
    logger.info("="*80)
    logger.info("Toyota PDF Processing API - Shutting Down")
    logger.info("="*80)


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload during development
        log_level="info"
    )