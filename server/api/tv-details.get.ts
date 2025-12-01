export default defineEventHandler(async (event) => {
  try {
    const query = getQuery(event)
    const tmdbId = query.tmdbId as string
    
    if (!tmdbId) {
      return {
        success: false,
        error: 'tmdbId parameter is required'
      }
    }
    
    // Get Overseerr configuration
    const seerrbridgeUrl = process.env.SEERRBRIDGE_URL || 'http://localhost:8777'
    
    let overseerrBaseUrl: string | null = null
    let overseerrApiKey: string | null = null
    
    try {
      const configResponse = await fetch(`${seerrbridgeUrl}/api/config/internal`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      })
      
      if (configResponse.ok) {
        const configData = await configResponse.json()
        if (configData.success && configData.data) {
          overseerrBaseUrl = configData.data['overseerr_base'] || null
          overseerrApiKey = configData.data['overseerr_api_key'] || null
        }
      }
    } catch (error) {
      console.error('Failed to get config:', error)
    }
    
    if (!overseerrBaseUrl || !overseerrApiKey) {
      return {
        success: false,
        error: 'Overseerr configuration not found'
      }
    }
    
    const baseUrl = overseerrBaseUrl.replace(/\/$/, '')
    const tvDetailsUrl = `${baseUrl}/api/v1/tv/${tmdbId}`
    
    const response = await fetch(tvDetailsUrl, {
      method: 'GET',
      headers: {
        'X-Api-Key': overseerrApiKey,
        'Content-Type': 'application/json'
      }
    })
    
    if (!response.ok) {
      return {
        success: false,
        error: `Overseerr API error: ${response.status}`
      }
    }
    
    const data = await response.json()
    
    return {
      success: true,
      data
    }
    
  } catch (error) {
    console.error('Error fetching TV details:', error)
    return {
      success: false,
      error: 'Failed to fetch TV details',
      details: error instanceof Error ? error.message : String(error)
    }
  }
})

