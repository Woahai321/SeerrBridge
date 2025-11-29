#!/usr/bin/env python3
"""
Simple script to encrypt a value using the same encryption utilities as the backend
Can be called from Node.js when encryption is needed
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

def encrypt_value(plaintext_value: str):
    """Encrypt a value using the backend's encryption utilities"""
    if not plaintext_value:
        return ""
    
    try:
        # Encrypt it
        encrypted = config_encryption.encrypt_value(plaintext_value)
        return encrypted
    except Exception as e:
        # If encryption fails, return error
        import traceback
        print(f"ERROR: Encryption failed: {e}", file=sys.stderr)
        print(f"ERROR: Traceback:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return None

if __name__ == "__main__":
    # Read from stdin or command line args
    if len(sys.argv) > 1:
        plaintext_value = sys.argv[1]
    else:
        plaintext_value = sys.stdin.read().strip()
    
    if not plaintext_value:
        print("", end="")
        sys.exit(0)
    
    # Encrypt and output
    encrypted = encrypt_value(plaintext_value)
    
    if encrypted is None:
        # Encryption failed
        print(json.dumps({"error": "Encryption failed"}), end="")
        sys.exit(1)
    else:
        # Output the encrypted value as JSON
        print(json.dumps({"value": encrypted}), end="")
        sys.exit(0)

