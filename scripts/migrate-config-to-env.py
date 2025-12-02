#!/usr/bin/env python3
"""
Migration script to move configuration from system_config table to .env file
This script reads all config values from the database and writes them to .env
"""

import os
import sys
sys.path.append('.')

from seerr.database import get_db, SystemConfig
from seerr.env_file_manager import env_file
from loguru import logger

# Map config keys to environment variable names
CONFIG_TO_ENV = {
    'rd_access_token': 'RD_ACCESS_TOKEN',
    'rd_refresh_token': 'RD_REFRESH_TOKEN',
    'rd_client_id': 'RD_CLIENT_ID',
    'rd_client_secret': 'RD_CLIENT_SECRET',
    'overseerr_base': 'OVERSEERR_BASE',
    'overseerr_api_key': 'OVERSEERR_API_KEY',
    'trakt_api_key': 'TRAKT_API_KEY',
    'discord_webhook_url': 'DISCORD_WEBHOOK_URL',
    'headless_mode': 'HEADLESS_MODE',
    'enable_automatic_background_task': 'ENABLE_AUTOMATIC_BACKGROUND_TASK',
    'enable_show_subscription_task': 'ENABLE_SHOW_SUBSCRIPTION_TASK',
    'refresh_interval_minutes': 'REFRESH_INTERVAL_MINUTES',
    'torrent_filter_regex': 'TORRENT_FILTER_REGEX',
    'max_movie_size': 'MAX_MOVIE_SIZE',
    'max_episode_size': 'MAX_EPISODE_SIZE',
    'db_host': 'DB_HOST',
    'db_port': 'DB_PORT',
    'db_name': 'DB_NAME',
    'db_user': 'DB_USER',
    'db_password': 'DB_PASSWORD',
    'mysql_root_password': 'MYSQL_ROOT_PASSWORD',
    'setup_required': 'SETUP_REQUIRED',
    'onboarding_completed': 'ONBOARDING_COMPLETED',
    'enable_failed_item_retry': 'ENABLE_FAILED_ITEM_RETRY',
    'failed_item_retry_interval_minutes': 'FAILED_ITEM_RETRY_INTERVAL_MINUTES',
    'failed_item_max_retry_attempts': 'FAILED_ITEM_MAX_RETRY_ATTEMPTS',
    'failed_item_retry_delay_hours': 'FAILED_ITEM_RETRY_DELAY_HOURS',
    'failed_item_retry_backoff_multiplier': 'FAILED_ITEM_RETRY_BACKOFF_MULTIPLIER',
    'failed_item_max_retry_delay_hours': 'FAILED_ITEM_MAX_RETRY_DELAY_HOURS'
}

def migrate_config_to_env():
    """Migrate configuration from database to .env file"""
    logger.info("Starting migration of configuration from database to .env file")
    
    db = get_db()
    try:
        # Get all configs from database
        configs = db.query(SystemConfig).filter(
            SystemConfig.is_active == True
        ).all()
        
        env_updates = {}
        migrated_count = 0
        skipped_count = 0
        
        for config in configs:
            config_key = config.config_key
            
            # Skip setup progress keys (keep in database)
            if config_key.startswith('setup_step_') or config_key == 'setup_current_step':
                logger.debug(f"Skipping setup progress key: {config_key}")
                skipped_count += 1
                continue
            
            # Check if this config should be migrated
            env_key = CONFIG_TO_ENV.get(config_key)
            if not env_key:
                logger.debug(f"No environment variable mapping for: {config_key}, skipping")
                skipped_count += 1
                continue
            
            # Get value and convert based on type
            value = config.config_value
            if value is None or value == '':
                logger.debug(f"Empty value for {config_key}, skipping")
                skipped_count += 1
                continue
            
            # Convert value based on config type
            if config.config_type == 'bool':
                env_value = 'true' if str(value).lower() in ('true', '1', 'yes', 'on') else 'false'
            else:
                env_value = str(value)
            
            env_updates[env_key] = env_value
            migrated_count += 1
            logger.info(f"Migrating {config_key} -> {env_key}")
        
        # Write all updates to .env file
        if env_updates:
            env_file.update_env(env_updates)
            logger.success(f"Successfully migrated {migrated_count} configuration values to .env file")
        else:
            logger.info("No configuration values to migrate")
        
        logger.info(f"Migration complete: {migrated_count} migrated, {skipped_count} skipped")
        
        return migrated_count, skipped_count
        
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        raise
    finally:
        db.close()

def cleanup_database_configs():
    """Remove migrated configs from database"""
    logger.info("Cleaning up migrated configuration from database")
    
    db = get_db()
    try:
        # Get all configs that were migrated
        configs_to_delete = db.query(SystemConfig).filter(
            SystemConfig.config_key.in_(list(CONFIG_TO_ENV.keys())),
            SystemConfig.is_active == True
        ).all()
        
        deleted_count = 0
        for config in configs_to_delete:
            logger.info(f"Deleting migrated config: {config.config_key}")
            db.delete(config)
            deleted_count += 1
        
        db.commit()
        logger.success(f"Successfully deleted {deleted_count} migrated configuration entries from database")
        
        return deleted_count
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate configuration from database to .env file')
    parser.add_argument('--cleanup', action='store_true', help='Also remove migrated configs from database')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be migrated without making changes')
    
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be made")
        # TODO: Implement dry-run mode
        logger.info("Dry-run mode not fully implemented yet")
    else:
        migrated, skipped = migrate_config_to_env()
        
        if args.cleanup:
            cleanup_database_configs()
        else:
            logger.info("Use --cleanup flag to remove migrated configs from database")

