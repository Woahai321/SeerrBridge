"""
Trakt List Manager
Handles database operations for Trakt lists and sync history
"""
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from loguru import logger

from seerr.database import get_db, TraktList, TraktListSyncHistory, TraktListSyncItem
from seerr.unified_models import UnifiedMedia
from seerr.unified_media_manager import track_media_request, get_media_by_tmdb


def get_or_create_trakt_list(list_identifier: str, list_type: str = None, list_name: str = None) -> Dict[str, Any]:
    """
    Get existing Trakt list or create a new one.
    
    Args:
        list_identifier: The list URL or identifier
        list_type: Type of list (watchlist, custom, public, trending, etc.)
        list_name: User-friendly name for the list
        
    Returns:
        Dict[str, Any]: Dictionary with list data (extracted before session closes)
    """
    db = get_db()
    try:
        # Try to find existing list
        existing_list = db.query(TraktList).filter(
            TraktList.list_identifier == list_identifier
        ).first()
        
        if existing_list:
            # Update metadata if provided
            if list_name and not existing_list.list_name:
                existing_list.list_name = list_name
            if list_type:
                existing_list.list_type = list_type
            existing_list.updated_at = datetime.utcnow()
            db.commit()
            
            # Extract all values before closing session
            result = {
                'id': existing_list.id,
                'list_identifier': existing_list.list_identifier,
                'list_type': existing_list.list_type,
                'list_name': existing_list.list_name,
                'description': existing_list.description,
                'item_count': existing_list.item_count or 0,
                'sync_count': getattr(existing_list, 'sync_count', None) or 0,
                'last_synced': existing_list.last_synced.isoformat() if existing_list.last_synced else None,
                'last_sync_status': existing_list.last_sync_status,
                'auto_sync': existing_list.auto_sync,
                'sync_interval_hours': existing_list.sync_interval_hours,
                'is_active': existing_list.is_active,
                'created_at': existing_list.created_at.isoformat() if existing_list.created_at else None,
                'updated_at': existing_list.updated_at.isoformat() if existing_list.updated_at else None
            }
            return result
        
        # Determine list type if not provided
        if not list_type:
            # Check for Letterboxd lists
            if 'letterboxd.com' in list_identifier.lower() or list_identifier.startswith(('letterboxd/', '/letterboxd/')):
                list_type = 'letterboxd'
            # Check for Trakt Special lists (format: category:media_type, e.g., trending:movies)
            elif ':' in list_identifier and not list_identifier.startswith(('http://', 'https://')):
                parts = list_identifier.split(':')
                if len(parts) == 2:
                    category, media_type = parts
                    # Valid categories for Trakt Special
                    valid_categories = ['trending', 'popular', 'anticipated', 'watched', 'collected', 
                                      'recommendations', 'boxoffice', 'favorited']
                    if category.lower() in valid_categories:
                        list_type = 'trakt_special'
                    else:
                        list_type = 'custom'
                else:
                    list_type = 'custom'
            elif 'watchlist' in list_identifier.lower() and 'letterboxd' not in list_identifier.lower():
                list_type = 'watchlist'
            elif '/lists/' in list_identifier and 'letterboxd' not in list_identifier.lower():
                list_type = 'public'
            elif '/users/' in list_identifier and '/lists/' in list_identifier:
                list_type = 'custom'
            else:
                list_type = 'unknown'
        
        new_list = TraktList(
            list_identifier=list_identifier,
            list_type=list_type,
            list_name=list_name or list_identifier,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(new_list)
        db.commit()
        db.refresh(new_list)  # Refresh to get the ID
        
        # Extract all values before closing session
        result = {
            'id': new_list.id,
            'list_identifier': new_list.list_identifier,
            'list_type': new_list.list_type,
            'list_name': new_list.list_name,
            'description': new_list.description,
            'item_count': new_list.item_count or 0,
            'sync_count': getattr(new_list, 'sync_count', None) or 0,
            'last_synced': new_list.last_synced.isoformat() if new_list.last_synced else None,
            'last_sync_status': new_list.last_sync_status,
            'auto_sync': new_list.auto_sync,
            'sync_interval_hours': new_list.sync_interval_hours,
            'is_active': new_list.is_active,
            'created_at': new_list.created_at.isoformat() if new_list.created_at else None,
            'updated_at': new_list.updated_at.isoformat() if new_list.updated_at else None
        }
        
        logger.info(f"Created new Trakt list: {list_identifier} (type: {list_type})")
        return result
        
    except Exception as e:
        logger.error(f"Error getting/creating Trakt list: {e}")
        raise
    finally:
        db.close()


def create_sync_history(trakt_list_id: int, sync_type: str = 'manual', total_items: int = 0) -> Dict[str, Any]:
    """
    Create a new sync history record.
    
    Args:
        trakt_list_id: ID of the Trakt list
        sync_type: Type of sync (manual, automated, dry_run)
        total_items: Total number of items in the list
        
    Returns:
        Dict[str, Any]: Dictionary with sync history data (extracted before session closes)
    """
    db = get_db()
    try:
        session_id = str(uuid.uuid4())
        
        sync_history = TraktListSyncHistory(
            trakt_list_id=trakt_list_id,
            session_id=session_id,
            sync_type=sync_type,
            status='in_progress',
            start_time=datetime.utcnow(),
            total_items=total_items
        )
        
        db.add(sync_history)
        db.commit()
        db.refresh(sync_history)
        
        # Extract all values before closing session
        result = {
            'id': sync_history.id,
            'sessionId': sync_history.session_id,
            'traktListId': sync_history.trakt_list_id,
            'syncType': sync_history.sync_type,
            'status': sync_history.status,
            'startTime': sync_history.start_time.isoformat() if sync_history.start_time else None,
            'endTime': sync_history.end_time.isoformat() if sync_history.end_time else None,
            'totalItems': sync_history.total_items,
            'itemsRequested': sync_history.items_requested,
            'itemsAlreadyRequested': sync_history.items_already_requested,
            'itemsAlreadyAvailable': sync_history.items_already_available,
            'itemsNotFound': sync_history.items_not_found,
            'itemsErrors': sync_history.items_errors,
            'errorMessage': sync_history.error_message
        }
        
        logger.info(f"Created sync history session {session_id} for list {trakt_list_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error creating sync history: {e}")
        raise
    finally:
        db.close()


def update_sync_history(session_id: str, status: str = 'completed', 
                       items_requested: int = 0, items_already_requested: int = 0,
                       items_already_available: int = 0, items_not_found: int = 0,
                       items_errors: int = 0, error_message: str = None) -> bool:
    """
    Update sync history record with final results.
    
    Args:
        session_id: Session ID of the sync
        status: Final status (completed, failed, cancelled)
        items_requested: Number of items successfully requested
        items_already_requested: Number of items already requested
        items_already_available: Number of items already available
        items_not_found: Number of items not found
        items_errors: Number of items with errors
        error_message: Error message if sync failed
        
    Returns:
        bool: True if updated successfully
    """
    db = get_db()
    try:
        sync_history = db.query(TraktListSyncHistory).filter(
            TraktListSyncHistory.session_id == session_id
        ).first()
        
        if not sync_history:
            logger.warning(f"Sync history not found for session {session_id}")
            return False
        
        sync_history.status = status
        sync_history.end_time = datetime.utcnow()
        sync_history.items_requested = items_requested
        sync_history.items_already_requested = items_already_requested
        sync_history.items_already_available = items_already_available
        sync_history.items_not_found = items_not_found
        sync_history.items_errors = items_errors
        sync_history.error_message = error_message
        
        # Update the list's last_synced timestamp and status
        trakt_list = db.query(TraktList).filter(TraktList.id == sync_history.trakt_list_id).first()
        if trakt_list:
            trakt_list.last_synced = datetime.utcnow()
            trakt_list.last_sync_status = status
            # Increment sync_count when sync completes
            if status in ['completed', 'failed']:
                trakt_list.sync_count = (trakt_list.sync_count or 0) + 1
                # Update item_count by counting unique items from all sync history
                # Get all sync history IDs for this list
                all_sync_histories = db.query(TraktListSyncHistory).filter(
                    TraktListSyncHistory.trakt_list_id == trakt_list.id
                ).all()
                sync_history_ids = [h.id for h in all_sync_histories]
                
                # Update item_count using the helper function
                # (This will use the same database session, so we'll do it inline)
                if sync_history_ids:
                    all_items = db.query(TraktListSyncItem).filter(
                        TraktListSyncItem.sync_history_id.in_(sync_history_ids)
                    ).all()
                    
                    # Count unique items
                    unique_keys = set()
                    for item in all_items:
                        if item.tmdb_id:
                            key = f"{item.media_type}_{item.tmdb_id}"
                        elif item.imdb_id:
                            key = f"{item.media_type}_{item.imdb_id}"
                        else:
                            key = f"{item.media_type}_{item.title}_{item.year}"
                        unique_keys.add(key)
                    
                    trakt_list.item_count = len(unique_keys)
        
        db.commit()
        logger.info(f"Updated sync history {session_id} with status {status}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating sync history: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def save_sync_item(sync_history_id: int, item: Dict[str, Any], 
                  status: str, match_method: str = None,
                  error_message: str = None, overseerr_request_id: int = None) -> Optional[int]:
    """
    Save an individual sync item to the database.
    
    Args:
        sync_history_id: ID of the sync history record
        item: Media item data (title, year, media_type, tmdb_id, imdb_id, etc.)
        status: Sync status (requested, already_requested, already_available, not_found, error)
        match_method: Method used to match the item (TMDB_ID_DIRECT, IMDB_TO_TMDB, etc.)
        error_message: Error message if sync failed
        overseerr_request_id: Overseerr request ID if item was requested
        
    Returns:
        Optional[int]: ID of the saved sync item, or None if save failed
    """
    db = get_db()
    try:
        # Try to find existing unified_media record
        unified_media_id = None
        if item.get('tmdb_id'):
            unified_media = db.query(UnifiedMedia).filter(
                UnifiedMedia.tmdb_id == item['tmdb_id'],
                UnifiedMedia.media_type == item.get('media_type', 'movie')
            ).first()
            if unified_media:
                unified_media_id = unified_media.id
        elif item.get('imdb_id'):
            unified_media = db.query(UnifiedMedia).filter(
                UnifiedMedia.imdb_id == item['imdb_id'],
                UnifiedMedia.media_type == item.get('media_type', 'movie')
            ).first()
            if unified_media:
                unified_media_id = unified_media.id
        
        sync_item = TraktListSyncItem(
            sync_history_id=sync_history_id,
            unified_media_id=unified_media_id,
            title=item.get('title', 'Unknown'),
            year=item.get('year'),
            media_type=item.get('media_type', 'movie'),
            tmdb_id=item.get('tmdb_id'),
            imdb_id=item.get('imdb_id'),
            trakt_id=item.get('trakt_id'),
            season_number=item.get('season_number'),
            status=status,
            match_method=match_method,
            error_message=error_message,
            overseerr_request_id=overseerr_request_id,
            synced_at=datetime.utcnow()
        )
        
        db.add(sync_item)
        db.commit()
        db.refresh(sync_item)
        
        return sync_item.id
        
    except Exception as e:
        logger.error(f"Error saving sync item: {e}")
        db.rollback()
        return None
    finally:
        db.close()


def update_list_item_count(trakt_list_id: int) -> int:
    """
    Update and return the item count for a Trakt list by counting unique items.
    
    Args:
        trakt_list_id: ID of the Trakt list
        
    Returns:
        int: The updated item count
    """
    db = get_db()
    try:
        trakt_list = db.query(TraktList).filter(TraktList.id == trakt_list_id).first()
        if not trakt_list:
            return 0
        
        # Get all sync history IDs for this list
        all_sync_histories = db.query(TraktListSyncHistory).filter(
            TraktListSyncHistory.trakt_list_id == trakt_list_id
        ).all()
        sync_history_ids = [h.id for h in all_sync_histories]
        
        if not sync_history_ids:
            trakt_list.item_count = 0
            db.commit()
            return 0
        
        # Get all items from all sync histories
        all_items = db.query(TraktListSyncItem).filter(
            TraktListSyncItem.sync_history_id.in_(sync_history_ids)
        ).all()
        
        # Count unique items
        unique_keys = set()
        for item in all_items:
            if item.tmdb_id:
                key = f"{item.media_type}_{item.tmdb_id}"
            elif item.imdb_id:
                key = f"{item.media_type}_{item.imdb_id}"
            else:
                key = f"{item.media_type}_{item.title}_{item.year}"
            unique_keys.add(key)
        
        trakt_list.item_count = len(unique_keys)
        db.commit()
        return len(unique_keys)
        
    except Exception as e:
        logger.error(f"Error updating item count for list {trakt_list_id}: {e}")
        db.rollback()
        return 0
    finally:
        db.close()

def get_trakt_lists_with_totals(active_only: bool = True) -> List[Dict[str, Any]]:
    """
    Get all Trakt lists with actual item counts from get_sync_items_for_list.
    This uses the same logic as the modal to ensure consistency.
    
    Args:
        active_only: If True, only return active lists
        
    Returns:
        List[Dict]: List of dictionaries with list data and total_items
    """
    db = get_db()
    try:
        from sqlalchemy import case
        
        query = db.query(TraktList)
        if active_only:
            query = query.filter(TraktList.is_active == True)
        
        # MySQL doesn't support NULLS LAST, so we use a CASE statement to sort NULLs last
        null_sort_key = case(
            (TraktList.last_synced.is_(None), 1),
            else_=0
        )
        
        lists = query.order_by(
            null_sort_key.asc(),
            TraktList.last_synced.desc(),
            TraktList.created_at.desc()
        ).all()
        
        result = []
        updates_needed = []  # Track which lists need item_count updates
        
        for lst in lists:
            # Extract all data we need BEFORE calling get_sync_items_for_list
            # (which will open/close its own session and detach this object)
            list_id = lst.id
            list_identifier = lst.list_identifier
            list_name = lst.list_name
            list_type = lst.list_type
            current_item_count = lst.item_count or 0
            sync_count = lst.sync_count or 0
            last_synced = lst.last_synced.isoformat() if lst.last_synced else None
            last_sync_status = lst.last_sync_status
            auto_sync = lst.auto_sync
            sync_interval_hours = lst.sync_interval_hours
            is_active = lst.is_active
            created_at = lst.created_at.isoformat()
            updated_at = lst.updated_at.isoformat()
            
            # Now call get_sync_items_for_list (this will open/close its own session)
            # Use get_sync_items_for_list to get the actual count (same as modal)
            # This ensures consistency - if modal shows items, this will show the same count
            try:
                items = get_sync_items_for_list(list_id, limit=10000)
                total_items = len(items)
                
                # Track if we need to update item_count (but do it later to avoid session issues)
                if current_item_count != total_items:
                    updates_needed.append((list_id, total_items))
            except Exception as e:
                logger.warning(f"Error getting items for list {list_id}: {e}")
                # Fall back to current_item_count or 0
                total_items = current_item_count or 0
            
            # Build result using extracted data (not the detached object)
            result.append({
                'list': {
                    'id': list_id,
                    'list_identifier': list_identifier,
                    'list_name': list_name,
                    'list_type': list_type,
                    'item_count': current_item_count,
                    'sync_count': sync_count,
                    'last_synced': last_synced,
                    'last_sync_status': last_sync_status,
                    'auto_sync': auto_sync,
                    'sync_interval_hours': sync_interval_hours,
                    'is_active': is_active,
                    'created_at': created_at,
                    'updated_at': updated_at
                },
                'total_items': total_items
            })
        
        # Update item_count for lists that need it (in a separate pass to avoid session issues)
        if updates_needed:
            for list_id, new_count in updates_needed:
                try:
                    list_to_update = db.query(TraktList).filter(TraktList.id == list_id).first()
                    if list_to_update:
                        list_to_update.item_count = new_count
                except Exception as e:
                    logger.warning(f"Error updating item_count for list {list_id}: {e}")
        
        db.commit()
        return result
    except Exception as e:
        logger.error(f"Error getting Trakt lists with totals: {e}")
        db.rollback()
        return []
    finally:
        db.close()

def get_trakt_lists(active_only: bool = True) -> List[TraktList]:
    """
    Get all Trakt lists from the database.
    
    Args:
        active_only: If True, only return active lists
        
    Returns:
        List[TraktList]: List of Trakt list records
    """
    db = get_db()
    try:
        from sqlalchemy import case
        
        query = db.query(TraktList)
        if active_only:
            query = query.filter(TraktList.is_active == True)
        
        # MySQL doesn't support NULLS LAST, so we use a CASE statement to sort NULLs last
        # This creates a sort key where NULL values get 1 (sorted last) and non-NULL get 0 (sorted first)
        null_sort_key = case(
            (TraktList.last_synced.is_(None), 1),
            else_=0
        )
        
        lists = query.order_by(
            null_sort_key.asc(),  # NULLs (1) come after non-NULLs (0)
            TraktList.last_synced.desc(),  # Then sort by last_synced descending
            TraktList.created_at.desc()  # Finally by created_at descending
        ).all()
        
        # Update item_count for lists that have sync history but count is 0
        for lst in lists:
            if lst.item_count == 0:
                # Check if list has any sync history
                has_history = db.query(TraktListSyncHistory).filter(
                    TraktListSyncHistory.trakt_list_id == lst.id
                ).first()
                
                if has_history:
                    # Recalculate item count
                    sync_history_ids = [h.id for h in db.query(TraktListSyncHistory).filter(
                        TraktListSyncHistory.trakt_list_id == lst.id
                    ).all()]
                    
                    if sync_history_ids:
                        all_items = db.query(TraktListSyncItem).filter(
                            TraktListSyncItem.sync_history_id.in_(sync_history_ids)
                        ).all()
                        
                        unique_keys = set()
                        for item in all_items:
                            if item.tmdb_id:
                                key = f"{item.media_type}_{item.tmdb_id}"
                            elif item.imdb_id:
                                key = f"{item.media_type}_{item.imdb_id}"
                            else:
                                key = f"{item.media_type}_{item.title}_{item.year}"
                            unique_keys.add(key)
                        
                        lst.item_count = len(unique_keys)
        
        db.commit()
        return lists
    except Exception as e:
        logger.error(f"Error getting Trakt lists: {e}")
        db.rollback()
        return []
    finally:
        db.close()


def get_trakt_list_by_id(list_id: int) -> Optional[TraktList]:
    """
    Get a Trakt list by ID.
    
    Args:
        list_id: ID of the list
        
    Returns:
        Optional[TraktList]: Trakt list record or None
    """
    db = get_db()
    try:
        return db.query(TraktList).filter(TraktList.id == list_id).first()
    except Exception as e:
        logger.error(f"Error getting Trakt list by ID: {e}")
        return None
    finally:
        db.close()


def delete_trakt_list(list_id: int) -> bool:
    """
    Delete a Trakt list (soft delete by setting is_active=False).
    
    Args:
        list_id: ID of the list to delete
        
    Returns:
        bool: True if deleted successfully
    """
    db = get_db()
    try:
        trakt_list = db.query(TraktList).filter(TraktList.id == list_id).first()
        if not trakt_list:
            return False
        
        trakt_list.is_active = False
        trakt_list.updated_at = datetime.utcnow()
        db.commit()
        logger.info(f"Deleted Trakt list {list_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error deleting Trakt list: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def get_sync_history(trakt_list_id: Optional[int] = None, limit: int = 50) -> List[TraktListSyncHistory]:
    """
    Get sync history records.
    
    Args:
        trakt_list_id: Optional list ID to filter by
        limit: Maximum number of records to return
        
    Returns:
        List[TraktListSyncHistory]: List of sync history records
    """
    db = get_db()
    try:
        query = db.query(TraktListSyncHistory)
        if trakt_list_id:
            query = query.filter(TraktListSyncHistory.trakt_list_id == trakt_list_id)
        return query.order_by(TraktListSyncHistory.start_time.desc()).limit(limit).all()
    except Exception as e:
        logger.error(f"Error getting sync history: {e}")
        return []
    finally:
        db.close()


def get_all_sync_history(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get all sync history records with list information.
    
    Args:
        limit: Maximum number of records to return
        
    Returns:
        List[Dict]: List of sync history records with list details
    """
    db = get_db()
    try:
        from sqlalchemy.orm import joinedload
        
        query = db.query(TraktListSyncHistory).options(
            joinedload(TraktListSyncHistory.trakt_list)
        ).order_by(TraktListSyncHistory.start_time.desc()).limit(limit)
        
        results = query.all()
        
        return [
            {
                'id': h.id,
                'sessionId': h.session_id,
                'traktListId': h.trakt_list_id,
                'listIdentifier': h.trakt_list.list_identifier if h.trakt_list else None,
                'listName': h.trakt_list.list_name if h.trakt_list else None,
                'listType': h.trakt_list.list_type if h.trakt_list else None,
                'syncType': h.sync_type,
                'status': h.status,
                'startTime': h.start_time.isoformat() if h.start_time else None,
                'endTime': h.end_time.isoformat() if h.end_time else None,
                'totalItems': h.total_items,
                'itemsRequested': h.items_requested,
                'itemsAlreadyRequested': h.items_already_requested,
                'itemsAlreadyAvailable': h.items_already_available,
                'itemsNotFound': h.items_not_found,
                'itemsErrors': h.items_errors,
                'errorMessage': h.error_message
            }
            for h in results
        ]
    except Exception as e:
        logger.error(f"Error getting all sync history: {e}")
        return []
    finally:
        db.close()


def get_sync_history_by_session(session_id: str) -> Optional[TraktListSyncHistory]:
    """
    Get sync history by session ID.
    
    Args:
        session_id: Session ID
        
    Returns:
        Optional[TraktListSyncHistory]: Sync history record or None
    """
    db = get_db()
    try:
        return db.query(TraktListSyncHistory).filter(
            TraktListSyncHistory.session_id == session_id
        ).first()
    except Exception as e:
        logger.error(f"Error getting sync history by session: {e}")
        return None
    finally:
        db.close()


def get_sync_items_for_list(trakt_list_id: int, limit: int = 1000) -> List[Dict[str, Any]]:
    """
    Get all unique items from all sync sessions for a specific list.
    This aggregates items from all sync history records for the list.
    Enriches items with data from unified_media when available.
    
    Args:
        trakt_list_id: ID of the Trakt list
        limit: Maximum number of items to return
        
    Returns:
        List[Dict]: List of unique items with their latest sync status, enriched with unified_media data
    """
    db = get_db()
    try:
        # First, verify the list exists and get sync history IDs
        sync_histories = db.query(TraktListSyncHistory).filter(
            TraktListSyncHistory.trakt_list_id == trakt_list_id
        ).all()
        
        if not sync_histories:
            logger.warning(f"No sync history found for trakt_list_id={trakt_list_id}")
            return []
        
        # Get sync history IDs
        sync_history_ids = [h.id for h in sync_histories]
        logger.info(f"Found {len(sync_history_ids)} sync history records for list {trakt_list_id}")
        
        # Get all sync items for these sync histories
        items = db.query(TraktListSyncItem).filter(
            TraktListSyncItem.sync_history_id.in_(sync_history_ids)
        ).order_by(
            TraktListSyncItem.synced_at.desc()
        ).limit(limit).all()
        
        logger.info(f"Found {len(items)} sync items for list {trakt_list_id}")
        
        if not items:
            logger.warning(f"No sync items found for trakt_list_id={trakt_list_id} (sync_history_ids={sync_history_ids})")
            return []
        
        # Get all unified_media_ids to fetch enriched data
        unified_media_ids = [item.unified_media_id for item in items if item.unified_media_id]
        unified_media_map = {}
        
        if unified_media_ids:
            # Fetch unified_media records
            unified_media_records = db.query(UnifiedMedia).filter(
                UnifiedMedia.id.in_(unified_media_ids)
            ).all()
            
            # Create a map by ID
            for media in unified_media_records:
                unified_media_map[media.id] = media
        
        # Also create maps by tmdb_id and imdb_id for items without unified_media_id
        tmdb_ids = [item.tmdb_id for item in items if item.tmdb_id]
        imdb_ids = [item.imdb_id for item in items if item.imdb_id and item.imdb_id.strip()]
        
        if tmdb_ids:
            # Fetch by tmdb_id
            tmdb_media_records = db.query(UnifiedMedia).filter(
                UnifiedMedia.tmdb_id.in_(tmdb_ids)
            ).all()
            for media in tmdb_media_records:
                # Store by composite key for lookup by tmdb_id
                key = f"{media.media_type}_{media.tmdb_id}"
                if key not in unified_media_map:
                    unified_media_map[key] = media
                # Also store by ID for direct lookup
                if media.id not in unified_media_map:
                    unified_media_map[media.id] = media
        
        if imdb_ids:
            # Fetch by imdb_id
            imdb_media_records = db.query(UnifiedMedia).filter(
                UnifiedMedia.imdb_id.in_(imdb_ids)
            ).all()
            for media in imdb_media_records:
                # Store by composite key for lookup by imdb_id
                key = f"{media.media_type}_{media.imdb_id}"
                if key not in unified_media_map:
                    unified_media_map[key] = media
                # Also store by ID for direct lookup
                if media.id not in unified_media_map:
                    unified_media_map[media.id] = media
        
        # Group by unique identifier (tmdb_id + media_type, or imdb_id + media_type)
        unique_items = {}
        for item in items:
            # Create unique key
            if item.tmdb_id:
                key = f"{item.media_type}_{item.tmdb_id}"
            elif item.imdb_id:
                key = f"{item.media_type}_{item.imdb_id}"
            else:
                # Fallback to title + year
                key = f"{item.media_type}_{item.title}_{item.year}"
            
            # Only keep the most recent item for each unique key
            if key not in unique_items:
                # Start with sync item data
                item_data = {
                    'title': item.title,
                    'year': item.year,
                    'media_type': item.media_type,
                    'tmdb_id': item.tmdb_id,
                    'imdb_id': item.imdb_id,
                    'trakt_id': item.trakt_id,
                    'season_number': item.season_number,
                    'status': item.status,
                    'match_method': item.match_method,
                    'error_message': item.error_message,
                    'overseerr_request_id': item.overseerr_request_id,
                    'unified_media_id': item.unified_media_id,
                    'synced_at': item.synced_at.isoformat() if item.synced_at else None
                }
                
                # Try to enrich with unified_media data
                unified_media = None
                
                # First try by unified_media_id (direct lookup by ID)
                if item.unified_media_id:
                    if item.unified_media_id in unified_media_map:
                        unified_media = unified_media_map[item.unified_media_id]
                    else:
                        # If not in map but we have the ID, try direct database lookup
                        try:
                            direct_media = db.query(UnifiedMedia).filter(
                                UnifiedMedia.id == item.unified_media_id
                            ).first()
                            if direct_media:
                                unified_media = direct_media
                                # Add to map for future lookups
                                unified_media_map[direct_media.id] = direct_media
                        except Exception as e:
                            logger.warning(f"Error looking up unified_media by ID {item.unified_media_id}: {e}")
                
                # Then try by tmdb_id (if unified_media_id lookup failed or wasn't set)
                if not unified_media and item.tmdb_id:
                    lookup_key = f"{item.media_type}_{item.tmdb_id}"
                    if lookup_key in unified_media_map:
                        unified_media = unified_media_map[lookup_key]
                
                # Finally try by imdb_id (if both previous lookups failed)
                if not unified_media and item.imdb_id:
                    lookup_key = f"{item.media_type}_{item.imdb_id}"
                    if lookup_key in unified_media_map:
                        unified_media = unified_media_map[lookup_key]
                
                # Enrich with unified_media data if found
                if unified_media:
                    item_data['title'] = unified_media.title or item_data['title']
                    item_data['year'] = unified_media.year or item_data['year']
                    item_data['overview'] = unified_media.overview
                    item_data['unified_media_id'] = unified_media.id
                    # Cached image information - ONLY use cached images, no external URLs
                    item_data['has_poster_image'] = unified_media.poster_image is not None
                    item_data['poster_image_format'] = unified_media.poster_image_format
                    item_data['has_thumb_image'] = unified_media.thumb_image is not None
                    item_data['thumb_image_format'] = unified_media.thumb_image_format
                    item_data['has_fanart_image'] = unified_media.fanart_image is not None
                    item_data['fanart_image_format'] = unified_media.fanart_image_format
                    # Update IDs if they're missing
                    if not item_data['tmdb_id']:
                        item_data['tmdb_id'] = unified_media.tmdb_id
                    if not item_data['imdb_id']:
                        item_data['imdb_id'] = unified_media.imdb_id
                else:
                    # Even if unified_media not found, ensure has_poster_image is set to False
                    item_data['has_poster_image'] = False
                    item_data['has_thumb_image'] = False
                    item_data['has_fanart_image'] = False
                
                unique_items[key] = item_data
        
        return list(unique_items.values())
        
    except Exception as e:
        logger.error(f"Error getting sync items for list: {e}")
        return []
    finally:
        db.close()
