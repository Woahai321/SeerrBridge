import { getOverseerrConfig } from '~/server/utils/overseerr-config'

interface BulkDeleteRequest {
  request_ids: number[]
}

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody<BulkDeleteRequest>(event)
    const { request_ids } = body
    
    if (!request_ids || !Array.isArray(request_ids) || request_ids.length === 0) {
      throw createError({
        statusCode: 400,
        statusMessage: 'request_ids array is required and must not be empty'
      })
    }
    
    // Get Overseerr configuration
    const { baseUrl: overseerrBaseUrl, apiKey: overseerrApiKey } = await getOverseerrConfig()
    
    if (!overseerrBaseUrl) {
      throw createError({
        statusCode: 500,
        statusMessage: 'Overseerr base URL not configured'
      })
    }
    
    if (!overseerrApiKey) {
      throw createError({
        statusCode: 500,
        statusMessage: 'Overseerr API key not configured'
      })
    }
    
    // Remove trailing slash from base URL
    const baseUrl = overseerrBaseUrl.replace(/\/$/, '')
    
    const results = {
      success: [] as Array<{ id: number; request_id: number }>,
      failed: [] as Array<{ id: number; request_id: number; error: string }>,
      total: request_ids.length,
      success_count: 0,
      failed_count: 0
    }
    
    // Process each request ID
    for (const requestId of request_ids) {
      try {
        const deleteUrl = `${baseUrl}/api/v1/request/${requestId}`
        const response = await fetch(deleteUrl, {
          method: 'DELETE',
          headers: {
            'X-Api-Key': overseerrApiKey,
            'Content-Type': 'application/json'
          }
        })
        
        if (response.ok) {
          results.success.push({
            id: requestId,
            request_id: requestId
          })
          results.success_count++
        } else {
          const errorText = await response.text()
          results.failed.push({
            id: requestId,
            request_id: requestId,
            error: `Overseerr API error: ${response.status} ${errorText}`
          })
          results.failed_count++
        }
      } catch (error) {
        console.error(`Error deleting request ${requestId}:`, error)
        results.failed.push({
          id: requestId,
          request_id: requestId,
          error: error instanceof Error ? error.message : 'Unknown error'
        })
        results.failed_count++
      }
    }
    
    return {
      status: results.failed_count === 0 ? 'completed' : 'partial',
      results
    }
  } catch (error) {
    console.error('Error bulk deleting requests:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to bulk delete requests',
      data: error instanceof Error ? error.message : 'Unknown error'
    })
  }
})

