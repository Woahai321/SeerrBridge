"""
Unified Media Models
This module contains the new unified media tracking models that replace
all fragmented media tables with a single, comprehensive system.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON, LargeBinary, DECIMAL, Enum, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from typing import Optional, Dict, Any, List

Base = declarative_base()

class UnifiedMedia(Base):
    """
    Unified media tracking table that consolidates all media data.
    This replaces: media_requests, processed_media, show_subscriptions, etc.
    """
    __tablename__ = "unified_media"
    
    # Primary identification
    id = Column(Integer, primary_key=True)
    
    # External service IDs (all optional, indexed for lookups)
    tmdb_id = Column(Integer, nullable=True, index=True)
    imdb_id = Column(String(20), nullable=True, index=True)
    trakt_id = Column(String(20), nullable=True, index=True)
    overseerr_media_id = Column(Integer, nullable=True, index=True)
    overseerr_request_id = Column(Integer, nullable=True, index=True)
    
    # Media identification
    media_type = Column(Enum('movie', 'tv', name='media_type_enum'), nullable=False)
    title = Column(String(500), nullable=False)
    year = Column(Integer, nullable=True)
    overview = Column(Text, nullable=True)
    
    # Legacy single-season fields have been removed from the database
    # All TV show season tracking now uses the enhanced multi-season system below
    
    # Enhanced TV Show Multi-Season System
    total_seasons = Column(Integer, nullable=True, default=0)  # Total number of seasons for this TV show
    seasons_data = Column(JSON, nullable=True)  # Enhanced season tracking with discrepancy detection
    seasons_processing = Column(String(500), nullable=True)  # String representation of seasons being processed (e.g., "1,2,3" or "1-5")
    seasons_discrepant = Column(JSON, nullable=True)  # Array of season numbers that have discrepancies
    seasons_completed = Column(JSON, nullable=True)   # Array of season numbers that are fully completed
    seasons_failed = Column(JSON, nullable=True)      # Array of season numbers that have failed processing
    
    # Request tracking
    requested_by = Column(String(200), nullable=True)
    requested_at = Column(DateTime, nullable=True)
    first_requested_at = Column(DateTime, nullable=True)  # First time this media was requested
    last_requested_at = Column(DateTime, nullable=True)   # Most recent request
    request_count = Column(Integer, nullable=False, default=1)  # Total number of requests
    
    # Processing status (unified)
    status = Column(Enum('pending', 'processing', 'completed', 'failed', 'skipped', 'cancelled', 'ignored', 'unreleased', name='status_enum'), 
                   nullable=False, default='pending', index=True)
    processing_stage = Column(String(50), nullable=True, index=True)  # browser_automation, search_complete, etc.
    processing_started_at = Column(DateTime, nullable=True)
    processing_completed_at = Column(DateTime, nullable=True)
    last_checked_at = Column(DateTime, nullable=True)
    
    # Release date tracking (for movies and TV shows)
    released_date = Column(DateTime, nullable=True, index=True)  # Release date from Trakt API
    
    # Subscription tracking (for TV shows)
    is_subscribed = Column(Boolean, nullable=False, default=False, index=True)
    subscription_active = Column(Boolean, nullable=False, default=True, index=True)
    subscription_last_checked = Column(DateTime, nullable=True)
    
    # Search and torrent data
    torrents_found = Column(Integer, nullable=False, default=0)
    search_attempts = Column(Integer, nullable=False, default=0)
    last_search_at = Column(DateTime, nullable=True)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    error_count = Column(Integer, nullable=False, default=0)
    last_error_at = Column(DateTime, nullable=True)
    
    # Queue tracking
    is_in_queue = Column(Boolean, nullable=False, default=False, index=True)
    queue_added_at = Column(DateTime, nullable=True)
    queue_attempts = Column(Integer, nullable=False, default=0)
    
    # Media metadata
    genres = Column(JSON, nullable=True)           # Array of genre names
    runtime = Column(Integer, nullable=True)       # Runtime in minutes
    rating = Column(DECIMAL(3,1), nullable=True)   # Average rating
    vote_count = Column(Integer, nullable=True)    # Number of votes
    popularity = Column(DECIMAL(10,2), nullable=True) # Popularity score
    
    # Image URLs
    poster_url = Column(String(500), nullable=True)
    thumb_url = Column(String(500), nullable=True)
    fanart_url = Column(String(500), nullable=True)
    backdrop_url = Column(String(500), nullable=True)
    
    # Compressed image storage
    poster_image = Column(LargeBinary, nullable=True)
    poster_image_format = Column(String(10), nullable=True)
    poster_image_size = Column(Integer, nullable=True)
    thumb_image = Column(LargeBinary, nullable=True)
    thumb_image_format = Column(String(10), nullable=True)
    thumb_image_size = Column(Integer, nullable=True)
    fanart_image = Column(LargeBinary, nullable=True)
    fanart_image_format = Column(String(10), nullable=True)
    fanart_image_size = Column(Integer, nullable=True)
    backdrop_image = Column(LargeBinary, nullable=True)
    backdrop_image_format = Column(String(10), nullable=True)
    backdrop_image_size = Column(Integer, nullable=True)
    
    # Additional data
    extra_data = Column(JSON, nullable=True)       # Flexible field for any additional data
    tags = Column(JSON, nullable=True)            # User-defined tags
    notes = Column(Text, nullable=True)           # User notes
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_media_type_status', 'media_type', 'status'),
        Index('idx_tmdb_media_type', 'tmdb_id', 'media_type'),
        Index('idx_status_created', 'status', 'created_at'),
        Index('idx_subscription_active_checked', 'subscription_active', 'subscription_last_checked'),
        Index('idx_processing_stage_status', 'processing_stage', 'status'),
        Index('idx_requested_at', 'requested_at'),
        Index('idx_processing_started_at', 'processing_started_at'),
        Index('idx_processing_completed_at', 'processing_completed_at'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the model to a dictionary for API responses"""
        return {
            'id': self.id,
            'tmdb_id': self.tmdb_id,
            'imdb_id': self.imdb_id,
            'trakt_id': self.trakt_id,
            'overseerr_media_id': self.overseerr_media_id,
            'overseerr_request_id': self.overseerr_request_id,
            'media_type': self.media_type,
            'title': self.title,
            'year': self.year,
            'overview': self.overview,
            # Legacy single-season fields removed - use seasons_data instead
            'requested_by': self.requested_by,
            'requested_at': self.requested_at.isoformat() if self.requested_at else None,
            'first_requested_at': self.first_requested_at.isoformat() if self.first_requested_at else None,
            'last_requested_at': self.last_requested_at.isoformat() if self.last_requested_at else None,
            'request_count': self.request_count,
            'status': self.status,
            'processing_stage': self.processing_stage,
            'processing_started_at': self.processing_started_at.isoformat() if self.processing_started_at else None,
            'processing_completed_at': self.processing_completed_at.isoformat() if self.processing_completed_at else None,
            'last_checked_at': self.last_checked_at.isoformat() if self.last_checked_at else None,
            'is_subscribed': self.is_subscribed,
            'subscription_active': self.subscription_active,
            'subscription_last_checked': self.subscription_last_checked.isoformat() if self.subscription_last_checked else None,
            'torrents_found': self.torrents_found,
            'search_attempts': self.search_attempts,
            'last_search_at': self.last_search_at.isoformat() if self.last_search_at else None,
            'error_message': self.error_message,
            'error_count': self.error_count,
            'last_error_at': self.last_error_at.isoformat() if self.last_error_at else None,
            'genres': self.genres,
            'runtime': self.runtime,
            'rating': float(self.rating) if self.rating else None,
            'vote_count': self.vote_count,
            'popularity': float(self.popularity) if self.popularity else None,
            'released_date': self.released_date.isoformat() if self.released_date else None,
            'poster_url': self.poster_url,
            'thumb_url': self.thumb_url,
            'fanart_url': self.fanart_url,
            'backdrop_url': self.backdrop_url,
            'has_poster_image': self.poster_image is not None,
            'poster_image_format': self.poster_image_format,
            'poster_image_size': self.poster_image_size,
            'has_thumb_image': self.thumb_image is not None,
            'thumb_image_format': self.thumb_image_format,
            'thumb_image_size': self.thumb_image_size,
            'has_fanart_image': self.fanart_image is not None,
            'fanart_image_format': self.fanart_image_format,
            'fanart_image_size': self.fanart_image_size,
            'has_backdrop_image': self.backdrop_image is not None,
            'backdrop_image_format': self.backdrop_image_format,
            'backdrop_image_size': self.backdrop_image_size,
            'extra_data': self.extra_data,
            'tags': self.tags,
            'notes': self.notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def get_display_status(self) -> str:
        """Get a user-friendly display status"""
        if self.media_type == 'tv' and self.is_subscribed:
            # Calculate from seasons_data
            confirmed_count = 0
            aired_count = 0
            failed_count = 0
            
            if self.seasons_data:
                for season in self.seasons_data:
                    if isinstance(season, dict):
                        confirmed_count += len(season.get('confirmed_episodes', []))
                        aired_count += season.get('aired_episodes', 0)
                        failed_count += len(season.get('failed_episodes', []))
            
            if aired_count > 0 and confirmed_count >= aired_count:
                return 'completed'
            elif confirmed_count > 0:
                return f'{confirmed_count}/{aired_count}'
            elif failed_count > 0:
                return 'failed'
            elif self.status == 'processing':
                return 'processing'
            else:
                return 'pending'
        
        return self.status
    
    def get_progress_percentage(self) -> float:
        """Get progress percentage for TV shows"""
        if self.media_type != 'tv' or not self.seasons_data:
            return 0.0
        
        # Calculate from seasons_data
        confirmed_count = 0
        aired_count = 0
        
        for season in self.seasons_data:
            if isinstance(season, dict):
                confirmed_count += len(season.get('confirmed_episodes', []))
                aired_count += season.get('aired_episodes', 0)
        
        if aired_count > 0:
            return (confirmed_count / aired_count) * 100
        
        return 0.0
    
    def is_processing(self) -> bool:
        """Check if media is currently being processed"""
        return self.status == 'processing'
    
    def is_completed(self) -> bool:
        """Check if media processing is completed"""
        return self.status == 'completed'
    
    def is_failed(self) -> bool:
        """Check if media processing has failed"""
        return self.status == 'failed'
    
    def has_images(self) -> bool:
        """Check if media has any stored images"""
        return any([
            self.poster_image is not None,
            self.thumb_image is not None,
            self.fanart_image is not None,
            self.backdrop_image is not None
        ])

# Backward compatibility views (these would be created in the database)
# The views are defined in the SQL schema file for database creation
