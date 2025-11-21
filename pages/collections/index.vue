<template>
  <div class="space-y-8">
    <!-- Header -->
    <div class="space-y-4">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-3xl font-bold text-foreground">Collections</h1>
          <p class="text-muted-foreground mt-1">
            Browse your movie collections by franchise
          </p>
        </div>
        
        <div class="flex items-center gap-4">
          <div class="text-sm text-muted-foreground">
            <span v-if="pagination">
              Showing {{ (pagination.page - 1) * pagination.limit + 1 }} - {{ Math.min(pagination.page * pagination.limit, pagination.total) }} of {{ pagination.total }} collections
            </span>
            <span v-else-if="collections.length > 0">
              {{ collections.length }} collections
            </span>
            <span v-if="totalMovies > 0" class="ml-2">
              • {{ totalMovies }} movies total
            </span>
          </div>
          <Button 
            @click="refreshCollections"
            :disabled="loading"
            variant="outline"
            size="sm"
          >
            <AppIcon 
              icon="lucide:refresh-cw" 
              size="16" 
              class="mr-2"
              :class="{ 'animate-spin': loading }"
            />
            Refresh
          </Button>
        </div>
      </div>
      
      <!-- Search Box -->
      <div class="relative">
        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <AppIcon icon="lucide:search" size="20" class="text-muted-foreground" />
        </div>
        <Input
          v-model="searchQuery"
          type="text"
          placeholder="Search collections or movies by title..."
          class="pl-10 pr-10"
        />
        <div v-if="searchQuery" class="absolute inset-y-0 right-0 pr-3 flex items-center">
          <Button
            @click="clearSearch"
            variant="ghost"
            size="sm"
            class="h-6 w-6 p-0 hover:bg-muted"
          >
            <AppIcon icon="lucide:x" size="16" class="text-muted-foreground" />
          </Button>
        </div>
      </div>
    </div>

    <!-- Random Collections Badges Section -->
    <div v-if="randomCollections.length > 0 && !searchQuery" class="space-y-4">
      <div class="flex items-center gap-3">
        <div class="flex items-center gap-2">
          <AppIcon icon="lucide:shuffle" size="24" class="text-primary" />
          <h2 class="text-2xl font-bold text-foreground">Discover Collections</h2>
        </div>
        <div class="flex-1 h-px bg-gradient-to-r from-primary/30 via-primary/10 to-transparent"></div>
        <Button
          @click="loadRandomCollections"
          variant="ghost"
          size="sm"
          class="text-xs"
          :disabled="loadingRandomCollections"
        >
          <AppIcon 
            icon="lucide:refresh-cw" 
            size="14" 
            class="mr-1"
            :class="{ 'animate-spin': loadingRandomCollections }"
          />
          Shuffle
        </Button>
      </div>
      <p class="text-sm text-muted-foreground mb-4">50 randomly selected collections • Click to explore</p>
      
      <div class="flex flex-wrap gap-2">
        <Button
          v-for="collection in randomCollections"
          :key="collection.franchise_name"
          @click="viewCollection(collection)"
          variant="outline"
          size="sm"
          class="text-sm font-medium hover:bg-primary hover:text-primary-foreground hover:border-primary transition-colors"
        >
          {{ collection.franchise_name }}
          <span v-if="collection.total_movies > 0" class="ml-2 text-xs text-muted-foreground">
            ({{ collection.total_movies }})
          </span>
        </Button>
      </div>
    </div>

    <!-- Vardarr's Choice Section -->
    <div v-if="vardarrChoice.length > 0 && !searchQuery" class="space-y-4">
      <div class="flex items-center gap-3">
        <div class="flex items-center gap-2">
          <AppIcon icon="lucide:star" size="24" class="text-primary" />
          <h2 class="text-2xl font-bold text-foreground">Vardarr's Choice</h2>
        </div>
        <div class="flex-1 h-px bg-gradient-to-r from-primary/30 via-primary/10 to-transparent"></div>
      </div>
      <p class="text-sm text-muted-foreground mb-4">Hand-picked favorite collections</p>
      
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-6">
        <div
          v-for="collection in vardarrChoice"
          :key="collection.franchise_name"
          @click="viewCollection(collection)"
          class="group relative bg-card rounded-2xl cursor-pointer transition-all duration-300 hover:shadow-2xl hover:-translate-y-1 border-2 border-primary/30 hover:border-primary/60"
        >
          <!-- Collection Card with Stacked Posters -->
          <div class="relative aspect-[2/3] bg-gradient-to-br from-primary/10 to-primary/5 overflow-hidden rounded-t-2xl">
            <!-- Stacked Poster Cards (up to 3) - Book/Collection Style -->
            <div class="absolute inset-0 flex items-center justify-center" style="padding: 1.5rem;">
              <template v-if="hasAnyPoster(collection)">
                <template v-for="(movie, index) in getMoviesWithPosters(collection)" :key="`${movie.title}-${index}`">
                  <!-- Third Poster (back, if 3 movies) - Largest rotation, most offset -->
                  <div
                    v-if="index === 2"
                    class="absolute transform"
                    :style="{
                      transform: 'translateX(-32px) translateY(-6px) rotate(10deg) scale(0.88)',
                      zIndex: 1,
                      filter: 'brightness(0.7) contrast(0.95)'
                    }"
                  >
                    <div class="w-56 h-80 md:w-64 md:h-96 rounded-lg overflow-hidden shadow-[0_20px_60px_-12px_rgba(0,0,0,0.5)] border-2 border-black/20 bg-card">
                      <img
                        v-if="getPosterUrl(movie)"
                        :src="getPosterUrl(movie)"
                        :alt="movie.title"
                        class="w-full h-full object-cover"
                        @error="handleImageError"
                      />
                    </div>
                  </div>
                  
                  <!-- Second Poster (middle, if 2+ movies) - Medium rotation and offset -->
                  <div
                    v-if="index === 1"
                    class="absolute transform"
                    :style="{
                      transform: 'translateX(-16px) translateY(-3px) rotate(-8deg) scale(0.94)',
                      zIndex: 2,
                      filter: 'brightness(0.8) contrast(0.98)'
                    }"
                  >
                    <div class="w-56 h-80 md:w-64 md:h-96 rounded-lg overflow-hidden shadow-[0_20px_60px_-12px_rgba(0,0,0,0.5)] border-2 border-black/30 bg-card">
                      <img
                        v-if="getPosterUrl(movie)"
                        :src="getPosterUrl(movie)"
                        :alt="movie.title"
                        class="w-full h-full object-cover"
                        @error="handleImageError"
                      />
                    </div>
                  </div>
                  
                  <!-- First Poster (front, main) - Slight rotation, on top -->
                  <div
                    v-if="index === 0"
                    class="absolute transform transition-all duration-300 group-hover:scale-105 group-hover:rotate-0"
                    :style="{
                      transform: 'translateX(0px) translateY(0px) rotate(3deg) scale(1)',
                      zIndex: 3
                    }"
                  >
                    <div class="w-56 h-80 md:w-64 md:h-96 rounded-lg overflow-hidden shadow-[0_25px_70px_-12px_rgba(0,0,0,0.6)] border-4 border-black/40 bg-card">
                      <img
                        v-if="getPosterUrl(movie)"
                        :src="getPosterUrl(movie)"
                        :alt="movie.title"
                        class="w-full h-full object-cover"
                        @error="handleImageError"
                      />
                    </div>
                  </div>
                </template>
              </template>
              
              <!-- Fallback if no movies with posters -->
              <div
                v-else
                class="flex flex-col items-center justify-center space-y-3 w-full h-full"
              >
                <div class="w-20 h-20 rounded-2xl bg-primary/20 flex items-center justify-center">
                  <AppIcon icon="lucide:folder" size="40" class="text-primary" />
                </div>
                <p class="text-sm font-medium text-muted-foreground text-center px-4 line-clamp-2">
                  {{ collection.franchise_name }}
                </p>
              </div>
            </div>
            
            <!-- Collection Info Overlay -->
            <div class="absolute inset-0 bg-gradient-to-t from-primary/90 via-primary/40 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-end">
              <div class="p-4 w-full">
                <h3 class="text-white font-bold text-lg mb-1 line-clamp-1">
                  {{ collection.franchise_name }}
                </h3>
                <p class="text-white/80 text-sm">
                  {{ collection.total_movies }} {{ collection.total_movies === 1 ? 'movie' : 'movies' }}
                </p>
                <div v-if="collection.years.length > 0" class="text-white/70 text-xs mt-1">
                  {{ collection.years[0] }} - {{ collection.years[collection.years.length - 1] }}
                </div>
              </div>
            </div>
            
            <!-- Vardarr's Choice Badge -->
            <div class="absolute top-3 left-3">
              <div class="bg-primary/90 backdrop-blur-sm text-primary-foreground px-3 py-1 rounded-full text-xs font-semibold shadow-lg flex items-center gap-1">
                <AppIcon icon="lucide:star" size="12" />
                <span>Vardarr's Choice</span>
              </div>
            </div>
            
            <!-- Movie Count Badge -->
            <div class="absolute top-3 right-3">
              <div class="bg-primary/90 backdrop-blur-sm text-primary-foreground px-3 py-1 rounded-full text-xs font-semibold shadow-lg">
                {{ collection.total_movies }}
              </div>
            </div>
          </div>
          
          <!-- Collection Footer -->
          <div class="p-4">
            <h3 class="font-semibold text-foreground mb-1 line-clamp-1">
              {{ collection.franchise_name }}
            </h3>
            <p class="text-xs text-muted-foreground mb-3">
              {{ collection.total_movies }} {{ collection.total_movies === 1 ? 'movie' : 'movies' }}
              <span v-if="collection.years.length > 0">
                • {{ collection.years[0] }}-{{ collection.years[collection.years.length - 1] }}
              </span>
            </p>
            <!-- Request Entire Collection Button -->
            <Button
              @click.stop="handleRequestCollection(collection)"
              :disabled="requestingCollections.has(collection.franchise_name)"
              size="sm"
              variant="outline"
              class="w-full"
            >
              <AppIcon 
                v-if="requestingCollections.has(collection.franchise_name)"
                icon="lucide:loader-2" 
                size="14" 
                class="mr-2 animate-spin"
              />
              <AppIcon 
                v-else
                icon="lucide:plus-circle" 
                size="14" 
                class="mr-2"
              />
              <span v-if="requestingCollections.has(collection.franchise_name)">
                {{ getCollectionProgressText(collection.franchise_name) }}
              </span>
              <span v-else>Request Entire Collection</span>
            </Button>
          </div>
        </div>
      </div>
    </div>

    <!-- All Collections Section -->
    <div v-if="!searchQuery && vardarrChoice.length > 0" class="space-y-4 pt-8">
      <div class="flex items-center gap-3">
        <div class="flex items-center gap-2">
          <AppIcon icon="lucide:folder" size="24" class="text-muted-foreground" />
          <h2 class="text-2xl font-bold text-foreground">All Collections</h2>
        </div>
        <div class="flex-1 h-px bg-gradient-to-r from-border via-border/50 to-transparent"></div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading && collections.length === 0 && vardarrChoice.length === 0" class="flex items-center justify-center py-24">
      <div class="text-center">
        <AppIcon 
          icon="lucide:loader-2" 
          size="48" 
          class="mx-auto text-primary animate-spin mb-4"
        />
        <p class="text-muted-foreground">Loading collections...</p>
      </div>
    </div>

    <!-- Collections Grid -->
    <div v-else-if="collections.length > 0" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-6">
      <div
        v-for="collection in collections"
        :key="collection.franchise_name"
        @click="viewCollection(collection)"
        class="group relative bg-card rounded-2xl cursor-pointer transition-all duration-300 hover:shadow-2xl hover:-translate-y-1 border border-border"
      >
        <!-- Collection Card with Stacked Posters -->
        <div class="relative aspect-[2/3] bg-gradient-to-br from-muted to-muted/50 overflow-hidden rounded-t-2xl">
          <!-- Stacked Poster Cards (up to 3) - Book/Collection Style -->
          <div class="absolute inset-0 flex items-center justify-center" style="padding: 1.5rem;">
            <template v-if="hasAnyPoster(collection)">
              <template v-for="(movie, index) in getMoviesWithPosters(collection)" :key="`${movie.title}-${index}`">
                <!-- Third Poster (back, if 3 movies) - Largest rotation, most offset -->
                <div
                  v-if="index === 2"
                  class="absolute transform"
                  :style="{
                    transform: 'translateX(-32px) translateY(-6px) rotate(10deg) scale(0.88)',
                    zIndex: 1,
                    filter: 'brightness(0.7) contrast(0.95)'
                  }"
                >
                  <div class="w-56 h-80 md:w-64 md:h-96 rounded-lg overflow-hidden shadow-[0_20px_60px_-12px_rgba(0,0,0,0.5)] border-2 border-black/20 bg-card">
                    <img
                      v-if="getPosterUrl(movie)"
                      :src="getPosterUrl(movie)"
                      :alt="movie.title"
                      class="w-full h-full object-cover"
                      @error="handleImageError"
                    />
                  </div>
                </div>
                
                <!-- Second Poster (middle, if 2+ movies) - Medium rotation and offset -->
                <div
                  v-if="index === 1"
                  class="absolute transform"
                  :style="{
                    transform: 'translateX(-16px) translateY(-3px) rotate(-8deg) scale(0.94)',
                    zIndex: 2,
                    filter: 'brightness(0.8) contrast(0.98)'
                  }"
                >
                  <div class="w-56 h-80 md:w-64 md:h-96 rounded-lg overflow-hidden shadow-[0_20px_60px_-12px_rgba(0,0,0,0.5)] border-2 border-black/30 bg-card">
                    <img
                      v-if="getPosterUrl(movie)"
                      :src="getPosterUrl(movie)"
                      :alt="movie.title"
                      class="w-full h-full object-cover"
                      @error="handleImageError"
                    />
                  </div>
                </div>
                
                <!-- First Poster (front, main) - Slight rotation, on top -->
                <div
                  v-if="index === 0"
                  class="absolute transform transition-all duration-300 group-hover:scale-105 group-hover:rotate-0"
                  :style="{
                    transform: 'translateX(0px) translateY(0px) rotate(3deg) scale(1)',
                    zIndex: 3
                  }"
                >
                  <div class="w-56 h-80 md:w-64 md:h-96 rounded-lg overflow-hidden shadow-[0_25px_70px_-12px_rgba(0,0,0,0.6)] border-4 border-black/40 bg-card">
                    <img
                      v-if="getPosterUrl(movie)"
                      :src="getPosterUrl(movie)"
                      :alt="movie.title"
                      class="w-full h-full object-cover"
                      @error="handleImageError"
                    />
                  </div>
                </div>
              </template>
            </template>
            
            <!-- Fallback if no movies with posters -->
            <div
              v-else
              class="flex flex-col items-center justify-center space-y-3 w-full h-full"
            >
              <div class="w-20 h-20 rounded-2xl bg-primary/10 flex items-center justify-center">
                <AppIcon icon="lucide:folder" size="40" class="text-primary" />
              </div>
              <p class="text-sm font-medium text-muted-foreground text-center px-4 line-clamp-2">
                {{ collection.franchise_name }}
              </p>
            </div>
          </div>
          
          <!-- Collection Info Overlay -->
          <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-end">
            <div class="p-4 w-full">
              <h3 class="text-white font-bold text-lg mb-1 line-clamp-1">
                {{ collection.franchise_name }}
              </h3>
              <p class="text-white/80 text-sm">
                {{ collection.total_movies }} {{ collection.total_movies === 1 ? 'movie' : 'movies' }}
              </p>
              <div v-if="collection.years.length > 0" class="text-white/70 text-xs mt-1">
                {{ collection.years[0] }} - {{ collection.years[collection.years.length - 1] }}
              </div>
            </div>
          </div>
          
          <!-- Movie Count Badge -->
          <div class="absolute top-3 right-3">
            <div class="bg-primary/90 backdrop-blur-sm text-primary-foreground px-3 py-1 rounded-full text-xs font-semibold shadow-lg">
              {{ collection.total_movies }}
            </div>
          </div>
        </div>
        
        <!-- Card Footer -->
        <div class="p-4 bg-card border-t border-border">
          <h3 class="font-semibold text-foreground line-clamp-1 mb-1">
            {{ collection.franchise_name }}
          </h3>
          <div class="flex items-center justify-between text-sm text-muted-foreground mb-3">
            <span>{{ collection.total_movies }} {{ collection.total_movies === 1 ? 'movie' : 'movies' }}</span>
            <span v-if="collection.years.length > 0">
              {{ collection.years[0] }}-{{ collection.years[collection.years.length - 1] }}
            </span>
          </div>
          <!-- Request Entire Collection Button -->
          <Button
            @click.stop="handleRequestCollection(collection)"
            :disabled="requestingCollections.has(collection.franchise_name)"
            size="sm"
            variant="outline"
            class="w-full"
          >
            <AppIcon 
              v-if="requestingCollections.has(collection.franchise_name)"
              icon="lucide:loader-2" 
              size="14" 
              class="mr-2 animate-spin"
            />
            <AppIcon 
              v-else
              icon="lucide:plus-circle" 
              size="14" 
              class="mr-2"
            />
            <span v-if="requestingCollections.has(collection.franchise_name)">
              {{ getCollectionProgressText(collection.franchise_name) }}
            </span>
            <span v-else>Request Entire Collection</span>
          </Button>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="flex flex-col items-center justify-center py-24 text-center">
      <div class="w-24 h-24 rounded-full bg-muted flex items-center justify-center mb-6">
        <AppIcon icon="lucide:folder-x" size="48" class="text-muted-foreground" />
      </div>
      <h3 class="text-xl font-semibold text-foreground mb-2">No collections found</h3>
      <p class="text-muted-foreground max-w-md">
        Collections will appear here once you have movies grouped by franchise in your unified.json file.
      </p>
    </div>

    <!-- Pagination Controls -->
    <div v-if="pagination && pagination.total_pages > 1" class="space-y-4 pt-6">
      <!-- Main Pagination -->
      <div class="flex flex-wrap items-center justify-center gap-2">
        <!-- First Page -->
        <Button
          @click="goToPage(1)"
          :disabled="pagination.page === 1 || loading"
          variant="outline"
          size="sm"
          class="gap-1"
        >
          <AppIcon icon="lucide:chevrons-left" size="16" />
          <span class="hidden sm:inline">First</span>
        </Button>
        
        <!-- Previous Page -->
        <Button
          @click="goToPage(pagination.page - 1)"
          :disabled="!pagination.has_prev || loading"
          variant="outline"
          size="sm"
          class="gap-1"
        >
          <AppIcon icon="lucide:chevron-left" size="16" />
          <span class="hidden sm:inline">Previous</span>
        </Button>
        
        <!-- Page Numbers -->
        <div class="flex items-center gap-1 flex-wrap justify-center">
          <template v-if="pagination.total_pages <= 20">
            <!-- Show all pages if 20 or less -->
            <Button
              v-for="pageNum in Array.from({ length: pagination.total_pages }, (_, i) => i + 1)"
              :key="pageNum"
              @click="goToPage(pageNum)"
              :disabled="loading"
              :variant="pageNum === pagination.page ? 'default' : 'outline'"
              size="sm"
              class="min-w-[40px]"
            >
              {{ pageNum }}
            </Button>
          </template>
          <template v-else>
            <!-- Show pages with ellipsis for large page counts -->
            <!-- First page -->
            <Button
              @click="goToPage(1)"
              :disabled="loading"
              :variant="pagination.page === 1 ? 'default' : 'outline'"
              size="sm"
              class="min-w-[40px]"
            >
              1
            </Button>
            
            <!-- Ellipsis before current range -->
            <span v-if="pagination.page > 4" class="px-2 text-muted-foreground">...</span>
            
            <!-- Pages around current page -->
            <Button
              v-for="pageNum in visiblePages"
              :key="pageNum"
              @click="goToPage(pageNum)"
              :disabled="loading"
              :variant="pageNum === pagination.page ? 'default' : 'outline'"
              size="sm"
              class="min-w-[40px]"
            >
              {{ pageNum }}
            </Button>
            
            <!-- Ellipsis after current range -->
            <span v-if="pagination.page < pagination.total_pages - 3" class="px-2 text-muted-foreground">...</span>
            
            <!-- Last page -->
            <Button
              @click="goToPage(pagination.total_pages)"
              :disabled="loading"
              :variant="pagination.page === pagination.total_pages ? 'default' : 'outline'"
              size="sm"
              class="min-w-[40px]"
            >
              {{ pagination.total_pages }}
            </Button>
          </template>
        </div>
        
        <!-- Next Page -->
        <Button
          @click="goToPage(pagination.page + 1)"
          :disabled="!pagination.has_next || loading"
          variant="outline"
          size="sm"
          class="gap-1"
        >
          <span class="hidden sm:inline">Next</span>
          <AppIcon icon="lucide:chevron-right" size="16" />
        </Button>
        
        <!-- Last Page -->
        <Button
          @click="goToPage(pagination.total_pages)"
          :disabled="pagination.page === pagination.total_pages || loading"
          variant="outline"
          size="sm"
          class="gap-1"
        >
          <span class="hidden sm:inline">Last</span>
          <AppIcon icon="lucide:chevrons-right" size="16" />
        </Button>
      </div>
      
      <!-- Page Jump Dropdown -->
      <div class="flex items-center justify-center gap-2">
        <span class="text-sm text-muted-foreground">Jump to:</span>
        <select
          v-model="selectedPageChunk"
          @change="handlePageChunkChange"
          :disabled="loading"
          class="px-3 py-1.5 text-sm rounded-md border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <option value="">Select page range...</option>
          <optgroup v-for="chunk in pageChunks" :key="chunk.label" :label="chunk.label">
            <option
              v-for="pageNum in chunk.pages"
              :key="pageNum"
              :value="pageNum"
              :selected="pageNum === pagination.page"
            >
              Page {{ pageNum }}
            </option>
          </optgroup>
        </select>
        <span class="text-sm text-muted-foreground">
          (Page {{ pagination.page }} of {{ pagination.total_pages }})
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import Button from '~/components/ui/Button.vue'
import Input from '~/components/ui/Input.vue'

interface Movie {
  title: string
  title_original: string
  year: number
  trakt?: {
    ids?: {
      tmdb?: number
      imdb?: string
    }
  }
  local_images?: {
    poster?: string
    fanart?: string
    logo?: string
    clearart?: string
    banner?: string
  }
}

interface Collection {
  franchise_name: string
  franchise_url?: string
  movies: Movie[]
  total_movies: number
  years: number[]
  genres: string[]
}

interface PaginationInfo {
  page: number
  limit: number
  total: number
  total_pages: number
  has_next: boolean
  has_prev: boolean
}

const { getCollections, getCollection, getBulkCollectionMetadata, getAllMoviesInCollection, getPosterUrl } = useCollections()
const router = useRouter()
const route = useRoute()
const { toast } = useToast()

// Hardcoded list of favorite collections for "Vardarr's Choice"
const VARDARR_CHOICE_FRANCHISES = [
  'Marvel Cinematic Universe',
  'Star Wars',
  'The Lord of the Rings',
  'Harry Potter',
  'James Bond',
  'The Dark Knight',
  'Pirates of the Caribbean',
  'Fast & Furious',
  'The Matrix'
]

const collections = ref<Collection[]>([])
const vardarrChoice = ref<Collection[]>([])
const randomCollections = ref<Collection[]>([])
const pagination = ref<PaginationInfo | null>(null)
const totalMovies = ref(0)
const loading = ref(false)
const loadingVardarrChoice = ref(false)
const loadingRandomCollections = ref(false)
const currentPage = ref(1)
const itemsPerPage = ref(20)
const searchQuery = ref('')

// Track collections being requested
const requestingCollections = ref<Set<string>>(new Set())
const collectionRequestProgress = ref<Map<string, { current: number, total: number }>>(new Map())

// Track requestable counts for collections
const collectionRequestableCounts = ref<Map<string, number>>(new Map())
const calculatingCollectionCounts = ref<Set<string>>(new Set())

const hasAnyPoster = (collection: Collection): boolean => {
  return collection.movies.some(movie => movie.local_images?.poster)
}

const getMoviesWithPosters = (collection: Collection): Movie[] => {
  return collection.movies
    .filter(movie => movie.local_images?.poster)
    .slice(0, 3) // Limit to 3 movies for stacking
}

const handleImageError = (event: Event) => {
  const img = event.target as HTMLImageElement
  img.style.display = 'none'
}

const visiblePages = computed(() => {
  if (!pagination.value) return []
  
  const total = pagination.value.total_pages
  const current = pagination.value.page
  
  // If total pages is 20 or less, show all (handled in template)
  if (total <= 20) return []
  
  // For large page counts, show pages around current
  const pages: number[] = []
  const range = 2 // Show 2 pages on each side
  let start = Math.max(2, current - range) // Start from 2 (1 is always shown)
  let end = Math.min(total - 1, current + range) // End before last (last is always shown)
  
  // Adjust range if near boundaries
  if (current <= 4) {
    start = 2
    end = Math.min(6, total - 1)
  } else if (current >= total - 3) {
    start = Math.max(2, total - 5)
    end = total - 1
  }
  
  for (let i = start; i <= end; i++) {
    pages.push(i)
  }
  
  return pages
})

// Page chunks for dropdown (divide pages into chunks)
const pageChunks = computed(() => {
  if (!pagination.value) return []
  
  const total = pagination.value.total_pages
  const chunkSize = 10 // Show 10 pages per chunk
  
  const chunks: Array<{ label: string, pages: number[] }> = []
  
  for (let i = 1; i <= total; i += chunkSize) {
    const chunkEnd = Math.min(i + chunkSize - 1, total)
    const pages: number[] = []
    
    for (let page = i; page <= chunkEnd; page++) {
      pages.push(page)
    }
    
    chunks.push({
      label: `Pages ${i}-${chunkEnd}`,
      pages
    })
  }
  
  return chunks
})

const selectedPageChunk = ref<string>('')

const handlePageChunkChange = (event: Event) => {
  const select = event.target as HTMLSelectElement
  const pageNum = parseInt(select.value)
  if (pageNum && pageNum > 0 && pagination.value && pageNum <= pagination.value.total_pages) {
    goToPage(pageNum)
    selectedPageChunk.value = '' // Reset dropdown after selection
  }
}

const applySearch = async () => {
  // Reset to page 1 when searching
  currentPage.value = 1
  
  const trimmedSearch = searchQuery.value.trim()
  console.log('applySearch called - searchQuery.value:', searchQuery.value, 'trimmed:', trimmedSearch)
  
  // Update URL with search query (don't await - do it in parallel)
  const query: Record<string, string> = {}
  if (trimmedSearch) {
    query.search = trimmedSearch
  }
  
  console.log('Updating URL query:', query)
  router.replace({ query }).catch(() => {
    // Ignore navigation errors
  })
  
  // Immediately fetch with current search value
  await refreshCollections()
}

const clearSearch = async () => {
  if (!searchQuery.value) return
  
  searchQuery.value = ''
  currentPage.value = 1
  
  // Clear search from URL
  const query: Record<string, string> = {}
  await router.replace({ query })
  
  await refreshCollections()
}

const goToPage = async (page: number) => {
  if (page < 1 || (pagination.value && page > pagination.value.total_pages)) {
    return
  }
  
  currentPage.value = page
  
  // Update URL without navigation
  const query: Record<string, string> = { page: String(page) }
  if (searchQuery.value) {
    query.search = searchQuery.value
  }
  await router.replace({ query })
  
  await refreshCollections()
}

const refreshCollections = async () => {
  loading.value = true
  try {
    // Use current search query value directly (most up-to-date)
    const searchTerm = searchQuery.value.trim()
    
    // Get page from query params or use current
    const pageFromQuery = parseInt(route.query.page as string) || currentPage.value
    currentPage.value = pageFromQuery
    
    console.log('Fetching collections with search:', searchTerm, 'page:', currentPage.value)
    
    const data = await getCollections(currentPage.value, itemsPerPage.value, searchTerm)
    if (data) {
      collections.value = data.collections
      pagination.value = data.pagination
      totalMovies.value = data.total_movies
      console.log('Collections loaded:', data.collections.length, 'total:', data.pagination.total)
      
      // Don't auto-calculate - calculate on-demand when user hovers/interacts
    }
  } catch (error) {
    console.error('Error refreshing collections:', error)
    const toast = useToast()
    toast.add({
      title: 'Error',
      description: 'Failed to refresh collections',
      color: 'red'
    })
  } finally {
    loading.value = false
  }
}

const viewCollection = (collection: Collection) => {
  const encodedName = encodeURIComponent(collection.franchise_name)
  router.push(`/collections/${encodedName}`)
}

// Calculate requestable count for a collection
// NOTE: This is now only called from handleRequestCollection, not on page load or hover
const calculateCollectionRequestableCount = async (collection: Collection) => {
  const franchiseName = collection.franchise_name
  
  // Skip if already calculating
  if (calculatingCollectionCounts.value.has(franchiseName)) {
    return
  }
  
  // Skip if already calculated
  if (collectionRequestableCounts.value.has(franchiseName)) {
    return
  }
  
  calculatingCollectionCounts.value.add(franchiseName)
  
  try {
    // Fetch all movies in the collection
    const allMovies = await getAllMoviesInCollection(franchiseName)
    
    if (!allMovies || allMovies.length === 0) {
      collectionRequestableCounts.value.set(franchiseName, 0)
      return
    }
    
    // Check Overseerr status for all movies (batched to avoid overwhelming)
    const moviesToCheck = allMovies.filter(movie => movie.trakt?.ids?.tmdb)
    
    // Process in batches of 5 to avoid overwhelming the system
    const BATCH_SIZE = 5
    const statusResults: Array<{ movie: Movie, available: boolean }> = []
    
    for (let i = 0; i < moviesToCheck.length; i += BATCH_SIZE) {
      const batch = moviesToCheck.slice(i, i + BATCH_SIZE)
      const batchChecks = batch.map(async (movie) => {
        try {
          const response = await $fetch<{
            success: boolean
            data?: {
              status: number | null
              available: boolean
              requested?: boolean
            }
            error?: string
          }>(`/api/overseerr-movie-status?tmdb_id=${movie.trakt!.ids!.tmdb}`, {
            timeout: 10000 // 10 second timeout per request
          })
          
          // Status 2 or 3 means already requested (so it's not available for new request)
          return {
            movie,
            available: response.success && (response.data?.available === true || response.data?.requested === true)
          }
        } catch (error) {
          // Silently handle errors - treat as not available
          return { movie, available: false }
        }
      })
      
      const batchResults = await Promise.all(batchChecks)
      statusResults.push(...batchResults)
      
      // Small delay between batches to avoid overwhelming
      if (i + BATCH_SIZE < moviesToCheck.length) {
        await new Promise(resolve => setTimeout(resolve, 100))
      }
    }
    
    // Count movies that can be requested (have TMDB ID and are not available)
    const count = statusResults.filter(result => !result.available).length
    
    collectionRequestableCounts.value.set(franchiseName, count)
  } catch (error) {
    console.error('Error calculating requestable count:', error)
    collectionRequestableCounts.value.set(franchiseName, collection.total_movies) // Fallback to total
  } finally {
    calculatingCollectionCounts.value.delete(franchiseName)
  }
}

// Get progress text for collection request
const getCollectionProgressText = (franchiseName: string): string => {
  const progress = collectionRequestProgress.value.get(franchiseName)
  if (progress) {
    return `Requesting ${progress.current}/${progress.total}`
  }
  return 'Requesting...'
}

// Request entire collection
const handleRequestCollection = async (collection: Collection) => {
  const franchiseName = collection.franchise_name
  
  // Check if already requesting
  if (requestingCollections.value.has(franchiseName)) {
    return
  }
  
  requestingCollections.value.add(franchiseName)
  
  try {
    // Fetch all movies in the collection
    const allMovies = await getAllMoviesInCollection(franchiseName)
    
    if (!allMovies || allMovies.length === 0) {
      toast.error('No movies found in collection', 'Request Failed')
      requestingCollections.value.delete(franchiseName)
      return
    }
    
    // Check Overseerr status for all movies first (batched to avoid overwhelming)
    const moviesToCheck = allMovies.filter(movie => movie.trakt?.ids?.tmdb)
    
    // Process in batches of 5 to avoid overwhelming the system
    const BATCH_SIZE = 5
    const statusResults: Array<{ movie: Movie, available: boolean }> = []
    
    for (let i = 0; i < moviesToCheck.length; i += BATCH_SIZE) {
      const batch = moviesToCheck.slice(i, i + BATCH_SIZE)
      const batchChecks = batch.map(async (movie) => {
        try {
          const response = await $fetch<{
            success: boolean
            data?: {
              status: number | null
              available: boolean
              requested?: boolean
            }
            error?: string
          }>(`/api/overseerr-movie-status?tmdb_id=${movie.trakt!.ids!.tmdb}`, {
            timeout: 10000 // 10 second timeout per request
          })
          
          // Status 2 or 3 means already requested (so it's not available for new request)
          return {
            movie,
            available: response.success && (response.data?.available === true || response.data?.requested === true)
          }
        } catch (error) {
          // Silently handle errors - treat as not available
          return { movie, available: false }
        }
      })
      
      const batchResults = await Promise.all(batchChecks)
      statusResults.push(...batchResults)
      
      // Small delay between batches to avoid overwhelming
      if (i + BATCH_SIZE < moviesToCheck.length) {
        await new Promise(resolve => setTimeout(resolve, 100))
      }
    }
    
    // Filter movies that have TMDB IDs and are not already available in Overseerr
    const moviesToRequest = statusResults
      .filter(result => !result.available)
      .map(result => result.movie)
    
    if (moviesToRequest.length === 0) {
      const availableCount = statusResults.filter(r => r.available).length
      const totalChecked = statusResults.length
      if (availableCount > 0 || totalChecked > 0) {
        // Some or all movies are already available or requested
        const message = availableCount > 0 && availableCount === totalChecked
          ? `All ${totalChecked} ${totalChecked === 1 ? 'movie is' : 'movies are'} already available in Overseerr`
          : totalChecked > 0
          ? `All ${totalChecked} ${totalChecked === 1 ? 'movie has' : 'movies have'} been requested or are available in Overseerr`
          : `All ${totalChecked} ${totalChecked === 1 ? 'movie is' : 'movies are'} already available or requested in Overseerr`
        toast.info(message, 'Collection Already Processed')
      } else {
        toast.error('No movies with TMDB IDs found in collection', 'Request Failed')
      }
      requestingCollections.value.delete(franchiseName)
      return
    }
    
    // Initialize progress
    collectionRequestProgress.value.set(franchiseName, { current: 0, total: moviesToRequest.length })
    
    let successCount = 0
    let errorCount = 0
    
    // Request movies one by one sequentially
    for (let i = 0; i < moviesToRequest.length; i++) {
      const movie = moviesToRequest[i]
      
      try {
        // Update progress
        collectionRequestProgress.value.set(franchiseName, { current: i + 1, total: moviesToRequest.length })
        
        // Make request
        const response = await $fetch('/api/overseerr-request', {
          method: 'POST',
          body: {
            mediaId: movie.trakt!.ids!.tmdb!,
            mediaType: 'movie',
            is4k: false
          }
        })
        
        if (response.success) {
          successCount++
        } else {
          errorCount++
          console.error(`Failed to request ${movie.title}:`, response.error)
        }
        
        // Small delay between requests to avoid overwhelming the API
        if (i < moviesToRequest.length - 1) {
          await new Promise(resolve => setTimeout(resolve, 500))
        }
      } catch (error) {
        errorCount++
        console.error(`Error requesting ${movie.title}:`, error)
      }
    }
    
    // Show completion message
    if (successCount > 0) {
      toast.success(
        `Successfully requested ${successCount} ${successCount === 1 ? 'movie' : 'movies'} from "${franchiseName}"`,
        'Collection Request Complete'
      )
    }
    
    if (errorCount > 0) {
      toast.warning(
        `${errorCount} ${errorCount === 1 ? 'movie' : 'movies'} failed to request`,
        'Some Requests Failed'
      )
    }
    
  } catch (error) {
    console.error('Error requesting collection:', error)
    toast.error(
      error instanceof Error ? error.message : 'Failed to request collection',
      'Request Error'
    )
  } finally {
    requestingCollections.value.delete(franchiseName)
    collectionRequestProgress.value.delete(franchiseName)
  }
}

// Load 50 random collections for badges
const loadRandomCollections = async () => {
  if (loadingRandomCollections.value) return
  
  loadingRandomCollections.value = true
  try {
    // Fetch a large batch of collections to choose from
    // Fetch pages in parallel for speed
    const vardarrNames = new Set(VARDARR_CHOICE_FRANCHISES)
    const allCollectionNames: string[] = []
    
    // Fetch first few pages in parallel to get a good pool of collections
    const pagePromises = []
    for (let page = 1; page <= 5; page++) {
      pagePromises.push(
        getCollections(page, 100, '').catch(error => {
          console.warn(`Failed to load page ${page} for random collections:`, error)
          return null
        })
      )
    }
    
    const pageResults = await Promise.all(pagePromises)
    
    // Collect all collection names, excluding Vardarr's Choice
    for (const data of pageResults) {
      if (data && data.collections) {
        for (const collection of data.collections) {
          if (!vardarrNames.has(collection.franchise_name)) {
            allCollectionNames.push(collection.franchise_name)
          }
        }
      }
    }
    
    // Remove duplicates
    const uniqueNames = [...new Set(allCollectionNames)]
    
    // Randomly shuffle and select 50
    const shuffled = [...uniqueNames].sort(() => Math.random() - 0.5)
    const selectedNames = shuffled.slice(0, Math.min(50, uniqueNames.length))
    
    // Fetch metadata for all 50 collections in a single bulk request
    const bulkMetadata = await getBulkCollectionMetadata(selectedNames)
    
    // Create collection objects with metadata
    const randomColls: Collection[] = selectedNames.map(name => {
      const metadata = bulkMetadata?.find(m => m.franchise_name === name)
      return {
        franchise_name: name,
        franchise_url: metadata?.franchise_url,
        movies: [],
        total_movies: metadata?.total_movies || 0,
        years: metadata?.years || [],
        genres: []
      }
    })
    
    randomCollections.value = randomColls
    console.log('Random collections loaded:', randomColls.length, 'collections')
  } catch (error) {
    console.error('Error loading random collections:', error)
  } finally {
    loadingRandomCollections.value = false
  }
}

// Load Vardarr's Choice collections
const loadVardarrChoice = async () => {
  if (loadingVardarrChoice.value) return
  
  loadingVardarrChoice.value = true
  try {
    const choiceCollections: Collection[] = []
    
    // Fetch each favorite collection (get enough movies for stacked effect)
    for (const franchiseName of VARDARR_CHOICE_FRANCHISES) {
      try {
        // Fetch with a high limit to get all movies for the stacked effect
        // We want all movies, but we'll limit the display to 3 for stacking
        const result = await getCollection(franchiseName, 1, 1000, '')
        if (result && result.collection) {
          choiceCollections.push(result.collection)
        }
      } catch (error) {
        console.warn(`Failed to load collection "${franchiseName}":`, error)
        // Continue loading other collections even if one fails
      }
    }
    
    vardarrChoice.value = choiceCollections
    console.log('Vardarr\'s Choice loaded:', choiceCollections.length, 'collections')
    
    // Don't auto-calculate - calculate on-demand when user hovers/interacts
  } catch (error) {
    console.error('Error loading Vardarr\'s Choice:', error)
  } finally {
    loadingVardarrChoice.value = false
  }
}

// Load collections on mount
onMounted(async () => {
  // Initialize search from URL params
  const searchFromUrl = (route.query.search as string) || ''
  if (searchFromUrl) {
    searchQuery.value = searchFromUrl
  }
  
  // Load random collections and Vardarr's Choice (only if not searching)
  if (!searchFromUrl) {
    await Promise.all([
      loadRandomCollections(),
      loadVardarrChoice()
    ])
  }
  
  await refreshCollections()
  
  // Don't calculate requestable counts on initial load - too many requests
  // Calculate them lazily when user interacts with collections
})

// Watch for query param changes
watch(() => route.query.page, (newPage) => {
  if (newPage) {
    const page = parseInt(newPage as string)
    if (page !== currentPage.value && page > 0) {
      currentPage.value = page
      refreshCollections()
    }
  }
})

// Don't auto-calculate on collection changes - calculate on-demand when user hovers/interacts
// This prevents overwhelming the system with too many concurrent requests

// Watch searchQuery for live updates with debounce
let searchTimeout: NodeJS.Timeout | null = null
watch(searchQuery, (newVal, oldVal) => {
  if (searchTimeout) {
    clearTimeout(searchTimeout)
  }
  searchTimeout = setTimeout(() => {
    applySearch()
    
    // Reload random collections and Vardarr's Choice when search is cleared
    if (!newVal && oldVal) {
      if (randomCollections.value.length === 0) {
        loadRandomCollections()
      }
      if (vardarrChoice.value.length === 0) {
        loadVardarrChoice()
      }
    }
  }, 300)
})

// Watch URL query param changes
watch(() => route.query.search, (newSearch) => {
  const searchVal = (newSearch as string) || ''
  if (searchVal !== searchQuery.value) {
    searchQuery.value = searchVal
  }
})

// Page head
useHead({
  title: 'Collections'
})
</script>

<style scoped>
.line-clamp-1 {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>

