import { getDatabaseConnection } from '~/server/utils/database'
import { getOverseerrConfig } from '~/server/utils/overseerr-config'

interface BulkDeleteRequest {
  media_ids: number[]
}

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody<BulkDeleteRequest>(event)
    const { media_ids } = body
    
    if (!media_ids || !Array.isArray(media_ids) || media_ids.length === 0) {
      throw createError({
        statusCode: 400,
        statusMessage: 'media_ids array is required and must not be empty'
      })
    }

    const db = await getDatabaseConnection()
    
    const results = {
      success: [] as Array<{ id: number; title: string; media_type: string }>,
      failed: [] as Array<{ id: number; error: string }>,
      overseerr_deleted: [] as number[],
      overseerr_failed: [] as Array<{ id: number; request_id: number; error: string }>,
      total: media_ids.length,
      success_count: 0,
      failed_count: 0
    }

    // Get Overseerr config for request deletion
    let overseerrConfig: { baseUrl: string; apiKey: string } | null = null
    try {
      const config = await getOverseerrConfig()
      if (config.baseUrl && config.apiKey) {
        overseerrConfig = {
          baseUrl: config.baseUrl.replace(/\/$/, ''),
          apiKey: config.apiKey
        }
      }
    } catch (error) {
      console.warn('Overseerr config not available, skipping Overseerr deletions')
    }

    // Process each media ID
    for (const mediaId of media_ids) {
      try {
        // First, get the media item to check for Overseerr request ID
        const [existingRows] = await db.execute(`
          SELECT id, title, media_type, status, overseerr_request_id
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

        // Try to delete from Overseerr if we have a request ID
        if (existingMedia.overseerr_request_id && overseerrConfig) {
          try {
            const deleteUrl = `${overseerrConfig.baseUrl}/api/v1/request/${existingMedia.overseerr_request_id}`
            const response = await fetch(deleteUrl, {
              method: 'DELETE',
              headers: {
                'X-Api-Key': overseerrConfig.apiKey,
                'Content-Type': 'application/json'
              }
            })
            
            if (response.ok) {
              results.overseerr_deleted.push(existingMedia.overseerr_request_id)
            } else {
              const errorText = await response.text()
              results.overseerr_failed.push({
                id: mediaId,
                request_id: existingMedia.overseerr_request_id,
                error: `Overseerr API error: ${response.status} ${errorText}`
              })
            }
          } catch (error) {
            results.overseerr_failed.push({
              id: mediaId,
              request_id: existingMedia.overseerr_request_id,
              error: error instanceof Error ? error.message : 'Unknown error'
            })
          }
        }

        // Delete from database
        const [result] = await db.execute(`
          DELETE FROM unified_media 
          WHERE id = ?
        `, [mediaId])
        
        const affectedRows = (result as any).affectedRows
        
        if (affectedRows === 0) {
          results.failed.push({
            id: mediaId,
            error: 'Media item not found or already deleted'
          })
          results.failed_count++
        } else {
          results.success.push({
            id: mediaId,
            title: existingMedia.title,
            media_type: existingMedia.media_type
          })
          results.success_count++
        }
      } catch (error) {
        console.error(`Error deleting media item ${mediaId}:`, error)
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
    console.error('Error bulk deleting media items:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to bulk delete media items',
      data: error instanceof Error ? error.message : 'Unknown error'
    })
  }
})

