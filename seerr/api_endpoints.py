"""
API endpoints for SeerrBridge
Handles HTTP requests for configuration and task management
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
