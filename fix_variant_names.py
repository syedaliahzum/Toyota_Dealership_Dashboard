"""
Toyota Variant Name Standardization Script

This script reads all unique variants from both daily_cpus_reports and technician_reports tables,
maps them to professional Toyota variant names, and updates the database accordingly.

It ensures consistency across both tables and uses proper brand/model/generation naming conventions.
"""

import mysql.connector
from mysql.connector import Error
import logging
from typing import Dict, Set, Tuple
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database connection details from .env
# When running locally against Docker, use localhost instead of mysql hostname
LOCAL_HOST = 'localhost' if os.getenv('DB_HOST') == 'mysql' else os.getenv('DB_HOST', 'localhost')
DB_CONFIG = {
    'host': LOCAL_HOST,
    'user': os.getenv('DB_USER', 'toyota_user'),
    'password': os.getenv('DB_PASSWORD', 'toyota_password'),
    'database': os.getenv('DB_NAME', 'toyota_db'),
    'port': int(os.getenv('DB_PORT', '3307')),
}

logger.info(f"Database config: host={DB_CONFIG['host']}, port={DB_CONFIG['port']}, database={DB_CONFIG['database']}")

# Professional Toyota variant mapping
# Maps current variant names (in database) to professional names
VARIANT_MAP = {
    # Engine displacement variants (Corolla)
    '1.3L': 'Toyota Corolla 1.3L',
    '2.0L': 'Toyota Corolla 2.0L',
    
    # Transmission variants
    'Automatic': 'Toyota Corolla Automatic',
    
    # Corolla variants
    'corolla': 'Toyota Corolla',
    'Corolla': 'Toyota Corolla',
    'COROLLA': 'Toyota Corolla',
    'gli': 'Toyota Corolla GLi',
    'GLi': 'Toyota Corolla GLi',
    'GLI': 'Toyota Corolla GLi',
    'gli plus': 'Toyota Corolla GLi Plus',
    'GLi Plus': 'Toyota Corolla GLi Plus',
    'xli': 'Toyota Corolla Xli',
    'Xli': 'Toyota Corolla Xli',
    'XLI': 'Toyota Corolla Xli',
    'altis': 'Toyota Corolla Altis',
    'Altis': 'Toyota Corolla Altis',
    'ALTIS': 'Toyota Corolla Altis',
    'corolla gli': 'Toyota Corolla GLi',
    'Corolla GLi': 'Toyota Corolla GLi',
    'corolla xli': 'Toyota Corolla Xli',
    'Corolla Xli': 'Toyota Corolla Xli',
    'corolla altis': 'Toyota Corolla Altis',
    'Corolla Altis': 'Toyota Corolla Altis',
    
    # Fortuner variants
    'fortuner': 'Toyota Fortuner',
    'Fortuner': 'Toyota Fortuner',
    'FORTUNER': 'Toyota Fortuner',
    
    # Hybrid variants (generic to specific)
    'hybrid': 'Toyota Hybrid',
    'Hybrid': 'Toyota Hybrid',
    'HYBRID': 'Toyota Hybrid',
    'corolla hybrid': 'Toyota Corolla Hybrid',
    'Corolla Hybrid': 'Toyota Corolla Hybrid',
    'fortuner hybrid': 'Toyota Fortuner Hybrid',
    'Fortuner Hybrid': 'Toyota Fortuner Hybrid',
    
    # Land Cruiser variants
    'land cruiser': 'Toyota Land Cruiser',
    'Land Cruiser': 'Toyota Land Cruiser',
    'LAND CRUISER': 'Toyota Land Cruiser',
    'landcruiser': 'Toyota Land Cruiser',
    
    # Prius variants
    'prius': 'Toyota Prius',
    'Prius': 'Toyota Prius',
    'PRIUS': 'Toyota Prius',
    
    # Yaris variants
    'yaris': 'Toyota Yaris',
    'Yaris': 'Toyota Yaris',
    'YARIS': 'Toyota Yaris',
    
    # Vitz variants
    'vitz': 'Toyota Vitz',
    'Vitz': 'Toyota Vitz',
    'VITZ': 'Toyota Vitz',
    
    # Innova variants
    'innova': 'Toyota Innova',
    'Innova': 'Toyota Innova',
    'INNOVA': 'Toyota Innova',
    'innova crystal': 'Toyota Innova Crysta',
    'Innova Crystal': 'Toyota Innova Crysta',
    'innova crysta': 'Toyota Innova Crysta',
    'Innova Crysta': 'Toyota Innova Crysta',
    
    # RAV4 variants
    'rav4': 'Toyota RAV4',
    'Rav4': 'Toyota RAV4',
    'RAV4': 'Toyota RAV4',
    
    # Avanza variants
    'avanza': 'Toyota Avanza',
    'Avanza': 'Toyota Avanza',
    'AVANZA': 'Toyota Avanza',
    
    # Hilux variants
    'hilux': 'Toyota Hilux',
    'Hilux': 'Toyota Hilux',
    'HILUX': 'Toyota Hilux',
}

def get_connection():
    """Create and return database connection."""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            logger.info("✓ Connected to MySQL database")
            return connection
    except Error as e:
        logger.error(f"✗ Error connecting to database: {e}")
        return None

def get_unique_variants(connection) -> Tuple[Set[str], Set[str]]:
    """Get all unique variants from both tables."""
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Get unique variants from daily_cpus_reports
        logger.info("\n📋 Fetching unique variants from daily_cpus_reports...")
        cursor.execute("SELECT DISTINCT vehicle_variant FROM daily_cpus_reports WHERE vehicle_variant IS NOT NULL ORDER BY vehicle_variant")
        daily_variants = {row['vehicle_variant'] for row in cursor.fetchall()}
        logger.info(f"   Found {len(daily_variants)} unique variants in daily_cpus_reports")
        for variant in sorted(daily_variants):
            logger.info(f"   • {variant}")
        
        # Get unique variants from technician_reports
        logger.info("\n📋 Fetching unique variants from technician_reports...")
        cursor.execute("SELECT DISTINCT variant FROM technician_reports WHERE variant IS NOT NULL ORDER BY variant")
        tech_variants = {row['variant'] for row in cursor.fetchall()}
        logger.info(f"   Found {len(tech_variants)} unique variants in technician_reports")
        for variant in sorted(tech_variants):
            logger.info(f"   • {variant}")
        
        cursor.close()
        return daily_variants, tech_variants
        
    except Error as e:
        logger.error(f"✗ Error fetching variants: {e}")
        return set(), set()

def create_variant_mapping(all_variants: Set[str]) -> Dict[str, str]:
    """Create mapping for all variants found in database."""
    mapping = {}
    
    for variant in all_variants:
        if variant in VARIANT_MAP:
            mapping[variant] = VARIANT_MAP[variant]
        else:
            # For unmapped variants, try fuzzy matching
            lower_variant = variant.lower().strip()
            
            # Try exact match in lowercase
            for key, value in VARIANT_MAP.items():
                if key.lower() == lower_variant:
                    mapping[variant] = value
                    break
            
            # If still not found, try to find the best match
            if variant not in mapping:
                # Default: use original variant (will be logged as unmapped)
                mapping[variant] = variant
    
    return mapping

def update_variants(connection, mapping: Dict[str, str]) -> int:
    """Update variants in both tables."""
    try:
        cursor = connection.cursor()
        updated_count = 0
        
        logger.info("\n🔄 Updating variants in database...\n")
        
        # Update daily_cpus_reports
        logger.info("Updating daily_cpus_reports table:")
        for old_variant, new_variant in sorted(mapping.items()):
            if old_variant != new_variant:
                update_query = "UPDATE daily_cpus_reports SET vehicle_variant = %s WHERE vehicle_variant = %s"
                cursor.execute(update_query, (new_variant, old_variant))
                count = cursor.rowcount
                if count > 0:
                    logger.info(f"   ✓ '{old_variant}' → '{new_variant}' ({count} records)")
                    updated_count += count
        
        # Update technician_reports
        logger.info("\nUpdating technician_reports table:")
        for old_variant, new_variant in sorted(mapping.items()):
            if old_variant != new_variant:
                update_query = "UPDATE technician_reports SET variant = %s WHERE variant = %s"
                cursor.execute(update_query, (new_variant, old_variant))
                count = cursor.rowcount
                if count > 0:
                    logger.info(f"   ✓ '{old_variant}' → '{new_variant}' ({count} records)")
                    updated_count += count
        
        connection.commit()
        logger.info(f"\n✅ Total records updated: {updated_count}")
        cursor.close()
        return updated_count
        
    except Error as e:
        logger.error(f"✗ Error updating variants: {e}")
        connection.rollback()
        return 0

def verify_updates(connection):
    """Verify that variants were updated successfully."""
    try:
        cursor = connection.cursor(dictionary=True)
        
        logger.info("\n📊 Verification - Unique variants after update:\n")
        
        # Verify daily_cpus_reports
        logger.info("daily_cpus_reports variants:")
        cursor.execute("SELECT DISTINCT vehicle_variant FROM daily_cpus_reports WHERE vehicle_variant IS NOT NULL ORDER BY vehicle_variant")
        variants = [row['vehicle_variant'] for row in cursor.fetchall()]
        for variant in variants:
            logger.info(f"   • {variant}")
        
        # Verify technician_reports
        logger.info("\ntechnician_reports variants:")
        cursor.execute("SELECT DISTINCT variant FROM technician_reports WHERE variant IS NOT NULL ORDER BY variant")
        variants = [row['variant'] for row in cursor.fetchall()]
        for variant in variants:
            logger.info(f"   • {variant}")
        
        cursor.close()
        
    except Error as e:
        logger.error(f"✗ Error verifying updates: {e}")

def main():
    logger.info("="*80)
    logger.info("Toyota Variant Name Standardization Script")
    logger.info("="*80)
    
    # Connect to database
    connection = get_connection()
    if not connection:
        logger.error("✗ Failed to connect to database")
        return
    
    # Get unique variants from both tables
    daily_variants, tech_variants = get_unique_variants(connection)
    
    # Combine all variants
    all_variants = daily_variants.union(tech_variants)
    logger.info(f"\n📊 Total unique variants across both tables: {len(all_variants)}")
    
    # Create mapping
    mapping = create_variant_mapping(all_variants)
    
    # Show mapping summary
    logger.info("\n📝 Variant Mapping Summary:")
    changes_needed = 0
    for old_variant in sorted(mapping.keys()):
        new_variant = mapping[old_variant]
        if old_variant != new_variant:
            logger.info(f"   '{old_variant}' → '{new_variant}'")
            changes_needed += 1
    
    if changes_needed == 0:
        logger.info("   (No changes needed - all variants are already standard)")
    
    # Update variants
    if changes_needed > 0:
        logger.info(f"\n🔄 Will update {changes_needed} variant names...")
        updated = update_variants(connection, mapping)
        if updated > 0:
            logger.info(f"\n✅ Successfully updated {updated} records")
    else:
        logger.info("\n✓ All variants are already standardized")
    
    # Verify
    verify_updates(connection)
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("✅ Variant standardization complete!")
    logger.info("="*80)
    
    connection.close()

if __name__ == "__main__":
    main()
