import { getDatabaseConnection } from '~/server/utils/database'

export default defineEventHandler(async (event) => {
  try {
    const query = getQuery(event)
    const imdbId = query.imdb_id as string
    const tmdbId = query.tmdb_id ? parseInt(query.tmdb_id as string) : null

    if (!imdbId && !tmdbId) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Either imdb_id or tmdb_id query parameter is required'
      })
    }

    const db = await getDatabaseConnection()
    if (!db) {
      throw new Error('Failed to get database connection')
    }

    let exists = false
    let foundBy = ''
    let databaseId: number | null = null

    // Check if movie exists by IMDB ID or TMDB ID in unified_media table
    if (imdbId) {
      const [rows] = await db.execute(
        'SELECT id FROM unified_media WHERE imdb_id = ? AND media_type = ? LIMIT 1',
        [imdbId, 'movie']
      )
      const result = rows as any[]
      exists = result.length > 0
      if (exists && result[0]) {
        databaseId = result[0].id
      }
      foundBy = 'imdb_id'
    } else if (tmdbId) {
      const [rows] = await db.execute(
        'SELECT id FROM unified_media WHERE tmdb_id = ? AND media_type = ? LIMIT 1',
        [tmdbId, 'movie']
      )
      const result = rows as any[]
      exists = result.length > 0
      if (exists && result[0]) {
        databaseId = result[0].id
      }
      foundBy = 'tmdb_id'
    }

    return {
      success: true,
      data: {
        exists,
        foundBy,
        id: imdbId || tmdbId,
        databaseId
      }
    }
  } catch (error: any) {
    console.error('Error checking if movie exists:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to check if movie exists',
      data: { error: error.message }
    })
  }
})

