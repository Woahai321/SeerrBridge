"""
Overseerr integration module
Handles interaction with the Overseerr API
"""
import json
import requests
from typing import List, Dict, Any, Optional
from loguru import logger

from seerr.config import OVERSEERR_API_BASE_URL, OVERSEERR_API_KEY, USE_DATABASE
from seerr.database import get_db
from seerr.unified_media_manager import track_media_request, update_media_request_status, get_media_by_tmdb
from seerr.unified_models import UnifiedMedia
from seerr.db_logger import log_info, log_success, log_error

def aggregate_tv_requests_by_media_id(requests: list[dict]) -> list[dict]:
    """
    Aggregate TV show requests with the same media ID to collect all season numbers
    
    Args:
        requests: List of Overseerr request objects
        
    Returns:
        list[dict]: List of aggregated request objects with combined season data
    """
    # Group requests by media ID
    media_groups = {}
    
    for request in requests:
        media_id = request['media']['id']
        media_type = request['media']['mediaType']
        
        if media_type == 'tv':
            if media_id not in media_groups:
                media_groups[media_id] = []
            media_groups[media_id].append(request)
        else:
            # For movies, keep them as-is
            media_groups[f"movie_{request['id']}"] = [request]
    
    aggregated_requests = []
    
    for media_id, group_requests in media_groups.items():
        if len(group_requests) == 1:
            # Single request, no aggregation needed
            aggregated_requests.append(group_requests[0])
        else:
            # Multiple requests for same TV show, aggregate them
            logger.info(f"Aggregating {len(group_requests)} requests for TV show media ID {media_id}")
            
            # Use the first request as the base
            base_request = group_requests[0].copy()
            
            # Collect all seasons from all requests
            all_seasons = []
            all_request_ids = []
            
            for req in group_requests:
                all_request_ids.append(req['id'])
                if 'seasons' in req and req['seasons']:
                    for season in req['seasons']:
                        # Check if this season number already exists
                        existing_season = next(
                            (s for s in all_seasons if s['seasonNumber'] == season['seasonNumber']), 
                            None
                        )
                        if not existing_season:
                            all_seasons.append(season)
                        else:
                            # Update with the latest status if different
                            if season['status'] != existing_season['status']:
                                logger.info(f"Season {season['seasonNumber']} has different statuses across requests: {existing_season['status']} vs {season['status']}")
                                # Keep the most recent one (assuming higher status is more recent)
                                if season['status'] > existing_season['status']:
                                    all_seasons.remove(existing_season)
                                    all_seasons.append(season)
            
            # Sort seasons by season number
            all_seasons.sort(key=lambda x: x['seasonNumber'])
            
            # Update the base request with aggregated data
            base_request['seasons'] = all_seasons
            base_request['seasonCount'] = len(all_seasons)
            base_request['aggregated_request_ids'] = all_request_ids
            
            logger.info(f"Aggregated TV show {media_id}: {len(all_seasons)} seasons from {len(group_requests)} requests")
            aggregated_requests.append(base_request)
    
    return aggregated_requests


def get_overseerr_media_requests() -> list[dict]:
    """
    Fetch media requests from Overseerr API and aggregate TV show requests by media ID
    
    Returns:
        list[dict]: List of aggregated media request objects
    """
    url = f"{OVERSEERR_API_BASE_URL}/api/v1/request?take=500&filter=approved&sort=added"
    headers = {
        "X-Api-Key": OVERSEERR_API_KEY
    }
    
    # API request logging
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch requests from Overseerr: {response.status_code}")
            logger.error(f"Response text: {response.text}")
            return []
        
        # Response processing
        
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Raw response: {response.text}")
            return []
        logger.info(f"Fetched {len(data.get('results', []))} requests from Overseerr")
        
        if not data.get('results'):
            return []
        
        # Filter requests that are approved (status 2) and processing (status 3), excluding available (status 5) and unavailable (status 7)
        processing_requests = [item for item in data['results'] if item['status'] == 2 and item['media']['status'] == 3]
        logger.info(f"Filtered {len(processing_requests)} approved requests (processing items only, excluding status 5 and 7)")
        
        # Aggregate TV show requests by media ID
        aggregated_requests = aggregate_tv_requests_by_media_id(processing_requests)
        logger.info(f"Aggregated to {len(aggregated_requests)} requests (TV shows combined by media ID)")
        
        return aggregated_requests
    except Exception as e:
        logger.error(f"Error fetching media requests from Overseerr: {e}")
        return []

def get_all_overseerr_requests_for_media(overseerr_media_id: int) -> list[dict]:
    """
    Get all Overseerr requests for a specific media ID (TV show)
    
    Args:
        overseerr_media_id (int): Overseerr media ID
        
    Returns:
        list[dict]: List of all requests for this media ID
    """
    url = f"{OVERSEERR_API_BASE_URL}/api/v1/request?take=500&filter=all&sort=added"
    headers = {
        "X-Api-Key": OVERSEERR_API_KEY
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch all requests from Overseerr: {response.status_code}")
            return []
        
        data = response.json()
        
        if not data.get('results'):
            return []
        
        # Filter requests for the specific media ID, only processing (status 3), excluding available (status 5) and unavailable (status 7)
        media_requests = [item for item in data['results'] if item['media']['id'] == overseerr_media_id and item['media']['status'] == 3]
        logger.info(f"Found {len(media_requests)} total requests for media ID {overseerr_media_id} (processing items only, excluding status 5 and 7)")
        return media_requests
        
    except Exception as e:
        logger.error(f"Error fetching requests for media ID {overseerr_media_id}: {e}")
        return []

def get_media_id_from_request_id(request_id: int) -> Optional[int]:
    """
    Get the media_id from a request_id by fetching the request details from Overseerr
    
    Args:
        request_id (int): Request ID from webhook
        
    Returns:
        Optional[int]: Media ID if found, None otherwise
    """
    url = f"{OVERSEERR_API_BASE_URL}/api/v1/request/{request_id}"
    headers = {
        "X-Api-Key": OVERSEERR_API_KEY
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch request {request_id} from Overseerr: {response.status_code}")
            return None
        
        data = response.json()
        media_id = data.get('media', {}).get('id')
        
        if media_id:
            logger.info(f"Found media_id {media_id} for request_id {request_id}")
            return media_id
        else:
            logger.error(f"No media_id found in request {request_id} response")
            return None
            
    except Exception as e:
        logger.error(f"Error fetching request {request_id} from Overseerr: {e}")
        return None

def mark_completed(media_id: int, tmdb_id: int) -> bool:
    """
    Mark an item as completed in Overseerr
    
    Args:
        media_id (int): Media ID in Overseerr
        tmdb_id (int): TMDb ID for verification
        
    Returns:
        bool: True if successful, False otherwise
    """
    url = f"{OVERSEERR_API_BASE_URL}/api/v1/media/{media_id}/available"
    headers = {
        "X-Api-Key": OVERSEERR_API_KEY,
        "Content-Type": "application/json"
    }
    data = {"is4k": False}
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response_data = response.json()  # Parse the JSON response
        
        if response.status_code == 200:
            # Verify that the response contains the correct tmdb_id
            if response_data.get('tmdbId') == tmdb_id:
                logger.info(f"Marked media {media_id} as completed in overseerr. Response: {response_data}")
                return True
            else:
                logger.error(f"TMDB ID mismatch for media {media_id}. Expected {tmdb_id}, got {response_data.get('tmdbId')}")
                return False
        else:
            logger.error(f"Failed to mark media as completed in overseerr with id {media_id}: Status code {response.status_code}, Response: {response_data}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to mark media as completed in overseerr with id {media_id}: {str(e)}")
        return False
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON response for media {media_id}: {str(e)}")
        return False

# track_media_request and update_media_request_status functions moved to unified_media_manager.py

def get_media_request_by_id(overseerr_request_id: int) -> Optional[UnifiedMedia]:
    """
    Get a media request from the database by Overseerr request ID
    
    Args:
        overseerr_request_id (int): Overseerr request ID
        
    Returns:
        Optional[UnifiedMedia]: Media object if found, None otherwise
    """
    if not USE_DATABASE:
        return None
    
    try:
        db = get_db()
        return db.query(UnifiedMedia).filter(
            UnifiedMedia.overseerr_request_id == overseerr_request_id
        ).first()
    except Exception as e:
        log_error("Database Error", f"Failed to get media request {overseerr_request_id}: {e}")
        return None
    finally:
        if 'db' in locals():
            db.close()

def get_media_requests_by_status(status: str, limit: int = 100) -> List[UnifiedMedia]:
    """
    Get media requests by status from the database
    
    Args:
        status (str): Status to filter by
        limit (int): Maximum number of results
        
    Returns:
        List[UnifiedMedia]: List of media records
    """
    if not USE_DATABASE:
        return []
    
    try:
        db = get_db()
        return db.query(UnifiedMedia).filter(
            UnifiedMedia.status == status
        ).order_by(UnifiedMedia.created_at.desc()).limit(limit).all()
    except Exception as e:
        log_error("Database Error", f"Failed to get media requests by status {status}: {e}")
        return []
    finally:
        if 'db' in locals():
            db.close() 