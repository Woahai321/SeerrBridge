"""
Trakt Lists integration for SeerrBridge
Fetches media items from Trakt lists and syncs them to Overseerr
"""
import re
import requests
from typing import List, Dict, Any, Optional
from loguru import logger

from seerr.config import TRAKT_API_KEY
from seerr.trakt import get_trakt_rate_limit_status

# Trakt API configuration
TRAKT_BASE_URL = "https://api.trakt.tv"
TRAKT_API_VERSION = "2"


def get_trakt_headers() -> Dict[str, str]:
    """
    Get headers for Trakt API requests using SeerrBridge's existing API key.
    
    Returns:
        Dict[str, str]: Headers including API key
        
    Raises:
        ValueError: If TRAKT_API_KEY is not configured
    """
    if not TRAKT_API_KEY:
        raise ValueError(
            "TRAKT_API_KEY is not configured. "
            "Please set it in your SeerrBridge configuration."
        )
    
    return {
        "Content-Type": "application/json",
        "trakt-api-version": TRAKT_API_VERSION,
        "trakt-api-key": TRAKT_API_KEY
    }


def parse_trakt_list_url(list_id: str) -> str:
    """
    Parse Trakt list URL to extract API endpoint path.
    
    Supports:
    - User custom lists: https://trakt.tv/users/{username}/lists/{list-slug}
    - User watchlists: https://trakt.tv/users/{username}/watchlist
    - Public lists: https://trakt.tv/lists/{numeric-id}
    - Shortcut format: trending:movies, popular:shows, etc.
    
    Args:
        list_id (str): Trakt list ID, URL, or shortcut
        
    Returns:
        str: API endpoint path
        
    Raises:
        ValueError: If list ID format is invalid
    """
    # Handle shortcut format like "trending:movies"
    if ':' in list_id and not list_id.startswith(('http://', 'https://')):
        parts = list_id.split(':')
        if len(parts) == 2:
            list_type, media_type = parts
            
            # Normalize media type
            if media_type.lower() in ['movies', 'movie']:
                return f"/movies/{list_type.lower()}"
            elif media_type.lower() in ['shows', 'show', 'tv']:
                return f"/shows/{list_type.lower()}"
            else:
                raise ValueError(f"Invalid media type in shortcut: {media_type}")
        else:
            raise ValueError(f"Invalid shortcut format: {list_id}")
    
    # Handle full URLs
    if list_id.startswith(('http://', 'https://')):
        url = list_id.split('?')[0].rstrip('/')
        
        # Pattern 1: /users/{username}/watchlist
        pattern_watchlist = r'trakt\.tv/users/([^/]+)/watchlist'
        match = re.search(pattern_watchlist, url)
        if match:
            username = match.group(1)
            return f"/users/{username}/watchlist"
        
        # Pattern 2: /users/{username}/lists/{list-slug}
        pattern_list = r'trakt\.tv/users/([^/]+)/lists/([^/?]+)'
        match = re.search(pattern_list, url)
        if match:
            username, list_slug = match.groups()
            return f"/users/{username}/lists/{list_slug}/items"
        
        # Pattern 3: /lists/{numeric-id}
        pattern_numeric = r'trakt\.tv/lists/(\d+)'
        match = re.search(pattern_numeric, url)
        if match:
            list_id_num = match.group(1)
            return f"/lists/{list_id_num}/items"
        
        # Pattern 4: Special lists (trending, popular, etc.)
        special_patterns = [
            (r'trakt\.tv/movies/(trending|popular|recommendations|streaming|anticipated|favorited|watched|collected|boxoffice)', r'/movies/\1'),
            (r'trakt\.tv/shows/(trending|popular|recommendations|streaming|anticipated|favorited|watched|collected)', r'/shows/\1'),
        ]
        
        for pattern, replacement in special_patterns:
            match = re.search(pattern, url)
            if match:
                return match.expand(replacement)
        
        raise ValueError(f"Invalid Trakt URL format: {list_id}")
    
    # Handle numeric list IDs (legacy format)
    if list_id.isdigit():
        return f"/lists/{list_id}/items"
    
    raise ValueError(
        f"Invalid Trakt list ID format: {list_id}. "
        "Expected a numeric ID, list URL, watchlist URL, or shortcut format (e.g., 'trending:movies')."
    )


def extract_media_from_list_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract media information from a Trakt list item.
    
    Supports:
    - Movies: Returns movie data
    - Shows: Returns full show data
    - Seasons: Returns show data with season number for specific season requests
    
    Args:
        item (Dict[str, Any]): Trakt API list item
        
    Returns:
        Optional[Dict[str, Any]]: Normalized media item or None if parsing fails
    """
    try:
        item_type = item.get('type')
        
        # Handle season items specially
        if item_type == 'season':
            season_data = item.get('season', {})
            show_data = item.get('show', {})
            
            if not show_data:
                logger.warning(f"No show data found in season item")
                return None
            
            season_number = season_data.get('number')
            if season_number is None:
                logger.warning(f"No season number found in season item")
                return None
            
            title = show_data.get('title')
            year = show_data.get('year')
            ids = show_data.get('ids', {})
            
            if not title:
                logger.warning(f"No title found in show")
                return None
            
            # Extract poster path from images if available
            images = show_data.get('images', {})
            poster_path = None
            if images:
                poster_array = images.get('poster', [])
                if poster_array and len(poster_array) > 0:
                    poster_url = poster_array[0].get('full', '') if isinstance(poster_array[0], dict) else str(poster_array[0])
                    if poster_url:
                        poster_path = poster_url
            
            return {
                "title": title,
                "year": year,
                "media_type": "tv",
                "tmdb_id": ids.get('tmdb'),
                "imdb_id": ids.get('imdb'),
                "season_number": season_number,
                "poster_path": poster_path  # Add poster path if available
            }
        
        # Get the media object (nested under 'movie' or 'show' key)
        if item_type == 'movie':
            media = item.get('movie', {})
        elif item_type == 'show':
            media = item.get('show', {})
        else:
            logger.warning(f"Unknown item type: {item_type}")
            return None
        
        if not media:
            logger.warning(f"No media object found in item")
            return None
        
        title = media.get('title')
        year = media.get('year')
        ids = media.get('ids', {})
        
        if not title:
            logger.warning(f"No title found in media")
            return None
        
        # Extract poster path from images if available
        images = media.get('images', {})
        poster_path = None
        if images:
            poster_array = images.get('poster', [])
            if poster_array and len(poster_array) > 0:
                # Trakt returns full URLs, extract just the path
                poster_url = poster_array[0].get('full', '') if isinstance(poster_array[0], dict) else str(poster_array[0])
                if poster_url:
                    # Extract path from Trakt URL (format: https://walter.trakt.tv/images/...)
                    # Or use TMDB poster path if available in IDs
                    # For now, we'll try to get TMDB poster path
                    if 'tmdb' in poster_url.lower() or 'themoviedb' in poster_url.lower():
                        # Extract TMDB path
                        import re
                        match = re.search(r'/(w\d+/[^/]+)$', poster_url)
                        if match:
                            poster_path = match.group(1)
                    # If we have tmdb_id, we can construct TMDB poster URL later
                    # For now, store the Trakt poster URL
                    poster_path = poster_url
        
        return {
            "title": title,
            "year": year,
            "media_type": "tv" if item_type == "show" else "movie",
            "tmdb_id": ids.get('tmdb'),
            "imdb_id": ids.get('imdb'),
            "poster_path": poster_path  # Add poster path if available
        }
        
    except Exception as e:
        logger.warning(f"Failed to parse Trakt list item: {str(e)}")
        return None


def extract_media_from_special_list_item(item: Dict[str, Any], endpoint: str) -> Optional[Dict[str, Any]]:
    """
    Extract media information from a special list item (trending, popular, etc.).
    
    Args:
        item (Dict[str, Any]): API response item
        endpoint (str): The API endpoint to help determine format
        
    Returns:
        Optional[Dict[str, Any]]: Normalized media item or None if parsing fails
    """
    try:
        # Determine if this is movies or shows from endpoint
        is_movie = '/movies/' in endpoint
        media_key = 'movie' if is_movie else 'show'
        media_type = 'movie' if is_movie else 'tv'
        
        # Some endpoints (like trending) wrap the media object, others don't
        if media_key in item:
            # Wrapped format (e.g., trending)
            media = item[media_key]
        else:
            # Direct format (e.g., popular)
            media = item
        
        title = media.get('title')
        year = media.get('year')
        ids = media.get('ids', {})
        
        if not title:
            logger.warning(f"No title found in media")
            return None
        
        # Extract poster path from images if available
        images = media.get('images', {})
        poster_path = None
        if images:
            poster_array = images.get('poster', [])
            if poster_array and len(poster_array) > 0:
                # Trakt returns full URLs, extract just the path
                poster_url = poster_array[0].get('full', '') if isinstance(poster_array[0], dict) else str(poster_array[0])
                if poster_url:
                    poster_path = poster_url
        
        return {
            "title": title,
            "year": year,
            "media_type": media_type,
            "tmdb_id": ids.get('tmdb'),
            "imdb_id": ids.get('imdb'),
            "poster_path": poster_path  # Add poster path if available
        }
        
    except Exception as e:
        logger.warning(f"Failed to parse special list item: {str(e)}")
        return None


def search_trakt_by_imdb_id(imdb_id: str) -> Optional[Dict[str, Any]]:
    """
    Search Trakt by IMDB ID to get TMDB ID and other metadata.
    
    Args:
        imdb_id (str): IMDB ID (e.g., 'tt0372784')
        
    Returns:
        Optional[Dict[str, Any]]: Media info with IDs or None if not found
    """
    try:
        logger.info(f"Searching Trakt by IMDB ID: {imdb_id}")
        url = f"{TRAKT_BASE_URL}/search/imdb/{imdb_id}"
        
        response = requests.get(url, headers=get_trakt_headers(), timeout=30)
        
        # Handle rate limiting
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 10))
            logger.warning(f"Trakt API rate limit hit. Waiting {retry_after} seconds...")
            import time
            time.sleep(retry_after)
            response = requests.get(url, headers=get_trakt_headers(), timeout=30)
        
        response.raise_for_status()
        results = response.json()
        
        if not results or len(results) == 0:
            logger.info(f"No results found for IMDB ID: {imdb_id}")
            return None
        
        # Take first result
        first_result = results[0]
        result_type = first_result.get('type')
        
        # Extract the media object
        if result_type == 'movie':
            media = first_result.get('movie', {})
            media_type = 'movie'
        elif result_type == 'show':
            media = first_result.get('show', {})
            media_type = 'tv'
        else:
            logger.warning(f"Unknown result type from Trakt: {result_type}")
            return None
        
        title = media.get('title')
        year = media.get('year')
        ids = media.get('ids', {})
        tmdb_id = ids.get('tmdb')
        returned_imdb_id = ids.get('imdb')
        
        # Validate IMDB ID matches
        if returned_imdb_id and returned_imdb_id != imdb_id:
            logger.error(f"IMDB ID mismatch! Input: {imdb_id}, Returned: {returned_imdb_id}")
            return None
        
        if tmdb_id:
            logger.info(f"Found TMDB ID {tmdb_id} for IMDB ID {imdb_id}")
        
        return {
            "title": title,
            "year": year,
            "media_type": media_type,
            "tmdb_id": tmdb_id,
            "imdb_id": returned_imdb_id,
            "trakt_id": ids.get('trakt')
        }
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.info(f"IMDB ID not found in Trakt: {imdb_id}")
            return None
        elif e.response.status_code == 401:
            logger.error("Trakt API authentication failed")
            return None
        else:
            logger.error(f"Trakt API error searching by IMDB ID: {e.response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error searching Trakt by IMDB ID {imdb_id}: {str(e)}")
        return None


def search_trakt_by_title(title: str, year: Optional[int], media_type: str) -> Optional[Dict[str, Any]]:
    """
    Search Trakt by title and year to get TMDB ID and other metadata.
    
    Args:
        title (str): Title to search for
        year (Optional[int]): Release year (helps with matching)
        media_type (str): 'movie' or 'tv'
        
    Returns:
        Optional[Dict[str, Any]]: Media info with IDs or None if not found
    """
    try:
        logger.info(f"Searching Trakt by title: '{title}' ({year}) [{media_type}]")
        
        # Map media_type to Trakt API endpoint: 'tv' -> 'show', 'movie' -> 'movie'
        trakt_type = 'show' if media_type == 'tv' else media_type
        
        # Use text query search
        url = f"{TRAKT_BASE_URL}/search/{trakt_type}"
        params = {"query": title}
        
        response = requests.get(url, headers=get_trakt_headers(), params=params, timeout=30)
        
        # Handle rate limiting
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 10))
            logger.warning(f"Trakt API rate limit hit. Waiting {retry_after} seconds...")
            import time
            time.sleep(retry_after)
            response = requests.get(url, headers=get_trakt_headers(), params=params, timeout=30)
        
        response.raise_for_status()
        results = response.json()
        
        if not results or len(results) == 0:
            logger.info(f"No results found for title: '{title}'")
            return None
        
        logger.info(f"Found {len(results)} results for '{title}'")
        
        # Find best match based on year
        best_match = None
        exact_year_match = False
        
        for result in results:
            result_type = result.get('type')
            
            # Extract the media object
            if result_type == 'movie':
                media = result.get('movie', {})
            elif result_type == 'show':
                media = result.get('show', {})
            else:
                continue
            
            result_title = media.get('title')
            result_year = media.get('year')
            ids = media.get('ids', {})
            
            # If we have a year, try to match it
            if year and result_year:
                if result_year == year:
                    logger.info(f"Exact year match found: '{result_title}' ({result_year})")
                    best_match = {
                        "title": result_title,
                        "year": result_year,
                        "media_type": media_type,
                        "tmdb_id": ids.get('tmdb'),
                        "imdb_id": ids.get('imdb'),
                        "trakt_id": ids.get('trakt')
                    }
                    exact_year_match = True
                    break
                elif not exact_year_match and abs(result_year - year) <= 1:
                    # Close year match (±1 year)
                    if not best_match:
                        best_match = {
                            "title": result_title,
                            "year": result_year,
                            "media_type": media_type,
                            "tmdb_id": ids.get('tmdb'),
                            "imdb_id": ids.get('imdb'),
                            "trakt_id": ids.get('trakt')
                        }
            else:
                # No year to match against, take first result
                if not best_match:
                    best_match = {
                        "title": result_title,
                        "year": result_year,
                        "media_type": media_type,
                        "tmdb_id": ids.get('tmdb'),
                        "imdb_id": ids.get('imdb'),
                        "trakt_id": ids.get('trakt')
                    }
        
        if best_match and best_match.get('tmdb_id'):
            logger.info(f"Found TMDB ID {best_match['tmdb_id']} for '{title}'")
        
        return best_match
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            logger.error("Trakt API authentication failed")
        else:
            logger.error(f"Trakt API error searching by title: {e.response.status_code}")
        return None
    except Exception as e:
        logger.error(f"Error searching Trakt by title '{title}': {str(e)}")
        return None


def fetch_trakt_list(list_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Fetch Trakt list using Trakt API v2.
    
    Supports:
    - User custom lists: https://trakt.tv/users/{username}/lists/{list-slug}
    - User watchlists: https://trakt.tv/users/{username}/watchlist
    - Public lists: https://trakt.tv/lists/{numeric-id}
    - Special lists: trending:movies, popular:shows, etc.
    
    Args:
        list_id (str): Trakt list ID, URL, or shortcut
        limit (Optional[int]): Maximum number of items to fetch (for special lists)
        
    Returns:
        List[Dict[str, Any]]: List of media items with title, year, media_type, tmdb_id, imdb_id
        
    Raises:
        ValueError: If list ID format is invalid or API credentials not set
        requests.HTTPError: If API request fails
    """
    media_items = []
    logger.info(f"Fetching Trakt list: {list_id}")
    
    try:
        # Parse the list ID to get API endpoint
        endpoint = parse_trakt_list_url(list_id)
        url = f"{TRAKT_BASE_URL}{endpoint}"
        
        logger.info(f"Fetching from API endpoint: {url}")
        
        # Check if this is a special list (trending, popular, etc.)
        is_special_list = any(keyword in endpoint for keyword in ['/movies/', '/shows/'])
        
        try:
            if is_special_list and limit:
                # Special lists support pagination
                params = {"limit": min(limit, 100), "page": 1}
                response = requests.get(url, headers=get_trakt_headers(), params=params, timeout=30)
            else:
                # Regular lists and watchlists
                response = requests.get(url, headers=get_trakt_headers(), timeout=30)
            
            response.raise_for_status()
            items = response.json()
            
            if not isinstance(items, list):
                raise ValueError(f"Unexpected API response format: expected list, got {type(items)}")
            
            logger.info(f"Found {len(items)} items in list")
            
            # Parse each item
            for item in items:
                try:
                    if is_special_list:
                        media = extract_media_from_special_list_item(item, endpoint)
                    else:
                        media = extract_media_from_list_item(item)
                    
                    if media:
                        media_items.append({
                            "title": media["title"],
                            "media_type": media["media_type"],
                            "year": media.get("year"),
                            "tmdb_id": media.get("tmdb_id"),
                            "imdb_id": media.get("imdb_id"),
                            "season_number": media.get("season_number"),  # Include season number if present
                            "poster_path": media.get("poster_path")  # Include poster path if available
                        })
                        
                        # Log every 10th item to reduce log verbosity
                        if len(media_items) % 10 == 0 or len(media_items) <= 5:
                            ids_info = f"TMDB: {media.get('tmdb_id')}, IMDB: {media.get('imdb_id')}" if media.get('tmdb_id') or media.get('imdb_id') else "No IDs"
                            season_info = f" Season {media.get('season_number')}" if media.get('season_number') else ""
                            logger.info(f"Added {media['media_type']}: {media['title']} ({media.get('year', 'unknown year')}){season_info} [{ids_info}]")
                except Exception as item_error:
                    logger.warning(f"Failed to parse item from Trakt list: {str(item_error)}")
                    continue  # Skip this item and continue with others
            
            logger.info(f"Trakt list {list_id} fetched successfully. Found {len(media_items)} items.")
            return media_items
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout while fetching Trakt list: {list_id}")
            raise ValueError(f"Request timeout while fetching Trakt list. Please try again.")
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error while fetching Trakt list: {list_id}")
            raise ValueError(f"Connection error while fetching Trakt list. Please check your internet connection.")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.error(f"Trakt list not found: {list_id}")
                raise ValueError(f"Trakt list not found: {list_id}. Please check the list URL or ID.")
            elif e.response.status_code == 401:
                logger.error("Trakt API authentication failed. Please check your TRAKT_API_KEY.")
                raise ValueError("Trakt API authentication failed. Please check your TRAKT_API_KEY.")
            elif e.response.status_code == 429:
                retry_after = e.response.headers.get('Retry-After', '60')
                logger.warning(f"Trakt API rate limit reached. Retry after {retry_after} seconds")
                raise ValueError(f"Trakt API rate limit reached. Please try again in {retry_after} seconds.")
            else:
                error_text = e.response.text[:200] if e.response.text else "No error details"
                logger.error(f"Trakt API error: {e.response.status_code} - {error_text}")
                raise ValueError(f"Trakt API error ({e.response.status_code}): {error_text}")
                
    except ValueError as ve:
        # Re-raise ValueError as-is (these are user-friendly messages)
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching Trakt list {list_id}: {str(e)}", exc_info=True)
        raise ValueError(f"Failed to fetch Trakt list: {str(e)}")
