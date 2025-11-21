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
          <div v-if="movie" class="relative min-h-[400px] sm:min-h-[450px] md:h-96 lg:h-[500px] overflow-hidden bg-gradient-to-br from-primary/20 to-primary/10">
            <!-- Background Image -->
            <img
              v-if="getFanartUrl(movie)"
              :src="getFanartUrl(movie)"
              :alt="movie.title"
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
                      v-if="getPosterUrl(movie)"
                      :src="getPosterUrl(movie)"
                      :alt="movie.title"
                      class="w-full h-full object-cover"
                    />
                    <div
                      v-else
                      class="w-full h-full bg-muted flex items-center justify-center"
                    >
                      <AppIcon icon="lucide:film" size="32" class="sm:w-10 sm:h-10 md:w-12 md:h-12 text-muted-foreground" />
                    </div>
                  </div>
                </div>
                
                <!-- Info -->
                <div class="flex-1 w-full min-w-0">
                  <div class="flex gap-2 sm:gap-2.5 mb-3 sm:mb-4 md:mb-5 flex-wrap">
                    <span class="px-2.5 sm:px-3 py-1 text-[10px] sm:text-xs font-semibold bg-muted text-foreground rounded-full border border-border whitespace-nowrap">
                      MOVIE
                    </span>
                    <span v-if="movie.year" class="px-2.5 sm:px-3 py-1 text-[10px] sm:text-xs font-semibold bg-muted text-foreground rounded-full border border-border whitespace-nowrap">
                      {{ movie.year }}
                    </span>
                    <span 
                      v-if="movie.trakt?.rating"
                      class="px-2.5 sm:px-3 py-1 text-[10px] sm:text-xs font-semibold bg-amber-500/20 text-amber-400 rounded-full border border-amber-500/30 flex items-center gap-1 whitespace-nowrap"
                    >
                      <AppIcon icon="lucide:star" size="10" class="sm:w-3 sm:h-3 fill-current flex-shrink-0" />
                      <span>{{ movie.trakt.rating.toFixed(1) }}</span>
                      <span v-if="movie.trakt.votes" class="text-amber-300 hidden sm:inline">({{ formatVotes(movie.trakt.votes) }})</span>
                    </span>
                    <span 
                      v-if="movie.trakt?.certification"
                      class="px-2.5 sm:px-3 py-1 text-[10px] sm:text-xs font-semibold bg-muted text-foreground rounded-full border border-border whitespace-nowrap"
                    >
                      {{ movie.trakt.certification }}
                    </span>
                    <!-- In Database Status Badge -->
                    <span 
                      v-if="inDatabase !== null"
                      :class="inDatabase 
                        ? 'px-2.5 sm:px-3 py-1 text-[10px] sm:text-xs font-semibold bg-emerald-500/20 text-emerald-400 rounded-full border border-emerald-500/30 flex items-center gap-1 whitespace-nowrap'
                        : 'px-2.5 sm:px-3 py-1 text-[10px] sm:text-xs font-semibold bg-muted text-muted-foreground rounded-full border border-border flex items-center gap-1 whitespace-nowrap'"
                    >
                      <AppIcon :icon="inDatabase ? 'lucide:check-circle' : 'lucide:x-circle'" size="10" class="sm:w-3 sm:h-3 flex-shrink-0" />
                      <span class="hidden sm:inline">{{ inDatabase ? 'In Database' : 'Not in Database' }}</span>
                      <span class="sm:hidden">{{ inDatabase ? 'In DB' : 'Not in DB' }}</span>
                    </span>
                    <!-- Available in Overseerr Badge -->
                    <span 
                      v-if="availableInOverseerr === true"
                      class="px-2.5 sm:px-3 py-1 text-[10px] sm:text-xs font-semibold bg-emerald-500/20 text-emerald-400 rounded-full border border-emerald-500/30 flex items-center gap-1 whitespace-nowrap"
                    >
                      <AppIcon icon="lucide:check-circle-2" size="10" class="sm:w-3 sm:h-3 flex-shrink-0" />
                      <span class="hidden sm:inline">Available in Overseerr</span>
                      <span class="sm:hidden">Available</span>
                    </span>
                    <!-- Already Requested Badge -->
                    <span 
                      v-else-if="requestedInOverseerr === true"
                      class="px-2.5 sm:px-3 py-1 text-[10px] sm:text-xs font-semibold bg-amber-500/20 text-amber-400 rounded-full border border-amber-500/30 flex items-center gap-1 whitespace-nowrap"
                    >
                      <AppIcon icon="lucide:clock" size="10" class="sm:w-3 sm:h-3 flex-shrink-0" />
                      <span class="hidden sm:inline">Already Requested</span>
                      <span class="sm:hidden">Requested</span>
                    </span>
                  </div>
                  
                  <h2 class="text-xl sm:text-2xl md:text-3xl lg:text-4xl font-bold text-foreground mb-2 sm:mb-3 leading-tight break-words pr-8 sm:pr-0">{{ movie.title }}</h2>
                  <p v-if="movie.title_original && movie.title_original !== movie.title" class="text-xs sm:text-sm md:text-base text-muted-foreground mb-2 sm:mb-3 md:mb-4 break-words">
                    {{ movie.title_original }}
                  </p>
                  
                  <div class="flex items-center gap-2 sm:gap-3 md:gap-4 mb-3 sm:mb-4 flex-wrap">
                    <span v-if="movie.release_date" class="inline-flex items-center gap-1 text-xs sm:text-sm text-muted-foreground whitespace-nowrap">
                      <AppIcon icon="lucide:calendar" size="12" class="sm:w-3.5 sm:h-3.5 flex-shrink-0" />
                      <span class="hidden sm:inline">{{ formatDate(movie.release_date) }}</span>
                      <span class="sm:hidden">{{ new Date(movie.release_date).getFullYear() }}</span>
                    </span>
                    <span v-if="movie.trakt?.runtime" class="inline-flex items-center gap-1 text-xs sm:text-sm text-muted-foreground whitespace-nowrap">
                      <AppIcon icon="lucide:clock" size="12" class="sm:w-3.5 sm:h-3.5 flex-shrink-0" />
                      {{ movie.trakt.runtime }} min
                    </span>
                    <!-- Genres as badges -->
                    <div v-if="movie.trakt?.genres && movie.trakt.genres.length > 0" class="flex items-center gap-1.5 sm:gap-2 flex-wrap">
                      <span 
                        v-for="genre in movie.trakt.genres.slice(0, 3)" 
                        :key="genre"
                        class="px-1.5 sm:px-2 py-0.5 sm:py-1 text-[10px] sm:text-xs font-medium bg-muted text-foreground rounded-full border border-border capitalize whitespace-nowrap"
                      >
                        {{ genre.replace('-', ' ') }}
                      </span>
                      <span v-if="movie.trakt.genres.length > 3" class="px-1.5 sm:px-2 py-0.5 sm:py-1 text-[10px] sm:text-xs font-medium bg-muted text-muted-foreground rounded-full border border-border whitespace-nowrap">
                        +{{ movie.trakt.genres.length - 3 }} more
                      </span>
                    </div>
                  </div>
                  
                  <p v-if="movie.trakt?.overview" class="text-xs sm:text-sm md:text-base text-muted-foreground line-clamp-2 sm:line-clamp-3 lg:line-clamp-none mb-3 sm:mb-4 max-w-2xl">
                    {{ movie.trakt.overview }}
                  </p>
                  
                  <!-- Request Button -->
                  <div class="mt-2 sm:mt-3 flex-shrink-0">
                    <Button
                      v-if="!inDatabase && !isRequested && !availableInOverseerr && !requestedInOverseerr"
                      @click="handleRequest"
                      :disabled="isRequesting"
                      size="sm"
                      class="bg-primary text-primary-foreground hover:bg-primary/90 w-full sm:w-auto"
                    >
                      <AppIcon 
                        v-if="isRequesting"
                        icon="lucide:loader-2" 
                        size="14" 
                        class="mr-1.5 animate-spin"
                      />
                      <AppIcon 
                        v-else
                        icon="lucide:plus" 
                        size="14" 
                        class="mr-1.5"
                      />
                      {{ isRequesting ? 'Requesting...' : 'Request Movie' }}
                    </Button>
                    <Button
                      v-else-if="inDatabase && databaseId"
                      @click="viewInDatabase"
                      size="sm"
                      variant="outline"
                      class="bg-primary/20 border-primary/30 text-primary hover:bg-primary/30 w-full sm:w-auto"
                    >
                      <AppIcon icon="lucide:external-link" size="14" class="mr-1.5" />
                      View Item
                    </Button>
                    <Button
                      v-else-if="availableInOverseerr"
                      size="sm"
                      variant="outline"
                      class="bg-emerald-500/20 border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/30 w-full sm:w-auto"
                      disabled
                    >
                      <AppIcon icon="lucide:check-circle-2" size="14" class="mr-1.5" />
                      Available
                    </Button>
                    <Button
                      v-else-if="requestedInOverseerr"
                      size="sm"
                      variant="outline"
                      class="bg-amber-500/20 border-amber-500/30 text-amber-400 hover:bg-amber-500/30 w-full sm:w-auto"
                      disabled
                    >
                      <AppIcon icon="lucide:clock" size="14" class="mr-1.5" />
                      Already Requested
                    </Button>
                    <Button
                      v-else-if="isRequested && !inDatabase"
                      size="sm"
                      variant="outline"
                      class="bg-amber-500/20 border-amber-500/30 text-amber-400 hover:bg-amber-500/30 w-full sm:w-auto"
                      disabled
                    >
                      <AppIcon icon="lucide:check-circle" size="14" class="mr-1.5" />
                      Already Requested
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Body -->
          <div v-if="movie" class="px-4 sm:px-5 md:px-6 py-3 sm:py-4 space-y-3">
            <!-- Main Info Card -->
            <div class="bg-gradient-to-br from-muted to-muted/50 rounded-xl p-4 border border-border">
              <div class="flex items-center gap-2 mb-2">
                <div class="w-8 h-8 bg-primary/10 rounded-lg flex items-center justify-center">
                  <AppIcon icon="lucide:info" size="18" class="text-primary" />
                </div>
                <div>
                  <h3 class="text-sm font-bold text-foreground">Movie Details & Information</h3>
                </div>
              </div>
              
              <div class="grid grid-cols-1 lg:grid-cols-2 gap-3">
                <!-- Left Column -->
                <div class="space-y-1.5">
                  <div v-if="movie.title_original && movie.title_original !== movie.title" class="flex items-start justify-between">
                    <span class="text-xs text-muted-foreground">Original Title</span>
                    <span class="text-xs font-medium text-foreground text-right max-w-[60%] line-clamp-1">{{ movie.title_original }}</span>
                  </div>
                  
                  <div v-if="movie.trakt?.tagline" class="flex items-start justify-between">
                    <span class="text-xs text-muted-foreground">Tagline</span>
                    <span class="text-xs font-medium text-foreground text-right italic max-w-[60%] line-clamp-1">{{ movie.trakt.tagline }}</span>
                  </div>
                  
                  <div v-if="movie.trakt?.trakt_id" class="flex items-center justify-between">
                    <span class="text-xs text-muted-foreground">Trakt ID</span>
                    <span class="text-xs font-medium text-foreground">{{ movie.trakt.trakt_id }}</span>
                  </div>
                  
                  <div v-if="movie.trakt?.ids?.slug" class="flex items-center justify-between">
                    <span class="text-xs text-muted-foreground">Slug</span>
                    <span class="text-xs font-medium text-foreground font-mono truncate">{{ movie.trakt.ids.slug }}</span>
                  </div>
                </div>
                
                <!-- Right Column -->
                <div class="space-y-1.5">
                  <div v-if="movie.trakt?.ids?.imdb" class="flex items-center justify-between">
                    <span class="text-xs text-muted-foreground">IMDB ID</span>
                    <a 
                      :href="`https://www.imdb.com/title/${movie.trakt.ids.imdb}`"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="text-xs font-medium text-primary hover:underline truncate"
                    >
                      {{ movie.trakt.ids.imdb }}
                      <AppIcon icon="lucide:external-link" size="10" class="inline ml-1" />
                    </a>
                  </div>
                  
                  <div v-if="movie.trakt?.ids?.tmdb">
                    <div class="flex items-center justify-between">
                      <span class="text-xs text-muted-foreground">TMDB ID</span>
                      <a 
                        :href="`https://www.themoviedb.org/movie/${movie.trakt.ids.tmdb}`"
                        target="_blank"
                        rel="noopener noreferrer"
                        class="text-xs font-medium text-primary hover:underline"
                      >
                        {{ movie.trakt.ids.tmdb }}
                        <AppIcon icon="lucide:external-link" size="10" class="inline ml-1" />
                      </a>
                    </div>
                    <!-- Overseerr Link -->
                    <div v-if="overseerrBaseUrl && movie.trakt?.ids?.tmdb" class="flex items-center justify-between mt-1.5">
                      <span class="text-xs text-muted-foreground">{{ overseerrBaseUrl }}</span>
                      <a 
                        :href="getOverseerrUrl(movie)!" 
                        target="_blank" 
                        rel="noopener noreferrer"
                        class="inline-flex items-center gap-1 text-xs text-primary hover:text-primary/80 transition-colors"
                      >
                        <AppIcon icon="lucide:external-link" size="10" />
                        View in Overseerr
                      </a>
                    </div>
                  </div>
                  
                  <div v-if="movie.trakt?.updated_at" class="flex items-center justify-between">
                    <span class="text-xs text-muted-foreground">Updated</span>
                    <span class="text-xs font-medium text-foreground">{{ formatDate(movie.trakt.updated_at) }}</span>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Links, Overview & Media -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-3">
              <!-- Links & Overview -->
              <div v-if="hasLinks(movie) || movie.trakt?.overview" class="bg-gradient-to-br from-muted to-muted/50 rounded-xl p-4 border border-border">
                <div class="flex items-center gap-2 mb-2">
                  <div class="w-8 h-8 bg-indigo-600/10 rounded-lg flex items-center justify-center">
                    <AppIcon icon="lucide:file-text" size="18" class="text-indigo-600" />
                  </div>
                  <div>
                    <h3 class="text-sm font-bold text-foreground">Overview & Links</h3>
                  </div>
                </div>
                
                <div class="space-y-3">
                  <!-- Overview -->
                  <div v-if="movie.trakt?.overview">
                    <p class="text-xs text-muted-foreground leading-relaxed line-clamp-4">{{ movie.trakt.overview }}</p>
                  </div>
                  
                  <!-- External Links -->
                  <div v-if="hasLinks(movie)" class="space-y-1.5">
                    <a
                      v-if="movie.trakt?.homepage"
                      :href="movie.trakt.homepage"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="flex items-center gap-2 p-2 bg-card rounded-lg border border-border hover:border-primary hover:bg-primary/5 transition-colors group"
                    >
                      <AppIcon icon="lucide:globe" size="14" class="text-muted-foreground group-hover:text-primary" />
                      <span class="text-xs font-medium text-foreground flex-1">Official Website</span>
                      <AppIcon icon="lucide:external-link" size="12" class="text-muted-foreground group-hover:text-primary" />
                    </a>
                    
                    <a
                      v-if="movie.trakt?.trailer"
                      :href="movie.trakt.trailer"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="flex items-center gap-2 p-2 bg-card rounded-lg border border-border hover:border-primary hover:bg-primary/5 transition-colors group"
                    >
                      <AppIcon icon="lucide:play-circle" size="14" class="text-muted-foreground group-hover:text-primary" />
                      <span class="text-xs font-medium text-foreground flex-1">Watch Trailer</span>
                      <AppIcon icon="lucide:external-link" size="12" class="text-muted-foreground group-hover:text-primary" />
                    </a>
                  </div>
                </div>
              </div>
              
              <!-- Local Images -->
              <div v-if="hasLocalImages(movie)" class="bg-gradient-to-br from-muted to-muted/50 rounded-xl p-4 border border-border">
                <div class="flex items-center gap-2 mb-2">
                  <div class="w-8 h-8 bg-purple-600/10 rounded-lg flex items-center justify-center">
                    <AppIcon icon="lucide:image" size="18" class="text-purple-600" />
                  </div>
                  <div>
                    <h3 class="text-sm font-bold text-foreground">Local Images</h3>
                  </div>
                </div>
                
                <div class="grid grid-cols-2 gap-2">
                  <div v-if="movie.local_images?.poster" class="text-center">
                    <p class="text-[10px] text-muted-foreground mb-1">Poster</p>
                    <img
                      :src="getPosterUrl(movie)"
                      :alt="movie.title + ' poster'"
                      class="w-full rounded border border-border hover:border-primary transition-colors cursor-pointer"
                      @click="openImageInNewTab(getPosterUrl(movie)!)"
                    />
                  </div>
                  
                  <div v-if="movie.local_images?.fanart" class="text-center">
                    <p class="text-[10px] text-muted-foreground mb-1">Fanart</p>
                    <img
                      :src="getFanartUrl(movie)"
                      :alt="movie.title + ' fanart'"
                      class="w-full rounded border border-border hover:border-primary transition-colors cursor-pointer"
                      @click="openImageInNewTab(getFanartUrl(movie)!)"
                    />
                  </div>
                  
                  <div v-if="movie.local_images?.logo" class="text-center">
                    <p class="text-[10px] text-muted-foreground mb-1">Logo</p>
                    <img
                      :src="getLogoUrl(movie)"
                      :alt="movie.title + ' logo'"
                      class="w-full rounded border border-border hover:border-primary transition-colors cursor-pointer bg-card"
                      @click="openImageInNewTab(getLogoUrl(movie)!)"
                    />
                  </div>
                  
                  <div v-if="movie.local_images?.clearart" class="text-center">
                    <p class="text-[10px] text-muted-foreground mb-1">Clearart</p>
                    <img
                      :src="getClearartUrl(movie)"
                      :alt="movie.title + ' clearart'"
                      class="w-full rounded border border-border hover:border-primary transition-colors cursor-pointer bg-card"
                      @click="openImageInNewTab(getClearartUrl(movie)!)"
                    />
                  </div>
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
import { useCollections } from '~/composables/useCollections'
import { useConfig } from '~/composables/useConfig'

interface Movie {
  title: string
  title_original: string
  year: number
  release_date?: string
  local_images?: {
    poster?: string
    fanart?: string
    logo?: string
    clearart?: string
    banner?: string
  }
  trakt?: {
    trakt_id: number
    title: string
    year: number
    ids?: {
      trakt?: number
      slug?: string
      imdb?: string
      tmdb?: number
    }
    overview?: string
    rating?: number
    votes?: number
    genres?: string[]
    certification?: string
    runtime?: number
    tagline?: string
    trailer?: string
    homepage?: string
    updated_at?: string
  }
}

interface Props {
  movie: Movie | null
  isOpen: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  close: []
}>()

const { getPosterUrl, getFanartUrl, getLogoUrl, getClearartUrl } = useCollections()
const { overseerrBaseUrl, fetchConfig } = useConfig()
const { toast } = useToast()

const inDatabase = ref<boolean | null>(null)
const databaseId = ref<number | null>(null)
const checkingDatabase = ref(false)
const isRequested = ref(false)
const isRequesting = ref(false)

// Track Overseerr availability
const availableInOverseerr = ref<boolean | null>(null)
const requestedInOverseerr = ref<boolean | null>(null)
const checkingOverseerrStatus = ref(false)

// Check if movie exists in database
const checkMovieInDatabase = async (movie: Movie) => {
  if (!movie) return
  
  checkingDatabase.value = true
  inDatabase.value = null
  databaseId.value = null
  
  try {
    const params = new URLSearchParams()
    
    if (movie.trakt?.ids?.imdb) {
      params.append('imdb_id', movie.trakt.ids.imdb)
    } else if (movie.trakt?.ids?.tmdb) {
      params.append('tmdb_id', String(movie.trakt.ids.tmdb))
    } else {
      checkingDatabase.value = false
      return
    }
    
    const response = await $fetch<{
      success: boolean
      data: {
        exists: boolean
        foundBy: string
        id: string | number
        databaseId?: number | null
      }
    }>(`/api/movie-exists?${params.toString()}`)
    
    if (response.success) {
      inDatabase.value = response.data.exists
      databaseId.value = response.data.databaseId || null
    }
  } catch (error) {
    console.error('Error checking if movie exists in database:', error)
    inDatabase.value = null
    databaseId.value = null
  } finally {
    checkingDatabase.value = false
  }
}

// Check Overseerr availability status
const checkOverseerrStatus = async (movie: Movie) => {
  if (!movie || !movie.trakt?.ids?.tmdb) return
  
  checkingOverseerrStatus.value = true
  availableInOverseerr.value = null
  requestedInOverseerr.value = null
  
  try {
    const response = await $fetch<{
      success: boolean
      data?: {
        status: number | null
        available: boolean
        requested?: boolean
      }
      error?: string
    }>(`/api/overseerr-movie-status?tmdb_id=${movie.trakt.ids.tmdb}`)
    
    if (response.success && response.data) {
      // Status 1 or 5 - fully available
      // Status 2 or 3 - already requested (not available for new request)
      if (response.data.available) {
        availableInOverseerr.value = true
        requestedInOverseerr.value = false
      } else if (response.data.requested) {
        requestedInOverseerr.value = true
        availableInOverseerr.value = false
      } else {
        availableInOverseerr.value = false
        requestedInOverseerr.value = false
      }
    }
  } catch (error) {
    console.error('Error checking Overseerr status:', error)
    availableInOverseerr.value = null
    requestedInOverseerr.value = null
  } finally {
    checkingOverseerrStatus.value = false
  }
}

// Fetch config when modal opens
watch(() => props.isOpen, async (isOpen) => {
  if (isOpen) {
    fetchConfig()
    if (props.movie) {
      checkMovieInDatabase(props.movie)
      checkOverseerrStatus(props.movie)
    }
    // Reset request state when opening
    isRequested.value = false
  } else {
    // Reset when modal closes
    inDatabase.value = null
    databaseId.value = null
    availableInOverseerr.value = null
    requestedInOverseerr.value = null
    isRequested.value = false
  }
}, { immediate: true })

// Watch for movie changes
watch(() => props.movie, (newMovie) => {
  if (props.isOpen && newMovie) {
    checkMovieInDatabase(newMovie)
    checkOverseerrStatus(newMovie)
    // Reset request state when movie changes
    isRequested.value = false
    availableInOverseerr.value = null
    requestedInOverseerr.value = null
  }
})

// Handle request
const handleRequest = async () => {
  if (!props.movie || !props.movie.trakt?.ids?.tmdb) {
    toast.error('Movie does not have a TMDB ID', 'Cannot Request')
    return
  }
  
  isRequesting.value = true
  
  try {
    const response = await $fetch('/api/overseerr-request', {
      method: 'POST',
      body: {
        mediaId: props.movie.trakt.ids.tmdb,
        mediaType: 'movie',
        is4k: false
      }
    })
    
    if (response.success) {
      // Mark as requested
      isRequested.value = true
      
      // Re-check database to get the new database ID
      await checkMovieInDatabase(props.movie!)
      
      toast.success(
        `"${props.movie.title}" request submitted successfully`,
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
    isRequesting.value = false
  }
}

// View item in database
const viewInDatabase = () => {
  if (databaseId.value) {
    navigateTo(`/processed-media?mediaId=${databaseId.value}`)
    close()
  }
}

// Also fetch on mount in case modal opens immediately
onMounted(() => {
  fetchConfig()
  if (props.isOpen && props.movie) {
    checkMovieInDatabase(props.movie)
    checkOverseerrStatus(props.movie)
  }
})

const close = () => {
  emit('close')
}

const formatDate = (date: string) => {
  if (!date) return 'N/A'
  try {
    return new Date(date).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
  } catch {
    return date
  }
}

const formatVotes = (votes: number) => {
  if (votes >= 1000000) {
    return `${(votes / 1000000).toFixed(1)}M`
  } else if (votes >= 1000) {
    return `${(votes / 1000).toFixed(1)}K`
  }
  return votes.toString()
}

const hasLinks = (movie: Movie) => {
  return !!(movie.trakt?.homepage || movie.trakt?.trailer)
}

const hasLocalImages = (movie: Movie) => {
  return !!(movie.local_images?.poster || movie.local_images?.fanart || movie.local_images?.logo || movie.local_images?.clearart)
}

const openImageInNewTab = (url: string) => {
  window.open(url, '_blank')
}

const getOverseerrUrl = (movie: Movie) => {
  if (!overseerrBaseUrl.value || !movie.trakt?.ids?.tmdb) return null
  return `${overseerrBaseUrl.value}/movie/${movie.trakt.ids.tmdb}`
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


