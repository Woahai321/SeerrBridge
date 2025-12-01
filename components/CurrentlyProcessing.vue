<template>
  <Card class="relative overflow-hidden group">
    <!-- Animated background gradient -->
    <div class="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-accent/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
    
    <!-- Content -->
    <div class="relative">
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center space-x-3">
          <div class="w-10 h-10 sm:w-12 sm:h-12 bg-primary/10 rounded-lg sm:rounded-xl flex items-center justify-center group-hover:bg-primary/20 transition-colors relative">
            <AppIcon 
              icon="lucide:play-circle" 
              size="20" 
              class="sm:w-6 sm:h-6 text-primary"
              :class="{ 'animate-pulse': isProcessing }"
            />
            <div 
              v-if="isProcessing"
              class="absolute inset-0 rounded-lg sm:rounded-xl bg-primary/20 animate-ping"
            />
          </div>
          <div>
            <h2 class="text-xl font-semibold text-foreground">Currently Processing</h2>
            <p class="text-sm text-muted-foreground">
              {{ processingCount > 0 ? `${processingCount} item${processingCount > 1 ? 's' : ''} in queue` : 'No items processing' }}
            </p>
          </div>
        </div>
        <div 
          v-if="isProcessing"
          class="flex items-center space-x-2 px-3 py-1.5 bg-primary/10 rounded-full"
        >
          <div class="w-2 h-2 bg-primary rounded-full animate-pulse" />
          <span class="text-xs font-medium text-primary">Live</span>
        </div>
      </div>

      <!-- Current Item Display -->
      <div v-if="currentItem" class="space-y-4">
        <!-- Main Processing Item Card -->
        <div class="bg-muted/30 rounded-xl p-4 border border-border/50 hover:border-primary/30 transition-all duration-300">
          <div class="flex items-start space-x-4">
            <!-- Poster Image -->
            <div class="flex-shrink-0 relative">
              <div 
                v-if="currentItem.has_poster_image || currentItem.has_thumb_image"
                class="w-20 h-28 rounded-lg overflow-hidden bg-muted relative group/image"
              >
                <img 
                  :src="getImageUrl(currentItem.id, currentItem.has_poster_image ? 'poster' : 'thumb')"
                  :alt="currentItem.title"
                  class="w-full h-full object-cover transition-transform duration-300 group-hover/image:scale-105"
                  @error="handleImageError"
                />
                <!-- Processing overlay -->
                <div class="absolute inset-0 bg-primary/20 flex items-center justify-center">
                  <AppIcon 
                    icon="lucide:loader-2" 
                    size="20" 
                    class="sm:w-6 sm:h-6 text-primary animate-spin"
                  />
                </div>
              </div>
              <div 
                v-else
                class="w-20 h-28 rounded-lg bg-gradient-to-br from-muted to-muted/50 flex items-center justify-center"
              >
                <AppIcon 
                  :icon="currentItem.media_type === 'movie' ? 'lucide:film' : 'lucide:tv'" 
                  size="24" 
                  class="text-muted-foreground"
                />
              </div>
            </div>

            <!-- Item Details -->
            <div class="flex-1 min-w-0 space-y-2">
              <div>
                <h3 class="text-lg font-bold text-foreground truncate">
                  {{ currentItem.title }}
                </h3>
                <div class="flex items-center space-x-2 mt-1">
                  <span class="text-sm text-muted-foreground">
                    {{ currentItem.year || 'N/A' }}
                  </span>
                  <span class="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary font-medium">
                    {{ currentItem.media_type.toUpperCase() }}
                  </span>
                </div>
              </div>

              <!-- Processing Stage -->
              <div v-if="currentItem.processing_stage" class="flex items-center space-x-2">
                <AppIcon icon="lucide:activity" size="16" class="text-primary animate-pulse" />
                <span class="text-sm text-foreground font-medium">
                  {{ formatProcessingStage(currentItem.processing_stage) }}
                </span>
              </div>

              <!-- Progress for TV Shows -->
              <div v-if="currentItem.media_type === 'tv' && currentItem.seasons_processing" class="space-y-1">
                <div class="flex items-center justify-between text-xs">
                  <span class="text-muted-foreground">Seasons Processing</span>
                  <span class="text-foreground font-medium">{{ currentItem.seasons_processing }}</span>
                </div>
                <div v-if="currentItem.total_seasons" class="w-full bg-muted rounded-full h-1.5 overflow-hidden">
                  <div 
                    class="h-full bg-gradient-to-r from-primary to-accent transition-all duration-500"
                    :style="{ width: `${(parseInt(currentItem.seasons_processing) / currentItem.total_seasons) * 100}%` }"
                  />
                </div>
              </div>

              <!-- Started Time -->
              <div class="flex items-center space-x-2 text-xs text-muted-foreground">
                <AppIcon icon="lucide:clock" size="14" />
                <span>Started {{ formatTimeAgo(currentItem.processing_started_at) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Processing Queue List (if multiple items) -->
        <div v-if="processingItems.length > 1" class="space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-sm font-medium text-foreground">Queue</span>
            <span class="text-xs text-muted-foreground">{{ processingItems.length - 1 }} more</span>
          </div>
          <div class="space-y-1.5 max-h-32 overflow-y-auto">
            <div 
              v-for="item in processingItems.slice(1, 4)" 
              :key="item.id"
              class="flex items-center space-x-2 p-2 rounded-lg bg-muted/20 hover:bg-muted/40 transition-colors"
            >
              <div class="w-8 h-12 rounded bg-muted flex-shrink-0 overflow-hidden">
                <img 
                  v-if="item.has_poster_image || item.has_thumb_image"
                  :src="getImageUrl(item.id, item.has_poster_image ? 'poster' : 'thumb')"
                  :alt="item.title"
                  class="w-full h-full object-cover"
                  @error="handleImageError"
                />
                <div v-else class="w-full h-full flex items-center justify-center">
                  <AppIcon 
                    :icon="item.media_type === 'movie' ? 'lucide:film' : 'lucide:tv'" 
                    size="16" 
                    class="text-muted-foreground"
                  />
                </div>
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-foreground truncate">{{ item.title }}</p>
                <p class="text-xs text-muted-foreground">{{ item.media_type.toUpperCase() }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-else class="text-center py-8">
        <div class="inline-flex w-12 h-12 sm:w-16 sm:h-16 bg-muted rounded-lg sm:rounded-xl items-center justify-center mb-3">
          <AppIcon icon="lucide:check-circle-2" size="20" class="sm:w-6 sm:h-6 text-muted-foreground" />
        </div>
        <p class="text-sm font-medium text-foreground mb-1">All caught up!</p>
        <p class="text-xs text-muted-foreground">No items are currently being processed</p>
      </div>
    </div>
  </Card>
</template>

<script setup lang="ts">
import Card from '~/components/ui/Card.vue'

interface ProcessingItem {
  id: number
  tmdb_id: number
  title: string
  year?: number
  media_type: string
  processing_stage?: string
  processing_started_at?: string
  has_poster_image?: boolean
  has_thumb_image?: boolean
  has_fanart_image?: boolean
  seasons_processing?: string
  total_seasons?: number
  progress_percentage?: number
}

interface Props {
  currentItem: ProcessingItem | null
  processingItems: ProcessingItem[]
  processingCount: number
}

const props = defineProps<Props>()

const isProcessing = computed(() => props.processingCount > 0)

const getImageUrl = (mediaId: number, type: 'poster' | 'thumb' | 'fanart' = 'poster') => {
  return `/api/media-image/${mediaId}?type=${type}`
}

const handleImageError = (event: Event) => {
  const img = event.target as HTMLImageElement
  img.style.display = 'none'
}

const formatProcessingStage = (stage: string) => {
  if (!stage) return 'Processing...'
  return stage
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

const formatTimeAgo = (timestamp?: string) => {
  if (!timestamp) return 'recently'
  
  const date = new Date(timestamp)
  const now = new Date()
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000)
  
  if (diffInSeconds < 60) return 'just now'
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`
  return `${Math.floor(diffInSeconds / 86400)}d ago`
}
</script>

