<template>
  <div class="space-y-8">
    <!-- Header Section -->
    <div class="flex items-center justify-between flex-wrap gap-4">
      <div>
        <h1 class="text-3xl font-bold text-foreground tracking-tight">Processed Media</h1>
        <p class="text-sm text-muted-foreground mt-1">View and manage all processed media in your library</p>
      </div>
      
      <!-- Action Buttons -->
      <div class="flex items-center gap-3">
        <!-- Search -->
        <div class="relative">
          <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <AppIcon icon="lucide:search" size="18" class="text-muted-foreground" />
          </div>
          <input
            v-model="searchQuery"
            @input="debouncedSearch"
            type="text"
            placeholder="Search media..."
            class="w-72 pl-10 pr-4 py-2.5 bg-background border border-input rounded-xl text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        
        <!-- Filter Toggle -->
        <Button 
          @click="showFilters = !showFilters" 
          variant="outline"
          class="gap-2"
        >
          <AppIcon icon="lucide:filter" size="18" />
          <span>Filters</span>
          <span v-if="activeFiltersCount > 0" class="ml-1 inline-flex items-center justify-center min-w-[1.5rem] h-6 px-2 text-xs font-medium text-white bg-primary rounded-full">
            {{ activeFiltersCount }}
          </span>
        </Button>
        
        <!-- Refresh Button -->
        <Button 
          @click="refreshData" 
          :disabled="loading"
          variant="outline"
        >
          <AppIcon v-if="loading" icon="lucide:loader-2" size="18" class="animate-spin" />
          <AppIcon v-else icon="lucide:refresh-cw" size="18" />
        </Button>
      </div>
    </div>
    
    <!-- Stats Section -->
    <div class="bg-card border border-border rounded-2xl p-6 space-y-6">
      <div class="flex items-center justify-between">
        <h2 class="text-xl font-semibold text-foreground">Media Statistics</h2>
        <div class="flex items-center gap-4">
          <span v-if="stats.subscribed_count > 0" class="text-sm text-muted-foreground flex items-center gap-2">
            <AppIcon icon="lucide:bell" size="16" class="text-purple-500" />
            {{ formatNumber(stats.subscribed_count) }} subscriptions
          </span>
          <span class="text-sm text-muted-foreground">{{ formatNumber(stats.total_media || 0) }} total items</span>
        </div>
      </div>
      
      <!-- Status Overview -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div 
          @click="applyStatFilter('', '')"
          class="bg-background border border-border rounded-2xl p-6 shadow-sm hover:shadow-md transition-all cursor-pointer hover:border-primary/50 group relative overflow-hidden"
          :class="{ 'border-primary/50 bg-primary/5': filters.status === '' && filters.mediaType === '' }"
        >
          <div class="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-primary to-purple-500"></div>
          <div class="flex items-center justify-between mb-3">
            <div class="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center group-hover:bg-primary/20 transition-colors">
              <AppIcon icon="lucide:database" size="24" class="text-primary" />
            </div>
            <span class="text-xs font-medium text-muted-foreground">All Statuses</span>
          </div>
          <p class="text-3xl font-bold text-foreground mb-1">{{ formatNumber(stats.total_media || 0) }}</p>
          <p class="text-xs text-muted-foreground">Total media items</p>
        </div>
        
        <div 
          @click="applyStatFilter('completed', '')"
          class="bg-background border border-border rounded-2xl p-6 shadow-sm hover:shadow-md transition-all cursor-pointer hover:border-emerald-500/50 group relative overflow-hidden"
          :class="{ 'border-emerald-500/50 bg-emerald-500/5': filters.status === 'completed' }"
        >
          <div class="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-emerald-500 to-green-500"></div>
          <div class="flex items-center justify-between mb-3">
            <div class="w-12 h-12 bg-emerald-500/10 rounded-xl flex items-center justify-center group-hover:bg-emerald-500/20 transition-colors">
              <AppIcon icon="lucide:check-circle" size="24" class="text-emerald-500" />
            </div>
            <span class="text-xs font-medium text-emerald-500">{{ Math.round((stats.completed_count / stats.total_media) * 100) || 0 }}%</span>
          </div>
          <p class="text-3xl font-bold text-foreground mb-1">{{ formatNumber(stats.completed_count || 0) }}</p>
          <p class="text-xs text-muted-foreground">Successfully completed</p>
        </div>
        
        <div 
          @click="applyStatFilter('processing', '')"
          class="bg-background border border-border rounded-2xl p-6 shadow-sm hover:shadow-md transition-all cursor-pointer hover:border-amber-500/50 group relative overflow-hidden"
          :class="{ 'border-amber-500/50 bg-amber-500/5': filters.status === 'processing' }"
        >
          <div class="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-amber-500 to-orange-500"></div>
          <div class="flex items-center justify-between mb-3">
            <div class="w-12 h-12 bg-amber-500/10 rounded-xl flex items-center justify-center group-hover:bg-amber-500/20 transition-colors">
              <AppIcon icon="lucide:loader-2" size="24" class="text-amber-500 animate-spin" />
            </div>
            <span class="text-xs font-medium text-amber-500">{{ Math.round((stats.processing_count / stats.total_media) * 100) || 0 }}%</span>
          </div>
          <p class="text-3xl font-bold text-foreground mb-1">{{ formatNumber(stats.processing_count || 0) }}</p>
          <p class="text-xs text-muted-foreground">Currently processing</p>
        </div>
        
        <div 
          @click="applyStatFilter('failed', '')"
          class="bg-background border border-border rounded-2xl p-6 shadow-sm hover:shadow-md transition-all cursor-pointer hover:border-red-500/50 group relative overflow-hidden"
          :class="{ 'border-red-500/50 bg-red-500/5': filters.status === 'failed' }"
        >
          <div class="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-red-500 to-rose-500"></div>
          <div class="flex items-center justify-between mb-3">
            <div class="w-12 h-12 bg-red-500/10 rounded-xl flex items-center justify-center group-hover:bg-red-500/20 transition-colors">
              <AppIcon icon="lucide:x-circle" size="24" class="text-red-500" />
            </div>
            <span class="text-xs font-medium text-red-500">{{ Math.round((stats.failed_count / stats.total_media) * 100) || 0 }}%</span>
          </div>
          <p class="text-3xl font-bold text-foreground mb-1">{{ formatNumber(stats.failed_count || 0) }}</p>
          <p class="text-xs text-muted-foreground">Requires attention</p>
        </div>
      </div>
      
      <!-- Divider -->
      <div class="border-t border-border"></div>
      
      <!-- Media Type Breakdown -->
      <div class="flex flex-col lg:flex-row gap-4 lg:gap-0">
        <!-- Movies Card -->
        <div 
          @click="applyStatFilter('', 'movie')"
          class="flex-1 bg-background border border-border rounded-2xl lg:rounded-l-2xl lg:rounded-r-none lg:border-r-0 p-4 shadow-sm hover:shadow-md transition-all cursor-pointer hover:border-primary/50 group"
          :class="{ 'border-primary/50 bg-primary/5': filters.mediaType === 'movie' }"
        >
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 bg-primary/10 rounded-xl flex items-center justify-center group-hover:bg-primary/20 transition-colors">
                <AppIcon icon="lucide:film" size="20" class="text-primary" />
              </div>
              <div>
                <h3 class="text-xl font-bold text-foreground">{{ formatNumber(stats.total_movies || 0) }}</h3>
                <p class="text-xs text-muted-foreground">Movies</p>
              </div>
            </div>
            <span class="text-xs font-semibold px-2.5 py-1 bg-primary/10 text-primary rounded-full">
              {{ Math.round((stats.total_movies / stats.total_media) * 100) || 0 }}%
            </span>
          </div>
          
          <div class="grid grid-cols-3 gap-2 pt-3 border-t border-border">
            <div>
              <p class="text-xs text-muted-foreground mb-0.5">Completed</p>
              <p class="text-base font-bold text-foreground">{{ formatNumber(stats.movies_completed || 0) }}</p>
            </div>
            <div>
              <p class="text-xs text-muted-foreground mb-0.5">Processing</p>
              <p class="text-base font-bold text-foreground">{{ formatNumber(stats.movies_processing || 0) }}</p>
            </div>
            <div>
              <p class="text-xs text-muted-foreground mb-0.5">Failed</p>
              <p class="text-base font-bold text-foreground">{{ formatNumber(stats.movies_failed || 0) }}</p>
            </div>
          </div>
        </div>
        
        <!-- Vertical Divider -->
        <div class="hidden lg:block w-px bg-border self-stretch"></div>
        
        <!-- TV Shows Card -->
        <div 
          @click="applyStatFilter('', 'tv')"
          class="flex-1 bg-background border border-border rounded-2xl lg:rounded-r-2xl lg:rounded-l-none lg:border-l-0 p-4 shadow-sm hover:shadow-md transition-all cursor-pointer hover:border-primary/50 group"
          :class="{ 'border-primary/50 bg-primary/5': filters.mediaType === 'tv' }"
        >
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 bg-primary/10 rounded-xl flex items-center justify-center group-hover:bg-primary/20 transition-colors">
                <AppIcon icon="lucide:tv" size="20" class="text-primary" />
              </div>
              <div>
                <h3 class="text-xl font-bold text-foreground">{{ formatNumber(stats.total_tv_shows || 0) }}</h3>
                <p class="text-xs text-muted-foreground">TV Shows</p>
              </div>
            </div>
            <span class="text-xs font-semibold px-2.5 py-1 bg-primary/10 text-primary rounded-full">
              {{ Math.round((stats.total_tv_shows / stats.total_media) * 100) || 0 }}%
            </span>
          </div>
          
          <div class="grid grid-cols-3 gap-2 pt-3 border-t border-border">
            <div>
              <p class="text-xs text-muted-foreground mb-0.5">Completed</p>
              <p class="text-base font-bold text-foreground">{{ formatNumber(stats.tv_completed || 0) }}</p>
            </div>
            <div>
              <p class="text-xs text-muted-foreground mb-0.5">Processing</p>
              <p class="text-base font-bold text-foreground">{{ formatNumber(stats.tv_processing || 0) }}</p>
            </div>
            <div>
              <p class="text-xs text-muted-foreground mb-0.5">Failed</p>
              <p class="text-base font-bold text-foreground">{{ formatNumber(stats.tv_failed || 0) }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Filters Panel -->
    <Transition
      enter-active-class="transition-all duration-300 ease-out"
      enter-from-class="opacity-0 -translate-y-2"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition-all duration-200 ease-in"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 -translate-y-2"
    >
      <div v-if="showFilters" class="bg-card rounded-2xl p-6 border border-border">
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label class="block text-sm font-semibold text-foreground mb-2">Status</label>
            <select 
              v-model="filters.status" 
              class="w-full px-4 py-2.5 bg-background border border-input rounded-xl text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="">All Statuses</option>
              <option v-for="option in statusOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </div>
          
          <div>
            <label class="block text-sm font-semibold text-foreground mb-2">Media Type</label>
            <select 
              v-model="filters.mediaType" 
              class="w-full px-4 py-2.5 bg-background border border-input rounded-xl text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="">All Types</option>
              <option v-for="option in mediaTypeOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </div>
          
          <div>
            <label class="block text-sm font-semibold text-foreground mb-2">Sort By</label>
            <select 
              v-model="filters.sortBy" 
              class="w-full px-4 py-2.5 bg-background border border-input rounded-xl text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="updated_at">Last Updated</option>
              <option value="title">Title</option>
              <option value="year">Year</option>
              <option value="status">Status</option>
              <option value="request_count">Request Count</option>
            </select>
          </div>
          
          <div class="flex items-end gap-2">
            <Button 
              @click="applyFilters" 
              :disabled="loading" 
              class="flex-1"
            >
              Apply
            </Button>
            <Button 
              @click="clearFilters" 
              variant="outline"
            >
              Clear
            </Button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Media Grid -->
    <div v-if="!loading && mediaItems.length > 0" class="grid grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-6">
      <div
        v-for="media in mediaItems"
        :key="media.id"
        @click="viewDetails(media)"
        class="group relative bg-card rounded-2xl overflow-hidden cursor-pointer transition-all hover:shadow-2xl hover:-translate-y-2 border border-border"
      >
        <!-- Poster Container -->
        <div class="relative aspect-[2/3] bg-muted">
          <!-- Image -->
          <img
            v-if="getBestImageUrl(media)"
            :src="getBestImageUrl(media)"
            :alt="media.title"
            class="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
            @error="handleImageError"
          />
          
          <!-- Placeholder -->
          <div v-else class="w-full h-full flex items-center justify-center p-6">
            <div class="text-center">
              <div class="w-16 h-16 mx-auto mb-3 rounded-2xl bg-muted flex items-center justify-center">
                <AppIcon 
                  :icon="media.media_type === 'movie' ? 'lucide:film' : 'lucide:tv'" 
                  size="32" 
                  class="text-muted-foreground"
                />
              </div>
              <p class="text-xs text-muted-foreground font-medium line-clamp-2">{{ media.title }}</p>
            </div>
          </div>
          
          <!-- Status Badge with Boat Icon -->
          <div class="absolute top-3 right-3 z-10">
            <div 
              :class="getStatusIconClass(media)" 
              class="w-8 h-8 rounded-lg backdrop-blur-md shadow-lg flex items-center justify-center"
            >
              <AppIcon 
                :icon="getStatusIcon(media)" 
                size="16" 
                :class="getStatusIconColor(media)"
              />
            </div>
          </div>
          
          <!-- Media Type Badge -->
          <div class="absolute top-3 left-3 z-10">
            <span 
              :class="media.media_type === 'movie' ? 'bg-muted/90' : 'bg-muted/90'" 
              class="px-3 py-1 text-xs font-semibold text-foreground rounded-full backdrop-blur-md shadow-lg border border-border/50"
            >
              {{ media.media_type.toUpperCase() }}
            </span>
          </div>
          
          <!-- Request Count -->
          <div v-if="media.request_count && media.request_count > 1" class="absolute bottom-3 right-3 z-10">
            <span class="bg-muted/90 text-foreground px-2 py-1 text-xs font-semibold rounded-full backdrop-blur-md shadow-lg border border-border/50 flex items-center gap-1">
              <AppIcon icon="lucide:repeat" size="10" />
              {{ media.request_count }}x
            </span>
          </div>
          
          <!-- Error Badge (only show icon, not when completed) -->
          <div v-if="media.error_message && getDisplayStatus(media) !== 'completed'" class="absolute bottom-3 left-3 z-10">
            <div class="bg-muted/90 backdrop-blur-md shadow-lg flex items-center justify-center w-8 h-8 rounded-lg border border-border/50">
              <AppIcon icon="lucide:alert-circle" size="16" class="text-foreground" />
            </div>
          </div>
          
          <!-- Progress Bar -->
          <div v-if="media.media_type === 'tv' && media.progress_percentage > 0" class="absolute bottom-0 left-0 right-0 z-10">
            <div class="h-1.5 bg-black/50">
              <div 
                class="h-full bg-emerald-500 transition-all duration-500"
                :style="{ width: `${media.progress_percentage}%` }"
              />
            </div>
          </div>
        </div>
        
        <!-- Card Info -->
        <div class="p-4 space-y-2">
          <h3 class="text-sm font-bold text-foreground line-clamp-2">
            {{ media.title }}
          </h3>
          <p class="text-xs text-muted-foreground">
            {{ media.year || 'N/A' }}
          </p>
          <div class="flex items-center gap-2">
            <div v-if="media.rating" class="flex items-center text-xs text-muted-foreground">
              <AppIcon icon="lucide:star" size="12" class="text-amber-500 mr-0.5" />
              <span class="font-semibold">{{ media.rating }}</span>
            </div>
            <div v-if="media.genres && media.genres.length > 0" class="flex-1">
              <span class="text-xs px-2 py-0.5 bg-muted text-foreground rounded-full">
                {{ media.genres[0] }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Loading State -->
    <div v-if="loading && mediaItems.length === 0" class="flex items-center justify-center py-24">
      <div class="text-center">
        <div class="w-20 h-20 mx-auto mb-6 bg-primary/10 rounded-2xl flex items-center justify-center">
          <AppIcon icon="lucide:loader-2" size="40" class="text-primary animate-spin" />
        </div>
        <h3 class="text-xl font-semibold text-foreground mb-2">Loading media library</h3>
        <p class="text-sm text-muted-foreground">Please wait while we fetch your processed media</p>
      </div>
    </div>
    
    <!-- Loading More -->
    <div v-if="loadingMore" class="flex items-center justify-center py-12">
      <div class="flex items-center gap-3 px-6 py-3 bg-card rounded-xl border border-border shadow-sm">
        <AppIcon icon="lucide:loader-2" size="20" class="animate-spin text-primary" />
        <span class="text-sm font-medium text-muted-foreground">Loading more items...</span>
      </div>
    </div>
    
    <!-- Empty State -->
    <div v-if="!loading && mediaItems.length === 0" class="text-center py-24">
      <div class="inline-flex w-24 h-24 mb-6 bg-muted rounded-3xl items-center justify-center">
        <AppIcon icon="lucide:film" size="48" class="text-muted-foreground" />
      </div>
      <h3 class="text-2xl font-bold text-foreground mb-3">No media found</h3>
      <p class="text-muted-foreground mb-8 max-w-md mx-auto">
        {{ searchQuery || activeFiltersCount > 0 ? 'Try adjusting your search or filters' : 'No media has been processed yet' }}
      </p>
      <Button 
        v-if="activeFiltersCount > 0" 
        @click="clearFilters"
      >
        Clear Filters
      </Button>
    </div>
    
    <!-- Load More -->
    <div v-if="hasMore && !loadingMore" class="flex justify-center mt-12">
      <Button 
        @click="loadMore" 
        variant="outline"
        class="gap-2"
      >
        <AppIcon icon="lucide:download" size="18" />
        Load More
      </Button>
    </div>
  </div>
  
  <!-- Modal -->
  <Transition
    enter-active-class="transition-all duration-300"
    enter-from-class="opacity-0"
    enter-to-class="opacity-100"
    leave-active-class="transition-all duration-200"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <div v-if="showDetailsModal" class="fixed inset-0 z-50 overflow-y-auto p-4">
      <!-- Overlay -->
      <div 
        class="fixed inset-0 bg-black/80 backdrop-blur-sm" 
        @click="closeModal"
      ></div>
      
      <!-- Modal Content -->
      <div class="relative mx-auto max-w-4xl my-8 bg-card rounded-3xl shadow-2xl overflow-hidden">
        <!-- Hero -->
        <div v-if="selectedMedia" class="relative h-80 overflow-hidden bg-gradient-to-br from-primary/20 to-primary/10">
          <img
            v-if="getBestImageUrl(selectedMedia)"
            :src="getBestImageUrl(selectedMedia)"
            :alt="selectedMedia.title"
            class="absolute inset-0 w-full h-full object-cover opacity-20"
          />
          
          <!-- Top Right Buttons -->
          <div class="absolute top-4 right-4 z-10 flex items-center gap-2">
            <!-- Action Menu -->
            <div class="relative action-menu-container">
              <Button
                @click.stop="showActionMenu = !showActionMenu"
                variant="outline"
                class="w-12 h-12 rounded-full bg-background/90 backdrop-blur-md hover:bg-background border-border hover:border-primary/50 hover:bg-primary/10 transition-all duration-200"
              >
                <AppIcon 
                  icon="lucide:more-horizontal" 
                  size="24"
                  class="text-foreground hover:text-primary transition-colors duration-200"
                />
              </Button>
              
              <!-- Action Menu Dropdown -->
              <Transition
                enter-active-class="transition-all duration-200"
                enter-from-class="opacity-0 -translate-y-2"
                enter-to-class="opacity-100 translate-y-0"
                leave-active-class="transition-all duration-150"
                leave-from-class="opacity-100 translate-y-0"
                leave-to-class="opacity-0 -translate-y-2"
              >
                <div v-if="showActionMenu" class="absolute right-0 top-14 w-64 bg-background rounded-xl border border-border shadow-lg p-2 z-20">
                  <!-- Processing Status -->
                  <div class="px-3 py-2 border-b border-border mb-2">
                    <div class="flex items-center justify-between">
                      <span class="text-xs font-medium text-muted-foreground">Processing Status</span>
                      <span :class="getStatusBadgeClass(selectedMedia)" class="px-2 py-0.5 text-xs font-semibold rounded-full">
                        {{ selectedMedia.status === 'ignored' ? 'Ignored' : 'Active' }}
                      </span>
                    </div>
                    <p class="text-xs text-muted-foreground mt-1">
                      {{ selectedMedia.status === 'ignored' ? 'Not processed by background tasks' : 'Will be processed by background tasks' }}
                    </p>
                  </div>
                  
                  <!-- Actions -->
                  <div class="space-y-1">
                    <!-- View in Overseerr -->
                    <a
                      v-if="getOverseerrUrl(selectedMedia)"
                      :href="getOverseerrUrl(selectedMedia)"
                      target="_blank"
                      rel="noopener noreferrer"
                      @click.stop
                      class="w-full flex items-center gap-3 px-3 py-2 text-sm text-primary hover:bg-primary/10 rounded-lg transition-colors"
                    >
                      <AppIcon icon="lucide:external-link" size="16" />
                      View in Overseerr
                    </a>
                    
                    <button
                      @click.stop="retriggerMedia"
                      :disabled="selectedMedia.status === 'ignored'"
                      class="w-full flex items-center gap-3 px-3 py-2 text-sm text-foreground hover:bg-muted rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <AppIcon icon="lucide:refresh-cw" size="16" />
                      Re-trigger Processing
                    </button>
                    
                    <button
                      @click.stop="toggleIgnoreStatus"
                      class="w-full flex items-center gap-3 px-3 py-2 text-sm text-foreground hover:bg-muted rounded-lg transition-colors"
                    >
                      <AppIcon :icon="selectedMedia.status === 'ignored' ? 'lucide:play' : 'lucide:pause'" size="16" />
                      {{ selectedMedia.status === 'ignored' ? 'Enable Processing' : 'Ignore Processing' }}
                    </button>
                    
                    <div class="border-t border-border my-1"></div>
                    
                    <button
                      @click.stop="confirmDeleteMedia"
                      class="w-full flex items-center gap-3 px-3 py-2 text-sm text-red-600 hover:bg-red-500/10 rounded-lg transition-colors"
                    >
                      <AppIcon icon="lucide:trash-2" size="16" />
                      Delete Media Item
                    </button>
                  </div>
                </div>
              </Transition>
            </div>
            
            <!-- Subscription Button (for TV shows) -->
            <Button
              v-if="selectedMedia.media_type === 'tv'"
              @click.stop="toggleSubscription"
              :variant="selectedMedia.is_subscribed ? 'default' : 'outline'"
              class="w-12 h-12 rounded-full bg-background/90 backdrop-blur-md hover:bg-background border-border hover:border-purple-500/50 hover:bg-purple-500/10 transition-all duration-200"
            >
              <AppIcon 
                :icon="selectedMedia.is_subscribed ? 'lucide:bell' : 'lucide:bell-off'" 
                size="24"
                :class="selectedMedia.is_subscribed ? 'text-purple-500 hover:text-purple-600' : 'text-muted-foreground hover:text-purple-500'"
              />
            </Button>
            
            <!-- Close Button -->
            <Button 
              @click="closeModal" 
              variant="outline"
              class="w-12 h-12 rounded-full bg-background/90 backdrop-blur-md hover:bg-background border-border hover:border-red-500/50 hover:bg-red-500/10 transition-all duration-200"
            >
              <AppIcon icon="lucide:x" size="24" class="text-foreground hover:text-red-500 transition-colors duration-200" />
            </Button>
          </div>
          
          <!-- Content -->
          <div class="relative h-full flex items-end p-8">
            <div class="flex gap-6 w-full">
              <!-- Poster -->
              <div class="flex-shrink-0">
                <div class="w-40 h-60 rounded-2xl overflow-hidden shadow-2xl ring-2 ring-border">
                  <img
                    v-if="getBestImageUrl(selectedMedia)"
                    :src="getBestImageUrl(selectedMedia)"
                    :alt="selectedMedia.title"
                    class="w-full h-full object-cover"
                  />
                  <div
                    v-else
                    class="w-full h-full bg-muted flex items-center justify-center"
                  >
                    <AppIcon 
                      :icon="selectedMedia.media_type === 'movie' ? 'lucide:film' : 'lucide:tv'" 
                      size="48" 
                      class="text-muted-foreground"
                    />
                  </div>
                </div>
              </div>
              
              <!-- Info -->
              <div class="flex-1 pb-2">
                <div class="flex gap-2 mb-3 flex-wrap">
                  <span 
                    class="px-3 py-1 text-xs font-semibold bg-muted text-foreground rounded-full border border-border"
                  >
                    {{ selectedMedia.media_type.toUpperCase() }}
                  </span>
                  <span class="px-3 py-1 text-xs font-semibold bg-muted text-foreground rounded-full border border-border">
                    {{ getDisplayStatus(selectedMedia) }}
                  </span>
                  <span 
                    v-if="selectedMedia.media_type === 'tv'"
                    class="px-3 py-1 text-xs font-semibold bg-muted text-foreground rounded-full border border-border flex items-center gap-1"
                  >
                    <AppIcon :icon="selectedMedia.is_subscribed ? 'lucide:bell' : 'lucide:bell-off'" size="12" />
                    {{ selectedMedia.is_subscribed ? 'Subscribed' : 'Not Subscribed' }}
                  </span>
                </div>
                
                <h2 class="text-3xl font-bold text-foreground mb-3">{{ selectedMedia.title }}</h2>
                
                <!-- Season Status Overview for TV Shows -->
                <div v-if="selectedMedia.media_type === 'tv' && selectedMedia.seasons && selectedMedia.seasons.length > 0" class="mb-4">
                  <div class="flex items-center gap-3 flex-wrap">
                    <div class="flex items-center gap-2">
                      <AppIcon icon="lucide:tv" size="14" class="text-muted-foreground" />
                      <span class="text-sm font-medium text-foreground">Seasons:</span>
                    </div>
                    <div class="flex flex-wrap gap-2">
                      <span 
                        v-for="season in selectedMedia.seasons" 
                        :key="season.season_number"
                        :class="getSeasonStatusBadgeClass(season)" 
                        class="px-2 py-1 text-xs font-semibold rounded-full flex items-center gap-1"
                      >
                        <AppIcon :icon="getSeasonStatusIcon(season)" size="10" />
                        S{{ season.season_number }}: {{ getSeasonStatusText(season) }}
                      </span>
                    </div>
                  </div>
                </div>
                
                <div class="flex items-center gap-4 mb-4 flex-wrap">
                  <span class="text-muted-foreground">{{ selectedMedia.year || 'N/A' }}</span>
                  <span v-if="selectedMedia.runtime" class="inline-flex items-center gap-1">
                    <AppIcon icon="lucide:clock" size="14" class="text-muted-foreground" />
                    <span class="text-muted-foreground">{{ selectedMedia.runtime }} min</span>
                  </span>
                  <span v-if="selectedMedia.rating" class="inline-flex items-center gap-1">
                    <AppIcon icon="lucide:star" size="16" class="text-amber-500" />
                    <span class="font-semibold text-foreground">{{ selectedMedia.rating }}</span>
                  </span>
                  <!-- Genres as badges -->
                  <div v-if="selectedMedia.genres && selectedMedia.genres.length > 0" class="flex items-center gap-2 flex-wrap">
                    <span 
                      v-for="genre in selectedMedia.genres.slice(0, 3)" 
                      :key="genre"
                      class="px-2 py-1 text-xs font-medium bg-muted text-foreground rounded-full border border-border"
                    >
                      {{ genre }}
                    </span>
                    <span v-if="selectedMedia.genres.length > 3" class="px-2 py-1 text-xs font-medium bg-muted text-muted-foreground rounded-full border border-border">
                      +{{ selectedMedia.genres.length - 3 }} more
                    </span>
                  </div>
                </div>
                <p v-if="selectedMedia.overview" class="text-muted-foreground line-clamp-2 max-w-2xl">
                  {{ selectedMedia.overview }}
                </p>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Body -->
        <div v-if="selectedMedia" class="px-8 py-8 space-y-6">
          <!-- Enhanced Status & Progress Cards -->
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <!-- Status & Processing Info -->
            <div class="bg-gradient-to-br from-muted to-muted/50 rounded-2xl p-6 border border-border">
              <div class="flex items-center gap-3 mb-4">
                <div class="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center">
                  <AppIcon icon="lucide:activity" size="24" class="text-primary" />
                </div>
                <div>
                  <h3 class="text-lg font-bold text-foreground">Processing Status</h3>
                  <span class="text-sm font-semibold px-3 py-1 rounded-full bg-muted text-foreground border border-border">
                    {{ getDisplayStatus(selectedMedia) }}
                  </span>
                </div>
              </div>
              
              <div class="space-y-3">
                <div class="flex items-center justify-between">
                  <span class="text-sm text-muted-foreground">Database Status</span>
                  <span class="text-sm font-medium text-foreground">{{ selectedMedia.status }}</span>
                </div>
                
                <div v-if="selectedMedia.request_count" class="flex items-center justify-between">
                  <span class="text-sm text-muted-foreground">Request Count</span>
                  <span class="text-sm font-medium text-foreground">{{ selectedMedia.request_count }}x</span>
                </div>
                
                <div v-if="selectedMedia.processing_stage" class="flex items-center justify-between">
                  <span class="text-sm text-muted-foreground">Processing Stage</span>
                  <span class="text-sm font-medium text-foreground">{{ selectedMedia.processing_stage }}</span>
                </div>
                
                <div v-if="selectedMedia.torrents_found" class="flex items-center justify-between">
                  <span class="text-sm text-muted-foreground">Torrents Found</span>
                  <span class="text-sm font-medium text-foreground">{{ selectedMedia.torrents_found }}</span>
                </div>
                
                <div v-if="selectedMedia.last_checked_at" class="flex items-center justify-between">
                  <span class="text-sm text-muted-foreground">Last Checked</span>
                  <span class="text-sm font-medium text-foreground">{{ formatDate(selectedMedia.last_checked_at) }}</span>
                </div>
              </div>
            </div>
            
            <!-- Progress & Timeline -->
            <div class="bg-gradient-to-br from-muted to-muted/50 rounded-2xl p-6 border border-border">
              <div class="flex items-center gap-3 mb-4">
                <div class="w-12 h-12 bg-emerald-600/10 rounded-xl flex items-center justify-center">
                  <AppIcon icon="lucide:trending-up" size="24" class="text-emerald-600" />
                </div>
                <div>
                  <h3 class="text-lg font-bold text-foreground">Progress & Timeline</h3>
                  <span v-if="selectedMedia.media_type === 'tv' && selectedMedia.progress_percentage > 0" class="text-sm font-semibold text-emerald-600">
                    {{ Math.round(selectedMedia.progress_percentage) }}% Complete
                  </span>
                </div>
              </div>
              
              <!-- Progress Bar for TV Shows -->
              <div v-if="selectedMedia.media_type === 'tv' && selectedMedia.progress_percentage > 0" class="mb-4">
                <div class="w-full bg-muted rounded-full h-3 overflow-hidden">
                  <div 
                    class="h-full bg-gradient-to-r from-emerald-500 to-emerald-600 transition-all duration-500 rounded-full"
                    :style="{ width: `${selectedMedia.progress_percentage}%` }"
                  />
                </div>
              </div>
              
              <div class="space-y-3">
                <div v-if="selectedMedia.processing_started_at" class="flex items-center justify-between">
                  <span class="text-sm text-muted-foreground">Processing Started</span>
                  <span class="text-sm font-medium text-foreground">{{ formatDate(selectedMedia.processing_started_at) }}</span>
                </div>
                
                <div v-if="selectedMedia.processing_completed_at" class="flex items-center justify-between">
                  <span class="text-sm text-muted-foreground">Processing Completed</span>
                  <span class="text-sm font-medium text-foreground">{{ formatDate(selectedMedia.processing_completed_at) }}</span>
                </div>
                
                <div v-if="selectedMedia.first_requested_at" class="flex items-center justify-between">
                  <span class="text-sm text-muted-foreground">First Requested</span>
                  <span class="text-sm font-medium text-foreground">{{ formatDate(selectedMedia.first_requested_at) }}</span>
                </div>
                
                <div v-if="selectedMedia.last_requested_at" class="flex items-center justify-between">
                  <span class="text-sm text-muted-foreground">Last Requested</span>
                  <span class="text-sm font-medium text-foreground">{{ formatDate(selectedMedia.last_requested_at) }}</span>
                </div>
                
                <div v-if="selectedMedia.error_count && selectedMedia.error_count > 0" class="flex items-center justify-between">
                  <span class="text-sm text-muted-foreground">Error Count</span>
                  <span class="text-sm font-medium text-red-600">{{ selectedMedia.error_count }}</span>
                </div>
              </div>
            </div>
          </div>
          
          
          
          <!-- TV Seasons -->
          <div v-if="selectedMedia.media_type === 'tv' && selectedMedia.seasons && selectedMedia.seasons.length > 0" class="border-t border-border pt-6">
            <!-- Season Details Toggle -->
            <button 
              @click="toggleSeason(0)"
              class="flex items-center justify-between w-full mb-4 group hover:bg-muted/50 rounded-lg p-2 transition-colors"
            >
              <span class="text-sm font-medium text-foreground">Season Details</span>
              <AppIcon 
                icon="lucide:chevron-down" 
                size="16" 
                class="text-muted-foreground transition-transform duration-200"
                :class="{ 'rotate-180': expandedSeasons.has(0) }"
              />
            </button>
            
            <Transition
              enter-active-class="transition-all duration-300"
              enter-from-class="opacity-0 -translate-y-2"
              enter-to-class="opacity-100 translate-y-0"
              leave-active-class="transition-all duration-200"
              leave-from-class="opacity-100 translate-y-0"
              leave-to-class="opacity-0 -translate-y-2"
            >
              <div v-if="expandedSeasons.has(0)" class="space-y-3">
                <div 
                  v-for="season in selectedMedia.seasons" 
                  :key="season.season_number"
                  :class="season.is_discrepant ? 'bg-muted rounded-xl p-4 border-2 border-orange-500/50' : 'bg-muted rounded-xl p-4 border border-border'"
                >
                  <div class="flex items-center justify-between mb-3">
                    <div class="flex items-center gap-2">
                      <h5 class="text-sm font-bold text-foreground">Season {{ season.season_number }}</h5>
                      <!-- Season Status Badge -->
                      <span :class="getSeasonStatusBadgeClass(season)" class="px-2 py-0.5 rounded-full text-xs font-semibold flex items-center gap-1">
                        <AppIcon :icon="getSeasonStatusIcon(season)" size="12" />
                        {{ getSeasonStatusText(season) }}
                      </span>
                      <span v-if="season.is_discrepant" class="px-2 py-0.5 bg-orange-500/20 text-orange-500 rounded-full text-xs font-semibold flex items-center gap-1">
                        <AppIcon icon="lucide:alert-triangle" size="12" />
                        Discrepant
                      </span>
                    </div>
                    <span class="text-xs text-muted-foreground">{{ season.aired_episodes }}/{{ season.episode_count }} aired</span>
                  </div>
                  
                  <!-- Discrepancy Details -->
                  <div v-if="season.is_discrepant && season.discrepancy_reason" class="mb-3 p-2 bg-orange-500/10 border border-orange-500/20 rounded-lg">
                    <p class="text-xs font-semibold text-orange-600 mb-1">Discrepancy Notice</p>
                    <p class="text-xs text-orange-500">{{ season.discrepancy_reason }}</p>
                  </div>
                  
                  <div v-if="season.episode_count > 0" class="grid grid-cols-2 lg:grid-cols-4 gap-2 mb-3">
                    <div v-if="season.confirmed_episodes && season.confirmed_episodes.length" class="flex items-center gap-2 p-2 bg-emerald-600/10 rounded-lg border border-emerald-600/20">
                      <AppIcon icon="lucide:check-circle" size="14" class="text-emerald-600" />
                      <div>
                        <p class="text-xs text-muted-foreground font-medium">Confirmed</p>
                        <p class="text-sm font-bold text-foreground">{{ season.confirmed_episodes.length }}</p>
                      </div>
                    </div>
                    <div v-if="season.failed_episodes && season.failed_episodes.length" class="flex items-center gap-2 p-2 bg-red-600/10 rounded-lg border border-red-600/20">
                      <AppIcon icon="lucide:x-circle" size="14" class="text-red-600" />
                      <div>
                        <p class="text-xs text-muted-foreground font-medium">Failed</p>
                        <p class="text-sm font-bold text-foreground">{{ season.failed_episodes.length }}</p>
                      </div>
                    </div>
                    <div v-if="season.unprocessed_episodes && season.unprocessed_episodes.length" class="flex items-center gap-2 p-2 bg-amber-600/10 rounded-lg border border-amber-600/20">
                      <AppIcon icon="lucide:clock" size="14" class="text-amber-600" />
                      <div>
                        <p class="text-xs text-muted-foreground font-medium">Pending</p>
                        <p class="text-sm font-bold text-foreground">{{ season.unprocessed_episodes.length }}</p>
                      </div>
                    </div>
                    <div v-if="season.episode_count > season.aired_episodes" class="flex items-center gap-2 p-2 bg-blue-600/10 rounded-lg border border-blue-600/20">
                      <AppIcon icon="lucide:calendar" size="14" class="text-blue-600" />
                      <div>
                        <p class="text-xs text-muted-foreground font-medium">Unaired</p>
                        <p class="text-sm font-bold text-foreground">{{ season.episode_count - season.aired_episodes }}</p>
                      </div>
                    </div>
                  </div>
                  
                  <!-- Episode Lists (only show if there are episodes) -->
                  <div v-if="season.confirmed_episodes && season.confirmed_episodes.length" class="mt-3 pt-3 border-t border-border">
                    <p class="text-xs font-semibold text-emerald-600 mb-2">Confirmed Episodes</p>
                    <div class="flex flex-wrap gap-1">
                      <span 
                        v-for="episode in season.confirmed_episodes" 
                        :key="episode"
                        class="px-2 py-0.5 bg-emerald-600/10 text-emerald-600 rounded text-xs font-medium border border-emerald-600/20"
                      >
                        {{ episode }}
                      </span>
                    </div>
                  </div>
                  
                  <div v-if="season.failed_episodes && season.failed_episodes.length" class="mt-3 pt-3 border-t border-border">
                    <p class="text-xs font-semibold text-red-600 mb-2">Failed Episodes</p>
                    <div class="flex flex-wrap gap-1">
                      <span 
                        v-for="episode in season.failed_episodes" 
                        :key="episode"
                        class="px-2 py-0.5 bg-red-600/10 text-red-600 rounded text-xs font-medium border border-red-600/20"
                      >
                        {{ episode }}
                      </span>
                    </div>
                  </div>
                  
                  <div v-if="season.unprocessed_episodes && season.unprocessed_episodes.length" class="mt-3 pt-3 border-t border-border">
                    <p class="text-xs font-semibold text-amber-600 mb-2">Unprocessed Episodes</p>
                    <div class="flex flex-wrap gap-1">
                      <span 
                        v-for="episode in season.unprocessed_episodes" 
                        :key="episode"
                        class="px-2 py-0.5 bg-amber-600/10 text-amber-600 rounded text-xs font-medium border border-amber-600/20"
                      >
                        {{ episode }}
                      </span>
                    </div>
                  </div>
                  
                  <div v-if="season.episode_count > season.aired_episodes" class="mt-3 pt-3 border-t border-border">
                    <p class="text-xs font-semibold text-blue-600 mb-2">Unaired Episodes</p>
                    <div class="flex flex-wrap gap-1">
                      <span 
                        v-for="episode in getUnairedEpisodes(season)" 
                        :key="episode"
                        class="px-2 py-0.5 bg-blue-600/10 text-blue-600 rounded text-xs font-medium border border-blue-600/20"
                      >
                        {{ episode }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </Transition>
          </div>
          
          <!-- Error Details -->
          <div v-if="selectedMedia.error_message || selectedMedia.error_count > 0 || hasSeasonErrors(selectedMedia)" class="border border-red-500/20 rounded-xl bg-red-500/5">
            <button 
              @click="toggleErrorDetails"
              class="w-full p-3 flex items-center justify-between group hover:bg-red-500/10 transition-colors"
            >
              <div class="flex items-center gap-2">
                <AppIcon icon="lucide:alert-triangle" size="16" class="text-red-500" />
                <div class="flex-1 text-left">
                  <p class="text-sm font-medium text-red-600">Error Details</p>
                  <p class="text-xs text-red-500">
                    {{ getTotalErrorCount(selectedMedia) }} error(s) found
                  </p>
                </div>
              </div>
              <AppIcon 
                icon="lucide:chevron-down" 
                size="14" 
                class="text-red-500 transition-transform duration-200"
                :class="{ 'rotate-180': expandedErrorDetails }"
              />
            </button>
            
            <Transition
              enter-active-class="transition-all duration-300"
              enter-from-class="opacity-0 -translate-y-2"
              enter-to-class="opacity-100 translate-y-0"
              leave-active-class="transition-all duration-200"
              leave-from-class="opacity-100 translate-y-0"
              leave-to-class="opacity-0 -translate-y-2"
            >
              <div v-if="expandedErrorDetails" class="px-3 pb-3 space-y-3">
                <!-- Main Error Message -->
                <div v-if="selectedMedia.error_message" class="p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                  <div class="flex items-center gap-2 mb-2">
                    <AppIcon icon="lucide:alert-circle" size="14" class="text-red-500" />
                    <span class="text-xs font-semibold text-red-600">Latest Error</span>
                    <span v-if="selectedMedia.last_error_at" class="text-xs text-red-500">
                      ({{ formatDate(selectedMedia.last_error_at) }})
                    </span>
                  </div>
                  <p class="text-xs text-red-500 font-medium">{{ selectedMedia.error_message }}</p>
                </div>
                
                <!-- Error Statistics -->
                <div v-if="selectedMedia.error_count > 0" class="p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                  <div class="flex items-center gap-2 mb-2">
                    <AppIcon icon="lucide:bar-chart-3" size="14" class="text-red-500" />
                    <span class="text-xs font-semibold text-red-600">Error Statistics</span>
                  </div>
                  <div class="grid grid-cols-2 gap-3">
                    <div>
                      <p class="text-xs text-red-500 mb-1">Total Errors</p>
                      <p class="text-sm font-bold text-red-600">{{ selectedMedia.error_count }}</p>
                    </div>
                    <div v-if="selectedMedia.last_error_at">
                      <p class="text-xs text-red-500 mb-1">Last Error</p>
                      <p class="text-sm font-bold text-red-600">{{ formatDate(selectedMedia.last_error_at) }}</p>
                    </div>
                  </div>
                </div>
                
                <!-- Season Errors -->
                <div v-if="hasSeasonErrors(selectedMedia)" class="space-y-2">
                  <div class="flex items-center gap-2">
                    <AppIcon icon="lucide:tv" size="14" class="text-red-500" />
                    <span class="text-xs font-semibold text-red-600">Season Errors</span>
                  </div>
                  <div v-for="season in selectedMedia.seasons" :key="season.season_number">
                    <div v-if="season.failed_episodes && season.failed_episodes.length > 0" class="p-2 bg-red-500/5 border border-red-500/10 rounded-lg">
                      <div class="flex items-center justify-between mb-1">
                        <span class="text-xs font-medium text-red-600">Season {{ season.season_number }}</span>
                        <span class="text-xs text-red-500">{{ season.failed_episodes.length }} failed</span>
                      </div>
                      <div class="flex flex-wrap gap-1">
                        <span 
                          v-for="episode in season.failed_episodes" 
                          :key="episode"
                          class="px-2 py-0.5 bg-red-500/10 text-red-600 rounded text-xs font-medium border border-red-500/20"
                        >
                          {{ episode }}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </Transition>
          </div>
          
          <!-- Technical Details -->
          <div class="border-t border-border pt-6">
            <h4 class="text-sm font-semibold text-foreground mb-4">Technical Details</h4>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div v-if="selectedMedia.tmdb_id">
                <p class="text-xs text-muted-foreground mb-1">TMDB ID</p>
                <p class="text-sm font-mono text-foreground">{{ selectedMedia.tmdb_id }}</p>
                <!-- Overseerr Link -->
                <div v-if="getOverseerrUrl(selectedMedia)" class="mt-2">
                  <a 
                    :href="getOverseerrUrl(selectedMedia)" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    class="inline-flex items-center gap-1 text-xs text-primary hover:text-primary/80 transition-colors"
                  >
                    <AppIcon icon="lucide:external-link" size="12" />
                    View in Overseerr
                  </a>
                </div>
              </div>
              <div v-if="selectedMedia.imdb_id">
                <p class="text-xs text-muted-foreground mb-1">IMDB ID</p>
                <p class="text-sm font-mono text-foreground">{{ selectedMedia.imdb_id }}</p>
                <!-- Debrid Media Manager Link -->
                <div class="mt-2">
                  <a 
                    :href="getDebridMediaManagerUrl(selectedMedia)" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    class="inline-flex items-center gap-1 text-xs text-primary hover:text-primary/80 transition-colors"
                  >
                    <AppIcon icon="lucide:external-link" size="12" />
                    View in Debrid Media Manager
                  </a>
                </div>
              </div>
              <div v-if="selectedMedia.trakt_id">
                <p class="text-xs text-muted-foreground mb-1">Trakt ID</p>
                <p class="text-sm font-mono text-foreground">{{ selectedMedia.trakt_id }}</p>
              </div>
              <div v-if="selectedMedia.overseerr_request_id">
                <p class="text-xs text-muted-foreground mb-1">Request ID</p>
                <p class="text-sm font-mono text-foreground">{{ selectedMedia.overseerr_request_id }}</p>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Footer -->
        <div class="bg-muted px-8 py-6 border-t border-border flex justify-end">
          <Button 
            @click="closeModal"
          >
            Close
          </Button>
        </div>
      </div>
    </div>
  </Transition>
  
  <!-- Delete Confirmation Modal -->
  <Transition
    enter-active-class="transition-all duration-300"
    enter-from-class="opacity-0"
    enter-to-class="opacity-100"
    leave-active-class="transition-all duration-200"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <div v-if="showDeleteConfirmation" class="fixed inset-0 z-[100] overflow-y-auto p-4">
      <!-- Overlay -->
      <div 
        class="fixed inset-0 bg-black/80 backdrop-blur-sm" 
        @click="showDeleteConfirmation = false"
      ></div>
      
      <!-- Confirmation Modal -->
      <div class="relative mx-auto max-w-md my-8 bg-card rounded-3xl shadow-2xl overflow-hidden">
        <!-- Header -->
        <div class="bg-red-500/10 border-b border-red-500/20 px-6 py-4">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-red-500/20 rounded-xl flex items-center justify-center">
              <AppIcon icon="lucide:trash-2" size="20" class="text-red-500" />
            </div>
            <div>
              <h3 class="text-lg font-bold text-foreground">Delete Media Item</h3>
              <p class="text-sm text-muted-foreground">This action cannot be undone</p>
            </div>
          </div>
        </div>
        
        <!-- Body -->
        <div class="px-6 py-6">
          <div class="space-y-4">
            <p class="text-sm text-muted-foreground">
              Are you sure you want to permanently delete this media item from the database?
            </p>
            
            <div v-if="selectedMedia.overseerr_request_id" class="bg-blue-500/10 border border-blue-500/20 rounded-xl p-3">
              <div class="flex items-start gap-2">
                <AppIcon icon="lucide:info" size="16" class="text-blue-500 mt-0.5 flex-shrink-0" />
                <div class="text-xs text-blue-500">
                  <p class="font-semibold mb-1">Overseerr Integration:</p>
                  <p>This will also delete the associated request (ID: {{ selectedMedia.overseerr_request_id }}) from Overseerr.</p>
                </div>
              </div>
            </div>
            
            <div v-if="selectedMedia" class="bg-muted rounded-xl p-4 border border-border">
              <div class="flex items-center gap-3">
                <div class="w-12 h-16 bg-muted rounded-lg overflow-hidden flex-shrink-0">
                  <img
                    v-if="getBestImageUrl(selectedMedia)"
                    :src="getBestImageUrl(selectedMedia)"
                    :alt="selectedMedia.title"
                    class="w-full h-full object-cover"
                  />
                  <div
                    v-else
                    class="w-full h-full flex items-center justify-center"
                  >
                    <AppIcon 
                      :icon="selectedMedia.media_type === 'movie' ? 'lucide:film' : 'lucide:tv'" 
                      size="20" 
                      class="text-muted-foreground"
                    />
                  </div>
                </div>
                <div class="flex-1 min-w-0">
                  <h4 class="text-sm font-bold text-foreground truncate">{{ selectedMedia.title }}</h4>
                  <p class="text-xs text-muted-foreground">{{ selectedMedia.year || 'N/A' }}</p>
                  <div class="flex items-center gap-2 mt-1">
                    <span 
                      :class="selectedMedia.media_type === 'movie' ? 'bg-blue-600' : 'bg-emerald-600'"
                      class="px-2 py-0.5 text-xs font-semibold text-white rounded-full"
                    >
                      {{ selectedMedia.media_type.toUpperCase() }}
                    </span>
                    <span :class="getStatusBadgeClass(selectedMedia)" class="px-2 py-0.5 text-xs font-semibold rounded-full">
                      {{ getDisplayStatus(selectedMedia) }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
            
            <div class="bg-red-500/10 border border-red-500/20 rounded-xl p-3">
              <div class="flex items-start gap-2">
                <AppIcon icon="lucide:alert-triangle" size="16" class="text-red-500 mt-0.5 flex-shrink-0" />
                <div class="text-xs text-red-500">
                  <p class="font-semibold mb-1">Warning:</p>
                  <ul class="space-y-1 text-xs">
                    <li>• This will permanently remove the item from the database</li>
                    <li>• All associated data (seasons, episodes, processing history) will be lost</li>
                    <li v-if="selectedMedia.overseerr_request_id">• The associated Overseerr request will also be deleted</li>
                    <li>• This action cannot be undone</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Footer -->
        <div class="bg-muted px-6 py-4 border-t border-border flex justify-end gap-3">
          <Button 
            @click="showDeleteConfirmation = false"
            variant="outline"
            :disabled="deleting"
          >
            Cancel
          </Button>
          <Button 
            @click="deleteMedia"
            :disabled="deleting"
            class="bg-red-600 hover:bg-red-700 text-white border-red-600 hover:border-red-700"
          >
            <AppIcon 
              v-if="deleting" 
              icon="lucide:loader-2" 
              size="16" 
              class="animate-spin mr-2"
            />
            <AppIcon 
              v-else 
              icon="lucide:trash-2" 
              size="16" 
              class="mr-2"
            />
            {{ deleting ? 'Deleting...' : 'Delete Permanently' }}
          </Button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import Button from '~/components/ui/Button.vue'
import { useDebounceFn } from '@vueuse/core'
import { useConfig } from '~/composables/useConfig'

interface Season {
  season_number: number
  episode_count: number
  aired_episodes: number
  confirmed_episodes: string[]
  failed_episodes: string[]
  unprocessed_episodes: string[]
  unaired_episodes?: string[]
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
  seasons?: Season[]
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
  movies_completed: number
  movies_processing: number
  movies_failed: number
  tv_completed: number
  tv_processing: number
  tv_failed: number
}

useHead({
  title: 'Processed Media - SeerrBridge'
})

useSeoMeta({
  title: 'Processed Media - SeerrBridge',
  description: 'Track all processed movies and TV shows in SeerrBridge'
})

const loading = ref(false)
const loadingMore = ref(false)
const mediaItems = ref<ProcessedMedia[]>([])
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
  subscribed_count: 0,
  movies_completed: 0,
  movies_processing: 0,
  movies_failed: 0,
  tv_completed: 0,
  tv_processing: 0,
  tv_failed: 0
})

const currentPage = ref(1)
const hasMore = ref(true)
const totalItems = ref(0)

const showFilters = ref(false)
const searchQuery = ref('')
const filters = ref({
  status: '',
  mediaType: '',
  sortBy: 'updated_at',
  sortOrder: 'DESC'
})

const showDetailsModal = ref(false)
const selectedMedia = ref<ProcessedMedia | null>(null)
const expandedSeasons = ref<Set<number>>(new Set([0])) // Default open for all seasons
const expandedErrorDetails = ref(false)
const showDeleteConfirmation = ref(false)
const deleting = ref(false)
const showActionMenu = ref(false)

// Configuration composable
const { overseerrBaseUrl, hasOverseerrConfig, fetchConfig } = useConfig()

const statusOptions = [
  { label: 'All Statuses', value: '' },
  { label: 'Pending', value: 'pending' },
  { label: 'Processing', value: 'processing' },
  { label: 'Completed', value: 'completed' },
  { label: 'Failed', value: 'failed' },
  { label: 'Skipped', value: 'skipped' },
  { label: 'Cancelled', value: 'cancelled' },
  { label: 'Ignored', value: 'ignored' }
]

const mediaTypeOptions = [
  { label: 'All Types', value: '' },
  { label: 'Movies', value: 'movie' },
  { label: 'TV Shows', value: 'tv' }
]

const activeFiltersCount = computed(() => {
  let count = 0
  if (filters.value.status) count++
  if (filters.value.mediaType) count++
  if (searchQuery.value) count++
  return count
})

const debouncedSearch = useDebounceFn(() => {
  currentPage.value = 1
  mediaItems.value = []
  hasMore.value = true
  loadMedia()
}, 500)

const formatNumber = (num: number) => {
  return new Intl.NumberFormat().format(num)
}

const getStatusBadgeClass = (media: ProcessedMedia) => {
  const status = media.display_status || media.status
  
  if (typeof status === 'string' && status.includes('/')) {
    return 'bg-amber-600 text-white'
  }
  
  switch (status) {
    case 'completed': return 'bg-emerald-600 text-white'
    case 'processing': return 'bg-amber-600 text-white'
    case 'failed': return 'bg-red-600 text-white'
    case 'pending': return 'bg-yellow-600 text-white'
    case 'skipped': return 'bg-gray-600 text-white'
    case 'cancelled': return 'bg-orange-600 text-white'
    case 'ignored': return 'bg-slate-600 text-white'
    default: return 'bg-gray-600 text-white'
  }
}

const getDisplayStatus = (media: ProcessedMedia) => {
  return media.display_status || media.status
}

const getStatusIcon = (media: ProcessedMedia) => {
  // Use the same sailboat icon for all statuses, differentiate with color
  return 'lucide:sailboat'
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

const getUnairedEpisodes = (season: Season) => {
  if (season.episode_count <= season.aired_episodes) {
    return []
  }
  
  const unairedEpisodes = []
  for (let i = season.aired_episodes + 1; i <= season.episode_count; i++) {
    unairedEpisodes.push(`E${i.toString().padStart(2, '0')}`)
  }
  return unairedEpisodes
}

const getTotalErrorCount = (media: ProcessedMedia) => {
  let totalErrors = media.error_count || 0
  
  // Add failed episodes from seasons
  if (media.seasons && Array.isArray(media.seasons)) {
    media.seasons.forEach(season => {
      if (season.failed_episodes && Array.isArray(season.failed_episodes)) {
        totalErrors += season.failed_episodes.length
      }
    })
  }
  
  return totalErrors
}

const hasSeasonErrors = (media: ProcessedMedia) => {
  if (!media.seasons || !Array.isArray(media.seasons)) return false
  
  return media.seasons.some(season => 
    season.failed_episodes && 
    Array.isArray(season.failed_episodes) && 
    season.failed_episodes.length > 0
  )
}

const getSeasonStatusText = (season: Season) => {
  if (season.status === 'completed') {
    return 'Completed'
  } else if (season.status === 'processing') {
    return 'Processing'
  } else if (season.status === 'failed') {
    return 'Failed'
  } else if (season.status === 'not_aired') {
    return 'Not Aired'
  } else if (season.status === 'pending') {
    return 'Pending'
  } else {
    return 'Unknown'
  }
}

const getSeasonStatusIcon = (season: Season) => {
  switch (season.status) {
    case 'completed': return 'lucide:check-circle'
    case 'processing': return 'lucide:loader-2'
    case 'failed': return 'lucide:x-circle'
    case 'not_aired': return 'lucide:calendar'
    case 'pending': return 'lucide:clock'
    default: return 'lucide:help-circle'
  }
}

const getSeasonStatusBadgeClass = (season: Season) => {
  switch (season.status) {
    case 'completed': return 'bg-emerald-500/20 text-emerald-600 dark:bg-emerald-900/20 dark:text-emerald-400'
    case 'processing': return 'bg-amber-500/20 text-amber-600 dark:bg-amber-900/20 dark:text-amber-400'
    case 'failed': return 'bg-red-500/20 text-red-600 dark:bg-red-900/20 dark:text-red-400'
    case 'not_aired': return 'bg-blue-500/20 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400'
    case 'pending': return 'bg-yellow-500/20 text-yellow-600 dark:bg-yellow-900/20 dark:text-yellow-400'
    default: return 'bg-gray-500/20 text-gray-600 dark:bg-gray-900/20 dark:text-gray-400'
  }
}

const getCompletedSeasonsCount = (media: ProcessedMedia) => {
  if (!media.seasons) return 0
  return media.seasons.filter(season => season.status === 'completed').length
}

const getProcessingSeasonsCount = (media: ProcessedMedia) => {
  if (!media.seasons) return 0
  return media.seasons.filter(season => season.status === 'processing' || season.status === 'pending').length
}

const getFailedSeasonsCount = (media: ProcessedMedia) => {
  if (!media.seasons) return 0
  return media.seasons.filter(season => season.status === 'failed').length
}

const getNotAiredSeasonsCount = (media: ProcessedMedia) => {
  if (!media.seasons) return 0
  return media.seasons.filter(season => season.status === 'not_aired').length
}

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

const loadMedia = async (page = 1, append = false) => {
  if (page === 1) {
    loading.value = true
  } else {
    loadingMore.value = true
  }
  
  try {
    const params = new URLSearchParams({
      page: page.toString(),
      limit: '20',
      sortBy: filters.value.sortBy,
      sortOrder: filters.value.sortOrder
    })
    
    if (filters.value.status) params.append('status', filters.value.status)
    if (filters.value.mediaType) params.append('mediaType', filters.value.mediaType)
    if (searchQuery.value) params.append('search', searchQuery.value)
    
    const response = await $fetch(`/api/unified-media?${params.toString()}`)
    
    if (response.success) {
      const newItems = response.data.media || []
      
      if (append) {
        mediaItems.value = [...mediaItems.value, ...newItems]
      } else {
        mediaItems.value = newItems
        stats.value = response.data.stats || stats.value
        totalItems.value = response.data.pagination?.total || 0
      }
      
      hasMore.value = response.data.pagination?.has_next || false
    }
  } catch (error) {
    // Error loading media - could add toast notification here
    console.error('Error loading media:', error)
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

const loadMore = () => {
  if (!hasMore.value || loadingMore.value) return
  currentPage.value++
  loadMedia(currentPage.value, true)
}

const refreshData = () => {
  currentPage.value = 1
  mediaItems.value = []
  hasMore.value = true
  loadMedia()
}

const applyFilters = () => {
  currentPage.value = 1
  mediaItems.value = []
  hasMore.value = true
  loadMedia()
  showFilters.value = false
}

const clearFilters = () => {
  filters.value = {
    status: '',
    mediaType: '',
    sortBy: 'updated_at',
    sortOrder: 'DESC'
  }
  searchQuery.value = ''
  currentPage.value = 1
  mediaItems.value = []
  hasMore.value = true
  loadMedia()
  showFilters.value = false
}

const applyStatFilter = (status: string, mediaType: string) => {
  // If clicking "Total Media" (both empty), clear all filters
  if (status === '' && mediaType === '') {
    clearFilters()
    return
  }
  
  // If clicking a status filter
  if (status !== '') {
    // Toggle if already applied - clear just the status, keep mediaType
    if (filters.value.status === status) {
      filters.value.status = ''
    } else {
      filters.value.status = status
    }
  }
  
  // If clicking a media type filter
  if (mediaType !== '') {
    // Toggle if already applied - clear just the mediaType, keep status
    if (filters.value.mediaType === mediaType) {
      filters.value.mediaType = ''
    } else {
      filters.value.mediaType = mediaType
    }
  }
  
  // If both filters are now empty and we toggled something, we effectively cleared
  if (filters.value.status === '' && filters.value.mediaType === '') {
    filters.value.sortBy = 'updated_at'
    filters.value.sortOrder = 'DESC'
    searchQuery.value = ''
  }
  
  currentPage.value = 1
  mediaItems.value = []
  hasMore.value = true
  loadMedia()
  showFilters.value = false
}

const closeModal = () => {
  showDetailsModal.value = false
  
  // Remove mediaId from URL
  const route = useRoute()
  const router = useRouter()
  const query = { ...route.query }
  delete query.mediaId
  router.replace({
    path: route.path,
    query
  })
}

const viewDetails = (media: ProcessedMedia) => {
  selectedMedia.value = media
  showDetailsModal.value = true
  expandedSeasons.value.clear()
  expandedSeasons.value.add(0) // Default open for all seasons
  expandedErrorDetails.value = false // Default collapsed for error details
  showActionMenu.value = false // Reset action menu state
  
  // Update URL to include mediaId parameter
  const route = useRoute()
  const router = useRouter()
  router.replace({
    path: route.path,
    query: { ...route.query, mediaId: media.id.toString() }
  })
}

const toggleSeason = (seasonNumber: number) => {
  if (expandedSeasons.value.has(seasonNumber)) {
    expandedSeasons.value.delete(seasonNumber)
  } else {
    expandedSeasons.value.add(seasonNumber)
  }
}

const toggleErrorDetails = () => {
  expandedErrorDetails.value = !expandedErrorDetails.value
}

const toggleSubscription = async () => {
  if (!selectedMedia.value) return
  
  const isSubscribed = selectedMedia.value.is_subscribed
  const newStatus = !isSubscribed
  
  try {
    const response = await $fetch(`/api/tv-subscriptions/${selectedMedia.value.id}`, {
      method: 'PUT',
      body: {
        is_subscribed: newStatus,
        subscription_active: newStatus
      }
    })
    
    if (response) {
      selectedMedia.value.is_subscribed = newStatus
      selectedMedia.value.subscription_active = newStatus
      
      // Refresh the media items to update stats
      await refreshData()
    }
  } catch (error) {
    // Error toggling subscription - could add toast notification here
    console.error('Error toggling subscription:', error)
  }
}

const toggleIgnoreStatus = async () => {
  if (!selectedMedia.value) return
  
  const currentStatus = selectedMedia.value.status
  const newStatus = currentStatus === 'ignored' ? 'pending' : 'ignored'
  
  try {
    const response = await $fetch(`/api/unified-media/${selectedMedia.value.id}`, {
      method: 'PUT',
      body: {
        status: newStatus
      }
    })
    
    if (response && response.success) {
      selectedMedia.value.status = newStatus
      selectedMedia.value.display_status = newStatus
      
      // Refresh the media items to update list
      await refreshData()
    }
  } catch (error) {
    // Error toggling ignore status - could add toast notification here
    console.error('Error toggling ignore status:', error)
  }
}

const retriggerMedia = async () => {
  if (!selectedMedia.value) return
  
  // Show confirmation dialog
  const confirmed = confirm(
    `Are you sure you want to re-trigger processing for "${selectedMedia.value.title}"?\n\n` +
    `This will:\n` +
    `• Remove it from completed status\n` +
    `• Set it to unprocessed (pending)\n` +
    `• Queue it for processing by SeerrBridge again\n\n` +
    `Click OK to confirm or Cancel to abort.`
  )
  
  if (!confirmed) return
  
  try {
    const response = await $fetch(`/api/retrigger-media/${selectedMedia.value.id}`, {
      method: 'POST'
    })
    
    if (response && response.status === 'success') {
      // Update the media status to pending
      selectedMedia.value.status = 'pending'
      selectedMedia.value.display_status = 'pending'
      selectedMedia.value.processing_stage = 'retriggered'
      
      // Refresh the media list to update the UI
      await refreshData()
      
      // Success - could add toast notification here
    }
  } catch (error) {
    // Error retriggering media - could add toast notification here
    console.error('Error retriggering media:', error)
  }
}

const confirmDeleteMedia = () => {
  if (!selectedMedia.value) return
  showDeleteConfirmation.value = true
}

const deleteMedia = async () => {
  if (!selectedMedia.value) return
  
  deleting.value = true
  
  try {
    // First, try to delete the request from Overseerr if we have a request ID
    let overseerrDeleteSuccess = true
    let overseerrDeleteMessage = ''
    
    if (selectedMedia.value.overseerr_request_id) {
      try {
        const overseerrResponse = await $fetch('/api/overseerr-request-delete', {
          method: 'DELETE',
          query: {
            requestId: selectedMedia.value.overseerr_request_id.toString()
          }
        })
        
        if (overseerrResponse.success) {
          overseerrDeleteMessage = 'Request deleted from Overseerr successfully.'
        } else {
          overseerrDeleteSuccess = false
          overseerrDeleteMessage = `Failed to delete from Overseerr: ${overseerrResponse.error}`
        }
      } catch (error) {
        overseerrDeleteSuccess = false
        overseerrDeleteMessage = `Error deleting from Overseerr: ${error instanceof Error ? error.message : 'Unknown error'}`
      }
    }
    
    // Delete from SeerrBridge database
    const response = await $fetch(`/api/unified-media/${selectedMedia.value.id}`, {
      method: 'DELETE'
    })
    
    if (response && response.success) {
      // Close both modals
      showDeleteConfirmation.value = false
      showDetailsModal.value = false
      
      // Remove the deleted item from the current list
      const index = mediaItems.value.findIndex(item => item.id === selectedMedia.value!.id)
      if (index !== -1) {
        mediaItems.value.splice(index, 1)
      }
      
      // Refresh the data to update stats
      await refreshData()
      
      // Reset selected media
      selectedMedia.value = null
      
      // Show success message with Overseerr status
      const successMessage = overseerrDeleteSuccess 
        ? `Media item deleted successfully. ${overseerrDeleteMessage}`
        : `Media item deleted from database. ${overseerrDeleteMessage}`
      
      // Success - could add toast notification here
    } else {
      // Error deleting media item from database - could add toast notification here
      console.error('Error deleting media item from database:', response?.error)
    }
  } catch (error) {
    // Error deleting media item - could add toast notification here
    console.error('Error deleting media item:', error)
  } finally {
    deleting.value = false
  }
}

const formatDate = (dateString: string) => {
  if (!dateString) return 'Never'
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', { 
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const getOverseerrUrl = (media: ProcessedMedia) => {
  if (!overseerrBaseUrl.value || !media.tmdb_id) return null
  
  const mediaType = media.media_type === 'movie' ? 'movie' : 'tv'
  return `${overseerrBaseUrl.value}/${mediaType}/${media.tmdb_id}`
}

const getDebridMediaManagerUrl = (media: ProcessedMedia) => {
  if (!media.imdb_id) return '#'
  
  const baseUrl = 'https://debridmediamanager.com'
  const mediaType = media.media_type === 'movie' ? 'movie' : 'show'
  
  return `${baseUrl}/${mediaType}/${media.imdb_id}`
}

const handleScroll = () => {
  if (loadingMore.value || !hasMore.value) return
  
  const scrollTop = window.pageYOffset || document.documentElement.scrollTop
  const windowHeight = window.innerHeight
  const documentHeight = document.documentElement.scrollHeight
  
  if (scrollTop + windowHeight >= documentHeight - 1000) {
    loadMore()
  }
}

const openModalForMediaId = async (mediaId: number) => {
  // Wait for media to load first
  await nextTick()
  
  // Find the media item with the specified ID
  const media = mediaItems.value.find(item => item.id === mediaId)
  
  if (media) {
    // Open the modal for this specific media item
    viewDetails(media)
  } else {
    // If not found in current page, try to load it directly
    try {
      const response = await $fetch(`/api/unified-media/${mediaId}`)
      if (response && response.success && response.data) {
        viewDetails(response.data)
      }
    } catch (error) {
      // Error loading specific media item - could add toast notification here
      console.error('Error loading specific media item:', error)
    }
  }
}

// Watch for route changes to handle dynamic navigation
watch(() => useRoute().query.mediaId, async (newMediaId) => {
  if (newMediaId && typeof newMediaId === 'string') {
    const id = parseInt(newMediaId)
    if (!isNaN(id)) {
      // Small delay to ensure the page is fully rendered
      setTimeout(() => {
        openModalForMediaId(id)
      }, 100)
    }
  } else if (!newMediaId && showDetailsModal.value) {
    // Close modal if mediaId is removed from URL
    showDetailsModal.value = false
  }
})

onMounted(async () => {
  // Load configuration first
  await fetchConfig()
  
  await loadMedia()
  
  // Check for mediaId query parameter to auto-open modal
  const route = useRoute()
  const mediaId = route.query.mediaId
  
  if (mediaId && typeof mediaId === 'string') {
    const id = parseInt(mediaId)
    if (!isNaN(id)) {
      // Small delay to ensure the page is fully rendered
      setTimeout(() => {
        openModalForMediaId(id)
      }, 100)
    }
  }
  
  window.addEventListener('scroll', handleScroll)
  
  // Close action menu when clicking outside
  document.addEventListener('click', (event) => {
    if (showActionMenu.value) {
      const target = event.target as HTMLElement
      if (!target.closest('.action-menu-container')) {
        showActionMenu.value = false
      }
    }
  })
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
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
