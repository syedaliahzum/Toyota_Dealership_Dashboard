import pandas as pd
import numpy as np
import os

# Load the data (use raw string to avoid escape warnings)
file_path = r'D:\Toyota\csv_files\idea data of Repeat Repair.xlsx'

# Open the workbook and select sheet safely; fall back to the first sheet if 'All Tables' is missing
try:
    xls = pd.ExcelFile(file_path)
    available_sheets = xls.sheet_names
    if 'All Tables' in available_sheets:
        sheet_name = 'All Tables'
    else:
        sheet_name = available_sheets[0]
        print(f"Warning: Worksheet named 'All Tables' not found. Using sheet: {sheet_name}")

    df = pd.read_excel(xls, sheet_name=sheet_name)
except FileNotFoundError:
    raise FileNotFoundError(f"Input file not found: {file_path}")

# Clean the data
df['Date'] = pd.to_datetime(df['Date'])
df['Repeat Repair %age'] = df['Repeat Repair %age'].str.rstrip('%').astype(float) / 100
df = df.sort_values('Date')

# Add month name column
df['Month'] = df['Date'].dt.month_name()
df['Month_Year'] = df['Date'].dt.to_period('M')

# ========================================
# MONTHLY CALCULATIONS
# ========================================

monthly_data = []

for month_year in df['Month_Year'].unique():
    month_df = df[df['Month_Year'] == month_year]
    
    # Extract month name
    month_name = month_df['Date'].iloc[0].strftime('%B %Y')
    
    # Calculate metrics
    total_vehicle_delivered = month_df['Total Vehicle Delivered'].sum()
    total_rr = month_df['Repeat Repair Count'].sum()
    
    # Total Jobs = Total Vehicle Delivered + Repeat Repair
    total_jobs = total_vehicle_delivered
    
    # Repeat Repair %age = Total RR / Total Jobs × 100%
    if total_jobs > 0:
        repeat_repair_percentage = (total_rr / total_jobs) * 100
    else:
        repeat_repair_percentage = 0
    
    # First Time Fix = Total Vehicle Delivered - Total RR
    first_time_fix = total_vehicle_delivered - total_rr
    
    # First Time Fix Rate %age = (Total Vehicle Delivered - Total RR) / Total Jobs × 100%
    if total_jobs > 0:
        first_time_fix_rate = (first_time_fix / total_jobs) * 100
    else:
        first_time_fix_rate = 0
    
    monthly_data.append({
        'Month': month_name,
        'Total Vehicle Delivered': total_vehicle_delivered,
        'Total RR (Repeat Repair)': total_rr,
        'First Time Fix': first_time_fix,
        'Repeat Repair %': round(repeat_repair_percentage, 2),
        'First Time Fix Rate %': round(first_time_fix_rate, 2)
    })

# Create DataFrame for monthly data
monthly_df = pd.DataFrame(monthly_data)

print(monthly_df.to_string(index=False))
