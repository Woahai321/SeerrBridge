#!/usr/bin/env python3

"""
SeerrBridge API endpoint for testing DMM credentials during setup
This endpoint can be called from the frontend to test Real-Debrid credentials
"""

import json
import sys
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def test_dmm_credentials_api(client_id, client_secret, access_token, refresh_token, headless=True):
    """
    Test DMM credentials by spinning up a browser instance
    
    Args:
        client_id: Real-Debrid Client ID
        client_secret: Real-Debrid Client Secret
        access_token: Real-Debrid Access Token
        refresh_token: Real-Debrid Refresh Token
        headless: Run browser in headless mode
    
    Returns:
        dict: Test results with success status and library stats
    """
    driver = None
    
    try:
        # Setup Chrome options
        options = Options()
        if headless:
            options.add_argument("--headless=new")
        
        # Docker/Linux-specific configurations
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-setuid-sandbox")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1920,1080")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        # Check if running in Docker
        if os.path.exists('/.dockerenv'):
            options.binary_location = "/usr/bin/google-chrome"
            options.add_argument("--headless=new")
        
        # Initialize the driver using local chromedriver
        chromedriver_path = None
        
        # Try different possible locations for chromedriver
        # Prioritize system-installed chromedriver for Docker environment (matches Chrome version)
        if os.path.exists('/.dockerenv'):
            # Docker environment - prioritize system-installed chromedriver
            possible_paths = [
                "/usr/local/bin/chromedriver",  # System-installed (from Dockerfile)
                "/usr/bin/chromedriver",        # Alternative system location
                "/app/seerr/chromedriver/chromedriver-linux64/chromedriver",  # Bundled fallback
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "seerr", "chromedriver", "chromedriver-linux64", "chromedriver"),
            ]
        else:
            # Local development environment
            possible_paths = [
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "seerr", "chromedriver", "chromedriver-linux64", "chromedriver"),
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "seerr", "chromedriver", "chromedriver-win64", "chromedriver.exe"),
                "/usr/local/bin/chromedriver",
                "/usr/bin/chromedriver",
                "/app/seerr/chromedriver/chromedriver-linux64/chromedriver",
                "/app/seerr/chromedriver/chromedriver-win64/chromedriver.exe"
            ]
        
        for path in possible_paths:
            if os.path.exists(path):
                chromedriver_path = path
                break
        
        if chromedriver_path:
            driver = webdriver.Chrome(service=Service(chromedriver_path), options=options)
        else:
            # Use default chromedriver location
            driver = webdriver.Chrome(options=options)
        
        # Navigate to Debrid Media Manager
        driver.get("https://debridmediamanager.com")
        time.sleep(2)
        
        # Inject credentials into localStorage
        driver.execute_script(f"""
            localStorage.setItem('rd:accessToken', '{access_token}');
            localStorage.setItem('rd:clientId', '"{client_id}"');
            localStorage.setItem('rd:clientSecret', '"{client_secret}"');
            localStorage.setItem('rd:refreshToken', '"{refresh_token}"');
        """)
        
        # Refresh the page to apply the local storage values
        driver.refresh()
        time.sleep(3)
        
        # Check for login button and click if present
        try:
            login_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Login with Real Debrid')]"))
            )
            login_button.click()
            time.sleep(2)
        except TimeoutException:
            pass  # No login button found, proceed
        
        # Navigate to library page
        driver.get("https://debridmediamanager.com/library")
        time.sleep(3)
        
        # Check if we were redirected to the start/login page (authentication failure)
        current_url = driver.current_url
        if "/start" in current_url or "/login" in current_url:
            raise Exception("DMM credentials are invalid. User was redirected to login page.")
        
        # Extract library stats
        library_stats = None
        try:
            library_stats_element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//h1[contains(@class, 'text-xl') and contains(@class, 'font-bold')]"))
            )
            library_stats_text = library_stats_element.text.strip()
            
            # CRITICAL: If we see "Welcome to Debrid Media Manager", we're on the login/welcome page, not the library page
            # This indicates authentication failure - immediately fail the test
            if "Welcome to Debrid Media Manager" in library_stats_text:
                raise Exception("DMM credentials are invalid. User is on login/welcome page instead of library page. Authentication failed.")
            
            # Verify we're actually on the library page - must contain "Library" or "torrents"
            if "Library" not in library_stats_text and "torrents" not in library_stats_text.lower():
                raise Exception(f"DMM credentials are invalid. Page text indicates we're not on the library page. Found: '{library_stats_text}'")
            
            # Parse the text to extract torrent count and size
            import re
            
            # Extract torrent count
            torrent_match = re.search(r'(\d+)\s+torrents', library_stats_text)
            torrents_count = int(torrent_match.group(1)) if torrent_match else 0
            
            # Extract TB size (also check for GB)
            size_match = re.search(r'([\d.]+)\s*TB', library_stats_text)
            if not size_match:
                size_match = re.search(r'([\d.]+)\s*GB', library_stats_text)
            total_size_tb = float(size_match.group(1)) if size_match else 0.0
            
            # If we see 0 torrents and 0TB/0GB, wait 5 seconds and check again
            # Sometimes people have larger libraries and it takes longer to load
            if torrents_count == 0 and total_size_tb == 0.0:
                time.sleep(5)
                try:
                    # Re-check the library stats element
                    library_stats_element = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, "//h1[contains(@class, 'text-xl') and contains(@class, 'font-bold')]"))
                    )
                    library_stats_text = library_stats_element.text.strip()
                    
                    # Re-extract torrent count and size
                    torrent_match = re.search(r'(\d+)\s+torrents', library_stats_text)
                    torrents_count = int(torrent_match.group(1)) if torrent_match else 0
                    
                    size_match = re.search(r'([\d.]+)\s*TB', library_stats_text)
                    if not size_match:
                        size_match = re.search(r'([\d.]+)\s*GB', library_stats_text)
                    total_size_tb = float(size_match.group(1)) if size_match else 0.0
                except (TimeoutException, Exception):
                    # If re-check fails, proceed with the original 0 values
                    pass
            
            library_stats = {
                "torrents_count": torrents_count,
                "total_size_tb": total_size_tb,
                "last_updated": time.strftime('%Y-%m-%d %H:%M:%S')
            }
        except TimeoutException:
            library_stats = {
                "torrents_count": 0,
                "total_size_tb": 0.0,
                "last_updated": time.strftime('%Y-%m-%d %H:%M:%S'),
                "note": "Could not extract library stats, but connection successful"
            }
        
        # Close the browser
        driver.quit()
        
        return {
            "success": True,
            "library_stats": library_stats,
            "message": "DMM credentials are valid and working"
        }
        
    except Exception as e:
        if driver:
            try:
                driver.quit()
            except:
                pass
        
        return {
            "success": False,
            "error": str(e),
            "library_stats": None
        }


if __name__ == "__main__":
    # This script can be called directly for testing
    if len(sys.argv) >= 5:
        client_id = sys.argv[1]
        client_secret = sys.argv[2]
        access_token = sys.argv[3]
        refresh_token = sys.argv[4]
        headless = sys.argv[5].lower() == 'true' if len(sys.argv) > 5 else True
        
        result = test_dmm_credentials_api(client_id, client_secret, access_token, refresh_token, headless)
        print(json.dumps(result))
        sys.exit(0 if result["success"] else 1)
    else:
        print(json.dumps({
            "success": False,
            "error": "Missing required credentials"
        }))
        sys.exit(1)
