# =============================================================================
# Soluify.com  |  Your #1 IT Problem Solver  |  {SeerrBridge v0.3.3.1}
# =============================================================================
#  __         _
# (_  _ |   .(_
# __)(_)||_||| \/
#              /
# © 2024
# -----------------------------------------------------------------------------
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel, Field, ValidationError, field_validator
from typing import Optional, List, Dict, Any
import asyncio
import json
import time
import os
import sys
import urllib.parse
import re
import inflect
import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
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
    requestedBy_settings_discordId: str
    requestedBy_settings_telegramChatId: str

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
    media: MediaInfo
    request: RequestInfo
    issue: Optional[IssueInfo] = None  # Allow issue to be None
    comment: Optional[CommentInfo] = None  # Allow comment to be None
    extra: List[Dict[str, Any]] = []

def refresh_access_token():
    global RD_REFRESH_TOKEN, RD_ACCESS_TOKEN, driver

    TOKEN_URL = "https://api.real-debrid.com/oauth/v2/token"

    # Prepare token refresh request payload
    data = {
        'client_id': RD_CLIENT_ID,
        'client_secret': RD_CLIENT_SECRET,
        'code': RD_REFRESH_TOKEN,
        'grant_type': 'http://oauth.net/grant_type/device/1.0'
    }

    try:
        logger.info("Requesting a new access token with the refresh token.")
        response = requests.post(TOKEN_URL, data=data)
        response_data = response.json()

        if response.status_code == 200:
            # Calculate new expiry time (24 hours from now) in milliseconds
            expiry_time = int((datetime.now() + timedelta(hours=24)).timestamp() * 1000)

            # Update the access token with new expiry time
            RD_ACCESS_TOKEN = json.dumps({
                "value": response_data['access_token'],
                "expiry": expiry_time
            })
            logger.success("Successfully refreshed access token.")
            update_env_file()  # Update the .env file with the new token

            # Update local storage with the new token
            if driver:
                driver.execute_script(f"""
                    localStorage.setItem('rd:accessToken', '{RD_ACCESS_TOKEN}');
                """)
                logger.info("Updated Real-Debrid credentials in local storage after token refresh.")

                # Refresh the page to apply the local storage values
                driver.refresh()
                logger.success("Refreshed the page after updating local storage with the new token.")

        else:
            logger.error(f"Failed to refresh access token: {response_data.get('error_description', 'Unknown error')}")
    except Exception as e:
        logger.error(f"Error refreshing access token: {e}")

def update_env_file():
    """Update the .env file with the new access token."""
    with open('.env', 'r') as file:
        lines = file.readlines()

    with open('.env', 'w') as file:
        for line in lines:
            if line.startswith('RD_ACCESS_TOKEN'):
                # Update the existing access token line
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

        options = Options()
        # Use the HEADLESS_MODE from .env
        if HEADLESS_MODE:
            options.add_argument('--headless')  # Run browser in headless mode
        options.add_argument('--disable-gpu')  # Disable GPU to save resources
        options.add_argument('--no-sandbox')  # Required for running Chrome in Docker
        options.add_argument('--disable-dev-shm-usage')  # Overcome limited /dev/shm size in containers        chromedriver_path = os.getenv('CHROMEDRIVER_PATH')
        
        chromedriver_path = os.getenv('CHROMEDRIVER_PATH')
        service = ChromeService(executable_path=chromedriver_path)
        driver = uc.Chrome(service=service, options=options)
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
            Object.defineProperty(navigator, 'webdriver', {
              get: () => undefined
            })
          """
        })
        logger.success("Initialized Selenium WebDriver.")

        # Navigate to Debrid Media Manager
        driver.get("https://debridmediamanager.com")
        logger.success("Navigated to Debrid Media Manager start page.")

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
        movie_title = await request_queue.get()  # Wait for the next request in the queue
        logger.info(f"Processing movie request: {movie_title}")
        try:
            await asyncio.to_thread(search_on_debrid, movie_title, driver)  # Process the request
        except Exception as ex:
            logger.critical(f"Error processing movie request {movie_title}: {ex}")
        finally:
            request_queue.task_done()  # Mark the request as done

### Function to add requests to the queue
async def add_request_to_queue(movie_title):
    if request_queue.full():
        logger.warning(f"Request queue is full. Cannot add movie: {movie_title}")
        return False
    
    await request_queue.put(movie_title)
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

def get_movie_details_from_trakt(tmdb_id: str) -> Optional[dict]:
    global trakt_api_calls, last_reset_time

    # Check if the rate limit period has elapsed
    current_time = time.time()
    if current_time - last_reset_time >= TRAKT_RATE_LIMIT_PERIOD:
        trakt_api_calls = 0
        last_reset_time = current_time

    # Check if we have reached the rate limit
    if trakt_api_calls >= TRAKT_RATE_LIMIT:
        logger.warning("Trakt API rate limit reached. Waiting for the next period.")
        time.sleep(TRAKT_RATE_LIMIT_PERIOD - (current_time - last_reset_time))
        trakt_api_calls = 0
        last_reset_time = time.time()

    url = f"https://api.trakt.tv/search/tmdb/{tmdb_id}?type=movie"
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
                movie_info = data[0]['movie']
                return {
                    "title": movie_info['title'],
                    "year": movie_info['year']
                }
            else:
                logger.error("Movie details for ID not found in Trakt API response.")
                return None
        else:
            logger.error(f"Trakt API request failed with status code {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching movie details from Trakt API: {e}")
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
        logger.info(f"Processing request with TMDB ID {tmdb_id} and media ID {media_id}")
        
        movie_details = get_movie_details_from_trakt(tmdb_id)
        if not movie_details:
            logger.error(f"Failed to get movie details for TMDB ID {tmdb_id}")
            continue
        
        movie_title = f"{movie_details['title']} ({movie_details['year']})"
        logger.info(f"Processing movie request: {movie_title}")
        
        try:
            confirmation_flag = await asyncio.to_thread(search_on_debrid, movie_title, driver)  # Process the request and get the confirmation flag
            if confirmation_flag:
                if mark_completed(media_id, tmdb_id):
                    logger.success(f"Marked media {media_id} as completed in overseerr")
                else:
                    logger.error(f"Failed to mark media {media_id} as completed in overseerr")
            else:
                logger.info(f"Media {media_id} was not properly confirmed. Skipping marking as completed.")
        except Exception as ex:
            logger.critical(f"Error processing movie request {movie_title}: {ex}")

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




### Search Function to Reuse Browser
def search_on_debrid(movie_title, driver):
    logger.info(f"Starting Selenium automation for movie: {movie_title}")

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
        # Directly jump to the search results page after login
        driver.get(url)
        logger.success(f"Navigated to search results page for {movie_title}.")
        
        # Wait for the results page to load dynamically
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/movie/')]"))
        )

        # Clean and normalize the movie title (remove year in parentheses)
        movie_title_cleaned = movie_title.split('(')[0].strip()
        movie_title_normalized = normalize_title(movie_title_cleaned)
        logger.info(f"Searching for normalized movie title: {movie_title_normalized}")

        # Find the movie result elements
        try:
            movie_elements = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, f"//a[contains(@href, '/movie/')]"))
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
                if title_match_ratio >= 85 and (expected_year is None or abs(search_year - expected_year) <= 1):
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
            
            # Step 2: Check if any red buttons (RD 100%) exist and verify the title for each
            try:
                red_buttons_elements = driver.find_elements(By.XPATH, "//button[contains(@class, 'bg-red-900/30')]")
                logger.info(f"Found {len(red_buttons_elements)} red button(s) (100% RD). Verifying titles before deciding to skip.")

                for i, red_button_element in enumerate(red_buttons_elements, start=1):
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

                        # Expanded year match check with more leeway (±2 years to avoid overly strict checks)
                        year_matched = (expected_year is None or abs(red_button_year - expected_year) <= 2)

                        if title_matched and year_matched:
                            logger.info(f"Found a match on red button {i} - {red_button_title_cleaned}. Skipping...")
                            # Handle the RD button selection or matching action here
                            confirmation_flag = True  # Mark as confirmed match.
                            return confirmation_flag  # Once we click a matching button, we stop further checks.

                        else:
                            # If no match, continue with the next available RD red button.
                            logger.warning(f"No match for red button {i}: Title - {red_button_title_cleaned}, Year - {red_button_year}. Moving to next red button.")

                    except NoSuchElementException as e:
                        logger.warning(f"Could not find title associated with red button {i}: {e}")
                        continue  # If a title is not found for a red button, continue to the next one
            except NoSuchElementException:
                logger.info("No red buttons (100% RD) detected. Proceeding with optional fallback.")


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
            
            # Step 7: Check if any red button (RD 100%) exists again before continuing
            try:
                red_buttons_elements = driver.find_elements(By.XPATH, "//button[contains(@class, 'bg-red-900/30')]")
                logger.info(f"Found {len(red_buttons_elements)} red button(s) (100% RD). Verifying titles before deciding to skip.")

                for i, red_button_element in enumerate(red_buttons_elements, start=1):
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

                        # Expanded year match check with more leeway (±2 years to avoid overly strict checks)
                        year_matched = (expected_year is None or abs(red_button_year - expected_year) <= 2)

                        if title_matched and year_matched:
                            logger.info(f"Found a match on red button {i} - {red_button_title_cleaned}. Skipping...")
                            # Handle the RD button selection or matching action here
                            confirmation_flag = True  # Mark as confirmed match.
                            return confirmation_flag  # Once we click a matching button, we stop further checks.

                        else:
                            # If no match, continue with the next available RD red button.
                            logger.warning(f"No match for red button {i}: Title - {red_button_title_cleaned}, Year - {red_button_year}. Moving to next red button.")

                    except NoSuchElementException as e:
                        logger.warning(f"Could not find title associated with red button {i}: {e}")
                        continue  # If a title is not found for a red button, continue to the next one
            except NoSuchElementException:
                logger.info("No red buttons (100% RD) detected. Proceeding with optional fallback.")


            # After clicking the matched movie title, we now check the popup boxes for Instant RD buttons
            # Step 8: Check the result boxes with the specified class for "Instant RD"
            try:
                result_boxes = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'border-black')]"))
                )

                for i, result_box in enumerate(result_boxes, start=1):
                    try:
                        # Extract the title from the result box
                        title_element = result_box.find_element(By.XPATH, ".//h2")
                        title_text = title_element.text.strip()
                        logger.info(f"Box {i} title: {title_text}")

                        # Extract the year from the title
                        box_year = extract_year(title_text)
                        if box_year is None:
                            logger.warning(f"Could not extract year from '{title_text}'. Skipping box {i}.")
                            continue

                        # Clean both the movie title and the box title for comparison
                        movie_title_cleaned = clean_title(movie_title.split('(')[0].strip(), target_lang='en')
                        title_text_cleaned = clean_title(title_text.split(str(box_year))[0].strip(), target_lang='en')

                        movie_title_normalized = normalize_title(movie_title.split('(')[0].strip(), target_lang='en')
                        title_text_normalized = normalize_title(title_text.split(str(box_year))[0].strip(), target_lang='en')


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

                        # Compare the year with the expected year (allow ±1 year)
                        expected_year = extract_year(movie_title)
                        if expected_year is not None and abs(box_year - expected_year) > 1:
                            logger.warning(f"Year mismatch for box {i}: {box_year} (Expected: {expected_year}). Skipping.")
                            continue  # Skip this box if the year doesn't match

                        # After navigating to the movie details page and verifying the title/year
                        if prioritize_buttons_in_box(result_box):
                            logger.info(f"Successfully handled buttons in box {i}.")
                            confirmation_flag = True  # Mark confirmation as successful
                        else:
                            logger.warning(f"Failed to handle buttons in box {i}. Skipping.")
                        # After clicking, check if the button has changed to "RD (0%)" or "RD (100%)"
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
                                continue  # Move to the next box

                            # If it's "RD (100%)", we are done with this entry
                            if "RD (100%)" in rd_button_text:
                                logger.success(f"RD (100%) button detected. {i} {title_text}. This entry is complete.")
                                confirmation_flag = True
                                return confirmation_flag  # Exit the function as we've found a matching red button
                                break  # Break out of the loop since the task is complete

                        except TimeoutException:
                            logger.warning(f"Timeout waiting for RD button status change in box {i}.")
                            continue  # Move to the next box if a timeout occurs

                    except NoSuchElementException as e:
                        logger.warning(f"Could not find 'Instant RD' button in box {i}: {e}")
                    except TimeoutException as e:
                        logger.warning(f"Timeout when processing box {i}: {e}")

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

    # Log the specific event from the payload
    logger.success(f"Received webhook with event: {payload.event}")

    # Extract tmdbId from the payload
    tmdb_id = payload.media.tmdbId
    if not tmdb_id:
        logger.error("TMDB ID is missing in the payload")
        raise HTTPException(status_code=400, detail="TMDB ID is missing in the payload")

    # Log the extracted tmdb_id
    logger.info(f"Extracted tmdbId: {tmdb_id}")

    # Fetch movie details from Trakt using tmdb_id
    movie_details = get_movie_details_from_trakt(tmdb_id)
    if not movie_details:
        logger.error("Failed to fetch movie details from Trakt")
        raise HTTPException(status_code=500, detail="Failed to fetch movie details from Trakt")

    # Log the fetched movie details
    movie_title = f"{movie_details['title']} ({movie_details['year']})"
    logger.info(f"Fetched movie details: {movie_title}")

    # Add movie request to background processing queue
    background_tasks.add_task(add_request_to_queue, movie_title)
    
    # Log the response before returning
    logger.info(f"Returning response: {movie_details['title']} ({movie_details['year']})")
    
    return {"status": "success", "movie_title": movie_details['title'], "movie_year": movie_details['year']}

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
    # Ask user if they want to proceed with the initial check and recurring task
    if ENABLE_AUTOMATIC_BACKGROUND_TASK:
        user_input = 'y'
    else: 
        user_input = await get_user_input()
    
    if user_input == 'y':
        try:
            # Run the initial check immediately
            await process_movie_requests()
            logger.info("Completed initial check of movie requests.")

            # Schedule the rechecking of movie requests every 2 hours
            schedule_recheck_movie_requests()
        except Exception as e:
            logger.error(f"Error while processing movie requests: {e}")

    elif user_input == 'n':
        logger.info("Initial check and recurring task were skipped by user input.")
        return  # Exit the function if the user opts out

    else:
        logger.warning("Invalid input. Please restart the bot and enter 'y' or 'n'.")


def schedule_recheck_movie_requests():
    # Correctly schedule the job with the REFRESH_INTERVAL_MINUTES configured interval.
    scheduler.add_job(process_movie_requests, 'interval', minutes=REFRESH_INTERVAL_MINUTES)
    logger.info(f"Scheduled rechecking movie requests every {REFRESH_INTERVAL_MINUTES} minute(s).")



async def on_close():
    await shutdown_browser()  # Ensure browser is closed when the bot closes

# Main entry point for running the FastAPI server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8777)
