<template>
  <div class="space-y-4 sm:space-y-6 lg:space-y-8">
    <!-- Header -->
    <div v-if="collection" class="space-y-3 sm:space-y-4">
      <div class="flex items-start justify-between gap-3 sm:gap-4">
        <div class="flex-1 min-w-0">
          <Button 
            @click="router.back()"
            variant="ghost"
            size="sm"
            class="mb-3 sm:mb-4 w-full sm:w-auto"
          >
            <AppIcon icon="lucide:arrow-left" size="16" class="mr-2" />
            Back to Collections
          </Button>
          
          <h1 class="text-2xl sm:text-3xl lg:text-4xl font-bold text-foreground mb-2 break-words">
            {{ collection.franchise_name }}
          </h1>
          
          <div class="flex flex-col sm:flex-row sm:flex-wrap items-start sm:items-center gap-2 sm:gap-3 lg:gap-4 text-xs sm:text-sm text-muted-foreground">
            <span class="flex items-center gap-1">
              <AppIcon icon="lucide:film" size="14" class="sm:w-4 sm:h-4" />
              <span v-if="pagination">
                Showing {{ (pagination.page - 1) * pagination.limit + 1 }} - {{ Math.min(pagination.page * pagination.limit, pagination.total) }} of {{ pagination.total }} {{ pagination.total === 1 ? 'movie' : 'movies' }}
              </span>
              <span v-else>
                {{ collection.total_movies }} {{ collection.total_movies === 1 ? 'movie' : 'movies' }}
              </span>
            </span>
            <span v-if="collection.years.length > 0" class="flex items-center gap-1">
              <AppIcon icon="lucide:calendar" size="14" class="sm:w-4 sm:h-4" />
              {{ collection.years[0] }} - {{ collection.years[collection.years.length - 1] }}
            </span>
            <div v-if="collection.genres.length > 0" class="flex items-center gap-1.5 sm:gap-2 flex-wrap">
              <AppIcon icon="lucide:tag" size="14" class="sm:w-4 sm:h-4 flex-shrink-0" />
              <div class="flex gap-1 flex-wrap">
                <span
                  v-for="genre in collection.genres"
                  :key="genre"
                  class="px-1.5 sm:px-2 py-0.5 bg-muted rounded-md text-[10px] sm:text-xs capitalize"
                >
                  {{ genre.replace('-', ' ') }}
                </span>
              </div>
            </div>
          </div>
          
          <div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 sm:gap-3 mt-3 sm:mt-4">
            <Button
              @click="handleRequestCollection"
              :disabled="requestingCollection || (requestableMovieCount !== null && requestableMovieCount === 0)"
              size="lg"
              class="bg-primary text-primary-foreground hover:bg-primary/90 w-full sm:w-auto text-sm sm:text-base"
            >
              <AppIcon 
                v-if="requestingCollection"
                icon="lucide:loader-2" 
                size="16" 
                class="sm:w-4.5 sm:h-4.5 mr-1.5 sm:mr-2 animate-spin"
              />
              <AppIcon 
                v-else
                icon="lucide:plus-circle" 
                size="16" 
                class="sm:w-4.5 sm:h-4.5 mr-1.5 sm:mr-2"
              />
              <span v-if="requestingCollection" class="truncate">
                {{ getCollectionProgressText() }}
              </span>
              <span v-else class="truncate">
                {{ getRequestableCountText }}
              </span>
            </Button>
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
    <div v-else-if="collection && collection.movies.length > 0" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-7 gap-2 sm:gap-3">
      <div
        v-for="(movie, index) in collection.movies"
        :key="`${movie.id}-${index}`"
        :style="{ animationDelay: `${index * 50}ms` }"
        @click="openMovieModal(movie)"
        class="group relative glass-card-enhanced rounded-2xl overflow-hidden cursor-pointer transition-all duration-500 animate-fade-in-up will-change-transform h-full flex flex-col"
      >
        <!-- Glow Effect on Hover -->
        <div class="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none z-0">
          <div class="absolute inset-0 bg-gradient-to-br from-primary/20 via-primary/10 to-transparent blur-2xl rounded-3xl"></div>
        </div>
        
        <!-- Movie Poster -->
        <div class="relative flex-1 bg-gradient-to-br from-muted via-muted/80 to-muted/60 overflow-hidden rounded-t-2xl">
          <img
            v-if="getMoviePosterUrl(movie)"
            :src="getMoviePosterUrl(movie)"
            :alt="movie.title"
            class="w-full h-full object-cover transition-all duration-700 group-hover:scale-110 group-hover:brightness-110"
            @error="handleImageError"
            loading="lazy"
          />
          <div v-else class="w-full h-full flex items-center justify-center p-6 bg-gradient-to-br from-primary/10 via-primary/5 to-muted/50">
            <div class="text-center transform group-hover:scale-110 transition-transform duration-300">
              <div class="w-16 h-16 mx-auto mb-3 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/10 backdrop-blur-sm flex items-center justify-center border border-primary/20 shadow-lg">
                <AppIcon icon="lucide:film" size="32" class="text-primary" />
              </div>
              <p class="text-xs text-foreground font-semibold line-clamp-2 drop-shadow-sm">
                {{ movie.title }}
              </p>
            </div>
          </div>
          
          <!-- Year Badge -->
          <div class="absolute top-3 left-3 z-20">
            <div class="bg-black/60 backdrop-blur-sm text-white px-2 py-1 rounded-md text-[10px] sm:text-xs font-semibold">
              {{ getMovieYear(movie) }}
            </div>
          </div>
          
          <!-- Rating Badge -->
          <div v-if="movie.rating" class="absolute top-3 right-3 z-20">
            <div class="flex items-center gap-1 text-[10px] sm:text-xs bg-amber-500/20 px-2 py-0.5 rounded-full border border-amber-500/30 backdrop-blur-sm">
              <AppIcon icon="lucide:star" size="10" class="sm:w-3 sm:h-3 text-amber-400 fill-amber-400" />
              <span class="font-bold text-amber-400">{{ movie.rating.toFixed(1) }}</span>
            </div>
          </div>
          
          <!-- Hover Overlay -->
          <div class="absolute inset-0 bg-gradient-to-t from-black/90 via-black/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-end z-10">
            <div class="p-2 sm:p-3 w-full">
              <h3 class="text-white font-bold text-xs sm:text-sm mb-1 line-clamp-2">
                {{ movie.title }}
              </h3>
              <p v-if="movie.overview" class="text-white/90 text-[10px] sm:text-xs line-clamp-2 mb-1.5 sm:mb-2">
                {{ movie.overview }}
              </p>
              <!-- Availability Badge -->
              <div v-if="isMovieAvailableInOverseerr(movie)" class="mb-1.5 sm:mb-2">
                <div class="w-full bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 px-2 sm:px-3 py-1 sm:py-1.5 rounded-md text-[10px] sm:text-xs font-semibold flex items-center justify-center gap-1 sm:gap-1.5">
                  <AppIcon icon="lucide:check-circle-2" size="10" class="sm:w-3 sm:h-3" />
                  <span class="hidden sm:inline">Available in Overseerr</span>
                  <span class="sm:hidden">Available</span>
                </div>
              </div>
              <div v-else-if="isMovieRequestedInOverseerr(movie)" class="mb-1.5 sm:mb-2">
                <div class="w-full bg-amber-500/20 border border-amber-500/30 text-amber-400 px-2 sm:px-3 py-1 sm:py-1.5 rounded-md text-[10px] sm:text-xs font-semibold flex items-center justify-center gap-1 sm:gap-1.5">
                  <AppIcon icon="lucide:clock" size="10" class="sm:w-3 sm:h-3" />
                  <span class="hidden sm:inline">Already Requested</span>
                  <span class="sm:hidden">Requested</span>
                </div>
              </div>
              
              <!-- Request Button -->
              <Button
                v-if="!isMovieInDatabase(movie) && !isMovieRequested(movie) && !isMovieAvailableInOverseerr(movie) && !isMovieRequestedInOverseerr(movie)"
                @click.stop="handleRequest(movie)"
                :disabled="requestingMovies.has(getMovieId(movie))"
                size="sm"
                class="w-full text-xs sm:text-sm"
              >
                <AppIcon 
                  v-if="requestingMovies.has(getMovieId(movie))"
                  icon="lucide:loader-2" 
                  size="12" 
                  class="sm:w-3.5 sm:h-3.5 mr-1.5 sm:mr-2 animate-spin"
                />
                <AppIcon 
                  v-else
                  icon="lucide:plus" 
                  size="12" 
                  class="sm:w-3.5 sm:h-3.5 mr-1.5 sm:mr-2"
                />
                {{ requestingMovies.has(getMovieId(movie)) ? 'Requesting...' : 'Request' }}
              </Button>
              <Button
                v-else-if="isMovieInDatabase(movie) && movieDatabaseIds.has(getMovieId(movie))"
                @click.stop="viewMovieInDatabase(movie)"
                size="sm"
                variant="outline"
                class="w-full bg-primary/20 border-primary/30 text-primary hover:bg-primary/30 text-xs sm:text-sm"
              >
                <AppIcon icon="lucide:external-link" size="12" class="sm:w-3.5 sm:h-3.5 mr-1.5 sm:mr-2" />
                <span class="hidden sm:inline">View Item</span>
                <span class="sm:hidden">View</span>
              </Button>
              <Button
                v-else-if="isMovieAvailableInOverseerr(movie)"
                @click.stop
                size="sm"
                variant="outline"
                class="w-full bg-emerald-500/20 border-emerald-500/30 text-emerald-400 text-xs sm:text-sm"
                disabled
              >
                <AppIcon icon="lucide:check-circle-2" size="12" class="sm:w-3.5 sm:h-3.5 mr-1.5 sm:mr-2" />
                Available
              </Button>
              <Button
                v-else-if="isMovieRequestedInOverseerr(movie)"
                @click.stop
                size="sm"
                variant="outline"
                class="w-full bg-amber-500/20 border-amber-500/30 text-amber-400 text-xs sm:text-sm"
                disabled
              >
                <AppIcon icon="lucide:clock" size="12" class="sm:w-3.5 sm:h-3.5 mr-1.5 sm:mr-2" />
                <span class="hidden sm:inline">Already Requested</span>
                <span class="sm:hidden">Requested</span>
              </Button>
              <Button
                v-else-if="isMovieRequested(movie) && !isMovieInDatabase(movie)"
                @click.stop
                size="sm"
                variant="outline"
                class="w-full bg-amber-500/20 border-amber-500/30 text-amber-400 text-xs sm:text-sm"
                disabled
              >
                <AppIcon icon="lucide:check-circle" size="12" class="sm:w-3.5 sm:h-3.5 mr-1.5 sm:mr-2" />
                <span class="hidden sm:inline">Already Requested</span>
                <span class="sm:hidden">Requested</span>
              </Button>
            </div>
          </div>
        </div>
        
        <!-- Enhanced Card Info with Glassmorphic Background -->
        <div class="relative p-3 sm:p-4 space-y-2 bg-gradient-to-b from-card/95 via-card/90 to-card backdrop-blur-sm flex-shrink-0 rounded-b-2xl">
          <!-- Title -->
          <h3 class="text-xs sm:text-sm font-bold text-foreground line-clamp-1 transition-all duration-300 group-hover:text-primary">
            {{ movie.title }}
          </h3>
          
          <!-- Year and Runtime Row -->
          <div class="flex items-center justify-between gap-2">
            <p class="text-[10px] sm:text-xs text-muted-foreground font-medium">
              {{ getMovieYear(movie) }}
            </p>
            <span v-if="movie.runtime" class="flex items-center gap-1 text-[10px] sm:text-xs text-muted-foreground">
              <AppIcon icon="lucide:clock" size="10" class="sm:w-3 sm:h-3" />
              {{ movie.runtime }}m
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
    <div v-if="pagination && pagination.total_pages > 1" class="flex flex-wrap items-center justify-center gap-1.5 sm:gap-2 pt-3 sm:pt-4">
      <Button
        @click="goToPage(pagination.page - 1)"
        :disabled="!pagination.has_prev || loading"
        variant="outline"
        size="sm"
        class="p-1.5 sm:px-3 sm:py-2"
      >
        <AppIcon icon="lucide:chevron-left" size="14" class="sm:w-4 sm:h-4 mr-0.5 sm:mr-1" />
        <span class="hidden sm:inline">Previous</span>
      </Button>
      
      <div class="flex items-center gap-0.5 sm:gap-1">
        <Button
          v-for="pageNum in visiblePages"
          :key="pageNum"
          @click="goToPage(pageNum)"
          :disabled="loading"
          :variant="pageNum === pagination.page ? 'default' : 'outline'"
          size="sm"
          class="min-w-[32px] sm:min-w-[40px] p-1.5 sm:px-3 sm:py-2 text-xs sm:text-sm"
        >
          {{ pageNum }}
        </Button>
      </div>
      
      <Button
        @click="goToPage(pagination.page + 1)"
        :disabled="!pagination.has_next || loading"
        variant="outline"
        size="sm"
        class="p-1.5 sm:px-3 sm:py-2"
      >
        <span class="hidden sm:inline">Next</span>
        <AppIcon icon="lucide:chevron-right" size="14" class="sm:w-4 sm:h-4 ml-0.5 sm:ml-1" />
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
import type { SeerrMovie, SeerrCollection } from '~/types'

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
const { getCollection, getAllMoviesInCollection, getSeerrPosterUrl } = useSeerrCollections()
const { toast } = useToast()

const collection = ref<Collection | null>(null)
const pagination = ref<PaginationInfo | null>(null)
const loading = ref(false)
const currentPage = ref(1)
const itemsPerPage = ref(30)
const searchQuery = ref('')
const showMovieModal = ref(false)
const selectedMovie = ref<SeerrMovie | null>(null)

// Track movies in database and requested movies
const moviesInDatabase = ref<Set<string>>(new Set())
const movieDatabaseIds = ref<Map<string, number>>(new Map())
const requestedMovies = ref<Set<string>>(new Set())
const requestingMovies = ref<Set<string>>(new Set())
const checkingMoviesInDatabase = ref(false)

// Track Overseerr availability status
const moviesAvailableInOverseerr = ref<Set<string>>(new Set())
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

const getMovieYear = (movie: SeerrMovie): number => {
  if (movie.releaseDate) {
    return new Date(movie.releaseDate).getFullYear()
  }
  return 0
}

const getMovieId = (movie: SeerrMovie): string => {
  return `tmdb_${movie.id}`
}

const getMoviePosterUrl = (movie: SeerrMovie): string | null => {
  return getSeerrPosterUrl(movie)
}

const visiblePages = computed(() => {
  if (!pagination.value) return []
  
  const total = pagination.value.total_pages
  const current = pagination.value.page
  const pages: number[] = []
  
  let start = Math.max(1, current - 3)
  let end = Math.min(total, current + 3)
  
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

const openMovieModal = (movie: SeerrMovie) => {
  // Convert SeerrMovie to format expected by MovieDetailsModal
  selectedMovie.value = movie as any
  showMovieModal.value = true
}

const closeMovieModal = () => {
  showMovieModal.value = false
  selectedMovie.value = null
}

const checkMoviesInDatabase = async (movies: SeerrMovie[]) => {
  if (checkingMoviesInDatabase.value) return
  
  checkingMoviesInDatabase.value = true
  
  try {
    const checks = movies
      .filter(movie => movie.id || movie.imdb_id)
      .map(async (movie) => {
        try {
          const params = new URLSearchParams()
          if (movie.imdb_id) {
            params.append('imdb_id', movie.imdb_id)
          } else if (movie.id) {
            params.append('tmdb_id', String(movie.id))
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

const checkOverseerrStatus = async (movies: SeerrMovie[], force: boolean = false) => {
  if (!force && checkingOverseerrStatus.value) {
    while (checkingOverseerrStatus.value) {
      await new Promise(resolve => setTimeout(resolve, 100))
    }
    return
  }
  
  checkingOverseerrStatus.value = true
  
  try {
    const moviesToCheck = movies.filter(movie => movie.id)
    
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
          }>(`/api/overseerr-movie-status?tmdb_id=${movie.id}`, {
            timeout: 10000
          })
          
          if (response.success && response.data) {
            const movieId = getMovieId(movie)
            if (response.data.available) {
              moviesAvailableInOverseerr.value.add(movieId)
              moviesRequestedInOverseerr.value.delete(movieId)
            } else if (response.data.requested) {
              moviesRequestedInOverseerr.value.add(movieId)
              moviesAvailableInOverseerr.value.delete(movieId)
            }
          }
        } catch (error) {
          // Silently handle errors
        }
      })
      
      await Promise.all(batchChecks)
      
      if (i + BATCH_SIZE < moviesToCheck.length) {
        await new Promise(resolve => setTimeout(resolve, 100))
      }
    }
  } finally {
    checkingOverseerrStatus.value = false
  }
}

const isMovieAvailableInOverseerr = (movie: SeerrMovie): boolean => {
  return moviesAvailableInOverseerr.value.has(getMovieId(movie))
}

const isMovieRequestedInOverseerr = (movie: SeerrMovie): boolean => {
  return moviesRequestedInOverseerr.value.has(getMovieId(movie))
}

const isMovieInDatabase = (movie: SeerrMovie): boolean => {
  return moviesInDatabase.value.has(getMovieId(movie))
}

const isMovieRequested = (movie: SeerrMovie): boolean => {
  return requestedMovies.value.has(getMovieId(movie))
}

const viewMovieInDatabase = (movie: SeerrMovie) => {
  const movieId = getMovieId(movie)
  const databaseId = movieDatabaseIds.value.get(movieId)
  if (databaseId) {
    navigateTo(`/processed-media?mediaId=${databaseId}`)
  }
}

const handleRequest = async (movie: SeerrMovie) => {
  if (!movie.id) {
    toast.error('Movie does not have a TMDB ID', 'Cannot Request')
    return
  }
  
  const movieId = getMovieId(movie)
  requestingMovies.value.add(movieId)
  
  try {
    const response = await $fetch('/api/overseerr-request', {
      method: 'POST',
      body: {
        mediaId: movie.id,
        mediaType: 'movie',
        is4k: false
      }
    })
    
    if (response.success) {
      requestedMovies.value.add(movieId)
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

const calculateRequestableCount = async () => {
  if (!collection.value || calculatingRequestableCount.value) return
  
  calculatingRequestableCount.value = true
  
  try {
    const allMovies = await getAllMoviesInCollection(collection.value.franchise_name)
    
    if (!allMovies || allMovies.length === 0) {
      requestableMovieCount.value = 0
      return
    }
    
    if (allMovies.some(m => m.id)) {
      await checkOverseerrStatus(allMovies, true)
    }
    
    const count = allMovies.filter(movie => {
      if (!movie.id) return false
      const movieId = getMovieId(movie)
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

const getCollectionProgressText = (): string => {
  if (collectionRequestProgress.value) {
    return `Requesting ${collectionRequestProgress.value.current}/${collectionRequestProgress.value.total}`
  }
  return 'Requesting...'
}

const getRequestableCountText = computed(() => {
  if (requestableMovieCount.value === null) {
    return calculatingRequestableCount.value ? 'Calculating...' : 'Request Entire Collection'
  }
  if (requestableMovieCount.value === 0) {
    return 'All Movies Available'
  }
  return `Request Entire Collection (${requestableMovieCount.value})`
})

const handleRequestCollection = async () => {
  if (!collection.value || requestingCollection.value) {
    return
  }
  
  requestingCollection.value = true
  
  try {
    const allMovies = await getAllMoviesInCollection(collection.value.franchise_name)
    
    if (!allMovies || allMovies.length === 0) {
      toast.error('No movies found in collection', 'Request Failed')
      requestingCollection.value = false
      return
    }
    
    await checkOverseerrStatus(allMovies)
    
    const moviesToRequest = allMovies.filter(movie => {
      if (!movie.id) return false
      const movieId = getMovieId(movie)
      return !moviesAvailableInOverseerr.value.has(movieId) && !moviesRequestedInOverseerr.value.has(movieId)
    })
    
    if (moviesToRequest.length === 0) {
      const availableCount = moviesAvailableInOverseerr.value.size
      const requestedCount = moviesRequestedInOverseerr.value.size
      const totalCount = availableCount + requestedCount
      
      if (totalCount > 0) {
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
    
    collectionRequestProgress.value = { current: 0, total: moviesToRequest.length }
    
    let successCount = 0
    let errorCount = 0
    
    for (let i = 0; i < moviesToRequest.length; i++) {
      const movie = moviesToRequest[i]
      
      try {
        collectionRequestProgress.value = { current: i + 1, total: moviesToRequest.length }
        
        const response = await $fetch('/api/overseerr-request', {
          method: 'POST',
          body: {
            mediaId: movie.id,
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
        
        if (i < moviesToRequest.length - 1) {
          await new Promise(resolve => setTimeout(resolve, 500))
        }
      } catch (error) {
        errorCount++
        console.error(`Error requesting ${movie.title}:`, error)
      }
    }
    
    const skippedCount = allMovies.length - moviesToRequest.length
    
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
  currentPage.value = 1
  
  const query: Record<string, string> = {}
  if (searchQuery.value.trim()) {
    query.search = searchQuery.value.trim()
  }
  
  router.replace({ query }).catch(() => {})
  
  await loadCollection()
}

const clearSearch = async () => {
  if (!searchQuery.value) return
  
  searchQuery.value = ''
  currentPage.value = 1
  
  const query: Record<string, string> = {}
  await router.replace({ query })
  
  await loadCollection()
}

const goToPage = async (page: number) => {
  if (page < 1 || (pagination.value && page > pagination.value.total_pages)) {
    return
  }
  
  currentPage.value = page
  
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
    const searchTerm = searchQuery.value.trim()
    const pageFromQuery = parseInt(route.query.page as string) || currentPage.value
    currentPage.value = pageFromQuery
    
    const data = await getCollection(franchiseName.value, currentPage.value, itemsPerPage.value, searchTerm)
    if (data) {
      collection.value = data.collection
      pagination.value = data.pagination
    }
  } catch (error) {
    console.error('Error loading Seerr collection:', error)
    toast.add({
      title: 'Error',
      description: 'Failed to load collection',
      color: 'red'
    })
  } finally {
    loading.value = false
  }
}

watch(() => collection.value?.movies, async (movies) => {
  if (movies && movies.length > 0) {
    checkMoviesInDatabase(movies)
    checkOverseerrStatus(movies)
  }
}, { immediate: true })

watch(() => collection.value, async (newCollection) => {
  if (newCollection) {
    setTimeout(() => {
      calculateRequestableCount()
    }, 1000)
  } else {
    requestableMovieCount.value = null
  }
}, { immediate: true })

watch([moviesAvailableInOverseerr, moviesRequestedInOverseerr, moviesInDatabase], () => {
  if (collection.value) {
    calculateRequestableCount()
  }
})

watch(() => route.params.franchise, () => {
  currentPage.value = 1
  searchQuery.value = ''
  loadCollection()
}, { immediate: true })

watch(() => route.query.page, (newPage) => {
  if (newPage) {
    const page = parseInt(newPage as string)
    if (page !== currentPage.value && page > 0) {
      currentPage.value = page
      loadCollection()
    }
  }
})

let searchTimeout: NodeJS.Timeout | null = null
watch(searchQuery, () => {
  if (searchTimeout) {
    clearTimeout(searchTimeout)
  }
  searchTimeout = setTimeout(() => {
    applySearch()
  }, 300)
})

watch(() => route.query.search, (newSearch) => {
  const searchVal = (newSearch as string) || ''
  if (searchVal !== searchQuery.value) {
    searchQuery.value = searchVal
  }
})

useHead({
  title: () => collection.value ? `${collection.value.franchise_name} - Seerr Collections` : 'Seerr Collection'
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

