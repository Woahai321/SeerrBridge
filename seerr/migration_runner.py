#!/usr/bin/env python3
"""
Automatic database migration runner
This ensures all database migrations are applied on startup
"""
import os
import sys
from loguru import logger
from sqlalchemy import text, inspect
from .database import get_db, engine

class MigrationRunner:
    """Handles automatic database migrations"""
    
    def __init__(self):
        self.db = get_db()
        self.inspector = inspect(engine)
    
    def check_column_exists(self, table_name: str, column_name: str) -> bool:
        """Check if a column exists in a table"""
        try:
            columns = self.inspector.get_columns(table_name)
            return any(col['name'] == column_name for col in columns)
        except Exception as e:
            logger.warning(f"Could not check columns for table {table_name}: {e}")
            return False
    
    def create_missing_tables(self):
        """Create any missing tables"""
        try:
            # Check if processed_media table exists
            if not self.inspector.has_table('processed_media'):
                logger.info("processed_media table does not exist, creating it...")
                create_table_sql = """
                CREATE TABLE processed_media (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    tmdb_id INT NOT NULL,
                    imdb_id VARCHAR(20),
                    trakt_id VARCHAR(20),
                    media_type VARCHAR(10) NOT NULL,
                    title VARCHAR(500) NOT NULL,
                    year INT,
                    overseerr_request_id INT,
                    overseerr_media_id INT,
                    processing_status VARCHAR(20) NOT NULL DEFAULT 'pending',
                    processing_stage VARCHAR(50),
                    seasons_processed JSON,
                    episodes_confirmed JSON,
                    episodes_failed JSON,
                    torrents_found INT DEFAULT 0,
                    error_message TEXT,
                    processing_started_at DATETIME,
                    processing_completed_at DATETIME,
                    last_checked_at DATETIME,
                    extra_data JSON,
                    poster_url VARCHAR(500),
                    thumb_url VARCHAR(500),
                    fanart_url VARCHAR(500),
                    poster_image LONGBLOB,
                    poster_image_format VARCHAR(10),
                    poster_image_size INT,
                    thumb_image LONGBLOB,
                    thumb_image_format VARCHAR(10),
                    thumb_image_size INT,
                    fanart_image LONGBLOB,
                    fanart_image_format VARCHAR(10),
                    fanart_image_size INT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_tmdb_id (tmdb_id),
                    INDEX idx_imdb_id (imdb_id),
                    INDEX idx_trakt_id (trakt_id),
                    INDEX idx_media_type (media_type),
                    INDEX idx_overseerr_request_id (overseerr_request_id),
                    INDEX idx_overseerr_media_id (overseerr_media_id),
                    INDEX idx_processing_status (processing_status),
                    INDEX idx_processing_stage (processing_stage),
                    INDEX idx_created_at (created_at),
                    INDEX idx_updated_at (updated_at),
                    INDEX idx_tmdb_media_type (tmdb_id, media_type),
                    INDEX idx_overseerr_request (overseerr_request_id),
                    INDEX idx_created_updated (created_at, updated_at)
                )
                """
                self.db.execute(text(create_table_sql))
                logger.success("Successfully created processed_media table")
            else:
                pass  # Table already exists
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error creating missing tables: {e}")
            self.db.rollback()
            raise
        finally:
            self.db.close()

    def add_missing_columns(self):
        """Add any missing columns to existing tables"""
        try:
            # show_subscriptions table has been removed - now using unified_media table
            logger.info("show_subscriptions table migration skipped - using unified_media table")
            
            # Check if processed_media table exists and add missing URL columns
            if self.inspector.has_table('processed_media'):
                processed_media_columns = [
                    ('poster_url', 'VARCHAR(500) NULL'),
                    ('thumb_url', 'VARCHAR(500) NULL'),
                    ('fanart_url', 'VARCHAR(500) NULL')
                ]
                
                # Add missing URL columns to processed_media
                for column_name, column_definition in processed_media_columns:
                    if not self.check_column_exists('processed_media', column_name):
                        logger.info(f"Adding missing column to processed_media: {column_name}")
                        alter_sql = f"ALTER TABLE processed_media ADD COLUMN {column_name} {column_definition}"
                        self.db.execute(text(alter_sql))
                        logger.success(f"Successfully added column to processed_media: {column_name}")
                    else:
                        pass  # Column already exists
            
            # Add 'ignored' status to unified_media table if it doesn't exist
            if self.inspector.has_table('unified_media'):
                try:
                    # Check if 'ignored' is already in the ENUM
                    check_sql = text("""
                        SELECT COLUMN_TYPE 
                        FROM INFORMATION_SCHEMA.COLUMNS 
                        WHERE TABLE_SCHEMA = DATABASE() 
                        AND TABLE_NAME = 'unified_media' 
                        AND COLUMN_NAME = 'status'
                    """)
                    result = self.db.execute(check_sql).fetchone()
                    
                    if result and result[0]:
                        current_enum = result[0].decode() if isinstance(result[0], bytes) else str(result[0])
                        needs_update = False
                        new_enum_values = []
                        
                        # Check which values need to be added
                        if 'ignored' not in current_enum:
                            needs_update = True
                            new_enum_values.append('ignored')
                        if 'unreleased' not in current_enum:
                            needs_update = True
                            new_enum_values.append('unreleased')
                        
                        if needs_update:
                            # Build the new ENUM with all values
                            enum_values = ['pending', 'processing', 'completed', 'failed', 'skipped', 'cancelled', 'ignored', 'unreleased']
                            logger.info(f"Adding status values to unified_media.status column: {new_enum_values}")
                            enum_string = "', '".join(enum_values)
                            alter_enum_sql = text(f"""
                                ALTER TABLE unified_media 
                                MODIFY COLUMN status ENUM('{enum_string}') NOT NULL DEFAULT 'pending'
                            """)
                            self.db.execute(alter_enum_sql)
                            logger.success(f"Successfully added status values {new_enum_values} to unified_media table")
                        else:
                            logger.info("All status values already exist in unified_media.status column")
                        
                        # Add released_date column if it doesn't exist
                        if not self.check_column_exists('unified_media', 'released_date'):
                            logger.info("Adding released_date column to unified_media table")
                            alter_table_sql = text("""
                                ALTER TABLE unified_media 
                                ADD COLUMN released_date DATETIME NULL COMMENT 'Release date from Trakt API'
                            """)
                            self.db.execute(alter_table_sql)
                            
                            # Add index for released_date
                            try:
                                index_sql = text("""
                                    CREATE INDEX idx_released_date ON unified_media(released_date)
                                """)
                                self.db.execute(index_sql)
                                logger.success("Successfully added released_date column and index to unified_media table")
                            except Exception as idx_e:
                                logger.warning(f"Could not create index for released_date (may already exist): {idx_e}")
                                logger.success("Successfully added released_date column to unified_media table")
                        else:
                            logger.info("released_date column already exists in unified_media table")
                except Exception as e:
                    logger.warning(f"Could not check/modify status ENUM: {e}")
            
            self.db.commit()
            logger.info("Database migration completed successfully")
            
        except Exception as e:
            logger.error(f"Error during database migration: {e}")
            self.db.rollback()
            raise
        finally:
            self.db.close()
    
    def run_migrations(self):
        """Run all necessary migrations"""
        logger.info("Starting automatic database migrations...")
        try:
            self.create_missing_tables()
            self.add_missing_columns()
            logger.success("All database migrations completed successfully")
        except Exception as e:
            logger.error(f"Database migration failed: {e}")
            raise

def run_automatic_migrations():
    """Entry point for automatic migrations"""
    try:
        migration_runner = MigrationRunner()
        migration_runner.run_migrations()
    except Exception as e:
        logger.error(f"Failed to run automatic migrations: {e}")
        # Don't raise here - let the application continue even if migrations fail
        # This prevents the app from crashing on startup due to migration issues
        pass

if __name__ == "__main__":
    run_automatic_migrations()
