"""
Utility functions for SeerrBridge
"""
import re
import inflect
from loguru import logger
from fuzzywuzzy import fuzz
from deep_translator import GoogleTranslator
from datetime import datetime, timedelta
from seerr.config import USE_DATABASE
from seerr.database import get_db, LogEntry
from seerr.db_logger import log_info, log_success, log_error


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

def extract_main_title(title):
    """
    Extract the main title from a torrent name, removing technical specifications.
    For torrent filenames with dots, extract the title part before year and technical specs.
    Tries multiple extraction strategies to find the best result.
    """
    # Check if this looks like a torrent filename (has many dots)
    is_torrent_filename = title.count('.') >= 3 or ('.' in title and re.search(r'\d{4}', title))
    
    extraction_candidates = []
    
    if is_torrent_filename:
        # Strategy 1: Extract before year pattern (most reliable)
        # For dot-separated filenames like "Title.Title.2015.QUALITY", match ".2015" or ".2015."
        year_match = re.search(r'\.(19\d{2}|20\d{2})(?:\.|$)', title)
        if year_match:
            candidate = title[:year_match.start()].strip().rstrip('.').strip()
            if candidate:
                extraction_candidates.append(('year', candidate))
        
        # Strategy 2: Also try space-separated year pattern
        year_match_space = re.search(r'(?:^|\s)(19\d{2}|20\d{2})(?:\s|$)', title)
        if year_match_space:
            candidate = title[:year_match_space.start()].strip().rstrip('.').strip()
            if candidate and candidate != title:
                extraction_candidates.append(('year_space', candidate))
        
        # Strategy 3: Extract before common technical keywords
        tech_keywords = [
            r'\.(PROPER|REMASTERED|REPACK|EXTENDED|DIRECTOR|CUT)(?:\.|$)',  # Dot-separated keywords
            r'\b(PROPER|REMASTERED|REPACK|EXTENDED|DIRECTOR|CUT)\b',  # Word boundaries
            r'\.\d{3,4}p(?:\.|$)',  # .720p, .1080p, .2160p
            r'\b\d{3,4}p\b',  # 720p, 1080p, 2160p
            r'\.(BluRay|Blu-Ray|WEB-DL|HDTV|DVDRip|BDRip|BRRip|REMUX|Remux)(?:\.|$)',  # Dot-separated
            r'\b(BluRay|Blu-Ray|WEB-DL|HDTV|DVDRip|BDRip|BRRip|REMUX|Remux)\b',  # Word boundaries
            r'\.(HEVC|x265|x264|H264|H265)(?:\.|$)',  # Dot-separated codecs
            r'\b(HEVC|x265|x264|H264|H265)\b',  # Word boundaries
        ]
        
        earliest_match = None
        for pattern in tech_keywords:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                if earliest_match is None or match.start() < earliest_match.start():
                    earliest_match = match
        
        if earliest_match:
            candidate = title[:earliest_match.start()].strip().rstrip('.').strip()
            if candidate and candidate != title:
                extraction_candidates.append(('tech_keyword', candidate))
        
        # Strategy 4: If we have a long title with dots, try extracting first N segments
        # This handles cases where year/keywords aren't found but title is still extractable
        if title.count('.') >= 3:
            # Try taking first 3-5 segments (typical for movie titles)
            segments = title.split('.')
            for num_segments in range(3, min(6, len(segments))):
                candidate = '.'.join(segments[:num_segments])
                # Don't include if it looks like it ends with technical specs
                if not re.search(r'(PROPER|REMASTERED|REPACK|EXTENDED|\d{3,4}p|BluRay|REMUX)', candidate, re.IGNORECASE):
                    extraction_candidates.append(('segments', candidate))
                    break  # Use first reasonable segment count
        
        # Pick the best extraction candidate
        if extraction_candidates:
            # Prefer year-based extraction, then tech keyword, then segments
            priority_order = ['year', 'year_space', 'tech_keyword', 'segments']
            for priority in priority_order:
                for strategy, candidate in extraction_candidates:
                    if strategy == priority and candidate:
                        main_title = candidate
                        break
                else:
                    continue
                break
            else:
                # If no preferred strategy worked, use the first candidate
                main_title = extraction_candidates[0][1]
        else:
            # No extraction worked, return original (will be cleaned later)
            main_title = title
    else:
        # For regular titles (not torrent filenames), use original logic
        main_title = title
    
    # Remove common technical specifications that appear at the end
    patterns_to_remove = [
        r'\s*\[.*?\]\s*$',  # Remove [BluRay Rip 720p] etc at the end
        r'\s*\(.*?\)\s*$',  # Remove (AC3 2.0 Español) etc at the end
        r'\s*-\s*[A-Z0-9]+$',  # Remove -RARBG, -YIFY etc at the end
        r'\s*\.\s*[A-Z0-9]+$',  # Remove .RARBG, .YIFY etc at the end
    ]
    
    for pattern in patterns_to_remove:
        main_title = re.sub(pattern, '', main_title, flags=re.IGNORECASE)
    
    return main_title.strip()

def clean_title(title, target_lang='en'):
    """
    Cleans the movie title by removing commas, hyphens, colons, semicolons, and apostrophes,
    translating it to the target language, and converting to lowercase.
    For TV shows with episode information, extracts just the main title before cleaning.
    For torrent filenames, extracts the main title first before translating to avoid translation issues.
    If extraction fails, still attempts to clean and match the original title.
    """
    # Check if this looks like a torrent filename (has many dots or technical specs)
    is_torrent_filename = title.count('.') >= 3 or ('.' in title and re.search(r'\d{4}', title))
    
    if is_torrent_filename:
        # For torrent filenames: Extract main title FIRST, then translate
        # This prevents Google Translate from getting confused by dots and technical specs
        main_title = extract_main_title(title)
        
        # Check if extraction actually worked (not just returned the original)
        # If extraction failed or returned something very similar to original, try cleaning anyway
        extraction_succeeded = (main_title != title and 
                              len(main_title) < len(title) * 0.8 and  # At least 20% shorter
                              title.count('.') > main_title.count('.'))  # Has fewer dots
        
        if extraction_succeeded:
            # Replace dots with spaces for better translation
            main_title_for_translation = main_title.replace('.', ' ')
            translated_title = translate_title(main_title_for_translation, target_lang)
            main_title = translated_title
        else:
            # Extraction didn't work well, try translating the original with dots replaced
            # This handles cases where year/keywords weren't found but title is still valid
            main_title_for_translation = title.replace('.', ' ')
            translated_title = translate_title(main_title_for_translation, target_lang)
            main_title = translated_title
    else:
        # For regular titles: Translate first, then extract
        translated_title = translate_title(title, target_lang)
        main_title = extract_main_title(translated_title)
    
    # For TV shows, extract just the main title (before any S01E01 pattern)
    # This helps with matching by ignoring episode info and technical specs
    season_ep_match = re.search(r'S\d+E\d+', main_title, re.IGNORECASE)
    if season_ep_match:
        main_title = main_title[:season_ep_match.start()].strip()
    
    # Remove technical specifications and quality indicators that might interfere with matching
    # Remove resolution info (720p, 1080p, 2160p, etc.)
    main_title = re.sub(r'\b\d{3,4}p\b', '', main_title, flags=re.IGNORECASE)
    # Remove quality indicators (BluRay, WEB-DL, HDTV, etc.)
    main_title = re.sub(r'\b(BluRay|Blu-Ray|WEB-DL|HDTV|DVDRip|BDRip|BRRip|Remux|x265|x264)\b', '', main_title, flags=re.IGNORECASE)
    # Remove group names (RARBG, YIFY, etc.)
    main_title = re.sub(r'\b(RARBG|YIFY|YTS|HDBits|PublicHD)\b', '', main_title, flags=re.IGNORECASE)
    # Remove year ranges (2001–2011, 2001-2011)
    main_title = re.sub(r'\b\d{4}[-–]\d{4}\b', '', main_title)
    # Remove standalone years (4 digits) - but be careful not to remove years from movie names
    # Only remove if it's clearly a year (not part of a word and at word boundaries)
    main_title = re.sub(r'\b(19\d{2}|20\d{2})\b', '', main_title)
    
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
    - Handles parentheses format: (2009), space-separated, and dot-separated formats.
    """
    if expected_year:
        return expected_year  # Prioritize the known year from a reliable source

    # Remove common video resolutions that might interfere
    if ignore_resolution:
        text = re.sub(r'\b\d{3,4}p\b', '', text)

    # Extract years explicitly (avoid numbers inside movie titles)
    # Handle parentheses format: (2009) or (1984)
    years = re.findall(r'\((\d{4})\)', text)
    
    # If no parentheses format found, try space/dot-separated formats
    if not years:
        # Pattern matches years that are either at word boundaries or surrounded by dots/spaces
        years = re.findall(r'(?:^|[.\s])(19\d{2}|20\d{2})(?:[.\s]|$)', text)
    
    if years:
        # Filter to only valid years (1900-2099) and prefer the latest one
        valid_years = [int(y) for y in years if 1900 <= int(y) <= 2099]
        if valid_years:
            return int(max(valid_years))

    return None  # Return None if no valid year is found

def is_complete_word_match(movie_title, torrent_title):
    """
    Validates that the movie title appears as a complete word/phrase in the torrent title.
    Prevents substring matches like "bounty" matching "perriers bounty".
    For single-word titles, requires the word to be at the start or be the primary match.
    
    Args:
        movie_title: The cleaned/normalized movie title (e.g., "bounty")
        torrent_title: The cleaned/normalized torrent title (e.g., "perriers.bounty" or "bounty.2009")
    
    Returns:
        True if movie title appears as a complete word/phrase, False otherwise
    """
    # Convert to lowercase for comparison
    movie_title = movie_title.lower().strip()
    torrent_title = torrent_title.lower().strip()
    
    # If titles are identical, it's a match
    if movie_title == torrent_title:
        return True
    
    # Split both titles into words (using dots, spaces, etc. as separators)
    movie_words = re.split(r'[.\s]+', movie_title)
    torrent_words = re.split(r'[.\s]+', torrent_title)
    
    # Remove empty strings
    movie_words = [w for w in movie_words if w]
    torrent_words = [w for w in torrent_words if w]
    
    # Check if all movie words appear consecutively in torrent words
    if len(movie_words) == 0:
        return False
    
    # For single-word titles, be more strict: require it to be at the start or be the primary match
    # This prevents "bounty" matching "perriers bounty"
    if len(movie_words) == 1:
        word = movie_words[0]
        torrent_phrase = ' '.join(torrent_words)
        
        # Check if the word is at the start of the torrent title (most reliable)
        if torrent_words and torrent_words[0] == word:
            return True
        
        # If not at start, check if it appears as a complete word with word boundaries
        pattern = r'\b' + re.escape(word) + r'\b'
        if re.search(pattern, torrent_phrase):
            # Additional check: use ratio to ensure the word is a significant part of the title
            # This prevents "bounty" from matching "perriers bounty" where "bounty" is just a word
            from fuzzywuzzy import fuzz
            # Use ratio (not partial_ratio) to compare full strings
            # For "bounty" vs "perriers bounty", ratio will be low (~40%)
            # For "bounty" vs "bounty 2009", ratio will be higher (~60-70%)
            # We want to allow matches where the word is a significant portion
            ratio = fuzz.ratio(word, torrent_phrase)
            # Require at least 60% ratio for single-word titles not at the start
            # This allows "bounty" to match "bounty 2009" but not "perriers bounty"
            if ratio >= 60:
                return True
        
        return False
    
    # For multi-word titles, try to find the movie title as a consecutive sequence
    for i in range(len(torrent_words) - len(movie_words) + 1):
        if torrent_words[i:i+len(movie_words)] == movie_words:
            # Prefer matches at the start, but allow matches anywhere for multi-word titles
            return True
    
    # Also check if movie title appears as a complete phrase in the torrent title
    # (handles cases where movie title might be "the bounty" and torrent has "the.bounty.2009")
    movie_phrase = ' '.join(movie_words)
    torrent_phrase = ' '.join(torrent_words)
    
    # Check if movie phrase appears as a complete phrase (word boundaries)
    pattern = r'\b' + re.escape(movie_phrase) + r'\b'
    if re.search(pattern, torrent_phrase):
        return True
    
    return False

def parse_requested_seasons(extra_data):
    """
    Parse the requested seasons from the extra data in the JSON payload.
    """
    if not extra_data:
        return []

    # Handle JSON string from database
    if isinstance(extra_data, str):
        try:
            import json
            extra_data = json.loads(extra_data)
        except (json.JSONDecodeError, TypeError):
            return []

    # Handle dictionary format (new format)
    if isinstance(extra_data, dict):
        if 'Requested Seasons' in extra_data:
            seasons_str = extra_data['Requested Seasons']
            if isinstance(seasons_str, str):
                # Handle different formats:
                # 1. "Season 1, Season 2" format
                if 'Season ' in seasons_str:
                    return seasons_str.split(', ')
                # 2. "1,2,3" or "1-5" format (from seasons_processing field)
                else:
                    seasons = []
                    # Split by comma and handle ranges
                    for part in seasons_str.split(','):
                        part = part.strip()
                        if '-' in part:
                            # Handle range like "1-5"
                            try:
                                start, end = map(int, part.split('-'))
                                for season_num in range(start, end + 1):
                                    seasons.append(f"Season {season_num}")
                            except ValueError:
                                continue
                        else:
                            # Handle single season like "19"
                            try:
                                season_num = int(part)
                                seasons.append(f"Season {season_num}")
                            except ValueError:
                                continue
                    return seasons
        return []

    # Handle list format (old format)
    if isinstance(extra_data, list):
        for item in extra_data:
            if isinstance(item, dict) and item.get('name') == 'Requested Seasons':
                return item.get('value', '').split(', ')
    
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
    
    # Check for complete series patterns first
    complete_patterns = [
        r'complete\s+series',
        r'complete\s+collection',
        r'complete\s+box\s+set',
        r'complete\s+pack',
        r'full\s+series',
        r'all\s+seasons',
        r'seasons?\s+\d+\s*[-–]\s*\d+',  # Seasons 1-10, Season 1-10
        r's\d+\s*[-–]\s*s\d+',  # S01-S10, S1-S10
        r'\d{4}[-–]\d{4}',  # Year ranges like 2001–2011
    ]
    
    # Check if any complete pattern is found
    for pattern in complete_patterns:
        if re.search(pattern, title):
            # If it's a complete series, assume it covers all seasons
            # This is more permissive and handles cases like "Complete Series" or year ranges
            logger.info(f"Found complete series pattern '{pattern}' in title: {title}")
            return True
    
    # Fallback to original logic
    for season in seasons:
        if f"complete {season.lower()}" not in title and f"complete {season.lower().replace('s', 'season ')}" not in title:
            return False
    return True

def match_single_season(title, season):
    """
    Check if the title contains the exact requested season.
    Handles formats like "Season 1", "S01", "S1", etc.
    Also handles season ranges like "S01-04" where the requested season falls within the range.
    """
    import re
    
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

    # First check for season ranges in the title (e.g., S01-04, S1-S4, Season 1-4)
    range_patterns = [
        r's(\d+)[-–](\d+)',  # S01-04, S1-4
        r's(\d+)[-–]s(\d+)',  # S01-S04, S1-S4
        r'season\s+(\d+)[-–]season\s+(\d+)',  # Season 1-Season 4
        r'season\s+(\d+)[-–](\d+)',  # Season 1-4
    ]
    
    for pattern in range_patterns:
        range_matches = re.findall(pattern, title)
        for start_str, end_str in range_matches:
            try:
                start_season = int(start_str)
                end_season = int(end_str)
                if start_season <= season_number <= end_season:
                    logger.info(f"Season {season_number} found within range S{start_season:02d}-S{end_season:02d} in title: {title}")
                    return True
            except ValueError:
                continue

    # Check if the requested season is present in the title
    # But exclude single episodes (e.g., S19E25 should not match Season 19)
    season_present = False
    
    # Check for explicit season patterns (complete seasons)
    explicit_season_patterns = [
        f"season {season_number}",
        f"s{season_number:02d}",  # S19 (zero-padded)
        f"s{season_number}",  # S19 (non-zero-padded)
        f"temporada {season_number}",  # Spanish
        f"temporada {season_number:02d}",  # Spanish with zero padding
        f"season.{season_number}",  # With dots
        f"s.{season_number:02d}",  # With dots and zero padding
        f"s.{season_number}",  # With dots
    ]
    
    for pattern in explicit_season_patterns:
        if pattern in title:
            # Additional check: make sure it's not a single episode
            # Look for episode patterns like E01, E1, Episode 1, etc.
            episode_patterns = [
                r'e\d+',  # E01, E1, E25, etc.
                r'episode\s+\d+',  # Episode 1, Episode 25, etc.
                r'ep\s+\d+',  # Ep 1, Ep 25, etc.
            ]
            
            is_single_episode = False
            for ep_pattern in episode_patterns:
                if re.search(ep_pattern, title):
                    is_single_episode = True
                    break
            
            # For individual episode processing, we want to match episodes too
            # Only skip if it's clearly a single episode that doesn't match our season
            if not is_single_episode:
                season_present = True
                logger.info(f"Found complete season {season_number} pattern '{pattern}' in title: {title}")
                break
            else:
                # Check if the episode belongs to our requested season
                episode_season_patterns = [
                    rf"s{season_number:02d}e\d+",  # S04E01, S04E02, etc.
                    rf"s{season_number}e\d+",  # S4E01, S4E02, etc.
                ]
                
                episode_matches_season = False
                for ep_season_pattern in episode_season_patterns:
                    if re.search(ep_season_pattern, title):
                        episode_matches_season = True
                        break
                
                if episode_matches_season:
                    season_present = True
                    logger.info(f"Found season {season_number} episode pattern '{pattern}' in title: {title}")
                    break
                else:
                    logger.info(f"Found season {season_number} pattern '{pattern}' but title contains single episode indicators for different season. Skipping.")
    
    if not season_present:
        return False
    
    # For single season matching, we should be more permissive
    # Only reject if the title explicitly contains multiple seasons in a way that suggests it's a complete pack
    # Check for patterns like "S01-S10", "S1-S10", "Season 1-10", etc.
    complete_pack_patterns = [
        rf"s\d+[-–]s{season_number:02d}",  # S01-S10, S1-S10
        rf"s{season_number:02d}[-–]s\d+",  # S10-S01, S10-S1
        rf"season\s+\d+[-–]season\s+{season_number}",  # Season 1-Season 10
        rf"season\s+{season_number}[-–]season\s+\d+",  # Season 10-Season 1
        rf"s\d+[-–]{season_number:02d}",  # S01-10, S1-10
        rf"{season_number:02d}[-–]s\d+",  # 10-S01, 10-S1
    ]
    
    # If it's a complete pack pattern, only allow if it's the first season or if it's a range that includes our season
    for pattern in complete_pack_patterns:
        if re.search(pattern, title):
            # Extract the range and check if our season is within it
            range_match = re.search(rf"s(\d+)[-–]s?(\d+)", title)
            if range_match:
                start_season = int(range_match.group(1))
                end_season = int(range_match.group(2))
                if start_season <= season_number <= end_season:
                    return True
            return False
    
    # If no complete pack pattern is found, allow the match
    return True

def extract_season(title):
    """
    Extract the season number from a title (e.g., 'naruto.s01.bdrip' → 1).
    """
    season_match = re.search(r"[sS](\d{1,2})", title)
    if season_match:
        return int(season_match.group(1))
    return None

def get_system_uptime() -> dict:
    """
    Get system uptime information
    
    Returns:
        dict: Uptime information
    """
    current_time = datetime.now()
    uptime_delta = current_time - START_TIME
    
    uptime_info = {
        'start_time': START_TIME.isoformat(),
        'current_time': current_time.isoformat(),
        'uptime_seconds': int(uptime_delta.total_seconds()),
        'uptime_days': uptime_delta.days,
        'uptime_hours': uptime_delta.seconds // 3600,
        'uptime_minutes': (uptime_delta.seconds % 3600) // 60,
        'uptime_seconds_remainder': uptime_delta.seconds % 60
    }
    
    log_info("System Uptime", f"System uptime: {uptime_info['uptime_days']} days, {uptime_info['uptime_hours']} hours, {uptime_info['uptime_minutes']} minutes")
    return uptime_info

def get_processing_statistics() -> dict:
    """
    Get processing statistics from the database
    
    Returns:
        dict: Processing statistics
    """
    if not USE_DATABASE:
        return {}
    
    try:
        db = get_db()
        
        # Get total log entries
        total_logs = db.query(LogEntry).count()
        
        # Get logs by level
        success_logs = db.query(LogEntry).filter(LogEntry.level == 'SUCCESS').count()
        error_logs = db.query(LogEntry).filter(LogEntry.level == 'ERROR').count()
        warning_logs = db.query(LogEntry).filter(LogEntry.level == 'WARNING').count()
        info_logs = db.query(LogEntry).filter(LogEntry.level == 'INFO').count()
        
        # Get logs by module
        module_stats = {}
        modules = db.query(LogEntry.module).distinct().all()
        for module in modules:
            if module[0]:  # Check if module is not None
                count = db.query(LogEntry).filter(LogEntry.module == module[0]).count()
                module_stats[module[0]] = count
        
        # Get recent activity (last 24 hours)
        from datetime import timedelta
        yesterday = datetime.now() - timedelta(days=1)
        recent_logs = db.query(LogEntry).filter(LogEntry.timestamp >= yesterday).count()
        
        stats = {
            'total_logs': total_logs,
            'success_logs': success_logs,
            'error_logs': error_logs,
            'warning_logs': warning_logs,
            'info_logs': info_logs,
            'module_stats': module_stats,
            'recent_logs_24h': recent_logs,
            'success_rate': (success_logs / total_logs * 100) if total_logs > 0 else 0
        }
        
        log_info("Processing Statistics", f"Retrieved processing statistics: {stats}")
        return stats
        
    except Exception as e:
        log_error("Database Error", f"Failed to get processing statistics: {e}")
        return {}
    finally:
        if 'db' in locals():
            db.close()

def cleanup_old_logs(days_to_keep: int = 30) -> bool:
    """
    Clean up old log entries from the database
    
    Args:
        days_to_keep (int): Number of days to keep logs
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not USE_DATABASE:
        return False
    
    try:
        db = get_db()
        
        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        # Count logs to be deleted
        logs_to_delete = db.query(LogEntry).filter(LogEntry.timestamp < cutoff_date).count()
        
        if logs_to_delete > 0:
            # Delete old logs
            db.query(LogEntry).filter(LogEntry.timestamp < cutoff_date).delete()
            db.commit()
            
            log_success("Log Cleanup", f"Deleted {logs_to_delete} old log entries (older than {days_to_keep} days)")
            return True
        else:
            log_info("Log Cleanup", f"No old log entries found to delete (older than {days_to_keep} days)")
            return True
            
    except Exception as e:
        log_error("Database Error", f"Failed to cleanup old logs: {e}")
        if 'db' in locals():
            db.rollback()
        return False
    finally:
        if 'db' in locals():
            db.close()

def get_database_health() -> dict:
    """
    Get database health information
    
    Returns:
        dict: Database health information
    """
    if not USE_DATABASE:
        return {'status': 'disabled', 'message': 'Database is disabled'}
    
    try:
        db = get_db()
        
        # Test database connection
        db.execute("SELECT 1")
        
        # Get table counts
        table_counts = {}
        tables = ['log_entries', 'notification_history', 'media_requests', 'unified_media', 
                 'library_stats', 'queue_status', 'system_config', 'token_status']
        
        for table in tables:
            try:
                result = db.execute(f"SELECT COUNT(*) FROM {table}")
                count = result.scalar()
                table_counts[table] = count
            except Exception as e:
                table_counts[table] = f"Error: {str(e)}"
        
        health_info = {
            'status': 'healthy',
            'connection': 'active',
            'table_counts': table_counts,
            'last_check': datetime.now().isoformat()
        }
        
        log_success("Database Health", f"Database health check passed: {health_info}")
        return health_info
        
    except Exception as e:
        health_info = {
            'status': 'unhealthy',
            'connection': 'failed',
            'error': str(e),
            'last_check': datetime.now().isoformat()
        }
        
        log_error("Database Health", f"Database health check failed: {health_info}")
        return health_info
    finally:
        if 'db' in locals():
            db.close()

def export_logs_to_file(filename: str = None, days: int = 7) -> str:
    """
    Export logs from database to a file
    
    Args:
        filename (str): Output filename (optional)
        days (int): Number of days to export
        
    Returns:
        str: Path to exported file
    """
    if not USE_DATABASE:
        return None
    
    try:
        db = get_db()
        
        # Calculate date range
        start_date = datetime.now() - timedelta(days=days)
        
        # Get logs from database
        logs = db.query(LogEntry).filter(
            LogEntry.timestamp >= start_date
        ).order_by(LogEntry.timestamp.desc()).all()
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"seerrbridge_logs_export_{timestamp}.json"
        
        # Export to JSON file
        import json
        export_data = []
        for log in logs:
            export_data.append({
                'timestamp': log.timestamp.isoformat(),
                'level': log.level,
                'module': log.module,
                'function': log.function,
                'line_number': log.line_number,
                'message': log.message,
                'extra_data': log.extra_data
            })
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        log_success("Log Export", f"Exported {len(export_data)} log entries to {filename}")
        return filename
        
    except Exception as e:
        log_error("Database Error", f"Failed to export logs: {e}")
        return None
    finally:
        if 'db' in locals():
            db.close() 