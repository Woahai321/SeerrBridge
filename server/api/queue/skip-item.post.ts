import { getDatabaseConnection } from '~/server/utils/database'

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody(event)
    const { media_id, tmdb_id, media_type } = body
    
    if (!media_id && !tmdb_id) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Invalid request: media_id or tmdb_id is required'
      })
    }
    
    if (!media_type) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Invalid request: media_type is required'
      })
    }
    
    const db = await getDatabaseConnection()
    
    // Find the media record
    let mediaRecord
    if (media_id) {
      const [results] = await db.execute(
        'SELECT id, tmdb_id, media_type, title, is_in_queue, status FROM unified_media WHERE id = ?',
        [media_id]
      )
      mediaRecord = (results as any[])[0]
    } else {
      const [results] = await db.execute(
        'SELECT id, tmdb_id, media_type, title, is_in_queue, status FROM unified_media WHERE tmdb_id = ? AND media_type = ?',
        [tmdb_id, media_type]
      )
      mediaRecord = (results as any[])[0]
    }
    
    if (!mediaRecord) {
      throw createError({
        statusCode: 404,
        statusMessage: 'Media record not found'
      })
    }
    
    // Check if item is in queue or currently processing
    if (!mediaRecord.is_in_queue && mediaRecord.status !== 'processing') {
      return {
        success: true,
        message: 'Item is not in queue',
        skipped: false
      }
    }
    
    // Mark as failed with cancellation message
    // The Python backend will check the database status when processing items
    await db.execute(`
      UPDATE unified_media 
      SET 
        status = 'failed',
        processing_stage = 'cancelled',
        error_message = 'Cancelled by user',
        is_in_queue = FALSE,
        last_checked_at = NOW(),
        updated_at = NOW()
      WHERE id = ?
    `, [mediaRecord.id])
    
    return {
      success: true,
      message: `Successfully skipped ${mediaRecord.title}`,
      media_id: mediaRecord.id,
      tmdb_id: mediaRecord.tmdb_id,
      media_type: mediaRecord.media_type
    }
    
  } catch (error) {
    console.error('Error skipping queue item:', error)
    
    if (error.statusCode) {
      throw error
    }
    
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to skip queue item'
    })
  }
})

