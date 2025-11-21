import { getDatabaseConnection } from '~/server/utils/database'

interface UpdateTVSubscriptionRequest {
  title?: string
  is_subscribed?: boolean
  subscription_active?: boolean
}

export default defineEventHandler(async (event) => {
  try {
    const id = getRouterParam(event, 'id')
    if (!id) {
      throw createError({
        statusCode: 400,
        statusMessage: 'TV show ID is required'
      })
    }

    const body = await readBody<UpdateTVSubscriptionRequest>(event)
    
    const db = await getDatabaseConnection()
    
    // Build dynamic update query
    const updateFields: string[] = []
    const updateValues: any[] = []
    
    if (body.title !== undefined) {
      updateFields.push('title = ?')
      updateValues.push(body.title)
    }
    
    if (body.is_subscribed !== undefined) {
      updateFields.push('is_subscribed = ?')
      updateValues.push(body.is_subscribed ? 1 : 0)
    }
    
    if (body.subscription_active !== undefined) {
      updateFields.push('subscription_active = ?')
      updateValues.push(body.subscription_active ? 1 : 0)
    }
    
    if (updateFields.length === 0) {
      throw createError({
        statusCode: 400,
        statusMessage: 'No valid fields to update'
      })
    }
    
    updateFields.push('updated_at = NOW()')
    updateValues.push(id)
    
    const query = `
      UPDATE unified_media 
      SET ${updateFields.join(', ')}
      WHERE id = ? AND media_type = 'tv'
    `
    
    const [result] = await db.execute(query, updateValues)
    const affectedRows = (result as any).affectedRows
    
    if (affectedRows === 0) {
      throw createError({
        statusCode: 404,
        statusMessage: 'TV show not found'
      })
    }
    
    // Fetch updated TV show
    const [rows] = await db.execute(`
      SELECT 
        id,
        title,
        poster_url,
        poster_image_format,
        poster_image_size,
        thumb_url,
        thumb_image_format,
        thumb_image_size,
        is_subscribed,
        subscription_active,
        last_checked_at,
        updated_at
      FROM unified_media 
      WHERE id = ? AND media_type = 'tv'
    `, [id])
    
    const tvShow = (rows as any[])[0]
    if (!tvShow) {
      throw createError({
        statusCode: 404,
        statusMessage: 'TV show not found'
      })
    }
    
    return {
      id: tvShow.id.toString(),
      title: tvShow.title,
      poster_url: tvShow.poster_url,
      poster_image_url: tvShow.poster_url,
      poster_image_format: tvShow.poster_image_format,
      poster_image_size: tvShow.poster_image_size,
      thumb_url: tvShow.thumb_url,
      thumb_image_url: tvShow.thumb_url,
      thumb_image_format: tvShow.thumb_image_format,
      thumb_image_size: tvShow.thumb_image_size,
      status: (tvShow.is_subscribed ? 'active' : 'inactive') as 'active' | 'inactive',
      last_checked: tvShow.last_checked_at,
      updated_at: tvShow.updated_at
    }
  } catch (error) {
    console.error('Error updating TV subscription:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to update TV subscription'
    })
  }
})
