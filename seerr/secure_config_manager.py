"""
Secure Configuration Manager for SeerrBridge
Handles encrypted storage and retrieval of all configuration values
"""
import os
import json
from typing import Any, Dict, Optional, Union
from datetime import datetime
from sqlalchemy.orm import Session
from seerr.database import get_db, SystemConfig
from seerr.encryption_utils import config_encryption
from loguru import logger

class SecureConfigManager:
    """Manages secure configuration stored in database with encryption"""
    
    def __init__(self):
        self._cache = {}
        self._cache_timestamp = None
        self._cache_ttl = 30  # Cache for 30 seconds
        self._sensitive_keys = {
            'rd_access_token', 'rd_refresh_token', 'rd_client_id', 'rd_client_secret',
            'overseerr_api_key', 'trakt_api_key', 'discord_webhook_url',
            'mysql_password', 'mysql_root_password'
        }
    
    def _is_cache_valid(self) -> bool:
        """Check if the cache is still valid"""
        if not self._cache_timestamp:
            return False
        return (datetime.utcnow() - self._cache_timestamp).total_seconds() < self._cache_ttl
    
    def _load_config_from_db(self) -> Dict[str, Any]:
        """Load all configuration from database"""
        db = get_db()
        try:
            configs = db.query(SystemConfig).filter(
                SystemConfig.is_active == True
            ).all()
            
            config_dict = {}
            for config in configs:
                # Decrypt sensitive values
                if config.config_key in self._sensitive_keys and config.config_value:
                    try:
                        if config_encryption.is_encrypted(config.config_value):
                            value = config_encryption.decrypt_value(config.config_value)
                            
                            # Validate decrypted value for tokens (should be valid JSON for access tokens)
                            if config.config_key == 'rd_access_token' and value:
                                # Check if the decrypted value looks valid
                                value_str = str(value).strip()
                                if value_str and len(value_str) > 10:
                                    # Check for obvious corruption (too many asterisks)
                                    if value_str.count('*') > len(value_str) * 0.3:
                                        logger.warning(f"Config Error: Decrypted token for {config.config_key} appears corrupted (too many asterisks)")
                                        logger.warning(f"Config Error: Decrypted value preview: {value_str[:50]}...")
                                        logger.warning(f"Config Error: Clearing corrupted token from database")
                                        # Clear the corrupted value
                                        value = None
                                        try:
                                            config.config_value = ''
                                            db.commit()
                                            logger.info(f"Config Fix: Cleared corrupted {config.config_key} from database")
                                            # Force setup mode since tokens are corrupted
                                            self.force_setup_mode(reason=f"Corrupted {config.config_key} detected")
                                        except Exception as clear_err:
                                            logger.error(f"Config Error: Failed to clear corrupted value: {clear_err}")
                                    # Try to parse as JSON if it looks like JSON
                                    elif value_str.startswith('{'):
                                        try:
                                            import json
                                            parsed = json.loads(value_str)
                                            # Validate required fields for access token
                                            if 'expiry' not in parsed or 'value' not in parsed:
                                                raise ValueError("Token missing required fields")
                                            # Token is valid, keep it
                                        except (json.JSONDecodeError, ValueError) as json_err:
                                            logger.warning(f"Config Error: Decrypted token for {config.config_key} is not valid JSON: {json_err}")
                                            logger.warning(f"Config Error: Decrypted value preview: {value_str[:50]}...")
                                            logger.warning(f"Config Error: Clearing corrupted token from database")
                                            # Clear the corrupted value instead of keeping it
                                            value = None
                                            try:
                                                config.config_value = ''
                                                db.commit()
                                                logger.info(f"Config Fix: Cleared corrupted {config.config_key} from database")
                                                # Force setup mode since tokens are corrupted
                                                self.force_setup_mode(reason=f"Corrupted {config.config_key} - Invalid JSON structure")
                                            except Exception as clear_err:
                                                logger.error(f"Config Error: Failed to clear corrupted value: {clear_err}")
                                    elif len(value_str) < 20:
                                        # Too short to be a valid token structure
                                        logger.warning(f"Config Error: Decrypted token for {config.config_key} appears too short ({len(value_str)} chars)")
                                        value = None
                                        try:
                                            config.config_value = ''
                                            db.commit()
                                            logger.info(f"Config Fix: Cleared too-short {config.config_key} from database")
                                            # Force setup mode since tokens are corrupted
                                            self.force_setup_mode(reason=f"Corrupted {config.config_key} - Token too short")
                                        except Exception as clear_err:
                                            logger.error(f"Config Error: Failed to clear corrupted value: {clear_err}")
                                    else:
                                        # Value doesn't start with '{' and is long enough - might be a plain token
                                        # Keep it, but log a warning
                                        logger.warning(f"Config Error: Token for {config.config_key} doesn't appear to be JSON format")
                                else:
                                    logger.warning(f"Config Error: Decrypted value for {config.config_key} is empty or too short")
                                    value = None
                        else:
                            # Legacy unencrypted value - encrypt it
                            value = config.config_value
                            self.set_config(config.config_key, value, config.config_type, config.description)
                    except Exception as e:
                        logger.error(f"Config Error: Failed to decrypt {config.config_key}: {e}")
                        logger.error(f"Config Error: Value preview: {config.config_value[:100] if config.config_value else 'None'}...")
                        logger.error(f"Config Error: This usually means the encryption key has changed or the value is corrupted.")
                        # Clear the corrupted encrypted value instead of using it
                        value = None
                        # Update the database to clear the corrupted value
                        try:
                            config.config_value = ''
                            db.commit()
                            logger.info(f"Config Fix: Cleared corrupted value for {config.config_key}")
                            # Force setup mode for sensitive token configs that failed to decrypt
                            if config.config_key in ['rd_access_token', 'rd_refresh_token']:
                                self.force_setup_mode(reason=f"Failed to decrypt {config.config_key} - Possible encryption key mismatch or corruption")
                        except Exception as update_error:
                            logger.error(f"Config Error: Failed to clear corrupted value: {update_error}")
                else:
                    # Convert value based on type
                    value = self._convert_config_value(config.config_value, config.config_type)
                
                config_dict[config.config_key] = value
            
            return config_dict
        except Exception as e:
            logger.error(f"Config Error: Error loading configuration from database: {e}")
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
            logger.error(f"Config Error: Error converting config value '{value}' to type '{config_type}': {e}")
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
    
    def set_config(self, key: str, value: Any, config_type: str = 'string', description: str = None, is_sensitive: bool = None) -> bool:
        """Set a configuration value"""
        try:
            db = get_db()
            
            # Determine if this is a sensitive key
            if is_sensitive is None:
                is_sensitive = key in self._sensitive_keys
            
            # Convert value to string for storage
            if config_type == 'json':
                str_value = json.dumps(value)
            else:
                str_value = str(value)
            
            # Check if config exists before processing
            existing_config = db.query(SystemConfig).filter(
                SystemConfig.config_key == key
            ).first()
            
            # For sensitive keys, prevent overwriting existing encrypted values with empty strings
            if is_sensitive and existing_config and existing_config.config_value:
                # Check if the existing value is encrypted
                existing_value = existing_config.config_value.strip()
                is_existing_encrypted = False
                try:
                    # Try to use the encryption utility's is_encrypted check
                    is_existing_encrypted = config_encryption.is_encrypted(existing_value)
                except:
                    # Fallback: check if it looks like base64-encoded encrypted data
                    # Encrypted values from Fernet are base64-encoded and typically 44+ characters
                    if len(existing_value) > 40:
                        try:
                            import base64
                            base64.urlsafe_b64decode(existing_value.encode())
                            is_existing_encrypted = True
                        except:
                            pass
                
                # If existing value is encrypted and new value is empty/None, skip update
                if is_existing_encrypted and (not str_value or str_value.strip() == '' or str_value == 'None' or str_value == 'null'):
                    logger.info(f"Config Update: Skipping update of encrypted {key} with empty value to preserve existing encrypted data")
                    return True  # Return success without updating
            
            # Encrypt sensitive values
            if is_sensitive and str_value:
                str_value = config_encryption.encrypt_value(str_value)
            
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
            
            logger.info(f"Config Update: Updated configuration: {key} = {'[ENCRYPTED]' if is_sensitive else value}")
            return True
            
        except Exception as e:
            logger.error(f"Config Error: Error setting configuration {key}: {e}")
            return False
        finally:
            db.close()
    
    def get_all_configs(self) -> Dict[str, Any]:
        """Get all configurations"""
        if not self._is_cache_valid():
            self._cache = self._load_config_from_db()
            self._cache_timestamp = datetime.utcnow()
        
        return self._cache.copy()
    
    def get_config_for_ui(self) -> Dict[str, Any]:
        """Get configurations for UI display (masks sensitive values)"""
        configs = self.get_all_configs()
        
        # Mask sensitive values for UI
        for key in self._sensitive_keys:
            if key in configs and configs[key]:
                configs[key] = "[ENCRYPTED]"
        
        return configs
    
    def invalidate_cache(self):
        """Force cache invalidation to reload from database"""
        self._cache = {}
        self._cache_timestamp = None
        logger.info("Config cache invalidated")
    
    def migrate_from_env(self) -> bool:
        """Migrate configuration from environment variables to database"""
        try:
            env_mappings = {
                'RD_ACCESS_TOKEN': 'rd_access_token',
                'RD_REFRESH_TOKEN': 'rd_refresh_token', 
                'RD_CLIENT_ID': 'rd_client_id',
                'RD_CLIENT_SECRET': 'rd_client_secret',
                'OVERSEERR_BASE': 'overseerr_base',
                'OVERSEERR_API_KEY': 'overseerr_api_key',
                'TRAKT_API_KEY': 'trakt_api_key',
                'HEADLESS_MODE': 'headless_mode',
                'ENABLE_AUTOMATIC_BACKGROUND_TASK': 'enable_automatic_background_task',
                'ENABLE_SHOW_SUBSCRIPTION_TASK': 'enable_show_subscription_task',
                'TORRENT_FILTER_REGEX': 'torrent_filter_regex',
                'MAX_MOVIE_SIZE': 'max_movie_size',
                'MAX_EPISODE_SIZE': 'max_episode_size',
                'REFRESH_INTERVAL_MINUTES': 'refresh_interval_minutes',
                'DB_HOST': 'db_host',
                'DB_PORT': 'db_port',
                'DB_NAME': 'db_name',
                'DB_USER': 'db_user',
                'DB_PASSWORD': 'db_password',
                'MYSQL_ROOT_PASSWORD': 'mysql_root_password'
            }
            
            migrated_count = 0
            for env_key, db_key in env_mappings.items():
                env_value = os.getenv(env_key)
                if env_value and not self.get_config(db_key):
                    # Determine config type
                    if env_key in ['HEADLESS_MODE', 'ENABLE_AUTOMATIC_BACKGROUND_TASK', 'ENABLE_SHOW_SUBSCRIPTION_TASK']:
                        config_type = 'bool'
                    elif env_key in ['DB_PORT', 'MAX_MOVIE_SIZE', 'MAX_EPISODE_SIZE']:
                        config_type = 'int'
                    elif env_key in ['REFRESH_INTERVAL_MINUTES']:
                        config_type = 'float'
                    else:
                        config_type = 'string'
                    
                    self.set_config(
                        db_key, 
                        env_value, 
                        config_type, 
                        f"Migrated from {env_key} environment variable",
                        is_sensitive=(db_key in self._sensitive_keys)
                    )
                    migrated_count += 1
            
            logger.info(f"Config Migration: Migrated {migrated_count} configuration values from environment variables")
            return True
            
        except Exception as e:
            logger.error(f"Config Migration: Error migrating configuration: {e}")
            return False
    
    def check_required_configs(self) -> Dict[str, bool]:
        """Check which required configurations are missing"""
        required_configs = {
            'rd_access_token': 'Real-Debrid Access Token',
            'rd_refresh_token': 'Real-Debrid Refresh Token',
            'rd_client_id': 'Real-Debrid Client ID',
            'rd_client_secret': 'Real-Debrid Client Secret',
            'overseerr_base': 'Overseerr Base URL',
            'overseerr_api_key': 'Overseerr API Key',
            'trakt_api_key': 'Trakt API Key'
        }
        
        missing = {}
        for key, description in required_configs.items():
            value = self.get_config(key)
            missing[key] = not value or value == ""
        
        return missing
    
    def invalidate_cache(self):
        """Invalidate the configuration cache"""
        self._cache = {}
        self._cache_timestamp = None
    
    def force_setup_mode(self, reason: str = "Corrupted tokens detected"):
        """Force the system back into setup mode by marking setup as required"""
        try:
            db = get_db()
            
            # Set setup_required to true
            setup_required_config = db.query(SystemConfig).filter(
                SystemConfig.config_key == 'setup_required'
            ).first()
            
            if setup_required_config:
                setup_required_config.config_value = 'true'
                setup_required_config.updated_at = datetime.utcnow()
            else:
                new_config = SystemConfig(
                    config_key='setup_required',
                    config_value='true',
                    config_type='bool',
                    description=f'Setup required: {reason}',
                    is_active=True
                )
                db.add(new_config)
            
            # Set onboarding_completed to false
            onboarding_completed_config = db.query(SystemConfig).filter(
                SystemConfig.config_key == 'onboarding_completed'
            ).first()
            
            if onboarding_completed_config:
                onboarding_completed_config.config_value = 'false'
                onboarding_completed_config.updated_at = datetime.utcnow()
            else:
                new_config = SystemConfig(
                    config_key='onboarding_completed',
                    config_value='false',
                    config_type='bool',
                    description='Onboarding completion status',
                    is_active=True
                )
                db.add(new_config)
            
            db.commit()
            
            # Invalidate cache to force reload
            self.invalidate_cache()
            
            logger.warning(f"Setup Mode: Forced setup mode enabled. Reason: {reason}")
            logger.warning(f"Setup Mode: System will require setup wizard completion before proceeding.")
            return True
            
        except Exception as e:
            logger.error(f"Setup Mode: Error forcing setup mode: {e}")
            return False
        finally:
            db.close()

# Global instance
secure_config = SecureConfigManager()
