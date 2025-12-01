"""
Task Configuration Manager for SeerrBridge
Handles reading and updating task configuration from the database
"""
import json
from typing import Any, Dict, Optional, Union
from datetime import datetime
from sqlalchemy.orm import Session
from seerr.database import get_db, SystemConfig
from seerr.db_logger import log_info, log_error, log_debug


class TaskConfigManager:
    """Manages task configuration stored in the database"""
    
    def __init__(self):
        self._cache = {}
        self._cache_timestamp = None
        self._cache_ttl = 30  # Cache for 30 seconds
    
    def _is_cache_valid(self) -> bool:
        """Check if the cache is still valid"""
        if not self._cache_timestamp:
            return False
        return (datetime.utcnow() - self._cache_timestamp).total_seconds() < self._cache_ttl
    
    def _load_config_from_db(self) -> Dict[str, Any]:
        """Load all task configuration from database"""
        db = get_db()
        try:
            configs = db.query(SystemConfig).filter(
                SystemConfig.is_active == True
            ).all()
            
            config_dict = {}
            for config in configs:
                # Convert value based on type
                value = self._convert_config_value(config.config_value, config.config_type)
                config_dict[config.config_key] = value
            
            return config_dict
        except Exception as e:
            log_error("Config Error", f"Error loading configuration from database: {e}", 
                     module="task_config_manager", function="_load_config_from_db")
            return {}
        finally:
            db.close()
    
    def _convert_config_value(self, value: str, config_type: str) -> Any:
        """Convert string value to appropriate type"""
        if value is None:
            return None
            
        try:
            if config_type == 'bool':
                return value.lower() in ('true', '1', 'yes', 'on')
            elif config_type == 'int':
                # Handle float values that should be int
                if '.' in str(value):
                    return int(float(value))
                return int(value)
            elif config_type == 'float':
                return float(value)
            elif config_type == 'json':
                return json.loads(value)
            else:  # string
                return value
        except (ValueError, TypeError, json.JSONDecodeError) as e:
            log_error("Config Error", f"Error converting config value '{value}' to type '{config_type}': {e}",
                     module="task_config_manager", function="_convert_config_value")
            return value
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key"""
        # Check cache first
        if self._is_cache_valid() and key in self._cache:
            return self._cache[key]
        
        # Load from database if cache is invalid
        if not self._is_cache_valid():
            self._cache = self._load_config_from_db()
            self._cache_timestamp = datetime.utcnow()
        
        return self._cache.get(key, default)
    
    def set_config(self, key: str, value: Any, config_type: str = 'string', description: str = None) -> bool:
        """Set a configuration value"""
        try:
            db = get_db()
            
            # Convert value to string for storage
            if config_type == 'json':
                str_value = json.dumps(value)
            else:
                str_value = str(value)
            
            # Check if config exists
            existing_config = db.query(SystemConfig).filter(
                SystemConfig.config_key == key
            ).first()
            
            if existing_config:
                # Update existing
                existing_config.config_value = str_value
                existing_config.config_type = config_type
                if description:
                    existing_config.description = description
                existing_config.updated_at = datetime.utcnow()
            else:
                # Create new
                new_config = SystemConfig(
                    config_key=key,
                    config_value=str_value,
                    config_type=config_type,
                    description=description or f"Configuration for {key}",
                    is_active=True
                )
                db.add(new_config)
            
            db.commit()
            
            # Update cache
            self._cache[key] = value
            if not self._cache_timestamp:
                self._cache_timestamp = datetime.utcnow()
            
            log_info("Config Update", f"Updated configuration: {key} = {value}", 
                    module="task_config_manager", function="set_config")
            return True
            
        except Exception as e:
            log_error("Config Error", f"Error setting configuration {key}: {e}", 
                     module="task_config_manager", function="set_config")
            return False
        finally:
            db.close()
    
    def get_all_task_configs(self) -> Dict[str, Any]:
        """Get all task-related configurations"""
        if not self._is_cache_valid():
            self._cache = self._load_config_from_db()
            self._cache_timestamp = datetime.utcnow()
        
        # Filter for task-related configs
        task_configs = {}
        task_keys = [
            'enable_automatic_background_task',
            'enable_show_subscription_task', 
            'refresh_interval_minutes',
            'movie_queue_maxsize',
            'tv_queue_maxsize',
            'token_refresh_interval_minutes',
            'movie_processing_check_interval_minutes',
            'library_refresh_interval_minutes',
            'subscription_check_interval_minutes',
            'background_tasks_enabled',
            'queue_processing_enabled',
            'scheduler_enabled',
            'overseerr_base',
            'headless_mode',
            'torrent_filter_regex',
            'max_movie_size',
            'max_episode_size'
        ]
        
        for key in task_keys:
            if key in self._cache:
                task_configs[key] = self._cache[key]
        
        return task_configs
    
    def invalidate_cache(self):
        """Invalidate the configuration cache"""
        self._cache = {}
        self._cache_timestamp = None
        log_debug("Config Cache", "Configuration cache invalidated", 
                 module="task_config_manager", function="invalidate_cache")


# Global instance
task_config = TaskConfigManager()
