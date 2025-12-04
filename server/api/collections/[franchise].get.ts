import { readFile } from 'fs/promises'
import { join } from 'path'

interface Movie {
  title: string
  title_original: string
  year: number
  release_date?: string
  sources: {
    franchises?: {
      franchise_name: string
      franchise_url: string
    }
    boxofficemojo?: {
      franchise_name: string
      franchise_url: string
    }
  }
  trakt?: {
    trakt_id: number
    title: string
    year: number
    ids: {
      trakt: number
      slug: string
      imdb?: string
      tmdb?: number
    }
    overview?: string
    rating?: number
    votes?: number
    genres?: string[]
    certification?: string
    runtime?: number
    tagline?: string
    trailer?: string
    homepage?: string
  }
  local_images?: {
    poster?: string
    fanart?: string
    logo?: string
    clearart?: string
    banner?: string
  }
  images_dir?: string
}

interface Collection {
  franchise_name: string
  franchise_url?: string
  movies: Movie[]
  total_movies: number
  years: number[]
  genres: string[]
}

export default defineEventHandler(async (event) => {
  try {
    const franchiseName = decodeURIComponent(getRouterParam(event, 'franchise') || '')
    const query = getQuery(event)
    const page = Math.max(1, parseInt(query.page as string) || 1)
    const limit = Math.min(100, Math.max(1, parseInt(query.limit as string) || 30))
    const offset = (page - 1) * limit
    const rawSearch = (query.search as string) || ''
    const searchQuery = rawSearch.trim().toLowerCase()
    
    console.log('Collection API - franchise:', franchiseName, 'rawSearch:', rawSearch, 'searchQuery:', searchQuery, 'page:', page, 'limit:', limit)
    
    if (!franchiseName) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Franchise name is required'
      })
    }
    
    const unifiedJsonPath = join(process.cwd(), 'data', 'unified.json')
    
    // Check if file exists
    let fileContent: string
    try {
      fileContent = await readFile(unifiedJsonPath, 'utf-8')
    } catch (error: any) {
      if (error.code === 'ENOENT') {
        throw createError({
          statusCode: 404,
          statusMessage: 'Collections data not available. unified.json file is missing.'
        })
      }
      throw error
    }
    
    const data = JSON.parse(fileContent)
    
    const movies: Movie[] = data.movies || []
    
    // Find movies for this franchise
    let franchiseMovies = movies.filter(movie => {
      const movieFranchiseName = movie.sources?.franchises?.franchise_name || 
                                 movie.sources?.boxofficemojo?.franchise_name
      return movieFranchiseName === franchiseName
    })
    
    if (franchiseMovies.length === 0) {
      throw createError({
        statusCode: 404,
        statusMessage: 'Collection not found'
      })
    }
    
    // Apply search filter if provided
    if (searchQuery) {
      franchiseMovies = franchiseMovies.filter(movie => 
        movie.title.toLowerCase().includes(searchQuery) ||
        movie.title_original.toLowerCase().includes(searchQuery) ||
        (movie.trakt?.title && movie.trakt.title.toLowerCase().includes(searchQuery))
      )
    }
    
    // Sort movies by year
    franchiseMovies.sort((a, b) => (a.year || 0) - (b.year || 0))
    
    // Apply pagination
    const totalMovies = franchiseMovies.length
    const totalPages = Math.ceil(totalMovies / limit)
    const paginatedMovies = franchiseMovies.slice(offset, offset + limit)
    
    // Build collection data
    const collection: Collection = {
      franchise_name: franchiseName,
      franchise_url: franchiseMovies[0].sources?.franchises?.franchise_url || 
                     franchiseMovies[0].sources?.boxofficemojo?.franchise_url,
      movies: paginatedMovies,
      total_movies: totalMovies,
      years: [...new Set(franchiseMovies.map(m => m.year).filter(Boolean))].sort((a, b) => a - b),
      genres: []
    }
    
    // Collect unique genres
    const genresSet = new Set<string>()
    for (const movie of franchiseMovies) {
      if (movie.trakt?.genres) {
        for (const genre of movie.trakt.genres) {
          genresSet.add(genre)
        }
      }
    }
    collection.genres = Array.from(genresSet).sort()
    
    return {
      success: true,
      data: {
        collection,
        pagination: {
          page,
          limit,
          total: totalMovies,
          total_pages: totalPages,
          has_next: page < totalPages,
          has_prev: page > 1
        }
      }
    }
  } catch (error: any) {
    if (error.statusCode) {
      throw error
    }
    
    console.error('Error reading collection:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to load collection',
      data: { error: error.message }
    })
  }
})

