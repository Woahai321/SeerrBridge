import { getDatabaseConnection } from '~/server/utils/database'

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody(event)
    const { tableName, confirmText } = body

    if (!tableName) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Table name is required'
      })
    }

    if (!confirmText || confirmText !== 'CLEAR') {
      throw createError({
        statusCode: 400,
        statusMessage: 'Confirmation text "CLEAR" is required'
      })
    }

    const db = await getDatabaseConnection()
    
    // First, verify the table exists
    const [tables] = await db.execute(`
      SELECT TABLE_NAME 
      FROM information_schema.TABLES 
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = ?
    `, [tableName])

    if ((tables as any[]).length === 0) {
      throw createError({
        statusCode: 404,
        statusMessage: `Table '${tableName}' not found`
      })
    }

    // Get row count before clearing
    const [countResult] = await db.execute(`SELECT COUNT(*) as count FROM \`${tableName}\``)
    const rowCount = (countResult as any)[0].count

    // Clear the table
    await db.execute(`TRUNCATE TABLE \`${tableName}\``)

    console.log(`Table '${tableName}' cleared successfully. Removed ${rowCount} rows.`)

    return {
      success: true,
      message: `Table '${tableName}' cleared successfully`,
      rowsRemoved: rowCount,
      tableName
    }
  } catch (error) {
    console.error('Error clearing table:', error)
    throw createError({
      statusCode: error.statusCode || 500,
      statusMessage: error.statusMessage || 'Failed to clear table'
    })
  }
})
