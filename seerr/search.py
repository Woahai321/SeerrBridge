"""
Search module for SeerrBridge
Handles searching on Debrid Media Manager
"""
import time
import json
import os
import asyncio
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException, TimeoutException
from loguru import logger
from fuzzywuzzy import fuzz

from seerr.config import TORRENT_FILTER_REGEX, USE_DATABASE
from seerr.database import get_db, LogEntry
from seerr.db_logger import log_info, log_success, log_error
from datetime import datetime
from seerr.browser import driver, click_show_more_results, check_red_buttons, prioritize_buttons_in_box
from seerr.utils import (
    clean_title,
    normalize_title,
    extract_year,
    extract_season,
    replace_numbers_with_words,
    replace_words_with_numbers,
    parse_requested_seasons,
    is_complete_word_match,
    normalize_season,
    match_complete_seasons,
    match_single_season
)
from seerr.background_tasks import search_individual_episodes

def search_dmm_by_title_and_extract_id(driver, title, media_type, year=None, tmdb_id=None):
    """
    Search DMM by title and extract IMDB ID from search results.
    This is a fallback when IMDB ID is not available.
    
    Args:
        driver: Selenium WebDriver instance
        title: Title of the media (without year)
        media_type: 'movie' or 'tv'
        year: Optional year to help with matching
        tmdb_id: Optional TMDB ID for queue status checks
    
    Returns:
        str: IMDB ID if found, None otherwise
    """
    # Check queue status before expensive search operation
    if tmdb_id and _check_queue_status(tmdb_id, media_type):
        logger.info(f"Item (TMDB: {tmdb_id}) is not in queue. Stopping before title search.")
        return None
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
    from urllib.parse import quote
    import re
    import time
    
    try:
        # Check queue status again before navigating to search page
        if tmdb_id and _check_queue_status(tmdb_id, media_type):
            logger.info(f"Item (TMDB: {tmdb_id}) is not in queue. Stopping before navigating to search page.")
            return None
        
        logger.info(f"Searching DMM for '{title}' ({media_type}) to find IMDB ID (fallback when IMDB ID is missing)")
        
        # Try using direct URL with query parameter first (more reliable)
        try:
            encoded_title = quote(title)
            search_url = f"https://debridmediamanager.com/search?query={encoded_title}"
            logger.info(f"Navigating to search URL: {search_url}")
            driver.get(search_url)
            
            # Wait a bit for page to load and JavaScript to execute
            time.sleep(3)
            
            # Wait for results to load - try multiple selectors with retries
            max_retries = 3
            results_found = False
            for attempt in range(max_retries):
                try:
                    result_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/show/'], a[href*='/movie/'], a.haptic")
                    if len(result_links) > 0:
                        results_found = True
                        logger.info(f"Found {len(result_links)} result links on attempt {attempt + 1}")
                        break
                    else:
                        logger.debug(f"No results found on attempt {attempt + 1}, waiting...")
                        time.sleep(2)
                except Exception as e:
                    logger.debug(f"Error finding results on attempt {attempt + 1}: {e}")
                    time.sleep(2)
            
            if not results_found:
                logger.warning(f"Timeout waiting for search results for '{title}'. Trying alternative approach...")
                # Fallback: try using search input
                raise TimeoutException("Results not found via URL")
                
        except (TimeoutException, WebDriverException) as e:
            # Check queue status before fallback search
            if tmdb_id and _check_queue_status(tmdb_id, media_type):
                logger.info(f"Item (TMDB: {tmdb_id}) is not in queue. Stopping before fallback search.")
                return None
            
            logger.info(f"Direct URL approach failed, trying search input method: {e}")
            # Fallback: Navigate to search page and use input
            driver.get("https://debridmediamanager.com/search")
            
            # Wait for search input and enter title
            try:
                search_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "search-input"))
                )
                search_input.clear()
                search_input.send_keys(title)
                time.sleep(1)  # Wait a bit before sending return
                search_input.send_keys(Keys.RETURN)
                
                # Wait for results to load
                WebDriverWait(driver, 15).until(
                    lambda d: len(d.find_elements(By.CSS_SELECTOR, "a[href*='/show/'], a[href*='/movie/'], a.haptic")) > 0
                )
            except TimeoutException:
                logger.warning(f"No search results found for '{title}'")
                return None
        
        # Find all result links (shows or movies)
        result_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/show/'], a[href*='/movie/']")
        
        if not result_links:
            logger.warning(f"No result links found for '{title}'")
            return None
        
        logger.info(f"Found {len(result_links)} potential results for '{title}'")
        
        # Extract title from the search query (remove year if present)
        title_clean = clean_title(title.split('(')[0].strip())
        
        # Try to find matching result by title
        best_match = None
        best_score = 0
        
        for link in result_links:
            try:
                # Extract IMDB ID from href (e.g., /show/tt26750568 or /movie/tt1234567)
                href = link.get_attribute('href')
                if not href:
                    continue
                
                # Extract IMDB ID from URL
                match = re.search(r'/(?:show|movie)/(tt\d+)', href)
                if not match:
                    continue
                
                imdb_id = match.group(1)
                
                # Get the title from the result element
                try:
                    # Look for h3 element with title (based on user's example)
                    title_element = link.find_element(By.CSS_SELECTOR, "h3")
                    result_title = title_element.text.strip()
                except NoSuchElementException:
                    # Fallback: try to get text from the link itself
                    result_title = link.text.strip()
                    if not result_title:
                        continue
                
                # Get year from result if available
                result_year = None
                try:
                    year_element = link.find_element(By.CSS_SELECTOR, ".text-sm.text-gray-600, div.text-sm")
                    year_text = year_element.text.strip()
                    # Try to extract year
                    year_match = re.search(r'\b(19|20)\d{2}\b', year_text)
                    if year_match:
                        result_year = int(year_match.group(0))
                except NoSuchElementException:
                    pass
                
                # Clean and compare titles
                result_title_clean = clean_title(result_title.split('(')[0].strip())
                
                # Calculate match score
                title_score = fuzz.partial_ratio(title_clean.lower(), result_title_clean.lower())
                
                # Bonus points for year match if provided
                year_bonus = 0
                if year and result_year and year == result_year:
                    year_bonus = 20
                
                total_score = title_score + year_bonus
                
                logger.info(f"Result: '{result_title}' ({result_year}) - IMDB: {imdb_id} - Score: {total_score} (title: {title_score}, year: {year_bonus})")
                
                # Only consider matches with at least 75% title similarity
                if title_score >= 75 and total_score > best_score:
                    best_match = imdb_id
                    best_score = total_score
                    
            except Exception as e:
                logger.debug(f"Error processing result link: {e}")
                continue
        
        if best_match:
            logger.info(f"Found matching IMDB ID for '{title}': {best_match} (match score: {best_score})")
            return best_match
        else:
            logger.warning(f"No suitable match found for '{title}' (best score was below threshold)")
            return None
            
    except WebDriverException as e:
        logger.error(f"WebDriver error searching DMM for '{title}': {str(e)}")
        if hasattr(e, 'msg') and e.msg:
            logger.error(f"WebDriver error message: {e.msg}")
        return None
    except TimeoutException as e:
        logger.error(f"Timeout error searching DMM for '{title}': {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error searching DMM for '{title}': {type(e).__name__}: {str(e)}")
        import traceback
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return None

def extract_episodes_from_torrents(driver, movie_title, season_num, processed_torrents):
    """
    Extract episode numbers from confirmed torrent titles.
    
    Args:
        driver: Selenium WebDriver instance
        movie_title: Title of the show
        season_num: Season number
        processed_torrents: Set of confirmed torrent titles
    
    Returns:
        list: List of episode numbers found in torrents
    """
    import re
    
    confirmed_episodes = []
    
    for torrent_title in processed_torrents:
        logger.info(f"Extracting episodes from torrent: {torrent_title}")
        
        # Look for episode patterns like S04E01, S04E02, S04E01-02, etc.
        episode_patterns = [
            rf'S{season_num:02d}E(\d+)',  # S04E01, S04E02
            rf'S{season_num:02d}E(\d+)-(\d+)',  # S04E01-02
            rf'S{season_num:02d}E(\d+)-E(\d+)',  # S04E01-E02
        ]
        
        for pattern in episode_patterns:
            matches = re.findall(pattern, torrent_title, re.IGNORECASE)
            if matches:
                if len(matches[0]) == 1:  # Single episode
                    episode_num = int(matches[0])
                    if episode_num not in confirmed_episodes:
                        confirmed_episodes.append(episode_num)
                        logger.info(f"Found episode {episode_num} in torrent: {torrent_title}")
                elif len(matches[0]) == 2:  # Episode range
                    start_ep = int(matches[0][0])
                    end_ep = int(matches[0][1])
                    for ep in range(start_ep, end_ep + 1):
                        if ep not in confirmed_episodes:
                            confirmed_episodes.append(ep)
                            logger.info(f"Found episode {ep} in range torrent: {torrent_title}")
    
    confirmed_episodes.sort()
    logger.info(f"Extracted {len(confirmed_episodes)} confirmed episodes for Season {season_num}: {confirmed_episodes}")
    return confirmed_episodes


def update_database_with_confirmed_episodes(movie_title, season_num, confirmed_episodes):
    """
    Update the database to mark episodes as confirmed.
    
    Args:
        movie_title: Title of the show
        season_num: Season number
        confirmed_episodes: List of confirmed episode numbers
    """
    if not USE_DATABASE:
        logger.info("Database not enabled, skipping episode confirmation update")
        return
    
    try:
        from seerr.database import get_db
        from seerr.unified_models import UnifiedMedia
        
        db = get_db()
        try:
            # Find the media record
            media_record = db.query(UnifiedMedia).filter(
                UnifiedMedia.title == movie_title.split(' (')[0],  # Remove year from title
                UnifiedMedia.media_type == 'tv'
            ).first()
            
            if not media_record:
                logger.warning(f"Could not find media record for {movie_title}")
                return
            
            # Update seasons_data
            if media_record.seasons_data:
                seasons_data = media_record.seasons_data
                updated = False
                
                for season_data in seasons_data:
                    if season_data.get('season_number') == season_num:
                        # Update confirmed episodes
                        existing_confirmed = season_data.get('confirmed_episodes', [])
                        new_confirmed = []
                        
                        for ep in confirmed_episodes:
                            ep_id = f"E{ep:02d}"
                            if ep_id not in existing_confirmed:
                                new_confirmed.append(ep_id)
                        
                        if new_confirmed:
                            season_data['confirmed_episodes'] = existing_confirmed + new_confirmed
                            season_data['updated_at'] = datetime.utcnow().isoformat()
                            updated = True
                            logger.info(f"Added {len(new_confirmed)} new confirmed episodes to Season {season_num}: {new_confirmed}")
                
                if updated:
                    media_record.seasons_data = seasons_data
                    media_record.updated_at = datetime.utcnow()
                    db.commit()
                    logger.success(f"Updated database with confirmed episodes for {movie_title} Season {season_num}")
                else:
                    logger.info(f"No new episodes to confirm for {movie_title} Season {season_num}")
            else:
                logger.warning(f"No seasons_data found for {movie_title}")
                
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error updating database with confirmed episodes: {e}")


def try_complete_season_pack(driver, movie_title, season_num, normalized_seasons):
    """
    Try to find a Complete season pack by clicking the Complete button.
    
    Args:
        driver: Selenium WebDriver instance
        movie_title: Title of the show
        season_num: Season number
        normalized_seasons: List of normalized season names
    
    Returns:
        bool: True if complete pack found and confirmed, False otherwise
    """
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    import time
    
    try:
        # Look for the Complete button
        complete_button = driver.find_element(By.XPATH, "//span[contains(@class, 'bg-green-900') and contains(text(), 'Complete')]")
        
        # Log page state before clicking
        
        logger.info(f"Found Complete button, clicking it for Season {season_num}")
        complete_button.click()
        
        # Click "Show more results" button if available to load all results
        try:
            show_more_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Show more results')]")
            logger.info(f"Found 'Show more results' button for Season {season_num}, clicking it")
            show_more_button.click()
        except NoSuchElementException:
            logger.info(f"'Show more results' button not found for Season {season_num}, proceeding without it")
        
        # Wait 10 seconds for results to load
        logger.info(f"Waiting 10 seconds for Complete results to load for Season {season_num}")
        time.sleep(10)
        
        # Try to click "Show more results" again after initial load
        try:
            show_more_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Show more results')]")
            logger.info(f"Found 'Show more results' button again for Season {season_num}, clicking it")
            show_more_button.click()
            logger.info(f"Waiting 3 seconds after clicking 'Show more results' for Season {season_num}")
            time.sleep(3)
        except NoSuchElementException:
            logger.info(f"'Show more results' button not available for Season {season_num}, proceeding with available results")
        
        # Check if page is still loading and wait longer if needed
        if not check_page_loading_state(driver, season_num, "Complete"):
            logger.info(f"Page still loading after 10 seconds, waiting additional 5 seconds for Season {season_num}")
            time.sleep(5)
            check_page_loading_state(driver, season_num, "Complete")
        
        # Log page state after waiting
        
        # Quick check: See if there's already an RD (100%) button for this season
        try:
            rd_100_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'RD (100%)') and not(contains(text(), 'Report'))]")
            if rd_100_buttons:
                logger.info(f"Found {len(rd_100_buttons)} existing RD (100%) buttons for Season {season_num}")
                # Check if any of them are for our season
                for button in rd_100_buttons:
                    try:
                        # Get title from parent container
                        title_element = button.find_element(By.XPATH, "./ancestor::div//h2")
                        button_title = title_element.text.strip()
                        
                        # Simple title match
                        tv_show_title_cleaned = clean_title(movie_title.split('(')[0].strip())
                        title_text_cleaned = clean_title(button_title.split('(')[0].strip())
                        
                        if tv_show_title_cleaned.lower() in title_text_cleaned.lower() or title_text_cleaned.lower() in tv_show_title_cleaned.lower():
                            logger.info(f"Found matching RD (100%) for: {button_title}")
                            mark_all_episodes_as_confirmed(movie_title, season_num)
                            return True
                    except:
                        continue
        except:
            pass
        
        # No RD (100%) exists, process result boxes one by one until we get a success
        logger.info(f"No RD (100%) found in Complete results. Processing result boxes for Season {season_num}")
        
        # Get result boxes after clicking Complete
        try:
            result_boxes = WebDriverWait(driver, 5).until(
                EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'border-2')]"))
            )
            logger.info(f"Found {len(result_boxes)} result boxes to process (will stop on first success)")
            
            # Process each result box ONE BY ONE until success
            for i, result_box in enumerate(result_boxes, 1):
                try:
                    # Extract title from result box
                    title_element = result_box.find_element(By.XPATH, ".//h2")
                    title_text = title_element.text.strip()
                    logger.info(f"[Box {i}/{len(result_boxes)}] Processing: {title_text}")
                    
                    # Skip boxes marked as "Single" episodes
                    try:
                        result_box.find_element(By.XPATH, ".//span[contains(., 'Single')]")
                        logger.info(f"Box {i} is a single episode. Skipping.")
                        continue
                    except:
                        pass
                    
                    # Clean and normalize titles for comparison
                    tv_show_title_cleaned = clean_title(movie_title.split('(')[0].strip())
                    title_text_cleaned = clean_title(title_text.split('(')[0].strip())
                    
                    # Check if title matches using fuzzy matching
                    title_match_score = fuzz.partial_ratio(title_text_cleaned.lower(), tv_show_title_cleaned.lower())
                    logger.info(f"Title match score: {title_match_score}% (box: {title_text_cleaned}, expected: {tv_show_title_cleaned})")
                    
                    if title_match_score < 75:
                        logger.info(f"Title mismatch for box {i}. Skipping.")
                        continue
                    
                    # Check if this box has a Complete badge (the real indicator of complete packs)
                    try:
                        complete_badge = result_box.find_element(By.XPATH, ".//span[contains(text(), 'Complete (')]")
                        complete_badge_text = complete_badge.text
                        logger.info(f"Found Complete badge in box {i}: {complete_badge_text}")
                    except:
                        logger.info(f"No Complete badge in box {i}, skipping")
                        continue
                    
                    # Process complete pack
                    logger.info(f"Processing complete season pack in box {i}: {title_text}")
                    
                    # Verify the complete pack by checking the modal before clicking Instant RD
                    try:
                        # Get expected episode count for this season from database if available
                        from seerr.database import get_db, UnifiedMedia
                        expected_episode_count = None
                        try:
                            db = get_db()
                            media = db.query(UnifiedMedia).filter(
                                UnifiedMedia.title == movie_title,
                                UnifiedMedia.type == 'tv'
                            ).first()
                            
                            if media and media.seasons:
                                season_data = next((s for s in media.seasons if s.get('season_number') == season_num), None)
                                if season_data:
                                    episodes = season_data.get('episodes', [])
                                    expected_episode_count = len(episodes) if episodes else None
                                    logger.info(f"Expected episode count for Season {season_num}: {expected_episode_count}")
                        except:
                            pass
                        
                        # Extract the file count from the badge text (e.g., "Complete (9/9)")
                        import re
                        match = re.search(r'Complete \((\d+)/(\d+)\)', complete_badge_text)
                        if match:
                            file_count = int(match.group(2))  # Total files
                            logger.info(f"Complete pack in box {i} contains {file_count} files")
                            
                            # Verify the file count matches expected
                            if expected_episode_count and file_count != expected_episode_count:
                                logger.warning(f"Box {i} has {file_count} files but expected {expected_episode_count}. Skipping.")
                                continue
                            
                            # For extra verification, click the badge to open modal and check the file list
                            try:
                                complete_badge.click()
                                logger.info(f"Opened Complete modal for box {i}")
                                time.sleep(2)  # Wait for modal to open
                                
                                # Try to parse the modal to verify files
                                try:
                                    # Find the modal
                                    modal = driver.find_element(By.XPATH, "//div[contains(@class, 'max-h-[90vh]')]")
                                    
                                    # Get all file rows in the modal
                                    file_rows = modal.find_elements(By.XPATH, ".//tr[@class='bg-gray-800 font-bold hover:bg-gray-700 rounded']")
                                    actual_file_count = len(file_rows)
                                    logger.info(f"Modal shows {actual_file_count} files in the complete pack")
                                    
                                    # Verify the actual file count
                                    if expected_episode_count and actual_file_count != expected_episode_count:
                                        logger.warning(f"Modal verification: box {i} has {actual_file_count} files but expected {expected_episode_count}. Skipping.")
                                        # Close modal
                                        try:
                                            close_button = driver.find_element(By.XPATH, "//button[contains(text(), '×')]")
                                            close_button.click()
                                        except:
                                            # Try clicking overlay if no close button
                                            overlay = driver.find_element(By.XPATH, "//div[contains(@class, 'fixed inset-0') and contains(@class, 'bg-black')]")
                                            overlay.click()
                                            time.sleep(1)
                                        continue
                                    
                                    # Close the modal before proceeding by pressing ESC
                                    logger.info(f"Closing Complete modal for box {i}...")
                                    try:
                                        # Press ESC to close modal
                                        driver.switch_to.active_element.send_keys(Keys.ESCAPE)
                                        logger.info(f"Pressed ESC to close Complete modal for box {i}")
                                        
                                        # Wait for modal to disappear (up to 5 seconds)
                                        WebDriverWait(driver, 5).until(
                                            EC.invisibility_of_element_located((By.XPATH, "//div[contains(@class, 'fixed inset-0') and contains(@class, 'bg-black')]"))
                                        )
                                        logger.info(f"Modal closed for box {i}")
                                    except:
                                        # Fallback: try clicking overlay
                                        try:
                                            overlay = driver.find_element(By.XPATH, "//div[contains(@class, 'fixed inset-0') and contains(@class, 'bg-black')]")
                                            overlay.click()
                                            logger.info(f"Clicked overlay to close modal for box {i}")
                                            WebDriverWait(driver, 5).until(
                                                EC.invisibility_of_element_located((By.XPATH, "//div[contains(@class, 'fixed inset-0') and contains(@class, 'bg-black')]"))
                                            )
                                            logger.info(f"Modal closed for box {i} via overlay click")
                                        except:
                                            logger.warning(f"Could not verify modal closure for box {i}, proceeding anyway")
                                except Exception as modal_error:
                                    logger.warning(f"Could not parse modal for box {i}: {modal_error}")
                                    # Try to close modal anyway
                                    try:
                                        overlay = driver.find_element(By.XPATH, "//div[contains(@class, 'fixed inset-0') and contains(@class, 'bg-black')]")
                                        overlay.click()
                                        time.sleep(1)
                                    except:
                                        pass
                            except Exception as click_error:
                                logger.warning(f"Could not click Complete badge or open modal for box {i}: {click_error}")
                        else:
                            logger.warning(f"Could not parse file count from badge")
                            continue
                    except Exception as verify_error:
                        logger.warning(f"Error verifying complete pack in box {i}: {verify_error}")
                        continue
                    
                    # Click Instant RD button in this box
                    if prioritize_buttons_in_box(result_box):
                        logger.info(f"Successfully clicked Instant RD button in box {i}")
                        
                        # Check RD status after clicking (within the result box)
                        try:
                            rd_button = WebDriverWait(result_box, 5).until(
                                EC.presence_of_element_located((By.XPATH, ".//button[contains(text(), 'RD (')]"))
                            )
                            rd_button_text = rd_button.text
                            logger.info(f"RD button text after clicking in box {i}: {rd_button_text}")
                            
                            # If RD (0%), undo and continue
                            if "RD (0%)" in rd_button_text:
                                logger.warning(f"RD (0%) detected in box {i}. Undoing click and continuing.")
                                rd_button.click()
                                continue
                            
                            # If RD (100%), we're done!
                            if "RD (100%)" in rd_button_text:
                                logger.success(f"RD (100%) achieved in box {i} for {title_text}")
                                mark_all_episodes_as_confirmed(movie_title, season_num)
                                return True
                                
                        except TimeoutException:
                            logger.warning(f"Timeout waiting for RD status in box {i}")
                            continue
                    else:
                        logger.warning(f"Failed to click Instant RD button in box {i}")
                        continue
                            
                except Exception as e:
                    logger.warning(f"Error processing box {i}: {e}")
                    continue
                    
        except TimeoutException:
            logger.warning(f"No result boxes found for Season {season_num}")
        except Exception as e:
            logger.error(f"Error processing result boxes: {e}")
        
        logger.info(f"No Complete season pack found for Season {season_num}")
        return False
            
    except NoSuchElementException:
        logger.info(f"Complete button not found for Season {season_num}")
        return False
    except Exception as e:
        logger.error(f"Error trying Complete season pack for Season {season_num}: {e}")
        return False


def check_all_rd_buttons(driver, movie_title, normalized_seasons, confirmed_seasons, is_tv_show, episode_id=None, processed_torrents=None, complete_season_pack_only=False):
    """
    Check for both red RD (100%) buttons and green Instant RD buttons on the page.
    
    Args:
        driver: Selenium WebDriver instance
        movie_title: Expected title to match
        normalized_seasons: List of seasons in normalized format
        confirmed_seasons: Set of already confirmed seasons
        is_tv_show: Whether we're checking a TV show
        episode_id: Optional episode ID for TV shows
        processed_torrents: Set of already processed torrent titles to avoid duplicates
        complete_season_pack_only: If True, only accept complete season packs, not individual episodes
    
    Returns:
        Tuple[bool, set]: (confirmation flag, updated confirmed seasons set)
    """
    from seerr.browser import check_red_buttons
    
    logger.info(f"Checking for both RD (100%) and Instant RD buttons")
    
    # First check for red RD (100%) buttons
    confirmation_flag, confirmed_seasons = check_red_buttons(
        driver, movie_title, normalized_seasons, confirmed_seasons, is_tv_show, episode_id, processed_torrents, complete_season_pack_only
    )
    
    if confirmation_flag:
        logger.info("Found RD (100%) buttons - confirmation successful")
        return confirmation_flag, confirmed_seasons
    
    # If no red buttons found, check for green Instant RD buttons
    logger.info("No RD (100%) buttons found, checking for Instant RD buttons")
    
    try:
        # Find all green Instant RD buttons - try multiple approaches
        instant_rd_buttons = []
        
        # Try exact text match first
        instant_rd_buttons = driver.find_elements(By.XPATH, "//button[contains(@class, 'bg-green-900/30') and contains(text(), 'Instant RD')]")
        
        # If no exact match, try looking for buttons containing 'Instant' or 'RD'
        if not instant_rd_buttons:
            instant_rd_buttons = driver.find_elements(By.XPATH, "//button[contains(@class, 'bg-green-900/30') and (contains(text(), 'Instant') or contains(text(), 'RD'))]")
        
        # If still no match, try looking for any green buttons that aren't Report buttons
        if not instant_rd_buttons:
            instant_rd_buttons = driver.find_elements(By.XPATH, "//button[contains(@class, 'bg-green-900/30') and not(contains(text(), 'Report'))]")
        
        logger.info(f"Found {len(instant_rd_buttons)} Instant RD buttons")
        
        if not instant_rd_buttons:
            logger.info("No Instant RD buttons found")
            return False, confirmed_seasons
        
        # Process Instant RD buttons similar to red buttons
        for i, button in enumerate(instant_rd_buttons, 1):
            try:
                button_text = button.text.strip()
                logger.info(f"Processing Instant RD button {i}: '{button_text}'")
                
                # Get the parent container to find the title
                try:
                    # Try multiple XPath strategies to find the title
                    title_element = None
                    title_text = None
                    
                    # Strategy 1: Look for h2 in ancestor div with bg-green-900
                    try:
                        title_element = button.find_element(By.XPATH, "./ancestor::div[contains(@class, 'bg-green-900')]//h2")
                        title_text = title_element.text.strip()
                    except:
                        pass
                    
                    # Strategy 2: Look for h2 in any ancestor div
                    if not title_text:
                        try:
                            title_element = button.find_element(By.XPATH, "./ancestor::div//h2")
                            title_text = title_element.text.strip()
                        except:
                            pass
                    
                    # Strategy 3: Look for any element with class containing 'line-clamp'
                    if not title_text:
                        try:
                            title_element = button.find_element(By.XPATH, "./ancestor::div//*[contains(@class, 'line-clamp')]")
                            title_text = title_element.text.strip()
                        except:
                            pass
                    
                    # Strategy 4: Look for any element with font-bold class
                    if not title_text:
                        try:
                            title_element = button.find_element(By.XPATH, "./ancestor::div//*[contains(@class, 'font-bold')]")
                            title_text = title_element.text.strip()
                        except:
                            pass
                    
                    # Strategy 5: Look for any text element that's not a button
                    if not title_text:
                        try:
                            title_element = button.find_element(By.XPATH, "./ancestor::div//*[not(self::button) and string-length(text()) > 10]")
                            title_text = title_element.text.strip()
                        except:
                            pass
                    
                    if not title_text:
                        logger.warning(f"Could not find title for Instant RD button {i}")
                        continue
                    
                    torrent_title = title_text
                    logger.info(f"Found torrent title: '{torrent_title}'")
                    
                    # Use the same validation logic as red buttons
                    from seerr.utils import clean_title, extract_year, extract_season
                    
                    cleaned_title = clean_title(torrent_title)
                    logger.info(f"Cleaned title: '{cleaned_title}'")
                    
                    # Also clean the movie_title for better comparison
                    cleaned_movie_title = clean_title(movie_title)
                    logger.info(f"Cleaned movie title: '{cleaned_movie_title}'")
                    
                    # Check if this torrent matches our expected title
                    if cleaned_title.lower() in cleaned_movie_title.lower() or cleaned_movie_title.lower() in cleaned_title.lower():
                        logger.info(f"Title match found for Instant RD button: '{torrent_title}'")
                        
                        # If we're looking for complete season packs only, check if this is an individual episode
                        if complete_season_pack_only and is_tv_show:
                            import re
                            # Check for episode patterns like E01, E1, Episode 1, etc.
                            episode_patterns = [
                                r'[sS]\d+[eE]\d+',  # S02E01, s2e3, etc.
                                r'episode\s+\d+',  # Episode 1, Episode 25, etc.
                                r'ep\s+\d+',  # Ep 1, Ep 25, etc.
                                r'[eE]\d+',  # E01, E1, E25, etc.
                            ]
                            
                            is_individual_episode = False
                            for ep_pattern in episode_patterns:
                                if re.search(ep_pattern, torrent_title):
                                    is_individual_episode = True
                                    logger.info(f"Found individual episode pattern in Instant RD torrent '{torrent_title}' - rejecting for complete season pack search")
                                    break
                            
                            if is_individual_episode:
                                logger.info(f"Skipping individual episode Instant RD button '{torrent_title}' - only looking for complete season packs")
                                continue
                        
                        if is_tv_show:
                            # Extract season from title
                            season_from_title = extract_season(torrent_title)
                            if season_from_title:
                                logger.info(f"Extracted season {season_from_title} from Instant RD torrent: '{torrent_title}'")
                                confirmed_seasons.add(f"Season {season_from_title}")
                                confirmation_flag = True
                        else:
                            # For movies, any match is good
                            confirmation_flag = True
                            
                        if confirmation_flag:
                            logger.info(f"Instant RD torrent confirmed: '{torrent_title}' - clicking button")
                            
                            # Get the parent container (result box) for this button
                            try:
                                result_box = button.find_element(By.XPATH, "./ancestor::div[contains(@class, 'border-2')]")
                                
                                # Import prioritize_buttons_in_box
                                from seerr.browser import prioritize_buttons_in_box
                                
                                # Click the button using prioritize_buttons_in_box
                                if prioritize_buttons_in_box(result_box):
                                    logger.info(f"Successfully clicked Instant RD button for: '{torrent_title}'")
                                else:
                                    logger.warning(f"Failed to click Instant RD button for: '{torrent_title}'")
                            except Exception as e:
                                logger.error(f"Error clicking Instant RD button: {e}")
                                # Try to click the button directly as fallback
                                try:
                                    button.click()
                                    logger.info(f"Clicked Instant RD button directly for: '{torrent_title}'")
                                except Exception as click_error:
                                    logger.error(f"Failed to click button directly: {click_error}")
                            
                            break
                    else:
                        logger.info(f"Title mismatch for Instant RD button: '{torrent_title}' vs '{movie_title}'")
                        
                except Exception as e:
                    logger.warning(f"Error processing Instant RD button {i}: {e}")
                    continue
                    
            except Exception as e:
                logger.warning(f"Error getting text for Instant RD button {i}: {e}")
                continue
        
        return confirmation_flag, confirmed_seasons
        
    except Exception as e:
        logger.error(f"Error checking Instant RD buttons: {e}")
        return False, confirmed_seasons


def check_page_loading_state(driver, season_num, strategy_name):
    """
    Check if the page is still loading or has finished loading results.
    
    Args:
        driver: Selenium WebDriver instance
        season_num: Season number being processed
        strategy_name: Name of the strategy (Complete, With extras, etc.)
    
    Returns:
        bool: True if page appears to be loaded, False if still loading
    """
    try:
        logger.info(f"Checking page loading state for Season {season_num} - {strategy_name}")
        
        # Check for loading indicators
        loading_indicators = driver.find_elements(By.XPATH, "//*[contains(@class, 'loading') or contains(@class, 'spinner') or contains(text(), 'Loading')]")
        if loading_indicators:
            logger.info(f"Page still loading - found {len(loading_indicators)} loading indicator(s)")
            return False
        
        # Check if we have any results or "no results" message
        has_results = len(driver.find_elements(By.XPATH, "//button[contains(@class, 'bg-red-900/30')]")) > 0
        has_instant_rd = len(driver.find_elements(By.XPATH, "//button[contains(@class, 'bg-green-900/30') and not(contains(text(), 'Report'))]")) > 0
        has_no_results = len(driver.find_elements(By.XPATH, "//*[contains(text(), 'No results') or contains(text(), 'No torrents')]")) > 0
        
        if has_results or has_instant_rd or has_no_results:
            logger.info(f"Page appears loaded - has_results: {has_results}, has_instant_rd: {has_instant_rd}, has_no_results: {has_no_results}")
            return True
        
        logger.info("Page loading state unclear - no clear indicators found")
        return True  # Assume loaded if we can't determine
        
    except Exception as e:
        logger.error(f"Error checking page loading state: {e}")
        return True  # Assume loaded on error


def get_season_episode_count(movie_title, season_num):
    """
    Get the episode count for a specific season from the database.
    
    Args:
        movie_title: Title of the show
        season_num: Season number
    
    Returns:
        int: Episode count for the season, or None if not found
    """
    if not USE_DATABASE:
        logger.info("Database not enabled, cannot get episode count")
        return None
    
    try:
        from seerr.database import get_db
        from seerr.unified_models import UnifiedMedia
        
        db = get_db()
        try:
            # Find the media record
            media_record = db.query(UnifiedMedia).filter(
                UnifiedMedia.title == movie_title.split(' (')[0],  # Remove year from title
                UnifiedMedia.media_type == 'tv'
            ).first()
            
            if not media_record:
                logger.warning(f"Could not find media record for {movie_title}")
                return None
            
            # Look for the specific season in seasons_data
            if media_record.seasons_data:
                for season_data in media_record.seasons_data:
                    if season_data.get('season_number') == season_num:
                        episode_count = season_data.get('episode_count', 0)
                        logger.info(f"Found episode count for Season {season_num}: {episode_count}")
                        return episode_count
            
            logger.warning(f"No season data found for Season {season_num}")
            return None
                
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error getting episode count for Season {season_num}: {e}")
        return None


def get_season_aired_episodes(movie_title, season_num):
    """
    Get the aired episodes count for a specific season from the database.
    
    Args:
        movie_title: Title of the show
        season_num: Season number
    
    Returns:
        int: Aired episodes count for the season, or None if not found
    """
    if not USE_DATABASE:
        logger.info("Database not enabled, cannot get aired episodes count")
        return None
    
    try:
        from seerr.database import get_db
        from seerr.unified_models import UnifiedMedia
        
        db = get_db()
        try:
            # Find the media record
            media_record = db.query(UnifiedMedia).filter(
                UnifiedMedia.title == movie_title.split(' (')[0],  # Remove year from title
                UnifiedMedia.media_type == 'tv'
            ).first()
            
            if not media_record:
                logger.warning(f"Could not find media record for {movie_title}")
                return None
            
            # Look for the specific season in seasons_data
            if media_record.seasons_data:
                for season_data in media_record.seasons_data:
                    if season_data.get('season_number') == season_num:
                        aired_episodes = season_data.get('aired_episodes', 0)
                        logger.info(f"Found aired episodes count for Season {season_num}: {aired_episodes}")
                        return aired_episodes
            
            logger.warning(f"No season data found for Season {season_num}")
            return None
                
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error getting aired episodes count for Season {season_num}: {e}")
        return None


def try_with_extras_pack(driver, movie_title, season_num, normalized_seasons):
    """
    Try to find a With extras pack by clicking the With extras button.
    Validates that the file count is at least equal to the season's episode count.
    
    Args:
        driver: Selenium WebDriver instance
        movie_title: Title of the show
        season_num: Season number
        normalized_seasons: List of normalized season names
    
    Returns:
        bool: True if with extras pack found and confirmed, False otherwise
    """
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    import time
    import re
    
    try:
        # Look for the With extras button and extract file count
        extras_button = driver.find_element(By.XPATH, "//span[contains(@class, 'bg-blue-900') and contains(text(), 'With extras')]")
        extras_button_text = extras_button.text
        
        logger.info(f"Found With extras button: '{extras_button_text}' for Season {season_num}")
        
        # Extract file count from button text (e.g., "With extras (34/9)" -> 34 files)
        file_count_match = re.search(r'With extras \((\d+)/\d+\)', extras_button_text)
        if file_count_match:
            file_count = int(file_count_match.group(1))
            logger.info(f"With extras pack has {file_count} files for Season {season_num}")
            
            # Get the season's episode count from database
            episode_count = get_season_episode_count(movie_title, season_num)
            if episode_count is not None:
                logger.info(f"Season {season_num} has {episode_count} episodes")
                
                # Validate file count is at least equal to episode count
                if file_count >= episode_count:
                    logger.info(f"File count validation passed: {file_count} >= {episode_count}")
                else:
                    logger.warning(f"File count validation failed: {file_count} < {episode_count}. Skipping With extras pack.")
                    return False
            else:
                logger.warning(f"Could not get episode count for Season {season_num}, proceeding anyway")
        else:
            logger.warning(f"Could not extract file count from With extras button text: '{extras_button_text}'")
        
        # Log page state before clicking
        
        logger.info(f"Clicking With extras button for Season {season_num}")
        extras_button.click()
        
        # Click "Show more results" button if available to load all results
        try:
            show_more_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Show more results')]")
            logger.info(f"Found 'Show more results' button for Season {season_num}, clicking it")
            show_more_button.click()
        except NoSuchElementException:
            logger.info(f"'Show more results' button not found for Season {season_num}, proceeding without it")
        
        # Wait 10 seconds for results to load
        logger.info(f"Waiting 10 seconds for With extras results to load for Season {season_num}")
        time.sleep(10)
        
        # Try to click "Show more results" again after initial load
        try:
            show_more_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Show more results')]")
            logger.info(f"Found 'Show more results' button again for Season {season_num}, clicking it")
            show_more_button.click()
            logger.info(f"Waiting 3 seconds after clicking 'Show more results' for Season {season_num}")
            time.sleep(3)
        except NoSuchElementException:
            logger.info(f"'Show more results' button not available for Season {season_num}, proceeding with available results")
        
        # Check if page is still loading and wait longer if needed
        if not check_page_loading_state(driver, season_num, "With extras"):
            logger.info(f"Page still loading after 10 seconds, waiting additional 5 seconds for Season {season_num}")
            time.sleep(5)
            check_page_loading_state(driver, season_num, "With extras")
        
        # Log page state after waiting
        
        # Quick check: See if there's already an RD (100%) button for this season
        try:
            rd_100_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'RD (100%)') and not(contains(text(), 'Report'))]")
            if rd_100_buttons:
                logger.info(f"Found {len(rd_100_buttons)} existing RD (100%) buttons for Season {season_num}")
                # Check if any of them are for our season
                for button in rd_100_buttons:
                    try:
                        # Get title from parent container
                        title_element = button.find_element(By.XPATH, "./ancestor::div//h2")
                        button_title = title_element.text.strip()
                        
                        # Simple title match
                        tv_show_title_cleaned = clean_title(movie_title.split('(')[0].strip())
                        title_text_cleaned = clean_title(button_title.split('(')[0].strip())
                        
                        if tv_show_title_cleaned.lower() in title_text_cleaned.lower() or title_text_cleaned.lower() in tv_show_title_cleaned.lower():
                            logger.info(f"Found matching RD (100%) for: {button_title}")
                            mark_all_episodes_as_confirmed(movie_title, season_num)
                            return True
                    except:
                        continue
        except:
            pass
        
        # No RD (100%) exists, process result boxes one by one until we get a success
        logger.info(f"No RD (100%) found in With extras results. Processing result boxes for Season {season_num}")
        
        # Get result boxes after clicking With extras
        try:
            result_boxes = WebDriverWait(driver, 5).until(
                EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'border-2')]"))
            )
            logger.info(f"Found {len(result_boxes)} result boxes to process (will stop on first success)")
            
            # Process each result box ONE BY ONE until success
            for i, result_box in enumerate(result_boxes, 1):
                try:
                    # Extract title from result box
                    title_element = result_box.find_element(By.XPATH, ".//h2")
                    title_text = title_element.text.strip()
                    logger.info(f"[Box {i}/{len(result_boxes)}] Processing: {title_text}")
                    
                    # Skip boxes marked as "Single" episodes
                    try:
                        result_box.find_element(By.XPATH, ".//span[contains(., 'Single')]")
                        logger.info(f"Box {i} is a single episode. Skipping.")
                        continue
                    except:
                        pass
                    
                    # Clean and normalize titles for comparison
                    tv_show_title_cleaned = clean_title(movie_title.split('(')[0].strip())
                    title_text_cleaned = clean_title(title_text.split('(')[0].strip())
                    
                    # Check if title matches using fuzzy matching
                    title_match_score = fuzz.partial_ratio(title_text_cleaned.lower(), tv_show_title_cleaned.lower())
                    logger.info(f"Title match score: {title_match_score}% (box: {title_text_cleaned}, expected: {tv_show_title_cleaned})")
                    
                    if title_match_score < 75:
                        logger.info(f"Title mismatch for box {i}. Skipping.")
                        continue
                    
                    # Check if this box has a Complete badge (the real indicator of complete packs)
                    try:
                        complete_badge = result_box.find_element(By.XPATH, ".//span[contains(text(), 'Complete (')]")
                        complete_badge_text = complete_badge.text
                        logger.info(f"Found Complete badge in box {i}: {complete_badge_text}")
                    except:
                        logger.info(f"No Complete badge in box {i}, skipping")
                        continue
                    
                    # Process complete pack
                    logger.info(f"Processing complete season pack in box {i}: {title_text}")
                    
                    # Verify the complete pack by checking the modal before clicking Instant RD
                    try:
                        # Get expected episode count for this season from database if available
                        from seerr.database import get_db, UnifiedMedia
                        expected_episode_count = None
                        try:
                            db = get_db()
                            media = db.query(UnifiedMedia).filter(
                                UnifiedMedia.title == movie_title,
                                UnifiedMedia.type == 'tv'
                            ).first()
                            
                            if media and media.seasons:
                                season_data = next((s for s in media.seasons if s.get('season_number') == season_num), None)
                                if season_data:
                                    episodes = season_data.get('episodes', [])
                                    expected_episode_count = len(episodes) if episodes else None
                                    logger.info(f"Expected episode count for Season {season_num}: {expected_episode_count}")
                        except:
                            pass
                        
                        # Extract the file count from the badge text (e.g., "Complete (9/9)")
                        import re
                        match = re.search(r'Complete \((\d+)/(\d+)\)', complete_badge_text)
                        if match:
                            file_count = int(match.group(2))  # Total files
                            logger.info(f"Complete pack in box {i} contains {file_count} files")
                            
                            # Verify the file count matches expected
                            if expected_episode_count and file_count != expected_episode_count:
                                logger.warning(f"Box {i} has {file_count} files but expected {expected_episode_count}. Skipping.")
                                continue
                            
                            # For extra verification, click the badge to open modal and check the file list
                            try:
                                complete_badge.click()
                                logger.info(f"Opened Complete modal for box {i}")
                                time.sleep(2)  # Wait for modal to open
                                
                                # Try to parse the modal to verify files
                                try:
                                    # Find the modal
                                    modal = driver.find_element(By.XPATH, "//div[contains(@class, 'max-h-[90vh]')]")
                                    
                                    # Get all file rows in the modal
                                    file_rows = modal.find_elements(By.XPATH, ".//tr[@class='bg-gray-800 font-bold hover:bg-gray-700 rounded']")
                                    actual_file_count = len(file_rows)
                                    logger.info(f"Modal shows {actual_file_count} files in the complete pack")
                                    
                                    # Verify the actual file count
                                    if expected_episode_count and actual_file_count != expected_episode_count:
                                        logger.warning(f"Modal verification: box {i} has {actual_file_count} files but expected {expected_episode_count}. Skipping.")
                                        # Close modal
                                        try:
                                            close_button = driver.find_element(By.XPATH, "//button[contains(text(), '×')]")
                                            close_button.click()
                                        except:
                                            # Try clicking overlay if no close button
                                            overlay = driver.find_element(By.XPATH, "//div[contains(@class, 'fixed inset-0') and contains(@class, 'bg-black')]")
                                            overlay.click()
                                            time.sleep(1)
                                        continue
                                    
                                    # Close the modal before proceeding by pressing ESC
                                    logger.info(f"Closing Complete modal for box {i}...")
                                    try:
                                        # Press ESC to close modal
                                        driver.switch_to.active_element.send_keys(Keys.ESCAPE)
                                        logger.info(f"Pressed ESC to close Complete modal for box {i}")
                                        
                                        # Wait for modal to disappear (up to 5 seconds)
                                        WebDriverWait(driver, 5).until(
                                            EC.invisibility_of_element_located((By.XPATH, "//div[contains(@class, 'fixed inset-0') and contains(@class, 'bg-black')]"))
                                        )
                                        logger.info(f"Modal closed for box {i}")
                                    except:
                                        # Fallback: try clicking overlay
                                        try:
                                            overlay = driver.find_element(By.XPATH, "//div[contains(@class, 'fixed inset-0') and contains(@class, 'bg-black')]")
                                            overlay.click()
                                            logger.info(f"Clicked overlay to close modal for box {i}")
                                            WebDriverWait(driver, 5).until(
                                                EC.invisibility_of_element_located((By.XPATH, "//div[contains(@class, 'fixed inset-0') and contains(@class, 'bg-black')]"))
                                            )
                                            logger.info(f"Modal closed for box {i} via overlay click")
                                        except:
                                            logger.warning(f"Could not verify modal closure for box {i}, proceeding anyway")
                                except Exception as modal_error:
                                    logger.warning(f"Could not parse modal for box {i}: {modal_error}")
                                    # Try to close modal anyway
                                    try:
                                        overlay = driver.find_element(By.XPATH, "//div[contains(@class, 'fixed inset-0') and contains(@class, 'bg-black')]")
                                        overlay.click()
                                        time.sleep(1)
                                    except:
                                        pass
                            except Exception as click_error:
                                logger.warning(f"Could not click Complete badge or open modal for box {i}: {click_error}")
                        else:
                            logger.warning(f"Could not parse file count from badge")
                            continue
                    except Exception as verify_error:
                        logger.warning(f"Error verifying complete pack in box {i}: {verify_error}")
                        continue
                    
                    # Click Instant RD button in this box
                    if prioritize_buttons_in_box(result_box):
                        logger.info(f"Successfully clicked Instant RD button in box {i}")
                        
                        # Check RD status after clicking (within the result box)
                        try:
                            rd_button = WebDriverWait(result_box, 5).until(
                                EC.presence_of_element_located((By.XPATH, ".//button[contains(text(), 'RD (')]"))
                            )
                            rd_button_text = rd_button.text
                            logger.info(f"RD button text after clicking in box {i}: {rd_button_text}")
                            
                            # If RD (0%), undo and continue
                            if "RD (0%)" in rd_button_text:
                                logger.warning(f"RD (0%) detected in box {i}. Undoing click and continuing.")
                                rd_button.click()
                                continue
                            
                            # If RD (100%), we're done!
                            if "RD (100%)" in rd_button_text:
                                logger.success(f"RD (100%) achieved in box {i} for {title_text}")
                                mark_all_episodes_as_confirmed(movie_title, season_num)
                                return True
                                
                        except TimeoutException:
                            logger.warning(f"Timeout waiting for RD status in box {i}")
                            continue
                    else:
                        logger.warning(f"Failed to click Instant RD button in box {i}")
                        continue
                            
                except Exception as e:
                    logger.warning(f"Error processing box {i}: {e}")
                    continue
                    
        except TimeoutException:
            logger.warning(f"No result boxes found for Season {season_num}")
        except Exception as e:
            logger.error(f"Error processing result boxes: {e}")
        
        logger.info(f"No With extras pack found for Season {season_num}")
        return False
            
    except NoSuchElementException:
        logger.info(f"With extras button not found for Season {season_num}")
        return False
    except Exception as e:
        logger.error(f"Error trying With extras pack for Season {season_num}: {e}")
        return False


def process_individual_episodes_fallback(driver, movie_title, season_num, normalized_seasons, tmdb_id=None):
    """
    Fall back to individual episode processing when complete packs are not found.
    This is the original logic that processes individual episodes.
    
    Args:
        driver: Selenium WebDriver instance
        movie_title: Title of the show
        season_num: Season number
        normalized_seasons: List of normalized season names
        tmdb_id: TMDB ID for cancellation checks (optional, will be looked up if not provided)
    
    Returns:
        bool: True if episodes are confirmed, False otherwise
    """
    logger.info(f"Processing individual episodes for Season {season_num}")
    
    # Check for red buttons (RD 100%) and verify titles
    confirmed_seasons = set()
    processed_torrents = set()
    confirmation_flag = False
    
    # For in-progress seasons, we need to check for aired episodes specifically
    from seerr.database import get_db
    from seerr.unified_models import UnifiedMedia
    
    aired_episodes_list = []
    if USE_DATABASE:
        try:
            db = get_db()
            try:
                # Get the list of unprocessed episodes (these are the ones that have aired)
                media_record = db.query(UnifiedMedia).filter(
                    UnifiedMedia.title == movie_title.split(' (')[0],
                    UnifiedMedia.media_type == 'tv'
                ).first()
                
                if media_record:
                    tmdb_id = media_record.tmdb_id
                    if media_record.seasons_data:
                        for season_data in media_record.seasons_data:
                            if season_data.get('season_number') == season_num:
                                aired_episodes_list = season_data.get('unprocessed_episodes', [])
                                logger.info(f"Found {len(aired_episodes_list)} aired episodes to process for Season {season_num}: {aired_episodes_list}")
                                break
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error getting aired episodes list: {e}")
    
    # If we have specific aired episodes, check for each one
    if aired_episodes_list:
        for episode in aired_episodes_list:
            # Check if item is still in queue before processing each episode
            if tmdb_id and _check_queue_status(tmdb_id, 'tv'):
                logger.info(f"Item {tmdb_id} is not in queue. Stopping episode processing.")
                return False
            # Extract episode number (e.g., "E01" -> 1)
            try:
                episode_num = int(episode.replace('E', ''))
            except (ValueError, AttributeError):
                logger.warning(f"Could not parse episode number from {episode}")
                continue
            
            # Build episode ID like "E01" (just the episode part)
            episode_id = f"E{episode_num:02d}"
            logger.info(f"Searching for episode: S{season_num:02d}{episode_id}")
            
            # Apply episode-specific filter to reduce the number of results
            try:
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                from selenium.webdriver.common.by import By
                from selenium.common.exceptions import TimeoutException
                
                # Clear and update the filter box with episode-specific filter
                filter_input = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.ID, "query"))
                )
                episode_filter = f"S{season_num:02d}{episode_id}"  # e.g., "S03E01"
                if TORRENT_FILTER_REGEX:
                    full_filter = f"{TORRENT_FILTER_REGEX} {episode_filter}"
                else:
                    full_filter = episode_filter
                
                # Use type_slowly for reliable filter application (same as subscription check)
                from seerr.background_tasks import type_slowly
                type_slowly(driver, filter_input, full_filter)
                logger.info(f"Applied episode filter: {full_filter}")
                
                # Wait for filter to update the results before clicking "Show More Results"
                time.sleep(1)
                
                # Click "Show more results" to expand filtered results
                try:
                    from seerr.browser import click_show_more_results
                    click_show_more_results(driver, logger)
                except TimeoutException:
                    logger.warning("Timed out while trying to click 'Show More Results'")
                except Exception as e:
                    logger.error(f"Unexpected error in click_show_more_results: {e}")
                
                # Wait for results to update after applying the filter
                time.sleep(2)  # Increased from 1 to match subscription check timing
                
            except Exception as e:
                logger.error(f"Error applying episode filter for {episode_id}: {e}")
                continue
            
            # Step 1: Check if episode already has RD (100%) - already cached
            full_episode_id = f"S{season_num:02d}{episode_id}"  # e.g., "S08E01"
            episode_confirmed, _ = check_red_buttons(
                driver, movie_title, normalized_seasons, confirmed_seasons, True, 
                episode_id=full_episode_id, processed_torrents=processed_torrents
            )
            
            if episode_confirmed:
                confirmation_flag = True
                logger.info(f"Episode {full_episode_id} already cached at RD (100%). Marking as confirmed.")
                # Update database immediately with confirmed episode
                if USE_DATABASE:
                    try:
                        from seerr.unified_media_manager import update_media_details
                        from seerr.database import get_db
                        from seerr.unified_models import UnifiedMedia
                        from datetime import datetime
                        
                        db = get_db()
                        try:
                            media_record = db.query(UnifiedMedia).filter(
                                UnifiedMedia.title == movie_title.split(' (')[0],
                                UnifiedMedia.media_type == 'tv'
                            ).first()
                            
                            if media_record and media_record.seasons_data:
                                seasons_data = media_record.seasons_data
                                updated_seasons = []
                                
                                for season_data in seasons_data:
                                    if season_data.get('season_number') == season_num:
                                        # Add episode to confirmed
                                        confirmed = season_data.get('confirmed_episodes', [])
                                        if episode_id not in confirmed:
                                            confirmed.append(episode_id)
                                        season_data['confirmed_episodes'] = confirmed
                                        
                                        # Remove from unprocessed
                                        unprocessed = season_data.get('unprocessed_episodes', [])
                                        if episode_id in unprocessed:
                                            unprocessed.remove(episode_id)
                                        season_data['unprocessed_episodes'] = unprocessed
                                        
                                        # Update timestamp
                                        season_data['updated_at'] = datetime.utcnow().isoformat()
                                    updated_seasons.append(season_data)
                                
                                update_media_details(
                                    media_record.id,
                                    seasons_data=updated_seasons
                                )
                                logger.info(f"Updated database: {episode_id} confirmed (already cached)")
                        finally:
                            db.close()
                    except Exception as db_error:
                        logger.error(f"Error updating database for {full_episode_id}: {db_error}")
                
                # Continue processing remaining aired episodes instead of stopping at first
                continue
            
            # Step 2: No RD (100%) found, process all result boxes to find and process matching torrents
            logger.info(f"No RD (100%) found for {full_episode_id}. Processing all result boxes to find matching torrents.")
            
            try:
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                from selenium.webdriver.common.by import By
                from selenium.common.exceptions import TimeoutException
                from seerr.utils import clean_title
                from fuzzywuzzy import fuzz
                from seerr.browser import prioritize_buttons_in_box
                
                result_boxes = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'border-black')]"))
                )
                logger.info(f"Found {len(result_boxes)} result boxes to process for {full_episode_id}")
                
                episode_confirmed = False
                for i, result_box in enumerate(result_boxes, start=1):
                    # Check if item is still in queue during processing
                    if tmdb_id and _check_queue_status(tmdb_id, 'tv'):
                        logger.info(f"Item {tmdb_id} is not in queue. Stopping episode processing.")
                        return False
                    
                    try:
                        title_element = result_box.find_element(By.XPATH, ".//h2")
                        title_text = title_element.text.strip()
                        logger.info(f"Box {i} title: {title_text}")
                        
                        # Check if this torrent matches our episode
                        if full_episode_id.lower() in title_text.lower():
                            title_clean = clean_title(title_text, 'en')
                            movie_title_clean = clean_title(movie_title.split(' (')[0], 'en')
                            match_ratio = fuzz.partial_ratio(title_clean, movie_title_clean)
                            logger.info(f"Match ratio: {match_ratio} for '{title_clean}' vs '{movie_title_clean}'")
                            
                            if match_ratio >= 50:
                                logger.info(f"Found match for {full_episode_id} in box {i}: {title_text}")
                                
                                # Process the torrent (click buttons to get RD (100%))
                                if prioritize_buttons_in_box(result_box):
                                    logger.info(f"Successfully processed {full_episode_id} in box {i}")
                                    episode_confirmed = True
                                    
                                    # Verify RD status after processing
                                    try:
                                        rd_button = WebDriverWait(driver, 10).until(
                                            EC.presence_of_element_located((By.XPATH, ".//button[contains(text(), 'RD (')]"))
                                        )
                                        rd_button_text = rd_button.text
                                        if "RD (100%)" in rd_button_text:
                                            logger.success(f"RD (100%) confirmed for {full_episode_id}. Episode fully processed.")
                                            confirmation_flag = True
                                            processed_torrents.add(title_text)
                                            break
                                        elif "RD (0%)" in rd_button_text:
                                            logger.warning(f"RD (0%) detected for {full_episode_id}. Undoing and skipping.")
                                            rd_button.click()
                                            episode_confirmed = False
                                            continue
                                    except TimeoutException:
                                        logger.warning(f"Timeout waiting for RD status for {full_episode_id}")
                                        continue
                                else:
                                    logger.warning(f"Failed to process buttons for {full_episode_id} in box {i}")
                        
                    except Exception as e:
                        logger.warning(f"Error processing box {i} for {full_episode_id}: {e}")
                
                if episode_confirmed:
                    logger.info(f"Successfully processed episode: {full_episode_id}")
                    # Update database immediately with confirmed episode
                    if USE_DATABASE:
                        try:
                            from seerr.unified_media_manager import get_media_by_overseerr_request, update_media_details
                            from seerr.database import get_db
                            from seerr.unified_models import UnifiedMedia
                            from datetime import datetime
                            
                            db = get_db()
                            try:
                                media_record = db.query(UnifiedMedia).filter(
                                    UnifiedMedia.title == movie_title.split(' (')[0],
                                    UnifiedMedia.media_type == 'tv'
                                ).first()
                                
                                if media_record and media_record.seasons_data:
                                    seasons_data = media_record.seasons_data
                                    updated_seasons = []
                                    
                                    for season_data in seasons_data:
                                        if season_data.get('season_number') == season_num:
                                            # Add episode to confirmed
                                            confirmed = season_data.get('confirmed_episodes', [])
                                            if episode_id not in confirmed:
                                                confirmed.append(episode_id)
                                            season_data['confirmed_episodes'] = confirmed
                                            
                                            # Remove from unprocessed
                                            unprocessed = season_data.get('unprocessed_episodes', [])
                                            if episode_id in unprocessed:
                                                unprocessed.remove(episode_id)
                                            season_data['unprocessed_episodes'] = unprocessed
                                            
                                            # Update timestamp
                                            season_data['updated_at'] = datetime.utcnow().isoformat()
                                        updated_seasons.append(season_data)
                                    
                                    update_media_details(
                                        media_record.id,
                                        seasons_data=updated_seasons
                                    )
                                    logger.info(f"Updated database: {episode_id} confirmed")
                            finally:
                                db.close()
                        except Exception as db_error:
                            logger.error(f"Error updating database for {full_episode_id}: {db_error}")
                else:
                    logger.info(f"No matching torrents found or processed for episode: {full_episode_id}")
                    # Update database with failed episode
                    if USE_DATABASE:
                        try:
                            from seerr.unified_media_manager import get_media_by_overseerr_request, update_media_details
                            from seerr.database import get_db
                            from seerr.unified_models import UnifiedMedia
                            from datetime import datetime
                            
                            db = get_db()
                            try:
                                media_record = db.query(UnifiedMedia).filter(
                                    UnifiedMedia.title == movie_title.split(' (')[0],
                                    UnifiedMedia.media_type == 'tv'
                                ).first()
                                
                                if media_record and media_record.seasons_data:
                                    seasons_data = media_record.seasons_data
                                    updated_seasons = []
                                    
                                    for season_data in seasons_data:
                                        if season_data.get('season_number') == season_num:
                                            # Add episode to failed
                                            failed = season_data.get('failed_episodes', [])
                                            if episode_id not in failed:
                                                failed.append(episode_id)
                                            season_data['failed_episodes'] = failed
                                            
                                            # Remove from unprocessed
                                            unprocessed = season_data.get('unprocessed_episodes', [])
                                            if episode_id in unprocessed:
                                                unprocessed.remove(episode_id)
                                            season_data['unprocessed_episodes'] = unprocessed
                                            
                                            # Update timestamp
                                            season_data['updated_at'] = datetime.utcnow().isoformat()
                                        updated_seasons.append(season_data)
                                    
                                    update_media_details(
                                        media_record.id,
                                        seasons_data=updated_seasons
                                    )
                                    logger.info(f"Updated database: {episode_id} marked as failed")
                            finally:
                                db.close()
                        except Exception as db_error:
                            logger.error(f"Error updating database for failed {full_episode_id}: {db_error}")
                    
            except Exception as e:
                logger.error(f"Error processing result boxes for {full_episode_id}: {e}")
    else:
        # Fallback: check for any episode in the season
        logger.info(f"No aired episodes list found, checking for any episode in Season {season_num}")
        confirmation_flag, confirmed_seasons = check_red_buttons(
            driver, movie_title, normalized_seasons, confirmed_seasons, True, processed_torrents=processed_torrents
        )
    
    if confirmation_flag:
        logger.info(f"Season {season_num} confirmed with individual episodes")
        logger.info(f"Total processed torrents collected: {len(processed_torrents)} - {list(processed_torrents)}")
        
        # Extract episode information from confirmed torrents and update database
        confirmed_episodes = extract_episodes_from_torrents(driver, movie_title, season_num, processed_torrents)
        if confirmed_episodes:
            logger.info(f"Extracted {len(confirmed_episodes)} episodes from torrents: {confirmed_episodes}")
            update_database_with_confirmed_episodes(movie_title, season_num, confirmed_episodes)
        else:
            logger.warning(f"No episodes could be extracted from processed torrents")
        
        return True
    else:
        logger.warning(f"Season {season_num} not confirmed - no matching individual episodes found")
        return False


def mark_all_episodes_as_confirmed(movie_title, season_num):
    """
    Mark all episodes for a season as confirmed when we have a complete pack.
    
    Uses the unified_media_manager.update_media_details() function to coordinate
    with background tasks instead of fighting them.
    
    Args:
        movie_title: Title of the show
        season_num: Season number
    """
    if not USE_DATABASE:
        logger.info("Database not enabled, skipping episode confirmation update")
        return
    
    try:
        from seerr.database import get_db
        from seerr.unified_models import UnifiedMedia
        from seerr.unified_media_manager import update_media_details
        
        # Find the media record
        db = get_db()
        try:
            clean_title = movie_title.split(' (')[0]  # Remove year from title
            
            # Try to find the media record
            media_record = db.query(UnifiedMedia).filter(
                UnifiedMedia.title == clean_title,
                UnifiedMedia.media_type == 'tv'
            ).first()
            
            if not media_record:
                logger.warning(f"Could not find media record for title '{clean_title}', trying with full title '{movie_title}'")
                # Second try: full title match
                media_record = db.query(UnifiedMedia).filter(
                    UnifiedMedia.title == movie_title,
                    UnifiedMedia.media_type == 'tv'
                ).first()
            
            if not media_record:
                logger.warning(f"Could not find media record for {movie_title} or {clean_title}")
                return
            
            logger.info(f"Found media record for {media_record.title} (ID: {media_record.id})")
            
            # Check if the season is already marked as complete
            if media_record.seasons_data:
                for season_data in media_record.seasons_data:
                    if season_data.get('season_number') == season_num:
                        if season_data.get('is_complete', False) and season_data.get('status') == 'completed':
                            logger.info(f"Season {season_num} is already marked as complete. Skipping update.")
                            return
                        break
            
            # Get the current seasons_data
            if not media_record.seasons_data:
                logger.warning(f"No seasons_data found for {movie_title}")
                return
            
            # Find the season we want to update
            seasons_data = media_record.seasons_data.copy()
            season_found = False
            
            for season_data in seasons_data:
                if season_data.get('season_number') == season_num:
                    aired_episodes = season_data.get('aired_episodes', 0)
                    
                    # Create confirmed episodes list for all aired episodes
                    confirmed_episodes = []
                    for ep in range(1, aired_episodes + 1):
                        confirmed_episodes.append(f"E{ep:02d}")
                    
                    # Update the season data
                    season_data['confirmed_episodes'] = confirmed_episodes
                    season_data['unprocessed_episodes'] = []  # All episodes are processed
                    season_data['is_complete'] = True
                    season_data['completion_method'] = 'complete_pack'
                    season_data['status'] = 'completed'
                    season_data['updated_at'] = datetime.utcnow().isoformat()
                    season_found = True
                    
                    logger.info(f"Prepared Season {season_num} update with {len(confirmed_episodes)} confirmed episodes: {confirmed_episodes}")
                    break
            
            if not season_found:
                logger.warning(f"No season data found for Season {season_num} in {len(seasons_data)} seasons")
                return
            
            # Use the unified_media_manager to update the database
            # This coordinates with background tasks instead of fighting them
            logger.info(f"Updating database using unified_media_manager for Season {season_num}")
            success = update_media_details(
                media_record.id,
                seasons_data=seasons_data,
                last_checked_at=datetime.utcnow()
            )
            
            if success:
                logger.success(f"Successfully updated database - Season {season_num} marked as complete with all episodes confirmed")
            else:
                logger.error(f"Failed to update database for Season {season_num}")
                
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error marking all episodes as confirmed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")


def mark_season_as_complete(movie_title, season_num):
    """
    Mark a season as complete in the database.
    
    Args:
        movie_title: Title of the show
        season_num: Season number
    """
    if not USE_DATABASE:
        logger.info("Database not enabled, skipping season completion update")
        return
    
    try:
        from seerr.database import get_db
        from seerr.unified_models import UnifiedMedia
        
        db = get_db()
        try:
            # Find the media record - try multiple approaches
            media_record = None
            
            # First try: exact title match
            clean_title = movie_title.split(' (')[0]  # Remove year from title
            media_record = db.query(UnifiedMedia).filter(
                UnifiedMedia.title == clean_title,
                UnifiedMedia.media_type == 'tv'
            ).first()
            
            if not media_record:
                logger.warning(f"Could not find media record for title '{clean_title}', trying with full title '{movie_title}'")
                # Second try: full title match
                media_record = db.query(UnifiedMedia).filter(
                    UnifiedMedia.title == movie_title,
                    UnifiedMedia.media_type == 'tv'
                ).first()
            
            if not media_record:
                logger.warning(f"Could not find media record for {movie_title} or {clean_title}")
                return
            
            logger.info(f"Found media record for {media_record.title} (ID: {media_record.id})")
            
            # Update seasons_data to mark season as complete
            if media_record.seasons_data:
                seasons_data = media_record.seasons_data
                updated = False
                
                logger.info(f"Processing seasons_data: {seasons_data}")
                
                for season_data in seasons_data:
                    if season_data.get('season_number') == season_num:
                        season_data['is_complete'] = True
                        season_data['completion_method'] = 'complete_pack'
                        season_data['updated_at'] = datetime.utcnow().isoformat()
                        updated = True
                        logger.info(f"Marked Season {season_num} as complete with complete pack")
                    else:
                        logger.info(f"Skipping season {season_data.get('season_number')} (looking for {season_num})")
                
                if updated:
                    media_record.seasons_data = seasons_data
                    media_record.updated_at = datetime.utcnow()
                    db.commit()
                    logger.success(f"Updated database - Season {season_num} marked as complete")
                else:
                    logger.warning(f"No season data found for Season {season_num} in {len(seasons_data)} seasons")
            else:
                logger.warning(f"No seasons_data found for {movie_title}")
                
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error marking season as complete: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")


def mark_season_as_discrepant(movie_title, season_num, reason):
    """
    Mark a season as discrepant in the database.
    
    Args:
        movie_title: Title of the show
        season_num: Season number
        reason: Reason for discrepancy
    
    Returns:
        bool: True if successfully marked as discrepant, False otherwise
    """
    if not USE_DATABASE:
        logger.info("Database not enabled, skipping season discrepancy update")
        return False
    
    try:
        from seerr.database import get_db
        from seerr.unified_models import UnifiedMedia
        
        db = get_db()
        try:
            # Find the media record
            media_record = db.query(UnifiedMedia).filter(
                UnifiedMedia.title == movie_title.split(' (')[0],  # Remove year from title
                UnifiedMedia.media_type == 'tv'
            ).first()
            
            if not media_record:
                logger.warning(f"Could not find media record for {movie_title}")
                return False
            
            # Update seasons_data to mark season as discrepant
            if media_record.seasons_data:
                seasons_data = media_record.seasons_data
                updated = False
                
                for season_data in seasons_data:
                    if season_data.get('season_number') == season_num:
                        season_data['is_discrepant'] = True
                        season_data['discrepancy_reason'] = reason
                        season_data['updated_at'] = datetime.utcnow().isoformat()
                        updated = True
                        logger.info(f"Marked Season {season_num} as discrepant: {reason}")
                
                if updated:
                    media_record.seasons_data = seasons_data
                    media_record.updated_at = datetime.utcnow()
                    db.commit()
                    logger.success(f"Updated database - Season {season_num} marked as discrepant")
                    return True
                else:
                    logger.info(f"No season data to update for Season {season_num}")
                    return False
            else:
                logger.warning(f"No seasons_data found for {movie_title}")
                return False
                
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error marking season as discrepant: {e}")
        return False


def is_season_discrepant(movie_title, season_num):
    """
    Check if a season is marked as discrepant in the database.
    
    Args:
        movie_title: Title of the show
        season_num: Season number to check
    
    Returns:
        bool: True if season is discrepant, False otherwise
    """
    if not USE_DATABASE:
        logger.info("Database not enabled, assuming season is not discrepant")
        return False
    
    try:
        from seerr.database import get_db
        from seerr.unified_models import UnifiedMedia
        
        db = get_db()
        try:
            # Find the media record
            media_record = db.query(UnifiedMedia).filter(
                UnifiedMedia.title == movie_title.split(' (')[0],  # Remove year from title
                UnifiedMedia.media_type == 'tv'
            ).first()
            
            if not media_record or not media_record.seasons_data:
                logger.info(f"No media record or seasons data found for {movie_title}")
                return False
            
            # Check if the specific season is marked as discrepant
            for season_data in media_record.seasons_data:
                if (isinstance(season_data, dict) and 
                    season_data.get('season_number') == season_num and
                    season_data.get('is_discrepant', False)):
                    logger.info(f"Season {season_num} is marked as discrepant: {season_data.get('discrepancy_reason', 'unknown')}")
                    return True
            
            logger.info(f"Season {season_num} is not marked as discrepant")
            return False
                
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error checking season discrepancy: {e}")
        return False


def is_season_completed(movie_title, season_num, tmdb_id=None):
    """
    Check if a season is already completed in the database.
    
    Args:
        movie_title: Title of the show
        season_num: Season number to check
        tmdb_id: TMDB ID (optional, for more accurate lookup)
    
    Returns:
        bool: True if season is completed, False otherwise
    """
    if not USE_DATABASE:
        logger.info("Database not enabled, assuming season is not completed")
        return False
    
    try:
        from seerr.database import get_db
        from seerr.unified_models import UnifiedMedia
        
        db = get_db()
        try:
            # Find the media record - try multiple approaches
            media_record = None
            
            if tmdb_id:
                # First try: TMDB ID lookup (most accurate)
                media_record = db.query(UnifiedMedia).filter(
                    UnifiedMedia.tmdb_id == tmdb_id,
                    UnifiedMedia.media_type == 'tv'
                ).first()
            
            if not media_record:
                # Second try: exact title match
                clean_title = movie_title.split(' (')[0]  # Remove year from title
                media_record = db.query(UnifiedMedia).filter(
                    UnifiedMedia.title == clean_title,
                    UnifiedMedia.media_type == 'tv'
                ).first()
            
            if not media_record:
                # Third try: full title match
                media_record = db.query(UnifiedMedia).filter(
                    UnifiedMedia.title == movie_title,
                    UnifiedMedia.media_type == 'tv'
                ).first()
            
            if not media_record or not media_record.seasons_data:
                logger.info(f"No media record or seasons data found for {movie_title}")
                return False
            
            # Check if the specific season is completed
            for season_data in media_record.seasons_data:
                if (isinstance(season_data, dict) and 
                    season_data.get('season_number') == season_num):
                    season_status = season_data.get('status', 'unknown')
                    is_complete = season_data.get('is_complete', False)
                    
                    if season_status == 'completed' or is_complete:
                        logger.info(f"Season {season_num} is completed (status: {season_status}, is_complete: {is_complete})")
                        return True
                    else:
                        logger.info(f"Season {season_num} is not completed (status: {season_status}, is_complete: {is_complete})")
                        return False
            
            logger.info(f"Season {season_num} not found in seasons data")
            return False
                
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error checking season completion: {e}")
        return False


def is_season_in_progress(movie_title, season_num):
    """
    Check if a season is in-progress (partially aired).
    A season is in-progress if aired_episodes < episode_count.
    
    Args:
        movie_title: Title of the show
        season_num: Season number to check
    
    Returns:
        bool: True if season is in-progress, False otherwise
    """
    if not USE_DATABASE:
        logger.info("Database not enabled, assuming season is not in-progress")
        return False
    
    try:
        from seerr.database import get_db
        from seerr.unified_models import UnifiedMedia
        
        db = get_db()
        try:
            # Find the media record
            media_record = db.query(UnifiedMedia).filter(
                UnifiedMedia.title == movie_title.split(' (')[0],  # Remove year from title
                UnifiedMedia.media_type == 'tv'
            ).first()
            
            if not media_record or not media_record.seasons_data:
                logger.info(f"No media record or seasons data found for {movie_title}")
                return False
            
            # Check if the specific season is in-progress
            for season_data in media_record.seasons_data:
                if isinstance(season_data, dict) and season_data.get('season_number') == season_num:
                    aired_episodes = season_data.get('aired_episodes', 0)
                    episode_count = season_data.get('episode_count', 0)
                    
                    # Season is in-progress if there are aired episodes but not all episodes have aired yet
                    if aired_episodes > 0 and episode_count > 0 and aired_episodes < episode_count:
                        logger.info(f"Season {season_num} is in-progress: {aired_episodes}/{episode_count} episodes aired")
                        return True
                    break
            
            logger.info(f"Season {season_num} is not in-progress")
            return False
                
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error checking if season is in-progress: {e}")
        return False


def process_season_page(driver, movie_title, season_num, normalized_seasons, tmdb_id=None):
    """
    Process a specific season page for torrents and confirmations.
    
    Args:
        driver: Selenium WebDriver instance
        movie_title: Title of the show
        season_num: Season number to process
        normalized_seasons: List of normalized season names
        tmdb_id: TMDB ID for cancellation checks
    
    Returns:
        bool: True if season is confirmed, False otherwise
    """
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import TimeoutException
    
    logger.info(f"Processing season {season_num} page for {movie_title}")
    
    # Check if item is still in queue
    if tmdb_id and _check_queue_status(tmdb_id, 'tv'):
        logger.info(f"Item {tmdb_id} is not in queue. Stopping season processing.")
        return False
    
    # Check if this season is in-progress (partially aired) - if so, skip Complete and With extras strategies
    if is_season_in_progress(movie_title, season_num):
        logger.info(f"Season {season_num} is in-progress - skipping Complete and With extras strategies, using individual episode processing only")
        return process_individual_episodes_fallback(driver, movie_title, season_num, normalized_seasons, tmdb_id)
    
    # Check if this season is discrepant - if so, skip Complete and With extras strategies
    if is_season_discrepant(movie_title, season_num):
        logger.info(f"Season {season_num} is discrepant - skipping Complete and With extras strategies, using individual episode processing only")
        # Skip directly to individual episode processing for discrepant seasons
        return process_individual_episodes_fallback(driver, movie_title, season_num, normalized_seasons, tmdb_id)
    
    try:
        # Check for "No results found" message
        try:
            no_results_element = WebDriverWait(driver, 2).until(
                EC.text_to_be_present_in_element(
                    (By.XPATH, "//div[@role='status' and contains(@aria-live, 'polite')]"),
                    "No results found"
                )
            )
            logger.warning(f"'No results found' message detected for season {season_num}. Skipping.")
            return False
        except TimeoutException:
            logger.info(f"'No results found' message not detected for season {season_num}. Proceeding.")
        
        # Check for available torrents status
        try:
            status_element = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[@role='status' and contains(@aria-live, 'polite') and contains(text(), 'available torrents in RD')]")
                )
            )
            status_text = status_element.text
            logger.info(f"Season {season_num} status message: {status_text}")
            
            # Extract torrent count
            import re
            torrents_match = re.search(r"Found (\d+) available torrents in RD", status_text)
            if torrents_match:
                torrents_count = int(torrents_match.group(1))
                logger.info(f"Found {torrents_count} available torrents in RD for season {season_num}.")
            else:
                logger.warning(f"Could not find expected torrent count message for season {season_num}.")
        except TimeoutException:
            logger.warning(f"Timeout waiting for RD status message for season {season_num}. Proceeding.")
        
        # Wait for "Checking RD availability..." to appear
        logger.info(f"Waiting for 'Checking RD availability...' to appear for season {season_num}.")
        
        # Strategy 1: Try to find Complete season packs first (only for non-discrepant seasons)
        logger.info(f"Strategy 1: Looking for Complete season packs for Season {season_num}")
        complete_confirmed = try_complete_season_pack(driver, movie_title, season_num, normalized_seasons)
        if complete_confirmed:
            logger.info(f"Season {season_num} confirmed with Complete pack")
            return True
        
        # Strategy 2: Try "With extras" if Complete failed (only for non-discrepant seasons)
        logger.info(f"Strategy 2: Looking for With extras packs for Season {season_num}")
        extras_confirmed = try_with_extras_pack(driver, movie_title, season_num, normalized_seasons)
        if extras_confirmed:
            logger.info(f"Season {season_num} confirmed with With extras pack")
            return True
        
        # Strategy 3: Fall back to individual episode processing
        logger.info(f"Strategy 3: Falling back to individual episode processing for Season {season_num} since no Complete or With extras packs found")
        
        # Ensure all aired episodes are in unprocessed_episodes for individual processing
        if USE_DATABASE:
            try:
                from seerr.database import get_db
                from seerr.unified_models import UnifiedMedia
                from seerr.unified_media_manager import update_media_details
                from datetime import datetime
                
                db = get_db()
                try:
                    media_record = db.query(UnifiedMedia).filter(
                        UnifiedMedia.title == movie_title.split(' (')[0],
                        UnifiedMedia.media_type == 'tv'
                    ).first()
                    
                    if media_record and media_record.seasons_data:
                        seasons_data = media_record.seasons_data
                        updated = False
                        
                        for season_data in seasons_data:
                            if season_data.get('season_number') == season_num:
                                aired_episodes = season_data.get('aired_episodes', 0)
                                if aired_episodes > 0:
                                    # Generate list of all aired episodes
                                    all_episodes = [f"E{str(i).zfill(2)}" for i in range(1, aired_episodes + 1)]
                                    
                                    # Get current unprocessed, confirmed, and failed episodes
                                    unprocessed = season_data.get('unprocessed_episodes', [])
                                    confirmed = season_data.get('confirmed_episodes', [])
                                    failed = season_data.get('failed_episodes', [])
                                    
                                    # Add all aired episodes to unprocessed if they're not already confirmed or failed
                                    for episode in all_episodes:
                                        if episode not in confirmed and episode not in failed and episode not in unprocessed:
                                            unprocessed.append(episode)
                                    
                                    season_data['unprocessed_episodes'] = unprocessed
                                    season_data['updated_at'] = datetime.utcnow().isoformat()
                                    updated = True
                                    logger.info(f"Added {len(all_episodes)} aired episodes to unprocessed_episodes for Season {season_num}: {all_episodes}")
                                    break
                        
                        if updated:
                            update_media_details(
                                media_record.id,
                                seasons_data=seasons_data
                            )
                            logger.info(f"Updated database with all aired episodes for Season {season_num}")
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"Error updating unprocessed episodes for Season {season_num}: {e}")
        
        # Refresh the page to get fresh results and clear any cached Complete/With extras results
        logger.info(f"Refreshing page for Season {season_num} to get fresh results for individual episode processing")
        driver.refresh()
        
        # Wait for page to load after refresh
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='status' and contains(@aria-live, 'polite')]"))
            )
            logger.info(f"Page refreshed successfully for Season {season_num}")
        except Exception as e:
            logger.warning(f"Timeout waiting for page refresh for Season {season_num}: {e}")
        
        # Process individual episodes for the entire season
        individual_result = process_individual_episodes_fallback(driver, movie_title, season_num, normalized_seasons)
        
        if individual_result:
            logger.info(f"Season {season_num} confirmed through individual episode processing")
            return True
        else:
            logger.warning(f"Season {season_num} individual episode processing did not confirm any episodes")
            return False
            
    except Exception as e:
        logger.error(f"Error processing season {season_num} page: {e}")
        return False


def _check_queue_status(tmdb_id, media_type):
    """
    Check if the current item is still in the queue.
    Database is the source of truth - if is_in_queue is False, stop processing.
    
    Args:
        tmdb_id (int): TMDB ID of the media
        media_type (str): Type of media ('movie' or 'tv')
        
    Returns:
        bool: True if item should stop processing (not in queue), False if should continue (in queue)
    """
    if not tmdb_id:
        return False
    
    try:
        if USE_DATABASE:
            from seerr.unified_media_manager import get_media_by_tmdb
            media_record = get_media_by_tmdb(tmdb_id, media_type)
            if media_record:
                # Simple check: if not in queue, stop processing
                if not media_record.is_in_queue:
                    logger.info(f"Item {tmdb_id} ({media_type}) is not in queue. Stopping processing.")
                    return True
                # Item is in queue, continue processing
                return False
        # If database not available or record not found, continue processing
        return False
    except Exception as e:
        logger.error(f"Error checking queue status: {e}")
        # On error, continue processing (safer than stopping)
        return False

def search_on_debrid(imdb_id, movie_title, media_type, driver, extra_data=None, tmdb_id=None):
    """
    Search for media on Debrid Media Manager
    
    Args:
        imdb_id (str): IMDb ID of the media
        movie_title (str): Title of the media
        media_type (str): Type of media ('movie' or 'tv')
        driver: Selenium WebDriver instance (passed from caller)
        extra_data (list, optional): Extra data for the request
        tmdb_id (int, optional): TMDB ID of the media
        
    Returns:
        bool: True if media was found and processed, False otherwise
    """
    # Import Selenium components at function level to avoid scope issues
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    from seerr.browser import check_red_buttons
    import re  # Import re at function level since it's used locally later
    
    # Check if item is still in queue at the start
    if tmdb_id and _check_queue_status(tmdb_id, media_type):
        logger.info(f"Item {movie_title} (TMDB: {tmdb_id}) is not in queue. Stopping search.")
        return "cancelled"
    try:
        logger.info(f"Starting Selenium automation for IMDb ID: {imdb_id}, Media Type: {media_type}")
        
        # Check if media is already available in Real-Debrid before processing
        if USE_DATABASE:
            from seerr.unified_media_manager import get_media_by_tmdb
            media_record = get_media_by_tmdb(tmdb_id, media_type)
            
            if media_record and media_record.status == 'completed':
                logger.info(f"Media {tmdb_id} ({media_type}) is already completed. Checking if still available in RD...")
                
                # Check if we can verify it's still available in RD without full processing
                from seerr.browser import driver
                if driver:
                    try:
                        # Quick check if media is still available in RD
                        from seerr.utils import translate_title_for_search
                        search_title = translate_title_for_search(movie_title)
                        
                        # Navigate to search page
                        driver.get("https://debridmediamanager.com/search")
                        
                        # Wait for search input and search
                        search_input = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.ID, "search-input"))
                        )
                        search_input.clear()
                        search_input.send_keys(search_title)
                        search_input.send_keys(Keys.RETURN)
                        
                        # Wait for results
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CLASS_NAME, "search-results"))
                        )
                        
                        # Check if we have RD (100%) results
                        red_buttons = check_red_buttons(movie_title, media_type)
                        
                        if red_buttons and len(red_buttons) > 0:
                            logger.info(f"Media {movie_title} is still available in RD (100%). Skipping duplicate processing.")
                            return "already_available"
                        else:
                            logger.info(f"Media {movie_title} not found in RD search. Proceeding with processing.")
                    except Exception as e:
                        logger.warning(f"Could not verify RD availability: {e}. Proceeding with processing.")
        
        # Process extra_data
    except Exception as e:
        logger.error(f"Error in search_on_debrid function start: {e}")
        return False
    
    # Check if media has already been processed before starting browser automation
    if USE_DATABASE:
        from seerr.unified_media_manager import is_media_processed, is_media_processing, start_media_processing, update_media_processing_status
        
        # Use the passed tmdb_id parameter, or look it up from the database
        if not tmdb_id:
            from seerr.database import get_db
            from seerr.unified_models import UnifiedMedia
            
            db = get_db()
            try:
                media_record = db.query(UnifiedMedia).filter(
                    UnifiedMedia.imdb_id == imdb_id,
                    UnifiedMedia.media_type == media_type
                ).first()
                
                if media_record:
                    tmdb_id = media_record.tmdb_id
                    pass  # Found TMDB ID from database
                else:
                    logger.warning(f"No media record found for IMDb ID {imdb_id} ({media_type}) in database")
            finally:
                db.close()
        
        if tmdb_id:
            # Check if already processed
            # Get trakt_id from extra_data if available
            trakt_id = None
            if extra_data:
                # Handle JSON string from database
                if isinstance(extra_data, str):
                    try:
                        extra_data = json.loads(extra_data)
                    except (json.JSONDecodeError, TypeError):
                        logger.warning(f"Failed to parse extra_data as JSON: {extra_data}")
                        extra_data = None
                
                if extra_data:
                    if isinstance(extra_data, list) and len(extra_data) > 0:
                        # Old format: list of dictionaries
                        first_item = extra_data[0]
                        if isinstance(first_item, dict):
                            trakt_id = first_item.get('value')
                        else:
                            logger.warning(f"Expected dict for extra_data item, got {type(first_item)}: {first_item}")
                    elif isinstance(extra_data, dict):
                        # New format: direct dictionary
                        trakt_id = extra_data.get('trakt_id')
            
            is_processed, processed_record = is_media_processed(tmdb_id, media_type, imdb_id, trakt_id)
            
            if is_processed:
                if processed_record.status == 'ignored':
                    logger.info(f"Media {tmdb_id} ({media_type}) has status ignored. Skipping browser automation.")
                    return "skipped"
                elif processed_record.status == 'completed':
                    logger.info(f"Media {tmdb_id} ({media_type}) already completed processing. Skipping browser automation.")
                    return "already_completed"
                elif processed_record.status == 'failed':
                    logger.info(f"Media {tmdb_id} ({media_type}) previously failed. Retrying browser automation...")
                    # Update status to processing
                    update_media_processing_status(processed_record.id, 'processing', 'browser_automation')
                elif processed_record.status == 'processing':
                    # This is expected during queue processing - continue with the work
                    logger.info(f"Media {tmdb_id} ({media_type}) is being processed. Continuing with browser automation...")
                elif processed_record.status == 'pending':
                    # Pending status means it should be processed - update to processing and continue
                    logger.info(f"Media {tmdb_id} ({media_type}) has pending status. Starting browser automation...")
                    update_media_processing_status(processed_record.id, 'processing', 'browser_automation')
                else:
                    logger.info(f"Media {tmdb_id} ({media_type}) has status {processed_record.status}. Skipping browser automation.")
                    return "skipped"
            
            # Note: Removed is_media_processing check as this function is called during queue processing
            
            # Start tracking browser automation
            trakt_id = None
            if extra_data:
                if isinstance(extra_data, list) and len(extra_data) > 0:
                    # Old format: list of dictionaries
                    first_item = extra_data[0]
                    if isinstance(first_item, dict):
                        trakt_id = first_item.get('value')
                elif isinstance(extra_data, dict):
                    # New format: direct dictionary
                    trakt_id = extra_data.get('trakt_id')
            
            processed_media_id = start_media_processing(
                tmdb_id=tmdb_id,
                imdb_id=imdb_id,
                trakt_id=trakt_id,
                media_type=media_type,
                title=movie_title,
                year=None,  # Will be updated if available
                processing_stage='browser_automation',
                extra_data=extra_data
            )
        else:
            logger.warning("TMDB ID not found in extra_data. Cannot track processing status.")
            processed_media_id = None
    
    # Use the imported driver module if the passed driver is None
    from seerr.browser import driver as browser_driver
    if driver is None:
        if browser_driver is None:
            logger.error("Selenium WebDriver is not initialized. Cannot proceed.")
            if USE_DATABASE and processed_media_id:
                update_media_processing_status(processed_media_id, 'failed', 'browser_automation', error_message='Selenium WebDriver not initialized')
            return False
        logger.info("Using the global browser driver instance.")
        driver = browser_driver
        
    # Extract requested seasons from the extra data
    logger.info(f"Debug: extra_data = {extra_data}")
    requested_seasons = parse_requested_seasons(extra_data) if extra_data else []
    logger.info(f"Debug: requested_seasons = {requested_seasons}")
    
    # If no seasons found in extra_data, try to get them from the database
    if not requested_seasons and USE_DATABASE and tmdb_id and media_type == 'tv':
        logger.info("No seasons found in extra_data, checking database for seasons_processing")
        from seerr.database import get_db
        from seerr.unified_models import UnifiedMedia
        
        db = get_db()
        try:
            media_record = db.query(UnifiedMedia).filter(
                UnifiedMedia.tmdb_id == tmdb_id,
                UnifiedMedia.media_type == 'tv'
            ).first()
            
            if media_record and media_record.seasons_processing:
                logger.info(f"Found seasons_processing in database: {media_record.seasons_processing}")
                # Parse the seasons_processing field
                seasons_processing = media_record.seasons_processing
                if seasons_processing:
                    # Convert seasons_processing to requested_seasons format
                    seasons = []
                    for part in seasons_processing.split(','):
                        part = part.strip()
                        if '-' in part:
                            # Handle range like "1-5"
                            try:
                                start, end = map(int, part.split('-'))
                                for season_num in range(start, end + 1):
                                    seasons.append(f"Season {season_num}")
                            except ValueError:
                                continue
                        else:
                            # Handle single season like "19"
                            try:
                                season_num = int(part)
                                seasons.append(f"Season {season_num}")
                            except ValueError:
                                continue
                    requested_seasons = seasons
                    logger.info(f"Extracted seasons from database: {requested_seasons}")
                    
                    # Check if we have actual season data for these seasons
                    if media_record and media_record.seasons_data:
                        existing_season_numbers = {season.get('season_number', 0) for season in media_record.seasons_data}
                        missing_seasons = []
                        invalid_seasons = []
                        
                        for season in requested_seasons:
                            if isinstance(season, str) and season.startswith('Season '):
                                try:
                                    season_num = int(season.split()[-1])
                                    if season_num not in existing_season_numbers:
                                        missing_seasons.append(season_num)
                                    else:
                                        # Check if existing season data is valid (has proper episode counts)
                                        for existing_season in media_record.seasons_data:
                                            if existing_season.get('season_number') == season_num:
                                                episode_count = existing_season.get('episode_count', 0)
                                                aired_episodes = existing_season.get('aired_episodes', 0)
                                                
                                                # Consider season data invalid if episode_count is 0 or aired_episodes is 0
                                                # This indicates the season data was created by Overseerr but never populated with Trakt data
                                                if episode_count == 0 or aired_episodes == 0:
                                                    invalid_seasons.append(season_num)
                                                    logger.warning(f"Season {season_num} has invalid data: episode_count={episode_count}, aired_episodes={aired_episodes}")
                                                break
                                except (ValueError, IndexError):
                                    continue
                        
                        # Combine missing and invalid seasons
                        seasons_to_fetch = list(set(missing_seasons + invalid_seasons))
                        
                        # If we have seasons that need fetching (missing or invalid), fetch them from Trakt
                        if seasons_to_fetch and media_record.trakt_id:
                            logger.info(f"Seasons needing data fetch: {seasons_to_fetch} (missing: {missing_seasons}, invalid: {invalid_seasons}), fetching from Trakt")
                            from seerr.trakt import get_season_details_from_trakt, check_next_episode_aired
                            from seerr.enhanced_season_manager import EnhancedSeasonManager
                            from datetime import datetime
                            
                            trakt_show_id = media_record.trakt_id
                            new_seasons_data = []
                            
                            for season_num in seasons_to_fetch:
                                # Fetch season details from Trakt
                                season_details = get_season_details_from_trakt(str(trakt_show_id), season_num)
                                
                                if season_details:
                                    episode_count = season_details.get('episode_count', 0)
                                    aired_episodes = season_details.get('aired_episodes', 0)
                                    logger.info(f"Fetched Season {season_num} details: episode_count={episode_count}, aired_episodes={aired_episodes}")
                                    
                                    # Check for next episode if there's a discrepancy
                                    if episode_count != aired_episodes:
                                        has_aired, next_episode_details = check_next_episode_aired(
                                            str(trakt_show_id), season_num, aired_episodes
                                        )
                                        if has_aired:
                                            logger.info(f"Next episode (E{aired_episodes + 1:02d}) has aired for Season {season_num}. Updating aired_episodes.")
                                            aired_episodes += 1
                                    
                                    # Create enhanced season data
                                    season_data = {
                                        'season_number': season_num,
                                        'episode_count': episode_count,
                                        'aired_episodes': aired_episodes,
                                        'confirmed_episodes': [],
                                        'failed_episodes': [],
                                        'unprocessed_episodes': [f"E{str(i).zfill(2)}" for i in range(1, aired_episodes + 1)] if aired_episodes > 0 else [],
                                        'last_checked': datetime.utcnow().isoformat(),
                                        'updated_at': datetime.utcnow().isoformat(),
                                        'status': 'pending'
                                    }
                                    
                                    new_seasons_data.append(season_data)
                                    logger.info(f"Created season data for Season {season_num}")
                                    
                                    # Check if season should be processed (has aired episodes)
                                    if aired_episodes == 0:
                                        logger.warning(f"Season {season_num} has not aired any episodes yet (episode_count={episode_count}, aired_episodes={aired_episodes}). Skipping processing.")
                                        # Mark season as not ready for processing
                                        season_data['status'] = 'not_aired'
                                        season_data['processing_skip_reason'] = 'no_episodes_aired'
                                    else:
                                        logger.info(f"Season {season_num} has {aired_episodes} aired episodes, ready for processing")
                                else:
                                    logger.warning(f"Failed to fetch Season {season_num} details from Trakt")
                            
                            # Store the new season data in database
                            if new_seasons_data:
                                # Merge with existing seasons data, replacing invalid data
                                existing_seasons_data = media_record.seasons_data or []
                                
                                # Remove invalid seasons from existing data
                                existing_seasons_data = [season for season in existing_seasons_data 
                                                       if season.get('season_number') not in invalid_seasons]
                                
                                # Add new seasons data
                                existing_seasons_data.extend(new_seasons_data)
                                existing_seasons_data.sort(key=lambda x: x.get('season_number', 0))
                                
                                # Update the database record
                                media_record.seasons_data = existing_seasons_data
                                media_record.total_seasons = len(existing_seasons_data)
                                media_record.updated_at = datetime.utcnow()
                                
                                db.commit()
                                logger.info(f"Updated {len(new_seasons_data)} seasons in database for {movie_title} (replaced invalid data)")
                                
                                # Check if any seasons are not ready for processing (haven't aired)
                                unaired_seasons = [season for season in new_seasons_data if season.get('status') == 'not_aired']
                                if unaired_seasons:
                                    unaired_numbers = [season['season_number'] for season in unaired_seasons]
                                    logger.warning(f"Seasons {unaired_numbers} have not aired any episodes yet. Skipping processing.")
                                    
                                    # Remove unaired seasons from requested_seasons to prevent processing
                                    requested_seasons = [season for season in requested_seasons 
                                                        if not any(season.endswith(f" {num}") for num in unaired_numbers)]
                                    logger.info(f"Updated requested_seasons to exclude unaired seasons: {requested_seasons}")
                                    
                                    if not requested_seasons:
                                        logger.warning(f"All requested seasons for {movie_title} have not aired yet. Skipping entire processing.")
                                        return False
                            else:
                                logger.warning(f"No season data could be fetched for seasons {seasons_to_fetch}")
                        else:
                            logger.info(f"All requested seasons have valid data in database")
                            
                            # Check if any existing seasons haven't aired yet
                            unaired_existing_seasons = []
                            for season in requested_seasons:
                                if isinstance(season, str) and season.startswith('Season '):
                                    try:
                                        season_num = int(season.split()[-1])
                                        for existing_season in media_record.seasons_data:
                                            if existing_season.get('season_number') == season_num:
                                                aired_episodes = existing_season.get('aired_episodes', 0)
                                                if aired_episodes == 0:
                                                    unaired_existing_seasons.append(season_num)
                                                    logger.warning(f"Existing Season {season_num} has not aired any episodes yet (aired_episodes={aired_episodes}). Skipping processing.")
                                                break
                                    except (ValueError, IndexError):
                                        continue
                            
                            # Remove unaired seasons from processing
                            if unaired_existing_seasons:
                                requested_seasons = [season for season in requested_seasons 
                                                    if not any(season.endswith(f" {num}") for num in unaired_existing_seasons)]
                                logger.info(f"Updated requested_seasons to exclude unaired existing seasons: {requested_seasons}")
                                
                                if not requested_seasons:
                                    logger.warning(f"All requested seasons for {movie_title} have not aired yet. Skipping entire processing.")
                                    return False
        finally:
            db.close()
    
    normalized_seasons = [normalize_season(season) for season in requested_seasons]
    logger.info(f"Debug: normalized_seasons = {normalized_seasons}")

    # Determine if the media is a TV show
    # Use the media_type parameter passed in, not extra_data logic
    is_tv_show = (media_type == 'tv')
    
    logger.info(f"Media type: {'TV Show' if is_tv_show else 'Movie'} (from media_type parameter)")

    try:
        # Check if item is still in queue before starting any expensive operations
        if tmdb_id and _check_queue_status(tmdb_id, media_type):
            logger.info(f"Item {movie_title} (TMDB: {tmdb_id}) is not in queue. Stopping before starting browser automation.")
            return "cancelled"
        
        # Starting browser automation
        # Check if IMDB ID is missing or invalid - if so, search by title (RARE FALLBACK)
        if not imdb_id or imdb_id.lower() == 'none' or (isinstance(imdb_id, str) and imdb_id.strip() == ''):
            logger.warning(f"IMDB ID is missing or invalid ({imdb_id}). Performing title search fallback (rare case).")
            
            # Check queue status again before expensive title search
            if tmdb_id and _check_queue_status(tmdb_id, media_type):
                logger.info(f"Item {movie_title} (TMDB: {tmdb_id}) is not in queue. Stopping before title search.")
                return "cancelled"
            
            # Extract year from title if present (format: "Title (Year)")
            year = None
            title_for_search = movie_title
            year_match = re.search(r'\((\d{4})\)', movie_title)
            if year_match:
                year = int(year_match.group(1))
                title_for_search = movie_title.split('(')[0].strip()
            
            # Search DMM by title to find IMDB ID
            found_imdb_id = search_dmm_by_title_and_extract_id(driver, title_for_search, media_type, year, tmdb_id)
            
            if found_imdb_id:
                logger.info(f"Found IMDB ID via title search: {found_imdb_id}. Using it instead of missing ID.")
                imdb_id = found_imdb_id
            else:
                logger.error(f"Could not find IMDB ID via title search for '{title_for_search}'. Cannot proceed.")
                if USE_DATABASE and processed_media_id:
                    from seerr.unified_media_manager import update_media_processing_status
                    update_media_processing_status(processed_media_id, 'failed', 'browser_automation', 
                                                  error_message=f'IMDB ID not found via title search for {title_for_search}')
                return False
        
        # Check queue status again before navigation to DMM page
        if tmdb_id and _check_queue_status(tmdb_id, media_type):
            logger.info(f"Item {movie_title} (TMDB: {tmdb_id}) is not in queue. Stopping before navigation to DMM page.")
            return "cancelled"
        
        # Navigate directly using IMDb ID
        if media_type == 'movie':
            url = f"https://debridmediamanager.com/movie/{imdb_id}"
            driver.get(url)
            logger.info(f"Navigated to movie page: {url}")
            
            # Check for cancellation after navigation
            if tmdb_id and _check_queue_status(tmdb_id, media_type):
                logger.info(f"Search cancelled for {movie_title} (TMDB: {tmdb_id}) after navigation")
                return "cancelled"
        elif media_type == 'tv':
            # For TV shows with specific requested seasons, navigate to each season page
            if normalized_seasons and len(normalized_seasons) > 0:
                # Extract season numbers from normalized_seasons
                season_numbers = []
                for season in normalized_seasons:
                    if isinstance(season, str) and season.startswith('Season '):
                        try:
                            season_num = int(season.split()[-1])
                            season_numbers.append(season_num)
                        except (ValueError, IndexError):
                            pass
                
                if season_numbers:
                    logger.info(f"Processing TV show with specific seasons: {season_numbers}")
                    # Process each season individually
                    all_seasons_confirmed = True
                    confirmed_seasons = set()
                    
                    for season_num in season_numbers:
                        # Check for cancellation before processing each season
                        if tmdb_id and _check_queue_status(tmdb_id, media_type):
                            logger.info(f"Search cancelled for {movie_title} (TMDB: {tmdb_id}) during season processing")
                            return "cancelled"
                        
                        logger.info(f"Starting processing for Season {season_num}")
                        
                        # Update processing stage to reflect current season being processed
                        if USE_DATABASE and 'processed_media_id' in locals() and processed_media_id:
                            from seerr.unified_media_manager import update_media_processing_status
                            update_media_processing_status(
                                processed_media_id, 
                                'processing', 
                                f'browser_automation_season_{season_num}'
                            )
                            logger.info(f"Updated processing stage to browser_automation_season_{season_num} for {movie_title}")
                        
                        # Check if this season has aired episodes before processing
                        aired_episodes = get_season_aired_episodes(movie_title, season_num)
                        
                        if aired_episodes == 0:
                            logger.info(f"Season {season_num} has not aired any episodes yet (aired_episodes=0). Skipping processing.")
                            continue
                        
                        # Check if this season is already completed before processing
                        if is_season_completed(movie_title, season_num, tmdb_id):
                            logger.info(f"Season {season_num} is already completed. Skipping processing.")
                            continue
                        
                        # Check if this season is in-progress and mark as subscribed if needed
                        if is_season_in_progress(movie_title, season_num) and USE_DATABASE:
                            from seerr.unified_media_manager import update_media_details
                            from seerr.database import get_db as get_search_db
                            from seerr.unified_models import UnifiedMedia
                            
                            db = get_search_db()
                            try:
                                media_record = db.query(UnifiedMedia).filter(
                                    UnifiedMedia.tmdb_id == tmdb_id,
                                    UnifiedMedia.media_type == 'tv'
                                ).first()
                                
                                if media_record:
                                    # Get episode count from season data
                                    episode_count = 0
                                    for season_data in media_record.seasons_data or []:
                                        if season_data.get('season_number') == season_num:
                                            episode_count = season_data.get('episode_count', 0)
                                            break
                                    
                                    if episode_count > 0:
                                        from datetime import datetime as dt
                                        update_media_details(
                                            media_record.id,
                                            is_subscribed=True,
                                            subscription_active=True,
                                            subscription_last_checked=dt.utcnow()
                                        )
                                        logger.info(f"Marked {movie_title} Season {season_num} as subscribed (in-progress: {aired_episodes}/{episode_count} episodes aired)")
                            except Exception as e:
                                logger.error(f"Error marking show as subscribed: {e}")
                            finally:
                                db.close()
                        
                        # Check queue status before navigation to season page
                        if tmdb_id and _check_queue_status(tmdb_id, media_type):
                            logger.info(f"Item {movie_title} (TMDB: {tmdb_id}) is not in queue. Stopping before season navigation.")
                            return "cancelled"
                        
                        season_url = f"https://debridmediamanager.com/show/{imdb_id}/{season_num}"
                        driver.get(season_url)
                        logger.info(f"Navigated to season {season_num} page: {season_url}")
                        
                        # Check if item is still in queue after navigation
                        if tmdb_id and _check_queue_status(tmdb_id, media_type):
                            logger.info(f"Item {movie_title} (TMDB: {tmdb_id}) is not in queue. Stopping after navigation.")
                            return "cancelled"
                        
                        # Wait for page to load
                        try:
                            WebDriverWait(driver, 3).until(
                                EC.presence_of_element_located((By.XPATH, "//div[@role='status' and contains(@aria-live, 'polite')]"))
                            )
                        except TimeoutException:
                            logger.warning(f"Timeout waiting for season {season_num} page to load. Proceeding anyway.")
                        
                        # Check if item is still in queue before processing season
                        if tmdb_id and _check_queue_status(tmdb_id, media_type):
                            logger.info(f"Item {tmdb_id} is not in queue. Stopping season processing.")
                            return "cancelled"
                        
                        # Process this season
                        logger.info(f"Calling process_season_page for Season {season_num}")
                        season_result = process_season_page(driver, movie_title, season_num, normalized_seasons, tmdb_id)
                        logger.info(f"process_season_page returned {season_result} for Season {season_num}")
                        
                        # Check again after processing season
                        if tmdb_id and _check_queue_status(tmdb_id, media_type):
                            logger.info(f"Item {tmdb_id} is not in queue. Stopping after season processing.")
                            return "cancelled"
                        
                        if season_result is True:
                            confirmed_seasons.add(f"Season {season_num}")
                            logger.info(f"Season {season_num} confirmed")
                        elif season_result == "discrepant":
                            logger.info(f"Season {season_num} is discrepant - this is a valid state, not a failure")
                            # Don't mark as failed, discrepant seasons are handled separately
                            # Don't process further - discrepant seasons should not be reprocessed
                            logger.info(f"Skipping Season {season_num} - already marked as discrepant")
                        else:
                            # Check if this season is marked as discrepant - if so, it's a valid state, not a failure
                            if is_season_discrepant(movie_title, season_num):
                                logger.info(f"Season {season_num} is discrepant - this is a valid state, not a failure")
                                # Don't mark as failed, discrepant seasons are handled separately
                                # Don't process further - discrepant seasons should not be reprocessed
                                logger.info(f"Skipping Season {season_num} - already marked as discrepant")
                            else:
                                all_seasons_confirmed = False
                                logger.warning(f"Season {season_num} not confirmed")
                    
                    # Return success if at least one season is confirmed
                    # Unaired seasons are expected to fail, so we don't require all seasons to be confirmed
                    if confirmed_seasons:
                        logger.info(f"Successfully confirmed seasons: {confirmed_seasons}")
                        return True
                    else:
                        # Check if any of the requested seasons are discrepant - if so, don't mark as failed
                        has_discrepant_seasons = False
                        for season_num in season_numbers:
                            if is_season_discrepant(movie_title, season_num):
                                has_discrepant_seasons = True
                                logger.info(f"Season {season_num} is discrepant - not marking show as failed")
                        
                        if has_discrepant_seasons:
                            logger.info(f"No seasons confirmed, but some seasons are discrepant - this is a valid state")
                            logger.info(f"Returning 'already_available' to prevent reprocessing of discrepant seasons")
                            return "already_available"  # Return special status to prevent reprocessing discrepant seasons
                        else:
                            logger.warning(f"No seasons confirmed. All seasons may be unaired or unavailable.")
                            return False
                else:
                    # Check queue status before fallback navigation
                    if tmdb_id and _check_queue_status(tmdb_id, media_type):
                        logger.info(f"Item {movie_title} (TMDB: {tmdb_id}) is not in queue. Stopping before fallback navigation.")
                        return "cancelled"
                    
                    # Fallback to general show page if no valid season numbers
                    url = f"https://debridmediamanager.com/show/{imdb_id}"
                    driver.get(url)
                    logger.info(f"Navigated to show page (fallback): {url}")
            else:
                # Check queue status before general show page navigation
                if tmdb_id and _check_queue_status(tmdb_id, media_type):
                    logger.info(f"Item {movie_title} (TMDB: {tmdb_id}) is not in queue. Stopping before general show page navigation.")
                    return "cancelled"
                
                # No specific seasons requested, use general show page
                url = f"https://debridmediamanager.com/show/{imdb_id}"
                driver.get(url)
                logger.info(f"Navigated to show page: {url}")
        else:
            logger.error(f"Unsupported media type: {media_type}")
            return False

        # Check for discrepancies if it's a TV show (only if we haven't already processed specific seasons)
        discrepant_seasons = {}
        if is_tv_show and not (normalized_seasons and len(normalized_seasons) > 0):
            # First try to get discrepancy info from database
            if USE_DATABASE and tmdb_id:
                from seerr.database import get_db
                from seerr.unified_models import UnifiedMedia
                
                db = get_db()
                try:
                    media_record = db.query(UnifiedMedia).filter(
                        UnifiedMedia.tmdb_id == tmdb_id,
                        UnifiedMedia.media_type == 'tv'
                    ).first()
                    
                    if media_record and media_record.seasons_data:
                        # Found seasons_data in database
                        # Only process discrepant seasons that are in the requested seasons list
                        requested_season_numbers = []
                        if normalized_seasons:
                            for season in normalized_seasons:
                                if isinstance(season, str) and season.startswith('Season '):
                                    try:
                                        season_num = int(season.split()[-1])
                                        requested_season_numbers.append(season_num)
                                    except (ValueError, IndexError):
                                        pass
                        
                        logger.info(f"Requested season numbers: {requested_season_numbers}")
                        
                        # Only find discrepant seasons that match the requested seasons
                        for season_data in media_record.seasons_data:
                            if season_data.get('is_discrepant', False):
                                season_number = season_data.get('season_number', 0)
                                
                                # Only include if this season is in the requested seasons
                                if not requested_season_numbers or season_number in requested_season_numbers:
                                    season_name = f"Season {season_number}"
                                    logger.info(f"Found requested discrepant season {season_name} in database: {season_data}")
                                    discrepant_seasons[season_name] = {
                                        "season_number": season_number,
                                        "season_details": season_data,
                                        "discrepancy_reason": season_data.get('discrepancy_reason', 'unknown'),
                                        "unprocessed_episodes": season_data.get('unprocessed_episodes', [])
                                    }
                                else:
                                    logger.info(f"Skipping discrepant season {season_number} - not in requested seasons {requested_season_numbers}")
                finally:
                    db.close()
            
            # Log if no discrepancy info found in database
            if not discrepant_seasons:
                logger.info("No discrepant seasons found in database for requested seasons")

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
                status_element = WebDriverWait(driver, 2).until(
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
            # Initialize a set to track confirmed seasons and processed torrents
            confirmed_seasons = set()
            processed_torrents = set()
            
            # Step 2: Check if any red buttons (RD 100%) exist and verify the title for each
            confirmation_flag, confirmed_seasons = check_red_buttons(driver, movie_title, normalized_seasons, confirmed_seasons, is_tv_show, processed_torrents=processed_torrents)

            # If a red button is confirmed and it's not a TV show, skip further processing
            if confirmation_flag and not is_tv_show:
                logger.success(f"Red button confirmed for Movie {movie_title}. Skipping further processing.")
                # Update processing status to completed
                if USE_DATABASE and 'processed_media_id' in locals() and processed_media_id:
                    update_media_processing_status(processed_media_id, 'completed', 'browser_automation', extra_data={'torrents_found': 1})
                return confirmation_flag

            # Step 3: Wait for the "Checking RD availability..." message to disappear
            try:
                WebDriverWait(driver, 5).until_not(
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
                status_element = WebDriverWait(driver, 3).until(
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
            try:
                confirmation_flag, confirmed_seasons = check_red_buttons(driver, movie_title, normalized_seasons, confirmed_seasons, is_tv_show, processed_torrents=processed_torrents)
            except StaleElementReferenceException as e:
                logger.warning(f"Stale element reference in check_red_buttons: {e}. Retrying...")
                # Wait a moment and retry
                time.sleep(2)
                try:
                    confirmation_flag, confirmed_seasons = check_red_buttons(driver, movie_title, normalized_seasons, confirmed_seasons, is_tv_show, processed_torrents=processed_torrents)
                except Exception as retry_e:
                    logger.error(f"Failed to retry check_red_buttons: {retry_e}")
                    confirmation_flag = False
                    confirmed_seasons = set()

            # If a red button is confirmed, skip further processing
            if confirmation_flag:
                logger.info("Red button confirmed. Checking if Movie or TV Show...")
            # If a red button is confirmed and it's not a TV show, skip further processing
            if confirmation_flag and not is_tv_show:
                logger.success(f"Red button confirmed for Movie {movie_title}. Skipping further processing.")
                # Update processing status to completed
                if USE_DATABASE and 'processed_media_id' in locals() and processed_media_id:
                    update_media_processing_status(processed_media_id, 'completed', 'browser_automation', extra_data={'torrents_found': 1})
                return confirmation_flag

            # After clicking the matched movie title, we now check the popup boxes for Instant RD buttons
            # Step 8: Check the result boxes with the specified class for "Instant RD"
            try:
                if is_tv_show:
                    logger.info(f"Processing TV show seasons for: {movie_title}")

                    # Phase 1: Process discrepant seasons first (priority)
                    if discrepant_seasons:
                        logger.info(f"Processing discrepant seasons: {list(discrepant_seasons.keys())}")
                        # Process discrepant seasons using individual episode search
                        for season_name, season_info in discrepant_seasons.items():
                            season_number = season_info["season_number"]
                            season_details = season_info["season_details"]
                            
                            logger.info(f"Discrepancy detected for {movie_title} {season_name}. Switching to individual episode search.")
                            
                            # Since we're in a synchronous function, and search_individual_episodes is async,
                            # we need to synchronously run the coroutine
                            import asyncio
                            try:
                                # Create and run a synchronous version of search_individual_episodes
                                from seerr.background_tasks import search_individual_episodes_sync
                                confirmation_flag = search_individual_episodes_sync(
                                    imdb_id, movie_title, season_number, season_details, driver, tmdb_id
                                )
                            except StaleElementReferenceException as e:
                                logger.warning(f"Stale element reference in search_individual_episodes for {season_name}: {e}. Retrying...")
                                time.sleep(2)
                                try:
                                    confirmation_flag = search_individual_episodes_sync(
                                        imdb_id, movie_title, season_number, season_details, driver, tmdb_id
                                    )
                                except Exception as retry_e:
                                    logger.error(f"Failed to retry search_individual_episodes: {retry_e}")
                                    confirmation_flag = False
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
                                        imdb_id, movie_title, season_number, season_details, driver, tmdb_id
                                    )
                                )
                            
                            if confirmation_flag:
                                logger.success(f"Successfully processed individual episodes for {movie_title} {season_name}")
                            else:
                                logger.warning(f"Failed to process individual episodes for {movie_title} {season_name}")

                    # If we processed discrepant seasons, we're done - individual episode search handles everything
                    if discrepant_seasons:
                        logger.info(f"Completed processing discrepant seasons for {movie_title}. Individual episode search handled all processing.")
                        return confirmation_flag

                    # Phase 2: Process non-discrepant seasons with original logic (if any)
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
                            
                            # Log which season we're processing
                            logger.info(f"Starting processing for {movie_title} - {season}")

                            # Get the base URL (root URL without the season number)
                            base_url = driver.current_url.split("/")[:-1]  # Split the URL and remove the last part (season number)
                            base_url = "/".join(base_url)  # Reconstruct the base URL

                            # Construct the new URL by appending the season number
                            season_url = f"{base_url}/{season_number}"

                            # Navigate to the new URL
                            driver.get(season_url)
                            time.sleep(2)  # Wait longer for the page to load and stabilize
                            logger.info(f"Navigated to season {season} URL: {season_url}")
                            
                            # Wait for page to be fully loaded
                            try:
                                WebDriverWait(driver, 10).until(
                                    lambda d: d.execute_script("return document.readyState") == "complete"
                                )
                            except TimeoutException:
                                logger.warning(f"Page load timeout for season {season}, continuing anyway...")

                            # Wait a bit more for dynamic content to load
                            time.sleep(2)

                            # Perform red button checks for the current season with error handling
                            try:
                                confirmation_flag, confirmed_seasons = check_red_buttons(driver, movie_title, normalized_seasons, confirmed_seasons, is_tv_show, processed_torrents=processed_torrents)
                            except StaleElementReferenceException as e:
                                logger.warning(f"Stale element reference in check_red_buttons for season {season}: {e}. Continuing with season processing.")
                                confirmation_flag = False
                            except Exception as e:
                                logger.error(f"Error in check_red_buttons for season {season}: {e}. Continuing with season processing.")
                                confirmation_flag = False
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
                                result_boxes = WebDriverWait(driver, 5).until(
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
                                
                            # First pass: Try to find complete season torrents (avoid singles)
                            complete_season_found = False
                            single_episode_boxes = []  # Track single episode boxes for fallback
                            max_boxes_to_check = 250  # Limit to prevent excessive processing
                            
                            for i, result_box in enumerate(result_boxes, start=1):
                                # Limit the number of boxes we check to prevent excessive processing
                                if i > max_boxes_to_check:
                                    logger.warning(f"Reached limit of {max_boxes_to_check} torrent boxes. Stopping search and triggering fallback.")
                                    break
                                try:
                                    # Extract the title from the result box with stale element handling
                                    try:
                                        title_element = result_box.find_element(By.XPATH, ".//h2")
                                        title_text = title_element.text.strip()
                                    except StaleElementReferenceException:
                                        logger.warning(f"Stale element reference for box {i} title. Re-locating result boxes...")
                                        # Re-locate result boxes and try again
                                        try:
                                            result_boxes = WebDriverWait(driver, 3).until(
                                                EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'border-black')]"))
                                            )
                                            if i <= len(result_boxes):
                                                result_box = result_boxes[i-1]
                                                title_element = result_box.find_element(By.XPATH, ".//h2")
                                                title_text = title_element.text.strip()
                                            else:
                                                logger.warning(f"Could not re-locate box {i}. Skipping.")
                                                continue
                                        except Exception as e:
                                            logger.error(f"Failed to re-locate result boxes: {e}. Skipping box {i}.")
                                            continue
                                    
                                    logger.info(f"Box {i} title: {title_text}")
                                    
                                    # Check if the result box contains "Single" and track it for fallback
                                    is_single_episode = False
                                    try:
                                        extras_element = WebDriverWait(result_box, 2).until(
                                            EC.presence_of_element_located((By.XPATH, ".//span[contains(., 'Single')]"))
                                        )
                                        logger.info(f"Box {i} contains 'Single'. Tracking for fallback.")
                                        is_single_episode = True
                                        single_episode_boxes.append((i, result_box, title_text))
                                        continue  # Skip singles in first pass
                                    except TimeoutException:
                                        logger.info(f"Box {i} does not contain 'Single'. Proceeding with complete season check.")
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
                                    logger.info(f"Original box title: {title_text}")
                                    logger.info(f"Cleaned TV show title: {tv_show_title_cleaned}, Cleaned box title: {title_text_cleaned}")
                                    logger.info(f"TV show title (digits to words): {tv_show_title_cleaned_word}, Box title (digits to words): {title_text_cleaned_word}")
                                    logger.info(f"TV show title (words to digits): {tv_show_title_cleaned_digit}, Box title (words to digits): {title_text_cleaned_digit}")
                                    
                                    # Log fuzzy matching scores for debugging
                                    fuzz_score_1 = fuzz.partial_ratio(title_text_cleaned.lower(), tv_show_title_cleaned.lower())
                                    fuzz_score_2 = fuzz.partial_ratio(title_text_cleaned_word.lower(), tv_show_title_cleaned_word.lower())
                                    fuzz_score_3 = fuzz.partial_ratio(title_text_cleaned_digit.lower(), tv_show_title_cleaned_digit.lower())
                                    logger.info(f"Fuzzy matching scores: {fuzz_score_1}%, {fuzz_score_2}%, {fuzz_score_3}%")

                                    # Compare the title in all variations with improved matching
                                    title_matches = False
                                    
                                    # Check if the cleaned title contains the show title (more permissive)
                                    if tv_show_title_cleaned in title_text_cleaned or title_text_cleaned in tv_show_title_cleaned:
                                        title_matches = True
                                        logger.info(f"Direct title match found: '{tv_show_title_cleaned}' in '{title_text_cleaned}'")
                                    
                                    # Check fuzzy matching with lower threshold for better matching
                                    elif (
                                        fuzz.partial_ratio(title_text_cleaned.lower(), tv_show_title_cleaned.lower()) >= 60 or
                                        fuzz.partial_ratio(title_text_cleaned_word.lower(), tv_show_title_cleaned_word.lower()) >= 60 or
                                        fuzz.partial_ratio(title_text_cleaned_digit.lower(), tv_show_title_cleaned_digit.lower()) >= 60
                                    ):
                                        title_matches = True
                                        logger.info(f"Fuzzy title match found with 60% threshold")
                                    
                                    # Check if the original title contains the show name (before cleaning)
                                    elif tv_show_title_cleaned.replace('.', ' ').strip() in title_text.lower():
                                        title_matches = True
                                        logger.info(f"Original title contains show name: '{tv_show_title_cleaned}' in '{title_text}'")
                                    
                                    if not title_matches:
                                        logger.warning(f"Title mismatch for box {i}: {title_text_cleaned} (Expected: {tv_show_title_cleaned}). Skipping.")
                                        continue  # Skip this box if none of the variations match

                                    # Check for complete season packs first
                                    if match_complete_seasons(title_text, [season]):
                                        logger.info(f"Found complete season pack for {season} in box {i}: {title_text}")
                                        if prioritize_buttons_in_box(result_box):
                                            logger.info(f"Successfully handled complete season pack in box {i}.")
                                            confirmation_flag = True
                                            complete_season_found = True

                                            # Add the confirmed season to the set
                                            confirmed_seasons.add(season)
                                            logger.info(f"Added {season} to confirmed seasons: {confirmed_seasons}")

                                            # Perform RD status checks after clicking the button
                                            try:
                                                rd_button = WebDriverWait(driver, 5).until(
                                                    EC.presence_of_element_located((By.XPATH, ".//button[contains(text(), 'RD (')]"))
                                                )
                                                rd_button_text = rd_button.text
                                                logger.info(f"RD button text after clicking: {rd_button_text}")

                                                # If the button is now "RD (0%)", undo the click and retry with the next box
                                                if "RD (0%)" in rd_button_text:
                                                    logger.warning(f"RD (0%) button detected after clicking Instant RD in box {i} {title_text}. Undoing the click and moving to the next box.")
                                                    rd_button.click()  # Undo the click by clicking the RD (0%) button
                                                    confirmation_flag = False  # Reset the flag
                                                    complete_season_found = False
                                                    continue  # Move to the next box

                                                # If it's "RD (100%)", we are done with this entry
                                                if "RD (100%)" in rd_button_text:
                                                    logger.info(f"RD (100%) button detected. {i} {title_text}. This entry is complete.")
                                                    break  # Move to the next season

                                            except TimeoutException:
                                                logger.warning(f"Timeout waiting for RD button status change in box {i}.")
                                                continue  # Move to the next box if a timeout occurs

                                    # If no complete pack, check for individual seasons
                                    logger.info(f"Checking if '{title_text}' matches season {season}")
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
                                                rd_button = WebDriverWait(driver, 5).until(
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
                                                    logger.info(f"RD (100%) button detected. {i} {title_text}. This entry is complete.")
                                                    break  # Move to the next season

                                            except TimeoutException:
                                                logger.warning(f"Timeout waiting for RD button status change in box {i}.")
                                                continue  # Move to the next box if a timeout occurs

                                except NoSuchElementException as e:
                                    logger.warning(f"Could not find 'Instant RD' button in box {i}: {e}")
                                except TimeoutException as e:
                                    logger.warning(f"Timeout when processing box {i}: {e}")

                            # Fallback mechanism: If no complete season found and single episodes are available, or if we hit the limit
                            should_trigger_fallback = (
                                not complete_season_found and single_episode_boxes
                            ) or (
                                len(result_boxes) > max_boxes_to_check and not complete_season_found
                            )
                            
                            if should_trigger_fallback:
                                if len(result_boxes) > max_boxes_to_check:
                                    logger.warning(f"Reached limit of {max_boxes_to_check} torrent boxes for {season}. Triggering fallback.")
                                else:
                                    logger.warning(f"No complete season torrents found for {season}. Found {len(single_episode_boxes)} single episode torrents.")
                                logger.info(f"Implementing fallback: Processing all episodes for {season} using individual episode search.")
                                
                                # Mark this season as discrepant to trigger individual episode processing
                                # This will cause the system to process all episodes individually
                                season_number = int(season.split()[-1])  # Extract season number
                                
                                # Get proper season details from database (should already be there)
                                season_details = None
                                if USE_DATABASE and tmdb_id:
                                    try:
                                        from seerr.database import get_db
                                        from seerr.unified_models import UnifiedMedia
                                        
                                        db = get_db()
                                        try:
                                            media_record = db.query(UnifiedMedia).filter(
                                                UnifiedMedia.tmdb_id == tmdb_id,
                                                UnifiedMedia.media_type == 'tv'
                                            ).first()
                                            
                                            if media_record and media_record.seasons_data:
                                                # Find the specific season in the database
                                                for season_data in media_record.seasons_data:
                                                    if season_data.get('season_number') == season_number:
                                                        aired_episodes = season_data.get('aired_episodes', 0)
                                                        episode_count = season_data.get('episode_count', 0)
                                                        logger.info(f"Found season {season_number} in database: aired_episodes={aired_episodes}, episode_count={episode_count}")
                                                        
                                                        season_details = {
                                                            'season_number': season_number,
                                                            'aired_episodes': aired_episodes,
                                                            'episode_count': episode_count,
                                                            'failed_episodes': season_data.get('failed_episodes', []),
                                                            'confirmed_episodes': season_data.get('confirmed_episodes', []),
                                                            'unprocessed_episodes': season_data.get('unprocessed_episodes', [f"E{str(i).zfill(2)}" for i in range(1, aired_episodes + 1)] if aired_episodes > 0 else []),
                                                            'is_discrepant': True,
                                                            'discrepancy_reason': 'fallback_due_to_single_episodes_only'
                                                        }
                                                        
                                                        # Update the database to mark this season as discrepant
                                                        try:
                                                            from seerr.enhanced_season_manager import EnhancedSeasonManager
                                                            EnhancedSeasonManager.update_tv_show_seasons(tmdb_id, [season_details], movie_title)
                                                            logger.info(f"Marked season {season_number} as discrepant in database for fallback processing")
                                                            
                                                            # Ensure the database transaction is committed before proceeding
                                                            from seerr.database import get_db
                                                            db_commit = get_db()
                                                            try:
                                                                db_commit.commit()
                                                                logger.info(f"Database transaction committed for season {season_number}")
                                                            finally:
                                                                db_commit.close()
                                                        except Exception as e:
                                                            logger.error(f"Failed to update database with discrepant season: {e}")
                                                        break
                                                
                                                if not season_details:
                                                    logger.warning(f"Season {season_number} not found in database seasons_data for {movie_title}")
                                            else:
                                                logger.warning(f"No seasons_data found in database for {movie_title} (TMDB ID: {tmdb_id})")
                                        finally:
                                            db.close()
                                    except Exception as e:
                                        logger.error(f"Error getting season details from database: {e}")
                                
                                # Fallback to default if we couldn't get proper details from database
                                if not season_details:
                                    logger.warning(f"Using default season details for {movie_title} Season {season_number} (database data not available)")
                                    season_details = {
                                        'season_number': season_number,
                                        'aired_episodes': 0,  # Will be updated by individual episode search
                                        'failed_episodes': [],
                                        'confirmed_episodes': [],
                                        'unprocessed_episodes': [],
                                        'is_discrepant': True,
                                        'discrepancy_reason': 'fallback_due_to_single_episodes_only'
                                    }
                                    
                                    # Try to update the database with this fallback season
                                    if tmdb_id:
                                        try:
                                            from seerr.enhanced_season_manager import EnhancedSeasonManager
                                            EnhancedSeasonManager.update_tv_show_seasons(tmdb_id, [season_details], movie_title)
                                            logger.info(f"Created fallback season {season_number} entry in database")
                                            
                                            # Ensure the database transaction is committed before proceeding
                                            from seerr.database import get_db
                                            db_commit = get_db()
                                            try:
                                                db_commit.commit()
                                                logger.info(f"Database transaction committed for fallback season {season_number}")
                                            finally:
                                                db_commit.close()
                                        except Exception as e:
                                            logger.error(f"Failed to create fallback season in database: {e}")
                                
                                logger.info(f"Triggering individual episode search for {movie_title} Season {season_number} due to single episodes only.")
                                
                                # Use the synchronous version of search_individual_episodes
                                try:
                                    from seerr.background_tasks import search_individual_episodes_sync
                                    episode_confirmation_flag = search_individual_episodes_sync(
                                        imdb_id, movie_title, season_number, season_details, driver, tmdb_id
                                    )
                                    if episode_confirmation_flag:
                                        logger.success(f"Successfully processed individual episodes for {movie_title} Season {season_number}")
                                        confirmation_flag = True
                                        confirmed_seasons.add(season)
                                    else:
                                        logger.warning(f"Failed to process individual episodes for {movie_title} Season {season_number}")
                                except ImportError:
                                    # Fallback if the sync version doesn't exist
                                    logger.warning("Using fallback method for search_individual_episodes")
                                    
                                    def run_async_in_sync(coro):
                                        """Run an async function synchronously by creating a new event loop."""
                                        loop = asyncio.new_event_loop()
                                        asyncio.set_event_loop(loop)
                                        try:
                                            return loop.run_until_complete(coro)
                                        finally:
                                            loop.close()
                                    
                                    episode_confirmation_flag = run_async_in_sync(
                                        search_individual_episodes(
                                            imdb_id, movie_title, season_number, season_details, driver, tmdb_id
                                        )
                                    )
                                    if episode_confirmation_flag:
                                        logger.success(f"Successfully processed individual episodes for {movie_title} Season {season_number}")
                                        confirmation_flag = True
                                        confirmed_seasons.add(season)
                                    else:
                                        logger.warning(f"Failed to process individual episodes for {movie_title} Season {season_number}")
                                except Exception as e:
                                    logger.error(f"Error in fallback individual episode search: {e}")
                            elif not complete_season_found and not single_episode_boxes:
                                logger.warning(f"No complete season torrents or single episode torrents found for {season}.")

                            # Log completion of the current season
                            logger.success(f"Completed processing for {season}.")

                    # Log completion of all processed seasons
                    all_processed_seasons = list(discrepant_seasons.keys()) + non_discrepant_seasons
                    logger.success(f"Completed processing for all seasons: {all_processed_seasons}.")

                else:
                    # Handle movies or TV shows without specific seasons
                    # Re-locate the result boxes after navigating to the new URL
                    try:
                        result_boxes = WebDriverWait(driver, 5).until(
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
                        # Check for cancellation before processing each box
                        if tmdb_id and _check_queue_status(tmdb_id, media_type):
                            logger.info(f"Search cancelled for {movie_title} (TMDB: {tmdb_id}) during box processing")
                            return "cancelled"
                        
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

                            # Compare the title in all variations with stricter threshold (90%)
                            # Calculate all fuzzy match scores to find the highest one
                            fuzzy_scores = [
                                fuzz.partial_ratio(title_text_cleaned.lower(), movie_title_cleaned.lower()),
                                fuzz.partial_ratio(title_text_normalized.lower(), movie_title_normalized.lower()),
                                fuzz.partial_ratio(title_text_cleaned_word.lower(), movie_title_cleaned_word.lower()),
                                fuzz.partial_ratio(title_text_normalized_word.lower(), movie_title_normalized_word.lower()),
                                fuzz.partial_ratio(title_text_cleaned_digit.lower(), movie_title_cleaned_digit.lower()),
                                fuzz.partial_ratio(title_text_normalized_digit.lower(), movie_title_normalized_digit.lower())
                            ]
                            max_fuzzy_score = max(fuzzy_scores) if fuzzy_scores else 0
                            fuzzy_match = max_fuzzy_score >= 90
                            
                            # Additionally validate that movie title appears as a complete word/phrase
                            complete_word_match = (
                                is_complete_word_match(movie_title_cleaned, title_text_cleaned) or
                                is_complete_word_match(movie_title_normalized, title_text_normalized) or
                                is_complete_word_match(movie_title_cleaned_word, title_text_cleaned_word) or
                                is_complete_word_match(movie_title_normalized_word, title_text_normalized_word) or
                                is_complete_word_match(movie_title_cleaned_digit, title_text_cleaned_digit) or
                                is_complete_word_match(movie_title_normalized_digit, title_text_normalized_digit)
                            )
                            
                            # If fuzzy match is very high (>=95), be more lenient with complete_word_match
                            # This handles cases where minor formatting differences (underscores, em dashes) 
                            # cause complete_word_match to fail even though titles are very similar
                            if max_fuzzy_score >= 95:
                                # With very high fuzzy match, allow if either complete_word_match OR fuzzy is >= 95
                                # This is more lenient for high-confidence matches
                                title_matches = fuzzy_match and (complete_word_match or max_fuzzy_score >= 95)
                            else:
                                # For lower fuzzy scores, require both conditions
                                title_matches = fuzzy_match and complete_word_match
                            
                            if not title_matches:
                                logger.warning(f"Title mismatch for box {i}: {title_text_cleaned} or {title_text_normalized} (Expected: {movie_title_cleaned} or {movie_title_normalized}). Fuzzy match: {fuzzy_match} (max score: {max_fuzzy_score}), Complete word match: {complete_word_match}. Skipping.")
                                continue  # Skip this box if none of the variations match

                            # Compare the year with the expected year (allow ±1 year) only if it's not a TV show
                            if not is_tv_show:
                                expected_year = extract_year(movie_title)
                                box_year = extract_year(title_text)
                                
                                # Log year extraction results for debugging
                                if expected_year is None:
                                    logger.debug(f"Year extraction from movie title '{movie_title}' returned None. This may indicate the year format is not recognized.")
                                if box_year is None:
                                    logger.debug(f"Year extraction from box title '{title_text}' returned None.")

                                # Only perform year comparison if both years are present
                                if expected_year is not None and box_year is not None:
                                    if abs(box_year - expected_year) > 1:
                                        logger.warning(f"Year mismatch for box {i}: {box_year} (Expected: {expected_year}). Skipping.")
                                        continue  # Skip this box if the year doesn't match
                                    else:
                                        logger.info(f"Year match for box {i}: {box_year} matches expected {expected_year}")
                                elif expected_year is None and box_year is not None:
                                    logger.info(f"No year in movie title '{movie_title}', accepting box {i} with year {box_year}")
                                elif expected_year is not None and box_year is None:
                                    logger.warning(f"Expected year {expected_year} but no year found in box {i} title '{title_text}'. Skipping.")
                                    continue
                                else:
                                    logger.info(f"No year information available for box {i}, proceeding with title match only")

                            # Check for cancellation before processing buttons
                            if tmdb_id and _check_queue_status(tmdb_id, media_type):
                                logger.info(f"Search cancelled for {movie_title} (TMDB: {tmdb_id}) before clicking buttons in box {i}")
                                return "cancelled"

                            # After navigating to the movie details page and verifying the title/year
                            try:
                                if prioritize_buttons_in_box(result_box):
                                    logger.info(f"Successfully handled buttons in box {i}.")
                                    confirmation_flag = True

                                    # Perform RD status checks after clicking the button
                                    rd_status_confirmed = False
                                    max_retries = 3
                                    
                                    for retry in range(max_retries):
                                        # Check for cancellation during retry loop
                                        if tmdb_id and _check_queue_status(tmdb_id, media_type):
                                            logger.info(f"Search cancelled for {movie_title} (TMDB: {tmdb_id}) during RD status check")
                                            return "cancelled"
                                        try:
                                            # Wait longer for the RD button status to change (15 seconds)
                                            rd_button = WebDriverWait(driver, 15).until(
                                                EC.presence_of_element_located((By.XPATH, ".//button[contains(text(), 'RD (')]"))
                                            )
                                            rd_button_text = rd_button.text
                                            logger.info(f"RD button text after clicking (attempt {retry + 1}): {rd_button_text}")

                                            # If the button is now "RD (0%)", undo the click and retry with the next box
                                            if "RD (0%)" in rd_button_text:
                                                logger.warning(f"RD (0%) button detected after clicking Instant RD in box {i} {title_text}. Undoing the click and moving to the next box.")
                                                rd_button.click()  # Undo the click by clicking the RD (0%) button
                                                confirmation_flag = False  # Reset the flag
                                                rd_status_confirmed = True
                                                break  # Exit retry loop

                                            # If it's "RD (100%)", we are done with this entry
                                            if "RD (100%)" in rd_button_text:
                                                logger.info(f"RD (100%) button detected. {i} {title_text}. This entry is complete.")
                                                return confirmation_flag  # Exit the function as we've found a matching red button

                                            # If it's still "Instant RD" or similar, wait a bit more and retry
                                            if "Instant" in rd_button_text or "RD (" not in rd_button_text:
                                                logger.info(f"Button still shows '{rd_button_text}', waiting for status change...")
                                                if retry < max_retries - 1:
                                                    time.sleep(3)  # Wait 3 seconds before retry
                                                    continue
                                                else:
                                                    logger.warning(f"Button status did not change after {max_retries} attempts in box {i}. Moving to next box.")
                                                    rd_status_confirmed = True
                                                    break
                                            
                                            # If we get here, the status is confirmed
                                            rd_status_confirmed = True
                                            break

                                        except TimeoutException:
                                            if retry < max_retries - 1:
                                                logger.warning(f"Timeout waiting for RD button status change in box {i} (attempt {retry + 1}). Retrying...")
                                                time.sleep(2)  # Wait 2 seconds before retry
                                                continue
                                            else:
                                                logger.warning(f"Timeout waiting for RD button status change in box {i} after {max_retries} attempts. Moving to next box.")
                                                rd_status_confirmed = True
                                                break
                                        except StaleElementReferenceException:
                                            if retry < max_retries - 1:
                                                logger.warning(f"Stale element reference for RD button in box {i} (attempt {retry + 1}). Retrying...")
                                                time.sleep(1)  # Wait 1 second before retry
                                                continue
                                            else:
                                                logger.warning(f"Stale element reference for RD button in box {i} after {max_retries} attempts. Moving to next box.")
                                                rd_status_confirmed = True
                                                break
                                    
                                    # Only continue to next box if we've confirmed the status
                                    if rd_status_confirmed:
                                        continue
                            except StaleElementReferenceException:
                                logger.warning(f"Stale element reference in prioritize_buttons_in_box for box {i}. Continuing to next box.")
                                continue

                            else:
                                logger.warning(f"Failed to handle buttons in box {i}. Skipping.")

                        except NoSuchElementException as e:
                            logger.warning(f"Could not find 'Instant RD' button in box {i}: {e}")
                        except TimeoutException as e:
                            logger.warning(f"Timeout when processing box {i}: {e}")
                        except StaleElementReferenceException as e:
                            logger.warning(f"Stale element reference when processing box {i}: {e}. Continuing to next box.")
                            continue
                        except Exception as e:
                            logger.error(f"Unexpected error when processing box {i}: {e}. Continuing to next box.")
                            continue

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
        logger.critical(f"Error type: {type(ex).__name__}")
        logger.critical(f"Error details: {str(ex)}")
        import traceback
        logger.critical(f"Traceback: {traceback.format_exc()}")
        # Update processing status to failed
        if USE_DATABASE and 'processed_media_id' in locals() and processed_media_id:
            update_media_processing_status(processed_media_id, 'failed', 'browser_automation', error_message=str(ex))
        return False

def track_search_result(imdb_id: str, movie_title: str, media_type: str, 
                       search_successful: bool, torrents_found: int = 0,
                       error_message: str = None, extra_data: dict = None) -> bool:
    """
    Track search results in the database
    
    Args:
        imdb_id (str): IMDb ID of the media
        movie_title (str): Title of the media
        media_type (str): Type of media (movie/tv)
        search_successful (bool): Whether the search was successful
        torrents_found (int): Number of torrents found
        error_message (str): Error message if search failed
        extra_data (dict): Additional search data
        
    Returns:
        bool: True if successfully tracked, False otherwise
    """
    if not USE_DATABASE:
        return False
    
    try:
        db = get_db()
        
        # Create search result record
        search_data = {
            'imdb_id': imdb_id,
            'title': movie_title,
            'media_type': media_type,
            'search_successful': search_successful,
            'torrents_found': torrents_found,
            'error_message': error_message,
            'search_timestamp': datetime.now(),
            'extra_data': extra_data or {}
        }
        
        # Log the search result
        if search_successful:
            log_success("Search Result", f"Search successful for {movie_title} ({media_type}): {torrents_found} torrents found")
        else:
            log_error("Search Result", f"Search failed for {movie_title} ({media_type}): {error_message}")
        
        return True
        
    except Exception as e:
        log_error("Database Error", f"Failed to track search result for {movie_title}: {e}")
        return False
    finally:
        if 'db' in locals():
            db.close()

def get_search_history(imdb_id: str = None, media_type: str = None, 
                      limit: int = 100) -> list:
    """
    Get search history from the database
    
    Args:
        imdb_id (str): Filter by IMDb ID
        media_type (str): Filter by media type
        limit (int): Maximum number of results
        
    Returns:
        list: List of search history records
    """
    if not USE_DATABASE:
        return []
    
    try:
        db = get_db()
        
        # This would require a SearchHistory model in the database
        # For now, we'll return search results from log entries
        query = db.query(LogEntry).filter(
            LogEntry.module == 'Search Result'
        )
        
        if imdb_id:
            query = query.filter(LogEntry.message.contains(imdb_id))
        if media_type:
            query = query.filter(LogEntry.message.contains(media_type))
        
        return query.order_by(LogEntry.timestamp.desc()).limit(limit).all()
        
    except Exception as e:
        log_error("Database Error", f"Failed to get search history: {e}")
        return []
    finally:
        if 'db' in locals():
            db.close()

def update_search_statistics() -> dict:
    """
    Update and return search statistics
    
    Returns:
        dict: Search statistics
    """
    if not USE_DATABASE:
        return {}
    
    try:
        db = get_db()
        
        # Get search statistics from log entries
        total_searches = db.query(LogEntry).filter(
            LogEntry.module == 'Search Result'
        ).count()
        
        successful_searches = db.query(LogEntry).filter(
            LogEntry.module == 'Search Result',
            LogEntry.level == 'SUCCESS'
        ).count()
        
        failed_searches = db.query(LogEntry).filter(
            LogEntry.module == 'Search Result',
            LogEntry.level == 'ERROR'
        ).count()
        
        # Get recent search activity (last 24 hours)
        from datetime import datetime, timedelta
        yesterday = datetime.now() - timedelta(days=1)
        
        recent_searches = db.query(LogEntry).filter(
            LogEntry.module == 'Search Result',
            LogEntry.timestamp >= yesterday
        ).count()
        
        stats = {
            'total_searches': total_searches,
            'successful_searches': successful_searches,
            'failed_searches': failed_searches,
            'success_rate': (successful_searches / total_searches * 100) if total_searches > 0 else 0,
            'recent_searches_24h': recent_searches
        }
        
        log_info("Search Statistics", f"Updated search statistics: {stats}")
        return stats
        
    except Exception as e:
        log_error("Database Error", f"Failed to update search statistics: {e}")
        return {}
    finally:
        if 'db' in locals():
            db.close() 