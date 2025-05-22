"""
Real-Debrid integration module
Handles token refresh and authentication with Real-Debrid
"""
import json
import time
import requests
from datetime import datetime, timedelta
from loguru import logger

from seerr.config import RD_CLIENT_ID, RD_CLIENT_SECRET, RD_REFRESH_TOKEN, RD_ACCESS_TOKEN, update_env_file

def refresh_access_token():
    """
    Refresh the Real-Debrid access token using the refresh token
    Updates the global variables and environment file
    """
    global RD_REFRESH_TOKEN, RD_ACCESS_TOKEN
    from seerr.config import RD_ACCESS_TOKEN, RD_REFRESH_TOKEN
    from seerr.browser import driver

    TOKEN_URL = "https://api.real-debrid.com/oauth/v2/token"
    data = {
        'client_id': RD_CLIENT_ID,
        'client_secret': RD_CLIENT_SECRET,
        'code': RD_REFRESH_TOKEN,
        'grant_type': 'http://oauth.net/grant_type/device/1.0'
    }

    try:
        logger.info("Requesting a new access token with the refresh token.")
        response = requests.post(TOKEN_URL, data=data)
        response.encoding = 'utf-8'  # Explicitly set UTF-8 encoding for the response
        response_data = response.json()

        if response.status_code == 200:
            expiry_time = int((datetime.now() + timedelta(hours=24)).timestamp() * 1000)
            # Update the module-level variable
            from seerr.config import RD_ACCESS_TOKEN as config_token
            global RD_ACCESS_TOKEN
            RD_ACCESS_TOKEN = json.dumps({
                "value": response_data['access_token'],
                "expiry": expiry_time
            }, ensure_ascii=False)  # Ensure non-ASCII characters are preserved
            
            # Update the config module's variable
            import seerr.config
            seerr.config.RD_ACCESS_TOKEN = RD_ACCESS_TOKEN
            
            logger.info("Successfully refreshed access token.")
            
            update_env_file()

            if driver:
                driver.execute_script(f"""
                    localStorage.setItem('rd:accessToken', '{RD_ACCESS_TOKEN}');
                """)
                logger.info("Updated Real-Debrid credentials in local storage after token refresh.")
                driver.refresh()
                logger.info("Refreshed the page after updating local storage with the new token.")
            return True
        else:
            logger.error(f"Failed to refresh access token: {response_data.get('error_description', 'Unknown error')}")
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
            token_data = json.loads(seerr.config.RD_ACCESS_TOKEN)
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
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error parsing access token: {e}")
            return refresh_access_token()
    else:
        logger.error("Access token is not set. Requesting a new token.")
        return refresh_access_token() 