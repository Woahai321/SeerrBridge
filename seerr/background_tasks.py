"""
Background tasks module for SeerrBridge
Handles queuing and processing of requests
"""
import os
import json
import asyncio
import time
from asyncio import Queue, Semaphore
from typing import Tuple, Dict, List, Any, Optional
from datetime import datetime, timezone
from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from selenium.common.exceptions import NoSuchElementException
import random
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from seerr.config import (
    TORRENT_FILTER_REGEX,
    USE_DATABASE
)
from seerr.task_config_manager import task_config
from seerr.browser import driver, click_show_more_results, check_red_buttons, prioritize_buttons_in_box
from seerr.overseerr import get_overseerr_media_requests, mark_completed
from seerr.trakt import get_media_details_from_trakt, get_season_details_from_trakt, check_next_episode_aired
from seerr.utils import parse_requested_seasons, normalize_season, extract_season, clean_title
from seerr.database import get_db, LibraryStats, QueueStatus
from seerr.image_utils import fetch_trakt_show_images, fetch_trakt_movie_images, store_show_image, store_media_images, should_update_image
from seerr.db_logger import log_info, log_success, log_warning, log_error, log_critical, log_debug

# Load queue sizes from database configuration
def get_queue_sizes():
    """Get queue sizes from database configuration"""
    movie_size = task_config.get_config('movie_queue_maxsize', 250)
    tv_size = task_config.get_config('tv_queue_maxsize', 250)
    return int(movie_size), int(tv_size)

def refresh_queue_sizes():
    """Refresh queue sizes from database configuration and sync with database"""
    global movie_queue, tv_queue, movie_queue_maxsize, tv_queue_maxsize
    
    new_movie_size, new_tv_size = get_queue_sizes()
    
    # Only recreate queues if sizes have changed
    if new_movie_size != movie_queue_maxsize or new_tv_size != tv_queue_maxsize:
        log_info("Queue Management", f"Updating queue sizes: Movie {movie_queue_maxsize}->{new_movie_size}, TV {tv_queue_maxsize}->{new_tv_size}", 
                module="background_tasks", function="refresh_queue_sizes")
        
        # Create new queues with updated sizes
        old_movie_queue = movie_queue
        old_tv_queue = tv_queue
        
        movie_queue = Queue(maxsize=new_movie_size)
        tv_queue = Queue(maxsize=new_tv_size)
        
        # Transfer any pending items from old queues to new queues
        # Note: This is a best-effort transfer, some items might be lost if queues are full
        try:
            while not old_movie_queue.empty() and not movie_queue.full():
                item = old_movie_queue.get_nowait()
                movie_queue.put_nowait(item)
        except:
            pass
            
        try:
            while not old_tv_queue.empty() and not tv_queue.full():
                item = old_tv_queue.get_nowait()
                tv_queue.put_nowait(item)
        except:
            pass
        
        movie_queue_maxsize = new_movie_size
        tv_queue_maxsize = new_tv_size
        
        # Update database queue_status.max_size to match actual queue sizes
        if USE_DATABASE:
            from seerr.queue_persistence_manager import queue_persistence_manager
            try:
                db = get_db()
                try:
                    from sqlalchemy import text
                    # Update movie queue max_size
                    db.execute(text("""
                        UPDATE queue_status 
                        SET max_size = :max_size, updated_at = NOW()
                        WHERE queue_type = 'movie'
                    """), {"max_size": new_movie_size})
                    # Update TV queue max_size
                    db.execute(text("""
                        UPDATE queue_status 
                        SET max_size = :max_size, updated_at = NOW()
                        WHERE queue_type = 'tv'
                    """), {"max_size": new_tv_size})
                    db.commit()
                    log_info("Queue Management", f"Updated database queue_status.max_size: Movie={new_movie_size}, TV={new_tv_size}", 
                            module="background_tasks", function="refresh_queue_sizes")
                except Exception as e:
                    log_error("Queue Management", f"Error updating database queue_status.max_size: {e}", 
                             module="background_tasks", function="refresh_queue_sizes")
                    db.rollback()
                finally:
                    db.close()
            except Exception as e:
                log_error("Queue Management", f"Error syncing queue sizes with database: {e}", 
                         module="background_tasks", function="refresh_queue_sizes")

# Initialize queues for different types of requests
movie_queue_maxsize, tv_queue_maxsize = get_queue_sizes()
movie_queue = Queue(maxsize=movie_queue_maxsize)  # Queue for movie requests
tv_queue = Queue(maxsize=tv_queue_maxsize)     # Queue for TV show requests 
processing_task = None  # To track the current processing task

# Cancellation tracking system (simplified)
# Only track items currently being processed that need to be cancelled
cancellation_registry = {}  # Track items currently being processed that should be cancelled
# Format: {(tmdb_id, media_type): {'media_type': str, 'cancelled_at': datetime}}

# Timestamp tracking for queue activity
last_queue_activity_time = time.time()  # Track when queues were last non-empty

# Scheduler for background tasks
scheduler = AsyncIOScheduler()

# Browser access semaphore to prevent concurrent browser access
browser_semaphore = Semaphore(1)

# Global semaphore to ensure only one scheduled task runs at a time
scheduled_task_semaphore = Semaphore(1)

# Processing status flags
is_processing_queue = False
queue_processing_complete = asyncio.Event()

# Flag to track if library refresh has been done for current empty queue cycle
library_refreshed_for_current_cycle = False

# Configuration refresh tracking
last_config_refresh_time = 0
config_refresh_interval = 60  # Check for config changes every 60 seconds

async def check_config_changes():
    """Check for configuration changes and refresh if needed"""
    global last_config_refresh_time
    
    current_time = time.time()
    if current_time - last_config_refresh_time < config_refresh_interval:
        return
    
    last_config_refresh_time = current_time
    
    try:
        # Invalidate cache to force reload from database
        task_config.invalidate_cache()
        
        # Check if queue sizes have changed
        refresh_queue_sizes()
        
        # Check if any task configuration has changed by comparing with current scheduler state
        current_jobs = {job.id: job for job in scheduler.get_jobs()}
        
        # Check if we need to refresh scheduled tasks
        should_refresh = False
        
        # Check if scheduler is enabled
        if not task_config.get_config('scheduler_enabled', True):
            if current_jobs:
                should_refresh = True
        else:
            # Check if token refresh interval changed
            token_interval = float(task_config.get_config('token_refresh_interval_minutes', 10))
            if 'token_refresh' in current_jobs:
                if abs(current_jobs['token_refresh'].trigger.interval.total_seconds() / 60 - token_interval) > 0.1:
                    should_refresh = True
            elif task_config.get_config('scheduler_enabled', True):
                should_refresh = True
            
            # Check if movie processing check interval changed
            movie_interval = float(task_config.get_config('movie_processing_check_interval_minutes', 15))
            if 'movie_processing_checks' in current_jobs:
                if abs(current_jobs['movie_processing_checks'].trigger.interval.total_seconds() / 60 - movie_interval) > 0.1:
                    should_refresh = True
            elif task_config.get_config('enable_automatic_background_task', False):
                should_refresh = True
            
            # Check if movie requests recheck interval changed
            refresh_interval = float(task_config.get_config('refresh_interval_minutes', 60.0))
            if 'process_movie_requests' in current_jobs:
                if abs(current_jobs['process_movie_requests'].trigger.interval.total_seconds() / 60 - refresh_interval) > 0.1:
                    should_refresh = True
            elif task_config.get_config('background_tasks_enabled', True):
                should_refresh = True
        
        if should_refresh:
            log_info("Config Refresh", "Configuration changes detected, refreshing scheduled tasks", 
                    module="background_tasks", function="check_config_changes")
            await refresh_all_scheduled_tasks()
            
    except Exception as e:
        log_error("Config Refresh Error", f"Error checking configuration changes: {e}", 
                 module="background_tasks", function="check_config_changes")

async def refresh_all_scheduled_tasks():
    """Refresh all scheduled tasks based on current database configuration"""
    # Clear all existing jobs
    scheduler.remove_all_jobs()
    log_info("Scheduler", "Cleared all existing scheduled jobs", module="background_tasks", function="refresh_all_scheduled_tasks")
    
    # Check if scheduler is enabled
    if not task_config.get_config('scheduler_enabled', True):
        log_info("Scheduler", "Scheduler disabled. No tasks will be scheduled.", module="background_tasks", function="refresh_all_scheduled_tasks")
        return
    
    # Schedule token refresh
    schedule_token_refresh()
    
    # Schedule movie processing checks
    schedule_movie_processing_checks()
    
    # Schedule movie requests recheck
    await schedule_recheck_movie_requests()
    
    # Schedule failed item processing
    schedule_failed_item_processing()
    
    # Schedule periodic queue reconciliation (every 2 minutes to drain cleared items)
    scheduler.add_job(
        reconcile_queues_periodically,
        'interval',
        minutes=2,
        id='reconcile_queues_periodically',
        replace_existing=True
    )
    log_info("Scheduler", "Scheduled queue reconciliation every 2 minutes", module="background_tasks", function="refresh_all_scheduled_tasks")
    
    log_info("Scheduler", "Refreshed all scheduled tasks from database configuration", module="background_tasks", function="refresh_all_scheduled_tasks")

async def initialize_background_tasks():
    """Initialize background tasks and the queue processor."""
    global processing_task, last_queue_activity_time, is_processing_queue
    
    # Initialize the queue activity timestamp
    last_queue_activity_time = time.time()
    log_info("Queue Management", "Initialized queue activity timestamp", module="background_tasks", function="init_queue_activity_timestamp")
    
    # Initialize queue persistence
    from seerr.queue_persistence_manager import initialize_queue_persistence
    initialize_queue_persistence()
    
    # Refresh queue sizes from database BEFORE syncing queues
    # This ensures queues are properly sized before we try to add items
    refresh_queue_sizes()
    
    # Start the processing task BEFORE syncing queues
    # This ensures the consumer is running so items can be processed even if queue gets full
    if processing_task is None:
        processing_task = asyncio.create_task(process_queues())
        log_info("Queue Management", "Started queue processing task.", module="background_tasks", function="init_background_tasks")
        log_info("Queue Management", f"Processing task created: {processing_task}", module="background_tasks", function="init_background_tasks")
    else:
        log_info("Queue Management", f"Processing task already exists: {processing_task}", module="background_tasks", function="init_background_tasks")
    
    # Sync queues from database on startup (after processing task is started)
    await sync_queues_from_database()

    # Schedule all tasks based on database configuration
    await refresh_all_scheduled_tasks()
    
    # On first boot, immediately check for stuck items
    await check_stuck_items_on_startup()
    
    # On first boot, immediately check for failed items
    from seerr.failed_item_manager import process_failed_items
    log_info("Failed Item Processing", "Checking failed items on startup...", module="background_tasks", function="init_background_tasks")
    retry_count = await process_failed_items()
    log_info("Failed Item Processing", f"Startup check: Processed {retry_count} failed items", module="background_tasks", function="init_background_tasks")
    
    scheduler.start()

def type_slowly(driver, element, text, trigger_enter=False):
    """
    Simulate human-like typing into an element with varying delays.
    Uses chained actions for clearing and typing to maintain focus.
    """
    actions = ActionChains(driver)
    actions.click(element)  # Focus
    actions.key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL)  # Select all
    actions.send_keys(Keys.DELETE)  # Clear selected text
    
    for char in text:
        actions.send_keys(char)
        delay = random.uniform(0.001, 0.002)  # Tighter range: 20–80ms per character
        actions.pause(delay)
    
    if trigger_enter:
        actions.send_keys(Keys.ENTER)  # Optional: Force submit if needed
    
    actions.perform()

def schedule_token_refresh():
    """Schedule the token refresh based on database configuration."""
    from seerr.realdebrid import check_and_refresh_access_token
    
    # Check if scheduler is enabled
    if not task_config.get_config('scheduler_enabled', True):
        log_info("Token Management", "Scheduler disabled. Skipping token refresh scheduling.", module="background_tasks", function="schedule_token_refresh")
        return
    
    interval = int(task_config.get_config('token_refresh_interval_minutes', 10))
    scheduler.add_job(check_and_refresh_access_token, 'interval', minutes=interval)
    log_info("Token Management", f"Scheduled token refresh every {interval} minutes.", module="background_tasks", function="schedule_token_refresh")

def schedule_movie_processing_checks():
    """Schedule movie processing checks based on database configuration."""
    # Check if background tasks and scheduler are enabled
    if not task_config.get_config('background_tasks_enabled', True) or not task_config.get_config('scheduler_enabled', True):
        log_info("Movie Processing", "Background tasks or scheduler disabled. Skipping movie processing checks.", module="background_tasks", function="schedule_movie_processing_checks")
        return
    
    if task_config.get_config('enable_automatic_background_task', False):
        interval = int(task_config.get_config('movie_processing_check_interval_minutes', 15))
        scheduler.add_job(
            add_movie_processing_check_to_queue,
            'interval',
            minutes=interval,
            id="movie_processing_checks",
            replace_existing=True,
            max_instances=1
        )
        log_info("Movie Processing", f"Scheduled movie processing checks every {interval} minutes.", module="background_tasks", function="schedule_movie_processing_checks")
    else:
        log_info("Movie Processing", "Movie processing checks disabled (enable_automatic_background_task=False).", module="background_tasks", function="schedule_movie_processing_checks")

def schedule_failed_item_processing():
    """Schedule failed item processing based on database configuration."""
    # Check if background tasks and scheduler are enabled
    if not task_config.get_config('background_tasks_enabled', True) or not task_config.get_config('scheduler_enabled', True):
        log_info("Failed Item Processing", "Background tasks or scheduler disabled. Skipping failed item processing.", module="background_tasks", function="schedule_failed_item_processing")
        return
    
    # Check if failed item processing is enabled
    if not task_config.get_config('enable_failed_item_retry', True):
        log_info("Failed Item Processing", "Failed item retry disabled.", module="background_tasks", function="schedule_failed_item_processing")
        return
    
    interval = int(task_config.get_config('failed_item_retry_interval_minutes', 30))
    scheduler.add_job(
        add_failed_item_processing_to_queue,
        'interval',
        minutes=interval,
        id="failed_item_processing",
        replace_existing=True,
        max_instances=1
    )
    log_info("Failed Item Processing", f"Scheduled failed item processing every {interval} minutes.", module="background_tasks", function="schedule_failed_item_processing")

async def add_failed_item_processing_to_queue():
    """Add failed item processing task to the queue"""
    try:
        # Add a special task to process failed items
        await movie_queue.put(("failed_item_processing",))
        log_info("Failed Item Processing", "Added failed item processing task to queue", module="background_tasks", function="add_failed_item_processing_to_queue")
    except Exception as e:
        log_error("Failed Item Processing", f"Error adding failed item processing to queue: {e}", module="background_tasks", function="add_failed_item_processing_to_queue")

async def schedule_recheck_movie_requests():
    """Schedule or reschedule the movie requests recheck job, replacing any existing job."""
    # Check if background tasks and scheduler are enabled
    if not task_config.get_config('background_tasks_enabled', True) or not task_config.get_config('scheduler_enabled', True):
        log_info("Scheduler", "Background tasks or scheduler disabled. Skipping movie requests recheck scheduling.", module="background_tasks", function="schedule_recheck_movie_requests")
        return
    
    # Get interval from database configuration
    refresh_interval = float(task_config.get_config('refresh_interval_minutes', 60.0))
    min_interval = 1.0  # Minimum interval in minutes
    
    if refresh_interval < min_interval:
        log_warning("Configuration Warning", f"refresh_interval_minutes ({refresh_interval}) is too small. Using minimum interval of {min_interval} minutes.", module="background_tasks", function="schedule_movie_requests_recheck")
        interval = min_interval
    else:
        interval = refresh_interval

    try:
        # Remove all existing jobs with the same ID
        for job in scheduler.get_jobs():
            if job.id == "process_movie_requests":
                scheduler.remove_job(job.id)
                log_info("Scheduler", "Removed existing job with ID: process_movie_requests", module="background_tasks", function="schedule_movie_requests_recheck")

        # Schedule the new job with a unique ID
        scheduler.add_job(
            scheduled_task_wrapper,
            'interval',
            minutes=interval,
            id="process_movie_requests",
            replace_existing=True,
            max_instances=1  # Explicitly set to avoid unexpected concurrency
        )
        log_info("Scheduler", f"Scheduled rechecking movie requests every {interval} minute(s).", module="background_tasks", function="schedule_movie_requests_recheck")
    except Exception as e:
        log_error("Scheduler Error", f"Error scheduling movie requests recheck: {e}", module="background_tasks", function="schedule_movie_requests_recheck")

async def scheduled_task_wrapper():
    """Wrapper to ensure only one scheduled task runs at a time and waits for queue completion."""
    async with scheduled_task_semaphore:
        log_info("Scheduled Task", "Starting scheduled task - waiting for queue processing to complete", module="background_tasks", function="scheduled_task")
        
        # Wait for any ongoing queue processing to complete
        if is_processing_queue:
            await queue_processing_complete.wait()
        
        try:
            # First populate from Overseerr requests
            await populate_queues_from_overseerr()
            
            # Then populate from unified_media processing items
            await populate_queues_from_unified_media()
        except Exception as e:
            log_error("Scheduled Task Error", f"Error in scheduled task: {e}", module="background_tasks", function="scheduled_task")

### Function to process requests from the queues
async def process_queues():
    """Process requests from movie queue first, then TV queue."""
    global is_processing_queue, library_refreshed_for_current_cycle
    
    while True:
        try:
            # Check if there are any items in either queue
            if movie_queue.empty() and tv_queue.empty():
                # Set processing flag to false when no items to process
                is_processing_queue = False
                queue_processing_complete.set()
                
                # Run library refresh immediately if not already done for this cycle
                if not library_refreshed_for_current_cycle:
                    # Check if it's safe to refresh before attempting
                    if is_safe_to_refresh_library_stats(min_idle_seconds=30):
                        log_info("Library Refresh", "Queues are empty. Running library refresh now.", module="background_tasks", function="scheduled_task")
                        try:
                            from seerr.browser import refresh_library_stats
                            refresh_library_stats()
                            library_refreshed_for_current_cycle = True
                            log_info("Library Refresh", "Library refresh completed after queue completion.", module="background_tasks", function="scheduled_task")
                        except Exception as e:
                            log_error("Library Refresh Error", f"Error during library refresh: {e}", module="background_tasks", function="scheduled_task")
                    else:
                        log_info("Library Refresh", "Queues are empty but not safe to refresh yet. Skipping library refresh.", module="background_tasks", function="scheduled_task")
                
                # Check for configuration changes when queues are empty
                await check_config_changes()
                
                # Wait longer when queues are empty to avoid tight loop
                await asyncio.sleep(10)
                continue
            
            # Reset the refresh flag when queues become active again
            if library_refreshed_for_current_cycle:
                log_debug("Queue Management", "Queues became active again. Reset library refresh flag for next cycle.", module="background_tasks", function="scheduled_task")
                library_refreshed_for_current_cycle = False
            
            # Update activity timestamp when we have items to process
            update_queue_activity_timestamp()
            
            # Set processing flag and clear completion event when we have items
            is_processing_queue = True
            queue_processing_complete.clear()
            
            # Process all movies first (if any)
            if not movie_queue.empty():
                await process_movie_queue()
            
            # Then process all TV shows (if any)
            if not tv_queue.empty():
                await process_tv_queue()
            
            # Mark processing complete after this cycle
            is_processing_queue = False
            queue_processing_complete.set()
            
            # Short wait before checking queues again
            await asyncio.sleep(2)
            
        except Exception as e:
            log_error("Queue Processing Error", f"Error in process_queues: {e}", module="background_tasks", function="process_queues")
            is_processing_queue = False
            queue_processing_complete.set()
            await asyncio.sleep(5)

async def process_movie_queue():
    """Process all movies in the movie queue."""
    processed_count = 0
    
    while not movie_queue.empty():
        try:
            if processed_count == 0:  # Only log once when starting to process movies
                log_info("Queue Processing", "Processing movie queue...", module="background_tasks", function="process_queues")
            
            queue_item = await movie_queue.get()
            
            # Check if this is a special task (has string as first element)
            if isinstance(queue_item[0], str) and queue_item[0] == "movie_processing_check":
                # Check for stuck movies
                log_info("Movie Processing Check", "Processing movie processing check task", module="background_tasks", function="process_movie_queue")
                await check_movie_processing()
                movie_queue.task_done()
                
            elif isinstance(queue_item[0], str) and queue_item[0] == "failed_item_processing":
                # Process failed items
                log_info("Failed Item Processing", "Processing failed item retry task", module="background_tasks", function="process_movie_queue")
                from seerr.failed_item_manager import process_failed_items
                retry_count = await process_failed_items()
                log_info("Failed Item Processing", f"Processed {retry_count} failed items for retry", module="background_tasks", function="process_movie_queue")
                movie_queue.task_done()
                
            else:
                # Regular movie processing
                imdb_id, movie_title, media_type, extra_data, media_id, tmdb_id, request_id = queue_item
                task_done_called = False
                
                # Check if this item was cancelled/cleared before processing
                # Database is source of truth - if is_in_queue is False, item was cleared
                if USE_DATABASE:
                    from seerr.unified_media_manager import get_media_by_tmdb
                    from seerr.database_queue_manager import database_queue_manager
                    media_record = get_media_by_tmdb(tmdb_id, media_type)
                    if media_record:
                        # Check if item was cleared (is_in_queue = False AND status = 'failed' with 'cancelled' stage)
                        # This means the user cleared the queue while item was in in-memory queue
                        is_cleared = (not media_record.is_in_queue and 
                                     media_record.status == 'failed' and 
                                     media_record.processing_stage == 'cancelled')
                        
                        if is_cleared:
                            log_info("Queue Cancellation", f"Skipping cleared item from in-memory queue: {movie_title} (TMDB: {tmdb_id})", 
                                    module="background_tasks", function="process_movie_queue")
                            # Item was cleared, don't process it and don't set is_in_queue back to True
                            task_done_called = True
                            movie_queue.task_done()
                            continue
                        
                        # Item is valid - ensure is_in_queue is set to True (item is in queue since we just dequeued it)
                        if not media_record.is_in_queue:
                            database_queue_manager._update_queue_tracking(media_record, True)
                        
                        # Clear any stale cancellation tracking (item is active since we dequeued it)
                        cancellation_registry.pop((tmdb_id, media_type), None)
                        
                        # Check for recently cancelled items (race condition handling)
                        is_cancelled = False
                        if media_record.status == 'failed' and media_record.processing_stage == 'cancelled':
                            # Explicitly cancelled - check if it was cancelled very recently (within last 2 seconds)
                            # This handles race conditions where item was cancelled right before dequeuing
                            if media_record.last_checked_at:
                                time_since_update = (datetime.utcnow() - media_record.last_checked_at).total_seconds()
                                if time_since_update < 2:  # Cancelled within last 2 seconds
                                    is_cancelled = True
                                    log_info("Queue Cancellation", f"Item was cancelled very recently: {movie_title} (TMDB: {tmdb_id})", 
                                            module="background_tasks", function="process_movie_queue")
                        
                        if is_cancelled:
                            log_info("Queue Cancellation", f"Skipping cancelled item: {movie_title} (TMDB: {tmdb_id})", 
                                    module="background_tasks", function="process_movie_queue")
                            # Clear queue tracking
                            database_queue_manager._update_queue_tracking(media_record, False)
                            task_done_called = True
                            movie_queue.task_done()
                            continue
                    else:
                        # Media record doesn't exist yet - clear any stale cancellation tracking
                        cancellation_registry.pop((tmdb_id, media_type), None)
                
                processed_count += 1
                
                # Check if media is unreleased - skip processing if so
                if USE_DATABASE:
                    from seerr.unified_media_manager import get_media_by_tmdb
                    from seerr.database_queue_manager import database_queue_manager
                    # datetime is already imported at top of file
                    media_record = get_media_by_tmdb(tmdb_id, media_type)
                    if media_record and media_record.status == 'unreleased':
                        log_info("Movie Processing", f"Skipping unreleased movie {movie_title} (releases {media_record.released_date.strftime('%Y-%m-%d') if media_record.released_date else 'unknown'})", module="background_tasks", function="process_movie_queue")
                        # Clear queue tracking before removing from queue
                        database_queue_manager._update_queue_tracking(media_record, False)
                        task_done_called = True
                        movie_queue.task_done()
                        continue
                
                log_info("Movie Processing", f"Processing movie request #{processed_count} - IMDb ID: {imdb_id}, Title: {movie_title}", module="background_tasks", function="process_movie_queue")
                
                # Set processing stage when item starts processing
                if USE_DATABASE:
                    from seerr.unified_media_manager import get_media_by_tmdb, update_media_processing_status
                    media_record = get_media_by_tmdb(tmdb_id, media_type)
                    if media_record:
                        update_media_processing_status(
                            media_record.id,
                            'processing',
                            'browser_automation'
                        )
                        log_info("Queue Processing", f"Set processing stage to browser_automation for {movie_title}", module="background_tasks", function="process_movie_queue")
                
                # Check if browser driver is available
                from seerr.browser import driver as browser_driver
                if browser_driver is None:
                    log_warning("Browser Warning", "Browser driver not initialized. Attempting to initialize...", module="background_tasks", function="process_movie_queue")
                    from seerr.browser import initialize_browser
                    await initialize_browser()
                    from seerr.browser import driver as browser_driver
                    if browser_driver is None:
                        log_error("Browser Error", "Failed to initialize browser driver. Skipping request.", module="background_tasks", function="process_movie_queue")
                        # Clear queue tracking before removing from queue
                        if USE_DATABASE:
                            from seerr.unified_media_manager import get_media_by_tmdb
                            from seerr.database_queue_manager import database_queue_manager
                            media_record = get_media_by_tmdb(tmdb_id, media_type)
                            if media_record:
                                database_queue_manager._update_queue_tracking(media_record, False)
                        task_done_called = True
                        movie_queue.task_done()
                        continue
                
                try:
                    # Acquire browser semaphore for processing
                    async with browser_semaphore:
                        from seerr.search import search_on_debrid
                        log_info("Movie Processing", f"Calling search_on_debrid with imdb_id={imdb_id}, movie_title={movie_title}, media_type={media_type}, extra_data={extra_data}", module="background_tasks", function="process_movie_queue")
                        search_result = await asyncio.to_thread(search_on_debrid, imdb_id, movie_title, media_type, browser_driver, extra_data, tmdb_id)
                        
                        # Handle search result - if True, item completed successfully
                        if search_result == True:
                            if mark_completed(media_id, tmdb_id):
                                log_info("Overseerr Update", f"Marked {movie_title} ({media_id}) as completed in Overseerr", module="background_tasks", function="process_movie_queue")
                                
                                # Update database status to completed
                                if USE_DATABASE and request_id:
                                    from seerr.overseerr import update_media_request_status
                                    update_media_request_status(request_id, 'completed', completed_at=datetime.utcnow().isoformat())
                                
                                # Update unified_media table to completed status
                                if USE_DATABASE:
                                    from seerr.unified_media_manager import update_media_processing_status, get_media_by_tmdb
                                    
                                    # Find the media record by tmdb_id and media_type
                                    media_record = get_media_by_tmdb(tmdb_id, media_type)
                                    
                                    if media_record:
                                        update_media_processing_status(
                                            media_record.id,
                                            'completed',
                                            'movie_processing_complete',
                                            extra_data={'completed_at': datetime.utcnow().isoformat(), 'overseerr_media_id': media_id}
                                        )
                                        log_info("Media Update", f"Updated unified_media status to completed for {movie_title} (TMDB: {tmdb_id})", module="background_tasks", function="process_movie_queue")
                                    else:
                                        log_warning("Media Warning", f"No unified_media record found for {movie_title} (TMDB: {tmdb_id})", module="background_tasks", function="process_movie_queue")
                                
                                # Single success message for the entire process
                                log_success("Media Processing", f"Successfully processed and completed {movie_title} ({media_id})", module="background_tasks", function="process_movie_queue")
                            else:
                                log_error("Overseerr Error", f"Failed to mark media {media_id} as completed in Overseerr", module="background_tasks", function="process_movie_queue")
                        elif search_result == "cancelled":
                            log_info("Queue Cancellation", f"{movie_title} ({media_id}) was cancelled during search", module="background_tasks", function="process_movie_queue")
                            # Mark as failed and clear queue tracking
                            if USE_DATABASE:
                                from seerr.unified_media_manager import get_media_by_tmdb, update_media_processing_status
                                from seerr.database_queue_manager import database_queue_manager
                                media_record = get_media_by_tmdb(tmdb_id, media_type)
                                if media_record:
                                    update_media_processing_status(
                                        media_record.id,
                                        'failed',
                                        'cancelled',
                                        error_message="Cancelled by user"
                                    )
                                    # Clear queue tracking before removing from queue
                                    database_queue_manager._update_queue_tracking(media_record, False)
                            # Remove from registry
                            cancellation_registry.pop((tmdb_id, media_type), None)
                            task_done_called = True
                        elif search_result in ["already_processing", "already_completed", "already_available", "skipped"]:
                            log_info("Movie Processing", f"{movie_title} ({media_id}) was skipped - {search_result.replace('_', ' ')}. No action needed.", module="background_tasks", function="process_movie_queue")
                        else:
                            log_error("Movie Processing", f"{movie_title} ({media_id}) was not properly confirmed. Marking as failed.", module="background_tasks", function="process_movie_queue")
                            
                            # Update media status to failed when search fails
                            if USE_DATABASE:
                                from seerr.unified_media_manager import update_media_processing_status, get_media_by_tmdb
                                
                                # Find the media record by tmdb_id and media_type
                                media_record = get_media_by_tmdb(tmdb_id, media_type)
                                
                                if media_record:
                                    update_media_processing_status(
                                        media_record.id,
                                        'failed',
                                        'search_failed',
                                        error_message=f"Search failed for {movie_title} - no torrents found or processing timeout"
                                    )
                                    log_info("Media Update", f"Updated unified_media status to failed for {movie_title} (TMDB: {tmdb_id})", module="background_tasks", function="process_movie_queue")
                                else:
                                    log_warning("Media Warning", f"No unified_media record found for {movie_title} (TMDB: {tmdb_id})", module="background_tasks", function="process_movie_queue")
                            
                except Exception as ex:
                    log_critical("Movie Processing Error", f"Error processing movie request for IMDb ID {imdb_id}: {ex}", module="background_tasks", function="process_movie_queue")
                finally:
                    # Clear queue tracking when item is done processing (BEFORE task_done)
                    # This ensures database is updated before queue item is marked as done
                    # Only clear if item successfully completed or failed - don't clear if it was cancelled/removed
                    if USE_DATABASE and not task_done_called:
                        try:
                            from seerr.database_queue_manager import database_queue_manager
                            from seerr.unified_media_manager import get_media_by_tmdb
                            from seerr.queue_persistence_manager import queue_persistence_manager
                            media_record = get_media_by_tmdb(tmdb_id, media_type)
                            if media_record:
                                # Only clear queue tracking if item is actually done (completed or failed, not cancelled)
                                # If item was cancelled, queue tracking was already cleared above
                                if media_record.status in ['completed', 'failed']:
                                    database_queue_manager._update_queue_tracking(media_record, False)
                                # Update queue status from database (source of truth)
                                queue_persistence_manager.update_queue_status_from_database('movie', not movie_queue.empty())
                        except Exception as db_error:
                            log_error("Queue Database Update Error", f"Error updating database for {movie_title}: {db_error}", 
                                     module="background_tasks", function="process_movie_queue")
                    
                    # Only call task_done() if we haven't already called it
                    if not task_done_called:
                        movie_queue.task_done()
                
        except Exception as e:
            log_error("Movie Queue Error", f"Error processing movie from queue: {e}", module="background_tasks", function="process_movie_queue")
    
    if processed_count > 0:
        log_info("Movie Processing", f"Completed processing {processed_count} movie(s)", module="background_tasks", function="process_movie_queue")

async def process_tv_queue():
    """Process all TV shows in the TV queue."""
    processed_count = 0
    
    while not tv_queue.empty():
        try:
            if processed_count == 0:  # Only log once when starting to process TV items
                log_info("Queue Processing", "Processing TV queue...", module="background_tasks", function="process_queues")
            
            queue_item = await tv_queue.get()
            queue_type = queue_item[0]
            
            if queue_type == "tv_processing":
                # Regular TV show processing
                _, imdb_id, movie_title, media_type, extra_data, media_id, tmdb_id, request_id = queue_item
                task_done_called = False
                
                # Check if this item was cancelled/cleared before processing
                # Database is source of truth - if is_in_queue is False, item was cleared
                if USE_DATABASE:
                    from seerr.unified_media_manager import get_media_by_tmdb
                    from seerr.database_queue_manager import database_queue_manager
                    media_record = get_media_by_tmdb(tmdb_id, media_type)
                    if media_record:
                        # Check if item was cleared (is_in_queue = False AND status = 'failed' with 'cancelled' stage)
                        # This means the user cleared the queue while item was in in-memory queue
                        is_cleared = (not media_record.is_in_queue and 
                                     media_record.status == 'failed' and 
                                     media_record.processing_stage == 'cancelled')
                        
                        if is_cleared:
                            log_info("Queue Cancellation", f"Skipping cleared item from in-memory queue: {movie_title} (TMDB: {tmdb_id})", 
                                    module="background_tasks", function="process_tv_queue")
                            # Item was cleared, don't process it and don't set is_in_queue back to True
                            task_done_called = True
                            tv_queue.task_done()
                            continue
                        
                        # Item is valid - ensure is_in_queue is set to True (item is in queue since we just dequeued it)
                        if not media_record.is_in_queue:
                            database_queue_manager._update_queue_tracking(media_record, True)
                        
                        # Clear any stale cancellation tracking (item is active since we dequeued it)
                        cancellation_registry.pop((tmdb_id, media_type), None)
                        
                        # Check for recently cancelled items (race condition handling)
                        is_cancelled = False
                        if media_record.status == 'failed' and media_record.processing_stage == 'cancelled':
                            # Explicitly cancelled - check if it was cancelled very recently (within last 2 seconds)
                            # This handles race conditions where item was cancelled right before dequeuing
                            if media_record.last_checked_at:
                                time_since_update = (datetime.utcnow() - media_record.last_checked_at).total_seconds()
                                if time_since_update < 2:  # Cancelled within last 2 seconds
                                    is_cancelled = True
                                    log_info("Queue Cancellation", f"Item was cancelled very recently: {movie_title} (TMDB: {tmdb_id})", 
                                            module="background_tasks", function="process_tv_queue")
                        
                        if is_cancelled:
                            log_info("Queue Cancellation", f"Skipping cancelled item: {movie_title} (TMDB: {tmdb_id})", 
                                    module="background_tasks", function="process_tv_queue")
                            # Clear queue tracking
                            database_queue_manager._update_queue_tracking(media_record, False)
                            task_done_called = True
                            tv_queue.task_done()
                            continue
                        
                        if is_cancelled:
                            log_info("Queue Cancellation", f"Skipping cancelled item: {movie_title} (TMDB: {tmdb_id})", module="background_tasks", function="process_tv_queue")
                            # Clear queue tracking
                            database_queue_manager._update_queue_tracking(media_record, False)
                            task_done_called = True
                            tv_queue.task_done()
                            continue
                    else:
                        # Media record doesn't exist yet - clear any stale cancellation tracking
                        cancellation_registry.pop((tmdb_id, media_type), None)
                
                processed_count += 1
                
                log_info("TV Processing", f"Processing TV request #{processed_count} - IMDb ID: {imdb_id}, Title: {movie_title}", module="background_tasks", function="process_tv_queue")
                
                # Set processing stage when item starts processing
                if USE_DATABASE:
                    from seerr.unified_media_manager import get_media_by_tmdb, update_media_processing_status
                    media_record = get_media_by_tmdb(tmdb_id, media_type)
                    if media_record:
                        update_media_processing_status(
                            media_record.id,
                            'processing',
                            'browser_automation'
                        )
                        log_info("Queue Processing", f"Set processing stage to browser_automation for {movie_title}", module="background_tasks", function="process_tv_queue")
                
                from seerr.browser import driver as browser_driver
                if browser_driver is None:
                    log_warning("Browser Warning", "Browser driver not initialized. Attempting to initialize...", module="background_tasks", function="process_movie_queue")
                    from seerr.browser import initialize_browser
                    await initialize_browser()
                    from seerr.browser import driver as browser_driver
                    if browser_driver is None:
                        log_error("Browser Error", "Failed to initialize browser driver. Skipping request.", module="background_tasks", function="process_movie_queue")
                        # Clear queue tracking before removing from queue
                        if USE_DATABASE:
                            from seerr.unified_media_manager import get_media_by_tmdb
                            from seerr.database_queue_manager import database_queue_manager
                            media_record = get_media_by_tmdb(tmdb_id, media_type)
                            if media_record:
                                database_queue_manager._update_queue_tracking(media_record, False)
                        task_done_called = True
                        tv_queue.task_done()
                        continue
                
                try:
                    # Acquire browser semaphore for processing
                    async with browser_semaphore:
                        from seerr.search import search_on_debrid
                        search_result = await asyncio.to_thread(search_on_debrid, imdb_id, movie_title, media_type, browser_driver, extra_data, tmdb_id)
                        
                        # Handle search result - if True, item completed successfully
                        if search_result == True:
                            # Check if any seasons are discrepant before marking as available
                            should_mark_available = True
                            if USE_DATABASE:
                                from seerr.unified_media_manager import get_media_by_tmdb
                                media_record = get_media_by_tmdb(tmdb_id, media_type)
                                
                                if media_record and media_record.seasons_data:
                                    for season_data in media_record.seasons_data:
                                        if season_data.get('is_discrepant', False):
                                            should_mark_available = False
                                            log_info("TV Processing", f"Skipping marking {movie_title} as available due to discrepant seasons", module="background_tasks", function="process_tv_queue")
                                            break
                            
                            
                            # Only proceed with Overseerr marking if should_mark_available is True
                            if not should_mark_available:
                                # Discrepant seasons - episodes processed but not marking as available
                                log_info("TV Processing", f"Episodes processed for {movie_title} but not marking as available due to discrepant seasons", module="background_tasks", function="process_tv_queue")
                                # Skip the rest of the processing logic for this item
                                continue
                            
                            # Proceed with marking as available and updating database
                            if mark_completed(media_id, tmdb_id):
                                log_info("Overseerr Update", f"Marked {movie_title} ({media_id}) as completed in Overseerr", module="background_tasks", function="process_tv_queue")
                                
                                # Update database status to completed
                                if USE_DATABASE and request_id:
                                    from seerr.overseerr import update_media_request_status
                                    update_media_request_status(request_id, 'completed', completed_at=datetime.utcnow().isoformat())
                                
                                # Update unified_media table to completed status
                                if USE_DATABASE:
                                    from seerr.unified_media_manager import update_media_processing_status, get_media_by_tmdb
                                    
                                    # Find the media record by tmdb_id and media_type
                                    media_record = get_media_by_tmdb(tmdb_id, media_type)
                                    
                                    if media_record:
                                        # Update processing status
                                        update_media_processing_status(
                                            media_record.id,
                                            'completed',
                                            'tv_processing_complete',
                                            extra_data={'completed_at': datetime.utcnow().isoformat(), 'overseerr_media_id': media_id}
                                        )
                                        
                                        # For TV shows, update season completion status and set subscription
                                        if media_type == 'tv' and media_record.seasons_data:
                                            from seerr.enhanced_season_manager import EnhancedSeasonManager
                                            
                                            # Mark all seasons as completed
                                            seasons_data = media_record.seasons_data
                                            for season in seasons_data:
                                                if isinstance(season, dict):
                                                    season['status'] = 'completed'
                                                    season['updated_at'] = datetime.utcnow().isoformat()
                                            
                                            # Update the seasons data
                                            EnhancedSeasonManager.update_tv_show_seasons(tmdb_id, seasons_data, movie_title)
                                            log_info("Season Update", f"Marked all seasons as completed for {movie_title}", module="background_tasks", function="process_tv_queue")
                                            
                                            # Set subscription status for TV shows
                                            from seerr.unified_media_manager import update_media_details
                                            update_media_details(
                                                media_record.id,
                                                is_subscribed=True,
                                                subscription_active=True,
                                                subscription_last_checked=datetime.utcnow()
                                            )
                                            log_info("Subscription Update", f"Set subscription status for {movie_title}", module="background_tasks", function="process_tv_queue")
                                        
                                        log_info("Media Update", f"Updated unified_media status to completed for {movie_title} (TMDB: {tmdb_id})", module="background_tasks", function="process_tv_queue")
                                    else:
                                        log_warning("Media Warning", f"No unified_media record found for {movie_title} (TMDB: {tmdb_id})", module="background_tasks", function="process_tv_queue")
                                
                                # Single success message for the entire process
                                log_success("Media Processing", f"Successfully processed and completed {movie_title} ({media_id})", module="background_tasks", function="process_tv_queue")
                            else:
                                log_error("Overseerr Error", f"Failed to mark media {media_id} as completed in Overseerr", module="background_tasks", function="process_tv_queue")
                        elif search_result == "cancelled":
                            log_info("Queue Cancellation", f"{movie_title} ({media_id}) was cancelled during search", module="background_tasks", function="process_tv_queue")
                            # Mark as failed and clear queue tracking
                            if USE_DATABASE:
                                from seerr.unified_media_manager import get_media_by_tmdb, update_media_processing_status
                                from seerr.database_queue_manager import database_queue_manager
                                media_record = get_media_by_tmdb(tmdb_id, media_type)
                                if media_record:
                                    update_media_processing_status(
                                        media_record.id,
                                        'failed',
                                        'cancelled',
                                        error_message="Cancelled by user"
                                    )
                                    # Clear queue tracking before removing from queue
                                    database_queue_manager._update_queue_tracking(media_record, False)
                            # Remove from registry
                            cancellation_registry.pop((tmdb_id, media_type), None)
                            task_done_called = True
                        elif search_result in ["already_processing", "already_completed", "already_available", "skipped"]:
                            log_info("TV Processing", f"{movie_title} ({media_id}) was skipped - {search_result.replace('_', ' ')}. No action needed.", module="background_tasks", function="process_tv_queue")
                        else:
                            log_error("TV Processing", f"{movie_title} ({media_id}) was not properly confirmed. Marking as failed.", module="background_tasks", function="process_tv_queue")
                            
                            # Update media status to failed when search fails
                            if USE_DATABASE:
                                from seerr.unified_media_manager import update_media_processing_status, get_media_by_tmdb
                                
                                # Find the media record by tmdb_id and media_type
                                media_record = get_media_by_tmdb(tmdb_id, media_type)
                                
                                if media_record:
                                    update_media_processing_status(
                                        media_record.id,
                                        'failed',
                                        'search_failed',
                                        error_message=f"Search failed for {movie_title} - no torrents found or processing timeout"
                                    )
                                    log_info("Media Update", f"Updated unified_media status to failed for {movie_title} (TMDB: {tmdb_id})", module="background_tasks", function="process_tv_queue")
                                else:
                                    log_warning("Media Warning", f"No unified_media record found for {movie_title} (TMDB: {tmdb_id})", module="background_tasks", function="process_tv_queue")
                            
                except Exception as ex:
                    log_critical("TV Processing Error", f"Error processing TV request for IMDb ID {imdb_id}: {ex}", module="background_tasks", function="process_tv_queue")
                finally:
                    # Remove from cancellation registry
                    cancellation_registry.pop((tmdb_id, media_type), None)
                    
                    # Clear queue tracking when item is done processing (BEFORE task_done)
                    # This ensures database is updated before queue item is marked as done
                    if USE_DATABASE:
                        try:
                            from seerr.database_queue_manager import database_queue_manager
                            from seerr.unified_media_manager import get_media_by_tmdb
                            from seerr.queue_persistence_manager import queue_persistence_manager
                            media_record = get_media_by_tmdb(tmdb_id, media_type)
                            if media_record:
                                database_queue_manager._update_queue_tracking(media_record, False)
                                # Update queue status from database (source of truth)
                                queue_persistence_manager.update_queue_status_from_database('tv', not tv_queue.empty())
                        except Exception as db_error:
                            log_error("Queue Database Update Error", f"Error updating database for {movie_title}: {db_error}", 
                                     module="background_tasks", function="process_tv_queue")
                    
                    # Only call task_done() if we haven't already called it
                    if not task_done_called:
                        tv_queue.task_done()
                    
            elif queue_type == "subscription_check":
                # Check show subscriptions
                log_info("Subscription Check", "Processing subscription check task", module="background_tasks", function="process_tv_queue")
                await check_show_subscriptions()
                tv_queue.task_done()
                
        except Exception as e:
            log_error("TV Queue Error", f"Error processing TV item from queue: {e}", module="background_tasks", function="process_tv_queue")
    
    if processed_count > 0:
        log_info("TV Processing", f"Completed processing {processed_count} TV show(s)", module="background_tasks", function="process_tv_queue")

### Function to add requests to the appropriate queue
async def add_movie_to_queue(imdb_id, movie_title, media_type, extra_data, media_id, tmdb_id, request_id=None):
    """Add a movie request to the movie queue."""
    if movie_queue.full():
        movie_size = task_config.get_config('movie_queue_maxsize', 250)
        log_warning("Queue Warning", f"Movie queue is full (maxsize={movie_size}). Cannot add request for IMDb ID: {imdb_id}", module="background_tasks", function="add_movie_to_queue")
        return False
    
    # Clear any stale cancellation tracking FIRST (before checking database)
    # This ensures new items aren't blocked by stale cancellation flags
    cancellation_registry.pop((tmdb_id, media_type), None)
    
    # Update database FIRST to ensure 1:1 synchronization
    if USE_DATABASE:
        from seerr.unified_media_manager import get_media_by_tmdb
        from seerr.database_queue_manager import database_queue_manager
        # datetime is already imported at top of file
        
        media_record = get_media_by_tmdb(tmdb_id, media_type)
        if media_record:
            # Set is_in_queue flag in database before adding to in-memory queue
            database_queue_manager._update_queue_tracking(media_record, True)
            log_info("Queue Management", f"Set is_in_queue=True in database for {movie_title} (TMDB: {tmdb_id})", module="background_tasks", function="add_movie_to_queue")
        else:
            log_warning("Queue Warning", f"Media record not found for {movie_title} (TMDB: {tmdb_id}), adding to queue anyway", module="background_tasks", function="add_movie_to_queue")
    
    # Add to in-memory queue
    await movie_queue.put((imdb_id, movie_title, media_type, extra_data, media_id, tmdb_id, request_id))
    update_queue_activity_timestamp()  # Update timestamp when item is added
    
    # Update queue persistence (will calculate from database)
    from seerr.queue_persistence_manager import queue_persistence_manager
    queue_persistence_manager.update_queue_status_from_database('movie')
    
    log_info("Queue Management", f"Added movie to queue for IMDb ID: {imdb_id}, Title: {movie_title}", module="background_tasks", function="add_movie_to_queue")
    return True

async def sync_queues_from_database():
    """Sync in-memory queues with database queue status on startup"""
    try:
        from seerr.queue_persistence_manager import queue_persistence_manager
        
        log_info("Queue Sync", "Syncing queues from database on startup", 
                module="background_tasks", function="sync_queues_from_database")
        
        # Use reconciliation to ensure queues match database exactly
        movie_result = queue_persistence_manager.reconcile_queue_from_database('movie', movie_queue)
        tv_result = queue_persistence_manager.reconcile_queue_from_database('tv', tv_queue)
        
        # Update queue status from database (source of truth)
        queue_persistence_manager.update_queue_status_from_database('movie', False)
        queue_persistence_manager.update_queue_status_from_database('tv', False)
        
        log_success("Queue Sync", 
                   f"Synced queues from database: Movie (added {movie_result.get('added_to_memory', 0)}, removed {movie_result.get('removed_from_memory', 0)}), "
                   f"TV (added {tv_result.get('added_to_memory', 0)}, removed {tv_result.get('removed_from_memory', 0)})", 
                   module="background_tasks", function="sync_queues_from_database")
        
    except Exception as e:
        log_error("Queue Sync", f"Error syncing queues from database: {e}", 
                 module="background_tasks", function="sync_queues_from_database")


async def reconcile_queues_periodically():
    """Periodically reconcile in-memory queues with database state"""
    try:
        from seerr.queue_persistence_manager import queue_persistence_manager
        
        # Validate queues first
        movie_validation = queue_persistence_manager.validate_queue_sync('movie', movie_queue)
        tv_validation = queue_persistence_manager.validate_queue_sync('tv', tv_queue)
        
        # Reconcile if there are discrepancies
        if not movie_validation.get('valid', True):
            log_info("Queue Reconciliation", f"Movie queue has discrepancies, reconciling...", 
                    module="background_tasks", function="reconcile_queues_periodically")
            queue_persistence_manager.reconcile_queue_from_database('movie', movie_queue)
        
        if not tv_validation.get('valid', True):
            log_info("Queue Reconciliation", f"TV queue has discrepancies, reconciling...", 
                    module="background_tasks", function="reconcile_queues_periodically")
            queue_persistence_manager.reconcile_queue_from_database('tv', tv_queue)
        
        # Drain cleared items from in-memory queues (items that were cleared via UI)
        drain_cleared_items_from_queues()
        
    except Exception as e:
        log_error("Queue Reconciliation", f"Error in periodic queue reconciliation: {e}", 
                 module="background_tasks", function="reconcile_queues_periodically")

def drain_cleared_items_from_queues():
    """
    Drain items from in-memory queues that were cleared in the database.
    This handles the case where UI clears queue but in-memory queues still have items.
    """
    if not USE_DATABASE:
        return
    
    try:
        from seerr.database import get_db
        from seerr.unified_models import UnifiedMedia
        
        db = get_db()
        try:
            # Get all cleared items (is_in_queue=False, status='failed', processing_stage='cancelled')
            cleared_items = db.query(UnifiedMedia).filter(
                UnifiedMedia.is_in_queue == False,
                UnifiedMedia.status == 'failed',
                UnifiedMedia.processing_stage == 'cancelled'
            ).all()
            
            if not cleared_items:
                return
            
            # Build sets of cleared tmdb_ids by type
            cleared_movie_ids = {item.tmdb_id for item in cleared_items if item.media_type == 'movie' and item.tmdb_id}
            cleared_tv_ids = {item.tmdb_id for item in cleared_items if item.media_type == 'tv' and item.tmdb_id}
            
            global movie_queue, tv_queue
            drained_movie = 0
            drained_tv = 0
            
            # Drain movie queue
            if cleared_movie_ids:
                temp_items = []
                try:
                    while not movie_queue.empty():
                        item = movie_queue.get_nowait()
                        if isinstance(item, tuple) and len(item) >= 6:
                            if not isinstance(item[0], str):  # Regular item
                                item_tmdb_id = item[5] if len(item) > 5 else None
                                if item_tmdb_id in cleared_movie_ids:
                                    drained_movie += 1
                                    continue  # Skip this item
                        temp_items.append(item)
                except Exception:
                    pass
                
                # Put items back
                for item in temp_items:
                    try:
                        movie_queue.put_nowait(item)
                    except Exception:
                        pass
                
                if drained_movie > 0:
                    log_info("Queue Drain", f"Drained {drained_movie} cleared items from in-memory movie queue", 
                            module="background_tasks", function="drain_cleared_items_from_queues")
            
            # Drain TV queue
            if cleared_tv_ids:
                temp_items = []
                try:
                    while not tv_queue.empty():
                        item = tv_queue.get_nowait()
                        if isinstance(item, tuple) and len(item) >= 8:
                            if item[0] == "tv_processing":  # Regular TV item
                                item_tmdb_id = item[7] if len(item) > 7 else None
                                if item_tmdb_id in cleared_tv_ids:
                                    drained_tv += 1
                                    continue  # Skip this item
                        temp_items.append(item)
                except Exception:
                    pass
                
                # Put items back
                for item in temp_items:
                    try:
                        tv_queue.put_nowait(item)
                    except Exception:
                        pass
                
                if drained_tv > 0:
                    log_info("Queue Drain", f"Drained {drained_tv} cleared items from in-memory TV queue", 
                            module="background_tasks", function="drain_cleared_items_from_queues")
        
        finally:
            db.close()
    except Exception as e:
        log_warning("Queue Drain", f"Error draining cleared items from queues: {e}", 
                   module="background_tasks", function="drain_cleared_items_from_queues")

def skip_queue_item(tmdb_id: int, media_type: str) -> bool:
    """
    Skip a queue item by removing it from queue and updating database.
    Simplified approach: just remove from queue, no complex tracking.
    
    Args:
        tmdb_id (int): TMDB ID of the media
        media_type (str): Type of media ('movie' or 'tv')
        
    Returns:
        bool: True if item was removed from queue
    """
    try:
        if USE_DATABASE:
            from seerr.unified_media_manager import get_media_by_tmdb
            from seerr.database_queue_manager import database_queue_manager
            from seerr.unified_media_manager import update_media_processing_status
            
            media_record = get_media_by_tmdb(tmdb_id, media_type)
            if media_record and media_record.is_in_queue:
                # Mark as cancelled in database
                update_media_processing_status(
                    media_record.id,
                    'failed',
                    'cancelled',
                    error_message="Cancelled by user"
                )
                # Clear queue tracking
                database_queue_manager._update_queue_tracking(media_record, False)
                
                log_info("Queue Cancellation", f"Removed item from queue: TMDB {tmdb_id} ({media_type})", 
                        module="background_tasks", function="skip_queue_item")
                return True
            else:
                log_warning("Queue Cancellation", f"Item not found in queue: TMDB {tmdb_id} ({media_type})", 
                           module="background_tasks", function="skip_queue_item")
                return False
        return False
    except Exception as e:
        log_error("Queue Cancellation", f"Error removing item from queue: {e}", 
                 module="background_tasks", function="skip_queue_item")
        return False

def clear_queue(media_type: str = None) -> int:
    """
    Clear all items from queue by removing them and updating database.
    Also drains in-memory queues to prevent "secret" queue items.
    
    Args:
        media_type (str, optional): Type of media to clear ('movie', 'tv', or None for both)
        
    Returns:
        int: Number of items removed from queue
    """
    try:
        count = 0
        drained_movie_count = 0
        drained_tv_count = 0
        
        if USE_DATABASE:
            from seerr.database import get_db
            from seerr.unified_models import UnifiedMedia
            from seerr.unified_media_manager import update_media_processing_status
            from seerr.database_queue_manager import database_queue_manager
            
            db = get_db()
            try:
                # Get all queued items
                query = db.query(UnifiedMedia).filter(
                    UnifiedMedia.is_in_queue == True,
                    UnifiedMedia.status != 'completed',
                    UnifiedMedia.status != 'ignored'
                )
                
                if media_type:
                    query = query.filter(UnifiedMedia.media_type == media_type)
                
                queued_items = query.all()
                
                # Collect tmdb_ids to drain from in-memory queues
                movie_tmdb_ids = set()
                tv_tmdb_ids = set()
                
                for item in queued_items:
                    # Mark as failed in database
                    update_media_processing_status(
                        item.id,
                        'failed',
                        'cancelled',
                        error_message="Cancelled by user (queue cleared)"
                    )
                    
                    # Clear queue tracking
                    database_queue_manager._update_queue_tracking(item, False)
                    
                    # Track tmdb_ids for draining in-memory queues
                    if item.media_type == 'movie' and item.tmdb_id:
                        movie_tmdb_ids.add(item.tmdb_id)
                    elif item.media_type == 'tv' and item.tmdb_id:
                        tv_tmdb_ids.add(item.tmdb_id)
                    
                    count += 1
                
                log_info("Queue Cancellation", f"Cleared {count} items from database (type: {media_type or 'all'})", 
                        module="background_tasks", function="clear_queue")
            finally:
                db.close()
        
        # Drain in-memory queues - remove items that match cleared tmdb_ids
        global movie_queue, tv_queue
        
        if not media_type or media_type == 'movie':
            # Drain movie queue
            temp_items = []
            try:
                while not movie_queue.empty():
                    item = movie_queue.get_nowait()
                    # Check if this is a regular item (not a special task)
                    if isinstance(item, tuple) and len(item) >= 6:
                        if not isinstance(item[0], str):  # Regular item, not special task
                            item_tmdb_id = item[5] if len(item) > 5 else None
                            # Keep item only if it's not in the cleared list
                            if item_tmdb_id not in movie_tmdb_ids:
                                temp_items.append(item)
                            else:
                                drained_movie_count += 1
                        else:
                            # Special task, keep it
                            temp_items.append(item)
                    else:
                        # Unknown format, keep it
                        temp_items.append(item)
            except Exception as e:
                log_warning("Queue Cancellation", f"Error draining movie queue: {e}", 
                           module="background_tasks", function="clear_queue")
            
            # Put items back
            for item in temp_items:
                try:
                    movie_queue.put_nowait(item)
                except Exception:
                    pass  # Queue might be full, but we tried
            
            if drained_movie_count > 0:
                log_info("Queue Cancellation", f"Drained {drained_movie_count} items from in-memory movie queue", 
                        module="background_tasks", function="clear_queue")
        
        if not media_type or media_type == 'tv':
            # Drain TV queue
            temp_items = []
            try:
                while not tv_queue.empty():
                    item = tv_queue.get_nowait()
                    # Check if this is a regular item
                    if isinstance(item, tuple) and len(item) >= 8:
                        if item[0] == "tv_processing":  # Regular TV item
                            item_tmdb_id = item[7] if len(item) > 7 else None
                            # Keep item only if it's not in the cleared list
                            if item_tmdb_id not in tv_tmdb_ids:
                                temp_items.append(item)
                            else:
                                drained_tv_count += 1
                        else:
                            # Special task or other format, keep it
                            temp_items.append(item)
                    else:
                        # Unknown format, keep it
                        temp_items.append(item)
            except Exception as e:
                log_warning("Queue Cancellation", f"Error draining TV queue: {e}", 
                           module="background_tasks", function="clear_queue")
            
            # Put items back
            for item in temp_items:
                try:
                    tv_queue.put_nowait(item)
                except Exception:
                    pass  # Queue might be full, but we tried
            
            if drained_tv_count > 0:
                log_info("Queue Cancellation", f"Drained {drained_tv_count} items from in-memory TV queue", 
                        module="background_tasks", function="clear_queue")
        
        log_info("Queue Cancellation", f"Cleared {count} items total (type: {media_type or 'all'}, drained: {drained_movie_count} movies, {drained_tv_count} TV)", 
                module="background_tasks", function="clear_queue")
        
        return count
    except Exception as e:
        log_error("Queue Cancellation", f"Error clearing queue: {e}", 
                 module="background_tasks", function="clear_queue")
        return 0

async def add_tv_to_queue(imdb_id, movie_title, media_type, extra_data, media_id, tmdb_id, request_id=None):
    """Add a TV show request to the TV queue."""
    if tv_queue.full():
        tv_size = task_config.get_config('tv_queue_maxsize', 250)
        log_warning("Queue Warning", f"TV queue is full (maxsize={tv_size}). Cannot add request for IMDb ID: {imdb_id}", module="background_tasks", function="add_tv_to_queue")
        return False
    
    # Clear any stale cancellation tracking FIRST (before checking database)
    # This ensures new items aren't blocked by stale cancellation flags
    cancellation_registry.pop((tmdb_id, media_type), None)
    
    # Update database FIRST to ensure 1:1 synchronization
    if USE_DATABASE:
        from seerr.unified_media_manager import get_media_by_tmdb
        from seerr.database_queue_manager import database_queue_manager
        # datetime is already imported at top of file
        
        media_record = get_media_by_tmdb(tmdb_id, media_type)
        if media_record:
            # Set is_in_queue flag in database before adding to in-memory queue
            database_queue_manager._update_queue_tracking(media_record, True)
            log_info("Queue Management", f"Set is_in_queue=True in database for {movie_title} (TMDB: {tmdb_id})", module="background_tasks", function="add_tv_to_queue")
        else:
            log_warning("Queue Warning", f"Media record not found for {movie_title} (TMDB: {tmdb_id}), adding to queue anyway", module="background_tasks", function="add_tv_to_queue")
    
    # Add to in-memory queue
    await tv_queue.put(("tv_processing", imdb_id, movie_title, media_type, extra_data, media_id, tmdb_id, request_id))
    update_queue_activity_timestamp()  # Update timestamp when item is added
    
    # Update queue persistence (will calculate from database)
    from seerr.queue_persistence_manager import queue_persistence_manager
    queue_persistence_manager.update_queue_status_from_database('tv')
    
    log_info("Queue Management", f"Added TV show to queue for IMDb ID: {imdb_id}, Title: {movie_title}", module="background_tasks", function="add_tv_to_queue")
    return True

async def add_movie_processing_check_to_queue():
    """Add a movie processing check task to the movie queue."""
    if movie_queue.full():
        movie_size = task_config.get_config('movie_queue_maxsize', 250)
        log_warning("Queue Warning", f"Movie queue is full (maxsize={movie_size}). Cannot add movie processing check task.", module="background_tasks", function="add_movie_processing_check_to_queue")
        return False
    
    await movie_queue.put(("movie_processing_check",))
    update_queue_activity_timestamp()  # Update timestamp when item is added
    log_info("Queue Management", "Added movie processing check task to movie queue", module="background_tasks", function="add_movie_processing_check_to_queue")
    return True

async def add_subscription_check_to_queue():
    """Add a subscription check task to the TV queue."""
    if tv_queue.full():
        tv_size = task_config.get_config('tv_queue_maxsize', 250)
        log_warning("Queue Warning", f"TV queue is full (maxsize={tv_size}). Cannot add subscription check task.", module="background_tasks", function="add_subscription_check_to_queue")
        return False
    
    await tv_queue.put(("subscription_check",))
    update_queue_activity_timestamp()  # Update timestamp when item is added
    log_info("Queue Management", "Added subscription check task to TV queue", module="background_tasks", function="add_subscription_check_to_queue")
    return True

async def populate_queues_from_unified_media():
    """
    Populate queues from unified_media table for items in processing state
    This ensures that items added through the unavailable media processing are also queued for processing
    """
    if not USE_DATABASE:
        return
    
    log_info("Queue Population", "Populating queues from unified_media processing items...", module="background_tasks", function="populate_queues_from_unified_media")
    
    try:
        from seerr.unified_models import UnifiedMedia
        from seerr.unified_media_manager import get_media_by_tmdb
        
        db = get_db()
        try:
            # Get all media items that are in processing state
            processing_items = db.query(UnifiedMedia).filter(
                UnifiedMedia.status == 'processing',
                UnifiedMedia.processing_stage.in_(['queue_processing', 'browser_automation'])
            ).all()
            
            movies_added = 0
            tv_shows_added = 0
            
            for item in processing_items:
                try:
                    # Check if already in queue (basic check)
                    if item.media_type == 'movie':
                        # Add movie to queue
                        success = await add_movie_to_queue(
                            imdb_id=item.imdb_id or '',
                            movie_title=f"{item.title} ({item.year})",
                            media_type=item.media_type,
                            extra_data=item.extra_data or {},
                            media_id=item.overseerr_media_id or 0,
                            tmdb_id=item.tmdb_id,
                            request_id=item.overseerr_request_id
                        )
                        if success:
                            movies_added += 1
                            log_info("Queue Population", f"Added processing movie to queue: {item.title}", module="background_tasks", function="populate_queues_from_unified_media")
                    
                    elif item.media_type == 'tv':
                        # Check if this TV show actually has seasons that need processing
                        seasons_need_processing = []
                        
                        if item.seasons_data:
                            import json
                            if isinstance(item.seasons_data, str):
                                seasons_data = json.loads(item.seasons_data)
                            else:
                                seasons_data = item.seasons_data
                            
                            for season in seasons_data:
                                season_number = season.get('season_number')
                                season_status = season.get('status')
                                
                                # Only process seasons that are not completed and not "not_aired"
                                if season_status not in ['completed', 'not_aired']:
                                    seasons_need_processing.append(season_number)
                        
                        # Only add to queue if there are seasons that actually need processing
                        if seasons_need_processing:
                            # Prepare extra_data with only the seasons that need processing
                            extra_data = item.extra_data or {}
                            if isinstance(extra_data, str):
                                try:
                                    extra_data = json.loads(extra_data)
                                except (json.JSONDecodeError, TypeError):
                                    extra_data = {}
                            
                            extra_data['requested_seasons'] = seasons_need_processing
                            
                            success = await add_tv_to_queue(
                                imdb_id=item.imdb_id or '',
                                movie_title=f"{item.title} ({item.year})",
                                media_type=item.media_type,
                                extra_data=extra_data,
                                media_id=item.overseerr_media_id or 0,
                                tmdb_id=item.tmdb_id,
                                request_id=item.overseerr_request_id
                            )
                            if success:
                                tv_shows_added += 1
                                log_info("Queue Population", f"Added processing TV show to queue: {item.title} for seasons {seasons_need_processing}", module="background_tasks", function="populate_queues_from_unified_media")
                        else:
                            log_info("Queue Population", f"TV show {item.title} has no seasons that need processing. Skipping queue addition.", module="background_tasks", function="populate_queues_from_unified_media")
                            
                            # If no seasons need processing, mark as completed
                            from seerr.unified_media_manager import update_media_processing_status
                            update_media_processing_status(
                                item.id,
                                'completed',
                                'queue_population_completed',
                                extra_data={'queue_population_completed_at': datetime.utcnow().isoformat()}
                            )
                            log_info("Queue Population", f"Marked TV show {item.title} as completed (no seasons need processing)", module="background_tasks", function="populate_queues_from_unified_media")
                
                except Exception as e:
                    log_error("Queue Population Error", f"Error adding {item.title} to queue: {e}", module="background_tasks", function="populate_queues_from_unified_media")
                    continue
            
            if movies_added > 0 or tv_shows_added > 0:
                log_success("Queue Population", f"Added {movies_added} movies and {tv_shows_added} TV shows from unified_media to queues", module="background_tasks", function="populate_queues_from_unified_media")
            else:
                log_info("Queue Population", "No processing items found in unified_media", module="background_tasks", function="populate_queues_from_unified_media")
        
        finally:
            db.close()
    
    except Exception as e:
        log_error("Queue Population Error", f"Error populating queues from unified_media: {e}", module="background_tasks", function="populate_queues_from_unified_media")

async def process_unavailable_tv_show(first_request: dict, all_requests_for_media: list):
    """
    Process a TV show that is unavailable/available but not in our database
    Add it to the database and begin processing
    """
    try:
        from seerr.unified_media_manager import start_media_processing
        from seerr.trakt import get_media_details_from_trakt
        
        # Extract basic info from the first request
        media = first_request['media']
        tmdb_id = media['tmdbId']
        media_type = media['mediaType']
        
        # Note: Overseerr media object doesn't have title/year, we'll get them from Trakt
        title = 'Unknown Title'  # Will be updated from Trakt API
        year = 0  # Will be updated from Trakt API
        
        log_info("Unavailable TV Processing", f"Processing unavailable TV show: {title} ({year}) - TMDB ID: {tmdb_id}", module="background_tasks", function="process_unavailable_tv_show")
        
        # Get Trakt details
        trakt_details = get_media_details_from_trakt(tmdb_id, media_type)
        if not trakt_details:
            log_warning("Unavailable TV Processing", f"Could not fetch Trakt details for TMDB ID {tmdb_id}, skipping", module="background_tasks", function="process_unavailable_tv_show")
            return
        
        # Update title and year from Trakt details
        title = trakt_details.get('title', 'Unknown Title')
        year = trakt_details.get('year', 0)
        
        log_info("Unavailable TV Processing", f"Updated details from Trakt: {title} ({year})", module="background_tasks", function="process_unavailable_tv_show")
        
        # Extract season information from all requests
        requested_seasons = []
        for request in all_requests_for_media:
            if 'seasons' in request and request['seasons']:
                for season in request['seasons']:
                    season_name = season.get('seasonName', '')
                    if season_name and season_name not in requested_seasons:
                        requested_seasons.append(season_name)
        
        # Prepare extra data with season information
        extra_data = {
            'requested_seasons': requested_seasons,
            'overseerr_media_id': media['id'],
            'overseerr_requests': [req['id'] for req in all_requests_for_media],
            'overview': trakt_details.get('overview', '')
        }
        
        # Start media processing
        success = start_media_processing(
            tmdb_id=tmdb_id,
            imdb_id=trakt_details.get('imdb_id'),
            trakt_id=trakt_details.get('trakt_id'),
            media_type=media_type,
            title=title,
            year=year,
            overseerr_request_id=first_request['id'],
            overseerr_media_id=media['id'],
            extra_data=extra_data
        )
        
        if success:
            log_success("Unavailable TV Processing", f"Successfully added and started processing {title}", module="background_tasks", function="process_unavailable_tv_show")
        else:
            log_error("Unavailable TV Processing", f"Failed to add {title} to database", module="background_tasks", function="process_unavailable_tv_show")
            
    except Exception as e:
        # Get title from the request if available, otherwise use a fallback
        try:
            error_title = first_request['media']['title'] if 'media' in first_request else "Unknown TV Show"
        except:
            error_title = "Unknown TV Show"
        log_error("Unavailable TV Processing Error", f"Error processing unavailable TV show {error_title}: {e}", module="background_tasks", function="process_unavailable_tv_show")

async def process_unavailable_movie(first_request: dict):
    """
    Process a movie that is unavailable/available but not in our database
    Add it to the database and begin processing
    """
    try:
        from seerr.unified_media_manager import start_media_processing
        from seerr.trakt import get_media_details_from_trakt
        
        # Extract basic info from the request
        media = first_request['media']
        tmdb_id = media['tmdbId']
        media_type = media['mediaType']
        
        # Note: Overseerr media object doesn't have title/year, we'll get them from Trakt
        title = 'Unknown Title'  # Will be updated from Trakt API
        year = 0  # Will be updated from Trakt API
        
        log_info("Unavailable Movie Processing", f"Processing unavailable movie: {title} ({year}) - TMDB ID: {tmdb_id}", module="background_tasks", function="process_unavailable_movie")
        
        # Get Trakt details
        trakt_details = get_media_details_from_trakt(tmdb_id, media_type)
        if not trakt_details:
            log_warning("Unavailable Movie Processing", f"Could not fetch Trakt details for TMDB ID {tmdb_id}, skipping", module="background_tasks", function="process_unavailable_movie")
            return
        
        # Update title and year from Trakt details
        title = trakt_details.get('title', 'Unknown Title')
        year = trakt_details.get('year', 0)
        
        log_info("Unavailable Movie Processing", f"Updated details from Trakt: {title} ({year})", module="background_tasks", function="process_unavailable_movie")
        
        # Prepare extra data
        extra_data = {
            'overseerr_media_id': media['id'],
            'overseerr_request_id': first_request['id'],
            'overview': trakt_details.get('overview', '')
        }
        
        # Start media processing
        success = start_media_processing(
            tmdb_id=tmdb_id,
            imdb_id=trakt_details.get('imdb_id'),
            trakt_id=trakt_details.get('trakt_id'),
            media_type=media_type,
            title=title,
            year=year,
            overseerr_request_id=first_request['id'],
            overseerr_media_id=media['id'],
            extra_data=extra_data,
            media_details=trakt_details
        )
        
        if success:
            log_success("Unavailable Movie Processing", f"Successfully added and started processing {title}", module="background_tasks", function="process_unavailable_movie")
        else:
            log_error("Unavailable Movie Processing", f"Failed to add {title} to database", module="background_tasks", function="process_unavailable_movie")
            
    except Exception as e:
        # Get title from the request if available, otherwise use a fallback
        try:
            error_title = first_request['media']['title'] if 'media' in first_request else "Unknown Movie"
        except:
            error_title = "Unknown Movie"
        log_error("Unavailable Movie Processing Error", f"Error processing unavailable movie {error_title}: {e}", module="background_tasks", function="process_unavailable_movie")

async def sync_all_requests_to_database():
    """
    Sync all Overseerr requests to the database for tracking
    """
    if not USE_DATABASE:
        return
    
    log_info("Database Sync", "Syncing all Overseerr requests to database...", module="background_tasks", function="sync_all_requests_to_database")
    
    try:
        # Get processing requests (original logic)
        processing_requests = get_overseerr_media_requests()
        if not processing_requests:
            log_info("Database Sync", "No processing requests found in Overseerr", module="background_tasks", function="sync_all_requests_to_database")
        else:
            log_info("Database Sync", f"Found {len(processing_requests)} processing requests", module="background_tasks", function="sync_all_requests_to_database")
        
        # Also check for TV shows with available/unavailable status that might need season updates
        from seerr.config import OVERSEERR_API_BASE_URL, OVERSEERR_API_KEY
        import requests
        from seerr.overseerr import get_all_overseerr_requests_for_media
        from seerr.unified_media_manager import update_tv_show_season_count_comprehensive
        
        # Get overseerr_media_ids from the unified media table instead of from Overseerr API
        tv_media_ids_to_check = set()
        try:
            from seerr.unified_models import UnifiedMedia
            db = get_db()
            try:
                # Get all media items that have overseerr_media_id set
                media_items = db.query(UnifiedMedia).filter(
                    UnifiedMedia.overseerr_media_id.isnot(None),
                    UnifiedMedia.overseerr_media_id != 0
                ).all()
                
                for media_item in media_items:
                    tv_media_ids_to_check.add(media_item.overseerr_media_id)
                
                if tv_media_ids_to_check:
                    # Limit to first 10 media items to avoid excessive API calls
                    tv_media_ids_to_check = list(tv_media_ids_to_check)[:10]
                    log_info("Database Sync", f"Found {len(tv_media_ids_to_check)} media items with overseerr_media_id that may need processing", module="background_tasks", function="sync_all_requests_to_database")
                else:
                    log_info("Database Sync", "No media items with overseerr_media_id found in database", module="background_tasks", function="sync_all_requests_to_database")
            finally:
                db.close()
        except Exception as e:
            log_error("Database Sync Error", f"Error querying unified media table: {e}", module="background_tasks", function="sync_all_requests_to_database")
        
        # Process TV shows that need season updates (only if they exist in database)
        if tv_media_ids_to_check:
            from seerr.unified_media_manager import get_media_by_tmdb
            import time
            
            for i, media_id in enumerate(tv_media_ids_to_check):
                # Add small delay between API calls to respect rate limits
                if i > 0:
                    time.sleep(0.1)  # 100ms delay between calls
                try:
                    # Get all requests for this media ID to check seasons
                    all_requests_for_media = get_all_overseerr_requests_for_media(media_id)
                    if not all_requests_for_media:
                        continue
                    
                    # Get media details from the first request
                    first_request = all_requests_for_media[0]
                    tmdb_id = first_request['media']['tmdbId']
                    media_type = first_request['media']['mediaType']
                    
                    # Check if this media already exists in our database
                    existing_media = get_media_by_tmdb(tmdb_id, media_type)
                    if not existing_media:
                        # Media not in database - add it and begin processing
                        log_info("Database Sync", f"{media_type.title()} with TMDB ID {tmdb_id} not found in database, adding and beginning processing", module="background_tasks", function="sync_all_requests_to_database")
                        
                        # Process this media by adding it to the database and queues
                        if media_type == 'tv':
                            await process_unavailable_tv_show(first_request, all_requests_for_media)
                        else:  # movie
                            await process_unavailable_movie(first_request)
                        continue
                    
                    # Only update season count for TV shows
                    if media_type == 'tv':
                        log_info("Database Sync", f"Checking season count for TV show: {existing_media.title} (Media ID: {media_id})", module="background_tasks", function="sync_all_requests_to_database")
                        
                        update_success = update_tv_show_season_count_comprehensive(
                            overseerr_media_id=media_id,
                            tmdb_id=tmdb_id,
                            title=existing_media.title
                        )
                        
                        if update_success:
                            log_success("Database Sync", f"Season count updated for {existing_media.title}", module="background_tasks", function="sync_all_requests_to_database")
                        else:
                            log_warning("Database Sync Warning", f"Failed to update season count for {existing_media.title}", module="background_tasks", function="sync_all_requests_to_database")
                    else:
                        log_info("Database Sync", f"Movie {existing_media.title} already exists in database, no action needed", module="background_tasks", function="sync_all_requests_to_database")
                        
                except Exception as e:
                    log_error("Database Sync Error", f"Error processing media ID {media_id}: {e}", module="background_tasks", function="sync_all_requests_to_database")
                    continue
        
        # Use enhanced sync manager for processing requests
        if processing_requests:
            from seerr.enhanced_sync_manager import enhanced_sync_all_requests
            await enhanced_sync_all_requests()
        else:
            log_info("Database Sync", "No processing requests to sync", module="background_tasks", function="sync_all_requests_to_database")
        
        # Queue existing database items that need processing
        from seerr.database_queue_manager import queue_existing_database_items
        from seerr.queue_persistence_manager import queue_persistence_manager, initialize_queue_persistence
        await queue_existing_database_items()
        
        from seerr.overseerr import track_media_request
        from seerr.trakt import get_media_details_from_trakt
        
        synced_count = 0
        for request in processing_requests:
            try:
                tmdb_id = request['media']['tmdbId']
                media_id = request['media']['id']
                request_id = request['id']
                media_type = request['media']['mediaType']
                
                # Check if media exists in database FIRST to avoid unnecessary Trakt API calls
                from seerr.unified_media_manager import get_media_by_tmdb, has_complete_critical_data
                existing_media = get_media_by_tmdb(tmdb_id, media_type)
                movie_details = None
                needs_trakt_call = True
                
                if existing_media and has_complete_critical_data(existing_media):
                    # We already have all critical data, no need for Trakt API call
                    log_info("Database Sync", f"Media {existing_media.title} already has complete critical data, skipping Trakt API call", 
                            module="background_tasks", function="sync_all_requests_to_database")
                    needs_trakt_call = False
                    
                    # Create movie_details dict from existing data
                    movie_details = {
                        'title': existing_media.title,
                        'year': existing_media.year,
                        'imdb_id': existing_media.imdb_id,
                        'trakt_id': existing_media.trakt_id
                    }
                
                # Only make Trakt API call if we don't have complete data
                if needs_trakt_call:
                    movie_details = get_media_details_from_trakt(tmdb_id, media_type)
                    if not movie_details:
                        log_warning("Database Sync Warning", f"Could not get details for TMDB ID {tmdb_id}, skipping database sync", module="background_tasks", function="sync_all_requests_to_database")
                        continue
                
                # Determine status based on Overseerr status
                overseerr_status = request.get('status', 0)
                if overseerr_status == 5:  # Available
                    # For TV shows, check if all episodes are actually processed using new season system
                    if media_type == 'tv':
                        from seerr.unified_models import UnifiedMedia
                        db = get_db()
                        try:
                            subscription = db.query(UnifiedMedia).filter(
                                UnifiedMedia.title == movie_details['title'],
                                UnifiedMedia.media_type == 'tv'
                            ).first()
                            if subscription and subscription.seasons_data:
                                # Check if all seasons are completed using new season data
                                all_seasons_completed = True
                                for season in subscription.seasons_data:
                                    if isinstance(season, dict):
                                        confirmed_count = len(season.get('confirmed_episodes', []))
                                        aired_count = season.get('aired_episodes', 0)
                                        if aired_count > 0 and confirmed_count < aired_count:
                                            all_seasons_completed = False
                                            break
                                
                                if all_seasons_completed:
                                    status = 'completed'
                                else:
                                    status = 'processing'
                            else:
                                status = 'processing'  # No subscription found, assume still processing
                        finally:
                            db.close()
                    else:
                        status = 'completed'  # Movies can be completed immediately
                elif overseerr_status == 2:  # Approved
                    status = 'processing'
                else:
                    status = 'pending'
                
                # Track the request
                track_media_request(
                    overseerr_request_id=request_id,
                    overseerr_media_id=media_id,
                    tmdb_id=tmdb_id,
                    imdb_id=movie_details.get('imdb_id'),
                    trakt_id=movie_details.get('trakt_id'),
                    media_type=media_type,
                    title=movie_details['title'],
                    year=movie_details['year'],
                    requested_by=request.get('requestedBy', {}).get('username', 'Unknown'),
                    extra_data={'overseerr_status': overseerr_status}
                )
                
                synced_count += 1
                
            except Exception as e:
                log_error("Database Sync Error", f"Error syncing request {request.get('id', 'unknown')}: {e}", module="background_tasks", function="sync_all_requests_to_database")
                continue
        
        log_success("Database Sync", f"Synced {synced_count} requests to database", module="background_tasks", function="sync_all_requests_to_database")
        
    except Exception as e:
        log_error("Database Sync Error", f"Error syncing requests to database: {e}", module="background_tasks", function="sync_all_requests_to_database")

async def populate_queues_from_overseerr():
    """
    Fetch Overseerr media requests and populate the appropriate queues.
    For TV shows, fetch season details and log discrepancies if found,
    then add them to the TV queue. Movies are added to the movie queue.
    """
    log_info("Queue Population", "Starting to populate queues from Overseerr media requests...", module="background_tasks", function="populate_queues_from_overseerr")

    # Check if browser driver is available
    from seerr.browser import driver as browser_driver
    if browser_driver is None:
        log_warning("Browser Warning", "Browser driver not initialized. Attempting to initialize...", module="background_tasks", function="populate_queues_from_overseerr")
        from seerr.browser import initialize_browser
        await initialize_browser()
        from seerr.browser import driver as browser_driver
        if browser_driver is None:
            log_error("Browser Error", "Failed to initialize browser driver. Cannot populate queues.", module="background_tasks", function="populate_queues_from_overseerr")
            return

    # Load discrepant shows from database instead of external JSON file
    discrepant_shows = set()  # Set to store (show_title, season_number) tuples

    if USE_DATABASE:
        try:
            from seerr.unified_models import UnifiedMedia
            db = get_db()
            try:
                # Get all TV shows with discrepant seasons from the database
                tv_shows = db.query(UnifiedMedia).filter(
                    UnifiedMedia.media_type == 'tv',
                    UnifiedMedia.seasons_data.isnot(None)
                ).all()
                
                for tv_show in tv_shows:
                    if tv_show.seasons_data:
                        for season_data in tv_show.seasons_data:
                            if isinstance(season_data, dict) and season_data.get('is_discrepant', False):
                                show_title = tv_show.title
                                season_number = season_data.get('season_number')
                                if show_title and season_number is not None:
                                    discrepant_shows.add((show_title, season_number))
                
                log_info("Episode Discrepancies", f"Loaded {len(discrepant_shows)} shows with discrepancies from database", module="background_tasks", function="populate_queues_from_overseerr")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to load discrepant shows from database: {e}")
            discrepant_shows = set()  # Proceed with an empty set if reading fails
    else:
        logger.info("Database not enabled. No discrepancy information available.")

    requests = get_overseerr_media_requests()
    if not requests:
        logger.info("No requests to process")
        # Add subscription check to TV queue even if no new requests
        await add_subscription_check_to_queue()
        return
    
    movies_added = 0
    tv_shows_added = 0
    
    for request in requests:
        tmdb_id = request['media']['tmdbId']
        media_id = request['media']['id']
        request_id = request['id']  # Extract request ID for seerr_id
        media_type = request['media']['mediaType']  # Extract media_type from the request
        
        # Handle aggregated requests - check if this is an aggregated request
        aggregated_request_ids = request.get('aggregated_request_ids', [])
        if aggregated_request_ids:
            logger.info(f"Processing aggregated request with TMDB ID {tmdb_id}, media ID {media_id}, and aggregated request IDs {aggregated_request_ids} (Media Type: {media_type})")
        else:
            logger.info(f"Processing request with TMDB ID {tmdb_id}, media ID {media_id}, and request ID {request_id} (Media Type: {media_type})")

        # Check if this media is already being processed or in queue
        if USE_DATABASE:
            from seerr.unified_media_manager import is_media_processing, is_media_processed
            
            # Check if already being processed
            if is_media_processing(tmdb_id, media_type):
                logger.info(f"Media {tmdb_id} ({media_type}) is already being processed. Skipping.")
                continue
            
            # Check if already completed - for aggregated requests, check all request IDs
            is_completed = False
            existing_media = None
            
            if aggregated_request_ids:
                # For aggregated requests, check if any of the individual requests have been processed
                for agg_request_id in aggregated_request_ids:
                    is_completed, existing_media = is_media_processed(tmdb_id, media_type, overseerr_request_id=agg_request_id)
                    if is_completed:
                        logger.info(f"Media {tmdb_id} ({media_type}) is already completed (found via aggregated request ID {agg_request_id}). Skipping.")
                        break
                # If any aggregated request was completed, skip processing
                if is_completed:
                    continue
            else:
                # For single requests, use the original logic
                is_completed, existing_media = is_media_processed(tmdb_id, media_type, overseerr_request_id=request_id)
                if is_completed:
                    logger.info(f"Media {tmdb_id} ({media_type}) is already completed. Skipping.")
                    continue

        logger.info(f"Processing media {tmdb_id} ({media_type}) - adding to queue for processing...")

        # Check if we already have the needed info in the database
        movie_details = None
        needs_trakt_call = True
        needs_image_processing = True
        
        if USE_DATABASE:
            from seerr.unified_media_manager import get_media_by_overseerr_request
            # For aggregated requests, try to find existing media using any of the request IDs
            existing_media = None
            if aggregated_request_ids:
                for agg_request_id in aggregated_request_ids:
                    existing_media = get_media_by_overseerr_request(agg_request_id)
                    if existing_media and existing_media.overview and existing_media.genres:
                        break
            else:
                existing_media = get_media_by_overseerr_request(request_id)
            
            if existing_media and existing_media.overview and existing_media.genres:
                # We already have rich data, use it
                movie_details = {
                    'title': existing_media.title,
                    'year': existing_media.year,
                    'imdb_id': existing_media.imdb_id,
                    'trakt_id': existing_media.trakt_id,
                    'overview': existing_media.overview,
                    'genres': existing_media.genres,
                    'runtime': existing_media.runtime,
                    'rating': existing_media.rating,
                    'poster_url': existing_media.poster_url,
                    'fanart_url': existing_media.fanart_url,
                    'backdrop_url': existing_media.backdrop_url,
                    'released_date': existing_media.released_date  # Include released_date for unreleased check
                }
                needs_trakt_call = False
                if aggregated_request_ids:
                    logger.info(f"Using existing rich data for {movie_details['title']} (Aggregated Request IDs: {aggregated_request_ids})")
                else:
                    logger.info(f"Using existing rich data for {movie_details['title']} (Request ID: {request_id})")
                
                # Check if we need image processing
                if existing_media.poster_image_format and existing_media.poster_image_size and existing_media.poster_image_size > 0:
                    needs_image_processing = False
                    logger.info(f"Images already stored for {movie_details['title']}")
        
        # Only fetch Trakt details if we don't have the needed info
        if needs_trakt_call:
            from seerr.trakt import get_media_details_from_trakt
            movie_details = get_media_details_from_trakt(tmdb_id, media_type)
            if not movie_details:
                logger.error(f"Failed to get media details for TMDB ID {tmdb_id}")
                continue

        # Extract requested seasons for TV shows
        extra_data = []
        requested_seasons = []
        if media_type == 'tv':
            logger.info(f"Processing TV show request: {request}")
            if 'seasons' in request and request['seasons']:
                requested_seasons = [f"Season {season['seasonNumber']}" for season in request['seasons']]
                extra_data.append({"name": "Requested Seasons", "value": ", ".join(requested_seasons)})
                logger.info(f"Requested seasons for TV show: {requested_seasons}")
            else:
                logger.warning(f"No seasons data found in request for TV show {request.get('media', {}).get('title', 'Unknown')}")
                logger.info(f"Request structure: {list(request.keys())}")
                if 'seasons' in request:
                    logger.info(f"Seasons field exists but is empty or None: {request['seasons']}")
                else:
                    logger.info("No 'seasons' field found in request")

        # Use the movie_details we already fetched earlier
        imdb_id = movie_details['imdb_id']
        media_title = f"{movie_details['title']} ({movie_details['year']})"
        logger.info(f"Preparing {media_type} request for queue: {media_title}")

        # Check if media is unreleased BEFORE queuing (for movies)
        if media_type == 'movie' and movie_details.get('released_date'):
            from datetime import datetime, timezone
            current_time = datetime.now(timezone.utc)
            released_date = movie_details['released_date']
            
            # Ensure released_date is timezone-aware for comparison
            if released_date.tzinfo is None:
                released_date = released_date.replace(tzinfo=timezone.utc)
            
            if released_date > current_time:
                logger.info(f"Movie {media_title} is unreleased (releases {released_date.strftime('%Y-%m-%d')}), skipping queue")
                # Still create the media record with unreleased status, but don't add to queue
                if USE_DATABASE:
                    from seerr.unified_media_manager import start_media_processing
                    start_media_processing(
                        tmdb_id=tmdb_id,
                        imdb_id=imdb_id,
                        trakt_id=movie_details.get('trakt_id'),
                        media_type=media_type,
                        title=movie_details['title'],
                        year=movie_details['year'],
                        overseerr_request_id=request_id,
                        overseerr_media_id=media_id,
                        processing_stage='queue_processing',
                        extra_data={'requested_seasons': requested_seasons} if requested_seasons else None,
                        media_details=movie_details  # Pass media_details so it sets unreleased status
                    )
                    # Track the media request in the database
                    from seerr.overseerr import track_media_request
                    track_media_request(
                        overseerr_request_id=request_id,
                        overseerr_media_id=media_id,
                        tmdb_id=tmdb_id,
                        imdb_id=imdb_id,
                        trakt_id=movie_details.get('trakt_id'),
                        media_type=media_type,
                        title=movie_details['title'],
                        year=movie_details['year'],
                        requested_by=request.get('requestedBy', {}).get('username', 'Unknown'),
                        extra_data={'requested_seasons': requested_seasons} if requested_seasons else None
                    )
                continue  # Skip queueing for unreleased movies

        # Also check if existing media has unreleased status
        if USE_DATABASE:
            from seerr.unified_media_manager import get_media_by_overseerr_request
            existing_media_check = get_media_by_overseerr_request(request_id)
            if existing_media_check and existing_media_check.status == 'unreleased':
                logger.info(f"Media {media_title} already marked as unreleased, skipping queue")
                continue

        # Process images if needed
        image_data = None
        if needs_image_processing and movie_details.get('trakt_id'):
            try:
                logger.info(f"Fetching and processing images for {media_title}")
                if media_type == 'movie':
                    images = fetch_trakt_movie_images(str(movie_details['trakt_id']))
                    if images:
                        image_data = store_media_images(media_title, tmdb_id, media_type, str(movie_details['trakt_id']))
                else:  # TV show
                    images = fetch_trakt_show_images(str(movie_details['trakt_id']))
                    if images:
                        image_data = store_show_image(media_title, str(movie_details['trakt_id']), images)
                
                if image_data:
                    logger.info(f"Successfully processed images for {media_title}")
                else:
                    logger.warning(f"Failed to process images for {media_title}")
            except Exception as e:
                logger.error(f"Error processing images for {media_title}: {e}")

        # Add to appropriate queue FIRST, before updating status
        if media_type == 'movie':
            success = await add_movie_to_queue(imdb_id, media_title, media_type, extra_data, media_id, tmdb_id, request_id)
            if success:
                movies_added += 1
                # Start tracking media processing AFTER successfully adding to queue
                if USE_DATABASE:
                    from seerr.unified_media_manager import start_media_processing
                    processed_media_id = start_media_processing(
                        tmdb_id=tmdb_id,
                        imdb_id=imdb_id,
                        trakt_id=movie_details.get('trakt_id'),
                        media_type=media_type,
                        title=movie_details['title'],
                        year=movie_details['year'],
                        overseerr_request_id=request_id,
                        overseerr_media_id=media_id,
                        processing_stage='queue_processing',
                        extra_data={'requested_seasons': requested_seasons} if requested_seasons else None,
                        image_data=image_data,
                        media_details=movie_details  # Pass media_details so it can check released_date
                    )
                    
                    # Track the media request in the database
                    from seerr.overseerr import track_media_request
                    track_media_request(
                        overseerr_request_id=request_id,
                        overseerr_media_id=media_id,
                        tmdb_id=tmdb_id,
                        imdb_id=imdb_id,
                        trakt_id=movie_details.get('trakt_id'),
                        media_type=media_type,
                        title=movie_details['title'],
                        year=movie_details['year'],
                        requested_by=request.get('requestedBy', {}).get('username', 'Unknown'),
                        extra_data={'requested_seasons': requested_seasons} if requested_seasons else None
                    )
        else:  # TV show
            success = await add_tv_to_queue(imdb_id, media_title, media_type, extra_data, media_id, tmdb_id, request_id)
            if success:
                tv_shows_added += 1
                # Start tracking media processing AFTER successfully adding to queue
                if USE_DATABASE:
                    from seerr.unified_media_manager import start_media_processing
                    processed_media_id = start_media_processing(
                        tmdb_id=tmdb_id,
                        imdb_id=imdb_id,
                        trakt_id=movie_details.get('trakt_id'),
                        media_type=media_type,
                        title=movie_details['title'],
                        year=movie_details['year'],
                        overseerr_request_id=request_id,
                        overseerr_media_id=media_id,
                        processing_stage='queue_processing',
                        extra_data={'requested_seasons': requested_seasons} if requested_seasons else None,
                        image_data=image_data,
                        media_details=movie_details  # Pass media_details so it can check released_date
                    )
                    
                    # Track the media request in the database
                    from seerr.overseerr import track_media_request
                    track_media_request(
                        overseerr_request_id=request_id,
                        overseerr_media_id=media_id,
                        tmdb_id=tmdb_id,
                        imdb_id=imdb_id,
                        trakt_id=movie_details.get('trakt_id'),
                        media_type=media_type,
                        title=movie_details['title'],
                        year=movie_details['year'],
                        requested_by=request.get('requestedBy', {}).get('username', 'Unknown'),
                        extra_data={'requested_seasons': requested_seasons} if requested_seasons else None
                    )

        # Track the media request in the database (only if successfully added to queue)
        # This is now handled inside the queue addition blocks above

        # For TV shows, process all seasons using the new multi-season approach
        if media_type == 'tv':
            # If no requested seasons found in request data, try to get them from Overseerr API
            if not requested_seasons:
                logger.info(f"No seasons found in request data for {media_title}, attempting to fetch from Overseerr API")
                try:
                    from seerr.overseerr import get_all_overseerr_requests_for_media
                    all_requests = get_all_overseerr_requests_for_media(media_id)
                    logger.info(f"Found {len(all_requests)} total requests for media ID {media_id}")
                    
                    # Extract seasons from all requests for this media
                    for req in all_requests:
                        if 'seasons' in req and req['seasons']:
                            for season in req['seasons']:
                                season_name = f"Season {season['seasonNumber']}"
                                if season_name not in requested_seasons:
                                    requested_seasons.append(season_name)
                    
                    if requested_seasons:
                        logger.info(f"Successfully extracted seasons from Overseerr API: {requested_seasons}")
                        extra_data.append({"name": "Requested Seasons", "value": ", ".join(requested_seasons)})
                    else:
                        logger.warning(f"Still no seasons found for {media_title} after checking Overseerr API")
                except Exception as e:
                    logger.error(f"Error fetching seasons from Overseerr API for {media_title}: {e}")
            
            # Process seasons if we have them
            if requested_seasons:
                logger.info(f"Processing {len(requested_seasons)} seasons for {media_title}: {requested_seasons}")
                trakt_show_id = movie_details['trakt_id']
                
                # Process individual seasons using enhanced multi-season system
                from seerr.enhanced_season_manager import EnhancedSeasonManager
                
                seasons_data = []
                
                for season in requested_seasons:
                    season_number = int(season.split()[-1])  # Extract number from "Season X"
                    
                    # Fetch season details from Trakt
                    season_details = get_season_details_from_trakt(str(trakt_show_id), season_number)
                    
                    if season_details:
                        episode_count = season_details.get('episode_count', 0)
                        aired_episodes = season_details.get('aired_episodes', 0)
                        logger.info(f"Processed season {season_number} for {media_title}: {episode_count} episodes, {aired_episodes} aired")
                        
                        # Check for next episode if there's a discrepancy
                        if episode_count != aired_episodes:
                            has_aired, next_episode_details = check_next_episode_aired(
                                str(trakt_show_id), season_number, aired_episodes
                            )
                            if has_aired:
                                logger.info(f"Next episode (E{aired_episodes + 1:02d}) has aired for {media_title} Season {season_number}. Updating aired_episodes.")
                                aired_episodes += 1
                        
                        # Create enhanced season data
                        season_data = {
                            'season_number': season_number,
                            'episode_count': episode_count,
                            'aired_episodes': aired_episodes,
                            'confirmed_episodes': [],
                            'failed_episodes': [],
                            'unprocessed_episodes': [f"E{str(i).zfill(2)}" for i in range(1, aired_episodes + 1)] if aired_episodes > 0 else [],
                            'last_checked': datetime.utcnow().isoformat(),
                            'updated_at': datetime.utcnow().isoformat()
                        }
                        
                        seasons_data.append(season_data)
                    else:
                        logger.warning(f"Could not fetch season details for {media_title} Season {season_number}")
                
                # Update TV show with enhanced season data
                if seasons_data:
                    logger.info(f"Updating {media_title} with enhanced season data for {len(seasons_data)} seasons")
                    success = EnhancedSeasonManager.update_tv_show_seasons(tmdb_id, seasons_data, media_title)
                    
                    if success:
                        logger.info(f"Successfully updated {media_title} with enhanced season tracking")
                    else:
                        logger.warning(f"Failed to update {media_title} with enhanced season tracking")
                else:
                    logger.warning(f"No season data to update for {media_title}")
            else:
                logger.warning(f"No seasons to process for TV show {media_title}")

        # Queue addition is now handled earlier in the flow

    logger.info(f"Added {movies_added} movies and {tv_shows_added} TV shows to queues")
    
    # Always add subscription check to TV queue at the end
    await add_subscription_check_to_queue()
    
    logger.info("Finished populating queues from Overseerr requests.")
    await schedule_recheck_movie_requests()

async def check_movie_processing():
    """
    Recurring task to check for movies stuck in processing status.
    Re-queues movies that have been processing for too long or are stuck.
    """
    logger.info("Starting movie processing check...")

    # Check if browser driver is available
    from seerr.browser import driver as browser_driver
    if browser_driver is None:
        log_warning("Browser Warning", "Browser driver not initialized. Attempting to initialize...", module="background_tasks", function="check_movie_processing")
        from seerr.browser import initialize_browser
        await initialize_browser()
        from seerr.browser import driver as browser_driver
        if browser_driver is None:
            logger.error("Failed to initialize browser driver. Cannot check movie processing.")
            return

    logger.info("Starting movie processing check")
    
    # Get movies stuck in processing status from database
    if not USE_DATABASE:
        logger.info("Database not enabled. Skipping movie processing check.")
        return
    
    db = get_db()
    try:
        from datetime import datetime, timedelta
        from datetime import timezone
        
        # First, check for unreleased items that should now be released
        current_time = datetime.now(timezone.utc)
        unreleased_items = db.query(UnifiedMedia).filter(
            UnifiedMedia.status == 'unreleased',
            UnifiedMedia.released_date <= current_time
        ).all()
        
        if unreleased_items:
            logger.info(f"Found {len(unreleased_items)} unreleased items that should now be released. Updating status to pending...")
            for item in unreleased_items:
                try:
                    item.status = 'pending'
                    item.updated_at = datetime.utcnow()
                    logger.info(f"Updated {item.title} (TMDB: {item.tmdb_id}) from unreleased to pending (released date: {item.released_date})")
                except Exception as e:
                    logger.error(f"Error updating unreleased item {item.title}: {e}")
            db.commit()
            logger.info(f"Updated {len(unreleased_items)} unreleased items to pending status")
        
        # Find movies that have been processing for more than 5 minutes OR are not in queue
        cutoff_time = datetime.utcnow() - timedelta(minutes=5)
        
        from seerr.unified_models import UnifiedMedia
        stuck_movies = db.query(UnifiedMedia).filter(
            UnifiedMedia.media_type == 'movie',
            UnifiedMedia.status == 'processing',
            UnifiedMedia.last_checked_at < cutoff_time
        ).all()
        
        # Also check if there are movies in processing status that should be in queue
        # but aren't (this handles the case where movies are stuck but recently updated)
        if not stuck_movies:
            # Check if there are movies in processing but queue is empty
            if movie_queue.empty():
                logger.info("Queue is empty but movies are in processing status. Checking for stuck movies...")
                stuck_movies = db.query(UnifiedMedia).filter(
                    UnifiedMedia.media_type == 'movie',
                    UnifiedMedia.status == 'processing'
                ).all()
        
        if not stuck_movies:
            logger.info("No stuck movies found in processing status.")
            return
        
        logger.info(f"Found {len(stuck_movies)} stuck movies. Checking release dates...")
        
        for movie in stuck_movies:
            try:
                logger.info(f"Checking stuck movie: {movie.title} (TMDB: {movie.tmdb_id})")
                
                # Check release date from database first (avoid unnecessary Trakt API call)
                from datetime import datetime, timezone
                current_time = datetime.now(timezone.utc)
                
                if movie.released_date:
                    # Ensure released_date is timezone-aware for comparison
                    released_date = movie.released_date
                    if released_date.tzinfo is None:
                        # If naive, assume it's UTC
                        released_date = released_date.replace(tzinfo=timezone.utc)
                    
                    # We have release date - check if it's in the future
                    if released_date > current_time:
                        # Movie is unreleased - set status to unreleased instead of re-queuing
                        logger.info(f"Movie {movie.title} is unreleased (releases {released_date.strftime('%Y-%m-%d')}), setting status to unreleased")
                        from seerr.unified_media_manager import update_media_processing_status
                        update_media_processing_status(
                            movie.id,
                            'unreleased',
                            'unreleased_detected_on_check',
                            extra_data={'released_date': released_date.isoformat()}
                        )
                        logger.info(f"Set {movie.title} status to unreleased (skipping re-queue)")
                        continue
                
                # If we don't have released_date, fetch from Trakt API
                needs_trakt_call = not movie.released_date
                movie_details = None
                
                if needs_trakt_call:
                    logger.info(f"No released_date in database for {movie.title}, fetching from Trakt API")
                    from seerr.trakt import get_media_details_from_trakt
                    movie_details = get_media_details_from_trakt(movie.tmdb_id, 'movie')
                    if not movie_details:
                        logger.warning(f"Could not get details for movie {movie.title} (TMDB: {movie.tmdb_id}). Skipping.")
                        continue
                    
                    # Check release date from Trakt response
                    if movie_details.get('released_date'):
                        released_date = movie_details['released_date']
                        if released_date > current_time:
                            # Movie is unreleased - set status to unreleased
                            logger.info(f"Movie {movie.title} is unreleased (releases {released_date.strftime('%Y-%m-%d')}), setting status to unreleased")
                            from seerr.unified_media_manager import update_media_processing_status
                            update_media_processing_status(
                                movie.id,
                                'unreleased',
                                'unreleased_detected_on_check',
                                extra_data={'released_date': released_date.isoformat()}
                            )
                            logger.info(f"Set {movie.title} status to unreleased (skipping re-queue)")
                            continue
                
                # Movie is released or has no release date restriction - proceed with re-queueing
                logger.info(f"Re-queuing stuck movie: {movie.title} (TMDB: {movie.tmdb_id})")
                
                # Re-queue the movie for processing
                await add_movie_to_queue(
                    imdb_id=movie.imdb_id,
                    movie_title=movie.title,
                    media_type='movie',
                    extra_data=movie.extra_data,
                    media_id=movie.overseerr_media_id,
                    tmdb_id=movie.tmdb_id,
                    request_id=movie.overseerr_request_id
                )
                
                # Update the processing stage to indicate it's been re-queued
                from seerr.unified_media_manager import update_media_processing_status
                update_media_processing_status(
                    movie.id,
                    'processing',
                    're_queued_for_processing',
                    extra_data={'re_queued_at': datetime.utcnow().isoformat()}
                )
                
                logger.info(f"Successfully re-queued movie: {movie.title}")
                
            except Exception as e:
                logger.error(f"Error re-queuing movie {movie.title}: {e}")
                continue
        
        logger.info("Completed movie processing check.")
        
    except Exception as e:
        logger.error(f"Error during movie processing check: {e}")
    finally:
        db.close()

async def check_stuck_items_on_startup():
    """
    Check for stuck items on startup and immediately re-queue them.
    This runs once when the system starts up to handle any items that were
    stuck in processing status from previous runs.
    """
    logger.info("Startup Check: Checking for stuck items on startup...")
    
    if not USE_DATABASE:
        logger.info("Startup Check: Database not enabled. Skipping startup check.")
        return
    
    try:
        # Import UnifiedMedia model
        from seerr.unified_models import UnifiedMedia
        
        # Check for stuck movies (any movie in processing status, regardless of time)
        db = get_db()
        try:
            stuck_movies = db.query(UnifiedMedia).filter(
                UnifiedMedia.media_type == 'movie',
                UnifiedMedia.status == 'processing'
            ).all()
            
            if stuck_movies:
                logger.info(f"Startup Check: Found {len(stuck_movies)} movies stuck in processing status. Checking release dates...")
                
                for movie in stuck_movies:
                    try:
                        logger.info(f"Startup Check: Checking stuck movie: {movie.title} (TMDB: {movie.tmdb_id})")
                        
                        # Check release date from database first (avoid unnecessary Trakt API call)
                        from datetime import datetime, timezone
                        current_time = datetime.now(timezone.utc)
                        
                        if movie.released_date:
                            # Ensure released_date is timezone-aware for comparison
                            released_date = movie.released_date
                            if released_date.tzinfo is None:
                                # If naive, assume it's UTC
                                released_date = released_date.replace(tzinfo=timezone.utc)
                            
                            # We have release date - check if it's in the future
                            if released_date > current_time:
                                # Movie is unreleased - set status to unreleased instead of re-queuing
                                logger.info(f"Startup Check: Movie {movie.title} is unreleased (releases {released_date.strftime('%Y-%m-%d')}), setting status to unreleased")
                                from seerr.unified_media_manager import update_media_processing_status
                                update_media_processing_status(
                                    movie.id,
                                    'unreleased',
                                    'unreleased_detected_on_startup',
                                    extra_data={'released_date': released_date.isoformat(), 'startup_check': True}
                                )
                                logger.info(f"Startup Check: Set {movie.title} status to unreleased (skipping re-queue)")
                                continue
                        
                        # If we don't have released_date, fetch from Trakt API
                        needs_trakt_call = not movie.released_date
                        movie_details = None
                        
                        if needs_trakt_call:
                            logger.info(f"Startup Check: No released_date in database for {movie.title}, fetching from Trakt API")
                            from seerr.trakt import get_media_details_from_trakt
                            movie_details = get_media_details_from_trakt(movie.tmdb_id, 'movie')
                            if not movie_details:
                                logger.warning(f"Startup Check: Could not get details for movie {movie.title} (TMDB: {movie.tmdb_id}). Skipping.")
                                continue
                            
                            # Check release date from Trakt response
                            if movie_details.get('released_date'):
                                released_date = movie_details['released_date']
                                if released_date > current_time:
                                    # Movie is unreleased - set status to unreleased
                                    logger.info(f"Startup Check: Movie {movie.title} is unreleased (releases {released_date.strftime('%Y-%m-%d')}), setting status to unreleased")
                                    from seerr.unified_media_manager import update_media_processing_status
                                    update_media_processing_status(
                                        movie.id,
                                        'unreleased',
                                        'unreleased_detected_on_startup',
                                        extra_data={'released_date': released_date.isoformat(), 'startup_check': True}
                                    )
                                    logger.info(f"Startup Check: Set {movie.title} status to unreleased (skipping re-queue)")
                                    continue
                        
                        # Movie is released or has no release date restriction - proceed with re-queueing
                        logger.info(f"Startup Check: Re-queuing stuck movie: {movie.title} (TMDB: {movie.tmdb_id})")
                        
                        # Re-queue the movie for processing
                        # Ensure extra_data is properly parsed if it's a JSON string
                        extra_data = movie.extra_data
                        if isinstance(extra_data, str):
                            try:
                                import json
                                extra_data = json.loads(extra_data)
                                # Parsed extra_data from JSON string
                            except (json.JSONDecodeError, TypeError) as e:
                                logger.warning(f"Failed to parse extra_data as JSON: {extra_data}, error: {e}")
                                extra_data = []
                        
                        await add_movie_to_queue(
                            imdb_id=movie.imdb_id,
                            movie_title=movie.title,
                            media_type='movie',
                            extra_data=extra_data,
                            media_id=movie.overseerr_media_id,
                            tmdb_id=movie.tmdb_id,
                            request_id=movie.overseerr_request_id
                        )
                        
                        # Update the processing stage to indicate it's been re-queued on startup
                        from seerr.unified_media_manager import update_media_processing_status
                        update_media_processing_status(
                            movie.id,
                            'processing',
                            're_queued_on_startup',
                            extra_data={'re_queued_at': datetime.utcnow().isoformat(), 'startup_requeue': True}
                        )
                        
                        logger.info(f"Startup Check: Successfully re-queued movie: {movie.title}")
                        
                    except Exception as e:
                        logger.error(f"Startup Check: Error re-queuing movie {movie.title}: {e}")
                        continue
            else:
                logger.info("Startup Check: No movies found stuck in processing status.")
            
            # Check for stuck TV shows (any TV show in processing status, regardless of time)
            stuck_tv_shows = db.query(UnifiedMedia).filter(
                UnifiedMedia.media_type == 'tv',
                UnifiedMedia.status == 'processing'
            ).all()
            
            if stuck_tv_shows:
                logger.info(f"Startup Check: Found {len(stuck_tv_shows)} TV shows in processing status. Checking which seasons need processing...")
                
                for tv_show in stuck_tv_shows:
                    try:
                        logger.info(f"Startup Check: Analyzing TV show: {tv_show.title} (TMDB: {tv_show.tmdb_id})")
                        
                        # Check if this TV show actually has seasons that need processing
                        seasons_need_processing = []
                        
                        if tv_show.seasons_data:
                            import json
                            if isinstance(tv_show.seasons_data, str):
                                seasons_data = json.loads(tv_show.seasons_data)
                            else:
                                seasons_data = tv_show.seasons_data
                            
                            for season in seasons_data:
                                season_number = season.get('season_number')
                                season_status = season.get('status')
                                
                                # Check if season has confirmed episodes
                                confirmed_episodes = season.get('confirmed_episodes', [])
                                aired_episodes = season.get('aired_episodes', 0)
                                has_confirmed_episodes = len(confirmed_episodes) > 0
                                
                                # Only process seasons that are:
                                # - Not completed and not "not_aired" AND
                                # - Either has no confirmed episodes, OR has unprocessed episodes remaining
                                if season_status not in ['completed', 'not_aired']:
                                    if has_confirmed_episodes:
                                        # Season has some episodes confirmed - check if there are unprocessed episodes
                                        unprocessed_episodes = season.get('unprocessed_episodes', [])
                                        if unprocessed_episodes and len(unprocessed_episodes) > 0:
                                            seasons_need_processing.append(season_number)
                                            logger.info(f"Startup Check: Season {season_number} has {len(confirmed_episodes)} confirmed but {len(unprocessed_episodes)} unprocessed episodes - needs processing")
                                        else:
                                            # All aired episodes are either confirmed or failed
                                            logger.info(f"Startup Check: Season {season_number} has confirmed episodes but no unprocessed episodes - skipping")
                                    else:
                                        # No episodes confirmed yet - needs processing
                                        seasons_need_processing.append(season_number)
                                        logger.info(f"Startup Check: Season {season_number} needs processing (status: {season_status}, no confirmed episodes)")
                                else:
                                    logger.info(f"Startup Check: Season {season_number} is {season_status}, skipping")
                        
                        # Only re-queue if there are seasons that actually need processing
                        if seasons_need_processing:
                            logger.info(f"Startup Check: Re-queuing TV show {tv_show.title} for seasons: {seasons_need_processing}")
                            
                            # Get media details from Trakt
                            from seerr.trakt import get_media_details_from_trakt
                            tv_details = get_media_details_from_trakt(tv_show.tmdb_id, 'tv')
                            if not tv_details:
                                logger.warning(f"Startup Check: Could not get details for TV show {tv_show.title} (TMDB: {tv_show.tmdb_id}). Skipping.")
                                continue
                            
                            # Re-queue the TV show for processing with only the seasons that need it
                            # Ensure extra_data is properly parsed if it's a JSON string
                            extra_data = tv_show.extra_data
                            if isinstance(extra_data, str):
                                try:
                                    import json
                                    extra_data = json.loads(extra_data)
                                    # Parsed extra_data from JSON string
                                except (json.JSONDecodeError, TypeError) as e:
                                    logger.warning(f"Failed to parse extra_data as JSON: {extra_data}, error: {e}")
                                    extra_data = {}
                            
                            # Add the seasons that need processing to extra_data
                            extra_data['requested_seasons'] = seasons_need_processing
                            
                            await add_tv_to_queue(
                                imdb_id=tv_show.imdb_id,
                                movie_title=tv_show.title,
                                media_type='tv',
                                extra_data=extra_data,
                                media_id=tv_show.overseerr_media_id,
                                tmdb_id=tv_show.tmdb_id,
                                request_id=tv_show.overseerr_request_id
                            )
                            
                            # Update the processing stage to indicate it's been re-queued on startup
                            from seerr.unified_media_manager import update_media_processing_status
                            update_media_processing_status(
                                tv_show.id,
                                'processing',
                                're_queued_on_startup',
                                extra_data={'re_queued_at': datetime.utcnow().isoformat(), 'startup_requeue': True, 'seasons_requeued': seasons_need_processing}
                            )
                            
                            logger.info(f"Startup Check: Successfully re-queued TV show: {tv_show.title} for seasons {seasons_need_processing}")
                        else:
                            logger.info(f"Startup Check: TV show {tv_show.title} has no seasons that need processing. Skipping re-queue.")
                            
                            # If no seasons need processing, we should update the status to completed
                            from seerr.unified_media_manager import update_media_processing_status
                            update_media_processing_status(
                                tv_show.id,
                                'completed',
                                'startup_check_completed',
                                extra_data={'startup_check_completed_at': datetime.utcnow().isoformat()}
                            )
                            logger.info(f"Startup Check: Marked TV show {tv_show.title} as completed (no seasons need processing)")
                        
                    except Exception as e:
                        logger.error(f"Startup Check: Error analyzing TV show {tv_show.title}: {e}")
                        continue
            else:
                logger.info("Startup Check: No TV shows found in processing status.")
            
            logger.info("Startup Check: Completed startup check for stuck items.")
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Startup Check: Error during startup check: {e}")

async def check_show_subscriptions():
    """
    Recurring task to check for new episodes in subscribed shows from database.
    Updates the database with the latest aired episode counts and processes new episodes if found.
    Also reattempts processing of previously failed episodes and checks for the next episode if there's a discrepancy.
    """
    # Check if show subscription task is enabled
    if not task_config.get_config('enable_show_subscription_task', False):
        logger.info("Show subscription check disabled (enable_show_subscription_task=False).")
        return
    
    logger.info("Starting show subscription check...")

    # Check if browser driver is available
    from seerr.browser import driver as browser_driver
    if browser_driver is None:
        log_warning("Browser Warning", "Browser driver not initialized. Attempting to initialize...", module="background_tasks", function="populate_queues_from_overseerr")
        from seerr.browser import initialize_browser
        await initialize_browser()
        from seerr.browser import driver as browser_driver
        if browser_driver is None:
            logger.error("Failed to initialize browser driver. Cannot check show subscriptions.")
            return

    logger.info("Starting show subscription check processing")
    
    # Get active show subscriptions from unified_media table
    from seerr.unified_models import UnifiedMedia
    db = get_db()
    try:
        subscriptions = db.query(UnifiedMedia).filter(
            UnifiedMedia.media_type == 'tv',
            UnifiedMedia.is_subscribed == True,
            UnifiedMedia.status != 'ignored'  # Exclude ignored items
        ).all()
        
        if not subscriptions:
            logger.info("No active show subscriptions found in database. Skipping show subscription check.")
            return
    finally:
        db.close()

    # Process each show subscription from database
    for subscription in subscriptions:
        # Check if item is still in queue before processing subscription
        # If user cleared it from queue, skip processing
        if subscription.is_in_queue == False:
            logger.info(f"Show {subscription.title} (TMDB: {subscription.tmdb_id}) is not in queue. Skipping subscription check.")
            continue
        
        show_title = subscription.title
        trakt_show_id = subscription.trakt_id
        imdb_id = subscription.imdb_id
        tmdb_id = subscription.tmdb_id
        # Get season information from seasons_data instead of old fields
        if not subscription.seasons_data:
            logger.warning(f"No seasons_data found for {show_title}. Skipping.")
            continue
        
        # Process each season in the seasons_data
        for season_data in subscription.seasons_data:
            if not isinstance(season_data, dict):
                continue
                
            season_number = season_data.get('season_number')
            if not season_number:
                continue
                
            season_details = season_data
            previous_aired_episodes = season_data.get('aired_episodes', 0)
            failed_episodes = season_data.get('failed_episodes', [])
            confirmed_episodes = season_data.get('confirmed_episodes', [])
            unprocessed_episodes = season_data.get('unprocessed_episodes', [])

            logger.info(f"Checking for new episodes for {show_title} Season {season_number}...")

            # Check if this show was previously completed but now has new episodes
            if subscription.overseerr_request_id:
                from seerr.unified_media_manager import get_media_by_overseerr_request
                media_record = get_media_by_overseerr_request(subscription.overseerr_request_id)
                if media_record and media_record.status == 'completed':
                    logger.info(f"Found completed show {show_title} - checking for new episodes...")
                    # We'll check for new episodes below and update status if needed

            if not trakt_show_id or not season_number or not imdb_id:
                logger.warning(f"Missing trakt_show_id, season_number, or imdb_id for {show_title}. Skipping.")
                continue

            # Fetch the latest season details from Trakt
            latest_season_details = get_season_details_from_trakt(str(trakt_show_id), season_number)
            if not latest_season_details:
                logger.error(f"Failed to fetch latest season details for {show_title} Season {season_number}. Skipping.")
                continue

            current_aired_episodes = latest_season_details.get("aired_episodes", 0)
            episode_count = latest_season_details.get("episode_count", 0)
            logger.info(f"Previous aired episodes: {previous_aired_episodes}, Current aired episodes: {current_aired_episodes}, Episode count: {episode_count}")

            # Check for the next episode if there's a discrepancy
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

            # Update the subscription in the database with latest episode counts
            # Use the unified media system instead of the old subscription system
            from seerr.unified_media_manager import update_media_details
            
            # Find the media record for this subscription
            if subscription.overseerr_request_id:
                from seerr.unified_media_manager import get_media_by_overseerr_request
                media_record = get_media_by_overseerr_request(subscription.overseerr_request_id)
                if media_record:
                    # Update the seasons_data with the latest information
                    seasons_data = media_record.seasons_data or []
                    updated_seasons = []
                    
                    for season_data in seasons_data:
                        if season_data.get('season_number') == season_number:
                            # Update this season's data
                            season_data['aired_episodes'] = current_aired_episodes
                            season_data['episode_count'] = episode_count
                            season_data['last_checked'] = datetime.utcnow().isoformat()
                            season_data['updated_at'] = datetime.utcnow().isoformat()
                            # Update other fields from latest_season_details if available
                            if 'status' in latest_season_details:
                                season_data['status'] = latest_season_details['status']
                            if 'rating' in latest_season_details:
                                season_data['rating'] = latest_season_details['rating']
                        updated_seasons.append(season_data)
                    
                    # Update the media record with the new seasons data
                    update_media_details(
                        media_record.id,
                        seasons_data=updated_seasons,
                        last_checked_at=datetime.utcnow()
                    )
                    logger.info(f"Updated seasons data for {show_title} Season {season_number}")
                else:
                    logger.warning(f"Could not find media record for subscription {show_title}")
            else:
                logger.warning(f"No overseerr_request_id for subscription {show_title}")
            
            # Check if a previously completed show now has new episodes and needs to be reactivated
            if subscription.overseerr_request_id:
                from seerr.unified_media_manager import get_media_by_overseerr_request, update_media_processing_status
                media_record = get_media_by_overseerr_request(subscription.overseerr_request_id)
                if media_record and media_record.status == 'completed':
                    # Check if there are new episodes that haven't been confirmed
                    needs_reactivation = False
                    reactivation_reason = ""
                    
                    # Case 1: New aired episodes that haven't been confirmed
                    if current_aired_episodes > len(confirmed_episodes):
                        needs_reactivation = True
                        reactivation_reason = f"New aired episodes: {current_aired_episodes} aired, {len(confirmed_episodes)} confirmed"
                    
                    # Case 2: Show has more total episodes than confirmed (future episodes coming)
                    elif episode_count > len(confirmed_episodes):
                        needs_reactivation = True
                        reactivation_reason = f"Future episodes pending: {episode_count} total, {len(confirmed_episodes)} confirmed"
                    
                    if needs_reactivation:
                        logger.info(f"Completed show {show_title} needs reactivation: {reactivation_reason}")
                        update_media_processing_status(
                            media_record.id, 
                            'processing', 
                            'new_episodes_detected',
                            reactivation_reason
                        )
                        logger.info(f"Reactivated {show_title} from completed to processing: {reactivation_reason}")

            # Get current episode statuses from database
            # Initialize lists to track episode statuses
            episodes_to_process = []
            new_unprocessed_episodes = []
            
            # Check ALL aired episodes to categorize their status
            logger.info(f"Verifying confirmation status for all {current_aired_episodes} aired episodes...")
            
            for episode_num in range(1, current_aired_episodes + 1):
                episode_id = f"E{episode_num:02d}"
                
                # Check if this episode is already confirmed
                if episode_id in confirmed_episodes:
                    logger.info(f"Episode {episode_id} is already confirmed in database. Skipping verification.")
                    continue
                    
                # Check if this episode was previously failed
                if episode_id in failed_episodes:
                    episodes_to_process.append((episode_num, episode_id, "failed"))
                    logger.info(f"Reattempting previously failed episode {episode_id}")
                else:
                    # This episode needs verification - it's not confirmed and not failed
                    episodes_to_process.append((episode_num, episode_id, "verify"))
                    new_unprocessed_episodes.append(episode_id)
                    logger.info(f"Episode {episode_id} needs verification - not confirmed in database")

        # Update unprocessed episodes in database if we have new unprocessed episodes
        if new_unprocessed_episodes:
            # Combine with existing unprocessed episodes and remove duplicates
            all_unprocessed = list(set(unprocessed_episodes + new_unprocessed_episodes))
            
            # Update the unified media record with new unprocessed episodes
            if subscription.overseerr_request_id:
                from seerr.unified_media_manager import get_media_by_overseerr_request, update_media_details
                media_record = get_media_by_overseerr_request(subscription.overseerr_request_id)
                if media_record:
                    seasons_data = media_record.seasons_data or []
                    updated_seasons = []
                    
                    for season_data in seasons_data:
                        if season_data.get('season_number') == season_number:
                            season_data['unprocessed_episodes'] = all_unprocessed
                            season_data['updated_at'] = datetime.utcnow().isoformat()
                        updated_seasons.append(season_data)
                    
                    update_media_details(
                        media_record.id,
                        seasons_data=updated_seasons
                    )
            
            # Update local list for consistency
            unprocessed_episodes = all_unprocessed
            
            logger.info(f"Updated database with {len(new_unprocessed_episodes)} new unprocessed episodes: {new_unprocessed_episodes}")
            logger.info(f"Total unprocessed episodes: {len(unprocessed_episodes)} - {unprocessed_episodes}")

        # If there are no episodes to process, skip
        if not episodes_to_process:
            logger.info(f"All episodes for {show_title} Season {season_number} are already confirmed. No processing needed.")
            continue

        # Navigate to the show page
        from seerr.browser import driver as browser_driver
        
        # Check queue status before title search or navigation
        if tmdb_id:
            from seerr.search import _check_queue_status
            if _check_queue_status(tmdb_id, 'tv'):
                logger.info(f"Show {show_title} (TMDB: {tmdb_id}) is not in queue. Skipping subscription check for this show.")
                continue
        
        # Check if IMDB ID is missing or invalid - if so, search by title (RARE FALLBACK)
        if not imdb_id or imdb_id.lower() == 'none' or (isinstance(imdb_id, str) and imdb_id.strip() == ''):
            logger.warning(f"IMDB ID is missing or invalid ({imdb_id}) for {show_title}. Performing title search fallback (rare case).")
            from seerr.search import search_dmm_by_title_and_extract_id
            import re
            
            # Extract year from title if present (format: "Title (Year)")
            year = None
            title_for_search = show_title
            year_match = re.search(r'\((\d{4})\)', show_title)
            if year_match:
                year = int(year_match.group(1))
                title_for_search = show_title.split('(')[0].strip()
            
            # Search DMM by title to find IMDB ID (pass tmdb_id for queue checks)
            found_imdb_id = search_dmm_by_title_and_extract_id(browser_driver, title_for_search, 'tv', year, tmdb_id)
            
            if found_imdb_id:
                logger.info(f"Found IMDB ID via title search: {found_imdb_id}. Using it instead of missing ID.")
                imdb_id = found_imdb_id
            else:
                logger.error(f"Could not find IMDB ID via title search for '{title_for_search}'. Skipping this show.")
                continue
        
        # Check queue status again before navigation
        if tmdb_id:
            from seerr.search import _check_queue_status
            if _check_queue_status(tmdb_id, 'tv'):
                logger.info(f"Show {show_title} (TMDB: {tmdb_id}) is not in queue. Stopping before navigation.")
                continue
        
        url = f"https://debridmediamanager.com/show/{imdb_id}/{season_number}"
        browser_driver.get(url)
        logger.info(f"Navigated to show page for Season {season_number}: {url}")
        
        # Wait for the page to load (ensure the status element is present)
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By
            from selenium.common.exceptions import TimeoutException
            
            WebDriverWait(browser_driver, 3).until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='status' and contains(@aria-live, 'polite')]"))
            )
            logger.info("Page load confirmed via status element.")
        except TimeoutException:
            logger.warning("Timeout waiting for page load status. Proceeding anyway.")

        # Process all episodes (new, failed, and verify)
        normalized_seasons = [f"Season {season_number}"]
        confirmed_seasons = set()
        is_tv_show = True
        
        # Check if all aired episodes are confirmed (including those not being processed in this run)
        all_episodes_confirmed = len(confirmed_episodes) >= current_aired_episodes and current_aired_episodes > 0
        
        new_failed_episodes = []  # Track episodes that fail in this run
        newly_confirmed_episodes = []  # Track episodes that are newly confirmed

        for episode_num, episode_id, episode_type in episodes_to_process:
            logger.info(f"Processing {episode_type} episode for {show_title} Season {season_number} {episode_id}")

            # Clear and update the filter box with episode-specific filter
            try:
                filter_input = WebDriverWait(browser_driver, 10).until(
                    EC.presence_of_element_located((By.ID, "query"))
                )
                episode_filter = f"S{season_number:02d}{episode_id}"
                full_filter = f"{TORRENT_FILTER_REGEX} {episode_filter}"
                type_slowly(browser_driver, filter_input, full_filter)  # Replace send_keys with slow typing
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
                    logger.success(f"{episode_id} already cached at RD (100%). Marking as confirmed.")
                    newly_confirmed_episodes.append(episode_id)
                    
                    # Update database immediately with confirmed episode
                    updated_confirmed = list(set(confirmed_episodes + [episode_id]))
                    updated_unprocessed = [ep for ep in unprocessed_episodes if ep != episode_id]
                    
                    # Update the unified media record with confirmed and unprocessed episodes
                    if subscription.overseerr_request_id:
                        from seerr.unified_media_manager import get_media_by_overseerr_request, update_media_details
                        media_record = get_media_by_overseerr_request(subscription.overseerr_request_id)
                        if media_record:
                            seasons_data = media_record.seasons_data or []
                            updated_seasons = []
                            
                            for season_data in seasons_data:
                                if season_data.get('season_number') == season_number:
                                    season_data['confirmed_episodes'] = updated_confirmed
                                    season_data['unprocessed_episodes'] = updated_unprocessed
                                    season_data['updated_at'] = datetime.utcnow().isoformat()
                                updated_seasons.append(season_data)
                            
                            update_media_details(
                                media_record.id,
                                seasons_data=updated_seasons
                            )
                    
                    # Update local lists for consistency
                    confirmed_episodes = updated_confirmed
                    unprocessed_episodes = updated_unprocessed
                    
                    logger.info(f"Updated database: {episode_id} confirmed, {len(updated_unprocessed)} unprocessed episodes remaining")
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
                                            newly_confirmed_episodes.append(episode_id)
                                            
                                            # Update database immediately with confirmed episode
                                            updated_confirmed = list(set(confirmed_episodes + [episode_id]))
                                            updated_unprocessed = [ep for ep in unprocessed_episodes if ep != episode_id]
                                            
                                            # Update the unified media record with confirmed and unprocessed episodes
                                            if subscription.overseerr_request_id:
                                                from seerr.unified_media_manager import get_media_by_overseerr_request, update_media_details
                                                media_record = get_media_by_overseerr_request(subscription.overseerr_request_id)
                                                if media_record:
                                                    seasons_data = media_record.seasons_data or []
                                                    updated_seasons = []
                                                    
                                                    for season_data in seasons_data:
                                                        if season_data.get('season_number') == season_number:
                                                            season_data['confirmed_episodes'] = updated_confirmed
                                                            season_data['unprocessed_episodes'] = updated_unprocessed
                                                            season_data['updated_at'] = datetime.utcnow().isoformat()
                                                        updated_seasons.append(season_data)
                                                    
                                                    update_media_details(
                                                        media_record.id,
                                                        seasons_data=updated_seasons
                                                    )
                                            
                                            # Update local lists for consistency
                                            confirmed_episodes = updated_confirmed
                                            unprocessed_episodes = updated_unprocessed
                                            
                                            # Update completion status
                                            all_episodes_confirmed = len(confirmed_episodes) >= current_aired_episodes and current_aired_episodes > 0
                                            
                                            logger.info(f"Updated database: {episode_id} confirmed, {len(updated_unprocessed)} unprocessed episodes remaining")
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
                        
                        # Update database immediately with failed episode
                        updated_failed = list(set(failed_episodes + [episode_id]))
                        updated_unprocessed = [ep for ep in unprocessed_episodes if ep != episode_id]
                        
                        # Update the unified media record with failed and unprocessed episodes
                        if subscription.overseerr_request_id:
                            from seerr.unified_media_manager import get_media_by_overseerr_request, update_media_details
                            media_record = get_media_by_overseerr_request(subscription.overseerr_request_id)
                            if media_record:
                                seasons_data = media_record.seasons_data or []
                                updated_seasons = []
                                
                                for season_data in seasons_data:
                                    if season_data.get('season_number') == season_number:
                                        season_data['failed_episodes'] = updated_failed
                                        season_data['unprocessed_episodes'] = updated_unprocessed
                                        season_data['updated_at'] = datetime.utcnow().isoformat()
                                    updated_seasons.append(season_data)
                                
                                update_media_details(
                                    media_record.id,
                                    seasons_data=updated_seasons
                                )
                        
                        # Update local lists for consistency
                        failed_episodes = updated_failed
                        unprocessed_episodes = updated_unprocessed
                        
                        # Update completion status
                        all_episodes_confirmed = len(confirmed_episodes) >= current_aired_episodes and current_aired_episodes > 0
                        
                        logger.info(f"Updated database: {episode_id} failed, {len(updated_unprocessed)} unprocessed episodes remaining")

                except TimeoutException:
                    logger.warning(f"No result boxes found for {episode_id}")
                    new_failed_episodes.append(episode_id)
                    all_episodes_confirmed = False
                    
                    # Update database immediately with failed episode
                    updated_failed = list(set(failed_episodes + [episode_id]))
                    updated_unprocessed = [ep for ep in unprocessed_episodes if ep != episode_id]
                    
                    # Update the unified media record with failed and unprocessed episodes
                    if subscription.overseerr_request_id:
                        from seerr.unified_media_manager import get_media_by_overseerr_request, update_media_details
                        media_record = get_media_by_overseerr_request(subscription.overseerr_request_id)
                        if media_record:
                            seasons_data = media_record.seasons_data or []
                            updated_seasons = []
                            
                            for season_data in seasons_data:
                                if season_data.get('season_number') == season_number:
                                    season_data['failed_episodes'] = updated_failed
                                    season_data['unprocessed_episodes'] = updated_unprocessed
                                    season_data['updated_at'] = datetime.utcnow().isoformat()
                                updated_seasons.append(season_data)
                            
                            update_media_details(
                                media_record.id,
                                seasons_data=updated_seasons
                            )
                    
                    # Update local lists for consistency
                    failed_episodes = updated_failed
                    unprocessed_episodes = updated_unprocessed
                    
                    # Update completion status
                    all_episodes_confirmed = len(confirmed_episodes) >= current_aired_episodes and current_aired_episodes > 0
                    
                    logger.info(f"Updated database: {episode_id} failed (timeout), {len(updated_unprocessed)} unprocessed episodes remaining")

            except TimeoutException:
                logger.error(f"Filter input with ID 'query' not found for {episode_id}")
                new_failed_episodes.append(episode_id)
                all_episodes_confirmed = False
                
                # Update database immediately with failed episode
                updated_failed = list(set(failed_episodes + [episode_id]))
                updated_unprocessed = [ep for ep in unprocessed_episodes if ep != episode_id]
                
                # Update the unified media record with failed and unprocessed episodes
                if subscription.overseerr_request_id:
                    from seerr.unified_media_manager import get_media_by_overseerr_request, update_media_details
                    media_record = get_media_by_overseerr_request(subscription.overseerr_request_id)
                    if media_record:
                        seasons_data = media_record.seasons_data or []
                        updated_seasons = []
                        
                        for season_data in seasons_data:
                            if season_data.get('season_number') == season_number:
                                season_data['failed_episodes'] = updated_failed
                                season_data['unprocessed_episodes'] = updated_unprocessed
                                season_data['updated_at'] = datetime.utcnow().isoformat()
                            updated_seasons.append(season_data)
                        
                        update_media_details(
                            media_record.id,
                            seasons_data=updated_seasons
                        )
                
                # Update local lists for consistency
                failed_episodes = updated_failed
                unprocessed_episodes = updated_unprocessed
                
                # Update completion status
                all_episodes_confirmed = len(confirmed_episodes) >= current_aired_episodes and current_aired_episodes > 0
                
                logger.info(f"Updated database: {episode_id} failed (filter timeout), {len(updated_unprocessed)} unprocessed episodes remaining")

        # Reset the filter
        try:
            filter_input = browser_driver.find_element(By.ID, "query")
            type_slowly(browser_driver, filter_input, TORRENT_FILTER_REGEX)  # Slow typing for reset
            logger.info(f"Reset filter to default: {TORRENT_FILTER_REGEX}")
        except NoSuchElementException:
            logger.warning("Could not reset filter to default using ID 'query'")

        # Log final processing summary (database was updated live during processing)
        logger.info(f"Processing complete for {show_title} Season {season_number}:")
        logger.info(f"  - Confirmed episodes: {len(confirmed_episodes)} - {confirmed_episodes}")
        logger.info(f"  - Unprocessed episodes: {len(unprocessed_episodes)} - {unprocessed_episodes}")
        logger.info(f"  - Failed episodes: {len(failed_episodes)} - {failed_episodes}")

        if all_episodes_confirmed:
            logger.info(f"Successfully processed all episodes for {show_title} Season {season_number}")
            
            # Update processed media status to completed if all episodes are confirmed
            if USE_DATABASE and subscription.overseerr_request_id:
                from seerr.unified_media_manager import update_media_processing_status, get_media_by_overseerr_request, update_media_details
                
                # Get the media record using the subscription's overseerr_request_id
                media_record = get_media_by_overseerr_request(subscription.overseerr_request_id)
                if media_record:
                    # Update the season status to completed in seasons_data
                    seasons_data = media_record.seasons_data or []
                    updated_seasons = []
                    
                    for season_data in seasons_data:
                        if season_data.get('season_number') == season_number:
                            # Mark this season as completed
                            season_data['status'] = 'completed'
                            season_data['is_discrepant'] = False
                            season_data['updated_at'] = datetime.utcnow().isoformat()
                            season_data['confirmed_episodes'] = confirmed_episodes
                            season_data['unprocessed_episodes'] = []
                        updated_seasons.append(season_data)
                    
                    # Check if all seasons are now completed
                    all_seasons_completed = True
                    for season_data in updated_seasons:
                        if season_data.get('status') != 'completed':
                            all_seasons_completed = False
                            break
                    
                    # Update the media record
                    update_media_details(
                        media_record.id,
                        seasons_data=updated_seasons,
                        is_subscribed=True,
                        subscription_active=True,
                        subscription_last_checked=datetime.utcnow()
                    )
                    
                    # If all seasons are completed, mark the overall show as completed
                    if all_seasons_completed:
                        update_media_processing_status(
                            media_record.id,
                            'completed',
                            'all_seasons_completed',
                            extra_data={'all_episodes_confirmed': True}
                        )
                        logger.success(f"All seasons completed for {show_title}. Marked show as completed.")
                    
                    logger.info(f"Updated processed media status to completed and set subscription for {show_title} Season {season_number}")
        else:
            logger.warning(f"Failed to process some episodes for {show_title} Season {season_number}. Failed episodes: {new_failed_episodes}")

    logger.info("Completed show subscription check.")

async def search_individual_episodes(imdb_id, movie_title, season_number, season_details, driver, tmdb_id=None):
    """
    Search for and process individual episodes for a TV show season with a discrepancy.
    Updates database with failed episodes for later reprocessing.
    
    Args:
        imdb_id (str): IMDb ID of the show
        movie_title (str): Title of the show with year (e.g., "Daredevil: Born Again (2025)")
        season_number (int): Season number with discrepancy
        season_details (dict): Season details from Trakt, including 'aired_episodes'
        driver (WebDriver): Selenium WebDriver instance
        tmdb_id (int, optional): TMDB ID for queue status checks
    
    Returns:
        bool: True if all episodes were successfully processed or already cached, False otherwise
    """
    # Check queue status before starting episode processing
    if tmdb_id:
        from seerr.search import _check_queue_status
        if _check_queue_status(tmdb_id, 'tv'):
            logger.info(f"Item {movie_title} (TMDB: {tmdb_id}) is not in queue. Stopping episode search.")
            return False
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
    
    # Get the list of episodes to process from the season details
    unprocessed_episodes = season_details.get('unprocessed_episodes', [])
    failed_episodes_list = season_details.get('failed_episodes', [])
    confirmed_episodes = season_details.get('confirmed_episodes', [])
    
    # Determine which episodes to process
    # Priority: unprocessed episodes > failed episodes > all episodes
    if unprocessed_episodes:
        episodes_to_process = unprocessed_episodes
        logger.info(f"Found {len(unprocessed_episodes)} unprocessed episodes. Processing those first.")
    elif failed_episodes_list:
        episodes_to_process = failed_episodes_list
        logger.info(f"Found {len(failed_episodes_list)} failed episodes. Processing those.")
    else:
        # No unprocessed or failed episodes, process all episodes
        episodes_to_process = [f"E{str(i).zfill(2)}" for i in range(1, aired_episodes + 1)]
        logger.info(f"No unprocessed or failed episodes found. Processing all {len(episodes_to_process)} episodes.")
    
    logger.info(f"Episodes to process: {episodes_to_process}")
    
    all_confirmed = True  # Track if all episodes are successfully processed or already cached
    failed_episodes = []  # Track episodes that fail to process
    
    # Get discrepancy information from database instead of external JSON file
    discrepancy_entry = None
    if USE_DATABASE:
        try:
            from seerr.unified_models import UnifiedMedia
            from seerr.database import get_db
            db = get_db()
            try:
                # Find the TV show in the database - try exact match first, then partial match
                tv_show = db.query(UnifiedMedia).filter(
                    UnifiedMedia.title == movie_title,
                    UnifiedMedia.media_type == 'tv'
                ).first()
                
                # If no exact match, try to find by partial title match
                if not tv_show:
                    # No exact title match, trying partial match
                    # Extract the base title without year for partial matching
                    base_title = movie_title.split(' (')[0] if ' (' in movie_title else movie_title
                    tv_show = db.query(UnifiedMedia).filter(
                        UnifiedMedia.title.like(f"%{base_title}%"),
                        UnifiedMedia.media_type == 'tv'
                    ).first()
                    if tv_show:
                        logger.info(f"Found TV show by partial match: '{tv_show.title}' for '{movie_title}'")
                
                if not tv_show:
                    logger.warning(f"No TV show found in database for '{movie_title}'")
                    return False
                
                if tv_show and tv_show.seasons_data:
                    # Look for the specific season in seasons_data
                    for season_data in tv_show.seasons_data:
                        if (isinstance(season_data, dict) and 
                            season_data.get('season_number') == season_number and
                            season_data.get('is_discrepant', False)):
                            discrepancy_entry = {
                                'show_title': movie_title,
                                'season_number': season_number,
                                'season_details': season_data,
                                'trakt_show_id': tv_show.trakt_id,
                                'imdb_id': tv_show.imdb_id,
                                'seerr_id': tv_show.overseerr_request_id
                            }
                            break
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to load discrepancy information from database: {e}")
            return False
    
    if not discrepancy_entry:
        logger.error(f"No discrepancy entry found for {movie_title} Season {season_number} in database")
        return False

    # Check if IMDB ID is missing or invalid - if so, search by title (RARE FALLBACK)
    if not imdb_id or imdb_id.lower() == 'none' or (isinstance(imdb_id, str) and imdb_id.strip() == ''):
        logger.warning(f"IMDB ID is missing or invalid ({imdb_id}) for {movie_title}. Performing title search fallback (rare case).")
        from seerr.search import search_dmm_by_title_and_extract_id
        import re
        
        # Extract year from title if present (format: "Title (Year)")
        year = None
        title_for_search = movie_title
        year_match = re.search(r'\((\d{4})\)', movie_title)
        if year_match:
            year = int(year_match.group(1))
            title_for_search = movie_title.split('(')[0].strip()
        
        # Use the same driver instance for consistency
        from seerr.browser import driver as browser_driver
        if driver is None:
            driver = browser_driver
        
        # Check queue status before title search
        if tmdb_id:
            from seerr.search import _check_queue_status
            if _check_queue_status(tmdb_id, 'tv'):
                logger.info(f"Item {movie_title} (TMDB: {tmdb_id}) is not in queue. Stopping before title search.")
                return False
        
        # Search DMM by title to find IMDB ID (pass tmdb_id for queue checks)
        found_imdb_id = search_dmm_by_title_and_extract_id(driver, title_for_search, 'tv', year, tmdb_id)
        
        if found_imdb_id:
            logger.info(f"Found IMDB ID via title search: {found_imdb_id}. Using it instead of missing ID.")
            imdb_id = found_imdb_id
        else:
            logger.error(f"Could not find IMDB ID via title search for '{title_for_search}'. Cannot proceed.")
            return False
    
    # Navigate to the show page with season
    url = f"https://debridmediamanager.com/show/{imdb_id}/{season_number}"
    from seerr.browser import driver as browser_driver
    
    # Use the same driver instance for consistency
    if driver is None:
        driver = browser_driver
    
    # Navigate to the season-specific URL
    driver.get(url)
    logger.info(f"Navigated to show page for Season {season_number}: {url}")
    
    # Wait for the page to load (ensure the status element is present)
    try:
        WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.XPATH, "//div[@role='status' and contains(@aria-live, 'polite')]"))
        )
        logger.info("Page load confirmed via status element.")
    except TimeoutException:
        logger.warning("Timeout waiting for page load status. Proceeding anyway.")
        
    # Set up parameters for check_red_buttons
    normalized_seasons = [f"Season {season_number}"]
    confirmed_seasons = set()
    is_tv_show = True
    
    # Process only the episodes that need processing
    for episode_id in episodes_to_process:
        logger.info(f"Searching for {movie_title} Season {season_number} {episode_id}")
        
        # Clear and update the filter box with episode-specific filter
        try:
            filter_input = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.ID, "query"))
            )
            episode_filter = f"S{season_number:02d}{episode_id}"  # e.g., "S01E01"
            full_filter = f"{TORRENT_FILTER_REGEX} {episode_filter}"
            type_slowly(driver, filter_input, full_filter)  # Replace send_keys with slow typing
            logger.info(f"Applied filter: {full_filter}")
            
            try:
                click_show_more_results(driver, logger)
            except TimeoutException:
                logger.warning("Timed out while trying to click 'Show More Results'")
            except Exception as e:
                logger.error(f"Unexpected error in click_show_more_results: {e}")

            
            # Wait for results to update after applying the filter
            time.sleep(1)  # Adjust this delay if needed based on page response time
            
            # First pass: Check for existing RD (100%) using check_red_buttons
            try:
                confirmation_flag, confirmed_seasons = check_red_buttons(
                    driver, movie_title, normalized_seasons, confirmed_seasons, is_tv_show, episode_id=episode_id
                )
            except StaleElementReferenceException as e:
                logger.warning(f"Stale element reference in check_red_buttons for {episode_id}: {e}. Retrying...")
                time.sleep(2)
                try:
                    confirmation_flag, confirmed_seasons = check_red_buttons(
                        driver, movie_title, normalized_seasons, confirmed_seasons, is_tv_show, episode_id=episode_id
                    )
                except Exception as retry_e:
                    logger.error(f"Failed to retry check_red_buttons for {episode_id}: {retry_e}")
                    confirmation_flag = False
                    confirmed_seasons = set()
            
            if confirmation_flag:
                logger.success(f"{episode_id} already cached at RD (100%). Skipping further processing.")
                logger.info(f"{episode_id} already confirmed as cached. Moving to next episode.")
                
                # Update database to mark this episode as confirmed even though it's cached
                if USE_DATABASE:
                    try:
                        from seerr.database import get_db
                        from seerr.unified_models import UnifiedMedia
                        from sqlalchemy.orm.attributes import flag_modified
                        
                        db = get_db()
                        try:
                            # Find the TV show record by title
                            tv_show = db.query(UnifiedMedia).filter(
                                UnifiedMedia.title == movie_title,
                                UnifiedMedia.media_type == 'tv'
                            ).first()
                            
                            if not tv_show:
                                # Try by partial title match
                                base_title = movie_title.split(' (')[0] if ' (' in movie_title else movie_title
                                tv_show = db.query(UnifiedMedia).filter(
                                    UnifiedMedia.title.like(f"%{base_title}%"),
                                    UnifiedMedia.media_type == 'tv'
                                ).first()
                            
                            if tv_show and tv_show.seasons_data:
                                # Update the specific season and episode
                                for season_data in tv_show.seasons_data:
                                    if (isinstance(season_data, dict) and 
                                        season_data.get('season_number') == season_number):
                                        
                                        # Add episode to confirmed_episodes if not already there
                                        confirmed_episodes = season_data.get('confirmed_episodes', [])
                                        if episode_id not in confirmed_episodes:
                                            confirmed_episodes.append(episode_id)
                                            season_data['confirmed_episodes'] = confirmed_episodes
                                            season_data['updated_at'] = datetime.utcnow().isoformat()
                                            logger.info(f"Marked cached {episode_id} as confirmed in database")
                                        
                                        # Remove episode from unprocessed_episodes if it's there
                                        unprocessed_episodes = season_data.get('unprocessed_episodes', [])
                                        if episode_id in unprocessed_episodes:
                                            unprocessed_episodes.remove(episode_id)
                                            season_data['unprocessed_episodes'] = unprocessed_episodes
                                            logger.info(f"Removed cached {episode_id} from unprocessed episodes")
                                        
                                        # Update the database
                                        flag_modified(tv_show, 'seasons_data')
                                        tv_show.updated_at = datetime.utcnow()
                                        db.commit()
                                        logger.success(f"Updated database: Cached {episode_id} confirmed for {movie_title} Season {season_number}")
                                        break
                        finally:
                            db.close()
                    except Exception as e:
                        logger.error(f"Failed to update database for cached {episode_id}: {e}")
                
                continue
            
            # Second pass: Process uncached episodes
            try:
                result_boxes = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'border-black')]"))
                )
                
                # Before processing, undo any existing RD (0%) buttons to clean up the queue
                logger.info(f"Checking for any existing RD (0%) buttons to clean up before processing {episode_id}")
                try:
                    rd_zero_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'RD (0%)')]")
                    for rd_zero_button in rd_zero_buttons:
                        rd_zero_button.click()
                        logger.info(f"Clicked RD (0%) button to remove from queue")
                    if rd_zero_buttons:
                        time.sleep(2)  # Wait for buttons to update
                        logger.info(f"Cleaned up {len(rd_zero_buttons)} RD (0%) buttons")
                except Exception as e:
                    logger.warning(f"Error cleaning up RD (0%) buttons: {e}")
                
                episode_confirmed = False
                
                # Limit to first 10 torrents per episode to prevent excessive searching
                max_torrents_per_episode = 10
                limited_boxes = result_boxes[:max_torrents_per_episode]
                logger.info(f"Checking {len(limited_boxes)} torrent boxes for {episode_id} (out of {len(result_boxes)} available)")
                
                for i, result_box in enumerate(limited_boxes, start=1):
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
                                        
                                        # Update database to mark this episode as confirmed
                                        if USE_DATABASE and discrepancy_entry:
                                            try:
                                                from seerr.database import get_db
                                                from seerr.unified_models import UnifiedMedia
                                                
                                                db = get_db()
                                                try:
                                                    # Find the TV show record by title (most reliable)
                                                    tv_show = db.query(UnifiedMedia).filter(
                                                        UnifiedMedia.title == movie_title,
                                                        UnifiedMedia.media_type == 'tv'
                                                    ).first()
                                                    
                                                    if not tv_show:
                                                        # Try by partial title match if exact match fails
                                                        base_title = movie_title.split(' (')[0] if ' (' in movie_title else movie_title
                                                        tv_show = db.query(UnifiedMedia).filter(
                                                            UnifiedMedia.title.like(f"%{base_title}%"),
                                                            UnifiedMedia.media_type == 'tv'
                                                        ).first()
                                                    
                                                    if tv_show and tv_show.seasons_data:
                                                        # Update the specific season and episode
                                                        for season_data in tv_show.seasons_data:
                                                            if (isinstance(season_data, dict) and 
                                                                season_data.get('season_number') == season_number):
                                                                
                                                                # Add episode to confirmed_episodes if not already there
                                                                confirmed_episodes = season_data.get('confirmed_episodes', [])
                                                                if episode_id not in confirmed_episodes:
                                                                    confirmed_episodes.append(episode_id)
                                                                    season_data['confirmed_episodes'] = confirmed_episodes
                                                                    season_data['updated_at'] = datetime.utcnow().isoformat()
                                                                    logger.info(f"Marked {episode_id} as confirmed in database")
                                                                
                                                                # Remove episode from unprocessed_episodes if it's there
                                                                unprocessed_episodes = season_data.get('unprocessed_episodes', [])
                                                                if episode_id in unprocessed_episodes:
                                                                    unprocessed_episodes.remove(episode_id)
                                                                    season_data['unprocessed_episodes'] = unprocessed_episodes
                                                                    logger.info(f"Removed {episode_id} from unprocessed episodes")
                                                                
                                                                # Update the database - explicitly mark seasons_data as changed
                                                                from sqlalchemy.orm.attributes import flag_modified
                                                                flag_modified(tv_show, 'seasons_data')
                                                                tv_show.updated_at = datetime.utcnow()
                                                                db.commit()
                                                                logger.success(f"Updated database: {episode_id} confirmed for {movie_title} Season {season_number}")
                                                                break
                                                finally:
                                                    db.close()
                                            except Exception as e:
                                                logger.error(f"Failed to update database for {episode_id}: {e}")
                                        
                                        logger.info(f"Found cached torrent for {episode_id}. Moving to next episode.")
                                        break  # Exit the loop - we found a cached torrent
                                    elif "RD (0%)" in rd_button_text:
                                        logger.warning(f"RD (0%) detected for {episode_id}. Clicking to undo and remove from queue.")
                                        
                                        # Click the specific "RD (0%)" button to undo it
                                        try:
                                            rd_button.click()  # Click the RD (0%) button to undo it
                                            logger.info(f"Clicked RD (0%) button for {episode_id} to undo the action.")
                                            
                                            # Wait a moment for the button state to change back
                                            time.sleep(2)
                                            
                                            # Verify the button changed back to "DL with RD" in the same box
                                            try:
                                                updated_button = result_box.find_element(By.XPATH, ".//button[contains(text(), 'DL with RD')]")
                                                logger.info(f"Successfully undid RD (0%) click for {episode_id}. Button reverted to 'DL with RD'.")
                                            except NoSuchElementException:
                                                logger.warning(f"Could not verify button reverted to 'DL with RD' for {episode_id}")
                                            
                                        except Exception as e:
                                            logger.error(f"Failed to click RD (0%) button for {episode_id}: {e}")
                                        
                                        episode_confirmed = False
                                        continue  # Try the next torrent box
                                    else:
                                        logger.warning(f"RD status: {rd_button_text} for {episode_id}. Undoing and trying next torrent.")
                                        rd_button.click()  # Undo the click
                                        episode_confirmed = False
                                        continue  # Try the next torrent box
                                except TimeoutException:
                                    logger.warning(f"Timeout waiting for RD status for {episode_id}. Undoing and trying next torrent.")
                                    # Try to undo the click if possible
                                    try:
                                        rd_button = driver.find_element(By.XPATH, ".//button[contains(text(), 'RD (')]")
                                        rd_button.click()
                                    except:
                                        pass
                                    episode_confirmed = False
                                    continue  # Try the next torrent box
                            else:
                                logger.warning(f"Failed to handle buttons for {episode_id} in box {i}")
                                continue
                    
                    except NoSuchElementException:
                        logger.warning(f"No title found in box {i} for {episode_id}")
                
                if not episode_confirmed:
                    if len(result_boxes) > max_torrents_per_episode:
                        logger.warning(f"Failed to confirm {episode_id} after checking {max_torrents_per_episode} torrents (out of {len(result_boxes)} available). No cached torrents found.")
                    else:
                        logger.error(f"Failed to confirm {episode_id} for {movie_title} Season {season_number} - no cached torrents found.")
                    failed_episodes.append(episode_id)
                    all_confirmed = False
                    
                    # Update database to mark this episode as failed
                    if USE_DATABASE and discrepancy_entry:
                        try:
                            from seerr.database import get_db
                            from seerr.unified_models import UnifiedMedia
                            from sqlalchemy.orm.attributes import flag_modified
                            
                            db = get_db()
                            try:
                                # Find the TV show record by title (most reliable)
                                tv_show = db.query(UnifiedMedia).filter(
                                    UnifiedMedia.title == movie_title,
                                    UnifiedMedia.media_type == 'tv'
                                ).first()
                                
                                if not tv_show:
                                    # Try by partial title match if exact match fails
                                    base_title = movie_title.split(' (')[0] if ' (' in movie_title else movie_title
                                    tv_show = db.query(UnifiedMedia).filter(
                                        UnifiedMedia.title.like(f"%{base_title}%"),
                                        UnifiedMedia.media_type == 'tv'
                                    ).first()
                                
                                if tv_show and tv_show.seasons_data:
                                    # Update the specific season and episode
                                    for season_data in tv_show.seasons_data:
                                        if (isinstance(season_data, dict) and 
                                            season_data.get('season_number') == season_number):
                                            
                                            # Add episode to failed_episodes if not already there
                                            failed_ep_list = season_data.get('failed_episodes', [])
                                            if episode_id not in failed_ep_list:
                                                failed_ep_list.append(episode_id)
                                                season_data['failed_episodes'] = failed_ep_list
                                                season_data['updated_at'] = datetime.utcnow().isoformat()
                                                logger.info(f"Marked {episode_id} as failed in database")
                                            
                                            # Update the database - explicitly mark seasons_data as changed
                                            flag_modified(tv_show, 'seasons_data')
                                            tv_show.updated_at = datetime.utcnow()
                                            db.commit()
                                            logger.warning(f"Updated database: {episode_id} failed for {movie_title} Season {season_number}")
                                            break
                            finally:
                                db.close()
                        except Exception as e:
                            logger.error(f"Failed to update database for failed {episode_id}: {e}")
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
        type_slowly(browser_driver, filter_input, TORRENT_FILTER_REGEX)  # Slow typing for reset
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

    # Update the database with the subscription data using the discrepancy_entry we already have
    try:
        if discrepancy_entry:
            # Extract show details from discrepancy entry
            trakt_show_id = discrepancy_entry.get("trakt_show_id")
            imdb_id = discrepancy_entry.get("imdb_id")
            overseerr_request_id = discrepancy_entry.get("seerr_id")
            season_details = discrepancy_entry.get("season_details", {})
            
            if trakt_show_id and imdb_id:
                # Update or create subscription in database
                from seerr.unified_media_manager import update_media_details
                from seerr.unified_models import UnifiedMedia
                db = get_db()
                try:
                    # Find media record by trakt_id since we don't have tmdb_id
                    media_record = db.query(UnifiedMedia).filter(
                        UnifiedMedia.trakt_id == str(trakt_show_id),
                        UnifiedMedia.media_type == 'tv'
                    ).first()
                    
                    if media_record:
                        success = update_media_details(
                            media_record.id,
                            overseerr_request_id=overseerr_request_id,
                            season_number=season_number,
                            episode_count=season_details.get("episode_count", 0),
                            aired_episodes=aired_episodes,
                            failed_episodes=failed_episodes,
                            seasons_processed=season_details
                        )
                    else:
                        success = False
                finally:
                    db.close()
                
                if success:
                    logger.info(f"Updated show subscription in database for {movie_title} Season {season_number}")
                else:
                    logger.error(f"Failed to update show subscription in database for {movie_title} Season {season_number}")
            else:
                logger.warning(f"Missing trakt_show_id or imdb_id for {movie_title} Season {season_number}, cannot save to database")
        else:
            logger.warning(f"Could not find discrepancy entry for {movie_title} Season {season_number}")
    except Exception as e:
        logger.error(f"Error updating database for {movie_title} Season {season_number}: {e}")

    # Update database with failed episodes instead of writing to JSON file
    if USE_DATABASE and failed_episodes:
        try:
            from seerr.unified_models import UnifiedMedia
            db = get_db()
            try:
                # Find the TV show in the database
                tv_show = db.query(UnifiedMedia).filter(
                    UnifiedMedia.title == movie_title,
                    UnifiedMedia.media_type == 'tv'
                ).first()
                
                if tv_show and tv_show.seasons_data:
                    # Update the specific season with failed episodes
                    updated_seasons_data = []
                    for season_data in tv_show.seasons_data:
                        if (isinstance(season_data, dict) and 
                            season_data.get('season_number') == season_number):
                            # Update this season with failed episodes
                            season_data['failed_episodes'] = failed_episodes
                            season_data['updated_at'] = datetime.utcnow().isoformat()
                        updated_seasons_data.append(season_data)
                    
                    # Update the TV show with the modified seasons data
                    tv_show.seasons_data = updated_seasons_data
                    db.commit()
                    logger.info(f"Updated database with {len(failed_episodes)} failed episodes for {movie_title} Season {season_number}")
                else:
                    logger.warning(f"Could not find TV show or seasons data for {movie_title} Season {season_number}")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to update database with failed episodes: {e}")

    logger.info(f"Completed processing {aired_episodes} episodes for {movie_title} Season {season_number}")
    return all_confirmed 

def search_individual_episodes_sync(imdb_id, movie_title, season_number, season_details, driver, tmdb_id=None):
    """
    Synchronous version of search_individual_episodes - this is a wrapper around the async function
    to be called from synchronous code.
    
    Args:
        imdb_id (str): IMDb ID of the show
        movie_title (str): Title of the show with year (e.g., "Daredevil: Born Again (2025)")
        season_number (int): Season number with discrepancy
        season_details (dict): Season details from Trakt, including 'aired_episodes'
        driver (WebDriver): Selenium WebDriver instance
        tmdb_id (int, optional): TMDB ID for queue status checks
    
    Returns:
        bool: True if all episodes were successfully processed or already cached, False otherwise
    """
    import asyncio
    
    # Create a new event loop and run the async function
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        return loop.run_until_complete(
            search_individual_episodes(imdb_id, movie_title, season_number, season_details, driver, tmdb_id)
        )
    finally:
        loop.close() 

# Utility functions for status endpoint
def get_queue_status():
    """Get the current status of all queues."""
    return {
        "movie_queue_size": movie_queue.qsize(),
        "movie_queue_max": movie_queue.maxsize,
        "tv_queue_size": tv_queue.qsize(),
        "tv_queue_max": tv_queue.maxsize,
        "is_processing": is_processing_queue,
        "total_queued": movie_queue.qsize() + tv_queue.qsize()
    }

async def get_detailed_queue_status():
    """Get detailed status of queues and processing state."""
    return {
        "queues": get_queue_status(),
        "scheduled_tasks": {
            "active_jobs": len(scheduler.get_jobs()),
            "scheduler_running": scheduler.running
        },
        "browser_available": browser_semaphore._value > 0,
        "scheduled_task_locked": scheduled_task_semaphore.locked()
    }

def update_queue_activity_timestamp():
    """Update the timestamp when queue activity occurs."""
    global last_queue_activity_time
    last_queue_activity_time = time.time()
    # Updated queue activity timestamp

def is_safe_to_refresh_library_stats(min_idle_seconds=30):
    """
    Check if it's safe to refresh library stats.
    
    Returns True only if:
    - All queues are empty
    - No queue processing is active
    - At least min_idle_seconds have passed since the last queue activity
    
    Args:
        min_idle_seconds (int): Minimum seconds queues must be idle
        
    Returns:
        bool: True if safe to refresh, False otherwise
    """
    current_time = time.time()
    time_since_last_activity = current_time - last_queue_activity_time
    
    # Check if queues are empty
    queues_empty = movie_queue.empty() and tv_queue.empty()
    
    # Check if processing is active
    processing_inactive = not is_processing_queue
    
    # Check if enough time has passed since last activity
    enough_time_passed = time_since_last_activity >= min_idle_seconds
    
    is_safe = queues_empty and processing_inactive and enough_time_passed
    
#    if not is_safe:
#        # Not safe to refresh library stats
#                    f"Processing inactive: {processing_inactive}, "
#                    f"Time since last activity: {time_since_last_activity:.1f}s (need {min_idle_seconds}s)")
    
    return is_safe 
