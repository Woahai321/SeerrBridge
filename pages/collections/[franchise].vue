<template>
  <div class="space-y-8">
    <!-- Header -->
    <div v-if="collection" class="space-y-4">
      <div class="flex items-start justify-between gap-4">
        <div class="flex-1">
          <Button 
            @click="router.back()"
            variant="ghost"
            size="sm"
            class="mb-4"
          >
            <AppIcon icon="lucide:arrow-left" size="16" class="mr-2" />
            Back to Collections
          </Button>
          
          <h1 class="text-4xl font-bold text-foreground mb-2">
            {{ collection.franchise_name }}
          </h1>
          
          <div class="flex flex-wrap items-center gap-4 text-muted-foreground">
            <span class="flex items-center gap-1">
              <AppIcon icon="lucide:film" size="16" />
              <span v-if="pagination">
                Showing {{ (pagination.page - 1) * pagination.limit + 1 }} - {{ Math.min(pagination.page * pagination.limit, pagination.total) }} of {{ pagination.total }} {{ pagination.total === 1 ? 'movie' : 'movies' }}
              </span>
              <span v-else>
                {{ collection.total_movies }} {{ collection.total_movies === 1 ? 'movie' : 'movies' }}
              </span>
            </span>
            <span v-if="collection.years.length > 0" class="flex items-center gap-1">
              <AppIcon icon="lucide:calendar" size="16" />
              {{ collection.years[0] }} - {{ collection.years[collection.years.length - 1] }}
            </span>
            <div v-if="collection.genres.length > 0" class="flex items-center gap-2">
              <AppIcon icon="lucide:tag" size="16" />
              <div class="flex gap-1 flex-wrap">
                <span
                  v-for="genre in collection.genres"
                  :key="genre"
                  class="px-2 py-0.5 bg-muted rounded-md text-xs capitalize"
                >
                  {{ genre.replace('-', ' ') }}
                </span>
              </div>
            </div>
          </div>
          
          <div class="flex items-center gap-3 mt-4">
            <Button
              @click="handleRequestCollection"
              :disabled="requestingCollection || (requestableMovieCount !== null && requestableMovieCount === 0)"
              size="lg"
              class="bg-primary text-primary-foreground hover:bg-primary/90"
            >
              <AppIcon 
                v-if="requestingCollection"
                icon="lucide:loader-2" 
                size="18" 
                class="mr-2 animate-spin"
              />
              <AppIcon 
                v-else
                icon="lucide:plus-circle" 
                size="18" 
                class="mr-2"
              />
              <span v-if="requestingCollection">
                {{ getCollectionProgressText() }}
              </span>
              <span v-else>
                {{ getRequestableCountText }}
              </span>
            </Button>
            
            <a
              v-if="collection.franchise_url"
              :href="collection.franchise_url"
              target="_blank"
              rel="noopener noreferrer"
              class="inline-flex items-center gap-2 text-sm text-primary hover:underline"
            >
              <AppIcon icon="lucide:external-link" size="14" />
              View on Source
            </a>
          </div>
        </div>
      </div>
      
      <!-- Search Box -->
      <div class="relative">
        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <AppIcon icon="lucide:search" size="20" class="text-muted-foreground" />
        </div>
        <Input
          v-model="searchQuery"
          type="text"
          placeholder="Search movies by title..."
          class="pl-10 pr-10"
        />
        <div v-if="searchQuery" class="absolute inset-y-0 right-0 pr-3 flex items-center">
          <Button
            @click="clearSearch"
            variant="ghost"
            size="sm"
            class="h-6 w-6 p-0 hover:bg-muted"
          >
            <AppIcon icon="lucide:x" size="16" class="text-muted-foreground" />
          </Button>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="flex items-center justify-center py-24">
      <div class="text-center">
        <AppIcon 
          icon="lucide:loader-2" 
          size="48" 
          class="mx-auto text-primary animate-spin mb-4"
        />
        <p class="text-muted-foreground">Loading collection...</p>
      </div>
    </div>

    <!-- Movies Grid -->
    <div v-else-if="collection && collection.movies.length > 0" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-7 gap-4">
      <div
        v-for="(movie, index) in collection.movies"
        :key="`${movie.title}-${movie.year}-${index}`"
        @click="openMovieModal(movie)"
        class="group relative bg-card rounded-xl overflow-hidden cursor-pointer transition-all duration-300 hover:shadow-xl hover:-translate-y-1 border border-border"
      >
        <!-- Movie Poster -->
        <div class="relative aspect-[2/3] bg-gradient-to-br from-muted to-muted/50 overflow-hidden">
          <img
            v-if="getPosterUrl(movie)"
            :src="getPosterUrl(movie)"
            :alt="movie.title"
            class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
            @error="handleImageError"
          />
          <div v-else class="w-full h-full flex flex-col items-center justify-center p-4">
            <div class="w-16 h-16 rounded-lg bg-muted flex items-center justify-center mb-3">
              <AppIcon icon="lucide:film" size="32" class="text-muted-foreground" />
            </div>
            <p class="text-xs text-muted-foreground text-center line-clamp-2 font-medium">
              {{ movie.title }}
            </p>
          </div>
          
          <!-- Year Badge -->
          <div class="absolute top-2 left-2">
            <div class="bg-black/60 backdrop-blur-sm text-white px-2 py-0.5 rounded-md text-xs font-semibold">
              {{ movie.year }}
            </div>
          </div>
          
          <!-- Rating Badge -->
          <div v-if="movie.trakt?.rating" class="absolute top-2 right-2">
            <div class="bg-primary/90 backdrop-blur-sm text-primary-foreground px-2 py-0.5 rounded-md text-xs font-semibold flex items-center gap-1">
              <AppIcon icon="lucide:star" size="12" class="fill-current" />
              {{ movie.trakt.rating.toFixed(1) }}
            </div>
          </div>
          
          <!-- Hover Overlay -->
          <div class="absolute inset-0 bg-gradient-to-t from-black/90 via-black/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-end">
            <div class="p-3 w-full">
              <h3 class="text-white font-bold text-sm mb-1 line-clamp-2">
                {{ movie.title }}
              </h3>
              <p v-if="movie.trakt?.overview" class="text-white/90 text-xs line-clamp-2 mb-2">
                {{ movie.trakt.overview }}
              </p>
              <!-- Availability Badge -->
              <div v-if="isMovieAvailableInOverseerr(movie)" class="mb-2">
                <div class="w-full bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 px-3 py-1.5 rounded-md text-xs font-semibold flex items-center justify-center gap-1.5">
                  <AppIcon icon="lucide:check-circle-2" size="12" />
                  Available in Overseerr
                </div>
              </div>
              <div v-else-if="isMovieRequestedInOverseerr(movie)" class="mb-2">
                <div class="w-full bg-amber-500/20 border border-amber-500/30 text-amber-400 px-3 py-1.5 rounded-md text-xs font-semibold flex items-center justify-center gap-1.5">
                  <AppIcon icon="lucide:clock" size="12" />
                  Already Requested
                </div>
              </div>
              
              <!-- Request Button -->
              <Button
                v-if="!isMovieInDatabase(movie) && !isMovieRequested(movie) && !isMovieAvailableInOverseerr(movie) && !isMovieRequestedInOverseerr(movie)"
                @click.stop="handleRequest(movie)"
                :disabled="requestingMovies.has(getMovieId(movie))"
                size="sm"
                class="w-full"
              >
                <AppIcon 
                  v-if="requestingMovies.has(getMovieId(movie))"
                  icon="lucide:loader-2" 
                  size="14" 
                  class="mr-2 animate-spin"
                />
                <AppIcon 
                  v-else
                  icon="lucide:plus" 
                  size="14" 
                  class="mr-2"
                />
                {{ requestingMovies.has(getMovieId(movie)) ? 'Requesting...' : 'Request' }}
              </Button>
              <Button
                v-else-if="isMovieInDatabase(movie) && movieDatabaseIds.has(getMovieId(movie))"
                @click.stop="viewMovieInDatabase(movie)"
                size="sm"
                variant="outline"
                class="w-full bg-primary/20 border-primary/30 text-primary hover:bg-primary/30"
              >
                <AppIcon icon="lucide:external-link" size="14" class="mr-2" />
                View Item
              </Button>
              <Button
                v-else-if="isMovieAvailableInOverseerr(movie)"
                @click.stop
                size="sm"
                variant="outline"
                class="w-full bg-emerald-500/20 border-emerald-500/30 text-emerald-400"
                disabled
              >
                <AppIcon icon="lucide:check-circle-2" size="14" class="mr-2" />
                Available
              </Button>
              <Button
                v-else-if="isMovieRequestedInOverseerr(movie)"
                @click.stop
                size="sm"
                variant="outline"
                class="w-full bg-amber-500/20 border-amber-500/30 text-amber-400"
                disabled
              >
                <AppIcon icon="lucide:clock" size="14" class="mr-2" />
                Already Requested
              </Button>
              <Button
                v-else-if="isMovieRequested(movie) && !isMovieInDatabase(movie)"
                @click.stop
                size="sm"
                variant="outline"
                class="w-full bg-amber-500/20 border-amber-500/30 text-amber-400"
                disabled
              >
                <AppIcon icon="lucide:check-circle" size="14" class="mr-2" />
                Already Requested
              </Button>
            </div>
          </div>
        </div>
        
        <!-- Movie Info -->
        <div class="p-3 bg-card">
          <h3 class="font-semibold text-sm text-foreground line-clamp-1 mb-1">
            {{ movie.title }}
          </h3>
          <div class="flex items-center justify-between text-xs text-muted-foreground">
            <span>{{ movie.year }}</span>
            <span v-if="movie.trakt?.runtime" class="flex items-center gap-1">
              <AppIcon icon="lucide:clock" size="12" />
              {{ movie.trakt.runtime }}m
            </span>
          </div>
          <div v-if="movie.trakt?.genres && movie.trakt.genres.length > 0" class="mt-2 flex gap-1 flex-wrap">
            <span
              v-for="genre in movie.trakt.genres.slice(0, 2)"
              :key="genre"
              class="px-1.5 py-0.5 bg-muted rounded text-xs capitalize"
            >
              {{ genre.replace('-', ' ') }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else-if="!loading" class="flex flex-col items-center justify-center py-24 text-center">
      <div class="w-24 h-24 rounded-full bg-muted flex items-center justify-center mb-6">
        <AppIcon icon="lucide:film-x" size="48" class="text-muted-foreground" />
      </div>
      <h3 class="text-xl font-semibold text-foreground mb-2">Collection not found</h3>
      <p class="text-muted-foreground max-w-md mb-4">
        The collection you're looking for doesn't exist or has no movies.
      </p>
      <Button @click="router.push('/collections')" variant="outline">
        <AppIcon icon="lucide:arrow-left" size="16" class="mr-2" />
        Back to Collections
      </Button>
    </div>

    <!-- Pagination Controls -->
    <div v-if="pagination && pagination.total_pages > 1" class="flex items-center justify-center gap-2 pt-4">
      <Button
        @click="goToPage(pagination.page - 1)"
        :disabled="!pagination.has_prev || loading"
        variant="outline"
        size="sm"
      >
        <AppIcon icon="lucide:chevron-left" size="16" class="mr-1" />
        Previous
      </Button>
      
      <div class="flex items-center gap-1">
        <Button
          v-for="pageNum in visiblePages"
          :key="pageNum"
          @click="goToPage(pageNum)"
          :disabled="loading"
          :variant="pageNum === pagination.page ? 'default' : 'outline'"
          size="sm"
          class="min-w-[40px]"
        >
          {{ pageNum }}
        </Button>
      </div>
      
      <Button
        @click="goToPage(pagination.page + 1)"
        :disabled="!pagination.has_next || loading"
        variant="outline"
        size="sm"
      >
        Next
        <AppIcon icon="lucide:chevron-right" size="16" class="ml-1" />
      </Button>
    </div>
    
    <!-- Movie Details Modal -->
    <MovieDetailsModal
      :movie="selectedMovie"
      :is-open="showMovieModal"
      @close="closeMovieModal"
    />
  </div>
</template>

<script setup lang="ts">
import Button from '~/components/ui/Button.vue'
import Input from '~/components/ui/Input.vue'
import MovieDetailsModal from '~/components/MovieDetailsModal.vue'

interface Movie {
  title: string
  title_original: string
  year: number
  release_date?: string
  local_images?: {
    poster?: string
    fanart?: string
    logo?: string
    clearart?: string
    banner?: string
  }
  trakt?: {
    trakt_id: number
    title: string
    year: number
    ids?: {
      trakt?: number
      slug?: string
      imdb?: string
      tmdb?: number
    }
    rating?: number
    votes?: number
    genres?: string[]
    runtime?: number
    overview?: string
  }
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

const route = useRoute()
const router = useRouter()
const { getCollection, getAllMoviesInCollection, getPosterUrl } = useCollections()
const { toast } = useToast()

const collection = ref<Collection | null>(null)
const pagination = ref<PaginationInfo | null>(null)
const loading = ref(false)
const currentPage = ref(1)
const itemsPerPage = ref(30)
const searchQuery = ref('')
const showMovieModal = ref(false)
const selectedMovie = ref<Movie | null>(null)

// Track movies in database and requested movies
const moviesInDatabase = ref<Set<string>>(new Set())
const movieDatabaseIds = ref<Map<string, number>>(new Map())
const requestedMovies = ref<Set<string>>(new Set())
const requestingMovies = ref<Set<string>>(new Set())
const checkingMoviesInDatabase = ref(false)

// Track Overseerr availability status
const moviesAvailableInOverseerr = ref<Set<string>>(new Set())
// Track movies that are requested (status 2 or 3) vs available (status 1 or 5)
const moviesRequestedInOverseerr = ref<Set<string>>(new Set())
const checkingOverseerrStatus = ref(false)

// Track collection request
const requestingCollection = ref(false)
const collectionRequestProgress = ref<{ current: number, total: number } | null>(null)

// Track count of requestable movies
const requestableMovieCount = ref<number | null>(null)
const calculatingRequestableCount = ref(false)

const franchiseName = computed(() => {
  return decodeURIComponent((route.params.franchise as string) || '')
})

// Calculate how many movies can actually be requested
const calculateRequestableCount = async () => {
  if (!collection.value || calculatingRequestableCount.value) return
  
  calculatingRequestableCount.value = true
  
  try {
    // Fetch all movies in the collection
    const allMovies = await getAllMoviesInCollection(collection.value.franchise_name)
    
    if (!allMovies || allMovies.length === 0) {
      requestableMovieCount.value = 0
      return
    }
    
    // Always check Overseerr status for ALL movies in the collection
    // (The Sets might only contain paginated movies, so we need to check everything)
    // Force a full check even if one is in progress
    if (allMovies.some(m => m.trakt?.ids?.tmdb)) {
      await checkOverseerrStatus(allMovies, true)
    }
    
    // Filter movies that can be requested
    const count = allMovies.filter(movie => {
      if (!movie.trakt?.ids?.tmdb) return false
      const movieId = getMovieId(movie)
      // Exclude if in database, available, or already requested in Overseerr
      return !moviesInDatabase.value.has(movieId) 
        && !moviesAvailableInOverseerr.value.has(movieId)
        && !moviesRequestedInOverseerr.value.has(movieId)
    }).length
    
    requestableMovieCount.value = count
  } catch (error) {
    console.error('Error calculating requestable count:', error)
    requestableMovieCount.value = null
  } finally {
    calculatingRequestableCount.value = false
  }
}

const visiblePages = computed(() => {
  if (!pagination.value) return []
  
  const total = pagination.value.total_pages
  const current = pagination.value.page
  const pages: number[] = []
  
  // Show max 7 pages around current page
  let start = Math.max(1, current - 3)
  let end = Math.min(total, current + 3)
  
  // Adjust if near boundaries
  if (end - start < 6) {
    if (start === 1) {
      end = Math.min(total, 7)
    } else if (end === total) {
      start = Math.max(1, total - 6)
    }
  }
  
  for (let i = start; i <= end; i++) {
    pages.push(i)
  }
  
  return pages
})

const handleImageError = (event: Event) => {
  const img = event.target as HTMLImageElement
  img.style.display = 'none'
}

const openMovieModal = (movie: Movie) => {
  selectedMovie.value = movie
  showMovieModal.value = true
}

const closeMovieModal = () => {
  showMovieModal.value = false
  selectedMovie.value = null
}

// Get unique ID for movie (using TMDB ID or IMDB ID)
const getMovieId = (movie: Movie): string => {
  if (movie.trakt?.ids?.tmdb) {
    return `tmdb_${movie.trakt.ids.tmdb}`
  }
  if (movie.trakt?.ids?.imdb) {
    return `imdb_${movie.trakt.ids.imdb}`
  }
  return `${movie.title}-${movie.year}`
}

// Check if movie is in database
const checkMoviesInDatabase = async (movies: Movie[]) => {
  if (checkingMoviesInDatabase.value) return
  
  checkingMoviesInDatabase.value = true
  
  try {
    // Check each movie in parallel
    const checks = movies
      .filter(movie => movie.trakt?.ids?.tmdb || movie.trakt?.ids?.imdb)
      .map(async (movie) => {
        try {
          const params = new URLSearchParams()
          if (movie.trakt?.ids?.imdb) {
            params.append('imdb_id', movie.trakt.ids.imdb)
          } else if (movie.trakt?.ids?.tmdb) {
            params.append('tmdb_id', String(movie.trakt.ids.tmdb))
          } else {
            return
          }
          
          const response = await $fetch<{
            success: boolean
            data: {
              exists: boolean
              databaseId?: number | null
            }
          }>(`/api/movie-exists?${params.toString()}`)
          
          if (response.success && response.data.exists) {
            const movieId = getMovieId(movie)
            moviesInDatabase.value.add(movieId)
            if (response.data.databaseId) {
              movieDatabaseIds.value.set(movieId, response.data.databaseId)
            }
          }
        } catch (error) {
          console.error('Error checking if movie exists:', error)
        }
      })
    
    await Promise.all(checks)
  } finally {
    checkingMoviesInDatabase.value = false
  }
}

// Check Overseerr availability status for movies
const checkOverseerrStatus = async (movies: Movie[], force: boolean = false) => {
  if (!force && checkingOverseerrStatus.value) {
    // Wait for current check to complete
    while (checkingOverseerrStatus.value) {
      await new Promise(resolve => setTimeout(resolve, 100))
    }
    return
  }
  
  checkingOverseerrStatus.value = true
  
  try {
    // Check each movie in batches to avoid overwhelming the system
    const moviesToCheck = movies.filter(movie => movie.trakt?.ids?.tmdb)
    
    // Process in batches of 5
    const BATCH_SIZE = 5
    for (let i = 0; i < moviesToCheck.length; i += BATCH_SIZE) {
      const batch = moviesToCheck.slice(i, i + BATCH_SIZE)
      const batchChecks = batch.map(async (movie) => {
        try {
          const response = await $fetch<{
            success: boolean
            data?: {
              status: number | null
              available: boolean
              requested?: boolean
            }
            error?: string
          }>(`/api/overseerr-movie-status?tmdb_id=${movie.trakt!.ids!.tmdb}`, {
            timeout: 10000 // 10 second timeout per request
          })
          
          // Mark as available or requested (status 2 or 3 means already requested)
          if (response.success && response.data) {
            const movieId = getMovieId(movie)
            if (response.data.available) {
              // Status 1 or 5 - fully available
              moviesAvailableInOverseerr.value.add(movieId)
              moviesRequestedInOverseerr.value.delete(movieId) // Remove if it was previously requested
            } else if (response.data.requested) {
              // Status 2 or 3 - already requested but not fully available
              moviesRequestedInOverseerr.value.add(movieId)
              moviesAvailableInOverseerr.value.delete(movieId) // Don't mark as available
            }
          }
        } catch (error) {
          // Silently handle errors - treat as not available
        }
      })
      
      await Promise.all(batchChecks)
      
      // Small delay between batches
      if (i + BATCH_SIZE < moviesToCheck.length) {
        await new Promise(resolve => setTimeout(resolve, 100))
      }
    }
  } finally {
    checkingOverseerrStatus.value = false
  }
}

// Check if movie is available in Overseerr (status 1 or 5)
const isMovieAvailableInOverseerr = (movie: Movie): boolean => {
  return moviesAvailableInOverseerr.value.has(getMovieId(movie))
}

// Check if movie is already requested in Overseerr (status 2 or 3)
const isMovieRequestedInOverseerr = (movie: Movie): boolean => {
  return moviesRequestedInOverseerr.value.has(getMovieId(movie))
}

// Check if movie is in database
const isMovieInDatabase = (movie: Movie): boolean => {
  return moviesInDatabase.value.has(getMovieId(movie))
}

// Check if movie has been requested
const isMovieRequested = (movie: Movie): boolean => {
  return requestedMovies.value.has(getMovieId(movie))
}

// View movie in database
const viewMovieInDatabase = (movie: Movie) => {
  const movieId = getMovieId(movie)
  const databaseId = movieDatabaseIds.value.get(movieId)
  if (databaseId) {
    navigateTo(`/processed-media?mediaId=${databaseId}`)
  }
}

// Handle request
const handleRequest = async (movie: Movie) => {
  if (!movie.trakt?.ids?.tmdb) {
    toast.error('Movie does not have a TMDB ID', 'Cannot Request')
    return
  }
  
  const movieId = getMovieId(movie)
  requestingMovies.value.add(movieId)
  
  try {
    const response = await $fetch('/api/overseerr-request', {
      method: 'POST',
      body: {
        mediaId: movie.trakt.ids.tmdb,
        mediaType: 'movie',
        is4k: false
      }
    })
    
    if (response.success) {
      // Mark as requested
      requestedMovies.value.add(movieId)
      
      // Also mark as in database since it will be added
      moviesInDatabase.value.add(movieId)
      
      toast.success(
        `"${movie.title}" request submitted successfully`,
        'Request Submitted'
      )
    } else {
      toast.error(
        response.error || 'Failed to submit request',
        'Request Failed'
      )
    }
  } catch (error) {
    console.error('Error creating request:', error)
    toast.error(
      error instanceof Error ? error.message : 'Failed to submit request',
      'Request Error'
    )
  } finally {
    requestingMovies.value.delete(movieId)
  }
}

// Watch for collection changes to check movies in database and Overseerr status
watch(() => collection.value?.movies, (movies) => {
  if (movies && movies.length > 0) {
    checkMoviesInDatabase(movies)
    checkOverseerrStatus(movies)
  }
}, { immediate: true })

// Watch for collection changes to calculate requestable count
watch(() => collection.value, async (newCollection) => {
  if (newCollection) {
    // Wait a bit for status checks to complete, then calculate count
    setTimeout(() => {
      calculateRequestableCount()
    }, 1000)
  } else {
    requestableMovieCount.value = null
  }
}, { immediate: true })

// Recalculate when Overseerr status or database status changes
watch([moviesAvailableInOverseerr, moviesRequestedInOverseerr, moviesInDatabase], () => {
  if (collection.value) {
    calculateRequestableCount()
  }
})

// Get progress text for collection request
const getCollectionProgressText = (): string => {
  if (collectionRequestProgress.value) {
    return `Requesting ${collectionRequestProgress.value.current}/${collectionRequestProgress.value.total}`
  }
  return 'Requesting...'
}

// Get requestable count text
const getRequestableCountText = computed(() => {
  if (requestableMovieCount.value === null) {
    return calculatingRequestableCount.value ? 'Calculating...' : 'Request Entire Collection'
  }
  if (requestableMovieCount.value === 0) {
    return 'All Movies Available'
  }
  return `Request Entire Collection (${requestableMovieCount.value})`
})

// Request entire collection
const handleRequestCollection = async () => {
  if (!collection.value || requestingCollection.value) {
    return
  }
  
  requestingCollection.value = true
  
  try {
    // Fetch all movies in the collection
    const allMovies = await getAllMoviesInCollection(collection.value.franchise_name)
    
    if (!allMovies || allMovies.length === 0) {
      toast.error('No movies found in collection', 'Request Failed')
      requestingCollection.value = false
      return
    }
    
    // Check Overseerr status for all movies first
    await checkOverseerrStatus(allMovies)
    
    // Filter movies that have TMDB IDs and are not already available or requested in Overseerr
    const moviesToRequest = allMovies.filter(movie => {
      if (!movie.trakt?.ids?.tmdb) return false
      const movieId = getMovieId(movie)
      // Exclude if available or already requested
      return !moviesAvailableInOverseerr.value.has(movieId) && !moviesRequestedInOverseerr.value.has(movieId)
    })
    
    if (moviesToRequest.length === 0) {
      const availableCount = moviesAvailableInOverseerr.value.size
      const requestedCount = moviesRequestedInOverseerr.value.size
      const totalCount = availableCount + requestedCount
      
      if (totalCount > 0) {
        // Some or all movies are already available or requested
        const message = availableCount > 0 && requestedCount === 0
          ? `All ${totalCount} ${totalCount === 1 ? 'movie is' : 'movies are'} already available in Overseerr`
          : requestedCount > 0 && availableCount === 0
          ? `All ${totalCount} ${totalCount === 1 ? 'movie has' : 'movies have'} been requested in Overseerr`
          : `All ${totalCount} ${totalCount === 1 ? 'movie is' : 'movies are'} already available or requested in Overseerr`
        toast.info(message, 'Collection Already Processed')
      } else {
        toast.error('No movies with TMDB IDs found in collection', 'Request Failed')
      }
      requestingCollection.value = false
      return
    }
    
    // Initialize progress
    collectionRequestProgress.value = { current: 0, total: moviesToRequest.length }
    
    let successCount = 0
    let errorCount = 0
    
    // Request movies one by one sequentially
    for (let i = 0; i < moviesToRequest.length; i++) {
      const movie = moviesToRequest[i]
      
      try {
        // Update progress
        collectionRequestProgress.value = { current: i + 1, total: moviesToRequest.length }
        
        // Make request
        const response = await $fetch('/api/overseerr-request', {
          method: 'POST',
          body: {
            mediaId: movie.trakt!.ids!.tmdb!,
            mediaType: 'movie',
            is4k: false
          }
        })
        
        if (response.success) {
          successCount++
        } else {
          errorCount++
          console.error(`Failed to request ${movie.title}:`, response.error)
        }
        
        // Small delay between requests to avoid overwhelming the API
        if (i < moviesToRequest.length - 1) {
          await new Promise(resolve => setTimeout(resolve, 500))
        }
      } catch (error) {
        errorCount++
        console.error(`Error requesting ${movie.title}:`, error)
      }
    }
    
    const skippedCount = allMovies.length - moviesToRequest.length
    
    // Show completion message
    if (successCount > 0) {
      let message = `Successfully requested ${successCount} ${successCount === 1 ? 'movie' : 'movies'} from "${collection.value.franchise_name}"`
      if (skippedCount > 0) {
        message += `. ${skippedCount} ${skippedCount === 1 ? 'movie was' : 'movies were'} already available and skipped.`
      }
      toast.success(message, 'Collection Request Complete')
    } else if (skippedCount > 0) {
      toast.info(
        `All ${skippedCount} ${skippedCount === 1 ? 'movie is' : 'movies are'} already available in Overseerr`,
        'Collection Already Available'
      )
    }
    
    if (errorCount > 0) {
      toast.warning(
        `${errorCount} ${errorCount === 1 ? 'movie' : 'movies'} failed to request`,
        'Some Requests Failed'
      )
    }
    
  } catch (error) {
    console.error('Error requesting collection:', error)
    toast.error(
      error instanceof Error ? error.message : 'Failed to request collection',
      'Request Error'
    )
  } finally {
    requestingCollection.value = false
    collectionRequestProgress.value = null
  }
}

const applySearch = async () => {
  // Reset to page 1 when searching
  currentPage.value = 1
  
  // Update URL with search query (don't await - do it in parallel)
  const query: Record<string, string> = {}
  if (searchQuery.value.trim()) {
    query.search = searchQuery.value.trim()
  }
  
  router.replace({ query }).catch(() => {
    // Ignore navigation errors
  })
  
  // Immediately fetch with current search value
  await loadCollection()
}

const clearSearch = async () => {
  if (!searchQuery.value) return
  
  searchQuery.value = ''
  currentPage.value = 1
  
  // Clear search from URL
  const query: Record<string, string> = {}
  await router.replace({ query })
  
  await loadCollection()
}

const goToPage = async (page: number) => {
  if (page < 1 || (pagination.value && page > pagination.value.total_pages)) {
    return
  }
  
  currentPage.value = page
  
  // Update URL without navigation
  const query: Record<string, string> = { page: String(page) }
  if (searchQuery.value) {
    query.search = searchQuery.value
  }
  await router.replace({ query })
  
  await loadCollection()
}

const loadCollection = async () => {
  if (!franchiseName.value) {
    return
  }
  
  loading.value = true
  try {
    // Use current search query value directly (most up-to-date)
    const searchTerm = searchQuery.value.trim()
    
    // Get page from query params or use current
    const pageFromQuery = parseInt(route.query.page as string) || currentPage.value
    currentPage.value = pageFromQuery
    
    console.log('Fetching collection with search:', searchTerm, 'page:', currentPage.value)
    
    const data = await getCollection(franchiseName.value, currentPage.value, itemsPerPage.value, searchTerm)
    if (data) {
      collection.value = data.collection
      pagination.value = data.pagination
      console.log('Collection loaded:', data.collection.movies.length, 'total:', data.pagination.total)
    }
  } catch (error) {
    console.error('Error loading collection:', error)
    const toast = useToast()
    toast.add({
      title: 'Error',
      description: 'Failed to load collection',
      color: 'red'
    })
  } finally {
    loading.value = false
  }
}

// Load collection when route changes
watch(() => route.params.franchise, () => {
  currentPage.value = 1
  searchQuery.value = ''
  loadCollection()
}, { immediate: true })

// Watch for query param changes
watch(() => route.query.page, (newPage) => {
  if (newPage) {
    const page = parseInt(newPage as string)
    if (page !== currentPage.value && page > 0) {
      currentPage.value = page
      loadCollection()
    }
  }
})

// Watch searchQuery for live updates with debounce
let searchTimeout: NodeJS.Timeout | null = null
watch(searchQuery, () => {
  if (searchTimeout) {
    clearTimeout(searchTimeout)
  }
  searchTimeout = setTimeout(() => {
    applySearch()
  }, 300)
})

// Watch URL query param changes
watch(() => route.query.search, (newSearch) => {
  const searchVal = (newSearch as string) || ''
  if (searchVal !== searchQuery.value) {
    searchQuery.value = searchVal
  }
})

// Page head
useHead({
  title: () => collection.value ? `${collection.value.franchise_name} - Collections` : 'Collection'
})
</script>

<style scoped>
.line-clamp-1 {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>

