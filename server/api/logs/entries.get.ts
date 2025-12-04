import { getLogEntries } from '~/server/utils/database'

export default defineEventHandler(async (event) => {
  try {
    const query = getQuery(event)
    const page = parseInt(query.page as string) || 1
    const limit = parseInt(query.limit as string) || 50
    const level = query.level as string
    
    const result = await getLogEntries(page, limit, level)
    
    return {
      entries: result.entries,
      total: result.total,
      page,
      limit
    }
  } catch (error: any) {
    console.error('Error fetching log entries:', {
      message: error.message,
      code: error.code,
      errno: error.errno
    })
    
    // If database connection fails, return empty result instead of error
    if (error.code === 'ECONNREFUSED' || error.code === 'ETIMEDOUT' || error.errno === 2003 || error.errno === 1045) {
      console.warn('Database not available, returning empty logs')
      return {
        entries: [],
        total: 0,
        page,
        limit
      }
    }
    
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to fetch log entries',
      data: { error: error.message }
    })
  }
})
