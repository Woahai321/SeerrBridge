"""
Trakt API integration module
Handles fetching media information from Trakt
"""
import time
import requests
from typing import Optional, Dict, Tuple
from datetime import datetime, timezone
from loguru import logger

from seerr.config import TRAKT_API_KEY, USE_DATABASE
from seerr.database import get_db
from seerr.unified_models import UnifiedMedia
from seerr.db_logger import log_info, log_success, log_error

# Trakt API rate limit: 1000 calls every 5 minutes
TRAKT_RATE_LIMIT = 1000
TRAKT_RATE_LIMIT_PERIOD = 5 * 60  # 5 minutes in seconds

trakt_api_calls = 0
last_reset_time = time.time()

def get_media_details_from_trakt(tmdb_id: str, media_type: str) -> Optional[dict]:
    """
    Fetch media details from Trakt API using TMDb ID
    
    Args:
        tmdb_id (str): TMDb ID of the movie or TV show
        media_type (str): 'movie' or 'tv'
        
    Returns:
        Optional[dict]: Media details if successful, None if failed
    """
    global trakt_api_calls, last_reset_time

    current_time = time.time()
    if current_time - last_reset_time >= TRAKT_RATE_LIMIT_PERIOD:
        trakt_api_calls = 0
        last_reset_time = current_time

    if trakt_api_calls >= TRAKT_RATE_LIMIT:
        logger.warning("Trakt API rate limit reached. Waiting for the next period.")
        time.sleep(TRAKT_RATE_LIMIT_PERIOD - (current_time - last_reset_time))
        trakt_api_calls = 0
        last_reset_time = time.time()

    # Determine the type based on media_type
    trakt_type = 'show' if media_type == 'tv' else 'movie'
    
    # Check database first for existing Trakt ID to avoid unnecessary search API call
    trakt_id = None
    if USE_DATABASE:
        try:
            db = get_db()
            existing_media = db.query(UnifiedMedia).filter(
                UnifiedMedia.tmdb_id == int(tmdb_id)
            ).first()
            if existing_media and existing_media.trakt_id:
                trakt_id = int(existing_media.trakt_id)
                logger.info(f"Found existing Trakt ID {trakt_id} for TMDB ID {tmdb_id} in database, skipping search API call")
        except Exception as e:
            logger.warning(f"Error checking database for Trakt ID: {e}")
        finally:
            if 'db' in locals():
                db.close()
    
    # If we don't have Trakt ID from database, fetch it via search API
    search_url = None
    search_response_time = None
    if trakt_id is None:
        url = f"https://api.trakt.tv/search/tmdb/{tmdb_id}?type={trakt_type}"
        headers = {
            "Content-type": "application/json",
            "trakt-api-key": TRAKT_API_KEY,
            "trakt-api-version": "2"
        }

        try:
            start_time = time.time()
            response = requests.get(url, headers=headers, timeout=10)
            search_response_time = time.time() - start_time
            trakt_api_calls += 1
            search_url = url

            if response.status_code == 200:
                data = response.json()
                if data and isinstance(data, list) and data:
                    media_info = data[0][trakt_type]
                    trakt_id = media_info['ids']['trakt']
                    if USE_DATABASE:
                        track_trakt_api_usage(url, True, search_response_time)
                else:
                    logger.error(f"{trakt_type.capitalize()} details for ID not found in Trakt API response.")
                    if USE_DATABASE:
                        track_trakt_api_usage(url, False, search_response_time)
                    return None
            else:
                logger.error(f"Trakt API request failed with status code {response.status_code}")
                if USE_DATABASE:
                    track_trakt_api_usage(url, False, search_response_time)
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching {trakt_type} details from Trakt API: {e}")
            if USE_DATABASE:
                track_trakt_api_usage(url, False)
            return None
    
    # Now fetch all details from extended endpoint (includes title, year, imdb_id, and more)
    # This replaces the need to extract basic info from the search endpoint
    detailed_info = get_detailed_media_info(trakt_id, trakt_type)
    if not detailed_info:
        return None
    
    # Extract all media details from the extended endpoint response
    # The extended endpoint provides everything we need including title, year, imdb_id
    media_details = {
        "title": detailed_info.get('title', 'Unknown Title'),
        "year": detailed_info.get('year', 0),
        "imdb_id": detailed_info.get('imdb_id', ''),
        "trakt_id": str(trakt_id)
    }
    
    # Add all the detailed information (overview, genres, runtime, etc.)
    media_details.update({
        "overview": detailed_info.get('overview', ''),
        "genres": detailed_info.get('genres', []),
        "runtime": detailed_info.get('runtime', 0),
        "rating": detailed_info.get('rating', 0.0),
        "vote_count": detailed_info.get('vote_count', 0),
        "popularity": detailed_info.get('popularity', 0.0),
        "status": detailed_info.get('status', ''),
        "network": detailed_info.get('network', ''),
        "country": detailed_info.get('country', ''),
        "language": detailed_info.get('language', ''),
        "certification": detailed_info.get('certification', ''),
        "trailer": detailed_info.get('trailer', ''),
        "homepage": detailed_info.get('homepage', ''),
        "tagline": detailed_info.get('tagline', ''),
        "poster_url": detailed_info.get('poster_url', ''),
        "fanart_url": detailed_info.get('fanart_url', ''),
        "backdrop_url": detailed_info.get('backdrop_url', ''),
        "released_date": detailed_info.get('released_date')
    })
    
    # Save to database if enabled
    if USE_DATABASE:
        save_media_details_to_database(tmdb_id, media_type, media_details)
        # Only track search API call if we actually made one
        if search_url and search_response_time:
            pass  # Already tracked above
    
    return media_details

def get_detailed_media_info(trakt_id: int, trakt_type: str) -> Optional[dict]:
    """
    Fetch detailed media information from Trakt API using Trakt ID
    
    Args:
        trakt_id (int): Trakt ID of the media
        trakt_type (str): 'movie' or 'show'
        
    Returns:
        Optional[dict]: Detailed media information if successful, None if failed
    """
    global trakt_api_calls, last_reset_time

    current_time = time.time()
    if current_time - last_reset_time >= TRAKT_RATE_LIMIT_PERIOD:
        trakt_api_calls = 0
        last_reset_time = current_time

    if trakt_api_calls >= TRAKT_RATE_LIMIT:
        logger.warning("Trakt API rate limit reached. Waiting for the next period.")
        time.sleep(TRAKT_RATE_LIMIT_PERIOD - (current_time - last_reset_time))
        trakt_api_calls = 0
        last_reset_time = time.time()

    # Get detailed information
    url = f"https://api.trakt.tv/{trakt_type}s/{trakt_id}?extended=full"
    headers = {
        "Content-type": "application/json",
        "trakt-api-key": TRAKT_API_KEY,
        "trakt-api-version": "2"
    }

    try:
        start_time = time.time()
        response = requests.get(url, headers=headers, timeout=10)
        response_time = time.time() - start_time
        trakt_api_calls += 1

        if response.status_code == 200:
            data = response.json()
            
            # Extract IDs (imdb_id is needed from the extended endpoint)
            imdb_id = ''
            if 'ids' in data and data['ids']:
                imdb_id = data['ids'].get('imdb', '')
            
            # Get title - handle different field names for movies vs shows
            title = data.get('title') or data.get('name', 'Unknown Title')
            
            # Extract released date if available
            released_date = None
            if 'released' in data and data['released']:
                try:
                    # Trakt API returns dates in YYYY-MM-DD format
                    released_date = datetime.strptime(data['released'], '%Y-%m-%d')
                    # Make it timezone-aware (UTC)
                    released_date = released_date.replace(tzinfo=timezone.utc)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse released date '{data.get('released')}': {e}")
                    released_date = None
            
            detailed_info = {
                "title": title,
                "year": data.get('year', 0),
                "imdb_id": imdb_id,
                "overview": data.get('overview', ''),
                "genres": data.get('genres', []),
                "runtime": data.get('runtime', 0),
                "rating": data.get('rating', 0.0),
                "vote_count": data.get('votes', 0),
                "popularity": data.get('popularity', 0.0),
                "status": data.get('status', ''),
                "network": data.get('network', ''),
                "country": data.get('country', ''),
                "language": data.get('language', ''),
                "certification": data.get('certification', ''),
                "trailer": data.get('trailer', ''),
                "homepage": data.get('homepage', ''),
                "tagline": data.get('tagline', ''),
                "released_date": released_date
            }
            
            # Add images if available
            if 'images' in data:
                images = data['images']
                if 'poster' in images and images['poster']:
                    detailed_info['poster_url'] = images['poster']['full']
                if 'fanart' in images and images['fanart']:
                    detailed_info['fanart_url'] = images['fanart']['full']
                if 'backdrop' in images and images['backdrop']:
                    detailed_info['backdrop_url'] = images['backdrop']['full']
            
            track_trakt_api_usage(url, True, response_time)
            return detailed_info
        else:
            logger.error(f"Trakt API detailed request failed with status code {response.status_code}")
            track_trakt_api_usage(url, False, response_time)
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching detailed {trakt_type} info from Trakt API: {e}")
        track_trakt_api_usage(url, False)
        return None

def get_season_details_from_trakt(trakt_show_id: str, season_number: int) -> Optional[dict]:
    """
    Fetch season details from Trakt API using a Trakt show ID and season number.
    
    Args:
        trakt_show_id (str): The Trakt ID of the show, obtained from get_media_details_from_trakt
        season_number (int): The season number to fetch details for
    
    Returns:
        Optional[dict]: Season details if successful, None if failed
    """
    global trakt_api_calls, last_reset_time

    # Validate input parameters
    if not trakt_show_id or not isinstance(trakt_show_id, str):
        logger.error(f"Invalid trakt_show_id provided: {trakt_show_id}")
        return None
    if not isinstance(season_number, int) or season_number < 0:
        logger.error(f"Invalid season_number provided: {season_number}")
        return None

    current_time = time.time()
    if current_time - last_reset_time >= TRAKT_RATE_LIMIT_PERIOD:
        trakt_api_calls = 0
        last_reset_time = current_time

    if trakt_api_calls >= TRAKT_RATE_LIMIT:
        logger.warning("Trakt API rate limit reached. Waiting for the next period.")
        time.sleep(TRAKT_RATE_LIMIT_PERIOD - (current_time - last_reset_time))
        trakt_api_calls = 0
        last_reset_time = time.time()

    url = f"https://api.trakt.tv/shows/{trakt_show_id}/seasons/{season_number}/info?extended=full"
    headers = {
        "Content-type": "application/json",
        "trakt-api-key": TRAKT_API_KEY,
        "trakt-api-version": "2"
    }

    try:
        logger.info(f"Fetching season details for show ID {trakt_show_id}, season {season_number}")
        response = requests.get(url, headers=headers, timeout=10)
        trakt_api_calls += 1

        if response.status_code == 200:
            data = response.json()
            logger.info(f"Successfully fetched season {season_number} details for show ID {trakt_show_id}")
            return data
        else:
            logger.error(f"Trakt API season request failed with status code {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching season details from Trakt API for show ID {trakt_show_id}, season {season_number}: {e}")
        return None

def check_next_episode_aired(trakt_show_id: str, season_number: int, current_aired_episodes: int) -> Tuple[bool, Optional[dict]]:
    """
    Check if the next episode (current_aired_episodes + 1) has aired for a given show and season.
    
    Args:
        trakt_show_id (str): The Trakt ID of the show
        season_number (int): The season number to check
        current_aired_episodes (int): The current number of aired episodes in the season
    
    Returns:
        tuple[bool, Optional[dict]]: (has_aired, episode_details)
            - has_aired: True if the next episode has aired, False otherwise
            - episode_details: Episode details if the episode exists, None otherwise
    """
    global trakt_api_calls, last_reset_time

    # Starting check_next_episode_aired

    # Validate input parameters
    if not trakt_show_id or not isinstance(trakt_show_id, str):
        logger.error(f"Invalid trakt_show_id provided: {trakt_show_id}")
        return False, None
    if not isinstance(season_number, int) or season_number < 0:
        logger.error(f"Invalid season_number provided: {season_number}")
        return False, None
    if not isinstance(current_aired_episodes, int) or current_aired_episodes < 0:
        logger.error(f"Invalid current_aired_episodes provided: {current_aired_episodes}")
        return False, None

    current_time = time.time()

    if current_time - last_reset_time >= TRAKT_RATE_LIMIT_PERIOD:
        # Rate limit period expired, resetting API call counter
        trakt_api_calls = 0
        last_reset_time = current_time

    if trakt_api_calls >= TRAKT_RATE_LIMIT:
        wait_time = TRAKT_RATE_LIMIT_PERIOD - (current_time - last_reset_time)
        logger.warning(f"Trakt API rate limit reached. Sleeping for {wait_time} seconds.")
        time.sleep(wait_time)
        trakt_api_calls = 0
        last_reset_time = time.time()
        # Woke up from sleep, reset API call counter

    next_episode_number = current_aired_episodes + 1
    url = f"https://api.trakt.tv/shows/{trakt_show_id}/seasons/{season_number}/episodes/{next_episode_number}?extended=full"
    headers = {
        "Content-type": "application/json",
        "trakt-api-key": TRAKT_API_KEY,
        "trakt-api-version": "2"
    }

    # Sending GET request to Trakt API

    try:
        logger.info(f"Fetching next episode details for show ID {trakt_show_id}, season {season_number}, episode {next_episode_number}")
        response = requests.get(url, headers=headers, timeout=10)
        trakt_api_calls += 1
        # Received response from Trakt API

        if response.status_code == 200:
            episode_data = response.json()
            # Next episode data received

            first_aired = episode_data.get('first_aired')
            # Next episode first_aired data

            if first_aired:
                try:
                    first_aired_datetime = datetime.fromisoformat(first_aired.replace('Z', '+00:00'))
                    current_utc_time = datetime.now(timezone.utc)
                    # Parsed first_aired_datetime and current_utc_time

                    if current_utc_time >= first_aired_datetime:
                        logger.info(f"Episode {next_episode_number} has aired for show ID {trakt_show_id}, season {season_number}")
                        return True, episode_data
                    else:
                        logger.info(f"Episode {next_episode_number} has not aired yet for show ID {trakt_show_id}, season {season_number}")
                        return False, episode_data
                except ValueError as e:
                    logger.error(f"Invalid first_aired format for episode {next_episode_number}: {e}")
                    return False, episode_data
            else:
                logger.warning(f"Episode {next_episode_number} missing 'first_aired' field for show ID {trakt_show_id}, season {season_number}")
                return False, episode_data

        elif response.status_code == 404:
            logger.info(f"Episode {next_episode_number} does not exist yet for show ID {trakt_show_id}, season {season_number}")
            return False, None
        else:
            logger.warning(f"Failed to fetch next episode details for show ID {trakt_show_id}, season {season_number}, episode {next_episode_number}: Status code {response.status_code}")
            return False, None

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching next episode details from Trakt API for show ID {trakt_show_id}, season {season_number}, episode {next_episode_number}: {e}")
        return False, None

def save_media_details_to_database(tmdb_id: str, media_type: str, media_details: dict) -> bool:
    """
    Save media details from Trakt to the database
    
    Args:
        tmdb_id (str): TMDb ID
        media_type (str): Type of media (movie/tv)
        media_details (dict): Media details from Trakt
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not USE_DATABASE:
        return False
    
    try:
        db = get_db()
        
        # Check if media request already exists
        existing_request = db.query(UnifiedMedia).filter(
            UnifiedMedia.tmdb_id == int(tmdb_id)
        ).first()
        
        if existing_request:
            # Update existing request with Trakt details
            existing_request.trakt_id = str(media_details.get('trakt_id', ''))
            existing_request.imdb_id = media_details.get('imdb_id', '')
            existing_request.title = media_details.get('title', existing_request.title)
            existing_request.year = media_details.get('year', existing_request.year)
            existing_request.media_type = media_type
            
            # Update released_date if available
            released_date = media_details.get('released_date')
            if released_date:
                existing_request.released_date = released_date
                
                # Check if release date is in the future
                current_time = datetime.now(timezone.utc)
                if released_date > current_time:
                    # Media is unreleased - set status to unreleased if not already processing/completed
                    if existing_request.status not in ['processing', 'completed', 'failed']:
                        existing_request.status = 'unreleased'
                        log_info("Trakt Integration", f"Media {tmdb_id} ({existing_request.title}) is unreleased (releases {released_date.strftime('%Y-%m-%d')}), status set to unreleased")
                else:
                    # Media is released or already released - update to pending if currently unreleased
                    if existing_request.status == 'unreleased':
                        existing_request.status = 'pending'
                        log_info("Trakt Integration", f"Media {tmdb_id} ({existing_request.title}) release date has passed, status updated to pending")
            
            # Update rich media data
            existing_request.overview = media_details.get('overview', existing_request.overview)
            existing_request.genres = media_details.get('genres', existing_request.genres)
            existing_request.runtime = media_details.get('runtime', existing_request.runtime)
            existing_request.rating = media_details.get('rating', existing_request.rating)
            existing_request.vote_count = media_details.get('vote_count', existing_request.vote_count)
            existing_request.popularity = media_details.get('popularity', existing_request.popularity)
            
            # Update image URLs
            existing_request.poster_url = media_details.get('poster_url', existing_request.poster_url)
            existing_request.fanart_url = media_details.get('fanart_url', existing_request.fanart_url)
            existing_request.backdrop_url = media_details.get('backdrop_url', existing_request.backdrop_url)
            
            # Update extra_data with additional Trakt information
            if not existing_request.extra_data:
                existing_request.extra_data = {}
            elif isinstance(existing_request.extra_data, list):
                # Convert old list format to dict format
                existing_request.extra_data = {}
            
            # Ensure extra_data is a dictionary before calling update
            if isinstance(existing_request.extra_data, dict):
                existing_request.extra_data.update({
                    'trakt_status': media_details.get('status', ''),
                    'trakt_network': media_details.get('network', ''),
                    'trakt_country': media_details.get('country', ''),
                    'trakt_language': media_details.get('language', ''),
                    'trakt_certification': media_details.get('certification', ''),
                    'trakt_trailer': media_details.get('trailer', ''),
                    'trakt_homepage': media_details.get('homepage', ''),
                    'trakt_tagline': media_details.get('tagline', '')
                })
            else:
                # If it's neither dict nor list, initialize as dict
                existing_request.extra_data = {
                    'trakt_status': media_details.get('status', ''),
                    'trakt_network': media_details.get('network', ''),
                    'trakt_country': media_details.get('country', ''),
                    'trakt_language': media_details.get('language', ''),
                    'trakt_certification': media_details.get('certification', ''),
                    'trakt_trailer': media_details.get('trailer', ''),
                    'trakt_homepage': media_details.get('homepage', ''),
                    'trakt_tagline': media_details.get('tagline', '')
                }
            
            db.commit()
            
            log_success("Trakt Integration", f"Updated media request {tmdb_id} with rich Trakt details")
            return True
        else:
            # Don't create new media requests here - they should be created by the Overseerr integration
            # Just log that we have Trakt details available for future use
            log_info("Trakt Integration", f"Trakt details available for {tmdb_id} but no existing media request found")
            return True
            
    except Exception as e:
        log_error("Database Error", f"Failed to save Trakt details for {tmdb_id}: {e}")
        if 'db' in locals():
            db.rollback()
        return False
    finally:
        if 'db' in locals():
            db.close()

def get_media_details_from_database(tmdb_id: str) -> Optional[dict]:
    """
    Get media details from the database
    
    Args:
        tmdb_id (str): TMDb ID
        
    Returns:
        Optional[dict]: Media details if found, None otherwise
    """
    if not USE_DATABASE:
        return None
    
    try:
        db = get_db()
        media_request = db.query(UnifiedMedia).filter(
            UnifiedMedia.tmdb_id == int(tmdb_id)
        ).first()
        
        if media_request and media_request.extra_data:
            trakt_details = media_request.extra_data.get('trakt_details')
            if trakt_details:
                return trakt_details
        
        return None
        
    except Exception as e:
        log_error("Database Error", f"Failed to get media details for {tmdb_id}: {e}")
        return None
    finally:
        if 'db' in locals():
            db.close()

def track_trakt_api_usage(api_endpoint: str, success: bool, response_time: float = None) -> bool:
    """
    Track Trakt API usage in the database
    
    Args:
        api_endpoint (str): API endpoint called
        success (bool): Whether the API call was successful
        response_time (float): Response time in seconds
        
    Returns:
        bool: True if successfully tracked, False otherwise
    """
    if not USE_DATABASE:
        return False
    
    try:
        # Log the API usage
        if success:
            log_success("Trakt API", f"API call to {api_endpoint} successful (response time: {response_time}s)")
        else:
            log_error("Trakt API", f"API call to {api_endpoint} failed")
        
        return True
        
    except Exception as e:
        log_error("Database Error", f"Failed to track Trakt API usage: {e}")
        return False

def get_trakt_rate_limit_status() -> dict:
    """
    Get current Trakt API rate limit status
    
    Returns:
        dict: Rate limit status information
    """
    global trakt_api_calls, last_reset_time
    
    current_time = time.time()
    time_until_reset = TRAKT_RATE_LIMIT_PERIOD - (current_time - last_reset_time)
    calls_remaining = TRAKT_RATE_LIMIT - trakt_api_calls
    
    status = {
        'calls_made': trakt_api_calls,
        'calls_remaining': max(0, calls_remaining),
        'rate_limit': TRAKT_RATE_LIMIT,
        'time_until_reset': max(0, time_until_reset),
        'rate_limit_period': TRAKT_RATE_LIMIT_PERIOD
    }
    
    log_info("Trakt Rate Limit", f"Rate limit status: {status}")
    return status 