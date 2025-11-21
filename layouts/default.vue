<template>
  <div class="min-h-screen bg-background">
    <!-- Main Layout -->
    <div class="flex h-screen">
      <!-- Sidebar -->
      <aside 
        :class="[
          'bg-card border-r border-border flex flex-col transition-all duration-300 ease-in-out overflow-hidden',
          isCollapsed ? 'w-20' : 'w-64'
        ]"
      >
        <!-- Logo -->
        <div class="p-6 border-b border-border">
          <div class="flex items-center" :class="isCollapsed ? 'justify-center' : 'justify-between space-x-3'">
            <NuxtLink 
              to="/dashboard" 
              class="flex items-center space-x-3 hover:opacity-80 transition-opacity"
              :class="{ 'opacity-0 w-0 h-0 overflow-hidden': isCollapsed }"
            >
              <div class="p-2 bg-primary/10 rounded-lg">
                <AppIcon icon="lucide:sailboat" size="24" class="text-primary" />
              </div>
              <div>
                <h1 class="text-xl font-bold text-foreground transition-opacity duration-300">DarthVadarr</h1>
                <p class="text-xs text-muted-foreground transition-opacity duration-300">SeerrBridge Dashboard</p>
              </div>
            </NuxtLink>
            <NuxtLink 
              v-if="isCollapsed" 
              to="/dashboard"
              class="flex justify-center hover:opacity-80 transition-opacity"
            >
              <div class="p-2 bg-primary/10 rounded-lg">
                <AppIcon icon="lucide:sailboat" size="24" class="text-primary" />
              </div>
            </NuxtLink>
          </div>
        </div>

        <!-- Navigation -->
        <nav class="flex-1 p-4 space-y-2">
          <NuxtLink
            to="/dashboard"
            class="nav-link group relative"
            :class="[isCollapsed ? 'justify-center' : 'justify-start', { 'nav-link-active': $route.path === '/dashboard' || $route.path === '/' }]"
          >
            <AppIcon icon="lucide:home" size="18" :class="isCollapsed ? '' : 'mr-3'" />
            <span :class="{ 'opacity-0 w-0 overflow-hidden': isCollapsed }" class="transition-all duration-300">Dashboard</span>
          </NuxtLink>
          
          <NuxtLink
            to="/processed-media"
            class="nav-link group relative"
            :class="[isCollapsed ? 'justify-center' : 'justify-start', { 'nav-link-active': $route.path === '/processed-media' }]"
          >
            <AppIcon icon="lucide:film" size="18" :class="isCollapsed ? '' : 'mr-3'" />
            <span :class="{ 'opacity-0 w-0 overflow-hidden': isCollapsed }" class="transition-all duration-300">Processed Media</span>
          </NuxtLink>
          
          <NuxtLink
            to="/search"
            class="nav-link group relative"
            :class="[isCollapsed ? 'justify-center' : 'justify-start', { 'nav-link-active': $route.path === '/search' }]"
          >
            <AppIcon icon="lucide:search" size="18" :class="isCollapsed ? '' : 'mr-3'" />
            <span :class="{ 'opacity-0 w-0 overflow-hidden': isCollapsed }" class="transition-all duration-300">Search Media</span>
          </NuxtLink>
          
          <NuxtLink
            to="/collections"
            class="nav-link group relative"
            :class="[isCollapsed ? 'justify-center' : 'justify-start', { 'nav-link-active': $route.path.startsWith('/collections') }]"
          >
            <AppIcon icon="lucide:folder" size="18" :class="isCollapsed ? '' : 'mr-3'" />
            <span :class="{ 'opacity-0 w-0 overflow-hidden': isCollapsed }" class="transition-all duration-300">Collections</span>
          </NuxtLink>
          
          <NuxtLink
            to="/logs/all"
            class="nav-link group relative"
            :class="[isCollapsed ? 'justify-center' : 'justify-start', { 'nav-link-active': $route.path.startsWith('/logs') }]"
          >
            <AppIcon icon="lucide:file-text" size="18" :class="isCollapsed ? '' : 'mr-3'" />
            <span :class="{ 'opacity-0 w-0 overflow-hidden': isCollapsed }" class="transition-all duration-300">Logs</span>
          </NuxtLink>
          
          <NuxtLink
            to="/dashboard/database"
            class="nav-link group relative"
            :class="[isCollapsed ? 'justify-center' : 'justify-start', { 'nav-link-active': $route.path === '/dashboard/database' }]"
          >
            <AppIcon icon="lucide:database" size="18" :class="isCollapsed ? '' : 'mr-3'" />
            <span :class="{ 'opacity-0 w-0 overflow-hidden': isCollapsed }" class="transition-all duration-300">Database</span>
          </NuxtLink>
          
          <NuxtLink
            to="/dashboard/settings"
            class="nav-link group relative"
            :class="[isCollapsed ? 'justify-center' : 'justify-start', { 'nav-link-active': $route.path.startsWith('/dashboard/settings') }]"
          >
            <AppIcon icon="lucide:settings" size="18" :class="isCollapsed ? '' : 'mr-3'" />
            <span :class="{ 'opacity-0 w-0 overflow-hidden': isCollapsed }" class="transition-all duration-300">Settings</span>
          </NuxtLink>
        </nav>

        <!-- User section -->
        <div class="p-4 border-t border-border">
          <div class="flex items-center" :class="isCollapsed ? 'justify-center' : 'space-x-3'">
            <div class="w-8 h-8 bg-primary/10 rounded-full flex items-center justify-center flex-shrink-0">
              <AppIcon icon="lucide:user" size="16" class="text-primary" />
            </div>
            <div class="flex-1 min-w-0" :class="{ 'opacity-0 w-0 overflow-hidden': isCollapsed }">
              <p class="text-sm font-medium text-foreground truncate">Admin</p>
              <p class="text-xs text-muted-foreground">System User</p>
            </div>
            <button
              @click="toggleTheme"
              class="p-1.5 hover:bg-muted rounded-md transition-colors flex-shrink-0"
              :class="{ 'mx-auto': isCollapsed }"
              :title="colorMode.value === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'"
            >
              <AppIcon 
                :icon="colorMode.value === 'dark' ? 'lucide:sun' : 'lucide:moon'" 
                size="16" 
              />
            </button>
          </div>
        </div>
      </aside>

      <!-- Main content area -->
      <div class="flex-1 flex flex-col overflow-hidden">
        <!-- Top bar -->
        <header class="h-16 bg-card border-b border-border flex items-center justify-between px-6">
          <div class="flex items-center space-x-4">
            <button
              @click="toggleSidebar"
              class="p-2 hover:bg-muted rounded-lg transition-colors"
              :title="isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'"
            >
              <AppIcon :icon="isCollapsed ? 'lucide:chevrons-right' : 'lucide:chevrons-left'" size="20" class="text-foreground" />
            </button>
            <h2 class="text-lg font-semibold text-foreground">
              {{ pageTitle }}
            </h2>
          </div>
          
          <div class="flex items-center space-x-3">
            <NotificationHistory />
            
            <div class="w-px h-6 bg-border" />
            
            <LiveStatus />
          </div>
        </header>

        <!-- Page content -->
        <main class="flex-1 overflow-auto">
          <div class="p-6">
            <NuxtPage />
          </div>
        </main>
      </div>
    </div>

    <!-- Notification system -->
    <NotificationSystem />
    
  </div>
</template>

<script setup lang="ts">
// Layout-specific head configuration
useHead({
  titleTemplate: '%s - Darth Vadarr'
})

const colorMode = useColorMode()
const route = useRoute()

// Sidebar state management with localStorage persistence
const isCollapsed = useState('sidebarCollapsed', () => {
  if (process.client) {
    const saved = localStorage.getItem('sidebarCollapsed')
    return saved === 'true'
  }
  return false
})

const toggleSidebar = () => {
  isCollapsed.value = !isCollapsed.value
  if (process.client) {
    localStorage.setItem('sidebarCollapsed', String(isCollapsed.value))
  }
}

const toggleTheme = () => {
  colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'
}

const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    '/': 'Dashboard',
    '/dashboard': 'Dashboard',
    '/processed-media': 'Processed Media',
    '/search': 'Search Media',
    '/collections': 'Collections',
    '/logs': 'Logs',
    '/dashboard/database': 'Database',
    '/dashboard/settings': 'Settings',
    '/settings': 'Settings'
  }
  
  // Handle dynamic collection routes
  if (route.path.startsWith('/collections/')) {
    return 'Collection'
  }
  
  return titles[route.path] || 'Dashboard'
})
</script>

<style scoped>
.nav-link {
  @apply flex items-center px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200;
  @apply text-muted-foreground hover:text-foreground hover:bg-muted/50;
  position: relative;
}

/* When collapsed, center the icon */
.nav-link svg {
  flex-shrink: 0;
}

.nav-link span {
  white-space: nowrap;
}

.nav-link-active {
  @apply text-primary bg-primary/10 border-r-2 border-primary;
}

</style>
