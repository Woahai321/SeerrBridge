import { getOverseerrConfig } from '~/server/utils/overseerr-config'

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody(event)
    const requestIds = body.request_ids || body.requestIds || []
    
    if (!Array.isArray(requestIds) || requestIds.length === 0) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Request IDs array is required'
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
    
    const results = {
      success: [] as Array<{ id: number; request_id: number }>,
      failed: [] as Array<{ id: number; request_id: number; error: string }>,
      success_count: 0,
      failed_count: 0
    }
    
    // Process deletions in parallel with error handling
    await Promise.all(
      requestIds.map(async (requestId: number) => {
        try {
          const requestIdNum = typeof requestId === 'string' ? parseInt(requestId, 10) : requestId
          
          if (isNaN(requestIdNum)) {
            throw new Error('Invalid request ID')
          }
          
          // Step 1: Fetch request details to get media ID
          let overseerrMediaId: number | null = null
          let is4k = false
          
          try {
            const getRequestUrl = `${baseUrl}/api/v1/request/${requestIdNum}`
            const getResponse = await fetch(getRequestUrl, {
              method: 'GET',
              headers: {
                'X-Api-Key': overseerrApiKey,
                'Content-Type': 'application/json'
              }
            })
            
            if (getResponse.ok) {
              const requestData = await getResponse.json()
              const media = requestData.media || requestData
              overseerrMediaId = media.id || requestData.media?.id || null
              is4k = requestData.is4k || false
            }
          } catch (e) {
            // If we can't fetch request details, continue with deletion anyway
            console.warn(`Could not fetch request ${requestIdNum} details:`, e)
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
            throw new Error(`HTTP ${response.status}: ${errorText}`)
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
          
          results.success.push({
            id: requestIdNum,
            request_id: requestIdNum
          })
          results.success_count++
        } catch (error) {
          const requestIdNum = typeof requestId === 'string' ? parseInt(requestId, 10) : requestId
          results.failed.push({
            id: requestIdNum,
            request_id: requestIdNum,
            error: error instanceof Error ? error.message : 'Unknown error'
          })
          results.failed_count++
        }
      })
    )
    
    return {
      status: results.failed_count === 0 ? 'completed' : results.success_count > 0 ? 'partial' : 'failed',
      results
    }
    
  } catch (error) {
    console.error('Error bulk deleting requests:', error)
    throw createError({
      statusCode: error.statusCode || 500,
      statusMessage: error.statusMessage || 'Failed to bulk delete requests',
      data: error instanceof Error ? error.message : 'Unknown error'
    })
  }
})

