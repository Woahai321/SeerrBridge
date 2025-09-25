"""
Browser automation module for SeerrBridge
Handles Selenium browser initialization and interactions with Debrid Media Manager
"""
import platform
import time
import os
import requests
import zipfile
import io
from loguru import logger
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager, ChromeType
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException, TimeoutException, ElementClickInterceptedException
from fuzzywuzzy import fuzz

from seerr.config import (
    HEADLESS_MODE, 
    RD_ACCESS_TOKEN, 
    RD_CLIENT_ID, 
    RD_CLIENT_SECRET, 
    RD_REFRESH_TOKEN,
    TORRENT_FILTER_REGEX,
    MAX_MOVIE_SIZE,
    MAX_EPISODE_SIZE
)

# Global driver variable to hold the Selenium WebDriver
driver = None

# Global library stats
library_stats = {
    "torrents_count": 0,
    "total_size_tb": 0.0,
    "last_updated": None
}

def get_latest_chrome_driver():
    """
    Fetch the latest stable Chrome driver from Google's Chrome for Testing.
    Returns the path to the downloaded chromedriver executable.
    """
    try:
        # Get the current operating system
        current_os = platform.system().lower()
        
        # Map OS to platform identifier used by Chrome for Testing
        platform_map = {
            'windows': 'win32' if platform.architecture()[0] == '32bit' else 'win64',
            'linux': 'linux64',
            'darwin': 'mac-arm64' if platform.processor() == 'arm' else 'mac-x64'
        }
        
        os_platform = platform_map.get(current_os)
        if not os_platform:
            logger.error(f"Unsupported operating system: {current_os}")
            return None
            
        # Fetch latest stable version information
        logger.info(f"Fetching latest stable Chrome driver information for {os_platform}")
        response = requests.get("https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json")
        response.raise_for_status()
        
        data = response.json()
        stable_version = data['channels']['Stable']['version']
        downloads = data['channels']['Stable']['downloads']['chromedriver']
        
        # Find the download URL for the current platform
        download_url = None
        for item in downloads:
            if item['platform'] == os_platform:
                download_url = item['url']
                break
                
        if not download_url:
            logger.error(f"Could not find Chrome driver download for platform: {os_platform}")
            return None
            
        # Create a directory for the driver if it doesn't exist
        driver_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chromedriver")
        os.makedirs(driver_dir, exist_ok=True)
        
        # Download and extract the driver
        logger.info(f"Downloading Chrome driver v{stable_version} from {download_url}")
        response = requests.get(download_url)
        response.raise_for_status()
        
        # Extract the zip file
        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
            zip_file.extractall(driver_dir)
            
        # Find the chromedriver executable in the extracted files
        if current_os == 'windows':
            driver_path = os.path.join(driver_dir, "chromedriver-" + os_platform, "chromedriver.exe")
        else:
            driver_path = os.path.join(driver_dir, "chromedriver-" + os_platform, "chromedriver")
            # Make the driver executable on Unix-like systems
            os.chmod(driver_path, 0o755)
            
        logger.success(f"Successfully downloaded and extracted Chrome driver v{stable_version} to {driver_path}")
        return driver_path
        
    except Exception as e:
        logger.error(f"Error downloading Chrome driver: {e}")
        return None

async def initialize_browser():
    """Initialize the Selenium WebDriver and set up the browser."""
    global driver
    if driver is None:
        logger.info("Starting persistent browser session.")
        # Detect the current operating system
        current_os = platform.system().lower() # Returns 'windows', 'linux', or 'darwin' (macOS)
        logger.info(f"Detected operating system: {current_os}")
        options = Options()
        ### Handle Docker/Linux-specific configurations
        if current_os == "linux" and os.getenv("RUNNING_IN_DOCKER", "false").lower() == "true":
            logger.info("Detected Linux environment inside Docker. Applying Linux-specific configurations.")
            # Explicitly set the Chrome binary location
            options.binary_location = os.getenv("CHROME_BIN", "/usr/bin/google-chrome")
            # Enable headless mode for Linux/Docker environments
            options.add_argument("--headless=new") # Updated modern headless flag
            options.add_argument("--no-sandbox") # Required for running as root in Docker
            options.add_argument("--disable-dev-shm-usage") # Handle shared memory limitations
            options.add_argument("--disable-gpu") # Disable GPU rendering for headless environments
            options.add_argument("--disable-setuid-sandbox") # Bypass setuid sandbox
        ### Handle Windows-specific configurations
        elif current_os == "windows":
            logger.info("Detected Windows environment. Applying Windows-specific configurations.")
        if HEADLESS_MODE:
            options.add_argument("--headless=new") # Modern headless mode for Chrome
        options.add_argument("--disable-gpu") # Disable GPU for Docker compatibility
        options.add_argument("--no-sandbox") # Required for running browser as root
        options.add_argument("--disable-dev-shm-usage") # Disable shared memory usage restrictions
        options.add_argument("--disable-setuid-sandbox") # Disable sandboxing for root permissions
        options.add_argument("--enable-logging")
        options.add_argument("--window-size=1920,1080") # Set explicit window size to avoid rendering issues
        # WebDriver options to suppress infobars and disable automation detection
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36")
        try:
            # Get the latest Chrome driver from Google's Chrome for Testing
            chrome_driver_path = get_latest_chrome_driver()
           
            if chrome_driver_path and os.path.exists(chrome_driver_path):
                logger.info(f"Using Chrome driver from Chrome for Testing: {chrome_driver_path}")
                driver = webdriver.Chrome(service=Service(chrome_driver_path), options=options)
            else:
                # Fallback to WebDriver Manager if download fails
                logger.warning("Failed to get Chrome driver from Chrome for Testing. Falling back to WebDriver Manager.")
                driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            # Suppress 'webdriver' detection
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                Object.defineProperty(navigator, 'webdriver', {
                  get: () => undefined
                })
                """
            })
            logger.info("Initialized Selenium WebDriver successfully.")
            # Navigate to an initial page to confirm browser works
            driver.get("https://debridmediamanager.com")
            logger.info("Navigated to Debrid Media Manager page.")
        except Exception as e:
            logger.error(f"Failed to initialize Selenium WebDriver: {e}")
            driver = None # Ensure driver is None on failure
            raise e
        # If initialization succeeded, continue with setup
        if driver:
            try:
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
               
                # Handle potential premium expiration modal
                try:
                    modal_h2 = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, "//h2[contains(text(), 'Premium Expiring Soon')]"))
                    )
                    logger.info("Premium Expiring Soon modal detected.")
                    # Extract the message to get days
                    p_element = driver.find_element(By.XPATH, "//p[contains(text(), 'Your Real-Debrid premium subscription will expire in')]")
                    message = p_element.text.strip()
                    import re
                    days_match = re.search(r'expire in (\d+) days', message)
                    days = int(days_match.group(1)) if days_match else "UNKNOWN"
                    # Log distinct message in big caps
                    logger.warning(f"YOUR REAL-DEBRID PREMIUM WILL EXPIRE IN {days} DAYS!!!")
                    # Click Cancel to dismiss
                    cancel_button = driver.find_element(By.XPATH, "//button[text()='Cancel']")
                    cancel_button.click()
                    logger.info("Dismissed the premium expiration modal by clicking Cancel.")
                    time.sleep(1)  # Wait briefly for modal to disappear
                except TimeoutException:
                    logger.info("No premium expiration modal found. Proceeding.")
               
                # After handling modal, click on "Settings" button
                try:
                    logger.info("Attempting to click the 'Settings' button.")
                    settings_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[.//span[contains(text(), 'Settings')]]"))
                    )
                    settings_button.click()
                    logger.info("Clicked on 'Settings' button.")
                    logger.info("Locating maximum movie size select element in 'Settings'.")
                    max_movie_select_elem = WebDriverWait(driver, 10).until(
                        EC.visibility_of_element_located((By.ID, "dmm-movie-max-size"))
                    )
                    # Initialize Select class with the <select> WebElement
                    select_obj = Select(max_movie_select_elem)
                    # Select size specified in the .env file
                    select_obj.select_by_value(MAX_MOVIE_SIZE)
                    logger.info("Biggest Movie Size Selected as {} GB.".format(MAX_MOVIE_SIZE))
                    # MAX EPISODE SIZE: Locate the maximum series size select element
                    logger.info("Locating maximum series size select element in 'Settings'.")
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
                    default_filter_input.clear() # Clear any existing filter
                    # Use the regex from .env
                    default_filter_input.send_keys(TORRENT_FILTER_REGEX)
                    logger.info(f"Inserted regex into 'Default torrents filter' input box: {TORRENT_FILTER_REGEX}")
                    settings_button.click()
                    logger.info("Closed 'Settings' to save settings.")
                except (TimeoutException, NoSuchElementException, ElementClickInterceptedException) as ex:
                    logger.error(f"Error while interacting with the settings: {ex}")
                    logger.warning("Continuing without applying custom settings (TORRENT_FILTER_REGEX, MAX_MOVIE_SIZE, MAX_EPISODE_SIZE)")
                # Navigate to the library section
                logger.info("Navigating to the library section.")
                driver.get("https://debridmediamanager.com/library")
                # Wait for 2 seconds on the library page before further processing
                try:
                    # Ensure the library page has loaded correctly (e.g., wait for a specific element on the library page)
                    library_element = WebDriverWait(driver, 2).until(
                        EC.presence_of_element_located((By.XPATH, "//div[@id='library-content']")) # Adjust the XPath as necessary
                    )
                    logger.info("Library section loaded successfully.")
                except TimeoutException:
                    logger.info("Library loading.")
                # Wait for at least 2 seconds on the library page
                logger.info("Waiting for 2 seconds on the library page.")
                time.sleep(2)
                logger.info("Completed waiting on the library page.")
               
                # Extract library stats from the page
                try:
                    logger.info("Extracting library statistics from the page.")
                    library_stats_element = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//h1[contains(@class, 'text-xl') and contains(@class, 'font-bold') and contains(@class, 'text-white') and contains(text(), 'Library')]"))
                    )
                    library_stats_text = library_stats_element.text.strip()
                    logger.info(f"Found library stats text: {library_stats_text}")
                   
                    # Parse the text to extract torrent count and size
                    # Example: "Library 📚 3132 torrents 🙂 76.5 TB"
                    import re
                    from datetime import datetime
                   
                    # Extract torrent count
                    torrent_match = re.search(r'(\d+)\s+torrents', library_stats_text)
                    torrents_count = int(torrent_match.group(1)) if torrent_match else 0
                   
                    # Extract TB size
                    size_match = re.search(r'([\d.]+)\s*TB', library_stats_text)
                    total_size_tb = float(size_match.group(1)) if size_match else 0.0
                   
                    # Update global library stats
                    global library_stats
                    library_stats = {
                        "torrents_count": torrents_count,
                        "total_size_tb": total_size_tb,
                        "last_updated": datetime.now().isoformat()
                    }
                   
                    logger.success(f"Successfully extracted library stats: {torrents_count} torrents, {total_size_tb} TB")
                   
                except TimeoutException:
                    logger.warning("Could not find library stats element on the page within timeout.")
                except Exception as e:
                    logger.error(f"Error extracting library stats: {e}")
               
                logger.success("Browser initialization completed successfully.")
            except Exception as e:
                logger.error(f"Error during browser setup: {e}")
                if driver:
                    driver.quit()
                    driver = None
    else:
        logger.info("Browser already initialized.")
   
    return driver # Return the driver instance for direct use

async def shutdown_browser():
    """Shut down the browser and clean up resources."""
    global driver
    if driver:
        driver.quit()
        logger.warning("Selenium WebDriver closed.")
        driver = None

def login(driver):
    """Handle login to Debrid Media Manager."""
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

def check_red_buttons(driver, movie_title, normalized_seasons, confirmed_seasons, is_tv_show, episode_id=None):
    """
    Check for red buttons (RD 100%) on the page and verify if they match the expected title
    
    Args:
        driver: Selenium WebDriver instance
        movie_title: Expected title to match
        normalized_seasons: List of seasons in normalized format
        confirmed_seasons: Set of already confirmed seasons
        is_tv_show: Whether we're checking a TV show
        episode_id: Optional episode ID for TV shows
        
    Returns:
        Tuple[bool, set]: (confirmation flag, updated confirmed seasons set)
    """
    from seerr.utils import clean_title, extract_year, extract_season
    
    confirmation_flag = False

    try:
        all_red_buttons_elements = driver.find_elements(By.XPATH, "//button[contains(@class, 'bg-red-900/30')]")
        # Filter out "Report" buttons and buttons that don't contain "RD (100%)"
        red_buttons_elements = [
            button for button in all_red_buttons_elements 
            if "Report" not in button.text and "RD (100%)" in button.text
        ]
        logger.info(f"Found {len(red_buttons_elements)} red button(s) with 'RD (100%)' without 'Report'. Verifying titles.")
        for i, red_button_element in enumerate(red_buttons_elements, start=1):
            if "Report" in red_button_element.text:
                continue
                
            # Double-check that this is actually an RD (100%) button
            button_text = red_button_element.text.strip()
            if "RD (100%)" not in button_text:
                logger.warning(f"Red button {i} does not contain 'RD (100%)' - text: '{button_text}'. Skipping.")
                continue
                
            logger.info(f"Checking red button {i} with text: '{button_text}'...")
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
                    logger.info(f"Found a match on red button {i} - {red_button_title_cleaned} with RD (100%). Marking as confirmed.")
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
        logger.info("No red buttons with 'RD (100%)' detected. Proceeding with optional fallback.")

    return confirmation_flag, confirmed_seasons

def refresh_library_stats():
    """
    Refresh library statistics from the current page
    """
    global driver, library_stats
    
    if driver is None:
        logger.warning("Browser not initialized. Cannot refresh library stats.")
        return False
    
    try:
        # Navigate to library page if we're not already there
        current_url = driver.current_url
        if "library" not in current_url:
            logger.info("Navigating to library page to refresh stats.")
            driver.get("https://debridmediamanager.com/library")
            time.sleep(2)  # Wait for page to load
        
        logger.info("Refreshing library statistics.")
        library_stats_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//h1[contains(@class, 'text-xl') and contains(@class, 'font-bold') and contains(@class, 'text-white') and contains(text(), 'Library')]"))
        )
        library_stats_text = library_stats_element.text.strip()
        logger.info(f"Found library stats text: {library_stats_text}")
        
        # Parse the text to extract torrent count and size
        import re
        from datetime import datetime
        
        # Extract torrent count
        torrent_match = re.search(r'(\d+)\s+torrents', library_stats_text)
        torrents_count = int(torrent_match.group(1)) if torrent_match else 0
        
        # Extract TB size
        size_match = re.search(r'([\d.]+)\s*TB', library_stats_text)
        total_size_tb = float(size_match.group(1)) if size_match else 0.0
        
        # Update global library stats
        library_stats = {
            "torrents_count": torrents_count,
            "total_size_tb": total_size_tb,
            "last_updated": datetime.now().isoformat()
        }
        
        logger.success(f"Successfully refreshed library stats: {torrents_count} torrents, {total_size_tb} TB")
        return True
        
    except TimeoutException:
        logger.warning("Could not find library stats element on the page within timeout.")
        return False
    except Exception as e:
        logger.error(f"Error refreshing library stats: {e}")
        return False 
