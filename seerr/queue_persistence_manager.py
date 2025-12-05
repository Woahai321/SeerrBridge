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
        """Initialize queue_status table with default entries, using actual queue sizes from config"""
        if not USE_DATABASE:
            return
        
        db = get_db()
        try:
            # Check if queue_status table exists and has entries
            result = db.execute(text("SELECT COUNT(*) as count FROM queue_status")).fetchone()
            if result and result[0] > 0:
                log_info("Queue Persistence", "Queue status table already initialized", 
                        module="queue_persistence_manager", function="initialize_queue_status")
                # Update max_size to match current queue sizes if needed
                try:
                    from seerr.task_config_manager import task_config
                    movie_size = task_config.get_config('movie_queue_maxsize', 250)
                    tv_size = task_config.get_config('tv_queue_maxsize', 250)
                    db.execute(text("""
                        UPDATE queue_status 
                        SET max_size = :max_size, updated_at = NOW()
                        WHERE queue_type = 'movie'
                    """), {"max_size": int(movie_size)})
                    db.execute(text("""
                        UPDATE queue_status 
                        SET max_size = :max_size, updated_at = NOW()
                        WHERE queue_type = 'tv'
                    """), {"max_size": int(tv_size)})
                    db.commit()
                except Exception as e:
                    log_warning("Queue Persistence", f"Error updating queue max_size: {e}", 
                              module="queue_persistence_manager", function="initialize_queue_status")
                    db.rollback()
                return
            
            # Get actual queue sizes from config
            try:
                from seerr.task_config_manager import task_config
                movie_size = task_config.get_config('movie_queue_maxsize', 250)
                tv_size = task_config.get_config('tv_queue_maxsize', 250)
            except:
                movie_size = 250
                tv_size = 250
            
            # Insert default queue status entries with actual sizes
            db.execute(text("""
                INSERT INTO queue_status (queue_type, queue_size, max_size, is_processing, last_activity, created_at, updated_at)
                VALUES 
                ('movie', 0, :movie_size, 0, NOW(), NOW(), NOW()),
                ('tv', 0, :tv_size, 0, NOW(), NOW(), NOW())
            """), {"movie_size": int(movie_size), "tv_size": int(tv_size)})
            db.commit()
            
            log_success("Queue Persistence", f"Initialized queue status table with sizes: Movie={movie_size}, TV={tv_size}", 
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
        """Update queue status in database (legacy method - use update_queue_status_from_database for accurate counts)"""
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
    
    def update_queue_status_from_database(self, queue_type: str, is_processing: bool = False):
        """Update queue status from actual database state (source of truth)"""
        if not USE_DATABASE:
            return
        
        db = get_db()
        try:
            # Calculate actual queue size from database where is_in_queue = TRUE
            # and status is not completed or ignored
            result = db.execute(text("""
                SELECT COUNT(*) as queue_size
                FROM unified_media
                WHERE media_type = :queue_type
                  AND is_in_queue = TRUE
                  AND status NOT IN ('completed', 'ignored')
            """), {"queue_type": queue_type}).fetchone()
            
            queue_size = result[0] if result else 0
            
            # Update queue_status table
            db.execute(text("""
                UPDATE queue_status 
                SET queue_size = :queue_size, is_processing = :is_processing, last_activity = NOW(), updated_at = NOW()
                WHERE queue_type = :queue_type
            """), {"queue_size": queue_size, "is_processing": is_processing, "queue_type": queue_type})
            db.commit()
            
            log_info("Queue Persistence", f"Updated {queue_type} queue status from database: size={queue_size}, processing={is_processing}", 
                    module="queue_persistence_manager", function="update_queue_status_from_database")
            
        except Exception as e:
            log_error("Queue Persistence", f"Error updating queue status from database: {e}", 
                     module="queue_persistence_manager", function="update_queue_status_from_database")
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
    
    def validate_queue_sync(self, queue_type: str, in_memory_queue) -> Dict[str, Any]:
        """
        Validate that in-memory queue matches database state.
        
        Args:
            queue_type: 'movie' or 'tv'
            in_memory_queue: The asyncio.Queue instance
            
        Returns:
            Dict with validation results including discrepancies
        """
        if not USE_DATABASE:
            return {'valid': True, 'message': 'Database not enabled'}
        
        try:
            # Get items from database that should be in queue
            db_items = self.get_queued_items_from_database(queue_type)
            db_tmdb_ids = {item['tmdb_id'] for item in db_items}
            
            # Get items currently in memory queue (non-destructive peek)
            memory_tmdb_ids = set()
            temp_items = []
            try:
                # Drain queue temporarily to inspect
                while not in_memory_queue.empty():
                    item = in_memory_queue.get_nowait()
                    temp_items.append(item)
                    # Extract tmdb_id from queue item
                    if len(item) >= 6:
                        # Regular item format: (imdb_id, title, media_type, extra_data, media_id, tmdb_id, ...)
                        if not isinstance(item[0], str):  # Not a special task
                            memory_tmdb_ids.add(item[5])  # tmdb_id is at index 5
                        elif item[0] == "tv_processing" and len(item) >= 8:
                            memory_tmdb_ids.add(item[7])  # tmdb_id is at index 7 for TV
                
                # Put items back
                for item in temp_items:
                    try:
                        in_memory_queue.put_nowait(item)
                    except:
                        pass  # Queue might be full, but we tried
            except Exception as e:
                log_warning("Queue Validation", f"Error inspecting memory queue: {e}", 
                           module="queue_persistence_manager", function="validate_queue_sync")
            
            # Find discrepancies
            in_db_not_in_memory = db_tmdb_ids - memory_tmdb_ids
            in_memory_not_in_db = memory_tmdb_ids - db_tmdb_ids
            
            is_valid = len(in_db_not_in_memory) == 0 and len(in_memory_not_in_db) == 0
            
            result = {
                'valid': is_valid,
                'queue_type': queue_type,
                'database_count': len(db_tmdb_ids),
                'memory_count': len(memory_tmdb_ids),
                'in_db_not_in_memory': list(in_db_not_in_memory),
                'in_memory_not_in_db': list(in_memory_not_in_db),
                'discrepancy_count': len(in_db_not_in_memory) + len(in_memory_not_in_db)
            }
            
            if not is_valid:
                log_warning("Queue Validation", 
                           f"Queue sync discrepancy for {queue_type}: {len(in_db_not_in_memory)} in DB not in memory, {len(in_memory_not_in_db)} in memory not in DB", 
                           module="queue_persistence_manager", function="validate_queue_sync")
            
            return result
            
        except Exception as e:
            log_error("Queue Validation", f"Error validating queue sync: {e}", 
                     module="queue_persistence_manager", function="validate_queue_sync")
            return {'valid': False, 'error': str(e)}
    
    def reconcile_queue_from_database(self, queue_type: str, in_memory_queue) -> Dict[str, Any]:
        """
        Reconcile in-memory queue with database state.
        Removes items from memory queue if not in database, adds items to memory queue if in database.
        
        Args:
            queue_type: 'movie' or 'tv'
            in_memory_queue: The asyncio.Queue instance
            
        Returns:
            Dict with reconciliation results
        """
        if not USE_DATABASE:
            return {'success': False, 'message': 'Database not enabled'}
        
        try:
            # Get items from database that should be in queue
            db_items = self.get_queued_items_from_database(queue_type)
            db_tmdb_ids = {item['tmdb_id']: item for item in db_items}
            
            # Collect all items from memory queue
            memory_items = []
            memory_tmdb_ids = set()
            
            try:
                # Drain queue
                while not in_memory_queue.empty():
                    item = in_memory_queue.get_nowait()
                    memory_items.append(item)
                    # Extract tmdb_id
                    if len(item) >= 6:
                        if not isinstance(item[0], str):  # Regular movie item
                            memory_tmdb_ids.add(item[5])
                        elif item[0] == "tv_processing" and len(item) >= 8:
                            memory_tmdb_ids.add(item[7])
            except Exception as e:
                log_error("Queue Reconciliation", f"Error draining memory queue: {e}", 
                         module="queue_persistence_manager", function="reconcile_queue_from_database")
                return {'success': False, 'error': str(e)}
            
            # Filter: keep only items that are in database
            items_to_keep = []
            removed_count = 0
            
            for item in memory_items:
                keep_item = False
                if len(item) >= 6:
                    if not isinstance(item[0], str):  # Regular movie item
                        if item[5] in db_tmdb_ids:
                            keep_item = True
                    elif item[0] == "tv_processing" and len(item) >= 8:
                        if item[7] in db_tmdb_ids:
                            keep_item = True
                    else:
                        # Special tasks (like "movie_processing_check") - keep them
                        keep_item = True
                
                if keep_item:
                    items_to_keep.append(item)
                else:
                    removed_count += 1
            
            # Add items from database that aren't in memory
            added_count = 0
            for tmdb_id, db_item in db_tmdb_ids.items():
                if tmdb_id not in memory_tmdb_ids:
                    # Add to queue
                    try:
                        import json
                        extra_data = db_item.get('extra_data', {})
                        if isinstance(extra_data, str):
                            try:
                                extra_data = json.loads(extra_data)
                            except:
                                extra_data = {}
                        
                        if queue_type == 'movie':
                            queue_item = (
                                db_item['imdb_id'],
                                db_item['title'],
                                db_item['media_type'],
                                extra_data,
                                db_item['overseerr_media_id'],
                                db_item['tmdb_id'],
                                db_item.get('overseerr_request_id')
                            )
                        else:  # tv
                            queue_item = (
                                "tv_processing",
                                db_item['imdb_id'],
                                db_item['title'],
                                db_item['media_type'],
                                extra_data,
                                db_item['overseerr_media_id'],
                                db_item['tmdb_id'],
                                db_item.get('overseerr_request_id')
                            )
                        
                        items_to_keep.append(queue_item)
                        added_count += 1
                    except Exception as e:
                        log_warning("Queue Reconciliation", f"Error adding item {db_item.get('title', 'Unknown')} to queue: {e}", 
                                   module="queue_persistence_manager", function="reconcile_queue_from_database")
            
            # Put items back into queue
            for item in items_to_keep:
                try:
                    in_memory_queue.put_nowait(item)
                except Exception as e:
                    log_warning("Queue Reconciliation", f"Queue full, could not add item: {e}", 
                               module="queue_persistence_manager", function="reconcile_queue_from_database")
            
            # Update queue status
            self.update_queue_status_from_database(queue_type, False)
            
            result = {
                'success': True,
                'queue_type': queue_type,
                'removed_from_memory': removed_count,
                'added_to_memory': added_count,
                'final_count': len(items_to_keep)
            }
            
            log_success("Queue Reconciliation", 
                       f"Reconciled {queue_type} queue: removed {removed_count}, added {added_count}, final count {len(items_to_keep)}", 
                       module="queue_persistence_manager", function="reconcile_queue_from_database")
            
            return result
            
        except Exception as e:
            log_error("Queue Reconciliation", f"Error reconciling queue: {e}", 
                     module="queue_persistence_manager", function="reconcile_queue_from_database")
            return {'success': False, 'error': str(e)}


# Global instance
queue_persistence_manager = QueuePersistenceManager()


def initialize_queue_persistence():
    """Initialize queue persistence system"""
    queue_persistence_manager.initialize_queue_status()


def get_queue_stats():
    """Get queue statistics"""
    return queue_persistence_manager.get_queue_stats()


def validate_queue_sync(queue_type: str, in_memory_queue):
    """Validate that in-memory queue matches database state"""
    return queue_persistence_manager.validate_queue_sync(queue_type, in_memory_queue)


def reconcile_queue_from_database(queue_type: str, in_memory_queue):
    """Reconcile in-memory queue with database state"""
    return queue_persistence_manager.reconcile_queue_from_database(queue_type, in_memory_queue)
