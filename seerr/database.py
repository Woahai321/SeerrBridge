"""
Database configuration and models for SeerrBridge
Handles MySQL database connection and SQLAlchemy models
"""

import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Float, JSON, ForeignKey, Index, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.dialects.mysql import LONGTEXT
from loguru import logger

# Database configuration
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '3306')
DB_NAME = os.getenv('DB_NAME', 'seerrbridge')
DB_USER = os.getenv('DB_USER', 'seerrbridge')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'seerrbridge')

# Create database URL
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False  # Set to True for SQL debugging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

class LogEntry(Base):
    """Log entries table"""
    __tablename__ = "log_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    level = Column(String(20), nullable=False, index=True)  # success, error, warning, info, critical
    module = Column(String(100), nullable=True, index=True)
    function = Column(String(100), nullable=True)
    line_number = Column(Integer, nullable=True)
    title = Column(String(500), nullable=False)
    message = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)
    source = Column(String(100), nullable=True, index=True)
    processed = Column(Boolean, default=False, index=True)
    notification_sent = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_level_timestamp', 'level', 'timestamp'),
        Index('idx_processed_timestamp', 'processed', 'timestamp'),
        Index('idx_notification_timestamp', 'notification_sent', 'timestamp'),
    )

class LogType(Base):
    """Log type configuration table"""
    __tablename__ = "log_types"
    
    id = Column(String(50), primary_key=True)
    name = Column(String(200), nullable=False)
    pattern = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    level = Column(String(20), nullable=False)  # success, error, warning, info, critical
    selected_words = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class LogDisplay(Base):
    """Log display configuration table"""
    __tablename__ = "log_displays"
    
    id = Column(String(50), primary_key=True)
    log_type_id = Column(String(50), ForeignKey('log_types.id'), nullable=False)
    location = Column(JSON, nullable=False)  # Array of locations or "all"
    show_notification = Column(Boolean, default=False)
    show_in_card = Column(Boolean, default=True)
    trigger_stat_update = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    log_type = relationship("LogType", back_populates="displays")

class NotificationHistory(Base):
    """Notification history table"""
    __tablename__ = "notification_history"
    
    id = Column(String(50), primary_key=True)
    type = Column(String(20), nullable=False, index=True)  # success, error, warning
    title = Column(String(500), nullable=False)
    message = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)
    successful = Column(Boolean, default=False, index=True)
    viewed = Column(Boolean, default=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_type_timestamp', 'type', 'timestamp'),
        Index('idx_viewed_timestamp', 'viewed', 'timestamp'),
        Index('idx_successful_timestamp', 'successful', 'timestamp'),
    )

class NotificationSettings(Base):
    """Notification settings table"""
    __tablename__ = "notification_settings"
    
    id = Column(Integer, primary_key=True)
    discord_webhook_url = Column(Text, nullable=True)
    notify_on_success = Column(Boolean, default=True)
    notify_on_error = Column(Boolean, default=True)
    notify_on_warning = Column(Boolean, default=True)
    show_debug_widget = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class LibraryStats(Base):
    """Library statistics table"""
    __tablename__ = "library_stats"
    
    id = Column(Integer, primary_key=True)
    torrents_count = Column(Integer, nullable=False, default=0)
    total_size_tb = Column(Float, nullable=False, default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

class TokenStatus(Base):
    """Token status tracking table"""
    __tablename__ = "token_status"
    
    id = Column(Integer, primary_key=True)
    token_type = Column(String(50), nullable=False, index=True)  # rd_access, rd_refresh, etc.
    token_value = Column(Text, nullable=False)
    expires_at = Column(DateTime, nullable=True, index=True)
    last_refreshed = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class QueueStatus(Base):
    """Queue status tracking table"""
    __tablename__ = "queue_status"
    
    id = Column(Integer, primary_key=True)
    queue_type = Column(String(20), nullable=False, index=True)  # movie, tv
    queue_size = Column(Integer, nullable=False, default=0)
    max_size = Column(Integer, nullable=False, default=250)
    is_processing = Column(Boolean, default=False, index=True)
    last_activity = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Import the UnifiedMedia class from unified_models
from seerr.unified_models import UnifiedMedia

class SystemConfig(Base):
    """System configuration table"""
    __tablename__ = "system_config"
    
    id = Column(Integer, primary_key=True)
    config_key = Column(String(100), nullable=False, unique=True, index=True)
    config_value = Column(Text, nullable=True)
    config_type = Column(String(20), nullable=False, default='string')  # string, int, float, bool, json
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ServiceStatus(Base):
    """Service status table for real-time status updates"""
    __tablename__ = "service_status"
    
    id = Column(Integer, primary_key=True)
    service_name = Column(String(50), nullable=False, unique=True, index=True)
    status = Column(String(20), nullable=False, default='unknown', index=True)
    version = Column(String(50), nullable=True)
    uptime_seconds = Column(Integer, default=0)
    uptime_string = Column(String(100), nullable=True)
    start_time = Column(DateTime, nullable=True)
    current_time_value = Column(DateTime, nullable=True)
    queue_status = Column(JSON, nullable=True)
    browser_status = Column(String(50), nullable=True)
    automatic_processing = Column(Boolean, default=False)
    show_subscription = Column(Boolean, default=False)
    refresh_interval_minutes = Column(Float, default=30.0)
    library_stats = Column(JSON, nullable=True)
    queue_activity = Column(JSON, nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# Add relationships
LogType.displays = relationship("LogDisplay", back_populates="log_type")

def get_db() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        return db
    finally:
        pass  # Don't close here, let the caller handle it

def create_tables():
    """Create all tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise

def drop_tables():
    """Drop all tables"""
    try:
        Base.metadata.drop_all(bind=engine)
        logger.info("Database tables dropped successfully")
    except Exception as e:
        logger.error(f"Error dropping database tables: {e}")
        raise

def init_database():
    """Initialize database with default data"""
    db = get_db()
    try:
        # Create tables
        create_tables()
        
        # Insert default notification settings if none exist
        existing_settings = db.query(NotificationSettings).first()
        if not existing_settings:
            default_settings = NotificationSettings(
                discord_webhook_url=None,
                notify_on_success=True,
                notify_on_error=True,
                notify_on_warning=True,
                show_debug_widget=False
            )
            db.add(default_settings)
            db.commit()
            logger.info("Default notification settings created")
        
        # Insert default system config if none exist
        existing_config = db.query(SystemConfig).first()
        if not existing_config:
            default_configs = [
                SystemConfig(config_key="refresh_interval_minutes", config_value="60", config_type="int", description="Background task refresh interval in minutes"),
                SystemConfig(config_key="headless_mode", config_value="true", config_type="bool", description="Run browser in headless mode"),
                SystemConfig(config_key="enable_automatic_background_task", config_value="false", config_type="bool", description="Enable automatic background processing"),
                SystemConfig(config_key="enable_show_subscription_task", config_value="false", config_type="bool", description="Enable TV show subscription monitoring"),
            ]
            for config in default_configs:
                db.add(config)
            db.commit()
            logger.info("Default system configuration created")
        
        logger.info("Database initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        db.rollback()
        raise
    finally:
        db.close()

# Database utility functions
def log_to_database(level: str, title: str, message: str, module: str = None, 
                   function: str = None, line_number: int = None, 
                   details: Dict[str, Any] = None, source: str = None):
    """Log entry to database"""
    db = get_db()
    try:
        log_entry = LogEntry(
            level=level,
            module=module,
            function=function,
            line_number=line_number,
            title=title,
            message=message,
            details=details,
            source=source
        )
        db.add(log_entry)
        db.commit()
        return log_entry.id
    except Exception as e:
        # Use print to avoid recursion when logging database errors
        print(f"Error logging to database: {e}")
        db.rollback()
        return None
    finally:
        db.close()

def get_recent_logs(limit: int = 100, level: str = None, processed: bool = None):
    """Get recent log entries"""
    db = get_db()
    try:
        query = db.query(LogEntry)
        if level:
            query = query.filter(LogEntry.level == level)
        if processed is not None:
            query = query.filter(LogEntry.processed == processed)
        
        return query.order_by(LogEntry.timestamp.desc()).limit(limit).all()
    except Exception as e:
        # Use print to avoid recursion when logging database errors
        print(f"Error getting recent logs: {e}")
        return []
    finally:
        db.close()

def update_log_processed(log_id: int, processed: bool = True, notification_sent: bool = None):
    """Update log entry processed status"""
    db = get_db()
    try:
        log_entry = db.query(LogEntry).filter(LogEntry.id == log_id).first()
        if log_entry:
            log_entry.processed = processed
            if notification_sent is not None:
                log_entry.notification_sent = notification_sent
            db.commit()
            return True
        return False
    except Exception as e:
        # Use print to avoid recursion when logging database errors
        print(f"Error updating log processed status: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def update_service_status(service_name: str, status_data: Dict[str, Any]) -> bool:
    """Update service status in database"""
    db = get_db()
    try:
        # Try to find existing record
        service_status = db.query(ServiceStatus).filter(ServiceStatus.service_name == service_name).first()
        
        if service_status:
            # Update existing record
            service_status.status = status_data.get('status', 'unknown')
            service_status.version = status_data.get('version')
            service_status.uptime_seconds = int(status_data.get('uptime_seconds', 0))
            service_status.uptime_string = status_data.get('uptime', '0s')
            service_status.start_time = status_data.get('start_time')
            service_status.current_time_value = status_data.get('current_time')
            service_status.queue_status = status_data.get('queue_status')
            service_status.browser_status = status_data.get('browser_status')
            # Ensure boolean values are properly converted
            automatic_processing = status_data.get('automatic_processing', False)
            if isinstance(automatic_processing, str):
                automatic_processing = automatic_processing.lower() == 'true'
            service_status.automatic_processing = automatic_processing
            
            show_subscription = status_data.get('show_subscription', False)
            if isinstance(show_subscription, str):
                show_subscription = show_subscription.lower() == 'true'
            service_status.show_subscription = show_subscription
            
            service_status.refresh_interval_minutes = status_data.get('refresh_interval_minutes', 30.0)
            service_status.library_stats = status_data.get('library_stats')
            service_status.queue_activity = status_data.get('queue_activity')
        else:
            # Create new record
            # Ensure boolean values are properly converted
            automatic_processing = status_data.get('automatic_processing', False)
            if isinstance(automatic_processing, str):
                automatic_processing = automatic_processing.lower() == 'true'
            
            show_subscription = status_data.get('show_subscription', False)
            if isinstance(show_subscription, str):
                show_subscription = show_subscription.lower() == 'true'
            
            service_status = ServiceStatus(
                service_name=service_name,
                status=status_data.get('status', 'unknown'),
                version=status_data.get('version'),
                uptime_seconds=int(status_data.get('uptime_seconds', 0)),
                uptime_string=status_data.get('uptime', '0s'),
                start_time=status_data.get('start_time'),
                current_time_value=status_data.get('current_time'),
                queue_status=status_data.get('queue_status'),
                browser_status=status_data.get('browser_status'),
                automatic_processing=automatic_processing,
                show_subscription=show_subscription,
                refresh_interval_minutes=status_data.get('refresh_interval_minutes', 30.0),
                library_stats=status_data.get('library_stats'),
                queue_activity=status_data.get('queue_activity')
            )
            db.add(service_status)
        
        db.commit()
        return True
    except Exception as e:
        # Use print to avoid recursion when logging database errors
        print(f"Error updating service status: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def get_service_status(service_name: str) -> Optional[ServiceStatus]:
    """Get service status from database"""
    db = get_db()
    try:
        return db.query(ServiceStatus).filter(ServiceStatus.service_name == service_name).first()
    except Exception as e:
        logger.error(f"Error getting service status: {e}")
        return None
    finally:
        db.close()
