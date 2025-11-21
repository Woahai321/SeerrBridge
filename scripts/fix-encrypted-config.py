#!/usr/bin/env python3

"""
Script to fix corrupted encrypted configuration values
"""

import os
import sys
sys.path.append('.')

from seerr.database import get_db, SystemConfig
from seerr.encryption_utils import config_encryption

def fix_encrypted_config():
    print("🔧 Fixing Corrupted Encrypted Configuration")
    print("=" * 50)
    
    db = get_db()
    try:
        sensitive_keys = ['rd_access_token', 'rd_refresh_token', 'rd_client_id', 'rd_client_secret', 'overseerr_api_key', 'trakt_api_key']
        
        print("\n1️⃣ Checking current values...")
        corrupted_keys = []
        
        for key in sensitive_keys:
            config = db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
            if config and config.config_value:
                try:
                    # Try to decrypt the value
                    if config_encryption.is_encrypted(config.config_value):
                        decrypted = config_encryption.decrypt_value(config.config_value)
                        print(f"   ✅ {key}: Decryption successful")
                    else:
                        print(f"   ⚠️  {key}: Not encrypted (legacy value)")
                except Exception as e:
                    print(f"   ❌ {key}: Decryption failed - {e}")
                    corrupted_keys.append(key)
            else:
                print(f"   ℹ️  {key}: No value set")
        
        if not corrupted_keys:
            print("\n✅ No corrupted values found!")
            return
        
        print(f"\n2️⃣ Found {len(corrupted_keys)} corrupted values:")
        for key in corrupted_keys:
            print(f"   - {key}")
        
        # Ask for confirmation
        response = input("\n❓ Do you want to clear these corrupted values? (y/N): ")
        if response.lower() != 'y':
            print("❌ Operation cancelled")
            return
        
        # Clear corrupted values
        print("\n3️⃣ Clearing corrupted values...")
        for key in corrupted_keys:
            config = db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
            if config:
                config.config_value = ''
                print(f"   ✅ Cleared {key}")
        
        db.commit()
        print("\n✅ Corrupted values cleared successfully!")
        print("\n💡 Next steps:")
        print("   1. Restart SeerrBridge")
        print("   2. Go to the settings page in the frontend")
        print("   3. Re-enter your API credentials")
        print("   4. The new values will be properly encrypted")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_encrypted_config()
