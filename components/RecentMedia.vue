<template>
  <Card class="h-full">
    <div class="flex items-center justify-between mb-6 flex-wrap gap-4">
      <div class="flex items-center space-x-3">
        <div class="w-10 h-10 sm:w-12 sm:h-12 bg-primary/10 rounded-lg sm:rounded-xl flex items-center justify-center group-hover:bg-primary/20 transition-colors">
          <AppIcon icon="lucide:film" size="20" class="sm:w-6 sm:h-6 text-primary" />
        </div>
        <div>
          <h2 class="text-xl font-semibold text-foreground">Recent Media</h2>
          <p class="text-sm text-muted-foreground">Latest processed items</p>
        </div>
      </div>
      
      <div class="flex items-center gap-3">
        <!-- View Toggle -->
        <div class="flex items-center gap-1 p-1 bg-muted rounded-lg">
          <button
            @click="viewMode = 'grid'"
            :class="[
              'p-1.5 rounded transition-colors',
              viewMode === 'grid' 
                ? 'bg-background text-primary shadow-sm' 
                : 'text-muted-foreground hover:text-foreground'
            ]"
            title="Grid View"
          >
            <AppIcon icon="lucide:grid-3x3" size="16" />
          </button>
          <button
            @click="viewMode = 'list'"
            :class="[
              'p-1.5 rounded transition-colors',
              viewMode === 'list' 
                ? 'bg-background text-primary shadow-sm' 
                : 'text-muted-foreground hover:text-foreground'
            ]"
            title="List View"
          >
            <AppIcon icon="lucide:list" size="16" />
          </button>
        </div>
        
        <NuxtLink to="/processed-media">
          <Button variant="ghost" size="sm" class="gap-1.5 sm:gap-2">
            <span>View All</span>
            <AppIcon icon="lucide:chevron-right" size="16" class="sm:w-[18px] sm:h-[18px]" />
          </Button>
        </NuxtLink>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="pending" class="space-y-4">
      <div v-if="viewMode === 'grid'" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-2 sm:gap-3">
        <div
          v-for="i in 8"
          :key="i"
          class="skeleton-card glass-card-enhanced overflow-hidden animate-pulse h-full flex flex-col rounded-2xl"
        >
          <div class="relative flex-1 bg-gradient-to-br from-muted via-muted/80 to-muted/60 rounded-t-2xl">
            <div class="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent animate-shimmer"></div>
          </div>
          <div class="p-3 sm:p-4 space-y-2 flex-shrink-0 rounded-b-2xl">
            <div class="h-4 bg-muted rounded-lg w-3/4"></div>
            <div class="h-3 bg-muted rounded-lg w-1/2"></div>
          </div>
        </div>
      </div>
      <div v-else class="space-y-3">
        <div v-for="i in 5" :key="i" class="flex items-center space-x-4 p-3 rounded-lg border border-border animate-pulse">
          <div class="w-12 h-16 bg-muted rounded"></div>
          <div class="flex-1 space-y-2">
            <div class="h-4 bg-muted rounded w-3/4"></div>
            <div class="h-3 bg-muted rounded w-1/2"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="text-center py-12">
      <AppIcon icon="lucide:alert-circle" size="48" class="mx-auto text-destructive mb-4" />
      <p class="text-destructive mb-2">Failed to load recent media</p>
      <Button @click="loadMore" variant="outline" size="sm" class="mt-4">
        <AppIcon icon="lucide:refresh-cw" size="18" class="mr-2" />
        Retry
      </Button>
    </div>

    <!-- Empty State -->
    <div v-else-if="!mediaItems || mediaItems.length === 0" class="text-center py-12">
      <div class="inline-flex w-12 h-12 sm:w-16 sm:h-16 bg-muted rounded-lg sm:rounded-xl items-center justify-center mb-4">
        <AppIcon icon="lucide:film" size="20" class="sm:w-6 sm:h-6 text-muted-foreground" />
      </div>
      <p class="text-muted-foreground">No media processed yet</p>
    </div>

    <!-- Grid View -->
    <div 
      v-else-if="viewMode === 'grid'"
      ref="scrollContainer"
      class="relative"
    >
      <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-2 sm:gap-3">
        <div
          v-for="(media, index) in mediaItems"
          :key="media.id"
          @click="viewMedia(media)"
          :style="{ animationDelay: `${index * 50}ms` }"
          class="media-card group relative glass-card-enhanced overflow-hidden cursor-pointer transition-all duration-500 ease-out hover:scale-[1.02] hover:shadow-2xl hover:shadow-primary/20 animate-fade-in-up rounded-2xl h-full flex flex-col"
        >
          <!-- Glow Effect on Hover -->
          <div class="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none z-0">
            <div class="absolute inset-0 bg-gradient-to-br from-primary/20 via-primary/10 to-transparent blur-2xl rounded-2xl"></div>
          </div>
          
          <!-- Poster Container -->
          <div class="relative flex-1 bg-gradient-to-br from-muted via-muted/80 to-muted/60 overflow-hidden rounded-t-2xl">
            <!-- Image with Gradient Overlay -->
            <div class="relative w-full h-full">
              <img
                v-if="getBestImageUrl(media)"
                :src="getBestImageUrl(media)"
                :alt="media.title"
                class="w-full h-full object-cover transition-all duration-700 group-hover:scale-110 group-hover:brightness-110"
                @error="handleImageError"
                loading="lazy"
              />
              
              <!-- Enhanced Placeholder with Gradient -->
              <div v-else class="w-full h-full flex items-center justify-center p-6 bg-gradient-to-br from-primary/10 via-primary/5 to-muted/50">
                <div class="text-center transform group-hover:scale-110 transition-transform duration-300">
                  <div class="w-16 h-16 mx-auto mb-3 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/10 backdrop-blur-sm flex items-center justify-center border border-primary/20 shadow-lg">
                    <AppIcon 
                      :icon="media.media_type === 'movie' ? 'lucide:film' : 'lucide:tv'" 
                      size="24" 
                      class="text-primary"
                    />
                  </div>
                  <p class="text-xs text-foreground font-semibold line-clamp-2 drop-shadow-sm">{{ media.title }}</p>
                </div>
              </div>
            </div>
            
            <!-- Animated Status Badge with Glow -->
            <div class="absolute top-3 right-3 z-20">
              <div 
                :class="getStatusIconClass(media)" 
                class="status-badge-enhanced w-8 h-8 sm:w-10 sm:h-10 rounded-2xl backdrop-blur-xl shadow-2xl flex items-center justify-center border-2 transition-all duration-300 group-hover:scale-110 group-hover:shadow-lg"
              >
                <img 
                  src="/vadarr-icon-white.svg" 
                  alt="Status" 
                  class="w-6 h-6 sm:w-8 sm:h-8 drop-shadow-lg"
                />
              </div>
            </div>
            
            <!-- Enhanced Media Type Badge -->
            <div class="absolute top-3 left-3 z-20">
              <span 
                class="media-type-badge px-3 py-1.5 text-[10px] sm:text-xs font-bold rounded-full backdrop-blur-xl shadow-xl border-2 transition-all duration-300 group-hover:scale-105"
                :class="media.media_type === 'movie' ? 'media-type-movie' : 'media-type-tv'"
              >
                {{ media.media_type.toUpperCase() }}
              </span>
            </div>
            
            <!-- Error Badge with Pulse Animation -->
            <div v-if="media.error_message && getDisplayStatus(media) !== 'completed'" class="absolute bottom-3 left-3 z-20">
              <div class="error-badge bg-red-500/40 backdrop-blur-xl shadow-xl flex items-center justify-center w-9 h-9 rounded-2xl border-2 border-red-500/40 transition-all duration-300 group-hover:scale-110 animate-pulse-soft">
                <AppIcon icon="lucide:alert-circle" size="16" class="text-red-400 drop-shadow-lg" />
              </div>
            </div>
            
            <!-- Enhanced Progress Ring for TV Shows -->
            <div v-if="media.media_type === 'tv' && media.progress_percentage > 0" class="absolute bottom-0 left-0 right-0 z-20 overflow-hidden">
              <div class="relative h-2 bg-black/60 backdrop-blur-sm overflow-hidden">
                <div 
                  class="h-full bg-gradient-to-r from-emerald-400 via-emerald-500 to-emerald-600 transition-all duration-700 shadow-lg shadow-emerald-500/50"
                  :style="{ width: `${media.progress_percentage}%` }"
                >
                  <div class="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer"></div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Enhanced Card Info with Glassmorphic Background -->
          <div class="relative p-3 sm:p-4 space-y-2 bg-gradient-to-b from-card/95 via-card/90 to-card backdrop-blur-sm flex-shrink-0 rounded-b-2xl">
            <!-- Title -->
            <h3 class="text-xs sm:text-sm font-bold text-foreground line-clamp-2 transition-all duration-300 group-hover:text-primary">
              {{ media.title }}
            </h3>
            
            <!-- Year and Rating Row -->
            <div class="flex items-center justify-between gap-2">
              <p class="text-[10px] sm:text-xs text-muted-foreground font-medium">
                {{ media.year || 'N/A' }}
              </p>
              <div v-if="media.rating" class="flex items-center gap-1 text-[10px] sm:text-xs bg-amber-500/20 px-2 py-0.5 rounded-full border border-amber-500/30">
                <AppIcon icon="lucide:star" size="12" class="text-amber-400 fill-amber-400" />
                <span class="font-bold text-amber-400">{{ media.rating }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Loading More Indicator -->
      <div v-if="loadingMore" class="flex justify-center py-8">
        <div class="flex items-center gap-2 text-muted-foreground">
          <AppIcon icon="lucide:loader-2" size="20" class="animate-spin" />
          <span class="text-sm">Loading more...</span>
        </div>
      </div>

      <!-- End of List Indicator -->
      <div v-if="hasMore === false && mediaItems.length > 0" class="text-center py-6">
        <p class="text-sm text-muted-foreground">No more items to load</p>
      </div>
    </div>

    <!-- List View -->
    <div
      v-else
      ref="scrollContainer"
      class="space-y-3 relative"
    >
      <div
        v-for="media in mediaItems"
        :key="media.id"
        @click="viewMedia(media)"
        class="flex items-center space-x-4 p-4 rounded-lg border border-border hover:bg-muted/50 transition-all duration-200 cursor-pointer group hover:shadow-md"
      >
        <div class="flex-shrink-0 relative">
          <div class="w-16 h-24 rounded-lg overflow-hidden bg-muted">
            <img
              v-if="getBestImageUrl(media)"
              :src="getBestImageUrl(media)"
              :alt="media.title"
              class="w-full h-full object-cover transition-transform duration-300 group-hover:scale-110"
              @error="handleImageError"
              loading="lazy"
            />
            <div
              v-else
              class="w-full h-full flex items-center justify-center bg-gradient-to-br from-muted to-muted/50"
            >
              <AppIcon
                :icon="media.media_type === 'movie' ? 'lucide:film' : 'lucide:tv'"
                size="24"
                class="text-muted-foreground"
              />
            </div>
          </div>
          <!-- Status Badge on Image -->
          <div class="absolute -top-1 -right-1">
            <span
              :class="getStatusBadgeClass(media)"
              class="px-1.5 py-0.5 text-xs font-medium rounded-full shadow-lg"
            >
              {{ getDisplayStatus(media) }}
            </span>
          </div>
        </div>

        <div class="flex-1 min-w-0">
          <div class="flex items-start justify-between gap-2">
            <div class="flex-1 min-w-0">
              <h3 class="text-base font-semibold text-foreground truncate group-hover:text-primary transition-colors">
                {{ media.title }}
              </h3>
              <div class="flex items-center gap-2 mt-1 flex-wrap">
                <span class="text-sm text-muted-foreground">
                  {{ media.year || 'N/A' }}
                </span>
                <span class="text-muted-foreground">•</span>
                <span
                  :class="media.media_type === 'movie' ? 'text-blue-500' : 'text-green-500'"
                  class="text-sm font-medium"
                >
                  {{ media.media_type.toUpperCase() }}
                </span>
                <span v-if="media.request_count && media.request_count > 1" class="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary">
                  {{ media.request_count }}x
                </span>
              </div>
            </div>
            <div class="flex-shrink-0 text-right">
              <div class="text-xs text-muted-foreground">
                {{ formatDate(media.updated_at) }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Loading More Indicator -->
      <div v-if="loadingMore" class="flex justify-center py-6">
        <div class="flex items-center gap-2 text-muted-foreground">
          <AppIcon icon="lucide:loader-2" size="18" class="animate-spin" />
          <span class="text-sm">Loading more...</span>
        </div>
      </div>

      <!-- End of List Indicator -->
      <div v-if="hasMore === false && mediaItems.length > 0" class="text-center py-6">
        <p class="text-sm text-muted-foreground">No more items to load</p>
      </div>
    </div>
  </Card>
</template>

<script setup lang="ts">
import Card from '~/components/ui/Card.vue'
import Button from '~/components/ui/Button.vue'

interface ProcessedMedia {
  id: number
  tmdb_id: number
  imdb_id?: string
  trakt_id?: string
  media_type: string
  title: string
  year?: number
  overview?: string
  overseerr_request_id?: number
  overseerr_media_id?: number
  status: string
  processing_stage?: string
  seasons_processed?: any
  confirmed_episodes?: string[]
  failed_episodes?: string[]
  unprocessed_episodes?: string[]
  torrents_found?: number
  error_message?: string
  error_count?: number
  last_error_at?: string
  processing_started_at?: string
  processing_completed_at?: string
  last_checked_at?: string
  extra_data?: any
  created_at: string
  updated_at: string
  requested_by?: string
  requested_at?: string
  first_requested_at?: string
  last_requested_at?: string
  request_count?: number
  is_subscribed?: boolean
  subscription_active?: boolean
  subscription_last_checked?: string
  seasons?: any[]
  total_seasons?: number
  seasons_processing?: string
  seasons_discrepant?: number[]
  seasons_completed?: number[]
  seasons_failed?: number[]
  poster_url?: string
  thumb_url?: string
  fanart_url?: string
  backdrop_url?: string
  poster_image_format?: string
  poster_image_size?: number
  thumb_image_format?: string
  thumb_image_size?: number
  fanart_image_format?: string
  fanart_image_size?: number
  backdrop_image_format?: string
  backdrop_image_size?: number
  has_poster_image?: boolean
  has_thumb_image?: boolean
  has_fanart_image?: boolean
  has_backdrop_image?: boolean
  display_status?: string
  progress_percentage?: number
  genres?: string[]
  runtime?: number
  rating?: string
  vote_count?: number
  popularity?: string
}

const viewMode = ref<'grid' | 'list'>('grid')
const currentPage = ref(1)
const pageSize = ref(24) // Load 24 items at a time
const mediaItems = ref<ProcessedMedia[]>([])
const hasMore = ref(true)
const loadingMore = ref(false)
const scrollContainer = ref<HTMLElement | null>(null)

// Load initial data
const { data: initialData, pending, error, refresh } = await useLazyAsyncData('recent-media', async () => {
  const params = new URLSearchParams({
    page: '1',
    limit: pageSize.value.toString(),
    sortBy: 'updated_at',
    sortOrder: 'DESC'
  })
  
  const response = await $fetch(`/api/unified-media?${params.toString()}`)
  
  if (response.success) {
    return {
      media: response.data.media || [],
      pagination: response.data.pagination || { has_next: false }
    }
  }
  return { media: [], pagination: { has_next: false } }
}, {
  server: false,
  default: () => ({ media: [], pagination: { has_next: false } })
})

// Initialize media items
watch(initialData, (data) => {
  if (data) {
    mediaItems.value = data.media || []
    hasMore.value = data.pagination?.has_next ?? false
  }
}, { immediate: true })

// Load more items
const loadMore = async () => {
  if (loadingMore.value || !hasMore.value) return
  
  loadingMore.value = true
  currentPage.value++
  
  try {
    const params = new URLSearchParams({
      page: currentPage.value.toString(),
      limit: pageSize.value.toString(),
      sortBy: 'updated_at',
      sortOrder: 'DESC'
    })
    
    const response = await $fetch(`/api/unified-media?${params.toString()}`)
    
    if (response.success && response.data) {
      const newMedia = response.data.media || []
      mediaItems.value = [...mediaItems.value, ...newMedia]
      hasMore.value = response.data.pagination?.has_next ?? false
    }
  } catch (err) {
    console.error('Error loading more media:', err)
    currentPage.value-- // Revert page on error
  } finally {
    loadingMore.value = false
  }
}

// Auto-scroll pagination using window scroll
const handleScroll = () => {
  if (loadingMore.value || !hasMore.value) return
  
  const windowHeight = window.innerHeight
  const documentHeight = document.documentElement.scrollHeight
  const scrollTop = window.pageYOffset || document.documentElement.scrollTop
  
  // Load more when user scrolls to within 500px of the bottom of the page
  if (scrollTop + windowHeight >= documentHeight - 500) {
    loadMore()
  }
}

// Set up window scroll listener
onMounted(() => {
  if (process.client) {
    window.addEventListener('scroll', handleScroll, { passive: true })
  }
})

onUnmounted(() => {
  if (process.client) {
    window.removeEventListener('scroll', handleScroll)
  }
})

const getBestImageUrl = (media: ProcessedMedia) => {
  if (media.has_poster_image) {
    return `/api/media-image/${media.id}?type=poster`
  } else if (media.has_thumb_image) {
    return `/api/media-image/${media.id}?type=thumb`
  } else if (media.has_fanart_image) {
    return `/api/media-image/${media.id}?type=fanart`
  }
  return null
}

const handleImageError = (event: Event) => {
  const img = event.target as HTMLImageElement
  img.style.display = 'none'
}

const getStatusBadgeClass = (media: ProcessedMedia) => {
  const status = media.display_status || media.status
  
  if (typeof status === 'string' && status.includes('/')) {
    return 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200'
  }
  
  switch (status) {
    case 'completed': return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200'
    case 'processing': return 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200'
    case 'failed': return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
    case 'pending': return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
    case 'skipped': return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
    case 'cancelled': return 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200'
    case 'ignored': return 'bg-slate-100 text-slate-800 dark:bg-slate-900 dark:text-slate-200'
    default: return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
  }
}

const getStatusIcon = (media: ProcessedMedia) => {
  // Using white Vadarr icon for all statuses
  return null // Not used anymore, replaced with img tag
}

const getStatusIconClass = (media: ProcessedMedia) => {
  const status = media.display_status || media.status
  
  if (typeof status === 'string' && status.includes('/')) {
    return 'bg-amber-600/90 border border-amber-500/50'
  }
  
  switch (status) {
    case 'completed': return 'bg-emerald-600/90 border border-emerald-500/50'
    case 'processing': return 'bg-amber-600/90 border border-amber-500/50'
    case 'failed': return 'bg-red-600/90 border border-red-500/50'
    case 'pending': return 'bg-yellow-600/90 border border-yellow-500/50'
    case 'ignored': return 'bg-slate-600/90 border border-slate-500/50'
    default: return 'bg-gray-600/90 border border-gray-500/50'
  }
}

const getStatusIconColor = (media: ProcessedMedia) => {
  return 'text-white'
}

const getDisplayStatus = (media: ProcessedMedia) => {
  return media.display_status || media.status
}

const formatDate = (dateString: string) => {
  if (!dateString) return 'Never'
  const date = new Date(dateString)
  const now = new Date()
  const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60))
  
  if (diffInHours < 1) return 'Just now'
  if (diffInHours < 24) return `${diffInHours}h ago`
  if (diffInHours < 48) return 'Yesterday'
  return date.toLocaleDateString('en-US', { 
    month: 'short',
    day: 'numeric'
  })
}

const viewMedia = (media: ProcessedMedia) => {
  navigateTo(`/processed-media?mediaId=${media.id}`)
}

// Save view mode preference
watch(viewMode, (mode) => {
  if (process.client) {
    localStorage.setItem('recent-media-view-mode', mode)
  }
})

// Load view mode preference
onMounted(() => {
  if (process.client) {
    const saved = localStorage.getItem('recent-media-view-mode')
    if (saved === 'list' || saved === 'grid') {
      viewMode.value = saved
    }
  }
})
</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Enhanced Glass Card - Rounded and Clean */
.glass-card-enhanced {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 
    0 4px 24px 0 rgba(31, 38, 135, 0.12),
    inset 0 0 0 1px rgba(255, 255, 255, 0.03);
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
  transform-style: preserve-3d;
  perspective: 1000px;
}

.dark .glass-card-enhanced {
  background: rgba(0, 0, 0, 0.6);
  border: 1px solid rgba(130, 36, 227, 0.2);
  box-shadow: 
    0 4px 24px 0 rgba(0, 0, 0, 0.4),
    0 0 0 1px rgba(130, 36, 227, 0.15),
    inset 0 0 15px rgba(130, 36, 227, 0.1);
}

.glass-card-enhanced:hover {
  border-color: rgba(130, 36, 227, 0.4);
  box-shadow: 
    0 12px 40px 0 rgba(130, 36, 227, 0.2),
    0 0 0 1px rgba(130, 36, 227, 0.3),
    inset 0 0 20px rgba(130, 36, 227, 0.12);
  transform: translateY(-6px);
}

/* Staggered Fade In Animation */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.animate-fade-in-up {
  animation: fadeInUp 0.6s cubic-bezier(0.4, 0, 0.2, 1) forwards;
  opacity: 0;
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

/* Media Type Badge - Color Palette Adherence */
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

/* Error Badge */
.error-badge {
  box-shadow: 
    0 4px 20px rgba(239, 68, 68, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

/* Shimmer Animation */
@keyframes shimmer {
  0% {
    transform: translateX(-100%) skewX(-15deg);
  }
  100% {
    transform: translateX(200%) skewX(-15deg);
  }
}

.animate-shimmer {
  animation: shimmer 2s infinite;
}

/* Soft Pulse Animation */
@keyframes pulse-soft {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.7;
    transform: scale(1.05);
  }
}

.animate-pulse-soft {
  animation: pulse-soft 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}
</style>
