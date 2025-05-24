"""
Utility functions for SeerrBridge
"""
import re
import inflect
from loguru import logger
from fuzzywuzzy import fuzz
from deep_translator import GoogleTranslator
from datetime import datetime


# Initialize the inflect engine for number-word conversion
p = inflect.engine()

# Add a global variable to track start time
START_TIME = datetime.now()


def translate_title(title, target_lang='en'):
    """
    Detects the language of the input title and translates it to the target language.
    """
    try:
        translator = GoogleTranslator(source='auto', target=target_lang)
        translated_title = translator.translate(title)
        logger.info(f"Translated '{title}' to '{translated_title}'")
        return translated_title
    except Exception as e:
        logger.error(f"Error translating title '{title}': {e}")
        return title  # Return the original title if translation fails

def clean_title(title, target_lang='en'):
    """
    Cleans the movie title by removing commas, hyphens, colons, semicolons, and apostrophes,
    translating it to the target language, and converting to lowercase.
    For TV shows with episode information, extracts just the main title before cleaning.
    """
    # Translate the title to the target language
    translated_title = translate_title(title, target_lang)
    
    # For TV shows, extract just the main title (before any S01E01 pattern)
    # This helps with matching by ignoring episode info and technical specs
    main_title = translated_title
    season_ep_match = re.search(r'S\d+E\d+', translated_title, re.IGNORECASE)
    if season_ep_match:
        main_title = translated_title[:season_ep_match.start()].strip()
    
    # Remove commas, hyphens, colons, semicolons, and apostrophes
    cleaned_title = re.sub(r"[,:;'-]", '', main_title)
    # Replace multiple spaces with a single dot
    cleaned_title = re.sub(r'\s+', '.', cleaned_title)
    # Convert to lowercase for comparison
    return cleaned_title.lower()

def normalize_title(title, target_lang='en'):
    """
    Normalizes the title by ensuring there are no unnecessary spaces or dots,
    translating it to the target language, and converting to lowercase.
    """
    # Replace ellipsis with three periods
    title = title.replace('…', '...')
    # Replace smart apostrophes with regular apostrophes
    title = title.replace("'", "'")
    
    # Translate the title to the target language
    translated_title = translate_title(title, target_lang)

    # Replace multiple spaces with a single space and dots with spaces
    normalized_title = re.sub(r'\s+', ' ', translated_title)
    normalized_title = normalized_title.replace('.', ' ')
    # Convert to lowercase
    return normalized_title.lower()

def replace_numbers_with_words(title):
    """
    Replaces digits with their word equivalents (e.g., "3" to "three").
    """
    return re.sub(r'\b\d+\b', lambda x: p.number_to_words(x.group()), title)

def replace_words_with_numbers(title):
    """
    Replaces number words with their digit equivalents (e.g., "three" to "3").
    """
    words_to_numbers = {
        "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
        "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
        "ten": "10", "eleven": "11", "twelve": "12", "thirteen": "13",
        "fourteen": "14", "fifteen": "15", "sixteen": "16", "seventeen": "17",
        "eighteen": "18", "nineteen": "19", "twenty": "20"
        # Add more mappings as needed
    }

    # Replace word numbers with digits
    for word, digit in words_to_numbers.items():
        title = re.sub(rf'\b{word}\b', digit, title, flags=re.IGNORECASE)
    return title

def extract_year(text, expected_year=None, ignore_resolution=False):
    """
    Extracts the correct year from a movie title.
    
    - Uses the explicitly provided expected_year (from TMDb or Trakt) if available.
    - Ensures the year is not mistakenly extracted from the movie's name (like '1984' in 'Wonder Woman 1984').
    """
    if expected_year:
        return expected_year  # Prioritize the known year from a reliable source

    # Remove common video resolutions that might interfere
    if ignore_resolution:
        text = re.sub(r'\b\d{3,4}p\b', '', text)

    # Extract years explicitly (avoid numbers inside movie titles)
    years = re.findall(r'\b(19\d{2}|20\d{2})\b', text)
    
    if years:
        # If multiple years are found, prefer the latest one
        return int(max(years))

    return None  # Return None if no valid year is found

def parse_requested_seasons(extra_data):
    """
    Parse the requested seasons from the extra data in the JSON payload.
    """
    if not extra_data:
        return []

    for item in extra_data:
        if item['name'] == 'Requested Seasons':
            return item['value'].split(', ')
    return []

def normalize_season(season):
    """
    Normalize season strings to a consistent format (e.g., "Season 1", "Season 2").
    Handles formats like "S01", "S1", "Season 1", etc.
    """
    season = season.strip().lower()  # Normalize to lowercase
    if season.startswith('s') and season[1:].isdigit():  # Handle "S01", "S1", etc.
        season_number = int(season[1:])
        return f"Season {season_number}"
    elif season.startswith('season') and season[6:].strip().isdigit():  # Handle "Season 1", "Season 2", etc.
        season_number = int(season[6:].strip())
        return f"Season {season_number}"
    else:
        # Default to "Season X" if the format is unrecognized
        return f"Season {season}"

def match_complete_seasons(title, seasons):
    """
    Check if the title contains all requested seasons in a complete pack.
    """
    title = title.lower()
    for season in seasons:
        if f"complete {season.lower()}" not in title and f"complete {season.lower().replace('s', 'season ')}" not in title:
            return False
    return True

def match_single_season(title, season):
    """
    Check if the title contains the exact requested season.
    Handles formats like "Season 1", "S01", "S1", etc.
    """
    # Normalize the season string for comparison
    season = season.lower().strip()
    title = title.lower()

    # Extract the season number from the requested season
    if season.startswith("season"):
        season_number = season.replace("season", "").strip()
    elif season.startswith("s"):
        season_number = season.replace("s", "").strip()
    else:
        season_number = season

    # Ensure the season number is a valid integer
    try:
        season_number = int(season_number)
    except ValueError:
        logger.warning(f"Invalid season number format: {season}")
        return False

    # Match "Season X", "SX", or "S0X" in the title
    # Ensure the season number is exactly the one requested
    return (
        f"season {season_number}" in title or
        f"s{season_number}" in title or
        f"s{season_number:02d}" in title
    ) and not any(
        f"season {other_season}" in title or
        f"s{other_season}" in title or
        f"s{other_season:02d}" in title
        for other_season in range(1, 100) if other_season != season_number
    )

def extract_season(title):
    """
    Extract the season number from a title (e.g., 'naruto.s01.bdrip' → 1).
    """
    season_match = re.search(r"[sS](\d{1,2})", title)
    if season_match:
        return int(season_match.group(1))
    return None 