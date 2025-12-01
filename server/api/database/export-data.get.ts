import { getDatabaseConnection } from '~/server/utils/database'

export default defineEventHandler(async (event) => {
  try {
    const query = getQuery(event)
    const tableName = query.table as string
    const format = query.format as string || 'json'
    const limit = parseInt(query.limit as string) || 1000
    
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
    
    // Validate format
    if (!['json', 'csv'].includes(format.toLowerCase())) {
      throw createError({
        statusCode: 400,
        message: 'Invalid format. Must be json or csv'
      })
    }
    
    const db = await getDatabaseConnection()
    
    // Check if table exists
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
    
    // Get all data
    const [data] = await db.execute(`
      SELECT * 
      FROM \`${tableName}\` 
      LIMIT ${parseInt(limit.toString())}
    `)
    
    const rows = data as any[]
    
    if (format.toLowerCase() === 'csv') {
      // Generate CSV
      if (rows.length === 0) {
        return new Response('', {
          headers: {
            'Content-Type': 'text/csv',
            'Content-Disposition': `attachment; filename="${tableName}.csv"`
          }
        })
      }
      
      const columns = Object.keys(rows[0])
      const csvHeader = columns.join(',')
      const csvRows = rows.map(row => 
        columns.map(col => {
          const value = row[col]
          if (value === null) return ''
          if (typeof value === 'string' && (value.includes(',') || value.includes('"') || value.includes('\n'))) {
            return `"${value.replace(/"/g, '""')}"`
          }
          return value
        }).join(',')
      )
      
      const csvContent = [csvHeader, ...csvRows].join('\n')
      
      return new Response(csvContent, {
        headers: {
          'Content-Type': 'text/csv',
          'Content-Disposition': `attachment; filename="${tableName}.csv"`
        }
      })
    } else {
      // Return JSON
      return {
        table: tableName,
        data: rows,
        count: rows.length,
        exported_at: new Date().toISOString()
      }
    }
  } catch (error: any) {
    console.error('Error exporting table data:', error)
    
    if (error.statusCode) {
      throw error
    }
    
    throw createError({
      statusCode: 500,
      message: `Failed to export table data: ${error.message || 'Unknown error'}`
    })
  }
})
