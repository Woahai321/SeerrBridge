import { defineEventHandler, readBody, createError } from 'h3'
import { getOverseerrConfig } from '~/server/utils/overseerr-config'

// Simple logger for database operations
const logger = {
  info: (msg: string) => console.log(`[DB] ${msg}`),
  warn: (msg: string) => console.warn(`[DB] ${msg}`),
  error: (msg: string) => console.error(`[DB] ${msg}`)
}

/**
 * Find TMDB ID for a media item using fallback methods (same as list-sync)
 * Priority: TMDB ID → IMDB→Trakt→TMDB → Title→Trakt→TMDB → Overseerr search
 */
async function findMediaId(
  item: any,
  overseerrBaseUrl: string,
  overseerrApiKey: string,
  seerrbridgeUrl: string = process.env.SEERRBRIDGE_URL || 'http://localhost:8777'
): Promise<{ tmdbId: number | null; method: string; error?: string }> {
  const { tmdb_id, imdb_id, title, year, media_type } = item

  // METHOD 1: Direct TMDB ID lookup (fastest, most reliable)
  if (tmdb_id) {
    try {
      const tmdbIdInt = parseInt(tmdb_id)
      if (!isNaN(tmdbIdInt)) {
        const mediaCheckUrl = `${overseerrBaseUrl}/api/v1/${media_type}/${tmdbIdInt}`
        const response = await fetch(mediaCheckUrl, {
          headers: {
            'X-Api-Key': overseerrApiKey,
            'Content-Type': 'application/json'
          }
        })

        if (response.ok || response.status === 404) {
          // 404 is fine - media exists in TMDB, just not in Overseerr yet
          return { tmdbId: tmdbIdInt, method: 'TMDB_ID_DIRECT' }
        }
      }
    } catch (error) {
      console.warn(`Direct TMDB lookup failed for ${title}:`, error)
    }
  }

  // METHOD 2: IMDB ID → Trakt → TMDB ID
  if (imdb_id) {
    try {
      const response = await fetch(`${seerrbridgeUrl}/api/trakt-lists/search-by-imdb`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ imdb_id })
      })
      
      if (response.ok) {
        const result = await response.json()
        
        if (result.success && result.tmdb_id) {
          const tmdbIdInt = parseInt(result.tmdb_id)
          if (!isNaN(tmdbIdInt)) {
            return { tmdbId: tmdbIdInt, method: 'IMDB_TO_TMDB' }
          }
        }
      }
    } catch (error) {
      console.warn(`IMDB→Trakt→TMDB lookup failed for ${title}:`, error)
    }
  }

  // METHOD 3: Title/Year → Trakt → TMDB ID
  if (title) {
    try {
      const response = await fetch(`${seerrbridgeUrl}/api/trakt-lists/search-by-title`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, year, media_type })
      })
      
      if (response.ok) {
        const result = await response.json()
        
        if (result.success && result.tmdb_id) {
          const tmdbIdInt = parseInt(result.tmdb_id)
          if (!isNaN(tmdbIdInt)) {
            return { tmdbId: tmdbIdInt, method: 'TITLE_TO_TMDB' }
          }
        }
      }
    } catch (error) {
      console.warn(`Title→Trakt→TMDB lookup failed for ${title}:`, error)
    }
  }

  // METHOD 4: Fallback to Overseerr title search (least reliable)
  try {
    const searchTitle = title.replace(/\s*\(?(?:19|20)\d{2}\)?$/, '').trim() || title
    const searchUrl = `${overseerrBaseUrl}/api/v1/search?query=${encodeURIComponent(searchTitle)}&page=1&language=en`
    
    const response = await fetch(searchUrl, {
      headers: {
        'X-Api-Key': overseerrApiKey,
        'Content-Type': 'application/json'
      }
    })

    if (response.ok) {
      const data = await response.json()
      const results = data.results || []
      
      // Find best match
      for (const result of results) {
        if (result.mediaType === media_type) {
          const resultYear = result.releaseDate?.substring(0, 4) || result.firstAirDate?.substring(0, 4)
          if (!year || !resultYear || Math.abs(parseInt(resultYear) - year) <= 1) {
            return { tmdbId: result.id, method: 'OVERSEERR_SEARCH_FALLBACK' }
          }
        }
      }
    }
  } catch (error) {
    console.warn(`Overseerr search fallback failed for ${title}:`, error)
  }

  return { tmdbId: null, method: 'NOT_FOUND', error: 'Could not find TMDB ID using any method' }
}

export default defineEventHandler(async (event) => {
  // Declare variables at function scope so they're available in catch block
  let sessionId: string | null = null
  let seerrbridgeUrl: string = 'http://localhost:8777'
  
  try {
    const body = await readBody(event)
    const { listId, limit, dryRun = false } = body

    if (!listId || !listId.trim()) {
      throw createError({
        statusCode: 400,
        statusMessage: 'listId is required'
      })
    }

    // Step 1: Fetch Trakt list from SeerrBridge backend
    const config = useRuntimeConfig(event)
    seerrbridgeUrl = config.seerrbridgeUrl || 'http://localhost:8777'
    
    let fetchResult: any
    try {
      // Detect list type for fetch endpoint
      let fetchListType: string | undefined = undefined
      if (listId.toLowerCase().includes('letterboxd.com') || listId.toLowerCase().startsWith('letterboxd/')) {
        fetchListType = 'letterboxd'
      } else if (listId.includes(':') && !listId.startsWith('http')) {
        const parts = listId.split(':')
        if (parts.length === 2) {
          const category = parts[0].toLowerCase()
          const validCategories = ['trending', 'popular', 'anticipated', 'watched', 'collected', 
                                  'recommendations', 'boxoffice', 'favorited']
          if (validCategories.includes(category)) {
            fetchListType = 'trakt_special'
          }
        }
      }
      
      const response = await fetch(`${seerrbridgeUrl}/api/trakt-lists/fetch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          listId: listId.trim(),
          limit: limit || undefined,
          listType: fetchListType
        })
      })

      if (!response.ok) {
        const errorText = await response.text()
        let errorMessage = 'Failed to fetch Trakt list'
        
        try {
          const errorData = JSON.parse(errorText)
          errorMessage = errorData.detail || errorData.error || errorMessage
        } catch {
          errorMessage = errorText || `HTTP ${response.status}`
        }
        
        throw createError({
          statusCode: response.status,
          statusMessage: errorMessage
        })
      }

      fetchResult = await response.json()
      
      if (!fetchResult.success) {
        throw createError({
          statusCode: 500,
          statusMessage: fetchResult.error || 'Failed to fetch Trakt list'
        })
      }
    } catch (error: any) {
      if (error.statusCode) throw error
      console.error('Error fetching Trakt list:', error)
      throw createError({
        statusCode: 500,
        statusMessage: `Failed to fetch Trakt list: ${error.message || 'Unknown error'}`
      })
    }

    if (dryRun) {
      return {
        success: true,
        dryRun: true,
        items: fetchResult.items,
        count: fetchResult.count,
        message: `Would sync ${fetchResult.count} items from Trakt list`
      }
    }

    // Step 2: Get Overseerr config
    const { baseUrl: overseerrBaseUrl, apiKey: overseerrApiKey } = await getOverseerrConfig()
    
    if (!overseerrBaseUrl || !overseerrApiKey) {
      throw createError({
        statusCode: 500,
        statusMessage: 'Overseerr not configured. Please configure Overseerr in settings.'
      })
    }

    const baseUrl = overseerrBaseUrl.replace(/\/$/, '')
    const requestUrl = `${baseUrl}/api/v1/request`

    // Step 2.5: Create database records for list and sync history
    // This ensures we track all sync operations in the database
    const seerrbridgeUrlForDb = seerrbridgeUrl // Use same URL for database operations
    let traktListId: number | null = null
    
    try {
      // Detect list type (check if it's a Trakt Special list or Letterboxd)
      let detectedListType: string | undefined = undefined
      
      // Check for Letterboxd lists
      if (listId.toLowerCase().includes('letterboxd.com') || listId.toLowerCase().startsWith('letterboxd/')) {
        detectedListType = 'letterboxd'
      }
      // Check for Trakt Special lists
      else if (listId.includes(':') && !listId.startsWith('http')) {
        const parts = listId.split(':')
        if (parts.length === 2) {
          const category = parts[0].toLowerCase()
          const validCategories = ['trending', 'popular', 'anticipated', 'watched', 'collected', 
                                  'recommendations', 'boxoffice', 'favorited']
          if (validCategories.includes(category)) {
            detectedListType = 'trakt_special'
          }
        }
      }
      
      // Get or create Trakt list in database
      // This creates a record if it doesn't exist, or updates metadata if it does
      const listResponse = await fetch(`${seerrbridgeUrlForDb}/api/trakt-lists/get-or-create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          listId: listId.trim(),
          listType: detectedListType
        })
      })
      
      if (listResponse.ok) {
        const listData = await listResponse.json()
        traktListId = listData.listId
        logger.info(`Database: Got/created Trakt list ID ${traktListId} for ${listId.trim()}`)
        
        // Create sync history record
        // This creates a new sync session that we'll update as we process items
        const historyResponse = await fetch(`${seerrbridgeUrlForDb}/api/trakt-lists/create-sync-history`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            traktListId: traktListId,
            syncType: dryRun ? 'dry_run' : 'manual',
            totalItems: fetchResult.count
          })
        })
        
        if (historyResponse.ok) {
          const historyData = await historyResponse.json()
          sessionId = historyData.sessionId
          logger.info(`Database: Created sync history session ${sessionId} for list ${traktListId}`)
        } else {
          const errorText = await historyResponse.text()
          logger.warn(`Database: Failed to create sync history: ${historyResponse.status} ${errorText}`)
        }
      } else {
        const errorText = await listResponse.text()
        logger.warn(`Database: Failed to create/get list: ${listResponse.status} ${errorText}`)
        // Continue anyway - we can still sync without database tracking
      }
    } catch (error) {
      logger.error('Database: Failed to create database records:', error)
      // Continue anyway - we can still sync without database tracking
    }

    // Step 3: Process each item
    const results = {
      requested: 0,
      alreadyRequested: 0,
      alreadyAvailable: 0,
      notFound: 0,
      errors: 0,
      details: [] as any[]
    }

    for (const item of fetchResult.items) {
      const { media_type, title, year, season_number } = item

      try {
        // Find TMDB ID using fallback methods (same as list-sync)
        const { tmdbId, method, error: lookupError } = await findMediaId(item, baseUrl, overseerrApiKey, seerrbridgeUrlForDb)

        if (!tmdbId) {
          results.notFound++
          results.details.push({
            title,
            year,
            status: 'not_found',
            reason: lookupError || 'No TMDB ID available',
            method
          })
          
          // Save to database
          if (sessionId) {
            try {
              await fetch(`${seerrbridgeUrlForDb}/api/trakt-lists/save-sync-item`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  sessionId,
                  item: { ...item, _list_identifier: listId.trim() },
                  status: 'not_found',
                  matchMethod: method,
                  errorMessage: lookupError || 'No TMDB ID available'
                })
              })
            } catch (error) {
              console.warn(`Failed to save sync item for ${title}:`, error)
            }
          }
          continue
        }

        // Check if media exists and is available/requested
        const mediaCheckUrl = `${baseUrl}/api/v1/${media_type}/${tmdbId}`
        let mediaData: any = null
        let numberOfSeasons = 1

        try {
          const mediaCheckResponse = await fetch(mediaCheckUrl, {
            headers: {
              'X-Api-Key': overseerrApiKey,
              'Content-Type': 'application/json'
            }
          })

          if (mediaCheckResponse.ok) {
            mediaData = await mediaCheckResponse.json()
            const mediaInfo = mediaData.mediaInfo
            
            if (mediaInfo) {
              const status = mediaInfo.status
              // Status codes: 0=not requested, 1-3=requested/processing, 4-5=available
            if (status >= 4) {
              results.alreadyAvailable++
              results.details.push({
                title,
                year,
                status: 'already_available',
                tmdb_id: tmdbId,
                method
              })
              
              // Save to database
              if (sessionId) {
                try {
                  await fetch(`${seerrbridgeUrlForDb}/api/trakt-lists/save-sync-item`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                      sessionId,
                      item: { ...item, tmdb_id: tmdbId, _list_identifier: listId.trim() },
                      status: 'already_available',
                      matchMethod: method
                    })
                  })
                } catch (error) {
                  console.warn(`Failed to save sync item for ${title}:`, error)
                }
              }
              continue
            } else if (status >= 1) {
              results.alreadyRequested++
              results.details.push({
                title,
                year,
                status: 'already_requested',
                tmdb_id: tmdbId,
                method
              })
              
              // Save to database
              if (sessionId) {
                try {
                  await fetch(`${seerrbridgeUrlForDb}/api/trakt-lists/save-sync-item`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                      sessionId,
                      item: { ...item, tmdb_id: tmdbId, _list_identifier: listId.trim() },
                      status: 'already_requested',
                      matchMethod: method
                    })
                  })
                } catch (error) {
                  console.warn(`Failed to save sync item for ${title}:`, error)
                }
              }
              continue
            }
            }

            // Get number of seasons for TV shows
            if (media_type === 'tv' && mediaData.numberOfSeasons) {
              numberOfSeasons = mediaData.numberOfSeasons
            }
          } else if (mediaCheckResponse.status !== 404) {
            // 404 is fine (media not in Overseerr yet), other errors are problems
            throw new Error(`Media check failed: ${mediaCheckResponse.status} ${mediaCheckResponse.statusText}`)
          }
        } catch (checkError: any) {
          // If media check fails but we have a TMDB ID, still try to request
          console.warn(`Media check failed for ${title} (TMDB: ${tmdbId}):`, checkError.message)
        }

        // Create request
        const requestBody: any = {
          mediaType: media_type,
          mediaId: tmdbId,
          is4k: false
        }

        // Add seasons for TV shows
        if (media_type === 'tv') {
          if (season_number) {
            // Request specific season
            requestBody.seasons = [parseInt(season_number)]
          } else {
            // Request all seasons
            requestBody.seasons = Array.from({ length: numberOfSeasons }, (_, i) => i + 1)
          }
        }

        const requestResponse = await fetch(requestUrl, {
          method: 'POST',
          headers: {
            'X-Api-Key': overseerrApiKey,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(requestBody)
        })

        if (requestResponse.ok) {
          const requestData = await requestResponse.json()
          const overseerrRequestId = requestData?.media?.request?.id || null
          
          results.requested++
          results.details.push({
            title,
            year,
            status: 'requested',
            tmdb_id: tmdbId,
            season_number: season_number || undefined,
            method,
            overseerr_request_id: overseerrRequestId
          })
          
          // Save to database if we have session ID
          if (sessionId) {
            try {
              await fetch(`${seerrbridgeUrlForDb}/api/trakt-lists/save-sync-item`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  sessionId,
                  item: {
                    ...item,
                    tmdb_id: tmdbId,
                    _list_identifier: listId.trim()
                  },
                  status: 'requested',
                  matchMethod: method,
                  overseerrRequestId: overseerrRequestId
                })
              })
            } catch (error) {
              console.warn(`Failed to save sync item for ${title}:`, error)
            }
          }
        } else {
          const errorText = await requestResponse.text()
          let errorMessage = errorText.substring(0, 200)
          
          // Check if it's already requested (400 with "already" in message)
          if (requestResponse.status === 400 && errorText.toLowerCase().includes('already')) {
            results.alreadyRequested++
            results.details.push({
              title,
              year,
              status: 'already_requested',
              tmdb_id: tmdbId,
              method
            })
            
            // Save to database
            if (sessionId) {
              try {
                await fetch(`${seerrbridgeUrlForDb}/api/trakt-lists/save-sync-item`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    sessionId,
                    item: { ...item, tmdb_id: tmdbId, _list_identifier: listId.trim() },
                    status: 'already_requested',
                    matchMethod: method
                  })
                })
              } catch (error) {
                console.warn(`Failed to save sync item for ${title}:`, error)
              }
            }
          } else {
            results.errors++
            results.details.push({
              title,
              year,
              status: 'error',
              tmdb_id: tmdbId,
              error: errorMessage,
              method
            })
            
            // Save to database
            if (sessionId) {
              try {
                await fetch(`${seerrbridgeUrlForDb}/api/trakt-lists/save-sync-item`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    sessionId,
                    item: { ...item, tmdb_id: tmdbId, _list_identifier: listId.trim() },
                    status: 'error',
                    matchMethod: method,
                    errorMessage: errorMessage
                  })
                })
              } catch (error) {
                console.warn(`Failed to save sync item for ${title}:`, error)
              }
            }
          }
        }
      } catch (error: any) {
        results.errors++
        results.details.push({
          title,
          year,
          status: 'error',
          tmdb_id: item.tmdb_id || null,
          error: error.message || String(error)
        })
        console.error(`Error processing item ${title}:`, error)
        
        // Save to database
        if (sessionId) {
          try {
                await fetch(`${seerrbridgeUrlForDb}/api/trakt-lists/save-sync-item`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                sessionId,
                item: { ...item, _list_identifier: listId.trim() },
                status: 'error',
                errorMessage: error.message || String(error)
              })
            })
          } catch (dbError) {
            console.warn(`Failed to save sync item for ${title}:`, dbError)
          }
        }
      }
    }

    // Update sync history with final results
    // This updates the sync count, item counts, and marks the sync as completed
    if (sessionId) {
      try {
        const updateResponse = await fetch(`${seerrbridgeUrlForDb}/api/trakt-lists/update-sync-history`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            sessionId,
            status: 'completed',
            itemsRequested: results.requested,
            itemsAlreadyRequested: results.alreadyRequested,
            itemsAlreadyAvailable: results.alreadyAvailable,
            itemsNotFound: results.notFound,
            itemsErrors: results.errors,
            details: {
              totalItems: fetchResult.count,
              results: results.details
            }
          })
        })
        
        if (updateResponse.ok) {
          logger.info(`Database: Updated sync history ${sessionId} - Requested: ${results.requested}, Already Requested: ${results.alreadyRequested}, Already Available: ${results.alreadyAvailable}, Not Found: ${results.notFound}, Errors: ${results.errors}`)
        } else {
          const errorText = await updateResponse.text()
          logger.warn(`Database: Failed to update sync history: ${updateResponse.status} ${errorText}`)
        }
      } catch (error) {
        logger.error(`Database: Error updating sync history: ${error}`)
      }
    } else {
      logger.warn('Database: No session ID available to update sync history')
    }

    return {
      success: true,
      listId,
      sessionId,
      totalItems: fetchResult.count,
      results: {
        requested: results.requested,
        alreadyRequested: results.alreadyRequested,
        alreadyAvailable: results.alreadyAvailable,
        notFound: results.notFound,
        errors: results.errors
      },
      details: results.details
    }
  } catch (error: any) {
    console.error('Error syncing Trakt list:', error)
    
    // Mark sync as failed in database if we have a session ID
    if (sessionId) {
      try {
        const errorMessage = error.statusMessage || error.message || 'Failed to sync Trakt list'
        await fetch(`${seerrbridgeUrl}/api/trakt-lists/update-sync-history`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            sessionId,
            status: 'failed',
            itemsRequested: 0,
            itemsAlreadyRequested: 0,
            itemsAlreadyAvailable: 0,
            itemsNotFound: 0,
            itemsErrors: 0,
            errorMessage: errorMessage.substring(0, 500) // Limit error message length
          })
        })
      } catch (dbError) {
        console.warn('Failed to update sync history with error status:', dbError)
      }
    }
    
    // Provide user-friendly error messages
    let errorMessage = 'Failed to sync Trakt list'
    if (error.statusCode === 400) {
      errorMessage = error.statusMessage || 'Invalid request. Please check your input.'
    } else if (error.statusCode === 500) {
      errorMessage = error.statusMessage || 'Server error. Please check your configuration and try again.'
    } else if (error.message) {
      errorMessage = error.message
    }
    
    throw createError({
      statusCode: error.statusCode || 500,
      statusMessage: errorMessage
    })
  }
})
