import { getDatabaseConnection } from '~/server/utils/database'

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody(event)
    const { confirmText } = body

    if (!confirmText || confirmText !== 'WIPE_DATABASE') {
      throw createError({
        statusCode: 400,
        statusMessage: 'Confirmation text "WIPE_DATABASE" is required'
      })
    }

    const db = await getDatabaseConnection()
    const config = useRuntimeConfig()
    const databaseName = config.dbName || process.env.DB_NAME || 'seerrbridge'
    
    // Get all tables in the database
    const [tables] = await db.execute(`
      SELECT TABLE_NAME 
      FROM information_schema.TABLES 
      WHERE TABLE_SCHEMA = ?
      ORDER BY TABLE_NAME
    `, [databaseName])

    const tableNames = (tables as any[]).map(table => table.TABLE_NAME)
    
    console.log(`Found ${tableNames.length} tables in database '${databaseName}':`, tableNames)
    
    if (tableNames.length === 0) {
      return {
        success: true,
        message: 'No tables found to clear',
        tablesCleared: [],
        totalRowsRemoved: 0
      }
    }

    // Disable foreign key checks temporarily
    await db.execute('SET FOREIGN_KEY_CHECKS = 0')
    
    const clearedTables = []
    let totalRowsRemoved = 0

    try {
      // Clear each table
      for (const tableName of tableNames) {
        try {
          // Get row count before clearing
          const [countResult] = await db.execute(`SELECT COUNT(*) as count FROM \`${tableName}\``)
          const rowCount = (countResult as any)[0].count
          
          // Clear the table
          await db.execute(`TRUNCATE TABLE \`${tableName}\``)
          
          clearedTables.push({
            name: tableName,
            rowsRemoved: rowCount
          })
          
          totalRowsRemoved += rowCount
          console.log(`Table '${tableName}' cleared. Removed ${rowCount} rows.`)
        } catch (tableError) {
          console.error(`Error clearing table '${tableName}':`, tableError)
          // Continue with other tables even if one fails
          clearedTables.push({
            name: tableName,
            rowsRemoved: 0,
            error: tableError.message
          })
        }
      }
    } finally {
      // Re-enable foreign key checks
      await db.execute('SET FOREIGN_KEY_CHECKS = 1')
    }

    console.log(`Database cleared successfully. Cleared ${clearedTables.length} tables, removed ${totalRowsRemoved} total rows.`)

    return {
      success: true,
      message: `Database cleared successfully. Cleared ${clearedTables.length} tables.`,
      tablesCleared: clearedTables,
      totalRowsRemoved,
      tablesCount: clearedTables.length
    }
  } catch (error) {
    console.error('Error clearing database:', error)
    throw createError({
      statusCode: error.statusCode || 500,
      statusMessage: error.statusMessage || 'Failed to clear database'
    })
  }
})
