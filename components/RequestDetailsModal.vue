<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition-all duration-300"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition-all duration-200"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div v-if="isOpen" class="fixed inset-0 z-50 overflow-y-auto p-2 sm:p-4" @click="close">
        <!-- Overlay -->
        <div class="fixed inset-0 bg-black/80 backdrop-blur-sm"></div>
        
        <!-- Modal Content -->
        <div 
          class="relative mx-auto max-w-4xl my-2 sm:my-4 md:my-8 bg-card rounded-xl sm:rounded-2xl lg:rounded-3xl shadow-2xl overflow-hidden"
          @click.stop
        >
          <!-- Hero Section -->
          <div v-if="request" class="relative min-h-[400px] sm:min-h-[450px] md:h-96 lg:h-[500px] overflow-hidden bg-gradient-to-br from-primary/20 to-primary/10">
            <!-- Background Image -->
            <img
              v-if="getBackdropUrl(request)"
              :src="getBackdropUrl(request)"
              :alt="request.media?.title || 'Media backdrop'"
              class="absolute inset-0 w-full h-full object-cover opacity-20"
            />
            
            <!-- Top Right Buttons -->
            <div class="absolute top-3 sm:top-4 right-3 sm:right-4 z-10 flex items-center gap-2">
              <!-- Close Button -->
              <Button 
                @click="close" 
                variant="outline"
                class="w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-background/90 backdrop-blur-md hover:bg-background border-border hover:border-red-500/50 hover:bg-red-500/10 transition-all duration-200"
              >
                <AppIcon icon="lucide:x" size="20" class="sm:w-6 sm:h-6 text-foreground hover:text-red-500 transition-colors duration-200" />
              </Button>
            </div>
            
            <!-- Content -->
            <div class="relative h-full flex flex-col sm:flex-row items-center justify-center px-4 sm:px-5 md:px-6 lg:px-8 pt-2 sm:pt-3 md:pt-4 lg:pt-5 pb-3 sm:pb-4 md:pb-5 lg:pb-6">
              <div class="flex flex-col sm:flex-row items-center gap-4 sm:gap-5 md:gap-6 w-full">
                <!-- Poster -->
                <div class="flex-shrink-0 w-full sm:w-auto flex justify-center sm:justify-start">
                  <div class="w-28 h-40 sm:w-32 sm:h-44 md:w-36 md:h-52 lg:w-40 lg:h-60 rounded-xl sm:rounded-2xl overflow-hidden shadow-2xl ring-2 ring-border">
                    <img
                      v-if="getPosterUrl(request)"
                      :src="getPosterUrl(request)"
                      :alt="request.media?.title || 'Media poster'"
                      class="w-full h-full object-cover"
                    />
                    <div
                      v-else
                      class="w-full h-full bg-muted flex items-center justify-center"
                    >
                      <AppIcon 
                        :icon="request.media?.media_type === 'movie' ? 'lucide:film' : 'lucide:tv'" 
                        size="32" 
                        class="sm:w-10 sm:h-10 md:w-12 md:h-12 text-muted-foreground" 
                      />
                    </div>
                  </div>
                </div>
                
                <!-- Info -->
                <div class="flex-1 w-full min-w-0">
                  <div class="flex gap-2 sm:gap-2.5 mb-3 sm:mb-4 md:mb-5 flex-wrap">
                    <span 
                      class="px-2.5 sm:px-3 py-1 text-[10px] sm:text-xs font-semibold bg-muted text-foreground rounded-full border border-border whitespace-nowrap"
                    >
                      {{ request.media?.media_type === 'movie' ? 'MOVIE' : 'TV SHOW' }}
                    </span>
                    <span v-if="getMediaYear(request)" class="px-2.5 sm:px-3 py-1 text-[10px] sm:text-xs font-semibold bg-muted text-foreground rounded-full border border-border whitespace-nowrap">
                      {{ getMediaYear(request) }}
                    </span>
                    <span 
                      v-if="request.media?.vote_average"
                      class="px-2.5 sm:px-3 py-1 text-[10px] sm:text-xs font-semibold bg-amber-500/20 text-amber-400 rounded-full border border-amber-500/30 flex items-center gap-1 whitespace-nowrap"
                    >
                      <AppIcon icon="lucide:star" size="10" class="sm:w-3 sm:h-3 fill-current flex-shrink-0" />
                      <span>{{ formatVoteAverage(request.media.vote_average) }}</span>
                    </span>
                    <span 
                      :class="getStatusLabelClass(request)"
                      class="px-2.5 sm:px-3 py-1 text-[10px] sm:text-xs font-semibold rounded-full border whitespace-nowrap"
                    >
                      {{ request.status_label || 'Unknown' }}
                    </span>
                    <span v-if="request.is4k" class="px-2.5 sm:px-3 py-1 text-[10px] sm:text-xs font-semibold bg-purple-500/20 text-purple-400 rounded-full border border-purple-500/30 whitespace-nowrap">
                      4K
                    </span>
                  </div>
                  
                  <h2 class="text-xl sm:text-2xl md:text-3xl lg:text-4xl font-bold text-foreground mb-2 sm:mb-3 leading-tight break-words pr-8 sm:pr-0">
                    {{ request.media?.title || 'Unknown Title' }}
                  </h2>
                  
                  <div class="flex items-center gap-2 sm:gap-3 md:gap-4 mb-3 sm:mb-4 flex-wrap">
                    <span v-if="request.media?.release_date || request.media?.first_air_date" class="inline-flex items-center gap-1 text-xs sm:text-sm text-muted-foreground whitespace-nowrap">
                      <AppIcon icon="lucide:calendar" size="12" class="sm:w-3.5 sm:h-3.5 flex-shrink-0" />
                      <span class="hidden sm:inline">{{ formatDate(request.media?.release_date || request.media?.first_air_date) }}</span>
                      <span class="sm:hidden">{{ getMediaYear(request) }}</span>
                    </span>
                    <span v-if="request.media?.runtime && request.media.media_type === 'movie'" class="inline-flex items-center gap-1 text-xs sm:text-sm text-muted-foreground whitespace-nowrap">
                      <AppIcon icon="lucide:clock" size="12" class="sm:w-3.5 sm:h-3.5 flex-shrink-0" />
                      {{ request.media.runtime }} min
                    </span>
                    <span v-if="request.media?.number_of_episodes && request.media.media_type === 'tv'" class="inline-flex items-center gap-1 text-xs sm:text-sm text-muted-foreground whitespace-nowrap">
                      <AppIcon icon="lucide:tv" size="12" class="sm:w-3.5 sm:h-3.5 flex-shrink-0" />
                      {{ request.media.number_of_episodes }} Episodes
                    </span>
                    <!-- Genres as badges -->
                    <div v-if="request.media?.genres && request.media.genres.length > 0" class="flex items-center gap-1.5 sm:gap-2 flex-wrap">
                      <span 
                        v-for="genre in request.media.genres.slice(0, 3)" 
                        :key="genre.id || genre"
                        class="px-1.5 sm:px-2 py-0.5 sm:py-1 text-[10px] sm:text-xs font-medium bg-muted text-foreground rounded-full border border-border capitalize whitespace-nowrap"
                      >
                        {{ typeof genre === 'string' ? genre : genre.name }}
                      </span>
                      <span v-if="request.media.genres.length > 3" class="px-1.5 sm:px-2 py-0.5 sm:py-1 text-[10px] sm:text-xs font-medium bg-muted text-muted-foreground rounded-full border border-border whitespace-nowrap">
                        +{{ request.media.genres.length - 3 }} more
                      </span>
                    </div>
                  </div>
                  
                  <p v-if="request.media?.overview" class="text-xs sm:text-sm md:text-base text-muted-foreground line-clamp-2 sm:line-clamp-3 lg:line-clamp-none mb-3 sm:mb-4 max-w-2xl">
                    {{ request.media.overview }}
                  </p>
                  
                  <!-- Action Buttons -->
                  <div class="mt-2 sm:mt-3 flex flex-wrap gap-2 flex-shrink-0">
                    <Button
                      v-if="overseerrBaseUrl && request.media?.tmdb_id"
                      @click="viewInOverseerr"
                      size="sm"
                      variant="outline"
                      class="bg-primary/20 border-primary/30 text-primary hover:bg-primary/30"
                    >
                      <AppIcon icon="lucide:external-link" size="14" class="mr-1.5" />
                      View in Overseerr
                    </Button>
                    <Button
                      @click="handleRetrigger"
                      :disabled="isRetriggering"
                      size="sm"
                      variant="outline"
                      class="bg-amber-500/20 border-amber-500/30 text-amber-400 hover:bg-amber-500/30"
                    >
                      <AppIcon 
                        v-if="isRetriggering"
                        icon="lucide:loader-2" 
                        size="14" 
                        class="mr-1.5 animate-spin"
                      />
                      <AppIcon 
                        v-else
                        icon="lucide:refresh-cw" 
                        size="14" 
                        class="mr-1.5"
                      />
                      {{ isRetriggering ? 'Retriggering...' : 'Retrigger Request' }}
                    </Button>
                    <Button
                      @click="handleDelete"
                      :disabled="isDeleting"
                      size="sm"
                      variant="outline"
                      class="bg-red-500/20 border-red-500/30 text-red-400 hover:bg-red-500/30"
                    >
                      <AppIcon 
                        v-if="isDeleting"
                        icon="lucide:loader-2" 
                        size="14" 
                        class="mr-1.5 animate-spin"
                      />
                      <AppIcon 
                        v-else
                        icon="lucide:trash-2" 
                        size="14" 
                        class="mr-1.5"
                      />
                      {{ isDeleting ? 'Deleting...' : 'Delete Request' }}
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Body -->
          <div v-if="request" class="px-4 sm:px-5 md:px-6 py-3 sm:py-4 space-y-3">
            <!-- Request Info Card -->
            <div class="bg-gradient-to-br from-muted to-muted/50 rounded-xl p-4 border border-border">
              <div class="flex items-center gap-2 mb-2">
                <div class="w-8 h-8 bg-primary/10 rounded-lg flex items-center justify-center">
                  <AppIcon icon="lucide:info" size="18" class="text-primary" />
                </div>
                <div>
                  <h3 class="text-sm font-bold text-foreground">Request Details</h3>
                </div>
              </div>
              
              <div class="grid grid-cols-1 lg:grid-cols-2 gap-3">
                <!-- Left Column -->
                <div class="space-y-1.5">
                  <div class="flex items-center justify-between">
                    <span class="text-xs text-muted-foreground">Request ID</span>
                    <span class="text-xs font-medium text-foreground">{{ request.id || request.request_id }}</span>
                  </div>
                  
                  <div v-if="request.requested_by" class="flex items-center justify-between">
                    <span class="text-xs text-muted-foreground">Requested By</span>
                    <span class="text-xs font-medium text-foreground">{{ request.requested_by.displayName || request.requested_by.username || request.requested_by.email || 'Unknown' }}</span>
                  </div>
                  
                  <div class="flex items-center justify-between">
                    <span class="text-xs text-muted-foreground">Status</span>
                    <span :class="getStatusLabelClass(request)" class="px-2 py-0.5 text-[10px] font-semibold rounded-full">
                      {{ request.status_label || 'Unknown' }}
                    </span>
                  </div>
                  
                  <div v-if="request.media?.media_status_label" class="flex items-center justify-between">
                    <span class="text-xs text-muted-foreground">Media Status</span>
                    <span class="text-xs font-medium text-foreground">{{ request.media.media_status_label }}</span>
                  </div>
                  
                  <div v-if="request.created_at" class="flex items-center justify-between">
                    <span class="text-xs text-muted-foreground">Created</span>
                    <span class="text-xs font-medium text-foreground">{{ formatDate(request.created_at) }}</span>
                  </div>
                </div>
                
                <!-- Right Column -->
                <div class="space-y-1.5">
                  <div v-if="request.media?.tmdb_id" class="flex items-center justify-between">
                    <span class="text-xs text-muted-foreground">TMDB ID</span>
                    <a 
                      :href="`https://www.themoviedb.org/${request.media.media_type === 'movie' ? 'movie' : 'tv'}/${request.media.tmdb_id}`"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="text-xs font-medium text-primary hover:underline"
                    >
                      {{ request.media.tmdb_id }}
                      <AppIcon icon="lucide:external-link" size="10" class="inline ml-1" />
                    </a>
                  </div>
                  
                  <div v-if="request.media?.tvdb_id" class="flex items-center justify-between">
                    <span class="text-xs text-muted-foreground">TVDB ID</span>
                    <span class="text-xs font-medium text-foreground">{{ request.media.tvdb_id }}</span>
                  </div>
                  
                  <div v-if="request.is4k !== undefined" class="flex items-center justify-between">
                    <span class="text-xs text-muted-foreground">4K Request</span>
                    <span class="text-xs font-medium text-foreground">{{ request.is4k ? 'Yes' : 'No' }}</span>
                  </div>
                  
                  <div v-if="request.updated_at" class="flex items-center justify-between">
                    <span class="text-xs text-muted-foreground">Last Updated</span>
                    <span class="text-xs font-medium text-foreground">{{ formatDate(request.updated_at) }}</span>
                  </div>
                  
                  <div v-if="overseerrBaseUrl && request.media?.tmdb_id" class="flex items-center justify-between mt-1.5">
                    <span class="text-xs text-muted-foreground">Overseerr</span>
                    <a 
                      :href="getOverseerrUrl(request)!" 
                      target="_blank" 
                      rel="noopener noreferrer"
                      class="inline-flex items-center gap-1 text-xs text-primary hover:text-primary/80 transition-colors"
                    >
                      <AppIcon icon="lucide:external-link" size="10" />
                      View Request
                    </a>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Media Details Card -->
            <div v-if="request.media" class="bg-gradient-to-br from-muted to-muted/50 rounded-xl p-4 border border-border">
              <div class="flex items-center gap-2 mb-2">
                <div class="w-8 h-8 bg-indigo-600/10 rounded-lg flex items-center justify-center">
                  <AppIcon icon="lucide:file-text" size="18" class="text-indigo-600" />
                </div>
                <div>
                  <h3 class="text-sm font-bold text-foreground">Media Information</h3>
                </div>
              </div>
              
              <div class="space-y-3">
                <!-- Overview -->
                <div v-if="request.media.overview">
                  <p class="text-xs text-muted-foreground leading-relaxed">{{ request.media.overview }}</p>
                </div>
                
                <!-- Additional Media Info -->
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div v-if="request.media.vote_count">
                    <p class="text-xs text-muted-foreground mb-0.5">Vote Count</p>
                    <p class="text-xs font-medium text-foreground">{{ formatNumber(request.media.vote_count) }}</p>
                  </div>
                  <div v-if="request.media.popularity">
                    <p class="text-xs text-muted-foreground mb-0.5">Popularity</p>
                    <p class="text-xs font-medium text-foreground">{{ request.media.popularity.toFixed(1) }}</p>
                  </div>
                  <div v-if="request.media.original_language">
                    <p class="text-xs text-muted-foreground mb-0.5">Original Language</p>
                    <p class="text-xs font-medium text-foreground uppercase">{{ request.media.original_language }}</p>
                  </div>
                  <div v-if="request.media.number_of_seasons && request.media.media_type === 'tv'">
                    <p class="text-xs text-muted-foreground mb-0.5">Seasons</p>
                    <p class="text-xs font-medium text-foreground">{{ request.media.number_of_seasons }}</p>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Seasons Info for TV Shows -->
            <div v-if="request.media?.media_type === 'tv' && request.all_seasons && request.all_seasons.length > 0" class="bg-gradient-to-br from-muted to-muted/50 rounded-xl p-4 border border-border">
              <div class="flex items-center gap-2 mb-3">
                <div class="w-8 h-8 bg-purple-600/10 rounded-lg flex items-center justify-center">
                  <AppIcon icon="lucide:tv" size="18" class="text-purple-600" />
                </div>
                <div>
                  <h3 class="text-sm font-bold text-foreground">Requested Seasons</h3>
                </div>
              </div>
              
              <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 max-h-64 overflow-y-auto">
                <div
                  v-for="season in request.all_seasons"
                  :key="season.id || season.seasonNumber"
                  class="p-2 bg-card rounded-lg border border-border"
                >
                  <p class="text-xs font-semibold text-foreground">Season {{ season.seasonNumber }}</p>
                  <p v-if="season.episodeCount" class="text-[10px] text-muted-foreground">{{ season.episodeCount }} Episodes</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import Button from '~/components/ui/Button.vue'
import { useConfig } from '~/composables/useConfig'
import { useToast } from '~/composables/useToast'

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
    release_date?: string
    first_air_date?: string
    poster_path?: string
    backdrop_path?: string
    overview?: string
    vote_average?: number
    vote_count?: number
    popularity?: number
    runtime?: number
    genres?: Array<{ id: number; name: string }>
    number_of_seasons?: number
    number_of_episodes?: number
    original_language?: string
  }
  all_seasons?: Array<{
    id: number
    seasonNumber: number
    name: string
    episodeCount: number
  }>
  is4k: boolean
}

interface Props {
  request: RequestItem | null
  isOpen: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  close: []
  delete: [requestId: number]
  retrigger: [requestId: number]
}>()

const { overseerrBaseUrl, fetchConfig } = useConfig()
const { toast } = useToast()

const isDeleting = ref(false)
const isRetriggering = ref(false)

// Fetch config when modal opens
watch(() => props.isOpen, async (isOpen) => {
  if (isOpen) {
    fetchConfig()
  }
}, { immediate: true })

const close = () => {
  emit('close')
}

const getPosterUrl = (request: RequestItem) => {
  const posterPath = request.media?.poster_path
  if (!posterPath) return null
  if (posterPath.startsWith('http')) return posterPath
  return `https://image.tmdb.org/t/p/w500${posterPath}`
}

const getBackdropUrl = (request: RequestItem) => {
  const backdropPath = request.media?.backdrop_path
  if (!backdropPath) return null
  if (backdropPath.startsWith('http')) return backdropPath
  return `https://image.tmdb.org/t/p/w1280${backdropPath}`
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
  if (!dateString) return 'N/A'
  try {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
  } catch {
    return dateString
  }
}

const formatVoteAverage = (voteAverage?: number) => {
  if (!voteAverage) return 'N/A'
  return voteAverage.toFixed(1)
}

const formatNumber = (num: number) => {
  return new Intl.NumberFormat().format(num)
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

const getOverseerrUrl = (request: RequestItem) => {
  if (!overseerrBaseUrl.value || !request.media?.tmdb_id) return null
  const mediaType = request.media.media_type === 'movie' ? 'movie' : 'tv'
  return `${overseerrBaseUrl.value}/${mediaType}/${request.media.tmdb_id}`
}

const viewInOverseerr = () => {
  if (props.request) {
    const url = getOverseerrUrl(props.request)
    if (url) {
      window.open(url, '_blank', 'noopener,noreferrer')
    }
  }
}

const handleDelete = async () => {
  if (!props.request) return
  
  const confirmed = confirm(
    `Are you sure you want to delete this request?\n\n` +
    `Request: ${props.request.media?.title || 'Unknown'}\n` +
    `This action cannot be undone.`
  )
  
  if (!confirmed) return
  
  isDeleting.value = true
  try {
    emit('delete', props.request.id || props.request.request_id)
  } finally {
    isDeleting.value = false
  }
}

const handleRetrigger = async () => {
  if (!props.request) return
  
  const confirmed = confirm(
    `Are you sure you want to re-trigger this request?\n\n` +
    `Request: ${props.request.media?.title || 'Unknown'}\n` +
    `This will update the request and trigger processing again.`
  )
  
  if (!confirmed) return
  
  isRetriggering.value = true
  try {
    emit('retrigger', props.request.id || props.request.request_id)
  } finally {
    isRetriggering.value = false
  }
}

// Close on Escape key
const handleEscape = (e: KeyboardEvent) => {
  if (e.key === 'Escape' && props.isOpen) {
    close()
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleEscape)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleEscape)
})
</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.line-clamp-3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>

