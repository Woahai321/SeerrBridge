<template>
  <Card class="h-full">
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center space-x-3">
        <div class="p-2 bg-primary/10 rounded-lg">
          <AppIcon icon="lucide:film" size="20" class="text-primary" />
        </div>
        <div>
          <h2 class="text-xl font-semibold text-foreground">Recent Media</h2>
          <p class="text-sm text-muted-foreground">Latest processed items</p>
        </div>
      </div>
      <NuxtLink to="/processed-media">
        <Button variant="ghost" size="sm">
          <span>View All</span>
          <AppIcon icon="lucide:chevron-right" size="16" class="ml-1" />
        </Button>
      </NuxtLink>
    </div>

    <div v-if="pending" class="space-y-4">
      <div v-for="i in 5" :key="i" class="animate-pulse">
        <div class="flex items-center space-x-4 p-3 rounded-lg border border-border">
          <div class="w-12 h-16 bg-muted rounded"></div>
          <div class="flex-1 space-y-2">
            <div class="h-4 bg-muted rounded w-3/4"></div>
            <div class="h-3 bg-muted rounded w-1/2"></div>
            <div class="h-2 bg-muted rounded w-full"></div>
          </div>
          <div class="w-16 space-y-2">
            <div class="h-6 bg-muted rounded"></div>
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="error" class="text-center py-8">
      <AppIcon icon="lucide:alert-circle" size="48" class="mx-auto text-destructive mb-4" />
      <p class="text-destructive">Failed to load recent media</p>
    </div>

    <div v-else-if="!mediaItems || mediaItems.length === 0" class="text-center py-8">
      <AppIcon icon="lucide:film" size="48" class="mx-auto text-muted-foreground mb-4" />
      <p class="text-muted-foreground">No media processed yet</p>
    </div>

    <div v-else class="space-y-3 max-h-96 overflow-y-auto">
      <div 
        v-for="media in mediaItems" 
        :key="media.id"
        class="flex items-center space-x-3 p-3 rounded-lg hover:bg-muted/50 transition-colors cursor-pointer"
        @click="viewMedia(media)"
      >
        <div class="flex-shrink-0">
          <img 
            v-if="getBestImageUrl(media)" 
            :src="getBestImageUrl(media)" 
            :alt="media.title"
            class="w-12 h-16 object-cover rounded"
            @error="handleImageError"
          />
          <div v-else class="w-12 h-16 bg-muted rounded flex items-center justify-center">
            <AppIcon 
              :icon="media.media_type === 'movie' ? 'lucide:film' : 'lucide:tv'" 
              size="20" 
              class="text-muted-foreground" 
            />
          </div>
        </div>
        <div class="flex-1 min-w-0">
          <h3 class="text-sm font-medium text-foreground truncate">
            {{ media.title }}
          </h3>
          <p class="text-xs text-muted-foreground">
            {{ media.year || 'N/A' }} • {{ media.media_type.toUpperCase() }}
          </p>
          <div class="flex items-center space-x-2 mt-1">
            <span 
              :class="getStatusBadgeClass(media)" 
              class="text-xs px-2 py-0.5 rounded-full font-medium"
            >
              {{ getDisplayStatus(media) }}
            </span>
            <span v-if="media.request_count && media.request_count > 1" class="text-xs px-2 py-0.5 rounded-full bg-purple-100 text-purple-600 dark:bg-purple-900 dark:text-purple-400">
              {{ media.request_count }}x
            </span>
          </div>
        </div>
        <div class="flex-shrink-0">
          <div class="text-right">
            <div class="text-xs text-muted-foreground">
              {{ formatDate(media.updated_at) }}
            </div>
          </div>
        </div>
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

const { data: mediaData, pending, error } = await useLazyAsyncData('recent-media', async () => {
  const params = new URLSearchParams({
    page: '1',
    limit: '5',
    sortBy: 'updated_at',
    sortOrder: 'DESC'
  })
  
  const response = await $fetch(`/api/unified-media?${params.toString()}`)
  
  if (response.success) {
    return response.data.media || []
  }
  return []
}, {
  server: false,
  default: () => []
})

const mediaItems = computed<ProcessedMedia[]>(() => {
  return mediaData.value || []
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
</script>
