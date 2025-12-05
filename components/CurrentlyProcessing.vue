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
            <h2 class="text-xl font-semibold text-foreground">Processing Queue</h2>
            <p class="text-sm text-muted-foreground">
              <span v-if="queueStats">
                {{ queueStats.total_queued }} item{{ queueStats.total_queued !== 1 ? 's' : '' }} in queue
                <span v-if="queueStats.movie_queue_size > 0 || queueStats.tv_queue_size > 0" class="text-xs">
                  ({{ queueStats.movie_queue_size }} movie{{ queueStats.movie_queue_size !== 1 ? 's' : '' }}, {{ queueStats.tv_queue_size }} TV)
                </span>
              </span>
              <span v-else>
                {{ processingCount > 0 ? `${processingCount} item${processingCount > 1 ? 's' : ''} processing` : 'No items processing' }}
              </span>
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

      <!-- Current Item Display (Processing Now) -->
      <div v-if="currentItem" class="space-y-4">
        <!-- Processing Now Badge -->
        <div class="flex items-center space-x-2">
          <div class="flex items-center space-x-2 px-3 py-1.5 bg-primary/20 rounded-full">
            <AppIcon icon="lucide:zap" size="14" class="text-primary animate-pulse" />
            <span class="text-xs font-semibold text-primary">Processing Now</span>
          </div>
        </div>

        <!-- Main Processing Item Card -->
        <div class="bg-gradient-to-br from-primary/10 via-primary/5 to-transparent rounded-xl p-4 border-2 border-primary/30 hover:border-primary/50 transition-all duration-300">
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
                <div class="absolute inset-0 bg-primary/30 flex items-center justify-center">
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
                  <span class="text-xs px-2 py-0.5 rounded-full bg-primary/20 text-primary font-medium">
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
                <!-- Show current season if processing specific season -->
                <span 
                  v-if="currentItem.media_type === 'tv' && getCurrentSeason(currentItem.processing_stage)"
                  class="text-xs px-2 py-0.5 rounded-full bg-primary/20 text-primary font-medium"
                >
                  Season {{ getCurrentSeason(currentItem.processing_stage) }}
                </span>
              </div>

              <!-- Progress for TV Shows -->
              <div v-if="currentItem.media_type === 'tv'" class="space-y-1">
                <div v-if="currentItem.seasons_processing" class="flex items-center justify-between text-xs">
                  <span class="text-muted-foreground">Seasons Processing</span>
                  <span class="text-foreground font-medium">{{ currentItem.seasons_processing }}</span>
                </div>
                <div v-if="currentItem.total_seasons && currentItem.seasons_processing" class="w-full bg-muted rounded-full h-1.5 overflow-hidden">
                  <div 
                    class="h-full bg-gradient-to-r from-primary to-accent transition-all duration-500"
                    :style="{ width: `${getSeasonProgress(currentItem)}%` }"
                  />
                </div>
                <!-- Show current season being processed if available -->
                <div 
                  v-if="getCurrentSeason(currentItem.processing_stage) && !currentItem.seasons_processing"
                  class="text-xs text-muted-foreground"
                >
                  Processing Season {{ getCurrentSeason(currentItem.processing_stage) }}
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
      </div>

      <!-- Queue List -->
      <div v-if="queuedItems.length > 0" class="space-y-3 mt-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <span class="text-sm font-medium text-foreground">Queue</span>
            <span class="text-xs px-2 py-0.5 rounded-full bg-muted text-muted-foreground">
              {{ queuedItems.length }} item{{ queuedItems.length !== 1 ? 's' : '' }}
            </span>
          </div>
          <div class="flex items-center space-x-2">
            <button
              @click="showClearQueueModal = true"
              class="text-xs text-destructive hover:text-destructive/80 transition-colors flex items-center space-x-1 px-2 py-1 rounded hover:bg-destructive/10"
              title="Clear entire queue"
            >
              <AppIcon icon="lucide:trash-2" size="14" />
              <span>Clear Queue</span>
            </button>
            <button
              @click="queueExpanded = !queueExpanded"
              class="text-xs text-muted-foreground hover:text-foreground transition-colors flex items-center space-x-1"
            >
              <span>{{ queueExpanded ? 'Collapse' : 'Expand' }}</span>
              <AppIcon 
                :icon="queueExpanded ? 'lucide:chevron-up' : 'lucide:chevron-down'" 
                size="14" 
              />
            </button>
          </div>
        </div>

        <div 
          class="space-y-2 transition-all duration-300"
          :class="queueExpanded ? 'max-h-[600px] overflow-y-auto' : 'max-h-[200px] overflow-y-auto'"
        >
          <div 
            v-for="(item, index) in queuedItems" 
            :key="item.id"
            class="flex items-center space-x-3 p-3 rounded-lg transition-all duration-200"
            :class="item.queue_status === 'processing' 
              ? 'bg-primary/10 border border-primary/20 hover:bg-primary/15' 
              : 'bg-muted/30 border border-border/50 hover:bg-muted/50'"
          >
            <!-- Queue Position -->
            <div class="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold"
              :class="item.queue_status === 'processing' 
                ? 'bg-primary text-primary-foreground' 
                : 'bg-muted text-muted-foreground'"
            >
              {{ index + 1 }}
            </div>

            <!-- Poster Thumbnail -->
            <div class="flex-shrink-0 w-12 h-16 rounded bg-muted overflow-hidden">
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

            <!-- Item Info -->
            <div class="flex-1 min-w-0">
              <div class="flex items-center space-x-2">
                <p class="text-sm font-medium text-foreground truncate">{{ item.title }}</p>
                <span 
                  class="text-xs px-1.5 py-0.5 rounded-full font-medium flex-shrink-0"
                  :class="item.queue_status === 'processing' 
                    ? 'bg-primary/20 text-primary' 
                    : 'bg-muted text-muted-foreground'"
                >
                  {{ item.queue_status === 'processing' ? 'Processing' : 'Queued' }}
                </span>
              </div>
              <div class="flex items-center space-x-2 mt-1">
                <span class="text-xs text-muted-foreground">{{ item.year || 'N/A' }}</span>
                <span class="text-xs px-1.5 py-0.5 rounded bg-muted/50 text-muted-foreground">
                  {{ item.media_type.toUpperCase() }}
                </span>
                <span v-if="item.queue_status === 'queued' && item.queue_added_at" class="text-xs text-muted-foreground">
                  • Queued {{ formatTimeAgo(item.queue_added_at) }}
                </span>
                <span v-else-if="item.processing_started_at" class="text-xs text-muted-foreground">
                  • Started {{ formatTimeAgo(item.processing_started_at) }}
                </span>
              </div>
              <!-- Estimated Wait Time for Queued Items -->
              <div v-if="item.queue_status === 'queued' && index > 0" class="mt-1">
                <span class="text-xs text-muted-foreground">
                  Est. wait: ~{{ estimateWaitTime(index) }}
                </span>
              </div>
            </div>

            <!-- Status Indicator and Skip Button -->
            <div class="flex-shrink-0 flex items-center space-x-2">
              <button
                @click="showSkipModal = true; itemToSkip = item"
                class="p-1.5 rounded hover:bg-destructive/10 text-destructive hover:text-destructive/80 transition-colors"
                title="Skip this item"
                :disabled="isSkipping"
              >
                <AppIcon 
                  icon="lucide:x" 
                  size="16" 
                  :class="{ 'animate-spin': isSkipping && itemToSkip?.id === item.id }"
                />
              </button>
              <div 
                v-if="item.queue_status === 'processing'"
                class="w-2 h-2 bg-primary rounded-full animate-pulse"
              />
              <div 
                v-else
                class="w-2 h-2 bg-muted-foreground/30 rounded-full"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Skip Item Confirmation Modal -->
      <div v-if="showSkipModal" class="fixed inset-0 z-[100] overflow-y-auto p-2 sm:p-4">
        <!-- Overlay -->
        <div 
          class="fixed inset-0 bg-black/80 backdrop-blur-sm" 
          @click="showSkipModal = false"
        ></div>
        
        <!-- Confirmation Modal -->
        <div class="relative mx-auto max-w-md my-4 sm:my-8 bg-card rounded-xl sm:rounded-2xl lg:rounded-3xl shadow-2xl overflow-hidden">
          <!-- Header -->
          <div class="bg-orange-500/10 border-b border-orange-500/20 px-4 sm:px-6 py-3 sm:py-4">
            <div class="flex items-center gap-2 sm:gap-3">
              <div class="w-8 h-8 sm:w-10 sm:h-10 bg-orange-500/20 rounded-lg sm:rounded-xl flex items-center justify-center">
                <AppIcon icon="lucide:skip-forward" size="18" class="sm:w-5 sm:h-5 text-orange-500" />
              </div>
              <div>
                <h3 class="text-base sm:text-lg font-bold text-foreground">Skip Queue Item</h3>
                <p class="text-xs sm:text-sm text-muted-foreground">Remove this item from the queue</p>
              </div>
            </div>
          </div>
          
          <!-- Body -->
          <div class="px-4 sm:px-6 py-4 sm:py-6">
            <p class="text-sm sm:text-base text-foreground mb-4">
              Are you sure you want to skip <span class="font-semibold">{{ itemToSkip?.title }}</span>?
            </p>
            <div class="bg-muted/50 rounded-lg p-3 space-y-2 text-xs sm:text-sm">
              <p class="text-muted-foreground">
                <strong class="text-foreground">This will:</strong>
              </p>
              <ul class="list-disc list-inside space-y-1 text-muted-foreground ml-2">
                <li>Remove the item from the queue</li>
                <li v-if="itemToSkip?.queue_status === 'processing'">Interrupt current processing (if active)</li>
                <li>Mark the item as failed</li>
                <li>Continue with the next item in queue</li>
              </ul>
            </div>
          </div>
          
          <!-- Footer -->
          <div class="px-4 sm:px-6 py-3 sm:py-4 border-t border-border flex flex-col sm:flex-row items-stretch sm:items-center gap-2 sm:gap-3">
            <Button
              @click="showSkipModal = false"
              variant="outline"
              class="flex-1"
              :disabled="isSkipping"
            >
              Cancel
            </Button>
            <Button
              @click="handleSkipItem"
              variant="destructive"
              class="flex-1"
              :disabled="isSkipping"
            >
              <AppIcon v-if="isSkipping" icon="lucide:loader-2" size="16" class="animate-spin mr-2" />
              {{ isSkipping ? 'Skipping...' : 'Skip Item' }}
            </Button>
          </div>
        </div>
      </div>

      <!-- Clear Queue Confirmation Modal -->
      <div v-if="showClearQueueModal" class="fixed inset-0 z-[100] overflow-y-auto p-2 sm:p-4">
        <!-- Overlay -->
        <div 
          class="fixed inset-0 bg-black/80 backdrop-blur-sm" 
          @click="showClearQueueModal = false"
        ></div>
        
        <!-- Confirmation Modal -->
        <div class="relative mx-auto max-w-md my-4 sm:my-8 bg-card rounded-xl sm:rounded-2xl lg:rounded-3xl shadow-2xl overflow-hidden">
          <!-- Header -->
          <div class="bg-red-500/10 border-b border-red-500/20 px-4 sm:px-6 py-3 sm:py-4">
            <div class="flex items-center gap-2 sm:gap-3">
              <div class="w-8 h-8 sm:w-10 sm:h-10 bg-red-500/20 rounded-lg sm:rounded-xl flex items-center justify-center">
                <AppIcon icon="lucide:trash-2" size="18" class="sm:w-5 sm:h-5 text-red-500" />
              </div>
              <div>
                <h3 class="text-base sm:text-lg font-bold text-foreground">Clear Queue</h3>
                <p class="text-xs sm:text-sm text-muted-foreground">Remove all items from the queue</p>
              </div>
            </div>
          </div>
          
          <!-- Body -->
          <div class="px-4 sm:px-6 py-4 sm:py-6">
            <p class="text-sm sm:text-base text-foreground mb-4">
              Are you sure you want to clear the entire queue?
            </p>
            <div class="bg-muted/50 rounded-lg p-3 space-y-2 text-xs sm:text-sm">
              <p class="text-muted-foreground">
                <strong class="text-foreground">This will:</strong>
              </p>
              <ul class="list-disc list-inside space-y-1 text-muted-foreground ml-2">
                <li>Remove all {{ queuedItems.length }} item{{ queuedItems.length !== 1 ? 's' : '' }} from the queue</li>
                <li>Interrupt any currently processing items</li>
                <li>Mark all items as failed</li>
              </ul>
            </div>
          </div>
          
          <!-- Footer -->
          <div class="px-4 sm:px-6 py-3 sm:py-4 border-t border-border flex flex-col sm:flex-row items-stretch sm:items-center gap-2 sm:gap-3">
            <Button
              @click="showClearQueueModal = false"
              variant="outline"
              class="flex-1"
              :disabled="isClearing"
            >
              Cancel
            </Button>
            <Button
              @click="handleClearQueue"
              variant="destructive"
              class="flex-1"
              :disabled="isClearing"
            >
              <AppIcon v-if="isClearing" icon="lucide:loader-2" size="16" class="animate-spin mr-2" />
              {{ isClearing ? 'Clearing...' : 'Clear Queue' }}
            </Button>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-if="!currentItem && queuedItems.length === 0" class="text-center py-8">
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
import Button from '~/components/ui/Button.vue'

interface ProcessingItem {
  id: number
  tmdb_id: number
  title: string
  year?: number
  media_type: string
  processing_stage?: string
  processing_started_at?: string
  queue_added_at?: string
  has_poster_image?: boolean
  has_thumb_image?: boolean
  has_fanart_image?: boolean
  seasons_processing?: string
  total_seasons?: number
  progress_percentage?: number
  queue_status?: 'processing' | 'queued'
}

interface QueueStats {
  movie_queue_size: number
  movie_queue_max: number
  tv_queue_size: number
  tv_queue_max: number
  total_queued: number
  is_processing: boolean
}

interface Props {
  currentItem: ProcessingItem | null
  queuedItems: ProcessingItem[]
  processingItems: ProcessingItem[]
  processingCount: number
  queueStats?: QueueStats | null
}

const props = defineProps<Props>()

const queueExpanded = ref(false)
const showSkipModal = ref(false)
const showClearQueueModal = ref(false)
const itemToSkip = ref<ProcessingItem | null>(null)
const isSkipping = ref(false)
const isClearing = ref(false)

const { skipItem, clearQueue } = useQueueManagement()
const { refresh: refreshProcessing } = useProcessingStatus()

const isProcessing = computed(() => props.processingCount > 0 || (props.queueStats?.is_processing ?? false))

const getImageUrl = (mediaId: number, type: 'poster' | 'thumb' | 'fanart' = 'poster') => {
  return `/api/media-image/${mediaId}?type=${type}`
}

const handleImageError = (event: Event) => {
  const img = event.target as HTMLImageElement
  img.style.display = 'none'
}

const formatProcessingStage = (stage: string) => {
  if (!stage) return 'Processing...'
  
  // Handle season-specific stages
  if (stage.indexOf('browser_automation_season_') === 0) {
    return 'Processing Season'
  }
  
  return stage
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

const getCurrentSeason = (stage: string | undefined): number | null => {
  if (!stage || stage.indexOf('browser_automation_season_') !== 0) {
    return null
  }
  
  const match = stage.match(/browser_automation_season_(\d+)/)
  if (match && match[1]) {
    return parseInt(match[1])
  }
  return null
}

const getSeasonProgress = (item: ProcessingItem): number => {
  if (item.media_type === 'tv' && item.seasons_processing && item.total_seasons) {
    // Try to parse seasons_processing (could be "1", "1-3", "1,2,3", etc.)
    const processing = item.seasons_processing
    const total = item.total_seasons
    
    // If it's a simple number, use it directly
    if (/^\d+$/.test(processing)) {
      return Math.round((parseInt(processing) / total) * 100)
    }
    
    // If it's a range like "1-3", count the seasons
    if (processing.includes('-')) {
      const [start, end] = processing.split('-').map(s => parseInt(s.trim()))
      if (!isNaN(start) && !isNaN(end)) {
        const count = end - start + 1
        return Math.round((count / total) * 100)
      }
    }
    
    // If it's comma-separated, count the items
    if (processing.includes(',')) {
      const seasons = processing.split(',').filter(s => s.trim())
      return Math.round((seasons.length / total) * 100)
    }
  }
  return 0
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

const estimateWaitTime = (queuePosition: number): string => {
  // Rough estimate: assume 5-10 minutes per item
  const avgMinutesPerItem = 7
  const estimatedMinutes = queuePosition * avgMinutesPerItem
  
  if (estimatedMinutes < 60) {
    return `${estimatedMinutes}m`
  }
  const hours = Math.floor(estimatedMinutes / 60)
  const minutes = estimatedMinutes % 60
  return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`
}

const handleSkipItem = async () => {
  if (!itemToSkip.value) return
  
  isSkipping.value = true
  try {
    const result = await skipItem(
      itemToSkip.value.id,
      itemToSkip.value.tmdb_id,
      itemToSkip.value.media_type,
      itemToSkip.value.title
    )
    
    if (result.success) {
      // Close modal immediately on success
      showSkipModal.value = false
      itemToSkip.value = null
      // Refresh the processing status to update the queue
      // Don't await - let it happen in background
      refreshProcessing().catch(err => console.error('Error refreshing processing status:', err))
    }
  } catch (error) {
    console.error('Error skipping item:', error)
    // Close modal even on error to prevent it from staying open
    showSkipModal.value = false
    itemToSkip.value = null
  } finally {
    isSkipping.value = false
  }
}

const handleClearQueue = async () => {
  isClearing.value = true
  try {
    const result = await clearQueue()
    
    if (result.success) {
      // Close modal immediately on success
      showClearQueueModal.value = false
      // Refresh the processing status to update the queue
      // Don't await - let it happen in background
      refreshProcessing().catch(err => console.error('Error refreshing processing status:', err))
    }
  } catch (error) {
    console.error('Error clearing queue:', error)
    // Close modal even on error to prevent it from staying open
    showClearQueueModal.value = false
  } finally {
    isClearing.value = false
  }
}
</script>
