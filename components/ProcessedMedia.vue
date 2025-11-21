<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Processed Media</h1>
        <p class="text-sm text-gray-600 dark:text-gray-400">Track all processed movies and TV shows</p>
      </div>
      <Button 
        @click="refreshData" 
        :disabled="loading"
        variant="outline"
        class="flex items-center space-x-2"
      >
        <AppIcon v-if="loading" icon="lucide:loader-2" size="16" class="animate-spin" />
        <AppIcon v-else icon="lucide:refresh-cw" size="16" />
        <span>Refresh</span>
      </Button>
    </div>

    <!-- Stats Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
        <div class="flex items-center">
          <div class="flex-shrink-0">
            <div class="w-8 h-8 bg-green-100 dark:bg-green-900 rounded-full flex items-center justify-center">
              <AppIcon icon="lucide:check-circle" size="20" class="text-green-600 dark:text-green-400" />
            </div>
          </div>
          <div class="ml-4">
            <p class="text-sm font-medium text-gray-500 dark:text-gray-400">Completed</p>
            <p class="text-2xl font-semibold text-gray-900 dark:text-white">{{ stats.completed_count || 0 }}</p>
          </div>
        </div>
      </div>

      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
        <div class="flex items-center">
          <div class="flex-shrink-0">
            <div class="w-8 h-8 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center">
              <AppIcon icon="lucide:cog" size="20" class="text-blue-600 dark:text-blue-400" />
            </div>
          </div>
          <div class="ml-4">
            <p class="text-sm font-medium text-gray-500 dark:text-gray-400">Processing</p>
            <p class="text-2xl font-semibold text-gray-900 dark:text-white">{{ stats.processing_count || 0 }}</p>
          </div>
        </div>
      </div>

      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
        <div class="flex items-center">
          <div class="flex-shrink-0">
            <div class="w-8 h-8 bg-red-100 dark:bg-red-900 rounded-full flex items-center justify-center">
              <AppIcon icon="lucide:x-circle" size="20" class="text-red-600 dark:text-red-400" />
            </div>
          </div>
          <div class="ml-4">
            <p class="text-sm font-medium text-gray-500 dark:text-gray-400">Failed</p>
            <p class="text-2xl font-semibold text-gray-900 dark:text-white">{{ stats.failed_count || 0 }}</p>
          </div>
        </div>
      </div>

      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
        <div class="flex items-center">
          <div class="flex-shrink-0">
            <div class="w-8 h-8 bg-gray-100 dark:bg-gray-900 rounded-full flex items-center justify-center">
              <AppIcon icon="lucide:film" size="20" class="text-gray-600 dark:text-gray-400" />
            </div>
          </div>
          <div class="ml-4">
            <p class="text-sm font-medium text-gray-500 dark:text-gray-400">Total Processed</p>
            <p class="text-2xl font-semibold text-gray-900 dark:text-white">{{ stats.total_media || 0 }}</p>
          </div>
        </div>
      </div>

      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
        <div class="flex items-center">
          <div class="flex-shrink-0">
            <div class="w-8 h-8 bg-purple-100 dark:bg-purple-900 rounded-full flex items-center justify-center">
              <AppIcon icon="lucide:refresh-cw" size="20" class="text-purple-600 dark:text-purple-400" />
            </div>
          </div>
          <div class="ml-4">
            <p class="text-sm font-medium text-gray-500 dark:text-gray-400">Total Requests</p>
            <p class="text-2xl font-semibold text-gray-900 dark:text-white">{{ stats.subscribed_count || 0 }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Filters -->
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
      <div class="flex flex-wrap gap-4 items-center">
        <div class="flex items-center space-x-2">
          <label class="text-sm font-medium text-gray-700 dark:text-gray-300">Status:</label>
          <select 
            v-model="selectedStatus"
            class="w-40 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Statuses</option>
            <option v-for="option in statusOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </div>
        <div class="flex items-center space-x-2">
          <label class="text-sm font-medium text-gray-700 dark:text-gray-300">Type:</label>
          <select 
            v-model="selectedMediaType"
            class="w-32 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Types</option>
            <option v-for="option in mediaTypeOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </div>
        <Button @click="applyFilters" :disabled="loading">
          Apply Filters
        </Button>
        <Button @click="clearFilters" variant="outline" :disabled="loading">
          Clear
        </Button>
      </div>
    </div>

    <!-- Processed Media Fluid Scroller -->
    <div class="relative">
      <!-- Scroll Container -->
      <div 
        ref="scrollContainer"
        class="overflow-x-auto overflow-y-hidden scrollbar-hide select-none"
        @scroll="handleScroll"
        @wheel="handleWheel"
      >
        <div 
          ref="scrollContent"
          class="flex gap-6 px-4 py-2"
        >
          <div 
            v-for="media in processedMedia" 
            :key="media.id" 
            class="flex-shrink-0 w-80 bg-white dark:bg-gray-800 rounded-lg shadow-md hover:shadow-lg transition-all duration-200 border border-gray-200 dark:border-gray-700 overflow-hidden group cursor-grab select-none"
            :class="{ 'cursor-grabbing': isDragging }"
            @mousedown="handleCardMouseDown($event, media)"
            @touchstart="handleCardTouchStart($event, media)"
            @touchmove="handleCardTouchMove"
            @touchend="handleCardTouchEnd"
          >
            <!-- Poster Image Area -->
            <div class="relative bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-700 dark:to-gray-800 overflow-hidden min-h-[200px] flex items-center justify-center">
              <!-- Placeholder for poster image -->
              <div v-if="!media.has_poster_image && !media.has_thumb_image && !media.has_fanart_image" class="text-center p-4">
                <div class="w-16 h-16 mx-auto mb-4 rounded-lg bg-gray-300 dark:bg-gray-600 flex items-center justify-center">
                  <AppIcon 
                    :icon="media.media_type === 'movie' ? 'lucide:film' : 'lucide:tv'" 
                    size="32" 
                    class="text-gray-500 dark:text-gray-400"
                  />
                </div>
                <p class="text-sm text-gray-500 dark:text-gray-400 font-medium line-clamp-2">{{ media.title }}</p>
                <p class="text-xs text-gray-400 dark:text-gray-500">{{ media.year || 'Unknown Year' }}</p>
                <p class="text-xs text-gray-400 dark:text-gray-500 mt-1">No image available</p>
              </div>
              
              <!-- Poster image (cached) -->
              <img 
                v-else-if="media.has_poster_image || media.has_thumb_image || media.has_fanart_image"
                :src="getBestImageUrl(media)"
                :alt="media.title"
                class="w-full object-contain"
                @error="handleImageError"
              />
              
              <!-- Status Badge Overlay -->
              <div class="absolute top-3 right-3">
                <span 
                  :class="getStatusColorClass(media.status || media.processing_status)"
                  class="px-2 py-1 text-xs font-medium rounded-full shadow-lg"
                >
                  {{ getDisplayStatus(media) }}
                </span>
              </div>
              
              <!-- Media Type Badge Overlay -->
              <div class="absolute top-3 left-3">
                <span 
                  :class="media.media_type === 'movie' ? 'bg-blue-500 text-white' : 'bg-green-500 text-white'"
                  class="px-2 py-1 text-xs font-medium rounded-full shadow-lg"
                >
                  {{ media.media_type.toUpperCase() }}
                </span>
              </div>
              
              <!-- Request Count Badge (if multiple requests) -->
              <div v-if="media.request_count && media.request_count > 1" class="absolute bottom-3 right-3">
                <span class="bg-blue-500 text-white px-2 py-1 text-xs font-medium rounded-full shadow-lg flex items-center space-x-1">
                  <AppIcon icon="lucide:check-circle" size="14" />
                  <span>{{ media.request_count }}x</span>
                </span>
              </div>
            </div>

            <!-- Card Body -->
            <div class="p-4 space-y-3">
              <!-- Media Title and Year -->
              <div>
                <h3 class="text-lg font-semibold text-gray-900 dark:text-white line-clamp-2">
                  {{ media.title }}
                </h3>
                <p class="text-sm text-gray-500 dark:text-gray-400">
                  {{ media.year || 'Unknown Year' }} • {{ media.media_type.toUpperCase() }}
                </p>
              </div>

              <!-- Request Information -->
              <div v-if="media.request_count && media.request_count > 1" class="text-sm text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 p-2 rounded">
                <span class="font-medium">Requests:</span> {{ media.request_count }} times
                <div v-if="media.requested_by" class="text-xs mt-1">
                  <span class="font-medium">Requested by:</span> {{ media.requested_by }}
                </div>
              </div>

              <!-- TV Show Information -->
              <div v-if="media.media_type === 'tv'" class="space-y-2">
                <div v-if="media.is_subscribed" class="text-sm text-green-600 dark:text-green-400">
                  <AppIcon icon="lucide:tv" size="14" class="inline mr-1" />
                  <span class="font-medium">Subscribed</span>
                  <span v-if="media.seasons_processing" class="ml-2">(Seasons {{ media.seasons_processing }})</span>
                  <span v-else-if="media.total_seasons" class="ml-2">({{ media.total_seasons }} seasons)</span>
                </div>
                
                <!-- Multi-Season Display -->
                <div v-if="media.seasons && media.seasons.length > 0" class="space-y-2">
                  <div class="text-sm text-gray-600 dark:text-gray-400">
                    <span class="font-medium">Seasons:</span> {{ media.seasons.length }}
                  </div>
                  
                  <!-- Season Breakdown -->
                  <div class="space-y-1">
                    <div v-for="season in media.seasons" :key="season.season_number" class="text-xs bg-gray-50 dark:bg-gray-700 p-2 rounded">
                      <div class="flex justify-between items-center">
                        <span class="font-medium">Season {{ season.season_number }}</span>
                        <span class="text-gray-500">{{ season.aired_episodes }}/{{ season.episode_count }} episodes</span>
                      </div>
                      
                      <!-- Episode Status for this season -->
                      <div v-if="season.aired_episodes > 0" class="mt-1 flex flex-wrap gap-2">
                        <div v-if="season.confirmed_episodes?.length" class="text-green-600 dark:text-green-400">
                          <AppIcon icon="lucide:check-circle" size="10" class="inline mr-1" />
                          {{ season.confirmed_episodes.length }} confirmed
                        </div>
                        <div v-if="season.failed_episodes?.length" class="text-red-600 dark:text-red-400">
                          <AppIcon icon="lucide:x-circle" size="10" class="inline mr-1" />
                          {{ season.failed_episodes.length }} failed
                        </div>
                        <div v-if="season.unprocessed_episodes?.length" class="text-yellow-600 dark:text-yellow-400">
                          <AppIcon icon="lucide:clock" size="10" class="inline mr-1" />
                          {{ season.unprocessed_episodes.length }} pending
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                
                <!-- No season data available -->
                <div v-else class="text-sm text-gray-500 dark:text-gray-400">
                  <AppIcon icon="lucide:info" size="14" class="inline mr-1" />
                  No season data available
                </div>
              </div>

              <!-- Movie Information -->
              <div v-else-if="media.media_type === 'movie'" class="space-y-2">
                <div v-if="media.torrents_found" class="text-sm text-green-600 dark:text-green-400">
                  <AppIcon icon="lucide:download" size="14" class="inline mr-1" />
                  <span class="font-medium">{{ media.torrents_found }} torrents found</span>
                </div>
              </div>

              <!-- Error Message -->
              <div v-if="media.error_message" class="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 p-2 rounded">
                <AppIcon icon="lucide:alert-circle" size="14" class="inline mr-1" />
                <span class="font-medium">Error:</span> {{ media.error_message }}
              </div>

              <!-- Timestamps -->
              <div class="text-xs text-gray-500 dark:text-gray-400 space-y-1">
                <div v-if="media.processing_completed_at">
                  <AppIcon icon="lucide:check-circle" size="12" class="inline mr-1" />
                  <span class="font-medium">Completed:</span> {{ formatDate(media.processing_completed_at) }}
                </div>
                <div v-if="media.last_checked_at">
                  <AppIcon icon="lucide:clock" size="12" class="inline mr-1" />
                  <span class="font-medium">Last Checked:</span> {{ formatDate(media.last_checked_at) }}
                </div>
                <div v-if="media.first_requested_at">
                  <AppIcon icon="lucide:calendar" size="12" class="inline mr-1" />
                  <span class="font-medium">First Requested:</span> {{ formatDate(media.first_requested_at) }}
                </div>
              </div>
            </div>

            <!-- Card Footer -->
            <div class="p-4 border-t border-gray-200 dark:border-gray-700">
              <Button 
                @click="viewDetails(media)" 
                size="sm" 
                variant="outline"
                class="w-full flex items-center justify-center space-x-2"
              >
                <AppIcon icon="lucide:eye" size="16" />
                <span>View Details</span>
              </Button>
            </div>
          </div>
        </div>
      </div>

      <!-- Scroll Progress Indicator -->
      <div v-if="processedMedia.length > 0" class="mt-4">
        <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
          <div 
            class="bg-blue-600 dark:bg-blue-400 h-2 rounded-full transition-all duration-300 ease-out"
            :style="{ width: `${scrollProgress}%` }"
          ></div>
        </div>
        <div class="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
          <span>{{ Math.round(scrollProgress) }}% scrolled</span>
          <span>{{ processedMedia.length }} items</span>
        </div>
      </div>
      
      <!-- Drag Indicator -->
      <div v-if="isDragging" class="absolute inset-0 pointer-events-none">
        <div class="absolute top-4 left-1/2 -translate-x-1/2 bg-black/30 text-white px-3 py-1 rounded-full text-sm backdrop-blur-sm">
          Dragging...
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-if="!loading && processedMedia.length === 0" class="text-center py-12">
      <AppIcon icon="lucide:film" size="48" class="mx-auto text-gray-400" />
      <h3 class="mt-2 text-sm font-medium text-gray-900 dark:text-white">No processed media found</h3>
      <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
        {{ selectedStatus || selectedMediaType ? 'Try adjusting your filters.' : 'No media has been processed yet.' }}
      </p>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-12">
      <AppIcon icon="lucide:loader-2" size="48" class="mx-auto text-gray-400 animate-spin" />
      <h3 class="mt-2 text-sm font-medium text-gray-900 dark:text-white">Loading...</h3>
    </div>

    <!-- Media Details Modal -->
    <div v-if="showDetailsModal" class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <!-- Background overlay -->
        <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" @click="showDetailsModal = false"></div>

        <!-- Modal panel -->
        <div class="inline-block align-bottom bg-white dark:bg-gray-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
          <!-- Header -->
          <div class="bg-white dark:bg-gray-800 px-4 pt-5 pb-4 sm:p-6 sm:pb-4 border-b border-gray-200 dark:border-gray-700">
            <div class="flex items-center justify-between">
              <h3 class="text-lg font-semibold text-gray-900 dark:text-white">{{ selectedMedia?.title }}</h3>
              <Button @click="showDetailsModal = false" variant="ghost" class="p-2">
                <AppIcon icon="lucide:x" size="16" />
              </Button>
            </div>
          </div>

          <!-- Body -->
          <div v-if="selectedMedia" class="bg-white dark:bg-gray-800 px-4 pt-5 pb-4 sm:p-6 space-y-6">
            <!-- Media Image -->
            <div v-if="selectedMedia.has_poster_image || selectedMedia.has_thumb_image || selectedMedia.has_fanart_image" class="flex justify-center">
              <img 
                :src="getBestImageUrl(selectedMedia)"
                :alt="selectedMedia.title"
                class="max-w-full max-h-64 object-contain rounded-lg shadow-md"
                @error="handleImageError"
              />
            </div>
            
            <!-- Basic Information -->
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="text-sm font-medium text-gray-500 dark:text-gray-400">Type</label>
                <p class="text-sm text-gray-900 dark:text-white">{{ selectedMedia.media_type.toUpperCase() }}</p>
              </div>
              <div>
                <label class="text-sm font-medium text-gray-500 dark:text-gray-400">Year</label>
                <p class="text-sm text-gray-900 dark:text-white">{{ selectedMedia.year || 'N/A' }}</p>
              </div>
              <div>
                <label class="text-sm font-medium text-gray-500 dark:text-gray-400">Status</label>
                <span 
                  :class="getStatusColorClass(selectedMedia.status || selectedMedia.processing_status)"
                  class="px-2 py-1 text-xs font-medium rounded-full"
                >
                  {{ getDisplayStatus(selectedMedia) }}
                </span>
              </div>
              <div>
                <label class="text-sm font-medium text-gray-500 dark:text-gray-400">Requests</label>
                <p class="text-sm text-gray-900 dark:text-white">{{ selectedMedia.request_count || 1 }} time(s)</p>
              </div>
            </div>

            <!-- Request Information -->
            <div v-if="selectedMedia.request_count && selectedMedia.request_count > 1" class="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
              <h4 class="text-sm font-medium text-blue-900 dark:text-blue-100 mb-2">Request History</h4>
              <div class="space-y-1 text-sm">
                <div v-if="selectedMedia.requested_by">
                  <span class="font-medium text-blue-800 dark:text-blue-200">Requested by:</span>
                  <span class="text-blue-700 dark:text-blue-300 ml-2">{{ selectedMedia.requested_by }}</span>
                </div>
                <div v-if="selectedMedia.first_requested_at">
                  <span class="font-medium text-blue-800 dark:text-blue-200">First Requested:</span>
                  <span class="text-blue-700 dark:text-blue-300 ml-2">{{ formatDate(selectedMedia.first_requested_at) }}</span>
                </div>
                <div v-if="selectedMedia.last_requested_at">
                  <span class="font-medium text-blue-800 dark:text-blue-200">Last Requested:</span>
                  <span class="text-blue-700 dark:text-blue-300 ml-2">{{ formatDate(selectedMedia.last_requested_at) }}</span>
                </div>
              </div>
            </div>

            <!-- TV Show Information -->
            <div v-if="selectedMedia.media_type === 'tv'" class="space-y-4">
              <h4 class="text-sm font-medium text-gray-900 dark:text-white">TV Show Details</h4>
              
              <!-- Multi-Season Details -->
              <div v-if="selectedMedia.seasons && selectedMedia.seasons.length > 0" class="space-y-4">
                <div class="grid grid-cols-2 gap-4">
                  <div v-if="selectedMedia.is_subscribed">
                    <label class="text-sm font-medium text-gray-500 dark:text-gray-400">Subscription</label>
                    <p class="text-sm text-green-600 dark:text-green-400">Active</p>
                  </div>
                  <div>
                    <label class="text-sm font-medium text-gray-500 dark:text-gray-400">Processing Seasons</label>
                    <p class="text-sm text-gray-900 dark:text-white">{{ selectedMedia.seasons_processing || 'None' }}</p>
                  </div>
                  <div>
                    <label class="text-sm font-medium text-gray-500 dark:text-gray-400">Total Seasons</label>
                    <p class="text-sm text-gray-900 dark:text-white">{{ selectedMedia.total_seasons || selectedMedia.seasons.length }}</p>
                  </div>
                </div>
                
                <!-- Season Details -->
                <div class="space-y-3">
                  <h5 class="text-sm font-medium text-gray-900 dark:text-white">Season Details</h5>
                  <div v-for="season in selectedMedia.seasons" :key="season.season_number" class="bg-gray-50 dark:bg-gray-700 p-3 rounded-lg">
                    <div class="flex justify-between items-center mb-2">
                      <h6 class="font-medium text-gray-900 dark:text-white">Season {{ season.season_number }}</h6>
                      <span class="text-sm text-gray-500">{{ season.aired_episodes }}/{{ season.episode_count }} episodes</span>
                    </div>
                    
                    <div v-if="season.aired_episodes > 0" class="grid grid-cols-3 gap-2 text-xs">
                      <div v-if="season.confirmed_episodes?.length" class="text-green-600 dark:text-green-400">
                        <AppIcon icon="lucide:check-circle" size="12" class="inline mr-1" />
                        {{ season.confirmed_episodes.length }} confirmed
                      </div>
                      <div v-if="season.failed_episodes?.length" class="text-red-600 dark:text-red-400">
                        <AppIcon icon="lucide:x-circle" size="12" class="inline mr-1" />
                        {{ season.failed_episodes.length }} failed
                      </div>
                      <div v-if="season.unprocessed_episodes?.length" class="text-yellow-600 dark:text-yellow-400">
                        <AppIcon icon="lucide:clock" size="12" class="inline mr-1" />
                        {{ season.unprocessed_episodes.length }} pending
                      </div>
                    </div>
                    
                    <div v-if="season.last_checked" class="text-xs text-gray-500 mt-2">
                      Last checked: {{ formatDate(season.last_checked) }}
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- No season data available -->
              <div v-else class="text-center py-8">
                <AppIcon icon="lucide:info" size="24" class="text-gray-400 mx-auto mb-2" />
                <p class="text-gray-500 dark:text-gray-400">No season data available</p>
              </div>
            </div>

            <!-- Movie Information -->
            <div v-else-if="selectedMedia.media_type === 'movie'" class="space-y-4">
              <h4 class="text-sm font-medium text-gray-900 dark:text-white">Movie Details</h4>
              <div class="grid grid-cols-2 gap-4">
                <div v-if="selectedMedia.torrents_found">
                  <label class="text-sm font-medium text-gray-500 dark:text-gray-400">Torrents Found</label>
                  <p class="text-sm text-green-600 dark:text-green-400">{{ selectedMedia.torrents_found }}</p>
                </div>
              </div>
            </div>

            <!-- Timestamps -->
            <div class="space-y-4">
              <h4 class="text-sm font-medium text-gray-900 dark:text-white">Timeline</h4>
              <div class="space-y-2">
                <div v-if="selectedMedia.processing_started_at" class="flex items-center space-x-2">
                  <AppIcon icon="lucide:play" size="14" class="text-blue-500" />
                  <span class="text-sm text-gray-600 dark:text-gray-400">Started:</span>
                  <span class="text-sm text-gray-900 dark:text-white">{{ formatDate(selectedMedia.processing_started_at) }}</span>
                </div>
                <div v-if="selectedMedia.processing_completed_at" class="flex items-center space-x-2">
                  <AppIcon icon="lucide:check-circle" size="14" class="text-green-500" />
                  <span class="text-sm text-gray-600 dark:text-gray-400">Completed:</span>
                  <span class="text-sm text-gray-900 dark:text-white">{{ formatDate(selectedMedia.processing_completed_at) }}</span>
                </div>
                <div v-if="selectedMedia.last_checked_at" class="flex items-center space-x-2">
                  <AppIcon icon="lucide:clock" size="14" class="text-gray-500" />
                  <span class="text-sm text-gray-600 dark:text-gray-400">Last Checked:</span>
                  <span class="text-sm text-gray-900 dark:text-white">{{ formatDate(selectedMedia.last_checked_at) }}</span>
                </div>
              </div>
            </div>

            <!-- Error Message -->
            <div v-if="selectedMedia.error_message" class="bg-red-50 dark:bg-red-900/20 p-4 rounded-lg">
              <h4 class="text-sm font-medium text-red-900 dark:text-red-100 mb-2">Error Details</h4>
              <p class="text-sm text-red-700 dark:text-red-300">{{ selectedMedia.error_message }}</p>
            </div>

            <!-- Technical Details (Collapsible) -->
            <div class="border-t border-gray-200 dark:border-gray-700 pt-4">
              <details class="group">
                <summary class="cursor-pointer text-sm font-medium text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300">
                  Technical Details
                </summary>
                <div class="mt-3 space-y-3">
                  <div v-if="selectedMedia.tmdb_id">
                    <label class="text-xs font-medium text-gray-500 dark:text-gray-400">TMDB ID</label>
                    <p class="text-xs text-gray-600 dark:text-gray-400">{{ selectedMedia.tmdb_id }}</p>
                  </div>
                  <div v-if="selectedMedia.imdb_id">
                    <label class="text-xs font-medium text-gray-500 dark:text-gray-400">IMDB ID</label>
                    <p class="text-xs text-gray-600 dark:text-gray-400">{{ selectedMedia.imdb_id }}</p>
                  </div>
                  <div v-if="selectedMedia.trakt_id">
                    <label class="text-xs font-medium text-gray-500 dark:text-gray-400">Trakt ID</label>
                    <p class="text-xs text-gray-600 dark:text-gray-400">{{ selectedMedia.trakt_id }}</p>
                  </div>
                  <div v-if="selectedMedia.overseerr_request_id">
                    <label class="text-xs font-medium text-gray-500 dark:text-gray-400">Overseerr Request ID</label>
                    <p class="text-xs text-gray-600 dark:text-gray-400">{{ selectedMedia.overseerr_request_id }}</p>
                  </div>
                </div>
              </details>
            </div>
          </div>

          <!-- Footer -->
          <div class="bg-gray-50 dark:bg-gray-700 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
            <Button @click="showDetailsModal = false" class="w-full sm:w-auto">
              Close
            </Button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import Button from '~/components/ui/Button.vue'

interface Season {
  season_number: number
  episode_count: number
  aired_episodes: number
  confirmed_episodes: string[]
  failed_episodes: string[]
  unprocessed_episodes: string[]
  is_discrepant?: boolean
  discrepancy_reason?: string
  discrepancy_details?: Record<string, any>
  status?: string
  season_details?: Record<string, any>
  last_checked?: string
  updated_at: string
}

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
  seasons_processed?: number[]
  confirmed_episodes?: string[]
  failed_episodes?: string[]
  unprocessed_episodes?: string[]
  torrents_found?: number
  error_message?: string
  processing_started_at?: string
  processing_completed_at?: string
  last_checked_at?: string
  extra_data?: any
  created_at: string
  updated_at: string
  // Request tracking fields
  requested_by?: string
  requested_at?: string
  first_requested_at?: string
  last_requested_at?: string
  request_count?: number
  // Subscription data for TV shows
  is_subscribed?: boolean
  subscription_active?: boolean
  subscription_last_checked?: string
  // Enhanced multi-season data structure
  seasons?: Season[]
  total_seasons?: number
  seasons_processing?: string
  seasons_discrepant?: number[]
  seasons_completed?: number[]
  seasons_failed?: number[]
  // Image fields
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
  // Computed fields from API
  has_poster_image?: boolean
  has_thumb_image?: boolean
  has_fanart_image?: boolean
  has_backdrop_image?: boolean
  display_status?: string
  progress_percentage?: number
}

interface Stats {
  status_counts: Record<string, number>
  media_type_counts: Record<string, number>
  recent_activity_24h: number
  total_media: number
  total_movies: number
  total_tv_shows: number
  completed_count: number
  processing_count: number
  failed_count: number
  pending_count: number
  subscribed_count: number
}

const loading = ref(false)
const processedMedia = ref<ProcessedMedia[]>([])
const stats = ref<Stats>({
  status_counts: {},
  media_type_counts: {},
  recent_activity_24h: 0,
  total_media: 0,
  total_movies: 0,
  total_tv_shows: 0,
  completed_count: 0,
  processing_count: 0,
  failed_count: 0,
  pending_count: 0,
  subscribed_count: 0
})

const selectedStatus = ref('')
const selectedMediaType = ref('')
const showDetailsModal = ref(false)
const selectedMedia = ref<ProcessedMedia | null>(null)

// Fluid scrolling
const scrollContainer = ref<HTMLElement>()
const scrollContent = ref<HTMLElement>()
const scrollProgress = ref(0)
const isScrolling = ref(false)

// Enhanced drag functionality
const isDragging = ref(false)
const dragStartX = ref(0)
const dragStartScrollLeft = ref(0)
const dragCurrentX = ref(0)
const dragVelocity = ref(0)
const lastDragTime = ref(0)
const dragMomentum = ref(0)
const isDragMomentum = ref(false)
const dragTarget = ref<ProcessedMedia | null>(null)

const statusOptions = [
  { label: 'All Statuses', value: '' },
  { label: 'Pending', value: 'pending' },
  { label: 'Processing', value: 'processing' },
  { label: 'Completed', value: 'completed' },
  { label: 'Failed', value: 'failed' },
  { label: 'Skipped', value: 'skipped' },
  { label: 'Cancelled', value: 'cancelled' }
]

const mediaTypeOptions = [
  { label: 'All Types', value: '' },
  { label: 'Movies', value: 'movie' },
  { label: 'TV Shows', value: 'tv' }
]

const getStatusColor = (status: string) => {
  switch (status) {
    case 'completed': return 'green'
    case 'processing': return 'blue'
    case 'failed': return 'red'
    case 'pending': return 'yellow'
    case 'skipped': return 'gray'
    default: return 'gray'
  }
}

const getStatusColorClass = (status: string) => {
  // Handle numeric status (e.g., "2/5" for TV shows)
  if (typeof status === 'string' && status.includes('/')) {
    return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
  }
  
  switch (status) {
    case 'completed': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
    case 'processing': return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
    case 'failed': return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
    case 'pending': return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
    case 'skipped': return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
    case 'cancelled': return 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200'
    default: return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
  }
}

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleString()
}

const getEpisodeProgress = (media: ProcessedMedia) => {
  if (media.media_type !== 'tv') {
    return 0
  }
  
  // Use new seasons structure if available
  if (media.seasons && media.seasons.length > 0) {
    const totalAiredEpisodes = media.seasons.reduce((sum, season) => sum + season.aired_episodes, 0)
    const totalConfirmedEpisodes = media.seasons.reduce((sum, season) => sum + (season.confirmed_episodes?.length || 0), 0)
    
    if (totalAiredEpisodes === 0) return 0
    return (totalConfirmedEpisodes / totalAiredEpisodes) * 100
  }
  
  // Fallback to old single-season structure
  if (!media.aired_episodes || media.aired_episodes === 0) {
    return 0
  }
  
  const confirmedCount = media.confirmed_episodes?.length || 0
  return (confirmedCount / media.aired_episodes) * 100
}

const getDisplayStatus = (media: any) => {
  // Use display_status if available (computed by API), otherwise fall back to status
  if (media.display_status) {
    return media.display_status
  }
  
  // Use status as the primary status (from unified_media table)
  const status = media.status
  
  // For TV shows, show more descriptive status based on episode confirmation
  if (media.media_type === 'tv' && media.is_subscribed) {
    let confirmedCount = 0
    let airedCount = 0
    
    // Use new seasons structure if available
    if (media.seasons && media.seasons.length > 0) {
      confirmedCount = media.seasons.reduce((sum, season) => sum + (season.confirmed_episodes?.length || 0), 0)
      airedCount = media.seasons.reduce((sum, season) => sum + season.aired_episodes, 0)
    } else {
      // Fallback to old single-season structure
      confirmedCount = media.confirmed_episodes?.length || 0
      airedCount = media.aired_episodes || 0
    }
    
    if (status === 'completed' && airedCount > 0 && confirmedCount >= airedCount) {
      return 'completed'
    } else if (confirmedCount > 0 && airedCount > 0) {
      return `${confirmedCount}/${airedCount}`
    } else if (media.failed_episodes?.length > 0) {
      return 'failed'
    }
  }
  
  return status
}

const getImageUrl = (mediaId: number, type: 'poster' | 'thumb' | 'fanart' = 'poster') => {
  // Add cache-busting parameter only when data is refreshed to ensure fresh images
  const cacheBuster = loading.value ? `&t=${Date.now()}` : ''
  const url = `/api/media-image/${mediaId}?type=${type}${cacheBuster}`
  console.log('Generated image URL:', url)
  return url
}

const getBestImageUrl = (media: ProcessedMedia) => {
  // Only try to load images if we know they exist
  if (media.has_poster_image) {
    return getImageUrl(media.id, 'poster')
  } else if (media.has_thumb_image) {
    return getImageUrl(media.id, 'thumb')
  } else if (media.has_fanart_image) {
    return getImageUrl(media.id, 'fanart')
  }
  return null
}

const getFallbackImageUrl = (media: ProcessedMedia, type: 'poster' | 'thumb' | 'fanart' = 'poster') => {
  // Never return external URLs - always return null to show placeholder
  return null
}

const handleImageError = (event: Event) => {
  const img = event.target as HTMLImageElement
  console.log('Image failed to load:', img.src)
  img.style.display = 'none'
  
  // Show a fallback placeholder
  const parent = img.parentElement
  if (parent) {
    parent.innerHTML = `
      <div class="text-center p-4">
        <div class="w-16 h-16 mx-auto mb-4 rounded-lg bg-gray-300 dark:bg-gray-600 flex items-center justify-center">
          <svg class="w-8 h-8 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
          </svg>
        </div>
        <p class="text-sm text-gray-500 dark:text-gray-400 font-medium">Image not available</p>
      </div>
    `
  }
}

// Scroll progress calculation
const updateScrollProgress = () => {
  if (!scrollContainer.value) return
  
  const container = scrollContainer.value
  const scrollLeft = container.scrollLeft
  const maxScroll = container.scrollWidth - container.clientWidth
  
  if (maxScroll > 0) {
    scrollProgress.value = (scrollLeft / maxScroll) * 100
  } else {
    scrollProgress.value = 0
  }
}

// Smooth scroll to position
const smoothScrollTo = (position: number) => {
  if (!scrollContainer.value) return
  
  scrollContainer.value.scrollTo({
    left: position,
    behavior: 'smooth'
  })
}

// Scroll by amount with precise control
const scrollBy = (amount: number) => {
  if (!scrollContainer.value) return
  
  const currentScroll = scrollContainer.value.scrollLeft
  const newScroll = Math.max(0, Math.min(
    scrollContainer.value.scrollWidth - scrollContainer.value.clientWidth,
    currentScroll + amount
  ))
  
  // Direct scroll for precise control - no snapping
  scrollContainer.value.scrollLeft = newScroll
  updateScrollProgress()
}

// Enhanced card drag handlers
const handleCardMouseDown = (e: MouseEvent, media: ProcessedMedia) => {
  e.preventDefault()
  startDrag(e, media)
  document.addEventListener('mousemove', handleCardMouseMove)
  document.addEventListener('mouseup', handleCardMouseUp)
}

const handleCardMouseMove = (e: MouseEvent) => {
  if (!isDragging.value) return
  e.preventDefault()
  updateDrag(e)
}

const handleCardMouseUp = () => {
  document.removeEventListener('mousemove', handleCardMouseMove)
  document.removeEventListener('mouseup', handleCardMouseUp)
  endDrag()
}

const handleCardTouchStart = (e: TouchEvent, media: ProcessedMedia) => {
  e.preventDefault()
  startDrag(e, media)
}

const handleCardTouchMove = (e: TouchEvent) => {
  if (!isDragging.value) return
  e.preventDefault()
  updateDrag(e)
}

const handleCardTouchEnd = () => {
  endDrag()
}

// Core drag functions
const startDrag = (e: MouseEvent | TouchEvent, media: ProcessedMedia) => {
  if (isScrolling.value || isDragMomentum.value) return
  
  isDragging.value = true
  dragTarget.value = media
  dragStartX.value = 'touches' in e ? e.touches[0].clientX : e.clientX
  dragCurrentX.value = dragStartX.value
  dragStartScrollLeft.value = scrollContainer.value?.scrollLeft || 0
  dragVelocity.value = 0
  lastDragTime.value = Date.now()
  dragMomentum.value = 0
}

const updateDrag = (e: MouseEvent | TouchEvent) => {
  if (!isDragging.value || !scrollContainer.value) return
  
  const now = Date.now()
  const timeDelta = now - lastDragTime.value
  const currentX = 'touches' in e ? e.touches[0].clientX : e.clientX
  const deltaX = currentX - dragCurrentX.value
  
  // Calculate velocity for momentum
  if (timeDelta > 0) {
    dragVelocity.value = deltaX / timeDelta
  }
  
  // Apply immediate scroll with 1:1 mapping for fluid movement
  const scrollDelta = deltaX // No resistance - direct 1:1 mapping
  const newScrollLeft = Math.max(0, Math.min(
    scrollContainer.value.scrollWidth - scrollContainer.value.clientWidth,
    scrollContainer.value.scrollLeft - scrollDelta
  ))
  
  scrollContainer.value.scrollLeft = newScrollLeft
  updateScrollProgress()
  
  dragCurrentX.value = currentX
  lastDragTime.value = now
}

const endDrag = () => {
  if (!isDragging.value) return
  
  isDragging.value = false
  dragTarget.value = null
  
  // Apply natural momentum scrolling
  const velocity = Math.abs(dragVelocity.value)
  if (velocity > 0.05) { // Lower threshold for more responsive momentum
    isDragMomentum.value = true
    dragMomentum.value = dragVelocity.value * 200 // Reduced multiplier for more control
    
    // Apply momentum with natural decay
    const applyMomentum = () => {
      if (!scrollContainer.value || Math.abs(dragMomentum.value) < 0.05) {
        isDragMomentum.value = false
        dragMomentum.value = 0
        return
      }
      
      const currentScroll = scrollContainer.value.scrollLeft
      const newScroll = Math.max(0, Math.min(
        scrollContainer.value.scrollWidth - scrollContainer.value.clientWidth,
        currentScroll - dragMomentum.value
      ))
      
      scrollContainer.value.scrollLeft = newScroll
      updateScrollProgress()
      
      // Natural decay - slower at first, then faster
      const decayRate = Math.abs(dragMomentum.value) > 5 ? 0.96 : 0.92
      dragMomentum.value *= decayRate
      
      requestAnimationFrame(applyMomentum)
    }
    
    requestAnimationFrame(applyMomentum)
  }
}

// Scroll event handlers
const handleScroll = () => {
  updateScrollProgress()
  isScrolling.value = true
  clearTimeout(scrollTimeout.value)
  scrollTimeout.value = setTimeout(() => {
    isScrolling.value = false
  }, 150)
}

const handleWheel = (e: WheelEvent) => {
  if (!scrollContainer.value || isDragging.value) return
  
  e.preventDefault()
  const scrollAmount = e.deltaY * 1.2 // More precise wheel scrolling
  scrollBy(scrollAmount)
}

// Scroll timeout for smooth transitions
const scrollTimeout = ref<NodeJS.Timeout>()

const refreshData = async () => {
  loading.value = true
  try {
    // Build query parameters
    const params = new URLSearchParams()
    if (selectedStatus.value) params.append('status', selectedStatus.value)
    if (selectedMediaType.value) params.append('mediaType', selectedMediaType.value)
    
    // Make single API call that returns both stats and media
    const response = await $fetch(`/api/processed-media?${params.toString()}`)
    if (response.success) {
      processedMedia.value = response.data.media || []
      stats.value = response.data.stats || {
        status_counts: {},
        media_type_counts: {},
        recent_activity_24h: 0,
        total_media: 0,
        total_movies: 0,
        total_tv_shows: 0,
        completed_count: 0,
        processing_count: 0,
        failed_count: 0,
        pending_count: 0,
        subscribed_count: 0
      }
      // Reset scroll position when data changes
      nextTick(() => {
        if (scrollContainer.value) {
          scrollContainer.value.scrollLeft = 0
          updateScrollProgress()
        }
      })
      
      // Force image refresh by triggering a re-render
      // This will cause the getImageUrl function to add cache-busting parameters
      nextTick(() => {
        // Force reactivity update for images
        processedMedia.value = [...processedMedia.value]
      })
    }
  } catch (error) {
    console.error('Error refreshing data:', error)
    // Show error notification
    const toast = useToast()
    toast.add({
      title: 'Error',
      description: 'Failed to refresh processed media data',
      color: 'red'
    })
  } finally {
    loading.value = false
  }
}

const applyFilters = () => {
  refreshData()
}

const clearFilters = () => {
  selectedStatus.value = ''
  selectedMediaType.value = ''
  refreshData()
}

const viewDetails = (media: ProcessedMedia) => {
  selectedMedia.value = media
  showDetailsModal.value = true
}

// Load data on mount
onMounted(() => {
  refreshData()
  // Initialize scroll progress
  nextTick(() => {
    updateScrollProgress()
  })
})
</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Smooth drag animations */
.cursor-grab {
  cursor: grab;
}

.cursor-grabbing {
  cursor: grabbing;
}

/* Prevent text selection during drag */
.select-none {
  -webkit-user-select: none;
  -moz-user-select: none;
  -ms-user-select: none;
  user-select: none;
}

/* Smooth transitions for all interactive elements */
button {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Enhanced hover effects */
button:hover:not(:disabled) {
  transform: translateY(-1px);
}

button:active:not(:disabled) {
  transform: translateY(0);
}

/* Hide scrollbar but keep functionality */
.scrollbar-hide {
  -ms-overflow-style: none;  /* Internet Explorer 10+ */
  scrollbar-width: none;  /* Firefox */
}

.scrollbar-hide::-webkit-scrollbar {
  display: none;  /* Safari and Chrome */
}

/* Optimize scrolling performance */
.scrollbar-hide {
  scroll-behavior: auto; /* Disable smooth scroll to prevent snapping */
  -webkit-overflow-scrolling: touch; /* iOS momentum scrolling */
}

/* Smooth card interactions */
.cursor-grab {
  cursor: grab;
  transition: transform 0.1s ease-out;
}

.cursor-grabbing {
  cursor: grabbing;
  transform: scale(0.98);
  transition: transform 0.1s ease-out;
}

/* Ensure fluid scrolling without constraints */
.flex {
  scroll-snap-type: none; /* Disable any snap behavior */
}

.flex-shrink-0 {
  scroll-snap-align: none; /* Disable snap alignment */
}

/* Prevent text selection during drag */
.select-none {
  -webkit-user-select: none;
  -moz-user-select: none;
  -ms-user-select: none;
  user-select: none;
  -webkit-touch-callout: none;
}

/* Drag indicator animation */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translate(-50%, -10px);
  }
  to {
    opacity: 1;
    transform: translate(-50%, 0);
  }
}

.absolute.top-4 {
  animation: fadeInUp 0.2s ease-out;
}
</style>
