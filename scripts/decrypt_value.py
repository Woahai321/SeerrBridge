#!/usr/bin/env python3
"""
Simple script to decrypt a value using the same encryption utilities as the backend
Can be called from Node.js when decryption is needed
"""
import sys
import os
import json

# Add the parent directory to the path so we can import seerr modules
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

try:
    from seerr.encryption_utils import config_encryption
except ImportError as e:
    print(f"ERROR: Failed to import encryption utilities: {e}", file=sys.stderr)
    print(f"ERROR: Project root: {project_root}", file=sys.stderr)
    print(f"ERROR: Script dir: {script_dir}", file=sys.stderr)
    sys.exit(1)

def decrypt_value(encrypted_value: str):
    """Decrypt a value using the backend's encryption utilities"""
    if not encrypted_value:
        return ""
    
    try:
        # Check if it's encrypted - if not, return None to indicate it's plaintext
        if not config_encryption.is_encrypted(encrypted_value):
            # Not encrypted, return None to indicate plaintext
            return None
        
        # Decrypt it
        decrypted = config_encryption.decrypt_value(encrypted_value)
        return decrypted
    except Exception as e:
        # If decryption fails, return None/null and log the error
        import traceback
        print(f"ERROR: Decryption failed: {e}", file=sys.stderr)
        print(f"ERROR: Traceback:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return None

if __name__ == "__main__":
    # Read from stdin or command line args
    if len(sys.argv) > 1:
        encrypted_value = sys.argv[1]
    else:
        encrypted_value = sys.stdin.read().strip()
    
    if not encrypted_value:
        print("", end="")
        sys.exit(0)
    
    # Decrypt and output
    decrypted = decrypt_value(encrypted_value)
    
    if decrypted is None:
        # Value is plaintext (not encrypted) or decryption failed
        # Return null to indicate it's plaintext
        print(json.dumps({"value": None}), end="")
        sys.exit(0)
    else:
        # Output the decrypted value as JSON
        print(json.dumps({"value": decrypted}), end="")
        sys.exit(0)

