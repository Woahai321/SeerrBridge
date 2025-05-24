"""
Configuration module for SeerrBridge
Loads environment variables and provides configuration values
"""
import os
import sys
import json
import time
from typing import Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv
from loguru import logger

# Configure loguru
logger.remove()  # Remove default handler
logger.add("logs/seerrbridge.log", rotation="500 MB", encoding='utf-8')  # Use utf-8 encoding for log file
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

# Add a global variable to track start time
START_TIME = datetime.now()

def load_config(override=False):
    """Load configuration from environment variables"""
    global RD_ACCESS_TOKEN, RD_REFRESH_TOKEN, RD_CLIENT_ID, RD_CLIENT_SECRET
    global OVERSEERR_BASE, OVERSEERR_API_BASE_URL, OVERSEERR_API_KEY, TRAKT_API_KEY
    global HEADLESS_MODE, ENABLE_AUTOMATIC_BACKGROUND_TASK, ENABLE_SHOW_SUBSCRIPTION_TASK
    global TORRENT_FILTER_REGEX, MAX_MOVIE_SIZE, MAX_EPISODE_SIZE, REFRESH_INTERVAL_MINUTES
    
    # Load environment variables
    load_dotenv(override=override)
    
    # Securely load credentials from environment variables
    RD_ACCESS_TOKEN = os.getenv('RD_ACCESS_TOKEN')
    RD_REFRESH_TOKEN = os.getenv('RD_REFRESH_TOKEN')
    RD_CLIENT_ID = os.getenv('RD_CLIENT_ID')
    RD_CLIENT_SECRET = os.getenv('RD_CLIENT_SECRET')
    OVERSEERR_BASE = os.getenv('OVERSEERR_BASE')
    OVERSEERR_API_BASE_URL = f"{OVERSEERR_BASE}/api/v1" if OVERSEERR_BASE else None
    OVERSEERR_API_KEY = os.getenv('OVERSEERR_API_KEY')
    TRAKT_API_KEY = os.getenv('TRAKT_API_KEY')
    HEADLESS_MODE = os.getenv("HEADLESS_MODE", "true").lower() == "true"
    ENABLE_AUTOMATIC_BACKGROUND_TASK = os.getenv("ENABLE_AUTOMATIC_BACKGROUND_TASK", "false").lower() == "true"
    ENABLE_SHOW_SUBSCRIPTION_TASK = os.getenv("ENABLE_SHOW_SUBSCRIPTION_TASK", "false").lower() == "true"
    TORRENT_FILTER_REGEX = os.getenv("TORRENT_FILTER_REGEX")
    MAX_MOVIE_SIZE = os.getenv("MAX_MOVIE_SIZE")
    MAX_EPISODE_SIZE = os.getenv("MAX_EPISODE_SIZE")
    
    # Confirm the interval is a valid number.
    try:
        REFRESH_INTERVAL_MINUTES = float(os.getenv("REFRESH_INTERVAL_MINUTES"))
        min_interval = 1.0  # Minimum interval in minutes
        if REFRESH_INTERVAL_MINUTES < min_interval:
            logger.warning(f"REFRESH_INTERVAL_MINUTES ({REFRESH_INTERVAL_MINUTES}) is too small. Setting to minimum interval of {min_interval} minutes.")
            REFRESH_INTERVAL_MINUTES = min_interval
    except (TypeError, ValueError):
        logger.error("REFRESH_INTERVAL_MINUTES environment variable is not a valid number. Using default of 60 minutes.")
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