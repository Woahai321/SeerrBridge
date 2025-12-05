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
    const seerrbridgeUrl = process.env.SEERRBRIDGE_URL || 'http://localhost:8777'
    const webhookUrl = `${seerrbridgeUrl}/jellyseer-webhook/`
    
    const results = {
      success: [] as Array<{ id: number; request_id: number }>,
      failed: [] as Array<{ id: number; request_id: number; error: string }>,
      success_count: 0,
      failed_count: 0
    }
    
    // Process retriggers in parallel with error handling
    await Promise.all(
      requestIds.map(async (requestId: number) => {
        try {
          const requestIdNum = typeof requestId === 'string' ? parseInt(requestId, 10) : requestId
          
          if (isNaN(requestIdNum)) {
            throw new Error('Invalid request ID')
          }
          
          // Step 1: Fetch request details
          const getRequestUrl = `${baseUrl}/api/v1/request/${requestIdNum}`
          const getResponse = await fetch(getRequestUrl, {
            method: 'GET',
            headers: {
              'X-Api-Key': overseerrApiKey,
              'Content-Type': 'application/json'
            }
          })
          
          if (!getResponse.ok) {
            const errorText = await getResponse.text()
            throw new Error(`Failed to fetch request: HTTP ${getResponse.status}: ${errorText}`)
          }
          
          const requestData = await getResponse.json()
          const media = requestData.media || requestData
          const mediaId = media.tmdbId || media.tmdb_id
          const mediaType = media.mediaType || media.media_type
          const overseerrMediaId = media.id || requestData.media?.id
          const is4k = requestData.is4k || false
          
          // Extract seasons for TV shows
          let seasons: number[] | undefined = undefined
          if (mediaType === 'tv') {
            const rawSeasons = requestData.seasons || requestData.media?.seasons
            if (rawSeasons && Array.isArray(rawSeasons) && rawSeasons.length > 0) {
              seasons = rawSeasons
                .map((s: any) => {
                  if (typeof s === 'object' && s !== null && 'seasonNumber' in s) {
                    return s.seasonNumber
                  }
                  return s
                })
                .map((s: any) => {
                  const num = typeof s === 'string' ? parseInt(s, 10) : Number(s)
                  return isNaN(num) ? null : num
                })
                .filter((s: any): s is number => s !== null && s !== undefined) as number[]
              
              if (seasons.length === 0) {
                seasons = undefined
              }
            }
          }
          
          if (!mediaId || !mediaType) {
            throw new Error('Missing mediaId or mediaType in request data')
          }
          
          // Step 2: Update the request
          const updateUrl = `${baseUrl}/api/v1/request/${requestIdNum}`
          const updateBody: any = {
            mediaType,
            is4k,
            status: 3 // Set status to processing (3)
          }
          
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
            throw new Error(`Failed to update request: HTTP ${updateResponse.status}: ${errorText}`)
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
          
          // Step 4: Send webhook
          try {
            const finalMediaInfo = finalRequestData.media || requestData.media || requestData
            const finalRequestInfo = finalRequestData || requestData
            
            if (requestIdNum && finalMediaInfo) {
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
                  request_id: String(requestIdNum),
                  requestedBy_email: finalRequestInfo.requestedBy?.email || finalRequestInfo.requestedBy_email || 'system@seerrbridge.local',
                  requestedBy_username: finalRequestInfo.requestedBy?.username || finalRequestInfo.requestedBy?.displayName || finalRequestInfo.requestedBy_username || 'System',
                  requestedBy_avatar: finalRequestInfo.requestedBy?.avatar || finalRequestInfo.requestedBy_avatar || '',
                  requestedBy_settings_discordId: finalRequestInfo.requestedBy?.settings?.discordId || finalRequestInfo.requestedBy_settings_discordId || null,
                  requestedBy_settings_telegramChatId: finalRequestInfo.requestedBy?.settings?.telegramChatId || finalRequestInfo.requestedBy_settings_telegramChatId || null
                },
                extra: seasons && seasons.length > 0 ? [{ requested_seasons: seasons }] : []
              }
              
              // Call webhook asynchronously
              fetch(webhookUrl, {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json'
                },
                body: JSON.stringify(webhookPayload)
              }).catch((webhookError) => {
                console.error(`Failed to trigger webhook for request ${requestIdNum}:`, webhookError)
              })
            }
          } catch (webhookError) {
            console.error(`Error constructing webhook for request ${requestIdNum}:`, webhookError)
            // Don't fail the whole operation if webhook fails
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
    console.error('Error bulk retriggering requests:', error)
    throw createError({
      statusCode: error.statusCode || 500,
      statusMessage: error.statusMessage || 'Failed to bulk retrigger requests',
      data: error instanceof Error ? error.message : 'Unknown error'
    })
  }
})

