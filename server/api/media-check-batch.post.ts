import { getDatabaseConnection } from '~/server/utils/database'
import { readBody } from 'h3'

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody(event)
    const items = body.items as Array<{ tmdb_id?: number; imdb_id?: string; media_type?: string }>
    
    if (!items || !Array.isArray(items) || items.length === 0) {
      return {
        success: false,
        error: 'items array is required'
      }
    }
    
    try {
      const db = await getDatabaseConnection()
      
      // Build query to check multiple items
      // We'll check by tmdb_id first, then imdb_id as fallback
      const results = new Map<string, any>()
      
      // Group items by media_type for more efficient querying
      const itemsByType = new Map<string, typeof items>()
      items.forEach(item => {
        const mediaType = item.media_type || 'movie'
        if (!itemsByType.has(mediaType)) {
          itemsByType.set(mediaType, [])
        }
        itemsByType.get(mediaType)!.push(item)
      })
      
      // Check each media type separately
      for (const [mediaType, typeItems] of itemsByType.entries()) {
        // First, try to match by tmdb_id
        const tmdbIds = typeItems
          .map(item => item.tmdb_id)
          .filter((id): id is number => id !== undefined && id !== null)
        
        if (tmdbIds.length > 0) {
          const placeholders = tmdbIds.map(() => '?').join(',')
          const query = `SELECT id, tmdb_id, imdb_id, status, media_type FROM unified_media WHERE tmdb_id IN (${placeholders}) AND media_type = ?`
          const params = [...tmdbIds, mediaType]
          
          const [rows] = await db.execute(query, params)
          
          if (Array.isArray(rows)) {
            rows.forEach((row: any) => {
              const key = `tmdb_${row.tmdb_id}_${mediaType}`
              results.set(key, row)
            })
          }
        }
        
        // Then, try to match by imdb_id for items that weren't matched by tmdb_id
        const unmatchedItems = typeItems.filter(item => {
          const key = `tmdb_${item.tmdb_id}_${mediaType}`
          return item.tmdb_id && !results.has(key)
        })
        
        const imdbIds = unmatchedItems
          .map(item => item.imdb_id)
          .filter((id): id is string => id !== undefined && id !== null && id !== '')
        
        if (imdbIds.length > 0) {
          const placeholders = imdbIds.map(() => '?').join(',')
          const query = `SELECT id, tmdb_id, imdb_id, status, media_type FROM unified_media WHERE imdb_id IN (${placeholders}) AND media_type = ?`
          const params = [...imdbIds, mediaType]
          
          const [rows] = await db.execute(query, params)
          
          if (Array.isArray(rows)) {
            rows.forEach((row: any) => {
              const key = `imdb_${row.imdb_id}_${mediaType}`
              results.set(key, row)
            })
          }
        }
      }
      
      // Build response mapping items to their database matches
      const matches = new Map<string, any>()
      
      items.forEach(item => {
        const mediaType = item.media_type || 'movie'
        let match = null
        
        // Try tmdb_id first
        if (item.tmdb_id) {
          const key = `tmdb_${item.tmdb_id}_${mediaType}`
          match = results.get(key)
        }
        
        // Fallback to imdb_id
        if (!match && item.imdb_id) {
          const key = `imdb_${item.imdb_id}_${mediaType}`
          match = results.get(key)
        }
        
        // Create a unique key for this item
        const itemKey = item.tmdb_id 
          ? `tmdb_${item.tmdb_id}_${mediaType}` 
          : item.imdb_id 
            ? `imdb_${item.imdb_id}_${mediaType}` 
            : `${item.media_type}_${Math.random()}`
        
        matches.set(itemKey, match)
      })
      
      // Convert to array format for easier frontend consumption
      const matchArray = items.map(item => {
        const mediaType = item.media_type || 'movie'
        let match = null
        
        if (item.tmdb_id) {
          const key = `tmdb_${item.tmdb_id}_${mediaType}`
          match = results.get(key)
        }
        
        if (!match && item.imdb_id) {
          const key = `imdb_${item.imdb_id}_${mediaType}`
          match = results.get(key)
        }
        
        return {
          item,
          match: match ? {
            id: match.id,
            tmdb_id: match.tmdb_id,
            imdb_id: match.imdb_id,
            status: match.status,
            media_type: match.media_type
          } : null
        }
      })
      
      return {
        success: true,
        matches: matchArray
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
    console.error('Error in batch media check:', error)
    return {
      success: false,
      error: 'Failed to process request',
      details: error instanceof Error ? error.message : String(error)
    }
  }
})

