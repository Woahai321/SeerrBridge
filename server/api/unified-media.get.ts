import { getDatabaseConnection } from '~/server/utils/database'

export default defineEventHandler(async (event) => {
  try {
    const query = getQuery(event)
    // DO NOT log full query - may contain sensitive data
    console.debug('Unified media API called with query params:', Object.keys(query))
    
    const db = await getDatabaseConnection()
    if (!db) {
      throw new Error('Failed to get database connection')
    }
    
    // Parse query parameters
    const page = parseInt(query.page as string) || 1
    const limit = Math.min(parseInt(query.limit as string) || 50, 100) // Max 100 records
    const offset = (page - 1) * limit
    
    const status = query.status as string
    const mediaType = query.mediaType as string
    const search = query.search as string
    const sortBy = query.sortBy as string || 'updated_at'
    const sortOrder = query.sortOrder as string || 'DESC'
    const subscribed = query.subscribed as string
    
    // Build WHERE clause
    const whereConditions = []
    const params: any = {}
    
    if (status) {
      whereConditions.push('status = ?')
      params.status = status
    }
    
    if (mediaType) {
      whereConditions.push('media_type = ?')
      params.mediaType = mediaType
    }
    
    if (search) {
      whereConditions.push('(title LIKE ? OR overview LIKE ?)')
      params.search = `%${search}%`
    }
    
    if (subscribed === 'true') {
      whereConditions.push('is_subscribed = TRUE')
    }
    
    const whereClause = whereConditions.length > 0 
      ? `WHERE ${whereConditions.join(' AND ')}`
      : ''
    
    // Build ORDER BY clause
    const validSortColumns = [
      'id', 'title', 'year', 'status', 'media_type', 'created_at', 'updated_at',
      'requested_at', 'processing_started_at', 'processing_completed_at',
      'torrents_found', 'request_count', 'rating', 'popularity'
    ]
    
    const sortColumn = validSortColumns.includes(sortBy) ? sortBy : 'updated_at'
    const orderDirection = sortOrder.toUpperCase() === 'ASC' ? 'ASC' : 'DESC'
    const orderClause = `ORDER BY ${sortColumn} ${orderDirection}`
    
    // Get total count
    const countQuery = `
      SELECT COUNT(*) as total
      FROM unified_media
      ${whereClause}
    `
    
    // Build count params array (same order as data query but without limit/offset)
    const countParamValues = []
    if (status) countParamValues.push(status)
    if (mediaType) countParamValues.push(mediaType)
    if (search) {
      countParamValues.push(`%${search}%`)
      countParamValues.push(`%${search}%`) // For the second LIKE in the OR condition
    }
    
    const countResult = whereConditions.length > 0 
      ? await db.execute(countQuery, countParamValues)
      : await db.execute(countQuery, [])
    const total = (countResult as any)[0][0].total
    
    // Get paginated data
    const dataQuery = `
      SELECT 
        id, tmdb_id, imdb_id, trakt_id, overseerr_media_id, overseerr_request_id,
        media_type, title, year, overview,
        total_seasons, seasons_data, seasons_processing, seasons_discrepant, seasons_completed, seasons_failed,
        requested_by, requested_at, first_requested_at, last_requested_at, request_count,
        status, processing_stage, processing_started_at, processing_completed_at, last_checked_at,
        is_subscribed, subscription_active, subscription_last_checked,
        torrents_found, search_attempts, last_search_at,
        error_message, error_count, last_error_at,
        genres, runtime, rating, vote_count, popularity,
        poster_url, thumb_url, fanart_url, backdrop_url,
        poster_image_format, poster_image_size,
        thumb_image_format, thumb_image_size,
        fanart_image_format, fanart_image_size,
        backdrop_image_format, backdrop_image_size,
        extra_data, tags, notes,
        created_at, updated_at
      FROM unified_media
      ${whereClause}
      ${orderClause}
      LIMIT ${limit} OFFSET ${offset}
    `
    
    // Convert params object to array for positional binding
    const paramValues = []
    if (status) paramValues.push(status)
    if (mediaType) paramValues.push(mediaType)
    if (search) {
      paramValues.push(`%${search}%`)
      paramValues.push(`%${search}%`) // For the second LIKE in the OR condition
    }
    
    // Only pass parameters if there are WHERE conditions
    const dataResult = whereConditions.length > 0 
      ? await db.execute(dataQuery, paramValues)
      : await db.execute(dataQuery, [])
    
    // DO NOT log query results - may contain sensitive data
    console.debug('Database query executed, result length:', (dataResult as any)[0]?.length || 0)
    
    // Process the data to add computed fields
    const media = ((dataResult as any)[0] || []).map((row: any) => {
      if (!row) {
        console.warn('Empty row found in database result')
        return null
      }
      
      const mediaItem = { ...row }
      
      // Add computed fields
      mediaItem.has_poster_image = !!row.poster_image_format
      mediaItem.has_thumb_image = !!row.thumb_image_format
      mediaItem.has_fanart_image = !!row.fanart_image_format
      mediaItem.has_backdrop_image = !!row.backdrop_image_format
      
      // Add display status
      if (mediaItem.media_type === 'tv' && mediaItem.is_subscribed) {
        let confirmedCount = 0
        let failedCount = 0
        let airedCount = 0
        let totalSeasons = 0
        let completedSeasons = 0
        let processingSeasons = 0
        let failedSeasons = 0
        
        // Use enhanced seasons structure
        if (mediaItem.seasons_data && Array.isArray(mediaItem.seasons_data) && mediaItem.seasons_data.length > 0) {
          totalSeasons = mediaItem.seasons_data.length
          
          mediaItem.seasons_data.forEach((season: any) => {
            confirmedCount += season.confirmed_episodes?.length || 0
            failedCount += season.failed_episodes?.length || 0
            airedCount += season.aired_episodes || 0
            
            // Count season statuses
            if (season.status === 'completed') {
              completedSeasons++
            } else if (season.status === 'processing' || season.status === 'pending') {
              processingSeasons++
            } else if (season.status === 'failed') {
              failedSeasons++
            }
          })
        }
        
        // Calculate total episodes across all seasons (not just aired)
        let totalEpisodes = 0
        if (mediaItem.seasons_data && Array.isArray(mediaItem.seasons_data) && mediaItem.seasons_data.length > 0) {
          totalEpisodes = mediaItem.seasons_data.reduce((sum: number, season: any) => sum + (season.episode_count || 0), 0)
        }
        
        // Determine overall status based on season completion
        if (completedSeasons === totalSeasons && totalSeasons > 0) {
          // All seasons are completed
          mediaItem.display_status = 'completed'
        } else if (failedSeasons > 0) {
          // Any failed seasons
          mediaItem.display_status = 'failed'
        } else if (processingSeasons > 0) {
          // Some seasons are still processing
          mediaItem.display_status = 'processing'
        } else if (confirmedCount > 0 && totalEpisodes > 0) {
          // Show progress across ALL episodes (not just aired ones)
          mediaItem.display_status = `${confirmedCount}/${totalEpisodes}`
        } else if (mediaItem.status === 'processing') {
          mediaItem.display_status = 'processing'
        } else {
          mediaItem.display_status = 'pending'
        }
      } else {
        mediaItem.display_status = mediaItem.status
      }
      
      // Add progress percentage for TV shows
      if (mediaItem.media_type === 'tv') {
        let confirmedCount = 0
        let totalEpisodes = 0
        
        // Use enhanced seasons structure
        if (mediaItem.seasons_data && Array.isArray(mediaItem.seasons_data) && mediaItem.seasons_data.length > 0) {
          confirmedCount = mediaItem.seasons_data.reduce((sum: number, season: any) => sum + (season.confirmed_episodes?.length || 0), 0)
          totalEpisodes = mediaItem.seasons_data.reduce((sum: number, season: any) => sum + (season.episode_count || 0), 0)
        }
        
        if (totalEpisodes > 0) {
          mediaItem.progress_percentage = (confirmedCount / totalEpisodes) * 100
        } else {
          mediaItem.progress_percentage = 0
        }
      } else {
        mediaItem.progress_percentage = 0
      }
      
      // Parse JSON fields safely
      try {
        
        // Parse new multi-season data
        if (mediaItem.seasons_data && typeof mediaItem.seasons_data === 'string' && mediaItem.seasons_data.trim()) {
          mediaItem.seasons_data = JSON.parse(mediaItem.seasons_data)
        } else if (mediaItem.seasons_data && typeof mediaItem.seasons_data === 'object') {
          // Already parsed by MySQL driver
          mediaItem.seasons_data = mediaItem.seasons_data
        } else if (mediaItem.seasons_data === null || mediaItem.seasons_data === '') {
          mediaItem.seasons_data = []
        }
        
        // Parse enhanced season tracking fields
        if (mediaItem.seasons_discrepant && typeof mediaItem.seasons_discrepant === 'string' && mediaItem.seasons_discrepant.trim()) {
          mediaItem.seasons_discrepant = JSON.parse(mediaItem.seasons_discrepant)
        } else if (mediaItem.seasons_discrepant === null || mediaItem.seasons_discrepant === '') {
          mediaItem.seasons_discrepant = []
        }
        
        if (mediaItem.seasons_completed && typeof mediaItem.seasons_completed === 'string' && mediaItem.seasons_completed.trim()) {
          mediaItem.seasons_completed = JSON.parse(mediaItem.seasons_completed)
        } else if (mediaItem.seasons_completed === null || mediaItem.seasons_completed === '') {
          mediaItem.seasons_completed = []
        }
        
        if (mediaItem.seasons_failed && typeof mediaItem.seasons_failed === 'string' && mediaItem.seasons_failed.trim()) {
          mediaItem.seasons_failed = JSON.parse(mediaItem.seasons_failed)
        } else if (mediaItem.seasons_failed === null || mediaItem.seasons_failed === '') {
          mediaItem.seasons_failed = []
        }
        
        if (mediaItem.genres && typeof mediaItem.genres === 'string' && mediaItem.genres.trim()) {
          mediaItem.genres = JSON.parse(mediaItem.genres)
        } else if (mediaItem.genres === null || mediaItem.genres === '') {
          mediaItem.genres = []
        }
        
        if (mediaItem.extra_data && typeof mediaItem.extra_data === 'string' && mediaItem.extra_data.trim()) {
          mediaItem.extra_data = JSON.parse(mediaItem.extra_data)
        } else if (mediaItem.extra_data === null || mediaItem.extra_data === '') {
          mediaItem.extra_data = {}
        }
        
        if (mediaItem.tags && typeof mediaItem.tags === 'string' && mediaItem.tags.trim()) {
          mediaItem.tags = JSON.parse(mediaItem.tags)
        } else if (mediaItem.tags === null || mediaItem.tags === '') {
          mediaItem.tags = []
        }
      } catch (jsonError) {
        console.error('JSON parsing error for item:', mediaItem.id, jsonError)
        // Set safe defaults if parsing fails
        mediaItem.seasons_data = []
        mediaItem.seasons_discrepant = []
        mediaItem.seasons_completed = []
        mediaItem.seasons_failed = []
        mediaItem.genres = []
        mediaItem.extra_data = {}
        mediaItem.tags = []
      }
      
      // Create seasons array for TV shows using new multi-season structure
      if (mediaItem.media_type === 'tv') {
        let seasons = []
        
        // Use new enhanced seasons_data structure if available
        if (mediaItem.seasons_data && Array.isArray(mediaItem.seasons_data) && mediaItem.seasons_data.length > 0) {
          seasons = mediaItem.seasons_data.map((season: any) => ({
            season_number: season.season_number || 0,
            episode_count: season.episode_count || 0,
            aired_episodes: season.aired_episodes || 0,
            failed_episodes: season.failed_episodes || [],
            confirmed_episodes: season.confirmed_episodes || [],
            unprocessed_episodes: season.unprocessed_episodes || [],
            is_discrepant: season.is_discrepant || false,
            discrepancy_reason: season.discrepancy_reason || null,
            discrepancy_details: season.discrepancy_details || {},
            status: season.status || 'unknown',
            season_details: season,
            last_checked: season.last_checked,
            updated_at: season.updated_at || mediaItem.updated_at
          }))
        } else {
          // No season data available
          seasons = []
        }
        
        mediaItem.seasons = seasons
      }
      
      return mediaItem
    }).filter((item: any) => item !== null)
    
    // Get statistics directly from unified_media table
    // This ensures we're checking the actual database status, not just fetched results
    const statsQuery = `
      SELECT 
        COUNT(*) as total_media,
        COUNT(CASE WHEN media_type = 'movie' THEN 1 END) as total_movies,
        COUNT(CASE WHEN media_type = 'tv' THEN 1 END) as total_tv_shows,
        COUNT(CASE WHEN is_subscribed = TRUE THEN 1 END) as subscribed_count,
        COUNT(CASE WHEN created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR) THEN 1 END) as recent_activity_24h,
        -- Completed items: status = 'completed' in unified_media table
        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_count,
        COUNT(CASE WHEN status = 'completed' AND media_type = 'movie' THEN 1 END) as movies_completed,
        COUNT(CASE WHEN status = 'completed' AND media_type = 'tv' THEN 1 END) as tv_completed,
        -- Processing items: status = 'processing' in unified_media table
        COUNT(CASE WHEN status = 'processing' THEN 1 END) as processing_count,
        COUNT(CASE WHEN status = 'processing' AND media_type = 'movie' THEN 1 END) as movies_processing,
        COUNT(CASE WHEN status = 'processing' AND media_type = 'tv' THEN 1 END) as tv_processing,
        -- Failed items: status = 'failed' in unified_media table
        COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_count,
        COUNT(CASE WHEN status = 'failed' AND media_type = 'movie' THEN 1 END) as movies_failed,
        COUNT(CASE WHEN status = 'failed' AND media_type = 'tv' THEN 1 END) as tv_failed,
        -- Pending items: status = 'pending' in unified_media table
        COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_count
      FROM unified_media
      ${whereClause}
    `
    
    const statsResult = whereConditions.length > 0 
      ? await db.execute(statsQuery, countParamValues)
      : await db.execute(statsQuery, [])
    const baseStats = (statsResult as any)[0][0]
    
    // Use the database counts directly from unified_media table
    const completedCount = parseInt(baseStats.completed_count) || 0
    const processingCount = parseInt(baseStats.processing_count) || 0
    const failedCount = parseInt(baseStats.failed_count) || 0
    const pendingCount = parseInt(baseStats.pending_count) || 0
    const moviesCompleted = parseInt(baseStats.movies_completed) || 0
    const moviesProcessing = parseInt(baseStats.movies_processing) || 0
    const moviesFailed = parseInt(baseStats.movies_failed) || 0
    const tvCompleted = parseInt(baseStats.tv_completed) || 0
    const tvProcessing = parseInt(baseStats.tv_processing) || 0
    const tvFailed = parseInt(baseStats.tv_failed) || 0
    
    const stats = {
      ...baseStats,
      // Use database counts directly from unified_media table
      completed_count: completedCount,
      processing_count: processingCount,
      failed_count: failedCount,
      pending_count: pendingCount,
      movies_completed: moviesCompleted,
      movies_processing: moviesProcessing,
      movies_failed: moviesFailed,
      tv_completed: tvCompleted,
      tv_processing: tvProcessing,
      tv_failed: tvFailed
    }
    
    // Calculate status distribution using display_status
    const status_counts: Record<string, number> = {}
    media.forEach((mediaItem: any) => {
      const displayStatus = mediaItem.display_status || mediaItem.status
      status_counts[displayStatus] = (status_counts[displayStatus] || 0) + 1
    })
    
    // Calculate media type distribution
    const media_type_counts: Record<string, number> = {}
    media.forEach((mediaItem: any) => {
      const mediaType = mediaItem.media_type
      media_type_counts[mediaType] = (media_type_counts[mediaType] || 0) + 1
    })
    
    return {
      success: true,
      data: {
        media,
        stats: {
          ...stats,
          status_counts,
          media_type_counts
        },
        pagination: {
          page,
          limit,
          total,
          total_pages: Math.ceil(total / limit),
          has_next: page * limit < total,
          has_prev: page > 1
        }
      }
    }
    
  } catch (error) {
    console.error('Error fetching unified media:', error)
    return {
      success: false,
      error: 'Failed to fetch media data',
      details: error instanceof Error ? error.message : 'Unknown error'
    }
  }
})
