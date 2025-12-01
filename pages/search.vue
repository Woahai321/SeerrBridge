<template>
  <div class="space-y-4 sm:space-y-6 lg:space-y-8">
      <!-- Search Header -->
      <div class="mb-4 sm:mb-6 lg:mb-8">
        <h1 class="text-2xl sm:text-3xl font-bold text-foreground mb-1 sm:mb-2">Search Media</h1>
        <p class="text-sm sm:text-base text-muted-foreground">Search for movies, TV shows, and more from Overseerr</p>
      </div>

      <!-- Search Input -->
      <div class="max-w-3xl mb-4 sm:mb-6 lg:mb-8">
        <div class="flex items-center gap-3 sm:gap-4 mb-3 sm:mb-4">
          <div class="relative flex-1">
            <input
              v-model="searchQuery"
              @keyup.enter="handleSearch"
              @input="handleInput"
              type="text"
              placeholder="Search for movies, TV shows..."
              class="w-full px-4 sm:px-6 py-3 sm:py-4 pr-12 sm:pr-16 text-base sm:text-lg bg-card border-2 border-border rounded-lg sm:rounded-xl focus:outline-none focus:border-primary transition-colors text-foreground placeholder:text-muted-foreground"
            />
            <button
              @click="handleSearch"
              :disabled="isSearching || !hasQuery"
              class="absolute right-1.5 sm:right-2 top-1/2 -translate-y-1/2 px-3 sm:px-4 py-1.5 sm:py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium text-sm sm:text-base"
            >
              <Icon v-if="!isSearching" name="mdi:magnify" class="w-4 h-4 sm:w-5 sm:h-5" />
              <Icon v-else name="mdi:loading" class="w-4 h-4 sm:w-5 sm:h-5 animate-spin" />
            </button>
          </div>
          <!-- View Toggle -->
          <div class="flex items-center gap-1 p-1 bg-muted rounded-lg flex-shrink-0">
            <button
              @click="viewMode = 'grid'"
              :class="[
                'p-1.5 rounded transition-colors',
                viewMode === 'grid' 
                  ? 'bg-background text-primary shadow-sm' 
                  : 'text-muted-foreground hover:text-foreground'
              ]"
              title="Grid View"
            >
              <Icon name="mdi:view-grid" class="w-4 h-4 sm:w-4.5 sm:h-4.5" />
            </button>
            <button
              @click="viewMode = 'list'"
              :class="[
                'p-1.5 rounded transition-colors',
                viewMode === 'list' 
                  ? 'bg-background text-primary shadow-sm' 
                  : 'text-muted-foreground hover:text-foreground'
              ]"
              title="List View"
            >
              <Icon name="mdi:view-list" class="w-4 h-4 sm:w-4.5 sm:h-4.5" />
            </button>
          </div>
        </div>
      </div>


      <!-- Results Count -->
      <div v-if="resultsLength > 0" class="mb-4 sm:mb-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-4">
        <p class="text-sm sm:text-base text-muted-foreground">
          Found <span class="font-semibold text-foreground">{{ searchState.totalResults }}</span> results
        </p>
        <div class="flex items-center gap-1.5 sm:gap-2">
          <button
            @click="searchState.previousPage"
            :disabled="searchState.page === 1 || isSearching"
            class="p-1.5 sm:px-3 sm:py-2 bg-card border border-border rounded-lg hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Icon name="mdi:chevron-left" class="w-4 h-4 sm:w-5 sm:h-5" />
          </button>
          <span class="text-xs sm:text-sm text-muted-foreground px-1 sm:px-2">
            Page {{ searchState.page }} of {{ searchState.totalPages }}
          </span>
          <button
            @click="searchState.nextPage"
            :disabled="searchState.page === searchState.totalPages || isSearching"
            class="p-1.5 sm:px-3 sm:py-2 bg-card border border-border rounded-lg hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Icon name="mdi:chevron-right" class="w-4 h-4 sm:w-5 sm:h-5" />
          </button>
        </div>
      </div>

      <!-- Results Grid View -->
      <div v-if="resultsLength > 0 && viewMode === 'grid'" class="grid grid-cols-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-2 sm:gap-3">
        <div
          v-for="(media, index) in results"
          :key="media.id"
          :style="{ animationDelay: `${index * 50}ms` }"
          class="group relative glass-card-enhanced rounded-2xl overflow-hidden cursor-pointer transition-all duration-500 animate-fade-in-up will-change-transform h-full flex flex-col"
          @click="openModal(media)"
        >
          <!-- Glow Effect on Hover -->
          <div class="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none z-0">
            <div class="absolute inset-0 bg-gradient-to-br from-primary/20 via-primary/10 to-transparent blur-2xl rounded-3xl"></div>
          </div>
          
          <!-- Poster Container -->
          <div class="relative flex-1 bg-gradient-to-br from-muted via-muted/80 to-muted/60 overflow-hidden rounded-t-2xl">
            <img
              v-if="getPosterUrl(media.posterPath)"
              :src="getPosterUrl(media.posterPath)"
              :alt="getMediaTitle(media)"
              class="w-full h-full object-cover transition-all duration-700 group-hover:scale-110 group-hover:brightness-110"
              @error="handleImageError"
              loading="lazy"
            />
            <div v-else class="w-full h-full flex items-center justify-center p-6 bg-gradient-to-br from-primary/10 via-primary/5 to-muted/50">
              <div class="text-center transform group-hover:scale-110 transition-transform duration-300">
                <div class="w-16 h-16 mx-auto mb-3 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/10 backdrop-blur-sm flex items-center justify-center border border-primary/20 shadow-lg">
                  <Icon :name="media.mediaType === 'movie' ? 'mdi:film' : 'mdi:television'" size="32" class="text-primary" />
                </div>
                <p class="text-xs text-foreground font-semibold line-clamp-2 drop-shadow-sm">{{ getMediaTitle(media) }}</p>
              </div>
            </div>

            <!-- Media Type Badge -->
            <div class="absolute top-3 left-3 z-20">
              <span 
                class="media-type-badge px-3 py-1.5 text-[10px] sm:text-xs font-bold text-foreground rounded-full backdrop-blur-xl shadow-xl border-2 transition-all duration-300 group-hover:scale-105 group-hover:border-primary/40"
                :class="media.mediaType === 'movie' ? 'bg-info/20 text-info border-info/30 dark:bg-info/15 dark:border-info/25' : 'bg-success/20 text-success border-success/30 dark:bg-success/15 dark:border-success/25'"
              >
                {{ getMediaTypeLabel(media).toUpperCase() }}
              </span>
            </div>

            <!-- In Database Checkmark -->
            <div
              v-if="isInDatabase(media)"
              class="absolute top-3 right-3 z-20"
            >
              <div class="status-badge-enhanced bg-success/30 backdrop-blur-xl shadow-2xl flex items-center justify-center w-8 h-8 sm:w-10 sm:h-10 rounded-2xl border-2 border-success/40 transition-all duration-300 group-hover:scale-110 group-hover:shadow-lg">
                <Icon name="mdi:check-circle" size="14" class="sm:w-5 sm:h-5 text-success drop-shadow-lg" />
              </div>
            </div>

            <!-- Hover Overlay with Request Button -->
            <div class="absolute inset-0 bg-gradient-to-t from-black/90 via-black/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-end z-10">
              <div class="p-2 sm:p-3 w-full">
                <button
                  v-if="canRequest(media)"
                  @click.stop="handleQuickRequestClick(media)"
                  class="w-full px-3 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium flex items-center justify-center gap-2 text-xs sm:text-sm"
                >
                  <Icon name="mdi:plus-circle" size="16" />
                  <span>Request</span>
                </button>
                <button
                  v-else-if="isInDatabase(media)"
                  @click.stop="handleViewDetails(media)"
                  class="w-full px-3 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium flex items-center justify-center gap-2 text-xs sm:text-sm"
                >
                  <Icon name="mdi:open-in-new" size="16" />
                  <span>View Details</span>
                </button>
                <div
                  v-else-if="hasBeenRequested(media)"
                  class="w-full px-3 py-2 bg-info/20 text-info rounded-lg font-medium flex items-center justify-center gap-2 text-xs sm:text-sm"
                >
                  <Icon name="mdi:clock-outline" size="16" />
                  <span>Request Submitted</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Enhanced Card Info with Glassmorphic Background -->
          <div class="relative p-3 sm:p-4 space-y-2 bg-gradient-to-b from-card/95 via-card/90 to-card backdrop-blur-sm flex-shrink-0 rounded-b-2xl">
            <!-- Title -->
            <h3 class="text-xs sm:text-sm font-bold text-foreground line-clamp-2 transition-all duration-300 group-hover:text-primary">
              {{ getMediaTitle(media) }}
            </h3>
            
            <!-- Year and Rating Row -->
            <div class="flex items-center justify-between gap-2">
              <p class="text-[10px] sm:text-xs text-muted-foreground font-medium">
                {{ getMediaYear(media) || 'N/A' }}
              </p>
              <div v-if="media.voteAverage" class="flex items-center gap-1 text-[10px] sm:text-xs bg-amber-500/20 px-2 py-0.5 rounded-full border border-amber-500/30">
                <Icon name="mdi:star" size="10" class="sm:w-3 sm:h-3 text-amber-400 fill-amber-400" />
                <span class="font-bold text-amber-400">{{ formatVoteAverage(media.voteAverage) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Results List View -->
      <div v-else-if="resultsLength > 0 && viewMode === 'list'" class="space-y-2 sm:space-y-3 lg:space-y-4">
        <div
          v-for="media in results"
          :key="media.id"
          @click="openModal(media)"
          class="group relative bg-card rounded-lg sm:rounded-xl cursor-pointer transition-all duration-300 hover:shadow-lg hover:border-primary border border-border overflow-hidden"
        >
          <div class="flex flex-row gap-2 sm:gap-3 lg:gap-4">
            <!-- Poster Thumbnail -->
            <div class="flex-shrink-0 w-16 sm:w-20 md:w-24 bg-muted rounded-l-lg sm:rounded-l-xl overflow-hidden relative" style="aspect-ratio: 2/3;">
              <img
                v-if="getPosterUrl(media.posterPath)"
                :src="getPosterUrl(media.posterPath)"
                :alt="getMediaTitle(media)"
                class="absolute inset-0 w-full h-full object-cover"
              />
              <div v-else class="absolute inset-0 w-full h-full flex items-center justify-center">
                <Icon name="mdi:image-off" class="w-8 h-8 sm:w-10 sm:h-10 text-muted-foreground" />
              </div>
              
              <!-- Media Type Badge -->
              <div class="absolute top-1 left-1 sm:top-1.5 sm:left-1.5 z-20">
                <div class="bg-primary/90 backdrop-blur-sm text-primary-foreground px-1.5 sm:px-2 py-0.5 rounded text-[9px] sm:text-[10px] font-semibold">
                  {{ getMediaTypeLabel(media) }}
                </div>
              </div>
              
              <!-- In Database Checkmark -->
              <div
                v-if="isInDatabase(media)"
                class="absolute top-1 right-1 sm:top-1.5 sm:right-1.5 z-20 w-5 h-5 sm:w-6 sm:h-6 flex items-center justify-center bg-success/90 backdrop-blur-sm rounded-full shadow-lg"
              >
                <Icon name="mdi:check-circle" class="w-3 h-3 sm:w-4 sm:h-4 text-white" />
              </div>
            </div>
            
            <!-- Media Info -->
            <div class="flex-1 min-w-0 flex flex-col justify-between py-2 sm:py-3 pr-2 sm:pr-3 lg:pr-4 lg:py-4">
              <div class="min-w-0">
                <div class="flex items-start justify-between gap-2 mb-1 sm:mb-2">
                  <h3 class="text-sm sm:text-base lg:text-lg font-semibold text-foreground line-clamp-1 group-hover:text-primary transition-colors flex-1 min-w-0">
                    {{ getMediaTitle(media) }}
                  </h3>
                  <div v-if="media.voteAverage" class="flex items-center gap-0.5 sm:gap-1 flex-shrink-0">
                    <Icon name="mdi:star" class="w-3 h-3 sm:w-4 sm:h-4 text-yellow-400" />
                    <span class="text-[10px] sm:text-xs font-semibold text-foreground">{{ formatVoteAverage(media.voteAverage) }}</span>
                  </div>
                </div>
                
                <div class="flex flex-wrap items-center gap-1.5 sm:gap-2 text-[10px] sm:text-xs text-muted-foreground mb-1.5 sm:mb-2">
                  <span v-if="getMediaYear(media)">{{ getMediaYear(media) }}</span>
                  <span v-if="media.mediaType !== 'person' && media.popularity" class="flex items-center gap-0.5 sm:gap-1">
                    <Icon name="mdi:trending-up" class="w-3 h-3 sm:w-4 sm:h-4" />
                    {{ Math.round(media.popularity) }}
                  </span>
                </div>
                
                <p v-if="media.overview" class="text-[10px] sm:text-xs text-muted-foreground line-clamp-2 mb-1.5 sm:mb-2">
                  {{ media.overview }}
                </p>
              </div>
              
              <!-- Action Buttons -->
              <div class="flex items-center gap-1.5 sm:gap-2">
                <button
                  v-if="canRequest(media)"
                  @click.stop="handleQuickRequestClick(media)"
                  class="flex-1 sm:flex-initial px-2 sm:px-3 py-1 sm:py-1.5 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium flex items-center justify-center gap-1 sm:gap-1.5 text-[10px] sm:text-xs h-7 sm:h-8"
                >
                  <Icon name="mdi:plus-circle" class="w-3 h-3 sm:w-4 sm:h-4" />
                  <span class="truncate">Request</span>
                </button>
                <button
                  v-else-if="isInDatabase(media)"
                  @click.stop="handleViewDetails(media)"
                  class="flex-1 sm:flex-initial px-2 sm:px-3 py-1 sm:py-1.5 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium flex items-center justify-center gap-1 sm:gap-1.5 text-[10px] sm:text-xs h-7 sm:h-8"
                >
                  <Icon name="mdi:open-in-new" class="w-3 h-3 sm:w-4 sm:h-4" />
                  <span class="truncate">View</span>
                </button>
                <div
                  v-else-if="hasBeenRequested(media)"
                  class="flex-1 sm:flex-initial px-2 sm:px-3 py-1 sm:py-1.5 bg-info/20 text-info rounded-lg font-medium flex items-center justify-center gap-1 sm:gap-1.5 text-[10px] sm:text-xs h-7 sm:h-8"
                >
                  <Icon name="mdi:clock-outline" class="w-3 h-3 sm:w-4 sm:h-4" />
                  <span class="truncate">Submitted</span>
                </div>
                <button
                  @click.stop="openModal(media)"
                  class="px-2 sm:px-3 py-1 sm:py-1.5 bg-card border border-border rounded-lg hover:bg-accent transition-colors flex items-center justify-center text-[10px] sm:text-xs h-7 sm:h-8 flex-shrink-0"
                >
                  <Icon name="mdi:chevron-right" class="w-3 h-3 sm:w-4 sm:h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="isSearching" class="flex items-center justify-center py-12 sm:py-16">
        <div class="flex flex-col items-center gap-3 sm:gap-4">
          <Icon name="mdi:loading" class="w-10 h-10 sm:w-12 sm:h-12 animate-spin text-primary" />
          <p class="text-sm sm:text-base text-muted-foreground">Searching...</p>
        </div>
      </div>

      <!-- Discover Results -->
      <div v-if="!isSearching && resultsLength === 0 && !hasQuery && (discoverMovies.length > 0 || discoverTv.length > 0)" class="mb-6 sm:mb-8 space-y-8 sm:space-y-12">
        <!-- Discover Movies -->
        <div v-if="discoverMovies.length > 0">
          <div class="mb-4 sm:mb-6">
            <h3 class="text-lg sm:text-xl font-semibold text-foreground mb-1 sm:mb-2">Discover Popular Movies</h3>
            <p class="text-sm sm:text-base text-muted-foreground">Trending and popular movies you might like</p>
          </div>
          
          <!-- Discover Movies Grid View -->
          <div v-if="viewMode === 'grid'" class="grid grid-cols-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-2 sm:gap-3 mb-4 sm:mb-6">
            <div
              v-for="(media, index) in discoverMovies"
              :key="media.id"
              :style="{ animationDelay: `${index * 50}ms` }"
              class="group relative glass-card-enhanced rounded-2xl overflow-hidden cursor-pointer transition-all duration-500 animate-fade-in-up will-change-transform h-full flex flex-col"
              @click="openModal(media)"
            >
              <!-- Glow Effect on Hover -->
              <div class="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none z-0">
                <div class="absolute inset-0 bg-gradient-to-br from-primary/20 via-primary/10 to-transparent blur-2xl rounded-3xl"></div>
              </div>
              
              <!-- Poster Container -->
              <div class="relative flex-1 bg-gradient-to-br from-muted via-muted/80 to-muted/60 overflow-hidden rounded-t-2xl">
                <img
                  v-if="getPosterUrl(media.posterPath)"
                  :src="getPosterUrl(media.posterPath)"
                  :alt="getMediaTitle(media)"
                  class="w-full h-full object-cover transition-all duration-700 group-hover:scale-110 group-hover:brightness-110"
                  @error="handleImageError"
                  loading="lazy"
                />
                <div v-else class="w-full h-full flex items-center justify-center p-6 bg-gradient-to-br from-primary/10 via-primary/5 to-muted/50">
                  <div class="text-center transform group-hover:scale-110 transition-transform duration-300">
                    <div class="w-16 h-16 mx-auto mb-3 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/10 backdrop-blur-sm flex items-center justify-center border border-primary/20 shadow-lg">
                      <Icon name="mdi:film" size="32" class="text-primary" />
                    </div>
                    <p class="text-xs text-foreground font-semibold line-clamp-2 drop-shadow-sm">{{ getMediaTitle(media) }}</p>
                  </div>
                </div>

                <!-- Media Type Badge -->
                <div class="absolute top-3 left-3 z-20">
                  <span 
                    class="media-type-badge px-3 py-1.5 text-[10px] sm:text-xs font-bold text-foreground rounded-full backdrop-blur-xl shadow-xl border-2 transition-all duration-300 group-hover:scale-105 group-hover:border-primary/40 bg-info/20 text-info border-info/30 dark:bg-info/15 dark:border-info/25"
                  >
                    {{ getMediaTypeLabel(media).toUpperCase() }}
                  </span>
                </div>

                <!-- In Database Checkmark -->
                <div
                  v-if="isInDatabase(media)"
                  class="absolute top-3 right-3 z-20"
                >
                  <div class="status-badge-enhanced bg-success/30 backdrop-blur-xl shadow-2xl flex items-center justify-center w-8 h-8 sm:w-10 sm:h-10 rounded-2xl border-2 border-success/40 transition-all duration-300 group-hover:scale-110 group-hover:shadow-lg">
                    <Icon name="mdi:check-circle" size="14" class="sm:w-5 sm:h-5 text-success drop-shadow-lg" />
                  </div>
                </div>

                <!-- Hover Overlay with Request Button -->
                <div class="absolute inset-0 bg-gradient-to-t from-black/90 via-black/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-end z-10">
                  <div class="p-2 sm:p-3 w-full">
                    <button
                      v-if="canRequest(media)"
                      @click.stop="handleQuickRequestClick(media)"
                      class="w-full px-3 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium flex items-center justify-center gap-2 text-xs sm:text-sm"
                    >
                      <Icon name="mdi:plus-circle" size="16" />
                      <span>Request</span>
                    </button>
                    <button
                      v-else-if="isInDatabase(media)"
                      @click.stop="handleViewDetails(media)"
                      class="w-full px-3 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium flex items-center justify-center gap-2 text-xs sm:text-sm"
                    >
                      <Icon name="mdi:open-in-new" size="16" />
                      <span>View Details</span>
                    </button>
                    <div
                      v-else-if="hasBeenRequested(media)"
                      class="w-full px-3 py-2 bg-info/20 text-info rounded-lg font-medium flex items-center justify-center gap-2 text-xs sm:text-sm"
                    >
                      <Icon name="mdi:clock-outline" size="16" />
                      <span>Request Submitted</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Enhanced Card Info with Glassmorphic Background -->
              <div class="relative p-3 sm:p-4 space-y-2 bg-gradient-to-b from-card/95 via-card/90 to-card backdrop-blur-sm flex-shrink-0 rounded-b-2xl">
                <!-- Title -->
                <h3 class="text-xs sm:text-sm font-bold text-foreground line-clamp-2 transition-all duration-300 group-hover:text-primary">
                  {{ getMediaTitle(media) }}
                </h3>
                
                <!-- Year and Rating Row -->
                <div class="flex items-center justify-between gap-2">
                  <p class="text-[10px] sm:text-xs text-muted-foreground font-medium">
                    {{ getMediaYear(media) || 'N/A' }}
                  </p>
                  <div v-if="media.voteAverage" class="flex items-center gap-1 text-[10px] sm:text-xs bg-amber-500/20 px-2 py-0.5 rounded-full border border-amber-500/30">
                    <Icon name="mdi:star" size="10" class="sm:w-3 sm:h-3 text-amber-400 fill-amber-400" />
                    <span class="font-bold text-amber-400">{{ formatVoteAverage(media.voteAverage) }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Discover Movies List View -->
          <div v-else class="space-y-2 sm:space-y-3 lg:space-y-4 mb-4 sm:mb-6">
            <div
              v-for="media in discoverMovies"
              :key="media.id"
              @click="openModal(media)"
              class="group relative bg-card rounded-lg sm:rounded-xl cursor-pointer transition-all duration-300 hover:shadow-lg hover:border-primary border border-border overflow-hidden"
            >
              <div class="flex flex-row gap-2 sm:gap-3 lg:gap-4">
                <!-- Poster Thumbnail -->
                <div class="flex-shrink-0 w-16 sm:w-20 md:w-24 bg-muted rounded-l-lg sm:rounded-l-xl overflow-hidden relative" style="aspect-ratio: 2/3;">
                  <img
                    v-if="getPosterUrl(media.posterPath)"
                    :src="getPosterUrl(media.posterPath)"
                    :alt="getMediaTitle(media)"
                    class="absolute inset-0 w-full h-full object-cover"
                  />
                  <div v-else class="absolute inset-0 w-full h-full flex items-center justify-center">
                    <Icon name="mdi:image-off" class="w-8 h-8 sm:w-10 sm:h-10 text-muted-foreground" />
                  </div>
                  
                  <!-- Media Type Badge -->
                  <div class="absolute top-1 left-1 sm:top-1.5 sm:left-1.5 z-20">
                    <div class="bg-primary/90 backdrop-blur-sm text-primary-foreground px-1.5 sm:px-2 py-0.5 rounded text-[9px] sm:text-[10px] font-semibold">
                      {{ getMediaTypeLabel(media) }}
                    </div>
                  </div>
                  
                  <!-- In Database Checkmark -->
                  <div
                    v-if="isInDatabase(media)"
                    class="absolute top-1 right-1 sm:top-1.5 sm:right-1.5 z-20 w-5 h-5 sm:w-6 sm:h-6 flex items-center justify-center bg-success/90 backdrop-blur-sm rounded-full shadow-lg"
                  >
                    <Icon name="mdi:check-circle" class="w-3 h-3 sm:w-4 sm:h-4 text-white" />
                  </div>
                </div>
                
                <!-- Media Info -->
                <div class="flex-1 min-w-0 flex flex-col justify-between py-2 sm:py-3 pr-2 sm:pr-3 lg:pr-4 lg:py-4">
                  <div class="min-w-0">
                    <div class="flex items-start justify-between gap-2 mb-1 sm:mb-2">
                      <h3 class="text-sm sm:text-base lg:text-lg font-semibold text-foreground line-clamp-1 group-hover:text-primary transition-colors flex-1 min-w-0">
                        {{ getMediaTitle(media) }}
                      </h3>
                      <div v-if="media.voteAverage" class="flex items-center gap-0.5 sm:gap-1 flex-shrink-0">
                        <Icon name="mdi:star" class="w-3 h-3 sm:w-4 sm:h-4 text-yellow-400" />
                        <span class="text-[10px] sm:text-xs font-semibold text-foreground">{{ formatVoteAverage(media.voteAverage) }}</span>
                      </div>
                    </div>
                    
                    <div class="flex flex-wrap items-center gap-1.5 sm:gap-2 text-[10px] sm:text-xs text-muted-foreground mb-1.5 sm:mb-2">
                      <span v-if="getMediaYear(media)">{{ getMediaYear(media) }}</span>
                      <span v-if="media.mediaType !== 'person' && media.popularity" class="flex items-center gap-0.5 sm:gap-1">
                        <Icon name="mdi:trending-up" class="w-3 h-3 sm:w-4 sm:h-4" />
                        {{ Math.round(media.popularity) }}
                      </span>
                    </div>
                    
                    <p v-if="media.overview" class="text-[10px] sm:text-xs text-muted-foreground line-clamp-2 mb-1.5 sm:mb-2">
                      {{ media.overview }}
                    </p>
                  </div>
                  
                  <!-- Action Buttons -->
                  <div class="flex items-center gap-1.5 sm:gap-2">
                    <button
                      v-if="canRequest(media)"
                      @click.stop="handleQuickRequestClick(media)"
                      class="flex-1 sm:flex-initial px-2 sm:px-3 py-1 sm:py-1.5 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium flex items-center justify-center gap-1 sm:gap-1.5 text-[10px] sm:text-xs h-7 sm:h-8"
                    >
                      <Icon name="mdi:plus-circle" class="w-3 h-3 sm:w-4 sm:h-4" />
                      <span class="truncate">Request</span>
                    </button>
                    <button
                      v-else-if="isInDatabase(media)"
                      @click.stop="handleViewDetails(media)"
                      class="flex-1 sm:flex-initial px-2 sm:px-3 py-1 sm:py-1.5 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium flex items-center justify-center gap-1 sm:gap-1.5 text-[10px] sm:text-xs h-7 sm:h-8"
                    >
                      <Icon name="mdi:open-in-new" class="w-3 h-3 sm:w-4 sm:h-4" />
                      <span class="truncate">View</span>
                    </button>
                    <div
                      v-else-if="hasBeenRequested(media)"
                      class="flex-1 sm:flex-initial px-2 sm:px-3 py-1 sm:py-1.5 bg-info/20 text-info rounded-lg font-medium flex items-center justify-center gap-1 sm:gap-1.5 text-[10px] sm:text-xs h-7 sm:h-8"
                    >
                      <Icon name="mdi:clock-outline" class="w-3 h-3 sm:w-4 sm:h-4" />
                      <span class="truncate">Submitted</span>
                    </div>
                    <button
                      @click.stop="openModal(media)"
                      class="px-2 sm:px-3 py-1 sm:py-1.5 bg-card border border-border rounded-lg hover:bg-accent transition-colors flex items-center justify-center text-[10px] sm:text-xs h-7 sm:h-8 flex-shrink-0"
                    >
                      <Icon name="mdi:chevron-right" class="w-3 h-3 sm:w-4 sm:h-4" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <div v-if="moviesPage < moviesTotalPages" class="text-center">
            <button
              @click="loadMoreMovies"
              class="px-4 sm:px-6 py-2 sm:py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium flex items-center gap-2 mx-auto text-sm sm:text-base"
            >
              <Icon name="mdi:chevron-down" class="w-4 h-4 sm:w-5 sm:h-5" />
              <span class="hidden sm:inline">Load More Movies</span>
              <span class="sm:hidden">Load More</span>
            </button>
          </div>
        </div>

        <!-- Discover TV Shows -->
        <div v-if="discoverTv.length > 0">
          <div class="mb-4 sm:mb-6">
            <h3 class="text-lg sm:text-xl font-semibold text-foreground mb-1 sm:mb-2">Discover Popular TV Shows</h3>
            <p class="text-sm sm:text-base text-muted-foreground">Trending and popular TV shows you might like</p>
          </div>
          
          <!-- Discover TV Grid View -->
          <div v-if="viewMode === 'grid'" class="grid grid-cols-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-2 sm:gap-3 mb-4 sm:mb-6">
            <div
              v-for="(media, index) in discoverTv"
              :key="media.id"
              :style="{ animationDelay: `${index * 50}ms` }"
              class="group relative glass-card-enhanced rounded-2xl overflow-hidden cursor-pointer transition-all duration-500 animate-fade-in-up will-change-transform h-full flex flex-col"
              @click="openModal(media)"
            >
              <!-- Glow Effect on Hover -->
              <div class="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none z-0">
                <div class="absolute inset-0 bg-gradient-to-br from-primary/20 via-primary/10 to-transparent blur-2xl rounded-3xl"></div>
              </div>
              
              <!-- Poster Container -->
              <div class="relative flex-1 bg-gradient-to-br from-muted via-muted/80 to-muted/60 overflow-hidden rounded-t-2xl">
                <img
                  v-if="getPosterUrl(media.posterPath)"
                  :src="getPosterUrl(media.posterPath)"
                  :alt="getMediaTitle(media)"
                  class="w-full h-full object-cover transition-all duration-700 group-hover:scale-110 group-hover:brightness-110"
                  @error="handleImageError"
                  loading="lazy"
                />
                <div v-else class="w-full h-full flex items-center justify-center p-6 bg-gradient-to-br from-primary/10 via-primary/5 to-muted/50">
                  <div class="text-center transform group-hover:scale-110 transition-transform duration-300">
                    <div class="w-16 h-16 mx-auto mb-3 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/10 backdrop-blur-sm flex items-center justify-center border border-primary/20 shadow-lg">
                      <Icon name="mdi:television" size="32" class="text-primary" />
                    </div>
                    <p class="text-xs text-foreground font-semibold line-clamp-2 drop-shadow-sm">{{ getMediaTitle(media) }}</p>
                  </div>
                </div>

                <!-- Media Type Badge -->
                <div class="absolute top-3 left-3 z-20">
                  <span 
                    class="media-type-badge px-3 py-1.5 text-[10px] sm:text-xs font-bold text-foreground rounded-full backdrop-blur-xl shadow-xl border-2 transition-all duration-300 group-hover:scale-105 group-hover:border-primary/40 bg-success/20 text-success border-success/30 dark:bg-success/15 dark:border-success/25"
                  >
                    {{ getMediaTypeLabel(media).toUpperCase() }}
                  </span>
                </div>

                <!-- In Database Checkmark -->
                <div
                  v-if="isInDatabase(media)"
                  class="absolute top-3 right-3 z-20"
                >
                  <div class="status-badge-enhanced bg-success/30 backdrop-blur-xl shadow-2xl flex items-center justify-center w-8 h-8 sm:w-10 sm:h-10 rounded-2xl border-2 border-success/40 transition-all duration-300 group-hover:scale-110 group-hover:shadow-lg">
                    <Icon name="mdi:check-circle" size="14" class="sm:w-5 sm:h-5 text-success drop-shadow-lg" />
                  </div>
                </div>

                <!-- Hover Overlay with Request Button -->
                <div class="absolute inset-0 bg-gradient-to-t from-black/90 via-black/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-end z-10">
                  <div class="p-2 sm:p-3 w-full">
                    <button
                      v-if="canRequest(media)"
                      @click.stop="handleQuickRequestClick(media)"
                      class="w-full px-3 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium flex items-center justify-center gap-2 text-xs sm:text-sm"
                    >
                      <Icon name="mdi:plus-circle" size="16" />
                      <span>Request</span>
                    </button>
                    <button
                      v-else-if="isInDatabase(media)"
                      @click.stop="handleViewDetails(media)"
                      class="w-full px-3 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium flex items-center justify-center gap-2 text-xs sm:text-sm"
                    >
                      <Icon name="mdi:open-in-new" size="16" />
                      <span>View Details</span>
                    </button>
                    <div
                      v-else-if="hasBeenRequested(media)"
                      class="w-full px-3 py-2 bg-info/20 text-info rounded-lg font-medium flex items-center justify-center gap-2 text-xs sm:text-sm"
                    >
                      <Icon name="mdi:clock-outline" size="16" />
                      <span>Request Submitted</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Enhanced Card Info with Glassmorphic Background -->
              <div class="relative p-3 sm:p-4 space-y-2 bg-gradient-to-b from-card/95 via-card/90 to-card backdrop-blur-sm flex-shrink-0 rounded-b-2xl">
                <!-- Title -->
                <h3 class="text-xs sm:text-sm font-bold text-foreground line-clamp-2 transition-all duration-300 group-hover:text-primary">
                  {{ getMediaTitle(media) }}
                </h3>
                
                <!-- Year and Rating Row -->
                <div class="flex items-center justify-between gap-2">
                  <p class="text-[10px] sm:text-xs text-muted-foreground font-medium">
                    {{ getMediaYear(media) || 'N/A' }}
                  </p>
                  <div v-if="media.voteAverage" class="flex items-center gap-1 text-[10px] sm:text-xs bg-amber-500/20 px-2 py-0.5 rounded-full border border-amber-500/30">
                    <Icon name="mdi:star" size="10" class="sm:w-3 sm:h-3 text-amber-400 fill-amber-400" />
                    <span class="font-bold text-amber-400">{{ formatVoteAverage(media.voteAverage) }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Discover TV List View -->
          <div v-else class="space-y-2 sm:space-y-3 lg:space-y-4 mb-4 sm:mb-6">
            <div
              v-for="media in discoverTv"
              :key="media.id"
              @click="openModal(media)"
              class="group relative bg-card rounded-lg sm:rounded-xl cursor-pointer transition-all duration-300 hover:shadow-lg hover:border-primary border border-border overflow-hidden"
            >
              <div class="flex flex-row gap-2 sm:gap-3 lg:gap-4">
                <!-- Poster Thumbnail -->
                <div class="flex-shrink-0 w-16 sm:w-20 md:w-24 bg-muted rounded-l-lg sm:rounded-l-xl overflow-hidden relative" style="aspect-ratio: 2/3;">
                  <img
                    v-if="getPosterUrl(media.posterPath)"
                    :src="getPosterUrl(media.posterPath)"
                    :alt="getMediaTitle(media)"
                    class="absolute inset-0 w-full h-full object-cover"
                  />
                  <div v-else class="absolute inset-0 w-full h-full flex items-center justify-center">
                    <Icon name="mdi:image-off" class="w-8 h-8 sm:w-10 sm:h-10 text-muted-foreground" />
                  </div>
                  
                  <!-- Media Type Badge -->
                  <div class="absolute top-1 left-1 sm:top-1.5 sm:left-1.5 z-20">
                    <div class="bg-primary/90 backdrop-blur-sm text-primary-foreground px-1.5 sm:px-2 py-0.5 rounded text-[9px] sm:text-[10px] font-semibold">
                      {{ getMediaTypeLabel(media) }}
                    </div>
                  </div>
                  
                  <!-- In Database Checkmark -->
                  <div
                    v-if="isInDatabase(media)"
                    class="absolute top-1 right-1 sm:top-1.5 sm:right-1.5 z-20 w-5 h-5 sm:w-6 sm:h-6 flex items-center justify-center bg-success/90 backdrop-blur-sm rounded-full shadow-lg"
                  >
                    <Icon name="mdi:check-circle" class="w-3 h-3 sm:w-4 sm:h-4 text-white" />
                  </div>
                </div>
                
                <!-- Media Info -->
                <div class="flex-1 min-w-0 flex flex-col justify-between py-2 sm:py-3 pr-2 sm:pr-3 lg:pr-4 lg:py-4">
                  <div class="min-w-0">
                    <div class="flex items-start justify-between gap-2 mb-1 sm:mb-2">
                      <h3 class="text-sm sm:text-base lg:text-lg font-semibold text-foreground line-clamp-1 group-hover:text-primary transition-colors flex-1 min-w-0">
                        {{ getMediaTitle(media) }}
                      </h3>
                      <div v-if="media.voteAverage" class="flex items-center gap-0.5 sm:gap-1 flex-shrink-0">
                        <Icon name="mdi:star" class="w-3 h-3 sm:w-4 sm:h-4 text-yellow-400" />
                        <span class="text-[10px] sm:text-xs font-semibold text-foreground">{{ formatVoteAverage(media.voteAverage) }}</span>
                      </div>
                    </div>
                    
                    <div class="flex flex-wrap items-center gap-1.5 sm:gap-2 text-[10px] sm:text-xs text-muted-foreground mb-1.5 sm:mb-2">
                      <span v-if="getMediaYear(media)">{{ getMediaYear(media) }}</span>
                      <span v-if="media.mediaType !== 'person' && media.popularity" class="flex items-center gap-0.5 sm:gap-1">
                        <Icon name="mdi:trending-up" class="w-3 h-3 sm:w-4 sm:h-4" />
                        {{ Math.round(media.popularity) }}
                      </span>
                    </div>
                    
                    <p v-if="media.overview" class="text-[10px] sm:text-xs text-muted-foreground line-clamp-2 mb-1.5 sm:mb-2">
                      {{ media.overview }}
                    </p>
                  </div>
                  
                  <!-- Action Buttons -->
                  <div class="flex items-center gap-1.5 sm:gap-2">
                    <button
                      v-if="canRequest(media)"
                      @click.stop="handleQuickRequestClick(media)"
                      class="flex-1 sm:flex-initial px-2 sm:px-3 py-1 sm:py-1.5 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium flex items-center justify-center gap-1 sm:gap-1.5 text-[10px] sm:text-xs h-7 sm:h-8"
                    >
                      <Icon name="mdi:plus-circle" class="w-3 h-3 sm:w-4 sm:h-4" />
                      <span class="truncate">Request</span>
                    </button>
                    <button
                      v-else-if="isInDatabase(media)"
                      @click.stop="handleViewDetails(media)"
                      class="flex-1 sm:flex-initial px-2 sm:px-3 py-1 sm:py-1.5 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium flex items-center justify-center gap-1 sm:gap-1.5 text-[10px] sm:text-xs h-7 sm:h-8"
                    >
                      <Icon name="mdi:open-in-new" class="w-3 h-3 sm:w-4 sm:h-4" />
                      <span class="truncate">View</span>
                    </button>
                    <div
                      v-else-if="hasBeenRequested(media)"
                      class="flex-1 sm:flex-initial px-2 sm:px-3 py-1 sm:py-1.5 bg-info/20 text-info rounded-lg font-medium flex items-center justify-center gap-1 sm:gap-1.5 text-[10px] sm:text-xs h-7 sm:h-8"
                    >
                      <Icon name="mdi:clock-outline" class="w-3 h-3 sm:w-4 sm:h-4" />
                      <span class="truncate">Submitted</span>
                    </div>
                    <button
                      @click.stop="openModal(media)"
                      class="px-2 sm:px-3 py-1 sm:py-1.5 bg-card border border-border rounded-lg hover:bg-accent transition-colors flex items-center justify-center text-[10px] sm:text-xs h-7 sm:h-8 flex-shrink-0"
                    >
                      <Icon name="mdi:chevron-right" class="w-3 h-3 sm:w-4 sm:h-4" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <div v-if="tvPage < tvTotalPages" class="text-center">
            <button
              @click="loadMoreTv"
              class="px-4 sm:px-6 py-2 sm:py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium flex items-center gap-2 mx-auto text-sm sm:text-base"
            >
              <Icon name="mdi:chevron-down" class="w-4 h-4 sm:w-5 sm:h-5" />
              <span class="hidden sm:inline">Load More TV Shows</span>
              <span class="sm:hidden">Load More</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-if="!isSearching && resultsLength === 0 && !hasQuery && discoverMovies.length === 0 && discoverTv.length === 0" class="flex flex-col items-center justify-center py-12 sm:py-16">
        <Icon name="mdi:magnify" class="w-16 h-16 sm:w-20 sm:h-20 text-muted-foreground/50 mb-3 sm:mb-4" />
        <p class="text-sm sm:text-base lg:text-lg text-muted-foreground">Enter a search query to find media</p>
      </div>
  </div>

  <!-- Media Details Modal -->
  <MediaDetailsModal
    :media="selectedMedia"
    :is-open="isModalOpen"
    @close="closeModal"
    @request="handleRequest"
  />

  <!-- Toast Notifications -->
  <div class="fixed bottom-2 right-2 sm:bottom-4 sm:right-4 z-50 space-y-2 max-h-[calc(100vh-1rem)] sm:max-h-[calc(100vh-2rem)] overflow-hidden pointer-events-none">
    <TransitionGroup name="toast" tag="div" class="flex flex-col-reverse space-y-reverse space-y-2">
      <div
        v-for="toast in displayedToasts"
        :key="toast.id"
        class="px-3 sm:px-4 py-2 sm:py-3 rounded-lg shadow-lg w-[calc(100vw-1rem)] sm:min-w-[300px] sm:max-w-[400px] animate-fade-in pointer-events-auto border"
        :class="getToastClass(toast.type)"
      >
        <div class="flex items-center gap-2 sm:gap-3">
          <Icon :name="getToastIcon(toast.type)" class="w-4 h-4 sm:w-5 sm:h-5 flex-shrink-0" />
          <div class="flex-1 min-w-0">
            <p class="text-xs sm:text-sm font-medium">{{ toast.title }}</p>
            <p class="text-xs sm:text-sm opacity-90 line-clamp-2">{{ toast.message }}</p>
          </div>
          <button
            @click="removeToast(toast.id)"
            class="flex-shrink-0 hover:opacity-70 transition-opacity p-1 -mt-1 -mr-1"
            aria-label="Close notification"
          >
            <Icon name="mdi:close" class="w-3.5 h-3.5 sm:w-4 sm:h-4" />
          </button>
        </div>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup lang="ts">
const searchState = useSearch()
const isSearching = ref(false)

// View mode (grid/list)
const viewMode = ref<'grid' | 'list'>('grid')

// Load view mode from localStorage
if (process.client) {
  const savedViewMode = localStorage.getItem('search-view-mode')
  if (savedViewMode === 'grid' || savedViewMode === 'list') {
    viewMode.value = savedViewMode
  }
}

// Save view mode to localStorage
watch(viewMode, (newMode) => {
  if (process.client) {
    localStorage.setItem('search-view-mode', newMode)
  }
})

// Toast state
interface Toast {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message: string
}

const toasts = ref<Toast[]>([])
const toastTimeouts = new Map<string, NodeJS.Timeout>()

// Maximum number of toasts to display at once
const MAX_DISPLAYED_TOASTS = 5

// Timeout durations in milliseconds based on toast type
const TOAST_DURATIONS = {
  success: 4000,  // 4 seconds
  info: 5000,     // 5 seconds
  warning: 6000,  // 6 seconds
  error: 8000     // 8 seconds (errors stay longer)
}

// Computed property to limit displayed toasts
const displayedToasts = computed(() => {
  return toasts.value.slice(0, MAX_DISPLAYED_TOASTS)
})

const addToast = (type: Toast['type'], title: string, message: string) => {
  const id = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  toasts.value.push({ id, type, title, message })
  
  // Limit total toasts in memory to prevent memory leaks
  if (toasts.value.length > 20) {
    const removed = toasts.value.splice(20)
    removed.forEach(t => {
      const timeout = toastTimeouts.get(t.id)
      if (timeout) {
        clearTimeout(timeout)
        toastTimeouts.delete(t.id)
      }
    })
  }
  
  // Auto remove after duration based on type
  const duration = TOAST_DURATIONS[type] || TOAST_DURATIONS.info
  const timeout = setTimeout(() => {
    removeToast(id)
  }, duration)
  
  toastTimeouts.set(id, timeout)
}

const removeToast = (id: string) => {
  const index = toasts.value.findIndex(t => t.id === id)
  if (index > -1) {
    toasts.value.splice(index, 1)
  }
  
  // Clear timeout if it exists
  const timeout = toastTimeouts.get(id)
  if (timeout) {
    clearTimeout(timeout)
    toastTimeouts.delete(id)
  }
}

// Clean up timeouts on unmount
onUnmounted(() => {
  toastTimeouts.forEach(timeout => clearTimeout(timeout))
  toastTimeouts.clear()
})

const getToastClass = (type: string) => {
  const classes = {
    success: 'bg-success text-success-foreground',
    error: 'bg-destructive text-destructive-foreground',
    warning: 'bg-warning text-warning-foreground',
    info: 'bg-info text-info-foreground'
  }
  return classes[type as keyof typeof classes] || 'bg-muted text-foreground'
}

const getToastIcon = (type: string) => {
  const icons = {
    success: 'mdi:check-circle',
    error: 'mdi:alert-circle',
    warning: 'mdi:alert-triangle',
    info: 'mdi:information'
  }
  return icons[type as keyof typeof icons] || 'mdi:information'
}

const toast = {
  success: (message: string, title: string = 'Success') => addToast('success', title, message),
  error: (message: string, title: string = 'Error') => addToast('error', title, message),
  warning: (message: string, title: string = 'Warning') => addToast('warning', title, message),
  info: (message: string, title: string = 'Info') => addToast('info', title, message)
}

// Create a local ref for the input binding
const searchQuery = ref('')

// Sync the local ref with the composable
watch(searchQuery, (newValue) => {
  searchState.query.value = newValue
}, { immediate: false })

// Computed to check if query has content
const hasQuery = computed(() => {
  return searchQuery.value.trim().length > 0
})

const handleInput = debounce(() => {
  if (hasQuery.value) {
    handleSearch()
  }
}, 500)

// Computed properties for template access
const results = computed(() => {
  const rawResults = searchState.results
  return Array.isArray(rawResults) ? rawResults : (typeof rawResults === 'object' && rawResults?.value ? rawResults.value : [])
})

const resultsLength = computed(() => results.value.length)

// Discover results
const discoverMovies = ref<any[]>([])
const discoverTv = ref<any[]>([])
const moviesPage = ref(1)
const tvPage = ref(1)
const moviesTotalPages = ref(1)
const tvTotalPages = ref(1)
const isLoadingDiscover = ref(false)

// Load discover results on mount
onMounted(async () => {
  await loadDiscoverResults()
})

const loadDiscoverResults = async () => {
  isLoadingDiscover.value = true
  try {
    // Load movies
    const moviesResponse = await $fetch('/api/overseerr-discover', {
      query: {
        page: moviesPage.value,
        sortBy: 'popularity.desc',
        language: 'en',
        type: 'movies'
      }
    })
    
    if (moviesResponse.success && moviesResponse.data) {
      discoverMovies.value = moviesResponse.data.results.slice(0, 12) // Limit to 12
      moviesTotalPages.value = moviesResponse.data.totalPages
    }
    
    // Load TV shows
    const tvResponse = await $fetch('/api/overseerr-discover', {
      query: {
        page: tvPage.value,
        sortBy: 'popularity.desc',
        language: 'en',
        type: 'tv'
      }
    })
    
    if (tvResponse.success && tvResponse.data) {
      discoverTv.value = tvResponse.data.results.slice(0, 12) // Limit to 12
      tvTotalPages.value = tvResponse.data.totalPages
    }
  } catch (error) {
    console.error('Error loading discover results:', error)
  } finally {
    isLoadingDiscover.value = false
  }
}

const loadMoreMovies = async () => {
  if (moviesPage.value >= moviesTotalPages.value) return
  moviesPage.value++
  
  try {
    const response = await $fetch('/api/overseerr-discover', {
      query: {
        page: moviesPage.value,
        sortBy: 'popularity.desc',
        language: 'en',
        type: 'movies'
      }
    })
    
    if (response.success && response.data) {
      // Append new results (limit to 12 per page)
      const newResults = response.data.results.slice(0, 12)
      discoverMovies.value.push(...newResults)
    }
  } catch (error) {
    console.error('Error loading more movies:', error)
  }
}

const loadMoreTv = async () => {
  if (tvPage.value >= tvTotalPages.value) return
  tvPage.value++
  
  try {
    const response = await $fetch('/api/overseerr-discover', {
      query: {
        page: tvPage.value,
        sortBy: 'popularity.desc',
        language: 'en',
        type: 'tv'
      }
    })
    
    if (response.success && response.data) {
      // Append new results (limit to 12 per page)
      const newResults = response.data.results.slice(0, 12)
      discoverTv.value.push(...newResults)
    }
  } catch (error) {
    console.error('Error loading more TV shows:', error)
  }
}

// Modal state
const isModalOpen = ref(false)
const selectedMedia = ref(null)

const openModal = (media: any) => {
  selectedMedia.value = media
  isModalOpen.value = true
}

const closeModal = () => {
  isModalOpen.value = false
  selectedMedia.value = null
}

const isAvailable = (media: any) => {
  // Available if mediaInfo exists and status is 5
  return media.mediaInfo && media.mediaInfo.status === 5
}

const isInDatabase = (media: any) => {
  // In database if mediaInfo exists (regardless of status)
  return !!media.mediaInfo
}

const canRequest = (media: any) => {
  // Can request if not in database and not already requested
  return !isInDatabase(media) && !hasBeenRequested(media)
}

// Cache for database links
const databaseLinks = ref<Map<number, string>>(new Map())

const getDatabaseLink = (media: any) => {
  // Return cached link if available
  if (databaseLinks.value.has(media.id)) {
    return databaseLinks.value.get(media.id)
  }
  
  // If not in database, return null
  if (!media.mediaInfo || !media.mediaInfo.id) {
    return null
  }
  
  // For now, return null - we'll fetch it when needed
  return null
}

// Fetch the database link for a media item
const fetchDatabaseLink = async (media: any) => {
  if (!media.mediaInfo) return null
  
  // Check cache first
  if (databaseLinks.value.has(media.id)) {
    return databaseLinks.value.get(media.id)
  }
  
  try {
    // Use tmdb_id to get the unified_media id from database
    const response = await $fetch('/api/media-check', {
      query: {
        tmdbId: media.id,
        mediaType: media.mediaType
      }
    })
    
    if (response.success && response.exists && response.data?.id) {
      const link = `/processed-media?mediaId=${response.data.id}`
      databaseLinks.value.set(media.id, link)
      return link
    }
    
    return null
  } catch (error) {
    console.error('Error fetching database link:', error)
    return null
  }
}

const requestedMedia = ref<Set<number>>(new Set())

const handleRequest = async (mediaId: number, mediaType: string, seasons?: number[]) => {
  console.log('Requesting media:', mediaId, mediaType, seasons)
  
  try {
    const response = await $fetch('/api/overseerr-request', {
      method: 'POST',
      body: {
        mediaId,
        mediaType,
        is4k: false,
        seasons
      }
    })
    
    if (response.success) {
      // Mark as requested
      requestedMedia.value.add(mediaId)
      
      // Show success notification
      toast.success(
        `${mediaType === 'tv' ? 'TV show' : 'Movie'} request submitted successfully`,
        'Request Submitted'
      )
      
      // Close modal if open
      if (isModalOpen.value && selectedMedia.value?.id === mediaId) {
        closeModal()
      }
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
  }
}

const hasBeenRequested = (media: any) => {
  return requestedMedia.value.has(media.id)
}

const handleViewDetails = async (media: any) => {
  const link = await fetchDatabaseLink(media)
  if (link) {
    navigateTo(link)
  }
}

const handleQuickRequestClick = async (media: any) => {
  // For TV shows, open modal to select seasons
  if (media.mediaType === 'tv') {
    openModal(media)
  } else {
    // For movies, quick request
    await handleRequest(media.id, media.mediaType)
  }
}

const handleQuickRequest = async (media: any) => {
  await handleRequest(media.id, media.mediaType)
}

const handleSearch = async () => {
  if (!hasQuery.value || isSearching.value) return
  
  isSearching.value = true
  await searchState.searchMedia(searchQuery.value)
  console.log('Search completed. Results:', searchState.results)
  console.log('Results length:', resultsLength.value)
  isSearching.value = false
}

const getPosterUrl = (posterPath?: string | null) => {
  if (!posterPath) return ''
  return `https://image.tmdb.org/t/p/w500${posterPath}`
}

const getMediaTitle = (media: any) => {
  if (media.mediaType === 'movie') {
    return media.title || media.originalTitle || 'Unknown Movie'
  } else if (media.mediaType === 'tv') {
    return media.name || media.originalName || 'Unknown Show'
  }
  return 'Unknown'
}

const getMediaYear = (media: any) => {
  if (media.mediaType === 'movie' && media.releaseDate) {
    return media.releaseDate.split('-')[0]
  } else if (media.mediaType === 'tv' && media.firstAirDate) {
    return media.firstAirDate.split('-')[0]
  }
  return ''
}

const getMediaTypeLabel = (media: any) => {
  if (media.mediaType === 'movie') return 'Movie'
  if (media.mediaType === 'tv') return 'TV Show'
  if (media.mediaType === 'person') return 'Person'
  return 'Unknown'
}

const formatVoteAverage = (voteAverage?: number) => {
  if (!voteAverage) return 'N/A'
  return voteAverage.toFixed(1)
}

const handleImageError = (event: Event) => {
  const img = event.target as HTMLImageElement
  img.style.display = 'none'
}

const hasRequests = (media: any) => {
  return media.mediaInfo?.requests && media.mediaInfo.requests.length > 0
}

function debounce(fn: Function, delay: number) {
  let timeout: NodeJS.Timeout
  return function(...args: any[]) {
    clearTimeout(timeout)
    timeout = setTimeout(() => fn.apply(null, args), delay)
  }
}

// Set page metadata
useHead({
  title: 'Search Media - Darth Vadarr'
})
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.toast-enter-from {
  opacity: 0;
  transform: translateY(100%) scale(0.95);
}

.toast-leave-to {
  opacity: 0;
  transform: translateY(100%) scale(0.95);
}

.toast-move {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
</style>

