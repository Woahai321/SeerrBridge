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
    const timeoutId = setTimeout(() => controller.abort(), 10000) // 10 second timeout
    
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
      // If timeout or network error, return error
      if (fetchError.name === 'AbortError' || fetchError.message?.includes('timeout')) {
        return {
          success: false,
          error: 'Request timeout - Overseerr API did not respond in time'
        }
      }
      throw fetchError
    }

    if (!response.ok) {
      // If movie not found in Overseerr
      if (response.status === 404) {
        return {
          success: false,
          error: 'Movie not found in Overseerr'
        }
      }

      return {
        success: false,
        error: `Overseerr API error: ${response.status} ${response.statusText}`
      }
    }

    const movieData = await response.json()

    // Extract poster path (can be posterPath or poster_path)
    const posterPath = movieData.posterPath || movieData.poster_path || null

    return {
      success: true,
      data: {
        id: movieData.id,
        title: movieData.title,
        tmdbId: movieData.id,
        posterPath: posterPath,
        backdropPath: movieData.backdropPath || movieData.backdrop_path || null,
        overview: movieData.overview || null,
        releaseDate: movieData.releaseDate || movieData.release_date || null,
        voteAverage: movieData.voteAverage || movieData.vote_average || null,
        runtime: movieData.runtime || null,
        genres: movieData.genres || []
      }
    }

  } catch (error) {
    console.error('Error fetching movie details:', error)
    return {
      success: false,
      error: 'Failed to fetch movie details',
      details: error instanceof Error ? error.message : String(error)
    }
  }
})

