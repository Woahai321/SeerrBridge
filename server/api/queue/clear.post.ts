import { getDatabaseConnection } from '~/server/utils/database'

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody(event)
    const { media_type } = body // Optional: 'movie', 'tv', or undefined for all
    
    const db = await getDatabaseConnection()
    
    // Build query to get all queued items
    let query = `
      SELECT id, tmdb_id, media_type, title, is_in_queue, status 
      FROM unified_media 
      WHERE is_in_queue = TRUE 
        AND status != 'completed' 
        AND status != 'ignored'
    `
    const params: any[] = []
    
    if (media_type) {
      query += ' AND media_type = ?'
      params.push(media_type)
    }
    
    const [results] = await db.execute(query, params)
    const queuedItems = results as any[]
    
    if (queuedItems.length === 0) {
      return {
        success: true,
        message: 'No items in queue to clear',
        cleared_count: 0
      }
    }
    
    // Build update query
    let updateQuery = `
      UPDATE unified_media 
      SET 
        status = 'failed',
        processing_stage = 'cancelled',
        error_message = 'Cancelled by user (queue cleared)',
        is_in_queue = FALSE,
        last_checked_at = NOW(),
        updated_at = NOW()
      WHERE is_in_queue = TRUE 
        AND status != 'completed' 
        AND status != 'ignored'
    `
    const updateParams: any[] = []
    
    if (media_type) {
      updateQuery += ' AND media_type = ?'
      updateParams.push(media_type)
    }
    
    await db.execute(updateQuery, updateParams)
    
    // Count by type
    const movieCount = queuedItems.filter(item => item.media_type === 'movie').length
    const tvCount = queuedItems.filter(item => item.media_type === 'tv').length
    
    return {
      success: true,
      message: `Successfully cleared ${queuedItems.length} item(s) from queue`,
      cleared_count: queuedItems.length,
      movie_count: movieCount,
      tv_count: tvCount,
      media_type: media_type || 'all'
    }
    
  } catch (error) {
    console.error('Error clearing queue:', error)
    
    if (error.statusCode) {
      throw error
    }
    
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to clear queue'
    })
  }
})

