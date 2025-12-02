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

async def process_tv_show_seasons(media_title: str, requested_seasons: List[str], media_details: Dict[str, Any], 
                                tmdb_id: int, imdb_id: str, request_id: int) -> None:
    """
    Process season data for a TV show after the database record has been created.
    
    Args:
        media_title: The formatted title of the TV show
        requested_seasons: List of requested season numbers
        media_details: Media details from Trakt
        tmdb_id: TMDB ID of the TV show
        imdb_id: IMDb ID of the TV show
        request_id: Overseerr request ID
    """
    if not requested_seasons or not media_details.get('trakt_id'):
        return
        
    logger.info(f"Webhook: Performing comprehensive season validation for {media_title}")
    
    try:
        from seerr.trakt import get_season_details_from_trakt, check_next_episode_aired
        from seerr.enhanced_season_manager import EnhancedSeasonManager
        from seerr.config import DISCREPANCY_REPO_FILE
        import os
        import json
        from datetime import datetime
        
        trakt_show_id = media_details['trakt_id']
        seasons_data = []
        discrepant_seasons = []
        
        logger.info(f"Webhook: Starting to process {len(requested_seasons)} seasons for {media_title}")
        
        # Load existing discrepancies if the file exists
        discrepant_shows = set()
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
        for season in requested_seasons:
            from seerr.utils import normalize_season
            normalized_season = normalize_season(season)
            season_number = int(normalized_season.split()[-1])
            
            logger.info(f"Webhook: Processing season {season_number} for {media_title}")
            
            # Check if this season is already in discrepancies
            if (media_title, season_number) in discrepant_shows:
                logger.info(f"Webhook: Season {season_number} of {media_title} already in discrepancies.")
                continue
            
            # Fetch season details from Trakt
            logger.info(f"Webhook: Fetching season {season_number} details from Trakt for show {trakt_show_id}")
            season_details = get_season_details_from_trakt(str(trakt_show_id), season_number)
            
            if season_details:
                logger.info(f"Webhook: Successfully fetched season {season_number} details from Trakt")
                episode_count = season_details.get('episode_count', 0)
                aired_episodes = season_details.get('aired_episodes', 0)
                logger.info(f"Webhook: Season {season_number} details: episode_count={episode_count}, aired_episodes={aired_episodes}")
                
                # Check for next episode if there's a discrepancy
                if episode_count != aired_episodes:
                    has_aired, next_episode_details = check_next_episode_aired(
                        str(trakt_show_id), season_number, aired_episodes
                    )
                    if has_aired:
                        logger.info(f"Webhook: Next episode (E{aired_episodes + 1:02d}) has aired for {media_title} Season {season_number}.")
                        aired_episodes += 1
                    else:
                        logger.info(f"Webhook: Next episode (E{aired_episodes + 1:02d}) has not aired for {media_title} Season {season_number}.")
                
                # Check for discrepancy first
                # Only mark as discrepant if there's a real data inconsistency
                # For in-progress seasons, episode_count > aired_episodes is NORMAL, not a discrepancy
                # A discrepancy would be aired_episodes > episode_count (data error)
                # For new shows that haven't aired yet, aired_episodes = 0 is also normal
                is_season_discrepant = False
                if aired_episodes > episode_count:
                    # This is a real discrepancy - more aired than total (data error)
                    is_season_discrepant = True
                
                # Create enhanced season data
                season_data = {
                    'season_number': season_number,
                    'episode_count': episode_count,
                    'aired_episodes': aired_episodes,
                    'confirmed_episodes': [],
                    'failed_episodes': [],
                    'unprocessed_episodes': [f"E{str(i).zfill(2)}" for i in range(1, aired_episodes + 1)] if aired_episodes > 0 else [],
                    'last_checked': datetime.utcnow().isoformat(),
                    'updated_at': datetime.utcnow().isoformat(),
                    'status': 'pending',
                    'is_discrepant': is_season_discrepant,
                    'discrepancy_reason': 'episode_count_mismatch' if is_season_discrepant else None,
                    'discrepancy_details': {'episode_count': episode_count, 'aired_episodes': aired_episodes} if is_season_discrepant else {}
                }
                
                seasons_data.append(season_data)
                
                # Check for discrepancy and add to discrepancy file if needed
                # Only log discrepancies for real data errors, not in-progress seasons
                if aired_episodes > episode_count:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    failed_episodes = [
                        f"E{str(i).zfill(2)}"  # Format as E01, E02, etc.
                        for i in range(1, aired_episodes + 1)
                    ]
                    discrepancy_entry = {
                        "show_title": media_title,
                        "trakt_show_id": trakt_show_id,
                        "imdb_id": imdb_id,
                        "seerr_id": request_id,
                        "season_number": season_number,
                        "season_details": season_details,
                        "timestamp": timestamp,
                        "failed_episodes": failed_episodes
                    }
                    
                    # Load current discrepancies and add new one
                    with open(DISCREPANCY_REPO_FILE, 'r', encoding='utf-8') as f:
                        repo_data = json.load(f)
                    repo_data["discrepancies"].append(discrepancy_entry)
                    with open(DISCREPANCY_REPO_FILE, 'w', encoding='utf-8') as f:
                        json.dump(repo_data, f, indent=2)
                    
                    logger.info(f"Webhook: Found episode count discrepancy for {media_title} Season {season_number}. Added to {DISCREPANCY_REPO_FILE}")
                    discrepant_seasons.append(season_number)
                else:
                    logger.info(f"Webhook: No episode count discrepancy for {media_title} Season {season_number}.")
            else:
                logger.warning(f"Webhook: Failed to fetch season {season_number} details for {media_title}")
        
        # Store comprehensive season data in database
        if seasons_data:
            logger.info(f"Webhook: Storing {len(seasons_data)} seasons data for TV show {media_title}")
            
            # Use EnhancedSeasonManager to store the season data
            EnhancedSeasonManager.update_tv_show_seasons(
                tmdb_id=tmdb_id,
                seasons_data=seasons_data,
                title=media_details['title']
            )
            logger.info(f"Webhook: Successfully stored seasons data for {media_title}")
            
            if discrepant_seasons:
                logger.info(f"Webhook: Found discrepancies in seasons {discrepant_seasons} for {media_title}")
        
    except Exception as e:
        logger.error(f"Webhook: Error in comprehensive season validation for {media_title}: {e}")

from seerr.config import load_config, REFRESH_INTERVAL_MINUTES
from seerr.models import WebhookPayload
from seerr.realdebrid import check_and_refresh_access_token
from seerr.trakt import get_media_details_from_trakt, get_season_details_from_trakt, check_next_episode_aired
from seerr.utils import parse_requested_seasons, START_TIME
from seerr.database import init_database
from seerr.db_logger import db_logger

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
from seerr.api_endpoints import app as api_app

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
    
    # Initialize database
    try:
        init_database()
        logger.info("Database initialized successfully")
        
        # Run automatic database migrations
        from seerr.migration_runner import run_automatic_migrations
        run_automatic_migrations()
        
        # Sync all existing Overseerr requests to database
        from seerr.background_tasks import sync_all_requests_to_database
        await sync_all_requests_to_database()
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        # Continue without database if it fails
        logger.warning("Continuing without database - using file-based logging")
    
    # Check RD token on startup
    check_and_refresh_access_token()
    
    # Initialize browser (optional - may fail in Docker)
    browser_result = await initialize_browser()
    if browser_result is None:
        logger.warning("Browser initialization failed - browser automation features will be disabled")
    else:
        logger.info(f"Browser initialized successfully: {seerr.browser.driver is not None}")
    
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
        # Check if it's safe to refresh before attempting
        if is_safe_to_refresh_library_stats(min_idle_seconds=30):
            logger.info("Initial library stats refresh triggered - queues are idle")
            refresh_library_stats()
        else:
            logger.info("Initial library stats refresh skipped - queues are active or recently active")
    
    # Initial refresh
    asyncio.create_task(delayed_refresh_library_stats())
    
    # Note: Library stats refresh will now be triggered automatically 
    # 30 seconds after queue processing completes, instead of on a schedule
    logger.info("Library stats refresh will be triggered after queue completion.")
    
    # Start background task to update database status every second
    async def status_updater():
        """Update service status in database every second"""
        while True:
            try:
                # Get current status data
                from datetime import datetime
                from seerr.config import ENABLE_AUTOMATIC_BACKGROUND_TASK, ENABLE_SHOW_SUBSCRIPTION_TASK, REFRESH_INTERVAL_MINUTES
                from seerr.background_tasks import is_safe_to_refresh_library_stats, last_queue_activity_time
                from seerr.database import update_service_status
                
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
                
                # Prepare status data
                status_data = {
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
                
                # Update database with current status
                update_service_status("seerrbridge", status_data)
                
            except Exception as e:
                logger.error(f"Error updating service status: {e}")
            
            # Wait 1 second before next update
            await asyncio.sleep(1)
    
    # Start the status updater task
    asyncio.create_task(status_updater())
    logger.info("Started background status updater (every 1 second)")
    
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

# Mount the API endpoints
app.mount("/api", api_app)

@app.get("/status")
async def get_status():
    """
    Get the status of the SeerrBridge service
    """
    from datetime import datetime
    # Import config variables fresh each time to get updated values after reload
    from seerr.config import ENABLE_AUTOMATIC_BACKGROUND_TASK, ENABLE_SHOW_SUBSCRIPTION_TASK, REFRESH_INTERVAL_MINUTES
    from seerr.background_tasks import is_safe_to_refresh_library_stats, last_queue_activity_time
    from seerr.database import update_service_status
    
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
    
    # Prepare status data
    status_data = {
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
    
    # Update database with current status
    try:
        update_service_status("seerrbridge", status_data)
    except Exception as e:
        logger.error(f"Failed to update service status in database: {e}")
    
    return status_data

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
        
        # Extract request_id early so it's available throughout the function
        request_id = int(payload.request.request_id)
        
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
        
        # Store requested seasons info for later processing after database record creation
        requested_seasons = []
        if media_type == 'tv' and payload.extra:
            for item in payload.extra:
                if item['name'] == 'Requested Seasons':
                    requested_seasons = item['value'].split(', ')
                    logger.info(f"Webhook: Requested seasons for TV show: {requested_seasons}")
                    break
        
        # Get the actual media_id from the request_id
        from seerr.overseerr import get_media_id_from_request_id
        media_id = get_media_id_from_request_id(request_id)
        
        if media_id is None:
            logger.error(f"Failed to get media_id for request_id {request_id}")
            raise HTTPException(status_code=500, detail=f"Failed to get media_id for request_id {request_id}")
        
        # Add to appropriate queue based on media type
        if media_type == 'movie':
            success = await add_movie_to_queue(
                imdb_id, media_title, media_type, payload.extra, 
                media_id, payload.media.tmdbId, request_id
            )
            if success:
                # Start tracking media processing in database
                from seerr.unified_media_manager import start_media_processing
                from seerr.config import USE_DATABASE
                
                if USE_DATABASE:
                    # Cache images if needed
                    image_data = None
                    try:
                        from seerr.unified_media_manager import fetch_and_cache_images_if_needed
                        image_data = fetch_and_cache_images_if_needed(
                            tmdb_id=int(payload.media.tmdbId),
                            title=media_details['title'],
                            media_type=media_type,
                            trakt_id=media_details.get('trakt_id')
                        )
                    except Exception as e:
                        logger.error(f"Error processing images for {media_title}: {e}")
                    
                    # Start tracking media processing
                    processed_media_id = start_media_processing(
                        tmdb_id=int(payload.media.tmdbId),
                        imdb_id=imdb_id,
                        trakt_id=media_details.get('trakt_id'),
                        media_type=media_type,
                        title=media_details['title'],
                        year=media_details['year'],
                        overseerr_request_id=request_id,
                        overseerr_media_id=media_id,
                        processing_stage='queue_processing',
                        extra_data=payload.extra,
                        image_data=image_data,
                        media_details=media_details
                    )
                    
                    # Track the media request in the database
                    from seerr.overseerr import track_media_request
                    track_media_request(
                        overseerr_request_id=request_id,
                        overseerr_media_id=media_id,
                        tmdb_id=int(payload.media.tmdbId),
                        imdb_id=imdb_id,
                        trakt_id=media_details.get('trakt_id'),
                        media_type=media_type,
                        title=media_details['title'],
                        year=media_details['year'],
                        requested_by=payload.request.requestedBy_username,
                        extra_data=payload.extra
                    )
        else:  # TV show
            success = await add_tv_to_queue(
                imdb_id, media_title, media_type, payload.extra,
                media_id, payload.media.tmdbId, request_id
            )
            if success:
                # Start tracking media processing in database for TV shows
                from seerr.unified_media_manager import start_media_processing
                from seerr.config import USE_DATABASE
                
                if USE_DATABASE:
                    # Cache images if needed
                    image_data = None
                    try:
                        from seerr.unified_media_manager import fetch_and_cache_images_if_needed
                        image_data = fetch_and_cache_images_if_needed(
                            tmdb_id=int(payload.media.tmdbId),
                            title=media_details['title'],
                            media_type=media_type,
                            trakt_id=media_details.get('trakt_id')
                        )
                    except Exception as e:
                        logger.error(f"Error processing images for {media_title}: {e}")
                    
                    # Use the requested seasons we extracted earlier
                    
                    # Start tracking media processing
                    processed_media_id = start_media_processing(
                        tmdb_id=int(payload.media.tmdbId),
                        imdb_id=imdb_id,
                        trakt_id=media_details.get('trakt_id'),
                        media_type=media_type,
                        title=media_details['title'],
                        year=media_details['year'],
                        overseerr_request_id=request_id,
                        overseerr_media_id=media_id,
                        processing_stage='queue_processing',
                        extra_data={'requested_seasons': requested_seasons} if requested_seasons else payload.extra,
                        image_data=image_data,
                        media_details=media_details
                    )
                    
                    # Track the media request in the database
                    from seerr.overseerr import track_media_request
                    track_media_request(
                        overseerr_request_id=request_id,
                        overseerr_media_id=media_id,
                        tmdb_id=int(payload.media.tmdbId),
                        imdb_id=imdb_id,
                        trakt_id=media_details.get('trakt_id'),
                        media_type=media_type,
                        title=media_details['title'],
                        year=media_details['year'],
                        requested_by=payload.request.requestedBy_username,
                        extra_data={'requested_seasons': requested_seasons} if requested_seasons else payload.extra
                    )
                    
                    # Process season data now that the database record exists
                    await process_tv_show_seasons(
                        media_title=media_title,
                        requested_seasons=requested_seasons,
                        media_details=media_details,
                        tmdb_id=int(payload.media.tmdbId),
                        imdb_id=imdb_id,
                        request_id=request_id
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
    
    # Reload configuration from .env file
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
                # Check if driver is still valid
                try:
                    driver.current_url
                except Exception as e:
                    logger.error(f"Browser driver is no longer valid: {e}")
                    logger.info("Skipping filter update due to invalid driver")
                    return {"message": "Environment reloaded, but browser driver is invalid"}
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                from selenium.common.exceptions import TimeoutException, NoSuchElementException
                
                # Navigate directly to settings page
                logger.info("Navigating to DMM settings page for filter update")
                driver.get("https://debridmediamanager.com/settings")
                
                # Wait for settings page to load
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "dmm-default-torrents-filter"))
                )
                logger.info("Settings page loaded successfully for filter update")
                
                # Update filter
                default_filter_input = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.ID, "dmm-default-torrents-filter"))
                )
                default_filter_input.clear()
                default_filter_input.send_keys(TORRENT_FILTER_REGEX)
                logger.info(f"Successfully updated torrent filter regex to: {TORRENT_FILTER_REGEX}")
                
            except TimeoutException as e:
                logger.error(f"Timeout while updating torrent filter regex: {e}")
            except NoSuchElementException as e:
                logger.error(f"Element not found while updating torrent filter regex: {e}")
            except Exception as e:
                logger.error(f"Error updating torrent filter regex: {e}")
                import traceback
                logger.error(f"Stacktrace:\n{traceback.format_exc()}")
        
        # Apply size settings if needed
        if driver and ("MAX_MOVIE_SIZE" in changes or "MAX_EPISODE_SIZE" in changes):
            logger.info("Updating size settings in browser")
            try:
                # Check if driver is still valid
                try:
                    driver.current_url
                except Exception as e:
                    logger.error(f"Browser driver is no longer valid: {e}")
                    logger.info("Skipping size settings update due to invalid driver")
                    return {"message": "Environment reloaded, but browser driver is invalid"}
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait, Select
                from selenium.webdriver.support import expected_conditions as EC
                from selenium.common.exceptions import TimeoutException, NoSuchElementException
                
                # Navigate directly to settings page
                logger.info("Navigating to DMM settings page")
                driver.get("https://debridmediamanager.com/settings")
                
                # Wait for settings page to load
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "dmm-movie-max-size"))
                )
                logger.info("Settings page loaded successfully")
                
                # Update movie size if changed
                if "MAX_MOVIE_SIZE" in changes:
                    logger.info(f"Updating max movie size to: {MAX_MOVIE_SIZE}")
                    max_movie_select = WebDriverWait(driver, 10).until(
                        EC.visibility_of_element_located((By.ID, "dmm-movie-max-size"))
                    )
                    select_obj = Select(max_movie_select)
                    
                    # Get available options for validation
                    available_options = [option.get_attribute('value') for option in select_obj.options]
                    logger.info(f"Available movie size options: {available_options}")
                    
                    # Convert to string and validate
                    movie_size_value = str(int(MAX_MOVIE_SIZE)) if MAX_MOVIE_SIZE is not None else "0"
                    if movie_size_value in available_options:
                        select_obj.select_by_value(movie_size_value)
                        logger.info(f"Successfully updated max movie size to: {MAX_MOVIE_SIZE}")
                    else:
                        logger.warning(f"Movie size value '{movie_size_value}' not available. Available options: {available_options}. Using 'Biggest available' (0) as fallback.")
                        select_obj.select_by_value("0")
                        logger.info("Set max movie size to 'Biggest available' (0) as fallback")
                
                # Update episode size if changed
                if "MAX_EPISODE_SIZE" in changes:
                    logger.info(f"Updating max episode size to: {MAX_EPISODE_SIZE}")
                    max_episode_select = WebDriverWait(driver, 10).until(
                        EC.visibility_of_element_located((By.ID, "dmm-episode-max-size"))
                    )
                    select_obj = Select(max_episode_select)
                    
                    # Get available options for validation
                    available_options = [option.get_attribute('value') for option in select_obj.options]
                    logger.info(f"Available episode size options: {available_options}")
                    
                    # Handle both integer and float values properly
                    if MAX_EPISODE_SIZE is not None:
                        if MAX_EPISODE_SIZE == int(MAX_EPISODE_SIZE):
                            # Integer value (e.g., 1, 3, 5)
                            episode_size_value = str(int(MAX_EPISODE_SIZE))
                        else:
                            # Float value (e.g., 0.1, 0.3, 0.5)
                            episode_size_value = str(MAX_EPISODE_SIZE)
                    else:
                        episode_size_value = "0"
                    
                    if episode_size_value in available_options:
                        select_obj.select_by_value(episode_size_value)
                        logger.info(f"Successfully updated max episode size to: {MAX_EPISODE_SIZE}")
                    else:
                        logger.warning(f"Episode size value '{episode_size_value}' not available. Available options: {available_options}. Using 'Biggest available' (0) as fallback.")
                        select_obj.select_by_value("0")
                        logger.info("Set max episode size to 'Biggest available' (0) as fallback")
                
                logger.info("Size settings updated successfully")
                
            except TimeoutException as e:
                logger.error(f"Timeout while updating size settings: {e}")
            except NoSuchElementException as e:
                logger.error(f"Element not found while updating size settings: {e}")
            except Exception as e:
                logger.error(f"Error updating size settings: {e}")
                import traceback
                logger.error(f"Stacktrace:\n{traceback.format_exc()}")
        
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

@app.post("/retrigger-media/{media_id}")
async def retrigger_media(media_id: int):
    """
    Re-trigger processing for a media item as if it was a new incoming webhook
    """
    try:
        logger.info(f"Re-triggering media processing for media ID: {media_id}")
        
        # Get media details from database
        from seerr.unified_media_manager import get_media_by_id
        from seerr.config import USE_DATABASE
        
        if not USE_DATABASE:
            raise HTTPException(status_code=500, detail="Database not enabled")
        
        media_record = get_media_by_id(media_id)
        if not media_record:
            raise HTTPException(status_code=404, detail="Media item not found")
        
        # Check if media is ignored - don't retrigger ignored items
        if media_record.status == 'ignored':
            raise HTTPException(status_code=400, detail="Cannot retrigger ignored media items")
        
        # Check if critical data is missing before calling Trakt
        needs_trakt_data = not media_record.tmdb_id or not media_record.imdb_id or not media_record.title
        
        if needs_trakt_data:
            logger.info(f"Critical data missing for media ID {media_id}, fetching from Trakt")
            # Get media details from Trakt
            media_details = get_media_details_from_trakt(media_record.tmdb_id, media_record.media_type)
            if not media_details:
                raise HTTPException(status_code=500, detail=f"Failed to fetch {media_record.media_type} details from Trakt")
            
            # Format title with year
            media_title = f"{media_details['title']} ({media_details['year']})"
            imdb_id = media_details['imdb_id']
        else:
            # Use existing data
            media_title = f"{media_record.title} ({media_record.year})" if media_record.year else media_record.title
            imdb_id = media_record.imdb_id
            media_details = None
            logger.info(f"Using existing data for media ID {media_id}, skipping Trakt call")
        
        # Check if browser is initialized
        if seerr.browser.driver is None:
            logger.warning("Browser not initialized. Attempting to reinitialize...")
            await initialize_browser()
        
        # Reset status to processing (not pending) and clear processing stage
        from seerr.unified_media_manager import update_media_details
        
        # Safely merge existing extra_data which could be a dict or a list
        existing_extra = media_record.extra_data
        if isinstance(existing_extra, dict):
            merged_extra = {**existing_extra}
        elif isinstance(existing_extra, list):
            # Preserve original payload under a namespaced key
            merged_extra = {'payload': existing_extra}
        else:
            merged_extra = {}

        merged_extra['retriggered_at'] = datetime.now().isoformat()

        update_kwargs = {
            'status': 'processing',
            'processing_stage': 'retriggered',
            'processing_started_at': datetime.utcnow(),
            'last_checked_at': datetime.utcnow(),
            'extra_data': merged_extra
        }
        
        # Update with fresh metadata if we fetched from Trakt
        if media_details:
            update_kwargs.update({
                'overview': media_details.get('overview'),
                'genres': media_details.get('genres'),
                'runtime': media_details.get('runtime'),
                'rating': media_details.get('rating'),
                'vote_count': media_details.get('vote_count'),
                'popularity': media_details.get('popularity')
            })
        
        # For TV shows, reset all seasons and episodes to processing status
        if media_record.media_type == 'tv' and media_record.seasons_data:
            from seerr.unified_media_manager import generate_seasons_processing_string
            
            seasons_data = media_record.seasons_data if isinstance(media_record.seasons_data, list) else json.loads(media_record.seasons_data) if media_record.seasons_data else []
            
            # Reset all seasons to processing and all episodes to unprocessed
            reset_seasons_data = []
            for season in seasons_data:
                season_num = season.get('season_number')
                aired_episodes = season.get('aired_episodes', 0)
                
                # Create unprocessed episodes list for all aired episodes
                unprocessed_episodes = [f"E{str(i).zfill(2)}" for i in range(1, aired_episodes + 1)] if aired_episodes > 0 else []
                
                reset_season = {
                    'season_number': season_num,
                    'episode_count': season.get('episode_count', 0),
                    'aired_episodes': aired_episodes,
                    'confirmed_episodes': [],
                    'failed_episodes': [],
                    'unprocessed_episodes': unprocessed_episodes,
                    'is_discrepant': False,
                    'discrepancy_reason': None,
                    'discrepancy_details': None,
                    'last_checked': datetime.utcnow().isoformat(),
                    'updated_at': datetime.utcnow().isoformat(),
                    'status': 'processing'
                }
                reset_seasons_data.append(reset_season)
            
            # Generate seasons_processing string using the proper function
            seasons_processing = generate_seasons_processing_string(reset_seasons_data)
            
            update_kwargs.update({
                'seasons_data': reset_seasons_data,
                'seasons_processing': seasons_processing,
                'seasons_completed': [],
                'seasons_failed': [],
                'seasons_discrepant': []
            })
            
            logger.info(f"Reset all {len(reset_seasons_data)} seasons to processing status for {media_record.title}")
        
        update_media_details(media_record.id, **update_kwargs)
        
        # Cache images if needed (only if we fetched from Trakt)
        if media_details:
            image_data = None
            try:
                from seerr.unified_media_manager import fetch_and_cache_images_if_needed
                image_data = fetch_and_cache_images_if_needed(
                    tmdb_id=media_record.tmdb_id,
                    title=media_details['title'],
                    media_type=media_record.media_type,
                    trakt_id=media_details.get('trakt_id'),
                    existing_media=media_record  # Pass existing media to check for existing images
                )
            except Exception as e:
                logger.error(f"Error processing images for {media_title}: {e}")
        
        # Add to appropriate queue based on media type
        if media_record.media_type == 'movie':
            success = await add_movie_to_queue(
                imdb_id, media_title, media_record.media_type, media_record.extra_data or {}, 
                media_record.overseerr_media_id or 0, media_record.tmdb_id, media_record.overseerr_request_id
            )
        else:  # TV show
            success = await add_tv_to_queue(
                imdb_id, media_title, media_record.media_type, media_record.extra_data or {},
                media_record.overseerr_media_id or 0, media_record.tmdb_id, media_record.overseerr_request_id
            )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to add request to queue - queue is full")
        
        logger.info(f"Successfully retriggered processing for {media_title}")
        
        return {
            "status": "success", 
            "message": f"Re-triggered {media_record.media_type} processing",
            "media": {
                "id": media_record.id,
                "title": media_details['title'] if media_details else media_record.title,
                "year": media_details['year'] if media_details else media_record.year,
                "imdb_id": imdb_id,
                "media_type": media_record.media_type
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retriggering media processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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

@app.post("/api/setup/test-dmm")
async def test_dmm_credentials_endpoint(request: Request):
    """
    Test DMM credentials during setup process
    """
    try:
        payload = await request.json()
        
        rd_client_id = payload.get('rd_client_id')
        rd_client_secret = payload.get('rd_client_secret')
        rd_access_token = payload.get('rd_access_token')
        rd_refresh_token = payload.get('rd_refresh_token')
        
        if not all([rd_client_id, rd_client_secret, rd_access_token, rd_refresh_token]):
            raise HTTPException(status_code=400, detail="Missing required credentials")
        
        # Import and call the test function
        from seerr.setup_test_dmm import test_dmm_credentials_api
        
        result = test_dmm_credentials_api(
            rd_client_id, 
            rd_client_secret, 
            rd_access_token, 
            rd_refresh_token, 
            headless=True
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error testing DMM credentials: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8777) 
