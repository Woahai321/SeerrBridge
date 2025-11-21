import { defineEventHandler, readBody } from 'h3'

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody(event)
    const { trakt_api_key, tmdb_id, media_type = 'movie' } = body
    
    // DO NOT log API key value - only log presence
    console.debug('Trakt test request:', { trakt_api_key: trakt_api_key ? 'provided' : 'missing', tmdb_id, media_type })
    
    if (!trakt_api_key) {
      return {
        success: false,
        error: 'Missing Trakt API key'
      }
    }
    
    // Test Trakt API by fetching media details
    try {
      // If tmdb_id is provided, fetch that specific media
      if (tmdb_id) {
        console.debug(`Testing Trakt with TMDB ID: ${tmdb_id}, type: ${media_type}`)
        const type = media_type === 'tv' ? 'show' : 'movie'
        const url = `https://api.trakt.tv/search/tmdb/${tmdb_id}?type=${type}`
        
        console.debug(`Trakt search URL: ${url}`)
        
        const response = await fetch(url, {
          headers: {
            'Content-type': 'application/json',
            'trakt-api-key': trakt_api_key,
            'trakt-api-version': '2'
          }
        })
        
        console.debug(`Trakt search response status: ${response.status}`)
        
        if (response.ok) {
          const data = await response.json()
          // DO NOT log full API response - may contain sensitive data
          console.debug(`Trakt search response: ${data?.length || 0} results`)
          
          if (data && data.length > 0) {
            const media = data[0][type]
            // DO NOT log full media data
            console.debug(`Found media: ${media?.title || media?.name || 'Unknown'}`)
            
            if (media && media.ids && media.ids.trakt) {
              // Get detailed information
              const detailedUrl = `https://api.trakt.tv/${type}s/${media.ids.trakt}?extended=full`
              console.debug(`Trakt details URL: ${detailedUrl}`)
              
              const detailedResponse = await fetch(detailedUrl, {
                headers: {
                  'Content-type': 'application/json',
                  'trakt-api-key': trakt_api_key,
                  'trakt-api-version': '2'
                }
              })
              
              console.debug(`Trakt details response status: ${detailedResponse.status}`)
              
              if (detailedResponse.ok) {
                const detailedData = await detailedResponse.json()
                // DO NOT log full detailed data
                console.debug(`Trakt details retrieved: ${detailedData?.title || detailedData?.name || 'Unknown'}`)
                
                return {
                  success: true,
                  data: {
                    title: detailedData.title || detailedData.name,
                    year: detailedData.year,
                    overview: detailedData.overview,
                    poster_url: null, // Trakt doesn't provide poster URLs directly
                    fanart_url: null, // Trakt doesn't provide fanart URLs directly
                    backdrop_url: null, // Trakt doesn't provide backdrop URLs directly
                    genres: detailedData.genres || [],
                    rating: detailedData.rating || 0,
                    runtime: detailedData.runtime || 0,
                    aired_episodes: detailedData.aired_episodes || 0,
                    tagline: detailedData.tagline || '',
                    first_aired: detailedData.first_aired || '',
                    trakt_id: detailedData.ids?.trakt,
                    tmdb_id: detailedData.ids?.tmdb,
                    imdb_id: detailedData.ids?.imdb
                  }
                }
              } else {
                const errorText = await detailedResponse.text()
                console.error(`Trakt details API error: ${detailedResponse.status} - ${errorText}`)
                return {
                  success: false,
                  error: `Trakt details API returned status ${detailedResponse.status}`
                }
              }
            } else {
              console.error('Media found but no Trakt ID:', media)
              return {
                success: false,
                error: 'Media found but no Trakt ID available'
              }
            }
          } else {
            console.error('No media found in Trakt search results')
            return {
              success: false,
              error: 'No media found for the given TMDB ID'
            }
          }
        } else {
          const errorText = await response.text()
          console.error(`Trakt search API error: ${response.status} - ${errorText}`)
          return {
            success: false,
            error: `Trakt search API returned status ${response.status}`
          }
        }
      } else {
        // No tmdb_id provided, just test API access
        console.debug('Testing Trakt API access without specific media')
        const url = 'https://api.trakt.tv/shows/popular'
        const response = await fetch(url, {
          headers: {
            'Content-type': 'application/json',
            'trakt-api-key': trakt_api_key,
            'trakt-api-version': '2'
          }
        })
        
        console.debug(`Trakt popular shows response status: ${response.status}`)
        
        if (response.ok) {
          const data = await response.json()
          // DO NOT log full response data
          console.debug(`Trakt API test successful, found ${data.length} popular shows`)
          return {
            success: true,
            data: {
              message: 'Trakt API connection successful',
              test_data: data.slice(0, 1)[0] // Return first show as example
            }
          }
        } else {
          const errorText = await response.text()
          console.error(`Trakt API error: ${response.status} - ${errorText}`)
          return {
            success: false,
            error: `Trakt API returned status ${response.status}`
          }
        }
      }
    } catch (fetchError: any) {
      console.error('Trakt connection error:', fetchError)
      return {
        success: false,
        error: `Failed to connect to Trakt: ${fetchError.message}`
      }
    }
    
    return {
      success: false,
      error: 'Could not fetch media details from Trakt'
    }
  } catch (error: any) {
    console.error('Error testing Trakt credentials:', error)
    return {
      success: false,
      error: 'Failed to test Trakt credentials'
    }
  }
})

