# Toyota Service Analytics API

Comprehensive FastAPI-based system for processing Toyota service reports and providing analytics through RESTful APIs.

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Quick Start](#quick-start)
- [API Endpoints](#api-endpoints)
- [Database Setup](#database-setup)
- [Configuration](#configuration)
- [Port Forwarding](#port-forwarding)

---

## Overview

This system processes three types of Toyota service reports (Technician, Daily CPUS, and Rework) and provides comprehensive analytics through REST APIs. It automatically converts PDFs to CSV/XLSX, cleans the data, syncs to MySQL database, and exposes metrics for technician performance, MSI data, and rework rates.

### Technology Stack
- **Backend**: FastAPI (Python 3.8+)
- **Database**: MySQL 8.0+
- **PDF Processing**: pdfplumber, ConvertAPI
- **Data Processing**: pandas, numpy

---

## Features

- PDF report upload and automatic conversion
- Data cleaning and validation
- Automatic database synchronization
- RESTful API for analytics
- CORS-enabled for frontend integration
- Comprehensive error handling and logging
- Interactive API documentation (Swagger/ReDoc)

---

## Quick Start

### 1. Prerequisites

- Python 3.8 or higher
- MySQL 8.0 or higher
- Git

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/Siyam00001/Toyota.git
cd Toyota

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Windows CMD:
venv\Scripts\activate.bat
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r Backend/requirements.txt
```

### 3. Database Setup

```bash
# Set environment variables (optional)
# Windows PowerShell:
$env:DB_HOST = "localhost"
$env:DB_USER = "root"
$env:DB_PASSWORD = "root"
$env:DB_NAME = "toyota_service"

# Start MySQL and create database
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS toyota_service;"
```

### 4. Run the Server

```bash
cd Backend
python main.py
```

Server will start at: `http://localhost:8000`

### 5. Access API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## API Endpoints

### Health & Info

#### GET `/`
Root endpoint with API information and available endpoints.

#### GET `/health`
Health check endpoint to verify API is operational.

```bash
curl http://localhost:8000/health
```

---

### Report Processing

#### POST `/upload-reports`
Upload and process Toyota service reports.

**Required Files:**
- `technicianreport`: Technician/TimeSheet report PDF
- `dailyreport`: Daily service report PDF

**Optional Files:**
- `reworkreport`: Repeat Repair/Rework report PDF

**Example using curl:**
```bash
curl -X POST "http://localhost:8000/upload-reports" \
  -F "technicianreport=@technician.pdf" \
  -F "dailyreport=@daily.pdf" \
  -F "reworkreport=@rework.pdf"
```

**Response:**
```json
{
  "message": "Reports uploaded and processed successfully",
  "status": "success",
  "uploaded_files": [...],
  "processing_summary": {
    "success": true,
    "total_operations": 3,
    "successful_operations": 3,
    "failed_operations": 0
  },
  "database_sync": {
    "success": true,
    "message": "Data successfully loaded into database"
  }
}
```

#### GET `/processed-files`
List all processed/cleaned files.

```bash
curl http://localhost:8000/processed-files
```

#### GET `/download/{filename}`
Download a cleaned/processed file.

```bash
curl http://localhost:8000/download/daily_cleaned.csv -O
```

---

### Analytics APIs

#### GET `/jobs-overview`
Get jobs overview with technician performance rankings.

**Response:**
```json
{
  "success": true,
  "num_total_jobs": 150,
  "total_technicians": 12,
  "job_data": [
    {
      "position": 1,
      "technician": "John Smith",
      "efficiency_percent": 95.5,
      "on_time": 43,
      "total_jobs": 45
    }
  ],
  "timestamp": "2025-01-17T12:30:00"
}
```

**Test:**
```bash
curl http://localhost:8000/jobs-overview
```

---

#### GET `/technician-performance`
Get specific technician's performance metrics.

**Query Parameters:**
- `name` (string): Technician name
- `start_date` (string): Start date (YYYY-MM-DD)
- `end_date` (string): End date (YYYY-MM-DD)

**Response:**
```json
{
  "success": true,
  "technician_name": "John Doe",
  "date_range": {
    "start_date": "2024-01-01",
    "end_date": "2024-01-31"
  },
  "late_jobs": 5,
  "ontime_jobs": 15,
  "grace_jobs": 5,
  "total_jobs": 25,
  "timestamp": "2025-01-17T12:30:00"
}
```

**Test:**
```bash
curl "http://localhost:8000/technician-performance?name=John%20Doe&start_date=2024-01-01&end_date=2024-01-31"
```

---

#### GET `/msi`
Get MSI (Maintenance Service Index) data for a category.

**Query Parameters:**
- `category` (string): The category to analyze

**Response:**
```json
{
  "success": true,
  "category": "maintenance",
  "most_used_operation": "Oil Change",
  "least_used_operation": "Engine Swap",
  "avg_no_of_operations": 42,
  "performance_table": [
    {
      "name": "Oil Change",
      "ontime": 120,
      "grace": 15,
      "late": 3
    }
  ],
  "timestamp": "2025-01-17T12:30:00"
}
```

**Test:**
```bash
curl "http://localhost:8000/msi?category=maintenance"
```

---

#### GET `/rework-rate`
Get rework rate metrics and monthly breakdown.

**Response:**
```json
{
  "success": true,
  "rework_rate": 15,
  "first_time_fix_rate": 85,
  "total_rework": 23,
  "total_jobs": 150,
  "rework_by_month": [
    {
      "month": "2025-01",
      "rework_count": 5
    },
    {
      "month": "2024-12",
      "rework_count": 7
    }
  ],
  "timestamp": "2025-01-17T12:30:00"
}
```

**Test:**
```bash
curl http://localhost:8000/rework-rate
```

---

### Maintenance

#### DELETE `/cleanup`
Clean up all uploaded and processed files.

**Warning:** This will delete all files in upload and cleaned directories.

```bash
curl -X DELETE http://localhost:8000/cleanup
```

---

## Database Setup

### Tables

The system uses three main tables:

1. **`daily_cpus_reports`** (56 rows, 46 columns)
   - Comprehensive daily service records
   - Customer, vehicle, service, and staff information

2. **`technician_reports`** (58 rows, 19 columns)
   - Repair order and technician data
   - Time tracking and bay assignments

3. **`repeat_repairs`** (aggregate data)
   - Daily repeat repair metrics
   - Percentage calculations

### Database Configuration

**Default Credentials:**
```
Host: localhost
Port: 3306
User: root
Password: root
Database: toyota_service
```

**Custom Configuration:**
Set environment variables to override defaults:

```bash
# Windows PowerShell
$env:DB_HOST = "localhost"
$env:DB_USER = "root"
$env:DB_PASSWORD = "your_password"
$env:DB_NAME = "toyota_service"
$env:DB_PORT = "3306"

# Linux/macOS
export DB_HOST="localhost"
export DB_USER="root"
export DB_PASSWORD="your_password"
export DB_NAME="toyota_service"
export DB_PORT="3306"
```

### Populate Database

The system automatically syncs data to the database after processing reports. You can also manually populate:

```bash
cd database
python -m database.populate_db
```

**Options:**
- `--setup-only`: Create tables without loading data
- `--dry-run`: Preview what would be done
- `--csv-dir PATH`: Use custom CSV directory

---

## Configuration

### Backend Configuration

Edit `Backend/config.py`:

```python
# Directory Configuration
UPLOAD_DIR = Path("uploads")
CLEANED_DIR = Path("cleaned")

# CORS Configuration
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "https://your-frontend-domain.com"
]
```

### ConvertAPI Key

For processing complex Technician/TimeSheet reports, set your ConvertAPI key:

```python
# In Backend/config.py
CONVERT_API_SECRET = "your_api_key_here"
```

Get a free key at: https://www.convertapi.com/

---

## Port Forwarding

To share your API with someone outside your local network:

### Option 1: ngrok (Recommended for Testing)

```bash
# Install ngrok from https://ngrok.com/download

# Run your API
cd Backend
python main.py

# In another terminal, expose port 8000
ngrok http 8000
```

You'll get a public URL like `https://abc123.ngrok.io`

### Option 2: VS Code Port Forwarding

1. Run your API
2. Go to **Ports** tab in VS Code
3. Forward port `8000`
4. Set visibility to **Public**
5. Share the forwarded URL

### Option 3: Router Port Forwarding

1. Find your local IP: `ipconfig` (Windows) or `ifconfig` (Linux/Mac)
2. Find your public IP: `curl ifconfig.me`
3. Configure router to forward port 8000 to your local IP
4. Share `http://YOUR_PUBLIC_IP:8000`

### Option 4: Cloud Deployment

For production, deploy to:
- **Railway**: `railway up`
- **Render**: Connect GitHub repo
- **Heroku**: `git push heroku main`
- **AWS/Azure/GCP**: Full cloud deployment

---

## Project Structure

```
Toyota/
├── Backend/
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Configuration settings
│   ├── requirements.txt        # Python dependencies
│   ├── workers/
│   │   ├── convertandclean.py  # PDF processing
│   │   └── sync_from_csv_folder.py  # Database sync
│   ├── uploads/                # Uploaded PDFs
│   └── cleaned/                # Processed files
├── Frontend/                   # React/Next.js frontend
├── database/
│   ├── schema.sql              # Database schema
│   ├── populate_db.py          # Database population script
│   └── lib/
│       └── db.py               # Database utilities
└── README.md                   # This file
```

---

## Development

### Running Tests

```bash
# Test API endpoints
curl http://localhost:8000/health

# Test database connection
python -c "from database.lib import db; print('✓ Success' if db.test_connection() else '✗ Failed')"
```

### Logging

Logs are written to `Backend/app.log` and console output.

### Hot Reload

The server runs with auto-reload enabled during development:

```bash
cd Backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## Troubleshooting

### Connection Issues

**"Connection refused"**
- Ensure MySQL is running
- Check port 3306 is accessible
- Windows: Start MySQL from Services
- Mac: `brew services start mysql`
- Linux: `sudo systemctl start mysql`

**"Access denied for user 'root'"**
- Verify password is correct
- Set `DB_PASSWORD` environment variable
- Reset MySQL password if needed

### CSV/File Issues

**"CSV file not found"**
- Verify files exist in correct directory
- Check file names match exactly
- Use absolute paths when needed

**"Duplicate entry in ingestion_log"**
- Script tracks ingested files
- To re-ingest: `DELETE FROM ingestion_log WHERE filename = 'filename.csv';`

### API Issues

**"404 Not Found"**
- Check endpoint URL is correct
- Ensure server is running on correct port
- Verify base URL is `http://localhost:8000`

**"CORS Error"**
- Add your frontend URL to `ALLOWED_ORIGINS` in `Backend/config.py`
- Restart the server after changes

---

## Support

For issues or questions:
1. Check the **Troubleshooting** section
2. Review FastAPI docs at http://localhost:8000/docs
3. Check server logs in `Backend/app.log`
4. Ensure all dependencies are installed: `pip install -r Backend/requirements.txt`

---

## License

Proprietary - Toyota Service Analytics Team

---

## Version

**Current Version**: 4.0.0
**Last Updated**: November 17, 2025

---

## Contributors

- Toyota Service Analytics Team
- Backend Development Team
- Database Team
