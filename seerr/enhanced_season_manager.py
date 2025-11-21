"""
Enhanced Season Management System
Handles multi-season TV show tracking with discrepancy detection
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
import logging
from seerr.database import get_db
from seerr.unified_models import UnifiedMedia

logger = logging.getLogger(__name__)

class SeasonDiscrepancyType:
    """Types of season discrepancies"""
    EPISODE_COUNT_MISMATCH = "episode_count_mismatch"
    AIRED_EPISODES_MISMATCH = "aired_episodes_mismatch"
    MISSING_EPISODES = "missing_episodes"
    EXTRA_EPISODES = "extra_episodes"
    PROCESSING_FAILED = "processing_failed"
    NO_DATA_AVAILABLE = "no_data_available"

class EnhancedSeasonManager:
    """Enhanced season management with discrepancy detection"""
    
    @staticmethod
    def create_enhanced_season_data(
        season_number: int,
        episode_count: int = 0,
        aired_episodes: int = 0,
        confirmed_episodes: List[str] = None,
        failed_episodes: List[str] = None,
        unprocessed_episodes: List[str] = None,
        is_discrepant: bool = False,
        discrepancy_reason: str = None,
        discrepancy_details: Dict[str, Any] = None,
        last_checked: str = None,
        updated_at: str = None
    ) -> Dict[str, Any]:
        """
        Create enhanced season data structure with discrepancy tracking
        
        Args:
            season_number: Season number
            episode_count: Total episodes in season
            aired_episodes: Episodes that have aired
            confirmed_episodes: List of confirmed episode IDs
            failed_episodes: List of failed episode IDs
            unprocessed_episodes: List of unprocessed episode IDs
            is_discrepant: Whether this season has discrepancies
            discrepancy_reason: Reason for discrepancy
            discrepancy_details: Additional discrepancy information
            last_checked: Last time this season was checked
            updated_at: Last update timestamp
            
        Returns:
            Enhanced season data dictionary
        """
        if confirmed_episodes is None:
            confirmed_episodes = []
        if failed_episodes is None:
            failed_episodes = []
        if unprocessed_episodes is None:
            unprocessed_episodes = []
        if discrepancy_details is None:
            discrepancy_details = {}
            
        now = datetime.utcnow().isoformat()
        
        return {
            'season_number': season_number,
            'episode_count': episode_count,
            'aired_episodes': aired_episodes,
            'confirmed_episodes': confirmed_episodes,
            'failed_episodes': failed_episodes,
            'unprocessed_episodes': unprocessed_episodes,
            'is_discrepant': is_discrepant,
            'discrepancy_reason': discrepancy_reason,
            'discrepancy_details': discrepancy_details,
            'last_checked': last_checked or now,
            'updated_at': updated_at or now,
            'status': EnhancedSeasonManager._calculate_season_status(
                episode_count, aired_episodes, confirmed_episodes, 
                failed_episodes, unprocessed_episodes, is_discrepant
            )
        }
    
    @staticmethod
    def _calculate_season_status(
        episode_count: int,
        aired_episodes: int,
        confirmed_episodes: List[str],
        failed_episodes: List[str],
        unprocessed_episodes: List[str],
        is_discrepant: bool
    ) -> str:
        """Calculate season status based on episode data"""
        if is_discrepant:
            return 'discrepant'
        
        if aired_episodes == 0:
            return 'not_aired'
        
        total_processed = len(confirmed_episodes) + len(failed_episodes)
        if total_processed >= aired_episodes:
            if len(failed_episodes) == 0:
                return 'completed'
            else:
                return 'partial'
        else:
            return 'processing'
    
    @staticmethod
    def detect_season_discrepancy(
        season_data: Dict[str, Any],
        trakt_episode_count: int = None,
        trakt_aired_episodes: int = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Detect discrepancies in season data
        
        Args:
            season_data: Current season data
            trakt_episode_count: Episode count from Trakt API
            trakt_aired_episodes: Aired episodes from Trakt API
            
        Returns:
            Tuple of (is_discrepant, reason, details)
        """
        discrepancies = []
        details = {}
        
        # Check episode count mismatch
        if trakt_episode_count is not None:
            current_episode_count = season_data.get('episode_count', 0)
            if current_episode_count != trakt_episode_count:
                discrepancies.append(SeasonDiscrepancyType.EPISODE_COUNT_MISMATCH)
                details['episode_count_mismatch'] = {
                    'current': current_episode_count,
                    'trakt': trakt_episode_count,
                    'difference': trakt_episode_count - current_episode_count
                }
        
        # Check aired episodes mismatch
        if trakt_aired_episodes is not None:
            current_aired_episodes = season_data.get('aired_episodes', 0)
            if current_aired_episodes != trakt_aired_episodes:
                discrepancies.append(SeasonDiscrepancyType.AIRED_EPISODES_MISMATCH)
                details['aired_episodes_mismatch'] = {
                    'current': current_aired_episodes,
                    'trakt': trakt_aired_episodes,
                    'difference': trakt_aired_episodes - current_aired_episodes
                }
        
        # Check for data inconsistencies (discrepancies)
        aired_episodes = season_data.get('aired_episodes', 0)
        episode_count = season_data.get('episode_count', 0)
        confirmed_episodes = season_data.get('confirmed_episodes', [])
        failed_episodes = season_data.get('failed_episodes', [])
        unprocessed_episodes = season_data.get('unprocessed_episodes', [])
        
        # A season is ONLY discrepant if there's a data inconsistency
        # In-progress shows (aired_episodes < episode_count) are NOT discrepancies
        # That's what TV show subscriptions handle now
        # Only mark as discrepant if aired_episodes > episode_count (data error)
        if aired_episodes > episode_count and episode_count > 0:
            discrepancies.append(SeasonDiscrepancyType.EPISODE_COUNT_MISMATCH)
            details['aired_too_many'] = {
                'count': aired_episodes,
                'expected': episode_count,
                'extra': aired_episodes - episode_count
            }
        
        is_discrepant = len(discrepancies) > 0
        reason = ', '.join(discrepancies) if discrepancies else None
        
        return is_discrepant, reason, details
    
    @staticmethod
    def update_tv_show_seasons(
        tmdb_id: int,
        seasons_data: List[Dict[str, Any]],
        title: str
    ) -> bool:
        """
        Update TV show with enhanced season data
        
        Args:
            tmdb_id: TMDB ID of the TV show
            seasons_data: List of enhanced season data
            title: TV show title for logging
            
        Returns:
            True if successful
        """
        try:
            db = get_db()
            
            # Get the TV show record
            tv_show = db.query(UnifiedMedia).filter(
                UnifiedMedia.tmdb_id == tmdb_id,
                UnifiedMedia.media_type == 'tv'
            ).first()
            
            if not tv_show:
                logger.error(f"No TV show record found for {title} (TMDB ID: {tmdb_id})")
                return False
            
            # Get existing seasons data to merge with new data
            existing_seasons_data = tv_show.seasons_data or []
            existing_season_numbers = {season.get('season_number', 0) for season in existing_seasons_data}
            
            # Create a map of existing seasons for easy lookup
            existing_seasons_map = {season.get('season_number', 0): season for season in existing_seasons_data}
            
            # Process new seasons and detect discrepancies
            processed_seasons = []
            discrepant_seasons = []
            completed_seasons = []
            failed_seasons = []
            
            # Process incoming seasons data
            for season_data in seasons_data:
                season_number = season_data.get('season_number', 0)
                
                # Check if is_discrepant is manually set (for fallback processing)
                manually_set_discrepant = season_data.get('is_discrepant', False)
                manually_set_reason = season_data.get('discrepancy_reason', None)
                
                if manually_set_discrepant and manually_set_reason:
                    # Use manually set discrepancy info (for fallback processing)
                    is_discrepant = manually_set_discrepant
                    discrepancy_reason = manually_set_reason
                    discrepancy_details = season_data.get('discrepancy_details', {})
                    logger.info(f"Using manually set discrepancy info for Season {season_number}: {discrepancy_reason}")
                else:
                    # Detect discrepancies automatically
                    is_discrepant, discrepancy_reason, discrepancy_details = EnhancedSeasonManager.detect_season_discrepancy(season_data)
                
                # Update season data with discrepancy info
                enhanced_season = EnhancedSeasonManager.create_enhanced_season_data(
                    season_number=season_number,
                    episode_count=season_data.get('episode_count', 0),
                    aired_episodes=season_data.get('aired_episodes', 0),
                    confirmed_episodes=season_data.get('confirmed_episodes', []),
                    failed_episodes=season_data.get('failed_episodes', []),
                    unprocessed_episodes=season_data.get('unprocessed_episodes', []),
                    is_discrepant=is_discrepant,
                    discrepancy_reason=discrepancy_reason,
                    discrepancy_details=discrepancy_details,
                    last_checked=season_data.get('last_checked'),
                    updated_at=season_data.get('updated_at')
                )
                
                processed_seasons.append(enhanced_season)
                
                # Track season status
                if is_discrepant:
                    discrepant_seasons.append(season_number)
                
                status = enhanced_season.get('status', 'unknown')
                if status == 'completed':
                    completed_seasons.append(season_number)
                elif status == 'discrepant' or 'failed' in status:
                    failed_seasons.append(season_number)
            
            # Merge with existing seasons that are not being updated
            incoming_season_numbers = {s.get('season_number', 0) for s in processed_seasons}
            for existing_season_number, existing_season in existing_seasons_map.items():
                if existing_season_number not in incoming_season_numbers:
                    # This existing season is not being updated, preserve it
                    processed_seasons.append(existing_season)
                    logger.info(f"Preserved existing season {existing_season_number} data for {title}")
            
            # Sort seasons by season number
            processed_seasons.sort(key=lambda x: x.get('season_number', 0))
            
            # Generate seasons processing string
            season_numbers = [s.get('season_number', 0) for s in processed_seasons]
            seasons_processing = EnhancedSeasonManager.generate_seasons_processing_string(season_numbers)
            
            # Update the record
            tv_show.seasons_data = processed_seasons
            tv_show.total_seasons = len(processed_seasons)
            tv_show.seasons_processing = seasons_processing
            tv_show.seasons_discrepant = discrepant_seasons
            tv_show.seasons_completed = completed_seasons
            tv_show.seasons_failed = failed_seasons
            tv_show.updated_at = datetime.utcnow()
            
            db.commit()
            
            logger.info(f"Updated {title} with {len(processed_seasons)} seasons (merged with existing data). "
                       f"Discrepant: {len(discrepant_seasons)}, "
                       f"Completed: {len(completed_seasons)}, "
                       f"Failed: {len(failed_seasons)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating seasons for {title} (TMDB ID: {tmdb_id}): {e}")
            if 'db' in locals():
                db.rollback()
            return False
        finally:
            if 'db' in locals():
                db.close()
    
    @staticmethod
    def generate_seasons_processing_string(season_numbers: List[int]) -> str:
        """
        Generate a seasons processing string from season numbers
        
        Args:
            season_numbers: List of season numbers
            
        Returns:
            String representation (e.g., "1,2,3" or "1-5")
        """
        if not season_numbers:
            return ""
        
        # Sort and remove duplicates
        season_numbers = sorted(list(set(season_numbers)))
        
        if len(season_numbers) <= 2:
            return ",".join(map(str, season_numbers))
        
        # Create ranges for consecutive seasons
        ranges = []
        start = season_numbers[0]
        end = start
        
        for i in range(1, len(season_numbers)):
            if season_numbers[i] == season_numbers[i-1] + 1:
                end = season_numbers[i]
            else:
                if start == end:
                    ranges.append(str(start))
                else:
                    ranges.append(f"{start}-{end}")
                start = season_numbers[i]
                end = start
        
        # Add the last range
        if start == end:
            ranges.append(str(start))
        else:
            ranges.append(f"{start}-{end}")
        
        return ",".join(ranges)
    
    @staticmethod
    def get_season_summary(tmdb_id: int) -> Dict[str, Any]:
        """
        Get summary of season data for a TV show
        
        Args:
            tmdb_id: TMDB ID of the TV show
            
        Returns:
            Season summary dictionary
        """
        try:
            db = get_db()
            
            tv_show = db.query(UnifiedMedia).filter(
                UnifiedMedia.tmdb_id == tmdb_id,
                UnifiedMedia.media_type == 'tv'
            ).first()
            
            if not tv_show:
                return {}
            
            seasons_data = tv_show.seasons_data or []
            
            summary = {
                'total_seasons': tv_show.total_seasons or 0,
                'seasons_processing': tv_show.seasons_processing or '',
                'seasons_discrepant': tv_show.seasons_discrepant or [],
                'seasons_completed': tv_show.seasons_completed or [],
                'seasons_failed': tv_show.seasons_failed or [],
                'seasons': []
            }
            
            for season in seasons_data:
                season_summary = {
                    'season_number': season.get('season_number', 0),
                    'episode_count': season.get('episode_count', 0),
                    'aired_episodes': season.get('aired_episodes', 0),
                    'confirmed_episodes': len(season.get('confirmed_episodes', [])),
                    'failed_episodes': len(season.get('failed_episodes', [])),
                    'unprocessed_episodes': len(season.get('unprocessed_episodes', [])),
                    'is_discrepant': season.get('is_discrepant', False),
                    'discrepancy_reason': season.get('discrepancy_reason'),
                    'status': season.get('status', 'unknown'),
                    'last_checked': season.get('last_checked'),
                    'updated_at': season.get('updated_at')
                }
                summary['seasons'].append(season_summary)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting season summary for TMDB ID {tmdb_id}: {e}")
            return {}
        finally:
            if 'db' in locals():
                db.close()
