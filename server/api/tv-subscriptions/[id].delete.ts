import { getDatabaseConnection } from '~/server/utils/database'

export default defineEventHandler(async (event) => {
  try {
    const id = getRouterParam(event, 'id')
    if (!id) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Subscription ID is required'
      })
    }

    const db = await getDatabaseConnection()
    
    // First, check if the TV show exists
    const [checkRows] = await db.execute(`
      SELECT id, title FROM unified_media WHERE id = ? AND media_type = 'tv'
    `, [id])
    
    if ((checkRows as any[]).length === 0) {
      throw createError({
        statusCode: 404,
        statusMessage: 'TV show not found'
      })
    }
    
    const tvShow = (checkRows as any[])[0]
    
    // Update the subscription status to inactive instead of deleting
    const [result] = await db.execute(`
      UPDATE unified_media 
      SET is_subscribed = 0, subscription_active = 0, updated_at = NOW()
      WHERE id = ? AND media_type = 'tv'
    `, [id])
    
    const affectedRows = (result as any).affectedRows
    
    if (affectedRows === 0) {
      throw createError({
        statusCode: 404,
        statusMessage: 'TV subscription not found'
      })
    }
    
    return {
      success: true,
      message: `Successfully unsubscribed from "${tvShow.title}"`,
      unsubscribedId: id
    }
  } catch (error) {
    console.error('Error deleting TV subscription:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to delete TV subscription'
    })
  }
})
