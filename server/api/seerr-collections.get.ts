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
    const query = getQuery(event)
    const page = Math.max(1, parseInt(query.page as string) || 1)
    const limit = Math.min(100, Math.max(1, parseInt(query.limit as string) || 20))
    const offset = (page - 1) * limit
    const rawSearch = (query.search as string) || ''
    const searchQuery = rawSearch.trim().toLowerCase()
    
    console.log('Seerr Collections API - rawSearch:', rawSearch, 'searchQuery:', searchQuery, 'page:', page, 'limit:', limit)
    
    const seerrCollectionsPath = join(process.cwd(), 'data', 'seerr-collections.json')
    
    // Check if file exists, return empty collections if not
    let fileContent: string
    try {
      fileContent = await readFile(seerrCollectionsPath, 'utf-8')
    } catch (error: any) {
      if (error.code === 'ENOENT') {
        // File doesn't exist, return empty collections
        console.warn('seerr-collections.json not found, returning empty collections')
        return {
          success: true,
          data: {
            collections: [],
            pagination: {
              page,
              limit,
              total: 0,
              total_pages: 0,
              has_next: false,
              has_prev: false
            },
            total_collections: 0,
            total_movies: 0
          }
        }
      }
      throw error
    }
    
    const data = JSON.parse(fileContent)
    
    const seerrCollections: SeerrCollection[] = data.collections || []
    
    // Transform Seerr collections to Collection format
    let allCollections: Collection[] = seerrCollections.map(seerrCollection => {
      // Extract years from release dates
      const years = seerrCollection.movieRatings
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
      for (const movie of seerrCollection.movieRatings) {
        if (movie.genres) {
          for (const genre of movie.genres) {
            genresSet.add(genre)
          }
        }
      }
      const genres = Array.from(genresSet).sort()
      
      return {
        franchise_name: seerrCollection.franchise,
        franchise_url: undefined, // Seerr collections don't have franchise URLs
        movies: seerrCollection.movieRatings,
        total_movies: seerrCollection.totalMovies,
        years: [...new Set(years)],
        genres,
        popularityScore: seerrCollection.popularityScore,
        averageRating: seerrCollection.averageRating,
        totalVotes: seerrCollection.totalVotes
      }
    })
    
    // Apply search filter if provided
    if (searchQuery) {
      allCollections = allCollections.filter(collection => {
        const franchiseNameMatch = collection.franchise_name.toLowerCase().includes(searchQuery)
        // Also search within movie titles in the collection
        const movieTitleMatch = collection.movies.some(movie => 
          movie.title.toLowerCase().includes(searchQuery) ||
          movie.original_title.toLowerCase().includes(searchQuery)
        )
        return franchiseNameMatch || movieTitleMatch
      })
    }
    
    // Sort collections by total movies (descending) then by name
    allCollections.sort((a, b) => {
      if (b.total_movies !== a.total_movies) {
        return b.total_movies - a.total_movies
      }
      return a.franchise_name.localeCompare(b.franchise_name)
    })
    
    // Apply pagination
    const totalCollections = allCollections.length
    const totalPages = Math.ceil(totalCollections / limit)
    const paginatedCollections = allCollections.slice(offset, offset + limit)
    
    // Calculate total movies across all collections
    const totalMovies = seerrCollections.reduce((sum, collection) => sum + collection.totalMovies, 0)
    
    return {
      success: true,
      data: {
        collections: paginatedCollections,
        pagination: {
          page,
          limit,
          total: totalCollections,
          total_pages: totalPages,
          has_next: page < totalPages,
          has_prev: page > 1
        },
        total_collections: totalCollections,
        total_movies: totalMovies
      }
    }
  } catch (error: any) {
    console.error('Error reading Seerr collections:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to load Seerr collections',
      data: { error: error.message }
    })
  }
})

