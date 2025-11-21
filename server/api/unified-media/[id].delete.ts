import { getDatabaseConnection } from '~/server/utils/database'

export default defineEventHandler(async (event) => {
  try {
    const id = getRouterParam(event, 'id')
    if (!id) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Media ID is required'
      })
    }

    const db = await getDatabaseConnection()
    
    // First, check if the media item exists
    const [existingRows] = await db.execute(`
      SELECT id, title, media_type, status
      FROM unified_media 
      WHERE id = ?
    `, [id])
    
    const existingMedia = (existingRows as any[])[0]
    if (!existingMedia) {
      throw createError({
        statusCode: 404,
        statusMessage: 'Media item not found'
      })
    }
    
    // Delete the media item
    const [result] = await db.execute(`
      DELETE FROM unified_media 
      WHERE id = ?
    `, [id])
    
    const affectedRows = (result as any).affectedRows
    
    if (affectedRows === 0) {
      throw createError({
        statusCode: 404,
        statusMessage: 'Media item not found or already deleted'
      })
    }
    
    return {
      success: true,
      message: `Successfully deleted ${existingMedia.media_type} "${existingMedia.title}"`,
      data: {
        id: parseInt(id),
        title: existingMedia.title,
        media_type: existingMedia.media_type,
        status: existingMedia.status
      }
    }
  } catch (error) {
    console.error('Error deleting media item:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to delete media item',
      data: error instanceof Error ? error.message : 'Unknown error'
    })
  }
})
