"""
Configuration file for Toyota PDF Processing API

Contains all configuration settings including:
- Directory paths
- CORS settings
- File size limits
- Environment variables
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================================================
# DIRECTORY CONFIGURATION
# ============================================================================

# Base directory (project root)
BASE_DIR = Path(__file__).resolve().parent

# Upload directory for incoming PDF files
UPLOAD_DIR = BASE_DIR / "uploads"

# Output directory for cleaned/processed files
CLEANED_DIR = BASE_DIR / "cleaned"

# ============================================================================
# API CONFIGURATION
# ============================================================================

# Allowed origins for CORS (Cross-Origin Resource Sharing)
# Add your frontend URLs here
ALLOWED_ORIGINS = [
    "http://localhost:3000",  # React default
    "http://localhost:8080",  # Vue default
    "http://localhost:5173",  # Vite default
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:5173",
    "*"  # Allow all origins - ALREADY ENABLED (works for network access)
]

# API configuration
API_VERSION = "4.0.0"
API_TITLE = "Toyota PDF Processing API"

# ============================================================================
# FILE CONFIGURATION
# ============================================================================

# Maximum file size (in bytes)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Allowed file types
ALLOWED_FILE_TYPES = ["application/pdf"]
ALLOWED_EXTENSIONS = [".pdf"]

# ============================================================================
# CONVERTAPI CONFIGURATION
# ============================================================================

# ConvertAPI token (required for technician report processing)
CONVERTAPI_TOKEN = os.getenv("CONVERTAPI_TOKEN", "")

if not CONVERTAPI_TOKEN:
    import warnings
    warnings.warn(
        "CONVERTAPI_TOKEN not found in environment variables. "
        "Technician report processing will fail without it. "
        "Please add CONVERTAPI_TOKEN to your .env file.",
        UserWarning
    )

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = "app.log"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# ============================================================================
# DEBUG CONFIGURATION
# ============================================================================

DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# ============================================================================
# DATABASE CONFIGURATION (for future use)
# ============================================================================

# Uncomment if you want to add database support in the future
# DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./toyota.db")

# ============================================================================
# VALIDATION
# ============================================================================

def validate_config():
    """
    Validate configuration settings on startup.
    Raises warnings or errors for invalid configurations.
    """
    issues = []
    
    # Check if CONVERTAPI_TOKEN is set
    if not CONVERTAPI_TOKEN:
        issues.append("⚠️  CONVERTAPI_TOKEN is not set - technician report processing will fail")
    
    # Check if directories exist (they will be created if not)
    if not UPLOAD_DIR.exists():
        issues.append(f"ℹ️  Upload directory will be created at: {UPLOAD_DIR}")
    
    if not CLEANED_DIR.exists():
        issues.append(f"ℹ️  Cleaned directory will be created at: {CLEANED_DIR}")
    
    # Print any issues found
    if issues:
        print("\n" + "="*80)
        print("CONFIGURATION VALIDATION")
        print("="*80)
        for issue in issues:
            print(issue)
        print("="*80 + "\n")
    
    return len([i for i in issues if i.startswith("⚠️")]) == 0  # Return False if there are warnings


# Run validation when config is imported
if __name__ != "__main__":
    validate_config()