import { getDatabaseConnection } from '~/server/utils/database'

export default defineEventHandler(async (event) => {
  try {
    const id = getRouterParam(event, 'id')
    const body = await readBody(event)
    
    if (!id) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Notification ID is required'
      })
    }
    
    const db = await getDatabaseConnection()
    
    // Build dynamic update query
    const updateFields: string[] = []
    const updateValues: any[] = []
    
    if (body.read !== undefined) {
      updateFields.push('viewed = ?')
      updateValues.push(body.read)
    }
    
    if (updateFields.length === 0) {
      throw createError({
        statusCode: 400,
        statusMessage: 'No valid fields to update'
      })
    }
    
    updateValues.push(id)
    
    const query = `
      UPDATE notification_history 
      SET ${updateFields.join(', ')}
      WHERE id = ?
    `
    
    const [result] = await db.execute(query, updateValues)
    const affectedRows = (result as any).affectedRows
    
    if (affectedRows === 0) {
      throw createError({
        statusCode: 404,
        statusMessage: 'Notification not found'
      })
    }
    
    return {
      success: true,
      message: 'Notification updated successfully'
    }
  } catch (error) {
    console.error('Error updating notification:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to update notification',
      data: error instanceof Error ? error.message : 'Unknown error'
    })
  }
})

