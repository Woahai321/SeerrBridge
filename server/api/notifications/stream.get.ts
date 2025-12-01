import { getDatabaseConnection } from '~/server/utils/database'

export default defineEventHandler(async (event) => {
  // Set headers for Server-Sent Events
  setHeader(event, 'Content-Type', 'text/event-stream')
  setHeader(event, 'Cache-Control', 'no-cache')
  setHeader(event, 'Connection', 'keep-alive')
  setHeader(event, 'X-Accel-Buffering', 'no') // Disable nginx buffering
  
  // Get the last notification timestamp from query params
  const query = getQuery(event)
  const lastTimestamp = query.lastTimestamp as string | undefined
  
  // Return a readable stream
  return new ReadableStream({
    async start(controller) {
      const encoder = new TextEncoder()
      
      // Send initial connection message
      controller.enqueue(encoder.encode(': connected\n\n'))
      
      let lastNotificationTime = lastTimestamp || null
      let isActive = true
      
      // Poll for new notifications every 500ms for ultra real-time
      const pollInterval = setInterval(async () => {
        if (!isActive) {
          clearInterval(pollInterval)
          controller.close()
          return
        }
        
        try {
          const db = await getDatabaseConnection()
          
          // Build query to get only new unread notifications
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
            WHERE viewed = FALSE
          `
          
          // If we have a last timestamp, only get notifications created after it
          if (lastNotificationTime) {
            sql += ` AND created_at > ?`
          }
          
          sql += ` ORDER BY created_at ASC LIMIT 50`
          
          const params = lastNotificationTime ? [lastNotificationTime] : []
          const [notifications] = await db.execute(sql, params)
          
          // Parse and send new notifications
          for (const notification of notifications as any[]) {
            let details: any = {}
            try {
              details = notification.details ? JSON.parse(notification.details) : {}
            } catch (e) {
              details = {}
            }
            
            const notificationData = {
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
            
            // Update last notification time
            lastNotificationTime = notification.created_at
            
            // Send notification as SSE event
            const data = JSON.stringify(notificationData)
            controller.enqueue(encoder.encode(`data: ${data}\n\n`))
          }
        } catch (error) {
          console.error('Error in notification stream:', error)
          // Send error as comment (won't trigger event)
          controller.enqueue(encoder.encode(`: error occurred\n\n`))
        }
      }, 500) // Poll every 500ms for ultra real-time
      
      // Cleanup on client disconnect
      event.node.req.on('close', () => {
        isActive = false
        clearInterval(pollInterval)
        controller.close()
      })
    }
  })
})

