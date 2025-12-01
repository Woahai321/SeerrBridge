"""
Database Queue Manager for SeerrBridge
Handles queuing existing database items that need processing
"""
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from loguru import logger

from seerr.database import get_db
from seerr.unified_models import UnifiedMedia
from seerr.db_logger import log_info, log_success, log_warning, log_error
from seerr.background_tasks import add_movie_to_queue, add_tv_to_queue
from seerr.config import USE_DATABASE


class DatabaseQueueManager:
    """Manages queuing of existing database items that need processing"""
    
    def __init__(self):
        self.max_retry_attempts = 3
        self.retry_delay_hours = 2
    
    async def queue_existing_items_for_processing(self):
        """
        Check existing database items and add them to queue if they need processing
        """
        if not USE_DATABASE:
            return
        
        log_info("Database Queue Manager", "Checking existing database items for queuing", 
                module="database_queue_manager", function="queue_existing_items_for_processing")
        
        try:
            # Get items that need processing
            items_to_queue = self._get_items_needing_processing()
            
            if not items_to_queue:
                log_info("Database Queue Manager", "No items need queuing", 
                        module="database_queue_manager", function="queue_existing_items_for_processing")
                return
            
            log_info("Database Queue Manager", f"Found {len(items_to_queue)} items that need queuing", 
                    module="database_queue_manager", function="queue_existing_items_for_processing")
            
            queued_count = 0
            for item in items_to_queue:
                try:
                    success = await self._queue_item(item)
                    if success:
                        queued_count += 1
                except Exception as e:
                    log_error("Database Queue Manager", f"Error queuing item {item.title}: {e}", 
                             module="database_queue_manager", function="queue_existing_items_for_processing")
                    continue
            
            log_success("Database Queue Manager", f"Successfully queued {queued_count} items", 
                       module="database_queue_manager", function="queue_existing_items_for_processing")
            
        except Exception as e:
            log_error("Database Queue Manager", f"Error in queue existing items: {e}", 
                     module="database_queue_manager", function="queue_existing_items_for_processing")
    
    def _get_items_needing_processing(self) -> List[UnifiedMedia]:
        """Get items from database that need to be queued for processing"""
        db = get_db()
        try:
            # Get items that are processing but not in queue
            processing_items = db.query(UnifiedMedia).filter(
                UnifiedMedia.status == 'processing',
                UnifiedMedia.is_in_queue == False
            ).all()
            
            # Get items that are failed and eligible for retry
            failed_items = db.query(UnifiedMedia).filter(
                UnifiedMedia.status == 'failed',
                UnifiedMedia.is_in_queue == False,
                UnifiedMedia.error_count < self.max_retry_attempts
            ).all()
            
            # Filter failed items by retry timing
            eligible_failed_items = []
            for item in failed_items:
                if self._is_eligible_for_retry(item):
                    eligible_failed_items.append(item)
            
            # Get items that are pending
            pending_items = db.query(UnifiedMedia).filter(
                UnifiedMedia.status == 'pending',
                UnifiedMedia.is_in_queue == False
            ).all()
            
            all_items = processing_items + eligible_failed_items + pending_items
            
            log_info("Database Queue Manager", 
                    f"Found {len(processing_items)} processing, {len(eligible_failed_items)} eligible failed, {len(pending_items)} pending items", 
                    module="database_queue_manager", function="_get_items_needing_processing")
            
            return all_items
            
        except Exception as e:
            log_error("Database Queue Manager", f"Error getting items needing processing: {e}", 
                     module="database_queue_manager", function="_get_items_needing_processing")
            return []
        finally:
            db.close()
    
    def _is_eligible_for_retry(self, item: UnifiedMedia) -> bool:
        """Check if a failed item is eligible for retry"""
        if not item.last_error_at:
            return True
        
        # Check if enough time has passed since last error
        time_since_error = datetime.utcnow() - item.last_error_at
        return time_since_error.total_seconds() >= (self.retry_delay_hours * 3600)
    
    async def _queue_item(self, item: UnifiedMedia) -> bool:
        """Queue a single item for processing"""
        try:
            from datetime import datetime
            
            # Prepare extra data
            extra_data = {
                'overseerr_media_id': item.overseerr_media_id,
                'overseerr_request_id': item.overseerr_request_id,
                'queue_attempt': item.queue_attempts + 1,
                'queued_from_database': True,
                'queued_at': datetime.utcnow().isoformat()
            }
            
            # Add retry info for failed items
            if item.status == 'failed':
                extra_data.update({
                    'retry_attempt': item.error_count + 1,
                    'original_error': item.error_message,
                    'last_error_at': item.last_error_at.isoformat() if item.last_error_at else None
                })
            
            # Initialize requested_seasons for both movies and TV shows
            requested_seasons = '1'  # Default fallback
            
            # Add to appropriate queue
            if item.media_type == 'movie':
                success = await add_movie_to_queue(
                    item.imdb_id,
                    item.title,
                    'movie',
                    extra_data,
                    item.overseerr_media_id,
                    item.tmdb_id,
                    item.overseerr_request_id
                )
            else:  # tv
                # For TV shows, add requested seasons info
                # Try to get seasons from Overseerr request first, fallback to seasons_processing or '1'
                
                if item.seasons_processing:
                    requested_seasons = item.seasons_processing
                else:
                    # Try to fetch seasons from Overseerr API
                    try:
                        from seerr.overseerr import get_all_overseerr_requests_for_media
                        all_requests = get_all_overseerr_requests_for_media(item.overseerr_media_id)
                        
                        seasons_found = []
                        for req in all_requests:
                            if 'seasons' in req and req['seasons']:
                                for season in req['seasons']:
                                    season_name = f"Season {season['seasonNumber']}"
                                    if season_name not in seasons_found:
                                        seasons_found.append(season_name)
                        
                        if seasons_found:
                            requested_seasons = ", ".join(seasons_found)
                            log_info("Database Queue Manager", f"Extracted seasons from Overseerr API: {requested_seasons}", 
                                   module="database_queue_manager", function="_queue_item")
                        else:
                            log_warning("Database Queue Manager", f"No seasons found in Overseerr requests for {item.title}, using default '1'", 
                                      module="database_queue_manager", function="_queue_item")
                    except Exception as e:
                        log_error("Database Queue Manager", f"Error fetching seasons from Overseerr API: {e}", 
                                module="database_queue_manager", function="_queue_item")
                
                extra_data['Requested Seasons'] = requested_seasons
                success = await add_tv_to_queue(
                    item.imdb_id,
                    item.title,
                    'tv',
                    extra_data,
                    item.overseerr_media_id,
                    item.tmdb_id,
                    item.overseerr_request_id
                )
            
            if success:
                # Update queue tracking
                self._update_queue_tracking(item, True)
                log_success("Database Queue Manager", f"Queued {item.title} ({item.status})", 
                           module="database_queue_manager", function="_queue_item")
                
                # Process season data for TV shows
                if item.media_type == 'tv' and requested_seasons != '1':
                    log_info("Database Queue Manager", f"Starting season processing for {item.title} with seasons: {requested_seasons}", 
                           module="database_queue_manager", function="_queue_item")
                    try:
                        # Import required modules
                        from datetime import datetime
                        from seerr.trakt import get_media_details_from_trakt
                        from seerr.enhanced_season_manager import EnhancedSeasonManager
                        from seerr.trakt import get_season_details_from_trakt, check_next_episode_aired
                        
                        log_info("Database Queue Manager", f"Imports successful for {item.title}", 
                               module="database_queue_manager", function="_queue_item")
                        
                        # Parse the requested seasons string
                        seasons_list = [s.strip() for s in requested_seasons.split(',')]
                        
                        log_info("Database Queue Manager", f"Parsed seasons list for {item.title}: {seasons_list}", 
                               module="database_queue_manager", function="_queue_item")
                        
                        # Get media details from Trakt
                        media_details = get_media_details_from_trakt(str(item.tmdb_id), 'tv')
                        
                        if media_details and media_details.get('trakt_id'):
                            log_info("Database Queue Manager", f"Processing {len(seasons_list)} seasons for {item.title}: {seasons_list}", 
                                   module="database_queue_manager", function="_queue_item")
                            
                            # Process seasons using the same logic as populate_queues_from_overseerr
                            trakt_show_id = media_details['trakt_id']
                            seasons_data = []
                            
                            for season in seasons_list:
                                season_number = int(season.split()[-1])  # Extract number from "Season X"
                                
                                # Fetch season details from Trakt
                                season_details = get_season_details_from_trakt(str(trakt_show_id), season_number)
                                
                                if season_details:
                                    episode_count = season_details.get('episode_count', 0)
                                    aired_episodes = season_details.get('aired_episodes', 0)
                                    
                                    # Check for next episode if there's a discrepancy
                                    if episode_count != aired_episodes:
                                        has_aired, next_episode_details = check_next_episode_aired(
                                            str(trakt_show_id), season_number, aired_episodes
                                        )
                                        if has_aired:
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
                                    log_info("Database Queue Manager", f"Processed season {season_number} for {item.title}: {episode_count} episodes, {aired_episodes} aired", 
                                           module="database_queue_manager", function="_queue_item")
                                else:
                                    log_warning("Database Queue Manager", f"Could not fetch season details for {item.title} Season {season_number}", 
                                              module="database_queue_manager", function="_queue_item")
                            
                            # Update TV show with enhanced season data
                            if seasons_data:
                                log_info("Database Queue Manager", f"Updating {item.title} with enhanced season data for {len(seasons_data)} seasons", 
                                       module="database_queue_manager", function="_queue_item")
                                success = EnhancedSeasonManager.update_tv_show_seasons(item.tmdb_id, seasons_data, item.title)
                                
                                if success:
                                    log_success("Database Queue Manager", f"Successfully updated {item.title} with enhanced season tracking", 
                                              module="database_queue_manager", function="_queue_item")
                                else:
                                    log_warning("Database Queue Manager", f"Failed to update {item.title} with enhanced season tracking", 
                                              module="database_queue_manager", function="_queue_item")
                            else:
                                log_warning("Database Queue Manager", f"No season data to update for {item.title}", 
                                          module="database_queue_manager", function="_queue_item")
                        else:
                            log_warning("Database Queue Manager", f"Could not get Trakt details for {item.title}", 
                                      module="database_queue_manager", function="_queue_item")
                    except Exception as e:
                        log_error("Database Queue Manager", f"Error processing seasons for {item.title}: {e}", 
                                module="database_queue_manager", function="_queue_item")
                
                return True
            else:
                log_warning("Database Queue Manager", f"Failed to queue {item.title}", 
                           module="database_queue_manager", function="_queue_item")
                return False
                
        except Exception as e:
            import traceback
            log_error("Database Queue Manager", f"Error queuing {item.title}: {e}", 
                     module="database_queue_manager", function="_queue_item")
            log_error("Database Queue Manager", f"Traceback: {traceback.format_exc()}", 
                     module="database_queue_manager", function="_queue_item")
            return False
    
    def _update_queue_tracking(self, item: UnifiedMedia, in_queue: bool):
        """Update queue tracking information"""
        db = get_db()
        try:
            # Get fresh instance of the item to avoid detached instance issues
            fresh_item = db.query(UnifiedMedia).filter(UnifiedMedia.id == item.id).first()
            if fresh_item:
                fresh_item.is_in_queue = in_queue
                if in_queue:
                    fresh_item.queue_added_at = datetime.utcnow()
                    fresh_item.queue_attempts += 1
                else:
                    fresh_item.queue_added_at = None
                
                db.commit()
                log_info("Database Queue Manager", f"Updated queue tracking for {fresh_item.title}: in_queue={in_queue}", 
                        module="database_queue_manager", function="_update_queue_tracking")
            else:
                log_warning("Database Queue Manager", f"Could not find item {item.title} in database for queue tracking update", 
                           module="database_queue_manager", function="_update_queue_tracking")
            
        except Exception as e:
            log_error("Database Queue Manager", f"Error updating queue tracking: {e}", 
                     module="database_queue_manager", function="_update_queue_tracking")
            db.rollback()
        finally:
            db.close()


# Global instance
database_queue_manager = DatabaseQueueManager()


async def queue_existing_database_items():
    """Queue existing database items that need processing"""
    await database_queue_manager.queue_existing_items_for_processing()
