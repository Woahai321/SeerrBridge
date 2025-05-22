# =============================================================================
# Soluify.com  |  Your #1 IT Problem Solver  |  {SeerrBridge v0.6}
# =============================================================================
#  __         _
# (_  _ |   .(_
# __)(_)||_||| \/
#              /
# © 2025
# -----------------------------------------------------------------------------
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, ValidationError, field_validator
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
import httpx
import asyncio
import json
import time
import os
import sys
import urllib.parse
import re
import inflect
import requests
import platform
import aiohttp
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException, TimeoutException
from asyncio import Queue
from datetime import datetime, timedelta, timezone
from deep_translator import GoogleTranslator
from fuzzywuzzy import fuzz
from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Configure loguru
logger.remove()  # Remove default handler
logger.add("seerrbridge.log", rotation="500 MB", encoding='utf-8')  # Use utf-8 encoding for log file
logger.add(sys.stdout, colorize=True)  # Ensure stdout can handle Unicode
logger.level("WARNING", color="<cyan>")

# Load environment variables
load_dotenv()

# Securely load credentials from environment variables
RD_ACCESS_TOKEN = os.getenv('RD_ACCESS_TOKEN')
RD_REFRESH_TOKEN = os.getenv('RD_REFRESH_TOKEN')
RD_CLIENT_ID = os.getenv('RD_CLIENT_ID')
RD_CLIENT_SECRET = os.getenv('RD_CLIENT_SECRET')
OVERSEERR_BASE = os.getenv('OVERSEERR_BASE')
OVERSEERR_API_BASE_URL = f"{OVERSEERR_BASE}/api/v1"
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
    exit(1)

if not OVERSEERR_API_BASE_URL:
    logger.error("OVERSEERR_API_BASE_URL environment variable is not set.")
    exit(1)

if not OVERSEERR_API_KEY:
    logger.error("OVERSEERR_API_KEY environment variable is not set.")
    exit(1)

if not TRAKT_API_KEY:
    logger.error("TRAKT_API_KEY environment variable is not set.")
    exit(1)

# Global driver variable to hold the Selenium WebDriver
driver = None

# Initialize a global queue with a maximum size of 500
request_queue = Queue(maxsize=500)
processing_task = None  # To track the current processing task

# Add a global variable to track start time
START_TIME = datetime.now()

class MediaInfo(BaseModel):
    media_type: str
    tmdbId: int
    tvdbId: Optional[int] = Field(default=None, alias='tvdbId')
    status: str
    status4k: str

    @field_validator('tvdbId', mode='before')
    @classmethod
    def empty_string_to_none(cls, value):
        if value == '':
            return None
        return value

class RequestInfo(BaseModel):
    request_id: str
    requestedBy_email: str
    requestedBy_username: str
    requestedBy_avatar: str
    requestedBy_settings_discordId: Optional[str] = None
    requestedBy_settings_telegramChatId: Optional[str] = None

class IssueInfo(BaseModel):
    issue_id: str
    issue_type: str
    issue_status: str
    reportedBy_email: str
    reportedBy_username: str
    reportedBy_avatar: str
    reportedBy_settings_discordId: str
    reportedBy_settings_telegramChatId: str

class CommentInfo(BaseModel):
    comment_message: str
    commentedBy_email: str
    commentedBy_username: str
    commentedBy_avatar: str
    commentedBy_settings_discordId: str
    commentedBy_settings_telegramChatId: str

class WebhookPayload(BaseModel):
    notification_type: str
    event: str
    subject: str
    message: Optional[str] = None
    image: Optional[str] = None
    media: Optional[MediaInfo] = None
    request: Optional[RequestInfo] = None
    issue: Optional[IssueInfo] = None
    comment: Optional[CommentInfo] = None
    extra: List[Dict[str, Any]] = []

def refresh_access_token():
    global RD_REFRESH_TOKEN, RD_ACCESS_TOKEN, driver

    TOKEN_URL = "https://api.real-debrid.com/oauth/v2/token"
    data = {
        'client_id': RD_CLIENT_ID,
        'client_secret': RD_CLIENT_SECRET,
        'code': RD_REFRESH_TOKEN,
        'grant_type': 'http://oauth.net/grant_type/device/1.0'
    }

    try:
        logger.info("Requesting a new access token with the refresh token.")
        response = requests.post(TOKEN_URL, data=data)
        response.encoding = 'utf-8'  # Explicitly set UTF-8 encoding for the response
        response_data = response.json()

        if response.status_code == 200:
            expiry_time = int((datetime.now() + timedelta(hours=24)).timestamp() * 1000)
            RD_ACCESS_TOKEN = json.dumps({
                "value": response_data['access_token'],
                "expiry": expiry_time
            }, ensure_ascii=False)  # Ensure non-ASCII characters are preserved
            logger.info("Successfully refreshed access token.")
            
            update_env_file()

            if driver:
                driver.execute_script(f"""
                    localStorage.setItem('rd:accessToken', '{RD_ACCESS_TOKEN}');
                """)
                logger.info("Updated Real-Debrid credentials in local storage after token refresh.")
                driver.refresh()
                logger.info("Refreshed the page after updating local storage with the new token.")
        else:
            logger.error(f"Failed to refresh access token: {response_data.get('error_description', 'Unknown error')}")
    except Exception as e:
        logger.error(f"Error refreshing access token: {e}")

def update_env_file():
    """Update the .env file with the new access token."""
    with open('.env', 'r', encoding='utf-8') as file:
        lines = file.readlines()

    with open('.env', 'w', encoding='utf-8') as file:
        for line in lines:
            if line.startswith('RD_ACCESS_TOKEN'):
                file.write(f'RD_ACCESS_TOKEN={RD_ACCESS_TOKEN}\n')
            else:
                file.write(line)

def check_and_refresh_access_token():
    """Check if the access token is expired or about to expire and refresh it if necessary."""
    global RD_ACCESS_TOKEN
    RD_ACCESS_TOKEN = None  # Reset before reloading
    load_dotenv(override=True)
    RD_ACCESS_TOKEN = os.getenv('RD_ACCESS_TOKEN')
    if RD_ACCESS_TOKEN:
        token_data = json.loads(RD_ACCESS_TOKEN)
        expiry_time = token_data['expiry']  # This is in milliseconds
        current_time = int(time.time() * 1000)  # Convert current time to milliseconds

        # Convert expiry time to a readable date format
        expiry_date = datetime.fromtimestamp(expiry_time / 1000).strftime('%Y-%m-%d %H:%M:%S')

        # Print the expiry date
        logger.info(f"Access token will expire on: {expiry_date}")

        # Check if the token is about to expire in the next 10 minutes (600000 milliseconds)
        if current_time >= expiry_time - 600000:  # 600000 milliseconds = 10 minutes
            logger.info("Access token is about to expire. Refreshing...")
            refresh_access_token()
        else:
            logger.info("Access token is still valid.")
    else:
        logger.error("Access token is not set. Requesting a new token.")
        refresh_access_token()

### Helper function to handle login
def login(driver):
    logger.info("Initiating login process.")

    try:
        # Check if the "Login with Real Debrid" button exists and is clickable
        login_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Login with Real Debrid')]"))
        )
        if login_button:
            login_button.click()
            logger.info("Clicked on 'Login with Real Debrid' button.")
        else:
            logger.info("'Login with Real Debrid' button was not found. Skipping this step.")

    except TimeoutException:
        # Handle case where the button was not found before the timeout
        logger.warning("'Login with Real Debrid' button not found or already bypassed. Proceeding...")
    
    except NoSuchElementException:
        # Handle case where the element is not in the DOM
        logger.warning("'Login with Real Debrid' button not present in the DOM. Proceeding...")

    except Exception as ex:
        # Log any other unexpected exception
        logger.error(f"An unexpected error occurred during login: {ex}")

scheduler = AsyncIOScheduler()

### Browser Initialization and Persistent Session
async def initialize_browser():
    global driver
    if driver is None:
        logger.info("Starting persistent browser session.")

        # Detect the current operating system
        current_os = platform.system().lower()  # Returns 'windows', 'linux', or 'darwin' (macOS)
        logger.info(f"Detected operating system: {current_os}")

        options = Options()

        ### Handle Docker/Linux-specific configurations
        if current_os == "linux" and os.getenv("RUNNING_IN_DOCKER", "false").lower() == "true":
            logger.info("Detected Linux environment inside Docker. Applying Linux-specific configurations.")

            # Explicitly set the Chrome binary location
            options.binary_location = os.getenv("CHROME_BIN", "/usr/bin/google-chrome")

            # Enable headless mode for Linux/Docker environments
            options.add_argument("--headless=new")  # Updated modern headless flag
            options.add_argument("--no-sandbox")  # Required for running as root in Docker
            options.add_argument("--disable-dev-shm-usage")  # Handle shared memory limitations
            options.add_argument("--disable-gpu")  # Disable GPU rendering for headless environments
            options.add_argument("--disable-setuid-sandbox")  # Bypass setuid sandbox

        ### Handle Windows-specific configurations
        elif current_os == "windows":
            logger.info("Detected Windows environment. Applying Windows-specific configurations.")

        if HEADLESS_MODE:
            options.add_argument("--headless=new")  # Modern headless mode for Chrome
        options.add_argument("--disable-gpu")  # Disable GPU for Docker compatibility
        options.add_argument("--no-sandbox")  # Required for running browser as root
        options.add_argument("--disable-dev-shm-usage")  # Disable shared memory usage restrictions
        options.add_argument("--disable-setuid-sandbox")  # Disable sandboxing for root permissions
        options.add_argument("--enable-logging")
        options.add_argument("--window-size=1920,1080")  # Set explicit window size to avoid rendering issues

        # WebDriver options to suppress infobars and disable automation detection
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36")

        # Log initialization method
        logger.info("Using WebDriver Manager for dynamic ChromeDriver downloads.")


        try:
            # Use webdriver-manager to install the appropriate ChromeDriver version
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

            # Suppress 'webdriver' detection
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                Object.defineProperty(navigator, 'webdriver', {
                  get: () => undefined
                })
                """
            })

            logger.info("Initialized Selenium WebDriver with WebDriver Manager.")
            # Navigate to an initial page to confirm browser works
            driver.get("https://debridmediamanager.com")
            logger.info("Navigated to Debrid Media Manager page.")
        except Exception as e:
            logger.error(f"Failed to initialize Selenium WebDriver: {e}")
            raise e

        # Inject Real-Debrid access token and other credentials into local storage
        driver.execute_script(f"""
            localStorage.setItem('rd:accessToken', '{RD_ACCESS_TOKEN}');
            localStorage.setItem('rd:clientId', '"{RD_CLIENT_ID}"');
            localStorage.setItem('rd:clientSecret', '"{RD_CLIENT_SECRET}"');
            localStorage.setItem('rd:refreshToken', '"{RD_REFRESH_TOKEN}"');          
        """)
        logger.info("Set Real-Debrid credentials in local storage.")

        # Refresh the page to apply the local storage values
        driver.refresh()
        login(driver)
        logger.info("Refreshed the page to apply local storage values.")
        # After refreshing, call the login function to click the login button
        # After successful login, click on "⚙️ Settings" to open the settings popup
        try:

            logger.info("Attempting to click the '⚙️ Settings' link.")
            settings_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[contains(text(),'⚙️ Settings')]"))
            )
            settings_link.click()
            logger.info("Clicked on '⚙️ Settings' link.")

            logger.info("Locating maximum movie size select element in '⚙️ Settings'.")
            max_movie_select_elem = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.ID, "dmm-movie-max-size"))
            )

            # Initialize Select class with the <select> WebElement
            select_obj = Select(max_movie_select_elem)

            # Select size specified in the .env file
            select_obj.select_by_value(MAX_MOVIE_SIZE)
            logger.info("Biggest Movie Size Selected as {} GB.".format(MAX_MOVIE_SIZE))

            # MAX EPISODE SIZE: Locate the maximum series size select element
            logger.info("Locating maximum series size select element in '⚙️ Settings'.")
            max_episode_select_elem = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.ID, "dmm-episode-max-size"))
            )

            # Initialize Select class with the <select> WebElement
            select_obj = Select(max_episode_select_elem)

            # Select size specified in the .env file
            select_obj.select_by_value(MAX_EPISODE_SIZE)
            logger.info("Biggest Episode Size Selected as {} GB.".format(MAX_EPISODE_SIZE))

            # Locate the "Default torrents filter" input box and insert the regex
            logger.info("Attempting to insert regex into 'Default torrents filter' box.")
            default_filter_input = WebDriverWait(driver, 10).until(

                EC.presence_of_element_located((By.ID, "dmm-default-torrents-filter"))
            )
            default_filter_input.clear()  # Clear any existing filter

            # Use the regex from .env
            default_filter_input.send_keys(TORRENT_FILTER_REGEX)

            logger.info(f"Inserted regex into 'Default torrents filter' input box: {TORRENT_FILTER_REGEX}")

            settings_link.click()
            logger.info("Closed 'Settings' to save settings.")

        except (TimeoutException, NoSuchElementException) as ex:
            logger.error(f"Error while interacting with the settings: {ex}")
            logger.error(f"Continuing without TORRENT_FILTER_REGEX")

        # Navigate to the library section
        logger.info("Navigating to the library section.")
        driver.get("https://debridmediamanager.com/library")

        # Wait for 2 seconds on the library page before further processing
        try:
            # Ensure the library page has loaded correctly (e.g., wait for a specific element on the library page)
            library_element = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.XPATH, "//div[@id='library-content']"))  # Adjust the XPath as necessary
            )
            logger.info("Library section loaded successfully.")
        except TimeoutException:
            logger.info("Library loading.")

        # Wait for at least 2 seconds on the library page
        logger.info("Waiting for 2 seconds on the library page.")
        time.sleep(2)
        logger.info("Completed waiting on the library page.")

async def shutdown_browser():
    global driver
    if driver:
        driver.quit()
        logger.warning("Selenium WebDriver closed.")
        driver = None

### Function to process requests from the queue
async def process_requests():
    while True:
        imdb_id, movie_title, media_type, extra_data = await request_queue.get()
        logger.info(f"Processing request for IMDb ID: {imdb_id}, Title: {movie_title}, Media Type: {media_type}")
        try:
            await asyncio.to_thread(search_on_debrid, imdb_id, movie_title, media_type, driver, extra_data)
        except Exception as ex:
            logger.critical(f"Error processing request for IMDb ID {imdb_id}: {ex}")
        finally:
            request_queue.task_done()

### Function to add requests to the queue
async def add_request_to_queue(imdb_id, movie_title, media_type, extra_data=None):
    if request_queue.full():
        logger.warning(f"Request queue is full. Cannot add request for IMDb ID: {imdb_id}")
        return False
    
    await request_queue.put((imdb_id, movie_title, media_type, extra_data))
    logger.info(f"Added request to queue for IMDb ID: {imdb_id}, Title: {movie_title}, Media Type: {media_type}")
    return True

### Helper function to extract year from a string
def extract_year(text, expected_year=None, ignore_resolution=False):
    """
    Extracts the correct year from a movie title.
    
    - Uses the explicitly provided expected_year (from TMDb or Trakt) if available.
    - Ensures the year is not mistakenly extracted from the movie's name (like '1984' in 'Wonder Woman 1984').
    """
    if expected_year:
        return expected_year  # Prioritize the known year from a reliable source

    # Remove common video resolutions that might interfere
    if ignore_resolution:
        text = re.sub(r'\b\d{3,4}p\b', '', text)

    # Extract years explicitly (avoid numbers inside movie titles)
    years = re.findall(r'\b(19\d{2}|20\d{2})\b', text)
    
    if years:
        # If multiple years are found, prefer the latest one
        return int(max(years))

    return None  # Return None if no valid year is found

# Initialize the inflect engine for number-word conversion
p = inflect.engine()

def translate_title(title, target_lang='en'):
    """
    Detects the language of the input title and translates it to the target language.
    """
    try:
        translator = GoogleTranslator(source='auto', target=target_lang)
        translated_title = translator.translate(title)
        logger.info(f"Translated '{title}' to '{translated_title}'")
        return translated_title
    except Exception as e:
        logger.error(f"Error translating title '{title}': {e}")
        return title  # Return the original title if translation fails

def clean_title(title, target_lang='en'):
    """
    Cleans the movie title by removing commas, hyphens, colons, semicolons, and apostrophes,
    translating it to the target language, and converting to lowercase.
    For TV shows with episode information, extracts just the main title before cleaning.
    """
    # Translate the title to the target language
    translated_title = translate_title(title, target_lang)
    
    # For TV shows, extract just the main title (before any S01E01 pattern)
    # This helps with matching by ignoring episode info and technical specs
    main_title = translated_title
    season_ep_match = re.search(r'S\d+E\d+', translated_title, re.IGNORECASE)
    if season_ep_match:
        main_title = translated_title[:season_ep_match.start()].strip()
    
    # Remove commas, hyphens, colons, semicolons, and apostrophes
    cleaned_title = re.sub(r"[,:;'-]", '', main_title)
    # Replace multiple spaces with a single dot
    cleaned_title = re.sub(r'\s+', '.', cleaned_title)
    # Convert to lowercase for comparison
    return cleaned_title.lower()

def normalize_title(title, target_lang='en'):
    """
    Normalizes the title by ensuring there are no unnecessary spaces or dots,
    translating it to the target language, and converting to lowercase.
    """
    # Replace ellipsis with three periods
    title = title.replace('…', '...')
    # Replace smart apostrophes with regular apostrophes
    title = title.replace("'", "'")
    
    # Translate the title to the target language
    translated_title = translate_title(title, target_lang)

    # Replace multiple spaces with a single space and dots with spaces
    normalized_title = re.sub(r'\s+', ' ', translated_title)
    normalized_title = normalized_title.replace('.', ' ')
    # Convert to lowercase
    return normalized_title.lower()

def replace_numbers_with_words(title):
    """
    Replaces digits with their word equivalents (e.g., "3" to "three").
    """
    return re.sub(r'\b\d+\b', lambda x: p.number_to_words(x.group()), title)

def replace_words_with_numbers(title):
    """
    Replaces number words with their digit equivalents (e.g., "three" to "3").
    """
    words_to_numbers = {
        "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
        "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
        "ten": "10", "eleven": "11", "twelve": "12", "thirteen": "13",
        "fourteen": "14", "fifteen": "15", "sixteen": "16", "seventeen": "17",
        "eighteen": "18", "nineteen": "19", "twenty": "20"
        # Add more mappings as needed
    }

    # Replace word numbers with digits
    for word, digit in words_to_numbers.items():
        title = re.sub(rf'\b{word}\b', digit, title, flags=re.IGNORECASE)
    return title

def click_show_more_results(driver, logger, max_attempts=3, wait_between=3, initial_timeout=5, subsequent_timeout=5):
    """
    Attempts to click the 'Show More Results' button multiple times with waits in between.
    
    Args:
        driver: The WebDriver instance
        logger: Logger instance for logging events
        max_attempts: Number of times to try clicking the button (default: 2)
        wait_between: Seconds to wait between clicks (default: 3)
        initial_timeout: Initial timeout in seconds for first click (default: 5)
        subsequent_timeout: Timeout in seconds for subsequent clicks (default: 5)
    """
    for attempt in range(max_attempts):
        try:
            # Adjust timeout based on whether it's the first attempt
            timeout = initial_timeout if attempt == 0 else subsequent_timeout
            
            # Locate and click the button
            show_more_button = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'haptic') and contains(text(), 'Show More Results')]"))
            )
            show_more_button.click()
            logger.info(f"Clicked 'Show More Results' button ({attempt + 1}{'st' if attempt == 0 else 'nd/th'} time).")
            
            # Wait between clicks if not the last attempt
            if attempt < max_attempts - 1:
                time.sleep(wait_between)
                
            time.sleep(2)    
        except TimeoutException:
            logger.info(f"No 'Show More Results' button found for {attempt + 1}{'st' if attempt == 0 else 'nd/th'} click after {timeout} seconds. Proceeding anyway.")
            break  # Exit the loop if we can't find the button
        except Exception as e:
            logger.warning(f"Error clicking 'Show More Results' button on attempt {attempt + 1}: {e}. Proceeding anyway.")
            break  # Exit on other errors too

# Function to fetch media requests from Overseerr
def get_overseerr_media_requests() -> list[dict]:
    url = f"{OVERSEERR_API_BASE_URL}/request?take=500&filter=approved&sort=added"
    headers = {
        "X-Api-Key": OVERSEERR_API_KEY
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        logger.error(f"Failed to fetch requests from Overseerr: {response.status_code}")
        return []
    
    data = response.json()
    logger.info(f"Fetched {len(data.get('results', []))} requests from Overseerr")
    
    if not data.get('results'):
        return []
    
    # Filter requests that are in processing state (status 3)
    processing_requests = [item for item in data['results'] if item['status'] == 2 and item['media']['status'] == 3]
    logger.info(f"Filtered {len(processing_requests)} processing requests")
    return processing_requests

# Trakt API rate limit: 1000 calls every 5 minutes
TRAKT_RATE_LIMIT = 1000
TRAKT_RATE_LIMIT_PERIOD = 5 * 60  # 5 minutes in seconds

trakt_api_calls = 0
last_reset_time = time.time()

def get_media_details_from_trakt(tmdb_id: str, media_type: str) -> Optional[dict]:
    global trakt_api_calls, last_reset_time

    current_time = time.time()
    if current_time - last_reset_time >= TRAKT_RATE_LIMIT_PERIOD:
        trakt_api_calls = 0
        last_reset_time = current_time

    if trakt_api_calls >= TRAKT_RATE_LIMIT:
        logger.warning("Trakt API rate limit reached. Waiting for the next period.")
        time.sleep(TRAKT_RATE_LIMIT_PERIOD - (current_time - last_reset_time))
        trakt_api_calls = 0
        last_reset_time = time.time()

    # Determine the type based on media_type
    trakt_type = 'show' if media_type == 'tv' else 'movie'
    url = f"https://api.trakt.tv/search/tmdb/{tmdb_id}?type={trakt_type}"
    headers = {
        "Content-type": "application/json",
        "trakt-api-key": TRAKT_API_KEY,
        "trakt-api-version": "2"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        trakt_api_calls += 1

        if response.status_code == 200:
            data = response.json()
            if data and isinstance(data, list) and data:
                media_info = data[0][trakt_type]
                return {
                    "title": media_info['title'],
                    "year": media_info['year'],
                    "imdb_id": media_info['ids']['imdb'],
                    "trakt_id": media_info['ids']['trakt']  # Add Trakt ID to the return dict
                }
            else:
                logger.error(f"{trakt_type.capitalize()} details for ID not found in Trakt API response.")
                return None
        else:
            logger.error(f"Trakt API request failed with status code {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching {trakt_type} details from Trakt API: {e}")
        return None

def get_season_details_from_trakt(trakt_show_id: str, season_number: int) -> Optional[dict]:
    """
    Fetch season details from Trakt API using a Trakt show ID and season number.
    
    Args:
        trakt_show_id (str): The Trakt ID of the show, obtained from get_media_details_from_trakt
        season_number (int): The season number to fetch details for
    
    Returns:
        Optional[dict]: Season details if successful, None if failed
    """
    global trakt_api_calls, last_reset_time

    # Validate input parameters
    if not trakt_show_id or not isinstance(trakt_show_id, str):
        logger.error(f"Invalid trakt_show_id provided: {trakt_show_id}")
        return None
    if not isinstance(season_number, int) or season_number < 0:
        logger.error(f"Invalid season_number provided: {season_number}")
        return None

    current_time = time.time()
    if current_time - last_reset_time >= TRAKT_RATE_LIMIT_PERIOD:
        trakt_api_calls = 0
        last_reset_time = current_time

    if trakt_api_calls >= TRAKT_RATE_LIMIT:
        logger.warning("Trakt API rate limit reached. Waiting for the next period.")
        time.sleep(TRAKT_RATE_LIMIT_PERIOD - (current_time - last_reset_time))
        trakt_api_calls = 0
        last_reset_time = time.time()

    url = f"https://api.trakt.tv/shows/{trakt_show_id}/seasons/{season_number}/info?extended=full"
    headers = {
        "Content-type": "application/json",
        "trakt-api-key": TRAKT_API_KEY,
        "trakt-api-version": "2"
    }

    try:
        logger.info(f"Fetching season details for show ID {trakt_show_id}, season {season_number}")
        response = requests.get(url, headers=headers, timeout=10)
        trakt_api_calls += 1

        if response.status_code == 200:
            data = response.json()
            logger.info(f"Successfully fetched season {season_number} details for show ID {trakt_show_id}")
            return data
        else:
            logger.error(f"Trakt API season request failed with status code {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching season details from Trakt API for show ID {trakt_show_id}, season {season_number}: {e}")
        return None

### Process the fetched messages (newest to oldest)
async def process_movie_requests():
    """
    Process Overseerr media requests. For TV shows, fetch season details and log discrepancies if found,
    then skip full processing, deferring to the check_show_subscriptions task. Movies are processed normally.
    """
    logger.info("Starting to process Overseerr media requests...")

    # Load episode_discrepancies.json to check for existing discrepancies
    DISCREPANCY_REPO_FILE = "episode_discrepancies.json"
    discrepant_shows = set()  # Set to store (show_title, season_number) tuples

    if os.path.exists(DISCREPANCY_REPO_FILE):
        try:
            with open(DISCREPANCY_REPO_FILE, 'r', encoding='utf-8') as f:
                repo_data = json.load(f)
            discrepancies = repo_data.get("discrepancies", [])
            for discrepancy in discrepancies:
                show_title = discrepancy.get("show_title")
                season_number = discrepancy.get("season_number")
                if show_title and season_number is not None:
                    discrepant_shows.add((show_title, season_number))
            logger.info(f"Loaded {len(discrepant_shows)} shows with discrepancies from episode_discrepancies.json")
        except Exception as e:
            logger.error(f"Failed to read episode_discrepancies.json: {e}")
            discrepant_shows = set()  # Proceed with an empty set if reading fails
    else:
        logger.info("No episode_discrepancies.json file found. Initializing it.")
        # Initialize the file if it doesn't exist
        with open(DISCREPANCY_REPO_FILE, 'w', encoding='utf-8') as f:
            json.dump({"discrepancies": []}, f)

    requests = get_overseerr_media_requests()
    if not requests:
        logger.info("No requests to process")
        return
    
    for request in requests:
        tmdb_id = request['media']['tmdbId']
        media_id = request['media']['id']
        media_type = request['media']['mediaType']  # Extract media_type from the request
        logger.info(f"Processing request with TMDB ID {tmdb_id} and media ID {media_id} (Media Type: {media_type})")

        # Extract requested seasons for TV shows
        extra_data = []
        requested_seasons = []
        if media_type == 'tv' and 'seasons' in request:
            requested_seasons = [f"Season {season['seasonNumber']}" for season in request['seasons']]
            extra_data.append({"name": "Requested Seasons", "value": ", ".join(requested_seasons)})
            logger.info(f"Requested seasons for TV show: {requested_seasons}")

        # Fetch media details from Trakt
        movie_details = get_media_details_from_trakt(tmdb_id, media_type)
        if not movie_details:
            logger.error(f"Failed to get media details for TMDB ID {tmdb_id}")
            continue
            
        imdb_id = movie_details['imdb_id']
        media_title = f"{movie_details['title']} ({movie_details['year']})"
        logger.info(f"Processing {media_type} request: {media_title}")

        # For TV shows, fetch season details and check for discrepancies
        has_discrepancy = False
        if media_type == 'tv' and requested_seasons:
            trakt_show_id = movie_details['trakt_id']
            for season in requested_seasons:
                season_number = int(season.split()[-1])  # Extract number from "Season X"
                
                # Check if this season is already in discrepancies
                if (media_title, season_number) in discrepant_shows:
                    logger.info(f"Season {season_number} of {media_title} already in discrepancies. Will be handled by check_show_subscriptions.")
                    has_discrepancy = True
                    continue
                
                # Fetch season details
                season_details = get_season_details_from_trakt(str(trakt_show_id), season_number)
                
                if season_details:
                    episode_count = season_details.get('episode_count', 0)
                    aired_episodes = season_details.get('aired_episodes', 0)
                    logger.info(f"Season {season_number} details: episode_count={episode_count}, aired_episodes={aired_episodes}")
                    
                    # Check for discrepancy between episode_count and aired_episodes
                    if episode_count != aired_episodes:
                        # Only check for the next episode if there's a discrepancy
                        has_aired, next_episode_details = check_next_episode_aired(
                            str(trakt_show_id), season_number, aired_episodes
                        )
                        if has_aired:
                            logger.info(f"Next episode (E{aired_episodes + 1:02d}) has aired for {media_title} Season {season_number}. Updating aired_episodes.")
                            season_details['aired_episodes'] = aired_episodes + 1
                        else:
                            logger.info(f"Next episode (E{aired_episodes + 1:02d}) has not aired for {media_title} Season {season_number}.")
                        
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        # Create list of all episodes marked as failed with "E01", "E02", etc.
                        failed_episodes = [
                            f"E{str(i).zfill(2)}"  # Format as E01, E02, etc.
                            for i in range(1, episode_count + 1)
                        ]
                        discrepancy_entry = {
                            "show_title": media_title,
                            "trakt_show_id": trakt_show_id,
                            "imdb_id": imdb_id,
                            "season_number": season_number,
                            "season_details": season_details,
                            "timestamp": timestamp,
                            "failed_episodes": failed_episodes  # Add all episodes as a list of E01, E02, etc.
                        }
                        
                        # Load current discrepancies
                        with open(DISCREPANCY_REPO_FILE, 'r', encoding='utf-8') as f:
                            repo_data = json.load(f)
                        
                        # Add the new discrepancy
                        repo_data["discrepancies"].append(discrepancy_entry)
                        with open(DISCREPANCY_REPO_FILE, 'w', encoding='utf-8') as f:
                            json.dump(repo_data, f, indent=2)
                        logger.info(f"Found episode count discrepancy for {media_title} Season {season_number}. Added to {DISCREPANCY_REPO_FILE} with all episodes marked as failed")
                        discrepant_shows.add((media_title, season_number))
                        has_discrepancy = True
                    else:
                        logger.info(f"No episode count discrepancy for {media_title} Season {season_number}. Skipping next episode check.")

        # If it's a TV show with any discrepancies (new or existing), skip full processing
        if media_type == 'tv' and has_discrepancy:
            logger.info(f"Skipping full processing for {media_title} due to discrepancies. Will be handled by the next check_show_subscriptions task.")
            continue

        # Process movies or TV shows without discrepancies normally
        try:
            confirmation_flag = await asyncio.to_thread(search_on_debrid, imdb_id, media_title, media_type, driver, extra_data)
            if confirmation_flag:
                if mark_completed(media_id, tmdb_id):
                    logger.info(f"Marked media {media_id} as completed in Overseerr")
                else:
                    logger.error(f"Failed to mark media {media_id} as completed in Overseerr")
            else:
                logger.info(f"Media {media_id} was not properly confirmed. Skipping marking as completed.")
        except Exception as ex:
            logger.critical(f"Error processing {media_type} request {media_title}: {ex}")

    logger.info("Finished processing all current requests. Waiting for new requests.")
    schedule_recheck_movie_requests()
  
def mark_completed(media_id: int, tmdb_id: int) -> bool:
    """Mark item as completed in overseerr"""
    url = f"{OVERSEERR_API_BASE_URL}/media/{media_id}/available"
    headers = {
        "X-Api-Key": OVERSEERR_API_KEY,
        "Content-Type": "application/json"
    }
    data = {"is4k": False}
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response_data = response.json()  # Parse the JSON response
        
        if response.status_code == 200:
            # Verify that the response contains the correct tmdb_id
            if response_data.get('tmdbId') == tmdb_id:
                logger.info(f"Marked media {media_id} as completed in overseerr. Response: {response_data}")
                return True
            else:
                logger.error(f"TMDB ID mismatch for media {media_id}. Expected {tmdb_id}, got {response_data.get('tmdbId')}")
                return False
        else:
            logger.error(f"Failed to mark media as completed in overseerr with id {media_id}: Status code {response.status_code}, Response: {response_data}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to mark media as completed in overseerr with id {media_id}: {str(e)}")
        return False
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON response for media {media_id}: {str(e)}")
        return False

def prioritize_buttons_in_box(result_box):
    """
    Prioritize buttons within a result box. Clicks the 'Instant RD' or 'DL with RD' button
    if available. Handles stale element references by retrying the operation once.

    Args:
        result_box (WebElement): The result box element.

    Returns:
        bool: True if a button was successfully clicked and handled, False otherwise.
    """
    try:
        # Attempt to locate the 'Instant RD' button
        instant_rd_button = result_box.find_element(By.XPATH, ".//button[contains(@class, 'bg-green-900/30')]")
        logger.info("Located 'Instant RD' button.")

        # Attempt to click the button and wait for a state change
        if attempt_button_click_with_state_check(instant_rd_button, result_box):
            return True

    except NoSuchElementException:
        logger.info("'Instant RD' button not found. Checking for 'DL with RD' button.")

    except StaleElementReferenceException:
        logger.warning("Stale element reference encountered for 'Instant RD' button. Retrying...")
        # Retry once by re-locating the button
        try:
            instant_rd_button = result_box.find_element(By.XPATH, ".//button[contains(@class, 'bg-green-900/30')]")
            if attempt_button_click_with_state_check(instant_rd_button, result_box):
                return True
        except Exception as e:
            logger.error(f"Retry failed for 'Instant RD' button due to: {e}")

    try:
        # If the 'Instant RD' button is not found, try to locate the 'DL with RD' button
        dl_with_rd_button = result_box.find_element(By.XPATH, ".//button[contains(text(), 'DL with RD')]")
        logger.info("Located 'DL with RD' button.")

        # Attempt to click the button and wait for a state change
        if attempt_button_click_with_state_check(dl_with_rd_button, result_box):
            return True

    except NoSuchElementException:
        logger.warning("Neither 'Instant RD' nor 'DL with RD' button found in this box.")

    except StaleElementReferenceException:
        logger.warning("Stale element reference encountered for 'DL with RD' button. Retrying...")
        # Retry once by re-locating the button
        try:
            dl_with_rd_button = result_box.find_element(By.XPATH, ".//button[contains(text(), 'DL with RD')]")
            if attempt_button_click_with_state_check(dl_with_rd_button, result_box):
                return True
        except Exception as e:
            logger.error(f"Retry failed for 'DL with RD' button due to: {e}")

    except Exception as e:
        logger.error(f"An unexpected error occurred while prioritizing buttons: {e}")

    return False

def attempt_button_click_with_state_check(button, result_box):
    """
    Attempts to click a button and waits for its state to change.

    Args:
        button (WebElement): The button element to click.
        result_box (WebElement): The parent result box (used for context).

    Returns:
        bool: True if the button's state changes, False otherwise.
    """
    try:
        # Get the initial state of the button
        initial_state = button.get_attribute("class")  # Or another attribute relevant to the state
        logger.info(f"Initial button state: {initial_state}")

        # Click the button
        button.click()
        logger.info("Clicked the button.")

        # Wait for a short period (max 2 seconds) to check for changes in the state
        WebDriverWait(result_box, 2).until(
            lambda driver: button.get_attribute("class") != initial_state
        )
        logger.info("Button state changed successfully after clicking.")
        return True  # Button was successfully clicked and handled

    except TimeoutException:
        logger.warning("No state change detected after clicking the button within 2 seconds.")

    except StaleElementReferenceException:
        logger.error("Stale element reference encountered while waiting for button state change.")

    return False

def parse_requested_seasons(extra_data):
    """
    Parse the requested seasons from the extra data in the JSON payload.
    """
    if not extra_data:
        return []

    for item in extra_data:
        if item['name'] == 'Requested Seasons':
            return item['value'].split(', ')
    return []

def normalize_season(season):
    """
    Normalize season strings to a consistent format (e.g., "Season 1", "Season 2").
    Handles formats like "S01", "S1", "Season 1", etc.
    """
    season = season.strip().lower()  # Normalize to lowercase
    if season.startswith('s') and season[1:].isdigit():  # Handle "S01", "S1", etc.
        season_number = int(season[1:])
        return f"Season {season_number}"
    elif season.startswith('season') and season[6:].strip().isdigit():  # Handle "Season 1", "Season 2", etc.
        season_number = int(season[6:].strip())
        return f"Season {season_number}"
    else:
        # Default to "Season X" if the format is unrecognized
        return f"Season {season}"

def match_complete_seasons(title, seasons):
    """
    Check if the title contains all requested seasons in a complete pack.
    """
    title = title.lower()
    for season in seasons:
        if f"complete {season.lower()}" not in title and f"complete {season.lower().replace('s', 'season ')}" not in title:
            return False
    return True

def match_single_season(title, season):
    """
    Check if the title contains the exact requested season.
    Handles formats like "Season 1", "S01", "S1", etc.
    """
    # Normalize the season string for comparison
    season = season.lower().strip()
    title = title.lower()

    # Extract the season number from the requested season
    if season.startswith("season"):
        season_number = season.replace("season", "").strip()
    elif season.startswith("s"):
        season_number = season.replace("s", "").strip()
    else:
        season_number = season

    # Ensure the season number is a valid integer
    try:
        season_number = int(season_number)
    except ValueError:
        logger.warning(f"Invalid season number format: {season}")
        return False

    # Match "Season X", "SX", or "S0X" in the title
    # Ensure the season number is exactly the one requested
    return (
        f"season {season_number}" in title or
        f"s{season_number}" in title or
        f"s{season_number:02d}" in title
    ) and not any(
        f"season {other_season}" in title or
        f"s{other_season}" in title or
        f"s{other_season:02d}" in title
        for other_season in range(1, 100) if other_season != season_number
    )

def extract_season(title):
    """
    Extract the season number from a title (e.g., 'naruto.s01.bdrip' → 1).
    """
    season_match = re.search(r"[sS](\d{1,2})", title)
    if season_match:
        return int(season_match.group(1))
    return None

def check_red_buttons(driver, movie_title, normalized_seasons, confirmed_seasons, is_tv_show, episode_id=None):
    confirmation_flag = False

    try:
        all_red_buttons_elements = driver.find_elements(By.XPATH, "//button[contains(@class, 'bg-red-900/30')]")
        red_buttons_elements = [button for button in all_red_buttons_elements if "Report" not in button.text]
        logger.info(f"Found {len(red_buttons_elements)} red button(s) (100% RD) without 'Report'. Verifying titles.")

        for i, red_button_element in enumerate(red_buttons_elements, start=1):
            if "Report" in red_button_element.text:
                continue
            logger.info(f"Checking red button {i}...")

            try:
                red_button_title_element = red_button_element.find_element(By.XPATH, ".//ancestor::div[contains(@class, 'border-2')]//h2")
                red_button_title_text = red_button_title_element.text.strip()

                # Use original title first, clean it for comparison
                red_button_title_cleaned = clean_title(red_button_title_text.split('(')[0].strip(), target_lang='en')
                movie_title_cleaned = clean_title(movie_title.split('(')[0].strip(), target_lang='en')

                # Extract year for comparison
                red_button_year = extract_year(red_button_title_text, ignore_resolution=True)
                expected_year = extract_year(movie_title)

                logger.info(f"Red button {i} title: {red_button_title_cleaned}, Expected movie title: {movie_title_cleaned}")

                # Fuzzy matching with a slightly lower threshold for robustness
                title_match_ratio = fuzz.partial_ratio(red_button_title_cleaned.lower(), movie_title_cleaned.lower())
                title_match_threshold = 65  # Lowered from 69 to allow more flexibility

                title_matched = title_match_ratio >= title_match_threshold

                # Year comparison (skip for TV shows or if missing)
                year_matched = True
                if not is_tv_show and red_button_year and expected_year:
                    year_matched = abs(red_button_year - expected_year) <= 1

                # Episode and season matching (for TV shows)
                season_matched = False
                episode_matched = True
                if is_tv_show and normalized_seasons:
                    found_season = extract_season(red_button_title_text)
                    found_season_normalized = f"Season {found_season}" if found_season else None
                    season_matched = found_season_normalized in normalized_seasons if found_season_normalized else False
                    if episode_id:
                        episode_matched = episode_id.lower() in red_button_title_text.lower()

                if title_matched and year_matched and (not is_tv_show or (season_matched and episode_matched)):
                    logger.info(f"Found a match on red button {i} - {red_button_title_cleaned}. Marking as confirmed.")
                    confirmation_flag = True
                    if is_tv_show and found_season_normalized and not episode_id:
                        confirmed_seasons.add(found_season_normalized)
                    return confirmation_flag, confirmed_seasons  # Early exit on match
                else:
                    logger.warning(f"No match for red button {i}: Title - {red_button_title_cleaned}, Year - {red_button_year}, Episode - {episode_id}. Moving to next red button.")

            except NoSuchElementException as e:
                logger.warning(f"Could not find title associated with red button {i}: {e}")
                continue

    except NoSuchElementException:
        logger.info("No red buttons (100% RD) detected. Proceeding with optional fallback.")

    return confirmation_flag, confirmed_seasons

def search_individual_episodes(imdb_id, movie_title, season_number, season_details, driver):
    """
    Search for and process individual episodes for a TV show season with a discrepancy.
    Logs failed episodes in episode_discrepancies.json for later reprocessing.
    
    Args:
        imdb_id (str): IMDb ID of the show
        movie_title (str): Title of the show with year (e.g., "Daredevil: Born Again (2025)")
        season_number (int): Season number with discrepancy
        season_details (dict): Season details from Trakt, including 'aired_episodes'
        driver (WebDriver): Selenium WebDriver instance
    
    Returns:
        bool: True if all episodes were successfully processed or already cached, False otherwise
    """
    logger.info(f"Starting individual episode search for {movie_title} Season {season_number}")
    
    aired_episodes = season_details.get('aired_episodes', 0)
    if not aired_episodes:
        logger.error(f"No aired episodes found in season details for {movie_title} Season {season_number}")
        return False

    logger.info(f"Processing {aired_episodes} aired episodes for Season {season_number}")
    
    all_confirmed = True  # Track if all episodes are successfully processed or already cached
    failed_episodes = []  # Track episodes that fail to process
    
    # Define the repository file name
    DISCREPANCY_REPO_FILE = "episode_discrepancies.json"
    
    # Read the discrepancies file to find the matching entry
    try:
        with open(DISCREPANCY_REPO_FILE, 'r', encoding='utf-8') as f:
            repo_data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to read episode_discrepancies.json: {e}")
        return False

    discrepancies = repo_data.get("discrepancies", [])
    discrepancy_entry = None
    for entry in discrepancies:
        if entry.get("show_title") == movie_title and entry.get("season_number") == season_number:
            discrepancy_entry = entry
            break
    
    if not discrepancy_entry:
        logger.error(f"No discrepancy entry found for {movie_title} Season {season_number} in episode_discrepancies.json")
        return False

    # Navigate to the show page with season
    url = f"https://debridmediamanager.com/show/{imdb_id}/{season_number}"
    driver.get(url)
    logger.info(f"Navigated to show page for Season {season_number}: {url}")
    
    # Wait for the page to load (ensure the status element is present)
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//div[@role='status' and contains(@aria-live, 'polite')]"))
        )
        logger.info("Page load confirmed via status element.")
    except TimeoutException:
        logger.warning("Timeout waiting for page load status. Proceeding anyway.")
        
    # Set up parameters for check_red_buttons
    normalized_seasons = [f"Season {season_number}"]
    confirmed_seasons = set()
    is_tv_show = True
    
    for episode_num in range(1, aired_episodes + 1):
        episode_id = f"E{episode_num:02d}"  # Format as "E01", "E02", etc.
        logger.info(f"Searching for {movie_title} Season {season_number} {episode_id}")
        
        # Clear and update the filter box with episode-specific filter
        try:
            filter_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "query"))
            )
            filter_input.clear()
            episode_filter = f"S{season_number:02d}{episode_id}"  # e.g., "S01E01"
            full_filter = f"{TORRENT_FILTER_REGEX} {episode_filter}"
            filter_input.send_keys(full_filter)
            logger.info(f"Applied filter: {full_filter}")
            
            try:
                click_show_more_results(driver, logger)
            except TimeoutException:
                logger.warning("Timed out while trying to click 'Show More Results'")
            except Exception as e:
                logger.error(f"Unexpected error in click_show_more_results: {e}")

            
            # Wait for results to update after applying the filter
            time.sleep(2)  # Adjust this delay if needed based on page response time
            
            # First pass: Check for existing RD (100%) using check_red_buttons
            confirmation_flag, confirmed_seasons = check_red_buttons(
                driver, movie_title, normalized_seasons, confirmed_seasons, is_tv_show, episode_id=episode_id
            )
            
            if confirmation_flag:
                logger.success(f"{episode_id} already cached at RD (100%). Skipping further processing.")
                logger.info(f"{episode_id} already confirmed as cached. Moving to next episode.")
                continue
            
            # Second pass: Process uncached episodes
            try:
                result_boxes = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'border-black')]"))
                )
                episode_confirmed = False
                
                for i, result_box in enumerate(result_boxes, start=1):
                    try:
                        title_element = result_box.find_element(By.XPATH, ".//h2")
                        title_text = title_element.text.strip()
                        logger.info(f"Box {i} title (second pass): {title_text}")
                        
                        # Check if the title matches the episode
                        title_clean = clean_title(title_text, 'en')
                        movie_clean = clean_title(movie_title, 'en')
                        match_ratio = fuzz.partial_ratio(title_clean, movie_clean)
                        logger.info(f"Match ratio: {match_ratio} for '{title_clean}' vs '{movie_clean}'")
                        
                        if episode_id.lower() in title_text.lower() and match_ratio >= 50:
                            logger.info(f"Found match for {episode_id} in box {i}: {title_text}")
                            
                            if prioritize_buttons_in_box(result_box):
                                logger.info(f"Successfully handled {episode_id} in box {i}")
                                episode_confirmed = True
                                
                                # Verify RD status after clicking
                                try:
                                    rd_button = WebDriverWait(driver, 10).until(
                                        EC.presence_of_element_located((By.XPATH, ".//button[contains(text(), 'RD (')]"))
                                    )
                                    rd_button_text = rd_button.text
                                    if "RD (100%)" in rd_button_text:
                                        logger.success(f"RD (100%) confirmed for {episode_id}. Episode fully processed.")
                                        episode_confirmed = True
                                        break  # Exit the loop once RD (100%) is confirmed
                                    elif "RD (0%)" in rd_button_text:
                                        logger.warning(f"RD (0%) detected for {episode_id}. Undoing and skipping.")
                                        rd_button.click()  # Undo the click
                                        episode_confirmed = False
                                        continue
                                except TimeoutException:
                                    logger.warning(f"Timeout waiting for RD status for {episode_id}")
                                    continue
                            else:
                                logger.warning(f"Failed to handle buttons for {episode_id} in box {i}")
                    
                    except NoSuchElementException:
                        logger.warning(f"No title found in box {i} for {episode_id}")
                
                if not episode_confirmed:
                    logger.error(f"Failed to confirm {episode_id} for {movie_title} Season {season_number}")
                    failed_episodes.append(episode_id)
                    all_confirmed = False
                else:
                    logger.info(f"{episode_id} confirmed and processed. Moving to next episode.")
                
            except TimeoutException:
                logger.warning(f"No result boxes found for {episode_id}")
                failed_episodes.append(episode_id)
                all_confirmed = False
        
        except TimeoutException:
            logger.error(f"Filter input with ID 'query' not found for {episode_id}")
            failed_episodes.append(episode_id)
            all_confirmed = False
    
    # Reset the filter to the default after processing
    try:
        filter_input = driver.find_element(By.ID, "query")
        filter_input.clear()
        filter_input.send_keys(TORRENT_FILTER_REGEX)
        logger.info(f"Reset filter to default: {TORRENT_FILTER_REGEX}")
    except NoSuchElementException:
        logger.warning("Could not reset filter to default using ID 'query'")
    
    # Update the discrepancy entry with failed episodes
    if failed_episodes:
        discrepancy_entry["failed_episodes"] = failed_episodes
        logger.warning(f"Failed to process episodes for {movie_title} Season {season_number}: {failed_episodes}")
    else:
        discrepancy_entry["failed_episodes"] = []  # Clear failed_episodes if all succeeded
        logger.success(f"Successfully processed all episodes for {movie_title} Season {season_number}")

    # Write the updated discrepancies back to the file
    try:
        with open(DISCREPANCY_REPO_FILE, 'w', encoding='utf-8') as f:
            json.dump(repo_data, f, indent=2)
        logger.info("Updated episode_discrepancies.json with failed episodes.")
    except Exception as e:
        logger.error(f"Failed to write updated episode_discrepancies.json: {e}")

    logger.info(f"Completed processing {aired_episodes} episodes for {movie_title} Season {season_number}")
    return all_confirmed

### Search Function to Reuse Browser
def search_on_debrid(imdb_id, movie_title, media_type, driver, extra_data=None):
    logger.info(f"Starting Selenium automation for IMDb ID: {imdb_id}, Media Type: {media_type}")
    if driver is None:
        logger.error("Selenium WebDriver is not initialized. Cannot proceed.")
        return False
    # Extract requested seasons from the extra data
    requested_seasons = parse_requested_seasons(extra_data) if extra_data else []
    normalized_seasons = [normalize_season(season) for season in requested_seasons]

    # Determine if the media is a TV show
    is_tv_show = any(item['name'] == 'Requested Seasons' for item in extra_data) if extra_data else False
    logger.info(f"Media type: {'TV Show' if is_tv_show else 'Movie'}")

    try:
        # Navigate directly using IMDb ID
        if media_type == 'movie':
            url = f"https://debridmediamanager.com/movie/{imdb_id}"
            driver.get(url)
            logger.info(f"Navigated to movie page: {url}")
        elif media_type == 'tv':
            url = f"https://debridmediamanager.com/show/{imdb_id}"
            driver.get(url)
            logger.info(f"Navigated to show page: {url}")
        else:
            logger.error(f"Unsupported media type: {media_type}")
            return False

# Check for discrepancies if it's a TV show
        DISCREPANCY_REPO_FILE = "episode_discrepancies.json"
        discrepant_seasons = {}
        if is_tv_show and normalized_seasons and os.path.exists(DISCREPANCY_REPO_FILE):
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    with open(DISCREPANCY_REPO_FILE, 'r', encoding='utf-8') as f:
                        repo_data = json.load(f)
                    break
                except json.JSONDecodeError:
                    if attempt < max_retries - 1:
                        time.sleep(0.1)  # Wait 100ms before retrying
                        continue
                    logger.error("Failed to read episode_discrepancies.json after retries")
                    repo_data = {"discrepancies": []}
            for season in normalized_seasons:
                season_number = int(season.split()[-1])
                discrepancy = next(
                    (entry for entry in repo_data["discrepancies"]
                     if entry["show_title"] == movie_title and entry["season_number"] == season_number),
                    None
                )
                if discrepancy:
                    discrepant_seasons[season] = discrepancy

        confirmation_flag = False  # Initialize the confirmation flag

        # Wait for the movie's details page to load by listening for the status message
        try:
            # Step 1: Check for Status Message
            try:
                no_results_element = WebDriverWait(driver, 2).until(
                    EC.text_to_be_present_in_element(
                        (By.XPATH, "//div[@role='status' and contains(@aria-live, 'polite')]"),
                        "No results found"
                    )
                )
                logger.warning("'No results found' message detected. Skipping further checks.")
                logger.error(f"Could not find {movie_title}, since no results were found.")
                return  # Skip further checks if "No results found" is detected
            except TimeoutException:
                logger.warning("'No results found' message not detected. Proceeding to check for available torrents.")

            try:
                status_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//div[@role='status' and contains(@aria-live, 'polite') and contains(text(), 'available torrents in RD')]")
                    )
                )
                status_text = status_element.text
                logger.info(f"Status message: {status_text}")

                # Extract the number of available torrents from the status message (look for the number)
                torrents_match = re.search(r"Found (\d+) available torrents in RD", status_text)
                if torrents_match:
                    torrents_count = int(torrents_match.group(1))
                    logger.info(f"Found {torrents_count} available torrents in RD.")
                else:
                    logger.warning("Could not find the expected 'Found X available torrents in RD' message. Proceeding to check for 'Checking RD availability...'.")
            except TimeoutException:
                logger.warning("Timeout waiting for the RD status message. Proceeding with the next steps.")
                status_text = None  # No status message found, but continue

            logger.info("Waiting for 'Checking RD availability...' to appear.")
            
            # Determine if the current URL is for a TV show
            current_url = driver.current_url
            is_tv_show = '/show/' in current_url
            logger.info(f"is_tv_show: {is_tv_show}")
            # Initialize a set to track confirmed seasons
            confirmed_seasons = set()
            
            # Step 2: Check if any red buttons (RD 100%) exist and verify the title for each
            confirmation_flag, confirmed_seasons = check_red_buttons(driver, movie_title, normalized_seasons, confirmed_seasons, is_tv_show)

            # Step 3: Wait for the "Checking RD availability..." message to disappear
            try:
                WebDriverWait(driver, 15).until_not(
                    EC.text_to_be_present_in_element(
                        (By.XPATH, "//div[@role='status' and contains(@aria-live, 'polite')]"),
                        "Checking RD availability"
                    )
                )
                logger.info("'Checking RD availability...' has disappeared. Now waiting for RD results.")
            except TimeoutException:
                logger.warning("'Checking RD availability...' did not disappear within 15 seconds. Proceeding to the next steps.")

            # Step 4: Wait for the "Found X available torrents in RD" message
            try:
                status_element = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//div[@role='status' and contains(@aria-live, 'polite') and contains(text(), 'available torrents in RD')]")
                    )
                )

                status_text = status_element.text
                logger.info(f"Status message: {status_text}")
            except TimeoutException:
                logger.warning("Timeout waiting for the RD status message. Proceeding with the next steps.")
                status_text = None  # No status message found, but continue

            # Step 5: Extract the number of available torrents from the status message (look for the number)
            if status_text:
                torrents_match = re.search(r"Found (\d+) available torrents in RD", status_text)

                if torrents_match:
                    torrents_count = int(torrents_match.group(1))
                    logger.info(f"Found {torrents_count} available torrents in RD.")
                else:
                    logger.warning("Could not find the expected 'Found X available torrents in RD' message. Proceeding to check for Instant RD.")
                    torrents_count = 0  # Default to 0 torrents if no match found
            else:
                logger.warning("No status text available. Proceeding to check for Instant RD.")
                torrents_count = 0  # Default to 0 torrents if no status text

            # Step 6: If the status says "0 torrents", check if there's still an Instant RD button
            if torrents_count == 0:
                logger.warning("No torrents found in RD according to status, but checking for Instant RD buttons.")
            else:
                logger.info(f"{torrents_count} torrents found in RD. Proceeding with RD checks.")
            # Initialize a set to track confirmed seasons
            confirmed_seasons = set()
            # Step 7: Check if any red button (RD 100%) exists again before continuing
            confirmation_flag, confirmed_seasons = check_red_buttons(driver, movie_title, normalized_seasons, confirmed_seasons, is_tv_show)

            # If a red button is confirmed, skip further processing
            if confirmation_flag:
                logger.info("Red button confirmed. Checking if Movie or TV Show...")
            # If a red button is confirmed and it's not a TV show, skip further processing
            if confirmation_flag and not is_tv_show:
                logger.success(f"Red button confirmed for Movie {movie_title}. Skipping further processing.")
                return confirmation_flag

            # After clicking the matched movie title, we now check the popup boxes for Instant RD buttons
            # Step 8: Check the result boxes with the specified class for "Instant RD"
            try:
                if is_tv_show and normalized_seasons:
                    logger.info(f"Processing TV show seasons for: {movie_title}")

                    # Phase 1: Process non-discrepant seasons with original logic
                    non_discrepant_seasons = [s for s in normalized_seasons if s not in discrepant_seasons]
                    if non_discrepant_seasons:
                        logger.info(f"Processing non-discrepant seasons: {non_discrepant_seasons}")
                        # Process each requested season sequentially
                        for season in non_discrepant_seasons:
                            # Skip this season if it has already been confirmed
                            if season in confirmed_seasons:
                                logger.success(f"Season {season} has already been confirmed. Skipping.")
                                continue  # Skip this season

                            # Extract the season number (e.g., "6" from "Season 6")
                            season_number = season.split()[-1]  # Assumes season is in the format "Season X"

                            # Get the base URL (root URL without the season number)
                            base_url = driver.current_url.split("/")[:-1]  # Split the URL and remove the last part (season number)
                            base_url = "/".join(base_url)  # Reconstruct the base URL

                            # Construct the new URL by appending the season number
                            season_url = f"{base_url}/{season_number}"

                            # Navigate to the new URL
                            driver.get(season_url)
                            time.sleep(2)  # Wait for the page to load
                            logger.info(f"Navigated to season {season} URL: {season_url}")

                            # Perform red button checks for the current season
                            confirmation_flag, confirmed_seasons = check_red_buttons(driver, movie_title, normalized_seasons, confirmed_seasons, is_tv_show)
                            # If a red button is confirmed, skip further processing for this season
                            if confirmation_flag and is_tv_show:
                                logger.success(f"Red button confirmed for {season}. Skipping further processing for this season.")
                                continue
                                
                            try:
                                click_show_more_results(driver, logger)
                            except TimeoutException:
                                logger.warning("Timed out while trying to click 'Show More Results'")
                            except Exception as e:
                                logger.error(f"Unexpected error in click_show_more_results: {e}")
                                continue  
                                
                            # Re-locate the result boxes after navigating to the new URL
                            try:
                                result_boxes = WebDriverWait(driver, 10).until(
                                    EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'border-black')]"))
                                )
                            except TimeoutException:
                                logger.warning(f"No result boxes found for season {season}. Skipping.")
                                continue
                                
                            # Now process the result boxes for the current season
                            for i, result_box in enumerate(result_boxes, start=1):
                                try:
                                    # Extract the title from the result box
                                    title_element = result_box.find_element(By.XPATH, ".//h2")
                                    title_text = title_element.text.strip()
                                    logger.info(f"Box {i} title: {title_text}")
                                    # Check if the result box contains "with extras" and skip if it does
                                    try:
                                        extras_element = WebDriverWait(result_box, 2).until(
                                            EC.presence_of_element_located((By.XPATH, ".//span[contains(., 'Single')]"))
                                        )
                                        logger.info(f"Box {i} contains 'Single'. Skipping.")
                                        continue
                                    except TimeoutException:
                                        logger.info(f"Box {i} does not contain 'Single'. Proceeding.")
                                    # Clean and normalize the TV show title for comparison
                                    tv_show_title_cleaned = clean_title(movie_title.split('(')[0].strip(), target_lang='en')
                                    title_text_cleaned = clean_title(title_text.split('(')[0].strip(), target_lang='en')

                                    # Normalize the titles for comparison
                                    tv_show_title_normalized = normalize_title(tv_show_title_cleaned, target_lang='en')
                                    title_text_normalized = normalize_title(title_text_cleaned, target_lang='en')

                                    # Convert digits to words for comparison
                                    tv_show_title_cleaned_word = replace_numbers_with_words(tv_show_title_cleaned)
                                    title_text_cleaned_word = replace_numbers_with_words(title_text_cleaned)

                                    # Convert words to digits for comparison
                                    tv_show_title_cleaned_digit = replace_words_with_numbers(tv_show_title_cleaned)
                                    title_text_cleaned_digit = replace_words_with_numbers(title_text_cleaned)

                                    # Log all variations for debugging
                                    logger.info(f"Cleaned TV show title: {tv_show_title_cleaned}, Cleaned box title: {title_text_cleaned}")
                                    logger.info(f"TV show title (digits to words): {tv_show_title_cleaned_word}, Box title (digits to words): {title_text_cleaned_word}")
                                    logger.info(f"TV show title (words to digits): {tv_show_title_cleaned_digit}, Box title (words to digits): {title_text_cleaned_digit}")

                                    # Compare the title in all variations
                                    if not (
                                        fuzz.partial_ratio(title_text_cleaned.lower(), tv_show_title_cleaned.lower()) >= 75 or
                                        fuzz.partial_ratio(title_text_cleaned_word.lower(), tv_show_title_cleaned_word.lower()) >= 75 or
                                        fuzz.partial_ratio(title_text_cleaned_digit.lower(), tv_show_title_cleaned_digit.lower()) >= 75
                                    ):
                                        logger.warning(f"Title mismatch for box {i}: {title_text_cleaned} or {title_text_normalized} (Expected: {tv_show_title_cleaned} or {tv_show_title_normalized}). Skipping.")
                                        continue  # Skip this box if none of the variations match

                                    # Check for complete season packs first
                                    if match_complete_seasons(title_text, [season]):
                                        logger.info(f"Found complete season pack for {season} in box {i}: {title_text}")
                                        if prioritize_buttons_in_box(result_box):
                                            logger.info(f"Successfully handled complete season pack in box {i}.")
                                            confirmation_flag = True

                                            # Add the confirmed season to the set
                                            confirmed_seasons.add(season)
                                            logger.info(f"Added {season} to confirmed seasons: {confirmed_seasons}")

                                            # Perform RD status checks after clicking the button
                                            try:
                                                rd_button = WebDriverWait(driver, 10).until(
                                                    EC.presence_of_element_located((By.XPATH, ".//button[contains(text(), 'RD (')]"))
                                                )
                                                rd_button_text = rd_button.text
                                                logger.info(f"RD button text after clicking: {rd_button_text}")

                                                # If the button is now "RD (0%)", undo the click and retry with the next box
                                                if "RD (0%)" in rd_button_text:
                                                    logger.warning(f"RD (0%) button detected after clicking Instant RD in box {i} {title_text}. Undoing the click and moving to the next box.")
                                                    rd_button.click()  # Undo the click by clicking the RD (0%) button
                                                    confirmation_flag = False  # Reset the flag
                                                    continue  # Move to the next box

                                                # If it's "RD (100%)", we are done with this entry
                                                if "RD (100%)" in rd_button_text:
                                                    logger.success(f"RD (100%) button detected. {i} {title_text}. This entry is complete.")
                                                    break  # Move to the next season

                                            except TimeoutException:
                                                logger.warning(f"Timeout waiting for RD button status change in box {i}.")
                                                continue  # Move to the next box if a timeout occurs

                                    # If no complete pack, check for individual seasons
                                    if match_single_season(title_text, season):
                                        logger.info(f"Found matching season {season} in box {i}: {title_text}")
                                        if prioritize_buttons_in_box(result_box):
                                            logger.info(f"Successfully handled season {season} in box {i}.")
                                            confirmation_flag = True

                                            # Add the confirmed season to the set
                                            confirmed_seasons.add(season)
                                            logger.info(f"Added {season} to confirmed seasons: {confirmed_seasons}")

                                            # Perform RD status checks after clicking the button
                                            try:
                                                rd_button = WebDriverWait(driver, 10).until(
                                                    EC.presence_of_element_located((By.XPATH, ".//button[contains(text(), 'RD (')]"))
                                                )
                                                rd_button_text = rd_button.text
                                                logger.info(f"RD button text after clicking: {rd_button_text}")

                                                # If the button is now "RD (0%)", undo the click and retry with the next box
                                                if "RD (0%)" in rd_button_text:
                                                    logger.warning(f"RD (0%) button detected after clicking Instant RD in box {i} {title_text}. Undoing the click and moving to the next box.")
                                                    rd_button.click()  # Undo the click by clicking the RD (0%) button
                                                    confirmation_flag = False  # Reset the flag
                                                    continue  # Move to the next box

                                                # If it's "RD (100%)", we are done with this entry
                                                if "RD (100%)" in rd_button_text:
                                                    logger.success(f"RD (100%) button detected. {i} {title_text}. This entry is complete.")
                                                    break  # Move to the next season

                                            except TimeoutException:
                                                logger.warning(f"Timeout waiting for RD button status change in box {i}.")
                                                continue  # Move to the next box if a timeout occurs

                                except NoSuchElementException as e:
                                    logger.warning(f"Could not find 'Instant RD' button in box {i}: {e}")
                                except TimeoutException as e:
                                    logger.warning(f"Timeout when processing box {i}: {e}")

                            # Log completion of the current season
                            logger.success(f"Completed processing for {season}.")

                    # Phase 2: Process discrepant seasons
                    if discrepant_seasons:
                        logger.info(f"Processing discrepant seasons: {list(discrepant_seasons.keys())}")
                        for season, discrepancy in discrepant_seasons.items():
                            season_number = discrepancy["season_number"]
                            logger.info(f"Discrepancy detected for {movie_title} {season}. Switching to individual episode search.")
                            confirmation_flag = search_individual_episodes(
                                imdb_id, movie_title, season_number, discrepancy["season_details"], driver
                            )
                            if confirmation_flag:
                                logger.success(f"Successfully processed individual episodes for {movie_title} {season}")
                            else:
                                logger.warning(f"Failed to process individual episodes for {movie_title} {season}")

                    # Log completion of all requested seasons
                    logger.success(f"Completed processing for all requested seasons: {normalized_seasons}.")

                else:
                    # Handle movies or TV shows without specific seasons
                    # Re-locate the result boxes after navigating to the new URL
                    try:
                        result_boxes = WebDriverWait(driver, 10).until(
                            EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'border-black')]"))
                        )
                    except TimeoutException:
                        logger.warning(f"No result boxes found. Skipping.")

                    for i, result_box in enumerate(result_boxes, start=1):
                        try:
                            # Extract the title from the result box
                            title_element = result_box.find_element(By.XPATH, ".//h2")
                            title_text = title_element.text.strip()
                            logger.info(f"Box {i} title: {title_text}")

                            # Check if the result box contains "with extras" and skip if it does
                            try:
                                extras_element = WebDriverWait(result_box, 2).until(
                                    EC.presence_of_element_located((By.XPATH, ".//span[contains(., 'With extras')]"))
                                )
                                logger.info(f"Box {i} contains 'With extras'. Skipping.")
                                continue
                            except TimeoutException:
                                logger.info(f"Box {i} does not contain 'With extras'. Proceeding.")
                            # Clean both the movie title and the box title for comparison
                            movie_title_cleaned = clean_title(movie_title.split('(')[0].strip(), target_lang='en')
                            title_text_cleaned = clean_title(title_text.split('(')[0].strip(), target_lang='en')

                            movie_title_normalized = normalize_title(movie_title.split('(')[0].strip(), target_lang='en')
                            title_text_normalized = normalize_title(title_text.split('(')[0].strip(), target_lang='en')

                            # Convert digits to words for comparison
                            movie_title_cleaned_word = replace_numbers_with_words(movie_title_cleaned)
                            title_text_cleaned_word = replace_numbers_with_words(title_text_cleaned)
                            movie_title_normalized_word = replace_numbers_with_words(movie_title_normalized)
                            title_text_normalized_word = replace_numbers_with_words(title_text_normalized)

                            # Convert words to digits for comparison
                            movie_title_cleaned_digit = replace_words_with_numbers(movie_title_cleaned)
                            title_text_cleaned_digit = replace_words_with_numbers(title_text_cleaned)
                            movie_title_normalized_digit = replace_words_with_numbers(movie_title_normalized)
                            title_text_normalized_digit = replace_words_with_numbers(title_text_normalized)

                            # Log all variations for debugging
                            logger.info(f"Cleaned movie title: {movie_title_cleaned}, Cleaned box title: {title_text_cleaned}")
                            logger.info(f"Normalized movie title: {movie_title_normalized}, Normalized box title: {title_text_normalized}")
                            logger.info(f"Movie title (digits to words): {movie_title_cleaned_word}, Box title (digits to words): {title_text_cleaned_word}")
                            logger.info(f"Movie title (words to digits): {movie_title_cleaned_digit}, Box title (words to digits): {title_text_cleaned_digit}")

                            # Compare the title in all variations
                            if not (
                                fuzz.partial_ratio(title_text_cleaned.lower(), movie_title_cleaned.lower()) >= 75 or
                                fuzz.partial_ratio(title_text_normalized.lower(), movie_title_normalized.lower()) >= 75 or
                                fuzz.partial_ratio(title_text_cleaned_word.lower(), movie_title_cleaned_word.lower()) >= 75 or
                                fuzz.partial_ratio(title_text_normalized_word.lower(), movie_title_normalized_word.lower()) >= 75 or
                                fuzz.partial_ratio(title_text_cleaned_digit.lower(), movie_title_cleaned_digit.lower()) >= 75 or
                                fuzz.partial_ratio(title_text_normalized_digit.lower(), movie_title_normalized_digit.lower()) >= 75
                            ):
                                logger.warning(f"Title mismatch for box {i}: {title_text_cleaned} or {title_text_normalized} (Expected: {movie_title_cleaned} or {movie_title_normalized}). Skipping.")
                                continue  # Skip this box if none of the variations match

                            # Compare the year with the expected year (allow ±1 year) only if it's not a TV show
                            if not is_tv_show:
                                expected_year = extract_year(movie_title)
                                box_year = extract_year(title_text)

                                # Check if either year is None before performing the subtraction
                                if expected_year is None or box_year is None:
                                    logger.warning("Could not extract year from title or box title. Skipping year comparison.")
                                    continue  # Skip this box if the year is missing

                                if abs(box_year - expected_year) > 1:
                                    logger.warning(f"Year mismatch for box {i}: {box_year} (Expected: {expected_year}). Skipping.")
                                    continue  # Skip this box if the year doesn't match

                            # After navigating to the movie details page and verifying the title/year
                            if prioritize_buttons_in_box(result_box):
                                logger.info(f"Successfully handled buttons in box {i}.")
                                confirmation_flag = True

                                # Perform RD status checks after clicking the button
                                try:
                                    rd_button = WebDriverWait(driver, 10).until(
                                        EC.presence_of_element_located((By.XPATH, ".//button[contains(text(), 'RD (')]"))
                                    )
                                    rd_button_text = rd_button.text
                                    logger.info(f"RD button text after clicking: {rd_button_text}")

                                    # If the button is now "RD (0%)", undo the click and retry with the next box
                                    if "RD (0%)" in rd_button_text:
                                        logger.warning(f"RD (0%) button detected after clicking Instant RD in box {i} {title_text}. Undoing the click and moving to the next box.")
                                        rd_button.click()  # Undo the click by clicking the RD (0%) button
                                        confirmation_flag = False  # Reset the flag
                                        continue  # Move to the next box

                                    # If it's "RD (100%)", we are done with this entry
                                    if "RD (100%)" in rd_button_text:
                                        logger.success(f"RD (100%) button detected. {i} {title_text}. This entry is complete.")
                                        return confirmation_flag  # Exit the function as we've found a matching red button

                                except TimeoutException:
                                    logger.warning(f"Timeout waiting for RD button status change in box {i}.")
                                    continue  # Move to the next box if a timeout occurs

                            else:
                                logger.warning(f"Failed to handle buttons in box {i}. Skipping.")

                        except NoSuchElementException as e:
                            logger.warning(f"Could not find 'Instant RD' button in box {i}: {e}")
                        except TimeoutException as e:
                            logger.warning(f"Timeout when processing box {i}: {e}")

                        # If a successful action was taken, break out of the outer loop
                        if confirmation_flag:
                            break

            except TimeoutException:
                logger.warning("Timeout waiting for result boxes to appear.")

            return confirmation_flag  # Return the confirmation flag

        except TimeoutException:
            logger.warning("Timeout waiting for the RD status message.")
            return

    except Exception as ex:
        logger.critical(f"Error during Selenium automation: {ex}")

async def get_user_input():
    try:
        # Check if running in a Docker container or non-interactive environment
        if os.getenv("RUNNING_IN_DOCKER", "false").lower() == "true":
            print("Running in Docker, automatically selecting 'y' for recurring Overseerr check.")
            return 'y'  # Automatically return 'yes' when running in Docker

        # Simulate asynchronous input with a timeout for interactive environments
        user_input = await asyncio.wait_for(
            asyncio.to_thread(input, "Do you want to start the initial check and recurring task? (y/n): "), 
            timeout=10
        )
        return user_input.strip().lower()

    except asyncio.TimeoutError:
        print("Input timeout. Defaulting to 'n'.")
        return 'n'  # Default to 'no' if no input is provided within 10 seconds

    except EOFError:
        # Handle cases where no input is provided (e.g., non-interactive environment)
        print("No input received (EOFError). Defaulting to 'n'.")
        return 'n'

def check_next_episode_aired(trakt_show_id: str, season_number: int, current_aired_episodes: int) -> tuple[bool, Optional[dict]]:
    """
    Check if the next episode (current_aired_episodes + 1) has aired for a given show and season.
    
    Args:
        trakt_show_id (str): The Trakt ID of the show
        season_number (int): The season number to check
        current_aired_episodes (int): The current number of aired episodes in the season
    
    Returns:
        tuple[bool, Optional[dict]]: (has_aired, episode_details)
            - has_aired: True if the next episode has aired, False otherwise
            - episode_details: Episode details if the episode exists, None otherwise
    """
    global trakt_api_calls, last_reset_time

    logger.debug(f"Starting check_next_episode_aired with trakt_show_id={trakt_show_id}, season_number={season_number}, current_aired_episodes={current_aired_episodes}")

    # Validate input parameters
    if not trakt_show_id or not isinstance(trakt_show_id, str):
        logger.error(f"Invalid trakt_show_id provided: {trakt_show_id}")
        return False, None
    if not isinstance(season_number, int) or season_number < 0:
        logger.error(f"Invalid season_number provided: {season_number}")
        return False, None
    if not isinstance(current_aired_episodes, int) or current_aired_episodes < 0:
        logger.error(f"Invalid current_aired_episodes provided: {current_aired_episodes}")
        return False, None

    current_time = time.time()
    logger.debug(f"Current time: {current_time}, Last reset time: {last_reset_time}")

    if current_time - last_reset_time >= TRAKT_RATE_LIMIT_PERIOD:
        logger.debug("Rate limit period expired. Resetting API call counter.")
        trakt_api_calls = 0
        last_reset_time = current_time

    if trakt_api_calls >= TRAKT_RATE_LIMIT:
        wait_time = TRAKT_RATE_LIMIT_PERIOD - (current_time - last_reset_time)
        logger.warning(f"Trakt API rate limit reached. Sleeping for {wait_time} seconds.")
        time.sleep(wait_time)
        trakt_api_calls = 0
        last_reset_time = time.time()
        logger.debug("Woke up from sleep. Reset API call counter.")

    next_episode_number = current_aired_episodes + 1
    url = f"https://api.trakt.tv/shows/{trakt_show_id}/seasons/{season_number}/episodes/{next_episode_number}?extended=full"
    headers = {
        "Content-type": "application/json",
        "trakt-api-key": TRAKT_API_KEY,
        "trakt-api-version": "2"
    }

    logger.debug(f"Sending GET request to {url} with headers {headers}")

    try:
        logger.info(f"Fetching next episode details for show ID {trakt_show_id}, season {season_number}, episode {next_episode_number}")
        response = requests.get(url, headers=headers, timeout=10)
        trakt_api_calls += 1
        logger.debug(f"Received response with status code {response.status_code}")

        if response.status_code == 200:
            episode_data = response.json()
            logger.debug(f"Next episode data: {episode_data}")

            first_aired = episode_data.get('first_aired')
            logger.debug(f"Next episode first_aired: {first_aired}")

            if first_aired:
                try:
                    first_aired_datetime = datetime.fromisoformat(first_aired.replace('Z', '+00:00'))
                    current_utc_time = datetime.now(timezone.utc)
                    logger.debug(f"Parsed first_aired_datetime: {first_aired_datetime}, current_utc_time: {current_utc_time}")

                    if current_utc_time >= first_aired_datetime:
                        logger.info(f"Episode {next_episode_number} has aired for show ID {trakt_show_id}, season {season_number}")
                        return True, episode_data
                    else:
                        logger.info(f"Episode {next_episode_number} has not aired yet for show ID {trakt_show_id}, season {season_number}")
                        return False, episode_data
                except ValueError as e:
                    logger.error(f"Invalid first_aired format for episode {next_episode_number}: {e}")
                    return False, episode_data
            else:
                logger.warning(f"Episode {next_episode_number} missing 'first_aired' field for show ID {trakt_show_id}, season {season_number}")
                return False, episode_data

        elif response.status_code == 404:
            logger.info(f"Episode {next_episode_number} does not exist yet for show ID {trakt_show_id}, season {season_number}")
            return False, None
        else:
            logger.warning(f"Failed to fetch next episode details for show ID {trakt_show_id}, season {season_number}, episode {next_episode_number}: Status code {response.status_code}")
            return False, None

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching next episode details from Trakt API for show ID {trakt_show_id}, season {season_number}, episode {next_episode_number}: {e}")
        return False, None

async def check_show_subscriptions():
    """
    Recurring task to check for new episodes in subscribed shows listed in episode_discrepancies.json.
    Updates the JSON file with the latest aired episode counts and processes new episodes if found.
    Also reattempts processing of previously failed episodes and checks for the next episode if there's a discrepancy.
    """
    logger.info("Starting show subscription check...")

    DISCREPANCY_REPO_FILE = "episode_discrepancies.json"
    
    # Check if the discrepancy file exists
    if not os.path.exists(DISCREPANCY_REPO_FILE):
        logger.info("No episode discrepancies file found. Skipping show subscription check.")
        return

    # Read the discrepancies file
    try:
        with open(DISCREPANCY_REPO_FILE, 'r', encoding='utf-8') as f:
            repo_data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to read episode_discrepancies.json: {e}")
        return

    discrepancies = repo_data.get("discrepancies", [])
    if not discrepancies:
        logger.info("No discrepancies found in episode_discrepancies.json. Skipping show subscription check.")
        return

    # Process each show in the discrepancies
    for discrepancy in discrepancies:
        show_title = discrepancy.get("show_title")
        trakt_show_id = discrepancy.get("trakt_show_id")
        imdb_id = discrepancy.get("imdb_id")
        season_number = discrepancy.get("season_number")
        season_details = discrepancy.get("season_details", {})
        previous_aired_episodes = season_details.get("aired_episodes", 0)
        failed_episodes = discrepancy.get("failed_episodes", [])  # Get previously failed episodes

        if not trakt_show_id or not season_number or not imdb_id:
            logger.warning(f"Missing trakt_show_id, season_number, or imdb_id for {show_title}. Skipping.")
            continue

        logger.info(f"Checking for new episodes for {show_title} Season {season_number}...")

        # Fetch the latest season details from Trakt
        latest_season_details = get_season_details_from_trakt(str(trakt_show_id), season_number)
        if not latest_season_details:
            logger.error(f"Failed to fetch latest season details for {show_title} Season {season_number}. Skipping.")
            continue

        current_aired_episodes = latest_season_details.get("aired_episodes", 0)
        episode_count = latest_season_details.get("episode_count", 0)
        logger.info(f"Previous aired episodes: {previous_aired_episodes}, Current aired episodes: {current_aired_episodes}, Episode count: {episode_count}")

        # Only check for the next episode if there's a discrepancy
        if episode_count != current_aired_episodes:
            has_aired, next_episode_details = check_next_episode_aired(
                str(trakt_show_id), season_number, current_aired_episodes
            )
            if has_aired:
                logger.info(f"Next episode (E{current_aired_episodes + 1:02d}) has aired for {show_title} Season {season_number}. Updating aired_episodes.")
                latest_season_details['aired_episodes'] = current_aired_episodes + 1
                current_aired_episodes += 1
            else:
                logger.info(f"Next episode (E{current_aired_episodes + 1:02d}) has not aired for {show_title} Season {season_number}.")
        else:
            logger.info(f"No episode count discrepancy for {show_title} Season {season_number}. Skipping next episode check.")

        # Update the season details in the discrepancy entry
        discrepancy["season_details"] = latest_season_details
        discrepancy["timestamp"] = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Initialize a list to track episodes to process (new episodes + failed episodes)
        episodes_to_process = []

        # Add previously failed episodes to the list
        for episode_id in failed_episodes:
            episode_num = int(episode_id.replace("E", ""))
            if episode_num <= current_aired_episodes:  # Only reprocess if the episode is still aired
                episodes_to_process.append((episode_num, episode_id, "failed"))
                logger.info(f"Reattempting previously failed episode for {show_title} Season {season_number} {episode_id}")

        # Check for new episodes
        if current_aired_episodes > previous_aired_episodes:
            logger.info(f"New episodes found for {show_title} Season {season_number}: {current_aired_episodes - previous_aired_episodes} new episodes.")
            new_episodes_start = previous_aired_episodes + 1
            new_episodes_end = current_aired_episodes
            for episode_num in range(new_episodes_start, new_episodes_end + 1):
                episode_id = f"E{episode_num:02d}"
                episodes_to_process.append((episode_num, episode_id, "new"))
                logger.info(f"Found new episode for {show_title} Season {season_number} {episode_id}")

        # If there are no episodes to process (neither new nor failed), skip
        if not episodes_to_process:
            logger.info(f"No new or failed episodes to process for {show_title} Season {season_number}.")
            continue

        # Navigate to the show page
        url = f"https://debridmediamanager.com/show/{imdb_id}/{season_number}"
        driver.get(url)
        logger.info(f"Navigated to show page for Season {season_number}: {url}")

        # Wait for the page to load
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='status' and contains(@aria-live, 'polite')]"))
            )
            logger.info("Page load confirmed via status element.")
        except TimeoutException:
            logger.warning("Timeout waiting for page load status. Proceeding anyway.")

        # Process all episodes (new and failed)
        normalized_seasons = [f"Season {season_number}"]
        confirmed_seasons = set()
        is_tv_show = True
        all_episodes_confirmed = True
        new_failed_episodes = []  # Track episodes that fail in this run

        for episode_num, episode_id, episode_type in episodes_to_process:
            logger.info(f"Processing {episode_type} episode for {show_title} Season {season_number} {episode_id}")

            # Clear and update the filter box with episode-specific filter
            try:
                filter_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "query"))
                )
                filter_input.clear()
                episode_filter = f"S{season_number:02d}{episode_id}"
                full_filter = f"{TORRENT_FILTER_REGEX} {episode_filter}"
                filter_input.send_keys(full_filter)
                logger.info(f"Applied filter: {full_filter}")

                try:
                    click_show_more_results(driver, logger)
                except TimeoutException:
                    logger.warning("Timed out while trying to click 'Show More Results'")
                except Exception as e:
                    logger.error(f"Unexpected error in click_show_more_results: {e}")

                # Wait for results to update
                time.sleep(2)

                # Check for existing RD (100%) using check_red_buttons
                confirmation_flag, confirmed_seasons = check_red_buttons(
                    driver, show_title, normalized_seasons, confirmed_seasons, is_tv_show, episode_id=episode_id
                )

                if confirmation_flag:
                    logger.success(f"{episode_id} already cached at RD (100%). Skipping further processing.")
                    continue

                # Process uncached episode
                try:
                    result_boxes = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'border-black')]"))
                    )
                    episode_confirmed = False

                    for i, result_box in enumerate(result_boxes, start=1):
                        try:
                            title_element = result_box.find_element(By.XPATH, ".//h2")
                            title_text = title_element.text.strip()
                            logger.info(f"Box {i} title: {title_text}")

                            title_clean = clean_title(title_text, 'en')
                            show_clean = clean_title(show_title, 'en')
                            match_ratio = fuzz.partial_ratio(title_clean, show_clean)
                            logger.info(f"Match ratio: {match_ratio} for '{title_clean}' vs '{show_clean}'")
                            
                            if episode_id.lower() in title_text.lower() and match_ratio >= 50:
                                logger.info(f"Found match for {episode_id} in box {i}: {title_text}")

                                if prioritize_buttons_in_box(result_box):
                                    logger.info(f"Successfully handled {episode_id} in box {i}")
                                    episode_confirmed = True

                                    # Verify RD status
                                    try:
                                        rd_button = WebDriverWait(driver, 10).until(
                                            EC.presence_of_element_located((By.XPATH, ".//button[contains(text(), 'RD (')]"))
                                        )
                                        rd_button_text = rd_button.text
                                        if "RD (100%)" in rd_button_text:
                                            logger.success(f"RD (100%) confirmed for {episode_id}. Episode fully processed.")
                                            episode_confirmed = True
                                            break
                                        elif "RD (0%)" in rd_button_text:
                                            logger.warning(f"RD (0%) detected for {episode_id}. Undoing and skipping.")
                                            rd_button.click()
                                            episode_confirmed = False
                                            continue
                                    except TimeoutException:
                                        logger.warning(f"Timeout waiting for RD status for {episode_id}")
                                        continue
                                else:
                                    logger.warning(f"Failed to handle buttons for {episode_id} in box {i}")

                        except NoSuchElementException:
                            logger.warning(f"No title found in box {i} for {episode_id}")

                    if not episode_confirmed:
                        logger.error(f"Failed to confirm {episode_id} for {show_title} Season {season_number}")
                        new_failed_episodes.append(episode_id)
                        all_episodes_confirmed = False

                except TimeoutException:
                    logger.warning(f"No result boxes found for {episode_id}")
                    new_failed_episodes.append(episode_id)
                    all_episodes_confirmed = False

            except TimeoutException:
                logger.error(f"Filter input with ID 'query' not found for {episode_id}")
                new_failed_episodes.append(episode_id)
                all_episodes_confirmed = False

        # Reset the filter
        try:
            filter_input = driver.find_element(By.ID, "query")
            filter_input.clear()
            filter_input.send_keys(TORRENT_FILTER_REGEX)
            logger.info(f"Reset filter to default: {TORRENT_FILTER_REGEX}")
        except NoSuchElementException:
            logger.warning("Could not reset filter to default using ID 'query'")

        # Update the failed_episodes list in the discrepancy entry
        discrepancy["failed_episodes"] = new_failed_episodes

        if all_episodes_confirmed:
            logger.info(f"Successfully processed all episodes for {show_title} Season {season_number}")
        else:
            logger.warning(f"Failed to process some episodes for {show_title} Season {season_number}. Failed episodes: {new_failed_episodes}")

    # Write the updated discrepancies back to the file
    try:
        with open(DISCREPANCY_REPO_FILE, 'w', encoding='utf-8') as f:
            json.dump(repo_data, f, indent=2)
        logger.info("Updated episode_discrepancies.json with latest aired episode counts and failed episodes.")
    except Exception as e:
        logger.error(f"Failed to write updated episode_discrepancies.json: {e}")

    logger.info("Completed show subscription check.")

def schedule_token_refresh():
    """Schedule the token refresh every 10 minutes."""
    scheduler.add_job(check_and_refresh_access_token, 'interval', minutes=10)
    logger.info("Scheduled token refresh every 10 minutes.")

# Lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Lifespan startup: Initializing SeerrBridge...")
    
    # Startup logic
    global processing_task
    logger.info('Starting SeerrBridge...')

    # Check and refresh access token before any other initialization
    check_and_refresh_access_token()

    # Always initialize the browser when the bot is ready
    try:
        await initialize_browser()
    except Exception as e:
        logger.error(f"Failed to initialize browser: {e}")
        raise  # Raise to prevent app start if critical

    # Generate and log status after browser initialization
    try:
        status = await get_status()
        logger.info(f"SeerrBridge browser initialized. Status: {status}")
    except Exception as e:
        logger.error(f"Error generating initial status: {e}")

    # Start the request processing task
    if processing_task is None:
        processing_task = asyncio.create_task(process_requests())
        logger.info("Started request processing task.")

    # Schedule the token refresh
    schedule_token_refresh()
    scheduler.start()

    # Defer background tasks to run after startup
    async def run_background_tasks():
        # Add a retry mechanism to ping /status after startup
        max_retries = 5
        retry_delay = 1  # seconds
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get("http://localhost:8777/status") as response:
                        if response.status == 200:
                            status = await response.json()
                            logger.info(f"Successfully pinged /status after startup: {status}")
                            break
                        else:
                            logger.warning(f"Failed to ping /status (attempt {attempt + 1}/{max_retries}): HTTP {response.status}")
            except Exception as e:
                logger.warning(f"Error pinging /status (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
        else:
            logger.error("Failed to ping /status after all retries.")

        # Run background tasks
        if ENABLE_AUTOMATIC_BACKGROUND_TASK:
            logger.info("Automatic background task is enabled. Starting initial check and recurring task.")
            try:
                await process_movie_requests()
                logger.info("Completed initial check of movie requests.")
                schedule_recheck_movie_requests()
            except Exception as e:
                logger.error(f"Error while processing movie requests: {e}")
        else:
            logger.info("Automatic background task is disabled. Skipping initial check and recurring task.")

        if ENABLE_SHOW_SUBSCRIPTION_TASK:
            logger.info("Show subscription task is enabled. Starting initial check and recurring task.")
            try:
                await check_show_subscriptions()
                logger.info("Completed initial check of show subscriptions.")
                scheduler.add_job(check_show_subscriptions, 'interval', minutes=REFRESH_INTERVAL_MINUTES)
                logger.info(f"Scheduled show subscription check every {REFRESH_INTERVAL_MINUTES} minute(s).")
            except Exception as e:
                logger.error(f"Error while processing show subscriptions: {e}")
        else:
            logger.info("Show subscription task is disabled. Skipping initial check and recurring task.")

    # Schedule background tasks to run after startup
    asyncio.create_task(run_background_tasks())

    try:
        logger.info("Lifespan startup complete. Yielding to application...")
        yield  # Application runs here
    finally:
        # Shutdown logic
        logger.info("Lifespan shutdown: Shutting down SeerrBridge...")
        try:
            if processing_task is not None:
                processing_task.cancel()
                try:
                    await processing_task
                except asyncio.CancelledError:
                    logger.info("Request processing task cancelled.")
            if scheduler.running:
                scheduler.shutdown()
                logger.info("Scheduler shut down.")
            if driver is not None:
                driver.quit()
                logger.info("Browser closed.")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

# Initialize FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)

# Status endpoint (must be after app definition)
@app.get("/status")
async def get_status():
    """Return status information about the running SeerrBridge service."""
    uptime_seconds = (datetime.now() - START_TIME).total_seconds()
    
    # Calculate days, hours, minutes, seconds
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    # Format uptime string
    uptime_str = ""
    if days > 0:
        uptime_str += f"{int(days)}d "
    if hours > 0 or days > 0:
        uptime_str += f"{int(hours)}h "
    if minutes > 0 or hours > 0 or days > 0:
        uptime_str += f"{int(minutes)}m "
    uptime_str += f"{int(seconds)}s"
    
    return {
        "status": "running",
        "version": "0.6",
        "uptime_seconds": uptime_seconds,
        "uptime": uptime_str,
        "start_time": START_TIME.isoformat(),
        "current_time": datetime.now().isoformat(),
        "browser_initialized": driver is not None
    }

### Webhook Endpoint ###
@app.post("/jellyseer-webhook/")
async def jellyseer_webhook(request: Request, background_tasks: BackgroundTasks):
    raw_payload = await request.json()
    
    try:
        payload = WebhookPayload(**raw_payload)
    except ValidationError as e:
        logger.error(f"Payload validation error: {e}")
        raise HTTPException(status_code=422, detail=str(e))

    if payload.notification_type == "TEST_NOTIFICATION":
        logger.success("Test notification received and processed successfully.")
        return {"status": "success", "message": "Test notification processed successfully."}

    logger.info(f"Received webhook with event: {payload.event}")

    if payload.media is None:
        logger.error("Media information is missing in the payload")
        raise HTTPException(status_code=400, detail="Media information is missing in the payload")

    media_type = payload.media.media_type
    logger.info(f"Received webhook with event: {payload.event} for {media_type.capitalize()}")

    tmdb_id = payload.media.tmdbId
    if not tmdb_id:
        logger.error("TMDB ID is missing in the payload")
        raise HTTPException(status_code=400, detail="TMDB ID is missing in the payload")

    logger.info(f"Extracted tmdbId: {tmdb_id}")

    # Fetch media details from Trakt
    media_details = get_media_details_from_trakt(tmdb_id, media_type)
    if not media_details:
        logger.error(f"Failed to fetch {media_type} details from Trakt")
        raise HTTPException(status_code=500, detail=f"Failed to fetch {media_type} details from Trakt")

    movie_or_tv_title = f"{media_details['title']} ({media_details['year']})"
    logger.info(f"Fetched {media_type.capitalize()} details: {movie_or_tv_title}")

    # Define the repository file name
    DISCREPANCY_REPO_FILE = "episode_discrepancies.json"
    
    # Initialize the repository if it doesn't exist
    if not os.path.exists(DISCREPANCY_REPO_FILE):
        with open(DISCREPANCY_REPO_FILE, 'w', encoding='utf-8') as f:
            json.dump({"discrepancies": []}, f)

    # Handle TV show seasons if applicable
    if media_type == 'tv' and payload.extra:
        requested_seasons = parse_requested_seasons(payload.extra)
        if requested_seasons:
            logger.info(f"Requested seasons for TV show: {requested_seasons}")
            trakt_show_id = media_details['trakt_id']
            imdb_id = media_details['imdb_id']  # Extract IMDb ID from media_details
            
            for season in requested_seasons:
                # Extract season number (e.g., "Season 1" -> 1)
                season_number = int(season.split()[-1]) if season.startswith("Season") else int(season)
                season_details = get_season_details_from_trakt(str(trakt_show_id), season_number)
                
                if season_details:
                    # Check for episode count discrepancy
                    episode_count = season_details.get('episode_count', 0)
                    aired_episodes = season_details.get('aired_episodes', 0)
                    logger.info(f"Season {season_number} details: episode_count={episode_count}, aired_episodes={aired_episodes}")

                    if episode_count != aired_episodes:
                        # Only check for the next episode if there's a discrepancy
                        has_aired, next_episode_details = check_next_episode_aired(
                            str(trakt_show_id), season_number, aired_episodes
                        )
                        if has_aired:
                            logger.info(f"Next episode (E{aired_episodes + 1:02d}) has aired for {movie_or_tv_title} Season {season_number}. Updating aired_episodes.")
                            season_details['aired_episodes'] = aired_episodes + 1
                        else:
                            logger.info(f"Next episode (E{aired_episodes + 1:02d}) has not aired for {movie_or_tv_title} Season {season_number}.")

                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        
                        discrepancy_entry = {
                            "show_title": movie_or_tv_title,
                            "trakt_show_id": trakt_show_id,
                            "imdb_id": imdb_id,
                            "season_number": season_number,
                            "season_details": season_details,
                            "timestamp": timestamp,
                            "failed_episodes": []  # Initialize the new field
                        }
                        
                        with open(DISCREPANCY_REPO_FILE, 'r', encoding='utf-8') as f:
                            repo_data = json.load(f)
                        
                        is_duplicate = any(
                            entry['trakt_show_id'] == trakt_show_id and 
                            entry['season_number'] == season_number
                            for entry in repo_data['discrepancies']
                        )
                        
                        if not is_duplicate:
                            repo_data["discrepancies"].append(discrepancy_entry)
                            with open(DISCREPANCY_REPO_FILE, 'w', encoding='utf-8') as f:
                                json.dump(repo_data, f, indent=2)
                            logger.info(f"Found episode count discrepancy for {movie_or_tv_title} Season {season_number}. Added to repository {DISCREPANCY_REPO_FILE}")
                        else:
                            logger.info(f"Episode count discrepancy for {movie_or_tv_title} Season {season_number} already exists in repository")
                    else:
                        logger.info(f"No episode count discrepancy for {movie_or_tv_title} Season {season_number}. Skipping next episode check.")

    # Add request to queue for further processing
    background_tasks.add_task(add_request_to_queue, media_details['imdb_id'], movie_or_tv_title, media_type, payload.extra)
    logger.info(f"Returning response: {media_details['title']} ({media_details['year']})")

    return {"status": "success", "title": media_details['title'], "year": media_details['year']}

def schedule_recheck_movie_requests():
    """Schedule or reschedule the movie requests recheck job, replacing any existing job."""
    # Validate REFRESH_INTERVAL_MINUTES
    min_interval = 1.0  # Minimum interval in minutes
    if REFRESH_INTERVAL_MINUTES < min_interval:
        logger.warning(f"REFRESH_INTERVAL_MINUTES ({REFRESH_INTERVAL_MINUTES}) is too small. Using minimum interval of {min_interval} minutes.")
        interval = min_interval
    else:
        interval = REFRESH_INTERVAL_MINUTES

    try:
        # Remove all existing jobs with the same ID
        for job in scheduler.get_jobs():
            if job.id == "process_movie_requests":
                scheduler.remove_job(job.id)
                logger.info("Removed existing job with ID: process_movie_requests")

        # Schedule the new job with a unique ID
        scheduler.add_job(
            process_movie_requests,
            'interval',
            minutes=interval,
            id="process_movie_requests",
            replace_existing=True,
            max_instances=1  # Explicitly set to avoid unexpected concurrency
        )
        logger.info(f"Scheduled rechecking movie requests every {interval} minute(s).")
    except Exception as e:
        logger.error(f"Error scheduling movie requests recheck: {e}")

async def on_close():
    await shutdown_browser()  # Ensure browser is closed when the bot closes

@app.post("/reload-env")
async def reload_environment():
    """
    Reload environment variables from the .env file.
    This endpoint can be called when environment variables have been changed externally.
    """
    logger.info("Environment reload triggered via API endpoint")
    
    # Reload environment variables
    global RD_ACCESS_TOKEN, RD_REFRESH_TOKEN, RD_CLIENT_ID, RD_CLIENT_SECRET
    global OVERSEERR_BASE, OVERSEERR_API_BASE_URL, OVERSEERR_API_KEY, TRAKT_API_KEY
    global HEADLESS_MODE, ENABLE_AUTOMATIC_BACKGROUND_TASK, ENABLE_SHOW_SUBSCRIPTION_TASK
    global TORRENT_FILTER_REGEX, MAX_MOVIE_SIZE, MAX_EPISODE_SIZE, REFRESH_INTERVAL_MINUTES
    
    # Store original values for comparison
    original_values = {
        "RD_ACCESS_TOKEN": RD_ACCESS_TOKEN,
        "RD_REFRESH_TOKEN": RD_REFRESH_TOKEN,
        "RD_CLIENT_ID": RD_CLIENT_ID,
        "RD_CLIENT_SECRET": RD_CLIENT_SECRET,
        "OVERSEERR_BASE": OVERSEERR_BASE,
        "OVERSEERR_API_KEY": OVERSEERR_API_KEY,
        "TRAKT_API_KEY": TRAKT_API_KEY,
        "HEADLESS_MODE": HEADLESS_MODE,
        "ENABLE_AUTOMATIC_BACKGROUND_TASK": ENABLE_AUTOMATIC_BACKGROUND_TASK,
        "ENABLE_SHOW_SUBSCRIPTION_TASK": ENABLE_SHOW_SUBSCRIPTION_TASK,
        "TORRENT_FILTER_REGEX": TORRENT_FILTER_REGEX,
        "MAX_MOVIE_SIZE": MAX_MOVIE_SIZE,
        "MAX_EPISODE_SIZE": MAX_EPISODE_SIZE,
        "REFRESH_INTERVAL_MINUTES": REFRESH_INTERVAL_MINUTES
    }
    
    # Force reload of all environment variables
    load_dotenv(override=True)
    
    # Update global variables with new values
    RD_ACCESS_TOKEN = os.getenv('RD_ACCESS_TOKEN')
    RD_REFRESH_TOKEN = os.getenv('RD_REFRESH_TOKEN')
    RD_CLIENT_ID = os.getenv('RD_CLIENT_ID')
    RD_CLIENT_SECRET = os.getenv('RD_CLIENT_SECRET')
    OVERSEERR_BASE = os.getenv('OVERSEERR_BASE')
    OVERSEERR_API_BASE_URL = f"{OVERSEERR_BASE}/api/v1"
    OVERSEERR_API_KEY = os.getenv('OVERSEERR_API_KEY')
    TRAKT_API_KEY = os.getenv('TRAKT_API_KEY')
    HEADLESS_MODE = os.getenv("HEADLESS_MODE", "true").lower() == "true"
    ENABLE_AUTOMATIC_BACKGROUND_TASK = os.getenv("ENABLE_AUTOMATIC_BACKGROUND_TASK", "false").lower() == "true"
    ENABLE_SHOW_SUBSCRIPTION_TASK = os.getenv("ENABLE_SHOW_SUBSCRIPTION_TASK", "false").lower() == "true"
    TORRENT_FILTER_REGEX = os.getenv("TORRENT_FILTER_REGEX")
    MAX_MOVIE_SIZE = os.getenv("MAX_MOVIE_SIZE")
    MAX_EPISODE_SIZE = os.getenv("MAX_EPISODE_SIZE")
    
    try:
        REFRESH_INTERVAL_MINUTES = float(os.getenv("REFRESH_INTERVAL_MINUTES"))
    except (TypeError, ValueError):
        logger.error("REFRESH_INTERVAL_MINUTES environment variable is not a valid number. Keeping previous value.")
    
    # Detect which values have changed
    changes = {}
    for key, old_value in original_values.items():
        new_value = globals()[key]
        if new_value != old_value:
            changes[key] = {"old": old_value, "new": new_value}
    
    if changes:
        logger.info(f"Environment variables changed: {list(changes.keys())}")
        
        # Apply changes to browser if needed
        if driver and any(key in changes for key in ["RD_ACCESS_TOKEN", "RD_REFRESH_TOKEN", "RD_CLIENT_ID", "RD_CLIENT_SECRET"]):
            logger.info("Updating Real-Debrid credentials in browser session")
            try:
                driver.execute_script(f"""
                    localStorage.setItem('rd:accessToken', '{RD_ACCESS_TOKEN}');
                    localStorage.setItem('rd:clientId', '"{RD_CLIENT_ID}"');
                    localStorage.setItem('rd:clientSecret', '"{RD_CLIENT_SECRET}"');
                    localStorage.setItem('rd:refreshToken', '"{RD_REFRESH_TOKEN}"');          
                """)
                driver.refresh()
                logger.info("Browser session updated with new credentials")
            except Exception as e:
                logger.error(f"Error updating browser session: {e}")
        
        # Apply filter changes if needed
        if driver and "TORRENT_FILTER_REGEX" in changes:
            logger.info("Updating torrent filter regex in browser")
            try:
                # Navigate to settings
                driver.get("https://debridmediamanager.com")
                settings_link = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[contains(text(),'⚙️ Settings')]"))
                )
                settings_link.click()
                
                # Update filter
                default_filter_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "dmm-default-torrents-filter"))
                )
                default_filter_input.clear()
                default_filter_input.send_keys(TORRENT_FILTER_REGEX)
                
                # Close settings
                settings_link.click()
                logger.info(f"Updated torrent filter regex to: {TORRENT_FILTER_REGEX}")
            except Exception as e:
                logger.error(f"Error updating torrent filter regex: {e}")
        
        # Apply size settings if needed
        if driver and ("MAX_MOVIE_SIZE" in changes or "MAX_EPISODE_SIZE" in changes):
            logger.info("Updating size settings in browser")
            try:
                # Navigate to settings
                driver.get("https://debridmediamanager.com")
                settings_link = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[contains(text(),'⚙️ Settings')]"))
                )
                settings_link.click()
                
                # Update movie size if changed
                if "MAX_MOVIE_SIZE" in changes:
                    max_movie_select = WebDriverWait(driver, 10).until(
                        EC.visibility_of_element_located((By.ID, "dmm-movie-max-size"))
                    )
                    select_obj = Select(max_movie_select)
                    select_obj.select_by_value(MAX_MOVIE_SIZE)
                    logger.info(f"Updated max movie size to: {MAX_MOVIE_SIZE}")
                
                # Update episode size if changed
                if "MAX_EPISODE_SIZE" in changes:
                    max_episode_select = WebDriverWait(driver, 10).until(
                        EC.visibility_of_element_located((By.ID, "dmm-episode-max-size"))
                    )
                    select_obj = Select(max_episode_select)
                    select_obj.select_by_value(MAX_EPISODE_SIZE)
                    logger.info(f"Updated max episode size to: {MAX_EPISODE_SIZE}")
                
                # Close settings
                settings_link.click()
            except Exception as e:
                logger.error(f"Error updating size settings: {e}")
        
        # Update scheduler if refresh interval changed
        if "REFRESH_INTERVAL_MINUTES" in changes and scheduler and scheduler.running:
            logger.info(f"Updating scheduler intervals to {REFRESH_INTERVAL_MINUTES} minutes")
            min_interval = 1.0  # Minimum interval in minutes
            if REFRESH_INTERVAL_MINUTES < min_interval:
                logger.warning(f"REFRESH_INTERVAL_MINUTES ({REFRESH_INTERVAL_MINUTES}) is too small. Using minimum interval of {min_interval} minutes.")
                interval = min_interval
            else:
                interval = REFRESH_INTERVAL_MINUTES
        
            try:
                # Remove all existing jobs for both tasks
                for job in scheduler.get_jobs():
                    if job.id in ["check_show_subscriptions", "process_movie_requests"]:
                        scheduler.remove_job(job.id)
                        logger.info(f"Removed existing job with ID: {job.id}")
        
                # Re-add jobs with new interval
                if ENABLE_AUTOMATIC_BACKGROUND_TASK:
                    scheduler.add_job(
                        process_movie_requests,
                        'interval',
                        minutes=interval,
                        id="process_movie_requests",
                        replace_existing=True,
                        max_instances=1
                    )
                    logger.info(f"Rescheduled movie requests check every {interval} minute(s)")
        
                if ENABLE_SHOW_SUBSCRIPTION_TASK:
                    scheduler.add_job(
                        check_show_subscriptions,
                        'interval',
                        minutes=interval,
                        id="check_show_subscriptions",
                        replace_existing=True,
                        max_instances=1
                    )
                    logger.info(f"Rescheduled show subscription check every {interval} minute(s)")
            except Exception as e:
                logger.error(f"Error updating scheduler: {e}")
    else:
        logger.info("No environment variable changes detected")
    
    return {
        "status": "success", 
        "message": "Environment variables reloaded successfully",
        "changes": list(changes.keys())
    }

# Main entry point for running the FastAPI server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8777)