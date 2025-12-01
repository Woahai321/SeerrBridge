import { getDatabaseConnection } from '~/server/utils/database'

export default defineEventHandler(async (event) => {
  try {
    const db = await getDatabaseConnection()
    
    const [rows] = await db.execute(`
      SELECT COUNT(*) as count 
      FROM notification_history 
      WHERE viewed = FALSE
    `)
    
    const count = (rows as any[])[0]?.count || 0
    
    return {
      success: true,
      count
    }
  } catch (error) {
    console.error('Error getting unread count:', error)
    return {
      success: false,
      error: 'Failed to get unread count',
      details: error instanceof Error ? error.message : String(error)
    }
  }
})

