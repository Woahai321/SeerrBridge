"""
API endpoints for SeerrBridge
Handles HTTP requests for configuration and task management
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import asyncio
import json
from seerr.task_config_manager import task_config
from seerr.background_tasks import refresh_all_scheduled_tasks, refresh_queue_sizes
from seerr.db_logger import log_info, log_error
from seerr.secure_config_manager import secure_config

app = FastAPI(title="SeerrBridge API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/refresh-tasks")
async def refresh_tasks():
    """Refresh all background tasks based on current database configuration"""
    try:
        log_info("API", "Refreshing background tasks from API request", module="api_endpoints", function="refresh_tasks")
        
        # Invalidate configuration cache
        task_config.invalidate_cache()
        
        # Refresh queue sizes
        refresh_queue_sizes()
        
        # Refresh all scheduled tasks
        await refresh_all_scheduled_tasks()
        
        return {
            "success": True,
            "message": "Background tasks refreshed successfully"
        }
    except Exception as e:
        log_error("API Error", f"Error refreshing tasks: {e}", module="api_endpoints", function="refresh_tasks")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/task-config")
async def get_task_config():
    """Get current task configuration"""
    try:
        config = task_config.get_all_task_configs()
        return {
            "success": True,
            "data": config
        }
    except Exception as e:
        log_error("API Error", f"Error getting task config: {e}", module="api_endpoints", function="get_task_config")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/task-config")
async def update_task_config(config_data: dict):
    """Update task configuration"""
    try:
        config_key = config_data.get('configKey')
        value = config_data.get('value')
        config_type = config_data.get('configType', 'string')
        description = config_data.get('description')
        
        if not config_key:
            raise HTTPException(status_code=400, detail="configKey is required")
        
        success = task_config.set_config(config_key, value, config_type, description)
        
        if success:
            # Trigger task refresh for task-related configs
            task_config_keys = [
                'enable_automatic_background_task',
                'enable_show_subscription_task',
                'refresh_interval_minutes',
                'movie_queue_maxsize',
                'tv_queue_maxsize',
                'token_refresh_interval_minutes',
                'movie_processing_check_interval_minutes',
                'library_refresh_interval_minutes',
                'subscription_check_interval_minutes',
                'background_tasks_enabled',
                'queue_processing_enabled',
                'scheduler_enabled'
            ]
            
            if config_key in task_config_keys:
                # Trigger refresh in background
                asyncio.create_task(refresh_all_scheduled_tasks())
            
            return {
                "success": True,
                "message": f"Configuration {config_key} updated successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update configuration")
            
    except Exception as e:
        log_error("API Error", f"Error updating task config: {e}", module="api_endpoints", function="update_task_config")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/re-queue-stuck-movies")
async def re_queue_stuck_movies():
    """Manually re-queue stuck movies"""
    try:
        from seerr.background_tasks import check_movie_processing
        await check_movie_processing()
        return {
            "success": True,
            "message": "Stuck movies re-queuing process completed"
        }
    except Exception as e:
        log_error("API Error", f"Error re-queuing stuck movies: {e}", module="api_endpoints", function="re_queue_stuck_movies")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/failed-items/stats")
async def get_failed_item_stats():
    """Get statistics about failed items"""
    try:
        from seerr.failed_item_manager import failed_item_manager
        stats = failed_item_manager.get_failed_item_stats()
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        log_error("API Error", f"Error getting failed item stats: {e}", module="api_endpoints", function="get_failed_item_stats")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/failed-items/retry")
async def retry_failed_items():
    """Manually retry failed items"""
    try:
        from seerr.failed_item_manager import process_failed_items
        retry_count = await process_failed_items()
        return {
            "success": True,
            "message": f"Retried {retry_count} failed items",
            "retry_count": retry_count
        }
    except Exception as e:
        log_error("API Error", f"Error retrying failed items: {e}", module="api_endpoints", function="retry_failed_items")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/config")
async def get_config():
    """Get all configuration values with proper masking for sensitive data"""
    try:
        # Get all configurations using the secure config manager
        configs = secure_config.get_all_configs()
        
        # Define sensitive keys that should be masked
        sensitive_keys = {
            'rd_access_token', 'rd_refresh_token', 'rd_client_id', 'rd_client_secret',
            'overseerr_api_key', 'trakt_api_key', 'discord_webhook_url',
            'db_password', 'mysql_root_password'
        }
        
        # Convert to the format expected by the frontend
        config_list = []
        for key, value in configs.items():
            # Determine config type based on value
            if isinstance(value, bool):
                config_type = 'bool'
            elif isinstance(value, int):
                config_type = 'int'
            elif isinstance(value, float):
                config_type = 'float'
            else:
                config_type = 'string'
            
            # Mask sensitive values for security
            display_value = value
            is_encrypted = False
            
            if key in sensitive_keys and value and isinstance(value, str):
                is_encrypted = True
                # Show first 3 and last 3 characters for sensitive values
                if len(value) > 6:
                    display_value = f"{value[:3]}{'*' * (len(value) - 6)}{value[-3:]}"
                elif len(value) > 3:
                    # For medium length values, show first 2 and last 2
                    display_value = f"{value[:2]}{'*' * (len(value) - 4)}{value[-2:]}"
                else:
                    # For very short values, just show asterisks
                    display_value = '*' * len(value)
            
            config_list.append({
                'config_key': key,
                'config_value': display_value,
                'config_type': config_type,
                'description': f"Configuration for {key}",
                'is_active': True,
                'is_encrypted': is_encrypted,
                'has_value': bool(value)  # Indicate if the value exists (even if encrypted)
            })
        
        return {
            "success": True,
            "configs": config_list
        }
    except Exception as e:
        log_error("API Error", f"Error getting config: {e}", module="api_endpoints", function="get_config")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/config/internal")
async def get_config_internal():
    """Get raw decrypted configuration values (INTERNAL USE ONLY)"""
    try:
        # Get all configurations using the secure config manager (already decrypted)
        configs = secure_config.get_all_configs()
        
        # Convert to dictionary format
        config_dict = {}
        for key, value in configs.items():
            # Store as string representation for consistency
            if isinstance(value, (bool, int, float)):
                config_dict[key] = str(value)
            elif value is None:
                config_dict[key] = ""
            else:
                config_dict[key] = value
        
        return {
            "success": True,
            "data": config_dict
        }
    except Exception as e:
        log_error("API Error", f"Error getting internal config: {e}", module="api_endpoints", function="get_config_internal")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/config")
async def update_config(config_data: dict):
    """Update configuration values using the secure config manager"""
    try:
        configs = config_data.get('configs', [])
        
        if not configs or not isinstance(configs, list):
            raise HTTPException(status_code=400, detail="Invalid configuration data")
        
        updated_count = 0
        errors = []
        
        for config in configs:
            try:
                config_key = config.get('config_key')
                config_value = config.get('config_value')
                config_type = config.get('config_type', 'string')
                description = config.get('description', f"Configuration for {config_key}")
                
                if not config_key:
                    errors.append("Missing config_key")
                    continue
                
                # Use the secure config manager to set the configuration
                success = secure_config.set_config(
                    key=config_key,
                    value=config_value,
                    config_type=config_type,
                    description=description
                )
                
                if success:
                    updated_count += 1
                    log_info("API", f"Updated configuration: {config_key}", module="api_endpoints", function="update_config")
                else:
                    errors.append(f"Failed to update {config_key}")
                    
            except Exception as e:
                error_msg = f"Error updating {config.get('config_key', 'unknown')}: {str(e)}"
                errors.append(error_msg)
                log_error("API Error", error_msg, module="api_endpoints", function="update_config")
        
        # Check if any task-related configurations were updated
        task_config_keys = [
            'enable_automatic_background_task',
            'enable_show_subscription_task',
            'refresh_interval_minutes',
            'movie_queue_maxsize',
            'tv_queue_maxsize',
            'token_refresh_interval_minutes',
            'movie_processing_check_interval_minutes',
            'library_refresh_interval_minutes',
            'subscription_check_interval_minutes',
            'background_tasks_enabled',
            'queue_processing_enabled',
            'scheduler_enabled',
            'headless_mode',
            'torrent_filter_regex',
            'max_movie_size',
            'max_episode_size'
        ]
        
        has_task_config_changes = any(
            config.get('config_key') in task_config_keys 
            for config in configs
        )
        
        if has_task_config_changes:
            # Trigger task refresh in background
            asyncio.create_task(refresh_all_scheduled_tasks())
            log_info("API", "Task configuration changes detected, refreshing tasks", module="api_endpoints", function="update_config")
        
        return {
            "success": True,
            "message": f"Updated {updated_count} configuration values",
            "updated_count": updated_count,
            "errors": errors,
            "task_refresh_triggered": has_task_config_changes
        }
        
    except Exception as e:
        log_error("API Error", f"Error updating config: {e}", module="api_endpoints", function="update_config")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/restart")
async def restart_service():
    """Restart the SeerrBridge service to reload configuration"""
    try:
        log_info("API", "Service restart requested", module="api_endpoints", function="restart_service")
        
        # Import the restart functionality
        import os
        import signal
        import sys
        
        # Schedule restart after a short delay to allow response to be sent
        def delayed_restart():
            import time
            time.sleep(1)
            os.kill(os.getpid(), signal.SIGTERM)
        
        import threading
        restart_thread = threading.Thread(target=delayed_restart)
        restart_thread.daemon = True
        restart_thread.start()
        
        return {
            "success": True,
            "message": "Service restart initiated"
        }
    except Exception as e:
        log_error("API Error", f"Error restarting service: {e}", module="api_endpoints", function="restart_service")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "SeerrBridge API"
    }

class TraktListFetchRequest(BaseModel):
    listId: str
    limit: Optional[int] = None
    listType: Optional[str] = None

@app.post("/trakt-lists/fetch")
async def fetch_trakt_list(request_data: TraktListFetchRequest):
    """Fetch items from a Trakt list or Letterboxd list"""
    try:
        list_id = request_data.listId
        limit = request_data.limit
        list_type = request_data.listType
        
        # Auto-detect list type if not provided
        if not list_type:
            list_id_lower = list_id.lower()
            if 'letterboxd.com' in list_id_lower or list_id_lower.startswith('letterboxd/'):
                list_type = "letterboxd"
            else:
                list_type = "trakt"
        
        if not list_id:
            raise HTTPException(status_code=400, detail="listId is required")
        
        log_info("API", f"Fetching {list_type} list: {list_id}", module="api_endpoints", function="fetch_trakt_list")
        
        # Route to appropriate provider based on list type
        if list_type == "letterboxd":
            from seerr.letterboxd_lists import fetch_letterboxd_list
            import concurrent.futures
            # Run HTTP requests in a thread executor to avoid blocking the async event loop
            # requests.get() is blocking I/O, so we run it in a separate thread
            log_info("API", f"Starting Letterboxd list fetch in thread executor", module="api_endpoints", function="fetch_trakt_list")
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(fetch_letterboxd_list, list_id, limit if limit else None)
                try:
                    items = future.result(timeout=300)  # 5 minute timeout
                    log_info("API", f"Letterboxd list fetch completed. Got {len(items)} items", module="api_endpoints", function="fetch_trakt_list")
                except concurrent.futures.TimeoutError:
                    log_error("API Error", f"Letterboxd list fetch timed out after 5 minutes", module="api_endpoints", function="fetch_trakt_list")
                    raise HTTPException(status_code=504, detail="Letterboxd list fetch timed out")
                except Exception as e:
                    log_error("API Error", f"Error in Letterboxd list fetch thread: {e}", module="api_endpoints", function="fetch_trakt_list")
                    raise
        else:
            from seerr.trakt_lists import fetch_trakt_list
            items = fetch_trakt_list(list_id, limit=limit if limit else None)
        
        return {
            "success": True,
            "items": items,
            "count": len(items)
        }
    except ValueError as e:
        log_error("API Error", f"Error fetching list: {e}", module="api_endpoints", function="fetch_trakt_list")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log_error("API Error", f"Error fetching list: {e}", module="api_endpoints", function="fetch_trakt_list")
        raise HTTPException(status_code=500, detail=str(e))

class TraktSearchByImdbRequest(BaseModel):
    imdb_id: str

@app.post("/trakt-lists/search-by-imdb")
async def search_trakt_by_imdb(request_data: TraktSearchByImdbRequest):
    """Search Trakt by IMDB ID to get TMDB ID"""
    try:
        from seerr.trakt_lists import search_trakt_by_imdb_id
        
        imdb_id = request_data.imdb_id
        
        if not imdb_id:
            raise HTTPException(status_code=400, detail="imdb_id is required")
        
        result = search_trakt_by_imdb_id(imdb_id)
        
        if result and result.get('tmdb_id'):
            return {
                "success": True,
                "tmdb_id": result['tmdb_id']
            }
        else:
            return {
                "success": False,
                "error": "No TMDB ID found"
            }
    except Exception as e:
        log_error("API Error", f"Error searching Trakt by IMDB: {e}", module="api_endpoints", function="search_trakt_by_imdb")
        raise HTTPException(status_code=500, detail=str(e))

class TraktSearchByTitleRequest(BaseModel):
    title: str
    year: Optional[int] = None
    media_type: str = 'movie'

@app.post("/trakt-lists/search-by-title")
async def search_trakt_by_title(request_data: TraktSearchByTitleRequest):
    """Search Trakt by title and year to get TMDB ID"""
    try:
        from seerr.trakt_lists import search_trakt_by_title
        
        title = request_data.title
        year = request_data.year
        media_type = request_data.media_type
        
        if not title:
            raise HTTPException(status_code=400, detail="title is required")
        
        result = search_trakt_by_title(title, year, media_type)
        
        if result and result.get('tmdb_id'):
            return {
                "success": True,
                "tmdb_id": result['tmdb_id']
            }
        else:
            return {
                "success": False,
                "error": "No TMDB ID found"
            }
    except Exception as e:
        log_error("API Error", f"Error searching Trakt by title: {e}", module="api_endpoints", function="search_trakt_by_title")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/trakt-lists/get-or-create")
async def get_or_create_list(request_data: TraktListFetchRequest):
    """Get or create a Trakt list in the database"""
    try:
        from seerr.trakt_list_manager import get_or_create_trakt_list
        
        list_identifier = request_data.listId
        list_name = request_data.listId  # Use listId as name by default
        list_type = request_data.listType
        
        trakt_list = get_or_create_trakt_list(
            list_identifier=list_identifier,
            list_type=list_type,
            list_name=list_name
        )
        
        # trakt_list is now a dictionary, not a SQLAlchemy object
        return {
            "success": True,
            "listId": trakt_list['id'],
            "listIdentifier": trakt_list['list_identifier'],
            "listName": trakt_list['list_name'],
            "listType": trakt_list['list_type'],
            "syncCount": trakt_list.get('sync_count', 0) or 0
        }
    except Exception as e:
        log_error("API Error", f"Error getting/creating Trakt list: {e}", module="api_endpoints", function="get_or_create_list")
        raise HTTPException(status_code=500, detail=str(e))

class CreateSyncHistoryRequest(BaseModel):
    traktListId: int
    syncType: str = 'manual'
    totalItems: int = 0

@app.post("/trakt-lists/create-sync-history")
async def create_sync_history(request_data: CreateSyncHistoryRequest):
    """Create a new sync history record"""
    try:
        from seerr.trakt_list_manager import create_sync_history
        
        sync_history = create_sync_history(
            trakt_list_id=request_data.traktListId,
            sync_type=request_data.syncType,
            total_items=request_data.totalItems
        )
        
        # sync_history is now a dictionary, not a SQLAlchemy object
        return {
            "success": True,
            "sessionId": sync_history['sessionId'],
            "syncHistoryId": sync_history['id']
        }
    except Exception as e:
        log_error("API Error", f"Error creating sync history: {e}", module="api_endpoints", function="create_sync_history")
        raise HTTPException(status_code=500, detail=str(e))

class SaveSyncItemRequest(BaseModel):
    sessionId: str
    item: dict
    status: str
    matchMethod: Optional[str] = None
    errorMessage: Optional[str] = None
    overseerrRequestId: Optional[int] = None

@app.post("/trakt-lists/save-sync-item")
async def save_sync_item(request_data: SaveSyncItemRequest):
    """Save a sync item to the database"""
    try:
        from seerr.trakt_list_manager import get_sync_history_by_session, save_sync_item
        
        # Get sync history to get the ID
        sync_history = get_sync_history_by_session(request_data.sessionId)
        if not sync_history:
            raise HTTPException(status_code=404, detail="Sync history not found")
        
        item_id = save_sync_item(
            sync_history_id=sync_history.id,
            item=request_data.item,
            status=request_data.status,
            match_method=request_data.matchMethod,
            error_message=request_data.errorMessage,
            overseerr_request_id=request_data.overseerrRequestId
        )
        
        return {
            "success": True,
            "itemId": item_id
        }
    except HTTPException:
        raise
    except Exception as e:
        log_error("API Error", f"Error saving sync item: {e}", module="api_endpoints", function="save_sync_item")
        raise HTTPException(status_code=500, detail=str(e))

class UpdateSyncHistoryRequest(BaseModel):
    sessionId: str
    status: str
    itemsRequested: int = 0
    itemsAlreadyRequested: int = 0
    itemsAlreadyAvailable: int = 0
    itemsNotFound: int = 0
    itemsErrors: int = 0
    errorMessage: Optional[str] = None
    details: Optional[dict] = None

@app.post("/trakt-lists/update-sync-history")
async def update_sync_history(request_data: UpdateSyncHistoryRequest):
    """Update sync history with final results"""
    try:
        from seerr.trakt_list_manager import update_sync_history
        
        success = update_sync_history(
            session_id=request_data.sessionId,
            status=request_data.status,
            items_requested=request_data.itemsRequested,
            items_already_requested=request_data.itemsAlreadyRequested,
            items_already_available=request_data.itemsAlreadyAvailable,
            items_not_found=request_data.itemsNotFound,
            items_errors=request_data.itemsErrors,
            error_message=request_data.errorMessage
        )
        
        return {
            "success": success
        }
    except Exception as e:
        log_error("API Error", f"Error updating sync history: {e}", module="api_endpoints", function="update_sync_history")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/trakt-lists")
async def get_trakt_lists(active_only: bool = True):
    """Get all Trakt lists"""
    try:
        from seerr.trakt_list_manager import get_trakt_lists_with_totals
        
        lists_with_totals = get_trakt_lists_with_totals(active_only=active_only)
        
        return {
            "success": True,
            "lists": [
                {
                    "id": item['list']['id'],
                    "listIdentifier": item['list']['list_identifier'],
                    "listName": item['list']['list_name'],
                    "listType": item['list']['list_type'],
                    "itemCount": item['total_items'],  # Total items from get_sync_items_for_list
                    "syncCount": item['list']['sync_count'],
                    "lastSynced": item['list']['last_synced'],
                    "lastSyncStatus": item['list']['last_sync_status'],
                    "autoSync": item['list']['auto_sync'],
                    "syncIntervalHours": item['list']['sync_interval_hours'],
                    "isActive": item['list']['is_active'],
                    "createdAt": item['list']['created_at'],
                    "updatedAt": item['list']['updated_at']
                }
                for item in lists_with_totals
            ]
        }
    except Exception as e:
        log_error("API Error", f"Error getting Trakt lists: {e}", module="api_endpoints", function="get_trakt_lists")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/trakt-lists/history/{session_id}/items")
async def get_sync_history_items(session_id: str):
    """Get all items for a specific sync session"""
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    
    def _get_items_sync():
        """Synchronous function to run in thread pool"""
        from seerr.trakt_list_manager import get_sync_history_by_session
        from seerr.database import TraktListSyncItem, get_db
        
        # First verify the sync history exists
        sync_history = get_sync_history_by_session(session_id)
        if not sync_history:
            return None
        
        # Query items directly to avoid lazy loading issues
        db = get_db()
        try:
            items = db.query(TraktListSyncItem).filter(
                TraktListSyncItem.sync_history_id == sync_history.id
            ).order_by(TraktListSyncItem.synced_at.desc()).all()
            
            # Convert to dicts while session is still open
            items_data = [
                {
                    "id": item.id,
                    "title": item.title,
                    "year": item.year,
                    "mediaType": item.media_type,
                    "tmdbId": item.tmdb_id,
                    "imdbId": item.imdb_id,
                    "seasonNumber": item.season_number,
                    "status": item.status,
                    "matchMethod": item.match_method,
                    "errorMessage": item.error_message,
                    "overseerrRequestId": item.overseerr_request_id,
                    "unifiedMediaId": item.unified_media_id,
                    "syncedAt": item.synced_at.isoformat() if item.synced_at else None
                }
                for item in items
            ]
            return items_data
        finally:
            db.close()
    
    try:
        # Run database operations in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            items_data = await loop.run_in_executor(executor, _get_items_sync)
        
        if items_data is None:
            raise HTTPException(status_code=404, detail="Sync history not found")
        
        return {
            "success": True,
            "items": items_data
        }
    except HTTPException:
        raise
    except Exception as e:
        log_error("API Error", f"Error getting sync history items: {e}", module="api_endpoints", function="get_sync_history_items")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/trakt-lists/history")
async def get_all_sync_history(limit: int = 100):
    """Get all sync history records across all lists"""
    try:
        from seerr.trakt_list_manager import get_all_sync_history
        
        history = get_all_sync_history(limit=limit)
        
        return {
            "success": True,
            "history": history,
            "count": len(history)
        }
    except Exception as e:
        log_error("API Error", f"Error getting all sync history: {e}", module="api_endpoints", function="get_all_sync_history")
        raise HTTPException(status_code=500, detail=str(e))

# IMPORTANT: More specific routes must be defined BEFORE more general ones
# /trakt-lists/{list_id}/items must come before /trakt-lists/{list_id}/history
@app.get("/trakt-lists/{list_id}/items")
async def get_list_items(list_id: int):
    """Get all unique items from database sync history for a specific list"""
    try:
        from seerr.trakt_list_manager import get_sync_items_for_list
        
        log_info("API", f"Getting items for list ID: {list_id}", module="api_endpoints", function="get_list_items")
        
        items = get_sync_items_for_list(list_id, limit=1000)
        
        log_info("API", f"Found {len(items)} items for list ID: {list_id}", module="api_endpoints", function="get_list_items")
        
        # Convert to format expected by frontend
        items_formatted = [
            {
                "title": item.get("title"),
                "year": item.get("year"),
                "media_type": item.get("media_type"),
                "tmdb_id": item.get("tmdb_id"),
                "imdb_id": item.get("imdb_id"),
                "overview": item.get("overview"),
                "status": item.get("status"),
                "match_method": item.get("match_method"),
                "error_message": item.get("error_message"),
                "unified_media_id": item.get("unified_media_id"),
                # Cached image information - ONLY cached images, no external URLs
                "has_poster_image": item.get("has_poster_image", False),
                "poster_image_format": item.get("poster_image_format"),
                "has_thumb_image": item.get("has_thumb_image", False),
                "thumb_image_format": item.get("thumb_image_format"),
                "has_fanart_image": item.get("has_fanart_image", False),
                "fanart_image_format": item.get("fanart_image_format")
            }
            for item in items
        ]
        
        return {
            "success": True,
            "items": items_formatted,
            "count": len(items_formatted),
            "source": "database"  # Indicate these came from database, not Trakt API
        }
    except Exception as e:
        log_error("API Error", f"Error getting list items: {e}", module="api_endpoints", function="get_list_items")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/trakt-lists/{list_id}/history")
async def get_list_sync_history(list_id: int, limit: int = 50):
    """Get sync history for a specific list"""
    try:
        from seerr.trakt_list_manager import get_sync_history
        
        history = get_sync_history(trakt_list_id=list_id, limit=limit)
        
        return {
            "success": True,
            "history": [
                {
                    "id": h.id,
                    "sessionId": h.session_id,
                    "syncType": h.sync_type,
                    "status": h.status,
                    "startTime": h.start_time.isoformat(),
                    "endTime": h.end_time.isoformat() if h.end_time else None,
                    "totalItems": h.total_items,
                    "itemsRequested": h.items_requested,
                    "itemsAlreadyRequested": h.items_already_requested,
                    "itemsAlreadyAvailable": h.items_already_available,
                    "itemsNotFound": h.items_not_found,
                    "itemsErrors": h.items_errors,
                    "errorMessage": h.error_message
                }
                for h in history
            ]
        }
    except Exception as e:
        log_error("API Error", f"Error getting sync history: {e}", module="api_endpoints", function="get_list_sync_history")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/trakt-lists/{list_id}")
async def delete_trakt_list_endpoint(list_id: int):
    """Delete a Trakt list"""
    try:
        from seerr.trakt_list_manager import delete_trakt_list
        
        success = delete_trakt_list(list_id)
        
        if success:
            return {
                "success": True,
                "message": "List deleted successfully"
            }
        else:
            raise HTTPException(status_code=404, detail="List not found")
    except HTTPException:
        raise
    except Exception as e:
        log_error("API Error", f"Error deleting Trakt list: {e}", module="api_endpoints", function="delete_trakt_list_endpoint")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
