#!/usr/bin/env python3
"""
Initialize failed item retry configuration in the database
"""
import sys
import os

# Add the parent directory to the path so we can import seerr modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seerr.task_config_manager import task_config
from seerr.db_logger import log_info, log_success, log_error

def init_failed_item_config():
    """Initialize failed item retry configuration"""
    try:
        log_info("Config Initialization", "Initializing failed item retry configuration", 
                module="init_failed_item_config", function="init_failed_item_config")
        
        # Failed item retry settings
        configs = [
            {
                'key': 'enable_failed_item_retry',
                'value': True,
                'type': 'boolean',
                'description': 'Enable automatic retry of failed movies and TV shows'
            },
            {
                'key': 'failed_item_retry_interval_minutes',
                'value': 30,
                'type': 'integer',
                'description': 'Interval in minutes between failed item retry checks'
            },
            {
                'key': 'failed_item_max_retry_attempts',
                'value': 3,
                'type': 'integer',
                'description': 'Maximum number of retry attempts for failed items'
            },
            {
                'key': 'failed_item_retry_delay_hours',
                'value': 2,
                'type': 'integer',
                'description': 'Initial delay in hours before first retry attempt'
            },
            {
                'key': 'failed_item_retry_backoff_multiplier',
                'value': 2,
                'type': 'integer',
                'description': 'Multiplier for retry delay (exponential backoff)'
            },
            {
                'key': 'failed_item_max_retry_delay_hours',
                'value': 24,
                'type': 'integer',
                'description': 'Maximum delay in hours between retry attempts'
            }
        ]
        
        # Set each configuration
        for config in configs:
            success = task_config.set_config(
                config['key'],
                config['value'],
                config['type'],
                config['description']
            )
            
            if success:
                log_success("Config Initialization", f"Set {config['key']} = {config['value']}", 
                           module="init_failed_item_config", function="init_failed_item_config")
            else:
                log_error("Config Initialization", f"Failed to set {config['key']}", 
                         module="init_failed_item_config", function="init_failed_item_config")
        
        log_success("Config Initialization", "Failed item retry configuration initialized successfully", 
                   module="init_failed_item_config", function="init_failed_item_config")
        
    except Exception as e:
        log_error("Config Initialization", f"Error initializing failed item config: {e}", 
                 module="init_failed_item_config", function="init_failed_item_config")
        raise

if __name__ == "__main__":
    init_failed_item_config()
