"""
Trakt API integration module
Handles fetching media information from Trakt
"""
import time
import requests
from typing import Optional, Dict, Tuple
from datetime import datetime, timezone
from loguru import logger

from seerr.config import TRAKT_API_KEY

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
    url = f"https://api.trakt.tv/search/tmdb/{tmdb_id}?type={trakt_type}"
    headers = {
        "Content-type": "application/json",
        "trakt-api-key": TRAKT_API_KEY,
        "trakt-api-version": "2"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        trakt_api_calls += 1

        if response.status_code == 200:
            data = response.json()
            if data and isinstance(data, list) and data:
                media_info = data[0][trakt_type]
                return {
                    "title": media_info['title'],
                    "year": media_info['year'],
                    "imdb_id": media_info['ids']['imdb'],
                    "trakt_id": media_info['ids']['trakt']  # Add Trakt ID to the return dict
                }
            else:
                logger.error(f"{trakt_type.capitalize()} details for ID not found in Trakt API response.")
                return None
        else:
            logger.error(f"Trakt API request failed with status code {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching {trakt_type} details from Trakt API: {e}")
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

    logger.debug(f"Starting check_next_episode_aired with trakt_show_id={trakt_show_id}, season_number={season_number}, current_aired_episodes={current_aired_episodes}")

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
    logger.debug(f"Current time: {current_time}, Last reset time: {last_reset_time}")

    if current_time - last_reset_time >= TRAKT_RATE_LIMIT_PERIOD:
        logger.debug("Rate limit period expired. Resetting API call counter.")
        trakt_api_calls = 0
        last_reset_time = current_time

    if trakt_api_calls >= TRAKT_RATE_LIMIT:
        wait_time = TRAKT_RATE_LIMIT_PERIOD - (current_time - last_reset_time)
        logger.warning(f"Trakt API rate limit reached. Sleeping for {wait_time} seconds.")
        time.sleep(wait_time)
        trakt_api_calls = 0
        last_reset_time = time.time()
        logger.debug("Woke up from sleep. Reset API call counter.")

    next_episode_number = current_aired_episodes + 1
    url = f"https://api.trakt.tv/shows/{trakt_show_id}/seasons/{season_number}/episodes/{next_episode_number}?extended=full"
    headers = {
        "Content-type": "application/json",
        "trakt-api-key": TRAKT_API_KEY,
        "trakt-api-version": "2"
    }

    logger.debug(f"Sending GET request to {url}")

    try:
        logger.info(f"Fetching next episode details for show ID {trakt_show_id}, season {season_number}, episode {next_episode_number}")
        response = requests.get(url, headers=headers, timeout=10)
        trakt_api_calls += 1
        logger.debug(f"Received response with status code {response.status_code}")

        if response.status_code == 200:
            episode_data = response.json()
            logger.debug(f"Next episode data: {episode_data}")

            first_aired = episode_data.get('first_aired')
            logger.debug(f"Next episode first_aired: {first_aired}")

            if first_aired:
                try:
                    first_aired_datetime = datetime.fromisoformat(first_aired.replace('Z', '+00:00'))
                    current_utc_time = datetime.now(timezone.utc)
                    logger.debug(f"Parsed first_aired_datetime: {first_aired_datetime}, current_utc_time: {current_utc_time}")

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