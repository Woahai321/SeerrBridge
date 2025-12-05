import { getDatabaseConnection } from '~/server/utils/database'

interface BulkUpdateStatusRequest {
  media_ids: number[]
  status: string
}

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody<BulkUpdateStatusRequest>(event)
    const { media_ids, status } = body
    
    if (!media_ids || !Array.isArray(media_ids) || media_ids.length === 0) {
      throw createError({
        statusCode: 400,
        statusMessage: 'media_ids array is required and must not be empty'
      })
    }

    if (!status || (status !== 'ignored' && status !== 'pending')) {
      throw createError({
        statusCode: 400,
        statusMessage: 'status must be either "ignored" or "pending"'
      })
    }

    const db = await getDatabaseConnection()
    
    const results = {
      success: [] as Array<{ id: number; title: string; media_type: string; status: string }>,
      failed: [] as Array<{ id: number; error: string }>,
      total: media_ids.length,
      success_count: 0,
      failed_count: 0
    }

    // Process each media ID
    for (const mediaId of media_ids) {
      try {
        // First, check if the media item exists
        const [existingRows] = await db.execute(`
          SELECT id, title, media_type, status
          FROM unified_media 
          WHERE id = ?
        `, [mediaId])
        
        const existingMedia = (existingRows as any[])[0]
        if (!existingMedia) {
          results.failed.push({
            id: mediaId,
            error: 'Media item not found'
          })
          results.failed_count++
          continue
        }

        // Update the status
        const [result] = await db.execute(`
          UPDATE unified_media 
          SET status = ?, updated_at = NOW()
          WHERE id = ?
        `, [status, mediaId])
        
        const affectedRows = (result as any).affectedRows
        
        if (affectedRows === 0) {
          results.failed.push({
            id: mediaId,
            error: 'Media item not found or update failed'
          })
          results.failed_count++
        } else {
          results.success.push({
            id: mediaId,
            title: existingMedia.title,
            media_type: existingMedia.media_type,
            status: status
          })
          results.success_count++
        }
      } catch (error) {
        console.error(`Error updating media item ${mediaId}:`, error)
        results.failed.push({
          id: mediaId,
          error: error instanceof Error ? error.message : 'Unknown error'
        })
        results.failed_count++
      }
    }
    
    return {
      status: results.failed_count === 0 ? 'completed' : 'partial',
      results
    }
  } catch (error) {
    console.error('Error bulk updating media status:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to bulk update media status',
      data: error instanceof Error ? error.message : 'Unknown error'
    })
  }
})

