interface MediaResult {
  id: number
  mediaType: 'movie' | 'tv' | 'person'
  popularity?: number
  posterPath?: string | null
  backdropPath?: string | null
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
  profilePath?: string | null
  knownFor?: MediaResult[]
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
  success: boolean
  data?: {
    page: number
    totalPages: number
    totalResults: number
    results: MediaResult[]
  }
  error?: string
  details?: string
}

export const useSearch = () => {
  const query = ref('')
  const results = ref<MediaResult[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const page = ref(1)
  const totalPages = ref(1)
  const totalResults = ref(0)
  const language = ref('en')
  
  const searchMedia = async (searchQuery?: string) => {
    const queryToUse = searchQuery || query.value
    if (!queryToUse.trim()) {
      results.value = []
      return
    }
    
    loading.value = true
    error.value = null
    
    try {
      const response = await $fetch<SearchResponse>('/api/overseerr-search', {
        query: {
          query: queryToUse,
          page: page.value,
          language: language.value
        }
      })
      
      if (response.success && response.data) {
        results.value = response.data.results
        totalPages.value = response.data.totalPages
        totalResults.value = response.data.totalResults
        console.log('Search success:', { results: results.value.length, totalPages: totalPages.value, totalResults: totalResults.value })
      } else {
        error.value = response.error || 'Search failed'
        results.value = []
      }
    } catch (err) {
      console.error('Search error:', err)
      error.value = err instanceof Error ? err.message : 'Failed to search'
      results.value = []
    } finally {
      loading.value = false
    }
  }
  
  const resetSearch = () => {
    query.value = ''
    results.value = []
    page.value = 1
    error.value = null
  }
  
  const nextPage = () => {
    if (page.value < totalPages.value) {
      page.value++
      searchMedia(query.value)
    }
  }
  
  const previousPage = () => {
    if (page.value > 1) {
      page.value--
      searchMedia(query.value)
    }
  }
  
  const goToPage = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages.value) {
      page.value = newPage
      searchMedia(query.value)
    }
  }
  
  const getPosterUrl = (posterPath: string | null | undefined): string => {
    if (!posterPath) return ''
    return `https://image.tmdb.org/t/p/w500${posterPath}`
  }
  
  const getBackdropUrl = (backdropPath: string | null | undefined): string => {
    if (!backdropPath) return ''
    return `https://image.tmdb.org/t/p/w1280${backdropPath}`
  }
  
  const getMediaTitle = (media: MediaResult): string => {
    if (media.mediaType === 'movie') {
      return media.title || media.originalTitle || 'Unknown Movie'
    } else if (media.mediaType === 'tv') {
      return media.name || media.originalName || 'Unknown Show'
    } else if (media.mediaType === 'person') {
      return 'Person'
    }
    return 'Unknown'
  }
  
  const getMediaYear = (media: MediaResult): string => {
    if (media.mediaType === 'movie' && media.releaseDate) {
      const year = media.releaseDate.split('-')[0]
      return year || ''
    } else if (media.mediaType === 'tv' && media.firstAirDate) {
      const year = media.firstAirDate.split('-')[0]
      return year || ''
    }
    return ''
  }
  
  const getMediaTypeLabel = (media: MediaResult): string => {
    if (media.mediaType === 'movie') return 'Movie'
    if (media.mediaType === 'tv') return 'TV Show'
    if (media.mediaType === 'person') return 'Person'
    return 'Unknown'
  }
  
  const formatVoteAverage = (voteAverage?: number): string => {
    if (!voteAverage) return 'N/A'
    return voteAverage.toFixed(1)
  }
  
  const hasRequests = (media: MediaResult): boolean => {
    return !!(media.mediaInfo?.requests && media.mediaInfo.requests.length > 0)
  }
  
  const getRequestStatus = (media: MediaResult): string | null => {
    if (!media.mediaInfo?.requests || media.mediaInfo.requests.length === 0) {
      return null
    }
    
    const status = media.mediaInfo.requests[0].status
    // Status codes: 0 = pending, 1 = approved, 2 = declined, 3 = available
    const statusLabels: Record<number, string> = {
      0: 'Pending Approval',
      1: 'Approved',
      2: 'Declined',
      3: 'Available'
    }
    
    return statusLabels[status] || 'Unknown'
  }
  
  return {
    query,
    results,
    loading,
    error,
    page,
    totalPages,
    totalResults,
    language,
    searchMedia,
    resetSearch,
    nextPage,
    previousPage,
    goToPage,
    getPosterUrl,
    getBackdropUrl,
    getMediaTitle,
    getMediaYear,
    getMediaTypeLabel,
    formatVoteAverage,
    hasRequests,
    getRequestStatus
  }
}

