# =============================================================================
# Soluify.com  |  Your #1 IT Problem Solver  |  {SeerrBridge v0.4.4}
# =============================================================================
#  __         _
# (_  _ |   .(_
# __)(_)||_||| \/
#              /
# © 2024
# -----------------------------------------------------------------------------
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, ValidationError, field_validator
from typing import Optional, List, Dict, Any
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
from datetime import datetime, timedelta
from deep_translator import GoogleTranslator
from fuzzywuzzy import fuzz
from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Configure loguru
logger.remove()  # Remove default handler
logger.add("seerbridge.log", rotation="500 MB", encoding='utf-8')  # Use utf-8 encoding for log file
logger.add(sys.stdout, colorize=True)  # Ensure stdout can handle Unicode
logger.level("WARNING", color="<cyan>")

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI()

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
TORRENT_FILTER_REGEX = os.getenv("TORRENT_FILTER_REGEX")
MAX_MOVIE_SIZE = os.getenv("MAX_MOVIE_SIZE")
MAX_EPISODE_SIZE = os.getenv("MAX_EPISODE_SIZE")

# Confirm the interval is a valid number.
try:
    REFRESH_INTERVAL_MINUTES = float(os.getenv("REFRESH_INTERVAL_MINUTES"))
except (TypeError, ValueError):
    logger.error("REFRESH_INTERVAL_MINUTES environment variable is not a valid number.")
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
            logger.success("Successfully refreshed access token.")
            
            update_env_file()

            if driver:
                driver.execute_script(f"""
                    localStorage.setItem('rd:accessToken', '{RD_ACCESS_TOKEN}');
                """)
                logger.info("Updated Real-Debrid credentials in local storage after token refresh.")
                driver.refresh()
                logger.success("Refreshed the page after updating local storage with the new token.")
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

            logger.success("Initialized Selenium WebDriver with WebDriver Manager.")
            # Navigate to an initial page to confirm browser works
            driver.get("https://debridmediamanager.com")
            logger.success("Navigated to Debrid Media Manager page.")
        except Exception as e:
            logger.error(f"Failed to initialize Selenium WebDriver: {e}")
            raise e

        # Inject Real-Debrid access token and other credentials into local storage
        driver.execute_script(f"""
            localStorage.setItem('rd:accessToken', '{RD_ACCESS_TOKEN}');
        """)
        logger.info("Set Real-Debrid credentials in local storage.")

        # Refresh the page to apply the local storage values
        driver.refresh()
        login(driver)
        logger.success("Refreshed the page to apply local storage values.")
        # After refreshing, call the login function to click the login button
        # After successful login, click on "⚙️ Settings" to open the settings popup
        try:

            logger.info("Attempting to click the '⚙️ Settings' link.")
            settings_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[contains(text(),'⚙️ Settings')]"))
            )
            settings_link.click()
            logger.info("Clicked on '⚙️ Settings' link.")

            #####################################    
            # 05.01.2025 - shivamsnaik@icloud.com
            # MAX MOVIE SIZE: Locate the maximum movie size select element
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
            ########################################

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
            logger.success("Closed 'Settings' to save settings.")

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
            logger.success("Library section loaded successfully.")
        except TimeoutException:
            logger.info("Library loading.")

        # Wait for at least 2 seconds on the library page
        logger.info("Waiting for 2 seconds on the library page.")
        time.sleep(2)
        logger.success("Completed waiting on the library page.")

async def shutdown_browser():
    global driver
    if driver:
        driver.quit()
        logger.warning("Selenium WebDriver closed.")
        driver = None

### Function to process requests from the queue
async def process_requests():
    while True:
        movie_title, extra_data = await request_queue.get()  # Wait for the next request in the queue
        logger.info(f"Processing movie request: {movie_title}")
        try:
            await asyncio.to_thread(search_on_debrid, movie_title, driver, extra_data)  # Process the request
        except Exception as ex:
            logger.critical(f"Error processing movie request {movie_title}: {ex}")
        finally:
            request_queue.task_done()  # Mark the request as done

### Function to add requests to the queue
async def add_request_to_queue(movie_title, extra_data=None):
    if request_queue.full():
        logger.warning(f"Request queue is full. Cannot add movie: {movie_title}")
        return False
    
    await request_queue.put((movie_title, extra_data))
    logger.info(f"Added movie request to queue: {movie_title}")
    return True

### Helper function to extract year from a string
def extract_year(text, ignore_resolution=False):
    if ignore_resolution:
        # Remove resolution strings like "2160p"
        text = re.sub(r'\b\d{3,4}p\b', '', text)
    
    # Extract the year using a regular expression
    match = re.search(r'\b(19\d{2}|20\d{2})\b', text)
    if match:
        return int(match.group(0))
    return None

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
    """
    # Translate the title to the target language
    translated_title = translate_title(title, target_lang)

    # Remove commas, hyphens, colons, semicolons, and apostrophes
    cleaned_title = re.sub(r"[,:;'-]", '', translated_title)
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
    title = title.replace('’', "'")
    # Further normalization can be added here if required
    return title.strip()
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
                    "year": media_info['year']
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

### Process the fetched messages (newest to oldest)
async def process_movie_requests():
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
        if media_type == 'tv' and 'seasons' in request:
            requested_seasons = [f"Season {season['seasonNumber']}" for season in request['seasons']]
            extra_data.append({"name": "Requested Seasons", "value": ", ".join(requested_seasons)})
            logger.info(f"Requested seasons for TV show: {requested_seasons}")

        # Fetch media details from Trakt
        movie_details = get_media_details_from_trakt(tmdb_id, media_type)  # Pass media_type here
        if not movie_details:
            logger.error(f"Failed to get media details for TMDB ID {tmdb_id}")
            continue
        
        media_title = f"{movie_details['title']} ({movie_details['year']})"
        logger.info(f"Processing {media_type} request: {media_title}")
        
        try:
            # Pass media_type and extra_data to search_on_debrid
            confirmation_flag = await asyncio.to_thread(search_on_debrid, media_title, driver, extra_data)
            if confirmation_flag:
                if mark_completed(media_id, tmdb_id):
                    logger.success(f"Marked media {media_id} as completed in Overseerr")
                else:
                    logger.error(f"Failed to mark media {media_id} as completed in Overseerr")
            else:
                logger.info(f"Media {media_id} was not properly confirmed. Skipping marking as completed.")
        except Exception as ex:
            logger.critical(f"Error processing {media_type} request {media_title}: {ex}")

    logger.info("Finished processing all current requests. Waiting for new requests.")

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

def check_red_buttons(driver, movie_title, normalized_seasons, confirmed_seasons, is_tv_show):
    """
    Check for red buttons (RD 100%) and verify titles and seasons.
    """
    confirmation_flag = False  # Initialize the confirmation flag

    try:
        # Find all red buttons
        all_red_buttons_elements = driver.find_elements(By.XPATH, "//button[contains(@class, 'bg-red-900/30')]")
        
        # Filter out the buttons that contain "Report" in their text
        red_buttons_elements = [button for button in all_red_buttons_elements if "Report" not in button.text]
        
        # Log the count of filtered red buttons
        logger.info(f"Found {len(red_buttons_elements)} red button(s) (100% RD) without 'Report'. Verifying titles.")

        # Flag to track if any red button was found for the current season
        found_red_button_for_season = False

        for i, red_button_element in enumerate(red_buttons_elements, start=1):
            if "Report" in red_button_element.text:
                continue
            logger.info(f"Checking red button {i}...")

            try:
                # Adjusted XPath to find the <h2> element within the same parent container as the red button
                red_button_title_element = red_button_element.find_element(By.XPATH, ".//ancestor::div[contains(@class, 'border-2')]//h2")
                red_button_title_text = red_button_title_element.text.strip()

                # Clean the title for comparison
                red_button_title_cleaned = clean_title(red_button_title_text.split('(')[0].strip(), target_lang='en')
                red_button_title_normalized = normalize_title(red_button_title_text.split('(')[0].strip(), target_lang='en')

                # Clean and normalize the movie title once outside the loop
                movie_title_cleaned = clean_title(movie_title.split('(')[0].strip(), target_lang='en')
                movie_title_normalized = normalize_title(movie_title.split('(')[0].strip(), target_lang='en')

                logger.info(f"Red button {i} title: {red_button_title_cleaned}, Expected movie title: {movie_title_cleaned}")

                # Extract the year from the red button title, ignoring resolution strings
                red_button_year = extract_year(red_button_title_text, ignore_resolution=True)

                # Extract the expected year from the provided movie title (if it exists)
                expected_year = extract_year(movie_title)

                # Use fuzzy matching instead of startswith (also allow partial matching for more relaxed comparisons)
                title_match_ratio = fuzz.partial_ratio(red_button_title_cleaned.lower(), movie_title_cleaned.lower())
                title_match_threshold = 75  # You can lower or raise this based on how aggressive you want it to be.

                # Additional title comparison logic with fuzzy matching and threshold
                title_matched = False
                if (
                    title_match_ratio >= title_match_threshold or  # Fuzzy match title (relaxed match)
                    movie_title_normalized.startswith(red_button_title_normalized)  # Backwards title check
                ):
                    # Titles match within boundaries.
                    title_matched = True  # Consider this a valid match.

                # Skip year comparison for TV shows or if either year is None
                if is_tv_show or red_button_year is None or expected_year is None:
                    year_matched = True  # Skip year comparison
                else:
                    # Expanded year match check with more leeway (±2 years to avoid overly strict checks)
                    year_matched = abs(red_button_year - expected_year) <= 2

                # Check if the season matches the requested season (only for TV shows)
                if is_tv_show and normalized_seasons:
                    # Extract the season from the red button title
                    found_season = extract_season(red_button_title_text)
                    logger.info(f"Found season (raw): {found_season}")
                    logger.info(f"Requested seasons (normalized): {normalized_seasons}")

                    # Convert found_season to a string (if it's not already)
                    found_season_str = str(found_season) if found_season is not None else None

                    # Normalize the found season to match the format of normalized_seasons
                    found_season_normalized = f"Season {found_season_str}" if found_season_str and found_season_str.isdigit() else found_season_str
                    logger.info(f"Found season (normalized): {found_season_normalized}")

                    # Check if the found season matches any of the requested seasons
                    if found_season_normalized:
                        if found_season_normalized in normalized_seasons:
                            # Check if the season has already been confirmed
                            if found_season_normalized in confirmed_seasons:
                                logger.info(f"Season {found_season_normalized} has already been confirmed. Skipping this red button.")
                                found_red_button_for_season = True
                                confirmed_seasons.add(found_season_normalized)
                                return confirmation_flag, confirmed_seasons  # Exit early if already confirmed

                            logger.info(f"Found a matching season {found_season_normalized} in the requested seasons. Proceeding with this red button.")
                            found_red_button_for_season = True
                        else:
                            logger.warning(f"Season mismatch for red button {i}: Found season {found_season_normalized}, but requested seasons are {normalized_seasons}. Skipping.")
                            continue  # Skip this red button if the season doesn't match

                if title_matched and year_matched:
                    logger.info(f"Found a match on red button {i} - {red_button_title_cleaned}. Skipping...")
                    # Handle the RD button selection or matching action here
                    confirmation_flag = True
                    # Add the confirmed season to the set
                    if is_tv_show and found_season_normalized:
                        confirmed_seasons.add(found_season_normalized)
                        logger.info(f"Added {found_season_normalized} to confirmed seasons: {confirmed_seasons}")
                        confirmation_flag = True  # Mark as confirmed match.

                else:
                    # If no match, continue with the next available RD red button.
                    logger.warning(f"No match for red button {i}: Title - {red_button_title_cleaned}, Year - {red_button_year}. Moving to next red button.")

            except NoSuchElementException as e:
                logger.warning(f"Could not find title associated with red button {i}: {e}")
                continue  # If a title is not found for a red button, continue to the next one

        # If no red buttons were found for the current season, log and continue to the next season
        if not found_red_button_for_season and is_tv_show and normalized_seasons:
            logger.info(f"No red buttons found for the current season. Continuing to the next season.")

    except NoSuchElementException:
        logger.info("No red buttons (100% RD) detected. Proceeding with optional fallback.")

    return confirmation_flag, confirmed_seasons

### Search Function to Reuse Browser
def search_on_debrid(movie_title, driver, extra_data=None):
    logger.info(f"Starting Selenium automation for movie: {movie_title}")

    # Extract requested seasons from the extra data
    requested_seasons = parse_requested_seasons(extra_data) if extra_data else []
    normalized_seasons = [normalize_season(season) for season in requested_seasons]

    # Determine if the media is a TV show
    is_tv_show = any(item['name'] == 'Requested Seasons' for item in extra_data) if extra_data else False
    logger.info(f"Media type: {'TV Show' if is_tv_show else 'Movie'}")

    # Check if the driver is None before proceeding to avoid NoneType errors
    if not driver:
        logger.error("Selenium WebDriver is not initialized. Attempting to reinitialize.")
        driver = initialize_browser()

    debrid_media_manager_base_url = "https://debridmediamanager.com/search?query="
    
    # Use urllib to encode the movie title safely, handling all special characters including '&', ':', '(', ')'
    encoded_movie_title = urllib.parse.quote(movie_title)
    
    url = debrid_media_manager_base_url + encoded_movie_title
    logger.info(f"Search URL: {url}")

    try:
        driver.get(url)
        logger.success(f"Navigated to search results page for {movie_title}.")
        
        # Attempt to locate the elements
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, f"//a[contains(@href, '/movie/') or contains(@href, '/show/')]"))
            )
            logger.info("Elements are present. Continuing...")
        except TimeoutException:
            logger.error(f"Timeout while waiting for search results elements for {movie_title}. Stopping processing.")
            return

        # Clean and normalize the movie title (remove year in parentheses)
        movie_title_cleaned = movie_title.split('(')[0].strip()
        movie_title_normalized = normalize_title(movie_title_cleaned)
        logger.info(f"Searching for normalized movie title: {movie_title_normalized}")

        # Find the movie result elements
        try:
            movie_elements = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, f"//a[contains(@href, '/movie/') or contains(@href, '/show/')]"))
            )

            # Iterate over the movie elements to find the correct one
            for movie_element in movie_elements:
                movie_title_element = movie_element.find_element(By.XPATH, ".//h3")
                movie_year_element = movie_element.find_element(By.XPATH, ".//div[contains(@class, 'text-gray-600')]")
                
                search_title_cleaned = movie_title_element.text.strip()
                search_title_normalized = normalize_title(search_title_cleaned)
                search_year = extract_year(movie_year_element.text)

                # Extract the expected year from the provided movie title (if it exists)
                expected_year = extract_year(movie_title)

                # Use fuzzy matching to allow for minor differences in titles
                title_match_ratio = fuzz.ratio(search_title_normalized.lower(), movie_title_normalized.lower())
                logger.info(f"Comparing '{search_title_normalized}' with '{movie_title_normalized}' (Match Ratio: {title_match_ratio})")

                # Check if the titles match (with a threshold) and if the years are within ±1 year range
                if title_match_ratio >= 69 and (expected_year is None or abs(search_year - expected_year) <= 1):
                    logger.info(f"Found matching movie: {search_title_cleaned} ({search_year})")
                    
                    # Click on the parent <a> tag (which is the clickable link)
                    parent_link = movie_element
                    parent_link.click()
                    logger.success(f"Clicked on the movie link for {search_title_cleaned}")
                    break
            else:
                logger.error(f"No matching movie found for {movie_title_cleaned} ({expected_year})")
                return
        except (TimeoutException, NoSuchElementException) as e:
            logger.critical(f"Failed to find or click on the search result: {movie_title}")
            return

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
                    logger.success(f"Found {torrents_count} available torrents in RD.")
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
                logger.success(f"{torrents_count} torrents found in RD. Proceeding with RD checks.")
            # Initialize a set to track confirmed seasons
            confirmed_seasons = set()
            # Step 7: Check if any red button (RD 100%) exists again before continuing
            confirmation_flag, confirmed_seasons = check_red_buttons(driver, movie_title, normalized_seasons, confirmed_seasons, is_tv_show)

            # If a red button is confirmed, skip further processing
            if confirmation_flag:
                logger.success("Red button confirmed. Checking if Movie or TV Show...")
            # If a red button is confirmed and it's not a TV show, skip further processing
            if confirmation_flag and not is_tv_show:
                logger.success("Red button confirmed for Movie. Skipping further processing.")
                return confirmation_flag

            # After clicking the matched movie title, we now check the popup boxes for Instant RD buttons
            # Step 8: Check the result boxes with the specified class for "Instant RD"
            try:
                if is_tv_show and normalized_seasons:
                    logger.info(f"Processing TV show seasons for: {movie_title}")

                    # Process each requested season sequentially
                    for season in normalized_seasons:
                        # Skip this season if it has already been confirmed
                        if season in confirmed_seasons:
                            logger.info(f"Season {season} has already been confirmed. Skipping.")
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
                                        logger.success(f"Successfully handled complete season pack in box {i}.")
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
                                        logger.success(f"Successfully handled season {season} in box {i}.")
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

### Webhook Endpoint ###
@app.post("/jellyseer-webhook/")
async def jellyseer_webhook(request: Request, background_tasks: BackgroundTasks):
    # Log the raw incoming payload for debugging
    raw_payload = await request.json()
    #logger.info(f"Raw incoming webhook payload: {raw_payload}")

    try:
        # Parse the payload using the WebhookPayload model
        payload = WebhookPayload(**raw_payload)
    except ValidationError as e:
        # Log the validation error details
        logger.error(f"Payload validation error: {e}")
        raise HTTPException(status_code=422, detail=str(e))

    # Check if this is a test notification
    if payload.notification_type == "TEST_NOTIFICATION":
        logger.success("Test notification received and processed successfully.")
        return {"status": "success", "message": "Test notification processed successfully."}

    # Log the specific event from the payload
    logger.success(f"Received webhook with event: {payload.event}")

    # Ensure media is not None before accessing its attributes
    if payload.media is None:
        logger.error("Media information is missing in the payload")
        raise HTTPException(status_code=400, detail="Media information is missing in the payload")

    media_type = payload.media.media_type
    logger.success(f"Received webhook with event: {payload.event} for {media_type.capitalize()}")

    # Extract tmdbId from the payload
    tmdb_id = payload.media.tmdbId
    if not tmdb_id:
        logger.error("TMDB ID is missing in the payload")
        raise HTTPException(status_code=400, detail="TMDB ID is missing in the payload")

    # Log the extracted tmdb_id
    logger.info(f"Extracted tmdbId: {tmdb_id}")

    # Fetch media details from Trakt using tmdb_id
    media_details = get_media_details_from_trakt(payload.media.tmdbId, payload.media.media_type)
    if not media_details:
        logger.error(f"Failed to fetch {payload.media.media_type} details from Trakt")
        raise HTTPException(status_code=500, detail=f"Failed to fetch {payload.media.media_type} details from Trakt")

    movie_or_tv_title = f"{media_details['title']} ({media_details['year']})"
    logger.info(f"Fetched {media_type.capitalize()} details: {movie_or_tv_title}")

    background_tasks.add_task(add_request_to_queue, movie_or_tv_title, payload.extra)
    logger.info(f"Returning response: {media_details['title']} ({media_details['year']})")

    return {"status": "success", "title": media_details['title'], "year": media_details['year']}

def schedule_token_refresh():
    """Schedule the token refresh every 10 minutes."""
    scheduler.add_job(check_and_refresh_access_token, 'interval', minutes=10)
    logger.info("Scheduled token refresh every 10 minutes.")

### Background Task to Process Overseerr Requests Periodically ###
@app.on_event("startup")
async def startup_event():
    global processing_task
    logger.info('Starting SeerrBridge...')

    # Check and refresh access token before any other initialization
    check_and_refresh_access_token()

    # Always initialize the browser when the bot is ready
    try:
        await initialize_browser()
    except Exception as e:
        logger.error(f"Failed to initialize browser: {e}")
        return

    # Start the request processing task if not already started
    if processing_task is None:
        processing_task = asyncio.create_task(process_requests())
        logger.info("Started request processing task.")

    # Schedule the token refresh
    schedule_token_refresh()
    scheduler.start()

    # Check if automatic background task is enabled
    if ENABLE_AUTOMATIC_BACKGROUND_TASK:
        logger.info("Automatic background task is enabled. Starting initial check and recurring task.")
        try:
            # Run the initial check immediately
            await process_movie_requests()
            logger.info("Completed initial check of movie requests.")

            # Schedule the rechecking of movie requests every REFRESH_INTERVAL_MINUTES
            schedule_recheck_movie_requests()
        except Exception as e:
            logger.error(f"Error while processing movie requests: {e}")
    else:
        logger.info("Automatic background task is disabled. Skipping initial check and recurring task.")

def schedule_recheck_movie_requests():
    # Correctly schedule the job with the REFRESH_INTERVAL_MINUTES configured interval.
    scheduler.add_job(process_movie_requests, 'interval', minutes=REFRESH_INTERVAL_MINUTES)
    logger.info(f"Scheduled rechecking movie requests every {REFRESH_INTERVAL_MINUTES} minute(s).")

async def on_close():
    await shutdown_browser()  # Ensure browser is closed when the bot closes

async def check_overseerr_base_url(url: str) -> bool:
    try:
        logger.info(f"Attempting to check Overseerr base URL: {url}")
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            logger.info(f"Response from Overseerr base URL: {response.status_code}")
            return response.status_code == 200 or 307
    except Exception as e:
        logger.error(f"Error checking Overseerr base URL: {e}")
        return False

@app.get("/", response_class=HTMLResponse)
async def get_index():
    with open("index.html", "r", encoding="utf-8") as file:
        return HTMLResponse(content=file.read())

@app.get("/env-vars")
async def get_env_vars():
    overseerr_base_status = await check_overseerr_base_url(OVERSEERR_BASE) if OVERSEERR_BASE else False

    return {
        # Sensitive information (show emojis for "Set" or "Missing")
        "RD_ACCESS_TOKEN": "✅ Set" if RD_ACCESS_TOKEN else "❌ Missing",
        "RD_REFRESH_TOKEN": "✅ Set" if RD_REFRESH_TOKEN else "❌ Missing",
        "RD_CLIENT_ID": "✅ Set" if RD_CLIENT_ID else "❌ Missing",
        "RD_CLIENT_SECRET": "✅ Set" if RD_CLIENT_SECRET else "❌ Missing",
        "OVERSEERR_API_KEY": "✅ Set" if OVERSEERR_API_KEY else "❌ Missing",
        "TRAKT_API_KEY": "✅ Set" if TRAKT_API_KEY else "❌ Missing",
        # Non-sensitive information (show emojis for "Enabled" or "Disabled")
        "HEADLESS_MODE": "✅ Enabled" if HEADLESS_MODE else "❌ Disabled",
        "ENABLE_AUTOMATIC_BACKGROUND_TASK": "✅ Enabled" if ENABLE_AUTOMATIC_BACKGROUND_TASK else "❌ Disabled",
        # Non-sensitive information (show actual values)
        "TORRENT_FILTER_REGEX": TORRENT_FILTER_REGEX if TORRENT_FILTER_REGEX else "❌ Not Set",
        "REFRESH_INTERVAL_MINUTES": REFRESH_INTERVAL_MINUTES if REFRESH_INTERVAL_MINUTES else "❌ Not Set",
        # URL check
        "OVERSEERR_BASE": "✅ Valid" if overseerr_base_status else "❌ Invalid",
        # Max Movie Size
        "MAX_MOVIE_SIZE": MAX_MOVIE_SIZE if MAX_MOVIE_SIZE else "5",
        # Max Episode Size
        "MAX_EPISODE_SIZE": MAX_EPISODE_SIZE if MAX_EPISODE_SIZE else "1",
    }

# Main entry point for running the FastAPI server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8777)
