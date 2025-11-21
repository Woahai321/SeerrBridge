#!/usr/bin/env python3

"""
Script to set up a persistent encryption key for SeerrBridge
"""

import os
import sys
sys.path.append('.')

from cryptography.fernet import Fernet
from seerr.database import get_db, SystemConfig

def setup_encryption_key():
    print("🔐 Setting up SeerrBridge Encryption Key")
    print("=" * 50)
    
    # Check if key already exists
    existing_key = os.getenv('SEERRBRIDGE_MASTER_KEY')
    if existing_key:
        print(f"✅ Master key already exists: {existing_key[:10]}...")
        print("   If you're having decryption issues, this key might be different from the one used to encrypt your data.")
        
        response = input("\n❓ Do you want to generate a new key? This will make existing encrypted data unreadable. (y/N): ")
        if response.lower() != 'y':
            print("❌ Keeping existing key")
            return
    
    # Generate new key
    print("\n🔑 Generating new master key...")
    master_key = Fernet.generate_key().decode()
    
    print(f"✅ Generated master key: {master_key}")
    print("\n📝 IMPORTANT: Save this key securely!")
    print("   You need to set this as the SEERRBRIDGE_MASTER_KEY environment variable.")
    print("   Add this to your .env file or environment:")
    print(f"   SEERRBRIDGE_MASTER_KEY={master_key}")
    
    # Check if we should clear existing encrypted data
    db = get_db()
    try:
        sensitive_keys = ['rd_access_token', 'rd_refresh_token', 'rd_client_id', 'rd_client_secret', 'overseerr_api_key', 'trakt_api_key']
        
        encrypted_count = 0
        for key in sensitive_keys:
            config = db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
            if config and config.config_value:
                encrypted_count += 1
        
        if encrypted_count > 0:
            print(f"\n⚠️  Found {encrypted_count} existing encrypted values in database")
            response = input("❓ Do you want to clear these so you can re-enter them with the new key? (y/N): ")
            if response.lower() == 'y':
                print("\n🧹 Clearing existing encrypted values...")
                for key in sensitive_keys:
                    config = db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
                    if config:
                        config.config_value = ''
                        print(f"   ✅ Cleared {key}")
                
                db.commit()
                print("✅ Existing values cleared")
            else:
                print("⚠️  Keeping existing values (they may not be decryptable with the new key)")
    
    except Exception as e:
        print(f"❌ Error checking database: {e}")
    finally:
        db.close()
    
    print("\n🎉 Setup complete!")
    print("\n📋 Next steps:")
    print("   1. Add the master key to your environment:")
    print(f"      export SEERRBRIDGE_MASTER_KEY={master_key}")
    print("   2. Restart SeerrBridge")
    print("   3. Go to settings and re-enter your API credentials")
    print("   4. The new credentials will be properly encrypted with the persistent key")

if __name__ == "__main__":
    setup_encryption_key()
