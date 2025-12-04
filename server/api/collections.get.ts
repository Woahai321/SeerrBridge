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
    const query = getQuery(event)
    const page = Math.max(1, parseInt(query.page as string) || 1)
    const limit = Math.min(100, Math.max(1, parseInt(query.limit as string) || 20))
    const offset = (page - 1) * limit
    const rawSearch = (query.search as string) || ''
    const searchQuery = rawSearch.trim().toLowerCase()
    
    console.log('Collections API - rawSearch:', rawSearch, 'searchQuery:', searchQuery, 'page:', page, 'limit:', limit)
    
    const unifiedJsonPath = join(process.cwd(), 'data', 'unified.json')
    
    // Check if file exists, return empty collections if not
    let fileContent: string
    try {
      fileContent = await readFile(unifiedJsonPath, 'utf-8')
    } catch (error: any) {
      if (error.code === 'ENOENT') {
        // File doesn't exist, return empty collections
        console.warn('unified.json not found, returning empty collections')
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
    
    const movies: Movie[] = data.movies || []
    
    // Group movies by franchise name
    const collectionsMap = new Map<string, Collection>()
    
    for (const movie of movies) {
      // Get franchise name from sources (prioritize franchises over boxofficemojo)
      const franchiseName = movie.sources?.franchises?.franchise_name || 
                           movie.sources?.boxofficemojo?.franchise_name
      
      if (!franchiseName) {
        continue
      }
      
      // Get or create collection
      if (!collectionsMap.has(franchiseName)) {
        collectionsMap.set(franchiseName, {
          franchise_name: franchiseName,
          franchise_url: movie.sources?.franchises?.franchise_url || 
                         movie.sources?.boxofficemojo?.franchise_url,
          movies: [],
          total_movies: 0,
          years: [],
          genres: []
        })
      }
      
      const collection = collectionsMap.get(franchiseName)!
      collection.movies.push(movie)
      
      // Add year if not already present
      if (movie.year && !collection.years.includes(movie.year)) {
        collection.years.push(movie.year)
        collection.years.sort((a, b) => a - b)
      }
      
      // Add genres from trakt data
      if (movie.trakt?.genres) {
        for (const genre of movie.trakt.genres) {
          if (!collection.genres.includes(genre)) {
            collection.genres.push(genre)
          }
        }
      }
    }
    
    // Calculate total movies for each collection
    // Sort movies by year (ascending)
    let allCollections = Array.from(collectionsMap.values()).map(collection => {
      collection.movies.sort((a, b) => (a.year || 0) - (b.year || 0))
      collection.total_movies = collection.movies.length
      return collection
    })
    
    // Apply search filter if provided
    if (searchQuery) {
      allCollections = allCollections.filter(collection => {
        const franchiseNameMatch = collection.franchise_name.toLowerCase().includes(searchQuery)
        // Also search within movie titles in the collection
        const movieTitleMatch = collection.movies.some(movie => 
          movie.title.toLowerCase().includes(searchQuery) ||
          movie.title_original.toLowerCase().includes(searchQuery)
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
        total_movies: movies.length
      }
    }
  } catch (error: any) {
    console.error('Error reading collections:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to load collections',
      data: { error: error.message }
    })
  }
})

