"""
Failed Item Manager for SeerrBridge
Handles retry logic for failed movies and TV shows
"""
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from loguru import logger

from seerr.database import get_db
from seerr.unified_models import UnifiedMedia
from seerr.db_logger import log_info, log_success, log_warning, log_error
from seerr.task_config_manager import task_config


class FailedItemManager:
    """Manages retry logic for failed media items"""
    
    def __init__(self):
        self.max_retry_attempts = 3
        self.retry_delay_hours = 2  # Wait 2 hours before first retry
        self.retry_backoff_multiplier = 2  # Double the delay each retry
        self.max_retry_delay_hours = 24  # Maximum 24 hours between retries
    
    def get_failed_movies(self, limit: int = 50) -> List[UnifiedMedia]:
        """Get failed movies that are eligible for retry"""
        db = get_db()
        try:
            # Get movies that have failed and haven't exceeded retry limits
            failed_movies = db.query(UnifiedMedia).filter(
                UnifiedMedia.media_type == 'movie',
                UnifiedMedia.status == 'failed',
                UnifiedMedia.error_count < self.max_retry_attempts,
                UnifiedMedia.last_error_at.isnot(None)
            ).order_by(UnifiedMedia.last_error_at.asc()).limit(limit).all()
            
            # Filter by retry delay
            eligible_movies = []
            for movie in failed_movies:
                if self._is_eligible_for_retry(movie):
                    eligible_movies.append(movie)
            
            return eligible_movies
        except Exception as e:
            log_error("Failed Item Manager", f"Error getting failed movies: {e}", 
                     module="failed_item_manager", function="get_failed_movies")
            return []
        finally:
            db.close()
    
    def get_failed_tv_shows(self, limit: int = 50) -> List[UnifiedMedia]:
        """Get failed TV shows that are eligible for retry"""
        db = get_db()
        try:
            # Get TV shows that have failed and haven't exceeded retry limits
            failed_shows = db.query(UnifiedMedia).filter(
                UnifiedMedia.media_type == 'tv',
                UnifiedMedia.status == 'failed',
                UnifiedMedia.error_count < self.max_retry_attempts,
                UnifiedMedia.last_error_at.isnot(None)
            ).order_by(UnifiedMedia.last_error_at.asc()).limit(limit).all()
            
            # Filter by retry delay
            eligible_shows = []
            for show in failed_shows:
                if self._is_eligible_for_retry(show):
                    eligible_shows.append(show)
            
            return eligible_shows
        except Exception as e:
            log_error("Failed Item Manager", f"Error getting failed TV shows: {e}", 
                     module="failed_item_manager", function="get_failed_tv_shows")
            return []
        finally:
            db.close()
    
    def _is_eligible_for_retry(self, media: UnifiedMedia) -> bool:
        """Check if a media item is eligible for retry based on timing"""
        if not media.last_error_at:
            return False
        
        # Calculate retry delay based on error count
        retry_delay_hours = min(
            self.retry_delay_hours * (self.retry_backoff_multiplier ** media.error_count),
            self.max_retry_delay_hours
        )
        
        # Check if enough time has passed since last error
        time_since_error = datetime.utcnow() - media.last_error_at
        return time_since_error >= timedelta(hours=retry_delay_hours)
    
    def retry_failed_movie(self, movie: UnifiedMedia) -> bool:
        """Retry a failed movie by adding it back to the queue"""
        try:
            from seerr.background_tasks import add_movie_to_queue
            
            # Prepare the movie data for re-queuing
            movie_data = {
                'imdb_id': movie.imdb_id,
                'movie_title': movie.title,
                'media_type': 'movie',
                'extra_data': {
                    'retry_attempt': movie.error_count + 1,
                    'original_error': movie.error_message,
                    'retry_at': datetime.utcnow().isoformat()
                },
                'media_id': movie.overseerr_media_id,
                'tmdb_id': movie.tmdb_id,
                'request_id': movie.overseerr_request_id
            }
            
            # Add to queue
            success = add_movie_to_queue(
                movie_data['imdb_id'],
                movie_data['movie_title'],
                movie_data['media_type'],
                movie_data['extra_data'],
                movie_data['media_id'],
                movie_data['tmdb_id'],
                movie_data['request_id']
            )
            
            if success:
                # Update retry tracking
                self._update_retry_tracking(movie, 'retry_queued')
                log_info("Failed Item Manager", f"Re-queued failed movie: {movie.title} (attempt {movie.error_count + 1})", 
                        module="failed_item_manager", function="retry_failed_movie")
                return True
            else:
                log_warning("Failed Item Manager", f"Failed to re-queue movie: {movie.title}", 
                           module="failed_item_manager", function="retry_failed_movie")
                return False
                
        except Exception as e:
            log_error("Failed Item Manager", f"Error retrying movie {movie.title}: {e}", 
                     module="failed_item_manager", function="retry_failed_movie")
            return False
    
    def retry_failed_tv_show(self, show: UnifiedMedia) -> bool:
        """Retry a failed TV show by adding it back to the queue"""
        try:
            from seerr.background_tasks import add_tv_to_queue
            
            # Prepare the TV show data for re-queuing
            show_data = {
                'imdb_id': show.imdb_id,
                'movie_title': show.title,
                'media_type': 'tv',
                'extra_data': {
                    'retry_attempt': show.error_count + 1,
                    'original_error': show.error_message,
                    'retry_at': datetime.utcnow().isoformat(),
                    'Requested Seasons': show.seasons_processing or '1'  # Default to season 1 if not specified
                },
                'media_id': show.overseerr_media_id,
                'tmdb_id': show.tmdb_id,
                'request_id': show.overseerr_request_id
            }
            
            # Add to queue
            success = add_tv_to_queue(
                show_data['imdb_id'],
                show_data['movie_title'],
                show_data['media_type'],
                show_data['extra_data'],
                show_data['media_id'],
                show_data['tmdb_id'],
                show_data['request_id']
            )
            
            if success:
                # Update retry tracking
                self._update_retry_tracking(show, 'retry_queued')
                log_info("Failed Item Manager", f"Re-queued failed TV show: {show.title} (attempt {show.error_count + 1})", 
                        module="failed_item_manager", function="retry_failed_tv_show")
                return True
            else:
                log_warning("Failed Item Manager", f"Failed to re-queue TV show: {show.title}", 
                           module="failed_item_manager", function="retry_failed_tv_show")
                return False
                
        except Exception as e:
            log_error("Failed Item Manager", f"Error retrying TV show {show.title}: {e}", 
                     module="failed_item_manager", function="retry_failed_tv_show")
            return False
    
    def _update_retry_tracking(self, media: UnifiedMedia, action: str):
        """Update retry tracking information"""
        db = get_db()
        try:
            if action == 'retry_queued':
                # Update status to pending for retry
                media.status = 'pending'
                media.processing_stage = 'retry_queued'
                media.last_checked_at = datetime.utcnow()
                
                # Add retry info to extra_data
                extra_data = media.extra_data or {}
                extra_data['retry_attempt'] = media.error_count + 1
                extra_data['retry_queued_at'] = datetime.utcnow().isoformat()
                media.extra_data = extra_data
                
                db.commit()
                log_info("Failed Item Manager", f"Updated retry tracking for {media.title}", 
                        module="failed_item_manager", function="_update_retry_tracking")
                
        except Exception as e:
            log_error("Failed Item Manager", f"Error updating retry tracking: {e}", 
                     module="failed_item_manager", function="_update_retry_tracking")
            db.rollback()
        finally:
            db.close()
    
    def get_failed_item_stats(self) -> Dict[str, Any]:
        """Get statistics about failed items"""
        db = get_db()
        try:
            # Count failed movies
            failed_movies_count = db.query(UnifiedMedia).filter(
                UnifiedMedia.media_type == 'movie',
                UnifiedMedia.status == 'failed'
            ).count()
            
            # Count failed TV shows
            failed_tv_count = db.query(UnifiedMedia).filter(
                UnifiedMedia.media_type == 'tv',
                UnifiedMedia.status == 'failed'
            ).count()
            
            # Count eligible for retry
            eligible_movies = len(self.get_failed_movies(limit=1000))
            eligible_tv = len(self.get_failed_tv_shows(limit=1000))
            
            return {
                'failed_movies': failed_movies_count,
                'failed_tv_shows': failed_tv_count,
                'eligible_movies_for_retry': eligible_movies,
                'eligible_tv_for_retry': eligible_tv,
                'total_failed': failed_movies_count + failed_tv_count,
                'total_eligible': eligible_movies + eligible_tv
            }
        except Exception as e:
            log_error("Failed Item Manager", f"Error getting failed item stats: {e}", 
                     module="failed_item_manager", function="get_failed_item_stats")
            return {}
        finally:
            db.close()


# Global instance
failed_item_manager = FailedItemManager()


async def process_failed_items():
    """Process failed items by retrying eligible ones"""
    try:
        log_info("Failed Item Processing", "Starting failed item processing", 
                module="failed_item_manager", function="process_failed_items")
        
        # Get failed movies and TV shows
        failed_movies = failed_item_manager.get_failed_movies(limit=10)  # Process 10 at a time
        failed_tv_shows = failed_item_manager.get_failed_tv_shows(limit=10)
        
        retry_count = 0
        
        # Retry failed movies
        for movie in failed_movies:
            if failed_item_manager.retry_failed_movie(movie):
                retry_count += 1
        
        # Retry failed TV shows
        for show in failed_tv_shows:
            if failed_item_manager.retry_failed_tv_show(show):
                retry_count += 1
        
        if retry_count > 0:
            log_success("Failed Item Processing", f"Successfully re-queued {retry_count} failed items", 
                       module="failed_item_manager", function="process_failed_items")
        else:
            log_info("Failed Item Processing", "No failed items eligible for retry", 
                    module="failed_item_manager", function="process_failed_items")
        
        return retry_count
        
    except Exception as e:
        log_error("Failed Item Processing", f"Error processing failed items: {e}", 
                 module="failed_item_manager", function="process_failed_items")
        return 0
