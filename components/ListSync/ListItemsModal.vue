<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
    @click.self="handleClose"
  >
    <div class="glass-card-enhanced rounded-2xl p-6 w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
      <!-- Header -->
      <div class="flex items-center justify-between mb-6 flex-shrink-0">
        <div class="flex-1 min-w-0">
          <h2 class="text-2xl font-bold text-foreground truncate">{{ listName }}</h2>
          <p class="text-sm text-muted-foreground mt-1 truncate">{{ listIdentifier }}</p>
        </div>
        <button
          @click="handleClose"
          class="p-2 hover:bg-muted rounded-lg transition-colors flex-shrink-0 ml-4"
        >
          <AppIcon icon="lucide:x" size="20" class="text-foreground" />
        </button>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="flex-1 flex items-center justify-center py-12">
        <AppIcon icon="lucide:loader-2" size="32" class="animate-spin text-primary" />
        <p class="text-muted-foreground ml-4">Loading items...</p>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="flex-1 flex items-center justify-center py-12">
        <div class="text-center">
          <AppIcon icon="lucide:alert-circle" size="32" class="text-destructive mx-auto mb-4" />
          <p class="text-destructive">{{ error }}</p>
          <button
            @click="loadItems"
            class="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>

      <!-- Empty State -->
      <div v-else-if="items.length === 0" class="flex-1 flex items-center justify-center py-12">
        <div class="text-center">
          <AppIcon icon="lucide:inbox" size="32" class="text-muted-foreground mx-auto mb-4" />
          <p class="text-muted-foreground">No items found in this list</p>
        </div>
      </div>

      <!-- Items Grid -->
      <div v-else class="flex-1 overflow-y-auto pr-2">
        <div v-if="checkingMatches" class="flex items-center justify-center py-8">
          <AppIcon icon="lucide:loader-2" size="20" class="animate-spin text-primary mr-2" />
          <span class="text-sm text-muted-foreground">Checking database matches...</span>
        </div>
        <div v-else class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          <div
            v-for="itemMatch in itemsWithMatches"
            :key="`${itemMatch.item.tmdb_id || itemMatch.item.imdb_id}-${itemMatch.item.title}-${itemMatch.item.year}`"
            @click="navigateToMedia(itemMatch.item, itemMatch.match)"
            class="group cursor-pointer relative"
          >
            <div class="glass-card-enhanced rounded-lg overflow-hidden border border-border hover:border-primary/50 transition-all hover:shadow-lg">
              <!-- Poster -->
              <div class="aspect-[2/3] bg-muted relative overflow-hidden">
                <img
                  v-if="getPosterUrl(itemMatch.item)"
                  :src="getPosterUrl(itemMatch.item)"
                  :alt="itemMatch.item.title || itemMatch.item.tmdb_id || itemMatch.item.imdb_id || 'Media poster'"
                  class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                  @error="handleImageError"
                  loading="lazy"
                />
                <div
                  v-else
                  class="w-full h-full flex flex-col items-center justify-center bg-gradient-to-br from-primary/20 to-primary/10"
                >
                  <AppIcon 
                    :icon="itemMatch.item.media_type === 'movie' ? 'lucide:film' : 'lucide:tv'" 
                    size="32" 
                    class="text-primary/50 mb-2" 
                  />
                  <span class="text-xs text-muted-foreground text-center px-2">
                    {{ itemMatch.item.title || itemMatch.item.tmdb_id || itemMatch.item.imdb_id || 'Unknown' }}
                  </span>
                </div>
                
                <!-- Media Type Badge -->
                <div class="absolute top-2 right-2 flex items-center gap-1">
                  <!-- In Database Badge -->
                  <span
                    v-if="itemMatch.match"
                    class="px-2 py-1 text-xs font-medium rounded-full bg-success/80 backdrop-blur-sm text-white flex items-center gap-1"
                    title="Already in database"
                  >
                    <AppIcon icon="lucide:check-circle" size="12" />
                    In DB
                  </span>
                  <span class="px-2 py-1 text-xs font-medium rounded-full bg-black/60 backdrop-blur-sm text-white">
                    {{ itemMatch.item.media_type === 'movie' ? 'Movie' : 'TV' }}
                  </span>
                </div>
              </div>

              <!-- Info -->
              <div class="p-3">
                <h3 class="font-semibold text-sm text-foreground line-clamp-2 mb-1 group-hover:text-primary transition-colors">
                  {{ itemMatch.item.title || itemMatch.item.tmdb_id || itemMatch.item.imdb_id || 'Unknown Title' }}
                </h3>
                <div class="flex items-center justify-between mb-1">
                  <p v-if="itemMatch.item.year" class="text-xs text-muted-foreground">
                    {{ itemMatch.item.year }}
                  </p>
                  <StatusBadge
                    v-if="itemMatch.item.status"
                    :status="itemMatch.item.status"
                    class="text-[10px]"
                  />
                </div>
                <div v-if="itemMatch.item.match_method" class="text-[10px] text-muted-foreground mt-1">
                  Matched: {{ itemMatch.item.match_method }}
                </div>
                <div v-if="itemMatch.item.error_message" class="text-[10px] text-destructive mt-1 line-clamp-1" :title="itemMatch.item.error_message">
                  ⚠️ {{ itemMatch.item.error_message }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="flex flex-col gap-3 pt-4 mt-4 border-t border-border flex-shrink-0">
        <!-- Status Summary -->
        <div class="flex flex-wrap items-center gap-3 text-xs">
          <div class="flex items-center gap-1.5">
            <span class="text-muted-foreground">Total:</span>
            <span class="font-semibold text-foreground">{{ items.length }}</span>
          </div>
          <div v-if="getStatusCount('already_available') > 0" class="flex items-center gap-1.5">
            <span class="text-primary">Available:</span>
            <span class="font-semibold text-primary">{{ getStatusCount('already_available') }}</span>
          </div>
          <div v-if="getStatusCount('already_requested') > 0" class="flex items-center gap-1.5">
            <span class="text-info">Already Req:</span>
            <span class="font-semibold text-info">{{ getStatusCount('already_requested') }}</span>
          </div>
          <div v-if="getStatusCount('requested') > 0" class="flex items-center gap-1.5">
            <span class="text-success">Requested:</span>
            <span class="font-semibold text-success">{{ getStatusCount('requested') }}</span>
          </div>
          <div v-if="getStatusCount('not_found') > 0" class="flex items-center gap-1.5">
            <span class="text-warning">Not Found:</span>
            <span class="font-semibold text-warning">{{ getStatusCount('not_found') }}</span>
          </div>
          <div v-if="getStatusCount('error') > 0" class="flex items-center gap-1.5">
            <span class="text-destructive">Errors:</span>
            <span class="font-semibold text-destructive">{{ getStatusCount('error') }}</span>
          </div>
          <div v-if="getStatusCount('skipped') > 0" class="flex items-center gap-1.5">
            <span class="text-muted-foreground">Skipped:</span>
            <span class="font-semibold text-muted-foreground">{{ getStatusCount('skipped') }}</span>
          </div>
        </div>
        <!-- Actions -->
        <div class="flex items-center justify-between">
          <p v-if="itemsWithMatches.length > 0" class="text-xs text-muted-foreground">
            <span class="text-success">
              {{ itemsWithMatches.filter(m => m.match).length }}
            </span>
            in unified_media database
          </p>
          <button
            @click="handleClose"
            class="px-4 py-2 text-foreground hover:bg-muted rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import StatusBadge from '~/components/ListSync/StatusBadge.vue'
interface Props {
  modelValue: boolean
  listIdentifier: string
  listName: string
  listId?: number  // Database ID of the list
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const isOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const items = ref<any[]>([])
const itemsWithMatches = ref<Array<{ item: any; match: any | null }>>([])
const loading = ref(false)
const checkingMatches = ref(false)
const error = ref('')

// Load items when modal opens
watch(isOpen, (newValue) => {
  if (newValue) {
    loadItems()
  } else {
    // Reset state when closing
    items.value = []
    itemsWithMatches.value = []
    error.value = ''
  }
})

const loadItems = async () => {
  loading.value = true
  error.value = ''
  
  try {
    // ALWAYS try to get items from database first (if list has been synced before)
    if (props.listId) {
      try {
        // Use server-side API route (not client-side fetch to avoid Vue Router interception)
        const dbResponse = await $fetch(`/api/trakt-lists/list-items?listId=${props.listId}`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json'
          }
        })
        
        if (dbResponse.success && dbResponse.items && dbResponse.items.length > 0) {
          // Use items from database - DO NOT fetch from Trakt API
          items.value = dbResponse.items || []
          // Check which items exist in unified_media (for status badges)
          await checkItemMatches()
          loading.value = false
          return
        } else if (dbResponse.success && dbResponse.items && dbResponse.items.length === 0) {
          // Database has no items - this list hasn't been synced yet
          error.value = 'This list has not been synced yet. Please sync it first to view items.'
          loading.value = false
          return
        }
      } catch (dbErr: any) {
        // If database lookup fails with 404, list hasn't been synced
        if (dbErr.statusCode === 404 || dbErr.data?.statusCode === 404) {
          error.value = 'This list has not been synced yet. Please sync it first to view items.'
          loading.value = false
          return
        }
        // For other errors, log but don't fall back to Trakt
        console.error('Error loading items from database:', dbErr)
        error.value = 'Failed to load items from database. Please sync this list first.'
        loading.value = false
        return
      }
    } else {
      // No listId provided - can't load from database
      error.value = 'List ID is required to load items from database. Please sync this list first.'
      loading.value = false
      return
    }
  } catch (err: any) {
    console.error('Error loading list items:', err)
    error.value = err.data?.message || err.message || 'Failed to load list items'
    loading.value = false
  }
}

const checkItemMatches = async () => {
  if (items.value.length === 0) return
  
  checkingMatches.value = true
  
  try {
    const response = await $fetch('/api/media-check-batch', {
      method: 'POST',
      body: {
        items: items.value.map(item => ({
          tmdb_id: item.tmdb_id,
          imdb_id: item.imdb_id,
          media_type: item.media_type
        }))
      }
    })
    
    if (response.success && response.matches) {
      // Map matches back to original full items
      // The API returns stripped items, so we need to match them back to our full items
      itemsWithMatches.value = items.value.map(fullItem => {
        // Find the corresponding match by matching tmdb_id/imdb_id
        const match = response.matches.find((m: any) => {
          if (fullItem.tmdb_id && m.item?.tmdb_id) {
            return m.item.tmdb_id === fullItem.tmdb_id && m.item.media_type === fullItem.media_type
          }
          if (fullItem.imdb_id && m.item?.imdb_id) {
            return m.item.imdb_id === fullItem.imdb_id && m.item.media_type === fullItem.media_type
          }
          return false
        })
        
        return {
          item: fullItem, // Use the full item with all fields (title, poster_path, etc.)
          match: match?.match || null
        }
      })
    } else {
      // If batch check fails, just use items without matches
      itemsWithMatches.value = items.value.map(item => ({ item, match: null }))
    }
  } catch (err: any) {
    console.error('Error checking item matches:', err)
    // Continue without matches
    itemsWithMatches.value = items.value.map(item => ({ item, match: null }))
  } finally {
    checkingMatches.value = false
  }
}

// Cache for poster URLs to avoid repeated fetches
const posterCache = ref<Map<string, string>>(new Map())

const getPosterUrl = (item: any) => {
  if (!item) return null
  
  // Check cache first
  const cacheKey = item.unified_media_id 
    ? `unified_${item.unified_media_id}` 
    : item.tmdb_id 
      ? `${item.media_type}_${item.tmdb_id}` 
      : `${item.title}_${item.year}`
  
  if (posterCache.value.has(cacheKey)) {
    return posterCache.value.get(cacheKey) || null
  }
  
  // ONLY use cached image from unified_media - NO external URLs
  if (item.has_poster_image && item.unified_media_id) {
    const cachedImageUrl = `/api/media-image/${item.unified_media_id}?type=poster`
    posterCache.value.set(cacheKey, cachedImageUrl)
    return cachedImageUrl
  }
  
  // No cached poster available - return null to show placeholder
  return null
}

const handleImageError = (event: Event) => {
  // Hide broken image
  const img = event.target as HTMLImageElement
  img.style.display = 'none'
}

const navigateToMedia = async (item: any, match: any | null) => {
  // If we already have a match from the batch check, use it
  if (match && match.id) {
    navigateTo(`/processed-media?mediaId=${match.id}`)
    handleClose()
    return
  }
  
  // Otherwise, try to find it (fallback)
  if (!item.tmdb_id && !item.imdb_id) {
    // If no IDs, can't navigate
    return
  }
  
  try {
    // Try to find the media in our database
    const response = await $fetch('/api/media-check', {
      query: {
        tmdbId: item.tmdb_id,
        mediaType: item.media_type
      }
    })
    
    if (response.success && response.exists && response.data?.id) {
      // Navigate to processed media page with the database ID
      navigateTo(`/processed-media?mediaId=${response.data.id}`)
    } else {
      // If not in database, still navigate but it won't have the modal open
      navigateTo('/processed-media')
    }
    
    // Close the modal
    handleClose()
  } catch (err) {
    console.error('Error checking media:', err)
    // Navigate anyway
    navigateTo('/processed-media')
    handleClose()
  }
}

const getStatusCount = (status: string) => {
  return itemsWithMatches.value.filter(m => m.item.status === status).length
}

const handleClose = () => {
  isOpen.value = false
}
</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>

