<template>
  <div 
    ref="containerRef"
    class="relative flex items-center space-x-2 text-sm cursor-pointer group"
    @mouseenter="handleMouseEnter"
    @mouseleave="handleMouseLeave"
  >
    <AppIcon 
      :icon="isConnected ? 'lucide:database' : 'lucide:database-x'" 
      size="16" 
      :class="isConnected ? 'text-success' : 'text-destructive'"
    />
    <div class="flex flex-col">
      <span class="font-medium" :class="isConnected ? 'text-success' : 'text-destructive'">
        {{ isConnected ? 'Database Connected' : 'Database Disconnected' }}
      </span>
      <span v-if="serviceStatus" class="text-xs text-muted-foreground">
        Status: {{ serviceStatus.status }} • Updated: {{ formatTime(serviceStatus.last_updated || serviceStatus.start_time) }}
      </span>
    </div>

    <!-- Hover Tooltip Modal -->
    <div 
      v-if="showTooltip && serviceStatus" 
      class="absolute z-50 w-80 sm:w-96 max-w-[calc(100vw-2rem)] p-4 mt-2 bg-popover border border-border rounded-lg shadow-lg top-full"
      :style="modalPosition"
      @mouseenter="handleModalMouseEnter"
      @mouseleave="handleModalMouseLeave"
    >
      <div class="space-y-3">
        <!-- Header -->
        <div class="flex items-center justify-between border-b border-border pb-2">
          <h3 class="text-lg font-semibold text-popover-foreground">Service Status</h3>
          <div class="flex items-center space-x-2">
            <div 
              class="w-2 h-2 rounded-full" 
              :class="serviceStatus.status === 'running' ? 'bg-success' : 'bg-destructive'"
            ></div>
            <span class="text-sm font-medium capitalize">{{ serviceStatus.status }}</span>
          </div>
        </div>

        <!-- Service Information -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 sm:gap-3 text-sm">
          <div class="flex flex-col sm:flex-row sm:items-center">
            <span class="text-muted-foreground text-xs sm:text-sm">Version:</span>
            <span class="ml-0 sm:ml-2 font-mono text-xs sm:text-sm text-popover-foreground">{{ serviceStatus.version || 'N/A' }}</span>
          </div>
          <div class="flex flex-col sm:flex-row sm:items-center">
            <span class="text-muted-foreground text-xs sm:text-sm">Uptime:</span>
            <span class="ml-0 sm:ml-2 text-xs sm:text-sm text-popover-foreground">{{ serviceStatus.uptime || 'N/A' }}</span>
          </div>
          <div class="flex flex-col sm:flex-row sm:items-center">
            <span class="text-muted-foreground text-xs sm:text-sm">Start Time:</span>
            <span class="ml-0 sm:ml-2 text-xs sm:text-sm text-popover-foreground">{{ formatTime(serviceStatus.start_time) }}</span>
          </div>
          <div class="flex flex-col sm:flex-row sm:items-center">
            <span class="text-muted-foreground text-xs sm:text-sm">Current Time:</span>
            <span class="ml-0 sm:ml-2 text-xs sm:text-sm text-popover-foreground">{{ formatTime(serviceStatus.current_time) }}</span>
          </div>
        </div>

        <!-- Browser Status -->
        <div v-if="serviceStatus.browser_status" class="border-t border-gray-200 dark:border-gray-700 pt-2">
          <div class="flex items-center justify-between">
            <span class="text-muted-foreground">Browser Status:</span>
            <span 
              class="px-2 py-1 rounded text-xs font-medium"
              :class="serviceStatus.browser_status === 'running' ? 'bg-success/10 text-success' : 'bg-destructive/10 text-destructive'"
            >
              {{ serviceStatus.browser_status }}
            </span>
          </div>
        </div>

        <!-- Processing Settings -->
        <div class="border-t border-border pt-2">
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-muted-foreground">Auto Processing:</span>
              <span 
                class="px-2 py-1 rounded text-xs font-medium"
                :class="serviceStatus.automatic_processing ? 'bg-success/10 text-success' : 'bg-muted text-muted-foreground'"
              >
                {{ serviceStatus.automatic_processing ? 'Enabled' : 'Disabled' }}
              </span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-muted-foreground">Show Subscription:</span>
              <span 
                class="px-2 py-1 rounded text-xs font-medium"
                :class="serviceStatus.show_subscription ? 'bg-success/10 text-success' : 'bg-muted text-muted-foreground'"
              >
                {{ serviceStatus.show_subscription ? 'Enabled' : 'Disabled' }}
              </span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-muted-foreground">Refresh Interval:</span>
              <span class="font-mono">{{ serviceStatus.refresh_interval_minutes }}m</span>
            </div>
          </div>
        </div>

        <!-- Queue Status -->
        <div v-if="serviceStatus.queue_status" class="border-t border-gray-200 dark:border-gray-700 pt-2">
          <h4 class="text-sm font-medium text-popover-foreground mb-2">Queue Status</h4>
          <div class="bg-muted rounded p-2">
            <pre class="text-xs text-muted-foreground whitespace-pre-wrap">{{ JSON.stringify(serviceStatus.queue_status, null, 2) }}</pre>
          </div>
        </div>

        <!-- Library Stats -->
        <div v-if="serviceStatus.library_stats" class="border-t border-gray-200 dark:border-gray-700 pt-2">
          <h4 class="text-sm font-medium text-popover-foreground mb-2">Library Stats</h4>
          <div class="bg-muted rounded p-2">
            <pre class="text-xs text-muted-foreground whitespace-pre-wrap">{{ JSON.stringify(serviceStatus.library_stats, null, 2) }}</pre>
          </div>
        </div>

        <!-- Queue Activity -->
        <div v-if="serviceStatus.queue_activity" class="border-t border-gray-200 dark:border-gray-700 pt-2">
          <h4 class="text-sm font-medium text-popover-foreground mb-2">Queue Activity</h4>
          <div class="bg-muted rounded p-2">
            <pre class="text-xs text-muted-foreground whitespace-pre-wrap">{{ JSON.stringify(serviceStatus.queue_activity, null, 2) }}</pre>
          </div>
        </div>

        <!-- Services Status -->
        <div v-if="serviceStatus.services" class="border-t border-gray-200 dark:border-gray-700 pt-2">
          <h4 class="text-sm font-medium text-popover-foreground mb-2">Services</h4>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <div 
              v-for="(status, service) in serviceStatus.services" 
              :key="service"
              class="flex items-center justify-between"
            >
              <span class="text-xs sm:text-sm capitalize">{{ service }}:</span>
              <div class="flex items-center space-x-1">
                <div 
                  class="w-2 h-2 rounded-full" 
                  :class="status ? 'bg-success' : 'bg-destructive'"
                ></div>
                <span class="text-xs">{{ status ? 'Online' : 'Offline' }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Last Check -->
        <div class="border-t border-border pt-2 text-xs text-muted-foreground">
          Last Check: {{ serviceStatus.last_check || 'N/A' }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useApi } from '~/composables/useApi'

interface ServiceStatus {
  status: string
  last_updated?: string
  version?: string
  uptime?: string
  uptime_seconds?: number
  start_time?: string
  current_time?: string
  queue_status?: any
  browser_status?: string
  automatic_processing?: boolean
  show_subscription?: boolean
  refresh_interval_minutes?: number
  library_stats?: any
  queue_activity?: any
  last_check?: string
  services?: {
    database?: boolean
    seerrbridge?: boolean
    overseerr?: boolean
    realdebrid?: boolean
    trakt?: boolean
  }
}

const { apiCall } = useApi()
const isConnected = ref(false)
const serviceStatus = ref<ServiceStatus | null>(null)
const showTooltip = ref(false)
const isNearRightEdge = ref(false)
const containerRef = ref<HTMLElement | null>(null)
const modalPosition = ref({ left: '0px', right: 'auto' })
let tooltipTimeout: NodeJS.Timeout | null = null

// Check database connection and get service status
const checkDatabaseStatus = async () => {
  try {
    console.log('🔍 LiveStatus: Checking database connection via /service-status...')
    
    // Try to fetch service status to test database connection
    const statusData = await apiCall<ServiceStatus>('/service-status')
    
    console.log('📊 LiveStatus: Service status response:', statusData)
    
    if (statusData) {
      isConnected.value = true
      serviceStatus.value = statusData
      console.log('✅ LiveStatus: Database connected, status:', statusData.status)
      console.log('📅 LiveStatus: Timestamps - last_updated:', statusData.last_updated, 'start_time:', statusData.start_time)
    } else {
      isConnected.value = false
      serviceStatus.value = null
      console.log('❌ LiveStatus: No status data received')
    }
  } catch (error) {
    console.error('❌ LiveStatus: Database connection failed:', error)
    isConnected.value = false
    serviceStatus.value = null
  }
}

const formatTime = (timestamp: string) => {
  if (!timestamp) return 'Unknown'
  
  try {
    const date = new Date(timestamp)
    if (isNaN(date.getTime())) {
      return 'Invalid Date'
    }
    return date.toLocaleTimeString()
  } catch (error) {
    console.error('Date formatting error:', error, 'for timestamp:', timestamp)
    return 'Invalid Date'
  }
}

const handleMouseEnter = () => {
  if (tooltipTimeout) {
    clearTimeout(tooltipTimeout)
  }
  
  // Calculate modal position to prevent off-screen display
  if (containerRef.value) {
    const rect = containerRef.value.getBoundingClientRect()
    const viewportWidth = window.innerWidth
    const modalWidth = 320 // w-80 = 20rem = 320px on mobile, 384px on desktop
    const spaceOnRight = viewportWidth - rect.left
    const spaceOnLeft = rect.left
    
    // Check if modal would go off-screen on the right
    if (spaceOnRight < modalWidth + 20) {
      // Position to the right of the container
      modalPosition.value = { 
        left: 'auto', 
        right: '0px' 
      }
      isNearRightEdge.value = true
    } else if (spaceOnLeft < modalWidth + 20) {
      // Position to the left of the container
      modalPosition.value = { 
        left: `-${modalWidth}px`, 
        right: 'auto' 
      }
      isNearRightEdge.value = false
    } else {
      // Default position (left-aligned with container)
      modalPosition.value = { 
        left: '0px', 
        right: 'auto' 
      }
      isNearRightEdge.value = false
    }
  }
  
  tooltipTimeout = setTimeout(() => {
    showTooltip.value = true
  }, 300) // 300ms delay
}

const handleMouseLeave = () => {
  if (tooltipTimeout) {
    clearTimeout(tooltipTimeout)
    tooltipTimeout = null
  }
  // Add a small delay before hiding to allow moving to modal
  tooltipTimeout = setTimeout(() => {
    showTooltip.value = false
  }, 100)
}

const handleModalMouseEnter = () => {
  // Clear any pending hide timeout when hovering over modal
  if (tooltipTimeout) {
    clearTimeout(tooltipTimeout)
    tooltipTimeout = null
  }
}

const handleModalMouseLeave = () => {
  // Hide modal when leaving the modal area
  showTooltip.value = false
}

// Check on mount and every 30 seconds
onMounted(() => {
  checkDatabaseStatus()
  setInterval(checkDatabaseStatus, 30000)
  
  // Add resize listener to recalculate position
  window.addEventListener('resize', handleWindowResize)
})

// Cleanup timeout on unmount
onUnmounted(() => {
  if (tooltipTimeout) {
    clearTimeout(tooltipTimeout)
  }
  window.removeEventListener('resize', handleWindowResize)
})

const handleWindowResize = () => {
  // Recalculate position if modal is currently visible
  if (showTooltip.value && containerRef.value) {
    handleMouseEnter()
  }
}
</script>