import { getDatabaseConnection } from '~/server/utils/database'

export default defineEventHandler(async (event) => {
  try {
    const db = await getDatabaseConnection()
    
    // Get database status
    const [status] = await db.execute('SHOW STATUS')
    const statusMap = (status as any[]).reduce((acc, row) => {
      acc[row.Variable_name] = row.Value
      return acc
    }, {})
    
    // Get database variables
    const [variables] = await db.execute('SHOW VARIABLES')
    const variablesMap = (variables as any[]).reduce((acc, row) => {
      acc[row.Variable_name] = row.Value
      return acc
    }, {})
    
    // Get process list
    const [processes] = await db.execute('SHOW PROCESSLIST')
    
    // Get database size
    const [dbSize] = await db.execute(`
      SELECT 
        ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS size_mb
      FROM information_schema.tables 
      WHERE table_schema = DATABASE()
    `)
    
    // Get table counts
    const [tableCounts] = await db.execute(`
      SELECT 
        COUNT(*) as total_tables,
        SUM(table_rows) as total_rows,
        SUM(data_length) as total_data_size,
        SUM(index_length) as total_index_size
      FROM information_schema.tables 
      WHERE table_schema = DATABASE()
    `)
    
    const tableCountsResult = (tableCounts as any)[0]
    
    return {
      status: {
        uptime: statusMap['Uptime'],
        threads_connected: statusMap['Threads_connected'],
        threads_running: statusMap['Threads_running'],
        questions: statusMap['Questions'],
        slow_queries: statusMap['Slow_queries'],
        connections: statusMap['Connections'],
        max_connections: variablesMap['max_connections'],
        version: variablesMap['version'],
        port: variablesMap['port'],
        datadir: variablesMap['datadir']
      },
      database: {
        name: process.env.DB_NAME || 'seerrbridge',
        size_mb: (dbSize as any)[0]?.size_mb || 0,
        total_tables: parseInt(tableCountsResult?.total_tables) || 0,
        total_rows: parseInt(tableCountsResult?.total_rows) || 0,
        total_data_size: parseInt(tableCountsResult?.total_data_size) || 0,
        total_index_size: parseInt(tableCountsResult?.total_index_size) || 0
      },
      processes: (processes as any[]).slice(0, 10), // Limit to first 10 processes
      timestamp: new Date().toISOString()
    }
  } catch (error) {
    console.error('Error fetching database health:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to fetch database health information'
    })
  }
})
