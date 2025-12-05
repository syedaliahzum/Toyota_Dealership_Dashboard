"""
PDF Conversion and Cleaning Worker Module

This module processes three types of Toyota service reports:
1. Technician Report (TimeSheet) - Converts via ConvertAPI, cleans service data
2. Daily Report - Converts via pdfplumber, removes duplicates and adds status
3. Rework Report (Repeat Repair) - Converts via pdfplumber, removes totals/months

Each report is processed independently with its own function.
Output files maintain original names with '_cleaned' suffix.
"""

from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import pandas as pd
import numpy as np
import pdfplumber
import convertapi
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ConvertAPI Token
TOKEN = os.getenv("CONVERTAPI_TOKEN")
if TOKEN:
    convertapi.api_credentials = TOKEN

# Month names to filter (for Repeat Repair cleaning)
MONTH_NAMES = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December',
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Sept', 'Oct', 'Nov', 'Dec'
]


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def ensure_dir(p: Path) -> None:
    """Ensure directory exists, create if it doesn't."""
    p.mkdir(parents=True, exist_ok=True)


def parse_time_to_hours(time_str) -> Optional[float]:
    """
    Convert HH:MM:SS string to hours as float.
    
    Args:
        time_str: Time string in HH:MM:SS format
        
    Returns:
        Float representing hours, or None if invalid
    """
    try:
        if pd.isna(time_str) or str(time_str).strip() == '':
            return None
        time_str = str(time_str).strip()
        parts = time_str.split(':')
        if len(parts) == 3:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2])
            return hours + minutes/60 + seconds/3600
        return None
    except:
        return None


def extract_tables_from_pdf(pdf_path: Path, include_metadata: bool = True) -> List[pd.DataFrame]:
    """
    Extract all tables from PDF using pdfplumber.
    
    Args:
        pdf_path: Path to PDF file
        include_metadata: Whether to add source_page and table_number columns
        
    Returns:
        List of DataFrames, one per table found
    """
    all_tables: List[pd.DataFrame] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables() or []
            for tbl_idx, table in enumerate(tables, start=1):
                if not table or len(table) == 0:
                    continue

                # Use first row as header or create generic headers
                header = table[0]
                body = table[1:]
                
                if not header or any(h is None for h in header):
                    max_cols = max(len(row) for row in table)
                    header = [f"col_{i+1}" for i in range(max_cols)]
                    normalized = []
                    for row in table:
                        row = (row or []) + [None] * (max_cols - len(row or []))
                        normalized.append(row)
                    body = normalized
                else:
                    # Normalize body rows to match header length
                    max_cols = len(header)
                    normalized_body = []
                    for row in body:
                        row = (row or []) + [None] * (max_cols - len(row or []))
                        normalized_body.append(row[:max_cols])
                    body = normalized_body

                # Create DataFrame
                df = pd.DataFrame(body, columns=header)
                
                # Add metadata if requested
                if include_metadata:
                    df["source_page"] = page_idx
                    df["table_number"] = tbl_idx
                
                all_tables.append(df)

    return all_tables


def should_drop_row(row: pd.Series) -> bool:
    """
    Check if a row should be dropped (contains 'Total' or month names).
    
    Args:
        row: Pandas Series representing a row
        
    Returns:
        True if row should be dropped, False otherwise
    """
    row_str = ' '.join([str(val).strip() for val in row if pd.notna(val)]).lower()
    
    # Check for "Total"
    if 'total' in row_str:
        return True
    
    # Check for month names
    for month in MONTH_NAMES:
        if month.lower() in row_str:
            return True
    
    return False


# ============================================================================
# TECHNICIAN REPORT PROCESSING (TimeSheet)
# ============================================================================

def process_technician_report(
    input_pdf_path: Path,
    output_dir: Path
) -> Dict[str, any]:
    """
    Process Technician Report (TimeSheet):
    1. Convert PDF to XLSX using ConvertAPI
    2. Clean data (remove invalid RO/Reg numbers, zero jobs, duplicates, etc.)
    3. Save as CSV with original filename + '_cleaned.csv'
    
    Args:
        input_pdf_path: Path to input PDF file
        output_dir: Directory to save cleaned output
        
    Returns:
        Dictionary with processing results and statistics
    """
    print("\n" + "="*80)
    print(f"PROCESSING TECHNICIAN REPORT: {input_pdf_path.name}")
    print("="*80)
    
    if not input_pdf_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_pdf_path}")
    
    if not TOKEN:
        raise ValueError("CONVERTAPI_TOKEN not found in environment variables")
    
    ensure_dir(output_dir)
    
    # Step 1: Convert PDF to XLSX using ConvertAPI
    print("\n[1/2] Converting PDF to XLSX using ConvertAPI...")
    temp_xlsx = output_dir / f"{input_pdf_path.stem}_temp.xlsx"
    
    try:
        result = convertapi.convert(
            "xlsx",
            {"File": str(input_pdf_path)},
            from_format="pdf",
        )
        result.file.save(str(temp_xlsx))
        print(f"✅ Conversion complete: {temp_xlsx}")
        print(f"Conversion cost (credits): {getattr(result, 'conversion_cost', 'n/a')}")
    except Exception as e:
        raise Exception(f"ConvertAPI conversion failed: {e}")
    
    # Step 2: Clean the data
    print("\n[2/2] Cleaning service data...")
    
    # Read the Excel file
    df = pd.read_excel(temp_xlsx)
    initial_count = len(df)
    print(f"Initial rows: {initial_count}")
    
    # Track dropped rows
    dropped_stats = {
        'negative_ro_no': 0,
        'negative_reg_no': 0,
        'zero_jobs': 0,
        'no_technician_bay': 0,
        'duplicates': 0,
        'invalid_time_calc': 0
    }
    
    # 1. Filter missing/invalid RO No
    before = len(df)
    df = df[df['RO No'].notna() & (df['RO No'] != '')]
    dropped_stats['negative_ro_no'] = before - len(df)
    print(f"   - Dropped {dropped_stats['negative_ro_no']} rows with missing RO No")
    
    # 2. Filter missing/invalid Reg. No
    before = len(df)
    df = df[df['Reg. No'].notna() & (df['Reg. No'] != '')]
    dropped_stats['negative_reg_no'] = before - len(df)
    print(f"   - Dropped {dropped_stats['negative_reg_no']} rows with missing Reg. No")
    
    # 3. Filter rows with 0 or missing jobs
    before = len(df)
    df = df[(df['No. of Jobs'].notna()) & (df['No. of Jobs'] != 0)]
    dropped_stats['zero_jobs'] = before - len(df)
    print(f"   - Dropped {dropped_stats['zero_jobs']} rows with 0/missing jobs")
    
    # 4. Filter rows with jobs but no technician AND no bay
    before = len(df)
    condition = (
        (df['No. of Jobs'] != 0) & 
        (df['Technician Name'].isna() | (df['Technician Name'] == '')) & 
        (df['Bay'].isna() | (df['Bay'] == ''))
    )
    df = df[~condition]
    dropped_stats['no_technician_bay'] = before - len(df)
    print(f"   - Dropped {dropped_stats['no_technician_bay']} rows with jobs but no tech/bay")
    
    # 5. Remove duplicates based on RO No
    before = len(df)
    df = df.drop_duplicates(subset=['RO No'], keep='first')
    dropped_stats['duplicates'] = before - len(df)
    print(f"   - Dropped {dropped_stats['duplicates']} duplicate rows")
    
    # 6. Filter invalid time calculations
    before = len(df)
    df = df[df['P.Lead Time'].notna() & df['Overall Lead Time'].notna()]
    dropped_stats['invalid_time_calc'] = before - len(df)
    print(f"   - Dropped {dropped_stats['invalid_time_calc']} rows with invalid times")
    
    # Save cleaned data with original name + _cleaned
    output_file = output_dir / f"{input_pdf_path.stem}_cleaned.csv"
    df.to_csv(output_file, index=False)
    
    # Clean up temp file
    if temp_xlsx.exists():
        temp_xlsx.unlink()
    
    # Summary
    print("\n" + "-"*80)
    print("CLEANING SUMMARY")
    print("-"*80)
    print(f"Initial rows: {initial_count}")
    print(f"Final rows: {len(df)}")
    print(f"Total dropped: {initial_count - len(df)}")
    print(f"\n✅ Cleaned file saved: {output_file}")
    print("="*80)
    
    return {
        "success": True,
        "input_file": str(input_pdf_path),
        "output_file": str(output_file),
        "initial_rows": initial_count,
        "final_rows": len(df),
        "dropped_rows": initial_count - len(df),
        "statistics": dropped_stats
    }


# ============================================================================
# DAILY REPORT PROCESSING
# ============================================================================

def process_daily_report(
    input_pdf_path: Path,
    output_dir: Path
) -> Dict[str, any]:
    """
    Process Daily Report:
    1. Convert PDF to XLSX using pdfplumber
    2. Remove duplicates based on RO No
    3. Add status column (Late/On-time/Grace) based on receiving vs promised time
    4. Save as CSV with original filename + '_cleaned.csv'
    
    Args:
        input_pdf_path: Path to input PDF file
        output_dir: Directory to save cleaned output
        
    Returns:
        Dictionary with processing results and statistics
    """
    print("\n" + "="*80)
    print(f"PROCESSING DAILY REPORT: {input_pdf_path.name}")
    print("="*80)
    
    if not input_pdf_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_pdf_path}")
    
    ensure_dir(output_dir)
    
    # Step 1: Convert PDF using pdfplumber
    print("\n[1/2] Converting PDF using pdfplumber...")
    tables = extract_tables_from_pdf(input_pdf_path, include_metadata=True)
    
    if not tables:
        raise ValueError("No tables found in PDF")
    
    # Combine all tables
    df = pd.concat(tables, ignore_index=True)
    print(f"✅ Extracted {len(tables)} table(s), {len(df)} total rows")
    
    # Step 2: Clean the data
    print("\n[2/2] Cleaning daily data...")
    initial_rows = len(df)
    print(f"Initial rows: {initial_rows}")
    
    # Remove metadata columns
    df = df.drop(columns=['source_page', 'table_number'], errors='ignore')
    
    # Remove duplicates based on RO No
    before = len(df)
    df = df.drop_duplicates(subset=['RO No'], keep='first')
    duplicates_removed = before - len(df)
    print(f"   - Removed {duplicates_removed} duplicate rows")
    
    # Convert date columns to datetime
    df['RECEIVING_DATE_TIME'] = pd.to_datetime(df['RECEIVING_DATE_TIME'], errors='coerce')
    df['PROMISED_DATE_TIME'] = pd.to_datetime(df['PROMISED_DATE_TIME'], errors='coerce')
    
    # Add status column
    def determine_status(row):
        receiving = row['RECEIVING_DATE_TIME']
        promised = row['PROMISED_DATE_TIME']
        
        if pd.isna(receiving) or pd.isna(promised):
            return 'Unknown'
        
        # On-time: receiving time <= promised time
        if receiving <= promised:
            return 'On-time'
        # Grace: receiving time <= promised time + 30 minutes
        elif receiving <= promised + pd.Timedelta(minutes=30):
            return 'Grace'
        # Late: everything else
        else:
            return 'Late'
    
    df['status'] = df.apply(determine_status, axis=1)
    
    # Display status distribution
    print("\n   Status Distribution:")
    status_counts = df['status'].value_counts().to_dict()
    for status, count in status_counts.items():
        print(f"      {status}: {count}")
    
    # Save cleaned data with original name + _cleaned
    output_file = output_dir / f"{input_pdf_path.stem}_cleaned.csv"
    df.to_csv(output_file, index=False)
    
    # Summary
    print("\n" + "-"*80)
    print("CLEANING SUMMARY")
    print("-"*80)
    print(f"Initial rows: {initial_rows}")
    print(f"Final rows: {len(df)}")
    print(f"Duplicates removed: {duplicates_removed}")
    print(f"\n✅ Cleaned file saved: {output_file}")
    print("="*80)
    
    return {
        "success": True,
        "input_file": str(input_pdf_path),
        "output_file": str(output_file),
        "initial_rows": initial_rows,
        "final_rows": len(df),
        "duplicates_removed": duplicates_removed,
        "status_distribution": status_counts
    }


# ============================================================================
# REWORK REPORT PROCESSING (Repeat Repair)
# ============================================================================

def process_rework_report(
    input_pdf_path: Path,
    output_dir: Path
) -> Dict[str, any]:
    """
    Process Rework Report (Repeat Repair):
    1. Convert PDF to XLSX using pdfplumber (multi-sheet)
    2. Remove rows containing 'Total' or month names from all sheets
    3. Save as XLSX with original filename + '_cleaned.xlsx'
    
    Args:
        input_pdf_path: Path to input PDF file
        output_dir: Directory to save cleaned output
        
    Returns:
        Dictionary with processing results and statistics
    """
    print("\n" + "="*80)
    print(f"PROCESSING REWORK REPORT: {input_pdf_path.name}")
    print("="*80)
    
    if not input_pdf_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_pdf_path}")
    
    ensure_dir(output_dir)
    
    # Step 1: Convert PDF using pdfplumber
    print("\n[1/2] Converting PDF using pdfplumber...")
    tables = extract_tables_from_pdf(input_pdf_path, include_metadata=False)
    
    if not tables:
        raise ValueError("No tables found in PDF")
    
    print(f"✅ Extracted {len(tables)} table(s)")
    
    # Step 2: Clean and save to XLSX
    print("\n[2/2] Cleaning rework data...")
    
    output_file = output_dir / f"{input_pdf_path.stem}_cleaned.xlsx"
    
    sheet_results = {}
    total_original = 0
    total_removed = 0
    total_remaining = 0
    sheets_with_data = 0
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Write combined sheet first
        combined_df = pd.concat(tables, ignore_index=True)
        original_rows = len(combined_df)
        
        # Clean combined data
        mask = ~combined_df.apply(should_drop_row, axis=1)
        combined_cleaned = combined_df[mask].reset_index(drop=True)
        rows_removed = original_rows - len(combined_cleaned)
        
        # Only write combined sheet if it has data
        if len(combined_cleaned) > 0:
            combined_cleaned.to_excel(writer, sheet_name="All Tables", index=False)
            sheets_with_data += 1
            
            sheet_results["All Tables"] = {
                'original': original_rows,
                'removed': rows_removed,
                'remaining': len(combined_cleaned)
            }
        else:
            # Write original data if all rows would be removed
            combined_df.to_excel(writer, sheet_name="All Tables", index=False)
            sheets_with_data += 1
            print("   ⚠️  Warning: All rows would be removed from combined sheet - keeping original data")
            
            sheet_results["All Tables"] = {
                'original': original_rows,
                'removed': 0,
                'remaining': original_rows,
                'warning': 'No cleaning applied - all rows would be removed'
            }
        
        total_original += original_rows
        total_removed += rows_removed
        total_remaining += len(combined_cleaned) if len(combined_cleaned) > 0 else original_rows
        
        # Write individual sheets
        for idx, df in enumerate(tables, start=1):
            original_rows = len(df)
            
            # Clean data
            mask = ~df.apply(should_drop_row, axis=1)
            df_cleaned = df[mask].reset_index(drop=True)
            rows_removed = original_rows - len(df_cleaned)
            
            # Create sheet name
            sheet_name = f"Table_{idx}"[:31]
            
            # Only write sheet if it has data after cleaning, otherwise write original
            if len(df_cleaned) > 0:
                df_cleaned.to_excel(writer, sheet_name=sheet_name, index=False)
                sheets_with_data += 1
                
                sheet_results[sheet_name] = {
                    'original': original_rows,
                    'removed': rows_removed,
                    'remaining': len(df_cleaned)
                }
            else:
                # Write original data if all rows would be removed
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                sheets_with_data += 1
                print(f"   ⚠️  Warning: All rows would be removed from {sheet_name} - keeping original data")
                
                sheet_results[sheet_name] = {
                    'original': original_rows,
                    'removed': 0,
                    'remaining': original_rows,
                    'warning': 'No cleaning applied - all rows would be removed'
                }
    
    # Summary
    print("\n   Sheet-by-sheet summary:")
    for sheet_name, stats in sheet_results.items():
        print(f"      {sheet_name}: {stats['original']} → {stats['remaining']} rows "
              f"({stats['removed']} removed)")
    
    print("\n" + "-"*80)
    print("CLEANING SUMMARY")
    print("-"*80)
    print(f"Total original rows: {total_original}")
    print(f"Total removed rows: {total_removed}")
    print(f"Total remaining rows: {total_remaining}")
    print(f"\n✅ Cleaned file saved: {output_file}")
    print("="*80)
    
    return {
        "success": True,
        "input_file": str(input_pdf_path),
        "output_file": str(output_file),
        "total_original_rows": total_original,
        "total_removed_rows": total_removed,
        "total_remaining_rows": total_remaining,
        "sheet_results": sheet_results
    }


# ============================================================================
# MAIN PROCESSING FUNCTION
# ============================================================================

def process_reports(
    technician_pdf_path: Path,
    daily_pdf_path: Path,
    rework_pdf_path: Optional[Path],
    output_dir: Path
) -> Dict[str, any]:
    """
    Main function to process all reports.
    
    Args:
        technician_pdf_path: Path to technician report PDF
        daily_pdf_path: Path to daily report PDF
        rework_pdf_path: Optional path to rework report PDF
        output_dir: Directory to save all cleaned outputs
        
    Returns:
        Dictionary containing processing results for all reports
    """
    print("\n" + "="*80)
    print("PDF PROCESSING AND CLEANING - STARTING")
    print("="*80)
    
    results = {
        "success": True,
        "processed_files": {},
        "errors": [],
        "success_count": 0,
        "error_count": 0,
        "total_operations": 2 if rework_pdf_path is None else 3
    }
    
    ensure_dir(output_dir)
    
    # Process Technician Report
    try:
        print("\n[1/3] Processing Technician Report...")
        tech_result = process_technician_report(technician_pdf_path, output_dir)
        results["processed_files"]["technician_report"] = tech_result
        results["success_count"] += 1
    except Exception as e:
        error_msg = f"Technician report processing failed: {str(e)}"
        print(f"❌ {error_msg}")
        results["errors"].append(error_msg)
        results["error_count"] += 1
        results["success"] = False
    
    # Process Daily Report
    try:
        print("\n[2/3] Processing Daily Report...")
        daily_result = process_daily_report(daily_pdf_path, output_dir)
        results["processed_files"]["daily_report"] = daily_result
        results["success_count"] += 1
    except Exception as e:
        error_msg = f"Daily report processing failed: {str(e)}"
        print(f"❌ {error_msg}")
        results["errors"].append(error_msg)
        results["error_count"] += 1
        results["success"] = False
    
    # Process Rework Report (if provided)
    if rework_pdf_path:
        try:
            print("\n[3/3] Processing Rework Report...")
            rework_result = process_rework_report(rework_pdf_path, output_dir)
            results["processed_files"]["rework_report"] = rework_result
            results["success_count"] += 1
        except Exception as e:
            error_msg = f"Rework report processing failed: {str(e)}"
            print(f"❌ {error_msg}")
            results["errors"].append(error_msg)
            results["error_count"] += 1
            results["success"] = False
    else:
        print("\n[3/3] Rework Report - Skipped (not provided)")
    
    # Final Summary
    print("\n" + "="*80)
    print("FINAL SUMMARY")
    print("="*80)
    print(f"✅ Successful operations: {results['success_count']}/{results['total_operations']}")
    print(f"❌ Failed operations: {results['error_count']}/{results['total_operations']}")
    print(f"📁 Output directory: {output_dir}")
    
    if results["processed_files"]:
        print("\nCleaned files:")
        for report_type, report_data in results["processed_files"].items():
            print(f"  - {report_type}: {report_data.get('output_file', 'N/A')}")
    
    if results["errors"]:
        print("\nErrors encountered:")
        for error in results["errors"]:
            print(f"  - {error}")
    
    print("="*80)
    
    return results


# ============================================================================
# STANDALONE EXECUTION
# ============================================================================

if __name__ == "__main__":
    """
    Standalone execution for testing.
    Modify the paths below to test the processing functions.
    """
    # Example paths - modify as needed
    technician_pdf = Path("path/to/timesheet.pdf")
    daily_pdf = Path("path/to/daily.pdf")
    rework_pdf = Path("path/to/repeat_repair.pdf")  # Optional
    output_directory = Path("path/to/output")
    
    try:
        results = process_reports(
            technician_pdf_path=technician_pdf,
            daily_pdf_path=daily_pdf,
            rework_pdf_path=rework_pdf,
            output_dir=output_directory
        )
        
        if results["success"]:
            print("\n✅ All reports processed successfully!")
            sys.exit(0)
        else:
            print("\n⚠️ Some reports failed to process. Check errors above.")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        sys.exit(1)