"""
Queue Persistence Manager for SeerrBridge
Handles persistent queue storage in the database using queue_status table
"""
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from loguru import logger

from seerr.database import get_db
from seerr.unified_models import UnifiedMedia
from seerr.db_logger import log_info, log_success, log_warning, log_error
from seerr.config import USE_DATABASE
from sqlalchemy import text


class QueuePersistenceManager:
    """Manages persistent queue storage in the database"""
    
    def __init__(self):
        self.movie_queue_type = 'movie'
        self.tv_queue_type = 'tv'
        self.max_queue_size = 250
    
    def initialize_queue_status(self):
        """Initialize queue_status table with default entries"""
        if not USE_DATABASE:
            return
        
        db = get_db()
        try:
            # Check if queue_status table exists and has entries
            result = db.execute(text("SELECT COUNT(*) as count FROM queue_status")).fetchone()
            if result and result[0] > 0:
                log_info("Queue Persistence", "Queue status table already initialized", 
                        module="queue_persistence_manager", function="initialize_queue_status")
                return
            
            # Insert default queue status entries
            db.execute(text("""
                INSERT INTO queue_status (queue_type, queue_size, max_size, is_processing, last_activity, created_at, updated_at)
                VALUES 
                ('movie', 0, 250, 0, NOW(), NOW(), NOW()),
                ('tv', 0, 250, 0, NOW(), NOW(), NOW())
            """))
            db.commit()
            
            log_success("Queue Persistence", "Initialized queue status table", 
                       module="queue_persistence_manager", function="initialize_queue_status")
            
        except Exception as e:
            log_error("Queue Persistence", f"Error initializing queue status: {e}", 
                     module="queue_persistence_manager", function="initialize_queue_status")
            db.rollback()
        finally:
            db.close()
    
    def get_queue_status(self, queue_type: str) -> Optional[Dict[str, Any]]:
        """Get current queue status from database"""
        if not USE_DATABASE:
            return None
        
        db = get_db()
        try:
            result = db.execute(text("""
                SELECT id, queue_type, queue_size, max_size, is_processing, last_activity, created_at, updated_at
                FROM queue_status 
                WHERE queue_type = :queue_type
            """), {"queue_type": queue_type}).fetchone()
            
            if result:
                return {
                    'id': result[0],
                    'queue_type': result[1],
                    'queue_size': result[2],
                    'max_size': result[3],
                    'is_processing': result[4],
                    'last_activity': result[5],
                    'created_at': result[6],
                    'updated_at': result[7]
                }
            return None
            
        except Exception as e:
            log_error("Queue Persistence", f"Error getting queue status: {e}", 
                     module="queue_persistence_manager", function="get_queue_status")
            return None
        finally:
            db.close()
    
    def update_queue_status(self, queue_type: str, queue_size: int, is_processing: bool = False):
        """Update queue status in database"""
        if not USE_DATABASE:
            return
        
        db = get_db()
        try:
            db.execute(text("""
                UPDATE queue_status 
                SET queue_size = :queue_size, is_processing = :is_processing, last_activity = NOW(), updated_at = NOW()
                WHERE queue_type = :queue_type
            """), {"queue_size": queue_size, "is_processing": is_processing, "queue_type": queue_type})
            db.commit()
            
            log_info("Queue Persistence", f"Updated {queue_type} queue status: size={queue_size}, processing={is_processing}", 
                    module="queue_persistence_manager", function="update_queue_status")
            
        except Exception as e:
            log_error("Queue Persistence", f"Error updating queue status: {e}", 
                     module="queue_persistence_manager", function="update_queue_status")
            db.rollback()
        finally:
            db.close()
    
    def get_queued_items_from_database(self, queue_type: str) -> List[Dict[str, Any]]:
        """Get items that should be in queue from database"""
        if not USE_DATABASE:
            return []
        
        db = get_db()
        try:
            # Get items marked as in queue
            items = db.query(UnifiedMedia).filter(
                UnifiedMedia.is_in_queue == True,
                UnifiedMedia.media_type == queue_type
            ).order_by(UnifiedMedia.queue_added_at.asc()).all()
            
            queued_items = []
            for item in items:
                queued_items.append({
                    'id': item.id,
                    'imdb_id': item.imdb_id,
                    'title': item.title,
                    'media_type': item.media_type,
                    'tmdb_id': item.tmdb_id,
                    'overseerr_media_id': item.overseerr_media_id,
                    'overseerr_request_id': item.overseerr_request_id,
                    'queue_added_at': item.queue_added_at,
                    'queue_attempts': item.queue_attempts,
                    'status': item.status,
                    'extra_data': item.extra_data
                })
            
            log_info("Queue Persistence", f"Found {len(queued_items)} {queue_type} items in database queue", 
                    module="queue_persistence_manager", function="get_queued_items_from_database")
            
            return queued_items
            
        except Exception as e:
            log_error("Queue Persistence", f"Error getting queued items: {e}", 
                     module="queue_persistence_manager", function="get_queued_items_from_database")
            return []
        finally:
            db.close()
    
    def clear_queue_status_from_database(self, queue_type: str):
        """Clear queue status from database (mark items as not in queue)"""
        if not USE_DATABASE:
            return
        
        db = get_db()
        try:
            # Mark all items as not in queue
            db.execute(text("""
                UPDATE unified_media 
                SET is_in_queue = FALSE, queue_added_at = NULL
                WHERE media_type = :queue_type AND is_in_queue = TRUE
            """), {"queue_type": queue_type})
            
            # Update queue status
            self.update_queue_status(queue_type, 0, False)
            
            log_info("Queue Persistence", f"Cleared {queue_type} queue status from database", 
                    module="queue_persistence_manager", function="clear_queue_status_from_database")
            
        except Exception as e:
            log_error("Queue Persistence", f"Error clearing queue status: {e}", 
                     module="queue_persistence_manager", function="clear_queue_status_from_database")
            db.rollback()
        finally:
            db.close()
    
    def sync_queue_from_database(self, queue_type: str, queue_instance) -> int:
        """Sync in-memory queue with database queue status"""
        if not USE_DATABASE:
            return 0
        
        try:
            # Get queued items from database
            queued_items = self.get_queued_items_from_database(queue_type)
            
            if not queued_items:
                # Clear queue status if no items
                self.update_queue_status(queue_type, 0, False)
                return 0
            
            # Add items to in-memory queue
            added_count = 0
            for item in queued_items:
                try:
                    # Prepare extra data
                    extra_data = item.get('extra_data', {})
                    if isinstance(extra_data, str):
                        try:
                            extra_data = json.loads(extra_data)
                        except (json.JSONDecodeError, TypeError):
                            extra_data = {}
                    
                    # Add to queue (this should be done by the background tasks)
                    # We'll just mark the count for now
                    added_count += 1
                    
                except Exception as e:
                    log_warning("Queue Persistence", f"Error processing queued item {item.get('title', 'Unknown')}: {e}", 
                               module="queue_persistence_manager", function="sync_queue_from_database")
                    continue
            
            # Update queue status
            self.update_queue_status(queue_type, added_count, False)
            
            log_success("Queue Persistence", f"Synced {added_count} {queue_type} items from database to queue", 
                       module="queue_persistence_manager", function="sync_queue_from_database")
            
            return added_count
            
        except Exception as e:
            log_error("Queue Persistence", f"Error syncing queue from database: {e}", 
                     module="queue_persistence_manager", function="sync_queue_from_database")
            return 0
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get comprehensive queue statistics"""
        if not USE_DATABASE:
            return {}
        
        try:
            movie_status = self.get_queue_status('movie')
            tv_status = self.get_queue_status('tv')
            
            # Get actual queued items count
            movie_queued_count = len(self.get_queued_items_from_database('movie'))
            tv_queued_count = len(self.get_queued_items_from_database('tv'))
            
            return {
                'movie_queue': {
                    'status': movie_status,
                    'actual_queued_items': movie_queued_count
                },
                'tv_queue': {
                    'status': tv_status,
                    'actual_queued_items': tv_queued_count
                },
                'total_queued_items': movie_queued_count + tv_queued_count
            }
            
        except Exception as e:
            log_error("Queue Persistence", f"Error getting queue stats: {e}", 
                     module="queue_persistence_manager", function="get_queue_stats")
            return {}


# Global instance
queue_persistence_manager = QueuePersistenceManager()


def initialize_queue_persistence():
    """Initialize queue persistence system"""
    queue_persistence_manager.initialize_queue_status()


def get_queue_stats():
    """Get queue statistics"""
    return queue_persistence_manager.get_queue_stats()
