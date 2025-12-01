"""
Letterboxd list provider for SeerrBridge.
Fetches movies from Letterboxd lists using HTTP requests and BeautifulSoup.
Then searches Trakt API to get TMDB IDs and other metadata.
"""
import logging
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin

try:
    import requests
    from bs4 import BeautifulSoup
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logging.warning("requests or beautifulsoup4 not available. Letterboxd lists will not work.")

# Try to import Selenium for JavaScript-rendered pages
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logging.debug("Selenium not available. Will only use HTTP requests for Letterboxd.")

logger = logging.getLogger(__name__)


def fetch_letterboxd_list(list_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Fetch Letterboxd list using HTTP requests and BeautifulSoup with pagination.
    Then searches Trakt API for each item to get TMDB IDs and other metadata.
    
    Args:
        list_id (str): Letterboxd list ID (username/list-slug) or full URL
        limit (Optional[int]): Maximum number of items to fetch
        
    Returns:
        List[Dict[str, Any]]: List of media items with:
            - title: Movie title
            - year: Release year
            - media_type: "movie"
            - film_id: Letterboxd film ID
            - slug: Letterboxd slug
            - tmdb_id: TMDB ID (from Trakt search, if found)
            - imdb_id: IMDB ID (from Trakt search, if found)
            - trakt_id: Trakt ID (from Trakt search, if found)
        
    Raises:
        ValueError: If requests/BeautifulSoup is not available or list ID format is invalid
        Exception: If scraping fails
    """
    logger.info("=" * 60)
    logger.info("LETTERBOXD LIST FETCH - START")
    logger.info(f"List ID: {list_id}")
    logger.info(f"Limit: {limit}")
    
    if not REQUESTS_AVAILABLE:
        logger.error("requests or beautifulsoup4 not available!")
        raise ValueError("requests and beautifulsoup4 are required for Letterboxd lists. Please install them: pip install requests beautifulsoup4")
    
    logger.info("REQUESTS_AVAILABLE: True")
    
    media_items = []
    
    try:
        # Set up session with headers to mimic a browser
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })
        # Handle full URLs vs list IDs
        if list_id.startswith(('http://', 'https://')):
            base_url = list_id.rstrip('/')
        else:
            base_url = f"https://letterboxd.com/{list_id}"
        
        # Determine if this is a watchlist or regular list
        is_watchlist = '/watchlist' in base_url or list_id.endswith('/watchlist')
        
        # For custom lists, DON'T use /detail/ view - it might be JavaScript-only
        # The regular list view should have the items in the HTML
        # Remove /detail/ if it's in the URL
        if not is_watchlist:
            base_url = base_url.rstrip('/')
            if base_url.endswith('/detail'):
                base_url = base_url[:-7]  # Remove '/detail'
            base_url = base_url.rstrip('/')
        
        logger.info(f"Processing Letterboxd {'watchlist' if is_watchlist else 'list'}: {base_url}")
        
        # Try to fetch JSON data first (many sites expose JSON endpoints)
        # Letterboxd might have a JSON endpoint like /list/.../json/ or similar
        json_url = None
        if not is_watchlist:
            # Try common JSON endpoint patterns
            json_patterns = [
                f"{base_url}/json/",
                f"{base_url}/data.json",
                f"{base_url}.json",
            ]
            for pattern in json_patterns:
                try:
                    test_response = session.get(pattern, timeout=10)
                    if test_response.status_code == 200:
                        try:
                            json_data = test_response.json()
                            if isinstance(json_data, (dict, list)) and len(json_data) > 0:
                                json_url = pattern
                                logger.info(f"Found JSON endpoint: {json_url}")
                                break
                        except:
                            pass
                except:
                    pass
        
        logger.info(f"Starting to fetch items from Letterboxd list...")
        
        page = 1
        next_page_url = None  # Track the next page URL
        items_fetched = 0
        
        while True:
            # Apply limit if specified
            if limit and items_fetched >= limit:
                logger.info(f"Reached limit of {limit} items")
                break
            
            # Construct page URL - handle both first page and subsequent pages
            if page == 1:
                current_url = base_url
            elif next_page_url:
                # Use the specific next page URL we found
                current_url = next_page_url
            else:
                # Fallback: construct URL manually
                if is_watchlist:
                    current_url = f"{base_url}/page/{page}/"
                else:
                    current_url = f"{base_url}page/{page}/"
            
            logger.info(f"Fetching URL: {current_url}")
            
            try:
                response = session.get(current_url, timeout=30)
                response.raise_for_status()
                logger.info(f"HTTP {response.status_code} - Response size: {len(response.text)} bytes")
                logger.debug(f"Response headers: {dict(response.headers)}")
            except requests.RequestException as e:
                logger.error(f"Failed to fetch page {page}: {str(e)}")
                logger.error(f"URL was: {current_url}")
                break
            
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            response_size = len(response.text)
            logger.info(f"Processing page {page} - Response size: {response_size} bytes")
            
            # Check if this looks like a JavaScript-rendered page (common patterns)
            page_text = soup.get_text().lower() if soup else ""
            if 'loading' in page_text[:200] or response_size < 5000:
                logger.warning(f"Page might be JavaScript-rendered or very small. Response size: {response_size} bytes")
            
            # Check for React/JavaScript indicators
            has_react_root = soup.find('div', id='react-root') is not None
            has_react_in_text = 'react' in response.text.lower()[:1000]
            if has_react_root or has_react_in_text:
                logger.warning("Page appears to be React/JavaScript-rendered. List items may not be in initial HTML.")
            
            # Log HTML structure for debugging
            body = soup.find('body')
            if body:
                body_text_sample = str(body)[:2000] if body else ""
                logger.info(f"Body HTML sample (first 2000 chars): {body_text_sample}")
            else:
                logger.warning("No <body> tag found in HTML!")
            
            # Check for script tags that might load content or contain JSON data
            script_tags = soup.find_all('script')
            logger.info(f"Found {len(script_tags)} <script> tags in HTML")
            
            # Look for JSON data embedded in script tags (common in React apps)
            for i, script in enumerate(script_tags):
                script_content = script.string if script.string else ""
                # Look for common patterns like window.__INITIAL_STATE__ or similar
                if 'film' in script_content.lower() and ('list' in script_content.lower() or 'item' in script_content.lower()):
                    logger.info(f"Script tag {i} might contain list data (length: {len(script_content)} chars)")
                    # Try to extract JSON if present
                    import json
                    try:
                        # Look for JSON objects in the script
                        # This is a simple heuristic - might need refinement
                        if '{' in script_content and '}' in script_content:
                            # Try to find JSON-like structures
                            logger.debug(f"Script {i} contains JSON-like data")
                    except:
                        pass
            
            # Check if there's a noscript tag (often indicates JS-rendered content)
            noscript = soup.find('noscript')
            if noscript:
                logger.warning("Found <noscript> tag - page likely requires JavaScript")
            
            # Since we're getting 0 <ul> elements, the page is likely JavaScript-rendered
            # We need to use a headless browser or find an API endpoint
            if response_size > 10000:  # If we got a substantial response but no <ul> elements
                logger.error("Received substantial HTML response but no list elements found. Page is likely JavaScript-rendered.")
                logger.error("Consider using Selenium/Playwright or finding Letterboxd's API endpoint.")
            
            # Check for common Letterboxd page elements
            has_title = soup.find('title')
            if has_title:
                logger.debug(f"Page title: {has_title.get_text()}")
            
            # Check if we got redirected or got an error page
            if 'sign in' in page_text[:500] or 'login' in page_text[:500]:
                logger.warning("Page might require authentication (sign in/login detected)")
            if 'error' in page_text[:500] or 'not found' in page_text[:500]:
                logger.warning("Page might be an error page")
            
            # Extract data - look for list items
            # Based on the HTML structure: <ul class="js-list-entries poster-list -p125 -grid">
            # with <li class="posteritem numbered-list-item"> inside
            
            # First, try to find the ul container with poster-list class
            # The ul might have multiple classes like "js-list-entries poster-list -p125 -grid"
            poster_list = None
            # Try finding ul with class containing 'poster-list' (most flexible)
            poster_list = soup.find('ul', class_=lambda x: x and isinstance(x, list) and any('poster-list' in str(c) for c in x))
            if not poster_list:
                # Try as string if class is stored as string
                poster_list = soup.find('ul', class_=lambda x: x and 'poster-list' in str(x))
            if not poster_list:
                # Try exact match
                poster_list = soup.find('ul', class_='poster-list')
            
            if poster_list:
                logger.info(f"Found ul.poster-list container with classes: {poster_list.get('class', [])}")
                # Get all li children
                list_items = poster_list.find_all('li', recursive=False)
                if not list_items:
                    # Try recursive search
                    list_items = poster_list.find_all('li')
                logger.info(f"Found {len(list_items)} <li> elements in ul.poster-list")
            else:
                logger.warning("Could not find ul.poster-list container, trying alternative methods...")
                # Fallback: look for li elements directly
                list_items = soup.find_all('li', class_=lambda x: x and isinstance(x, list) and any('posteritem' in str(c) or 'numbered-list-item' in str(c) for c in x))
                if not list_items:
                    # Try as string
                    list_items = soup.find_all('li', class_=lambda x: x and ('posteritem' in str(x) or 'numbered-list-item' in str(x)))
                logger.info(f"Found {len(list_items)} <li> elements via direct search")
            
            # If no items found, try alternative selector for watchlists
            if not list_items and is_watchlist:
                list_items = soup.find_all('li', class_='griditem')
            
            # Try finding any ul with li children that have react-component divs with data attributes
            if not list_items:
                all_uls = soup.find_all('ul')
                logger.info(f"Searching through {len(all_uls)} <ul> elements for items with react-component divs...")
                for ul in all_uls:
                    # Look for li elements that contain div.react-component with data-item-name
                    items_with_react = ul.find_all('li')
                    for li in items_with_react:
                        react_div = li.find('div', class_=lambda x: x and 'react-component' in str(x))
                        if react_div and react_div.get('data-item-name'):
                            if not list_items:
                                list_items = []
                            list_items.append(li)
                    if list_items:
                        logger.info(f"Found {len(list_items)} items via react-component divs in ul")
                        break
            
            # Debug: log the HTML structure if no items found
            if not list_items:
                logger.warning(f"No list items found on page {page}. Debugging HTML structure...")
                # Try to find the list container to see what's there
                poster_list = soup.find('ul', class_='poster-list')
                if not poster_list:
                    poster_list = soup.find('ul', class_=lambda x: x and 'poster-list' in x)
                if poster_list:
                    logger.warning(f"Found ul.poster-list but no <li> items inside. Container HTML length: {len(str(poster_list))}")
                    # Check what children it has
                    children = list(poster_list.children)
                    logger.warning(f"ul.poster-list has {len(children)} direct children")
                    # Log first 500 chars of the container HTML
                    logger.debug(f"Container HTML sample: {str(poster_list)[:500]}")
                else:
                    logger.warning(f"No ul.poster-list found on page {page}. Checking for alternative structures...")
                    # Check for list-detailed-entries-list
                    detailed_list = soup.find('div', class_='list-detailed-entries-list')
                    if detailed_list:
                        logger.warning(f"Found div.list-detailed-entries-list")
                        # Try to find items in this container
                        items_in_div = detailed_list.find_all('li')
                        logger.warning(f"div.list-detailed-entries-list has {len(items_in_div)} <li> elements")
                    # Check for any ul elements
                    all_uls = soup.find_all('ul')
                    logger.warning(f"Found {len(all_uls)} <ul> elements total on the page")
                    for i, ul in enumerate(all_uls[:5]):  # Log first 5
                        ul_classes = ul.get('class', [])
                        logger.warning(f"  ul[{i}]: classes={ul_classes}, children={len(list(ul.children))}")
                # Log response status and URL for debugging
                logger.warning(f"Response status: {response.status_code}, URL: {current_url}")
                # Save a sample of the HTML for manual inspection (first 2000 chars)
                html_sample = response.text[:2000] if response.text else "No response text"
                logger.debug(f"HTML sample (first 2000 chars):\n{html_sample}")
            
            logger.info(f"Found {len(list_items)} items on page {page}")
            
            # If we find 0 items, we've gone too far - break
            if len(list_items) == 0:
                logger.info(f"No items found on page {page}, ending pagination")
                break
            
            for item in list_items:
                # Apply limit check
                if limit and items_fetched >= limit:
                    break
                
                try:
                    # Find the react-component div with data attributes
                    react_div = item.find('div', class_='react-component')
                    if not react_div:
                        # Fallback: use the item itself if no react-component found
                        react_div = item
                    
                    item_name = react_div.get('data-item-name')
                    film_id = react_div.get('data-film-id')
                    slug = react_div.get('data-item-slug')
                    
                    if not item_name:
                        continue
                    
                    # Parse title and year (format: "Title (Year)")
                    year_match = re.search(r'(.+?)\s*\((\d{4})\)', item_name)
                    if year_match:
                        title = year_match.group(1).strip()
                        year = int(year_match.group(2))
                    else:
                        title = item_name
                        year = None
                    
                    # Skip items with empty titles
                    if not title:
                        logger.warning("Skipping item with empty title")
                        continue
                    
                    # Determine media type (Letterboxd is primarily for movies)
                    media_type = "movie"
                    
                    # Search Trakt API to get TMDB ID and other metadata
                    trakt_result = None
                    try:
                        from seerr.trakt_lists import search_trakt_by_title
                        # Search with the full title first (e.g., "Harakiri (1962)")
                        trakt_result = search_trakt_by_title(item_name, year, media_type)
                        
                        # If not found with full title, try just the title without year
                        if not trakt_result and year:
                            trakt_result = search_trakt_by_title(title, year, media_type)
                        
                        # If still not found, try without year
                        if not trakt_result:
                            trakt_result = search_trakt_by_title(title, None, media_type)
                    except Exception as e:
                        logger.warning(f"Failed to search Trakt for '{title}': {str(e)}")
                    
                    # Build the media item with Trakt data if available
                    media_item = {
                        "title": title,
                        "media_type": media_type,
                        "year": year,
                        "film_id": film_id,
                        "slug": slug
                    }
                    
                    # Add Trakt metadata if found
                    if trakt_result:
                        media_item.update({
                            "tmdb_id": trakt_result.get('tmdb_id'),
                            "imdb_id": trakt_result.get('imdb_id'),
                            "trakt_id": trakt_result.get('trakt_id'),
                            # Use Trakt's title if available (might be more accurate)
                            "title": trakt_result.get('title', title),
                            "year": trakt_result.get('year', year)
                        })
                        logger.debug(f"Found Trakt match for '{title}': TMDB ID {trakt_result.get('tmdb_id')}")
                    else:
                        logger.warning(f"No Trakt match found for '{title}' ({year if year else 'no year'})")
                    
                    media_items.append(media_item)
                    items_fetched += 1
                    
                    # Log every item for the first 10, then every 10th item
                    if items_fetched <= 10 or items_fetched % 10 == 0:
                        tmdb_info = f" (TMDB: {media_item.get('tmdb_id')})" if media_item.get('tmdb_id') else " (no TMDB ID)"
                        logger.info(f"Processed item {items_fetched}: {title} ({year if year else 'year unknown'}){tmdb_info}")
                    
                except Exception as e:
                    logger.warning(f"Failed to parse item: {str(e)}")
                    continue
            
            # Check if we've reached the limit
            if limit and items_fetched >= limit:
                break
            
            # Check for next page
            try:
                has_next_page = False
                next_page_url = None
                
                # Look for pagination container
                pagination = soup.find('div', class_='pagination')
                if pagination:
                    # Look for next button
                    next_link = pagination.find('a', class_='next')
                    if next_link and next_link.get('href'):
                        next_href = next_link.get('href')
                        has_next_page = True
                        # Convert relative URL to absolute URL
                        if next_href.startswith('/'):
                            next_page_url = urljoin('https://letterboxd.com', next_href)
                        else:
                            next_page_url = next_href
                        logger.info(f"Found next page URL: {next_page_url}")
                    
                    # Fallback: check for numbered pagination
                    if not has_next_page:
                        page_links = pagination.find_all('a', class_='paginate-page')
                        for link in page_links:
                            href = link.get('href')
                            if href and f"page/{page + 1}/" in href:
                                has_next_page = True
                                next_page_url = urljoin('https://letterboxd.com', href) if not href.startswith('http') else href
                                break
                
                if has_next_page and next_page_url:
                    page += 1
                    logger.info(f"Next page available, will load page {page} from URL: {next_page_url}")
                else:
                    logger.info("No next page found, must be the last page")
                    break
            except Exception as e:
                logger.warning(f"Error checking pagination: {str(e)}")
                # If there's an error checking pagination, assume we're done
                break
        
        logger.info("=" * 60)
        logger.info(f"LETTERBOXD LIST FETCH - COMPLETE")
        logger.info(f"Total items found: {len(media_items)}")
        logger.info(f"Pages processed: {page}")
        
        if len(media_items) == 0:
            logger.warning("=" * 60)
            logger.warning("WARNING: No items were extracted from Letterboxd list!")
            logger.warning(f"List ID: {list_id}")
            logger.warning("Possible reasons:")
            logger.warning("  1. The list is empty")
            logger.warning("  2. The HTML structure has changed")
            logger.warning("  3. The list requires authentication")
            logger.warning("  4. The URL format is incorrect")
            logger.warning("  5. The page is JavaScript-rendered and requires a browser")
            logger.warning("=" * 60)
            
            # If we got a response but no items, try using Selenium as fallback
            if SELENIUM_AVAILABLE:
                logger.info("Attempting to use Selenium to fetch JavaScript-rendered content...")
                try:
                    selenium_items = _fetch_with_selenium(base_url, limit, is_watchlist)
                    if selenium_items and len(selenium_items) > 0:
                        logger.info(f"Selenium successfully extracted {len(selenium_items)} items")
                        return selenium_items
                except Exception as selenium_error:
                    logger.warning(f"Selenium fallback failed: {str(selenium_error)}")
        else:
            logger.info(f"Successfully extracted {len(media_items)} items from Letterboxd")
            # Count how many have TMDB IDs
            items_with_tmdb = sum(1 for item in media_items if item.get('tmdb_id'))
            logger.info(f"Found Trakt matches for {items_with_tmdb} out of {len(media_items)} items")
            logger.info("=" * 60)
        
        return media_items
    except Exception as e:
        error_str = str(e)
        import traceback
        logger.error("=" * 60)
        logger.error("LETTERBOXD LIST FETCH - ERROR")
        logger.error(f"Error: {error_str}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        logger.error("=" * 60)
        # If we got some items before the error, return them
        if media_items:
            logger.warning(f"Error occurred but {len(media_items)} items were already fetched. Returning partial results.")
            return media_items
        raise ValueError(f"Failed to fetch Letterboxd list: {error_str}")


def _fetch_with_selenium(list_url: str, limit: Optional[int] = None, is_watchlist: bool = False) -> List[Dict[str, Any]]:
    """
    Fallback method to fetch Letterboxd list using Selenium when HTTP requests fail.
    This is used when the page is JavaScript-rendered.
    Handles pagination automatically.
    """
    if not SELENIUM_AVAILABLE:
        raise ValueError("Selenium is not available. Cannot fetch JavaScript-rendered content.")
    
    logger.info(f"Using Selenium to fetch Letterboxd list: {list_url}")
    
    # Set up Chrome options for headless browsing
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = None
    try:
        # Try to use existing ChromeDriver or find it
        driver = webdriver.Chrome(options=chrome_options)
        
        media_items = []
        trakt_matched_count = 0
        page = 1
        base_url = list_url.rstrip('/')
        
        while True:
            # Apply limit check
            if limit and len(media_items) >= limit:
                logger.info(f"Reached limit of {limit} items")
                break
            
            # Construct page URL
            if page == 1:
                current_url = base_url
            else:
                current_url = f"{base_url}/page/{page}/"
            
            logger.info(f"Fetching page {page}: {current_url}")
            driver.get(current_url)
            
            # Wait for the list items to load
            wait = WebDriverWait(driver, 30)
            try:
                # Wait for either the poster-list ul or list items to appear
                wait.until(
                    EC.any_of(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "ul.poster-list")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "li.posteritem"))
                    )
                )
            except TimeoutException:
                logger.warning(f"Timeout waiting for list items to load on page {page}")
                # If this is page 1, return empty. Otherwise, we've reached the end.
                if page == 1:
                    return []
                break
            
            # Get the page source after JavaScript has executed
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Find the ul.poster-list container
            poster_list = soup.find('ul', class_=lambda x: x and 'poster-list' in str(x))
            if not poster_list:
                logger.warning(f"Could not find ul.poster-list on page {page}")
                # If this is page 1, return empty. Otherwise, we've reached the end.
                if page == 1:
                    return []
                break
            
            list_items = poster_list.find_all('li', class_=lambda x: x and ('posteritem' in str(x) or 'numbered-list-item' in str(x)))
            logger.info(f"Found {len(list_items)} items on page {page}")
            
            # If no items found, we've reached the end
            if len(list_items) == 0:
                logger.info(f"No items found on page {page}, reached end of list")
                break
            
            # Extract items from this page
            page_items_count = 0
            logger.info(f"Processing {len(list_items)} list items on page {page}...")
            
            for item_index, item in enumerate(list_items, 1):
                if limit and len(media_items) >= limit:
                    logger.info(f"Reached limit of {limit} items, stopping extraction")
                    break
                
                try:
                    react_div = item.find('div', class_='react-component')
                    if not react_div:
                        react_div = item
                    
                    item_name = react_div.get('data-item-name')
                    film_id = react_div.get('data-film-id')
                    slug = react_div.get('data-item-slug')
                    
                    if not item_name:
                        logger.debug(f"Item {item_index} on page {page} has no data-item-name, skipping")
                        continue
                    
                    # Parse title and year
                    year_match = re.search(r'(.+?)\s*\((\d{4})\)', item_name)
                    if year_match:
                        title = year_match.group(1).strip()
                        year = int(year_match.group(2))
                    else:
                        title = item_name
                        year = None
                    
                    if not title:
                        logger.debug(f"Item {item_index} on page {page} has empty title after parsing, skipping")
                        continue
                    
                    # Log every 10th item or first 10 items
                    if page_items_count < 10 or (page_items_count + 1) % 10 == 0:
                        logger.info(f"Page {page}, Item {item_index}/{len(list_items)}: {title} ({year if year else 'year unknown'})")
                    
                    media_type = "movie"
                    
                    # Search Trakt API
                    trakt_result = None
                    try:
                        from seerr.trakt_lists import search_trakt_by_title
                        trakt_result = search_trakt_by_title(item_name, year, media_type)
                        if not trakt_result and year:
                            trakt_result = search_trakt_by_title(title, year, media_type)
                        if not trakt_result:
                            trakt_result = search_trakt_by_title(title, None, media_type)
                        if trakt_result:
                            trakt_matched_count += 1
                            if page_items_count < 10 or (page_items_count + 1) % 10 == 0:
                                logger.info(f"  → Found Trakt match: TMDB ID {trakt_result.get('tmdb_id')}")
                    except Exception as e:
                        logger.warning(f"Failed to search Trakt for '{title}': {str(e)}")
                    
                    media_item = {
                        "title": title,
                        "media_type": media_type,
                        "year": year,
                        "film_id": film_id,
                        "slug": slug,
                        "tmdb_id": trakt_result.get('tmdb_id') if trakt_result else None,
                        "imdb_id": trakt_result.get('imdb_id') if trakt_result else None,
                        "trakt_id": trakt_result.get('trakt_id') if trakt_result else None,
                    }
                    
                    media_items.append(media_item)
                    page_items_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to parse item {item_index} on page {page}: {str(e)}")
                    continue
            
            logger.info(f"✓ Page {page} complete: Extracted {page_items_count} items (Total so far: {len(media_items)})")
            
            # Check for next page
            has_next_page = False
            next_page_number = page + 1
            
            # Look for pagination links
            try:
                next_link = driver.find_element(By.CSS_SELECTOR, "a.next")
                if next_link and next_link.is_displayed():
                    has_next_page = True
                    logger.info(f"Found 'Next' button, will continue to page {next_page_number}")
            except:
                pass
            
            # Also check for numbered pagination
            if not has_next_page:
                try:
                    pagination = driver.find_element(By.CSS_SELECTOR, "div.pagination")
                    page_links = pagination.find_elements(By.CSS_SELECTOR, "a.paginate-page")
                    for link in page_links:
                        href = link.get_attribute('href')
                        if href and f"page/{next_page_number}/" in href:
                            has_next_page = True
                            logger.info(f"Found page {next_page_number} link in pagination")
                            break
                except:
                    pass
            
            # If we got fewer items than expected (usually 100 per page), we're probably at the end
            if page_items_count < 50:  # Less than half a typical page
                logger.info(f"Only {page_items_count} items on page {page}, reached end of list")
                break
            
            # If no next page link found but we got a full page, try the next page number anyway
            # (sometimes pagination links aren't visible but the URL pattern works)
            if not has_next_page and page_items_count >= 50:
                logger.info(f"No pagination link found, but got {page_items_count} items. Trying page {next_page_number} anyway...")
                has_next_page = True
            
            if has_next_page:
                page = next_page_number
                # Small delay between pages to be respectful
                import time
                time.sleep(1)
            else:
                logger.info(f"No next page found. Finished at page {page}")
                break
        
        logger.info(f"Selenium extracted {len(media_items)} items across {page} pages, {trakt_matched_count} matched in Trakt")
        return media_items
        
    except WebDriverException as e:
        logger.error(f"Selenium WebDriver error: {str(e)}")
        raise ValueError(f"Failed to fetch with Selenium: {str(e)}")
    except Exception as e:
        logger.error(f"Selenium error: {str(e)}")
        raise ValueError(f"Failed to fetch with Selenium: {str(e)}")
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

