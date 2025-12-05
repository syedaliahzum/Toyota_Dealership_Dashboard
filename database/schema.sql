-- database/schema.sql
-- DDL for Toyota service data
-- Idempotent CREATE TABLE statements for repair_orders, technicians, jobs, repeat_repairs

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS=0;
-- database/schema.sql
-- Denormalized DDL for Toyota service data

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS=0;

-- Technician reports table (denormalized; mirrors Technician CSV)
CREATE TABLE IF NOT EXISTS `technician_reports` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `sr` VARCHAR(64) DEFAULT NULL,
  `ro_no` VARCHAR(64) DEFAULT NULL,
  `mileage` INT DEFAULT NULL,
  `msi` VARCHAR(128) DEFAULT NULL,
  `no_of_jobs` INT DEFAULT NULL,
  `reg_no` VARCHAR(64) DEFAULT NULL,
  `variant` VARCHAR(255) DEFAULT NULL,
  `customer_name` VARCHAR(255) DEFAULT NULL,
  `service_adviser` VARCHAR(128) DEFAULT NULL,
  `technician_name` VARCHAR(255) DEFAULT NULL,
  `bay` VARCHAR(64) DEFAULT NULL,
  `operations` TEXT DEFAULT NULL,
  `creation_time` TIME DEFAULT NULL,
  `p_start_time` TIME DEFAULT NULL,
  `p_end_time` TIME DEFAULT NULL,
  `p_lead_time` TIME DEFAULT NULL,
  `gatepass_time` TIME DEFAULT NULL,
  `overall_lead_time` TIME DEFAULT NULL,
  `remarks` TEXT DEFAULT NULL,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `idx_technician_reports_ro` (`ro_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Daily CPUs reports table (denormalized; mirrors Daily CPUs CSV)
CREATE TABLE IF NOT EXISTS `daily_cpus_reports` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `service_date` DATE DEFAULT NULL,
  `chassis_number` VARCHAR(128) DEFAULT NULL,
  `ro_no` VARCHAR(64) DEFAULT NULL,
  `service_nature` VARCHAR(128) DEFAULT NULL,
  `campaign_type` VARCHAR(64) DEFAULT NULL,
  `customer_source` VARCHAR(128) DEFAULT NULL,
  `customer_name` VARCHAR(255) DEFAULT NULL,
  `customer_cnic` VARCHAR(64) DEFAULT NULL,
  `customer_ntn` VARCHAR(64) DEFAULT NULL,
  `customer_dob` DATE DEFAULT NULL,
  `customer_mobile_no` VARCHAR(64) DEFAULT NULL,
  `customer_landline_number` VARCHAR(64) DEFAULT NULL,
  `customer_mobile_no2` VARCHAR(64) DEFAULT NULL,
  `customer_email` VARCHAR(255) DEFAULT NULL,
  `customer_type` VARCHAR(64) DEFAULT NULL,
  `house_no` VARCHAR(255) DEFAULT NULL,
  `street_no` VARCHAR(255) DEFAULT NULL,
  `city_of_residence` VARCHAR(128) DEFAULT NULL,
  `postal_code` VARCHAR(32) DEFAULT NULL,
  `insurance_status` VARCHAR(64) DEFAULT NULL,
  `insurance_company` VARCHAR(255) DEFAULT NULL,
  `insurance_expiry_date` DATE DEFAULT NULL,
  `labour_sales` DECIMAL(15,2) DEFAULT NULL,
  `parts_sales` DECIMAL(15,2) DEFAULT NULL,
  `sublet_sales` DECIMAL(15,2) DEFAULT NULL,
  `odometer_reading` INT DEFAULT NULL,
  `vehicle_type` VARCHAR(64) DEFAULT NULL,
  `model_year` INT DEFAULT NULL,
  `reg_no` VARCHAR(64) DEFAULT NULL,
  `service_sub_category` VARCHAR(128) DEFAULT NULL,
  `vehicle_make` VARCHAR(128) DEFAULT NULL,
  `receiving_date_time` DATETIME DEFAULT NULL,
  `delivery_date_time` DATETIME DEFAULT NULL,
  `promised_date_time` DATETIME DEFAULT NULL,
  `prefered_date_time_for_psfu` DATETIME DEFAULT NULL,
  `voc` TEXT DEFAULT NULL,
  `sa_ta_instructions` TEXT DEFAULT NULL,
  `job_performed_by_technicians` TEXT DEFAULT NULL,
  `controller_remarks` TEXT DEFAULT NULL,
  `service_avisor_name` VARCHAR(128) DEFAULT NULL,
  `technical_advisor_name` VARCHAR(128) DEFAULT NULL,
  `job_controller_name` VARCHAR(128) DEFAULT NULL,
  `technician_name` VARCHAR(255) DEFAULT NULL,
  `vehicle_variant` VARCHAR(255) DEFAULT NULL,
  `imc_vehic` VARCHAR(32) DEFAULT NULL,
  `status` VARCHAR(64) DEFAULT NULL,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `idx_daily_service_date` (`service_date`),
  INDEX `idx_daily_ro` (`ro_no`),
  INDEX `idx_daily_reg_no` (`reg_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Repeat repairs table (keeps same purpose but stored as provided)
CREATE TABLE IF NOT EXISTS `repeat_repairs` (
  `date` DATE NOT NULL,
  `total_vehicle_delivered` INT DEFAULT 0,
  `repeat_repair_count` INT DEFAULT 0,
  `repeat_repair_percentage` DECIMAL(6,2) DEFAULT 0.00,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Raw repeat repairs table: stores CSV rows verbatim (all columns as VARCHAR)
-- Note: repeat_repairs_raw and repeat_repairs_csv tables were removed. The pipeline now
-- populates only the typed `repeat_repairs` table directly from the Repeat Repair CSV.

SET FOREIGN_KEY_CHECKS=1;
