"""
Search module for SeerrBridge
Handles searching on Debrid Media Manager
"""
import time
import json
import os
import asyncio
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException, TimeoutException
from loguru import logger
from fuzzywuzzy import fuzz

from seerr.config import TORRENT_FILTER_REGEX, DISCREPANCY_REPO_FILE
from seerr.browser import driver, click_show_more_results, check_red_buttons, prioritize_buttons_in_box
from seerr.utils import (
    clean_title,
    normalize_title,
    extract_year,
    extract_season,
    replace_numbers_with_words,
    replace_words_with_numbers,
    parse_requested_seasons,
    normalize_season,
    match_complete_seasons,
    match_single_season
)
from seerr.background_tasks import search_individual_episodes

def search_on_debrid(imdb_id, movie_title, media_type, driver, extra_data=None):
    """
    Search for media on Debrid Media Manager
    
    Args:
        imdb_id (str): IMDb ID of the media
        movie_title (str): Title of the media
        media_type (str): Type of media ('movie' or 'tv')
        driver: Selenium WebDriver instance (passed from caller)
        extra_data (list, optional): Extra data for the request
        
    Returns:
        bool: True if media was found and processed, False otherwise
    """
    logger.info(f"Starting Selenium automation for IMDb ID: {imdb_id}, Media Type: {media_type}")
    
    # Use the imported driver module if the passed driver is None
    from seerr.browser import driver as browser_driver
    if driver is None:
        if browser_driver is None:
            logger.error("Selenium WebDriver is not initialized. Cannot proceed.")
            return False
        logger.info("Using the global browser driver instance.")
        driver = browser_driver
        
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
                return False  # Skip further checks if "No results found" is detected
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
                import re
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
            torrents_count = 0
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
                                # Initialize result_boxes to an empty list to avoid reference errors
                                result_boxes = []
                                # Make one more attempt to find result boxes with a longer timeout
                                try:
                                    logger.info(f"Making one more attempt to find result boxes for season {season}...")
                                    result_boxes = WebDriverWait(driver, 3).until(
                                        EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'border-black')]"))
                                    )
                                    logger.info(f"Found {len(result_boxes)} result boxes for season {season} on second attempt")
                                except TimeoutException:
                                    logger.warning(f"Still no result boxes found for season {season} after second attempt")
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
                            
                            # Since we're in a synchronous function, and search_individual_episodes is async,
                            # we need to synchronously run the coroutine
                            import asyncio
                            try:
                                # Create and run a synchronous version of search_individual_episodes
                                from seerr.background_tasks import search_individual_episodes_sync
                                confirmation_flag = search_individual_episodes_sync(
                                    imdb_id, movie_title, season_number, discrepancy["season_details"], driver
                                )
                            except ImportError:
                                # Fallback if the sync version doesn't exist - create a simple wrapper
                                logger.warning("Using fallback method for search_individual_episodes")
                                
                                def run_async_in_sync(coro):
                                    """Run an async function synchronously by creating a new event loop."""
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                                    try:
                                        return loop.run_until_complete(coro)
                                    finally:
                                        loop.close()
                                
                                confirmation_flag = run_async_in_sync(
                                    search_individual_episodes(
                                        imdb_id, movie_title, season_number, discrepancy["season_details"], driver
                                    )
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
                        # Initialize result_boxes to an empty list to avoid reference errors
                        result_boxes = []
                        # Make one more attempt to find result boxes with a longer timeout
                        try:
                            logger.info("Making one more attempt to find result boxes.")
                            result_boxes = WebDriverWait(driver, 3).until(
                                EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'border-black')]"))
                            )
                            logger.info(f"Found {len(result_boxes)} result boxes on second attempt")
                        except TimeoutException:
                            logger.warning("Still no result boxes found after second attempt")
                            # result_boxes remains an empty list

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
            return False

    except Exception as ex:
        logger.critical(f"Error during Selenium automation: {ex}")
        return False 