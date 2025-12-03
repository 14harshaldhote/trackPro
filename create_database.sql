-- MySQL Database Setup for Tracker Pro
-- Run this in MySQL command line or MySQL Workbench

-- Create database
CREATE DATABASE IF NOT EXISTS tracker 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

-- Verify database created
SHOW DATABASES LIKE 'tracker';

-- Use the database
USE tracker;

-- Grant privileges (if needed)
-- GRANT ALL PRIVILEGES ON tracker.* TO 'root'@'localhost';
-- FLUSH PRIVILEGES;
