"""Generate 500 rows of accurate test data from Sept 1 to Nov 18, 2025"""

import mysql.connector
from datetime import datetime, timedelta, date
import random

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 3307,
    'user': 'toyota_user',
    'password': 'toyota_password',
    'database': 'toyota_db'
}

def get_connection():
    """Create and return a database connection"""
    return mysql.connector.connect(**DB_CONFIG)

def is_weekend(date_obj):
    """Check if date is Saturday (5) or Sunday (6)"""
    return date_obj.weekday() in [5, 6]

def clear_database():
    """Clear all existing data from tables"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM daily_cpus_reports")
        cursor.execute("DELETE FROM technician_reports")
        cursor.execute("DELETE FROM repeat_repairs")
        conn.commit()
        print("✓ Database cleared - all tables reset")
    except Exception as e:
        print(f"✗ Error clearing database: {e}")
    finally:
        cursor.close()
        conn.close()

def generate_500_rows_data():
    """Generate 500 rows of accurate data from Sept 1 to Nov 18, 2025"""
    
    # September 1, 2025 to November 18, 2025
    start_date = date(2025, 9, 1)
    end_date = date(2025, 11, 18)
    
    technicians = [
        "Ahmed Hassan", "Fatima Khan", "Hassan Ali", "Sara Malik",
        "Ibrahim Sheikh", "Ayesha Ahmed", "Usman Khan", "Zainab Hassan",
        "Muhammad Ali", "Hina Patel"
    ]
    
    service_advisers = [
        "Ali Raza", "Sophia Khan", "Hassan Malik", "Amira Ahmed",
        "Bilal Hassan", "Nadia Khan", "Tariq Ali"
    ] 
    
    # MSI categories - properly distributed
    msi_values = ["GR", "CARE","LIGHT","OIL FILTER", "SUPER LIGH", "MEDIUM", "HEAVY"]
    
    variants = ["GLi", "GLi Plus", "Automatic", "2.0L", "1.3L", "Hybrid"]
    service_natures = ["Routine Service", "Major Service", "Warranty", "Accident Repair"]
    campaign_types = ["Regular", "Recall", "Campaign", "Free Service"]
    customer_sources = ["Walk-in", "Referral", "Online", "Warranty", "Corporate"]
    customer_types = ["Retail", "Corporate", "Fleet", "Insurance"]
    insurance_statuses = ["Covered", "Not Covered", "Under Process"]
    vehicle_types = ["Sedan", "SUV", "Hatchback", "Pick-up"]
    bays = ["Bay-1", "Bay-2", "Bay-3", "Bay-4", "Bay-5", "Bay-6"]
    
    daily_cpus_data = []
    technician_reports_data = []
    repeat_repairs_data = []
    
    # MSI-specific operations
    msi_operations = {
        'LIGHT': 'Light inspection and basic maintenance',
        'OIL FILTER': 'Oil and filter change with top-up',
        'GR': 'General repair and maintenance',
        'CARE': 'Care service - fluid checks and adjustments',
        'SUPER LIGH': 'Super light service - basic maintenance',
        'MEDIUM': 'Medium service - component inspection and replacement',
        'HEAVY': 'Heavy service - major repairs and overhaul'
    }
    
    record_count = 0
    
    print(f"\n🗓️  Processing September 1 - November 18, 2025")
    print("=" * 80)
    
    current_date = start_date
    daily_repeat_repairs = {}  # Track repeat repairs per day
    
    while current_date <= end_date:
        # Skip weekends
        if is_weekend(current_date):
            print(f"⊘ Skipping {current_date.strftime('%A, %Y-%m-%d')} (weekend)")
            current_date += timedelta(days=1)
            continue
        
        print(f"📅 Generating data for {current_date.strftime('%A, %Y-%m-%d')}")
        
        # Calculate records needed for this day (target: 500 total)
        # Approximately 60 working days, so ~8-9 records per day
        records_today = random.randint(7, 10)
        
        daily_repeat_repairs[current_date] = {
            'total_vehicles': records_today,
            'repeat_count': random.randint(0, max(1, records_today // 3))
        }
        
        # Generate records for this day
        for job_idx in range(records_today):
            record_count += 1
            
            ro_number = f"RO{current_date.strftime('%Y%m%d')}{job_idx+1:03d}"
            sr_number = f"SR{current_date.strftime('%Y%m%d')}{job_idx+1:03d}"
            chassis = f"XXXXX{current_date.day:02d}{job_idx:05d}"
            reg_no = f"KHI-{random.randint(1000, 9999)}"
            
            technician = random.choice(technicians)
            service_adviser = random.choice(service_advisers)
            
            # MSI distribution: rotate through all 5 categories
            msi = msi_values[job_idx % len(msi_values)]
            
            variant = random.choice(variants)
            
            # Timing scenarios - realistic service times
            creation_hour = random.randint(8, 16)
            creation_minute = random.randint(0, 59)
            creation_time = f"{creation_hour:02d}:{creation_minute:02d}:00"
            
            start_delay = random.randint(0, 120)  # 0-2 hours delay before start
            start_hour = (creation_hour + start_delay // 60) % 24
            start_minute = (creation_minute + start_delay % 60) % 60
            start_time = f"{start_hour:02d}:{start_minute:02d}:00"
            
            # Lead time varies by MSI type
            if msi == "LIGHT":
                lead_hours = random.uniform(0.5, 1.5)
            elif msi == "OIL FILTER":
                lead_hours = random.uniform(0.5, 1)
            elif msi == "GR":
                lead_hours = random.uniform(0.5, 1.5)
            elif msi == "CARE":
                lead_hours = random.uniform(0.5, 1)
            elif msi == "SUPER LIGH":
                lead_hours = random.uniform(1, 2)
            elif msi == "MEDIUM":
                lead_hours = random.uniform(2, 4)
            else:  # HEAVY
                lead_hours = random.uniform(4, 8)
            
            lead_hours_int = int(lead_hours)
            lead_minutes = int((lead_hours - lead_hours_int) * 60)
            lead_time_str = f"{lead_hours_int}:{lead_minutes:02d}:00"
            
            end_hour = (start_hour + lead_hours_int) % 24
            end_minute = (start_minute + lead_minutes) % 60
            end_time = f"{end_hour:02d}:{end_minute:02d}:00"
            
            # Status distribution: 35% On-time, 30% Grace, 35% Late
            delay_chance = random.random()
            if delay_chance < 0.35:  # 35% on time
                overall_hours = lead_hours_int + (lead_minutes / 60)
                status = "On-time"
            elif delay_chance < 0.65:  # 30% grace time (0-2 hour delay)
                overall_hours = lead_hours_int + (lead_minutes + random.randint(0, 120)) / 60
                status = "Grace"
            else:  # 35% late (2+ hour delay)
                overall_hours = lead_hours_int + (lead_minutes + random.randint(120, 480)) / 60
                status = "Late"
            
            overall_hours_int = int(overall_hours)
            overall_minutes = int((overall_hours - overall_hours_int) * 60)
            overall_lead_time = f"{overall_hours_int}:{overall_minutes:02d}:00"
            
            gatepass_hour = (end_hour + random.randint(0, 2)) % 24
            gatepass_minute = random.randint(0, 59)
            gatepass_time = f"{gatepass_hour:02d}:{gatepass_minute:02d}:00"
            
            # Customer data
            customer_name = f"Customer_{record_count:03d}"
            customer_mobile = f"03{random.randint(100000000, 999999999)}"
            
            # Financial data
            labour_sales = round(random.uniform(500, 3000), 2)
            parts_sales = round(random.uniform(1000, 8000), 2)
            sublet_sales = round(random.uniform(0, 2000), 2) if random.random() > 0.7 else 0
            
            # Daily CPUs Report
            daily_cpus = {
                'service_date': current_date,
                'chassis_number': chassis,
                'ro_no': ro_number,
                'service_nature': random.choice(service_natures),
                'campaign_type': random.choice(campaign_types),
                'customer_source': random.choice(customer_sources),
                'customer_name': customer_name,
                'customer_cnic': f"{random.randint(10000, 99999)}-{random.randint(1000000, 9999999)}-{random.randint(1, 9)}",
                'customer_ntn': f"{random.randint(100000, 999999)}-{random.randint(1, 9)}",
                'customer_dob': (current_date - timedelta(days=random.randint(365*20, 365*70))),
                'customer_mobile_no': customer_mobile,
                'customer_landline_number': f"021{random.randint(10000000, 99999999)}",
                'customer_mobile_no2': f"03{random.randint(100000000, 999999999)}" if random.random() > 0.6 else None,
                'customer_email': f"cust_{record_count:03d}@example.com",
                'customer_type': random.choice(customer_types),
                'house_no': f"House {random.randint(1, 500)}",
                'street_no': f"Street {random.randint(1, 50)}",
                'city_of_residence': random.choice(["Karachi", "Lahore", "Islamabad", "Faisalabad"]),
                'postal_code': f"{random.randint(10000, 99999)}",
                'insurance_status': random.choice(insurance_statuses),
                'insurance_company': "Allianz" if random.random() > 0.5 else "EFU",
                'insurance_expiry_date': (current_date + timedelta(days=random.randint(30, 365))),
                'labour_sales': labour_sales,
                'parts_sales': parts_sales,
                'sublet_sales': sublet_sales,
                'odometer_reading': random.randint(5000, 150000),
                'vehicle_type': random.choice(vehicle_types),
                'model_year': random.randint(2015, 2024),
                'reg_no': reg_no,
                'service_sub_category': msi,
                'vehicle_make': "Toyota",
                'receiving_date_time': datetime.combine(current_date, datetime.strptime(creation_time, "%H:%M:%S").time()),
                'delivery_date_time': datetime.combine(current_date, datetime.strptime(end_time, "%H:%M:%S").time()),
                'promised_date_time': datetime.combine(current_date + timedelta(days=1), datetime.strptime(creation_time, "%H:%M:%S").time()),
                'prefered_date_time_for_psfu': datetime.combine(current_date + timedelta(days=random.randint(1, 7)), datetime.strptime(creation_time, "%H:%M:%S").time()),
                'voc': f"[{msi}] {random.choice(['Noise issue', 'Performance concern', 'Fluid leak', 'Belt wear', 'Bearing issue'])}",
                'sa_ta_instructions': f"[{msi}] {msi_operations[msi]}",
                'job_performed_by_technicians': msi_operations[msi],
                'controller_remarks': f"[{status}] Service completed",
                'service_avisor_name': service_adviser,
                'technical_advisor_name': f"Tech_Advisor_{random.randint(1, 5)}",
                'job_controller_name': f"Controller_{random.randint(1, 3)}",
                'technician_name': technician,
                'vehicle_variant': variant,
                'imc_vehic': "Yes" if random.random() > 0.3 else "No",
                'status': status,
            }
            daily_cpus_data.append(daily_cpus)
            
            # Technician Report - CRITICAL: Same RO number to link tables
            tech_report = {
                'sr': sr_number,
                'ro_no': ro_number,  # SAME RO NUMBER - enables joining
                'mileage': random.randint(5000, 150000),
                'msi': msi,
                'no_of_jobs': random.randint(1, 3),
                'reg_no': reg_no,
                'variant': variant,
                'customer_name': customer_name,
                'service_adviser': service_adviser,
                'technician_name': technician,
                'bay': random.choice(bays),
                'operations': msi_operations[msi],
                'creation_time': creation_time,
                'p_start_time': start_time,
                'p_end_time': end_time,
                'p_lead_time': lead_time_str,
                'gatepass_time': gatepass_time,
                'overall_lead_time': overall_lead_time,
                'remarks': f"[{msi}] {status} - {msi_operations[msi]}",
            }
            technician_reports_data.append(tech_report)
        
        current_date += timedelta(days=1)
    
    # Create repeat repairs records from daily aggregates
    for rep_date, rep_data in daily_repeat_repairs.items():
        repeat_repair = {
            'date': rep_date,
            'total_vehicle_delivered': rep_data['total_vehicles'],
            'repeat_repair_count': rep_data['repeat_count'],
            'repeat_repair_percentage': round((rep_data['repeat_count'] / rep_data['total_vehicles'] * 100) if rep_data['total_vehicles'] > 0 else 0, 2)
        }
        repeat_repairs_data.append(repeat_repair)
    
    return daily_cpus_data, technician_reports_data, repeat_repairs_data

def insert_data(daily_data, tech_data, repeat_data):
    """Insert all data into database"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Insert daily CPUs
        daily_insert = """
            INSERT INTO daily_cpus_reports (
                service_date, chassis_number, ro_no, service_nature, campaign_type,
                customer_source, customer_name, customer_cnic, customer_ntn, customer_dob,
                customer_mobile_no, customer_landline_number, customer_mobile_no2, customer_email,
                customer_type, house_no, street_no, city_of_residence, postal_code,
                insurance_status, insurance_company, insurance_expiry_date, labour_sales,
                parts_sales, sublet_sales, odometer_reading, vehicle_type, model_year,
                reg_no, service_sub_category, vehicle_make, receiving_date_time,
                delivery_date_time, promised_date_time, prefered_date_time_for_psfu,
                voc, sa_ta_instructions, job_performed_by_technicians, controller_remarks,
                service_avisor_name, technical_advisor_name, job_controller_name,
                technician_name, vehicle_variant, imc_vehic, status
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s
            )
        """
        
        for record in daily_data:
            values = (
                record['service_date'], record['chassis_number'], record['ro_no'],
                record['service_nature'], record['campaign_type'],
                record['customer_source'], record['customer_name'], record['customer_cnic'],
                record['customer_ntn'], record['customer_dob'], record['customer_mobile_no'],
                record['customer_landline_number'], record['customer_mobile_no2'],
                record['customer_email'], record['customer_type'], record['house_no'],
                record['street_no'], record['city_of_residence'], record['postal_code'],
                record['insurance_status'], record['insurance_company'],
                record['insurance_expiry_date'], record['labour_sales'], record['parts_sales'],
                record['sublet_sales'], record['odometer_reading'], record['vehicle_type'],
                record['model_year'], record['reg_no'], record['service_sub_category'],
                record['vehicle_make'], record['receiving_date_time'],
                record['delivery_date_time'], record['promised_date_time'],
                record['prefered_date_time_for_psfu'], record['voc'],
                record['sa_ta_instructions'], record['job_performed_by_technicians'],
                record['controller_remarks'], record['service_avisor_name'],
                record['technical_advisor_name'], record['job_controller_name'],
                record['technician_name'], record['vehicle_variant'], record['imc_vehic'],
                record['status']
            )
            cursor.execute(daily_insert, values)
        
        # Insert technician reports
        tech_insert = """
            INSERT INTO technician_reports (
                sr, ro_no, mileage, msi, no_of_jobs, reg_no, variant,
                customer_name, service_adviser, technician_name, bay,
                operations, creation_time, p_start_time, p_end_time, p_lead_time,
                gatepass_time, overall_lead_time, remarks
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """
        
        for record in tech_data:
            values = (
                record['sr'], record['ro_no'], record['mileage'], record['msi'],
                record['no_of_jobs'], record['reg_no'], record['variant'],
                record['customer_name'], record['service_adviser'], record['technician_name'],
                record['bay'], record['operations'], record['creation_time'],
                record['p_start_time'], record['p_end_time'], record['p_lead_time'],
                record['gatepass_time'], record['overall_lead_time'], record['remarks']
            )
            cursor.execute(tech_insert, values)
        
        # Insert repeat repairs
        repeat_insert = """
            INSERT INTO repeat_repairs (date, total_vehicle_delivered, repeat_repair_count, repeat_repair_percentage)
            VALUES (%s, %s, %s, %s)
        """
        
        for record in repeat_data:
            cursor.execute(repeat_insert, (
                record['date'],
                record['total_vehicle_delivered'],
                record['repeat_repair_count'],
                record['repeat_repair_percentage']
            ))
        
        conn.commit()
        print(f"\n✅ Inserted {len(daily_data)} daily CPUs reports")
        print(f"✅ Inserted {len(tech_data)} technician reports")
        print(f"✅ Inserted {len(repeat_data)} repeat repair records")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error inserting data: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()

def main():
    print("=" * 80)
    print("Toyota 500-Row Test Data Generator (Sept 1 - Nov 18, 2025)")
    print("=" * 80)
    print("\n📋 Configuration:")
    print("   • Date Range: September 1 - November 18, 2025")
    print("   • Target Records: ~500")
    print("   • Working Days Only: Excluding weekends")
    print("   • MSI Categories: GR, CARE, SUPER LIGH, MEDIUM, HEAVY")
    print("   • Status Distribution: 35% On-time, 30% Grace, 35% Late")
    print("   • Critical: Same RO numbers in both tables for proper joining")
    
    print("\n🔄 Resetting database...")
    clear_database()
    
    print("\n📝 Generating 500 rows of accurate data...")
    daily_data, tech_data, repeat_data = generate_500_rows_data()
    
    print(f"\n📊 Generated data:")
    print(f"   • Daily CPUs reports: {len(daily_data)} records")
    print(f"   • Technician reports: {len(tech_data)} records")
    print(f"   • Repeat repairs: {len(repeat_data)} records")
    
    # Analyze MSI distribution
    msi_counts = {}
    for r in tech_data:
        msi = r['msi']
        msi_counts[msi] = msi_counts.get(msi, 0) + 1
    
    print(f"\n🔧 MSI Category distribution:")
    for msi in ["GR", "CARE","LIGHT","OIL FILTER", "SUPER LIGH", "MEDIUM", "HEAVY"]:
        count = msi_counts.get(msi, 0)
        if count > 0:
            pct = (count / len(tech_data) * 100)
            print(f"   • {msi}: {count} ({pct:.1f}%)")
    
    # Analyze status distribution
    status_counts = {}
    for r in daily_data:
        status = r['status']
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print(f"\n⏱️  Status distribution:")
    for status in ["On-time", "Grace", "Late"]:
        count = status_counts.get(status, 0)
        if count > 0:
            pct = (count / len(daily_data) * 100)
            print(f"   • {status}: {count} ({pct:.1f}%)")
    
    # Analyze technician distribution
    tech_counts = {}
    for r in tech_data:
        tech = r['technician_name']
        tech_counts[tech] = tech_counts.get(tech, 0) + 1
    
    print(f"\n👨‍🔧 Technician job distribution:")
    for tech in sorted(tech_counts.keys()):
        count = tech_counts[tech]
        print(f"   • {tech}: {count} jobs")
    
    # Verify RO number matching
    daily_ros = set(r['ro_no'] for r in daily_data)
    tech_ros = set(r['ro_no'] for r in tech_data)
    matching_ros = daily_ros & tech_ros
    
    print(f"\n🔗 RO Number Matching:")
    print(f"   • Daily CPUs RO numbers: {len(daily_ros)}")
    print(f"   • Technician RO numbers: {len(tech_ros)}")
    print(f"   • Matching RO numbers: {len(matching_ros)} ✅")
    print(f"   • Join Ready: {'YES' if len(matching_ros) == len(tech_ros) else 'NO'}")
    
    print("\n💾 Inserting data into database...")
    insert_data(daily_data, tech_data, repeat_data)
    
    print("\n✅ SUCCESS: 500-row dataset ready for testing!")
    print("=" * 80)

if __name__ == "__main__":
    main()
