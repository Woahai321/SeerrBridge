-- Complete Database Initialization Script
-- This script ensures all tables and schema are created on first launch
-- It combines all necessary SQL files into one comprehensive initialization

-- Create database if it doesn't exist
CREATE DATABASE IF NOT EXISTS seerrbridge CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Use the database
USE seerrbridge;

-- ==============================================
-- CORE TABLES (from 01-init.sql)
-- ==============================================

-- Create log_entries table
CREATE TABLE IF NOT EXISTS log_entries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    level VARCHAR(20) NOT NULL,
    module VARCHAR(100),
    `function` VARCHAR(100),
    line_number INT,
    title VARCHAR(500) NOT NULL,
    message TEXT NOT NULL,
    details JSON,
    source VARCHAR(100),
    processed BOOLEAN DEFAULT FALSE,
    notification_sent BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_level_timestamp (level, timestamp),
    INDEX idx_processed_timestamp (processed, timestamp),
    INDEX idx_notification_timestamp (notification_sent, timestamp),
    INDEX idx_timestamp (timestamp)
);

-- Create log_types table
CREATE TABLE IF NOT EXISTS log_types (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    pattern TEXT NOT NULL,
    description TEXT,
    level VARCHAR(20) NOT NULL,
    selected_words JSON,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Create log_displays table
CREATE TABLE IF NOT EXISTS log_displays (
    id VARCHAR(50) PRIMARY KEY,
    log_type_id VARCHAR(50) NOT NULL,
    location JSON NOT NULL,
    show_notification BOOLEAN DEFAULT FALSE,
    show_in_card BOOLEAN DEFAULT TRUE,
    trigger_stat_update BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (log_type_id) REFERENCES log_types(id) ON DELETE CASCADE
);

-- Create notification_history table
CREATE TABLE IF NOT EXISTS notification_history (
    id VARCHAR(50) PRIMARY KEY,
    type VARCHAR(20) NOT NULL,
    title VARCHAR(500) NOT NULL,
    message TEXT NOT NULL,
    details JSON,
    successful BOOLEAN DEFAULT FALSE,
    viewed BOOLEAN DEFAULT FALSE,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_type_timestamp (type, timestamp),
    INDEX idx_viewed_timestamp (viewed, timestamp),
    INDEX idx_successful_timestamp (successful, timestamp)
);

-- Create notification_settings table
CREATE TABLE IF NOT EXISTS notification_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    discord_webhook_url TEXT,
    notify_on_success BOOLEAN DEFAULT TRUE,
    notify_on_error BOOLEAN DEFAULT TRUE,
    notify_on_warning BOOLEAN DEFAULT TRUE,
    show_debug_widget BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Create media_requests table
CREATE TABLE IF NOT EXISTS media_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    overseerr_request_id INT NOT NULL,
    overseerr_media_id INT NOT NULL,
    tmdb_id INT NOT NULL,
    imdb_id VARCHAR(20),
    trakt_id VARCHAR(20),
    media_type VARCHAR(10) NOT NULL,
    title VARCHAR(500) NOT NULL,
    year INT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    requested_by VARCHAR(200),
    requested_at DATETIME,
    processed_at DATETIME,
    completed_at DATETIME,
    error_message TEXT,
    extra_data JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_overseerr_request_id (overseerr_request_id),
    INDEX idx_overseerr_media_id (overseerr_media_id),
    INDEX idx_tmdb_id (tmdb_id),
    INDEX idx_imdb_id (imdb_id),
    INDEX idx_trakt_id (trakt_id),
    INDEX idx_status_created (status, created_at),
    INDEX idx_media_type_status (media_type, status),
    INDEX idx_processed_at (processed_at)
);

-- show_subscriptions table removed - now using unified_media table

-- Create library_stats table
CREATE TABLE IF NOT EXISTS library_stats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    torrents_count INT NOT NULL DEFAULT 0,
    total_size_tb FLOAT NOT NULL DEFAULT 0.0,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create token_status table
CREATE TABLE IF NOT EXISTS token_status (
    id INT AUTO_INCREMENT PRIMARY KEY,
    token_type VARCHAR(50) NOT NULL,
    token_value TEXT NOT NULL,
    expires_at DATETIME,
    last_refreshed DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_token_type (token_type),
    INDEX idx_expires_at (expires_at),
    INDEX idx_is_active (is_active)
);

-- Create queue_status table
CREATE TABLE IF NOT EXISTS queue_status (
    id INT AUTO_INCREMENT PRIMARY KEY,
    queue_type VARCHAR(20) NOT NULL,
    queue_size INT NOT NULL DEFAULT 0,
    max_size INT NOT NULL DEFAULT 250,
    is_processing BOOLEAN DEFAULT FALSE,
    last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_queue_type (queue_type),
    INDEX idx_queue_type (queue_type),
    INDEX idx_is_processing (is_processing)
);

-- Create system_config table
CREATE TABLE IF NOT EXISTS system_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value LONGTEXT,
    config_type VARCHAR(20) NOT NULL DEFAULT 'string',
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_config_key (config_key),
    INDEX idx_is_active (is_active)
);

-- Create service_status table for real-time status updates
CREATE TABLE IF NOT EXISTS service_status (
    id INT AUTO_INCREMENT PRIMARY KEY,
    service_name VARCHAR(50) NOT NULL UNIQUE,
    status VARCHAR(20) NOT NULL DEFAULT 'unknown',
    version VARCHAR(50),
    uptime_seconds INT DEFAULT 0,
    uptime_string VARCHAR(100),
    start_time DATETIME,
    current_time_value DATETIME,
    queue_status JSON,
    browser_status VARCHAR(50),
    automatic_processing BOOLEAN DEFAULT FALSE,
    show_subscription BOOLEAN DEFAULT FALSE,
    refresh_interval_minutes FLOAT DEFAULT 30.0,
    library_stats JSON,
    queue_activity JSON,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_service_name (service_name),
    INDEX idx_status (status),
    INDEX idx_last_updated (last_updated)
);

-- ==============================================
-- UNIFIED MEDIA TABLE (from unified_media_schema.sql)
-- ==============================================

CREATE TABLE unified_media (
    -- Primary identification
    id INT AUTO_INCREMENT PRIMARY KEY,
    
    -- External service IDs (all optional, indexed for lookups)
    tmdb_id INT NULL,
    imdb_id VARCHAR(20) NULL,
    trakt_id VARCHAR(20) NULL,
    overseerr_media_id INT NULL,
    overseerr_request_id INT NULL,
    
    -- Media identification
    media_type ENUM('movie', 'tv') NOT NULL,
    title VARCHAR(500) NOT NULL,
    year INT NULL,
    overview TEXT NULL,
    
    -- TV Show specific fields
    season_number INT NULL,  -- For TV shows: specific season being tracked
    episode_count INT NULL DEFAULT 0,
    aired_episodes INT NULL DEFAULT 0,
    confirmed_episodes JSON NULL,  -- Array of confirmed episode IDs
    failed_episodes JSON NULL,     -- Array of failed episode IDs
    unprocessed_episodes JSON NULL, -- Array of unprocessed episode IDs
    seasons_processed JSON NULL,   -- Array of processed season numbers
    
    -- Request tracking
    requested_by VARCHAR(200) NULL,
    requested_at DATETIME NULL,
    first_requested_at DATETIME NULL,  -- First time this media was requested
    last_requested_at DATETIME NULL,   -- Most recent request
    request_count INT DEFAULT 1,       -- Total number of requests
    
    -- Processing status (unified)
    status ENUM('pending', 'processing', 'completed', 'failed', 'skipped', 'cancelled', 'ignored', 'unreleased') NOT NULL DEFAULT 'pending',
    processing_stage VARCHAR(50) NULL,  -- browser_automation, search_complete, etc.
    processing_started_at DATETIME NULL,
    processing_completed_at DATETIME NULL,
    last_checked_at DATETIME NULL,
    
    -- Release date tracking (for movies and TV shows)
    released_date DATETIME NULL,  -- Release date from Trakt API
    
    -- Subscription tracking (for TV shows)
    is_subscribed BOOLEAN DEFAULT FALSE,
    subscription_active BOOLEAN DEFAULT TRUE,
    subscription_last_checked DATETIME NULL,
    
    -- Search and torrent data
    torrents_found INT DEFAULT 0,
    search_attempts INT DEFAULT 0,
    last_search_at DATETIME NULL,
    
    -- Error tracking
    error_message TEXT NULL,
    error_count INT DEFAULT 0,
    last_error_at DATETIME NULL,
    
    -- Media metadata
    genres JSON NULL,           -- Array of genre names
    runtime INT NULL,           -- Runtime in minutes
    rating DECIMAL(3,1) NULL,   -- Average rating
    vote_count INT NULL,        -- Number of votes
    popularity DECIMAL(10,2) NULL, -- Popularity score
    
    -- Image data
    poster_url VARCHAR(500) NULL,
    thumb_url VARCHAR(500) NULL,
    fanart_url VARCHAR(500) NULL,
    backdrop_url VARCHAR(500) NULL,
    
    -- Compressed image storage
    poster_image LONGBLOB NULL,
    poster_image_format VARCHAR(10) NULL,
    poster_image_size INT NULL,
    thumb_image LONGBLOB NULL,
    thumb_image_format VARCHAR(10) NULL,
    thumb_image_size INT NULL,
    fanart_image LONGBLOB NULL,
    fanart_image_format VARCHAR(10) NULL,
    fanart_image_size INT NULL,
    backdrop_image LONGBLOB NULL,
    backdrop_image_format VARCHAR(10) NULL,
    backdrop_image_size INT NULL,
    
    -- Additional data
    extra_data JSON NULL,       -- Flexible field for any additional data
    tags JSON NULL,            -- User-defined tags
    notes TEXT NULL,           -- User notes
    
    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Indexes for performance
    INDEX idx_tmdb_id (tmdb_id),
    INDEX idx_imdb_id (imdb_id),
    INDEX idx_trakt_id (trakt_id),
    INDEX idx_overseerr_media_id (overseerr_media_id),
    INDEX idx_overseerr_request_id (overseerr_request_id),
    INDEX idx_media_type (media_type),
    INDEX idx_status (status),
    INDEX idx_processing_stage (processing_stage),
    INDEX idx_is_subscribed (is_subscribed),
    INDEX idx_subscription_active (subscription_active),
    INDEX idx_created_at (created_at),
    INDEX idx_updated_at (updated_at),
    INDEX idx_requested_at (requested_at),
    INDEX idx_processing_started_at (processing_started_at),
    INDEX idx_processing_completed_at (processing_completed_at),
    INDEX idx_released_date (released_date),
    
    -- Composite indexes for common queries
    INDEX idx_media_type_status (media_type, status),
    INDEX idx_tmdb_media_type (tmdb_id, media_type),
    INDEX idx_status_created (status, created_at),
    INDEX idx_subscription_active_checked (subscription_active, subscription_last_checked),
    INDEX idx_processing_stage_status (processing_stage, status),
    
    -- Unique constraints to prevent duplicates
    UNIQUE KEY unique_tmdb_media_type (tmdb_id, media_type),
    UNIQUE KEY unique_imdb_media_type (imdb_id, media_type),
    UNIQUE KEY unique_trakt_media_type (trakt_id, media_type)
);

-- ==============================================
-- ENHANCED TV SEASONS SUPPORT
-- ==============================================

-- Add enhanced season tracking columns to unified_media (using stored procedures for IF NOT EXISTS)
DELIMITER $$

CREATE PROCEDURE AddColumnIfNotExists()
BEGIN
    -- Add total_seasons column
    IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS 
                   WHERE TABLE_NAME = 'unified_media' 
                   AND COLUMN_NAME = 'total_seasons' 
                   AND TABLE_SCHEMA = DATABASE()) THEN
        ALTER TABLE unified_media ADD COLUMN total_seasons INT NULL DEFAULT 0 COMMENT 'Total number of seasons for this TV show';
    END IF;
    
    -- Add seasons_data column
    IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS 
                   WHERE TABLE_NAME = 'unified_media' 
                   AND COLUMN_NAME = 'seasons_data' 
                   AND TABLE_SCHEMA = DATABASE()) THEN
        ALTER TABLE unified_media ADD COLUMN seasons_data JSON NULL COMMENT 'Detailed season information: [{"season_number": 1, "episode_count": 10, "aired_episodes": 8, "confirmed_episodes": [], "failed_episodes": [], "unprocessed_episodes": []}]';
    END IF;
    
    -- Add seasons_processing column
    IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS 
                   WHERE TABLE_NAME = 'unified_media' 
                   AND COLUMN_NAME = 'seasons_processing' 
                   AND TABLE_SCHEMA = DATABASE()) THEN
        ALTER TABLE unified_media ADD COLUMN seasons_processing VARCHAR(500) NULL COMMENT 'String representation of seasons being processed (e.g., "1,2,3" or "1-5")';
    END IF;
    
    -- Add seasons_discrepant column
    IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS 
                   WHERE TABLE_NAME = 'unified_media' 
                   AND COLUMN_NAME = 'seasons_discrepant' 
                   AND TABLE_SCHEMA = DATABASE()) THEN
        ALTER TABLE unified_media ADD COLUMN seasons_discrepant JSON NULL COMMENT 'Array of season numbers that have discrepancies';
    END IF;
    
    -- Add seasons_completed column
    IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS 
                   WHERE TABLE_NAME = 'unified_media' 
                   AND COLUMN_NAME = 'seasons_completed' 
                   AND TABLE_SCHEMA = DATABASE()) THEN
        ALTER TABLE unified_media ADD COLUMN seasons_completed JSON NULL COMMENT 'Array of season numbers that are fully completed';
    END IF;
    
    -- Add seasons_failed column
    IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS 
                   WHERE TABLE_NAME = 'unified_media' 
                   AND COLUMN_NAME = 'seasons_failed' 
                   AND TABLE_SCHEMA = DATABASE()) THEN
        ALTER TABLE unified_media ADD COLUMN seasons_failed JSON NULL COMMENT 'Array of season numbers that have failed processing';
    END IF;
    
    -- Add queue tracking columns
    IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS 
                   WHERE TABLE_NAME = 'unified_media' 
                   AND COLUMN_NAME = 'is_in_queue' 
                   AND TABLE_SCHEMA = DATABASE()) THEN
        ALTER TABLE unified_media ADD COLUMN is_in_queue BOOLEAN NOT NULL DEFAULT FALSE;
    END IF;
    
    IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS 
                   WHERE TABLE_NAME = 'unified_media' 
                   AND COLUMN_NAME = 'queue_added_at' 
                   AND TABLE_SCHEMA = DATABASE()) THEN
        ALTER TABLE unified_media ADD COLUMN queue_added_at DATETIME NULL;
    END IF;
    
    IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS 
                   WHERE TABLE_NAME = 'unified_media' 
                   AND COLUMN_NAME = 'queue_attempts' 
                   AND TABLE_SCHEMA = DATABASE()) THEN
        ALTER TABLE unified_media ADD COLUMN queue_attempts INT NOT NULL DEFAULT 0;
    END IF;
END$$

DELIMITER ;

-- Execute the procedure
CALL AddColumnIfNotExists();

-- Drop the procedure
DROP PROCEDURE AddColumnIfNotExists;

-- Create indexes for enhanced season tracking (using stored procedures for IF NOT EXISTS)
DELIMITER $$

CREATE PROCEDURE CreateIndexIfNotExists()
BEGIN
    -- Create idx_unified_media_tv_seasons index
    IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.STATISTICS 
                   WHERE TABLE_NAME = 'unified_media' 
                   AND INDEX_NAME = 'idx_unified_media_tv_seasons' 
                   AND TABLE_SCHEMA = DATABASE()) THEN
        CREATE INDEX idx_unified_media_tv_seasons ON unified_media(media_type, tmdb_id, total_seasons);
    END IF;
    
    -- Create idx_unified_media_seasons_processing index
    IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.STATISTICS 
                   WHERE TABLE_NAME = 'unified_media' 
                   AND INDEX_NAME = 'idx_unified_media_seasons_processing' 
                   AND TABLE_SCHEMA = DATABASE()) THEN
        CREATE INDEX idx_unified_media_seasons_processing ON unified_media(media_type, seasons_processing);
    END IF;
    
    -- Create idx_unified_media_tv_seasons_tracking index
    IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.STATISTICS 
                   WHERE TABLE_NAME = 'unified_media' 
                   AND INDEX_NAME = 'idx_unified_media_tv_seasons_tracking' 
                   AND TABLE_SCHEMA = DATABASE()) THEN
        CREATE INDEX idx_unified_media_tv_seasons_tracking ON unified_media(media_type, total_seasons, seasons_processing);
    END IF;
    
    -- Create idx_unified_media_queue_status index
    IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.STATISTICS 
                   WHERE TABLE_NAME = 'unified_media' 
                   AND INDEX_NAME = 'idx_unified_media_queue_status' 
                   AND TABLE_SCHEMA = DATABASE()) THEN
        CREATE INDEX idx_unified_media_queue_status ON unified_media (is_in_queue, status);
    END IF;
    
    -- Create idx_unified_media_queue_attempts index
    IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.STATISTICS 
                   WHERE TABLE_NAME = 'unified_media' 
                   AND INDEX_NAME = 'idx_unified_media_queue_attempts' 
                   AND TABLE_SCHEMA = DATABASE()) THEN
        CREATE INDEX idx_unified_media_queue_attempts ON unified_media (queue_attempts, queue_added_at);
    END IF;
END$$

DELIMITER ;

-- Execute the procedure
CALL CreateIndexIfNotExists();

-- Drop the procedure
DROP PROCEDURE CreateIndexIfNotExists;

-- ==============================================
-- VIEWS FOR BACKWARD COMPATIBILITY
-- ==============================================

-- tv_subscriptions view removed - frontend now queries unified_media directly

-- Create a view for processed media
CREATE OR REPLACE VIEW processed_media AS
SELECT 
    id,
    tmdb_id,
    imdb_id,
    trakt_id,
    media_type,
    title,
    year,
    overseerr_request_id,
    overseerr_media_id,
    status as processing_status,
    processing_stage,
    seasons_processed,
    confirmed_episodes as episodes_confirmed,
    failed_episodes as episodes_failed,
    torrents_found,
    error_message,
    processing_started_at,
    processing_completed_at,
    last_checked_at,
    extra_data,
    poster_url,
    thumb_url,
    fanart_url,
    poster_image,
    poster_image_format,
    poster_image_size,
    thumb_image,
    thumb_image_format,
    thumb_image_size,
    fanart_image,
    fanart_image_format,
    fanart_image_size,
    created_at,
    updated_at
FROM unified_media
WHERE status IN ('processing', 'completed', 'failed', 'skipped');

-- Create a view for media requests
CREATE OR REPLACE VIEW media_requests_view AS
SELECT 
    id,
    overseerr_request_id,
    overseerr_media_id,
    tmdb_id,
    imdb_id,
    trakt_id,
    media_type,
    title,
    year,
    status,
    requested_by,
    requested_at,
    processing_started_at as processed_at,
    processing_completed_at as completed_at,
    error_message,
    extra_data,
    created_at,
    updated_at
FROM unified_media
WHERE overseerr_request_id IS NOT NULL;

-- ==============================================
-- DEFAULT DATA INSERTION
-- ==============================================

-- Insert default notification settings
INSERT IGNORE INTO notification_settings (id, discord_webhook_url, notify_on_success, notify_on_error, notify_on_warning, show_debug_widget)
VALUES (1, NULL, TRUE, TRUE, TRUE, FALSE);

-- Insert default system configuration
INSERT IGNORE INTO system_config (config_key, config_value, config_type, description, is_active)
VALUES 
    ('refresh_interval_minutes', '60', 'int', 'Background task refresh interval in minutes', TRUE),
    ('headless_mode', 'true', 'bool', 'Run browser in headless mode', TRUE),
    ('enable_automatic_background_task', 'false', 'bool', 'Enable automatic background processing', TRUE),
    ('enable_show_subscription_task', 'false', 'bool', 'Enable TV show subscription monitoring', TRUE),
    ('torrent_filter_regex', '', 'string', 'Default torrent filter regex pattern', TRUE),
    ('max_movie_size', '0', 'string', 'Maximum movie size in GB (0 = biggest size possible)', TRUE),
    ('max_episode_size', '0', 'string', 'Maximum episode size in GB (0 = biggest size possible)', TRUE),
    -- Real-Debrid Configuration
    ('rd_access_token', '', 'string', 'Real-Debrid Access Token (encrypted)', TRUE),
    ('rd_refresh_token', '', 'string', 'Real-Debrid Refresh Token (encrypted)', TRUE),
    ('rd_client_id', '', 'string', 'Real-Debrid Client ID (encrypted)', TRUE),
    ('rd_client_secret', '', 'string', 'Real-Debrid Client Secret (encrypted)', TRUE),
    -- Overseerr Configuration
    ('overseerr_base', '', 'string', 'Overseerr Base URL', TRUE),
    ('overseerr_api_key', '', 'string', 'Overseerr API Key (encrypted)', TRUE),
    -- Trakt Configuration
    ('trakt_api_key', '', 'string', 'Trakt API Key (encrypted)', TRUE),
    -- Database Configuration
    ('db_host', 'mysql', 'string', 'Database Host', TRUE),
    ('db_port', '3306', 'int', 'Database Port', TRUE),
    ('db_name', 'seerrbridge', 'string', 'Database Name', TRUE),
    ('db_user', 'seerrbridge', 'string', 'Database User', TRUE),
    ('db_password', '', 'string', 'Database Password (encrypted)', TRUE),
    ('mysql_root_password', '', 'string', 'MySQL Root Password (encrypted)', TRUE),
    -- System Configuration
    ('onboarding_completed', 'false', 'bool', 'Whether initial setup has been completed', TRUE),
    ('setup_required', 'true', 'bool', 'Whether setup is required', TRUE),
    -- Failed Item Retry Configuration
    ('enable_failed_item_retry', 'true', 'boolean', 'Enable automatic retry of failed movies and TV shows', TRUE),
    ('failed_item_retry_interval_minutes', '30', 'integer', 'Interval in minutes between failed item retry checks', TRUE),
    ('failed_item_max_retry_attempts', '3', 'integer', 'Maximum number of retry attempts for failed items', TRUE),
    ('failed_item_retry_delay_hours', '2', 'integer', 'Initial delay in hours before first retry attempt', TRUE),
    ('failed_item_retry_backoff_multiplier', '2', 'integer', 'Multiplier for retry delay (exponential backoff)', TRUE),
    ('failed_item_max_retry_delay_hours', '24', 'integer', 'Maximum delay in hours between retry attempts', TRUE),
    -- Additional Task Configuration
    ('movie_queue_maxsize', '250', 'int', 'Maximum size of movie processing queue', TRUE),
    ('tv_queue_maxsize', '250', 'int', 'Maximum size of TV show processing queue', TRUE),
    ('token_refresh_interval_minutes', '10', 'int', 'Interval in minutes for token refresh', TRUE),
    ('movie_processing_check_interval_minutes', '15', 'int', 'Interval in minutes for movie processing checks', TRUE),
    ('library_refresh_interval_minutes', '30', 'int', 'Interval in minutes for library refresh when queues are empty', TRUE),
    ('subscription_check_interval_minutes', '60', 'int', 'Interval in minutes for show subscription checks', TRUE),
    ('background_tasks_enabled', 'true', 'bool', 'Master switch for all background tasks', TRUE),
    ('queue_processing_enabled', 'true', 'bool', 'Enable queue processing', TRUE),
    ('scheduler_enabled', 'true', 'bool', 'Enable task scheduler', TRUE);

-- Insert default queue status
INSERT IGNORE INTO queue_status (queue_type, queue_size, max_size, is_processing)
VALUES 
    ('movie', 0, 250, FALSE),
    ('tv', 0, 250, FALSE);

-- Insert default service status
INSERT IGNORE INTO service_status (service_name, status, version, uptime_seconds, uptime_string, start_time, current_time_value, browser_status, automatic_processing, show_subscription, refresh_interval_minutes)
VALUES 
    ('seerrbridge', 'starting', '0.7.0', 0, '0s', NOW(), NOW(), 'not_initialized', FALSE, FALSE, 30.0);

-- ==============================================
-- COMPLETION MESSAGE
-- ==============================================

SELECT 'Database initialization completed successfully!' as status;
