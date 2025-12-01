<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="isOpen"
        class="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 bg-black/50 backdrop-blur-sm"
        @click="close"
      >
        <div
          class="relative max-w-4xl w-full max-h-[95vh] sm:max-h-[90vh] overflow-y-auto bg-card border border-border rounded-lg sm:rounded-xl lg:rounded-2xl shadow-2xl"
          @click.stop
        >
          <!-- Header -->
          <div class="sticky top-0 z-10 flex items-center justify-between p-3 sm:p-4 lg:p-6 border-b border-border bg-card backdrop-blur-sm">
            <h2 class="text-lg sm:text-xl lg:text-2xl font-bold text-foreground pr-2 truncate">
              {{ media ? getMediaTitle(media) : '' }}
            </h2>
            <button
              @click="close"
              class="p-1.5 sm:p-2 hover:bg-muted rounded-lg transition-colors flex-shrink-0"
            >
              <Icon name="mdi:close" class="w-5 h-5 sm:w-6 sm:h-6" />
            </button>
          </div>

          <!-- Content -->
          <div v-if="media" class="p-3 sm:p-4 lg:p-6">
            <!-- Media Info -->
            <div class="flex flex-col sm:flex-row gap-4 sm:gap-6 mb-4 sm:mb-6">
              <!-- Poster -->
              <div class="flex-shrink-0 self-center sm:self-start">
                <img
                  v-if="getPosterUrl(media.posterPath)"
                  :src="getPosterUrl(media.posterPath)"
                  :alt="getMediaTitle(media)"
                  class="w-32 h-48 sm:w-40 sm:h-60 lg:w-48 lg:h-72 rounded-lg"
                />
                <div v-else class="w-32 h-48 sm:w-40 sm:h-60 lg:w-48 lg:h-72 bg-muted rounded-lg flex items-center justify-center">
                  <Icon name="mdi:image-off" class="w-12 h-12 sm:w-16 sm:h-16 text-muted-foreground" />
                </div>
              </div>

              <!-- Details -->
              <div class="flex-1 min-w-0">
                <div class="flex flex-wrap items-center gap-1.5 sm:gap-2 mb-3 sm:mb-4">
                  <span class="px-2 sm:px-3 py-0.5 sm:py-1 bg-primary text-primary-foreground text-xs sm:text-sm font-semibold rounded-full">
                    {{ getMediaTypeLabel(media) }}
                  </span>
                  <span v-if="media.voteAverage" class="flex items-center gap-1 px-2 sm:px-3 py-0.5 sm:py-1 bg-yellow-500/20 text-yellow-400 text-xs sm:text-sm font-semibold rounded-full">
                    <Icon name="mdi:star" class="w-3 h-3 sm:w-4 sm:h-4" />
                    {{ formatVoteAverage(media.voteAverage) }}
                  </span>
                  <span v-if="getMediaYear(media)" class="px-2 sm:px-3 py-0.5 sm:py-1 bg-muted text-xs sm:text-sm rounded-full">
                    {{ getMediaYear(media) }}
                  </span>
                </div>

                <p v-if="media.overview" class="text-sm sm:text-base text-muted-foreground mb-4 sm:mb-6 line-clamp-3 sm:line-clamp-4">
                  {{ media.overview }}
                </p>

                <!-- Availability Status -->
                <div class="space-y-2 sm:space-y-3">
                  <div class="p-3 sm:p-4 bg-muted rounded-lg">
                    <h3 class="text-sm sm:text-base font-semibold text-foreground mb-2 sm:mb-3">Availability Status</h3>
                    
                    <!-- If mediaInfo exists -->
                    <div v-if="media.mediaInfo" class="space-y-2">
                      <!-- Database Status -->
                      <div class="flex flex-wrap items-center gap-1.5 sm:gap-2">
                        <Icon
                          v-if="isLoadingStatus"
                          name="mdi:loading"
                          class="w-4 h-4 sm:w-5 sm:h-5 animate-spin text-muted-foreground flex-shrink-0"
                        />
                        <Icon
                          v-else
                          :name="inDatabase ? 'mdi:database-check' : 'mdi:database-remove'"
                          :class="inDatabase ? 'text-primary' : 'text-muted-foreground'"
                          class="w-4 h-4 sm:w-5 sm:h-5 flex-shrink-0"
                        />
                        <span class="text-xs sm:text-sm font-medium text-foreground">In SeerrBridge Database:</span>
                        <span :class="inDatabase ? 'bg-success/20 text-success' : 'bg-muted/20 text-muted-foreground'" class="px-1.5 sm:px-2 py-0.5 sm:py-1 text-[10px] sm:text-xs font-semibold rounded">
                          {{ isLoadingStatus ? 'Checking...' : (inDatabase ? 'Yes' : 'No') }}
                        </span>
                      </div>

                      <!-- Overseerr Status -->
                      <div class="flex flex-wrap items-center gap-1.5 sm:gap-2">
                        <Icon
                          :name="getStatusIcon(media.mediaInfo.status)"
                          :class="getStatusColor(media.mediaInfo.status)"
                          class="w-4 h-4 sm:w-5 sm:h-5 flex-shrink-0"
                        />
                        <span class="text-xs sm:text-sm font-medium text-foreground">Overseerr Status:</span>
                        <span :class="getStatusBadgeClass(media.mediaInfo.status)" class="px-1.5 sm:px-2 py-0.5 sm:py-1 text-[10px] sm:text-xs font-semibold rounded">
                          {{ getStatusText(media.mediaInfo.status) }}
                        </span>
                      </div>

                      <!-- 4K Status if applicable -->
                      <div v-if="media.mediaInfo.status4k" class="flex flex-wrap items-center gap-1.5 sm:gap-2">
                        <Icon
                          name="mdi:4k-box"
                          class="w-4 h-4 sm:w-5 sm:h-5 text-primary flex-shrink-0"
                        />
                        <span class="text-xs sm:text-sm font-medium text-foreground">4K Status:</span>
                        <span :class="getStatusBadgeClass(media.mediaInfo.status4k)" class="px-1.5 sm:px-2 py-0.5 sm:py-1 text-[10px] sm:text-xs font-semibold rounded">
                          {{ getStatusText(media.mediaInfo.status4k) }}
                        </span>
                      </div>
                    </div>

                    <!-- If mediaInfo doesn't exist -->
                    <div v-else>
                      <div class="flex items-center gap-1.5 sm:gap-2">
                        <Icon
                          name="mdi:information-outline"
                          class="w-4 h-4 sm:w-5 sm:h-5 text-muted-foreground flex-shrink-0"
                        />
                        <span class="text-xs sm:text-sm font-medium text-muted-foreground">Not available in database</span>
                      </div>
                    </div>
                  </div>

                  <!-- Request Button -->
                  <button
                    v-if="canRequest"
                    @click="handleRequest"
                    :disabled="isRequesting"
                    class="w-full py-2.5 sm:py-3 px-4 sm:px-6 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium flex items-center justify-center gap-2 text-sm sm:text-base"
                  >
                    <Icon v-if="!isRequesting" name="mdi:plus-circle" class="w-4 h-4 sm:w-5 sm:h-5" />
                    <Icon v-else name="mdi:loading" class="w-4 h-4 sm:w-5 sm:h-5 animate-spin" />
                    <span>{{ isRequesting ? 'Requesting...' : 'Request this ' + getMediaTypeLabel(media) }}</span>
                  </button>

                  <!-- Already Available -->
                  <div
                    v-if="isAvailable"
                    class="w-full py-2.5 sm:py-3 px-4 sm:px-6 bg-success/20 text-success rounded-lg flex items-center justify-center gap-2"
                  >
                    <Icon name="mdi:check-circle" class="w-4 h-4 sm:w-5 sm:h-5" />
                    <span class="text-sm sm:text-base font-medium">Already Available</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Season Selection for TV Shows -->
            <div v-if="media.mediaType === 'tv' && seasons.length > 0" class="mt-4 sm:mt-6 pt-4 sm:pt-6 border-t border-border">
              <h3 class="text-base sm:text-lg font-semibold text-foreground mb-3 sm:mb-4">Select Seasons</h3>
              <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2 sm:gap-3 max-h-64 sm:max-h-96 overflow-y-auto p-2 sm:p-4 bg-muted rounded-lg">
                <label
                  v-for="season in seasons"
                  :key="season.id"
                  class="flex items-center gap-1.5 sm:gap-2 p-2 sm:p-3 bg-card border border-border rounded-lg hover:border-primary transition-colors cursor-pointer"
                  :class="{ 'border-primary bg-primary/10': selectedSeasons.includes(season.seasonNumber) }"
                >
                  <input
                    v-model="selectedSeasons"
                    type="checkbox"
                    :value="season.seasonNumber"
                    class="w-3.5 h-3.5 sm:w-4 sm:h-4 text-primary rounded focus:ring-primary flex-shrink-0"
                  />
                  <span class="text-xs sm:text-sm font-medium text-foreground truncate">
                    Season {{ season.seasonNumber }}
                  </span>
                  <span v-if="season.episodeCount" class="text-[10px] sm:text-xs text-muted-foreground flex-shrink-0">
                    ({{ season.episodeCount }})
                  </span>
                </label>
              </div>
            </div>

            <!-- Additional Info -->
            <div v-if="media.mediaInfo" class="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4 mt-4 sm:mt-6 pt-4 sm:pt-6 border-t border-border">
              <div>
                <p class="text-xs sm:text-sm text-muted-foreground mb-0.5 sm:mb-1">TMDB ID</p>
                <p class="text-sm sm:text-base text-foreground font-medium break-all">{{ media.mediaInfo.tmdbId }}</p>
              </div>
              <div>
                <p class="text-xs sm:text-sm text-muted-foreground mb-0.5 sm:mb-1">TVDB ID</p>
                <p class="text-sm sm:text-base text-foreground font-medium">{{ media.mediaInfo.tvdbId || 'N/A' }}</p>
              </div>
              <div v-if="media.imdbId">
                <p class="text-xs sm:text-sm text-muted-foreground mb-0.5 sm:mb-1">IMDB ID</p>
                <p class="text-sm sm:text-base text-foreground font-medium break-all">{{ media.imdbId }}</p>
                <!-- Debrid Media Manager Link -->
                <div class="mt-1.5 sm:mt-2">
                  <a 
                    :href="getDebridMediaManagerUrl(media)" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    class="inline-flex items-center gap-1 text-[10px] sm:text-xs text-primary hover:text-primary/80 transition-colors"
                  >
                    <Icon name="mdi:external-link" class="w-3 h-3 flex-shrink-0" />
                    <span class="break-all">View in Debrid Media Manager</span>
                  </a>
                </div>
              </div>
              <div v-if="media.mediaInfo.mediaType === 'tv'">
                <p class="text-xs sm:text-sm text-muted-foreground mb-0.5 sm:mb-1">First Air Date</p>
                <p class="text-sm sm:text-base text-foreground font-medium">{{ formatDate(media.firstAirDate) }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
interface MediaResult {
  id: number
  mediaType: 'movie' | 'tv' | 'person'
  title?: string
  name?: string
  originalTitle?: string
  originalName?: string
  posterPath?: string | null
  overview?: string
  voteAverage?: number
  releaseDate?: string
  firstAirDate?: string
  mediaInfo?: {
    id: number
    tmdbId: number
    tvdbId: number | null
    status: number
    status4k?: number
    mediaType: string
    imdbId?: string
  }
}

interface Props {
  media: MediaResult | null
  isOpen: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  close: []
  request: [mediaId: number, mediaType: string, seasons?: number[]]
}>()

const isRequesting = ref(false)
const inDatabase = ref(false)
const databaseStatus = ref<number | null>(null)
const isLoadingStatus = ref(false)
const seasons = ref<any[]>([])
const selectedSeasons = ref<number[]>([])
const isLoadingSeasons = ref(false)

const close = () => {
  emit('close')
}

// Check database status and fetch seasons when modal opens
watch(() => props.isOpen, async (isOpen) => {
  if (isOpen && props.media) {
    await checkDatabaseStatus()
    if (props.media.mediaType === 'tv') {
      await fetchSeasons()
    }
  }
})

const checkDatabaseStatus = async () => {
  if (!props.media) return
  
  isLoadingStatus.value = true
  try {
    const tmdbId = props.media.mediaInfo?.tmdbId || props.media.id
    
    const response = await $fetch('/api/media-check', {
      query: {
        tmdbId,
        mediaType: props.media.mediaType
      }
    })
    
    if (response.success) {
      inDatabase.value = response.exists
      databaseStatus.value = response.data?.status || null
    }
  } catch (error) {
    console.error('Error checking database status:', error)
    inDatabase.value = false
  } finally {
    isLoadingStatus.value = false
  }
}

const getMediaTitle = (media: MediaResult) => {
  if (media.mediaType === 'movie') {
    return media.title || media.originalTitle || 'Unknown Movie'
  } else if (media.mediaType === 'tv') {
    return media.name || media.originalName || 'Unknown Show'
  }
  return 'Unknown'
}

const getMediaYear = (media: MediaResult) => {
  if (media.mediaType === 'movie' && media.releaseDate) {
    return media.releaseDate.split('-')[0]
  } else if (media.mediaType === 'tv' && media.firstAirDate) {
    return media.firstAirDate.split('-')[0]
  }
  return ''
}

const getMediaTypeLabel = (media: MediaResult) => {
  if (media.mediaType === 'movie') return 'Movie'
  if (media.mediaType === 'tv') return 'TV Show'
  return 'Unknown'
}

const getPosterUrl = (posterPath?: string | null) => {
  if (!posterPath) return ''
  return `https://image.tmdb.org/t/p/w500${posterPath}`
}

const formatVoteAverage = (voteAverage?: number) => {
  if (!voteAverage) return 'N/A'
  return voteAverage.toFixed(1)
}

const getStatusText = (status: number) => {
  // 1 = unknown, 2 = pending, 3 = processing, 4 = partially available, 5 = available
  const statusLabels: Record<number, string> = {
    1: 'Unknown',
    2: 'Pending',
    3: 'Processing',
    4: 'Partially Available',
    5: 'Available'
  }
  return statusLabels[status] || 'Unknown'
}

const getStatusIcon = (status: number) => {
  const icons: Record<number, string> = {
    1: 'mdi:help-circle',
    2: 'mdi:clock-outline',
    3: 'mdi:loading',
    4: 'mdi:alert-circle',
    5: 'mdi:check-circle'
  }
  return icons[status] || 'mdi:help-circle'
}

const getStatusColor = (status: number) => {
  const colors: Record<number, string> = {
    1: 'text-muted-foreground',
    2: 'text-yellow-400',
    3: 'text-blue-400',
    4: 'text-orange-400',
    5: 'text-green-400'
  }
  return colors[status] || 'text-muted-foreground'
}

const getStatusBadgeClass = (status: number) => {
  const classes: Record<number, string> = {
    1: 'bg-muted/20 text-muted-foreground',
    2: 'bg-yellow-500/20 text-yellow-400',
    3: 'bg-blue-500/20 text-blue-400',
    4: 'bg-orange-500/20 text-orange-400',
    5: 'bg-green-500/20 text-green-400'
  }
  return classes[status] || 'bg-muted/20 text-muted-foreground'
}

const canRequest = computed(() => {
  // Can always request if there's no mediaInfo (not in database)
  if (!props.media?.mediaInfo) return true
  // Can request if status is not 5 (available)
  return props.media.mediaInfo.status !== 5
})

const isAvailable = computed(() => {
  // Available if mediaInfo exists and status is 5
  return props.media?.mediaInfo && props.media.mediaInfo.status === 5
})

const fetchSeasons = async () => {
  if (!props.media || props.media.mediaType !== 'tv') return
  
  isLoadingSeasons.value = true
  try {
    // Get TMDB ID from media
    const tmdbId = props.media.mediaInfo?.tmdbId || props.media.id
    
    // Fetch TV details from our API
    const response = await $fetch('/api/tv-details', {
      query: {
        tmdbId
      }
    })
    
    if (response.success && response.data?.seasons) {
      // Filter out season 0 (specials) and sort by season number
      seasons.value = response.data.seasons
        .filter((s: any) => s.seasonNumber > 0)
        .sort((a: any, b: any) => a.seasonNumber - b.seasonNumber)
    }
  } catch (error) {
    console.error('Error fetching seasons:', error)
  } finally {
    isLoadingSeasons.value = false
  }
}

const handleRequest = async () => {
  if (!props.media) return
  
  isRequesting.value = true
  
  try {
    // Emit the request event (parent will handle the API call and toast)
    emit('request', props.media.id, props.media.mediaType, selectedSeasons.value)
    
    // Wait a moment for the request to complete
    await new Promise(resolve => setTimeout(resolve, 1500))
  } finally {
    isRequesting.value = false
    // Only close if not requesting (request might have failed)
    if (!isRequesting.value) {
      close()
    }
  }
}

const formatDate = (date?: string) => {
  if (!date) return 'N/A'
  return new Date(date).toLocaleDateString()
}

const getDebridMediaManagerUrl = (media: MediaResult) => {
  if (!media.imdbId) return '#'
  
  const baseUrl = 'https://debridmediamanager.com'
  const mediaType = media.mediaType === 'movie' ? 'movie' : 'show'
  
  return `${baseUrl}/${mediaType}/${media.imdbId}`
}
</script>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: all 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from > div,
.modal-leave-to > div {
  transform: scale(0.9);
}
</style>

