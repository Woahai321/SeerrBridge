"""
SeerrBridge - A bridge between Overseerr and Real-Debrid via Debrid Media Manager
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
import asyncio
import json
import os
from loguru import logger

from seerr import __version__
from seerr.config import load_config, ENABLE_AUTOMATIC_BACKGROUND_TASK, ENABLE_SHOW_SUBSCRIPTION_TASK, REFRESH_INTERVAL_MINUTES
from seerr.models import WebhookPayload
from seerr.realdebrid import check_and_refresh_access_token
from seerr.trakt import get_media_details_from_trakt
from seerr.utils import parse_requested_seasons, START_TIME

# Import modules first
import seerr.browser
import seerr.background_tasks
import seerr.search

# Initialize queue
request_queue = asyncio.Queue(maxsize=500)
# Share our queue with the background_tasks module
seerr.background_tasks.request_queue = request_queue

# Now import specific functions
from seerr.browser import initialize_browser, shutdown_browser
from seerr.background_tasks import process_requests, process_movie_requests, add_request_to_queue, check_show_subscriptions, scheduler

processing_task = None  # To track the current processing task

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Setup and teardown operations for the FastAPI application
    """
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
    
    # Start the scheduler
    scheduler.start()
    
    # Start the background processing task
    global processing_task
    processing_task = asyncio.create_task(process_requests())
    logger.info("Started request processing task.")
    
    # Schedule automatic background tasks if enabled
    if ENABLE_AUTOMATIC_BACKGROUND_TASK:
        logger.info("Automatic background task enabled. Starting initial check.")
        asyncio.create_task(process_movie_requests())
        
        # Schedule recurring task
        scheduler.add_job(
            process_movie_requests,
            'interval',
            minutes=REFRESH_INTERVAL_MINUTES,
            id="process_movie_requests",
            replace_existing=True
        )
        logger.info(f"Scheduled movie request checks every {REFRESH_INTERVAL_MINUTES} minute(s).")
    
    # Schedule show subscription check if enabled
    if ENABLE_SHOW_SUBSCRIPTION_TASK:
        logger.info("Show subscription task enabled. Starting initial check.")
        asyncio.create_task(check_show_subscriptions())
        
        # Schedule recurring task
        scheduler.add_job(
            check_show_subscriptions,
            'interval',
            minutes=REFRESH_INTERVAL_MINUTES,
            id="check_show_subscriptions",
            replace_existing=True
        )
        logger.info(f"Scheduled show subscription checks every {REFRESH_INTERVAL_MINUTES} minute(s).")
    
    yield
    
    # Shutdown operations
    logger.info("Shutting down SeerrBridge")
    
    # Cancel background task
    if processing_task:
        processing_task.cancel()
        try:
            await processing_task
        except asyncio.CancelledError:
            pass
    
    # Stop the scheduler
    scheduler.shutdown()
    
    # Shutdown browser
    await shutdown_browser()

app = FastAPI(lifespan=lifespan)

@app.get("/status")
async def get_status():
    """
    Get the status of the SeerrBridge service
    """
    from datetime import datetime
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
    
    return {
        "status": "running",
        "version": __version__,
        "uptime_seconds": uptime_seconds,
        "uptime": uptime_str,
        "start_time": START_TIME.isoformat(),
        "current_time": datetime.now().isoformat(),
        "queue_size": request_queue.qsize(),
        "browser_status": browser_status,
        "automatic_processing": ENABLE_AUTOMATIC_BACKGROUND_TASK,
        "show_subscription": ENABLE_SHOW_SUBSCRIPTION_TASK
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
                    from seerr.trakt import get_season_details_from_trakt, check_next_episode_aired
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
        
        # Directly add to queue instead of using background task
        await add_request_to_queue(imdb_id, media_title, media_type, payload.extra)
        
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
    Reload environment variables
    """
    try:
        if load_config(override=True):
            return {"status": "success", "message": "Environment variables reloaded"}
        else:
            raise HTTPException(status_code=500, detail="Failed to reload environment variables")
    except Exception as e:
        logger.error(f"Error reloading environment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8777) 