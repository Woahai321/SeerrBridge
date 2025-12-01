#!/usr/bin/env python3
"""
Startup Orchestrator for SeerrBridge
Ensures proper startup sequence: Database -> Frontend -> Setup -> Backend
"""

import time
import requests
import subprocess
import sys
import os
import json
from typing import Optional
from datetime import datetime

class StartupOrchestrator:
    def __init__(self):
        self.db_url = "http://mysql:3306"
        self.frontend_url = "http://darthvadarr-nuxt-dev:3777"
        self.setup_api_url = "http://darthvadarr-nuxt-dev:3777/api/setup-status"
        self.backend_process: Optional[subprocess.Popen] = None
        self.start_time = datetime.now()
        self.retry_delay = 2  # Initial retry delay in seconds
        self.max_retry_delay = 30  # Maximum retry delay in seconds
    
    def log_status(self, message: str, status: str = "info"):
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
    
    def exponential_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay"""
        delay = min(self.retry_delay * (2 ** attempt), self.max_retry_delay)
        return delay
    
    def make_request_with_retry(self, url: str, timeout: int = 5, max_retries: int = 3) -> Optional[requests.Response]:
        """Make HTTP request with exponential backoff retry"""
        for attempt in range(max_retries):
            try:
                response = requests.get(url, timeout=timeout)
                return response
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = self.exponential_backoff(attempt)
                    self.log_status(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {delay:.1f}s...", "warning")
                    time.sleep(delay)
                else:
                    self.log_status(f"Request failed after {max_retries} attempts: {e}", "error")
                    return None
        return None
        
    def wait_for_database(self, timeout: int = 300) -> bool:
        """Wait for MySQL database to be ready"""
        self.log_status("Starting database health check...", "info")
        start_time = time.time()
        attempt = 0
        
        while time.time() - start_time < timeout:
            attempt += 1
            elapsed = int(time.time() - start_time)
            
            try:
                # Try to connect to MySQL
                import pymysql
                connection = pymysql.connect(
                    host='mysql',
                    port=3306,
                    user='seerrbridge',
                    password='seerrbridge',
                    database='seerrbridge',
                    connect_timeout=5
                )
                connection.close()
                self.log_status(f"Database connection successful! (took {elapsed}s)", "success")
                return True
            except Exception as e:
                if attempt % 6 == 0:  # Log every 30 seconds (6 * 5s)
                    self.log_status(f"Database not ready yet (attempt {attempt}, {elapsed}s elapsed): {str(e)[:100]}...", "progress")
                time.sleep(5)
        
        self.log_status(f"Database failed to start within {timeout}s timeout", "error")
        return False
    
    def wait_for_frontend(self, timeout: int = 300) -> bool:
        """Wait for Nuxt frontend to be built and ready"""
        self.log_status("Starting frontend health check...", "info")
        start_time = time.time()
        attempt = 0
        
        while time.time() - start_time < timeout:
            attempt += 1
            elapsed = int(time.time() - start_time)
            
            response = self.make_request_with_retry(f"{self.frontend_url}/api/health", timeout=5, max_retries=1)
            if response and response.status_code == 200:
                self.log_status(f"Frontend is ready! (took {elapsed}s)", "success")
                return True
            else:
                if attempt % 6 == 0:  # Log every 30 seconds
                    self.log_status(f"Frontend not ready yet (attempt {attempt}, {elapsed}s elapsed)", "progress")
                time.sleep(5)
        
        self.log_status(f"Frontend failed to start within {timeout}s timeout", "error")
        return False
    
    def wait_for_setup_completion(self, timeout: int = 600) -> bool:
        """Wait for setup wizard to be completed"""
        self.log_status("Starting setup wizard completion check...", "info")
        start_time = time.time()
        attempt = 0
        
        while time.time() - start_time < timeout:
            attempt += 1
            elapsed = int(time.time() - start_time)
            
            response = self.make_request_with_retry(self.setup_api_url, timeout=5, max_retries=1)
            if response and response.status_code == 200:
                try:
                    data = response.json()
                    if data.get('success') and not data.get('data', {}).get('needsSetup', True):
                        self.log_status(f"Setup wizard completed! (took {elapsed}s)", "success")
                        return True
                    else:
                        missing_configs = data.get('data', {}).get('missingConfigs', [])
                        if attempt % 6 == 0:  # Log every 60 seconds
                            self.log_status(f"Setup still required (attempt {attempt}, {elapsed}s elapsed). Missing: {missing_configs}", "progress")
                except json.JSONDecodeError as e:
                    if attempt % 6 == 0:
                        self.log_status(f"Invalid JSON response from setup API (attempt {attempt}, {elapsed}s elapsed): {e}", "warning")
            else:
                if attempt % 6 == 0:  # Log every 60 seconds
                    self.log_status(f"Setup API not responding (attempt {attempt}, {elapsed}s elapsed)", "progress")
            
            time.sleep(10)
        
        self.log_status(f"Setup wizard not completed within {timeout}s timeout", "error")
        return False
    
    def start_backend(self):
        """Start the SeerrBridge backend"""
        self.log_status("Initializing SeerrBridge backend...", "info")
        
        # Change to the app directory
        os.chdir('/app')
        
        # Start the backend
        self.backend_process = subprocess.Popen([
            'python', 'main.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        self.log_status("SeerrBridge backend process started!", "success")
        
        # Stream output with better formatting
        try:
            for line in iter(self.backend_process.stdout.readline, ''):
                if line.strip():
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(f"[{timestamp}] [BACKEND] {line.rstrip()}")
        except KeyboardInterrupt:
            self.log_status("Received interrupt signal, shutting down backend...", "warning")
            if self.backend_process:
                self.backend_process.terminate()
                self.backend_process.wait()
    
    def run(self):
        """Run the complete startup sequence"""
        self.log_status("Starting SeerrBridge orchestrated startup sequence...", "info")
        self.log_status(f"Startup initiated at {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}", "info")
        
        # Step 1: Wait for database
        self.log_status("Step 1/4: Checking database availability...", "info")
        if not self.wait_for_database():
            self.log_status("Startup failed: Database not ready", "error")
            sys.exit(1)
        
        # Step 2: Wait for frontend
        self.log_status("Step 2/4: Checking frontend availability...", "info")
        if not self.wait_for_frontend():
            self.log_status("Startup failed: Frontend not ready", "error")
            sys.exit(1)
        
        # Step 3: Wait for setup completion
        self.log_status("Step 3/4: Checking setup wizard completion...", "info")
        if not self.wait_for_setup_completion():
            self.log_status("Startup failed: Setup not completed", "error")
            sys.exit(1)
        
        # Step 4: Start backend
        self.log_status("Step 4/4: Starting backend service...", "info")
        self.start_backend()
        
        # Step 5: Wait for backend to finish
        if self.backend_process:
            self.log_status("Backend process started, monitoring output...", "info")
            self.backend_process.wait()

if __name__ == "__main__":
    orchestrator = StartupOrchestrator()
    orchestrator.run()
