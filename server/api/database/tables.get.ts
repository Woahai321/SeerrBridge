import { getDatabaseConnection } from '~/server/utils/database'

export default defineEventHandler(async (event) => {
  try {
    const db = await getDatabaseConnection()
    
    // Get all tables in the database
    const [tables] = await db.execute(`
      SELECT 
        TABLE_NAME as name,
        TABLE_ROWS as row_count,
        DATA_LENGTH as data_size,
        INDEX_LENGTH as index_size,
        (DATA_LENGTH + INDEX_LENGTH) as total_size,
        TABLE_COLLATION as collation,
        ENGINE as engine,
        CREATE_TIME as created_at,
        UPDATE_TIME as updated_at
      FROM information_schema.TABLES 
      WHERE TABLE_SCHEMA = DATABASE()
      ORDER BY TABLE_NAME
    `)
    
    // Get accurate row counts for each table using COUNT(*)
    const tablesWithAccurateCounts = await Promise.all(
      (tables as any[]).map(async (table) => {
        try {
          const [countResult] = await db.execute(`SELECT COUNT(*) as exact_count FROM \`${table.name}\``)
          const exactCount = (countResult as any)[0].exact_count
          
          return {
            ...table,
            row_count: parseInt(exactCount) || 0,
            data_size: parseInt(table.data_size) || 0,
            index_size: parseInt(table.index_size) || 0,
            total_size: parseInt(table.data_size) + parseInt(table.index_size) || 0,
            // Use the exact count for more accurate display
            exact_row_count: parseInt(exactCount) || 0
          }
        } catch (error) {
          console.warn(`Could not get exact count for table ${table.name}:`, error)
          return {
            ...table,
            row_count: parseInt(table.row_count) || 0,
            data_size: parseInt(table.data_size) || 0,
            index_size: parseInt(table.index_size) || 0,
            total_size: parseInt(table.data_size) + parseInt(table.index_size) || 0
          }
        }
      })
    )
    
    console.log('Fetched tables data with accurate counts:', {
      count: tablesWithAccurateCounts.length,
      tables: tablesWithAccurateCounts.map(t => ({ 
        name: t.name, 
        rows: t.row_count, 
        exact_rows: t.exact_row_count,
        size: t.total_size 
      }))
    })
    
    return {
      tables: tablesWithAccurateCounts,
      database: process.env.DB_NAME || 'seerrbridge'
    }
  } catch (error) {
    console.error('Error fetching database tables:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to fetch database tables'
    })
  }
})
