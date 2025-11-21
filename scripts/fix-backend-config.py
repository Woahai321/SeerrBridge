#!/usr/bin/env python3

"""
Comprehensive script to fix backend configuration issues
"""

import os
import sys
import requests
sys.path.append('.')

def fix_backend_config():
    print("🔧 Fixing Backend Configuration Issues")
    print("=" * 50)
    
    seerrbridge_url = os.getenv('SEERRBRIDGE_URL', 'http://localhost:8777')
    
    # Step 1: Test current backend configuration
    print("\n1️⃣ Testing current backend configuration...")
    try:
        response = requests.get(f"{seerrbridge_url}/api/config", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                configs = data.get('configs', [])
                print("   ✅ Backend API is responding")
                
                # Check for API credentials
                overseerr_key = None
                overseerr_base = None
                for config in configs:
                    if config['config_key'] == 'overseerr_api_key':
                        overseerr_key = config['config_value']
                    elif config['config_key'] == 'overseerr_base':
                        overseerr_base = config['config_value']
                
                print(f"   Overseerr Base: {overseerr_base}")
                print(f"   Overseerr API Key: {overseerr_key[:20] + '...' if overseerr_key else 'None'}")
                
                if overseerr_key and len(overseerr_key) > 50:
                    print("   ⚠️  API key looks encrypted (too long)")
                elif overseerr_key:
                    print("   ✅ API key looks correct")
                else:
                    print("   ❌ No API key found")
            else:
                print("   ❌ Backend API returned error")
        else:
            print(f"   ❌ Backend API error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Could not connect to backend: {e}")
        return
    
    # Step 2: Trigger configuration reload
    print("\n2️⃣ Triggering configuration reload...")
    try:
        response = requests.post(f"{seerrbridge_url}/reload-env", timeout=30)
        if response.status_code == 200:
            data = response.json()
            print("   ✅ Configuration reload triggered")
            
            if 'changes' in data and data['changes']:
                print("   📊 Changes detected:")
                for key, change_info in data['changes'].items():
                    print(f"      {key}: {change_info}")
            else:
                print("   📊 No changes detected")
        else:
            print(f"   ❌ Reload failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Reload error: {e}")
    
    # Step 3: Test API call simulation
    print("\n3️⃣ Testing API call simulation...")
    try:
        # Get the current config again
        response = requests.get(f"{seerrbridge_url}/api/config", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                configs = data.get('configs', [])
                
                overseerr_key = None
                overseerr_base = None
                for config in configs:
                    if config['config_key'] == 'overseerr_api_key':
                        overseerr_key = config['config_value']
                    elif config['config_key'] == 'overseerr_base':
                        overseerr_base = config['config_value']
                
                if overseerr_key and overseerr_base:
                    print(f"   Would call: {overseerr_base}/api/v1/request")
                    print(f"   With key: {overseerr_key[:10]}...")
                    
                    # Test if the key looks like a real API key
                    if len(overseerr_key) > 50:
                        print("   ⚠️  Key still looks encrypted")
                        print("   💡 You may need to:")
                        print("      1. Clear corrupted encrypted values")
                        print("      2. Re-enter credentials in frontend")
                        print("      3. Restart SeerrBridge")
                    else:
                        print("   ✅ Key looks correct")
                else:
                    print("   ❌ Missing API credentials")
    except Exception as e:
        print(f"   ❌ Test error: {e}")
    
    print("\n🎯 Next Steps:")
    print("   1. If API key still looks encrypted, run:")
    print("      python scripts/fix-encrypted-config.py")
    print("   2. Re-enter your credentials in the frontend")
    print("   3. Restart SeerrBridge if needed")

if __name__ == "__main__":
    fix_backend_config()
