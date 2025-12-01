"""
Real-Debrid integration module
Handles token refresh and authentication with Real-Debrid
"""
import json
import time
import requests
from datetime import datetime, timedelta
from loguru import logger

from seerr.config import RD_CLIENT_ID, RD_CLIENT_SECRET, RD_REFRESH_TOKEN, RD_ACCESS_TOKEN, USE_DATABASE
from seerr.db_logger import log_info, log_success, log_error
from seerr.secure_config_manager import secure_config

def refresh_access_token():
    """
    Refresh the Real-Debrid access token using the refresh token
    Updates the global variables and environment file
    """
    global RD_REFRESH_TOKEN, RD_ACCESS_TOKEN
    from seerr.config import RD_ACCESS_TOKEN, RD_REFRESH_TOKEN
    from seerr.browser import driver

    # Strip quotes from tokens (they are stored with quotes in the database)
    def strip_quotes(token):
        if token and isinstance(token, str):
            return token.strip('"\'')
        return token

    actual_client_id = strip_quotes(RD_CLIENT_ID)
    actual_client_secret = strip_quotes(RD_CLIENT_SECRET)
    actual_refresh_token = strip_quotes(RD_REFRESH_TOKEN)

    # Validate tokens
    if not actual_client_id:
        logger.error("Client ID is empty after cleaning")
        return False
    if not actual_client_secret:
        logger.error("Client Secret is empty after cleaning")
        return False
    if not actual_refresh_token:
        logger.error("Refresh Token is empty after cleaning")
        return False

    logger.info(f"Token validation passed. Refresh token length: {len(actual_refresh_token)}")

    TOKEN_URL = "https://api.real-debrid.com/oauth/v2/token"
    data = {
        'client_id': actual_client_id,
        'client_secret': actual_client_secret,
        'code': actual_refresh_token,
        'grant_type': 'http://oauth.net/grant_type/device/1.0'
    }

    try:
        logger.info("Requesting a new access token with the refresh token.")
        # DO NOT log actual credential values for security
        logger.debug("Client ID and refresh token are present and validated")
        response = requests.post(TOKEN_URL, data=data)
        response.encoding = 'utf-8'  # Explicitly set UTF-8 encoding for the response
        response_data = response.json()

        if response.status_code == 200:
            expiry_time = int((datetime.now() + timedelta(hours=24)).timestamp() * 1000)
            # Update the module-level variable
            RD_ACCESS_TOKEN = json.dumps({
                "value": response_data['access_token'],
                "expiry": expiry_time
            }, ensure_ascii=False)  # Ensure non-ASCII characters are preserved
            
            # Update the config module's variable
            import seerr.config
            seerr.config.RD_ACCESS_TOKEN = RD_ACCESS_TOKEN
            
            # Save access token to secure config manager (encrypted)
            if USE_DATABASE:
                secure_config.set_config(
                    'rd_access_token',
                    RD_ACCESS_TOKEN,
                    'string',
                    'Real-Debrid Access Token (encrypted)',
                    is_sensitive=True
                )
            
            # Check if the API returned a new refresh token and save it if present
            if 'refresh_token' in response_data and response_data['refresh_token']:
                new_refresh_token = response_data['refresh_token']
                RD_REFRESH_TOKEN = new_refresh_token
                seerr.config.RD_REFRESH_TOKEN = new_refresh_token
                
                # Save refresh token to secure config manager (encrypted)
                if USE_DATABASE:
                    secure_config.set_config(
                        'rd_refresh_token',
                        new_refresh_token,
                        'string',
                        'Real-Debrid Refresh Token (encrypted)',
                        is_sensitive=True
                    )
                    logger.info("Successfully updated refresh token in database.")
            
            logger.info("Successfully refreshed access token.")

            if driver:
                driver.execute_script(f"""
                    localStorage.setItem('rd:accessToken', '{RD_ACCESS_TOKEN}');
                """)
                logger.info("Updated Real-Debrid credentials in local storage after token refresh.")
                driver.refresh()
                logger.info("Refreshed the page after updating local storage with the new token.")
            return True
        else:
            logger.error(f"Failed to refresh access token. Status: {response.status_code}")
            # Log only error codes and messages, not full response (may contain sensitive data)
            error_info = {
                'error': response_data.get('error', 'Unknown error'),
                'error_code': response_data.get('error_code', 'Unknown'),
                'error_description': response_data.get('error_description', 'No description')
            }
            logger.error(f"Error response: {error_info}")
            
            # Try with refresh_token parameter instead of code
            if response_data.get('error_code') == 2:
                logger.info("Trying with refresh_token parameter instead of code...")
                data_refresh = {
                    'client_id': actual_client_id,
                    'client_secret': actual_client_secret,
                    'refresh_token': actual_refresh_token,
                    'grant_type': 'refresh_token'
                }
                # DO NOT log request data containing credentials
                logger.debug("Using fallback refresh_token parameter method")
                response = requests.post(TOKEN_URL, data=data_refresh)
                response.encoding = 'utf-8'
                response_data = response.json()
                
                if response.status_code == 200:
                    logger.info("Fallback refresh_token parameter worked!")
                    # Process the successful response
                    expiry_time = int((datetime.now() + timedelta(hours=24)).timestamp() * 1000)
                    RD_ACCESS_TOKEN = json.dumps({
                        "value": response_data['access_token'],
                        "expiry": expiry_time
                    }, ensure_ascii=False)
                    
                    import seerr.config
                    seerr.config.RD_ACCESS_TOKEN = RD_ACCESS_TOKEN
                    
                    # Save access token to secure config manager (encrypted)
                    if USE_DATABASE:
                        secure_config.set_config(
                            'rd_access_token',
                            RD_ACCESS_TOKEN,
                            'string',
                            'Real-Debrid Access Token (encrypted)',
                            is_sensitive=True
                        )
                    
                    # Check if the API returned a new refresh token and save it if present
                    if 'refresh_token' in response_data and response_data['refresh_token']:
                        new_refresh_token = response_data['refresh_token']
                        RD_REFRESH_TOKEN = new_refresh_token
                        seerr.config.RD_REFRESH_TOKEN = new_refresh_token
                        
                        # Save refresh token to secure config manager (encrypted)
                        if USE_DATABASE:
                            secure_config.set_config(
                                'rd_refresh_token',
                                new_refresh_token,
                                'string',
                                'Real-Debrid Refresh Token (encrypted)',
                                is_sensitive=True
                            )
                            logger.info("Successfully updated refresh token in database (fallback method).")
                    
                    logger.info("Successfully refreshed access token using fallback method.")
                    return True
                else:
                    logger.error(f"Fallback also failed. Status: {response.status_code}")
                    # Log only error codes and messages, not full response (may contain sensitive data)
                    error_info = {
                        'error': response_data.get('error', 'Unknown error'),
                        'error_code': response_data.get('error_code', 'Unknown'),
                        'error_description': response_data.get('error_description', 'No description')
                    }
                    logger.error(f"Fallback error response: {error_info}")
                    
                    error_description = response_data.get('error_description', 'Unknown error')
                    logger.error(f"Failed to refresh access token: {error_description}")
                    
                    # If refresh token is invalid or expired, force setup mode
                    if response_data.get('error_code') == 2 or 'wrong_parameter' in str(response_data.get('error', '')).lower():
                        logger.warning("Refresh token appears to be invalid or expired. Forcing setup mode...")
                        if USE_DATABASE:
                            secure_config.force_setup_mode(reason="Refresh token invalid or expired - requires re-authentication")
                    
                    return False
            
            # If error_code is not 2, we didn't try the fallback, so handle the error here
            logger.error(f"Failed to refresh access token: {response_data.get('error_description', 'Unknown error')}")
            
            # If refresh token is invalid or expired, force setup mode
            if response_data.get('error_code') == 2 or 'wrong_parameter' in str(response_data.get('error', '')).lower():
                logger.warning("Refresh token appears to be invalid or expired. Forcing setup mode...")
                if USE_DATABASE:
                    secure_config.force_setup_mode(reason="Refresh token invalid or expired - requires re-authentication")
            
            return False
    except Exception as e:
        logger.error(f"Error refreshing access token: {e}")
        return False

def check_and_refresh_access_token():
    """Check if the access token is expired or about to expire and refresh it if necessary."""
    from seerr.config import load_config
    
    # Reload from environment to get the latest
    load_config(override=True)
    
    # Get the token from the config module
    import seerr.config
    if seerr.config.RD_ACCESS_TOKEN:
        try:
            # Handle access token - it should be proper JSON like {"value":"token","expiry":timestamp}
            access_token_str = seerr.config.RD_ACCESS_TOKEN.strip()
            
            # Validate that the token string is not empty or corrupted
            if not access_token_str or len(access_token_str) < 10:
                logger.warning("Access token appears to be empty or too short. Clearing and refreshing...")
                _clear_corrupted_token()
                return refresh_access_token()
            
            # Check for obvious corruption (contains only asterisks, malformed JSON patterns)
            if access_token_str.count('*') > len(access_token_str) * 0.5:
                logger.warning("Access token appears to be corrupted (too many asterisks). Clearing and refreshing...")
                _clear_corrupted_token()
                return refresh_access_token()
            
            # Validate JSON structure before parsing
            if not access_token_str.startswith('{'):
                logger.warning("Access token does not start with '{'. Attempting to fix...")
                # Try to find the start of JSON
                json_start = access_token_str.find('{')
                if json_start >= 0:
                    access_token_str = access_token_str[json_start:]
                else:
                    # If no JSON start found, this is corrupted
                    logger.warning("No JSON structure found. Clearing corrupted token...")
                    _clear_corrupted_token()
                    return refresh_access_token()
            
            # Validate that it's valid JSON before attempting to parse
            try:
                # Try to parse to validate JSON structure
                json.loads(access_token_str)
            except json.JSONDecodeError as json_err:
                logger.warning(f"Access token is not valid JSON: {json_err}")
                # Check if it's partially corrupted - try to find valid JSON within
                if '}' in access_token_str:
                    # Try to extract valid JSON
                    end_pos = access_token_str.rfind('}')
                    test_str = access_token_str[:end_pos + 1]
                    try:
                        json.loads(test_str)
                        access_token_str = test_str
                        logger.info("Successfully extracted valid JSON from corrupted token")
                    except json.JSONDecodeError:
                        logger.warning("Could not recover valid JSON from corrupted token. Clearing...")
                        _clear_corrupted_token()
                        return refresh_access_token()
                else:
                    logger.warning("Token JSON is incomplete (missing closing brace). Clearing...")
                    _clear_corrupted_token()
                    return refresh_access_token()
            
            # If it starts with quotes but doesn't end with quotes, it might be malformed
            if access_token_str.startswith('"') and not access_token_str.endswith('"'):
                logger.warning("Detected malformed access token JSON, attempting to fix...")
                # Try to find the end of the JSON by looking for the closing brace
                if '}' in access_token_str:
                    end_pos = access_token_str.rfind('}')
                    access_token_str = access_token_str[:end_pos + 1]
                else:
                    # If no closing brace, it's probably just a plain token with quotes
                    access_token_str = access_token_str.strip('"')
                    # Create a simple token structure
                    expiry_time = int((datetime.now() + timedelta(hours=24)).timestamp() * 1000)
                    access_token_str = json.dumps({
                        "value": access_token_str,
                        "expiry": expiry_time
                    })
                    logger.info("Created new token structure for malformed token")
            
            # Parse the validated JSON
            token_data = json.loads(access_token_str)
            
            # Validate required fields
            if 'expiry' not in token_data:
                logger.warning("Access token missing 'expiry' field. Clearing and refreshing...")
                _clear_corrupted_token()
                return refresh_access_token()
            
            if 'value' not in token_data or not token_data['value']:
                logger.warning("Access token missing or empty 'value' field. Clearing and refreshing...")
                _clear_corrupted_token()
                return refresh_access_token()
            
            expiry_time = token_data['expiry']  # This is in milliseconds
            current_time = int(time.time() * 1000)  # Convert current time to milliseconds

            # Convert expiry time to a readable date format
            expiry_date = datetime.fromtimestamp(expiry_time / 1000).strftime('%Y-%m-%d %H:%M:%S')

            # Print the expiry date
            logger.info(f"Access token will expire on: {expiry_date}")

            # Check if the token is about to expire in the next 10 minutes (600000 milliseconds)
            if current_time >= expiry_time - 600000:  # 600000 milliseconds = 10 minutes
                logger.info("Access token is about to expire. Refreshing...")
                return refresh_access_token()
            else:
                logger.info("Access token is still valid.")
                return True
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Error parsing access token: {e}")
            # DO NOT log access token content - contains sensitive data
            token_length = len(seerr.config.RD_ACCESS_TOKEN) if seerr.config.RD_ACCESS_TOKEN else 0
            logger.error(f"Access token appears to be corrupted (length: {token_length}). Clearing and attempting to refresh...")
            _clear_corrupted_token()
            return refresh_access_token()
    else:
        logger.error("Access token is not set. Requesting a new token.")
        return refresh_access_token()

def _clear_corrupted_token():
    """Clear corrupted access token from secure config and force setup mode"""
    try:
        if USE_DATABASE:
            # Clear the corrupted token
            secure_config.set_config(
                'rd_access_token',
                '',
                'string',
                'Real-Debrid Access Token (encrypted)',
                is_sensitive=True
            )
            # Also clear the module-level variable
            import seerr.config
            seerr.config.RD_ACCESS_TOKEN = None
            logger.info("Cleared corrupted access token from secure storage")
            # Force setup mode since tokens are corrupted
            secure_config.force_setup_mode(reason="Corrupted access token detected - requires re-authentication")
    except Exception as e:
        logger.error(f"Failed to clear corrupted token: {e}")

def save_token_to_secure_config(token_type: str, token_value: str, expiry_time: int = None) -> bool:
    """
    Save token information to secure config manager (encrypted)
    
    Args:
        token_type (str): Type of token (rd_access_token, rd_refresh_token, etc.)
        token_value (str): Token value to encrypt and store
        expiry_time (int): Expiry timestamp in milliseconds (optional)
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not USE_DATABASE:
        return False
    
    try:
        # Create token data structure if expiry is provided
        if expiry_time:
            token_data = {
                "value": token_value,
                "expiry": expiry_time
            }
            token_json = json.dumps(token_data, ensure_ascii=False)
        else:
            token_json = token_value
        
        # Save to secure config manager (automatically encrypted)
        success = secure_config.set_config(
            token_type,
            token_json,
            'string',
            f'Real-Debrid {token_type.replace("rd_", "").replace("_", " ").title()} (encrypted)',
            is_sensitive=True
        )
        
        if success:
            log_success("Token Management", f"Saved {token_type} token to secure config")
        else:
            log_error("Token Management", f"Failed to save {token_type} token to secure config")
        
        return success
        
    except Exception as e:
        log_error("Token Management", f"Failed to save {token_type} token: {e}")
        return False 