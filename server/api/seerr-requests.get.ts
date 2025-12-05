import { getOverseerrConfig } from '~/server/utils/overseerr-config'
import { getDatabaseConnection } from '~/server/utils/database'

export default defineEventHandler(async (event) => {
  // Track partial failures
  let mediaDetailsErrors: string[] = []
  
  try {
    const query = getQuery(event)
    const page = parseInt(query.page as string) || 1
    const limit = Math.min(parseInt(query.limit as string) || 20, 100)
    const skip = (page - 1) * limit
    
    const status = query.status as string
    const mediaType = query.mediaType as string
    const search = query.search as string
    const sortBy = query.sortBy as string || 'added'
    
    // Get Overseerr configuration
    const { baseUrl: overseerrBaseUrl, apiKey: overseerrApiKey } = await getOverseerrConfig()
    
    if (!overseerrBaseUrl || !overseerrApiKey) {
      return {
        success: false,
        error: 'Overseerr not configured',
        data: {
          requests: [],
          stats: getEmptyStats(),
          pagination: {
            page: 1,
            limit,
            total: 0,
            total_pages: 0,
            has_next: false,
            has_prev: false
          }
        }
      }
    }
    
    // Remove trailing slash
    const baseUrl = overseerrBaseUrl.replace(/\/$/, '')
    
    // PHASE 1: Fetch ALL requests from Overseerr (handle pagination if needed)
    console.log(`[Phase 1] Fetching all requests from Overseerr...`)
    let allRequests: any[] = []
    let currentPage = 1
    const pageSize = 1000 // Overseerr's max page size
    let hasMorePages = true
    
    while (hasMorePages) {
      // Try with skip parameter first, fallback to just take if skip doesn't work
      let requestUrl = `${baseUrl}/api/v1/request?take=${pageSize}&filter=all&sort=${sortBy}`
      if (currentPage > 1) {
        requestUrl += `&skip=${(currentPage - 1) * pageSize}`
      }
      console.log(`[Phase 1] Fetching page ${currentPage} from: ${requestUrl.replace(overseerrApiKey, '[REDACTED]')}`)
      
      const response = await fetch(requestUrl, {
        method: 'GET',
        headers: {
          'X-Api-Key': overseerrApiKey,
          'Content-Type': 'application/json'
        }
      })
      
      if (!response.ok) {
        const errorText = await response.text()
        console.error(`[SeerrRequests] Overseerr API error: ${response.status} - ${errorText}`)
        return {
          success: false,
          error: `Overseerr API error: ${response.status} ${response.statusText}`,
          data: {
            requests: [],
            stats: getEmptyStats(),
            pagination: {
              page: 1,
              limit,
              total: 0,
              total_pages: 0,
              has_next: false,
              has_prev: false
            }
          }
        }
      }
      
      const data = await response.json()
      const pageRequests: any[] = data.results || []
      allRequests = allRequests.concat(pageRequests)
      
      // Check if there are more pages
      const totalResults = data.pageInfo?.totalResults || data.total || pageRequests.length
      const hasNext = data.pageInfo?.hasNextPage || (pageRequests.length === pageSize && allRequests.length < totalResults)
      
      console.log(`[Phase 1] Fetched page ${currentPage}: ${pageRequests.length} requests (total so far: ${allRequests.length})`)
      
      if (!hasNext || pageRequests.length < pageSize) {
        hasMorePages = false
      } else {
        currentPage++
      }
    }
    
    console.log(`[Phase 1] Completed: Fetched ${allRequests.length} total requests from Overseerr`)
    
    // PHASE 2: Extract unique TMDB IDs and check cache / batch fetch media details
    console.log(`[Phase 2] Extracting unique TMDB IDs from ${allRequests.length} requests...`)
    const uniqueMediaMap = new Map<string, { tmdbId: number; mediaType: string; requestIds: number[]; maxUpdatedAt: string }>()
    
    // Extract unique media and track request metadata for change detection
    for (const req of allRequests) {
      const media = req.media || {}
      const tmdbId = media.tmdbId || media.tmdb_id
      const reqMediaType = media.mediaType || media.media_type
      const requestUpdatedAt = req.updatedAt || req.updated_at || req.createdAt || req.created_at
      
      if (tmdbId && reqMediaType) {
        const key = `${tmdbId}_${reqMediaType}`
        if (!uniqueMediaMap.has(key)) {
          uniqueMediaMap.set(key, {
            tmdbId,
            mediaType: reqMediaType,
            requestIds: [req.id],
            maxUpdatedAt: requestUpdatedAt
          })
        } else {
          const existing = uniqueMediaMap.get(key)!
          existing.requestIds.push(req.id)
          // Track the most recent updated_at
          if (requestUpdatedAt && (!existing.maxUpdatedAt || requestUpdatedAt > existing.maxUpdatedAt)) {
            existing.maxUpdatedAt = requestUpdatedAt
          }
        }
      }
    }
    
    console.log(`[Phase 2] Found ${uniqueMediaMap.size} unique media items`)
    
    // Check cache for existing media details
    const db = await getDatabaseConnection()
    
    // Ensure cache table exists (migration check)
    try {
      await db.execute(`
        CREATE TABLE IF NOT EXISTS overseerr_media_cache (
          id INT AUTO_INCREMENT PRIMARY KEY,
          tmdb_id INT NOT NULL,
          media_type ENUM('movie', 'tv') NOT NULL,
          media_details JSON NOT NULL,
          last_fetched_at DATETIME NOT NULL,
          last_request_updated_at DATETIME NULL,
          request_ids JSON NULL,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          UNIQUE KEY unique_tmdb_media (tmdb_id, media_type),
          INDEX idx_tmdb_id (tmdb_id),
          INDEX idx_media_type (media_type),
          INDEX idx_last_fetched_at (last_fetched_at),
          INDEX idx_last_request_updated_at (last_request_updated_at)
        )
      `)
    } catch (migrationError) {
      console.warn(`[Phase 2] Cache table migration check failed (may already exist):`, migrationError)
    }
    
    const mediaDetailsMap = new Map<string, any>()
    const needsFetch = new Map<string, { tmdbId: number; mediaType: string; requestIds: number[]; maxUpdatedAt: string }>()
    let cacheHits = 0
    let cacheMisses = 0
    
    for (const [key, { tmdbId, mediaType, requestIds, maxUpdatedAt }] of uniqueMediaMap.entries()) {
      try {
        const [cacheRows] = await db.execute(
          'SELECT media_details, last_fetched_at, last_request_updated_at, request_ids FROM overseerr_media_cache WHERE tmdb_id = ? AND media_type = ?',
          [tmdbId, mediaType]
        ) as any
        
        if (cacheRows && cacheRows.length > 0) {
          const cache = cacheRows[0]
          const cachedUpdatedAt = cache.last_request_updated_at ? new Date(cache.last_request_updated_at).toISOString() : null
          const requestUpdatedAt = maxUpdatedAt ? new Date(maxUpdatedAt).toISOString() : null
          
          // Check if any request has been updated since cache was created
          const needsRefresh = !cachedUpdatedAt || !requestUpdatedAt || requestUpdatedAt > cachedUpdatedAt
          
          if (!needsRefresh) {
            // Use cached data
            mediaDetailsMap.set(key, JSON.parse(cache.media_details))
            cacheHits++
            console.log(`[Phase 2] Cache HIT for ${mediaType} ${tmdbId}`)
            
            // Update cache metadata (request_ids and last_request_updated_at) if needed
            const currentRequestIds = JSON.parse(cache.request_ids || '[]')
            const allRequestIds = [...new Set([...currentRequestIds, ...requestIds])]
            const newMaxUpdatedAt = requestUpdatedAt && (!cachedUpdatedAt || requestUpdatedAt > cachedUpdatedAt) 
              ? requestUpdatedAt 
              : cachedUpdatedAt
            
            if (JSON.stringify(allRequestIds.sort()) !== JSON.stringify(currentRequestIds.sort()) || 
                newMaxUpdatedAt !== cachedUpdatedAt) {
              // Convert ISO string to MySQL DATETIME format (YYYY-MM-DD HH:MM:SS)
              const mysqlDateTime = newMaxUpdatedAt 
                ? new Date(newMaxUpdatedAt).toISOString().replace('T', ' ').substring(0, 19)
                : null
              
              await db.execute(
                'UPDATE overseerr_media_cache SET request_ids = ?, last_request_updated_at = ? WHERE tmdb_id = ? AND media_type = ?',
                [JSON.stringify(allRequestIds), mysqlDateTime, tmdbId, mediaType]
              )
            }
          } else {
            // Cache is stale, need to fetch
            needsFetch.set(key, { tmdbId, mediaType, requestIds, maxUpdatedAt })
            cacheMisses++
            console.log(`[Phase 2] Cache MISS/STALE for ${mediaType} ${tmdbId} (cache: ${cachedUpdatedAt}, request: ${requestUpdatedAt})`)
          }
        } else {
          // No cache, need to fetch
          needsFetch.set(key, { tmdbId, mediaType, requestIds, maxUpdatedAt })
          cacheMisses++
          console.log(`[Phase 2] Cache MISS for ${mediaType} ${tmdbId}`)
        }
      } catch (error) {
        console.error(`[Phase 2] Error checking cache for ${mediaType} ${tmdbId}:`, error)
        // On error, fetch from API
        needsFetch.set(key, { tmdbId, mediaType, requestIds, maxUpdatedAt })
        cacheMisses++
      }
    }
    
    console.log(`[Phase 2] Cache stats: ${cacheHits} hits, ${cacheMisses} misses/stale`)
    
    // Batch fetch media details for items not in cache or stale
    const batchSize = 10
    const needsFetchArray = Array.from(needsFetch.values())
    
    for (let i = 0; i < needsFetchArray.length; i += batchSize) {
      const batch = needsFetchArray.slice(i, i + batchSize)
      await Promise.all(batch.map(async ({ tmdbId, mediaType, requestIds, maxUpdatedAt }) => {
        const key = `${tmdbId}_${mediaType}`
        try {
          const mediaDetailsUrl = `${baseUrl}/api/v1/${mediaType}/${tmdbId}?language=en`
          
          const mediaResponse = await fetch(mediaDetailsUrl, {
            method: 'GET',
            headers: {
              'X-Api-Key': overseerrApiKey,
              'Content-Type': 'application/json'
            }
          })
          
          if (mediaResponse.ok) {
            const mediaDetails = await mediaResponse.json()
            mediaDetailsMap.set(key, mediaDetails)
            console.log(`[Phase 2] Successfully fetched ${mediaType} ${tmdbId}: title="${mediaDetails.title || mediaDetails.name || 'N/A'}", posterPath="${mediaDetails.posterPath || 'N/A'}"`)
            
            // Update cache
            try {
              // Convert ISO strings to MySQL DATETIME format (YYYY-MM-DD HH:MM:SS)
              const now = new Date().toISOString().replace('T', ' ').substring(0, 19)
              const requestUpdatedAt = maxUpdatedAt 
                ? new Date(maxUpdatedAt).toISOString().replace('T', ' ').substring(0, 19)
                : now
              
              await db.execute(
                `INSERT INTO overseerr_media_cache (tmdb_id, media_type, media_details, last_fetched_at, last_request_updated_at, request_ids)
                 VALUES (?, ?, ?, ?, ?, ?)
                 ON DUPLICATE KEY UPDATE
                   media_details = VALUES(media_details),
                   last_fetched_at = VALUES(last_fetched_at),
                   last_request_updated_at = VALUES(last_request_updated_at),
                   request_ids = VALUES(request_ids)`,
                [tmdbId, mediaType, JSON.stringify(mediaDetails), now, requestUpdatedAt, JSON.stringify(requestIds)]
              )
              console.log(`[Phase 2] Cached media details for ${mediaType} ${tmdbId}`)
            } catch (cacheError) {
              console.error(`[Phase 2] Error caching media details for ${mediaType} ${tmdbId}:`, cacheError)
            }
          } else {
            const errorText = await mediaResponse.text()
            const errorMsg = `Failed to fetch media details for ${mediaType} ${tmdbId}: ${mediaResponse.status} ${mediaResponse.statusText}`
            console.warn(`[Phase 2] ${errorMsg}`, errorText.substring(0, 200))
            mediaDetailsErrors.push(errorMsg)
          }
        } catch (error) {
          const errorMsg = `Error fetching media details for ${mediaType} ${tmdbId}: ${error instanceof Error ? error.message : 'Unknown error'}`
          console.error(`[Phase 2] ${errorMsg}`, error)
          mediaDetailsErrors.push(errorMsg)
        }
      }))
      
      console.log(`[Phase 2] Fetched media details: ${i + batch.length}/${needsFetchArray.length}`)
    }
    
    console.log(`[Phase 2] Completed: ${cacheHits} from cache, ${mediaDetailsMap.size - cacheHits} fetched from API`)
    
    // PHASE 3: Merge media details back into all requests
    console.log(`[Phase 3] Merging media details into ${allRequests.length} requests...`)
    let mergeCount = 0
    let noDetailsCount = 0
    
    for (const req of allRequests) {
      const media = req.media || {}
      const tmdbId = media.tmdbId || media.tmdb_id
      const reqMediaType = media.mediaType || media.media_type
      
      if (tmdbId && reqMediaType) {
        const key = `${tmdbId}_${reqMediaType}`
        const mediaDetails = mediaDetailsMap.get(key)
        
        if (mediaDetails) {
          mergeCount++
          
          // Extract title - Movies use 'title', TV shows use 'name'
          const beforeTitle = media.title || media.name || 'Unknown Title'
          if (reqMediaType === 'movie' && mediaDetails.title) {
            media.title = mediaDetails.title
          } else if (reqMediaType === 'tv' && mediaDetails.name) {
            media.name = mediaDetails.name
            media.title = mediaDetails.name // Also set title for consistency
          }
          
          // Fallback: if we didn't get the expected field, try the other
          if (!media.title && !media.name) {
            if (mediaDetails.title) {
              media.title = mediaDetails.title
            } else if (mediaDetails.name) {
              media.name = mediaDetails.name
              media.title = mediaDetails.name
            }
          }
          
          // Debug log for title extraction
          if (beforeTitle === 'Unknown Title' && (media.title || media.name) !== 'Unknown Title') {
            console.log(`[Phase 3] Fixed title for ${reqMediaType} ${tmdbId}: "${beforeTitle}" -> "${media.title || media.name}"`)
          }
          
          // Extract poster path - CRITICAL: Request endpoint doesn't return this
          if (mediaDetails.posterPath) {
            media.posterPath = mediaDetails.posterPath
          } else if (mediaDetails.poster_path) {
            media.posterPath = mediaDetails.poster_path
          }
          
          // Extract backdrop path
          if (mediaDetails.backdropPath) {
            media.backdropPath = mediaDetails.backdropPath
          } else if (mediaDetails.backdrop_path) {
            media.backdropPath = mediaDetails.backdrop_path
          }
          
          // Extract overview
          if (mediaDetails.overview) {
            media.overview = mediaDetails.overview
          }
          
          // Extract release dates
          if (mediaDetails.releaseDate) {
            media.releaseDate = mediaDetails.releaseDate
          }
          if (mediaDetails.firstAirDate) {
            media.firstAirDate = mediaDetails.firstAirDate
            if (!media.releaseDate) {
              media.releaseDate = mediaDetails.firstAirDate
            }
          }
          if (mediaDetails.lastAirDate) {
            media.lastAirDate = mediaDetails.lastAirDate
          }
          
          // Extract rating/vote information
          if (mediaDetails.voteAverage !== undefined) {
            media.voteAverage = mediaDetails.voteAverage
          }
          if (mediaDetails.voteCount !== undefined) {
            media.voteCount = mediaDetails.voteCount
          }
          if (mediaDetails.popularity !== undefined) {
            media.popularity = mediaDetails.popularity
          }
          
          // Extract runtime
          if (mediaDetails.runtime !== undefined) {
            media.runtime = mediaDetails.runtime
          }
          if (mediaDetails.episodeRunTime && Array.isArray(mediaDetails.episodeRunTime) && mediaDetails.episodeRunTime.length > 0) {
            media.episodeRuntime = mediaDetails.episodeRunTime[0]
          }
          
          // Extract genres
          if (mediaDetails.genres && Array.isArray(mediaDetails.genres)) {
            media.genres = mediaDetails.genres.map((g: any) => ({
              id: g.id,
              name: g.name
            }))
          }
          
          // Extract IMDB ID
          if (mediaDetails.imdbId) {
            media.imdbId = mediaDetails.imdbId
          } else if (mediaDetails.externalIds && mediaDetails.externalIds.imdbId) {
            media.imdbId = mediaDetails.externalIds.imdbId
          }
          
          // Extract external IDs
          if (mediaDetails.externalIds) {
            if (mediaDetails.externalIds.tvdbId && !media.tvdbId) {
              media.tvdbId = mediaDetails.externalIds.tvdbId
            }
          }
          
          // For TV shows, extract season information
          if (reqMediaType === 'tv' && mediaDetails.seasons && Array.isArray(mediaDetails.seasons)) {
            media.allSeasons = mediaDetails.seasons.map((season: any) => ({
              id: season.id,
              seasonNumber: season.seasonNumber,
              name: season.name,
              overview: season.overview || '',
              episodeCount: season.episodeCount || 0,
              airDate: season.airDate || season.air_date,
              posterPath: season.posterPath || season.poster_path
            }))
            
            if (mediaDetails.numberOfSeasons !== undefined) {
              media.numberOfSeasons = mediaDetails.numberOfSeasons
            }
            if (mediaDetails.numberOfEpisodes !== undefined) {
              media.numberOfEpisodes = mediaDetails.numberOfEpisodes
            }
          }
        } else {
          noDetailsCount++
          if (noDetailsCount <= 5) {
            console.warn(`[Phase 3] No media details found for key: ${key} (tmdbId: ${tmdbId}, mediaType: ${reqMediaType})`)
          }
        }
      }
    }
    
    console.log(`[Phase 3] Completed: Merged media details into ${mergeCount} requests, ${noDetailsCount} requests had no details available`)
    
    // PHASE 4: Filter requests (after media details are merged)
    console.log(`[Phase 4] Filtering ${allRequests.length} requests...`)
    
    if (status) {
      const statusMap: Record<string, number> = {
        'pending': 1,
        'approved': 2,
        'processing': 3,
        'failed': 4,
        'available': 5,
        'completed': 5,
        'unavailable': -1,
        'deleted': -2
      }
      const statusNum = statusMap[status]
      if (statusNum !== undefined) {
        allRequests = allRequests.filter(req => req.status === statusNum)
      }
    }
    
    if (mediaType) {
      allRequests = allRequests.filter(req => {
        const reqMediaType = req.media?.mediaType || req.media?.media_type
        return reqMediaType === mediaType
      })
    }
    
    if (search) {
      const searchLower = search.toLowerCase()
      allRequests = allRequests.filter(req => {
        const media = req.media || {}
        const title = media.title || media.name || ''
        const overview = media.overview || ''
        return title.toLowerCase().includes(searchLower) || overview.toLowerCase().includes(searchLower)
      })
    }
    
    console.log(`[Phase 4] Completed: Filtered to ${allRequests.length} requests`)
    
    // Calculate stats from filtered requests
    const stats = calculateStats(allRequests)
    
    // PHASE 5: Apply pagination LAST (after all media details are merged)
    const total = allRequests.length
    const safeSkip = Math.min(skip, total)
    const paginatedRequests = allRequests.slice(safeSkip, safeSkip + limit)
    const hasNext = safeSkip + limit < total
    
    console.log(`[Phase 5] Pagination: Returning ${paginatedRequests.length} requests (page ${page}, total: ${total})`)
    
    // Transform to frontend format
    const transformedRequests = paginatedRequests.map(req => {
      const media = req.media || {}
      const mediaType = media.mediaType || media.media_type || 'movie'
      
      // Extract title - use merged data
      let title = media.title || media.name || 'Unknown Title'
      
      // Extract other fields
      const posterPath = media.posterPath || media.poster_path
      const backdropPath = media.backdropPath || media.backdrop_path
      const overview = media.overview
      const releaseDate = media.releaseDate || media.release_date
      const firstAirDate = media.firstAirDate || media.first_air_date
      const voteAverage = media.voteAverage || media.vote_average
      
      return {
        id: req.id,
        request_id: req.id,
        status: req.status,
        status_label: getStatusLabel(req.status),
        media_status: media.status || 0,
        media_status_label: getMediaStatusLabel(media.status || 0),
        created_at: req.createdAt || req.created_at,
        updated_at: req.updatedAt || req.updated_at,
        requested_by: req.requestedBy || req.requested_by || {
          id: 0,
          email: '',
          username: 'Unknown',
          displayName: 'Unknown'
        },
        media: {
          id: media.id || 0,
          media_type: mediaType,
          tmdb_id: media.tmdbId || media.tmdb_id || 0,
          tvdb_id: media.tvdbId || media.tvdb_id,
          title: title,
          year: media.year,
          release_date: releaseDate,
          first_air_date: firstAirDate,
          last_air_date: media.lastAirDate || media.last_air_date,
          poster_path: posterPath,
          backdrop_path: backdropPath,
          overview: overview,
          status: media.status || 0,
          status4k: media.status4k || media.status_4k,
          vote_average: voteAverage,
          vote_count: media.voteCount || media.vote_count,
          popularity: media.popularity,
          runtime: media.runtime,
          episode_runtime: media.episodeRuntime || media.episode_runtime,
          genres: media.genres || [],
          all_seasons: media.allSeasons || [],
          number_of_seasons: media.numberOfSeasons,
          number_of_episodes: media.numberOfEpisodes
        },
        seasons: req.seasons || [],
        season_count: req.seasons?.length || 0,
        aggregated_request_ids: [req.id],
        is4k: req.is4k || false,
        has_unified_media: false
      }
    })
    
    console.log(`[SeerrRequests] Returning ${transformedRequests.length} requests (page ${page})`)
    
    const response: any = {
      success: true,
      data: {
        requests: transformedRequests,
        stats,
        pagination: {
          page,
          limit,
          total,
          total_pages: Math.ceil(total / limit),
          has_next: hasNext,
          has_prev: page > 1
        }
      }
    }
    
    // Add warnings for partial failures
    if (mediaDetailsErrors.length > 0) {
      response.warnings = [`Failed to fetch media details for ${mediaDetailsErrors.length} request(s)`]
    }
    
    return response
    
  } catch (error) {
    console.error('[SeerrRequests] Error:', error)
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to fetch requests',
      data: {
        requests: [],
        stats: getEmptyStats(),
        pagination: {
          page: 1,
          limit: 20,
          total: 0,
          total_pages: 0,
          has_next: false,
          has_prev: false
        }
      }
    }
  }
})

function getStatusLabel(status: number): string {
  if (status === 1) return 'pending'
  if (status === 2) return 'approved'
  if (status === 3) return 'processing'
  if (status === 4) return 'failed'
  if (status === 5) return 'available'
  if (status === -1) return 'unavailable'
  if (status === -2) return 'deleted'
  return 'unknown'
}

function getMediaStatusLabel(status: number): string {
  const statusMap: Record<number, string> = {
    1: 'unknown',
    2: 'partial',
    3: 'processing',
    4: 'partially_available',
    5: 'available',
    6: 'unavailable'
  }
  return statusMap[status] || 'unknown'
}

function getEmptyStats() {
  return {
    total_requests: 0,
    total_movies: 0,
    total_tv_shows: 0,
    pending_count: 0,
    approved_count: 0,
    processing_count: 0,
    failed_count: 0,
    available_count: 0,
    unavailable_count: 0,
    deleted_count: 0,
    movies_pending: 0,
    movies_approved: 0,
    movies_processing: 0,
    movies_failed: 0,
    movies_available: 0,
    movies_unavailable: 0,
    movies_deleted: 0,
    tv_pending: 0,
    tv_approved: 0,
    tv_processing: 0,
    tv_failed: 0,
    tv_available: 0,
    tv_unavailable: 0,
    tv_deleted: 0
  }
}

function calculateStats(requests: any[]) {
  const stats = getEmptyStats()
  
  stats.total_requests = requests.length
  stats.total_movies = requests.filter(r => {
    const mediaType = r.media?.mediaType || r.media?.media_type
    return mediaType === 'movie'
  }).length
  stats.total_tv_shows = requests.filter(r => {
    const mediaType = r.media?.mediaType || r.media?.media_type
    return mediaType === 'tv'
  }).length
  
  requests.forEach(req => {
    const status = req.status
    const mediaType = req.media?.mediaType || req.media?.media_type || 'movie'
    
    // Count by status
    if (status === 1) stats.pending_count++
    if (status === 2) stats.approved_count++
    if (status === 3) stats.processing_count++
    if (status === 4) stats.failed_count++
    if (status === 5) stats.available_count++
    if (status === -1) stats.unavailable_count++
    if (status === -2) stats.deleted_count++
    
    // Count by media type and status
    if (mediaType === 'movie') {
      if (status === 1) stats.movies_pending++
      if (status === 2) stats.movies_approved++
      if (status === 3) stats.movies_processing++
      if (status === 4) stats.movies_failed++
      if (status === 5) stats.movies_available++
      if (status === -1) stats.movies_unavailable++
      if (status === -2) stats.movies_deleted++
    } else if (mediaType === 'tv') {
      if (status === 1) stats.tv_pending++
      if (status === 2) stats.tv_approved++
      if (status === 3) stats.tv_processing++
      if (status === 4) stats.tv_failed++
      if (status === 5) stats.tv_available++
      if (status === -1) stats.tv_unavailable++
      if (status === -2) stats.tv_deleted++
    }
  })
  
  return stats
}
