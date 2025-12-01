<template>
  <div class="min-h-screen bg-background relative">
    <!-- Matrix Rain Background -->
    <MatrixRain />
    
    <!-- Mobile overlay -->
    <div 
      v-if="isMobileMenuOpen"
      class="fixed inset-0 bg-black/50 z-40 lg:hidden transition-opacity duration-300"
      @click="closeMobileMenu"
    />
    
    <!-- Main Layout -->
    <div class="flex h-screen w-full lg:flex-row">
      <!-- Sidebar -->
      <aside 
        :class="[
          'bg-card border-r border-border flex flex-col transition-all duration-300 ease-in-out overflow-hidden fixed lg:static z-50 h-full relative',
          isCollapsed && !isMobile ? 'w-20' : 'w-64',
          isMobile ? (isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full') : ''
        ]"
      >
        <!-- Logo -->
        <div class="p-4 lg:p-6 border-b border-border">
          <div class="flex items-center" :class="isCollapsed && !isMobile ? 'justify-center' : 'justify-between space-x-3'">
            <NuxtLink 
              to="/dashboard" 
              class="flex items-center space-x-3 hover:opacity-80 transition-opacity"
              :class="{ 'opacity-0 w-0 h-0 overflow-hidden': isCollapsed && !isMobile }"
              @click="closeMobileMenu"
            >
              <div class="w-10 h-10 rounded-lg overflow-hidden flex items-end justify-center relative">
                <div class="absolute inset-0 bg-[#1a0d2e]/80"></div>
                <div class="absolute inset-0 bg-gradient-to-b transition-colors" :class="colorMode.value === 'darth-vadarr' ? 'from-red-900/60 to-[#1a0d2e]/90' : 'from-purple-900/60 to-[#1a0d2e]/90'"></div>
                <div class="absolute inset-0 bg-[#0a0515]/70"></div>
                <img src="/vadarr-icon-white-red.svg" alt="DarthVadarr" class="w-7 h-7 relative z-10" />
              </div>
              <div>
                <h1 class="text-lg lg:text-xl font-bold text-foreground transition-opacity duration-300">DarthVadarr</h1>
                <p class="text-xs text-muted-foreground transition-opacity duration-300">SeerrBridge Dashboard</p>
              </div>
            </NuxtLink>
            <div class="flex items-center gap-2">
              <NuxtLink 
                v-if="isCollapsed && !isMobile" 
                to="/dashboard"
                class="flex justify-center hover:opacity-80 transition-opacity"
              >
                <div class="w-10 h-10 rounded-lg overflow-hidden flex items-end justify-center relative">
                  <div class="absolute inset-0 bg-[#1a0d2e]/80"></div>
                  <div class="absolute inset-0 bg-gradient-to-b transition-colors" :class="colorMode.value === 'darth-vadarr' ? 'from-red-900/60 to-[#1a0d2e]/90' : 'from-purple-900/60 to-[#1a0d2e]/90'"></div>
                  <div class="absolute inset-0 bg-[#0a0515]/70"></div>
                  <img src="/vadarr-icon-white-red.svg" alt="DarthVadarr" class="w-7 h-7 relative z-10" />
                </div>
              </NuxtLink>
              <button
                v-if="isMobile"
                @click="closeMobileMenu"
                class="p-2 hover:bg-muted rounded-lg transition-colors lg:hidden"
                title="Close menu"
              >
                <AppIcon icon="lucide:x" size="20" class="text-foreground" />
              </button>
            </div>
          </div>
        </div>

        <!-- Navigation -->
        <nav class="flex-1 p-3 lg:p-4 space-y-2 overflow-y-auto">
          <NuxtLink
            to="/dashboard"
            class="nav-link group relative"
            :class="[isCollapsed && !isMobile ? 'justify-center' : 'justify-start', { 'nav-link-active': $route.path === '/dashboard' || $route.path === '/' }]"
            @click="closeMobileMenu"
          >
            <AppIcon icon="lucide:home" size="18" class="nav-icon" />
            <span :class="{ 'opacity-0 w-0 overflow-hidden': isCollapsed && !isMobile }" class="transition-all duration-300">Dashboard</span>
          </NuxtLink>
          
          <NuxtLink
            to="/processed-media"
            class="nav-link group relative"
            :class="[isCollapsed && !isMobile ? 'justify-center' : 'justify-start', { 'nav-link-active': $route.path === '/processed-media' }]"
            @click="closeMobileMenu"
          >
            <AppIcon icon="lucide:film" size="18" class="nav-icon" />
            <span :class="{ 'opacity-0 w-0 overflow-hidden': isCollapsed && !isMobile }" class="transition-all duration-300">Processed Media</span>
          </NuxtLink>
          
          <NuxtLink
            to="/search"
            class="nav-link group relative"
            :class="[isCollapsed && !isMobile ? 'justify-center' : 'justify-start', { 'nav-link-active': $route.path === '/search' }]"
            @click="closeMobileMenu"
          >
            <AppIcon icon="lucide:search" size="18" class="nav-icon" />
            <span :class="{ 'opacity-0 w-0 overflow-hidden': isCollapsed && !isMobile }" class="transition-all duration-300">Search Media</span>
          </NuxtLink>
          
          <NuxtLink
            to="/collections"
            class="nav-link group relative"
            :class="[isCollapsed && !isMobile ? 'justify-center' : 'justify-start', { 'nav-link-active': $route.path.startsWith('/collections') }]"
            @click="closeMobileMenu"
          >
            <AppIcon icon="lucide:folder" size="18" class="nav-icon" />
            <span :class="{ 'opacity-0 w-0 overflow-hidden': isCollapsed && !isMobile }" class="transition-all duration-300">Collections</span>
          </NuxtLink>
          
          <NuxtLink
            to="/list-sync"
            class="nav-link group relative"
            :class="[isCollapsed && !isMobile ? 'justify-center' : 'justify-start', { 'nav-link-active': $route.path.startsWith('/list-sync') }]"
            @click="closeMobileMenu"
          >
            <AppIcon icon="lucide:list" size="18" class="nav-icon" />
            <span :class="{ 'opacity-0 w-0 overflow-hidden': isCollapsed && !isMobile }" class="transition-all duration-300">List Sync</span>
          </NuxtLink>
          
          <NuxtLink
            to="/logs/all"
            class="nav-link group relative"
            :class="[isCollapsed && !isMobile ? 'justify-center' : 'justify-start', { 'nav-link-active': $route.path.startsWith('/logs') }]"
            @click="closeMobileMenu"
          >
            <AppIcon icon="lucide:file-text" size="18" class="nav-icon" />
            <span :class="{ 'opacity-0 w-0 overflow-hidden': isCollapsed && !isMobile }" class="transition-all duration-300">Logs</span>
          </NuxtLink>
          
          <NuxtLink
            to="/dashboard/database"
            class="nav-link group relative"
            :class="[isCollapsed && !isMobile ? 'justify-center' : 'justify-start', { 'nav-link-active': $route.path === '/dashboard/database' }]"
            @click="closeMobileMenu"
          >
            <AppIcon icon="lucide:database" size="18" class="nav-icon" />
            <span :class="{ 'opacity-0 w-0 overflow-hidden': isCollapsed && !isMobile }" class="transition-all duration-300">Database</span>
          </NuxtLink>
          
          <NuxtLink
            to="/dashboard/settings"
            class="nav-link group relative"
            :class="[isCollapsed && !isMobile ? 'justify-center' : 'justify-start', { 'nav-link-active': $route.path.startsWith('/dashboard/settings') }]"
            @click="closeMobileMenu"
          >
            <AppIcon icon="lucide:settings" size="18" class="nav-icon" />
            <span :class="{ 'opacity-0 w-0 overflow-hidden': isCollapsed && !isMobile }" class="transition-all duration-300">Settings</span>
          </NuxtLink>
        </nav>

        <!-- User section -->
        <div class="p-3 lg:p-4 border-t border-border">
          <div class="flex items-center" :class="isCollapsed && !isMobile ? 'justify-center' : 'space-x-3'">
            <div class="w-8 h-8 bg-primary/10 rounded-full flex items-center justify-center flex-shrink-0 overflow-hidden">
              <img src="/vadarr-icon.svg" alt="Admin" class="w-full h-full object-cover" />
            </div>
            <div class="flex-1 min-w-0" :class="{ 'opacity-0 w-0 overflow-hidden': isCollapsed && !isMobile }">
              <p class="text-sm font-medium text-foreground truncate">Admin</p>
              <p class="text-xs text-muted-foreground">System User</p>
            </div>
            <button
              @click="toggleTheme"
              class="p-1.5 hover:bg-muted rounded-md transition-colors flex-shrink-0"
              :class="{ 'mx-auto': isCollapsed && !isMobile }"
              :title="colorMode.value === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'"
            >
              <AppIcon 
                :icon="colorMode.value === 'light' ? 'lucide:sun' : colorMode.value === 'darth-vadarr' ? 'lucide:sparkles' : 'lucide:moon'" 
                size="16" 
              />
            </button>
          </div>
        </div>
      </aside>

      <!-- Main content area -->
      <div class="flex-1 flex flex-col overflow-hidden relative z-10 w-full min-w-0 left-0 lg:left-auto">
        <!-- Top bar -->
        <header class="h-14 sm:h-16 bg-card border-b border-border flex items-center justify-between px-3 sm:px-4 lg:px-6 gap-2 sm:gap-3">
          <div class="flex items-center space-x-2 sm:space-x-4 min-w-0 flex-1">
            <button
              @click="isMobile ? toggleMobileMenu() : toggleSidebar()"
              class="p-1.5 sm:p-2 hover:bg-muted rounded-lg transition-colors flex-shrink-0"
              :title="isMobile ? 'Toggle menu' : (isCollapsed ? 'Expand sidebar' : 'Collapse sidebar')"
            >
              <AppIcon 
                :icon="isMobile ? 'lucide:menu' : (isCollapsed ? 'lucide:chevrons-right' : 'lucide:chevrons-left')" 
                size="18" 
                class="text-foreground" 
              />
            </button>
            <h2 class="text-base sm:text-lg font-semibold text-foreground truncate">
              {{ pageTitle }}
            </h2>
          </div>
          
          <div class="flex items-center space-x-1.5 sm:space-x-3 flex-shrink-0">
            <NotificationHistory />
            
            <div class="hidden sm:block w-px h-6 bg-border" />
            
            <LiveStatus />
          </div>
        </header>

        <!-- Page content -->
        <main class="flex-1 overflow-auto">
          <div class="p-4 lg:p-6 max-w-7xl mx-auto w-full">
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

// Mobile detection
const isMobile = ref(false)
const isMobileMenuOpen = ref(false)

// Check if mobile on mount and resize
onMounted(() => {
  const checkMobile = () => {
    isMobile.value = window.innerWidth < 1024 // lg breakpoint
    if (!isMobile.value) {
      isMobileMenuOpen.value = false
    }
  }
  checkMobile()
  window.addEventListener('resize', checkMobile)
  onUnmounted(() => window.removeEventListener('resize', checkMobile))
})

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

const toggleMobileMenu = () => {
  isMobileMenuOpen.value = !isMobileMenuOpen.value
}

const closeMobileMenu = () => {
  isMobileMenuOpen.value = false
}

// Close mobile menu on route change
watch(() => route.path, () => {
  if (isMobile.value) {
    closeMobileMenu()
  }
})

// Lock body scroll when mobile menu is open
watch(isMobileMenuOpen, (open) => {
  if (process.client) {
    if (open) {
      document.body.classList.add('menu-open')
    } else {
      document.body.classList.remove('menu-open')
    }
  }
})

// Cleanup on unmount
onUnmounted(() => {
  if (process.client) {
    document.body.classList.remove('menu-open')
  }
})

// Theme definitions
const themes = [
  { value: 'light', name: 'Light' },
  { value: 'dark', name: 'SeerrBridge' },
  { value: 'darth-vadarr', name: 'Darth Vadarr' }
]

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
}

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

const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    '/': 'Dashboard',
    '/dashboard': 'Dashboard',
    '/processed-media': 'Processed Media',
    '/search': 'Search Media',
    '/collections': 'Collections',
    '/list-sync': 'List Sync',
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
  @apply flex items-center px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200;
  @apply text-muted-foreground hover:text-foreground hover:bg-muted/50;
  position: relative;
  gap: 0.75rem; /* Consistent 12px gap between icon and text */
}

/* Icon spacing and styling */
.nav-icon {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  transition: color 0.2s ease;
}

/* When collapsed, remove gap since icon is centered */
.nav-link.justify-center {
  gap: 0;
}

.nav-link span {
  white-space: nowrap;
}

.nav-link-active {
  @apply text-white bg-primary/20 border-r-2 border-primary;
}

/* Make icon white when active */
.nav-link-active .nav-icon {
  color: white !important;
}

/* Mobile menu styles */
@media (max-width: 1023px) {
  aside {
    box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1);
  }
  
  /* Ensure main content takes full width on mobile when sidebar is fixed */
  /* The sidebar is fixed, so it doesn't take up space in the flex layout */
  .flex.h-screen > div:last-child {
    width: 100% !important;
    max-width: 100% !important;
    margin-left: 0 !important;
    padding-left: 0 !important;
    left: 0 !important;
    flex: 1 1 100% !important;
    min-width: 0 !important;
  }
  
  /* Ensure the flex container itself takes full width and doesn't reserve space for fixed sidebar */
  .flex.h-screen {
    width: 100% !important;
    max-width: 100% !important;
  }
  
  /* On mobile, the fixed sidebar should not affect flex layout */
  .flex.h-screen > aside.fixed {
    /* Fixed elements are out of flow, so flex won't reserve space */
  }
  
  /* Ensure fixed sidebar doesn't affect layout flow */
  aside.fixed {
    position: fixed;
    left: 0;
    top: 0;
  }
}

/* Prevent body scroll when mobile menu is open */
:global(body.menu-open) {
  overflow: hidden;
}

</style>
