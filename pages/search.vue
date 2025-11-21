<template>
  <div>
      <!-- Search Header -->
      <div class="mb-8">
        <h1 class="text-3xl font-bold text-foreground mb-2">Search Media</h1>
        <p class="text-muted-foreground">Search for movies, TV shows, and more from Overseerr</p>
      </div>

      <!-- Search Input -->
      <div class="max-w-3xl mb-8">
        <div class="relative">
          <input
            v-model="searchQuery"
            @keyup.enter="handleSearch"
            @input="handleInput"
            type="text"
            placeholder="Search for movies, TV shows..."
            class="w-full px-6 py-4 pr-16 text-lg bg-card border-2 border-border rounded-xl focus:outline-none focus:border-primary transition-colors text-foreground placeholder:text-muted-foreground"
          />
          <button
            @click="handleSearch"
            :disabled="isSearching || !hasQuery"
            class="absolute right-2 top-1/2 -translate-y-1/2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
          >
            <Icon v-if="!isSearching" name="mdi:magnify" class="w-5 h-5" />
            <Icon v-else name="mdi:loading" class="w-5 h-5 animate-spin" />
          </button>
        </div>
      </div>


      <!-- Results Count -->
      <div v-if="resultsLength > 0" class="mb-6 flex items-center justify-between">
        <p class="text-muted-foreground">
          Found <span class="font-semibold text-foreground">{{ searchState.totalResults }}</span> results
        </p>
        <div class="flex items-center gap-2">
          <button
            @click="searchState.previousPage"
            :disabled="searchState.page === 1 || isSearching"
            class="px-4 py-2 bg-card border border-border rounded-lg hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Icon name="mdi:chevron-left" class="w-5 h-5" />
          </button>
          <span class="text-sm text-muted-foreground">
            Page {{ searchState.page }} of {{ searchState.totalPages }}
          </span>
          <button
            @click="searchState.nextPage"
            :disabled="searchState.page === searchState.totalPages || isSearching"
            class="px-4 py-2 bg-card border border-border rounded-lg hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Icon name="mdi:chevron-right" class="w-5 h-5" />
          </button>
        </div>
      </div>

      <!-- Results Grid -->
      <div v-if="resultsLength > 0" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        <div
          v-for="media in results"
          :key="media.id"
          class="group relative bg-card border border-border rounded-xl overflow-hidden hover:border-primary transition-all hover:shadow-lg cursor-pointer"
          @click="openModal(media)"
        >
          <!-- Poster -->
          <div class="relative aspect-[2/3] bg-muted overflow-hidden">
            <img
              v-if="getPosterUrl(media.posterPath)"
              :src="getPosterUrl(media.posterPath)"
              :alt="getMediaTitle(media)"
              class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            />
            <div v-else class="w-full h-full flex items-center justify-center">
              <Icon name="mdi:image-off" class="w-12 h-12 text-muted-foreground" />
            </div>

            <!-- Media Type Badge -->
            <div class="absolute top-2 left-2 px-2 py-1 bg-primary/90 backdrop-blur-sm text-primary-foreground text-xs font-semibold rounded">
              {{ getMediaTypeLabel(media) }}
            </div>

            <!-- In Database Checkmark -->
            <div
              v-if="isInDatabase(media)"
              class="absolute top-2 right-2 w-8 h-8 flex items-center justify-center bg-success/90 backdrop-blur-sm rounded-full shadow-lg"
            >
              <Icon name="mdi:check-circle" class="w-5 h-5 text-white" />
            </div>

              <!-- Hover Overlay with Request Button -->
              <div class="absolute inset-0 bg-black/80 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                <div class="text-center p-4">
                  <p class="text-white font-medium mb-4">{{ getMediaTitle(media) }}</p>
                  <button
                    v-if="canRequest(media)"
                    @click.stop="handleQuickRequestClick(media)"
                    class="px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium flex items-center gap-2 mx-auto"
                  >
                    <Icon name="mdi:plus-circle" class="w-5 h-5" />
                    Request
                  </button>
                  <button
                    v-else-if="isInDatabase(media)"
                    @click="handleViewDetails(media)"
                    class="px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium flex items-center gap-2 mx-auto"
                  >
                    <Icon name="mdi:open-in-new" class="w-5 h-5" />
                    View Details
                  </button>
                  <div
                    v-else-if="hasBeenRequested(media)"
                    class="px-6 py-3 bg-info/20 text-info rounded-lg font-medium flex items-center gap-2 mx-auto"
                  >
                    <Icon name="mdi:clock-outline" class="w-5 h-5" />
                    Request Submitted
                  </div>
                </div>
              </div>

            <!-- Vote Average -->
            <div v-if="media.voteAverage" class="absolute bottom-2 right-2 flex items-center gap-1 px-2 py-1 bg-black/70 backdrop-blur-sm rounded">
              <Icon name="mdi:star" class="w-4 h-4 text-yellow-400" />
              <span class="text-sm font-semibold text-white">{{ formatVoteAverage(media.voteAverage) }}</span>
            </div>
          </div>

          <!-- Info -->
          <div class="p-4">
            <h3 class="font-semibold text-foreground mb-1 line-clamp-2">
              {{ getMediaTitle(media) }}
            </h3>
            <div class="flex items-center gap-2 text-sm text-muted-foreground">
              <span v-if="getMediaYear(media)">{{ getMediaYear(media) }}</span>
              <span v-if="media.mediaType !== 'person' && media.popularity" class="flex items-center gap-1">
                <Icon name="mdi:trending-up" class="w-4 h-4" />
                {{ Math.round(media.popularity) }}
              </span>
            </div>
            <p v-if="media.overview" class="mt-2 text-sm text-muted-foreground line-clamp-2">
              {{ media.overview }}
            </p>
          </div>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="isSearching" class="flex items-center justify-center py-16">
        <div class="flex flex-col items-center gap-4">
          <Icon name="mdi:loading" class="w-12 h-12 animate-spin text-primary" />
          <p class="text-muted-foreground">Searching...</p>
        </div>
      </div>

      <!-- Discover Results -->
      <div v-if="!isSearching && resultsLength === 0 && !hasQuery && (discoverMovies.length > 0 || discoverTv.length > 0)" class="mb-8 space-y-12">
        <!-- Discover Movies -->
        <div v-if="discoverMovies.length > 0">
          <div class="mb-6">
            <h3 class="text-xl font-semibold text-foreground mb-2">Discover Popular Movies</h3>
            <p class="text-muted-foreground">Trending and popular movies you might like</p>
          </div>
          
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 mb-6">
            <div
              v-for="media in discoverMovies"
              :key="media.id"
              class="group relative bg-card border border-border rounded-xl overflow-hidden hover:border-primary transition-all hover:shadow-lg cursor-pointer"
              @click="openModal(media)"
            >
              <!-- Same card structure -->
              <div class="relative aspect-[2/3] bg-muted overflow-hidden">
                <img
                  v-if="getPosterUrl(media.posterPath)"
                  :src="getPosterUrl(media.posterPath)"
                  :alt="getMediaTitle(media)"
                  class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                />
                <div v-else class="w-full h-full flex items-center justify-center">
                  <Icon name="mdi:image-off" class="w-12 h-12 text-muted-foreground" />
                </div>

                <div class="absolute top-2 left-2 px-2 py-1 bg-primary/90 backdrop-blur-sm text-primary-foreground text-xs font-semibold rounded">
                  {{ getMediaTypeLabel(media) }}
                </div>

                <div
                  v-if="isInDatabase(media)"
                  class="absolute top-2 right-2 w-8 h-8 flex items-center justify-center bg-success/90 backdrop-blur-sm rounded-full shadow-lg"
                >
                  <Icon name="mdi:check-circle" class="w-5 h-5 text-white" />
                </div>

                <div class="absolute inset-0 bg-black/80 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                  <div class="text-center p-4">
                    <p class="text-white font-medium mb-4">{{ getMediaTitle(media) }}</p>
                  <button
                    v-if="canRequest(media)"
                    @click.stop="handleQuickRequestClick(media)"
                    class="px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium flex items-center gap-2 mx-auto"
                  >
                    <Icon name="mdi:plus-circle" class="w-5 h-5" />
                    Request
                  </button>
                  <button
                    v-else-if="isInDatabase(media)"
                    @click="handleViewDetails(media)"
                    class="px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium flex items-center gap-2 mx-auto"
                  >
                    <Icon name="mdi:open-in-new" class="w-5 h-5" />
                    View Details
                  </button>
                  <div
                    v-else-if="hasBeenRequested(media)"
                    class="px-6 py-3 bg-info/20 text-info rounded-lg font-medium flex items-center gap-2 mx-auto"
                  >
                    <Icon name="mdi:clock-outline" class="w-5 h-5" />
                    Request Submitted
                  </div>
                  </div>
                </div>

                <div v-if="media.voteAverage" class="absolute bottom-2 right-2 flex items-center gap-1 px-2 py-1 bg-black/70 backdrop-blur-sm rounded">
                  <Icon name="mdi:star" class="w-4 h-4 text-yellow-400" />
                  <span class="text-sm font-semibold text-white">{{ formatVoteAverage(media.voteAverage) }}</span>
                </div>
              </div>

              <div class="p-4">
                <h3 class="font-semibold text-foreground mb-1 line-clamp-2">
                  {{ getMediaTitle(media) }}
                </h3>
                <div class="flex items-center gap-2 text-sm text-muted-foreground">
                  <span v-if="getMediaYear(media)">{{ getMediaYear(media) }}</span>
                  <span v-if="media.mediaType !== 'person' && media.popularity" class="flex items-center gap-1">
                    <Icon name="mdi:trending-up" class="w-4 h-4" />
                    {{ Math.round(media.popularity) }}
                  </span>
                </div>
                <p v-if="media.overview" class="mt-2 text-sm text-muted-foreground line-clamp-2">
                  {{ media.overview }}
                </p>
              </div>
            </div>
          </div>
          
          <div v-if="moviesPage < moviesTotalPages" class="text-center">
            <button
              @click="loadMoreMovies"
              class="px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium flex items-center gap-2 mx-auto"
            >
              <Icon name="mdi:chevron-down" class="w-5 h-5" />
              Load More Movies
            </button>
          </div>
        </div>

        <!-- Discover TV Shows -->
        <div v-if="discoverTv.length > 0">
          <div class="mb-6">
            <h3 class="text-xl font-semibold text-foreground mb-2">Discover Popular TV Shows</h3>
            <p class="text-muted-foreground">Trending and popular TV shows you might like</p>
          </div>
          
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 mb-6">
            <div
              v-for="media in discoverTv"
              :key="media.id"
              class="group relative bg-card border border-border rounded-xl overflow-hidden hover:border-primary transition-all hover:shadow-lg cursor-pointer"
              @click="openModal(media)"
            >
              <!-- Same card structure -->
              <div class="relative aspect-[2/3] bg-muted overflow-hidden">
                <img
                  v-if="getPosterUrl(media.posterPath)"
                  :src="getPosterUrl(media.posterPath)"
                  :alt="getMediaTitle(media)"
                  class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                />
                <div v-else class="w-full h-full flex items-center justify-center">
                  <Icon name="mdi:image-off" class="w-12 h-12 text-muted-foreground" />
                </div>

                <div class="absolute top-2 left-2 px-2 py-1 bg-primary/90 backdrop-blur-sm text-primary-foreground text-xs font-semibold rounded">
                  {{ getMediaTypeLabel(media) }}
                </div>

                <div
                  v-if="isInDatabase(media)"
                  class="absolute top-2 right-2 w-8 h-8 flex items-center justify-center bg-success/90 backdrop-blur-sm rounded-full shadow-lg"
                >
                  <Icon name="mdi:check-circle" class="w-5 h-5 text-white" />
                </div>

                <div class="absolute inset-0 bg-black/80 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                  <div class="text-center p-4">
                    <p class="text-white font-medium mb-4">{{ getMediaTitle(media) }}</p>
                  <button
                    v-if="canRequest(media)"
                    @click.stop="handleQuickRequestClick(media)"
                    class="px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium flex items-center gap-2 mx-auto"
                  >
                    <Icon name="mdi:plus-circle" class="w-5 h-5" />
                    Request
                  </button>
                  <button
                    v-else-if="isInDatabase(media)"
                    @click="handleViewDetails(media)"
                    class="px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium flex items-center gap-2 mx-auto"
                  >
                    <Icon name="mdi:open-in-new" class="w-5 h-5" />
                    View Details
                  </button>
                  <div
                    v-else-if="hasBeenRequested(media)"
                    class="px-6 py-3 bg-info/20 text-info rounded-lg font-medium flex items-center gap-2 mx-auto"
                  >
                    <Icon name="mdi:clock-outline" class="w-5 h-5" />
                    Request Submitted
                  </div>
                  </div>
                </div>

                <div v-if="media.voteAverage" class="absolute bottom-2 right-2 flex items-center gap-1 px-2 py-1 bg-black/70 backdrop-blur-sm rounded">
                  <Icon name="mdi:star" class="w-4 h-4 text-yellow-400" />
                  <span class="text-sm font-semibold text-white">{{ formatVoteAverage(media.voteAverage) }}</span>
                </div>
              </div>

              <div class="p-4">
                <h3 class="font-semibold text-foreground mb-1 line-clamp-2">
                  {{ getMediaTitle(media) }}
                </h3>
                <div class="flex items-center gap-2 text-sm text-muted-foreground">
                  <span v-if="getMediaYear(media)">{{ getMediaYear(media) }}</span>
                  <span v-if="media.mediaType !== 'person' && media.popularity" class="flex items-center gap-1">
                    <Icon name="mdi:trending-up" class="w-4 h-4" />
                    {{ Math.round(media.popularity) }}
                  </span>
                </div>
                <p v-if="media.overview" class="mt-2 text-sm text-muted-foreground line-clamp-2">
                  {{ media.overview }}
                </p>
              </div>
            </div>
          </div>
          
          <div v-if="tvPage < tvTotalPages" class="text-center">
            <button
              @click="loadMoreTv"
              class="px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium flex items-center gap-2 mx-auto"
            >
              <Icon name="mdi:chevron-down" class="w-5 h-5" />
              Load More TV Shows
            </button>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-if="!isSearching && resultsLength === 0 && !hasQuery && discoverMovies.length === 0 && discoverTv.length === 0" class="flex flex-col items-center justify-center py-16">
        <Icon name="mdi:magnify" class="w-20 h-20 text-muted-foreground/50 mb-4" />
        <p class="text-muted-foreground text-lg">Enter a search query to find media</p>
      </div>
  </div>

  <!-- Media Details Modal -->
  <MediaDetailsModal
    :media="selectedMedia"
    :is-open="isModalOpen"
    @close="closeModal"
    @request="handleRequest"
  />

  <!-- Toast Notifications -->
  <div class="fixed bottom-4 right-4 z-50 space-y-2">
    <TransitionGroup name="toast" tag="div">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        class="px-4 py-3 rounded-lg shadow-lg min-w-[300px] max-w-[400px] animate-fade-in"
        :class="getToastClass(toast.type)"
      >
        <div class="flex items-center gap-3">
          <Icon :name="getToastIcon(toast.type)" class="w-5 h-5 flex-shrink-0" />
          <div class="flex-1">
            <p class="text-sm font-medium">{{ toast.title }}</p>
            <p class="text-sm opacity-90">{{ toast.message }}</p>
          </div>
          <button
            @click="removeToast(toast.id)"
            class="flex-shrink-0 hover:opacity-70 transition-opacity"
          >
            <Icon name="mdi:close" class="w-4 h-4" />
          </button>
        </div>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup lang="ts">
const searchState = useSearch()
const isSearching = ref(false)

// Toast state
interface Toast {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message: string
}

const toasts = ref<Toast[]>([])

const addToast = (type: Toast['type'], title: string, message: string) => {
  const id = Date.now().toString()
  toasts.value.push({ id, type, title, message })
  
  // Auto remove after 5 seconds
  setTimeout(() => {
    removeToast(id)
  }, 5000)
}

const removeToast = (id: string) => {
  const index = toasts.value.findIndex(t => t.id === id)
  if (index > -1) {
    toasts.value.splice(index, 1)
  }
}

const getToastClass = (type: string) => {
  const classes = {
    success: 'bg-success text-success-foreground',
    error: 'bg-destructive text-destructive-foreground',
    warning: 'bg-warning text-warning-foreground',
    info: 'bg-info text-info-foreground'
  }
  return classes[type as keyof typeof classes] || 'bg-muted text-foreground'
}

const getToastIcon = (type: string) => {
  const icons = {
    success: 'mdi:check-circle',
    error: 'mdi:alert-circle',
    warning: 'mdi:alert-triangle',
    info: 'mdi:information'
  }
  return icons[type as keyof typeof icons] || 'mdi:information'
}

const toast = {
  success: (message: string, title: string = 'Success') => addToast('success', title, message),
  error: (message: string, title: string = 'Error') => addToast('error', title, message),
  warning: (message: string, title: string = 'Warning') => addToast('warning', title, message),
  info: (message: string, title: string = 'Info') => addToast('info', title, message)
}

// Create a local ref for the input binding
const searchQuery = ref('')

// Sync the local ref with the composable
watch(searchQuery, (newValue) => {
  searchState.query.value = newValue
}, { immediate: false })

// Computed to check if query has content
const hasQuery = computed(() => {
  return searchQuery.value.trim().length > 0
})

const handleInput = debounce(() => {
  if (hasQuery.value) {
    handleSearch()
  }
}, 500)

// Computed properties for template access
const results = computed(() => {
  const rawResults = searchState.results
  return Array.isArray(rawResults) ? rawResults : (typeof rawResults === 'object' && rawResults?.value ? rawResults.value : [])
})

const resultsLength = computed(() => results.value.length)

// Discover results
const discoverMovies = ref<any[]>([])
const discoverTv = ref<any[]>([])
const moviesPage = ref(1)
const tvPage = ref(1)
const moviesTotalPages = ref(1)
const tvTotalPages = ref(1)
const isLoadingDiscover = ref(false)

// Load discover results on mount
onMounted(async () => {
  await loadDiscoverResults()
})

const loadDiscoverResults = async () => {
  isLoadingDiscover.value = true
  try {
    // Load movies
    const moviesResponse = await $fetch('/api/overseerr-discover', {
      query: {
        page: moviesPage.value,
        sortBy: 'popularity.desc',
        language: 'en',
        type: 'movies'
      }
    })
    
    if (moviesResponse.success && moviesResponse.data) {
      discoverMovies.value = moviesResponse.data.results.slice(0, 12) // Limit to 12
      moviesTotalPages.value = moviesResponse.data.totalPages
    }
    
    // Load TV shows
    const tvResponse = await $fetch('/api/overseerr-discover', {
      query: {
        page: tvPage.value,
        sortBy: 'popularity.desc',
        language: 'en',
        type: 'tv'
      }
    })
    
    if (tvResponse.success && tvResponse.data) {
      discoverTv.value = tvResponse.data.results.slice(0, 12) // Limit to 12
      tvTotalPages.value = tvResponse.data.totalPages
    }
  } catch (error) {
    console.error('Error loading discover results:', error)
  } finally {
    isLoadingDiscover.value = false
  }
}

const loadMoreMovies = async () => {
  if (moviesPage.value >= moviesTotalPages.value) return
  moviesPage.value++
  
  try {
    const response = await $fetch('/api/overseerr-discover', {
      query: {
        page: moviesPage.value,
        sortBy: 'popularity.desc',
        language: 'en',
        type: 'movies'
      }
    })
    
    if (response.success && response.data) {
      // Append new results (limit to 12 per page)
      const newResults = response.data.results.slice(0, 12)
      discoverMovies.value.push(...newResults)
    }
  } catch (error) {
    console.error('Error loading more movies:', error)
  }
}

const loadMoreTv = async () => {
  if (tvPage.value >= tvTotalPages.value) return
  tvPage.value++
  
  try {
    const response = await $fetch('/api/overseerr-discover', {
      query: {
        page: tvPage.value,
        sortBy: 'popularity.desc',
        language: 'en',
        type: 'tv'
      }
    })
    
    if (response.success && response.data) {
      // Append new results (limit to 12 per page)
      const newResults = response.data.results.slice(0, 12)
      discoverTv.value.push(...newResults)
    }
  } catch (error) {
    console.error('Error loading more TV shows:', error)
  }
}

// Modal state
const isModalOpen = ref(false)
const selectedMedia = ref(null)

const openModal = (media: any) => {
  selectedMedia.value = media
  isModalOpen.value = true
}

const closeModal = () => {
  isModalOpen.value = false
  selectedMedia.value = null
}

const isAvailable = (media: any) => {
  // Available if mediaInfo exists and status is 5
  return media.mediaInfo && media.mediaInfo.status === 5
}

const isInDatabase = (media: any) => {
  // In database if mediaInfo exists (regardless of status)
  return !!media.mediaInfo
}

const canRequest = (media: any) => {
  // Can request if not in database and not already requested
  return !isInDatabase(media) && !hasBeenRequested(media)
}

// Cache for database links
const databaseLinks = ref<Map<number, string>>(new Map())

const getDatabaseLink = (media: any) => {
  // Return cached link if available
  if (databaseLinks.value.has(media.id)) {
    return databaseLinks.value.get(media.id)
  }
  
  // If not in database, return null
  if (!media.mediaInfo || !media.mediaInfo.id) {
    return null
  }
  
  // For now, return null - we'll fetch it when needed
  return null
}

// Fetch the database link for a media item
const fetchDatabaseLink = async (media: any) => {
  if (!media.mediaInfo) return null
  
  // Check cache first
  if (databaseLinks.value.has(media.id)) {
    return databaseLinks.value.get(media.id)
  }
  
  try {
    // Use tmdb_id to get the unified_media id from database
    const response = await $fetch('/api/media-check', {
      query: {
        tmdbId: media.id,
        mediaType: media.mediaType
      }
    })
    
    if (response.success && response.exists && response.data?.id) {
      const link = `/processed-media?mediaId=${response.data.id}`
      databaseLinks.value.set(media.id, link)
      return link
    }
    
    return null
  } catch (error) {
    console.error('Error fetching database link:', error)
    return null
  }
}

const requestedMedia = ref<Set<number>>(new Set())

const handleRequest = async (mediaId: number, mediaType: string, seasons?: number[]) => {
  console.log('Requesting media:', mediaId, mediaType, seasons)
  
  try {
    const response = await $fetch('/api/overseerr-request', {
      method: 'POST',
      body: {
        mediaId,
        mediaType,
        is4k: false,
        seasons
      }
    })
    
    if (response.success) {
      // Mark as requested
      requestedMedia.value.add(mediaId)
      
      // Show success notification
      toast.success(
        `${mediaType === 'tv' ? 'TV show' : 'Movie'} request submitted successfully`,
        'Request Submitted'
      )
      
      // Close modal if open
      if (isModalOpen.value && selectedMedia.value?.id === mediaId) {
        closeModal()
      }
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
  }
}

const hasBeenRequested = (media: any) => {
  return requestedMedia.value.has(media.id)
}

const handleViewDetails = async (media: any) => {
  const link = await fetchDatabaseLink(media)
  if (link) {
    navigateTo(link)
  }
}

const handleQuickRequestClick = async (media: any) => {
  // For TV shows, open modal to select seasons
  if (media.mediaType === 'tv') {
    openModal(media)
  } else {
    // For movies, quick request
    await handleRequest(media.id, media.mediaType)
  }
}

const handleQuickRequest = async (media: any) => {
  await handleRequest(media.id, media.mediaType)
}

const handleSearch = async () => {
  if (!hasQuery.value || isSearching.value) return
  
  isSearching.value = true
  await searchState.searchMedia(searchQuery.value)
  console.log('Search completed. Results:', searchState.results)
  console.log('Results length:', resultsLength.value)
  isSearching.value = false
}

const getPosterUrl = (posterPath?: string | null) => {
  if (!posterPath) return ''
  return `https://image.tmdb.org/t/p/w500${posterPath}`
}

const getMediaTitle = (media: any) => {
  if (media.mediaType === 'movie') {
    return media.title || media.originalTitle || 'Unknown Movie'
  } else if (media.mediaType === 'tv') {
    return media.name || media.originalName || 'Unknown Show'
  }
  return 'Unknown'
}

const getMediaYear = (media: any) => {
  if (media.mediaType === 'movie' && media.releaseDate) {
    return media.releaseDate.split('-')[0]
  } else if (media.mediaType === 'tv' && media.firstAirDate) {
    return media.firstAirDate.split('-')[0]
  }
  return ''
}

const getMediaTypeLabel = (media: any) => {
  if (media.mediaType === 'movie') return 'Movie'
  if (media.mediaType === 'tv') return 'TV Show'
  if (media.mediaType === 'person') return 'Person'
  return 'Unknown'
}

const formatVoteAverage = (voteAverage?: number) => {
  if (!voteAverage) return 'N/A'
  return voteAverage.toFixed(1)
}

const hasRequests = (media: any) => {
  return media.mediaInfo?.requests && media.mediaInfo.requests.length > 0
}

function debounce(fn: Function, delay: number) {
  let timeout: NodeJS.Timeout
  return function(...args: any[]) {
    clearTimeout(timeout)
    timeout = setTimeout(() => fn.apply(null, args), delay)
  }
}

// Set page metadata
useHead({
  title: 'Search Media - Darth Vadarr'
})
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateY(100%);
}

.toast-leave-to {
  opacity: 0;
  transform: translateY(100%);
}
</style>

