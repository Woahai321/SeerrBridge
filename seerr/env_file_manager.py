"""
Utility to read and write .env files for SeerrBridge
"""
import os
import re
from typing import Dict, Any, Optional

class EnvFileManager:
    """Manages reading and writing to .env file"""
    
    def __init__(self, env_path: str = None):
        # Use /app/data/.env in containers, or ./.env in local development
        if env_path is None:
            import os
            if os.getenv('PYTHON_ENV') == 'production' or os.path.exists('/app/data'):
                # Running in container - use shared data directory
                self.env_path = '/app/data/.env'
            else:
                # Local development - use project root
                self.env_path = '.env'
        else:
            self.env_path = env_path
    
    def read_env(self) -> Dict[str, str]:
        """Read all environment variables from .env file"""
        env: Dict[str, str] = {}
        
        if not os.path.exists(self.env_path):
            return env
        
        try:
            with open(self.env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse KEY=VALUE format
                    if '=' not in line:
                        continue
                    
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes if present and unescape
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                        # Unescape: \\ becomes \, \" becomes "
                        # Do this carefully to avoid double-unescaping
                        value = value.replace('\\\\', '\u0000TEMP_BACKSLASH\u0000')  # Temporarily replace \\
                        value = value.replace('\\"', '"')                            # Unescape quotes
                        value = value.replace('\u0000TEMP_BACKSLASH\u0000', '\\')    # Restore backslashes
                    
                    env[key] = value
        except Exception as e:
            print(f"Error reading .env file: {e}")
        
        return env
    
    def write_env(self, env: Dict[str, Any]) -> None:
        """Write environment variables to .env file"""
        lines = []
        
        # Add header comment
        lines.append('# SeerrBridge Configuration')
        lines.append('# This file is auto-generated. Do not edit manually unless you know what you are doing.')
        lines.append('')
        
        # Sort keys for better readability
        sorted_keys = sorted(env.keys())
        
        for key in sorted_keys:
            value = env[key]
            
            # Skip null/undefined values
            if value is None:
                continue
            
            # Convert value to string
            value_str = str(value)
            
            # Check if value is a JSON object (starts with { and ends with })
            is_json_object = value_str.strip().startswith('{') and value_str.strip().endswith('}')
            
            # Always wrap JSON objects and values with special characters in quotes
            if is_json_object or ' ' in value_str or '=' in value_str or '#' in value_str:
                # Escape quotes and backslashes for .env file format
                # Do this carefully: escape backslashes first, then quotes
                value_str = value_str.replace('\\', '\\\\').replace('"', '\\"')
                value_str = f'"{value_str}"'
            
            lines.append(f'{key}={value_str}')
        
        try:
            with open(self.env_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines) + '\n')
        except Exception as e:
            print(f"Error writing .env file: {e}")
            raise
    
    def update_env(self, updates: Dict[str, Any]) -> None:
        """Update specific environment variables in .env file"""
        # Read existing env
        existing = self.read_env()
        
        # Merge with updates
        merged = {**existing, **updates}
        
        # Remove null/undefined values
        merged = {k: v for k, v in merged.items() if v is not None}
        
        # Write back
        self.write_env(merged)
    
    def get(self, key: str) -> Optional[str]:
        """Get a specific environment variable"""
        env = self.read_env()
        return env.get(key)
    
    def set(self, key: str, value: Any) -> None:
        """Set a specific environment variable"""
        self.update_env({key: value})

# Global instance
env_file = EnvFileManager()

