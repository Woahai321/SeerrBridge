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
    collections: Collection[]
    pagination: PaginationInfo
    total_collections: number
    total_movies: number
  }
}

interface CollectionResponse {
  success: boolean
  data: {
    collection: Collection
    pagination: PaginationInfo
  }
}

export const useCollections = () => {
  const getCollections = async (page: number = 1, limit: number = 20, search: string = ''): Promise<{
    collections: Collection[]
    pagination: PaginationInfo
    total_collections: number
    total_movies: number
  } | null> => {
    try {
      const params = new URLSearchParams({
        page: String(page),
        limit: String(limit)
      })
      
      console.log('getCollections called - search param:', search)
      if (search && search.trim()) {
        params.append('search', search.trim())
        console.log('Added search param to URL:', search.trim())
      }
      
      const url = `/api/collections?${params.toString()}`
      console.log('Fetching from URL:', url)
      
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
      console.error('Error fetching collections:', error)
      return null
    }
  }
  
  const getCollection = async (franchiseName: string, page: number = 1, limit: number = 30, search: string = ''): Promise<{
    collection: Collection
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
      
      const response = await $fetch<CollectionResponse>(`/api/collections/${encodedName}?${params.toString()}`, {
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
      console.error('Error fetching collection:', error)
      return null
    }
  }
  
  const getImageUrl = (imagePath: string | undefined): string | null => {
    if (!imagePath) return null
    
    // Remove leading slash if present
    const cleanPath = imagePath.startsWith('/') ? imagePath.slice(1) : imagePath
    
    // Use query parameter to avoid Vue Router issues with nested paths
    return `/api/collection-image?path=${encodeURIComponent(cleanPath)}`
  }
  
  const getPosterUrl = (movie: Movie): string | null => {
    if (movie.local_images?.poster) {
      return getImageUrl(movie.local_images.poster)
    }
    return null
  }
  
  const getFanartUrl = (movie: Movie): string | null => {
    if (movie.local_images?.fanart) {
      return getImageUrl(movie.local_images.fanart)
    }
    return null
  }
  
  const getLogoUrl = (movie: Movie): string | null => {
    if (movie.local_images?.logo) {
      return getImageUrl(movie.local_images.logo)
    }
    return null
  }

  const getClearartUrl = (movie: Movie): string | null => {
    if (movie.local_images?.clearart) {
      return getImageUrl(movie.local_images.clearart)
    }
    return null
  }

  const getBannerUrl = (movie: Movie): string | null => {
    if (movie.local_images?.banner) {
      return getImageUrl(movie.local_images.banner)
    }
    return null
  }
  
  const getBulkCollectionMetadata = async (franchiseNames: string[]): Promise<CollectionMetadata[] | null> => {
    if (!franchiseNames.length || franchiseNames.length > 100) {
      console.error('getBulkCollectionMetadata: must provide 1-100 franchise names')
      return null
    }
    
    try {
      // Encode franchise names and join with comma
      const encodedNames = franchiseNames.map(name => encodeURIComponent(name)).join(',')
      
      const response = await $fetch<{
        success: boolean
        data: {
          collections: CollectionMetadata[]
        }
      }>(`/api/collections/bulk-metadata?names=${encodedNames}`, {
        method: 'GET'
      })
      
      if (response.success) {
        return response.data.collections
      }
      
      return null
    } catch (error) {
      console.error('Error fetching bulk collection metadata:', error)
      return null
    }
  }

  // Get all movies in a collection (without pagination)
  const getAllMoviesInCollection = async (franchiseName: string): Promise<Movie[] | null> => {
    try {
      const encodedName = encodeURIComponent(franchiseName)
      // Request a very large limit to get all movies
      const response = await $fetch<CollectionResponse>(`/api/collections/${encodedName}?page=1&limit=10000`, {
        method: 'GET'
      })
      
      if (response.success && response.data.collection) {
        return response.data.collection.movies || []
      }
      
      return null
    } catch (error) {
      console.error('Error fetching all movies in collection:', error)
      return null
    }
  }

  return {
    getCollections,
    getCollection,
    getBulkCollectionMetadata,
    getAllMoviesInCollection,
    getImageUrl,
    getPosterUrl,
    getFanartUrl,
    getLogoUrl,
    getClearartUrl,
    getBannerUrl
  }
}

