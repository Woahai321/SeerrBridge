#!/usr/bin/env python3
"""
Wait for Setup Completion Script
Waits for the setup wizard to be completed before starting the backend
Includes a simple API server for setup testing during the wait period
"""

import time
import requests
import subprocess
import sys
import os
import json
import threading
from datetime import datetime
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Create Flask app for setup API
app = Flask(__name__)

# Progress storage for test updates
test_progress = {}

def log_status(message: str, status: str = "info"):
    """Log status message with timestamp and formatting"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    if status == "success":
        print(f"[{timestamp}] ✅ {message}")
    elif status == "error":
        print(f"[{timestamp}] ❌ {message}")
    elif status == "warning":
        print(f"[{timestamp}] ⚠️  {message}")
    elif status == "progress":
        print(f"[{timestamp}] ⏳ {message}")
    else:
        print(f"[{timestamp}] ℹ️  {message}")

def add_progress(test_id: str, message: str, status: str = "info"):
    """Add progress message to test progress storage"""
    if test_id not in test_progress:
        test_progress[test_id] = []
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    progress_entry = {
        "timestamp": timestamp,
        "message": message,
        "status": status
    }
    test_progress[test_id].append(progress_entry)
    
    # Also log to console
    log_status(message, status)
    
    # Keep only last 50 progress entries per test
    if len(test_progress[test_id]) > 50:
        test_progress[test_id] = test_progress[test_id][-50:]

def test_dmm_credentials(client_id, client_secret, access_token, refresh_token, headless=True, test_id=None):
    """
    Test DMM credentials by spinning up a browser instance
    
    Args:
        client_id: Real-Debrid Client ID
        client_secret: Real-Debrid Client Secret
        access_token: Real-Debrid Access Token
        refresh_token: Real-Debrid Refresh Token
        headless: Run browser in headless mode
        test_id: Optional test ID for progress tracking
    
    Returns:
        dict: Test results with success status and library stats
    """
    driver = None
    
    try:
        progress_msg = "Starting DMM credentials test..."
        log_status(progress_msg, "info")
        if test_id:
            add_progress(test_id, progress_msg, "info")
        
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
            progress_msg = f"Using chromedriver at: {chromedriver_path}"
            log_status(progress_msg, "info")
            if test_id:
                add_progress(test_id, progress_msg, "info")
            driver = webdriver.Chrome(service=Service(chromedriver_path), options=options)
        else:
            progress_msg = "No chromedriver found, trying default location..."
            log_status(progress_msg, "warning")
            if test_id:
                add_progress(test_id, progress_msg, "warning")
            driver = webdriver.Chrome(options=options)
        
        # Navigate to Debrid Media Manager
        progress_msg = "Navigating to Debrid Media Manager..."
        log_status(progress_msg, "info")
        if test_id:
            add_progress(test_id, progress_msg, "info")
        driver.get("https://debridmediamanager.com")
        time.sleep(2)
        
        # Inject credentials into localStorage
        progress_msg = "Injecting credentials into browser..."
        if test_id:
            add_progress(test_id, progress_msg, "info")
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
            progress_msg = "Clicked login button"
            log_status(progress_msg, "info")
            if test_id:
                add_progress(test_id, progress_msg, "info")
            time.sleep(2)
        except TimeoutException:
            progress_msg = "No login button found, proceeding..."
            log_status(progress_msg, "info")
            if test_id:
                add_progress(test_id, progress_msg, "info")
        
        # Navigate to library page
        progress_msg = "Navigating to library page..."
        log_status(progress_msg, "info")
        if test_id:
            add_progress(test_id, progress_msg, "info")
        driver.get("https://debridmediamanager.com/library")
        time.sleep(3)
        
        # Check if we were redirected to the start/login page (authentication failure)
        current_url = driver.current_url
        progress_msg = f"Current URL after navigation: {current_url}"
        log_status(progress_msg, "info")
        if test_id:
            add_progress(test_id, progress_msg, "info")
        
        # Check if we're on the start/login page
        if "/start" in current_url or "/login" in current_url:
            progress_msg = "Authentication failed: Redirected to login/start page"
            log_status(progress_msg, "error")
            if test_id:
                add_progress(test_id, progress_msg, "error")
            raise Exception("DMM credentials are invalid. User was redirected to login page.")
        
        # Extract library stats - First check if we're on the library page
        library_stats = None
        try:
            library_stats_element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//h1[contains(@class, 'text-xl') and contains(@class, 'font-bold')]"))
            )
            library_stats_text = library_stats_element.text.strip()
            progress_msg = f"Page heading text found: {library_stats_text}"
            log_status(progress_msg, "info")
            if test_id:
                add_progress(test_id, progress_msg, "info")
            
            # CRITICAL: If we see "Welcome to Debrid Media Manager", we're on the login/welcome page, not the library page
            # This indicates authentication failure - immediately fail the test
            if "Welcome to Debrid Media Manager" in library_stats_text:
                progress_msg = "Authentication failed: Found 'Welcome to Debrid Media Manager' - user is on welcome/login page, not library page"
                log_status(progress_msg, "error")
                if test_id:
                    add_progress(test_id, progress_msg, "error")
                raise Exception("DMM credentials are invalid. User is on login/welcome page instead of library page. Authentication failed.")
            
            # Verify we're actually on the library page - must contain "Library" or "torrents"
            if "Library" not in library_stats_text and "torrents" not in library_stats_text.lower():
                progress_msg = f"Authentication failed: Page text '{library_stats_text}' doesn't match library page format. Expected 'Library' or 'torrents'."
                log_status(progress_msg, "error")
                if test_id:
                    add_progress(test_id, progress_msg, "error")
                raise Exception(f"DMM credentials are invalid. Page text indicates we're not on the library page. Found: '{library_stats_text}'")
            
            # Parse the text to extract torrent count and size
            import re
            
            # Extract torrent count
            torrent_match = re.search(r'(\d+)\s+torrents', library_stats_text)
            torrents_count = int(torrent_match.group(1)) if torrent_match else 0
            
            # Extract TB size
            size_match = re.search(r'([\d.]+)\s*TB', library_stats_text)
            total_size_tb = float(size_match.group(1)) if size_match else 0.0
            
            library_stats = {
                "torrents_count": torrents_count,
                "total_size_tb": total_size_tb,
                "last_updated": time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            progress_msg = f"Successfully extracted library stats: {torrents_count} torrents, {total_size_tb} TB"
            log_status(progress_msg, "success")
            if test_id:
                add_progress(test_id, progress_msg, "success")
        except TimeoutException:
            progress_msg = "Could not find library stats element within timeout"
            log_status(progress_msg, "warning")
            if test_id:
                add_progress(test_id, progress_msg, "warning")
            library_stats = {
                "torrents_count": 0,
                "total_size_tb": 0.0,
                "last_updated": time.strftime('%Y-%m-%d %H:%M:%S'),
                "note": "Could not extract library stats, but connection successful"
            }
        
        # Close the browser
        driver.quit()
        
        progress_msg = "DMM credentials test completed successfully"
        log_status(progress_msg, "success")
        if test_id:
            add_progress(test_id, progress_msg, "success")
        return {
            "success": True,
            "data": library_stats,
            "message": "DMM credentials are valid and working"
        }
        
    except Exception as e:
        log_status(f"Error testing DMM credentials: {e}", "error")
        if driver:
            try:
                driver.quit()
            except:
                pass
        
        progress_msg = f"Error testing DMM credentials: {str(e)}"
        log_status(progress_msg, "error")
        if test_id:
            add_progress(test_id, progress_msg, "error")
        
        return {
            "success": False,
            "error": str(e),
            "data": None
        }

@app.route('/api/setup/test-dmm', methods=['POST'])
def test_dmm_endpoint():
    """API endpoint for testing DMM credentials during setup"""
    try:
        data = request.get_json()
        
        rd_client_id = data.get('rd_client_id')
        rd_client_secret = data.get('rd_client_secret')
        rd_access_token = data.get('rd_access_token')
        rd_refresh_token = data.get('rd_refresh_token')
        test_id = data.get('test_id')  # Optional test ID for progress tracking
        
        if not all([rd_client_id, rd_client_secret, rd_access_token, rd_refresh_token]):
            return jsonify({
                "success": False,
                "error": "Missing required credentials"
            }), 400
        
        # Generate test_id if not provided
        if not test_id:
            test_id = f"dmm_test_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        log_status("Received DMM test request from frontend", "info")
        if test_id:
            add_progress(test_id, "Received DMM test request from frontend", "info")
        
        # Test the credentials
        result = test_dmm_credentials(
            rd_client_id, 
            rd_client_secret, 
            rd_access_token, 
            rd_refresh_token, 
            headless=True,
            test_id=test_id
        )
        
        # Add test_id to result
        result['test_id'] = test_id
        
        return jsonify(result)
        
    except Exception as e:
        log_status(f"Error in DMM test endpoint: {e}", "error")
        test_id = None
        try:
            test_id = data.get('test_id')
        except:
            pass
        if test_id:
            add_progress(test_id, f"Error testing DMM credentials: {str(e)}", "error")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/setup/test-dmm/progress/<test_id>', methods=['GET'])
def get_dmm_test_progress(test_id):
    """Get progress updates for a DMM test"""
    if test_id in test_progress:
        # Check if the last message indicates completion
        progress_list = test_progress[test_id]
        is_complete = False
        if progress_list:
            last_status = progress_list[-1].get('status', '')
            last_message = progress_list[-1].get('message', '').lower()
            if last_status == 'success' and ('completed successfully' in last_message or 'successfully extracted' in last_message):
                is_complete = True
            elif last_status == 'error':
                is_complete = True
        
        return jsonify({
            "success": True,
            "progress": progress_list,
            "is_complete": is_complete
        })
    else:
        # Test not found or completed
        return jsonify({
            "success": True,
            "progress": [],
            "is_complete": True
        })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "ok", "service": "setup-wait"})

def wait_for_database(timeout: int = 300) -> bool:
    """Wait for MySQL database to be ready"""
    log_status("Starting database health check...", "info")
    
    # Get database credentials from environment variables
    # Default to 'localhost' for unified container, 'mysql' for multi-container
    db_host = os.environ.get('DB_HOST', 'localhost')
    db_port = int(os.environ.get('DB_PORT', '3306'))
    db_user = os.environ.get('DB_USER', 'seerrbridge')
    db_password = os.environ.get('DB_PASSWORD', 'seerrbridge')
    db_name = os.environ.get('DB_NAME', 'seerrbridge')
    
    start_time = time.time()
    attempt = 0
    
    while time.time() - start_time < timeout:
        attempt += 1
        elapsed = int(time.time() - start_time)
        
        try:
            # Try to connect to MySQL
            import pymysql
            connection = pymysql.connect(
                host=db_host,
                port=db_port,
                user=db_user,
                password=db_password,
                database=db_name,
                connect_timeout=5
            )
            connection.close()
            log_status(f"Database connection successful! (took {elapsed}s)", "success")
            return True
        except ImportError:
            log_status("pymysql not available, skipping database check", "warning")
            return True  # Continue if pymysql is not installed
        except Exception as e:
            if attempt % 6 == 0:  # Log every 30 seconds (6 * 5s)
                log_status(f"Database not ready yet (attempt {attempt}, {elapsed}s elapsed): {str(e)[:100]}...", "progress")
            time.sleep(5)
    
    log_status(f"Database failed to start within {timeout}s timeout", "error")
    return False

def wait_for_setup_completion(timeout: int = 600) -> bool:
    """Wait for setup wizard to be completed"""
    log_status("Starting setup wizard completion check...", "info")
    # Try both production and dev URLs, plus localhost for unified container
    setup_api_urls = [
        "http://localhost:3777/api/setup-status",  # Unified container
        "http://darthvadarr-nuxt:3777/api/setup-status",  # Production multi-container
        "http://darthvadarr-nuxt-dev:3777/api/setup-status"  # Development
    ]
    start_time = time.time()
    attempt = 0
    
    while time.time() - start_time < timeout:
        attempt += 1
        elapsed = int(time.time() - start_time)
        
        # Try each URL until one works
        for setup_api_url in setup_api_urls:
            try:
                response = requests.get(setup_api_url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success') and not data.get('data', {}).get('needsSetup', True):
                        log_status(f"Setup wizard completed! (took {elapsed}s)", "success")
                        return True
                    else:
                        missing_configs = data.get('data', {}).get('missingConfigs', [])
                        if attempt % 6 == 0:  # Log every 60 seconds
                            log_status(f"Setup still required (attempt {attempt}, {elapsed}s elapsed). Missing: {missing_configs}", "progress")
                        break  # Found working URL, don't try others
                else:
                    if attempt % 6 == 0:  # Log every 60 seconds
                        log_status(f"Setup API returned status {response.status_code} (attempt {attempt}, {elapsed}s elapsed)", "progress")
            except Exception as e:
                if attempt % 6 == 0:  # Log every 60 seconds
                    log_status(f"Setup check failed for {setup_api_url} (attempt {attempt}, {elapsed}s elapsed): {e}", "progress")
                continue  # Try next URL
        
        time.sleep(10)
    
    log_status(f"Setup wizard not completed within {timeout}s timeout", "error")
    return False

def fix_permissions():
    """Fix permissions for logs and data directories"""
    log_status("Checking and fixing directory permissions...", "info")
    
    # Try to ensure directories exist and are writable
    try:
        # Create directories if they don't exist
        os.makedirs('/app/logs', mode=0o755, exist_ok=True)
        os.makedirs('/app/data', mode=0o755, exist_ok=True)
        
        # Try to create log file
        log_file = '/app/logs/seerrbridge.log'
        with open(log_file, 'a'):
            pass
        os.chmod(log_file, 0o664)
        
        log_status("Created/verified directory and log file permissions", "success")
    except PermissionError:
        log_status("Warning: Permission denied when trying to set permissions", "warning")
        log_status("Continuing anyway - the Docker volume should have correct permissions", "info")
    except Exception as e:
        log_status(f"Warning: Could not set permissions: {e}", "warning")

def start_backend():
    """Start the SeerrBridge backend"""
    log_status("Initializing SeerrBridge backend...", "info")
    
    # Change to the app directory
    os.chdir('/app')
    
    # Fix directory permissions
    fix_permissions()
    
    # Start the backend using uvicorn (production) or python main.py (dev)
    try:
        # Try uvicorn first (production)
        process = subprocess.Popen([
            'uvicorn', 'main:app', '--host', '0.0.0.0', '--port', '8777', '--workers', '1'
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        log_status("Started backend with uvicorn (production mode)", "success")
    except FileNotFoundError:
        # Fallback to python main.py (development)
        process = subprocess.Popen([
            'python', 'main.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        log_status("Started backend with python main.py (development mode)", "success")
    
    log_status("SeerrBridge backend process started!", "success")
    
    # Stream output with better formatting
    try:
        for line in iter(process.stdout.readline, ''):
            if line.strip():
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"[{timestamp}] [BACKEND] {line.rstrip()}")
    except KeyboardInterrupt:
        log_status("Received interrupt signal, shutting down backend...", "warning")
        process.terminate()
        process.wait()
    
    return process

def start_setup_api_server():
    """Start the Flask API server for setup testing"""
    log_status("Starting setup API server on port 8778...", "info")
    try:
        app.run(host='0.0.0.0', port=8778, debug=False, threaded=True)
    except Exception as e:
        log_status(f"Error starting setup API server: {e}", "error")

if __name__ == "__main__":
    log_status("Starting SeerrBridge setup wait process...", "info")
    log_status(f"Process initiated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "info")
    
    # Step 1: Wait for database to be ready
    log_status("Step 1/3: Waiting for MySQL database to be ready...", "info")
    if not wait_for_database():
        log_status("Startup failed: Database not ready", "error")
        sys.exit(1)
    
    # Start the setup API server in a separate thread
    api_thread = threading.Thread(target=start_setup_api_server, daemon=True)
    api_thread.start()
    
    # Give the API server a moment to start
    time.sleep(2)
    log_status("Setup API server started on port 8778", "success")
    
    # Step 2: Wait for setup completion
    log_status("Step 2/3: Waiting for setup wizard completion...", "info")
    if not wait_for_setup_completion():
        log_status("Setup not completed, exiting...", "error")
        sys.exit(1)
    
    # Step 3: Start backend
    log_status("Step 3/3: Starting backend service...", "info")
    backend_process = start_backend()
    
    # Wait for backend to finish
    backend_process.wait()
