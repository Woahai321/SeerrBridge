import { getOverseerrConfig } from '~/server/utils/overseerr-config'

interface BulkRetriggerRequest {
  request_ids: number[]
}

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody<BulkRetriggerRequest>(event)
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
      success: [] as Array<{ id: number; request_id: number; new_request_id?: number }>,
      failed: [] as Array<{ id: number; request_id: number; error: string }>,
      total: request_ids.length,
      success_count: 0,
      failed_count: 0
    }
    
    // Process each request ID
    for (const requestId of request_ids) {
      try {
        // Step 1: Fetch request details from Overseerr
        const getRequestUrl = `${baseUrl}/api/v1/request/${requestId}`
        const getResponse = await fetch(getRequestUrl, {
          method: 'GET',
          headers: {
            'X-Api-Key': overseerrApiKey,
            'Content-Type': 'application/json'
          }
        })
        
        if (!getResponse.ok) {
          const errorText = await getResponse.text()
          results.failed.push({
            id: requestId,
            request_id: requestId,
            error: `Failed to fetch request details: ${getResponse.status} ${errorText}`
          })
          results.failed_count++
          continue
        }
        
        const requestData = await getResponse.json()
        const media = requestData.media || requestData
        const mediaId = media.tmdbId || media.id
        const mediaType = media.mediaType || (media.type === 'tv' ? 'tv' : 'movie')
        const overseerrMediaId = media.id || requestData.media?.id
        const is4k = requestData.is4k || false
        
        // Extract and normalize seasons to ensure they're always numbers
        let seasons: number[] | undefined = undefined
        if (mediaType === 'tv') {
          const rawSeasons = requestData.seasons || requestData.media?.seasons
          if (rawSeasons && Array.isArray(rawSeasons) && rawSeasons.length > 0) {
            seasons = rawSeasons
              .map((s: any) => {
                // If it's an object, extract seasonNumber
                if (typeof s === 'object' && s !== null && 'seasonNumber' in s) {
                  return s.seasonNumber
                }
                // If it's already a number or string, convert to number
                return s
              })
              .map((s: any) => {
                // Convert to number, handling strings
                const num = typeof s === 'string' ? parseInt(s, 10) : Number(s)
                return isNaN(num) ? null : num
              })
              .filter((s: any): s is number => s !== null && s !== undefined) as number[]
            
            // If we ended up with an empty array, set to undefined
            if (seasons.length === 0) {
              seasons = undefined
            }
          }
        }
        
        if (!mediaId || !mediaType) {
          results.failed.push({
            id: requestId,
            request_id: requestId,
            error: 'Missing mediaId or mediaType in request data'
          })
          results.failed_count++
          continue
        }
        
        // Step 2: Update the request status back to processing (status 3) using PUT
        const updateUrl = `${baseUrl}/api/v1/request/${requestId}`
        const updateBody: any = {
          mediaType,
          is4k,
          status: 3 // Set status to processing (3)
        }
        
        // Add seasons for TV shows if available (must be array of numbers)
        if (mediaType === 'tv' && seasons && Array.isArray(seasons) && seasons.length > 0) {
          updateBody.seasons = seasons
        }
        
        const updateResponse = await fetch(updateUrl, {
          method: 'PUT',
          headers: {
            'X-Api-Key': overseerrApiKey,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(updateBody)
        })
        
        if (!updateResponse.ok) {
          const errorText = await updateResponse.text()
          results.failed.push({
            id: requestId,
            request_id: requestId,
            error: `Failed to update request: ${updateResponse.status} ${errorText}`
          })
          results.failed_count++
          continue
        }
        
        const updatedRequestData = await updateResponse.json()
        const finalRequestData = updatedRequestData.request || updatedRequestData
        
        // Step 3: Update media status to processing
        if (overseerrMediaId) {
          try {
            const updateMediaStatusUrl = `${baseUrl}/api/v1/media/${overseerrMediaId}/processing`
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
              console.warn(`Failed to update media status for media ${overseerrMediaId}: ${errorText}`)
              // Don't fail the whole operation if media status update fails
            } else {
              console.log(`Successfully updated media ${overseerrMediaId} status to processing`)
            }
          } catch (mediaError) {
            console.error(`Error updating media status for media ${overseerrMediaId}:`, mediaError)
            // Don't fail the whole operation if media status update fails
          }
        }
        
        // Step 4: Send webhook to trigger processing
        const seerrbridgeUrl = process.env.SEERRBRIDGE_URL || 'http://localhost:8777'
        const webhookUrl = `${seerrbridgeUrl}/jellyseer-webhook/`
        
        try {
          const finalMediaInfo = finalRequestData.media || requestData.media || requestData
          const finalRequestInfo = finalRequestData || requestData
          
          if (requestId && finalMediaInfo) {
            // Construct webhook payload similar to overseerr-request.post.ts
            const webhookPayload = {
              notification_type: 'MEDIA_REQUESTED',
              event: 'media.requested',
              subject: `${mediaType === 'tv' ? 'TV Show' : 'Movie'} Request`,
              message: `A ${mediaType === 'tv' ? 'TV show' : 'movie'} has been requested`,
              media: {
                media_type: mediaType,
                tmdbId: finalMediaInfo.tmdbId || mediaId,
                tvdbId: finalMediaInfo.tvdbId || null,
                status: String(finalMediaInfo.status || '3'),
                status4k: String(finalMediaInfo.status4k || '3')
              },
              request: {
                request_id: String(requestId),
                requestedBy_email: finalRequestInfo.requestedBy?.email || finalRequestInfo.requestedBy_email || 'system@seerrbridge.local',
                requestedBy_username: finalRequestInfo.requestedBy?.username || finalRequestInfo.requestedBy?.displayName || finalRequestInfo.requestedBy_username || 'System',
                requestedBy_avatar: finalRequestInfo.requestedBy?.avatar || finalRequestInfo.requestedBy_avatar || '',
                requestedBy_settings_discordId: finalRequestInfo.requestedBy?.settings?.discordId || finalRequestInfo.requestedBy_settings_discordId || null,
                requestedBy_settings_telegramChatId: finalRequestInfo.requestedBy?.settings?.telegramChatId || finalRequestInfo.requestedBy_settings_telegramChatId || null
              },
              extra: seasons && seasons.length > 0 ? [{ requested_seasons: seasons }] : []
            }
            
            // Call seerrbridge webhook asynchronously (don't wait for response)
            fetch(webhookUrl, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json'
              },
              body: JSON.stringify(webhookPayload)
            }).catch((webhookError) => {
              // Log webhook error but don't fail the request
              console.error(`Failed to trigger seerrbridge webhook for request ${requestId}:`, webhookError)
            })
          }
        } catch (webhookError) {
          // Log webhook error but don't fail the request update
          console.error(`Error constructing webhook payload for request ${requestId}:`, webhookError)
        }
        
        results.success.push({
          id: requestId,
          request_id: requestId
        })
        results.success_count++
        
      } catch (error) {
        console.error(`Error retriggering request ${requestId}:`, error)
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
    console.error('Error bulk retriggering requests:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to bulk retrigger requests',
      data: error instanceof Error ? error.message : 'Unknown error'
    })
  }
})

