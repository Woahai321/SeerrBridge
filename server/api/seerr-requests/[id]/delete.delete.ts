import { getOverseerrConfig } from '~/server/utils/overseerr-config'

export default defineEventHandler(async (event) => {
  try {
    const requestId = getRouterParam(event, 'id')
    
    if (!requestId) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Request ID is required'
      })
    }
    
    const requestIdNum = parseInt(requestId)
    if (isNaN(requestIdNum)) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Invalid request ID'
      })
    }
    
    // Get Overseerr configuration
    const { baseUrl: overseerrBaseUrl, apiKey: overseerrApiKey } = await getOverseerrConfig()
    
    if (!overseerrBaseUrl || !overseerrApiKey) {
      throw createError({
        statusCode: 500,
        statusMessage: 'Overseerr not configured'
      })
    }
    
    // Remove trailing slash from base URL
    const baseUrl = overseerrBaseUrl.replace(/\/$/, '')
    
    // Step 1: Fetch request details to get media ID
    const getRequestUrl = `${baseUrl}/api/v1/request/${requestIdNum}`
    const getResponse = await fetch(getRequestUrl, {
      method: 'GET',
      headers: {
        'X-Api-Key': overseerrApiKey,
        'Content-Type': 'application/json'
      }
    })
    
    let overseerrMediaId: number | null = null
    let is4k = false
    
    if (getResponse.ok) {
      try {
        const requestData = await getResponse.json()
        const media = requestData.media || requestData
        overseerrMediaId = media.id || requestData.media?.id || null
        is4k = requestData.is4k || false
      } catch (e) {
        // If we can't parse the response, continue with deletion anyway
        console.warn('Could not parse request data to get media ID:', e)
      }
    }
    
    // Step 2: Delete the request
    const deleteUrl = `${baseUrl}/api/v1/request/${requestIdNum}`
    const response = await fetch(deleteUrl, {
      method: 'DELETE',
      headers: {
        'X-Api-Key': overseerrApiKey,
        'Content-Type': 'application/json'
      }
    })
    
    if (!response.ok) {
      const errorText = await response.text()
      throw createError({
        statusCode: response.status,
        statusMessage: `Failed to delete request: ${errorText}`
      })
    }
    
    // Step 3: Update media status to deleted
    if (overseerrMediaId) {
      try {
        const updateMediaStatusUrl = `${baseUrl}/api/v1/media/${overseerrMediaId}/deleted`
        const updateMediaResponse = await fetch(updateMediaStatusUrl, {
          method: 'POST',
          headers: {
            'X-Api-Key': overseerrApiKey,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            is4k: is4k
          })
        })
        
        if (!updateMediaResponse.ok) {
          const errorText = await updateMediaResponse.text()
          console.warn(`Failed to update media status to deleted for media ${overseerrMediaId}: ${errorText}`)
          // Don't fail the whole operation if media status update fails
        } else {
          console.log(`Successfully updated media ${overseerrMediaId} status to deleted`)
        }
      } catch (mediaError) {
        console.error(`Error updating media status to deleted for media ${overseerrMediaId}:`, mediaError)
        // Don't fail the whole operation if media status update fails
      }
    }
    
    // DELETE returns 204 No Content on success
    return {
      success: true,
      message: 'Request deleted successfully'
    }
    
  } catch (error) {
    console.error('Error deleting request:', error)
    throw createError({
      statusCode: error.statusCode || 500,
      statusMessage: error.statusMessage || 'Failed to delete request',
      data: error instanceof Error ? error.message : 'Unknown error'
    })
  }
})

