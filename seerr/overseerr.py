"""
Overseerr integration module
Handles interaction with the Overseerr API
"""
import json
import requests
from typing import List, Dict, Any, Optional
from loguru import logger

from seerr.config import OVERSEERR_API_BASE_URL, OVERSEERR_API_KEY

def get_overseerr_media_requests() -> list[dict]:
    """
    Fetch media requests from Overseerr API
    
    Returns:
        list[dict]: List of media request objects
    """
    url = f"{OVERSEERR_API_BASE_URL}/request?take=500&filter=approved&sort=added"
    headers = {
        "X-Api-Key": OVERSEERR_API_KEY
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch requests from Overseerr: {response.status_code}")
            return []
        
        data = response.json()
        logger.info(f"Fetched {len(data.get('results', []))} requests from Overseerr")
        
        if not data.get('results'):
            return []
        
        # Filter requests that are in processing state (status 3)
        processing_requests = [item for item in data['results'] if item['status'] == 2 and item['media']['status'] == 3]
        logger.info(f"Filtered {len(processing_requests)} processing requests")
        return processing_requests
    except Exception as e:
        logger.error(f"Error fetching media requests from Overseerr: {e}")
        return []

def get_media_id_from_request_id(request_id: int) -> Optional[int]:
    """
    Get the media_id from a request_id by fetching the request details from Overseerr
    
    Args:
        request_id (int): Request ID from webhook
        
    Returns:
        Optional[int]: Media ID if found, None otherwise
    """
    url = f"{OVERSEERR_API_BASE_URL}/request/{request_id}"
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
    url = f"{OVERSEERR_API_BASE_URL}/media/{media_id}/available"
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