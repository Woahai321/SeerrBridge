import { getDatabaseConnection } from '~/server/utils/database'

export default defineEventHandler(async (event) => {
  try {
    const query = getQuery(event)
    const limit = Math.min(parseInt(query.limit as string) || 50, 100)
    const unreadOnly = query.unreadOnly === 'true'
    
    const db = await getDatabaseConnection()
    if (!db) {
      throw new Error('Failed to get database connection')
    }
    
    let sql = `
      SELECT 
        id,
        type,
        title,
        message,
        details,
        successful,
        viewed as \`read\`,
        timestamp,
        created_at
      FROM notification_history
    `
    
    if (unreadOnly) {
      sql += ' WHERE viewed = FALSE'
    }
    
    sql += ` ORDER BY timestamp DESC LIMIT ${limit}`
    
    const [notifications] = await db.execute(sql)
    
    // Parse details JSON and map to expected format
    const mappedNotifications = (notifications as any[]).map(notification => {
      let details = {}
      try {
        details = notification.details ? JSON.parse(notification.details) : {}
      } catch (e) {
        // If parsing fails, use empty object
        details = {}
      }
      
      return {
        id: notification.id,
        type: notification.type,
        title: notification.title,
        message: notification.message,
        timestamp: notification.timestamp,
        created_at: notification.created_at,
        read: notification.read,
        media_id: details.media_id || null,
        media_type: details.media_type || null,
        media_title: details.media_title || null,
        old_status: details.old_status || null,
        new_status: details.new_status || null
      }
    })
    
    return {
      success: true,
      data: mappedNotifications
    }
  } catch (error) {
    console.error('Error fetching notifications:', error)
    return {
      success: false,
      error: 'Failed to fetch notifications',
      details: error instanceof Error ? error.message : String(error)
    }
  }
})

