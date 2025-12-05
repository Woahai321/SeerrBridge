<template>
  <!-- Setup Wizard -->
  <div v-if="!showBackendInitializing" class="min-h-screen bg-background flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
    <div class="max-w-5xl w-full space-y-8">
      <div class="text-center">
        <h2 class="mt-6 text-3xl font-extrabold text-foreground">
          Welcome to SeerrBridge
        </h2>
        <p class="mt-2 text-sm text-muted-foreground">
          Let's get your SeerrBridge instance configured and ready to go!
        </p>
      </div>


      <!-- Environment Variables Available Banner -->
      <div v-if="envVarsAvailable && !setupSkipped" class="bg-blue-50 dark:bg-blue-900/20 border border-blue-500 rounded-lg p-4 mb-4">
        <div class="flex items-start justify-between">
          <div class="flex items-start">
            <Icon name="lucide:info" class="w-5 h-5 text-blue-600 mr-2 flex-shrink-0 mt-0.5" />
            <div class="flex-1">
              <h4 class="font-semibold text-blue-900 dark:text-blue-100">Environment Variables Detected</h4>
              <p class="text-sm text-blue-800 dark:text-blue-200 mt-1">
                All required configuration values are available in your .env file. You can skip the setup wizard and use these values directly.
              </p>
            </div>
          </div>
          <button
            @click="skipSetupWithEnv"
            :disabled="isSaving || isSkippingSetup"
            class="ml-4 px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
          >
            <Icon v-if="isSkippingSetup" name="lucide:loader-2" class="w-4 h-4 animate-spin" />
            <span>{{ isSkippingSetup ? 'Loading...' : 'Skip Setup & Use .env' }}</span>
          </button>
        </div>
      </div>

      <!-- Success Message After Skipping -->
      <div v-if="setupSkipped" class="bg-green-50 dark:bg-green-900/20 border border-green-500 rounded-lg p-4">
        <div class="flex items-start">
          <Icon name="lucide:check-circle" class="w-5 h-5 text-green-600 mr-2 flex-shrink-0" />
          <div class="flex-1">
            <h4 class="font-semibold text-green-900 dark:text-green-100">Setup Complete!</h4>
            <p class="text-sm text-green-800 dark:text-green-200 mt-1">
              Configuration loaded from environment variables successfully. Redirecting to dashboard...
            </p>
          </div>
        </div>
      </div>

      <div class="bg-card shadow rounded-lg border border-border">
        <div class="px-4 py-5 sm:p-6">
          <!-- Progress Steps -->
          <div class="mb-8">
            <nav aria-label="Progress">
              <ol class="flex items-center justify-center space-x-8">
                <li v-for="(step, index) in steps" :key="step.id" class="flex items-center">
                  <div class="flex items-center">
                    <div :class="[
                      'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-all',
                      step.testStatus === 'success' ? 'bg-green-600 text-white scale-110' : 
                      currentStep === index ? 'bg-primary text-primary-foreground' : 
                      'bg-muted text-muted-foreground'
                    ]">
                      <Icon v-if="step.testStatus === 'success'" name="lucide:check" class="w-5 h-5" />
                      <Icon v-else-if="step.testStatus === 'testing'" name="lucide:loader-2" class="w-5 h-5 animate-spin" />
                      <span v-else>{{ index + 1 }}</span>
                    </div>
                    <span :class="[
                      'ml-3 text-sm font-medium transition-colors',
                      step.testStatus === 'success' ? 'text-green-600' :
                      currentStep >= index ? 'text-foreground' : 'text-muted-foreground'
                    ]">
                      {{ step.name }}
                    </span>
                  </div>
                  <Icon v-if="index < steps.length - 1" name="lucide:chevron-right" class="ml-8 w-5 h-5 text-muted-foreground" />
                </li>
              </ol>
            </nav>
          </div>

          <!-- Step Content -->
          <div class="space-y-6">
            <!-- Step 1: Debrid Media Manager Configuration -->
            <div v-if="currentStep === 0" class="space-y-6">
              <div>
                <h3 class="text-lg font-medium text-foreground">Debrid Media Manager Configuration</h3>
                <p class="mt-1 text-sm text-muted-foreground">
                  Configure your credentials to access your DMM / Real-Debrid library.
                </p>
              </div>
              
              <!-- Success State -->
              <div v-if="testResults.dmm.success" class="bg-gradient-to-br from-green-50 to-blue-50 dark:from-green-900/20 dark:to-blue-900/20 border-2 border-green-500 rounded-lg p-6 relative overflow-hidden animate-pulse">
                <div class="absolute inset-0 pointer-events-none">
                  <div v-for="(particle, index) in dmmParticles" :key="index" 
                       class="absolute w-2 h-2 bg-green-400 rounded-full animate-ping"
                       :style="{ left: particle.left + '%', top: particle.top + '%', animationDelay: particle.animationDelay + 's' }">
                  </div>
                </div>
                <div class="flex items-start relative z-10">
                  <Icon name="lucide:check-circle" class="w-6 h-6 text-green-600 mr-3 flex-shrink-0" />
                  <div class="flex-1">
                    <h4 class="text-lg font-semibold text-green-900 dark:text-green-100 mb-2">🎉 Connection Successful!</h4>
                    <p class="text-sm text-green-800 dark:text-green-200 mb-4">
                      Your Debrid Media Manager credentials are working correctly.
                    </p>
                    <div class="grid grid-cols-2 gap-4 mt-4">
                      <div class="bg-white dark:bg-gray-800 rounded-lg p-4">
                        <p class="text-2xl font-bold text-green-900 dark:text-green-100">{{ testResults.dmm.libraryStats?.torrents_count || 0 }}</p>
                        <p class="text-sm text-green-700 dark:text-green-300">Torrents</p>
                      </div>
                      <div class="bg-white dark:bg-gray-800 rounded-lg p-4">
                        <p class="text-2xl font-bold text-green-900 dark:text-green-100">{{ testResults.dmm.libraryStats?.total_size_tb || 0 }} TB</p>
                        <p class="text-sm text-green-700 dark:text-green-300">Total Size</p>
                      </div>
                    </div>
                    <div v-if="testResults.dmm.libraryStats?.note" class="mt-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                      <p class="text-sm text-blue-800 dark:text-blue-200">{{ testResults.dmm.libraryStats.note }}</p>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Progress/Testing State -->
              <div v-if="testing[0] && dmmProgress.length > 0" class="bg-blue-50 dark:bg-blue-900/20 border border-blue-500 rounded-lg p-4 mb-4">
                <div class="flex items-start mb-2">
                  <Icon name="lucide:loader-2" class="w-5 h-5 text-blue-600 mr-2 flex-shrink-0 animate-spin" />
                  <h4 class="font-semibold text-blue-900 dark:text-blue-100">Testing Connection...</h4>
                </div>
                <div ref="progressContainerRef" class="max-h-48 overflow-y-auto space-y-2">
                  <div 
                    v-for="(progress, index) in dmmProgress" 
                    :key="index"
                    class="flex items-start text-sm"
                  >
                    <Icon 
                      v-if="progress.status === 'success'"
                      name="lucide:check-circle" 
                      class="w-4 h-4 text-green-600 mr-2 flex-shrink-0 mt-0.5" 
                    />
                    <Icon 
                      v-else-if="progress.status === 'error'"
                      name="lucide:alert-circle" 
                      class="w-4 h-4 text-red-600 mr-2 flex-shrink-0 mt-0.5" 
                    />
                    <Icon 
                      v-else-if="progress.status === 'warning'"
                      name="lucide:alert-triangle" 
                      class="w-4 h-4 text-yellow-600 mr-2 flex-shrink-0 mt-0.5" 
                    />
                    <Icon 
                      v-else
                      name="lucide:info" 
                      class="w-4 h-4 text-blue-600 mr-2 flex-shrink-0 mt-0.5" 
                    />
                    <div class="flex-1">
                      <span class="text-xs text-muted-foreground mr-2">{{ progress.timestamp }}</span>
                      <span 
                        :class="[
                          progress.status === 'success' ? 'text-green-800 dark:text-green-200' :
                          progress.status === 'error' ? 'text-red-800 dark:text-red-200' :
                          progress.status === 'warning' ? 'text-yellow-800 dark:text-yellow-200' :
                          'text-blue-800 dark:text-blue-200'
                        ]"
                      >
                        {{ progress.message }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Error State -->
              <div v-else-if="testResults.dmm.error" class="bg-red-50 dark:bg-red-900/20 border border-red-500 rounded-lg p-4">
                <div class="flex items-start">
                  <Icon name="lucide:alert-circle" class="w-5 h-5 text-red-600 mr-2 flex-shrink-0" />
                  <div>
                    <h4 class="font-semibold text-red-900 dark:text-red-100">Connection Failed</h4>
                    <p class="text-sm text-red-800 dark:text-red-200 mt-1">{{ testResults.dmm.error }}</p>
                  </div>
                </div>
              </div>

              <!-- Input Fields -->
              <div v-if="!testResults.dmm.success" class="grid grid-cols-1 gap-6 sm:grid-cols-2">
                <div>
                  <label class="block text-sm font-medium text-foreground">Access Token</label>
                  <input
                    v-model="config.rd_access_token"
                    type="password"
                    @blur="dmmValidationErrors.rd_access_token = validateAccessToken(config.rd_access_token)"
                    :class="[
                      'mt-1 block w-full border rounded-md shadow-sm bg-background text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-ring',
                      dmmValidationErrors.rd_access_token ? 'border-red-500 focus:border-red-500 focus:ring-red-500' : 'border-input'
                    ]"
                    placeholder='JSON object or token string'
                  />
                  <p v-if="dmmValidationErrors.rd_access_token" class="mt-1 text-sm text-red-600 dark:text-red-400">
                    {{ dmmValidationErrors.rd_access_token }}
                  </p>
                  <p v-else class="mt-1 text-xs text-muted-foreground">
                    Can be JSON object with "value" and "expiry" fields, or plain token string
                  </p>
                </div>
                <div>
                  <label class="block text-sm font-medium text-foreground">Client ID</label>
                  <input
                    v-model="config.rd_client_id"
                    type="text"
                    @blur="dmmValidationErrors.rd_client_id = validateClientId(config.rd_client_id)"
                    :class="[
                      'mt-1 block w-full border rounded-md shadow-sm bg-background text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-ring',
                      dmmValidationErrors.rd_client_id ? 'border-red-500 focus:border-red-500 focus:ring-red-500' : 'border-input'
                    ]"
                    placeholder='Example: ABC123XYZ789'
                  />
                  <p v-if="dmmValidationErrors.rd_client_id" class="mt-1 text-sm text-red-600 dark:text-red-400">
                    {{ dmmValidationErrors.rd_client_id }}
                  </p>
                  <p v-else class="mt-1 text-xs text-muted-foreground">
                    Alphanumeric, at least 8 characters (quotes optional)
                  </p>
                </div>
                <div>
                  <label class="block text-sm font-medium text-foreground">Client Secret</label>
                  <input
                    v-model="config.rd_client_secret"
                    type="password"
                    @blur="dmmValidationErrors.rd_client_secret = validateClientSecret(config.rd_client_secret)"
                    :class="[
                      'mt-1 block w-full border rounded-md shadow-sm bg-background text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-ring',
                      dmmValidationErrors.rd_client_secret ? 'border-red-500 focus:border-red-500 focus:ring-red-500' : 'border-input'
                    ]"
                    placeholder='Example: xyz789abc123def456'
                  />
                  <p v-if="dmmValidationErrors.rd_client_secret" class="mt-1 text-sm text-red-600 dark:text-red-400">
                    {{ dmmValidationErrors.rd_client_secret }}
                  </p>
                  <p v-else class="mt-1 text-xs text-muted-foreground">
                    Alphanumeric, at least 16 characters (quotes optional)
                  </p>
                </div>
                <div>
                  <label class="block text-sm font-medium text-foreground">Refresh Token</label>
                  <input
                    v-model="config.rd_refresh_token"
                    type="password"
                    @blur="dmmValidationErrors.rd_refresh_token = validateRefreshToken(config.rd_refresh_token)"
                    :class="[
                      'mt-1 block w-full border rounded-md shadow-sm bg-background text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-ring',
                      dmmValidationErrors.rd_refresh_token ? 'border-red-500 focus:border-red-500 focus:ring-red-500' : 'border-input'
                    ]"
                    placeholder='Example: abc123xyz789def456ghi012jkl345mno678'
                  />
                  <p v-if="dmmValidationErrors.rd_refresh_token" class="mt-1 text-sm text-red-600 dark:text-red-400">
                    {{ dmmValidationErrors.rd_refresh_token }}
                  </p>
                  <p v-else class="mt-1 text-xs text-muted-foreground">
                    Alphanumeric, at least 32 characters (quotes optional)
                  </p>
                </div>
              </div>
            </div>

            <!-- Step 2: Overseerr Configuration -->
            <div v-if="currentStep === 1" class="space-y-6">
              <div>
                <h3 class="text-lg font-medium text-foreground">Overseerr Configuration</h3>
                <p class="mt-1 text-sm text-muted-foreground">
                  Connect to your Overseerr instance for media request management.
                </p>
              </div>
              
              <!-- Success State -->
              <div v-if="testResults.overseerr.success" class="bg-gradient-to-br from-green-50 to-blue-50 dark:from-green-900/20 dark:to-blue-900/20 border-2 border-green-500 rounded-lg p-6 relative overflow-hidden animate-pulse">
                <div class="absolute inset-0 pointer-events-none">
                  <div v-for="(particle, index) in overseerrParticles" :key="index" 
                       class="absolute w-2 h-2 bg-blue-400 rounded-full animate-ping"
                       :style="{ left: particle.left + '%', top: particle.top + '%', animationDelay: particle.animationDelay + 's' }">
                  </div>
                </div>
                <div class="flex items-start relative z-10">
                  <Icon name="lucide:check-circle" class="w-6 h-6 text-green-600 mr-3 flex-shrink-0" />
                  <div class="flex-1">
                    <h4 class="text-lg font-semibold text-green-900 dark:text-green-100 mb-2">🎉 Overseerr Connected!</h4>
                    <p class="text-sm text-green-800 dark:text-green-200 mb-4">
                      Successfully connected to your Overseerr instance at {{ testResults.overseerr.data?.overseerr_url }}
                    </p>
                    
                    <!-- Total Requests -->
                    <div class="bg-white dark:bg-gray-800 rounded-lg p-4 mb-4">
                      <p class="text-2xl font-bold text-green-900 dark:text-green-100 text-center">{{ testResults.overseerr.data?.total_requests || 0 }}</p>
                      <p class="text-sm text-green-700 dark:text-green-300 text-center">Total Approved Requests</p>
                    </div>
                    
                    <!-- Greet first Jellyfin user -->
                    <div v-if="testResults.overseerr.data?.first_jellyfin_username" class="bg-gradient-to-r from-primary/10 to-primary/5 border border-primary/30 rounded-lg p-4 mb-4">
                      <p class="text-sm text-center font-medium text-primary">
                        👋 Hello <span class="font-bold">{{ testResults.overseerr.data.first_jellyfin_username }}</span>!
                      </p>
                    </div>
                    
                    <!-- First Request Example -->
                    <div v-if="testResults.overseerr.data?.first_request" class="bg-white dark:bg-gray-800 rounded-lg p-4 border-2 border-green-500">
                      <h5 class="font-semibold text-green-900 dark:text-green-100 mb-3">Example Request:</h5>
                      <div class="flex items-start space-x-4">
                        <div v-if="testResults.overseerr.data.first_request.poster" class="w-20 h-30 bg-gray-200 dark:bg-gray-700 rounded overflow-hidden flex-shrink-0">
                          <img :src="`https://image.tmdb.org/t/p/w500${testResults.overseerr.data.first_request.poster}`" 
                               :alt="testResults.overseerr.data.first_request.title" 
                               class="w-full h-full object-cover" />
                        </div>
                        <div class="flex-1">
                          <p class="font-bold text-lg text-foreground mb-1">{{ testResults.overseerr.data.first_request.title }}</p>
                          <p class="text-sm text-muted-foreground mb-2">{{ testResults.overseerr.data.first_request.year }} • {{ testResults.overseerr.data.first_request.type === 'movie' ? 'Movie' : 'TV Show' }}</p>
                          <p class="text-xs text-muted-foreground line-clamp-2 mb-2">{{ testResults.overseerr.data.first_request.overview }}</p>
                          <p class="text-xs text-muted-foreground">Requested by: <span class="font-medium">{{ testResults.overseerr.data.first_request.requestedBy }}</span></p>
                          <p class="text-xs text-muted-foreground">Created: {{ new Date(testResults.overseerr.data.first_request.createdAt).toLocaleDateString() }}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Error State -->
              <div v-else-if="testResults.overseerr.error" class="bg-red-50 dark:bg-red-900/20 border border-red-500 rounded-lg p-4">
                <div class="flex items-start">
                  <Icon name="lucide:alert-circle" class="w-5 h-5 text-red-600 mr-2 flex-shrink-0" />
                  <div>
                    <h4 class="font-semibold text-red-900 dark:text-red-100">Connection Failed</h4>
                    <p class="text-sm text-red-800 dark:text-red-200 mt-1">{{ testResults.overseerr.error }}</p>
                  </div>
                </div>
              </div>

              <!-- Input Fields -->
              <div v-if="!testResults.overseerr.success" class="space-y-4">
                <div>
                  <label class="block text-sm font-medium text-foreground">Overseerr Base URL</label>
                  <input
                    v-model="config.overseerr_base"
                    type="url"
                    class="mt-1 block w-full border border-input rounded-md shadow-sm bg-background text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-ring"
                    placeholder="https://your-overseerr-instance.com"
                  />
                </div>
                <div>
                  <label class="block text-sm font-medium text-foreground">API Key</label>
                  <input
                    v-model="config.overseerr_api_key"
                    type="password"
                    class="mt-1 block w-full border border-input rounded-md shadow-sm bg-background text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-ring"
                    placeholder="Enter your Overseerr API Key"
                  />
                </div>
              </div>
            </div>

            <!-- Step 3: Trakt Configuration -->
            <div v-if="currentStep === 2" class="space-y-6">
              <div>
                <h3 class="text-lg font-medium text-foreground">Trakt Configuration</h3>
                <p class="mt-1 text-sm text-muted-foreground">
                  Configure Trakt API for enhanced media information and images.
                </p>
              </div>
              
              <!-- Success State with Confetti -->
              <div v-if="testResults.trakt.success" class="bg-gradient-to-br from-green-50 to-primary/10 dark:from-green-900/20 dark:to-primary/20 border-2 border-green-500 rounded-lg p-6 relative overflow-hidden animate-pulse">
                <div class="absolute inset-0 pointer-events-none">
                  <div v-for="(particle, index) in traktParticles" :key="index" 
                       class="absolute w-2 h-2 bg-yellow-400 rounded-full animate-ping"
                       :style="{ left: particle.left + '%', top: particle.top + '%', animationDelay: particle.animationDelay + 's' }">
                  </div>
                </div>
                <div class="flex items-start relative z-10">
                  <Icon name="lucide:check-circle" class="w-6 h-6 text-green-600 mr-3 flex-shrink-0" />
                  <div class="flex-1">
                    <h4 class="text-lg font-semibold text-green-900 dark:text-green-100 mb-2">🎊 Confetti! Trakt API Connected!</h4>
                    <p class="text-sm text-green-800 dark:text-green-200 mb-4">
                      Trakt API is working perfectly. Here's a sample from your library:
                    </p>
                    <div v-if="testResults.trakt.mediaData" class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-lg">
                      <div class="flex items-start space-x-4">
                        <!-- Show poster if available, otherwise show a placeholder -->
                        <div v-if="testResults.trakt.mediaData.poster_url" class="flex-shrink-0">
                          <img :src="testResults.trakt.mediaData.poster_url" 
                               :alt="testResults.trakt.mediaData.title" 
                               class="w-24 h-36 object-cover rounded-lg shadow-md" />
                        </div>
                        <div v-else class="flex-shrink-0 w-24 h-36 bg-gradient-to-br from-primary/60 to-blue-500 rounded-lg shadow-md flex items-center justify-center">
                          <Icon name="lucide:tv" class="w-8 h-8 text-white" />
                        </div>
                        <div class="flex-1">
                          <h5 class="text-lg font-bold text-foreground">{{ testResults.trakt.mediaData.title }}</h5>
                          <p class="text-sm text-muted-foreground">{{ testResults.trakt.mediaData.year }}</p>
                          <p v-if="testResults.trakt.mediaData.tagline" class="text-sm text-primary italic mt-1">
                            "{{ testResults.trakt.mediaData.tagline }}"
                          </p>
                          <p class="text-sm text-foreground mt-2 line-clamp-3">{{ testResults.trakt.mediaData.overview }}</p>
                          <div class="flex items-center space-x-4 mt-3">
                            <div v-if="testResults.trakt.mediaData.rating" class="flex items-center space-x-1">
                              <Icon name="lucide:star" class="w-4 h-4 text-yellow-500" />
                              <span class="text-sm font-medium">{{ testResults.trakt.mediaData.rating.toFixed(1) }}</span>
                            </div>
                            <div v-if="testResults.trakt.mediaData.runtime" class="flex items-center space-x-1">
                              <Icon name="lucide:clock" class="w-4 h-4 text-blue-500" />
                              <span class="text-sm">{{ testResults.trakt.mediaData.runtime }} min</span>
                            </div>
                            <div v-if="testResults.trakt.mediaData.aired_episodes" class="flex items-center space-x-1">
                              <Icon name="lucide:play-circle" class="w-4 h-4 text-green-500" />
                              <span class="text-sm">{{ testResults.trakt.mediaData.aired_episodes }} episodes</span>
                            </div>
                          </div>
                          <div v-if="testResults.trakt.mediaData.first_aired" class="mt-2 text-xs text-muted-foreground">
                            First aired: {{ new Date(testResults.trakt.mediaData.first_aired).toLocaleDateString() }}
                          </div>
                          <div v-if="testResults.trakt.mediaData.trakt_id" class="mt-2 text-xs text-muted-foreground">
                            Trakt ID: {{ testResults.trakt.mediaData.trakt_id }} | TMDB ID: {{ testResults.trakt.mediaData.tmdb_id }}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Error State -->
              <div v-else-if="testResults.trakt.error" class="bg-red-50 dark:bg-red-900/20 border border-red-500 rounded-lg p-4">
                <div class="flex items-start">
                  <Icon name="lucide:alert-circle" class="w-5 h-5 text-red-600 mr-2 flex-shrink-0" />
                  <div>
                    <h4 class="font-semibold text-red-900 dark:text-red-100">Connection Failed</h4>
                    <p class="text-sm text-red-800 dark:text-red-200 mt-1">{{ testResults.trakt.error }}</p>
                  </div>
                </div>
              </div>

              <!-- Input Fields -->
              <div>
                <label class="block text-sm font-medium text-foreground">Trakt API Key</label>
                <input
                  v-model="config.trakt_api_key"
                  type="password"
                  class="mt-1 block w-full border border-input rounded-md shadow-sm bg-background text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-ring"
                  placeholder="Enter your Trakt API Key"
                />
                <p class="mt-1 text-xs text-muted-foreground">
                  Get your API key from <a href="https://trakt.tv/oauth/applications" target="_blank" class="text-primary hover:text-primary/80 underline">Trakt.tv</a>
                </p>
              </div>
            </div>

            <!-- Step 4: System Settings -->
            <div v-if="currentStep === 3" class="space-y-6">
              <div>
                <h3 class="text-lg font-medium text-foreground">System Settings</h3>
                <p class="mt-1 text-sm text-muted-foreground">
                  Configure general system behavior and preferences.
                </p>
              </div>
              
              <div class="space-y-4">
                <div class="flex items-center">
                  <input
                    v-model="config.headless_mode"
                    type="checkbox"
                    class="h-4 w-4 text-primary focus:ring-ring border-input rounded"
                  />
                  <label class="ml-2 block text-sm text-foreground">
                    Run browser in headless mode (recommended for servers)
                  </label>
                </div>
                
                <div>
                  <label class="block text-sm font-medium text-foreground">Refresh Interval (minutes)</label>
                  <input
                    v-model.number="config.refresh_interval_minutes"
                    type="number"
                    min="1"
                    max="1440"
                    class="mt-1 block w-full border border-input rounded-md shadow-sm bg-background text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-ring"
                  />
                </div>
                
                <div>
                  <label class="block text-sm font-medium text-foreground">Torrent Filter Regex</label>
                  <input
                    v-model="config.torrent_filter_regex"
                    type="text"
                    class="mt-1 block w-full border border-input rounded-md shadow-sm bg-background text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-ring"
                    placeholder="Enter regex pattern (default is prefilled)"
                  />
                </div>
              </div>
              
              <!-- Size Limits -->
              <div class="space-y-4 pt-4 border-t border-border">
                <h4 class="text-base font-medium text-foreground">Size Limits</h4>
                <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <label class="block text-sm font-medium text-foreground mb-2">Max Movie Size (GB)</label>
                    <select
                      v-model.number="config.max_movie_size"
                      class="mt-1 block w-full border border-input rounded-md shadow-sm bg-background text-foreground focus:ring-2 focus:ring-ring focus:border-ring"
                    >
                      <option :value="0">Unlimited</option>
                      <option :value="1">1 GB</option>
                      <option :value="3">3 GB</option>
                      <option :value="5">5 GB</option>
                      <option :value="15">15 GB</option>
                      <option :value="30">30 GB</option>
                      <option :value="60">60 GB</option>
                    </select>
                    <p class="mt-1 text-xs text-muted-foreground">0 = No size limit</p>
                  </div>
                  <div>
                    <label class="block text-sm font-medium text-foreground mb-2">Max Episode Size (GB)</label>
                    <select
                      v-model.number="config.max_episode_size"
                      class="mt-1 block w-full border border-input rounded-md shadow-sm bg-background text-foreground focus:ring-2 focus:ring-ring focus:border-ring"
                    >
                      <option :value="0">Unlimited</option>
                      <option :value="0.1">100 MB</option>
                      <option :value="0.3">300 MB</option>
                      <option :value="0.5">500 MB</option>
                      <option :value="1">1 GB</option>
                      <option :value="3">3 GB</option>
                      <option :value="5">5 GB</option>
                    </select>
                    <p class="mt-1 text-xs text-muted-foreground">0 = No size limit</p>
                  </div>
                </div>
              </div>
              
              <!-- Task Configuration -->
              <div class="space-y-4 pt-4 border-t border-border">
                <h4 class="text-base font-medium text-foreground">Background Tasks</h4>
                <div class="space-y-3">
                  <div class="flex items-center">
                    <input
                      v-model="config.background_tasks_enabled"
                      type="checkbox"
                      class="h-4 w-4 text-primary focus:ring-ring border-input rounded"
                    />
                    <label class="ml-2 block text-sm text-foreground">
                      Enable Background Tasks
                    </label>
                  </div>
                  <div class="flex items-center">
                    <input
                      v-model="config.scheduler_enabled"
                      type="checkbox"
                      class="h-4 w-4 text-primary focus:ring-ring border-input rounded"
                    />
                    <label class="ml-2 block text-sm text-foreground">
                      Enable Scheduler
                    </label>
                  </div>
                  <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <div>
                      <label class="block text-sm font-medium text-foreground">Token Refresh Interval (minutes)</label>
                      <input
                        v-model.number="config.token_refresh_interval_minutes"
                        type="number"
                        min="1"
                        max="60"
                        class="mt-1 block w-full border border-input rounded-md shadow-sm bg-background text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-ring"
                      />
                    </div>
                    <div>
                      <label class="block text-sm font-medium text-foreground">Movie Processing Check Interval (minutes)</label>
                      <input
                        v-model.number="config.movie_processing_check_interval_minutes"
                        type="number"
                        min="1"
                        max="120"
                        class="mt-1 block w-full border border-input rounded-md shadow-sm bg-background text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-ring"
                      />
                    </div>
                    <div>
                      <label class="block text-sm font-medium text-foreground">Movie Queue Max Size</label>
                      <input
                        v-model.number="config.movie_queue_maxsize"
                        type="number"
                        min="10"
                        max="1000"
                        class="mt-1 block w-full border border-input rounded-md shadow-sm bg-background text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-ring"
                      />
                    </div>
                    <div>
                      <label class="block text-sm font-medium text-foreground">TV Queue Max Size</label>
                      <input
                        v-model.number="config.tv_queue_maxsize"
                        type="number"
                        min="10"
                        max="1000"
                        class="mt-1 block w-full border border-input rounded-md shadow-sm bg-background text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-ring"
                      />
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- Failed Items Configuration -->
              <div class="space-y-4 pt-4 border-t border-border">
                <h4 class="text-base font-medium text-foreground">Failed Items Retry</h4>
                <div class="space-y-3">
                  <div class="flex items-center">
                    <input
                      v-model="config.enable_failed_item_retry"
                      type="checkbox"
                      class="h-4 w-4 text-primary focus:ring-ring border-input rounded"
                    />
                    <label class="ml-2 block text-sm text-foreground">
                      Enable Failed Item Retry
                    </label>
                  </div>
                  <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <div>
                      <label class="block text-sm font-medium text-foreground">Retry Interval (minutes)</label>
                      <input
                        v-model.number="config.failed_item_retry_interval_minutes"
                        type="number"
                        min="1"
                        max="1440"
                        class="mt-1 block w-full border border-input rounded-md shadow-sm bg-background text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-ring"
                      />
                    </div>
                    <div>
                      <label class="block text-sm font-medium text-foreground">Max Retry Attempts</label>
                      <input
                        v-model.number="config.failed_item_max_retry_attempts"
                        type="number"
                        min="1"
                        max="10"
                        class="mt-1 block w-full border border-input rounded-md shadow-sm bg-background text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-ring"
                      />
                    </div>
                    <div>
                      <label class="block text-sm font-medium text-foreground">Initial Retry Delay (hours)</label>
                      <input
                        v-model.number="config.failed_item_retry_delay_hours"
                        type="number"
                        min="1"
                        max="168"
                        class="mt-1 block w-full border border-input rounded-md shadow-sm bg-background text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-ring"
                      />
                    </div>
                    <div>
                      <label class="block text-sm font-medium text-foreground">Backoff Multiplier</label>
                      <input
                        v-model.number="config.failed_item_retry_backoff_multiplier"
                        type="number"
                        min="1"
                        max="10"
                        step="0.1"
                        class="mt-1 block w-full border border-input rounded-md shadow-sm bg-background text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-ring"
                      />
                    </div>
                    <div>
                      <label class="block text-sm font-medium text-foreground">Max Retry Delay (hours)</label>
                      <input
                        v-model.number="config.failed_item_max_retry_delay_hours"
                        type="number"
                        min="1"
                        max="168"
                        class="mt-1 block w-full border border-input rounded-md shadow-sm bg-background text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-ring"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Navigation Buttons -->
          <div class="flex justify-between pt-6">
            <div class="flex items-center space-x-3">
              <!-- Start Over button (only show on DMM step when test is successful) -->
              <button
                v-if="currentStep === 0 && testResults.dmm.success"
                @click="resetDMMTest"
                class="px-4 py-2 border border-red-600 rounded-md shadow-sm text-sm font-medium text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-all duration-200 flex items-center space-x-2"
              >
                <Icon name="lucide:refresh-cw" class="w-4 h-4" />
                <span>Start Over</span>
              </button>
              
              <!-- Previous button -->
              <button
                v-if="currentStep > 0"
                @click="previousStep"
                :disabled="testing[currentStep]"
                class="px-4 py-2 border border-input rounded-md shadow-sm text-sm font-medium text-foreground bg-background hover:bg-muted focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-ring disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              
              <!-- Reset button (only show on Overseerr step when test is successful) -->
              <button
                v-if="currentStep === 1 && testResults.overseerr.success"
                @click="resetOverseerrTest"
                class="px-4 py-2 border border-red-600 rounded-md shadow-sm text-sm font-medium text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-all duration-200 flex items-center space-x-2"
              >
                <Icon name="lucide:refresh-cw" class="w-4 h-4" />
                <span>Reset</span>
              </button>
            </div>
            
            <div class="flex items-center space-x-3">
              <!-- Test & Continue button (hide when test is successful) -->
              <button
                v-if="currentStep < steps.length - 1 && !isStepSuccessful(currentStep)"
                @click="handleNextStep"
                :disabled="!canProceed || testing[currentStep] || (currentStep === 0 && !areDMMCredentialsValid)"
                class="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-primary-foreground bg-primary hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-ring disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
              >
                <Icon v-if="testing[currentStep]" name="lucide:loader-2" class="w-4 h-4 animate-spin" />
                <span>{{ testing[currentStep] ? 'Testing...' : 'Test & Continue' }}</span>
              </button>
              
              <!-- Continue to Next Step button (show when test is successful) -->
              <button
                v-if="currentStep < steps.length - 1 && isStepSuccessful(currentStep)"
                @click="handleContinueAfterSuccess"
                class="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition-all duration-200 flex items-center space-x-2"
              >
                <Icon name="lucide:arrow-right" class="w-4 h-4" />
                <span>Continue to Next Step</span>
              </button>
              
              <!-- Complete Setup button -->
              <button
                v-if="currentStep === steps.length - 1"
                @click="completeSetup"
                :disabled="!canProceed || isSaving"
                class="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {{ isSaving ? 'Saving...' : 'Complete Setup' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Backend Initializing Screen - Show after setup save completes -->
  <BackendInitializing 
    v-if="showBackendInitializing" 
    @ready="handleBackendReady" 
  />
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'

const currentStep = ref(0)
const isSaving = ref(false)
const isSkippingSetup = ref(false)
const setupSkipped = ref(false)
const envVarsAvailable = ref(false)
const testing = ref([false, false, false, false])
const showBackendInitializing = ref(false)

const steps = ref([
  { id: 'dmm', name: 'DMM Config', testStatus: null },
  { id: 'overseerr', name: 'Overseerr', testStatus: null },
  { id: 'trakt', name: 'Trakt', testStatus: null },
  { id: 'system', name: 'System', testStatus: null }
])

const testResults = ref({
  dmm: { success: false, error: null, libraryStats: null },
  overseerr: { success: false, error: null, data: null },
  trakt: { success: false, error: null, mediaData: null }
})

// Pre-compute random animation particle positions to prevent infinite re-render loops
// These are computed once and stored, preventing Math.random() from being called on every render
const generateAnimationParticles = (count) => {
  return Array.from({ length: count }, () => ({
    left: Math.random() * 100,
    top: Math.random() * 100,
    animationDelay: Math.random() * 2
  }))
}

const dmmParticles = ref(generateAnimationParticles(30))
const overseerrParticles = ref(generateAnimationParticles(25))
const traktParticles = ref(generateAnimationParticles(50))

const config = ref({
  // Real-Debrid
  rd_client_id: '',
  rd_client_secret: '',
  rd_access_token: '',
  rd_refresh_token: '',
  
  // Overseerr
  overseerr_base: '',
  overseerr_api_key: '',
  
  // Trakt
  trakt_api_key: '',
  
  // System
  headless_mode: true,
  refresh_interval_minutes: 60,
  torrent_filter_regex: '^(?!.*【.*?】)(?!.*[\\u0400-\\u04FF])(?!.*\\[esp\\]).*',
  max_movie_size: 0,
  max_episode_size: 0,
  
  // Task Configuration
  background_tasks_enabled: true,
  scheduler_enabled: true,
  token_refresh_interval_minutes: 10,
  movie_processing_check_interval_minutes: 15,
  movie_queue_maxsize: 250,
  tv_queue_maxsize: 250,
  
  // Failed Items Configuration
  enable_failed_item_retry: true,
  failed_item_retry_interval_minutes: 30,
  failed_item_max_retry_attempts: 3,
  failed_item_retry_delay_hours: 2,
  failed_item_retry_backoff_multiplier: 2,
  failed_item_max_retry_delay_hours: 24
})

// Load saved setup state on mount
onMounted(async () => {
  try {
    // Check for environment variables first - use both endpoints for reliability
    const [setupStatus, envValues] = await Promise.all([
      $fetch('/api/setup-status').catch(() => ({ success: false, data: { canSkipSetup: false } })),
      $fetch('/api/setup-env-values').catch(() => ({ success: false, allRequiredPresent: false }))
    ])
    
    console.log('Setup status check:', { setupStatus, envValues })
    
    // Show skip button if either endpoint indicates all required env vars are present
    const canSkip = (setupStatus.success && setupStatus.data?.canSkipSetup) || 
                    (envValues.success && envValues.allRequiredPresent)
    
    if (canSkip) {
      envVarsAvailable.value = true
      console.log('Environment variables detected - skip button should be visible')
    } else {
      console.log('Environment variables not fully available:', {
        setupStatusCanSkip: setupStatus.success && setupStatus.data?.canSkipSetup,
        envValuesAllPresent: envValues.success && envValues.allRequiredPresent,
        envValuesData: envValues
      })
    }
    
    // Try to load environment variables into config
    await loadConfigFromEnv()
    
    const { data: setupState } = await $fetch('/api/setup-load-state')
    if (setupState) {
      // Restore current step
      currentStep.value = setupState.currentStep || 0
      
      // Restore config (but don't overwrite env-loaded values)
      if (setupState.config) {
        // Only merge values that aren't already set from env
        Object.keys(setupState.config).forEach(key => {
          if (!config.value[key] || config.value[key] === '') {
            config.value[key] = setupState.config[key]
          }
        })
      }
      
      // Ensure default torrent_filter_regex is prefilled if not already set
      if (!config.value.torrent_filter_regex || config.value.torrent_filter_regex.trim() === '') {
        config.value.torrent_filter_regex = '^(?!.*【.*?】)(?!.*[\\u0400-\\u04FF])(?!.*\\[esp\\]).*'
      }
      
      // Restore test results for completed steps
      if (setupState.savedSteps) {
        Object.keys(setupState.savedSteps).forEach(stepKey => {
          const step = parseInt(stepKey)
          const stepData = setupState.savedSteps[step]
          
          if (stepData.testResults) {
            if (step === 0 && stepData.testResults.dmm) {
              testResults.value.dmm = stepData.testResults.dmm
              steps.value[0].testStatus = stepData.testResults.dmm.success ? 'success' : 'error'
            } else if (step === 1 && stepData.testResults.overseerr) {
              testResults.value.overseerr = stepData.testResults.overseerr
              steps.value[1].testStatus = stepData.testResults.overseerr.success ? 'success' : 'error'
            } else if (step === 2 && stepData.testResults.trakt) {
              testResults.value.trakt = stepData.testResults.trakt
              steps.value[2].testStatus = stepData.testResults.trakt.success ? 'success' : 'error'
            }
          }
        })
      }
    }
  } catch (error) {
    console.error('Error loading setup state:', error)
  }
})

const loadConfigFromEnv = async () => {
  try {
    // Get safe environment variable values
    const envData = await $fetch('/api/setup-env-values')
    
    if (envData.success && envData.safeValues) {
      // Auto-populate non-sensitive values
      const safeValues = envData.safeValues
      
      // System settings
      if (safeValues.headless_mode !== undefined) {
        config.value.headless_mode = safeValues.headless_mode
      }
      if (safeValues.refresh_interval_minutes !== undefined) {
        config.value.refresh_interval_minutes = safeValues.refresh_interval_minutes
      }
      if (safeValues.torrent_filter_regex) {
        config.value.torrent_filter_regex = safeValues.torrent_filter_regex
      }
      if (safeValues.max_movie_size !== undefined) {
        config.value.max_movie_size = safeValues.max_movie_size
      }
      if (safeValues.max_episode_size !== undefined) {
        config.value.max_episode_size = safeValues.max_episode_size
      }
      
      // Task configuration
      if (safeValues.background_tasks_enabled !== undefined) {
        config.value.background_tasks_enabled = safeValues.background_tasks_enabled
      }
      if (safeValues.scheduler_enabled !== undefined) {
        config.value.scheduler_enabled = safeValues.scheduler_enabled
      }
      if (safeValues.token_refresh_interval_minutes !== undefined) {
        config.value.token_refresh_interval_minutes = safeValues.token_refresh_interval_minutes
      }
      if (safeValues.movie_processing_check_interval_minutes !== undefined) {
        config.value.movie_processing_check_interval_minutes = safeValues.movie_processing_check_interval_minutes
      }
      if (safeValues.movie_queue_maxsize !== undefined) {
        config.value.movie_queue_maxsize = safeValues.movie_queue_maxsize
      }
      if (safeValues.tv_queue_maxsize !== undefined) {
        config.value.tv_queue_maxsize = safeValues.tv_queue_maxsize
      }
      
      // Failed items configuration
      if (safeValues.enable_failed_item_retry !== undefined) {
        config.value.enable_failed_item_retry = safeValues.enable_failed_item_retry
      }
      if (safeValues.failed_item_retry_interval_minutes !== undefined) {
        config.value.failed_item_retry_interval_minutes = safeValues.failed_item_retry_interval_minutes
      }
      if (safeValues.failed_item_max_retry_attempts !== undefined) {
        config.value.failed_item_max_retry_attempts = safeValues.failed_item_max_retry_attempts
      }
      if (safeValues.failed_item_retry_delay_hours !== undefined) {
        config.value.failed_item_retry_delay_hours = safeValues.failed_item_retry_delay_hours
      }
      if (safeValues.failed_item_retry_backoff_multiplier !== undefined) {
        config.value.failed_item_retry_backoff_multiplier = safeValues.failed_item_retry_backoff_multiplier
      }
      if (safeValues.failed_item_max_retry_delay_hours !== undefined) {
        config.value.failed_item_max_retry_delay_hours = safeValues.failed_item_max_retry_delay_hours
      }
    }
  } catch (error) {
    console.error('Error loading config from env:', error)
  }
}

const skipSetupWithEnv = async () => {
  isSkippingSetup.value = true
  
  try {
    // Call the endpoint to load from .env and save to database
    const response = await $fetch('/api/setup-load-env', {
      method: 'POST'
    })
    
    if (response.success) {
      setupSkipped.value = true
      // Redirect to dashboard after a short delay
      setTimeout(() => {
        navigateTo('/dashboard')
      }, 1500)
    } else {
      // Show a more helpful error message
      let errorMsg = response.error || response.message || 'Unknown error'
      if (response.missingBackend || response.failedKeys) {
        errorMsg = `Configuration could not be fully saved. ${errorMsg}\n\n` +
          `Please ensure:\n` +
          `1. Python 3 is installed and available\n` +
          `2. SEERRBRIDGE_MASTER_KEY is set in your .env file\n` +
          `3. The SeerrBridge backend service is running (or will encrypt values when it starts)`
      }
      alert('Failed to load configuration from environment variables:\n\n' + errorMsg)
    }
  } catch (error) {
    console.error('Error skipping setup with env vars:', error)
    const errorMessage = error instanceof Error ? error.message : 'Unknown error'
    alert('Error loading configuration from environment variables: ' + errorMessage)
  } finally {
    isSkippingSetup.value = false
  }
}

// Computed property to check if DMM credentials are valid (read-only, doesn't mutate state)
// This is used in template bindings and must not mutate reactive state to prevent infinite loops
const areDMMCredentialsValid = computed(() => {
  // Extract token value (can be JSON object or plain string)
  let token = config.value.rd_access_token?.trim() || ''
  try {
    const parsed = JSON.parse(token)
    if (typeof parsed === 'object' && parsed.value) {
      token = parsed.value.trim()
    }
  } catch {
    // Not JSON, use as-is
    token = token.replace(/^["']|["']$/g, '')
  }
  
  const clientId = (config.value.rd_client_id?.trim() || '').replace(/^["']|["']$/g, '')
  const clientSecret = (config.value.rd_client_secret?.trim() || '').replace(/^["']|["']$/g, '')
  const refreshToken = (config.value.rd_refresh_token?.trim() || '').replace(/^["']|["']$/g, '')
  
  // Basic checks: all fields must be present and have minimum length
  // This is a lightweight check that doesn't mutate state
  return (
    token.length >= 20 &&
    clientId.length >= 8 &&
    clientSecret.length >= 16 &&
    refreshToken.length >= 32
  )
})

const canProceed = computed(() => {
  switch (currentStep.value) {
    case 0: // DMM
      // Allow proceed if credentials are filled OR if test passed
      return (config.value.rd_client_id && config.value.rd_client_secret && 
             config.value.rd_access_token && config.value.rd_refresh_token) ||
             testResults.value.dmm.success
    case 1: // Overseerr
      return (config.value.overseerr_base && config.value.overseerr_api_key) ||
             testResults.value.overseerr.success
    case 2: // Trakt
      return config.value.trakt_api_key || testResults.value.trakt.success
    case 3: // System
      return true
    default:
      return false
  }
})

const handleNextStep = async () => {
  if (!canProceed.value) return
  
  // Test the current step before proceeding
  await testCurrentStep()
  
  // Only proceed if test passed
  if (steps.value[currentStep.value].testStatus === 'success') {
    // Trigger confetti for successful tests and don't auto-advance
    if (currentStep.value === 0 && testResults.value.dmm.success) {
      triggerConfetti()
      // Don't auto-advance, let user click continue
      return
    } else if (currentStep.value === 1 && testResults.value.overseerr.success) {
      triggerConfetti()
      // Don't auto-advance, let user click continue
      return
    } else if (currentStep.value === 2 && testResults.value.trakt.success) {
      triggerConfetti()
      // Don't auto-advance, let user click continue
      return
    }
    
    currentStep.value++
  }
}

const isStepSuccessful = (step) => {
  switch (step) {
    case 0: // DMM
      return testResults.value.dmm.success
    case 1: // Overseerr
      return testResults.value.overseerr.success
    case 2: // Trakt
      return testResults.value.trakt.success
    default:
      return false
  }
}

const handleContinueAfterSuccess = async () => {
  if (currentStep.value < steps.value.length - 1) {
    // Save progress before moving to next step
    await saveStepProgress(currentStep.value)
    currentStep.value++
  }
}

const saveStepProgress = async (step) => {
  try {
    await $fetch('/api/setup-save-step', {
      method: 'POST',
      body: {
        step,
        config: config.value,
        testResults: testResults.value
      }
    })
  } catch (error) {
    console.error('Error saving step progress:', error)
  }
}

const testCurrentStep = async () => {
  testing.value[currentStep.value] = true
  steps.value[currentStep.value].testStatus = 'testing'
  
  try {
    switch (currentStep.value) {
      case 0: // DMM
        await testDMM()
        break
      case 1: // Overseerr
        await testOverseerr()
        break
      case 2: // Trakt
        await testTrakt()
        break
    }
  } catch (error) {
    console.error('Test failed:', error)
  } finally {
    testing.value[currentStep.value] = false
  }
}

const dmmProgress = ref([])
const dmmTestId = ref(null)
const progressContainerRef = ref(null)

// DMM validation errors
const dmmValidationErrors = ref({
  rd_access_token: '',
  rd_client_id: '',
  rd_client_secret: '',
  rd_refresh_token: ''
})

// DMM validation functions
const validateAccessToken = (token) => {
  if (!token || token.trim() === '') {
    return 'Access Token is required'
  }
  
  // Try to parse as JSON first (can be {"value": "...", "expiry": ...})
  try {
    const parsed = JSON.parse(token)
    if (typeof parsed === 'object' && parsed.value) {
      // Valid JSON format with value field
      if (!parsed.value || parsed.value.trim() === '') {
        return 'Access Token value is empty'
      }
      // Validate the token value format (alphanumeric, typically long)
      if (!/^[A-Za-z0-9]{20,}$/.test(parsed.value.trim())) {
        return 'Access Token value format is invalid (should be alphanumeric, at least 20 characters)'
      }
      return ''
    }
  } catch {
    // Not JSON, treat as plain string
  }
  
  // Validate as plain string token
  const cleanToken = token.trim().replace(/^["']|["']$/g, '') // Remove surrounding quotes if present
  if (!/^[A-Za-z0-9]{20,}$/.test(cleanToken)) {
    return 'Access Token format is invalid (should be alphanumeric, at least 20 characters)'
  }
  
  return ''
}

const validateClientId = (clientId) => {
  if (!clientId || clientId.trim() === '') {
    return 'Client ID is required'
  }
  
  // Remove surrounding quotes if present
  const cleanId = clientId.trim().replace(/^["']|["']$/g, '')
  
  // Client ID should be alphanumeric, typically shorter
  if (!/^[A-Za-z0-9]{8,}$/.test(cleanId)) {
    return 'Client ID format is invalid (should be alphanumeric, at least 8 characters)'
  }
  
  return ''
}

const validateClientSecret = (clientSecret) => {
  if (!clientSecret || clientSecret.trim() === '') {
    return 'Client Secret is required'
  }
  
  // Remove surrounding quotes if present
  const cleanSecret = clientSecret.trim().replace(/^["']|["']$/g, '')
  
  // Client Secret should be alphanumeric/hexadecimal, typically longer
  if (!/^[A-Za-z0-9]{16,}$/.test(cleanSecret)) {
    return 'Client Secret format is invalid (should be alphanumeric, at least 16 characters)'
  }
  
  return ''
}

const validateRefreshToken = (refreshToken) => {
  if (!refreshToken || refreshToken.trim() === '') {
    return 'Refresh Token is required'
  }
  
  // Remove surrounding quotes if present
  const cleanToken = refreshToken.trim().replace(/^["']|["']$/g, '')
  
  // Refresh Token should be alphanumeric, typically very long
  if (!/^[A-Za-z0-9]{32,}$/.test(cleanToken)) {
    return 'Refresh Token format is invalid (should be alphanumeric, at least 32 characters)'
  }
  
  return ''
}

const validateDMMCredentials = () => {
  // Clear previous errors
  dmmValidationErrors.value = {
    rd_access_token: '',
    rd_client_id: '',
    rd_client_secret: '',
    rd_refresh_token: ''
  }
  
  // Validate each field
  dmmValidationErrors.value.rd_access_token = validateAccessToken(config.value.rd_access_token)
  dmmValidationErrors.value.rd_client_id = validateClientId(config.value.rd_client_id)
  dmmValidationErrors.value.rd_client_secret = validateClientSecret(config.value.rd_client_secret)
  dmmValidationErrors.value.rd_refresh_token = validateRefreshToken(config.value.rd_refresh_token)
  
  // Check if any errors exist
  return !Object.values(dmmValidationErrors.value).some(error => error !== '')
}

// Helper function to clean/parse tokens
const cleanToken = (token) => {
  if (!token) return ''
  
  // Try to parse as JSON first (for access token with {"value": "...", "expiry": ...})
  try {
    const parsed = JSON.parse(token)
    if (typeof parsed === 'object' && parsed.value) {
      return parsed.value.trim()
    }
  } catch {
    // Not JSON, treat as plain string
  }
  
  // Remove surrounding quotes and trim
  return token.trim().replace(/^["']|["']$/g, '')
}

const resetDMMTest = () => {
  // Reset test results
  testResults.value.dmm = {
    success: false,
    error: null,
    libraryStats: null
  }
  steps.value[0].testStatus = null
  
  // Clear credential values
  config.value.rd_access_token = ''
  config.value.rd_client_id = ''
  config.value.rd_client_secret = ''
  config.value.rd_refresh_token = ''
  
  // Clear validation errors
  dmmValidationErrors.value = {
    rd_access_token: '',
    rd_client_id: '',
    rd_client_secret: '',
    rd_refresh_token: ''
  }
  
  // Clear progress
  dmmProgress.value = []
  dmmTestId.value = null
  
  // Clear saved progress
  saveStepProgress(0)
}

const resetOverseerrTest = () => {
  // Reset test results
  testResults.value.overseerr = {
    success: false,
    error: null,
    data: null
  }
  steps.value[1].testStatus = null
  
  // Clear credential values
  config.value.overseerr_base = ''
  config.value.overseerr_api_key = ''
  
  // Clear saved progress
  saveStepProgress(1)
}

const testDMM = async () => {
  // Validate credentials before testing
  if (!validateDMMCredentials()) {
    // Validation failed, don't proceed with test
    return
  }
  
  // Reset progress
  dmmProgress.value = []
  dmmTestId.value = `dmm_test_${Date.now()}`
  
  try {
    // Clean and parse tokens before sending to backend
    const accessToken = cleanToken(config.value.rd_access_token)
    const clientId = cleanToken(config.value.rd_client_id)
    const clientSecret = cleanToken(config.value.rd_client_secret)
    const refreshToken = cleanToken(config.value.rd_refresh_token)
    
    // Start the test (non-blocking)
    const testPromise = $fetch('/api/setup-test-dmm', {
      method: 'POST',
      body: {
        rd_client_id: clientId,
        rd_client_secret: clientSecret,
        rd_access_token: accessToken,
        rd_refresh_token: refreshToken,
        test_id: dmmTestId.value
      }
    })
    
    // Poll for progress updates
    const progressInterval = setInterval(async () => {
      try {
        const progressResponse = await $fetch(`/api/setup-test-dmm-progress?test_id=${dmmTestId.value}`)
        if (progressResponse.success && progressResponse.progress) {
          const previousLength = dmmProgress.value.length
          dmmProgress.value = progressResponse.progress
          
          // Auto-scroll to bottom when new messages arrive
          if (progressResponse.progress.length > previousLength) {
            await nextTick()
            if (progressContainerRef.value) {
              progressContainerRef.value.scrollTop = progressContainerRef.value.scrollHeight
            }
          }
          
          // Stop polling if test is complete
          if (progressResponse.is_complete) {
            clearInterval(progressInterval)
          }
        }
      } catch (error) {
        console.error('Error fetching progress:', error)
      }
    }, 500) // Poll every 500ms
    
    // Wait for test to complete
    const response = await testPromise
    
    // Clear polling interval
    clearInterval(progressInterval)
    
    // Get final progress update
    try {
      const finalProgress = await $fetch(`/api/setup-test-dmm-progress?test_id=${dmmTestId.value}`)
      if (finalProgress.success && finalProgress.progress) {
        dmmProgress.value = finalProgress.progress
      }
    } catch (error) {
      console.error('Error fetching final progress:', error)
    }
    
    if (response.success) {
      testResults.value.dmm = {
        success: true,
        error: null,
        libraryStats: response.data
      }
      steps.value[0].testStatus = 'success'
      // Save progress after successful test
      await saveStepProgress(0)
    } else {
      testResults.value.dmm = {
        success: false,
        error: response.error || 'Connection failed',
        libraryStats: null
      }
      steps.value[0].testStatus = 'error'
    }
  } catch (error) {
    testResults.value.dmm = {
      success: false,
      error: error.message || 'Failed to test DMM connection',
      libraryStats: null
    }
    steps.value[0].testStatus = 'error'
  } finally {
    // Clean up test_id after a delay
    setTimeout(() => {
      dmmTestId.value = null
      dmmProgress.value = []
    }, 5000)
  }
}

const testOverseerr = async () => {
  try {
    const response = await $fetch('/api/setup-test-overseerr', {
      method: 'POST',
      body: {
        overseerr_base: config.value.overseerr_base,
        overseerr_api_key: config.value.overseerr_api_key
      }
    })
    
    if (response.success) {
      testResults.value.overseerr = {
        success: true,
        error: null,
        data: response.data
      }
      steps.value[1].testStatus = 'success'
      // Save progress after successful test
      await saveStepProgress(1)
    } else {
      testResults.value.overseerr = {
        success: false,
        error: response.error || 'Connection failed',
        data: null
      }
      steps.value[1].testStatus = 'error'
    }
  } catch (error) {
    testResults.value.overseerr = {
      success: false,
      error: error.message || 'Failed to test Overseerr connection',
      data: null
    }
    steps.value[1].testStatus = 'error'
  }
}

const testTrakt = async () => {
  try {
    console.log('Starting Trakt test...')
    console.log('Overseerr test results:', testResults.value.overseerr)
    
    // Use the Overseerr request data to get TMDB ID for Trakt test
    let testData = null
    if (testResults.value.overseerr.success && testResults.value.overseerr.data?.first_request?.tmdbId) {
      const firstRequest = testResults.value.overseerr.data.first_request
      const tmdbId = firstRequest.tmdbId
      const mediaType = firstRequest.mediaType || firstRequest.type || 'movie'
      
      console.log('Using Overseerr data for Trakt test:', { tmdbId, mediaType })
      
      testData = await $fetch('/api/setup-test-trakt', {
        method: 'POST',
        body: {
          trakt_api_key: config.value.trakt_api_key,
          tmdb_id: tmdbId,
          media_type: mediaType
        }
      })
    } else {
      console.log('No Overseerr data available, testing Trakt API access only')
      // Just test API access without specific media
      testData = await $fetch('/api/setup-test-trakt', {
        method: 'POST',
        body: {
          trakt_api_key: config.value.trakt_api_key
        }
      })
    }
    
    console.log('Trakt test response:', testData)
    
    if (testData.success) {
      testResults.value.trakt = {
        success: true,
        error: null,
        mediaData: testData.data
      }
      steps.value[2].testStatus = 'success'
      
      // Save progress after successful test
      await saveStepProgress(2)
      
      // Trigger confetti animation
      triggerConfetti()
    } else {
      testResults.value.trakt = {
        success: false,
        error: testData.error || 'Connection failed',
        mediaData: null
      }
      steps.value[2].testStatus = 'error'
    }
  } catch (error) {
    console.error('Trakt test error:', error)
    testResults.value.trakt = {
      success: false,
      error: error.message || 'Failed to test Trakt connection',
      mediaData: null
    }
    steps.value[2].testStatus = 'error'
  }
}

const triggerConfetti = () => {
  // Create confetti effect using DOM manipulation
  for (let i = 0; i < 50; i++) {
    setTimeout(() => {
      const confetti = document.createElement('div')
      confetti.style.position = 'fixed'
      confetti.style.left = Math.random() * window.innerWidth + 'px'
      confetti.style.top = '-10px'
      confetti.style.width = '10px'
      confetti.style.height = '10px'
      confetti.style.backgroundColor = ['#f59e0b', '#ef4444', '#8b5cf6', '#10b981', '#3b82f6'][Math.floor(Math.random() * 5)]
      confetti.style.borderRadius = '50%'
      confetti.style.zIndex = '9999'
      confetti.style.pointerEvents = 'none'
      confetti.style.transition = 'transform 3s ease-out'
      confetti.style.transform = `translateY(${window.innerHeight + 100}px) rotate(${Math.random() * 720}deg)`
      document.body.appendChild(confetti)
      
      setTimeout(() => confetti.remove(), 3000)
    }, i * 50)
  }
}

const previousStep = () => {
  if (currentStep.value > 0) {
    currentStep.value--
  }
}

const completeSetup = async () => {
  if (!canProceed.value) return
  
  isSaving.value = true
  
  try {
    // Convert config to the format expected by the API
    const configs = Object.entries(config.value).map(([key, value]) => ({
      config_key: key,
      config_value: value,
      config_type: typeof value === 'boolean' ? 'bool' : 
                   typeof value === 'number' ? 'int' : 'string',
      description: getConfigDescription(key)
    }))
    
    // Add setup completion flags
    configs.push(
      {
        config_key: 'onboarding_completed',
        config_value: true,
        config_type: 'bool',
        description: 'Setup completed'
      },
      {
        config_key: 'setup_required',
        config_value: false,
        config_type: 'bool',
        description: 'Setup no longer required'
      }
    )
    
    const response = await $fetch('/api/config', {
      method: 'POST',
      body: { configs }
    })
    
    if (response.success) {
      // Show success message
      console.log('Setup completed successfully!')
      
      // Show backend initializing screen immediately after successful save
      // This will hide the setup wizard form and show the BackendInitializing component
      showBackendInitializing.value = true
      isSaving.value = false
    } else {
      console.error('Setup failed:', response.error)
      alert('Setup failed: ' + (response.error || 'Unknown error'))
    }
  } catch (error) {
    console.error('Error completing setup:', error)
    alert('Error completing setup: ' + error.message)
  } finally {
    isSaving.value = false
  }
}

const getConfigDescription = (key) => {
  const descriptions = {
    rd_client_id: 'Real-Debrid Client ID',
    rd_client_secret: 'Real-Debrid Client Secret',
    rd_access_token: 'Real-Debrid Access Token',
    rd_refresh_token: 'Real-Debrid Refresh Token',
    overseerr_base: 'Overseerr Base URL',
    overseerr_api_key: 'Overseerr API Key',
    trakt_api_key: 'Trakt API Key',
    headless_mode: 'Run browser in headless mode',
    refresh_interval_minutes: 'Background task refresh interval in minutes',
    torrent_filter_regex: 'Torrent filter regex pattern'
  }
  return descriptions[key] || `Configuration for ${key}`
}

onMounted(() => {
  loadExistingConfig()
})

const loadExistingConfig = async () => {
  try {
    const response = await $fetch('/api/config')
    if (response.success) {
      const existingConfigs = response.data
      const configMap = {}
      
      existingConfigs.forEach(config => {
        if (config.config_value !== '[ENCRYPTED]' && config.config_value) {
          configMap[config.config_key] = config.config_value
        }
      })
      
      // Merge with existing config, but preserve default torrent_filter_regex if not set
      config.value = { ...config.value, ...configMap }
      
      // Ensure default torrent_filter_regex is prefilled if not already set
      if (!config.value.torrent_filter_regex || config.value.torrent_filter_regex.trim() === '') {
        config.value.torrent_filter_regex = '^(?!.*【.*?】)(?!.*[\\u0400-\\u04FF])(?!.*\\[esp\\]).*'
      }
    }
  } catch (error) {
    console.error('Error loading existing config:', error)
  }
}

const handleBackendReady = () => {
  // Backend is ready, navigate to dashboard
  navigateTo('/dashboard')
}
</script>
