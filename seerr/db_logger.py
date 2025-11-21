"""
Database logger for SeerrBridge
Replaces file-based logging with database logging
"""
import sys
import traceback
from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger
from seerr.database import log_to_database, get_db, LogEntry
from seerr.config import USE_DATABASE

class DatabaseLogger:
    """Custom logger that writes to database instead of files"""
    
    def __init__(self):
        self.use_database = USE_DATABASE
        self.setup_loguru()
    
    def setup_loguru(self):
        """Setup loguru with database logging"""
        # Remove default handlers
        logger.remove()
        
        # Add console handler
        logger.add(
            sys.stdout,
            colorize=True,
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="INFO"
        )
        
        # Add database handler if enabled
        if self.use_database:
            logger.add(
                sink=self._log_to_db,
                level="INFO",
                filter=self._should_log_to_db,
                catch=False
            )
        
        # Also add a file handler for backup (only if directory exists and is writable)
        try:
            import os
            log_file = "logs/seerrbridge.log"
            if os.path.exists(os.path.dirname(log_file)):
                # Try to create/open the log file to check permissions
                open(log_file, 'a').close()
                logger.add(
                    log_file, 
                    rotation="500 MB", 
                    encoding='utf-8',
                    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
                    level="INFO"
                )
        except (PermissionError, OSError):
            # If we can't write to the file, skip file logging (database logging will be used instead)
            pass
    
    def _should_log_to_db(self, record):
        """Filter to determine if log should go to database"""
        try:
            # Skip certain log levels or messages
            skip_levels = ['TRACE']
            skip_messages = [
                'Starting new HTTPS connection',
                'Starting new HTTP connection',
                'Resetting dropped connection',
                'Connection pool is full',
            ]
            
            # Safely access record attributes
            level_name = getattr(record, 'level', None)
            if level_name and hasattr(level_name, 'name'):
                if level_name.name in skip_levels:
                    return False
            
            message_text = getattr(record, 'message', '')
            if any(skip_msg in message_text for skip_msg in skip_messages):
                return False
            
            return True
        except Exception:
            # If we can't determine, allow the log to go through
            return True
    
    def _log_to_db(self, record):
        """Log message to database - loguru handler"""
        try:
            # Extract message from loguru record - handle different record types
            if hasattr(record, 'message'):
                message_text = str(record.message)
            elif isinstance(record, dict) and 'message' in record:
                message_text = str(record['message'])
            else:
                message_text = str(record)
            
            lines = message_text.split('\n')
            title = lines[0][:500] if lines else "Log Entry"
            
            # Get level from record - handle different record types
            if hasattr(record, 'level'):
                level_name = record.level.name.lower()
            elif isinstance(record, dict) and 'level' in record:
                level_name = record['level'].name.lower()
            else:
                level_name = 'info'
            
            if level_name == 'trace':
                level = 'info'
            else:
                level = level_name
            
            # Get module, function, line from record - handle different record types
            if hasattr(record, 'name'):
                module = record.name
            elif isinstance(record, dict) and 'name' in record:
                module = record['name']
            else:
                module = None
                
            if hasattr(record, 'function'):
                function = record.function
            elif isinstance(record, dict) and 'function' in record:
                function = record['function']
            else:
                function = None
                
            if hasattr(record, 'line'):
                line_number = record.line
            elif isinstance(record, dict) and 'line' in record:
                line_number = record['line']
            else:
                line_number = None
            
            # Log to database
            log_id = log_to_database(
                level=level,
                title=title,
                message=message_text,
                module=module,
                function=function,
                line_number=line_number,
                details={'source': 'loguru'},
                source='seerrbridge'
            )
            
            return log_id
            
        except Exception as e:
            # Fallback to console if database logging fails
            # Only print debug info if it's not a connection error
            if "Access denied" not in str(e) and "OperationalError" not in str(e):
                print(f"Database logging failed: {e}")
            return None

    def _simple_log_to_db(self, message):
        """Simple database logging without complex record processing"""
        try:
            # Just log the message as-is to database
            message_text = str(message)
            lines = message_text.split('\n')
            title = lines[0][:500] if lines else "Log Entry"
            
            # Extract level from message
            level = 'info'
            if 'ERROR' in message_text:
                level = 'error'
            elif 'WARNING' in message_text:
                level = 'warning'
            elif 'SUCCESS' in message_text:
                level = 'success'
            elif 'CRITICAL' in message_text:
                level = 'critical'
            elif 'DEBUG' in message_text:
                level = 'info'
            
            # Log to database
            log_to_database(
                level=level,
                title=title,
                message=message_text,
                module=None,
                function=None,
                line_number=None,
                details={'source': 'loguru_simple'},
                source='seerrbridge'
            )
            
        except Exception as e:
            # Don't print error to avoid recursion
            pass

# Create global database logger instance and initialize it
db_logger = DatabaseLogger()

# Initialize the global logger configuration
db_logger.setup_loguru()

# Patch the global logger to use our database logging
import sys
import loguru

# Replace the default logger with our configured one
loguru.logger = logger
sys.modules['loguru'].logger = logger

# Convenience functions for different log levels
def log_info(title: str, message: str, **kwargs):
    """Log info message"""
    logger.info(f"{title}: {message}")
    # Also log to database directly
    if USE_DATABASE:
        try:
            log_to_database(
                level='info',
                title=title,
                message=message,
                module=kwargs.get('module'),
                function=kwargs.get('function'),
                line_number=kwargs.get('line_number'),
                details=kwargs.get('details', {}),
                source='seerrbridge'
            )
        except Exception as e:
            # Only print debug info if it's not a connection error
            if "Access denied" not in str(e) and "OperationalError" not in str(e):
                print(f"Database logging failed for info: {e}")

def log_success(title: str, message: str, **kwargs):
    """Log success message"""
    logger.info(f"{title}: {message}")
    # Also log to database directly
    if USE_DATABASE:
        try:
            log_to_database(
                level='success',
                title=title,
                message=message,
                module=kwargs.get('module'),
                function=kwargs.get('function'),
                line_number=kwargs.get('line_number'),
                details=kwargs.get('details', {}),
                source='seerrbridge'
            )
        except Exception as e:
            # Only print debug info if it's not a connection error
            if "Access denied" not in str(e) and "OperationalError" not in str(e):
                print(f"Database logging failed for success: {e}")

def log_warning(title: str, message: str, **kwargs):
    """Log warning message"""
    logger.warning(f"{title}: {message}")
    # Also log to database directly
    if USE_DATABASE:
        try:
            log_to_database(
                level='warning',
                title=title,
                message=message,
                module=kwargs.get('module'),
                function=kwargs.get('function'),
                line_number=kwargs.get('line_number'),
                details=kwargs.get('details', {}),
                source='seerrbridge'
            )
        except Exception as e:
            # Only print debug info if it's not a connection error
            if "Access denied" not in str(e) and "OperationalError" not in str(e):
                print(f"Database logging failed for warning: {e}")

def log_error(title: str, message: str, **kwargs):
    """Log error message"""
    logger.error(f"{title}: {message}")
    # Also log to database directly
    if USE_DATABASE:
        try:
            log_to_database(
                level='error',
                title=title,
                message=message,
                module=kwargs.get('module'),
                function=kwargs.get('function'),
                line_number=kwargs.get('line_number'),
                details=kwargs.get('details', {}),
                source='seerrbridge'
            )
        except Exception as e:
            # Only print debug info if it's not a connection error
            if "Access denied" not in str(e) and "OperationalError" not in str(e):
                print(f"Database logging failed for error: {e}")

def log_critical(title: str, message: str, **kwargs):
    """Log critical message"""
    logger.critical(f"{title}: {message}")
    # Also log to database directly
    if USE_DATABASE:
        try:
            log_to_database(
                level='critical',
                title=title,
                message=message,
                module=kwargs.get('module'),
                function=kwargs.get('function'),
                line_number=kwargs.get('line_number'),
                details=kwargs.get('details', {}),
                source='seerrbridge'
            )
        except Exception as e:
            # Only print debug info if it's not a connection error
            if "Access denied" not in str(e) and "OperationalError" not in str(e):
                print(f"Database logging failed for critical: {e}")

def log_debug(title: str, message: str, **kwargs):
    """Log debug message (disabled in production)"""
    # Debug logging disabled for production
    pass

# Function to get recent logs from database
def get_recent_logs(limit: int = 100, level: str = None, processed: bool = None):
    """Get recent log entries from database"""
    if not USE_DATABASE:
        return []
    
    try:
        return get_db().query(LogEntry).filter(
            LogEntry.level == level if level else True,
            LogEntry.processed == processed if processed is not None else True
        ).order_by(LogEntry.timestamp.desc()).limit(limit).all()
    except Exception as e:
        logger.error(f"Error getting recent logs from database: {e}")
        return []

# Function to mark logs as processed
def mark_logs_processed(log_ids: list, processed: bool = True):
    """Mark logs as processed"""
    if not USE_DATABASE or not log_ids:
        return False
    
    try:
        db = get_db()
        db.query(LogEntry).filter(LogEntry.id.in_(log_ids)).update({
            'processed': processed
        })
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Error marking logs as processed: {e}")
        return False

# Function to get log statistics
def get_log_statistics():
    """Get log statistics from database"""
    if not USE_DATABASE:
        return {}
    
    try:
        db = get_db()
        stats = {}
        
        # Count by level
        for level in ['success', 'error', 'warning', 'info', 'critical']:
            count = db.query(LogEntry).filter(LogEntry.level == level).count()
            stats[f'{level}_count'] = count
        
        # Total count
        stats['total_count'] = db.query(LogEntry).count()
        
        # Recent activity (last 24 hours)
        from datetime import datetime, timedelta
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_count = db.query(LogEntry).filter(LogEntry.timestamp >= yesterday).count()
        stats['recent_count'] = recent_count
        
        return stats
    except Exception as e:
        logger.error(f"Error getting log statistics: {e}")
        return {}

# Export the logger instance and functions
__all__ = [
    'db_logger', 'log_info', 'log_success', 'log_warning', 'log_error', 
    'log_critical', 'log_debug', 'get_recent_logs', 'mark_logs_processed', 
    'get_log_statistics'
]
