import { readFile } from 'fs/promises'
import { join } from 'path'

interface SeerrMovie {
  id: number
  title: string
  original_title: string
  rating: number
  voteCount: number
  releaseDate: string
  poster_path: string | null
  backdrop_path: string | null
  overview?: string
  tagline?: string
  runtime?: number
  genres?: string[]
  imdb_id?: string
  popularity?: number
  budget?: number
  revenue?: number
  status?: string
  original_language?: string
  production_countries?: string[]
  spoken_languages?: string[]
}

interface SeerrCollection {
  franchise: string
  popularityScore: number
  averageRating: number
  totalMovies: number
  totalVotes: number
  highestRatedMovie: {
    id: number
    title: string
    rating: number
  }
  lowestRatedMovie: {
    id: number
    title: string
    rating: number
  }
  movieRatings: SeerrMovie[]
}

interface Collection {
  franchise_name: string
  franchise_url?: string
  movies: SeerrMovie[]
  total_movies: number
  years: number[]
  genres: string[]
  popularityScore?: number
  averageRating?: number
  totalVotes?: number
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
    
    console.log('Seerr Collection API - franchise:', franchiseName, 'rawSearch:', rawSearch, 'searchQuery:', searchQuery, 'page:', page, 'limit:', limit)
    
    if (!franchiseName) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Franchise name is required'
      })
    }
    
    const seerrCollectionsPath = join(process.cwd(), 'data', 'seerr-collections.json')
    
    // Check if file exists
    let fileContent: string
    try {
      fileContent = await readFile(seerrCollectionsPath, 'utf-8')
    } catch (error: any) {
      if (error.code === 'ENOENT') {
        throw createError({
          statusCode: 404,
          statusMessage: 'Seerr collections data not available. seerr-collections.json file is missing.'
        })
      }
      throw error
    }
    
    const data = JSON.parse(fileContent)
    
    const seerrCollections: SeerrCollection[] = data.collections || []
    
    // Find collection by franchise name
    const seerrCollection = seerrCollections.find(
      collection => collection.franchise === franchiseName
    )
    
    if (!seerrCollection) {
      throw createError({
        statusCode: 404,
        statusMessage: 'Collection not found'
      })
    }
    
    // Get all movies from the collection
    let franchiseMovies = [...seerrCollection.movieRatings]
    
    // Apply search filter if provided
    if (searchQuery) {
      franchiseMovies = franchiseMovies.filter(movie => 
        movie.title.toLowerCase().includes(searchQuery) ||
        movie.original_title.toLowerCase().includes(searchQuery)
      )
    }
    
    // Sort movies by release date
    franchiseMovies.sort((a, b) => {
      const dateA = a.releaseDate ? new Date(a.releaseDate).getTime() : 0
      const dateB = b.releaseDate ? new Date(b.releaseDate).getTime() : 0
      return dateA - dateB
    })
    
    // Apply pagination
    const totalMovies = franchiseMovies.length
    const totalPages = Math.ceil(totalMovies / limit)
    const paginatedMovies = franchiseMovies.slice(offset, offset + limit)
    
    // Extract years
    const years = franchiseMovies
      .map(movie => {
        if (movie.releaseDate) {
          const year = new Date(movie.releaseDate).getFullYear()
          return isNaN(year) ? null : year
        }
        return null
      })
      .filter((year): year is number => year !== null)
      .sort((a, b) => a - b)
    
    // Extract unique genres
    const genresSet = new Set<string>()
    for (const movie of franchiseMovies) {
      if (movie.genres) {
        for (const genre of movie.genres) {
          genresSet.add(genre)
        }
      }
    }
    const genres = Array.from(genresSet).sort()
    
    // Build collection data
    const collection: Collection = {
      franchise_name: seerrCollection.franchise,
      franchise_url: undefined, // Seerr collections don't have franchise URLs
      movies: paginatedMovies,
      total_movies: totalMovies,
      years: [...new Set(years)],
      genres,
      popularityScore: seerrCollection.popularityScore,
      averageRating: seerrCollection.averageRating,
      totalVotes: seerrCollection.totalVotes
    }
    
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
    
    console.error('Error reading Seerr collection:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to load Seerr collection',
      data: { error: error.message }
    })
  }
})

