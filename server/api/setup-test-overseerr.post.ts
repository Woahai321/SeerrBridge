import { defineEventHandler, readBody } from 'h3'

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody(event)
    const { overseerr_base, overseerr_api_key } = body
    
    if (!overseerr_base || !overseerr_api_key) {
      return {
        success: false,
        error: 'Missing required credentials'
      }
    }
    
    // Remove trailing slash
    const baseUrl = overseerr_base.replace(/\/$/, '')
    
    // Test Overseerr connection by fetching recent approved requests
    try {
      const response = await fetch(`${baseUrl}/api/v1/request?take=10&filter=approved&sort=added`, {
        headers: {
          'X-Api-Key': overseerr_api_key
        }
      })
      
      if (!response.ok) {
        return {
          success: false,
          error: `Overseerr API returned status ${response.status}`
        }
      }
      
      const data = await response.json()
      const requests = data.results || []
      
      // Get details for the most recent request with full media info
      let recentRequest = null
      if (requests.length > 0) {
        const latest = requests[0]
        const mediaId = latest.media?.id
        const mediaType = latest.media?.mediaType
        
        if (mediaId && mediaType) {
          const mediaUrl = `${baseUrl}/api/v1/${mediaType === 'movie' ? 'movie' : 'tv'}/${mediaId}`
          const mediaResponse = await fetch(mediaUrl, {
            headers: {
              'X-Api-Key': overseerr_api_key
            }
          })
          
          if (mediaResponse.ok) {
            recentRequest = await mediaResponse.json()
          }
        }
      }
      
      // Get the first request with full details
      const firstRequest = requests.length > 0 ? {
            id: requests[0].id,
            title: recentRequest?.name || recentRequest?.title || 'Unknown',
            type: requests[0].type || requests[0].media?.mediaType,
            tmdbId: requests[0].media?.tmdbId,
            mediaType: requests[0].media?.mediaType || requests[0].type,
            year: recentRequest?.releaseDate ? new Date(recentRequest.releaseDate).getFullYear() : recentRequest?.firstAirDate ? new Date(recentRequest.firstAirDate).getFullYear() : null,
            poster: recentRequest?.posterPath,
            overview: recentRequest?.overview,
            status: requests[0].status,
            createdAt: requests[0].createdAt,
            updatedAt: requests[0].updatedAt,
            requestedBy: requests[0].requestedBy?.displayName || requests[0].requestedBy?.jellyfinUsername || requests[0].requestedBy?.email || 'Unknown',
            jellyfinUsername: requests[0].requestedBy?.jellyfinUsername
          } : null
      
      // Get the first Jellyfin username found
      const firstJellyfinUsername = requests.find((req: any) => req.requestedBy?.jellyfinUsername)?.requestedBy?.jellyfinUsername || null
      
      return {
        success: true,
        data: {
          total_requests: data.pageInfo?.results || 0,
          first_request: firstRequest,
          first_jellyfin_username: firstJellyfinUsername,
          overseerr_url: baseUrl,
          api_status: 'connected'
        }
      }
    } catch (fetchError: any) {
      console.error('Overseerr connection error:', fetchError)
      return {
        success: false,
        error: `Failed to connect to Overseerr: ${fetchError.message}`
      }
    }
  } catch (error) {
    console.error('Error testing Overseerr credentials:', error)
    return {
      success: false,
      error: 'Failed to test Overseerr credentials'
    }
  }
})

