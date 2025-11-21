import { getDatabaseConnection } from '~/server/utils/database'

export default defineEventHandler(async (event) => {
  try {
    const query = getQuery(event)
    const tmdbId = query.tmdbId as string
    const mediaType = query.mediaType as string
    
    if (!tmdbId) {
      return {
        success: false,
        error: 'tmdbId parameter is required'
      }
    }
    
    try {
      const db = await getDatabaseConnection()
      
      // Check if media exists in unified_media table
      // If mediaType is provided, filter by it as well
      let query: string
      let params: any[]
      
      if (mediaType) {
        query = 'SELECT id, tmdb_id, status, media_type FROM unified_media WHERE tmdb_id = ? AND media_type = ?'
        params = [parseInt(tmdbId), mediaType]
      } else {
        query = 'SELECT id, tmdb_id, status, media_type FROM unified_media WHERE tmdb_id = ?'
        params = [parseInt(tmdbId)]
      }
      
      const [rows] = await db.execute(query, params)
      
      const mediaExists = Array.isArray(rows) && rows.length > 0
      
      return {
        success: true,
        exists: mediaExists,
        data: mediaExists ? rows[0] : null
      }
      
    } catch (error) {
      console.error('Error checking media in database:', error)
      return {
        success: false,
        error: 'Failed to check database',
        details: error instanceof Error ? error.message : String(error)
      }
    }
  } catch (error) {
    console.error('Error in media check:', error)
    return {
      success: false,
      error: 'Failed to process request',
      details: error instanceof Error ? error.message : String(error)
    }
  }
})

