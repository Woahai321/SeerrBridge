"""
SeerrBridge - A bridge between Overseerr and Real-Debrid via Debrid Media Manager
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from contextlib import asynccontextmanager
import asyncio
import os
import json
import time

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from loguru import logger
import uvicorn

from seerr import __version__
from seerr.config import load_config, REFRESH_INTERVAL_MINUTES
from seerr.models import WebhookPayload
from seerr.realdebrid import check_and_refresh_access_token
from seerr.trakt import get_media_details_from_trakt, get_season_details_from_trakt, check_next_episode_aired
from seerr.utils import parse_requested_seasons, START_TIME

# Import modules first
import seerr.browser
import seerr.background_tasks
import seerr.search

# Now import specific functions
from seerr.browser import initialize_browser, shutdown_browser, refresh_library_stats
from seerr.background_tasks import (
    initialize_background_tasks, 
    populate_queues_from_overseerr, 
    add_movie_to_queue, 
    add_tv_to_queue,
    get_queue_status,
    get_detailed_queue_status,
    check_show_subscriptions, 
    scheduler,
    is_safe_to_refresh_library_stats,
    last_queue_activity_time
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Setup and teardown operations for the FastAPI application
    """
    # Import config variables fresh to ensure we have current values
    from seerr.config import ENABLE_AUTOMATIC_BACKGROUND_TASK, ENABLE_SHOW_SUBSCRIPTION_TASK
    
    # Startup operations
    logger.info(f"Starting SeerrBridge v{__version__}")
    
    # Initialize configuration
    if not load_config():
        logger.error("Failed to load configuration. Exiting.")
        os._exit(1)
    
    # Check RD token on startup
    check_and_refresh_access_token()
    
    # Initialize browser
    await initialize_browser()
    logger.info(f"Browser initialized: {seerr.browser.driver is not None}")
    
    # Initialize background tasks (this starts the queue processor and scheduler)
    await initialize_background_tasks()
    logger.info("Background tasks initialized")
    
    # Schedule automatic background tasks if enabled
    if ENABLE_AUTOMATIC_BACKGROUND_TASK:
        logger.info("Automatic background task enabled. Starting initial check.")
        # Run initial check after a short delay to ensure browser is ready
        asyncio.create_task(delayed_populate_queues())
    
    # Schedule library stats refresh every 30 minutes
    logger.info("Scheduling library stats refresh.")
    
    async def delayed_refresh_library_stats():
        """Run refresh_library_stats after a delay to avoid browser conflicts"""
        await asyncio.sleep(300)  # Wait 300 seconds before first refresh
        refresh_library_stats()
    
    # Initial refresh
    asyncio.create_task(delayed_refresh_library_stats())
    
    # Note: Library stats refresh will now be triggered automatically 
    # 30 seconds after queue processing completes, instead of on a schedule
    logger.info("Library stats refresh will be triggered after queue completion.")
    
    yield
    
    # Shutdown operations
    logger.info("Shutting down SeerrBridge")
    
    # Stop the scheduler
    scheduler.shutdown()
    
    # Shutdown browser
    await shutdown_browser()

# Add helper functions for delayed task execution
async def delayed_populate_queues():
    """Run populate_queues_from_overseerr after a short delay"""
    await asyncio.sleep(2)  # Wait 2 seconds before starting
    await populate_queues_from_overseerr()

app = FastAPI(lifespan=lifespan)

@app.get("/status")
async def get_status():
    """
    Get the status of the SeerrBridge service
    """
    from datetime import datetime
    # Import config variables fresh each time to get updated values after reload
    from seerr.config import ENABLE_AUTOMATIC_BACKGROUND_TASK, ENABLE_SHOW_SUBSCRIPTION_TASK, REFRESH_INTERVAL_MINUTES
    from seerr.background_tasks import is_safe_to_refresh_library_stats, last_queue_activity_time
    
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
    
    # Check browser status
    browser_status = "initialized" if seerr.browser.driver is not None else "not initialized"
    
    # Get library stats from browser module
    library_stats = getattr(seerr.browser, 'library_stats', {
        "torrents_count": 0,
        "total_size_tb": 0.0,
        "last_updated": None
    })
    
    # Get queue status
    queue_status = get_queue_status()
    
    # Calculate time since last queue activity
    time_since_last_activity = time.time() - last_queue_activity_time
    
    # Check library refresh status for current cycle
    from seerr.background_tasks import library_refreshed_for_current_cycle
    
    return {
        "status": "running",
        "version": __version__,
        "uptime_seconds": uptime_seconds,
        "uptime": uptime_str,
        "start_time": START_TIME.isoformat(),
        "current_time": datetime.now().isoformat(),
        "queue_status": queue_status,
        "browser_status": browser_status,
        "automatic_processing": ENABLE_AUTOMATIC_BACKGROUND_TASK,
        "show_subscription": ENABLE_SHOW_SUBSCRIPTION_TASK,
        "refresh_interval_minutes": REFRESH_INTERVAL_MINUTES,
        "library_stats": library_stats,
        "queue_activity": {
            "time_since_last_activity_seconds": round(time_since_last_activity, 1),
            "safe_to_refresh_library": is_safe_to_refresh_library_stats(),
            "library_refreshed_for_current_cycle": library_refreshed_for_current_cycle
        }
    }

@app.post("/jellyseer-webhook/")
async def jellyseer_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Process webhook from Jellyseerr/Overseerr
    """
    try:
        raw_payload = await request.json()
        logger.info(f"Received webhook payload: {raw_payload}")
        
        # Parse payload into WebhookPayload model
        payload = WebhookPayload(**raw_payload)
        
        # Test notification handling
        if payload.notification_type == "TEST_NOTIFICATION":
            logger.info("Test notification received and processed successfully.")
            return {"status": "success", "message": "Test notification processed successfully."}
        
        logger.info(f"Received webhook with event: {payload.event}")
        
        if payload.media is None:
            logger.error("Media information is missing in the payload")
            raise HTTPException(status_code=400, detail="Media information is missing in the payload")

        media_type = payload.media.media_type
        logger.info(f"Processing {media_type.capitalize()} request")

        tmdb_id = str(payload.media.tmdbId)
        if not tmdb_id:
            logger.error("TMDB ID is missing in the payload")
            raise HTTPException(status_code=400, detail="TMDB ID is missing in the payload")

        # Fetch media details from Trakt
        media_details = get_media_details_from_trakt(tmdb_id, media_type)
        if not media_details:
            logger.error(f"Failed to fetch {media_type} details from Trakt")
            raise HTTPException(status_code=500, detail=f"Failed to fetch {media_type} details from Trakt")

        # Format title with year
        media_title = f"{media_details['title']} ({media_details['year']})"
        imdb_id = media_details['imdb_id']
        
        # Check if browser is initialized
        if seerr.browser.driver is None:
            logger.warning("Browser not initialized. Attempting to reinitialize...")
            await initialize_browser()
        
        # For TV shows, check for discrepancies before adding to queue
        if media_type == 'tv' and payload.extra:
            # Extract requested seasons from extra data
            requested_seasons = []
            for item in payload.extra:
                if item['name'] == 'Requested Seasons':
                    requested_seasons = item['value'].split(', ')
                    logger.info(f"Webhook: Requested seasons for TV show: {requested_seasons}")
                    break
            
            if requested_seasons and media_details.get('trakt_id'):
                # Initialize discrepancy checking
                from seerr.config import DISCREPANCY_REPO_FILE
                import os
                import json
                from datetime import datetime
                
                discrepant_shows = set()
                has_discrepancy = False
                
                # Load existing discrepancies if the file exists
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
                        logger.info(f"Webhook: Loaded {len(discrepant_shows)} shows with discrepancies")
                    except Exception as e:
                        logger.error(f"Webhook: Failed to read episode_discrepancies.json: {e}")
                        discrepant_shows = set()
                else:
                    # Initialize the file if it doesn't exist
                    with open(DISCREPANCY_REPO_FILE, 'w', encoding='utf-8') as f:
                        json.dump({"discrepancies": []}, f)
                    logger.info("Webhook: Initialized new episode_discrepancies.json file")
                
                # Process each requested season
                trakt_show_id = media_details['trakt_id']
                for season in requested_seasons:
                    from seerr.utils import normalize_season
                    normalized_season = normalize_season(season)
                    season_number = int(normalized_season.split()[-1])
                    
                    # Check if this season is already in discrepancies
                    if (media_title, season_number) in discrepant_shows:
                        logger.info(f"Webhook: Season {season_number} of {media_title} already in discrepancies.")
                        has_discrepancy = True
                        continue
                    
                    # Fetch season details
                    season_details = get_season_details_from_trakt(str(trakt_show_id), season_number)
                    
                    if season_details:
                        episode_count = season_details.get('episode_count', 0)
                        aired_episodes = season_details.get('aired_episodes', 0)
                        logger.info(f"Webhook: Season {season_number} details: episode_count={episode_count}, aired_episodes={aired_episodes}")
                        
                        # Check for discrepancy between episode_count and aired_episodes
                        if episode_count != aired_episodes:
                            # Only check for the next episode if there's a discrepancy
                            has_aired, next_episode_details = check_next_episode_aired(
                                str(trakt_show_id), season_number, aired_episodes
                            )
                            if has_aired:
                                logger.info(f"Webhook: Next episode (E{aired_episodes + 1:02d}) has aired for {media_title} Season {season_number}.")
                                season_details['aired_episodes'] = aired_episodes + 1
                                # Update aired_episodes after confirming next episode aired
                                aired_episodes = season_details['aired_episodes']
                            else:
                                logger.info(f"Webhook: Next episode (E{aired_episodes + 1:02d}) has not aired for {media_title} Season {season_number}.")
                            
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
                                "failed_episodes": failed_episodes
                            }
                            
                            # Load current discrepancies
                            with open(DISCREPANCY_REPO_FILE, 'r', encoding='utf-8') as f:
                                repo_data = json.load(f)
                            
                            # Add the new discrepancy
                            repo_data["discrepancies"].append(discrepancy_entry)
                            with open(DISCREPANCY_REPO_FILE, 'w', encoding='utf-8') as f:
                                json.dump(repo_data, f, indent=2)
                            logger.info(f"Webhook: Found episode count discrepancy for {media_title} Season {season_number}. Added to {DISCREPANCY_REPO_FILE}")
                            discrepant_shows.add((media_title, season_number))
                            has_discrepancy = True
                        else:
                            logger.info(f"Webhook: No episode count discrepancy for {media_title} Season {season_number}.")
        
        # Get the actual media_id from the request_id
        from seerr.overseerr import get_media_id_from_request_id
        request_id = int(payload.request.request_id)
        media_id = get_media_id_from_request_id(request_id)
        
        if media_id is None:
            logger.error(f"Failed to get media_id for request_id {request_id}")
            raise HTTPException(status_code=500, detail=f"Failed to get media_id for request_id {request_id}")
        
        # Add to appropriate queue based on media type
        if media_type == 'movie':
            success = await add_movie_to_queue(
                imdb_id, media_title, media_type, payload.extra, 
                media_id, payload.media.tmdbId
            )
        else:  # TV show
            success = await add_tv_to_queue(
                imdb_id, media_title, media_type, payload.extra,
                media_id, payload.media.tmdbId
            )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to add request to queue - queue is full")
        
        return {
            "status": "success", 
            "message": f"Added {media_type} request to queue",
            "media": {
                "title": media_details['title'],
                "year": media_details['year'],
                "imdb_id": imdb_id
            }
        }
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reload-env")
async def reload_environment():
    """
    Reload environment variables from the .env file.
    This endpoint can be called when environment variables have been changed externally.
    """
    logger.info("Environment reload triggered via API endpoint")
    
    # Store original values for comparison
    from seerr.config import (
        RD_ACCESS_TOKEN, RD_REFRESH_TOKEN, RD_CLIENT_ID, RD_CLIENT_SECRET,
        OVERSEERR_BASE, OVERSEERR_API_BASE_URL, OVERSEERR_API_KEY, TRAKT_API_KEY,
        HEADLESS_MODE, ENABLE_AUTOMATIC_BACKGROUND_TASK, ENABLE_SHOW_SUBSCRIPTION_TASK,
        TORRENT_FILTER_REGEX, MAX_MOVIE_SIZE, MAX_EPISODE_SIZE, REFRESH_INTERVAL_MINUTES
    )
    
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
    
    # Reload configuration
    from seerr.config import load_config
    if not load_config(override=True):
        raise HTTPException(status_code=500, detail="Failed to reload environment variables")
    
    # Get updated values after reload
    from seerr.config import (
        RD_ACCESS_TOKEN, RD_REFRESH_TOKEN, RD_CLIENT_ID, RD_CLIENT_SECRET,
        OVERSEERR_BASE, OVERSEERR_API_BASE_URL, OVERSEERR_API_KEY, TRAKT_API_KEY,
        HEADLESS_MODE, ENABLE_AUTOMATIC_BACKGROUND_TASK, ENABLE_SHOW_SUBSCRIPTION_TASK,
        TORRENT_FILTER_REGEX, MAX_MOVIE_SIZE, MAX_EPISODE_SIZE, REFRESH_INTERVAL_MINUTES
    )
    
    # Detect which values have changed
    changes = {}
    for key, old_value in original_values.items():
        new_value = locals()[key]  # Get the new value from the reloaded config
        if new_value != old_value:
            changes[key] = {"old": old_value, "new": new_value}
    
    if changes:
        logger.info(f"Environment variables changed: {list(changes.keys())}")
        
        # Apply changes to browser if needed
        from seerr.browser import driver
        
        # Update RD credentials in browser if changed
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
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                
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
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait, Select
                from selenium.webdriver.support import expected_conditions as EC
                
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
        if "REFRESH_INTERVAL_MINUTES" in changes:
            from seerr.background_tasks import scheduler, populate_queues_from_overseerr
            
            if scheduler and scheduler.running:
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
                        if job.id in ["process_movie_requests"]:
                            scheduler.remove_job(job.id)
                            logger.info(f"Removed existing job with ID: {job.id}")
            
                    # Re-add jobs with new interval using current config values
                    if ENABLE_AUTOMATIC_BACKGROUND_TASK:
                        from seerr.background_tasks import scheduled_task_wrapper
                        scheduler.add_job(
                            scheduled_task_wrapper,
                            'interval',
                            minutes=interval,
                            id="process_movie_requests",
                            replace_existing=True,
                            max_instances=1
                        )
                        logger.info(f"Rescheduled movie requests check every {interval} minute(s)")
                except Exception as e:
                    logger.error(f"Error updating scheduler: {e}")
        
        # Handle changes to task enablement flags
        if "ENABLE_AUTOMATIC_BACKGROUND_TASK" in changes:
            from seerr.background_tasks import scheduler, scheduled_task_wrapper
            
            if scheduler and scheduler.running:
                logger.info("Updating scheduler based on task enablement changes")
                
                # Handle automatic background task changes
                if ENABLE_AUTOMATIC_BACKGROUND_TASK:
                    # Task was enabled - add the job
                    scheduler.add_job(
                        scheduled_task_wrapper,
                        'interval',
                        minutes=REFRESH_INTERVAL_MINUTES,
                        id="process_movie_requests",
                        replace_existing=True,
                        max_instances=1
                    )
                    logger.info(f"Enabled automatic movie requests check every {REFRESH_INTERVAL_MINUTES} minute(s)")
                else:
                    # Task was disabled - remove the job
                    try:
                        scheduler.remove_job("process_movie_requests")
                        logger.info("Disabled automatic movie requests check")
                    except Exception as e:
                        logger.debug(f"Job 'process_movie_requests' was already removed or didn't exist: {e}")
    else:
        logger.info("No environment variable changes detected")
    
    return {
        "status": "success", 
        "message": "Environment variables reloaded successfully",
        "changes": list(changes.keys())
    }

@app.post("/refresh-library-stats")
async def refresh_library_stats_endpoint():
    """
    Manually refresh library statistics from the browser
    """
    try:
        logger.info("Manual library stats refresh triggered via API endpoint")
        
        # Check if it's safe to refresh first (only for manual triggers)
        from seerr.background_tasks import get_queue_status
        if not is_safe_to_refresh_library_stats():
            queue_status = get_queue_status()
            logger.info("Manual library stats refresh skipped - queues are active or recently active")
            return {
                "status": "skipped",
                "message": "Library stats refresh skipped - queues are active or recently active. Please wait for queues to be idle for at least 60 seconds.",
                "queue_status": queue_status
            }
        
        # For manual refresh, call refresh_library_stats directly
        success = refresh_library_stats()
        
        if success:
            # Get updated stats
            library_stats = getattr(seerr.browser, 'library_stats', {
                "torrents_count": 0,
                "total_size_tb": 0.0,
                "last_updated": None
            })
            
            return {
                "status": "success",
                "message": "Library statistics refreshed successfully",
                "library_stats": library_stats
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to refresh library statistics")
            
    except Exception as e:
        logger.error(f"Error refreshing library stats via API: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8777) 
