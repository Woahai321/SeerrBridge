"""
Encryption utilities for sensitive configuration data
"""
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional
from loguru import logger

class ConfigEncryption:
    """Handles encryption and decryption of sensitive configuration values"""
    
    def __init__(self):
        self._fernet = None
        self._initialize_encryption()
    
    def _initialize_encryption(self):
        """Initialize encryption with a master key derived from environment"""
        try:
            # Get master key from environment - REQUIRED for production
            master_key = os.getenv('SEERRBRIDGE_MASTER_KEY')
            if not master_key:
                # Check if we're in production mode
                production_mode = os.getenv('PRODUCTION_MODE', 'false').lower() == 'true'
                
                if production_mode:
                    logger.error("SEERRBRIDGE_MASTER_KEY is required in production mode!")
                    logger.error("Please set SEERRBRIDGE_MASTER_KEY in your .env file")
                    raise ValueError("SEERRBRIDGE_MASTER_KEY environment variable is required in production")
                
                # Generate a new master key if none exists (development only)
                master_key = Fernet.generate_key().decode()
                logger.warning("No master key found. Generated new key (DO NOT USE IN PRODUCTION)")
                logger.warning("IMPORTANT: Save this key securely! Store it as SEERRBRIDGE_MASTER_KEY in your .env file")
                logger.warning("WARNING: This new key will not be able to decrypt previously encrypted data!")
                # DO NOT log the actual key value for security
            else:
                logger.info("Using SEERRBRIDGE_MASTER_KEY from environment")
            
            # Derive encryption key from master key
            password = master_key.encode()
            
            # Derive salt from master key for consistency (same master key = same salt)
            # This ensures deterministic encryption while keeping salt unique per master key
            import hashlib
            salt_hash = hashlib.sha256()
            salt_hash.update(b'SeerrBridge_Salt_Version_1.0')
            salt_hash.update(master_key.encode())
            salt = salt_hash.digest()[:16]  # Use first 16 bytes for salt (PBKDF2 requirement)
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password))
            self._fernet = Fernet(key)
            
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            raise
    
    def encrypt_value(self, value: str) -> str:
        """Encrypt a sensitive value"""
        if not value:
            return ""
        
        try:
            encrypted_bytes = self._fernet.encrypt(value.encode())
            return base64.urlsafe_b64encode(encrypted_bytes).decode()
        except Exception as e:
            logger.error(f"Failed to encrypt value: {e}")
            raise
    
    def decrypt_value(self, encrypted_value: str) -> str:
        """Decrypt a sensitive value"""
        if not encrypted_value:
            return ""
        
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_value.encode())
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            result = decrypted_bytes.decode()
            return result
        except Exception as e:
            logger.error(f"Failed to decrypt value: {e}")
            logger.error(f"Encrypted value was: {encrypted_value[:100]}...")
            raise
    
    def is_encrypted(self, value: str) -> bool:
        """Check if a value appears to be encrypted"""
        try:
            # Try to decode as base64 and decrypt
            base64.urlsafe_b64decode(value.encode())
            self._fernet.decrypt(base64.urlsafe_b64decode(value.encode()))
            return True
        except:
            return False

# Global instance
config_encryption = ConfigEncryption()
