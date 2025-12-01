import { getDatabaseConnection } from '~/server/utils/database'

export default defineEventHandler(async (event) => {
  try {
    const db = await getDatabaseConnection()
    
    const query = `
      UPDATE notification_history 
      SET viewed = TRUE
      WHERE viewed = FALSE
    `
    
    const [result] = await db.execute(query)
    const affectedRows = (result as any).affectedRows
    
    return {
      success: true,
      message: 'All notifications marked as read',
      affectedRows
    }
  } catch (error) {
    console.error('Error marking all notifications as read:', error)
    return {
      success: false,
      error: 'Failed to mark notifications as read',
      details: error instanceof Error ? error.message : String(error)
    }
  }
})

