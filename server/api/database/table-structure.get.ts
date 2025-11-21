import { getDatabaseConnection } from '~/server/utils/database'

export default defineEventHandler(async (event) => {
  try {
    const query = getQuery(event)
    const tableName = query.table as string
    
    if (!tableName) {
      throw createError({
        statusCode: 400,
        message: 'Table name is required'
      })
    }
    
    // Validate table name to prevent SQL injection
    if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(tableName)) {
      throw createError({
        statusCode: 400,
        message: 'Invalid table name format'
      })
    }
    
    const db = await getDatabaseConnection()
    
    // First, check if the table exists
    const [tableExists] = await db.execute(`
      SELECT COUNT(*) as count 
      FROM information_schema.TABLES 
      WHERE TABLE_SCHEMA = DATABASE() 
      AND TABLE_NAME = ?
    `, [tableName])
    
    if ((tableExists as any)[0].count === 0) {
      throw createError({
        statusCode: 404,
        message: `Table '${tableName}' not found`
      })
    }
    
    // Get table structure
    const [columns] = await db.execute(`
      SELECT 
        COLUMN_NAME as \`name\`,
        DATA_TYPE as \`type\`,
        IS_NULLABLE as nullable,
        COLUMN_DEFAULT as default_value,
        COLUMN_KEY as \`key\`,
        EXTRA as extra,
        COLUMN_COMMENT as comment,
        CHARACTER_MAXIMUM_LENGTH as max_length,
        NUMERIC_PRECISION as \`precision\`,
        NUMERIC_SCALE as scale
      FROM information_schema.COLUMNS 
      WHERE TABLE_SCHEMA = DATABASE() 
      AND TABLE_NAME = ?
      ORDER BY ORDINAL_POSITION
    `, [tableName])
    
    // Get table indexes
    const [indexes] = await db.execute(`
      SELECT 
        INDEX_NAME as \`name\`,
        COLUMN_NAME as column_name,
        NON_UNIQUE as non_unique,
        INDEX_TYPE as \`type\`,
        CARDINALITY as cardinality
      FROM information_schema.STATISTICS 
      WHERE TABLE_SCHEMA = DATABASE() 
      AND TABLE_NAME = ?
      ORDER BY INDEX_NAME, SEQ_IN_INDEX
    `, [tableName])
    
    return {
      table: tableName,
      columns: columns as any[],
      indexes: indexes as any[]
    }
  } catch (error: any) {
    console.error('Error fetching table structure:', error)
    
    // If it's already a createError, re-throw it
    if (error.statusCode) {
      throw error
    }
    
    // Otherwise, create a generic error
    throw createError({
      statusCode: 500,
      message: `Failed to fetch table structure: ${error.message || 'Unknown error'}`
    })
  }
})
