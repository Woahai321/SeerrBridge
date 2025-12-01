import { getOverseerrConfig } from '~/server/utils/overseerr-config'

export default defineEventHandler(async (event) => {
  try {
    const query = getQuery(event)
    const tmdbId = query.tmdb_id ? parseInt(query.tmdb_id as string) : null

    if (!tmdbId) {
      throw createError({
        statusCode: 400,
        statusMessage: 'tmdb_id query parameter is required'
      })
    }

    // Get Overseerr configuration
    const { baseUrl: overseerrBaseUrl, apiKey: overseerrApiKey } = await getOverseerrConfig()

    if (!overseerrBaseUrl) {
      return {
        success: false,
        error: 'Overseerr base URL not configured'
      }
    }

    if (!overseerrApiKey) {
      return {
        success: false,
        error: 'Overseerr API key not configured'
      }
    }

    // Remove trailing slash from base URL
    const baseUrl = overseerrBaseUrl.replace(/\/$/, '')

    // Construct Overseerr movie details API URL
    const movieUrl = `${baseUrl}/api/v1/movie/${tmdbId}`

    // Fetch movie details from Overseerr with timeout
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 10000) // 10 second timeout for Overseerr API
    
    let response: Response
    try {
      response = await fetch(movieUrl, {
        method: 'GET',
        headers: {
          'X-Api-Key': overseerrApiKey,
          'Content-Type': 'application/json'
        },
        signal: controller.signal
      })
      clearTimeout(timeoutId)
    } catch (fetchError: any) {
      clearTimeout(timeoutId)
      // If timeout or network error, return as not available
      if (fetchError.name === 'AbortError' || fetchError.message?.includes('timeout')) {
        return {
          success: true,
          data: {
            status: null,
            available: false,
            mediaInfo: null
          }
        }
      }
      throw fetchError
    }

    if (!response.ok) {
      // If movie not found in Overseerr, return status as null (not available)
      if (response.status === 404) {
        return {
          success: true,
          data: {
            status: null,
            available: false,
            mediaInfo: null
          }
        }
      }

      return {
        success: false,
        error: `Overseerr API error: ${response.status} ${response.statusText}`
      }
    }

    const movieData = await response.json()

    // Extract mediaInfo status
    // Status values: 0=Unknown, 1=Available, 2=Partial, 3=Processing, 4=Partially Available, 5=Available
    const status = movieData.mediaInfo?.status ?? null
    const isAvailable = status === 1 || status === 5
    // Status 2 (Partial) or 3 (Processing) means the movie has been requested but not fully available yet
    const isRequested = status === 2 || status === 3

    return {
      success: true,
      data: {
        status,
        available: isAvailable,
        requested: isRequested,
        mediaInfo: movieData.mediaInfo || null,
        movie: {
          id: movieData.id,
          title: movieData.title,
          tmdbId: movieData.id
        }
      }
    }

  } catch (error) {
    console.error('Error checking Overseerr movie status:', error)
    return {
      success: false,
      error: 'Failed to check movie status',
      details: error instanceof Error ? error.message : String(error)
    }
  }
})

