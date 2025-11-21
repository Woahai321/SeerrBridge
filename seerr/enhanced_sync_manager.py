"""
Enhanced Sync Manager for SeerrBridge
Handles intelligent database sync with proper status checking and queue management
"""
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from loguru import logger

from seerr.database import get_db
from seerr.unified_models import UnifiedMedia
from seerr.unified_media_manager import get_media_by_tmdb
from seerr.db_logger import log_info, log_success, log_warning, log_error
from seerr.overseerr import get_overseerr_media_requests, get_all_overseerr_requests_for_media
from seerr.trakt import get_media_details_from_trakt
from seerr.background_tasks import add_movie_to_queue, add_tv_to_queue
from seerr.config import USE_DATABASE


class EnhancedSyncManager:
    """Manages intelligent database sync with status checking and queue management"""
    
    def __init__(self):
        self.processed_items = set()  # Track processed items to avoid duplicates
    
    async def sync_all_requests_with_status_check(self):
        """
        Enhanced sync that checks database status and adds items to queue as needed
        """
        if not USE_DATABASE:
            return
        
        log_info("Enhanced Sync", "Starting enhanced database sync with status checking", 
                module="enhanced_sync_manager", function="sync_all_requests_with_status_check")
        
        try:
            # Get all processing requests from Overseerr
            processing_requests = get_overseerr_media_requests()
            if not processing_requests:
                log_info("Enhanced Sync", "No processing requests found in Overseerr", 
                        module="enhanced_sync_manager", function="sync_all_requests_with_status_check")
                return
            
            log_info("Enhanced Sync", f"Found {len(processing_requests)} processing requests to check", 
                    module="enhanced_sync_manager", function="sync_all_requests_with_status_check")
            
            # Process each request with status checking
            synced_count = 0
            queued_count = 0
            
            for request in processing_requests:
                try:
                    result = await self._process_request_with_status_check(request)
                    if result['synced']:
                        synced_count += 1
                    if result['queued']:
                        queued_count += 1
                        
                except Exception as e:
                    log_error("Enhanced Sync Error", f"Error processing request {request.get('id', 'unknown')}: {e}", 
                             module="enhanced_sync_manager", function="sync_all_requests_with_status_check")
                    continue
            
            log_success("Enhanced Sync", f"Sync completed: {synced_count} synced, {queued_count} queued for processing", 
                       module="enhanced_sync_manager", function="sync_all_requests_with_status_check")
            
        except Exception as e:
            log_error("Enhanced Sync Error", f"Error in enhanced sync: {e}", 
                     module="enhanced_sync_manager", function="sync_all_requests_with_status_check")
    
    async def _process_request_with_status_check(self, request: Dict[str, Any]) -> Dict[str, bool]:
        """
        Process a single request with proper status checking and queue management
        """
        try:
            tmdb_id = request['media']['tmdbId']
            media_id = request['media']['id']
            request_id = request['id']
            media_type = request['media']['mediaType']
            
            # Check if we've already processed this item in this sync cycle
            item_key = f"{media_type}_{tmdb_id}_{request_id}"
            if item_key in self.processed_items:
                return {'synced': False, 'queued': False}
            
            self.processed_items.add(item_key)
            
            # Check if media exists in database FIRST
            existing_media = self._get_media_by_tmdb(tmdb_id, media_type)
            
            # Only get media details from Trakt if we don't have complete critical data
            from seerr.unified_media_manager import has_complete_critical_data
            media_details = None
            needs_trakt_call = True
            
            if existing_media and has_complete_critical_data(existing_media):
                # We already have all critical data, no need for Trakt API call
                log_info("Enhanced Sync", f"Media {existing_media.title} already has complete critical data, skipping Trakt API call", 
                        module="enhanced_sync_manager", function="_process_request_with_status_check")
                needs_trakt_call = False
                
                # Create media_details dict from existing data
                media_details = {
                    'title': existing_media.title,
                    'year': existing_media.year,
                    'imdb_id': existing_media.imdb_id,
                    'trakt_id': existing_media.trakt_id,
                    'tmdb_id': existing_media.tmdb_id
                }
            
            # Only make Trakt API call if we don't have complete data
            if needs_trakt_call:
                media_details = get_media_details_from_trakt(tmdb_id, media_type)
                if not media_details:
                    log_warning("Enhanced Sync Warning", f"Could not get details for TMDB ID {tmdb_id}, skipping", 
                               module="enhanced_sync_manager", function="_process_request_with_status_check")
                    return {'synced': False, 'queued': False}
            
            if not existing_media:
                # Media doesn't exist - create it and add to queue
                log_info("Enhanced Sync", f"Media {media_details.get('title', 'Unknown')} not in database, creating and queuing", 
                        module="enhanced_sync_manager", function="_process_request_with_status_check")
                
                success = await self._create_and_queue_media(request, media_details)
                return {'synced': success, 'queued': success}
            
            # Media exists - check its status and decide what to do
            return await self._handle_existing_media(existing_media, request, media_details)
            
        except Exception as e:
            log_error("Enhanced Sync Error", f"Error processing request: {e}", 
                     module="enhanced_sync_manager", function="_process_request_with_status_check")
            return {'synced': False, 'queued': False}
    
    def _get_media_by_tmdb(self, tmdb_id: int, media_type: str) -> Optional[UnifiedMedia]:
        """Get media by TMDB ID and type"""
        return get_media_by_tmdb(tmdb_id, media_type)
    
    async def _create_and_queue_media(self, request: Dict[str, Any], media_details: Dict[str, Any]) -> bool:
        """Create new media record and add to queue"""
        try:
            from seerr.unified_media_manager import start_media_processing
            
            tmdb_id = request['media']['tmdbId']
            media_id = request['media']['id']
            request_id = request['id']
            media_type = request['media']['mediaType']
            
            # Prepare extra data
            extra_data = {
                'overseerr_media_id': media_id,
                'overseerr_request_id': request_id,
                'overview': media_details.get('overview', ''),
                'sync_created_at': datetime.utcnow().isoformat()
            }
            
            # Start media processing (creates database record)
            # Pass media_details so it can handle released_date and set status to unreleased if needed
            success = start_media_processing(
                tmdb_id=tmdb_id,
                imdb_id=media_details.get('imdb_id'),
                trakt_id=media_details.get('trakt_id'),
                media_type=media_type,
                title=media_details.get('title', 'Unknown Title'),
                year=media_details.get('year', 0),
                overseerr_request_id=request_id,
                overseerr_media_id=media_id,
                extra_data=extra_data,
                media_details=media_details  # Pass full media_details for released_date check
            )
            
            if success:
                # Check if media is unreleased - if so, don't add to queue
                media = self._get_media_by_tmdb(tmdb_id, media_type)
                if media and media.status == 'unreleased':
                    log_info("Enhanced Sync", f"Created {media_details.get('title', 'Unknown')} but it's unreleased, skipping queue", 
                           module="enhanced_sync_manager", function="_create_and_queue_media")
                    return success  # Successfully created, but not queued because unreleased
                
                # Add to queue (only if not unreleased)
                await self._add_to_queue(media_type, tmdb_id, media_details, extra_data, media_id, request_id)
                log_success("Enhanced Sync", f"Created and queued {media_details.get('title', 'Unknown')}", 
                           module="enhanced_sync_manager", function="_create_and_queue_media")
            
            return success
            
        except Exception as e:
            log_error("Enhanced Sync Error", f"Error creating and queuing media: {e}", 
                     module="enhanced_sync_manager", function="_create_and_queue_media")
            return False
    
    async def _handle_existing_media(self, existing_media: UnifiedMedia, request: Dict[str, Any], 
                                   media_details: Dict[str, Any]) -> Dict[str, bool]:
        """Handle existing media based on its current status"""
        try:
            media_type = existing_media.media_type
            title = existing_media.title
            
            # Check current status
            if existing_media.status == 'completed':
                log_info("Enhanced Sync", f"{title} already completed, no action needed", 
                        module="enhanced_sync_manager", function="_handle_existing_media")
                return {'synced': False, 'queued': False}
            
            elif existing_media.status == 'processing':
                if existing_media.is_in_queue:
                    log_info("Enhanced Sync", f"{title} already processing and in queue, no action needed", 
                            module="enhanced_sync_manager", function="_handle_existing_media")
                    return {'synced': False, 'queued': False}
                else:
                    # Processing but not in queue - add to queue
                    log_info("Enhanced Sync", f"{title} processing but not in queue, adding to queue", 
                            module="enhanced_sync_manager", function="_handle_existing_media")
                    await self._add_existing_to_queue(existing_media, request)
                    return {'synced': False, 'queued': True}
            
            elif existing_media.status == 'failed':
                # Failed - check if eligible for retry
                if self._is_eligible_for_retry(existing_media):
                    log_info("Enhanced Sync", f"{title} failed but eligible for retry, adding to queue", 
                            module="enhanced_sync_manager", function="_handle_existing_media")
                    await self._add_existing_to_queue(existing_media, request)
                    return {'synced': False, 'queued': True}
                else:
                    log_info("Enhanced Sync", f"{title} failed but not eligible for retry yet", 
                            module="enhanced_sync_manager", function="_handle_existing_media")
                    return {'synced': False, 'queued': False}
            
            elif existing_media.status == 'unreleased':
                # Unreleased - check if still unreleased, don't add to queue
                log_info("Enhanced Sync", f"{title} is unreleased, skipping queue", 
                        module="enhanced_sync_manager", function="_handle_existing_media")
                return {'synced': False, 'queued': False}
            
            elif existing_media.status in ['pending', 'skipped']:
                # Pending or skipped - add to queue
                log_info("Enhanced Sync", f"{title} is {existing_media.status}, adding to queue", 
                        module="enhanced_sync_manager", function="_handle_existing_media")
                await self._add_existing_to_queue(existing_media, request)
                return {'synced': False, 'queued': True}
            
            else:
                log_info("Enhanced Sync", f"{title} has status {existing_media.status}, no action needed", 
                        module="enhanced_sync_manager", function="_handle_existing_media")
                return {'synced': False, 'queued': False}
                
        except Exception as e:
            log_error("Enhanced Sync Error", f"Error handling existing media {existing_media.title}: {e}", 
                     module="enhanced_sync_manager", function="_handle_existing_media")
            return {'synced': False, 'queued': False}
    
    def _is_eligible_for_retry(self, media: UnifiedMedia) -> bool:
        """Check if failed media is eligible for retry"""
        if not media.last_error_at:
            return True
        
        # Check retry delay (2 hours minimum)
        time_since_error = datetime.utcnow() - media.last_error_at
        return time_since_error.total_seconds() >= 7200  # 2 hours
    
    async def _add_existing_to_queue(self, media: UnifiedMedia, request: Dict[str, Any]):
        """Add existing media to queue with proper tracking"""
        try:
            # Prepare extra data
            extra_data = {
                'overseerr_media_id': request['media']['id'],
                'overseerr_request_id': request['id'],
                'retry_attempt': media.queue_attempts + 1,
                'sync_queued_at': datetime.utcnow().isoformat()
            }
            
            # Add to appropriate queue
            if media.media_type == 'movie':
                success = add_movie_to_queue(
                    media.imdb_id,
                    media.title,
                    'movie',
                    extra_data,
                    request['media']['id'],
                    media.tmdb_id,
                    request['id']
                )
            else:  # tv
                # For TV shows, add requested seasons info
                extra_data['Requested Seasons'] = '1'  # Default to season 1
                success = add_tv_to_queue(
                    media.imdb_id,
                    media.title,
                    'tv',
                    extra_data,
                    request['media']['id'],
                    media.tmdb_id,
                    request['id']
                )
            
            if success:
                # Update queue tracking
                self._update_queue_tracking(media, True)
                log_success("Enhanced Sync", f"Added {media.title} to queue", 
                           module="enhanced_sync_manager", function="_add_existing_to_queue")
            else:
                log_warning("Enhanced Sync Warning", f"Failed to add {media.title} to queue", 
                           module="enhanced_sync_manager", function="_add_existing_to_queue")
                
        except Exception as e:
            log_error("Enhanced Sync Error", f"Error adding {media.title} to queue: {e}", 
                     module="enhanced_sync_manager", function="_add_existing_to_queue")
    
    async def _add_to_queue(self, media_type: str, tmdb_id: int, media_details: Dict[str, Any], 
                          extra_data: Dict[str, Any], media_id: int, request_id: int):
        """Add new media to queue"""
        try:
            if media_type == 'movie':
                success = add_movie_to_queue(
                    media_details.get('imdb_id'),
                    media_details.get('title', 'Unknown'),
                    'movie',
                    extra_data,
                    media_id,
                    tmdb_id,
                    request_id
                )
            else:  # tv
                extra_data['Requested Seasons'] = '1'  # Default to season 1
                success = add_tv_to_queue(
                    media_details.get('imdb_id'),
                    media_details.get('title', 'Unknown'),
                    'tv',
                    extra_data,
                    media_id,
                    tmdb_id,
                    request_id
                )
            
            if success:
                # Update queue tracking for the newly created media
                media = self._get_media_by_tmdb(tmdb_id, media_type)
                if media:
                    self._update_queue_tracking(media, True)
            
        except Exception as e:
            log_error("Enhanced Sync Error", f"Error adding to queue: {e}", 
                     module="enhanced_sync_manager", function="_add_to_queue")
    
    def _update_queue_tracking(self, media: UnifiedMedia, in_queue: bool):
        """Update queue tracking information"""
        db = get_db()
        try:
            media.is_in_queue = in_queue
            if in_queue:
                media.queue_added_at = datetime.utcnow()
                media.queue_attempts += 1
            else:
                media.queue_added_at = None
            
            db.commit()
            log_info("Enhanced Sync", f"Updated queue tracking for {media.title}: in_queue={in_queue}", 
                    module="enhanced_sync_manager", function="_update_queue_tracking")
            
        except Exception as e:
            log_error("Enhanced Sync Error", f"Error updating queue tracking: {e}", 
                     module="enhanced_sync_manager", function="_update_queue_tracking")
            db.rollback()
        finally:
            db.close()


# Global instance
enhanced_sync_manager = EnhancedSyncManager()


async def enhanced_sync_all_requests():
    """Enhanced sync function that checks status and manages queues properly"""
    await enhanced_sync_manager.sync_all_requests_with_status_check()
