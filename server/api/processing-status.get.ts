import { getDatabaseConnection } from '~/server/utils/database'

export default defineEventHandler(async (event) => {
  try {
    const db = await getDatabaseConnection()
    
    // Get currently processing items (status = 'processing')
    // Prioritize items with more specific processing stages and recent activity
    const [processingItems] = await db.execute(`
      SELECT 
        id, tmdb_id, imdb_id, trakt_id,
        media_type, title, year, overview,
        status, processing_stage, processing_started_at,
        last_checked_at, updated_at,
        poster_url, thumb_url, fanart_url, backdrop_url,
        poster_image_format, thumb_image_format, fanart_image_format, backdrop_image_format,
        seasons_processing, total_seasons, is_in_queue, queue_added_at
      FROM unified_media
      WHERE status = 'processing'
      ORDER BY 
        CASE 
          WHEN processing_stage LIKE 'browser_automation_season_%' THEN 0
          WHEN processing_stage = 'browser_automation' THEN 1
          WHEN processing_stage IS NOT NULL THEN 2
          ELSE 3
        END,
        COALESCE(last_checked_at, updated_at, processing_started_at) DESC
      LIMIT 10
    `)
    
    // Get queued items (is_in_queue = true but not processing)
    // Only include items that are actually in queue (pending or failed with retry eligibility)
    const [queuedItems] = await db.execute(`
      SELECT 
        id, tmdb_id, imdb_id, trakt_id,
        media_type, title, year, overview,
        status, processing_stage, processing_started_at,
        poster_url, thumb_url, fanart_url, backdrop_url,
        poster_image_format, thumb_image_format, fanart_image_format, backdrop_image_format,
        seasons_processing, total_seasons, is_in_queue, queue_added_at
      FROM unified_media
      WHERE is_in_queue = TRUE 
        AND status != 'processing'
        AND status != 'completed'
        AND status != 'ignored'
      ORDER BY queue_added_at ASC
      LIMIT 50
    `)
    
    // Get queue statistics from queue_status table (for max_size and is_processing)
    let queueStats = {
      movie_queue_size: 0,
      movie_queue_max: 250,
      tv_queue_size: 0,
      tv_queue_max: 250,
      total_queued: 0,
      is_processing: false
    }
    
    try {
      const [movieQueueStatus] = await db.execute(`
        SELECT queue_size, max_size, is_processing
        FROM queue_status
        WHERE queue_type = 'movie'
        LIMIT 1
      `)
      
      const [tvQueueStatus] = await db.execute(`
        SELECT queue_size, max_size, is_processing
        FROM queue_status
        WHERE queue_type = 'tv'
        LIMIT 1
      `)
      
      if (Array.isArray(movieQueueStatus) && movieQueueStatus.length > 0) {
        queueStats.movie_queue_max = movieQueueStatus[0]?.max_size || 250
        queueStats.is_processing = queueStats.is_processing || (movieQueueStatus[0]?.is_processing === 1)
      }
      
      if (Array.isArray(tvQueueStatus) && tvQueueStatus.length > 0) {
        queueStats.tv_queue_max = tvQueueStatus[0]?.max_size || 250
        queueStats.is_processing = queueStats.is_processing || (tvQueueStatus[0]?.is_processing === 1)
      }
    } catch (queueStatsError) {
      // If queue_status table doesn't exist, use defaults
      console.warn('Could not fetch queue stats from queue_status table:', queueStatsError)
    }
    
    // Note: queue_size values will be calculated from actual queuedItems below
    
    // Get processing statistics
    const [stats] = await db.execute(`
      SELECT 
        COUNT(*) as total_processing,
        SUM(CASE WHEN media_type = 'movie' THEN 1 ELSE 0 END) as movies_processing,
        SUM(CASE WHEN media_type = 'tv' THEN 1 ELSE 0 END) as tv_processing
      FROM unified_media
      WHERE status = 'processing'
    `)
    
    // Helper function to process items and add computed fields
    const processItem = (row: any) => {
      const item = { ...row }
      // Add computed fields (matching unified-media API pattern)
      item.has_poster_image = !!row.poster_image_format
      item.has_thumb_image = !!row.thumb_image_format
      item.has_fanart_image = !!row.fanart_image_format
      item.has_backdrop_image = !!row.backdrop_image_format
      return item
    }
    
    // Process items
    const processingItemsList = (Array.isArray(processingItems) ? processingItems : []).map(processItem)
    const queuedItemsList = (Array.isArray(queuedItems) ? queuedItems : []).map(processItem)
    
    // Clean up stale queue items (items marked as in_queue but shouldn't be)
    // This happens if items complete but is_in_queue wasn't cleared
    try {
      await db.execute(`
        UPDATE unified_media
        SET is_in_queue = FALSE, queue_added_at = NULL
        WHERE is_in_queue = TRUE 
          AND (status = 'completed' OR status = 'ignored')
      `)
    } catch (cleanupError) {
      console.warn('Error cleaning up stale queue items:', cleanupError)
    }
    
    // Combine all items for queuedItems (processing first, then queued)
    const allQueuedItems = [
      ...processingItemsList.map((item: any) => ({ ...item, queue_status: 'processing' })),
      ...queuedItemsList.map((item: any) => ({ ...item, queue_status: 'queued' }))
    ]
    
    // Calculate queueStats from actual queuedItems (source of truth)
    // This ensures the count matches what will be displayed
    const movieQueueSize = allQueuedItems.filter((item: any) => item.media_type === 'movie').length
    const tvQueueSize = allQueuedItems.filter((item: any) => item.media_type === 'tv').length
    const totalQueued = allQueuedItems.length
    
    // Update queueStats with calculated values from actual items
    queueStats.movie_queue_size = movieQueueSize
    queueStats.tv_queue_size = tvQueueSize
    queueStats.total_queued = totalQueued
    
    // Log discrepancy if queue_status table differs significantly from actual database state
    // This helps detect synchronization issues
    try {
      const [movieQueueStatus] = await db.execute(`
        SELECT queue_size
        FROM queue_status
        WHERE queue_type = 'movie'
        LIMIT 1
      `)
      
      const [tvQueueStatus] = await db.execute(`
        SELECT queue_size
        FROM queue_status
        WHERE queue_type = 'tv'
        LIMIT 1
      `)
      
      const dbMovieSize = (Array.isArray(movieQueueStatus) && movieQueueStatus.length > 0) ? (movieQueueStatus[0]?.queue_size || 0) : 0
      const dbTvSize = (Array.isArray(tvQueueStatus) && tvQueueStatus.length > 0) ? (tvQueueStatus[0]?.queue_size || 0) : 0
      
      if (Math.abs(dbMovieSize - movieQueueSize) > 2 || Math.abs(dbTvSize - tvQueueSize) > 2) {
        console.warn(`Queue synchronization discrepancy detected: queue_status table shows ${dbMovieSize} movies, ${dbTvSize} TV, but actual database has ${movieQueueSize} movies, ${tvQueueSize} TV`)
      }
    } catch (validationError) {
      // Ignore validation errors, not critical
      console.debug('Could not validate queue_status table:', validationError)
    }
    
    // Current item is the one actively being processed
    // Prioritize items with more specific processing stages (e.g., browser_automation_season_X)
    // and most recent activity (last_checked_at or updated_at)
    let currentItem = null
    
    // Helper function to get activity timestamp for sorting
    const getActivityTimestamp = (item: any): number => {
      const lastChecked = item.last_checked_at ? new Date(item.last_checked_at).getTime() : 0
      const updated = item.updated_at ? new Date(item.updated_at).getTime() : 0
      const started = item.processing_started_at ? new Date(item.processing_started_at).getTime() : 0
      return Math.max(lastChecked, updated, started)
    }
    
    // Helper function to get processing stage priority (lower = higher priority)
    const getStagePriority = (stage: string | null): number => {
      if (!stage) return 999
      if (stage.indexOf('browser_automation_season_') === 0) return 0
      if (stage === 'browser_automation') return 1
      if (stage.indexOf('browser_automation') === 0) return 2
      return 3
    }
    
    // Sort items by priority: more specific stages first, then by most recent activity
    const sortedItems = [...processingItemsList].sort((a, b) => {
      const priorityA = getStagePriority(a.processing_stage)
      const priorityB = getStagePriority(b.processing_stage)
      
      if (priorityA !== priorityB) {
        return priorityA - priorityB
      }
      
      // If same priority, sort by most recent activity
      const activityA = getActivityTimestamp(a)
      const activityB = getActivityTimestamp(b)
      return activityB - activityA
    })
    
    // Select the highest priority item (first in sorted list)
    if (sortedItems.length > 0) {
      currentItem = sortedItems[0]
    }
    
    // Calculate progress percentage for TV shows
    const calculateProgress = (item: any) => {
      if (item.media_type === 'tv' && item.seasons_processing && item.total_seasons) {
        const processing = parseInt(item.seasons_processing) || 0
        const total = parseInt(item.total_seasons) || 1
        return Math.round((processing / total) * 100)
      }
      return 0
    }
    
    // Format item for response
    const formatItem = (item: any) => ({
      id: item.id,
      tmdb_id: item.tmdb_id,
      title: item.title,
      year: item.year,
      media_type: item.media_type,
      processing_stage: item.processing_stage,
      processing_started_at: item.processing_started_at,
      queue_added_at: item.queue_added_at,
      has_poster_image: item.has_poster_image,
      has_thumb_image: item.has_thumb_image,
      has_fanart_image: item.has_fanart_image,
      seasons_processing: item.seasons_processing,
      total_seasons: item.total_seasons,
      progress_percentage: calculateProgress(item),
      queue_status: item.queue_status || (item.status === 'processing' ? 'processing' : 'queued')
    })
    
    return {
      success: true,
      data: {
        currentItem: currentItem ? formatItem({ ...currentItem, queue_status: 'processing' }) : null,
        queuedItems: allQueuedItems.map(formatItem),
        processingItems: processingItemsList.map(formatItem),
        stats: {
          total_processing: stats[0]?.total_processing || 0,
          movies_processing: stats[0]?.movies_processing || 0,
          tv_processing: stats[0]?.tv_processing || 0
        },
        queueStats
      }
    }
  } catch (error) {
    console.error('Error fetching processing status:', error)
    return {
      success: false,
      error: 'Failed to fetch processing status',
      data: {
        currentItem: null,
        queuedItems: [],
        processingItems: [],
        stats: {
          total_processing: 0,
          movies_processing: 0,
          tv_processing: 0
        },
        queueStats: {
          movie_queue_size: 0,
          movie_queue_max: 250,
          tv_queue_size: 0,
          tv_queue_max: 250,
          total_queued: 0,
          is_processing: false
        }
      }
    }
  }
})

