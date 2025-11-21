import { getDatabaseConnection } from '~/server/utils/database'

export default defineEventHandler(async (event) => {
  try {
    const query = getQuery(event)
    const tableName = query.table as string
    const page = parseInt(query.page as string) || 1
    const limit = parseInt(query.limit as string) || 50
    const search = query.search as string || ''
    const sortBy = query.sortBy as string || ''
    const sortOrder = query.sortOrder as string || 'ASC'
    
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
    
    // Validate sort order
    if (!['ASC', 'DESC'].includes(sortOrder.toUpperCase())) {
      throw createError({
        statusCode: 400,
        message: 'Invalid sort order. Must be ASC or DESC'
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
    
    // Get table columns for dynamic query building
    const [columns] = await db.execute(`
      SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
      FROM information_schema.COLUMNS 
      WHERE TABLE_SCHEMA = DATABASE() 
      AND TABLE_NAME = ?
      ORDER BY ORDINAL_POSITION
    `, [tableName])
    
    const columnNames = (columns as any[]).map(col => col.COLUMN_NAME)
    
    // Build WHERE clause for search
    let whereClause = ''
    let searchParams: any[] = []
    
    if (search.trim()) {
      const searchConditions = columnNames.map(col => `\`${col}\` LIKE ?`).join(' OR ')
      whereClause = `WHERE ${searchConditions}`
      searchParams = columnNames.map(() => `%${search}%`)
    }
    
    // Build ORDER BY clause
    let orderClause = ''
    if (sortBy && columnNames.includes(sortBy)) {
      orderClause = `ORDER BY \`${sortBy}\` ${sortOrder.toUpperCase()}`
    } else if (columnNames.length > 0) {
      // Default to first column if no sort specified
      orderClause = `ORDER BY \`${columnNames[0]}\` ASC`
    }
    
    // Calculate offset
    const offset = (page - 1) * limit
    
    // Get total count
    const [countResult] = await db.execute(`
      SELECT COUNT(*) as total 
      FROM \`${tableName}\` 
      ${whereClause}
    `, searchParams)
    
    const total = (countResult as any)[0].total
    
    // Get data
    const [data] = await db.execute(`
      SELECT * 
      FROM \`${tableName}\` 
      ${whereClause}
      ${orderClause}
      LIMIT ${parseInt(limit.toString())} OFFSET ${parseInt(offset.toString())}
    `, searchParams)
    
    // Get sample data for column type detection
    const [sampleData] = await db.execute(`
      SELECT * 
      FROM \`${tableName}\` 
      LIMIT 1
    `)
    
    return {
      table: tableName,
      columns: columnNames,
      data: data as any[],
      total,
      page,
      limit,
      totalPages: Math.ceil(total / limit),
      search,
      sortBy: sortBy || columnNames[0] || '',
      sortOrder: sortOrder.toUpperCase(),
      hasData: (data as any[]).length > 0,
      sampleRow: (sampleData as any[])[0] || null
    }
  } catch (error: any) {
    console.error('Error fetching table data:', error)
    
    // If it's already a createError, re-throw it
    if (error.statusCode) {
      throw error
    }
    
    // Otherwise, create a generic error
    throw createError({
      statusCode: 500,
      message: `Failed to fetch table data: ${error.message || 'Unknown error'}`
    })
  }
})
