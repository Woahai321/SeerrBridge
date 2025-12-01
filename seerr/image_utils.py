"""
Image utilities for fetching, compressing, and storing TV show images
"""
import requests
import io
from PIL import Image
from typing import Optional, Tuple, Dict, Any
from loguru import logger
import base64

def fetch_trakt_show_images(trakt_show_id: str) -> Optional[Dict[str, str]]:
    """
    Fetch show images from Trakt API using the correct endpoint format
    
    Args:
        trakt_show_id: Trakt show ID
        
    Returns:
        Dictionary with image URLs or None if failed
    """
    try:
        from seerr.config import TRAKT_API_KEY
        import time
        
        # Simple rate limiting - wait a bit to avoid hitting rate limits
        time.sleep(0.1)  # 100ms delay between requests
        
        headers = {
            'Content-Type': 'application/json',
            'trakt-api-version': '2',
            'trakt-api-key': TRAKT_API_KEY,
            'User-Agent': 'SeerrBridge/1.0.0'
        }
        
        # Use the correct endpoint format with extended=images parameter
        url = f"https://api.trakt.tv/shows/{trakt_show_id}?extended=images"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract image URLs from the response
            images = {}
            
            # Handle the response format from the extended=images endpoint
            if 'images' in data:
                image_data = data['images']
                
                # Process all available image types
                image_types = ['poster', 'thumb', 'fanart', 'banner', 'logo', 'clearart']
                
                for image_type in image_types:
                    if image_type in image_data and image_data[image_type]:
                        image_urls = image_data[image_type]
                        if isinstance(image_urls, list) and len(image_urls) > 0:
                            # Get the first URL and prepend https:// as required by Trakt
                            raw_url = image_urls[0]
                            if raw_url and not raw_url.startswith('http'):
                                # Prepend https:// prefix as required by Trakt API
                                full_url = f"https://{raw_url}"
                            else:
                                full_url = raw_url
                            images[image_type] = full_url
                            # Found image URL
                        elif isinstance(image_urls, dict):
                            # Fallback for old format (though not expected with new API)
                            full_url = image_urls.get('full', image_urls.get('medium', image_urls.get('thumb')))
                            if full_url and not full_url.startswith('http'):
                                full_url = f"https://{full_url}"
                            images[image_type] = full_url
            
            # Fallback to old format if images not found in new format
            elif 'poster' in data:
                poster_data = data['poster']
                if poster_data:
                    images['poster'] = poster_data.get('full', poster_data.get('medium', poster_data.get('thumb')))
            
            if images:
                logger.info(f"Successfully fetched images for show {trakt_show_id}: {list(images.keys())}")
                return images
            else:
                logger.warning(f"No images found for show {trakt_show_id}")
                return None
        else:
            logger.warning(f"Failed to fetch images for show {trakt_show_id}: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error fetching images for show {trakt_show_id}: {e}")
        return None

def fetch_trakt_movie_images(trakt_movie_id: str) -> Optional[Dict[str, str]]:
    """
    Fetch movie images from Trakt API using the correct endpoint format
    
    Args:
        trakt_movie_id: Trakt movie ID
        
    Returns:
        Dictionary with image URLs or None if failed
    """
    try:
        from seerr.config import TRAKT_API_KEY
        import time
        
        # Simple rate limiting - wait a bit to avoid hitting rate limits
        time.sleep(0.1)  # 100ms delay between requests
        
        headers = {
            'Content-Type': 'application/json',
            'trakt-api-version': '2',
            'trakt-api-key': TRAKT_API_KEY,
            'User-Agent': 'SeerrBridge/1.0.0'
        }
        
        # Use the correct endpoint format with extended=images parameter
        url = f"https://api.trakt.tv/movies/{trakt_movie_id}?extended=images"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract image URLs from the response
            images = {}
            
            # Handle the response format from the extended=images endpoint
            if 'images' in data:
                image_data = data['images']
                
                # Process all available image types
                image_types = ['poster', 'thumb', 'fanart', 'banner', 'logo', 'clearart']
                
                for image_type in image_types:
                    if image_type in image_data and image_data[image_type]:
                        image_urls = image_data[image_type]
                        if isinstance(image_urls, list) and len(image_urls) > 0:
                            # Get the first URL and prepend https:// as required by Trakt
                            raw_url = image_urls[0]
                            if raw_url and not raw_url.startswith('http'):
                                # Prepend https:// prefix as required by Trakt API
                                full_url = f"https://{raw_url}"
                            else:
                                full_url = raw_url
                            
                            if full_url:
                                images[image_type] = full_url
                                # Found image URL
            
            if images:
                # Successfully fetched images
                return images
            else:
                logger.warning(f"No images found for movie {trakt_movie_id}")
                return None
        else:
            logger.warning(f"Failed to fetch images for movie {trakt_movie_id}: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error fetching images for movie {trakt_movie_id}: {e}")
        return None

def download_and_compress_image(image_url: str, max_width: int = 300, max_height: int = 450, quality: int = 85) -> Optional[Tuple[bytes, str, int]]:
    """
    Download and compress an image from URL
    Handles WebP format from Trakt API and converts to JPEG for storage
    
    Args:
        image_url: URL of the image to download
        max_width: Maximum width for the compressed image
        max_height: Maximum height for the compressed image
        quality: JPEG quality (1-100)
        
    Returns:
        Tuple of (compressed_image_data, format, size_in_bytes) or None if failed
    """
    try:
        # Download image
        response = requests.get(image_url, timeout=15)
        response.raise_for_status()
        
        # Open image with PIL (supports WebP format)
        image = Image.open(io.BytesIO(response.content))
        
        # Log original format for debugging
        original_format = image.format.lower() if image.format else 'unknown'
        # Downloaded image
        
        # Convert to RGB if necessary (for JPEG compatibility)
        if image.mode in ('RGBA', 'LA', 'P'):
            # Create a white background
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Calculate new dimensions maintaining aspect ratio
        original_width, original_height = image.size
        ratio = min(max_width / original_width, max_height / original_height)
        
        if ratio < 1:  # Only resize if image is larger than max dimensions
            new_width = int(original_width * ratio)
            new_height = int(original_height * ratio)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Compress image to JPEG for consistent storage
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=quality, optimize=True)
        compressed_data = output.getvalue()
        
        # Get final size
        size_bytes = len(compressed_data)
        
        logger.info(f"Compressed {original_format} image from {len(response.content)} to {size_bytes} bytes ({size_bytes/1024:.1f}KB)")
        
        return compressed_data, 'jpeg', size_bytes
        
    except Exception as e:
        logger.error(f"Error downloading/compressing image from {image_url}: {e}")
        return None

def store_show_image(show_title: str, trakt_show_id: str, images_dict: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """
    Download, compress, and store show images from Trakt API
    Ensures all images are cached locally and not hotlinked from Trakt CDN
    
    Args:
        show_title: Title of the show
        trakt_show_id: Trakt show ID
        images_dict: Dictionary of image type -> URL mappings from Trakt API
        
    Returns:
        Dictionary with processed image data or None if failed
    """
    try:
        result = {}
        
        # Process poster image (primary image for display)
        if 'poster' in images_dict and images_dict['poster']:
            poster_url = images_dict['poster']
            result['poster_url'] = poster_url
            
            poster_result = download_and_compress_image(poster_url, max_width=300, max_height=450)
            if poster_result:
                compressed_data, format_type, size_bytes = poster_result
                result.update({
                    'poster_image': compressed_data,
                    'poster_image_format': format_type,
                    'poster_image_size': size_bytes
                })
                logger.info(f"Successfully processed poster image for {show_title}")
            else:
                logger.warning(f"Failed to process poster image for {show_title}")
        
        # Process thumbnail image (smaller version for lists)
        if 'thumb' in images_dict and images_dict['thumb']:
            thumb_url = images_dict['thumb']
            result['thumb_url'] = thumb_url
            
            thumb_result = download_and_compress_image(thumb_url, max_width=150, max_height=225, quality=80)
            if thumb_result:
                compressed_data, format_type, size_bytes = thumb_result
                result.update({
                    'thumb_image': compressed_data,
                    'thumb_image_format': format_type,
                    'thumb_image_size': size_bytes
                })
                logger.info(f"Successfully processed thumbnail image for {show_title}")
            else:
                logger.warning(f"Failed to process thumbnail image for {show_title}")
        
        # Process fanart image (background image)
        if 'fanart' in images_dict and images_dict['fanart']:
            fanart_url = images_dict['fanart']
            result['fanart_url'] = fanart_url
            
            fanart_result = download_and_compress_image(fanart_url, max_width=800, max_height=450, quality=85)
            if fanart_result:
                compressed_data, format_type, size_bytes = fanart_result
                result.update({
                    'fanart_image': compressed_data,
                    'fanart_image_format': format_type,
                    'fanart_image_size': size_bytes
                })
                logger.info(f"Successfully processed fanart image for {show_title}")
            else:
                logger.warning(f"Failed to process fanart image for {show_title}")
        
        # Process banner image (wide banner)
        if 'banner' in images_dict and images_dict['banner']:
            banner_url = images_dict['banner']
            result['banner_url'] = banner_url
            
            banner_result = download_and_compress_image(banner_url, max_width=800, max_height=200, quality=85)
            if banner_result:
                compressed_data, format_type, size_bytes = banner_result
                result.update({
                    'banner_image': compressed_data,
                    'banner_image_format': format_type,
                    'banner_image_size': size_bytes
                })
                logger.info(f"Successfully processed banner image for {show_title}")
            else:
                logger.warning(f"Failed to process banner image for {show_title}")
        
        # Log what images were successfully processed
        processed_types = [k for k in result.keys() if k.endswith('_image')]
        if processed_types:
            logger.info(f"Successfully cached {len(processed_types)} image types for {show_title}: {processed_types}")
        else:
            logger.warning(f"No images were successfully processed for {show_title}")
        
        return result if result else None
        
    except Exception as e:
        logger.error(f"Error storing images for {show_title}: {e}")
        return None

def get_image_data_url(image_data: bytes, format_type: str) -> str:
    """
    Convert binary image data to data URL for frontend display
    
    Args:
        image_data: Binary image data
        format_type: Image format (jpeg, png, etc.)
        
    Returns:
        Data URL string
    """
    try:
        base64_data = base64.b64encode(image_data).decode('utf-8')
        return f"data:image/{format_type};base64,{base64_data}"
    except Exception as e:
        logger.error(f"Error creating data URL: {e}")
        return ""

# TMDB functionality removed - using only Trakt API

# TMDB functionality removed - using only Trakt API

def store_media_images(media_title: str, tmdb_id: int, media_type: str, trakt_id: str = None) -> Optional[Dict[str, Any]]:
    """
    Download, compress, and store media images from Trakt API only
    Handles both movies and TV shows
    
    Args:
        media_title: Title of the media
        tmdb_id: TMDB ID (not used, kept for compatibility)
        media_type: 'movie' or 'tv'
        trakt_id: Trakt ID for the media
        
    Returns:
        Dictionary with processed image data or None if failed
    """
    try:
        result = {}
        
        # Only use Trakt API - no TMDB
        if not trakt_id:
            logger.warning(f"Trakt ID not available for {media_title} ({media_type})")
            return None
            
        if media_type == 'tv':
            logger.info(f"Fetching TV show images for {media_title} from Trakt...")
            images_dict = fetch_trakt_show_images(trakt_id)
        elif media_type == 'movie':
            logger.info(f"Fetching movie images for {media_title} from Trakt...")
            images_dict = fetch_trakt_movie_images(trakt_id)
        else:
            logger.warning(f"Unsupported media type: {media_type} for {media_title}")
            return None
        
        if not images_dict:
            logger.warning(f"No images found for {media_title} ({media_type})")
            return None
        
        # Process poster image (primary image for display)
        poster_key = 'poster' if 'poster' in images_dict else 'poster_thumb'
        if poster_key in images_dict and images_dict[poster_key]:
            poster_url = images_dict[poster_key]
            result['poster_url'] = poster_url
            
            poster_result = download_and_compress_image(poster_url, max_width=300, max_height=450)
            if poster_result:
                compressed_data, format_type, size_bytes = poster_result
                result.update({
                    'poster_image': compressed_data,
                    'poster_image_format': format_type,
                    'poster_image_size': size_bytes
                })
                logger.info(f"Successfully processed poster image for {media_title}")
            else:
                logger.warning(f"Failed to process poster image for {media_title}")
        
        # Process thumbnail image (smaller version for lists)
        thumb_key = 'thumb' if 'thumb' in images_dict else 'poster_thumb'
        if thumb_key in images_dict and images_dict[thumb_key]:
            thumb_url = images_dict[thumb_key]
            result['thumb_url'] = thumb_url
            
            thumb_result = download_and_compress_image(thumb_url, max_width=150, max_height=225, quality=80)
            if thumb_result:
                compressed_data, format_type, size_bytes = thumb_result
                result.update({
                    'thumb_image': compressed_data,
                    'thumb_image_format': format_type,
                    'thumb_image_size': size_bytes
                })
                logger.info(f"Successfully processed thumbnail image for {media_title}")
            else:
                logger.warning(f"Failed to process thumbnail image for {media_title}")
        
        # Process fanart image (background image)
        if 'fanart' in images_dict and images_dict['fanart']:
            fanart_url = images_dict['fanart']
            result['fanart_url'] = fanart_url
            
            fanart_result = download_and_compress_image(fanart_url, max_width=800, max_height=450, quality=85)
            if fanart_result:
                compressed_data, format_type, size_bytes = fanart_result
                result.update({
                    'fanart_image': compressed_data,
                    'fanart_image_format': format_type,
                    'fanart_image_size': size_bytes
                })
                logger.info(f"Successfully processed fanart image for {media_title}")
            else:
                logger.warning(f"Failed to process fanart image for {media_title}")
        
        # Log what images were successfully processed
        processed_types = [k for k in result.keys() if k.endswith('_image')]
        if processed_types:
            logger.info(f"Successfully cached {len(processed_types)} image types for {media_title}: {processed_types}")
        else:
            logger.warning(f"No images were successfully processed for {media_title}")
        
        return result if result else None
        
    except Exception as e:
        logger.error(f"Error storing images for {media_title}: {e}")
        return None

def should_update_image(existing_image_size: int, existing_updated_at: str, force_update: bool = False) -> bool:
    """
    Determine if an image should be updated based on age and size
    
    Args:
        existing_image_size: Current image size in bytes
        existing_updated_at: Last update timestamp
        force_update: Force update regardless of age
        
    Returns:
        True if image should be updated
    """
    if force_update:
        return True
    
    # If no existing image, always update
    if not existing_image_size or existing_image_size == 0:
        return True
    
    # Update if image is older than 30 days (basic check)
    from datetime import datetime, timedelta
    try:
        last_updated = datetime.fromisoformat(existing_updated_at.replace('Z', '+00:00'))
        if datetime.now() - last_updated > timedelta(days=30):
            return True
    except:
        # If we can't parse the date, update anyway
        return True
    
    return False
