import { defineEventHandler, getQuery } from 'h3'
import { getDatabaseConnection } from '~/server/utils/database'
import { configEncryption } from '~/server/utils/encryption'

interface SearchResult {
  id: number
  mediaType: 'movie' | 'tv' | 'person'
  popularity?: number
  posterPath?: string
  backdropPath?: string
  voteCount?: number
  voteAverage?: number
  genreIds?: number[]
  overview?: string
  originalLanguage?: string
  title?: string
  name?: string
  originalTitle?: string
  originalName?: string
  releaseDate?: string
  firstAirDate?: string
  originCountry?: string[]
  adult?: boolean
  video?: boolean
  profilePath?: string
  knownFor?: SearchResult[]
  mediaInfo?: {
    id: number
    tmdbId: number
    tvdbId: number
    status: number
    requests?: any[]
    createdAt?: string
    updatedAt?: string
  }
}

interface SearchResponse {
  page: number
  totalPages: number
  totalResults: number
  results: SearchResult[]
}


import { getOverseerrConfig } from '~/server/utils/overseerr-config'

export default defineEventHandler(async (event) => {
  try {
    const query = getQuery(event)
    const searchQuery = query.query as string
    const page = parseInt(query.page as string) || 1
    const language = (query.language as string) || 'en'
    
    if (!searchQuery) {
      return {
        success: false,
        error: 'Query parameter is required'
      }
    }
    
    // Get Overseerr configuration with database fallback
    const { baseUrl: overseerrBaseUrl, apiKey: overseerrApiKey } = await getOverseerrConfig()
    
    if (!overseerrBaseUrl) {
      return {
        success: false,
        error: 'Overseerr base URL not configured. Please set overseerr_base in settings.'
      }
    }
    
    if (!overseerrApiKey) {
      return {
        success: false,
        error: 'Overseerr API key not configured. Please set overseerr_api_key in settings.'
      }
    }
    
    // Remove trailing slash from base URL
    const baseUrl = overseerrBaseUrl.replace(/\/$/, '')
    
    // Construct Overseerr search API URL
    const searchUrl = `${baseUrl}/api/v1/search?query=${encodeURIComponent(searchQuery)}&page=${page}&language=${language}`
    
    // Make request to Overseerr API
    console.debug('Making Overseerr search request:', { 
      searchUrl: searchUrl.replace(overseerrApiKey, '[REDACTED]'), 
      query: searchQuery 
    })
    
    const response = await fetch(searchUrl, {
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
    
    const data: SearchResponse = await response.json()
    
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
    console.error('Error searching Overseerr:', error)
    return {
      success: false,
      error: 'Failed to search Overseerr',
      details: error instanceof Error ? error.message : String(error)
    }
  }
})

