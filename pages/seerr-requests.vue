<template>
  <div class="space-y-4 sm:space-y-6 lg:space-y-8">
    <!-- Header - Always visible -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-4">
      <div>
        <h1 class="text-2xl sm:text-3xl font-bold text-foreground tracking-tight">Seerr Requests</h1>
        <p class="text-xs sm:text-sm text-muted-foreground mt-1">View and manage all requests from Overseerr</p>
      </div>
      
      <div class="flex items-center gap-2 sm:gap-3 flex-wrap">
        <div class="relative flex-1 sm:flex-none min-w-0">
          <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <AppIcon icon="lucide:search" size="16" class="sm:w-[18px] sm:h-[18px] text-muted-foreground" />
          </div>
          <input
            v-model="searchQuery"
            @input="debouncedSearch"
            type="text"
            placeholder="Search requests..."
            class="w-full sm:w-64 lg:w-72 pl-9 sm:pl-10 pr-3 sm:pr-4 py-2 sm:py-2.5 bg-background border border-input rounded-xl text-xs sm:text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        
        <!-- Filter Toggle -->
        <Button 
          @click="showFilters = !showFilters" 
          variant="outline"
          size="sm"
          class="gap-1.5 sm:gap-2"
        >
          <AppIcon icon="lucide:filter" size="16" class="sm:w-[18px] sm:h-[18px]" />
          <span class="hidden sm:inline">Filters</span>
          <span v-if="activeFiltersCount > 0" class="ml-0.5 sm:ml-1 inline-flex items-center justify-center min-w-[1.25rem] sm:min-w-[1.5rem] h-5 sm:h-6 px-1.5 sm:px-2 text-[10px] sm:text-xs font-medium text-white bg-primary rounded-full">
            {{ activeFiltersCount }}
          </span>
        </Button>
        
        <Button 
          @click="refreshData" 
          :disabled="isLoading"
          variant="outline"
          size="sm"
        >
          <AppIcon v-if="isLoading" icon="lucide:loader-2" size="16" class="sm:w-[18px] sm:h-[18px] animate-spin" />
          <AppIcon v-else icon="lucide:refresh-cw" size="16" class="sm:w-[18px] sm:h-[18px]" />
        </Button>
      </div>
    </div>
    
    <!-- Filters Panel -->
    <div v-if="showFilters" class="bg-card border border-border rounded-xl sm:rounded-2xl p-4 sm:p-6">
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <!-- Media Type Filter -->
        <div>
          <label class="text-xs sm:text-sm font-medium text-foreground mb-2 block">Media Type</label>
          <select
            v-model="filters.mediaType"
            @change="applyFilters"
            class="w-full px-3 py-2 bg-background border border-input rounded-lg text-xs sm:text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option value="">All</option>
            <option value="movie">Movie</option>
            <option value="tv">TV Show</option>
          </select>
        </div>
        
        <!-- Status Filter -->
        <div>
          <label class="text-xs sm:text-sm font-medium text-foreground mb-2 block">Request Status</label>
          <select
            v-model="filters.status"
            @change="applyFilters"
            class="w-full px-3 py-2 bg-background border border-input rounded-lg text-xs sm:text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option value="">All</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="processing">Processing</option>
            <option value="failed">Failed</option>
            <option value="available">Available</option>
            <option value="unavailable">Unavailable</option>
            <option value="deleted">Deleted</option>
          </select>
        </div>
      </div>
    </div>
    
    <!-- Bulk Action Toolbar -->
    <div v-if="selectedRequestIds.size > 0" class="bg-card border border-border rounded-xl sm:rounded-2xl p-4 sm:p-6">
      <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-4">
        <div class="flex items-center gap-2 sm:gap-3">
          <span class="text-sm sm:text-base font-semibold text-foreground">
            {{ selectedRequestIds.size }} request{{ selectedRequestIds.size !== 1 ? 's' : '' }} selected
          </span>
          <Button
            @click="clearSelection"
            variant="ghost"
            size="sm"
            class="text-xs sm:text-sm"
          >
            Clear
          </Button>
        </div>
        <div class="flex items-center gap-2 sm:gap-3 flex-wrap">
          <Button
            @click="showBulkRetriggerConfirmation = true"
            :disabled="bulkRetriggering"
            variant="outline"
            size="sm"
            class="gap-1.5 sm:gap-2"
          >
            <AppIcon 
              v-if="bulkRetriggering"
              icon="lucide:loader-2" 
              size="14" 
              class="sm:w-4 sm:h-4 animate-spin"
            />
            <AppIcon 
              v-else
              icon="lucide:refresh-cw" 
              size="14" 
              class="sm:w-4 sm:h-4"
            />
            <span class="hidden sm:inline">Retrigger</span>
            <span class="sm:hidden">Retrigger</span>
          </Button>
          <Button
            @click="showBulkDeleteConfirmation = true"
            :disabled="bulkDeleting"
            variant="outline"
            size="sm"
            class="gap-1.5 sm:gap-2 text-red-400 border-red-500/30 hover:bg-red-500/10"
          >
            <AppIcon 
              v-if="bulkDeleting"
              icon="lucide:loader-2" 
              size="14" 
              class="sm:w-4 sm:h-4 animate-spin"
            />
            <AppIcon 
              v-else
              icon="lucide:trash-2" 
              size="14" 
              class="sm:w-4 sm:h-4"
            />
            <span class="hidden sm:inline">Delete</span>
            <span class="sm:hidden">Delete</span>
          </Button>
        </div>
      </div>
    </div>
    
    <!-- Stats - Always visible -->
    <div class="bg-card border border-border rounded-xl sm:rounded-2xl p-4 sm:p-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg sm:text-xl font-semibold text-foreground">Request Statistics</h2>
        <div v-if="requestItems.length > 0" class="flex items-center gap-2">
          <label class="flex items-center gap-2 cursor-pointer text-xs sm:text-sm text-muted-foreground hover:text-foreground transition-colors">
            <input
              type="checkbox"
              :checked="allSelected"
              @change="toggleSelectAll"
              class="w-4 h-4 rounded border-input text-primary focus:ring-2 focus:ring-ring"
            />
            <span>Select All</span>
          </label>
        </div>
      </div>
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <div class="bg-background border border-border rounded-xl p-4">
          <p class="text-2xl sm:text-3xl font-bold text-foreground">{{ formatNumber(stats.total_requests || 0) }}</p>
          <p class="text-xs text-muted-foreground">Total Requests</p>
        </div>
        <div class="bg-background border border-border rounded-xl p-4">
          <p class="text-2xl sm:text-3xl font-bold text-foreground">{{ formatNumber(stats.pending_count || 0) }}</p>
          <p class="text-xs text-muted-foreground">Pending</p>
        </div>
        <div class="bg-background border border-border rounded-xl p-4">
          <p class="text-2xl sm:text-3xl font-bold text-foreground">{{ formatNumber(stats.approved_count || 0) }}</p>
          <p class="text-xs text-muted-foreground">Approved</p>
        </div>
        <div class="bg-background border border-border rounded-xl p-4">
          <p class="text-2xl sm:text-3xl font-bold text-foreground">{{ formatNumber(stats.available_count || 0) }}</p>
          <p class="text-xs text-muted-foreground">Available</p>
        </div>
      </div>
    </div>
    
    <!-- Error Banner -->
    <div v-if="errorMessage" class="bg-red-500/10 border border-red-500/20 rounded-xl p-4">
      <div class="flex items-center justify-between gap-4">
        <div class="flex items-center gap-3">
          <AppIcon icon="lucide:alert-circle" size="20" class="text-red-500" />
          <div>
            <p class="text-sm font-semibold text-foreground">Error loading requests</p>
            <p class="text-xs text-muted-foreground">{{ errorMessage }}</p>
          </div>
        </div>
        <Button @click="refreshData" size="sm" variant="outline">Retry</Button>
      </div>
    </div>
    
    <!-- MAIN CONTENT - Guaranteed to always render something -->
    <div>
      <!-- Show items if we have them -->
      <div v-if="requestItems.length > 0" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-2 sm:gap-3">
        <div
          v-for="(request, index) in requestItems"
          :key="`request-${request.id}-${index}`"
          @click="handleCardClick(request, $event)"
          class="group relative glass-card-enhanced overflow-hidden cursor-pointer transition-all duration-300 hover:scale-[1.02] hover:shadow-xl rounded-2xl h-full flex flex-col"
        >
          <!-- Selection Checkbox -->
          <div 
            class="absolute top-2 left-2 z-30 selection-checkbox"
            @click.stop="toggleRequestSelection(request.id || request.request_id)"
          >
            <div 
              class="w-5 h-5 sm:w-6 sm:h-6 rounded-lg backdrop-blur-xl shadow-xl border-2 transition-all duration-300 flex items-center justify-center cursor-pointer"
              :class="selectedRequestIds.has(request.id || request.request_id)
                ? 'bg-primary border-primary hover:bg-primary/90' 
                : 'bg-background/90 border-border hover:border-primary/50 hover:bg-background'"
            >
              <AppIcon 
                v-if="selectedRequestIds.has(request.id || request.request_id)"
                icon="lucide:check" 
                size="12" 
                class="sm:w-3.5 sm:h-3.5 text-white drop-shadow-lg" 
              />
              <AppIcon 
                v-else
                icon="lucide:square" 
                size="10" 
                class="sm:w-2.5 sm:h-2.5 text-muted-foreground" 
              />
            </div>
          </div>
          
          <!-- Poster -->
          <div class="relative flex-1 bg-gradient-to-br from-muted via-muted/80 to-muted/60 overflow-hidden rounded-t-2xl">
            <img
              v-if="getPosterUrl(request)"
              :src="getPosterUrl(request)"
              :alt="request.media?.title || 'Media poster'"
              class="w-full h-full object-cover transition-all duration-300 group-hover:scale-110"
              @error="handleImageError"
              loading="lazy"
            />
            <div v-else class="w-full h-full flex items-center justify-center p-6 bg-gradient-to-br from-primary/10 to-muted/50">
              <AppIcon 
                :icon="request.media?.media_type === 'movie' ? 'lucide:film' : 'lucide:tv'" 
                size="32" 
                class="text-primary" 
              />
            </div>
            
            <!-- Unified Status and Media Type Badge Container -->
            <div class="absolute top-2 right-2 z-10 flex items-center gap-2">
              <!-- Status Badge with DarthVadarr Icon -->
              <div :class="getStatusBadgeClass(request)" class="status-badge-enhanced w-8 h-8 rounded-xl backdrop-blur-xl shadow-xl flex items-center justify-center border-2 transition-all duration-300 group-hover:scale-110 group-hover:shadow-lg flex-shrink-0">
                <img 
                  src="/vadarr-icon-white.svg" 
                  alt="Status" 
                  class="w-5 h-5 drop-shadow-lg"
                />
              </div>
              
              <!-- Media Type Badge -->
              <span 
                v-if="request.media?.media_type"
                class="media-type-badge px-2 py-1 text-[10px] font-bold rounded-full backdrop-blur-xl shadow-xl border-2 transition-all duration-300 group-hover:scale-105"
                :class="request.media.media_type === 'movie' ? 'media-type-movie' : 'media-type-tv'"
              >
                {{ request.media.media_type.toUpperCase() }}
              </span>
            </div>
          </div>
          
          <!-- Info -->
          <div class="p-3 sm:p-4 space-y-2 bg-card flex-shrink-0 rounded-b-2xl">
            <!-- Title - Always shown -->
            <h3 class="text-xs sm:text-sm font-bold text-foreground line-clamp-2" :title="request.media?.title || 'Unknown Title'">
              {{ request.media?.title || 'Unknown Title' }}
            </h3>
            
            <!-- Year and Status Row -->
            <div class="flex items-center justify-between gap-2">
              <p class="text-[10px] sm:text-xs text-muted-foreground">
                {{ getMediaYear(request) || 'N/A' }}
              </p>
              <span :class="getStatusLabelClass(request)" class="px-2 py-0.5 text-[10px] sm:text-xs font-semibold rounded-full">
                {{ request.status_label || 'Unknown' }}
              </span>
            </div>
            
            <!-- Rating and Runtime Row -->
            <div class="flex items-center gap-3 text-[10px] sm:text-xs text-muted-foreground">
              <div v-if="request.media?.vote_average" class="flex items-center gap-1">
                <AppIcon icon="lucide:star" size="12" class="text-amber-400 fill-amber-400" />
                <span>{{ formatVoteAverage(request.media.vote_average) }}</span>
              </div>
              <div v-if="request.media?.runtime && request.media.media_type === 'movie'" class="flex items-center gap-1">
                <AppIcon icon="lucide:clock" size="12" />
                <span>{{ request.media.runtime }}m</span>
              </div>
            </div>
            
            <!-- TV Show Season Info -->
            <div v-if="request.media?.media_type === 'tv' && (request.season_count > 0 || request.all_seasons?.length)" class="flex items-center gap-1.5 text-[10px] sm:text-xs text-muted-foreground">
              <AppIcon icon="lucide:tv" size="12" />
              <span>
                {{ request.all_seasons?.length || request.season_count || 0 }} Season{{ (request.all_seasons?.length || request.season_count || 0) !== 1 ? 's' : '' }}
                <span v-if="request.media?.number_of_episodes" class="ml-1">
                  ({{ request.media.number_of_episodes }} Episodes)
                </span>
              </span>
            </div>
            
            <!-- Genres (if available) -->
            <div v-if="request.media?.genres && request.media.genres.length > 0" class="flex items-center gap-1 flex-wrap">
              <AppIcon icon="lucide:tag" size="10" class="text-muted-foreground flex-shrink-0" />
              <span class="text-[9px] sm:text-[10px] text-muted-foreground line-clamp-1">
                {{ request.media.genres.slice(0, 2).map((g: any) => g.name || g).join(', ') }}
                <span v-if="request.media.genres.length > 2">...</span>
              </span>
            </div>
            
            <!-- Request Date -->
            <div class="flex items-center gap-1.5 text-[10px] sm:text-xs text-muted-foreground">
              <AppIcon icon="lucide:calendar" size="12" />
              <span>{{ formatDate(request.created_at) }}</span>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Loading State -->
      <div v-else-if="isLoading" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-2 sm:gap-3">
        <div
          v-for="i in 12"
          :key="`skeleton-${i}`"
          class="skeleton-card glass-card-enhanced overflow-hidden animate-pulse h-full flex flex-col rounded-2xl"
        >
          <div class="relative flex-1 bg-gradient-to-br from-muted via-muted/80 to-muted/60 rounded-t-2xl"></div>
          <div class="p-3 sm:p-4 space-y-2 flex-shrink-0 rounded-b-2xl">
            <div class="h-4 bg-muted rounded-lg w-3/4"></div>
            <div class="h-3 bg-muted rounded-lg w-1/2"></div>
          </div>
        </div>
      </div>
      
      <!-- Error State -->
      <div v-else-if="errorMessage" class="text-center py-24">
        <div class="inline-flex w-24 h-24 mb-6 bg-red-500/10 rounded-3xl items-center justify-center">
          <AppIcon icon="lucide:alert-circle" size="48" class="text-red-500" />
        </div>
        <h3 class="text-2xl font-bold text-foreground mb-3">Failed to Load Requests</h3>
        <p class="text-muted-foreground mb-8 max-w-md mx-auto">{{ errorMessage }}</p>
        <Button @click="refreshData" class="gap-2">
          <AppIcon icon="lucide:refresh-cw" size="18" />
          Retry
        </Button>
      </div>
      
      <!-- Empty State -->
      <div v-else class="text-center py-24">
        <div class="inline-flex w-24 h-24 mb-6 bg-muted rounded-3xl items-center justify-center">
          <AppIcon icon="lucide:inbox" size="48" class="text-muted-foreground" />
        </div>
        <h3 class="text-2xl font-bold text-foreground mb-3">No requests found</h3>
        <p class="text-muted-foreground mb-8 max-w-md mx-auto">
          {{ searchQuery ? 'Try adjusting your search' : 'No requests found in Overseerr' }}
        </p>
      </div>
    </div>
    
    <!-- Load More -->
    <div v-if="hasMore && !isLoading && requestItems.length > 0" class="flex justify-center mt-12">
      <Button @click="loadMore" variant="outline" class="gap-2" :disabled="isLoadingMore">
        <AppIcon v-if="isLoadingMore" icon="lucide:loader-2" size="18" class="animate-spin" />
        <AppIcon v-else icon="lucide:download" size="18" />
        {{ isLoadingMore ? 'Loading...' : 'Load More' }}
      </Button>
    </div>
    
    <!-- Request Details Modal -->
    <RequestDetailsModal
      :request="selectedRequest"
      :is-open="showDetailsModal"
      @close="closeDetailsModal"
      @delete="handleDeleteRequest"
      @retrigger="handleRetriggerRequest"
    />
    
    <!-- Bulk Delete Confirmation Modal -->
    <div v-if="showBulkDeleteConfirmation" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm" @click="showBulkDeleteConfirmation = false">
      <div class="bg-card border border-border rounded-xl p-6 max-w-md w-full" @click.stop>
        <h3 class="text-lg font-bold text-foreground mb-2">Delete Requests</h3>
        <p class="text-sm text-muted-foreground mb-4">
          Are you sure you want to delete {{ selectedRequestIds.size }} request{{ selectedRequestIds.size !== 1 ? 's' : '' }}? This action cannot be undone.
        </p>
        <div class="flex gap-3 justify-end">
          <Button @click="showBulkDeleteConfirmation = false" variant="outline" size="sm">Cancel</Button>
          <Button @click="confirmBulkDelete" :disabled="bulkDeleting" variant="destructive" size="sm" class="gap-2">
            <AppIcon v-if="bulkDeleting" icon="lucide:loader-2" size="14" class="animate-spin" />
            <AppIcon v-else icon="lucide:trash-2" size="14" />
            Delete
          </Button>
        </div>
      </div>
    </div>
    
    <!-- Bulk Retrigger Confirmation Modal -->
    <div v-if="showBulkRetriggerConfirmation" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm" @click="showBulkRetriggerConfirmation = false">
      <div class="bg-card border border-border rounded-xl p-6 max-w-md w-full" @click.stop>
        <h3 class="text-lg font-bold text-foreground mb-2">Retrigger Requests</h3>
        <p class="text-sm text-muted-foreground mb-4">
          Are you sure you want to re-trigger {{ selectedRequestIds.size }} request{{ selectedRequestIds.size !== 1 ? 's' : '' }}? This will update the requests and trigger processing again.
        </p>
        <div class="flex gap-3 justify-end">
          <Button @click="showBulkRetriggerConfirmation = false" variant="outline" size="sm">Cancel</Button>
          <Button @click="confirmBulkRetrigger" :disabled="bulkRetriggering" variant="outline" size="sm" class="gap-2">
            <AppIcon v-if="bulkRetriggering" icon="lucide:loader-2" size="14" class="animate-spin" />
            <AppIcon v-else icon="lucide:refresh-cw" size="14" />
            Retrigger
          </Button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useDebounceFn } from '@vueuse/core'
import RequestDetailsModal from '~/components/RequestDetailsModal.vue'
import Button from '~/components/ui/Button.vue'
import { useToast } from '~/composables/useToast'

const { toast } = useToast()

interface RequestItem {
  id: number
  request_id: number
  status: number
  status_label: string
  media_status: number
  media_status_label: string
  created_at: string
  updated_at: string
  requested_by?: {
    id: number
    email: string
    username: string
    displayName: string
  }
  media?: {
    id: number
    media_type: 'movie' | 'tv'
    tmdb_id: number
    tvdb_id?: number
    title: string
    original_title?: string
    year?: number
    release_date?: string
    first_air_date?: string
    last_air_date?: string
    poster_path?: string
    backdrop_path?: string
    overview?: string
    status: number
    status4k?: number
    vote_average?: number
    vote_count?: number
    popularity?: number
    runtime?: number
    episode_runtime?: number
    genres?: Array<{ id: number; name: string }>
    production_companies?: Array<{ id: number; name: string; logo_path?: string }>
    networks?: Array<{ id: number; name: string; logo_path?: string }>
    certification?: string
    content_rating?: string
    tagline?: string
    homepage?: string
    original_language?: string
    media_status?: string
    // TV show specific fields
    all_seasons?: Array<{
      id: number
      seasonNumber: number
      name: string
      overview?: string
      episodeCount: number
      airDate?: string
      posterPath?: string
    }>
    number_of_seasons?: number
    number_of_episodes?: number
  }
  seasons?: any[]
  season_count: number
  all_seasons?: Array<{
    id: number
    seasonNumber: number
    name: string
    overview?: string
    episodeCount: number
    airDate?: string
    posterPath?: string
  }>
  aggregated_request_ids: number[]
  is4k: boolean
  has_unified_media: boolean
  unified_media?: any
}

interface RequestStats {
  total_requests: number
  total_movies: number
  total_tv_shows: number
  pending_count: number
  approved_count: number
  processing_count: number
  failed_count: number
  available_count: number
  unavailable_count: number
  deleted_count: number
  movies_pending: number
  movies_approved: number
  movies_processing: number
  movies_failed: number
  movies_available: number
  movies_unavailable: number
  movies_deleted: number
  tv_pending: number
  tv_approved: number
  tv_processing: number
  tv_failed: number
  tv_available: number
  tv_unavailable: number
  tv_deleted: number
}

useHead({
  title: 'Seerr Requests - SeerrBridge',
  description: 'View and manage all requests from Overseerr'
})

// Simple state
const isLoading = ref(false)
const isLoadingMore = ref(false)
const requestItems = ref<RequestItem[]>([])
const errorMessage = ref<string | null>(null)
const stats = ref<RequestStats>({
  total_requests: 0,
  total_movies: 0,
  total_tv_shows: 0,
  pending_count: 0,
  approved_count: 0,
  processing_count: 0,
  failed_count: 0,
  available_count: 0,
  unavailable_count: 0,
  deleted_count: 0,
  movies_pending: 0,
  movies_approved: 0,
  movies_processing: 0,
  movies_failed: 0,
  movies_available: 0,
  movies_unavailable: 0,
  movies_deleted: 0,
  tv_pending: 0,
  tv_approved: 0,
  tv_processing: 0,
  tv_failed: 0,
  tv_available: 0,
  tv_unavailable: 0,
  tv_deleted: 0
})

const currentPage = ref(1)
const hasMore = ref(true)
const searchQuery = ref('')

// Filter state
const showFilters = ref(false)
const filters = ref({
  mediaType: '',
  status: ''
})

// Selection state
const selectedRequestIds = ref<Set<number>>(new Set())

// Modal state
const showDetailsModal = ref(false)
const selectedRequest = ref<RequestItem | null>(null)

// Bulk action state
const bulkDeleting = ref(false)
const bulkRetriggering = ref(false)
const showBulkDeleteConfirmation = ref(false)
const showBulkRetriggerConfirmation = ref(false)

// Computed
const activeFiltersCount = computed(() => {
  let count = 0
  if (filters.value.mediaType) count++
  if (filters.value.status) count++
  return count
})

const debouncedSearch = useDebounceFn(() => {
  currentPage.value = 1
  requestItems.value = []
  errorMessage.value = null
  loadRequests()
}, 500)

const applyFilters = () => {
  currentPage.value = 1
  requestItems.value = []
  errorMessage.value = null
  loadRequests()
}

// Utility functions
const formatNumber = (num: number) => {
  return new Intl.NumberFormat().format(num)
}

const getStatusBadgeClass = (request: RequestItem) => {
  switch (request.status) {
    case 1: return 'bg-yellow-600/90 border-yellow-500/50'
    case 2: return 'bg-blue-600/90 border-blue-500/50'
    case 3: return 'bg-purple-600/90 border-purple-500/50'
    case 4: return 'bg-red-600/90 border-red-500/50'
    case 5: return 'bg-emerald-600/90 border-emerald-500/50'
    case -1: return 'bg-gray-600/90 border-gray-500/50'
    case -2: return 'bg-gray-700/90 border-gray-600/50'
    default: return 'bg-gray-600/90 border-gray-500/50'
  }
}

const getStatusIcon = (request: RequestItem) => {
  switch (request.status) {
    case 1: return 'lucide:clock'
    case 2: return 'lucide:check-circle-2'
    case 3: return 'lucide:loader-2'
    case 4: return 'lucide:x-circle'
    case 5: return 'lucide:check-circle'
    case -1: return 'lucide:ban'
    case -2: return 'lucide:trash-2'
    default: return 'lucide:help-circle'
  }
}

const getStatusLabelClass = (request: RequestItem) => {
  switch (request.status) {
    case 1: return 'bg-yellow-500/20 text-yellow-600 dark:text-yellow-400'
    case 2: return 'bg-blue-500/20 text-blue-600 dark:text-blue-400'
    case 3: return 'bg-purple-500/20 text-purple-600 dark:text-purple-400'
    case 4: return 'bg-red-500/20 text-red-600 dark:text-red-400'
    case 5: return 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-400'
    case -1: return 'bg-gray-500/20 text-gray-600 dark:text-gray-400'
    case -2: return 'bg-gray-600/20 text-gray-700 dark:text-gray-500'
    default: return 'bg-gray-500/20 text-gray-600 dark:text-gray-400'
  }
}

const getPosterUrl = (request: RequestItem) => {
  // Handle both camelCase (from Overseerr) and snake_case (from transformation)
  const posterPath = request.media?.poster_path || (request.media as any)?.posterPath
  if (!posterPath) return null
  
  // If it's already a full URL, return it as-is
  if (posterPath.startsWith('http')) {
    return posterPath
  }
  
  // Construct TMDB URL exactly like the search page does
  // Overseerr returns paths like "/abc123.jpg" (with leading slash)
  return `https://image.tmdb.org/t/p/w500${posterPath}`
}

const getMediaYear = (request: RequestItem) => {
  if (request.media?.release_date) {
    return new Date(request.media.release_date).getFullYear()
  }
  if (request.media?.first_air_date) {
    return new Date(request.media.first_air_date).getFullYear()
  }
  return null
}

const formatDate = (dateString: string) => {
  if (!dateString) return 'Never'
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', { 
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}

const formatVoteAverage = (voteAverage?: number) => {
  if (!voteAverage) return 'N/A'
  return voteAverage.toFixed(1)
}

const handleImageError = (event: Event) => {
  const img = event.target as HTMLImageElement
  img.style.display = 'none'
}

// Selection functions
const toggleRequestSelection = (requestId: number) => {
  if (selectedRequestIds.value.has(requestId)) {
    selectedRequestIds.value.delete(requestId)
  } else {
    selectedRequestIds.value.add(requestId)
  }
}

const toggleSelectAll = () => {
  if (allSelected.value) {
    requestItems.value.forEach(item => {
      selectedRequestIds.value.delete(item.id || item.request_id)
    })
  } else {
    requestItems.value.forEach(item => {
      selectedRequestIds.value.add(item.id || item.request_id)
    })
  }
}

const clearSelection = () => {
  selectedRequestIds.value.clear()
}

const allSelected = computed(() => {
  if (requestItems.value.length === 0) return false
  return requestItems.value.every(item => 
    selectedRequestIds.value.has(item.id || item.request_id)
  )
})

const handleCardClick = (request: RequestItem, event: MouseEvent) => {
  // Don't open modal if clicking on checkbox
  if ((event.target as HTMLElement).closest('.selection-checkbox')) {
    return
  }
  openDetails(request)
}

const openDetails = (request: RequestItem) => {
  selectedRequest.value = request
  showDetailsModal.value = true
}

const closeDetailsModal = () => {
  showDetailsModal.value = false
  selectedRequest.value = null
}

// Data loading - SIMPLE
const loadRequests = async (page = 1, append = false) => {
  console.log(`[SeerrRequests] Loading page ${page}, append: ${append}`)
  
  if (page === 1) {
    isLoading.value = true
    errorMessage.value = null
  } else {
    isLoadingMore.value = true
  }
  
  try {
    const params = new URLSearchParams({
      page: page.toString(),
      limit: '20'
    })
    
    if (searchQuery.value) {
      params.append('search', searchQuery.value)
    }
    
    if (filters.value.mediaType) {
      params.append('mediaType', filters.value.mediaType)
    }
    
    if (filters.value.status) {
      params.append('status', filters.value.status)
    }
    
    console.log(`[SeerrRequests] Fetching: /api/seerr-requests?${params.toString()}`)
    const response = await $fetch(`/api/seerr-requests?${params.toString()}`)
    
    console.log(`[SeerrRequests] Response:`, { 
      success: response?.success, 
      count: response?.data?.requests?.length || 0 
    })
    
    if (response?.success && response.data) {
      const newItems = Array.isArray(response.data.requests) ? response.data.requests : []
      
      if (append) {
        requestItems.value = [...requestItems.value, ...newItems]
      } else {
        requestItems.value = newItems
        if (response.data.stats) {
          stats.value = response.data.stats
        }
      }
      
      if (response.data.pagination) {
        hasMore.value = response.data.pagination.has_next || false
      }
      
      errorMessage.value = null
    } else {
      errorMessage.value = response?.error || 'Failed to load requests'
      if (!append) {
        requestItems.value = []
      }
    }
  } catch (err: any) {
    const errorMsg = err.message || 'Failed to load requests'
    errorMessage.value = errorMsg
    if (!append) {
      requestItems.value = []
    }
    console.error(`[SeerrRequests] Error:`, err)
  } finally {
    isLoading.value = false
    isLoadingMore.value = false
    console.log(`[SeerrRequests] Done. Items: ${requestItems.value.length}`)
  }
}

const loadMore = () => {
  if (!hasMore.value || isLoadingMore.value) return
  currentPage.value++
  loadRequests(currentPage.value, true)
}

const refreshData = () => {
  currentPage.value = 1
  requestItems.value = []
  hasMore.value = true
  errorMessage.value = null
  loadRequests()
}

// Delete and retrigger handlers
const handleDeleteRequest = async (requestId: number) => {
  try {
    await $fetch(`/api/seerr-requests/${requestId}/delete`, {
      method: 'DELETE'
    })
    
    toast.success('Request deleted successfully', 'Success')
    closeDetailsModal()
    await refreshData()
  } catch (error: any) {
    toast.error(error.message || 'Failed to delete request', 'Error')
  }
}

const handleRetriggerRequest = async (requestId: number) => {
  try {
    await $fetch(`/api/seerr-requests/${requestId}/retrigger`, {
      method: 'POST'
    })
    
    toast.success('Request retriggered successfully', 'Success')
    closeDetailsModal()
    await refreshData()
  } catch (error: any) {
    toast.error(error.message || 'Failed to retrigger request', 'Error')
  }
}

// Bulk actions
const confirmBulkDelete = async () => {
  if (selectedRequestIds.value.size === 0) return
  
  bulkDeleting.value = true
  showBulkDeleteConfirmation.value = false
  
  try {
    const requestIdsArray = Array.from(selectedRequestIds.value)
    const response = await $fetch('/api/seerr-requests-bulk-delete', {
      method: 'POST',
      body: {
        request_ids: requestIdsArray
      }
    })
    
    if (response && (response.status === 'completed' || response.status === 'partial')) {
      const results = response.results
      
      if (results.failed_count > 0) {
        toast.warning(
          `Deleted ${results.success_count} request(s), ${results.failed_count} failed`,
          'Partial Success'
        )
      } else {
        toast.success(`Successfully deleted ${results.success_count} request(s)`, 'Success')
      }
      
      clearSelection()
      await refreshData()
    }
  } catch (error: any) {
    toast.error(error.message || 'Failed to delete requests', 'Error')
  } finally {
    bulkDeleting.value = false
  }
}

const confirmBulkRetrigger = async () => {
  if (selectedRequestIds.value.size === 0) return
  
  bulkRetriggering.value = true
  showBulkRetriggerConfirmation.value = false
  
  try {
    const requestIdsArray = Array.from(selectedRequestIds.value)
    const response = await $fetch('/api/seerr-requests-bulk-retrigger', {
      method: 'POST',
      body: {
        request_ids: requestIdsArray
      }
    })
    
    if (response && (response.status === 'completed' || response.status === 'partial')) {
      const results = response.results
      
      if (results.failed_count > 0) {
        toast.warning(
          `Retriggered ${results.success_count} request(s), ${results.failed_count} failed`,
          'Partial Success'
        )
      } else {
        toast.success(`Successfully retriggered ${results.success_count} request(s)`, 'Success')
      }
      
      clearSelection()
      await refreshData()
    }
  } catch (error: any) {
    toast.error(error.message || 'Failed to retrigger requests', 'Error')
  } finally {
    bulkRetriggering.value = false
  }
}

onMounted(async () => {
  console.log('[SeerrRequests] Page mounted')
  await loadRequests()
})
</script>

<style scoped>
.glass-card-enhanced {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 4px 24px 0 rgba(31, 38, 135, 0.12);
  transition: all 0.3s ease;
}

.dark .glass-card-enhanced {
  background: rgba(0, 0, 0, 0.6);
  border: 1px solid rgba(130, 36, 227, 0.2);
}

.glass-card-enhanced:hover {
  border-color: rgba(130, 36, 227, 0.4);
  box-shadow: 0 12px 40px 0 rgba(130, 36, 227, 0.2);
  transform: translateY(-4px);
}

.skeleton-card {
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.dark .skeleton-card {
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(130, 36, 227, 0.15);
}

/* Enhanced Status Badge */
.status-badge-enhanced {
  box-shadow: 
    0 4px 20px rgba(0, 0, 0, 0.3),
    0 0 0 1px rgba(255, 255, 255, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

.status-badge-enhanced:hover {
  box-shadow: 
    0 6px 30px rgba(130, 36, 227, 0.5),
    0 0 0 1px rgba(255, 255, 255, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.3);
}

/* Media Type Badge */
.media-type-badge {
  box-shadow: 
    0 4px 15px rgba(0, 0, 0, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.3);
}

.media-type-movie {
  background: hsl(var(--info) / 0.2);
  color: hsl(var(--info));
  border-color: hsl(var(--info) / 0.3);
}

.dark .media-type-movie {
  background: hsl(var(--info) / 0.15);
  color: hsl(var(--info));
  border-color: hsl(var(--info) / 0.25);
}

.media-type-movie:hover {
  border-color: hsl(var(--info) / 0.5);
  background: hsl(var(--info) / 0.25);
}

.dark .media-type-movie:hover {
  border-color: hsl(var(--info) / 0.4);
  background: hsl(var(--info) / 0.2);
}

.media-type-tv {
  background: hsl(var(--success) / 0.2);
  color: hsl(var(--success));
  border-color: hsl(var(--success) / 0.3);
}

.dark .media-type-tv {
  background: hsl(var(--success) / 0.15);
  color: hsl(var(--success));
  border-color: hsl(var(--success) / 0.25);
}

.media-type-tv:hover {
  border-color: hsl(var(--success) / 0.5);
  background: hsl(var(--success) / 0.25);
}

.dark .media-type-tv:hover {
  border-color: hsl(var(--success) / 0.4);
  background: hsl(var(--success) / 0.2);
}

.selection-checkbox {
  transition: all 0.2s ease;
}

.selection-checkbox:hover {
  transform: scale(1.1);
}
</style>

