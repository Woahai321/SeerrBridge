#!/usr/bin/env python3

"""
Script to force reload backend configuration
"""

import os
import sys
sys.path.append('.')

from seerr.config import load_config

def reload_backend_config():
    print("🔄 Reloading Backend Configuration")
    print("=" * 50)
    
    # Reload configuration from .env file
    print("\n1️⃣ Reloading configuration from .env file...")
    success = load_config(override=True)
    
    if success:
        print("   ✅ Configuration reloaded successfully")
        
        # Show current values
        from seerr.config import OVERSEERR_API_KEY, OVERSEERR_BASE, RD_ACCESS_TOKEN
        print(f"\n3️⃣ Current Values:")
        print(f"   OVERSEERR_BASE: {OVERSEERR_BASE}")
        print(f"   OVERSEERR_API_KEY: {OVERSEERR_API_KEY[:20] + '...' if OVERSEERR_API_KEY else 'None'}")
        print(f"   RD_ACCESS_TOKEN: {RD_ACCESS_TOKEN[:20] + '...' if RD_ACCESS_TOKEN else 'None'}")
        
        # Check if values look correct
        if OVERSEERR_API_KEY and OVERSEERR_BASE:
            print("\n   ✅ API key configured")
        else:
            print("\n   ❌ Missing API credentials")
            print("   💡 Please enter your credentials in the frontend settings")
    else:
        print("   ❌ Failed to reload configuration")

if __name__ == "__main__":
    reload_backend_config()
