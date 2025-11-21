import { getDatabaseConnection } from '~/server/utils/database'

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody(event)
    const { query: sqlQuery, limit = 100 } = body
    
    if (!sqlQuery || typeof sqlQuery !== 'string') {
      throw createError({
        statusCode: 400,
        statusMessage: 'SQL query is required'
      })
    }
    
    // Basic security checks
    const trimmedQuery = sqlQuery.trim().toLowerCase()
    const dangerousKeywords = ['drop', 'delete', 'update', 'insert', 'alter', 'create', 'truncate', 'replace']
    
    if (dangerousKeywords.some(keyword => trimmedQuery.includes(keyword))) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Only SELECT queries are allowed for security reasons'
      })
    }
    
    if (!trimmedQuery.startsWith('select')) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Only SELECT queries are allowed'
      })
    }
    
    const db = await getDatabaseConnection()
    
    // Add LIMIT if not present and limit is specified
    let finalQuery = sqlQuery
    if (limit > 0 && !trimmedQuery.includes('limit')) {
      finalQuery = `${sqlQuery} LIMIT ${parseInt(limit.toString())}`
    }
    
    const startTime = Date.now()
    const [rows] = await db.execute(finalQuery)
    const executionTime = Date.now() - startTime
    
    return {
      data: rows as any[],
      rowCount: (rows as any[]).length,
      executionTime,
      query: finalQuery
    }
  } catch (error) {
    console.error('Error executing database query:', error)
    throw createError({
      statusCode: 500,
      statusMessage: `Database query failed: ${error.message}`
    })
  }
})
