import { getDatabaseConnection } from '~/server/utils/database'

export default defineEventHandler(async (event) => {
  try {
    const db = await getDatabaseConnection()
    const query = getQuery(event)
    
    const {
      page = 1,
      limit = 20,
      media_type = 'all',
      status = 'failed',
      search = '',
      sort_by = 'last_error_at',
      sort_order = 'desc'
    } = query
    
    const offset = (Number(page) - 1) * Number(limit)
    
    // Build WHERE conditions
    const whereConditions = []
    const paramValues = []
    
    // Status filter
    if (status) {
      whereConditions.push('status = ?')
      paramValues.push(status)
    }
    
    // Media type filter
    if (media_type && media_type !== 'all') {
      whereConditions.push('media_type = ?')
      paramValues.push(media_type)
    }
    
    // Search filter
    if (search) {
      whereConditions.push('(title LIKE ? OR overview LIKE ?)')
      paramValues.push(`%${search}%`)
      paramValues.push(`%${search}%`)
    }
    
    // Only show items with errors (non-parameterized conditions)
    whereConditions.push('error_message IS NOT NULL')
    whereConditions.push('error_count > 0')
    
    const whereClause = whereConditions.length > 0 ? `WHERE ${whereConditions.join(' AND ')}` : ''
    
    // Build ORDER BY clause
    const validSortFields = ['last_error_at', 'error_count', 'title', 'created_at', 'updated_at']
    const sortByValue = sort_by?.toString() || 'last_error_at'
    const sortField = validSortFields.includes(sortByValue) ? sortByValue : 'last_error_at'
    const sortOrderValue = sort_order?.toString() || 'desc'
    const sortDirection = sortOrderValue === 'asc' ? 'ASC' : 'DESC'
    const orderClause = `ORDER BY ${sortField} ${sortDirection}`
    
    // Get total count
    const countQuery = `
      SELECT COUNT(*) as total
      FROM unified_media
      ${whereClause}
    `
    
    const [countResult] = await db.execute(countQuery, paramValues)
    const total = (countResult as any[])[0]?.total || 0
    
    // Get data - Use string interpolation for LIMIT/OFFSET to avoid MySQL2 parameter binding issues
    const dataQuery = `
      SELECT 
        id,
        title,
        year,
        media_type,
        status,
        processing_stage,
        error_message,
        error_count,
        last_error_at,
        created_at,
        updated_at,
        overseerr_media_id,
        overseerr_request_id,
        tmdb_id,
        imdb_id,
        poster_url,
        thumb_url,
        fanart_url,
        backdrop_url,
        poster_image_format,
        poster_image_size,
        thumb_image_format,
        thumb_image_size,
        fanart_image_format,
        fanart_image_size,
        backdrop_image_format,
        backdrop_image_size,
        is_in_queue,
        queue_attempts,
        queue_added_at,
        extra_data
      FROM unified_media
      ${whereClause}
      ${orderClause}
      LIMIT ${parseInt(limit.toString())} OFFSET ${parseInt(offset.toString())}
    `
    
    
    const [dataResult] = await db.execute(dataQuery, paramValues)
    
    // Process the data to add computed fields
    const media = (dataResult as any[]).map((row: any) => {
      if (!row) return null
      
      const mediaItem = { ...row }
      
      // Add computed fields
      mediaItem.has_poster_image = !!row.poster_image_format
      mediaItem.has_thumb_image = !!row.thumb_image_format
      mediaItem.has_fanart_image = !!row.fanart_image_format
      mediaItem.has_backdrop_image = !!row.backdrop_image_format
      
      // Parse extra_data if it's a string
      if (mediaItem.extra_data && typeof mediaItem.extra_data === 'string') {
        try {
          mediaItem.extra_data = JSON.parse(mediaItem.extra_data)
        } catch (e) {
          // Keep as string if parsing fails
        }
      }
      
      // Add retry eligibility
      const now = new Date()
      const lastError = new Date(mediaItem.last_error_at)
      const hoursSinceError = (now.getTime() - lastError.getTime()) / (1000 * 60 * 60)
      mediaItem.retry_eligible = hoursSinceError >= 2 // 2 hours minimum
      mediaItem.hours_since_error = Math.round(hoursSinceError * 10) / 10
      
      // Add retry status
      mediaItem.retry_status = mediaItem.is_in_queue ? 'queued' : 
                              mediaItem.retry_eligible ? 'eligible' : 'waiting'
      
      return mediaItem
    }).filter(Boolean)
    
    // Get statistics
    const statsQuery = `
      SELECT 
        COUNT(*) as total_failed,
        COUNT(CASE WHEN media_type = 'movie' THEN 1 END) as failed_movies,
        COUNT(CASE WHEN media_type = 'tv' THEN 1 END) as failed_tv_shows,
        COUNT(CASE WHEN is_in_queue = 1 THEN 1 END) as queued_for_retry,
        COUNT(CASE WHEN last_error_at > DATE_SUB(NOW(), INTERVAL 24 HOUR) THEN 1 END) as failed_last_24h,
        AVG(error_count) as avg_error_count,
        MAX(error_count) as max_error_count
      FROM unified_media
      WHERE status = 'failed' AND error_message IS NOT NULL AND error_count > 0
    `
    
    const [statsResult] = await db.execute(statsQuery)
    const stats = (statsResult as any[])[0] || {}
    
    return {
      data: media,
      pagination: {
        page: Number(page),
        limit: Number(limit),
        total,
        pages: Math.ceil(total / Number(limit))
      },
      stats: {
        total_failed: stats.total_failed || 0,
        failed_movies: stats.failed_movies || 0,
        failed_tv_shows: stats.failed_tv_shows || 0,
        queued_for_retry: stats.queued_for_retry || 0,
        failed_last_24h: stats.failed_last_24h || 0,
        avg_error_count: Math.round((stats.avg_error_count || 0) * 10) / 10,
        max_error_count: stats.max_error_count || 0
      }
    }
    
  } catch (error) {
    console.error('Error fetching failed items:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to fetch failed items'
    })
  }
})
