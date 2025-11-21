import { defineEventHandler, getQuery } from 'h3'
import { getOverseerrConfig } from '~/server/utils/overseerr-config'

export default defineEventHandler(async (event) => {
  try {
    const query = getQuery(event)
    const page = parseInt(query.page as string) || 1
    const sortBy = (query.sortBy as string) || 'popularity.desc'
    const language = (query.language as string) || 'en'
    const type = (query.type as string) || 'movies' // 'movies' or 'tv'
    
    // Get Overseerr configuration with database fallback
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
    
    // Construct Overseerr discover API URL based on type
    const endpoint = type === 'tv' ? 'tv' : 'movies'
    const discoverUrl = `${baseUrl}/api/v1/discover/${endpoint}?page=${page}&sortBy=${sortBy}&language=${language}`
    
    // Make request to Overseerr API
    
    const response = await fetch(discoverUrl, {
      method: 'GET',
      headers: {
        'X-Api-Key': overseerrApiKey,
        'Content-Type': 'application/json'
      }
    })
    
    if (!response.ok) {
      const errorText = await response.text()
      console.error('Overseerr API error:', {
        status: response.status,
        statusText: response.statusText,
        error: errorText.substring(0, 200)
      })
      return {
        success: false,
        error: `Overseerr API error: ${response.status} ${response.statusText}`,
        details: errorText
      }
    }
    
    const data = await response.json()
    
    return {
      success: true,
      data: {
        page: data.page,
        totalPages: data.totalPages,
        totalResults: data.totalResults,
        results: data.results
      }
    }
    
  } catch (error) {
    console.error('Error discovering media from Overseerr:', error)
    return {
      success: false,
      error: 'Failed to discover media',
      details: error instanceof Error ? error.message : String(error)
    }
  }
})

