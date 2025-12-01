import { getDatabaseConnection } from '~/server/utils/database'

export default defineEventHandler(async (event) => {
  try {
    const db = await getDatabaseConnection()
    
    // Get currently processing items (status = 'processing')
    const [processingItems] = await db.execute(`
      SELECT 
        id, tmdb_id, imdb_id, trakt_id,
        media_type, title, year, overview,
        status, processing_stage, processing_started_at,
        poster_url, thumb_url, fanart_url, backdrop_url,
        poster_image_format, thumb_image_format, fanart_image_format, backdrop_image_format,
        seasons_processing, total_seasons
      FROM unified_media
      WHERE status = 'processing'
      ORDER BY processing_started_at DESC
      LIMIT 10
    `)
    
    // Get processing statistics
    const [stats] = await db.execute(`
      SELECT 
        COUNT(*) as total_processing,
        SUM(CASE WHEN media_type = 'movie' THEN 1 ELSE 0 END) as movies_processing,
        SUM(CASE WHEN media_type = 'tv' THEN 1 ELSE 0 END) as tv_processing
      FROM unified_media
      WHERE status = 'processing'
    `)
    
    // Process items and add computed fields
    const items = (Array.isArray(processingItems) ? processingItems : []).map((row: any) => {
      const item = { ...row }
      // Add computed fields (matching unified-media API pattern)
      item.has_poster_image = !!row.poster_image_format
      item.has_thumb_image = !!row.thumb_image_format
      item.has_fanart_image = !!row.fanart_image_format
      item.has_backdrop_image = !!row.backdrop_image_format
      return item
    })
    
    const currentItem = items.length > 0 ? items[0] : null
    
    // Calculate progress percentage for TV shows
    const calculateProgress = (item: any) => {
      if (item.media_type === 'tv' && item.seasons_processing && item.total_seasons) {
        const processing = parseInt(item.seasons_processing) || 0
        const total = parseInt(item.total_seasons) || 1
        return Math.round((processing / total) * 100)
      }
      return 0
    }
    
    return {
      success: true,
      data: {
        currentItem: currentItem ? {
          id: currentItem.id,
          tmdb_id: currentItem.tmdb_id,
          title: currentItem.title,
          year: currentItem.year,
          media_type: currentItem.media_type,
          processing_stage: currentItem.processing_stage,
          processing_started_at: currentItem.processing_started_at,
          has_poster_image: currentItem.has_poster_image,
          has_thumb_image: currentItem.has_thumb_image,
          has_fanart_image: currentItem.has_fanart_image,
          seasons_processing: currentItem.seasons_processing,
          total_seasons: currentItem.total_seasons,
          progress_percentage: calculateProgress(currentItem)
        } : null,
        processingItems: items.map((item: any) => ({
          id: item.id,
          tmdb_id: item.tmdb_id,
          title: item.title,
          year: item.year,
          media_type: item.media_type,
          processing_stage: item.processing_stage,
          processing_started_at: item.processing_started_at,
          has_poster_image: item.has_poster_image,
          has_thumb_image: item.has_thumb_image,
          has_fanart_image: item.has_fanart_image
        })),
        stats: {
          total_processing: stats[0]?.total_processing || 0,
          movies_processing: stats[0]?.movies_processing || 0,
          tv_processing: stats[0]?.tv_processing || 0
        }
      }
    }
  } catch (error) {
    console.error('Error fetching processing status:', error)
    return {
      success: false,
      error: 'Failed to fetch processing status',
      data: {
        currentItem: null,
        processingItems: [],
        stats: {
          total_processing: 0,
          movies_processing: 0,
          tv_processing: 0
        }
      }
    }
  }
})

