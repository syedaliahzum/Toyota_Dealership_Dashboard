from pathlib import Path
import re
import sys
import traceback
from importlib.machinery import SourceFileLoader

BASE = Path(__file__).resolve().parents[1]  # Backend folder
PDF_DIR = BASE / "pdf"
OUTPUT_DIR = BASE / "csv"
WORKER_PATH = BASE / "workers" / "convert and clean.py"

print(f"Base: {BASE}")
print(f"PDF_DIR: {PDF_DIR}")
print(f"OUTPUT_DIR: {OUTPUT_DIR}")
print(f"Worker file: {WORKER_PATH}")

if not WORKER_PATH.exists():
    print("Worker file not found:", WORKER_PATH)
    sys.exit(1)

# Load the worker module that has a space in filename
loader = SourceFileLoader("convert_and_clean_worker", str(WORKER_PATH))
worker = loader.load_module()

# Ensure output dir exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Find pdf files
pdfs = [p for p in PDF_DIR.glob("*.pdf")]
if not pdfs:
    print("No PDFs found in", PDF_DIR)
    sys.exit(0)

# Group by leading timestamp (match YYYYMMDD_HHMMSS prefix)
pattern = re.compile(r"^(\d{8}_\d{6})")
by_ts = {}
for p in pdfs:
    m = pattern.match(p.name)
    if m:
        ts = m.group(1)
    else:
        ts = "unknown"
    by_ts.setdefault(ts, []).append(p)

print(f"Found timestamps: {list(by_ts.keys())}")

for ts, files in by_ts.items():
    # try to pick daily and technician from names
    daily = None
    tech = None
    for p in files:
        name = p.name.lower()
        if "daily" in name:
            daily = p
        if "technician" in name or "technician_report" in name:
            tech = p
    # if both present process pair
    if daily and tech:
        print(f"Processing pair for {ts}:\n  daily: {daily}\n  technician: {tech}")
        try:
            # convert daily with metadata True
            out_daily = worker.convert_pdf_with_pdfplumber(daily, OUTPUT_DIR, include_metadata=True)
            print("Converted daily ->", out_daily)
        except Exception as e:
            print("Error converting daily:", e)
            traceback.print_exc()
        try:
            # convert technician without metadata
            out_tech = worker.convert_pdf_with_pdfplumber(tech, OUTPUT_DIR, include_metadata=False)
            print("Converted technician ->", out_tech)
        except Exception as e:
            print("Error converting technician:", e)
            traceback.print_exc()
    else:
        print(f"Skipping timestamp {ts}, missing pair (daily: {bool(daily)}, technician: {bool(tech)})")

print("Done processing.")
