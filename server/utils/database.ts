import mysql from 'mysql2/promise'

let connection: mysql.Connection | null = null

export async function getDatabaseConnection(): Promise<mysql.Connection> {
  if (!connection) {
    const config = useRuntimeConfig()
    
    const connectionConfig = {
      host: config.dbHost || process.env.DB_HOST || 'localhost',
      port: parseInt(config.dbPort || process.env.DB_PORT || '3307'),
      user: config.dbUser || process.env.DB_USER || 'seerrbridge',
      password: config.dbPassword || process.env.DB_PASSWORD || 'seerrbridge',
      database: config.dbName || process.env.DB_NAME || 'seerrbridge',
      charset: 'utf8mb4'
    }
    
    // DO NOT log database password - only log non-sensitive connection info
    console.debug('Connecting to database:', {
      host: connectionConfig.host,
      port: connectionConfig.port,
      user: connectionConfig.user,
      database: connectionConfig.database
      // Password intentionally omitted
    })
    
    try {
      connection = await mysql.createConnection(connectionConfig)
      console.log('Database connection established successfully')
    } catch (error) {
      console.error('Failed to connect to database:', error)
      throw error
    }
  }
  
  return connection
}

export async function closeDatabaseConnection(): Promise<void> {
  if (connection) {
    await connection.end()
    connection = null
  }
}

export interface LogEntry {
  id: number
  timestamp: string
  level: string
  module?: string
  function?: string
  line_number?: number
  title: string
  message: string
  details?: any
  source?: string
  processed: boolean
  notification_sent: boolean
  created_at: string
}

export interface LogStatistics {
  totalLogs: number
  successCount: number
  errorCount: number
  warningCount: number
  infoCount: number
  failedEpisodes: number
  successfulGrabs: number
  criticalErrors: number
  tokenStatus: any
  recentSuccesses: LogEntry[]
  recentFailures: LogEntry[]
  recentCompletedMedia: any[]
}

export async function getLogEntries(page = 1, limit = 50, level?: string): Promise<{ entries: LogEntry[], total: number }> {
  const db = await getDatabaseConnection()
  const offset = (page - 1) * limit
  
  let whereClause = ''
  let countParams: any[] = []
  let queryParams: any[] = []
  
  if (level) {
    whereClause = 'WHERE level = ?'
    countParams = [level]
    queryParams = [level, limit, offset]
  } else {
    queryParams = [limit, offset]
  }
  
  // Get total count
  const [countResult] = await db.execute(
    `SELECT COUNT(*) as total FROM log_entries ${whereClause}`,
    countParams
  )
  const total = (countResult as any)[0].total
  
  // Get entries
  const [rows] = await db.execute(
    `SELECT * FROM log_entries ${whereClause} ORDER BY timestamp DESC LIMIT ${parseInt(limit.toString())} OFFSET ${parseInt(offset.toString())}`,
    level ? [level] : []
  )
  
  return {
    entries: rows as LogEntry[],
    total
  }
}

export async function getLogStatistics(): Promise<LogStatistics> {
  const db = await getDatabaseConnection()
  
  // Get basic counts
  const [totalResult] = await db.execute('SELECT COUNT(*) as total FROM log_entries')
  const totalLogs = (totalResult as any)[0].total
  
  const [levelCounts] = await db.execute(`
    SELECT level, COUNT(*) as count 
    FROM log_entries 
    GROUP BY level
  `)
  
  const counts = (levelCounts as any).reduce((acc: any, row: any) => {
    acc[row.level.toLowerCase()] = row.count
    return acc
  }, {})
  
  // Get successful grabs count from unified_media table
  // This includes completed movies and completed seasons from TV shows
  const [successfulGrabsResult] = await db.execute(`
    SELECT 
      COUNT(*) as completed_media,
      COALESCE(SUM(
        CASE 
          WHEN media_type = 'movie' AND status = 'completed' THEN 1
          WHEN media_type = 'tv' AND status = 'completed' THEN 1
          WHEN media_type = 'tv' AND seasons_completed IS NOT NULL THEN JSON_LENGTH(seasons_completed)
          ELSE 0
        END
      ), 0) as total_successful_grabs
    FROM unified_media 
    WHERE status = 'completed' 
       OR (media_type = 'tv' AND seasons_completed IS NOT NULL AND JSON_LENGTH(seasons_completed) > 0)
  `)
  const successfulGrabs = (successfulGrabsResult as any)[0].total_successful_grabs
  
  // Get recent successes and failures
  const [recentSuccesses] = await db.execute(`
    SELECT * FROM log_entries 
    WHERE level = 'success' 
    ORDER BY timestamp DESC 
    LIMIT 10
  `)
  
  const [recentFailures] = await db.execute(`
    SELECT * FROM log_entries 
    WHERE level = 'error' 
    ORDER BY timestamp DESC 
    LIMIT 10
  `)
  
  // Get recent completed media for the change indicator
  // Include both fully completed media and TV shows with completed seasons
  const [recentCompletedMedia] = await db.execute(`
    SELECT 
      id, 
      title, 
      media_type, 
      processing_completed_at,
      seasons_completed,
      CASE 
        WHEN media_type = 'movie' THEN 1
        WHEN media_type = 'tv' AND seasons_completed IS NOT NULL THEN JSON_LENGTH(seasons_completed)
        ELSE 1
      END as completed_count
    FROM unified_media 
    WHERE status = 'completed' 
       OR (media_type = 'tv' AND seasons_completed IS NOT NULL AND JSON_LENGTH(seasons_completed) > 0)
    ORDER BY processing_completed_at DESC 
    LIMIT 10
  `)
  
  return {
    totalLogs,
    successCount: counts.success || 0,
    errorCount: counts.error || 0,
    warningCount: counts.warning || 0,
    infoCount: counts.info || 0,
    failedEpisodes: 0, // This would need specific logic
    successfulGrabs: successfulGrabs,
    criticalErrors: counts.error || 0,
    tokenStatus: null, // This would need specific logic
    recentSuccesses: recentSuccesses as LogEntry[],
    recentFailures: recentFailures as LogEntry[],
    recentCompletedMedia: recentCompletedMedia as any[]
  }
}

export async function getRecentLogs(limit = 20): Promise<LogEntry[]> {
  const db = await getDatabaseConnection()
  
  // Use string interpolation for LIMIT since it's safe (small integer)
  // and avoids MySQL2 parameter binding issues with LIMIT clauses
  const [rows] = await db.execute(`
    SELECT * FROM log_entries 
    ORDER BY timestamp DESC 
    LIMIT ${parseInt(limit.toString())}
  `)
  
  return rows as LogEntry[]
}
