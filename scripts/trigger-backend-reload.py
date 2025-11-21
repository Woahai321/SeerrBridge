#!/usr/bin/env python3

"""
Script to trigger backend configuration reload
"""

import requests
import json

def trigger_backend_reload():
    print("🔄 Triggering Backend Configuration Reload")
    print("=" * 50)
    
    # Get SeerrBridge URL from environment or use default
    seerrbridge_url = os.getenv('SEERRBRIDGE_URL', 'http://localhost:8777')
    
    try:
        print(f"📍 Calling {seerrbridge_url}/reload-env...")
        
        response = requests.post(
            f"{seerrbridge_url}/reload-env",
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Backend reload triggered successfully")
            
            if 'changes' in data and data['changes']:
                print(f"\n📊 Configuration changes detected:")
                for key, change_info in data['changes'].items():
                    print(f"   {key}: {change_info}")
            else:
                print("\n📊 No configuration changes detected")
                
            print("\n💡 The backend should now be using the updated configuration")
            
        else:
            print(f"❌ Failed to trigger reload: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to SeerrBridge at {seerrbridge_url}")
        print("   Make sure SeerrBridge is running")
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    import os
    trigger_backend_reload()
