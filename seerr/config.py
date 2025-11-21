"""
Configuration module for SeerrBridge
Loads configuration from database with encryption support
"""
import os
import sys
import json
import time
from typing import Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv
from loguru import logger
from seerr.secure_config_manager import secure_config

# Configure loguru
logger.remove()  # Remove default handler

# Add file logger only if directory exists and is writable
log_file = "logs/seerrbridge.log"
if os.path.exists(os.path.dirname(log_file)):
    try:
        # Try to create/open the log file to check permissions
        open(log_file, 'a').close()
        logger.add(log_file, rotation="500 MB", encoding='utf-8')  # Use utf-8 encoding for log file
    except (PermissionError, OSError):
        # If we can't write to the file, skip file logging (database logging will be used instead)
        pass

logger.add(sys.stdout, colorize=True)  # Ensure stdout can handle Unicode
logger.level("WARNING", color="<cyan>")

# Initialize variables
RD_ACCESS_TOKEN = None
RD_REFRESH_TOKEN = None
RD_CLIENT_ID = None
RD_CLIENT_SECRET = None
OVERSEERR_BASE = None
OVERSEERR_API_BASE_URL = None
OVERSEERR_API_KEY = None
TRAKT_API_KEY = None
HEADLESS_MODE = True
ENABLE_AUTOMATIC_BACKGROUND_TASK = False
ENABLE_SHOW_SUBSCRIPTION_TASK = False
TORRENT_FILTER_REGEX = None
MAX_MOVIE_SIZE = None
MAX_EPISODE_SIZE = None
REFRESH_INTERVAL_MINUTES = 60.0
DISCREPANCY_REPO_FILE = "logs/episode_discrepancies.json"

# Database configuration
DB_HOST = None
DB_PORT = None
DB_NAME = None
DB_USER = None
DB_PASSWORD = None
USE_DATABASE = True

# Add a global variable to track start time
START_TIME = datetime.now()

def validate_size_values(movie_size, episode_size):
    """Validate movie and episode size values against available options"""
    # Valid movie size values based on DMM settings page
    valid_movie_sizes = [0, 1, 3, 5, 15, 30, 60]
    # Valid episode size values based on DMM settings page  
    valid_episode_sizes = [0, 0.1, 0.3, 0.5, 1, 3, 5]
    
    # Convert to appropriate types and validate
    try:
        if movie_size is not None:
            movie_size = float(movie_size)
            if movie_size not in valid_movie_sizes:
                logger.warning(f"Invalid movie size '{movie_size}'. Valid options: {valid_movie_sizes}. Using default (0).")
                movie_size = 0
    except (ValueError, TypeError):
        logger.warning(f"Invalid movie size format '{movie_size}'. Using default (0).")
        movie_size = 0
    
    try:
        if episode_size is not None:
            episode_size = float(episode_size)
            if episode_size not in valid_episode_sizes:
                logger.warning(f"Invalid episode size '{episode_size}'. Valid options: {valid_episode_sizes}. Using default (0).")
                episode_size = 0
    except (ValueError, TypeError):
        logger.warning(f"Invalid episode size format '{episode_size}'. Using default (0).")
        episode_size = 0
    
    return movie_size, episode_size

def load_config_from_database():
    """Load configuration from database"""
    global OVERSEERR_BASE, OVERSEERR_API_BASE_URL, HEADLESS_MODE, TORRENT_FILTER_REGEX, MAX_MOVIE_SIZE, MAX_EPISODE_SIZE
    
    try:
        # Load configuration from secure config manager
        OVERSEERR_BASE = secure_config.get_config('overseerr_base', '')
        OVERSEERR_API_BASE_URL = OVERSEERR_BASE if OVERSEERR_BASE else None
        HEADLESS_MODE = secure_config.get_config('headless_mode', False)
        TORRENT_FILTER_REGEX = secure_config.get_config('torrent_filter_regex', '^(?!.*【.*?】)(?!.*[\\u0400-\\u04FF])(?!.*\\[esp\\]).*')
        
        # Load and validate size values
        raw_movie_size = secure_config.get_config('max_movie_size', 0)
        raw_episode_size = secure_config.get_config('max_episode_size', 0)
        MAX_MOVIE_SIZE, MAX_EPISODE_SIZE = validate_size_values(raw_movie_size, raw_episode_size)
        
        logger.info("Configuration loaded from database successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to load configuration from database: {e}")
        return False

def load_config(override=False):
    """Load configuration from secure database storage with environment fallback"""
    global RD_ACCESS_TOKEN, RD_REFRESH_TOKEN, RD_CLIENT_ID, RD_CLIENT_SECRET
    global OVERSEERR_BASE, OVERSEERR_API_BASE_URL, OVERSEERR_API_KEY, TRAKT_API_KEY
    global HEADLESS_MODE, ENABLE_AUTOMATIC_BACKGROUND_TASK, ENABLE_SHOW_SUBSCRIPTION_TASK
    global TORRENT_FILTER_REGEX, MAX_MOVIE_SIZE, MAX_EPISODE_SIZE, REFRESH_INTERVAL_MINUTES
    global DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, USE_DATABASE
    
    # Load environment variables for fallback
    load_dotenv(override=override)
    
    # Try to load from secure database storage first
    if USE_DATABASE:
        try:
            # Load configuration from secure database storage
            RD_ACCESS_TOKEN = secure_config.get_config('rd_access_token') or os.getenv('RD_ACCESS_TOKEN')
            RD_REFRESH_TOKEN = secure_config.get_config('rd_refresh_token') or os.getenv('RD_REFRESH_TOKEN')
            RD_CLIENT_ID = secure_config.get_config('rd_client_id') or os.getenv('RD_CLIENT_ID')
            RD_CLIENT_SECRET = secure_config.get_config('rd_client_secret') or os.getenv('RD_CLIENT_SECRET')
            OVERSEERR_BASE = secure_config.get_config('overseerr_base') or os.getenv('OVERSEERR_BASE', '')
            OVERSEERR_API_BASE_URL = OVERSEERR_BASE if OVERSEERR_BASE else None
            OVERSEERR_API_KEY = secure_config.get_config('overseerr_api_key') or os.getenv('OVERSEERR_API_KEY')
            # OVERSEERR_API_KEY loaded
            TRAKT_API_KEY = secure_config.get_config('trakt_api_key') or os.getenv('TRAKT_API_KEY')
            HEADLESS_MODE = secure_config.get_config('headless_mode', os.getenv("HEADLESS_MODE", "true").lower() == "true")
            ENABLE_AUTOMATIC_BACKGROUND_TASK = secure_config.get_config('enable_automatic_background_task', os.getenv("ENABLE_AUTOMATIC_BACKGROUND_TASK", "false").lower() == "true")
            ENABLE_SHOW_SUBSCRIPTION_TASK = secure_config.get_config('enable_show_subscription_task', os.getenv("ENABLE_SHOW_SUBSCRIPTION_TASK", "false").lower() == "true")
            TORRENT_FILTER_REGEX = secure_config.get_config('torrent_filter_regex', os.getenv("TORRENT_FILTER_REGEX"))
            
            # Load and validate size values
            raw_movie_size = secure_config.get_config('max_movie_size', os.getenv("MAX_MOVIE_SIZE"))
            raw_episode_size = secure_config.get_config('max_episode_size', os.getenv("MAX_EPISODE_SIZE"))
            MAX_MOVIE_SIZE, MAX_EPISODE_SIZE = validate_size_values(raw_movie_size, raw_episode_size)
            
            # Database configuration
            DB_HOST = secure_config.get_config('db_host', os.getenv("DB_HOST", "localhost"))
            DB_PORT = secure_config.get_config('db_port', int(os.getenv("DB_PORT", "3306")))
            DB_NAME = secure_config.get_config('db_name', os.getenv("DB_NAME", "seerrbridge"))
            DB_USER = secure_config.get_config('db_user', os.getenv("DB_USER", "seerrbridge"))
            DB_PASSWORD = secure_config.get_config('db_password') or os.getenv("DB_PASSWORD", "seerrbridge")
            USE_DATABASE = secure_config.get_config('use_database', os.getenv("USE_DATABASE", "true").lower() == "true")
            
            # Load refresh interval from database
            raw_refresh_interval = secure_config.get_config('refresh_interval_minutes', os.getenv("REFRESH_INTERVAL_MINUTES"))
            try:
                REFRESH_INTERVAL_MINUTES = float(raw_refresh_interval) if raw_refresh_interval is not None else 60.0
                min_interval = 1.0  # Minimum interval in minutes
                if REFRESH_INTERVAL_MINUTES < min_interval:
                    logger.warning(f"REFRESH_INTERVAL_MINUTES ({REFRESH_INTERVAL_MINUTES}) is too small. Setting to minimum interval of {min_interval} minutes.")
                    REFRESH_INTERVAL_MINUTES = min_interval
            except (TypeError, ValueError):
                logger.warning(f"REFRESH_INTERVAL_MINUTES value '{raw_refresh_interval}' is not a valid number. Using default of 60 minutes.")
                REFRESH_INTERVAL_MINUTES = 60.0
            
            logger.info("Configuration loaded from secure database storage")
        except Exception as e:
            logger.warning(f"Could not load configuration from database, using environment variables: {e}")
            # Fallback to environment variables
            RD_ACCESS_TOKEN = os.getenv('RD_ACCESS_TOKEN')
            RD_REFRESH_TOKEN = os.getenv('RD_REFRESH_TOKEN')
            RD_CLIENT_ID = os.getenv('RD_CLIENT_ID')
            RD_CLIENT_SECRET = os.getenv('RD_CLIENT_SECRET')
            OVERSEERR_BASE = os.getenv('OVERSEERR_BASE')
            OVERSEERR_API_BASE_URL = OVERSEERR_BASE if OVERSEERR_BASE else None
            OVERSEERR_API_KEY = os.getenv('OVERSEERR_API_KEY')
            # OVERSEERR_API_KEY loaded from env
            TRAKT_API_KEY = os.getenv('TRAKT_API_KEY')
            HEADLESS_MODE = os.getenv("HEADLESS_MODE", "true").lower() == "true"
            ENABLE_AUTOMATIC_BACKGROUND_TASK = os.getenv("ENABLE_AUTOMATIC_BACKGROUND_TASK", "false").lower() == "true"
            ENABLE_SHOW_SUBSCRIPTION_TASK = os.getenv("ENABLE_SHOW_SUBSCRIPTION_TASK", "false").lower() == "true"
            TORRENT_FILTER_REGEX = os.getenv("TORRENT_FILTER_REGEX")
            
            # Load and validate size values
            raw_movie_size = os.getenv("MAX_MOVIE_SIZE")
            raw_episode_size = os.getenv("MAX_EPISODE_SIZE")
            MAX_MOVIE_SIZE, MAX_EPISODE_SIZE = validate_size_values(raw_movie_size, raw_episode_size)
            
            # Database configuration
            DB_HOST = os.getenv("DB_HOST", "localhost")
            DB_PORT = os.getenv("DB_PORT", "3306")
            DB_NAME = os.getenv("DB_NAME", "seerrbridge")
            DB_USER = os.getenv("DB_USER", "seerrbridge")
            DB_PASSWORD = os.getenv("DB_PASSWORD", "seerrbridge")
            USE_DATABASE = os.getenv("USE_DATABASE", "true").lower() == "true"
            
            # Load refresh interval from environment variable
            try:
                REFRESH_INTERVAL_MINUTES = float(os.getenv("REFRESH_INTERVAL_MINUTES", "60"))
                min_interval = 1.0  # Minimum interval in minutes
                if REFRESH_INTERVAL_MINUTES < min_interval:
                    logger.warning(f"REFRESH_INTERVAL_MINUTES ({REFRESH_INTERVAL_MINUTES}) is too small. Setting to minimum interval of {min_interval} minutes.")
                    REFRESH_INTERVAL_MINUTES = min_interval
            except (TypeError, ValueError):
                logger.warning(f"REFRESH_INTERVAL_MINUTES environment variable is not a valid number. Using default of 60 minutes.")
                REFRESH_INTERVAL_MINUTES = 60.0
    else:
        # Load from environment variables only
        RD_ACCESS_TOKEN = os.getenv('RD_ACCESS_TOKEN')
        RD_REFRESH_TOKEN = os.getenv('RD_REFRESH_TOKEN')
        RD_CLIENT_ID = os.getenv('RD_CLIENT_ID')
        RD_CLIENT_SECRET = os.getenv('RD_CLIENT_SECRET')
        OVERSEERR_BASE = os.getenv('OVERSEERR_BASE')
        OVERSEERR_API_BASE_URL = OVERSEERR_BASE if OVERSEERR_BASE else None
        OVERSEERR_API_KEY = os.getenv('OVERSEERR_API_KEY')
        # OVERSEERR_API_KEY loaded from env (no db)
        TRAKT_API_KEY = os.getenv('TRAKT_API_KEY')
        HEADLESS_MODE = os.getenv("HEADLESS_MODE", "true").lower() == "true"
        ENABLE_AUTOMATIC_BACKGROUND_TASK = os.getenv("ENABLE_AUTOMATIC_BACKGROUND_TASK", "false").lower() == "true"
        ENABLE_SHOW_SUBSCRIPTION_TASK = os.getenv("ENABLE_SHOW_SUBSCRIPTION_TASK", "false").lower() == "true"
        TORRENT_FILTER_REGEX = os.getenv("TORRENT_FILTER_REGEX")
        
        # Load and validate size values
        raw_movie_size = os.getenv("MAX_MOVIE_SIZE")
        raw_episode_size = os.getenv("MAX_EPISODE_SIZE")
        MAX_MOVIE_SIZE, MAX_EPISODE_SIZE = validate_size_values(raw_movie_size, raw_episode_size)
        
        # Database configuration
        DB_HOST = os.getenv("DB_HOST", "localhost")
        DB_PORT = os.getenv("DB_PORT", "3306")
        DB_NAME = os.getenv("DB_NAME", "seerrbridge")
        DB_USER = os.getenv("DB_USER", "seerrbridge")
        DB_PASSWORD = os.getenv("DB_PASSWORD", "seerrbridge")
        USE_DATABASE = os.getenv("USE_DATABASE", "true").lower() == "true"
        
        # Load refresh interval from environment variable
        try:
            REFRESH_INTERVAL_MINUTES = float(os.getenv("REFRESH_INTERVAL_MINUTES", "60"))
            min_interval = 1.0  # Minimum interval in minutes
            if REFRESH_INTERVAL_MINUTES < min_interval:
                logger.warning(f"REFRESH_INTERVAL_MINUTES ({REFRESH_INTERVAL_MINUTES}) is too small. Setting to minimum interval of {min_interval} minutes.")
                REFRESH_INTERVAL_MINUTES = min_interval
        except (TypeError, ValueError):
            logger.warning(f"REFRESH_INTERVAL_MINUTES environment variable is not a valid number. Using default of 60 minutes.")
            REFRESH_INTERVAL_MINUTES = 60.0
    
    # Validate required configuration
    if not OVERSEERR_API_BASE_URL:
        logger.error("OVERSEERR_API_BASE_URL environment variable is not set.")
        return False
    
    if not OVERSEERR_API_KEY:
        logger.error("OVERSEERR_API_KEY environment variable is not set.")
        return False
    
    if not TRAKT_API_KEY:
        logger.error("TRAKT_API_KEY environment variable is not set.")
        return False
    
    return True

# Initialize configuration
load_config()

def update_env_file():
    """Update the .env file with the new access token."""
    try:
        with open('.env', 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        with open('.env', 'w', encoding='utf-8') as file:
            for line in lines:
                if line.startswith('RD_ACCESS_TOKEN'):
                    file.write(f'RD_ACCESS_TOKEN={RD_ACCESS_TOKEN}\n')
                else:
                    file.write(line)
        return True
    except Exception as e:
        logger.error(f"Error updating .env file: {e}")
        return False 