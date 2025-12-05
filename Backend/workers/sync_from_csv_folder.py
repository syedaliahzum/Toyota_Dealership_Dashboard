"""
Database synchronization from Backend CSV folder.

Automatically discovers CSV files generated in Backend folder and loads them into the database.
Looks for:
- Daily CPUs Reports CSV (daily*.csv or *daily*.csv)
- Technician Reports CSV (tech*.csv or *technician*.csv)
- Repeat Repair XLSX/CSV (repeat*.csv, repeat*.xlsx or *rework*.xlsx)
"""
from pathlib import Path
import sys
import glob

# Navigate to Toyota root from current location
current_file = Path(__file__).resolve()
if 'Backend' in str(current_file):
    backend_dir = current_file.parent if 'workers' not in str(current_file) else current_file.parent.parent
    toyota_root = backend_dir.parent
else:
    # Fallback
    toyota_root = Path(__file__).resolve().parent.parent

# Add Toyota root to path
sys.path.insert(0, str(toyota_root))

from database.lib.db import process_database_files


def find_csv_files():
    """
    Discover CSV files in Backend folder (excluding venv).
    Returns tuple of (daily_csv, tech_csv, repeat_file)
    """
    backend_dir = toyota_root / "Backend"
    
    print(f"📂 Searching for CSV files in: {backend_dir}")
    print()
    
    daily_csv = None
    tech_csv = None
    repeat_file = None
    
    # Search for files recursively, excluding venv
    all_files = []
    for ext in ['*.csv', '*.xlsx']:
        for f in backend_dir.rglob(ext):
            # Skip venv and node_modules
            if '.venv' not in str(f) and 'node_modules' not in str(f):
                all_files.append(f)
    
    if not all_files:
        print("⚠️  No CSV/XLSX files found in Backend folder")
        return None, None, None
    
    print(f"📄 Found {len(all_files)} relevant file(s) in Backend:")
    for f in all_files:
        rel_path = f.relative_to(backend_dir)
        print(f"   • {rel_path}")
    print()
    
    # Categorize files - prefer most recent
    daily_files = []
    tech_files = []
    repeat_files = []
    
    for f in all_files:
        fname_lower = f.name.lower()
        
        # Daily CPUs reports (CSV or XLSX)
        if 'daily' in fname_lower:
            daily_files.append(f)
        
        # Technician reports (CSV or XLSX)
        elif 'technician' in fname_lower:
            tech_files.append(f)
        
        # Repeat repair data (CSV or XLSX)
        elif 'repeat' in fname_lower or 'rework' in fname_lower:
            repeat_files.append(f)
    
    # Use the last (most recent) file from each category
    if daily_files:
        daily_csv = sorted(daily_files)[-1]
        print(f"✓ Daily file: {daily_csv.name}")
    
    if tech_files:
        tech_csv = sorted(tech_files)[-1]
        print(f"✓ Technician file: {tech_csv.name}")
    
    if repeat_files:
        repeat_file = sorted(repeat_files)[-1]
        print(f"✓ Repeat repair file: {repeat_file.name}")
    
    print()
    return daily_csv, tech_csv, repeat_file


def main():
    """
    Run database synchronization from Backend CSV files.
    """
    print(f"🚀 Database Sync from Backend CSV Folder\n")
    print(f"📂 Toyota root: {toyota_root}")
    print()
    
    # Discover files
    daily_csv, tech_csv, repeat_file = find_csv_files()
    
    # Validate required files
    if not daily_csv:
        print("❌ ERROR: Daily file not found in Backend folder")
        print("   Expected file matching pattern: *daily*.csv or *daily*.xlsx")
        return 1
    
    if not tech_csv:
        print("❌ ERROR: Technician file not found in Backend folder")
        print("   Expected file matching pattern: *technician*.csv or *technician*.xlsx")
        return 1
    
    print(f"📥 Files to process:")
    print(f"   • Daily CPUs: {daily_csv.name}")
    print(f"   • Technician: {tech_csv.name}")
    if repeat_file:
        print(f"   • Repeat repair: {repeat_file.name}")
    print()
    
    # Call the main database function
    print("🔄 Processing database files...\n")
    response = process_database_files(
        str(daily_csv),
        str(tech_csv),
        str(repeat_file) if repeat_file else None
    )
    
    # Handle response
    if response["success"]:
        print("\n✅ SUCCESS: Database synchronization completed!")
        print(f"Status: {response['status']}")
        print(f"\n📊 Data loaded:")
        print(f"   • Daily CPUs reports: {response['data']['daily_cpus_reports']} rows")
        print(f"   • Technician reports: {response['data']['technician_reports']} rows")
        print(f"   • Repeat repairs: {response['data']['repeat_repairs']} rows")
        print(f"   • Schema statements: {response['data']['tables_created']}")
        print(f"\n📁 Source files:")
        print(f"   • {daily_csv}")
        print(f"   • {tech_csv}")
        if repeat_file:
            print(f"   • {repeat_file}")
        
        # Clear all CSV files from Backend folder after successful load
        print("\n🧹 Clearing all CSV/XLSX files from Backend folder...")
        backend_dir = toyota_root / "Backend"
        
        deleted_count = 0
        # Delete all CSV and XLSX files (excluding venv and node_modules)
        for f in backend_dir.rglob("*.*"):
            if f.suffix.lower() in ['.csv', '.xlsx']:
                if '.venv' not in str(f) and 'node_modules' not in str(f):
                    try:
                        f.unlink()  # Delete file
                        deleted_count += 1
                        rel_path = f.relative_to(backend_dir)
                        print(f"   ✓ Deleted: {rel_path}")
                    except Exception as e:
                        print(f"   ✗ Failed to delete {f.name}: {e}")
        
        print(f"\n✅ Cleanup complete! Deleted {deleted_count} file(s)")
        return 0
    else:
        print("\n❌ ERROR: Database synchronization failed!")
        print(f"Status: {response['status']}")
        print(f"Error: {response['error']}")
        print("\n⚠️  CSV files NOT deleted due to sync failure")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
