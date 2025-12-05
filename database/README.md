# Toyota Service Database Setup Guide

This directory contains the database schema, population scripts, and utilities for the Toyota service center data pipeline. The database stores denormalized CSV data in MySQL for quick access and reporting.

---

## ⚡ Quick Installation

### One-Command Setup (Choose Your OS)

**Windows (Command Prompt):**
```cmd
cd database && setup.bat
```

**Windows (PowerShell):**
```powershell
cd database; python setup.py
```

**macOS/Linux:**
```bash
cd database && chmod +x setup.sh && ./setup.sh
```

**Manual (Any OS):**
```bash
pip install -r database/requirements.txt
```

### After Installation
1. Create `.env` file in Toyota root with database credentials
2. Run: `python test_kpi_with_data.py` to verify
3. See [Setup Documentation](#-setup-documentation) below for detailed instructions

---

## 📚 Setup Documentation

New comprehensive setup files have been created:

| File | Purpose |
|------|---------|
| `requirements.txt` | All Python dependencies (pinned versions) |
| `setup.py` | Cross-platform automated setup |
| `setup.bat` | Windows Command Prompt automation |
| `setup.sh` | macOS/Linux Bash automation |
| **`QUICK_START.md`** | ⭐ One-page quick reference (start here) |
| **`SETUP_INSTRUCTIONS.md`** | 📖 Detailed step-by-step guide with troubleshooting |
| **`SETUP_SUMMARY.md`** | 📋 Overview of all setup files |

### Getting Started
1. **For quick setup:** See `QUICK_START.md`
2. **For detailed instructions:** See `SETUP_INSTRUCTIONS.md`
3. **For OS-specific help:** See the OS-Specific Installation section below

---

## 🖥️ OS-Specific Installation

### Windows

**Easiest way - Run setup script:**
```cmd
cd database
setup.bat
```

**Or use Python setup script:**
```cmd
cd database
python setup.py
```

**Manual installation:**
```cmd
pip install -r database/requirements.txt
```

**If dependencies fail:**
- Try: `pip install --only-binary :all: mysql-connector-python`
- Or install Visual C++ Build Tools: https://visualstudio.microsoft.com/visual-cpp-build-tools/
- See `SETUP_INSTRUCTIONS.md` for more options

### macOS

**Easiest way - Run setup script:**
```bash
cd database
chmod +x setup.sh
./setup.sh
```

**Or use Python setup script:**
```bash
cd database
python3 setup.py
```

**Manual installation:**
```bash
pip install -r database/requirements.txt
```

**For Apple Silicon (M1/M2):**
```bash
conda install -c conda-forge -r database/requirements.txt
```

### Linux (Ubuntu/Debian)

**Easiest way - Run setup script:**
```bash
cd database
chmod +x setup.sh
./setup.sh
```

**Manual installation:**
```bash
sudo apt-get install python3-dev mysql-client libmysqlclient-dev
pip install -r database/requirements.txt
```

**For CentOS/RHEL:**
```bash
sudo yum install python3-devel mysql-devel
pip install -r database/requirements.txt
```

---

## ✅ Verify Installation

```bash
# Test imports
python -c "import mysql.connector, pandas, openpyxl; print('✓ All packages installed')"

# Test KPI functions (from database directory)
python test_kpi_with_data.py
```

Expected output should show all 4 KPI functions with `Success: True`

---

## 🎯 Main Function: `process_database_files()`

**This is the PRIMARY way to interact with the database.** It handles all operations in one function call.

### Quick Example
```python
from database.lib.db import process_database_files

response = process_database_files(
    daily_csv_path="database/DAILY CPUS REPORT (1)_cleaned.csv",
    tech_csv_path="database/20251112_141532_technician_TECHNICIAN REPORT1.csv",
    schema_sql_path="database/schema.sql",
    repeat_csv_path="database/Repeat Repair_extracted.csv"
)

if response["success"]:
    print("✅ Success!")
    print(f"Daily reports: {response['data']['daily_cpus_reports']}")
    print(f"Tech reports: {response['data']['technician_reports']}")
else:
    print(f"❌ Error: {response['error']}")
```

### Function Signature
```python
process_database_files(
    daily_csv_path: str,          # Path to daily CPUs CSV
    tech_csv_path: str,           # Path to technician reports CSV
    schema_sql_path: str,         # Path to schema SQL file
    repeat_csv_path: str = None   # Path to repeat repairs CSV (optional)
) -> Dict[str, Any]
```

### Return Value
```python
{
    "success": True,                    # Whether all operations succeeded
    "status": "All database operations completed successfully",
    "data": {
        "daily_cpus_reports": 56,      # Rows inserted
        "technician_reports": 58,      # Rows inserted
        "repeat_repairs": 0,           # Rows inserted
        "tables_created": 8            # SQL statements executed
    },
    "error": None                       # Error message if failed
```

### Integration with FastAPI
```python
from fastapi import FastAPI, UploadFile, File
from database.lib.db import process_database_files
from pathlib import Path

@app.post("/api/upload-database")
async def upload_database(
    daily_csv: UploadFile = File(...),
    tech_csv: UploadFile = File(...),
    schema_sql: UploadFile = File(...),
    repeat_csv: UploadFile = File(None)
):
    # Save uploaded files temporarily
    daily_path = f"/tmp/{daily_csv.filename}"
    tech_path = f"/tmp/{tech_csv.filename}"
    schema_path = f"/tmp/{schema_sql.filename}"
    repeat_path = f"/tmp/{repeat_csv.filename}" if repeat_csv else None
    
    # Call the function
    response = process_database_files(daily_path, tech_path, schema_path, repeat_path)
    
    return response
```

---

## 📋 Prerequisites

### System Requirements
- **Python**: 3.8 or higher
- **MySQL/MariaDB**: 5.7 or higher (MySQL 8.0+ recommended)
- **Disk Space**: ~100MB (including CSV files and database)

### Required Packages
All dependencies are listed in `database/requirements.txt`:

```bash
# Install from Toyota root directory
pip install -r database/requirements.txt
```

**Key packages:**
- `mysql-connector-python==8.2.0` — MySQL database driver
- `pandas==2.2.0` — CSV reading and data manipulation
- `openpyxl==3.1.2` — Excel file support
- `python-dotenv>=1.0.0` — Environment variables

**For automated setup, see:**
- Windows: Run `database/setup.bat`
- macOS/Linux: Run `database/setup.sh`
- Or see `database/SETUP_INSTRUCTIONS.md` for detailed instructions

### MySQL Server
Ensure MySQL is running and accessible:
- **Default host**: `localhost`
- **Default port**: `3306`
- **Default user**: `root`
- **Default password**: `root`

To verify MySQL is running:
```bash
mysql -u root -p -e "SELECT 1"
```

---

## 🗄️ Database Tables

### 1. `technician_reports` (58 rows)
Repair order and technician data.

**Key Columns**: `sr`, `ro_no`, `mileage`, `technician_name`, `bay`, `p_start_time`, `p_end_time`, `remarks`

### 2. `daily_cpus_reports` (56 rows)
Comprehensive daily service records.

**Key Columns**:
- Customer: `customer_name`, `customer_mobile_no`, `customer_email`, `customer_type`
- Vehicle: `chassis_number`, `reg_no`, `vehicle_make`, `vehicle_variant`, `model_year`
- Service: `ro_no`, `service_date`, `service_nature`, `service_sub_category`, `status`
- Dates: `receiving_date_time`, `delivery_date_time`, `promised_date_time`, `prefered_date_time_for_psfu`
- Staff: `service_avisor_name`, `technical_advisor_name`, `job_controller_name`, `technician_name`

### 3. `repeat_repairs` (aggregate)
Daily repeat repair metrics.

**Columns**: `date`, `total_vehicle_delivered`, `repeat_repair_count`, `repeat_repair_percentage`

---

## 🚀 Quick Start

### Prerequisites
First, install dependencies from the database folder:

```bash
# From the Toyota root directory
pip install -r database/requirements.txt
```

**If you encounter errors**, see the [OS-Specific Installation](#os-specific-installation) section below.

### Windows — PowerShell

```powershell
# Navigate to project root
cd C:\path\to\Toyota

# Create virtual environment (recommended)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r database/requirements.txt

# Create tables and load data
python -m database.populate_db
```

**Just the table setup (no data)?**
```powershell
python -m database.populate_db --setup-only
```

### Windows — Command Prompt (cmd.exe)

```cmd
cd C:\path\to\Toyota
python -m venv venv
venv\Scripts\activate.bat
pip install -r database/requirements.txt
python -m database.populate_db
```

### macOS / Linux — Bash/Zsh

```bash
# Navigate to project root
cd /path/to/Toyota

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r database/requirements.txt

# Create tables and load data
python -m database.populate_db
```

**Just the table setup (no data)?**
```bash
python -m database.populate_db --setup-only
```

---

## 🖥️ OS-Specific Installation

### Windows

**Option 1: Using pip (Recommended)**
```powershell
# In PowerShell
pip install -r database/requirements.txt
```

**Option 2: If mysql-connector-python fails**
```powershell
pip install --no-binary mysql-connector-python mysql-connector-python
```

**Option 3: Using Conda (if you have Anaconda)**
```powershell
conda install -c conda-forge mysql-connector-python pandas openpyxl
```

**Troubleshooting Windows:**
- If you get "Visual C++ build tools" error, download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
- Ensure Python is in PATH: `python --version`
- Try with Administrator privileges: Right-click Command Prompt → Run as administrator
- For mysql-connector-python issues on Windows, try: `pip install --only-binary :all: mysql-connector-python`

### macOS

**Option 1: Using pip (Recommended)**
```bash
pip install -r database/requirements.txt
```

**Option 2: Using Homebrew**
```bash
# Install MySQL client
brew install mysql-client

# Then install Python packages
pip install -r database/requirements.txt
```

**Option 3: Using Conda**
```bash
conda install -c conda-forge mysql-connector-python pandas openpyxl
```

**Troubleshooting macOS:**
- If you need Xcode tools: `xcode-select --install`
- For Apple Silicon (M1/M2): Use conda for better ARM compatibility
- MySQL might need: `brew install mysql@8.0`

### Linux (Ubuntu/Debian)

**Option 1: Using pip (Recommended)**
```bash
# Install required system packages first
sudo apt-get update
sudo apt-get install python3-dev mysql-client libmysqlclient-dev

# Then install Python packages
pip install -r database/requirements.txt
```

**Option 2: Using apt (System packages)**
```bash
sudo apt-get install python3-pip python3-venv mysql-client
sudo apt-get install python3-pandas python3-openpyxl
# Note: mysql-connector-python may not be available via apt, use pip
pip install mysql-connector-python
```

**Option 3: Using conda**
```bash
conda install -c conda-forge mysql-connector-python pandas openpyxl
```

**Troubleshooting Linux:**
- If mysql.h is missing: `sudo apt-get install libmysqlclient-dev`
- For CentOS/RHEL: `sudo yum install mysql-devel python3-devel`
- Ensure pip is up-to-date: `pip install --upgrade pip`

---

## ⚙️ Command-Line Options

```
python -m database.populate_db [OPTIONS]

Options:
  --setup-only          Create tables without loading data
  --dry-run            Show what would be done without making changes
  --csv-dir PATH       Use custom CSV directory (default: ./database)
  -h, --help          Show help message
```

**Examples**:
```bash
# Dry-run to preview before loading
python -m database.populate_db --dry-run

# Create tables only
python -m database.populate_db --setup-only

# Use CSVs from a different folder
python -m database.populate_db --csv-dir "/path/to/csvs"
```

---

## 🔧 Configuration

### Environment Variables (Optional)
If you need non-default credentials, set environment variables:

**PowerShell**:
```powershell
$env:DB_HOST = "localhost"
$env:DB_USER = "root"
$env:DB_PASSWORD = "root"
$env:DB_NAME = "toyota_service"
$env:DB_PORT = "3306"
```

**Bash/Zsh**:
```bash
export DB_HOST="localhost"
export DB_USER="root"
export DB_PASSWORD="root"
export DB_NAME="toyota_service"
export DB_PORT="3306"
```

**Command Prompt**:
```cmd
set DB_HOST=localhost
set DB_USER=root
set DB_PASSWORD=root
set DB_NAME=toyota_service
set DB_PORT=3306
```

---

## 📂 CSV Files

The script expects these files in the `database/` directory:

| File | Rows | Columns | Updated |
|------|------|---------|---------|
| `DAILY CPUS REPORT (1)_cleaned.csv` | 56 | 46 | Nov 17, 2025 |
| `20251112_141532_technician_TECHNICIAN REPORT1.csv` | 58 | 19 | Nov 12, 2025 |
| `Repeat Repair_extracted.csv` | 244 | 4 | Nov 12, 2025 |

**Note**: Column names with spaces, newlines, and special characters are automatically normalized (e.g., `SA/TA INSTRUCTIONS` → `sa_ta_instructions`).

---

## ✅ Verification

### Check if Setup Worked
```python
from database.lib import db

# Test connection
if db.test_connection():
    print("✓ Database connection successful")
else:
    print("✗ Connection failed")

# Count records
result = db.run_query(
    "SELECT COUNT(*) as cnt FROM daily_cpus_reports",
    fetch=True
)
print(f"Total CPUS records: {result[0]['cnt']}")
```

### Query Examples
```python
from database.lib import db

# Get records by date
result = db.run_query(
    "SELECT ro_no, customer_name, service_date FROM daily_cpus_reports "
    "WHERE service_date = %s LIMIT 5",
    params=("2025-11-04",),
    fetch=True
)

for row in result:
    print(f"RO: {row['ro_no']}, Customer: {row['customer_name']}, Date: {row['service_date']}")
```

---

## 🐛 Troubleshooting

### Connection Problems

**Error: "Connection refused"**
```
✓ Ensure MySQL is running
✓ Check that localhost:3306 is accessible
✓ On Windows: Start MySQL from Services (services.msc)
✓ On macOS: brew services start mysql
✓ On Linux: sudo systemctl start mysql
```

**Error: "Access denied for user 'root'"**
```
✓ Verify password is correct
✓ Set DB_PASSWORD environment variable if different
✓ Reset MySQL password: https://dev.mysql.com/doc/refman/8.0/en/resetting-permissions.html
```

### CSV/Data Problems

**Error: "CSV file not found"**
```
✓ Verify files exist in database/ directory
✓ Check file names match exactly
✓ Use --csv-dir option for custom path
```

**Error: "Duplicate entry in ingestion_log"**
```
✓ Script tracks ingested files to prevent re-processing
✓ To re-ingest a file:
   DELETE FROM ingestion_log WHERE filename = 'DAILY CPUS REPORT (1)_cleaned.csv';
✓ Then run populate_db.py again
```

**Columns with NULL values**
```
✓ Some columns intentionally remain NULL when source CSV is empty
✓ Example: campaign_type, customer_mobile_no2
✓ Check raw CSV: those columns are also empty there
✓ This is correct behavior, not a bug
```

### Schema Issues

**Error: "Table already exists"**
```
✓ Tables are created with CREATE TABLE IF NOT EXISTS
✓ To rebuild, drop the old table:
   DROP TABLE daily_cpus_reports;
✓ Then run populate_db.py again
```

**Error: "Unknown column"**
```
✓ Ensure schema.sql and populate_db.py are in sync
✓ Special mapping: SERVICE_AVISOR_NAME (typo in CSV) → service_avisor_name (DB)
✓ Column normalization: spaces/slashes become underscores
```

---

## 📊 Features

### Automatic Column Normalization
CSV column names are automatically converted:
- `Spaces` → `underscores`
- `Line breaks` → `underscores`  
- `Special chars` (`.`, `-`, `/`) → `underscores`
- `UPPERCASE` → `lowercase`

**Example**: `SA/TA INSTRUCTIONS` → `sa_ta_instructions`

### Flexible Datetime Parsing
Supports multiple date/time formats:
- `2025-11-04` (date only)
- `2025-11-04 09:21:00` (ISO format)
- `2025-11-04 09:21:00.142` (with milliseconds)

### Duplicate Prevention
The `ingestion_log` table tracks which CSV files have been processed to prevent accidental re-ingestion.

### Atomic Transactions
All data loads use database transactions — either the entire batch succeeds or rolls back. No partial inserts.

---

## 📁 File Structure

```
database/
├── 📋 Documentation & Setup
│   ├── README.md                                    # Main documentation (this file)
│   ├── QUICK_START.md                               # One-page quick reference ⭐ START HERE
│   ├── SETUP_INSTRUCTIONS.md                        # Detailed setup guide (all OS)
│   ├── SETUP_SUMMARY.md                             # Overview of setup files
│   ├── requirements.txt                             # Python dependencies
│   ├── setup.py                                     # Cross-platform setup script
│   ├── setup.bat                                    # Windows setup (Command Prompt)
│   └── setup.sh                                     # macOS/Linux setup (Bash)
│
├── 🗄️ Database & Schema
│   ├── schema.sql                                   # Table definitions & indexes
│   ├── schema.md                                    # Schema documentation
│   └── lib/
│       ├── __init__.py
│       └── db.py                                    # Connection pool + query helpers
│
├── 📊 Data Processing
│   ├── populate_db.py                               # Main database population script
│   ├── process_files_example.py                     # Example usage
│   └── kpi_operations.py                            # KPI reporting functions (NEW!)
│
├── 🧪 Testing
│   ├── test_kpi_with_data.py                        # Test all KPI functions (NEW!)
│
├── 📁 Scripts & Utilities
│   └── scripts/
│       ├── insert_repeat.py
│       ├── show_repeat_repairs.py
│       └── update_repeat_repairs_from_csv.py
│
└── 📄 Data Files
    ├── DAILY CPUS REPORT (1)_cleaned.csv            # Daily service data (56 rows)
    ├── 20251112_141532_technician_TECHNICIAN REPORT1.csv # Technician data (58 rows)
    ├── Repeat Repair_extracted.csv                  # Repeat repair data (244 rows)
    └── .env.example                                 # Environment variables template
```

### Key Files by Purpose

**🚀 To Get Started:**
1. `QUICK_START.md` - One-page reference
2. `SETUP_INSTRUCTIONS.md` - Detailed guide
3. `setup.bat` or `setup.sh` - Automated setup

**📚 Documentation:**
- `README.md` - This comprehensive guide
- `schema.md` - Database schema details

**💻 Code:**
- `lib/db.py` - Database operations and connection pooling
- `populate_db.py` - Data loading script
- `kpi_operations.py` - KPI reporting (4 functions)

**🧪 Testing:**
- `test_kpi_with_data.py` - Verify all functions work

---

## 📊 KPI Operations Module

The `kpi_operations.py` module provides comprehensive KPI reporting functions, fully tested with actual database data.

### Available Functions

#### 1. `get_technician_efficiency_kpis(service_date: date) → Dict`
Groups technician performance data by technician name and status.

**Returns:**
```python
{
    "success": True,
    "total_records": 56,
    "data": [
        {
            "technician_name": "Rizwan Iqbal",
            "status": "Grace",
            "record_count": 5
        },
        ...
    ]
}
```

#### 2. `get_repeat_repair_kpis(service_date: Optional[date] = None) → Dict`
Retrieves repeat repair statistics and metrics for a specific date or all data.

**Returns:**
```python
{
    "success": True,
    "total_records": 1,
    "data": [
        {
            "date": "2025-11-04",
            "total_vehicle_delivered": 85,
            "repeat_repair_count": 0,
            "repeat_repair_percentage": 0.0
        }
    ]
}
```

#### 3. `get_msi_kpis(service_date: date) → Dict`
Provides MSI (Major Service Items) summaries and operation statistics.

**Returns:**
```python
{
    "success": True,
    "daily_cpus_total": 56,
    "technician_total": 56,
    "msi_summary": {
        "CARE": 12,
        "GR": 13,
        "LIGHT": 3,
        "MEDIUM": 3,
        "OIL FILTER": 21,
        "SUPER LIGH": 4
    },
    "operation_summary": [...],
    "data": [...]
}
```

#### 4. `get_combined_msi_report(service_date: date) → Dict`
Joins daily reports with technician reports for comprehensive analysis.

**Returns:**
```python
{
    "success": True,
    "total_daily_records": 56,
    "total_tech_records": 56,
    "total_matched_records": 56,
    "matched_percentage": 100.0,
    "data": [
        {
            "ro_number": "237270",
            "status": "Grace",
            "msi": "SUPER LIGH",
            "number_of_jobs": null,
            "operation": "ENGINE OIL AND OIL FILTER\nCHANGE",
            "technician_name": "Rizwan Iqbal",
            "service_date": "2025-11-04"
        }
    ]
}
```

### Usage Example

```python
from kpi_operations import (
    get_technician_efficiency_kpis,
    get_repeat_repair_kpis,
    get_msi_kpis,
    get_combined_msi_report
)
from datetime import date

# Get efficiency metrics
result = get_technician_efficiency_kpis(date(2025, 11, 4))
if result['success']:
    print(f"Retrieved {result['total_records']} records")
    for record in result['data']:
        print(f"  {record['technician_name']}: {record['record_count']} jobs")

# Get MSI metrics
msi_result = get_msi_kpis(date(2025, 11, 4))
print(f"MSI Summary: {msi_result['msi_summary']}")

# Get combined report
report = get_combined_msi_report(date(2025, 11, 4))
print(f"Match Rate: {report['matched_percentage']:.2f}%")
```

### Testing KPI Functions

All functions have been tested with actual data:

```bash
# From database directory
python test_kpi_with_data.py
```

**Test Results (with 2025-11-04 data):**
- ✅ Technician Efficiency KPIs: 56 records, 18 groups
- ✅ Repeat Repair KPIs: 1 record retrieved
- ✅ MSI KPIs: 56 records with MSI breakdown
- ✅ Combined MSI Report: 56 records (100% match rate)

---

## ⏱️ Performance

- **Initial load time**: ~0.3 seconds
- **CPUS records**: 56 rows
- **Technician records**: 58 rows
- **Repeat repairs**: 244 rows (aggregated)

---

## 🔄 Maintenance

### Backup Database
```bash
mysqldump -u root -p toyota_service > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Restore from Backup
```bash
mysql -u root -p toyota_service < backup_20251117_120000.sql
```

### Re-populate from Scratch
```bash
# Drop all tables
python -c "from database.lib import db; db.run_query('DROP TABLE IF EXISTS daily_cpus_reports; DROP TABLE IF EXISTS technician_reports; DROP TABLE IF EXISTS repeat_repairs;', commit=True)"

# Reload
python -m database.populate_db
```

---

## 📝 Recent Changes

**November 17, 2025** (Latest):
- ✅ **NEW**: Created `requirements.txt` with all dependencies (mysql-connector-python, pandas, openpyxl, etc.)
- ✅ **NEW**: Added `setup.py` - Cross-platform automated setup (Windows/macOS/Linux)
- ✅ **NEW**: Added `setup.bat` - Windows Command Prompt automation
- ✅ **NEW**: Added `setup.sh` - macOS/Linux Bash automation
- ✅ **NEW**: Created `SETUP_INSTRUCTIONS.md` - Comprehensive setup guide (200+ lines)
- ✅ **NEW**: Created `SETUP_SUMMARY.md` - Overview of setup files
- ✅ **NEW**: Created `QUICK_START.md` - One-page quick reference
- ✅ **NEW**: Completed `kpi_operations.py` - 4 fully tested KPI functions
- ✅ **NEW**: Created `test_kpi_with_data.py` - Test script for all KPI functions
- ✅ Fixed database schema column references (ro_no, operations, no_of_jobs)
- ✅ All 4 KPI functions tested and working with actual data

**Previous Updates**:
- ✅ Added `process_database_files()` function as primary interface
- ✅ Created example usage file (`process_files_example.py`)
- ✅ Added `status` column to daily_cpus_reports
- ✅ Removed `source_page`, `table_number` columns
- ✅ Fixed service_avisor_name mapping (typo handling)
- ✅ Updated CSV file to DAILY CPUS REPORT (1)_cleaned.csv

---

## 💬 Support

For setup help:
1. **Quick start:** See `QUICK_START.md` (1-page reference)
2. **Detailed guide:** See `SETUP_INSTRUCTIONS.md` (comprehensive instructions)
3. **Summary:** See `SETUP_SUMMARY.md` (overview of files)

For other issues:
1. Check the **Troubleshooting** section above
2. Verify MySQL is running and accessible
3. Ensure Python 3.8+ is installed
4. Install dependencies: `pip install -r database/requirements.txt`
5. Or use automated setup: `database/setup.bat` (Windows) or `database/setup.sh` (macOS/Linux)
