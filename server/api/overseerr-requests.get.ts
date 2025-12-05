import { getOverseerrConfig } from '~/server/utils/overseerr-config'
import { getDatabaseConnection } from '~/server/utils/database'

interface OverseerrRequest {
  id: number
  status: number
  createdAt: string
  updatedAt: string
  requestedBy: {
    id: number
    email: string
    username: string
    displayName: string
    avatar?: string
  }
  media: {
    id: number
    mediaType: 'movie' | 'tv'
    tmdbId: number
    tvdbId?: number
    status: number
    status4k?: number
    title: string
    releaseDate?: string
    posterPath?: string
    backdropPath?: string
    overview?: string
    seasons?: Array<{
      id: number
      seasonNumber: number
      status: number
      status4k?: number
    }>
  }
  seasons?: Array<{
    id: number
    seasonNumber: number
    status: number
    status4k?: number
  }>
  is4k?: boolean
}

interface AggregatedRequest extends OverseerrRequest {
  aggregated_request_ids?: number[]
  seasonCount?: number
}

function aggregateTvRequestsByMediaId(requests: OverseerrRequest[]): AggregatedRequest[] {
  // Use string keys to support both numeric (TV) and string (movie) keys
  const mediaGroups: Record<string, OverseerrRequest[]> = {}
  
  for (const request of requests) {
    // Validate request has required properties
    if (!request || !request.media || !request.media.mediaType) {
      console.warn('Skipping invalid request:', request)
      continue
    }
    
    const mediaId = request.media.id
    const mediaType = request.media.mediaType
    
    if (mediaType === 'tv') {
      // For TV shows, group by media ID to aggregate multiple requests for same show
      const key = `tv_${mediaId}`
      if (!mediaGroups[key]) {
        mediaGroups[key] = []
      }
      mediaGroups[key].push(request)
    } else if (mediaType === 'movie') {
      // For movies, keep them separate (one request per movie)
      const key = `movie_${request.id}`
      mediaGroups[key] = [request]
    } else {
      // Unknown media type, skip or handle as individual
      console.warn('Unknown media type:', mediaType, 'for request:', request.id)
      const key = `unknown_${request.id}`
      mediaGroups[key] = [request]
    }
  }
  
  const aggregatedRequests: AggregatedRequest[] = []
  
  for (const [key, groupRequests] of Object.entries(mediaGroups)) {
    if (!groupRequests || groupRequests.length === 0) {
      continue
    }
    
    if (groupRequests.length === 1) {
      // Single request, add as-is
      aggregatedRequests.push(groupRequests[0] as AggregatedRequest)
    } else {
      // Multiple requests for same TV show, aggregate them
      const baseRequest = { ...groupRequests[0] } as AggregatedRequest
      
      // Collect all seasons from all requests
      const allSeasons: Array<{ id: number; seasonNumber: number; status: number; status4k?: number }> = []
      const allRequestIds: number[] = []
      
      for (const req of groupRequests) {
        if (!req || !req.id) {
          console.warn('Skipping invalid request in group:', req)
          continue
        }
        
        allRequestIds.push(req.id)
        if (req.seasons && Array.isArray(req.seasons) && req.seasons.length > 0) {
          for (const season of req.seasons) {
            if (!season || typeof season.seasonNumber === 'undefined') {
              continue
            }
            const existingSeason = allSeasons.find(s => s.seasonNumber === season.seasonNumber)
            if (!existingSeason) {
              allSeasons.push(season)
            } else {
              // Update with the latest status if different
              if (season.status !== existingSeason.status) {
                const index = allSeasons.indexOf(existingSeason)
                allSeasons[index] = season
              }
            }
          }
        }
      }
      
      // Sort seasons by season number
      allSeasons.sort((a, b) => a.seasonNumber - b.seasonNumber)
      
      baseRequest.seasons = allSeasons
      baseRequest.seasonCount = allSeasons.length
      baseRequest.aggregated_request_ids = allRequestIds
      
      aggregatedRequests.push(baseRequest)
    }
  }
  
  return aggregatedRequests
}

function getRequestStatusLabel(status: number): string {
  // Overseerr request statuses - exact mapping as specified:
  // pending (1), approved (2), processing (3), failed (4), available (5), unavailable (-1), deleted (-2)
  // Status 5 is also "completed" in some forks (Jellyseerr)
  if (status === 1) return 'pending'
  if (status === 2) return 'approved'
  if (status === 3) return 'processing'
  if (status === 4) return 'failed'
  if (status === 5) return 'available'  // Also "completed" in some forks
  if (status === -1) return 'unavailable' // Legacy unavailable
  if (status === -2) return 'deleted'
  return 'unknown'
}

function getMediaStatusLabel(status: number): string {
  // Media statuses: 1=unknown, 2=partial, 3=processing, 4=partially available, 5=available, 6=unavailable
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

export default defineEventHandler(async (event) => {
  // Track partial failures
  let mediaDetailsErrors: string[] = []
  let unifiedMediaError: string | null = null
  
  try {
    const query = getQuery(event)
    const page = parseInt(query.page as string) || 1
    const limit = Math.min(parseInt(query.limit as string) || 50, 100)
    const skip = (page - 1) * limit
    
    const status = query.status as string
    const mediaType = query.mediaType as string
    const search = query.search as string
    const sortBy = query.sortBy as string || 'added'
    
    // Get Overseerr configuration
    const { baseUrl: overseerrBaseUrl, apiKey: overseerrApiKey } = await getOverseerrConfig()
    
    if (!overseerrBaseUrl) {
      return {
        success: false,
        error: 'Overseerr base URL not configured',
        data: null
      }
    }
    
    if (!overseerrApiKey) {
      return {
        success: false,
        error: 'Overseerr API key not configured',
        data: null
      }
    }
    
    // Remove trailing slash from base URL
    const baseUrl = overseerrBaseUrl.replace(/\/$/, '')
    
    // PHASE 1: Fetch ALL requests from Overseerr (handle pagination if needed)
    // We need all requests to extract unique TMDB IDs for media details fetching
    console.log(`[Phase 1] Fetching all requests from Overseerr...`)
    let allRequests: OverseerrRequest[] = []
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
        console.error('Overseerr API error:', response.status, errorText)
        return {
          success: false,
          error: `Failed to fetch requests from Overseerr: ${response.status} ${response.statusText}`,
          details: errorText,
          data: {
            requests: [],
            stats: {
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
            },
            pagination: {
              page,
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
      const pageRequests: OverseerrRequest[] = data.results || []
      allRequests = allRequests.concat(pageRequests)
      
      // Check if there are more pages
      // Overseerr might return pagination info in the response
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
    
    // Filter by request status if provided
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
    
    // Filter by media type if provided
    if (mediaType) {
      allRequests = allRequests.filter(req => {
        if (!req || !req.media || !req.media.mediaType) {
          return false
        }
        return req.media.mediaType === mediaType
      })
    }
    
    // PHASE 2: Extract unique TMDB IDs and batch fetch media details
    // Extract all unique {tmdbId, mediaType} pairs to avoid duplicate API calls
    console.log(`[Phase 2] Extracting unique TMDB IDs from ${allRequests.length} requests...`)
    const uniqueMediaMap = new Map<string, { tmdbId: number; mediaType: string }>()
    
    for (const req of allRequests) {
      if (req.media && req.media.tmdbId) {
        const key = `${req.media.tmdbId}_${req.media.mediaType}`
        if (!uniqueMediaMap.has(key)) {
          uniqueMediaMap.set(key, {
            tmdbId: req.media.tmdbId,
            mediaType: req.media.mediaType
          })
        }
      }
    }
    
    console.log(`[Phase 2] Found ${uniqueMediaMap.size} unique media items to fetch details for`)
    
    // Batch fetch media details for all unique TMDB IDs
    const mediaDetailsMap = new Map<string, any>()
    const batchSize = 10
    
    const uniqueMediaArray = Array.from(uniqueMediaMap.values())
    for (let i = 0; i < uniqueMediaArray.length; i += batchSize) {
      const batch = uniqueMediaArray.slice(i, i + batchSize)
      await Promise.all(batch.map(async ({ tmdbId, mediaType }) => {
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
          } else {
            const errorText = await mediaResponse.text()
            const errorMsg = `Failed to fetch media details for ${mediaType} ${tmdbId}: ${mediaResponse.status} ${mediaResponse.statusText}`
            console.warn(`[Phase 2] ${errorMsg}`, errorText.substring(0, 200))
            mediaDetailsErrors.push(errorMsg)
          }
        } catch (error) {
          const errorMsg = `Error fetching media details for ${mediaType} ${tmdbId}: ${error instanceof Error ? error.message : 'Unknown error'}`
          console.error(errorMsg, error)
          mediaDetailsErrors.push(errorMsg)
        }
      }))
      
      console.log(`[Phase 2] Fetched media details: ${i + batch.length}/${uniqueMediaArray.length}`)
    }
    
    console.log(`[Phase 2] Completed: Fetched media details for ${mediaDetailsMap.size}/${uniqueMediaMap.size} unique media items`)
    
    // Log sample of what we fetched
    if (mediaDetailsMap.size > 0) {
      const sampleKeys = Array.from(mediaDetailsMap.keys()).slice(0, 3)
      console.log(`[Phase 2] Sample fetched keys:`, sampleKeys)
      for (const key of sampleKeys) {
        const details = mediaDetailsMap.get(key)
        console.log(`[Phase 2] Sample ${key}:`, {
          title: details?.title || details?.name || 'N/A',
          posterPath: details?.posterPath || 'N/A',
          hasOverview: !!details?.overview
        })
      }
    } else {
      console.error(`[Phase 2] WARNING: No media details were fetched! This will cause "Unknown Title" issues.`)
    }
    
    // PHASE 3: Merge media details back into all requests
    console.log(`[Phase 3] Merging media details into ${allRequests.length} requests...`)
    let mergeCount = 0
    let noDetailsCount = 0
    for (const req of allRequests) {
      if (req.media && req.media.tmdbId) {
        const key = `${req.media.tmdbId}_${req.media.mediaType}`
        const mediaDetails = mediaDetailsMap.get(key)
        
        if (mediaDetails) {
          mergeCount++
          // Store original title if it exists (from request data)
          const originalTitle = req.media.title && req.media.title !== 'Unknown Title' ? req.media.title : null
          const mediaType = req.media.mediaType === 'movie' ? 'movie' : 'tv'
          
          // Extract title - Movies use 'title', TV shows use 'name'
          const beforeTitle = req.media.title
          if (mediaType === 'movie' && mediaDetails.title) {
            req.media.title = mediaDetails.title
          } else if (mediaType === 'tv' && mediaDetails.name) {
            req.media.title = mediaDetails.name
          }
          // Fallback: if we didn't get the expected field, try the other
          if (!req.media.title || req.media.title === 'Unknown Title') {
            if (mediaDetails.title) {
              req.media.title = mediaDetails.title
            } else if (mediaDetails.name) {
              req.media.title = mediaDetails.name
            }
          }
          
          // Debug log for title extraction
          if (beforeTitle === 'Unknown Title' && req.media.title !== 'Unknown Title') {
            console.log(`[Phase 3] Fixed title for ${mediaType} ${req.media.tmdbId}: "${beforeTitle}" -> "${req.media.title}"`)
          } else if (req.media.title === 'Unknown Title') {
            console.warn(`[Phase 3] Still Unknown Title for ${mediaType} ${req.media.tmdbId} after merge. mediaDetails has: title="${mediaDetails.title || 'N/A'}", name="${mediaDetails.name || 'N/A'}"`)
          }
          
          // Also capture original title/name
          if (mediaDetails.originalTitle) {
            (req.media as any).originalTitle = mediaDetails.originalTitle
          }
          if (mediaDetails.originalName && !(req.media as any).originalTitle) {
            (req.media as any).originalTitle = mediaDetails.originalName
          }
          
          // Extract poster path - CRITICAL: Request endpoint doesn't return this
          if (mediaDetails.posterPath) {
            req.media.posterPath = mediaDetails.posterPath
          } else if ((mediaDetails as any).poster_path) {
            req.media.posterPath = (mediaDetails as any).poster_path
          }
          
          // Extract backdrop path - CRITICAL: Request endpoint doesn't return this
          if (mediaDetails.backdropPath) {
            req.media.backdropPath = mediaDetails.backdropPath
          } else if ((mediaDetails as any).backdrop_path) {
            req.media.backdropPath = (mediaDetails as any).backdrop_path
          }
          
          // Extract overview/description
          if (mediaDetails.overview) {
            req.media.overview = mediaDetails.overview
          }
          
          // Extract IMDB ID
          if (mediaDetails.imdbId) {
            (req.media as any).imdbId = mediaDetails.imdbId
          } else if (mediaDetails.externalIds && mediaDetails.externalIds.imdbId) {
            (req.media as any).imdbId = mediaDetails.externalIds.imdbId
          }
          
          // Extract external IDs
          if (mediaDetails.externalIds) {
            (req.media as any).externalIds = mediaDetails.externalIds
            if (mediaDetails.externalIds.tvdbId && !req.media.tvdbId) {
              req.media.tvdbId = mediaDetails.externalIds.tvdbId
            }
          }
          
          // Extract release dates
          if (mediaDetails.releaseDate) {
            req.media.releaseDate = mediaDetails.releaseDate
          }
          if (mediaDetails.firstAirDate) {
            (req.media as any).firstAirDate = mediaDetails.firstAirDate
            if (!req.media.releaseDate) {
              req.media.releaseDate = mediaDetails.firstAirDate
            }
          }
          if (mediaDetails.lastAirDate) {
            (req.media as any).lastAirDate = mediaDetails.lastAirDate
          }
          
          // Extract rating/vote information
          if (mediaDetails.voteAverage !== undefined) {
            (req.media as any).voteAverage = mediaDetails.voteAverage
          }
          if (mediaDetails.voteCount !== undefined) {
            (req.media as any).voteCount = mediaDetails.voteCount
          }
          if (mediaDetails.popularity !== undefined) {
            (req.media as any).popularity = mediaDetails.popularity
          }
          
          // Extract runtime
          if (mediaDetails.runtime !== undefined) {
            (req.media as any).runtime = mediaDetails.runtime
          }
          if (mediaDetails.episodeRunTime && Array.isArray(mediaDetails.episodeRunTime) && mediaDetails.episodeRunTime.length > 0) {
            (req.media as any).episodeRuntime = mediaDetails.episodeRunTime[0]
            (req.media as any).episodeRunTime = mediaDetails.episodeRunTime
          }
          
          // Extract genres
          if (mediaDetails.genres && Array.isArray(mediaDetails.genres)) {
            (req.media as any).genres = mediaDetails.genres.map((g: any) => ({
              id: g.id,
              name: g.name
            }))
          }
          
          // Extract production companies/studios
          if (mediaDetails.productionCompanies && Array.isArray(mediaDetails.productionCompanies)) {
            (req.media as any).productionCompanies = mediaDetails.productionCompanies
          }
          
          // Extract production countries
          if (mediaDetails.productionCountries && Array.isArray(mediaDetails.productionCountries)) {
            (req.media as any).productionCountries = mediaDetails.productionCountries
          }
          
          // Extract networks (TV shows)
          if (mediaDetails.networks && Array.isArray(mediaDetails.networks)) {
            (req.media as any).networks = mediaDetails.networks
          }
          
          // Extract collection (for movies)
          if (mediaDetails.collection) {
            (req.media as any).collection = mediaDetails.collection
          }
          
          // Extract budget and revenue (movies)
          if (mediaDetails.budget !== undefined) {
            (req.media as any).budget = mediaDetails.budget
          }
          if (mediaDetails.revenue !== undefined) {
            (req.media as any).revenue = mediaDetails.revenue
          }
          
          // Extract releases/certification info (movies)
          if (mediaDetails.releases && mediaDetails.releases.results) {
            (req.media as any).releases = mediaDetails.releases
            const usRelease = mediaDetails.releases.results.find((r: any) => r.iso_3166_1 === 'US')
            if (usRelease && usRelease.release_dates && usRelease.release_dates.length > 0) {
              const theatricalRelease = usRelease.release_dates.find((rd: any) => rd.type === 3)
              if (theatricalRelease && theatricalRelease.certification) {
                (req.media as any).certification = theatricalRelease.certification
              }
            }
          }
          
          // Extract credits
          if (mediaDetails.credits) {
            (req.media as any).credits = {
              cast: mediaDetails.credits.cast || [],
              crew: mediaDetails.credits.crew || []
            }
          }
          
          // Extract watch providers
          if (mediaDetails.watchProviders && Array.isArray(mediaDetails.watchProviders)) {
            (req.media as any).watchProviders = mediaDetails.watchProviders
          }
          
          // Extract keywords
          if (mediaDetails.keywords && Array.isArray(mediaDetails.keywords)) {
            (req.media as any).keywords = mediaDetails.keywords
          }
          
          // Extract spoken languages
          if (mediaDetails.spokenLanguages && Array.isArray(mediaDetails.spokenLanguages)) {
            (req.media as any).spokenLanguages = mediaDetails.spokenLanguages
          }
          
          // Extract related videos
          if (mediaDetails.relatedVideos && Array.isArray(mediaDetails.relatedVideos)) {
            (req.media as any).relatedVideos = mediaDetails.relatedVideos
          }
          
          // Extract certification/rating
          if (mediaDetails.certification) {
            (req.media as any).certification = mediaDetails.certification
          }
          if (mediaDetails.contentRatings && mediaDetails.contentRatings.results && Array.isArray(mediaDetails.contentRatings.results)) {
            (req.media as any).contentRatings = mediaDetails.contentRatings.results
            const usRating = mediaDetails.contentRatings.results.find((r: any) => r.iso_3166_1 === 'US')
            if (usRating) {
              (req.media as any).contentRating = usRating.rating
            }
          } else if (mediaDetails.rating) {
            (req.media as any).contentRating = mediaDetails.rating
          }
          
          // Extract tagline
          if (mediaDetails.tagline) {
            (req.media as any).tagline = mediaDetails.tagline
          }
          
          // Extract homepage
          if (mediaDetails.homepage) {
            (req.media as any).homepage = mediaDetails.homepage
          }
          
          // Extract original language
          if (mediaDetails.originalLanguage) {
            (req.media as any).originalLanguage = mediaDetails.originalLanguage
          }
          
          // Extract status
          if (mediaDetails.status) {
            (req.media as any).mediaStatus = mediaDetails.status
          }
          
          // For TV shows, extract full season information
          if (mediaType === 'tv' && mediaDetails.seasons && Array.isArray(mediaDetails.seasons)) {
            (req.media as any).allSeasons = mediaDetails.seasons.map((season: any) => ({
              id: season.id,
              seasonNumber: season.seasonNumber,
              name: season.name,
              overview: season.overview || '',
              episodeCount: season.episodeCount || 0,
              airDate: season.airDate || season.air_date,
              posterPath: season.posterPath || season.poster_path,
              episodes: season.episodes || []
            }))
            
            if (mediaDetails.numberOfSeasons !== undefined) {
              (req.media as any).numberOfSeasons = mediaDetails.numberOfSeasons
            } else if (mediaDetails.numberOfSeason !== undefined) {
              (req.media as any).numberOfSeasons = mediaDetails.numberOfSeason
            }
            if (mediaDetails.numberOfEpisodes !== undefined) {
              (req.media as any).numberOfEpisodes = mediaDetails.numberOfEpisodes
            }
          }
          
          // Extract additional TV show specific fields
          if (mediaType === 'tv') {
            if (mediaDetails.createdBy && Array.isArray(mediaDetails.createdBy)) {
              (req.media as any).createdBy = mediaDetails.createdBy
            }
            
            if (mediaDetails.languages && Array.isArray(mediaDetails.languages)) {
              (req.media as any).languages = mediaDetails.languages
            }
            
            if (mediaDetails.originCountry && Array.isArray(mediaDetails.originCountry)) {
              (req.media as any).originCountry = mediaDetails.originCountry
            }
            
            if (mediaDetails.inProduction !== undefined) {
              (req.media as any).inProduction = mediaDetails.inProduction
            }
            
            if (mediaDetails.type) {
              (req.media as any).showType = mediaDetails.type
            }
            
            if (mediaDetails.lastEpisodeToAir) {
              (req.media as any).lastEpisodeToAir = mediaDetails.lastEpisodeToAir
            }
            
            if (mediaDetails.nextEpisodeToAir) {
              (req.media as any).nextEpisodeToAir = mediaDetails.nextEpisodeToAir
            }
          }
          
          // If we still don't have a title, restore original from request data
          if (!req.media.title || req.media.title === 'Unknown Title') {
            if (originalTitle) {
              req.media.title = originalTitle
            }
          }
        } else {
          noDetailsCount++
          if (noDetailsCount <= 5) {
            console.warn(`[Phase 3] No media details found for key: ${key} (tmdbId: ${req.media.tmdbId}, mediaType: ${req.media.mediaType})`)
          }
        }
      }
    }
    
    console.log(`[Phase 3] Completed: Merged media details into ${mergeCount} requests, ${noDetailsCount} requests had no details available`)
    
    // PHASE 4: Filter requests (after media details are merged)
    console.log(`[Phase 4] Filtering ${allRequests.length} requests...`)
    // Filter by request status if provided
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
    
    // Filter by media type if provided
    if (mediaType) {
      allRequests = allRequests.filter(req => {
        if (!req || !req.media || !req.media.mediaType) {
          return false
        }
        return req.media.mediaType === mediaType
      })
    }
    
    // Filter by search query if provided (now we can search on titles since they're populated)
    if (search) {
      const searchLower = search.toLowerCase()
      allRequests = allRequests.filter(req => 
        req.media.title?.toLowerCase().includes(searchLower) ||
        req.media.overview?.toLowerCase().includes(searchLower)
      )
    }
    
    // Aggregate TV show requests by media ID
    const aggregatedRequests = aggregateTvRequestsByMediaId(allRequests)
    
    console.log(`[Phase 4] Completed: Filtered to ${aggregatedRequests.length} requests after aggregation`)
    
    // Calculate stats from filtered/aggregated requests
    const stats = {
      total_requests: aggregatedRequests.length,
      total_movies: aggregatedRequests.filter(r => r.media.mediaType === 'movie').length,
      total_tv_shows: aggregatedRequests.filter(r => r.media.mediaType === 'tv').length,
      pending_count: aggregatedRequests.filter(r => r.status === 1).length,
      approved_count: aggregatedRequests.filter(r => r.status === 2).length,
      processing_count: aggregatedRequests.filter(r => r.status === 3).length,
      failed_count: aggregatedRequests.filter(r => r.status === 4).length,
      available_count: aggregatedRequests.filter(r => r.status === 5).length,
      unavailable_count: aggregatedRequests.filter(r => r.status === -1).length,
      deleted_count: aggregatedRequests.filter(r => r.status === -2).length,
      movies_pending: aggregatedRequests.filter(r => r.media.mediaType === 'movie' && r.status === 1).length,
      movies_approved: aggregatedRequests.filter(r => r.media.mediaType === 'movie' && r.status === 2).length,
      movies_processing: aggregatedRequests.filter(r => r.media.mediaType === 'movie' && r.status === 3).length,
      movies_failed: aggregatedRequests.filter(r => r.media.mediaType === 'movie' && r.status === 4).length,
      movies_available: aggregatedRequests.filter(r => r.media.mediaType === 'movie' && r.status === 5).length,
      movies_unavailable: aggregatedRequests.filter(r => r.media.mediaType === 'movie' && r.status === -1).length,
      movies_deleted: aggregatedRequests.filter(r => r.media.mediaType === 'movie' && r.status === -2).length,
      tv_pending: aggregatedRequests.filter(r => r.media.mediaType === 'tv' && r.status === 1).length,
      tv_approved: aggregatedRequests.filter(r => r.media.mediaType === 'tv' && r.status === 2).length,
      tv_processing: aggregatedRequests.filter(r => r.media.mediaType === 'tv' && r.status === 3).length,
      tv_failed: aggregatedRequests.filter(r => r.media.mediaType === 'tv' && r.status === 4).length,
      tv_available: aggregatedRequests.filter(r => r.media.mediaType === 'tv' && r.status === 5).length,
      tv_unavailable: aggregatedRequests.filter(r => r.media.mediaType === 'tv' && r.status === -1).length,
      tv_deleted: aggregatedRequests.filter(r => r.media.mediaType === 'tv' && r.status === -2).length
    }
    
    // PHASE 5: Apply pagination LAST (after all media details are merged)
    const total = aggregatedRequests.length
    const safeSkip = Math.min(skip, total)
    const paginatedRequests = aggregatedRequests.slice(safeSkip, safeSkip + limit)
    const hasNext = safeSkip + limit < total
    
    console.log(`[Phase 5] Pagination: Returning ${paginatedRequests.length} requests (page ${page}, total: ${total})`)
    
    // Match requests with unified_media data
    const db = await getDatabaseConnection()
    const tmdbIds = paginatedRequests.map(req => req.media.tmdbId)
    
    // Fetch matching unified_media records
    const unifiedMediaMap: Map<number, any> = new Map()
    if (tmdbIds.length > 0) {
      try {
        const placeholders = tmdbIds.map(() => '?').join(',')
        
        // Build query to match by tmdb_id and media_type
        const queryParts: string[] = []
        const queryParams: any[] = []
        
        for (const req of paginatedRequests) {
          queryParts.push('(tmdb_id = ? AND media_type = ?)')
          queryParams.push(req.media.tmdbId, req.media.mediaType)
        }
        
        const [unifiedRows] = await db.execute(`
          SELECT 
            id, tmdb_id, imdb_id, trakt_id, overseerr_media_id, overseerr_request_id,
            media_type, title, year, overview,
            status, processing_stage, processing_started_at, processing_completed_at,
            genres, runtime, rating, vote_count, popularity,
            poster_image_format, thumb_image_format, fanart_image_format, backdrop_image_format,
            poster_url, thumb_url, fanart_url, backdrop_url,
            seasons_data, total_seasons,
            error_message, error_count,
            created_at, updated_at
          FROM unified_media
          WHERE ${queryParts.join(' OR ')}
        `, queryParams)
        
        // Create a map by tmdb_id and media_type for quick lookup
        for (const row of (unifiedRows as any[])) {
          const key = `${row.tmdb_id}_${row.media_type}`
          unifiedMediaMap.set(key as any, row)
        }
      } catch (error) {
        unifiedMediaError = error instanceof Error ? error.message : 'Unknown error'
        console.error('Error fetching unified_media data:', error)
        // Continue without unified_media data if query fails
      }
    }
    
    // Transform requests for frontend
    // Filter out any invalid requests before transformation
    const validRequests = paginatedRequests.filter(req => {
      if (!req || typeof req !== 'object') {
        console.warn('Invalid request (not an object):', req)
        return false
      }
      if (req.id === undefined || req.id === null) {
        console.warn('Invalid request (missing id):', req)
        return false
      }
      if (!req.media || typeof req.media !== 'object') {
        console.warn('Invalid request (missing or invalid media):', req)
        return false
      }
      if (req.media.tmdbId === undefined || req.media.tmdbId === null) {
        console.warn('Invalid request (missing tmdbId):', req)
        return false
      }
      if (!req.media.mediaType || (req.media.mediaType !== 'movie' && req.media.mediaType !== 'tv')) {
        console.warn('Invalid request (missing or invalid mediaType):', req)
        return false
      }
      return true
    })
    
    const transformedRequests = validRequests.map(req => {
      const lookupKey = `${req.media.tmdbId}_${req.media.mediaType}`
      const unifiedMedia = unifiedMediaMap.get(lookupKey as any)
      
      // Extract title - Overseerr might use different field names
      // Only use "Unknown Title" if we truly have no title after all fallbacks
      let mediaTitle = req.media.title
      if (!mediaTitle || mediaTitle === 'Unknown Title') {
        if ((req.media as any).name) {
          mediaTitle = (req.media as any).name
        } else if ((req.media as any).originalTitle) {
          mediaTitle = (req.media as any).originalTitle
        } else if ((req.media as any).originalName) {
          mediaTitle = (req.media as any).originalName
        } else {
          // Last resort - use "Unknown Title" only if we have absolutely nothing
          mediaTitle = 'Unknown Title'
        }
      }
      
      // Extract release date - might be in different fields
      let releaseDate = req.media.releaseDate
      if (!releaseDate && (req.media as any).release_date) {
        releaseDate = (req.media as any).release_date
      }
      if (!releaseDate && (req.media as any).firstAirDate) {
        releaseDate = (req.media as any).firstAirDate
      }
      if (!releaseDate && (req.media as any).first_air_date) {
        releaseDate = (req.media as any).first_air_date
      }
      
      // Extract poster path
      let posterPath = req.media.posterPath
      if (!posterPath && (req.media as any).poster_path) {
        posterPath = (req.media as any).poster_path
      }
      if (!posterPath && (req.media as any).poster) {
        posterPath = (req.media as any).poster
      }
      
      // Extract backdrop path
      let backdropPath = req.media.backdropPath
      if (!backdropPath && (req.media as any).backdrop_path) {
        backdropPath = (req.media as any).backdrop_path
      }
      if (!backdropPath && (req.media as any).backdrop) {
        backdropPath = (req.media as any).backdrop
      }
      
      // Extract overview
      let overview = req.media.overview
      if (!overview && (req.media as any).description) {
        overview = (req.media as any).description
      }
      
      // Base request data
      const requestData: any = {
        id: req.id,
        request_id: req.id,
        status: req.status,
        status_label: getRequestStatusLabel(req.status),
        media_status: req.media.status,
        media_status_label: getMediaStatusLabel(req.media.status),
        created_at: req.createdAt,
        updated_at: req.updatedAt,
        requested_by: req.requestedBy || (req as any).requestedBy || {},
        media: {
          id: req.media.id,
          media_type: req.media.mediaType,
          tmdb_id: req.media.tmdbId,
          tvdb_id: req.media.tvdbId || (req.media as any).tvdb_id,
          title: mediaTitle,
          original_title: (req.media as any).originalTitle,
          release_date: releaseDate,
          first_air_date: (req.media as any).firstAirDate || releaseDate,
          last_air_date: (req.media as any).lastAirDate,
          poster_path: posterPath,
          backdrop_path: backdropPath,
          overview: overview,
          status: req.media.status,
          status4k: req.media.status4k || (req.media as any).status4k,
          vote_average: (req.media as any).voteAverage,
          vote_count: (req.media as any).voteCount,
          popularity: (req.media as any).popularity,
          runtime: (req.media as any).runtime,
          episode_runtime: (req.media as any).episodeRuntime,
          genres: (req.media as any).genres || [],
          production_companies: (req.media as any).productionCompanies || [],
          production_countries: (req.media as any).productionCountries || [],
          networks: (req.media as any).networks || [],
          certification: (req.media as any).certification,
          content_rating: (req.media as any).contentRating,
          content_ratings: (req.media as any).contentRatings || [],
          tagline: (req.media as any).tagline,
          homepage: (req.media as any).homepage,
          original_language: (req.media as any).originalLanguage,
          media_status: (req.media as any).mediaStatus,
          imdb_id: (req.media as any).imdbId,
          external_ids: (req.media as any).externalIds,
          collection: (req.media as any).collection,
          budget: (req.media as any).budget,
          revenue: (req.media as any).revenue,
          releases: (req.media as any).releases,
          credits: (req.media as any).credits,
          watch_providers: (req.media as any).watchProviders || [],
          keywords: (req.media as any).keywords || [],
          spoken_languages: (req.media as any).spokenLanguages || [],
          related_videos: (req.media as any).relatedVideos || [],
          // TV show specific fields
          all_seasons: (req.media as any).allSeasons || [],
          number_of_seasons: (req.media as any).numberOfSeasons,
          number_of_episodes: (req.media as any).numberOfEpisodes,
          in_production: (req.media as any).inProduction,
          show_type: (req.media as any).showType,
          last_episode_to_air: (req.media as any).lastEpisodeToAir,
          next_episode_to_air: (req.media as any).nextEpisodeToAir,
          created_by: (req.media as any).createdBy || [],
          languages: (req.media as any).languages || [],
          origin_country: (req.media as any).originCountry || [],
          episode_run_time: (req.media as any).episodeRunTime || []
        },
        seasons: req.seasons || [],
        season_count: req.seasonCount || (req.seasons?.length || 0),
        // Include all seasons from Overseerr for TV shows
        all_seasons: (req.media as any).allSeasons || [],
        aggregated_request_ids: req.aggregated_request_ids || [req.id],
        is4k: req.is4k || false,
        has_unified_media: !!unifiedMedia
      }
      
      // Merge unified_media data if available
      if (unifiedMedia) {
        // Parse JSON fields
        let seasonsData = []
        let genres = []
        try {
          if (unifiedMedia.seasons_data && typeof unifiedMedia.seasons_data === 'string') {
            seasonsData = JSON.parse(unifiedMedia.seasons_data)
          } else if (Array.isArray(unifiedMedia.seasons_data)) {
            seasonsData = unifiedMedia.seasons_data
          }
          
          if (unifiedMedia.genres && typeof unifiedMedia.genres === 'string') {
            genres = JSON.parse(unifiedMedia.genres)
          } else if (Array.isArray(unifiedMedia.genres)) {
            genres = unifiedMedia.genres
          }
        } catch (e) {
          console.error('Error parsing unified_media JSON fields:', e)
        }
        
        requestData.unified_media = {
          id: unifiedMedia.id,
          tmdb_id: unifiedMedia.tmdb_id,
          imdb_id: unifiedMedia.imdb_id,
          trakt_id: unifiedMedia.trakt_id,
          overseerr_media_id: unifiedMedia.overseerr_media_id,
          overseerr_request_id: unifiedMedia.overseerr_request_id,
          media_type: unifiedMedia.media_type,
          title: unifiedMedia.title,
          year: unifiedMedia.year,
          overview: unifiedMedia.overview || req.media.overview,
          status: unifiedMedia.status,
          processing_stage: unifiedMedia.processing_stage,
          processing_started_at: unifiedMedia.processing_started_at,
          processing_completed_at: unifiedMedia.processing_completed_at,
          genres: genres,
          runtime: unifiedMedia.runtime,
          rating: unifiedMedia.rating,
          vote_count: unifiedMedia.vote_count,
          popularity: unifiedMedia.popularity,
          has_poster_image: !!unifiedMedia.poster_image_format,
          has_thumb_image: !!unifiedMedia.thumb_image_format,
          has_fanart_image: !!unifiedMedia.fanart_image_format,
          has_backdrop_image: !!unifiedMedia.backdrop_image_format,
          poster_url: unifiedMedia.poster_url,
          thumb_url: unifiedMedia.thumb_url,
          fanart_url: unifiedMedia.fanart_url,
          backdrop_url: unifiedMedia.backdrop_url,
          seasons_data: seasonsData,
          total_seasons: unifiedMedia.total_seasons,
          error_message: unifiedMedia.error_message,
          error_count: unifiedMedia.error_count,
          created_at: unifiedMedia.created_at,
          updated_at: unifiedMedia.updated_at
        }
        
        // Prefer unified_media title, year, overview if available
        if (unifiedMedia.title) {
          requestData.media.title = unifiedMedia.title
        }
        if (unifiedMedia.year) {
          requestData.media.year = unifiedMedia.year
        }
        if (unifiedMedia.overview) {
          requestData.media.overview = unifiedMedia.overview
        }
      }
      
      return requestData
    })
    
    // Final validation: filter out any invalid transformed requests
    const validTransformedRequests = transformedRequests.filter(req => {
      if (!req || typeof req !== 'object') {
        console.warn('Invalid transformed request (not an object):', req)
        return false
      }
      if (!req.id && req.id !== 0) {
        console.warn('Invalid transformed request (missing id):', req)
        return false
      }
      if (!req.media || typeof req.media !== 'object') {
        console.warn('Invalid transformed request (missing or invalid media):', req)
        return false
      }
      return true
    })
    
    console.log(`Returning ${validTransformedRequests.length} valid requests (filtered from ${transformedRequests.length} transformed, ${paginatedRequests.length} paginated)`)
    
    // Build response with warnings if there were partial failures
    const apiResponse: any = {
      success: true,
      data: {
        requests: validTransformedRequests,
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
    
    // Add warnings for partial failures (but still return success)
    if (mediaDetailsErrors.length > 0 || unifiedMediaError) {
      apiResponse.warnings = []
      if (mediaDetailsErrors.length > 0) {
        apiResponse.warnings.push(`Failed to fetch media details for ${mediaDetailsErrors.length} request(s)`)
      }
      if (unifiedMediaError) {
        apiResponse.warnings.push(`Failed to fetch unified media data: ${unifiedMediaError}`)
      }
    }
    
    return apiResponse
    
  } catch (error) {
    console.error('Error fetching Overseerr requests:', error)
    const query = getQuery(event)
    const defaultLimit = Math.min(parseInt(query.limit as string) || 50, 100)
    return {
      success: false,
      error: 'Failed to fetch requests',
      details: error instanceof Error ? error.message : 'Unknown error',
      data: {
        requests: [],
        stats: {
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
        },
        pagination: {
          page: 1,
          limit: defaultLimit,
          total: 0,
          total_pages: 0,
          has_next: false,
          has_prev: false
        }
      }
    }
  }
})

