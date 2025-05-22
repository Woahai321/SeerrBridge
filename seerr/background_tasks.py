"""
Background tasks module for SeerrBridge
Handles queuing and processing of requests
"""
import os
import json
import asyncio
import time
from asyncio import Queue
from typing import Tuple, Dict, List, Any, Optional
from datetime import datetime, timezone
from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from seerr.config import (
    DISCREPANCY_REPO_FILE,
    REFRESH_INTERVAL_MINUTES,
    ENABLE_AUTOMATIC_BACKGROUND_TASK,
    ENABLE_SHOW_SUBSCRIPTION_TASK,
    TORRENT_FILTER_REGEX
)
from seerr.browser import driver, click_show_more_results, check_red_buttons, prioritize_buttons_in_box
from seerr.overseerr import get_overseerr_media_requests, mark_completed
from seerr.trakt import get_media_details_from_trakt, get_season_details_from_trakt, check_next_episode_aired
from seerr.utils import parse_requested_seasons, normalize_season, extract_season, clean_title

# Initialize a global queue with a maximum size of 500
request_queue = Queue(maxsize=500)
processing_task = None  # To track the current processing task

# Scheduler for background tasks
scheduler = AsyncIOScheduler()

async def initialize_background_tasks():
    """Initialize background tasks and the queue processor."""
    global processing_task
    
    if processing_task is None:
        processing_task = asyncio.create_task(process_requests())
        logger.info("Started request processing task.")

    # Schedule token refresh
    schedule_token_refresh()
    scheduler.start()

def schedule_token_refresh():
    """Schedule the token refresh every 10 minutes."""
    from seerr.realdebrid import check_and_refresh_access_token
    scheduler.add_job(check_and_refresh_access_token, 'interval', minutes=10)
    logger.info("Scheduled token refresh every 10 minutes.")

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

### Function to process requests from the queue
async def process_requests():
    """Process requests from the queue one by one."""
    while True:
        try:
            imdb_id, movie_title, media_type, extra_data = await request_queue.get()
            logger.info(f"Processing request for IMDb ID: {imdb_id}, Title: {movie_title}, Media Type: {media_type}")
            
            # Check if browser driver is available
            from seerr.browser import driver as browser_driver
            if browser_driver is None:
                logger.warning("Browser driver not initialized. Attempting to initialize...")
                from seerr.browser import initialize_browser
                await initialize_browser()
                from seerr.browser import driver as browser_driver
                if browser_driver is None:
                    logger.error("Failed to initialize browser driver. Skipping request.")
                    request_queue.task_done()
                    continue
            
            try:
                from seerr.search import search_on_debrid
                await asyncio.to_thread(search_on_debrid, imdb_id, movie_title, media_type, browser_driver, extra_data)
            except Exception as ex:
                logger.critical(f"Error processing request for IMDb ID {imdb_id}: {ex}")
            finally:
                request_queue.task_done()
        except Exception as e:
            logger.error(f"Error in process_requests: {e}")
            # Sleep briefly before continuing to prevent tight loop on error
            await asyncio.sleep(1)

### Function to add requests to the queue
async def add_request_to_queue(imdb_id, movie_title, media_type, extra_data=None):
    """Add a request to the processing queue."""
    if request_queue.full():
        logger.warning(f"Request queue is full. Cannot add request for IMDb ID: {imdb_id}")
        return False
    
    await request_queue.put((imdb_id, movie_title, media_type, extra_data))
    logger.info(f"Added request to queue for IMDb ID: {imdb_id}, Title: {movie_title}, Media Type: {media_type}")
    return True

async def process_movie_requests():
    """
    Process Overseerr media requests. For TV shows, fetch season details and log discrepancies if found,
    then skip full processing, deferring to the check_show_subscriptions task. Movies are processed normally.
    """
    logger.info("Starting to process Overseerr media requests...")

    # Check if browser driver is available
    from seerr.browser import driver as browser_driver
    if browser_driver is None:
        logger.warning("Browser driver not initialized. Attempting to initialize...")
        from seerr.browser import initialize_browser
        await initialize_browser()
        from seerr.browser import driver as browser_driver
        if browser_driver is None:
            logger.error("Failed to initialize browser driver. Cannot process media requests.")
            return

    # Load episode_discrepancies.json to check for existing discrepancies
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
                        # Create list of aired episodes marked as failed with "E01", "E02", etc.
                        # Only include episodes that have actually aired
                        failed_episodes = [
                            f"E{str(i).zfill(2)}"  # Format as E01, E02, etc.
                            for i in range(1, aired_episodes + 1)
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
            from seerr.search import search_on_debrid
            from seerr.browser import driver as browser_driver
            confirmation_flag = await asyncio.to_thread(search_on_debrid, imdb_id, media_title, media_type, browser_driver, extra_data)
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

async def check_show_subscriptions():
    """
    Recurring task to check for new episodes in subscribed shows listed in episode_discrepancies.json.
    Updates the JSON file with the latest aired episode counts and processes new episodes if found.
    Also reattempts processing of previously failed episodes and checks for the next episode if there's a discrepancy.
    """
    logger.info("Starting show subscription check...")

    # Check if browser driver is available
    from seerr.browser import driver as browser_driver
    if browser_driver is None:
        logger.warning("Browser driver not initialized. Attempting to initialize...")
        from seerr.browser import initialize_browser
        await initialize_browser()
        from seerr.browser import driver as browser_driver
        if browser_driver is None:
            logger.error("Failed to initialize browser driver. Cannot check show subscriptions.")
            return

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
        from seerr.browser import driver as browser_driver
        browser_driver.get(url)
        logger.info(f"Navigated to show page for Season {season_number}: {url}")
        
        # Wait for the page to load (ensure the status element is present)
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By
            from selenium.common.exceptions import TimeoutException
            
            WebDriverWait(browser_driver, 5).until(
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
                filter_input = WebDriverWait(browser_driver, 10).until(
                    EC.presence_of_element_located((By.ID, "query"))
                )
                filter_input.clear()
                episode_filter = f"S{season_number:02d}{episode_id}"
                full_filter = f"{TORRENT_FILTER_REGEX} {episode_filter}"
                filter_input.send_keys(full_filter)
                logger.info(f"Applied filter: {full_filter}")

                try:
                    click_show_more_results(browser_driver, logger)
                except TimeoutException:
                    logger.warning("Timed out while trying to click 'Show More Results'")
                except Exception as e:
                    logger.error(f"Unexpected error in click_show_more_results: {e}")

                # Wait for results to update
                time.sleep(2)

                # Check for existing RD (100%) using check_red_buttons
                confirmation_flag, confirmed_seasons = check_red_buttons(
                    browser_driver, show_title, normalized_seasons, confirmed_seasons, is_tv_show, episode_id=episode_id
                )

                if confirmation_flag:
                    logger.success(f"{episode_id} already cached at RD (100%). Skipping further processing.")
                    continue

                # Process uncached episode
                try:
                    result_boxes = WebDriverWait(browser_driver, 10).until(
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
                            from fuzzywuzzy import fuzz
                            match_ratio = fuzz.partial_ratio(title_clean, show_clean)
                            logger.info(f"Match ratio: {match_ratio} for '{title_clean}' vs '{show_clean}'")
                            
                            if episode_id.lower() in title_text.lower() and match_ratio >= 50:
                                logger.info(f"Found match for {episode_id} in box {i}: {title_text}")

                                if prioritize_buttons_in_box(result_box):
                                    logger.info(f"Successfully handled {episode_id} in box {i}")
                                    episode_confirmed = True

                                    # Verify RD status
                                    try:
                                        rd_button = WebDriverWait(browser_driver, 10).until(
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

                        except Exception as e:
                            logger.warning(f"Error processing box {i} for {episode_id}: {e}")

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
            filter_input = browser_driver.find_element(By.ID, "query")
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

async def search_individual_episodes(imdb_id, movie_title, season_number, season_details, driver):
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
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    from fuzzywuzzy import fuzz
    
    # Use the imported driver if the passed driver is None
    from seerr.browser import driver as browser_driver
    if driver is None:
        if browser_driver is None:
            logger.error("Selenium WebDriver is not initialized. Cannot search for episodes.")
            return False
        logger.info("Using the global browser driver instance.")
        driver = browser_driver
    
    logger.info(f"Starting individual episode search for {movie_title} Season {season_number}")
    
    aired_episodes = season_details.get('aired_episodes', 0)
    if not aired_episodes:
        logger.error(f"No aired episodes found in season details for {movie_title} Season {season_number}")
        return False

    logger.info(f"Processing {aired_episodes} aired episodes for Season {season_number}")
    
    all_confirmed = True  # Track if all episodes are successfully processed or already cached
    failed_episodes = []  # Track episodes that fail to process
    
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
    from seerr.browser import driver as browser_driver
    browser_driver.get(url)
    logger.info(f"Navigated to show page for Season {season_number}: {url}")
    
    # Wait for the page to load (ensure the status element is present)
    try:
        WebDriverWait(browser_driver, 5).until(
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
        filter_input = browser_driver.find_element(By.ID, "query")
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

def search_individual_episodes_sync(imdb_id, movie_title, season_number, season_details, driver):
    """
    Synchronous version of search_individual_episodes - this is a wrapper around the async function
    to be called from synchronous code.
    
    Args:
        imdb_id (str): IMDb ID of the show
        movie_title (str): Title of the show with year (e.g., "Daredevil: Born Again (2025)")
        season_number (int): Season number with discrepancy
        season_details (dict): Season details from Trakt, including 'aired_episodes'
        driver (WebDriver): Selenium WebDriver instance
    
    Returns:
        bool: True if all episodes were successfully processed or already cached, False otherwise
    """
    import asyncio
    
    # Create a new event loop and run the async function
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        return loop.run_until_complete(
            search_individual_episodes(imdb_id, movie_title, season_number, season_details, driver)
        )
    finally:
        loop.close() 