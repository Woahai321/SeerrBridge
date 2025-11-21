import { getOverseerrConfig } from '~/server/utils/overseerr-config'

export default defineEventHandler(async (event) => {
  try {
    const query = getQuery(event)
    const requestId = query.requestId as string
    
    if (!requestId) {
      return {
        success: false,
        error: 'Missing required parameter: requestId'
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
    
    // Construct Overseerr delete request API URL
    const deleteUrl = `${baseUrl}/api/v1/request/${requestId}`
    
    // Make request to Overseerr API
    const response = await fetch(deleteUrl, {
      method: 'DELETE',
      headers: {
        'X-Api-Key': overseerrApiKey,
        'Content-Type': 'application/json'
      }
    })
    
    if (response.ok) {
      return {
        success: true,
        message: 'Request deleted successfully from Overseerr'
      }
    } else {
      const errorText = await response.text()
      console.error('Overseerr API error:', response.status, errorText)
      
      return {
        success: false,
        error: `Failed to delete request from Overseerr: ${response.status} ${errorText}`
      }
    }
  } catch (error) {
    console.error('Error deleting Overseerr request:', error)
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to delete request from Overseerr'
    }
  }
})
