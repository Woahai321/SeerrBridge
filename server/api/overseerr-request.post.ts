import { getOverseerrConfig } from '~/server/utils/overseerr-config'

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody(event)
    const { mediaId, mediaType, is4k = false, seasons } = body
    
    if (!mediaId || !mediaType) {
      return {
        success: false,
        error: 'Missing required parameters: mediaId and mediaType'
      }
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
    
    // Construct Overseerr request API URL
    const requestUrl = `${baseUrl}/api/v1/request`
    
    // Prepare request body
    const requestBody: any = {
      mediaType,
      mediaId,
      is4k
    }
    
    // Add seasons for TV shows
    if (mediaType === 'tv' && seasons && Array.isArray(seasons)) {
      requestBody.seasons = seasons
    }
    
    // Make request to Overseerr API
    const response = await fetch(requestUrl, {
      method: 'POST',
      headers: {
        'X-Api-Key': overseerrApiKey,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(requestBody)
    })
    
    if (!response.ok) {
      const errorText = await response.text()
      return {
        success: false,
        error: `Overseerr API error: ${response.status} ${response.statusText}`,
        details: errorText
      }
    }
    
    const data = await response.json()
    
    return {
      success: true,
      data: data,
      message: 'Request created successfully'
    }
    
  } catch (error) {
    console.error('Error creating Overseerr request:', error)
    return {
      success: false,
      error: 'Failed to create request',
      details: error instanceof Error ? error.message : String(error)
    }
  }
})

