import { getDatabaseConnection } from '~/server/utils/database'

interface UpdateMediaStatusRequest {
  status?: string
}

export default defineEventHandler(async (event) => {
  try {
    const id = getRouterParam(event, 'id')
    if (!id) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Media ID is required'
      })
    }

    const body = await readBody<UpdateMediaStatusRequest>(event)
    
    const db = await getDatabaseConnection()
    
    // Build dynamic update query
    const updateFields: string[] = []
    const updateValues: any[] = []
    
    if (body.status !== undefined) {
      updateFields.push('status = ?')
      updateValues.push(body.status)
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
      WHERE id = ?
    `
    
    const [result] = await db.execute(query, updateValues)
    const affectedRows = (result as any).affectedRows
    
    if (affectedRows === 0) {
      throw createError({
        statusCode: 404,
        statusMessage: 'Media item not found'
      })
    }
    
    // Fetch updated media item
    const [rows] = await db.execute(`
      SELECT 
        id,
        status,
        processing_stage,
        updated_at
      FROM unified_media 
      WHERE id = ?
    `, [id])
    
    const mediaItem = (rows as any[])[0]
    if (!mediaItem) {
      throw createError({
        statusCode: 404,
        statusMessage: 'Media item not found'
      })
    }
    
    return {
      success: true,
      data: mediaItem
    }
  } catch (error) {
    console.error('Error updating media status:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to update media status',
      data: error instanceof Error ? error.message : 'Unknown error'
    })
  }
})

