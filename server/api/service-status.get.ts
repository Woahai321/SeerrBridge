interface ServiceStatusRow {
  last_updated: string
  status: string
  version: string
  uptime_seconds: number
  uptime_string: string
  start_time: string
  current_time: string
  queue_status: any
  browser_status: string
  automatic_processing: boolean
  show_subscription: boolean
  refresh_interval_minutes: number
  library_stats: any
  queue_activity: any
}

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  
  try {
    // Get database connection
    const { getDatabaseConnection } = await import('~/server/utils/database')
    const connection = await getDatabaseConnection()
    
    // Query the service status from database
    const [rows] = await connection.execute(
      'SELECT * FROM service_status WHERE service_name = ? ORDER BY last_updated DESC LIMIT 1',
      ['seerrbridge']
    )
    
    const statusData = Array.isArray(rows) && rows.length > 0 ? rows[0] as ServiceStatusRow : null
    
    if (!statusData) {
      return {
        status: 'offline',
        message: 'Service status not found in database',
        timestamp: new Date().toISOString()
      }
    }
    
    // Check if the status is recent (within last 30 seconds)
    const lastUpdated = new Date(statusData.last_updated)
    const now = new Date()
    const timeDiff = now.getTime() - lastUpdated.getTime()
    
    if (timeDiff > 30000) { // 30 seconds
      return {
        status: 'offline',
        message: 'Service status is stale',
        last_updated: statusData.last_updated,
        timestamp: new Date().toISOString()
      }
    }
    
    // Return the status data in the expected formatre
    return {
      status: statusData.status,
      version: statusData.version,
      uptime_seconds: statusData.uptime_seconds,
      uptime: statusData.uptime_string,
      start_time: statusData.start_time,
      current_time: statusData.current_time,
      queue_status: statusData.queue_status,
      browser_status: statusData.browser_status,
      automatic_processing: Boolean(statusData.automatic_processing),
      show_subscription: Boolean(statusData.show_subscription),
      refresh_interval_minutes: statusData.refresh_interval_minutes,
      library_stats: statusData.library_stats,
      queue_activity: statusData.queue_activity,
      last_check: new Date().toLocaleTimeString(),
      services: {
        database: true,
        seerrbridge: statusData.status === 'running',
        overseerr: false, // We don't track this in the current system
        realdebrid: false, // We don't track this in the current system
        trakt: false // We don't track this in the current system
      }
    }
    
  } catch (error) {
    console.error('Error fetching service status from database:', error)
    
    const errorMessage = error instanceof Error ? error.message : 'Database error'
    
    return {
      status: 'error',
      error: 'Failed to fetch service status',
      message: errorMessage,
      timestamp: new Date().toISOString()
    }
  }
})
