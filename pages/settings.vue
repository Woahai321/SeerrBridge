<template>
  <div class="container mx-auto px-3 sm:px-4 py-4 sm:py-6 lg:py-8">
    <!-- Breadcrumb -->
    <nav class="flex items-center space-x-1 sm:space-x-2 text-xs sm:text-sm text-muted-foreground mb-4 sm:mb-6 overflow-x-auto -mx-3 sm:mx-0 px-3 sm:px-0">
      <NuxtLink to="/" class="hover:text-foreground transition-colors whitespace-nowrap">Home</NuxtLink>
      <AppIcon icon="lucide:chevron-right" size="12" class="sm:w-4 sm:h-4 flex-shrink-0" />
      <NuxtLink to="/dashboard" class="hover:text-foreground transition-colors whitespace-nowrap">Dashboard</NuxtLink>
      <AppIcon icon="lucide:chevron-right" size="12" class="sm:w-4 sm:h-4 flex-shrink-0" />
      <span class="text-foreground whitespace-nowrap">Settings</span>
    </nav>

    <div class="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3 sm:gap-4 mb-6 sm:mb-8">
      <h1 class="text-2xl sm:text-3xl font-bold text-foreground flex items-center">
        <AppIcon icon="lucide:settings" size="24" class="sm:w-7 sm:h-7 mr-2 sm:mr-3 text-primary" />
        Settings
      </h1>
      
      <div class="flex items-center gap-2 sm:gap-3">
        <!-- Theme Selector -->
        <div class="relative">
          <button 
            @click="showThemeMenu = !showThemeMenu"
            class="glass-button flex items-center px-3 sm:px-4 py-1.5 sm:py-2 shadow-sm text-xs sm:text-sm"
            :title="`Current theme: ${getThemeName(colorMode.value)}`"
          >
            <AppIcon 
              :icon="getThemeIcon(colorMode.value)" 
              size="14" 
              class="sm:w-4 sm:h-4 mr-1.5 sm:mr-2" 
            />
            <span class="hidden sm:inline">{{ getThemeName(colorMode.value) }}</span>
            <span class="sm:hidden">{{ getThemeName(colorMode.value).charAt(0) }}</span>
            <AppIcon 
              icon="lucide:chevron-down" 
              size="12" 
              class="ml-1.5 sm:ml-2" 
            />
          </button>
          
          <!-- Theme Dropdown Menu -->
          <div 
            v-if="showThemeMenu"
            ref="themeMenuRef"
            class="absolute right-0 mt-2 w-48 glass-card p-2 z-50 shadow-lg"
          >
            <button
              v-for="theme in themes"
              :key="theme.value"
              @click="selectTheme(theme.value)"
              class="w-full flex items-center px-3 py-2 rounded-lg hover:bg-muted/50 transition-colors text-left"
              :class="{ 'bg-primary/20 text-primary': colorMode.value === theme.value }"
            >
              <AppIcon 
                :icon="theme.icon" 
                size="16" 
                class="mr-2" 
              />
              <span class="text-sm font-medium">{{ theme.name }}</span>
              <AppIcon 
                v-if="colorMode.value === theme.value"
                icon="lucide:check" 
                size="16" 
                class="ml-auto" 
              />
            </button>
          </div>
        </div>
        
        <button 
          @click="saveAllSettings"
          :disabled="pending"
          class="glass-button flex items-center px-3 sm:px-4 py-1.5 sm:py-2 shadow-sm text-xs sm:text-sm"
        >
          <AppIcon icon="lucide:save" size="14" class="sm:w-4 sm:h-4 mr-1.5 sm:mr-2" />
          <span class="hidden sm:inline">Save All Changes</span>
          <span class="sm:hidden">Save All</span>
        </button>
      </div>
    </div>

    <!-- Setup Status Banner -->
    <div v-if="!setupCompleted" class="glass-card p-4 sm:p-6 mb-6 sm:mb-8 border-l-4 border-l-orange-500">
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-4">
        <div class="flex items-start sm:items-center gap-2 sm:gap-3 min-w-0 flex-1">
          <AppIcon icon="lucide:alert-triangle" size="18" class="sm:w-5 sm:h-5 mr-1 sm:mr-3 text-orange-500 flex-shrink-0 mt-0.5 sm:mt-0" />
          <div class="min-w-0 flex-1">
            <h3 class="text-base sm:text-lg font-semibold text-foreground">Setup Incomplete</h3>
            <p class="text-xs sm:text-sm text-muted-foreground">Complete the initial setup to configure your SeerrBridge instance.</p>
          </div>
        </div>
        <NuxtLink 
          to="/setup"
          class="glass-button flex items-center justify-center px-3 sm:px-4 py-2 text-xs sm:text-sm whitespace-nowrap flex-shrink-0"
        >
          <AppIcon icon="lucide:arrow-right" size="14" class="sm:w-4 sm:h-4 mr-1.5 sm:mr-2" />
          Complete Setup
        </NuxtLink>
      </div>
    </div>

    <div class="grid grid-cols-1 xl:grid-cols-2 gap-4 sm:gap-6 lg:gap-8 animate-fade-in">
      <!-- API Credentials Section -->
      <div class="glass-card p-4 sm:p-6 hover:shadow-lg transition-all duration-300">
        <h2 class="text-lg sm:text-xl font-semibold mb-4 sm:mb-6 flex items-center">
          <AppIcon icon="lucide:key" size="18" class="sm:w-5 sm:h-5 mr-2 text-primary" />
          API Credentials
        </h2>
        <div class="space-y-6 sm:space-y-8 lg:space-y-10">


          <!-- Real-Debrid Configuration -->
          <div class="space-y-3 sm:space-y-4">
            <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 sm:gap-3">
              <h3 class="text-base sm:text-lg font-medium text-foreground">Real-Debrid</h3>
              <div class="flex items-center space-x-2 sm:space-x-3">
                <div class="flex items-center space-x-1.5 sm:space-x-2">
                  <div :class="[
                    'w-1.5 h-1.5 sm:w-2 sm:h-2 rounded-full',
                    configStatus.rd_client_id && configStatus.rd_client_secret && configStatus.rd_access_token && configStatus.rd_refresh_token 
                      ? 'bg-green-500' 
                      : 'bg-red-500'
                  ]"></div>
                  <span class="text-[10px] sm:text-xs text-muted-foreground whitespace-nowrap">
                    {{ configStatus.rd_client_id && configStatus.rd_client_secret && configStatus.rd_access_token && configStatus.rd_refresh_token ? 'Configured' : 'Not Configured' }}
                  </span>
                </div>
                <button 
                  @click="saveSection('realdebrid')"
                  :disabled="pendingSections.realdebrid || !hasSectionChanges('realdebrid')"
                  :class="[
                    'px-2 sm:px-3 py-1 text-[10px] sm:text-xs rounded transition-colors flex items-center gap-1',
                    hasSectionChanges('realdebrid') 
                      ? 'bg-primary text-primary-foreground hover:bg-primary/90' 
                      : 'bg-muted text-muted-foreground cursor-not-allowed'
                  ]"
                >
                  <AppIcon 
                    :icon="pendingSections.realdebrid ? 'lucide:loader-2' : 'lucide:save'" 
                    size="10" 
                    class="sm:w-3 sm:h-3"
                    :class="{ 'animate-spin': pendingSections.realdebrid }"
                  />
                  {{ pendingSections.realdebrid ? 'Saving...' : 'Save' }}
                </button>
              </div>
            </div>
            
            <div class="grid grid-cols-1 gap-3 sm:gap-4">
              <div>
                <label class="block text-xs sm:text-sm font-medium text-foreground mb-1.5 sm:mb-2">Client ID</label>
                <input
                  v-model="config.rd_client_id"
                  type="text"
                  :placeholder="configStatus.rd_client_id ? 'Client ID is configured (enter new value to update)' : 'Enter your Real-Debrid Client ID'"
                  :class="[
                    'w-full px-3 py-2 text-xs sm:text-sm glass-input rounded-lg',
                    config.rd_client_id && config.rd_client_id.includes('*') ? 'font-mono' : ''
                  ]"
                />
              </div>
              <div>
                <label class="block text-xs sm:text-sm font-medium text-foreground mb-1.5 sm:mb-2">Client Secret</label>
                <input
                  v-model="config.rd_client_secret"
                  type="text"
                  :placeholder="configStatus.rd_client_secret ? 'Client Secret is configured (enter new value to update)' : 'Enter your Real-Debrid Client Secret'"
                  :class="[
                    'w-full px-3 py-2 text-xs sm:text-sm glass-input rounded-lg',
                    config.rd_client_secret && config.rd_client_secret.includes('*') ? 'font-mono' : ''
                  ]"
                />
              </div>
              <div>
                <label class="block text-xs sm:text-sm font-medium text-foreground mb-1.5 sm:mb-2">Access Token</label>
                <input
                  v-model="config.rd_access_token"
                  type="text"
                  :placeholder="configStatus.rd_access_token ? 'Access Token is configured (enter new value to update)' : 'Enter your Real-Debrid Access Token'"
                  :class="[
                    'w-full px-3 py-2 text-xs sm:text-sm glass-input rounded-lg',
                    config.rd_access_token && config.rd_access_token.includes('*') ? 'font-mono' : ''
                  ]"
                />
              </div>
              <div>
                <label class="block text-xs sm:text-sm font-medium text-foreground mb-1.5 sm:mb-2">Refresh Token</label>
                <input
                  v-model="config.rd_refresh_token"
                  type="text"
                  :placeholder="configStatus.rd_refresh_token ? 'Refresh Token is configured (enter new value to update)' : 'Enter your Real-Debrid Refresh Token'"
                  :class="[
                    'w-full px-3 py-2 text-xs sm:text-sm glass-input rounded-lg',
                    config.rd_refresh_token && config.rd_refresh_token.includes('*') ? 'font-mono' : ''
                  ]"
                />
              </div>
            </div>
          </div>

          <!-- Overseerr Configuration -->
          <div class="space-y-3 sm:space-y-4 pt-3 sm:pt-4 border-t border-border">
            <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 sm:gap-3">
              <h3 class="text-base sm:text-lg font-medium text-foreground">Overseerr</h3>
              <div class="flex items-center space-x-2 sm:space-x-3">
                <div class="flex items-center space-x-1.5 sm:space-x-2">
                  <div :class="[
                    'w-1.5 h-1.5 sm:w-2 sm:h-2 rounded-full',
                    configStatus.overseerr_base && configStatus.overseerr_api_key 
                      ? 'bg-green-500' 
                      : 'bg-red-500'
                  ]"></div>
                  <span class="text-[10px] sm:text-xs text-muted-foreground whitespace-nowrap">
                    {{ configStatus.overseerr_base && configStatus.overseerr_api_key ? 'Configured' : 'Not Configured' }}
                  </span>
                </div>
                <button 
                  @click="saveSection('overseerr')"
                  :disabled="pendingSections.overseerr || !hasSectionChanges('overseerr')"
                  :class="[
                    'px-2 sm:px-3 py-1 text-[10px] sm:text-xs rounded transition-colors flex items-center gap-1',
                    hasSectionChanges('overseerr') 
                      ? 'bg-primary text-primary-foreground hover:bg-primary/90' 
                      : 'bg-muted text-muted-foreground cursor-not-allowed'
                  ]"
                >
                  <AppIcon 
                    :icon="pendingSections.overseerr ? 'lucide:loader-2' : 'lucide:save'" 
                    size="10" 
                    class="sm:w-3 sm:h-3"
                    :class="{ 'animate-spin': pendingSections.overseerr }"
                  />
                  {{ pendingSections.overseerr ? 'Saving...' : 'Save' }}
                </button>
              </div>
            </div>
            
            <div class="space-y-3 sm:space-y-4">
              <div>
                <label class="block text-xs sm:text-sm font-medium text-foreground mb-1.5 sm:mb-2">Base URL</label>
                <input
                  v-model="config.overseerr_base"
                  type="url"
                  :placeholder="configStatus.overseerr_base ? 'Overseerr URL is configured' : 'https://your-overseerr-instance.com'"
                  :class="[
                    'w-full px-3 py-2 text-xs sm:text-sm glass-input rounded-lg',
                    config.overseerr_base && config.overseerr_base.includes('*') ? 'font-mono' : ''
                  ]"
                />
              </div>
              <div>
                <label class="block text-xs sm:text-sm font-medium text-foreground mb-1.5 sm:mb-2">API Key</label>
                <input
                  v-model="config.overseerr_api_key"
                  type="text"
                  :placeholder="configStatus.overseerr_api_key ? 'API Key is configured' : 'Enter your Overseerr API Key'"
                  :class="[
                    'w-full px-3 py-2 text-xs sm:text-sm glass-input rounded-lg',
                    config.overseerr_api_key && config.overseerr_api_key.includes('*') ? 'font-mono' : ''
                  ]"
                />
              </div>
            </div>
          </div>

          <!-- Trakt Configuration -->
          <div class="space-y-3 sm:space-y-4 pt-3 sm:pt-4 border-t border-border">
            <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 sm:gap-3">
              <h3 class="text-base sm:text-lg font-medium text-foreground">Trakt</h3>
              <div class="flex items-center space-x-2 sm:space-x-3">
                <div class="flex items-center space-x-1.5 sm:space-x-2">
                  <div :class="[
                    'w-1.5 h-1.5 sm:w-2 sm:h-2 rounded-full',
                    configStatus.trakt_api_key ? 'bg-green-500' : 'bg-red-500'
                  ]"></div>
                  <span class="text-[10px] sm:text-xs text-muted-foreground whitespace-nowrap">
                    {{ configStatus.trakt_api_key ? 'Configured' : 'Not Configured' }}
                  </span>
                </div>
                <button 
                  @click="saveSection('trakt')"
                  :disabled="pendingSections.trakt || !hasSectionChanges('trakt')"
                  :class="[
                    'px-2 sm:px-3 py-1 text-[10px] sm:text-xs rounded transition-colors flex items-center gap-1',
                    hasSectionChanges('trakt') 
                      ? 'bg-primary text-primary-foreground hover:bg-primary/90' 
                      : 'bg-muted text-muted-foreground cursor-not-allowed'
                  ]"
                >
                  <AppIcon 
                    :icon="pendingSections.trakt ? 'lucide:loader-2' : 'lucide:save'" 
                    size="10" 
                    class="sm:w-3 sm:h-3"
                    :class="{ 'animate-spin': pendingSections.trakt }"
                  />
                  {{ pendingSections.trakt ? 'Saving...' : 'Save' }}
                </button>
              </div>
            </div>
            
            <div>
              <label class="block text-xs sm:text-sm font-medium text-foreground mb-1.5 sm:mb-2">API Key</label>
              <input
                v-model="config.trakt_api_key"
                type="text"
                :placeholder="configStatus.trakt_api_key ? 'Trakt API Key is configured' : 'Enter your Trakt API Key'"
                :class="[
                  'w-full px-3 py-2 text-xs sm:text-sm glass-input rounded-lg',
                  config.trakt_api_key && config.trakt_api_key.includes('*') ? 'font-mono' : ''
                ]"
              />
              <p class="text-[10px] sm:text-xs text-muted-foreground mt-1">
                Get your API key from <a href="https://trakt.tv/oauth/applications" target="_blank" class="text-primary hover:text-primary/80 underline">Trakt.tv</a>
              </p>
            </div>
          </div>
        </div>
      </div>

      <!-- System Configuration Section -->
      <div class="glass-card p-4 sm:p-6 hover:shadow-lg transition-all duration-300">
        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-4 mb-4 sm:mb-6">
          <h2 class="text-lg sm:text-xl font-semibold flex items-center">
            <AppIcon icon="lucide:cog" size="18" class="sm:w-5 sm:h-5 mr-2 text-primary" />
            System Configuration
          </h2>
          <button 
            @click="saveSection('system')"
            :disabled="pendingSections.system || !hasSectionChanges('system')"
            :class="[
              'px-2 sm:px-3 py-1 text-[10px] sm:text-xs rounded transition-colors flex items-center gap-1',
              hasSectionChanges('system') 
                ? 'bg-primary text-primary-foreground hover:bg-primary/90' 
                : 'bg-muted text-muted-foreground cursor-not-allowed'
            ]"
          >
            <AppIcon 
              :icon="pendingSections.system ? 'lucide:loader-2' : 'lucide:save'" 
              size="10" 
              class="sm:w-3 sm:h-3"
              :class="{ 'animate-spin': pendingSections.system }"
            />
            {{ pendingSections.system ? 'Saving...' : 'Save' }}
          </button>
        </div>
        
        <div class="space-y-4 sm:space-y-6">
          <!-- General Settings -->
          <div class="space-y-3 sm:space-y-4">
            <h3 class="text-base sm:text-lg font-medium text-foreground">General Settings</h3>
            
            <div class="flex items-center justify-between p-3 sm:p-4 bg-muted/50 rounded-lg">
              <div class="min-w-0 flex-1 pr-3">
                <label class="text-xs sm:text-sm font-medium text-foreground block">Headless Mode</label>
                <p class="text-[10px] sm:text-xs text-muted-foreground">Run browser in headless mode (recommended for servers)</p>
              </div>
              <div class="flex items-center space-x-2 flex-shrink-0">
                <input
                  v-model="config.headless_mode"
                  type="checkbox"
                  class="w-4 h-4 text-primary bg-background border-border rounded focus:ring-primary"
                />
              </div>
            </div>
            
            <div>
              <label class="block text-xs sm:text-sm font-medium text-foreground mb-1.5 sm:mb-2">
                Refresh Interval (minutes)
              </label>
              <input
                v-model.number="config.refresh_interval_minutes"
                type="number"
                min="1"
                max="1440"
                class="w-full px-3 py-2 text-xs sm:text-sm glass-input rounded-lg"
              />
              <p class="text-[10px] sm:text-xs text-muted-foreground mt-1">How often to check for new requests</p>
            </div>
            
            <div>
              <label class="block text-xs sm:text-sm font-medium text-foreground mb-1.5 sm:mb-2">
                Torrent Filter Regex
              </label>
              <input
                v-model="config.torrent_filter_regex"
                type="text"
                placeholder="^(?!.*【.*?】)(?!.*[\u0400-\u04FF])(?!.*\[esp\]).*"
                class="w-full px-3 py-2 text-xs sm:text-sm glass-input rounded-lg font-mono"
              />
              <p class="text-[10px] sm:text-xs text-muted-foreground mt-1">Regex pattern to filter torrents (advanced users only)</p>
            </div>
          </div>

          <!-- Size Limits -->
          <div class="space-y-3 sm:space-y-4 pt-3 sm:pt-4 border-t border-border">
            <h3 class="text-base sm:text-lg font-medium text-foreground">Size Limits</h3>
            
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
              <div>
                <label class="block text-xs sm:text-sm font-medium text-foreground mb-1.5 sm:mb-2">
                  Max Movie Size
                </label>
                <select
                  v-model.number="config.max_movie_size"
                  :key="`movie-size-${config.max_movie_size}`"
                  class="w-full px-3 py-2 text-xs sm:text-sm glass-input rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
                >
                  <option 
                    v-for="option in movieSizeOptions" 
                    :key="option.value" 
                    :value="option.value"
                  >
                    {{ option.label }}
                  </option>
                </select>
                <p class="text-[10px] sm:text-xs text-muted-foreground mt-1">
                  {{ movieSizeOptions.find(opt => opt.value === config.max_movie_size)?.description || 'Select a size limit' }}
                </p>
              </div>
              
              <div>
                <label class="block text-xs sm:text-sm font-medium text-foreground mb-1.5 sm:mb-2">
                  Max Episode Size
                </label>
                <select
                  v-model.number="config.max_episode_size"
                  :key="`episode-size-${config.max_episode_size}`"
                  class="w-full px-3 py-2 text-xs sm:text-sm glass-input rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
                >
                  <option 
                    v-for="option in episodeSizeOptions" 
                    :key="option.value" 
                    :value="option.value"
                  >
                    {{ option.label }}
                  </option>
                </select>
                <p class="text-[10px] sm:text-xs text-muted-foreground mt-1">
                  {{ episodeSizeOptions.find(opt => opt.value === config.max_episode_size)?.description || 'Select a size limit' }}
                </p>
              </div>
            </div>
          </div>

          <!-- Quick Actions -->
          <div class="pt-3 sm:pt-4 border-t border-border space-y-2 sm:space-y-3">
            <h3 class="text-base sm:text-lg font-medium text-foreground">Quick Actions</h3>
            
            <div class="flex flex-col sm:flex-row gap-2 sm:gap-3">
              <button 
                @click="testConnections"
                :disabled="testingConnections"
                class="glass-button flex items-center justify-center px-3 sm:px-4 py-2 text-xs sm:text-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <AppIcon 
                  :icon="testingConnections ? 'lucide:loader-2' : 'lucide:network'" 
                  size="14" 
                  class="sm:w-4 sm:h-4 mr-1.5 sm:mr-2"
                  :class="{ 'animate-spin': testingConnections }"
                />
                {{ testingConnections ? 'Testing...' : 'Test Connections' }}
              </button>
              
              <button 
                @click="resetToDefaults"
                class="glass-button flex items-center justify-center px-3 sm:px-4 py-2 text-xs sm:text-sm"
              >
                <AppIcon icon="lucide:rotate-ccw" size="14" class="sm:w-4 sm:h-4 mr-1.5 sm:mr-2" />
                Reset to Defaults
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Background Tasks Configuration -->
      <div class="glass-card p-4 sm:p-6 hover:shadow-lg transition-all duration-300">
        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-4 mb-4 sm:mb-6">
          <h2 class="text-lg sm:text-xl font-semibold flex items-center">
            <AppIcon 
              :icon="refreshingTasks ? 'lucide:loader-2' : 'lucide:clock'" 
              size="18" 
              class="sm:w-5 sm:h-5 mr-2 text-primary"
              :class="{ 'animate-spin': refreshingTasks }"
            />
            Background Tasks
            <span v-if="refreshingTasks" class="ml-2 text-xs sm:text-sm text-muted-foreground">(Refreshing...)</span>
          </h2>
          <div class="flex items-center gap-2">
            <button 
              @click="refreshTaskConfiguration"
              :disabled="refreshingTasks"
              class="px-2 sm:px-3 py-1 text-[10px] sm:text-xs rounded transition-colors bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
            >
              <AppIcon 
                :icon="refreshingTasks ? 'lucide:loader-2' : 'lucide:refresh-cw'" 
                size="10" 
                class="sm:w-3 sm:h-3"
                :class="{ 'animate-spin': refreshingTasks }"
              />
              <span class="hidden sm:inline">{{ refreshingTasks ? 'Refreshing...' : 'Refresh Tasks' }}</span>
              <span class="sm:hidden">{{ refreshingTasks ? 'Refreshing...' : 'Refresh' }}</span>
            </button>
            <button 
              @click="saveSection('tasks')"
              :disabled="pendingSections.tasks || !hasSectionChanges('tasks')"
              :class="[
                'px-2 sm:px-3 py-1 text-[10px] sm:text-xs rounded transition-colors flex items-center gap-1',
                hasSectionChanges('tasks') 
                  ? 'bg-primary text-primary-foreground hover:bg-primary/90' 
                  : 'bg-muted text-muted-foreground cursor-not-allowed'
              ]"
            >
              <AppIcon 
                :icon="pendingSections.tasks ? 'lucide:loader-2' : 'lucide:save'" 
                size="10" 
                class="sm:w-3 sm:h-3"
                :class="{ 'animate-spin': pendingSections.tasks }"
              />
              {{ pendingSections.tasks ? 'Saving...' : 'Save' }}
            </button>
          </div>
        </div>
        
        <div class="space-y-4 sm:space-y-6">
          <!-- Master Controls -->
          <div class="space-y-3 sm:space-y-4">
            <h3 class="text-base sm:text-lg font-medium text-foreground">Master Controls</h3>
            
            <div class="flex items-center justify-between p-3 sm:p-4 bg-muted/50 rounded-lg">
              <div class="min-w-0 flex-1 pr-3">
                <label class="text-xs sm:text-sm font-medium text-foreground block">Enable Background Tasks</label>
                <p class="text-[10px] sm:text-xs text-muted-foreground">Master switch for all background processing</p>
              </div>
              <div class="flex items-center space-x-2 flex-shrink-0">
                <input
                  v-model="taskConfig.background_tasks_enabled"
                  type="checkbox"
                  class="w-4 h-4 text-primary bg-background border-border rounded focus:ring-primary"
                />
              </div>
            </div>
            
            <div class="flex items-center justify-between p-3 sm:p-4 bg-muted/50 rounded-lg">
              <div class="min-w-0 flex-1 pr-3">
                <label class="text-xs sm:text-sm font-medium text-foreground block">Enable Scheduler</label>
                <p class="text-[10px] sm:text-xs text-muted-foreground">Enable scheduled task execution</p>
              </div>
              <div class="flex items-center space-x-2 flex-shrink-0">
                <input
                  v-model="taskConfig.scheduler_enabled"
                  type="checkbox"
                  class="w-4 h-4 text-primary bg-background border-border rounded focus:ring-primary"
                />
              </div>
            </div>
            
            <div class="flex items-center justify-between p-3 sm:p-4 bg-muted/50 rounded-lg">
              <div class="min-w-0 flex-1 pr-3">
                <label class="text-xs sm:text-sm font-medium text-foreground block">Enable Queue Processing</label>
                <p class="text-[10px] sm:text-xs text-muted-foreground">Process media requests from queues</p>
              </div>
              <div class="flex items-center space-x-2 flex-shrink-0">
                <input
                  v-model="taskConfig.queue_processing_enabled"
                  type="checkbox"
                  class="w-4 h-4 text-primary bg-background border-border rounded focus:ring-primary"
                />
              </div>
            </div>
          </div>
          
          <!-- Task Settings -->
          <div class="space-y-3 sm:space-y-4 pt-3 sm:pt-4 border-t border-border">
            <h3 class="text-base sm:text-lg font-medium text-foreground">Task Settings</h3>
            
            <div class="flex items-center justify-between p-3 sm:p-4 bg-muted/50 rounded-lg">
              <div class="min-w-0 flex-1 pr-3">
                <label class="text-xs sm:text-sm font-medium text-foreground block">Automatic Background Task</label>
                <p class="text-[10px] sm:text-xs text-muted-foreground">Process movie requests automatically</p>
              </div>
              <div class="flex items-center space-x-2 flex-shrink-0">
                <input
                  v-model="taskConfig.enable_automatic_background_task"
                  type="checkbox"
                  class="w-4 h-4 text-primary bg-background border-border rounded focus:ring-primary"
                />
              </div>
            </div>
            
            <div class="flex items-center justify-between p-3 sm:p-4 bg-muted/50 rounded-lg">
              <div class="min-w-0 flex-1 pr-3">
                <label class="text-xs sm:text-sm font-medium text-foreground block">Show Subscription Checks</label>
                <p class="text-[10px] sm:text-xs text-muted-foreground">Check for new episodes in subscribed shows</p>
              </div>
              <div class="flex items-center space-x-2 flex-shrink-0">
                <input
                  v-model="taskConfig.enable_show_subscription_task"
                  type="checkbox"
                  class="w-4 h-4 text-primary bg-background border-border rounded focus:ring-primary"
                />
              </div>
            </div>
          </div>
          
          <!-- Intervals -->
          <div class="space-y-3 sm:space-y-4 pt-3 sm:pt-4 border-t border-border">
            <h3 class="text-base sm:text-lg font-medium text-foreground">Intervals (Minutes)</h3>
            
            <div class="space-y-2 sm:space-y-3">
              <div class="flex items-center justify-between gap-2">
                <label class="text-xs sm:text-sm font-medium text-foreground min-w-0 flex-1">Refresh Interval</label>
                <input 
                  v-model.number="taskConfig.refresh_interval_minutes" 
                  type="number" 
                  min="1" 
                  max="1440"
                  class="w-16 sm:w-20 h-7 sm:h-8 px-2 text-xs sm:text-sm rounded border border-input bg-background focus:ring-2 focus:ring-primary focus:border-primary"
                />
              </div>
              
              <div class="flex items-center justify-between gap-2">
                <label class="text-xs sm:text-sm font-medium text-foreground min-w-0 flex-1">Token Refresh</label>
                <input 
                  v-model.number="taskConfig.token_refresh_interval_minutes" 
                  type="number" 
                  min="1" 
                  max="60"
                  class="w-16 sm:w-20 h-7 sm:h-8 px-2 text-xs sm:text-sm rounded border border-input bg-background focus:ring-2 focus:ring-primary focus:border-primary"
                />
              </div>
              
              <div class="flex items-center justify-between gap-2">
                <label class="text-xs sm:text-sm font-medium text-foreground min-w-0 flex-1">Movie Processing Check</label>
                <input 
                  v-model.number="taskConfig.movie_processing_check_interval_minutes" 
                  type="number" 
                  min="1" 
                  max="120"
                  class="w-16 sm:w-20 h-7 sm:h-8 px-2 text-xs sm:text-sm rounded border border-input bg-background focus:ring-2 focus:ring-primary focus:border-primary"
                />
              </div>
              
              <div class="flex items-center justify-between gap-2">
                <label class="text-xs sm:text-sm font-medium text-foreground min-w-0 flex-1">Library Refresh</label>
                <input 
                  v-model.number="taskConfig.library_refresh_interval_minutes" 
                  type="number" 
                  min="1" 
                  max="240"
                  class="w-16 sm:w-20 h-7 sm:h-8 px-2 text-xs sm:text-sm rounded border border-input bg-background focus:ring-2 focus:ring-primary focus:border-primary"
                />
              </div>
              
              <div class="flex items-center justify-between gap-2">
                <label class="text-xs sm:text-sm font-medium text-foreground min-w-0 flex-1">Subscription Check</label>
                <input 
                  v-model.number="taskConfig.subscription_check_interval_minutes" 
                  type="number" 
                  min="1" 
                  max="240"
                  class="w-16 sm:w-20 h-7 sm:h-8 px-2 text-xs sm:text-sm rounded border border-input bg-background focus:ring-2 focus:ring-primary focus:border-primary"
                />
              </div>
            </div>
          </div>
          
          <!-- Queue Sizes -->
          <div class="space-y-3 sm:space-y-4 pt-3 sm:pt-4 border-t border-border">
            <h3 class="text-base sm:text-lg font-medium text-foreground">Queue Sizes</h3>
            
            <div class="space-y-2 sm:space-y-3">
              <div class="flex items-center justify-between gap-2">
                <label class="text-xs sm:text-sm font-medium text-foreground min-w-0 flex-1">Movie Queue Size</label>
                <input 
                  v-model.number="taskConfig.movie_queue_maxsize" 
                  type="number" 
                  min="10" 
                  max="1000"
                  class="w-16 sm:w-20 h-7 sm:h-8 px-2 text-xs sm:text-sm rounded border border-input bg-background focus:ring-2 focus:ring-primary focus:border-primary"
                />
              </div>
              
              <div class="flex items-center justify-between gap-2">
                <label class="text-xs sm:text-sm font-medium text-foreground min-w-0 flex-1">TV Queue Size</label>
                <input 
                  v-model.number="taskConfig.tv_queue_maxsize" 
                  type="number" 
                  min="10" 
                  max="1000"
                  class="w-16 sm:w-20 h-7 sm:h-8 px-2 text-xs sm:text-sm rounded border border-input bg-background focus:ring-2 focus:ring-primary focus:border-primary"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Failed Items Configuration -->
      <div class="glass-card p-4 sm:p-6 hover:shadow-lg transition-all duration-300">
        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-4 mb-4 sm:mb-6">
          <h2 class="text-lg sm:text-xl font-semibold flex items-center">
            <AppIcon icon="lucide:alert-circle" size="18" class="sm:w-5 sm:h-5 mr-2 text-primary" />
            Failed Items Configuration
          </h2>
          <button 
            @click="saveSection('failedItems')"
            :disabled="pendingSections.failedItems || !hasSectionChanges('failedItems')"
            :class="[
              'px-2 sm:px-3 py-1 text-[10px] sm:text-xs rounded transition-colors flex items-center gap-1',
              hasSectionChanges('failedItems') 
                ? 'bg-primary text-primary-foreground hover:bg-primary/90' 
                : 'bg-muted text-muted-foreground cursor-not-allowed'
            ]"
          >
            <AppIcon 
              :icon="pendingSections.failedItems ? 'lucide:loader-2' : 'lucide:save'" 
              size="10" 
              class="sm:w-3 sm:h-3"
              :class="{ 'animate-spin': pendingSections.failedItems }"
            />
            {{ pendingSections.failedItems ? 'Saving...' : 'Save' }}
          </button>
        </div>
        
        <div class="space-y-4 sm:space-y-6">
          <div class="flex items-center justify-between p-3 sm:p-4 bg-muted/50 rounded-lg">
            <div class="min-w-0 flex-1 pr-3">
              <label class="text-xs sm:text-sm font-medium text-foreground block">Enable Failed Item Retry</label>
              <p class="text-[10px] sm:text-xs text-muted-foreground">Enable or disable the automatic retry of failed media items</p>
            </div>
            <div class="flex items-center space-x-2 flex-shrink-0">
              <input
                v-model="failedItemsConfig.enable_failed_item_retry"
                type="checkbox"
                class="w-4 h-4 text-primary bg-background border-border rounded focus:ring-primary"
              />
            </div>
          </div>
          
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
            <div>
              <label class="block text-xs sm:text-sm font-medium text-foreground mb-1.5 sm:mb-2">
                Retry Interval (minutes)
              </label>
              <input
                v-model.number="failedItemsConfig.failed_item_retry_interval_minutes"
                type="number"
                min="1"
                max="1440"
                class="w-full px-3 py-2 text-xs sm:text-sm glass-input rounded-lg"
              />
              <p class="text-[10px] sm:text-xs text-muted-foreground mt-1">Interval between failed item retry checks</p>
            </div>
            
            <div>
              <label class="block text-xs sm:text-sm font-medium text-foreground mb-1.5 sm:mb-2">
                Max Retry Attempts
              </label>
              <input
                v-model.number="failedItemsConfig.failed_item_max_retry_attempts"
                type="number"
                min="1"
                max="10"
                class="w-full px-3 py-2 text-xs sm:text-sm glass-input rounded-lg"
              />
              <p class="text-[10px] sm:text-xs text-muted-foreground mt-1">Maximum number of retry attempts for failed items</p>
            </div>
          </div>
          
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
            <div>
              <label class="block text-xs sm:text-sm font-medium text-foreground mb-1.5 sm:mb-2">
                Initial Retry Delay (hours)
              </label>
              <input
                v-model.number="failedItemsConfig.failed_item_retry_delay_hours"
                type="number"
                min="1"
                max="168"
                class="w-full px-3 py-2 text-xs sm:text-sm glass-input rounded-lg"
              />
              <p class="text-[10px] sm:text-xs text-muted-foreground mt-1">Initial delay before first retry attempt</p>
            </div>
            
            <div>
              <label class="block text-xs sm:text-sm font-medium text-foreground mb-1.5 sm:mb-2">
                Backoff Multiplier
              </label>
              <input
                v-model.number="failedItemsConfig.failed_item_retry_backoff_multiplier"
                type="number"
                min="1"
                max="10"
                step="0.1"
                class="w-full px-3 py-2 text-xs sm:text-sm glass-input rounded-lg"
              />
              <p class="text-[10px] sm:text-xs text-muted-foreground mt-1">Multiplier for exponential backoff (e.g., 2 = 2h, 4h, 8h)</p>
            </div>
          </div>
          
          <div>
            <label class="block text-xs sm:text-sm font-medium text-foreground mb-1.5 sm:mb-2">
              Max Retry Delay (hours)
            </label>
            <input
              v-model.number="failedItemsConfig.failed_item_max_retry_delay_hours"
              type="number"
              min="1"
              max="168"
              class="w-full px-3 py-2 text-xs sm:text-sm glass-input rounded-lg"
            />
            <p class="text-[10px] sm:text-xs text-muted-foreground mt-1">Maximum delay between retry attempts</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useNotifications } from '~/composables/useNotifications'
import { onClickOutside } from '@vueuse/core'

const { addNotification } = useNotifications()
const colorMode = useColorMode()
const showThemeMenu = ref(false)
const themeMenuRef = ref<HTMLElement | null>(null)

// Theme definitions
const themes = [
  { value: 'light', name: 'Light', icon: 'lucide:sun' },
  { value: 'dark', name: 'SeerrBridge', icon: 'lucide:moon' },
  { value: 'darth-vadarr', name: 'Darth Vadarr', icon: 'lucide:sparkles' }
]

// Get theme display name
const getThemeName = (themeValue: string) => {
  const theme = themes.find(t => t.value === themeValue)
  return theme ? theme.name : 'Light'
}

// Get theme icon
const getThemeIcon = (themeValue: string) => {
  const theme = themes.find(t => t.value === themeValue)
  return theme ? theme.icon : 'lucide:sun'
}

// Select theme
const selectTheme = (themeValue: string) => {
  colorMode.preference = themeValue
  // Apply custom class for darth-vadarr theme
  if (process.client) {
    const html = document.documentElement
    html.classList.remove('dark', 'darth-vadarr')
    if (themeValue === 'darth-vadarr') {
      html.classList.add('darth-vadarr')
    } else if (themeValue === 'dark') {
      html.classList.add('dark')
    }
  }
  showThemeMenu.value = false
}

// Main configuration object
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
  max_movie_size: 0, // Biggest size possible
  max_episode_size: 0 // Biggest size possible
})

// Task configuration
const taskConfig = ref({
  background_tasks_enabled: true,
  scheduler_enabled: true,
  queue_processing_enabled: true,
  enable_automatic_background_task: false,
  enable_show_subscription_task: false,
  refresh_interval_minutes: 60,
  token_refresh_interval_minutes: 10,
  movie_processing_check_interval_minutes: 15,
  library_refresh_interval_minutes: 30,
  subscription_check_interval_minutes: 60,
  movie_queue_maxsize: 250,
  tv_queue_maxsize: 250
})

// Failed items configuration
const failedItemsConfig = ref({
  enable_failed_item_retry: true,
  failed_item_retry_interval_minutes: 30,
  failed_item_max_retry_attempts: 3,
  failed_item_retry_delay_hours: 2,
  failed_item_retry_backoff_multiplier: 2,
  failed_item_max_retry_delay_hours: 24
})

// State management
const pending = ref(false)
const testingConnections = ref(false)
const setupCompleted = ref(true)
const configStatus = ref({})

// Track original values for change detection
const originalConfig = ref({})
const originalTaskConfig = ref({})
const originalFailedItemsConfig = ref({})

// Section-specific pending states
const pendingSections = ref({
  realdebrid: false,
  overseerr: false,
  trakt: false,
  system: false,
  tasks: false,
  failedItems: false
})

// Task refresh state
const refreshingTasks = ref(false)

// Size limit options
const movieSizeOptions = [
  { value: 0, label: 'Biggest Size Possible', description: 'No size limit' },
  { value: 1, label: '1 GB', description: '1 Gigabyte' },
  { value: 3, label: '3 GB', description: '3 Gigabytes' },
  { value: 5, label: '5 GB', description: '5 Gigabytes' },
  { value: 15, label: '15 GB', description: '15 Gigabytes' },
  { value: 30, label: '30 GB', description: '30 Gigabytes' },
  { value: 60, label: '60 GB', description: '60 Gigabytes' }
]

const episodeSizeOptions = [
  { value: 0, label: 'Biggest Size Possible', description: 'No size limit' },
  { value: 0.1, label: '100 MB', description: '100 Megabytes' },
  { value: 0.3, label: '300 MB', description: '300 Megabytes' },
  { value: 0.5, label: '500 MB', description: '500 Megabytes' },
  { value: 1, label: '1 GB', description: '1 Gigabyte' },
  { value: 3, label: '3 GB', description: '3 Gigabytes' },
  { value: 5, label: '5 GB', description: '5 Gigabytes' }
]

const toggleTheme = () => {
  // Cycle through themes: light -> dark -> darth-vadarr -> light
  const currentIndex = themes.findIndex(t => t.value === colorMode.value)
  const nextIndex = (currentIndex + 1) % themes.length
  selectTheme(themes[nextIndex].value)
}

// Watch for color mode changes to apply custom classes
watch(() => colorMode.value, (newValue) => {
  if (process.client) {
    const html = document.documentElement
    html.classList.remove('dark', 'darth-vadarr')
    if (newValue === 'darth-vadarr') {
      html.classList.add('darth-vadarr')
    } else if (newValue === 'dark') {
      html.classList.add('dark')
    }
  }
}, { immediate: true })

// Helper function to ensure size values match dropdown options
const ensureSizeValueMatches = (value, options, defaultValue) => {
  console.log(`🔍 ensureSizeValueMatches called with:`, { value, defaultValue, options })
  
  if (value === null || value === undefined) {
    console.log(`❌ Value is null/undefined, returning default: ${defaultValue}`)
    return defaultValue
  }
  
  const numValue = typeof value === 'string' ? parseFloat(value) : value
  console.log(`🔢 Converted value: ${value} -> ${numValue} (isNaN: ${isNaN(numValue)})`)
  
  if (isNaN(numValue)) {
    console.log(`❌ Value is NaN, returning default: ${defaultValue}`)
    return defaultValue
  }
  
  // Find exact match first
  const exactMatch = options.find(option => Math.abs(option.value - numValue) < 0.01)
  if (exactMatch) {
    console.log(`✅ Found exact match: ${exactMatch.value}`)
    return exactMatch.value
  }
  
  // Find closest match
  const closestMatch = options.reduce((prev, curr) => 
    Math.abs(curr.value - numValue) < Math.abs(prev.value - numValue) ? curr : prev
  )
  
  console.log(`🎯 Found closest match: ${closestMatch.value} (original: ${numValue})`)
  return closestMatch.value
}

// Function to manually refresh task configuration
const refreshTaskConfiguration = async () => {
  refreshingTasks.value = true
  
  try {
    const response = await $fetch('/api/task-config/refresh', {
      method: 'POST'
    })
    
    if (response.success) {
      addNotification({
        type: 'success',
        title: 'Tasks Refreshed',
        message: 'Background tasks have been refreshed successfully'
      })
    } else {
      throw new Error(response.error || 'Failed to refresh tasks')
    }
  } catch (error) {
    console.error('Error refreshing task configuration:', error)
    addNotification({
      type: 'error',
      title: 'Refresh Failed',
      message: 'Failed to refresh background tasks. Please try again.'
    })
  } finally {
    refreshingTasks.value = false
  }
}

// Function to restart SeerrBridge service
const restartSeerrBridgeService = async () => {
  try {
    const response = await $fetch('/api/restart', {
      method: 'POST'
    })
    
    if (!response.success) {
      throw new Error(response.error || 'Failed to restart service')
    }
    
    return response
  } catch (error) {
    console.error('Error restarting SeerrBridge service:', error)
    throw error
  }
}

// Helper function to check if a section has changes
const hasSectionChanges = (section) => {
  switch (section) {
    case 'realdebrid':
      return ['rd_client_id', 'rd_client_secret', 'rd_access_token', 'rd_refresh_token'].some(key => 
        config.value[key] !== originalConfig.value[key]
      )
    case 'overseerr':
      return ['overseerr_base', 'overseerr_api_key'].some(key => 
        config.value[key] !== originalConfig.value[key]
      )
    case 'trakt':
      return ['trakt_api_key'].some(key => 
        config.value[key] !== originalConfig.value[key]
      )
    case 'system':
      return ['headless_mode', 'refresh_interval_minutes', 'torrent_filter_regex', 'max_movie_size', 'max_episode_size'].some(key => 
        config.value[key] !== originalConfig.value[key]
      )
    case 'tasks':
      return Object.keys(taskConfig.value).some(key => 
        taskConfig.value[key] !== originalTaskConfig.value[key]
      )
    case 'failedItems':
      return Object.keys(failedItemsConfig.value).some(key => 
        failedItemsConfig.value[key] !== originalFailedItemsConfig.value[key]
      )
    default:
      return false
  }
}

// Helper function to get section-specific configs
const getSectionConfigs = (section) => {
  switch (section) {
    case 'realdebrid':
      return ['rd_client_id', 'rd_client_secret', 'rd_access_token', 'rd_refresh_token']
    case 'overseerr':
      return ['overseerr_base', 'overseerr_api_key']
    case 'trakt':
      return ['trakt_api_key']
    case 'system':
      return ['headless_mode', 'refresh_interval_minutes', 'torrent_filter_regex', 'max_movie_size', 'max_episode_size']
    case 'tasks':
      return Object.keys(taskConfig.value)
    case 'failedItems':
      return Object.keys(failedItemsConfig.value)
    default:
      return []
  }
}

const loadSettings = async () => {
  try {
    // DO NOT log sensitive data to console
    const response = await $fetch('/api/config')
    
    if (response.success) {
      const configs = response.data
      
      const configMap = {}
      const statusMap = {} // Track which configs have values
      
      configs.forEach(config => {
        // DO NOT log actual config values - only log status
        const sensitiveKeys = ['rd_access_token', 'rd_refresh_token', 'rd_client_id', 'rd_client_secret', 'overseerr_api_key', 'trakt_api_key', 'db_password', 'mysql_root_password']
        const isSensitive = sensitiveKeys.includes(config.config_key)
        const logValue = isSensitive ? '[REDACTED]' : (config.is_encrypted ? '[ENCRYPTED]' : '[VALUE]')
        console.debug(`🔧 Processing config: ${config.config_key} = ${logValue} (type: ${config.config_type}, encrypted: ${config.is_encrypted})`)
        
        // Store the actual value (or masked value for sensitive data)
        if (config.config_value && !config.is_encrypted) {
          configMap[config.config_key] = config.config_value
        } else if (config.is_encrypted) {
          // For sensitive values, don't store masked values - they would be sent back to backend
          // Only store if it's not a sensitive token that needs to be used for API calls
          const sensitiveTokens = ['rd_access_token', 'rd_refresh_token', 'rd_client_id', 'rd_client_secret', 'overseerr_api_key', 'trakt_api_key']
          if (!sensitiveTokens.includes(config.config_key)) {
            configMap[config.config_key] = config.config_value
          }
          // For sensitive tokens, leave them empty so they don't interfere with backend
        }
        
        // Track if the config has a value (even if encrypted)
        statusMap[config.config_key] = config.has_value
      })
      
      // DO NOT log config values - they may contain sensitive data
      console.debug(`📊 Processed ${Object.keys(configMap).length} configs, ${Object.keys(statusMap).length} statuses`)
      
      // Update main config
      config.value = { ...config.value, ...configMap }
      
      // Update task config
      Object.keys(taskConfig.value).forEach(key => {
        if (configMap[key] !== undefined) {
          taskConfig.value[key] = configMap[key]
        }
      })
      
      // Update failed items config
      Object.keys(failedItemsConfig.value).forEach(key => {
        if (configMap[key] !== undefined) {
          failedItemsConfig.value[key] = configMap[key]
        }
      })
      
      // DO NOT log config values - they may contain sensitive data
      
      // Ensure max_movie_size and max_episode_size are properly converted to numbers
      // and match the available dropdown options
      const originalMovieSize = config.value.max_movie_size
      const originalEpisodeSize = config.value.max_episode_size
      
      config.value.max_movie_size = ensureSizeValueMatches(
        config.value.max_movie_size, 
        movieSizeOptions, 
        0
      )
      
      config.value.max_episode_size = ensureSizeValueMatches(
        config.value.max_episode_size, 
        episodeSizeOptions, 
        0
      )
      
      // DO NOT log config values - they may contain sensitive data
      
      // Store original values for change detection
      originalConfig.value = JSON.parse(JSON.stringify(config.value))
      originalTaskConfig.value = JSON.parse(JSON.stringify(taskConfig.value))
      originalFailedItemsConfig.value = JSON.parse(JSON.stringify(failedItemsConfig.value))
      
      // Check if setup is completed (handle both boolean and string values)
      const onboardingCompleted = configMap.onboarding_completed === true || configMap.onboarding_completed === 'true'
      const setupRequired = configMap.setup_required === false || configMap.setup_required === 'false'
      setupCompleted.value = onboardingCompleted || setupRequired
      
      // Store config status for UI checks
      configStatus.value = statusMap
      
             // DO NOT log sensitive config values - only log status
             console.debug('Configuration loaded:', {
               onboarding_completed: configMap.onboarding_completed,
               setup_required: configMap.setup_required,
               onboardingCompleted,
               setupRequired,
               setupCompleted: setupCompleted.value
             })
             
             // Log only credential status (present/absent), not actual values
             console.debug('API Credential Status:', {
               rd_client_id: !!statusMap.rd_client_id,
               rd_client_secret: !!statusMap.rd_client_secret,
               rd_access_token: !!statusMap.rd_access_token,
               rd_refresh_token: !!statusMap.rd_refresh_token,
               overseerr_base: !!statusMap.overseerr_base,
               overseerr_api_key: !!statusMap.overseerr_api_key,
               trakt_api_key: !!statusMap.trakt_api_key
             })
             
             // DO NOT log config values - they may contain sensitive data
             // Only log non-sensitive size configuration metadata
             console.debug('Size Configuration Values (non-sensitive metadata only):', {
               max_movie_size: {
                 converted: config.value.max_movie_size,
                 type: typeof config.value.max_movie_size,
                 isNaN: isNaN(config.value.max_movie_size)
               },
               max_episode_size: {
                 converted: config.value.max_episode_size,
                 type: typeof config.value.max_episode_size,
                 isNaN: isNaN(config.value.max_episode_size)
               },
               configCount: Object.keys(configMap).length
               // DO NOT log configMap - may contain sensitive data
             })
    }
  } catch (error) {
    console.error('Error loading settings:', error)
    addNotification({
      type: 'error',
      title: 'Load Failed',
      message: 'Failed to load settings'
    })
  }
}

// Section-specific save functions
const saveSection = async (section) => {
  // Check if there are changes
  if (!hasSectionChanges(section)) {
    addNotification({
      type: 'info',
      title: 'No Changes',
      message: `${section.charAt(0).toUpperCase() + section.slice(1)} section has no changes to save`
    })
    return
  }

  pendingSections.value[section] = true
  
  try {
    let configsToSave = []
    
    if (['realdebrid', 'overseerr', 'trakt', 'system'].includes(section)) {
      // Main config section
      const keys = getSectionConfigs(section)
      configsToSave = keys.map(key => ({
        config_key: key,
        config_value: config.value[key],
        config_type: typeof config.value[key] === 'boolean' ? 'bool' : 
                     typeof config.value[key] === 'number' ? 'int' : 'string',
        description: getConfigDescription(key)
      }))
    } else if (section === 'tasks') {
      // Task config section
      configsToSave = Object.entries(taskConfig.value).map(([key, value]) => ({
        config_key: key,
        config_value: value,
        config_type: typeof value === 'boolean' ? 'bool' : 
                     typeof value === 'number' ? 'int' : 'string',
        description: getConfigDescription(key)
      }))
    } else if (section === 'failedItems') {
      // Failed items config section
      configsToSave = Object.entries(failedItemsConfig.value).map(([key, value]) => ({
        config_key: key,
        config_value: value,
        config_type: typeof value === 'boolean' ? 'bool' : 
                     typeof value === 'number' ? 'int' : 'string',
        description: getConfigDescription(key)
      }))
    }
    
    const response = await $fetch('/api/config-secure', {
      method: 'POST',
      body: { configs: configsToSave }
    })
    
    if (response.success) {
      // Update original values to reflect saved state
      if (['realdebrid', 'overseerr', 'trakt', 'system'].includes(section)) {
        const keys = getSectionConfigs(section)
        keys.forEach(key => {
          originalConfig.value[key] = config.value[key]
        })
      } else if (section === 'tasks') {
        originalTaskConfig.value = JSON.parse(JSON.stringify(taskConfig.value))
      } else if (section === 'failedItems') {
        originalFailedItemsConfig.value = JSON.parse(JSON.stringify(failedItemsConfig.value))
      }
      
      // Check if we need to restart the service for system config changes
      // Only restart for changes that actually require a restart (not live-updatable settings)
      const restartRequiredKeys = ['headless_mode', 'refresh_interval_minutes']
      const liveUpdateKeys = ['torrent_filter_regex', 'max_movie_size', 'max_episode_size']
      
      const hasRestartRequiredChanges = restartRequiredKeys.some(key => 
        taskConfig.value[key] !== originalTaskConfig.value[key]
      )
      
      const hasLiveUpdateChanges = liveUpdateKeys.some(key => 
        taskConfig.value[key] !== originalTaskConfig.value[key]
      )
      
      const needsRestart = section === 'system' && hasRestartRequiredChanges || (section === 'tasks' && ['refresh_interval_minutes', 'token_refresh_interval_minutes', 'movie_processing_check_interval_minutes', 'library_refresh_interval_minutes', 'subscription_check_interval_minutes'].some(key => 
        taskConfig.value[key] !== originalTaskConfig.value[key]
      ))
      
      // Check if task configuration was updated and needs refresh
      const taskConfigKeys = ['background_tasks_enabled', 'scheduler_enabled', 'queue_processing_enabled', 'enable_automatic_background_task', 'enable_show_subscription_task', 'movie_queue_maxsize', 'tv_queue_maxsize']
      const needsTaskRefresh = section === 'tasks' && taskConfigKeys.some(key => 
        taskConfig.value[key] !== originalTaskConfig.value[key]
      )
      
      // Handle live updates first if there are any
      if (hasLiveUpdateChanges) {
        try {
          await $fetch('/api/bridge-reload', {
            method: 'POST'
          })
          addNotification({
            type: 'success',
            title: 'Settings Updated Live',
            message: `${section.charAt(0).toUpperCase() + section.slice(1)} settings have been saved and applied live without restart`
          })
        } catch (reloadError) {
          console.error('Error reloading environment:', reloadError)
          addNotification({
            type: 'warning',
            title: 'Settings Saved, Live Update Failed',
            message: `${section.charAt(0).toUpperCase() + section.slice(1)} settings have been saved, but failed to apply live updates. Please restart manually.`
          })
        }
      }
      
      // Handle restart-required changes
      if (needsRestart) {
        // Restart the SeerrBridge service
        try {
          await restartSeerrBridgeService()
          const message = hasLiveUpdateChanges 
            ? `${section.charAt(0).toUpperCase() + section.slice(1)} settings have been saved. Live-updatable settings were applied, and SeerrBridge service has been restarted for remaining changes`
            : `${section.charAt(0).toUpperCase() + section.slice(1)} settings have been saved and SeerrBridge service has been restarted to apply changes`
          addNotification({
            type: 'success',
            title: 'Settings Saved & Service Restarted',
            message: message
          })
        } catch (restartError) {
          console.error('Error restarting service:', restartError)
          addNotification({
            type: 'warning',
            title: 'Settings Saved, Restart Failed',
            message: `${section.charAt(0).toUpperCase() + section.slice(1)} settings have been saved, but failed to restart SeerrBridge service. Please restart manually.`
          })
        }
      } else if (needsTaskRefresh) {
        // Trigger task configuration refresh
        refreshingTasks.value = true
        try {
          await $fetch('/api/task-config/refresh', {
            method: 'POST'
          })
          addNotification({
            type: 'success',
            title: 'Settings Saved & Tasks Refreshed',
            message: `${section.charAt(0).toUpperCase() + section.slice(1)} settings have been saved and background tasks have been refreshed`
          })
        } catch (refreshError) {
          console.error('Error refreshing tasks:', refreshError)
          addNotification({
            type: 'warning',
            title: 'Settings Saved, Refresh Failed',
            message: `${section.charAt(0).toUpperCase() + section.slice(1)} settings have been saved, but failed to refresh background tasks. Changes may not take effect immediately.`
          })
        } finally {
          refreshingTasks.value = false
        }
      } else {
        addNotification({
          type: 'success',
          title: 'Settings Saved',
          message: `${section.charAt(0).toUpperCase() + section.slice(1)} settings have been saved successfully`
        })
      }
    } else {
      throw new Error(response.error || 'Failed to save settings')
    }
  } catch (error) {
    console.error(`Error saving ${section} settings:`, error)
    addNotification({
      type: 'error',
      title: 'Save Failed',
      message: `Failed to save ${section} settings`
    })
  } finally {
    pendingSections.value[section] = false
  }
}

const saveAllSettings = async () => {
  pending.value = true
  
  try {
    // Define sensitive keys that should not be overwritten if empty/undefined
    const sensitiveKeys = [
      'rd_access_token', 'rd_refresh_token', 'rd_client_id', 'rd_client_secret',
      'overseerr_api_key', 'trakt_api_key', 'discord_webhook_url',
      'db_password', 'mysql_root_password'
    ]
    
    // Filter main configuration to only include changed values and skip empty sensitive keys
    const mainConfigs = Object.entries(config.value)
      .filter(([key, value]) => {
        // Only include if value has changed
        const hasChanged = config.value[key] !== originalConfig.value[key]
        
        // For sensitive keys, skip if empty/undefined (don't overwrite existing encrypted values)
        if (sensitiveKeys.includes(key)) {
          return hasChanged && (value !== undefined && value !== null && value !== '')
        }
        
        return hasChanged
      })
      .map(([key, value]) => ({
        config_key: key,
        config_value: value,
        config_type: typeof value === 'boolean' ? 'bool' : 
                     typeof value === 'number' ? 'int' : 'string',
        description: getConfigDescription(key)
      }))
    
    // Filter task configuration to only include changed values
    const taskConfigs = Object.entries(taskConfig.value)
      .filter(([key, value]) => taskConfig.value[key] !== originalTaskConfig.value[key])
      .map(([key, value]) => ({
        config_key: key,
        config_value: value,
        config_type: typeof value === 'boolean' ? 'bool' : 
                     typeof value === 'number' ? 'int' : 'string',
        description: getConfigDescription(key)
      }))
    
    // Filter failed items configuration to only include changed values
    const failedItemsConfigs = Object.entries(failedItemsConfig.value)
      .filter(([key, value]) => failedItemsConfig.value[key] !== originalFailedItemsConfig.value[key])
      .map(([key, value]) => ({
        config_key: key,
        config_value: value,
        config_type: typeof value === 'boolean' ? 'bool' : 
                     typeof value === 'number' ? 'int' : 'string',
        description: getConfigDescription(key)
      }))
    
    // Combine all configurations
    const allConfigs = [...mainConfigs, ...taskConfigs, ...failedItemsConfigs]
    
    // Check if there are any changes to save
    if (allConfigs.length === 0) {
      addNotification({
        type: 'info',
        title: 'No Changes',
        message: 'No settings have been changed'
      })
      return
    }
    
    // Use secure endpoint to ensure API keys are encrypted
    const response = await $fetch('/api/config-secure', {
      method: 'POST',
      body: { configs: allConfigs }
    })
    
    if (response.success) {
      // Update original values for the configs that were actually saved
      mainConfigs.forEach(({ config_key }) => {
        originalConfig.value[config_key] = config.value[config_key]
      })
      taskConfigs.forEach(({ config_key }) => {
        originalTaskConfig.value[config_key] = taskConfig.value[config_key]
      })
      failedItemsConfigs.forEach(({ config_key }) => {
        originalFailedItemsConfig.value[config_key] = failedItemsConfig.value[config_key]
      })
      
      // Settings saved successfully
      addNotification({
        type: 'success',
        title: 'Settings Saved',
        message: 'All settings have been saved successfully'
      })
    } else {
      throw new Error(response.error || 'Failed to save settings')
    }
  } catch (error) {
    console.error('Error saving settings:', error)
    addNotification({
      type: 'error',
      title: 'Save Failed',
      message: 'Failed to save settings'
    })
  } finally {
    pending.value = false
  }
}

const testConnections = async () => {
  testingConnections.value = true
  
  try {
    // Test Real-Debrid connection
    if (config.value.rd_client_id && config.value.rd_client_secret) {
      await $fetch('/api/test-rd-connection', {
        method: 'POST',
        body: {
          client_id: config.value.rd_client_id,
          client_secret: config.value.rd_client_secret
        }
      })
    }
    
    // Test Overseerr connection
    if (config.value.overseerr_base && config.value.overseerr_api_key) {
      await $fetch('/api/test-overseerr-connection', {
        method: 'POST',
        body: {
          base_url: config.value.overseerr_base,
          api_key: config.value.overseerr_api_key
        }
      })
    }
    
    // Test Trakt connection
    if (config.value.trakt_api_key) {
      await $fetch('/api/test-trakt-connection', {
        method: 'POST',
        body: {
          api_key: config.value.trakt_api_key
        }
      })
    }
    
    addNotification({
      type: 'success',
      title: 'Connections Tested',
      message: 'All configured connections tested successfully'
    })
  } catch (error) {
    console.error('Error testing connections:', error)
    addNotification({
      type: 'error',
      title: 'Connection Test Failed',
      message: 'One or more connections failed. Check your credentials.'
    })
  } finally {
    testingConnections.value = false
  }
}

const resetToDefaults = () => {
  if (confirm('Are you sure you want to reset all settings to their default values? This action cannot be undone.')) {
    // Reset main config
    config.value = {
      rd_client_id: '',
      rd_client_secret: '',
      rd_access_token: '',
      rd_refresh_token: '',
      overseerr_base: '',
      overseerr_api_key: '',
      trakt_api_key: '',
      headless_mode: true,
      refresh_interval_minutes: 60,
      torrent_filter_regex: '^(?!.*【.*?】)(?!.*[\\u0400-\\u04FF])(?!.*\\[esp\\]).*',
      max_movie_size: 0,
      max_episode_size: 0
    }
    
    // Reset task config
    taskConfig.value = {
      background_tasks_enabled: true,
      scheduler_enabled: true,
      queue_processing_enabled: true,
      enable_automatic_background_task: false,
      enable_show_subscription_task: false,
      refresh_interval_minutes: 60,
      token_refresh_interval_minutes: 10,
      movie_processing_check_interval_minutes: 15,
      library_refresh_interval_minutes: 30,
      subscription_check_interval_minutes: 60,
      movie_queue_maxsize: 250,
      tv_queue_maxsize: 250
    }
    
    // Reset failed items config
    failedItemsConfig.value = {
      enable_failed_item_retry: true,
      failed_item_retry_interval_minutes: 30,
      failed_item_max_retry_attempts: 3,
      failed_item_retry_delay_hours: 2,
      failed_item_retry_backoff_multiplier: 2,
      failed_item_max_retry_delay_hours: 24
    }
    
    addNotification({
      type: 'success',
      title: 'Settings Reset',
      message: 'All settings have been reset to their default values'
    })
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
    torrent_filter_regex: 'Torrent filter regex pattern',
    max_movie_size: 'Maximum movie size in GB',
    max_episode_size: 'Maximum episode size in GB',
    background_tasks_enabled: 'Enable background tasks',
    scheduler_enabled: 'Enable scheduler',
    queue_processing_enabled: 'Enable queue processing',
    enable_automatic_background_task: 'Enable automatic background task',
    enable_show_subscription_task: 'Enable show subscription task',
    token_refresh_interval_minutes: 'Token refresh interval in minutes',
    movie_processing_check_interval_minutes: 'Movie processing check interval in minutes',
    library_refresh_interval_minutes: 'Library refresh interval in minutes',
    subscription_check_interval_minutes: 'Subscription check interval in minutes',
    movie_queue_maxsize: 'Movie queue maximum size',
    tv_queue_maxsize: 'TV queue maximum size',
    enable_failed_item_retry: 'Enable failed item retry',
    failed_item_retry_interval_minutes: 'Failed item retry interval in minutes',
    failed_item_max_retry_attempts: 'Maximum retry attempts for failed items',
    failed_item_retry_delay_hours: 'Initial retry delay in hours',
    failed_item_retry_backoff_multiplier: 'Retry backoff multiplier',
    failed_item_max_retry_delay_hours: 'Maximum retry delay in hours'
  }
  return descriptions[key] || `Configuration for ${key}`
}

// Watch for changes in size values to ensure dropdowns are properly updated
watch([() => config.value.max_movie_size, () => config.value.max_episode_size], 
  ([newMovieSize, newEpisodeSize], [oldMovieSize, oldEpisodeSize]) => {
    // Ensure the values are valid numbers and match available options
    if (newMovieSize !== undefined && newMovieSize !== oldMovieSize) {
      const correctedMovieSize = ensureSizeValueMatches(newMovieSize, movieSizeOptions, 0)
      if (correctedMovieSize !== newMovieSize) {
        config.value.max_movie_size = correctedMovieSize
      }
    }
    
    if (newEpisodeSize !== undefined && newEpisodeSize !== oldEpisodeSize) {
      const correctedEpisodeSize = ensureSizeValueMatches(newEpisodeSize, episodeSizeOptions, 0)
      if (correctedEpisodeSize !== newEpisodeSize) {
        config.value.max_episode_size = correctedEpisodeSize
      }
    }
  },
  { immediate: false }
)

// Close theme menu when clicking outside
onClickOutside(themeMenuRef, () => {
  showThemeMenu.value = false
})

// Load settings on mount
onMounted(async () => {
  // DO NOT log config values - they may contain sensitive data
  await loadSettings()
})

// Page head configuration
useHead({
  title: 'Settings'
})
</script>
