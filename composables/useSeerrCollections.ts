interface SeerrMovie {
  id: number // TMDB ID
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

interface PaginationInfo {
  page: number
  limit: number
  total: number
  total_pages: number
  has_next: boolean
  has_prev: boolean
}

interface CollectionMetadata {
  franchise_name: string
  franchise_url?: string
  total_movies: number
  years: number[]
}

interface CollectionsResponse {
  success: boolean
  data: {
    collections: SeerrCollection[]
    pagination: PaginationInfo
    total_collections: number
    total_movies: number
  }
}

interface CollectionResponse {
  success: boolean
  data: {
    collection: SeerrCollection
    pagination: PaginationInfo
  }
}

export const useSeerrCollections = () => {
  /**
   * Construct TMDB image URL from poster path
   */
  const constructTmdbImageUrl = (posterPath: string | null | undefined): string | null => {
    if (!posterPath) return null
    
    // If it's already a full URL, return it as-is
    if (posterPath.startsWith('http')) {
      return posterPath
    }
    
    // Construct TMDB URL - ensure leading slash
    const cleanPath = posterPath.startsWith('/') ? posterPath : `/${posterPath}`
    return `https://image.tmdb.org/t/p/w500${cleanPath}`
  }

  /**
   * Get poster URL for a Seerr movie
   * Seerr collections already have poster_path ready to use
   */
  const getSeerrPosterUrl = (movie: SeerrMovie): string | null => {
    return constructTmdbImageUrl(movie.poster_path)
  }

  const getCollections = async (page: number = 1, limit: number = 20, search: string = ''): Promise<{
    collections: SeerrCollection[]
    pagination: PaginationInfo
    total_collections: number
    total_movies: number
  } | null> => {
    try {
      const params = new URLSearchParams({
        page: String(page),
        limit: String(limit)
      })
      
      if (search && search.trim()) {
        params.append('search', search.trim())
      }
      
      const url = `/api/seerr-collections?${params.toString()}`
      
      const response = await $fetch<CollectionsResponse>(url, {
        method: 'GET'
      })
      
      if (response.success) {
        return {
          collections: response.data.collections,
          pagination: response.data.pagination,
          total_collections: response.data.total_collections,
          total_movies: response.data.total_movies
        }
      }
      
      return null
    } catch (error) {
      console.error('Error fetching Seerr collections:', error)
      return null
    }
  }
  
  const getCollection = async (franchiseName: string, page: number = 1, limit: number = 30, search: string = ''): Promise<{
    collection: SeerrCollection
    pagination: PaginationInfo
  } | null> => {
    try {
      const encodedName = encodeURIComponent(franchiseName)
      const params = new URLSearchParams({
        page: String(page),
        limit: String(limit)
      })
      
      if (search) {
        params.append('search', search)
      }
      
      const response = await $fetch<CollectionResponse>(`/api/seerr-collections/${encodedName}?${params.toString()}`, {
        method: 'GET'
      })
      
      if (response.success) {
        return {
          collection: response.data.collection,
          pagination: response.data.pagination
        }
      }
      
      return null
    } catch (error) {
      console.error('Error fetching Seerr collection:', error)
      return null
    }
  }
  
  const getBulkCollectionMetadata = async (franchiseNames: string[]): Promise<CollectionMetadata[] | null> => {
    if (!franchiseNames.length || franchiseNames.length > 100) {
      console.error('getBulkCollectionMetadata: must provide 1-100 franchise names')
      return null
    }
    
    try {
      // Fetch all collections and filter
      const allCollections = await getCollections(1, 1000, '')
      if (!allCollections) return null
      
      const metadata: CollectionMetadata[] = []
      for (const name of franchiseNames) {
        const collection = allCollections.collections.find(c => c.franchise_name === name)
        if (collection) {
          metadata.push({
            franchise_name: collection.franchise_name,
            franchise_url: collection.franchise_url,
            total_movies: collection.total_movies,
            years: collection.years
          })
        }
      }
      
      return metadata
    } catch (error) {
      console.error('Error fetching bulk Seerr collection metadata:', error)
      return null
    }
  }

  // Get all movies in a collection (without pagination)
  const getAllMoviesInCollection = async (franchiseName: string): Promise<SeerrMovie[] | null> => {
    try {
      const encodedName = encodeURIComponent(franchiseName)
      // Request a very large limit to get all movies
      const response = await $fetch<CollectionResponse>(`/api/seerr-collections/${encodedName}?page=1&limit=10000`, {
        method: 'GET'
      })
      
      if (response.success && response.data.collection) {
        return response.data.collection.movies || []
      }
      
      return null
    } catch (error) {
      console.error('Error fetching all movies in Seerr collection:', error)
      return null
    }
  }

  return {
    getCollections,
    getCollection,
    getBulkCollectionMetadata,
    getAllMoviesInCollection,
    getSeerrPosterUrl
  }
}

