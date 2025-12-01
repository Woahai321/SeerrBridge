<template>
  <div>
    <div 
      ref="containerRef"
      class="relative flex items-center space-x-1.5 sm:space-x-2 text-xs sm:text-sm cursor-pointer group"
      @mouseenter="handleMouseEnter"
      @mouseleave="handleMouseLeave"
      @click="handleClick"
    >
    <AppIcon 
      :icon="isConnected ? 'lucide:database' : 'lucide:database-x'" 
      size="16" 
      class="flex-shrink-0"
      :class="isConnected ? 'text-success' : 'text-destructive'"
    />
    <div class="flex flex-col min-w-0">
      <span class="font-medium truncate" :class="isConnected ? 'text-success' : 'text-destructive'">
        <span class="hidden sm:inline">{{ isConnected ? 'Database Connected' : 'Database Disconnected' }}</span>
        <span class="sm:hidden">{{ isConnected ? 'Connected' : 'Disconnected' }}</span>
      </span>
      <span v-if="serviceStatus" class="text-[10px] sm:text-xs text-muted-foreground truncate">
        <span class="hidden sm:inline">Status: {{ serviceStatus.status }} • Updated: {{ formatTime(serviceStatus.last_updated || serviceStatus.start_time) }}</span>
        <span class="sm:hidden">{{ serviceStatus.status }} • {{ formatTime(serviceStatus.last_updated || serviceStatus.start_time) }}</span>
      </span>
    </div>
    </div>

    <Teleport to="body">
      <!-- Mobile overlay -->
      <div 
        v-if="showTooltip && isMobile"
        class="fixed inset-0 bg-black/50 z-[99998] sm:hidden"
        @click="showTooltip = false"
      />
      
      <!-- Hover Tooltip Modal -->
      <div 
        v-if="showTooltip && serviceStatus" 
        class="live-status-modal fixed z-[99999] sm:w-80 lg:w-96 max-h-[85vh] sm:max-h-none bg-popover border border-border rounded-lg shadow-lg overflow-hidden flex flex-col"
        :style="modalStyle"
        @mouseenter="handleModalMouseEnter"
        @mouseleave="handleModalMouseLeave"
        @click.stop
      >
      <div class="overflow-y-auto flex-1 p-3 sm:p-4 space-y-3">
        <!-- Header -->
        <div class="flex items-center justify-between border-b border-border pb-2 flex-shrink-0">
          <h3 class="text-base sm:text-lg font-semibold text-popover-foreground">Service Status</h3>
          <div class="flex items-center space-x-2">
            <button
              v-if="isMobile"
              @click="showTooltip = false"
              class="p-1 hover:bg-muted rounded transition-colors"
            >
              <AppIcon icon="lucide:x" size="16" />
            </button>
            <div 
              class="w-2 h-2 rounded-full" 
              :class="serviceStatus.status === 'running' ? 'bg-success' : 'bg-destructive'"
            ></div>
            <span class="text-xs sm:text-sm font-medium capitalize">{{ serviceStatus.status }}</span>
          </div>
        </div>

        <!-- Service Information -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 sm:gap-3 text-xs sm:text-sm">
          <div class="flex flex-col sm:flex-row sm:items-center">
            <span class="text-muted-foreground">Version:</span>
            <span class="ml-0 sm:ml-2 font-mono text-popover-foreground break-all">{{ serviceStatus.version || 'N/A' }}</span>
          </div>
          <div class="flex flex-col sm:flex-row sm:items-center">
            <span class="text-muted-foreground">Uptime:</span>
            <span class="ml-0 sm:ml-2 text-popover-foreground break-all">{{ serviceStatus.uptime || 'N/A' }}</span>
          </div>
          <div class="flex flex-col sm:flex-row sm:items-center">
            <span class="text-muted-foreground">Start Time:</span>
            <span class="ml-0 sm:ml-2 text-popover-foreground break-all">{{ formatTime(serviceStatus.start_time) }}</span>
          </div>
          <div class="flex flex-col sm:flex-row sm:items-center">
            <span class="text-muted-foreground">Current Time:</span>
            <span class="ml-0 sm:ml-2 text-popover-foreground break-all">{{ formatTime(serviceStatus.current_time) }}</span>
          </div>
        </div>

        <!-- Browser Status -->
        <div v-if="serviceStatus.browser_status" class="border-t border-gray-200 dark:border-gray-700 pt-2">
          <div class="flex items-center justify-between flex-wrap gap-1">
            <span class="text-xs sm:text-sm text-muted-foreground">Browser Status:</span>
            <span 
              class="px-2 py-1 rounded text-xs font-medium whitespace-nowrap"
              :class="serviceStatus.browser_status === 'running' ? 'bg-success/10 text-success' : 'bg-destructive/10 text-destructive'"
            >
              {{ serviceStatus.browser_status }}
            </span>
          </div>
        </div>

        <!-- Processing Settings -->
        <div class="border-t border-border pt-2">
          <div class="space-y-2">
            <div class="flex items-center justify-between flex-wrap gap-1">
              <span class="text-xs sm:text-sm text-muted-foreground">Auto Processing:</span>
              <span 
                class="px-2 py-1 rounded text-xs font-medium whitespace-nowrap"
                :class="serviceStatus.automatic_processing ? 'bg-success/10 text-success' : 'bg-muted text-muted-foreground'"
              >
                {{ serviceStatus.automatic_processing ? 'Enabled' : 'Disabled' }}
              </span>
            </div>
            <div class="flex items-center justify-between flex-wrap gap-1">
              <span class="text-xs sm:text-sm text-muted-foreground">Show Subscription:</span>
              <span 
                class="px-2 py-1 rounded text-xs font-medium whitespace-nowrap"
                :class="serviceStatus.show_subscription ? 'bg-success/10 text-success' : 'bg-muted text-muted-foreground'"
              >
                {{ serviceStatus.show_subscription ? 'Enabled' : 'Disabled' }}
              </span>
            </div>
            <div class="flex items-center justify-between flex-wrap gap-1">
              <span class="text-xs sm:text-sm text-muted-foreground">Refresh Interval:</span>
              <span class="text-xs sm:text-sm font-mono whitespace-nowrap">{{ serviceStatus.refresh_interval_minutes }}m</span>
            </div>
          </div>
        </div>

        <!-- Queue Status -->
        <div v-if="serviceStatus.queue_status" class="border-t border-gray-200 dark:border-gray-700 pt-2">
          <h4 class="text-xs sm:text-sm font-medium text-popover-foreground mb-2">Queue Status</h4>
          <div class="bg-muted rounded p-2 overflow-x-auto">
            <pre class="text-[10px] sm:text-xs text-muted-foreground whitespace-pre-wrap break-all">{{ JSON.stringify(serviceStatus.queue_status, null, 2) }}</pre>
          </div>
        </div>

        <!-- Library Stats -->
        <div v-if="serviceStatus.library_stats" class="border-t border-gray-200 dark:border-gray-700 pt-2">
          <h4 class="text-xs sm:text-sm font-medium text-popover-foreground mb-2">Library Stats</h4>
          <div class="bg-muted rounded p-2 overflow-x-auto">
            <pre class="text-[10px] sm:text-xs text-muted-foreground whitespace-pre-wrap break-all">{{ JSON.stringify(serviceStatus.library_stats, null, 2) }}</pre>
          </div>
        </div>

        <!-- Queue Activity -->
        <div v-if="serviceStatus.queue_activity" class="border-t border-gray-200 dark:border-gray-700 pt-2">
          <h4 class="text-xs sm:text-sm font-medium text-popover-foreground mb-2">Queue Activity</h4>
          <div class="bg-muted rounded p-2 overflow-x-auto">
            <pre class="text-[10px] sm:text-xs text-muted-foreground whitespace-pre-wrap break-all">{{ JSON.stringify(serviceStatus.queue_activity, null, 2) }}</pre>
          </div>
        </div>

        <!-- Services Status -->
        <div v-if="serviceStatus.services" class="border-t border-gray-200 dark:border-gray-700 pt-2">
          <h4 class="text-xs sm:text-sm font-medium text-popover-foreground mb-2">Services</h4>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <div 
              v-for="(status, service) in serviceStatus.services" 
              :key="service"
              class="flex items-center justify-between flex-wrap gap-1"
            >
              <span class="text-xs sm:text-sm capitalize">{{ service }}:</span>
              <div class="flex items-center space-x-1">
                <div 
                  class="w-2 h-2 rounded-full flex-shrink-0" 
                  :class="status ? 'bg-success' : 'bg-destructive'"
                ></div>
                <span class="text-xs whitespace-nowrap">{{ status ? 'Online' : 'Offline' }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Last Check -->
        <div class="border-t border-border pt-2 text-[10px] sm:text-xs text-muted-foreground">
          Last Check: {{ serviceStatus.last_check || 'N/A' }}
        </div>
      </div>
    </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { nextTick } from 'vue'
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
const modalPosition = ref({ left: '0px', right: 'auto', top: 'auto', bottom: 'auto', marginTop: '8px', marginBottom: '0px' })
const modalStyle = ref<Record<string, string>>({})
const isMobile = ref(false)
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

const calculateModalPosition = () => {
  if (!containerRef.value) return
  
  const rect = containerRef.value.getBoundingClientRect()
  const viewportWidth = window.innerWidth
  const viewportHeight = window.innerHeight
  const isMobileCheck = viewportWidth < 640 // sm breakpoint
  
  // On mobile, center the modal
  if (isMobileCheck) {
    modalStyle.value = {
      left: '1rem',
      right: '1rem',
      top: '50%',
      transform: 'translateY(-50%)'
    }
    return
  }
  
  // Determine modal width based on screen size
  const modalWidth = viewportWidth >= 1024 ? 384 : 320 // lg:w-96 (384px) or sm:w-80 (320px)
  const modalPadding = 16 // Padding from viewport edges
  const estimatedModalHeight = 400 // Estimated height
  
  // Calculate horizontal positioning (absolute pixel values)
  let left = rect.right - modalWidth
  let right = 'auto'
  
  // Check if modal would overflow on the left
  if (left < modalPadding) {
    // Try positioning to the left of container
    const leftPosition = rect.left - modalWidth
    if (leftPosition >= modalPadding) {
      left = leftPosition
      right = 'auto'
    } else {
      // Not enough space, align to right edge with padding
      left = 'auto'
      right = `${viewportWidth - rect.right}px`
    }
  }
  
  // Calculate vertical positioning
  const spaceBelow = viewportHeight - rect.bottom
  const spaceAbove = rect.top
  const minSpaceNeeded = estimatedModalHeight + modalPadding
  
  let top = 'auto'
  let bottom = 'auto'
  let maxHeight = 'none'
  
  if (spaceBelow < minSpaceNeeded && spaceAbove > spaceBelow) {
    // Position above the container
    bottom = `${viewportHeight - rect.top + 8}px`
    top = 'auto'
    const maxHeightAbove = spaceAbove - modalPadding
    if (maxHeightAbove < estimatedModalHeight) {
      maxHeight = `${maxHeightAbove}px`
    }
  } else {
    // Position below the container (default)
    top = `${rect.bottom + 8}px`
    bottom = 'auto'
    const maxHeightBelow = spaceBelow - modalPadding
    if (maxHeightBelow < estimatedModalHeight) {
      maxHeight = `${maxHeightBelow}px`
    }
  }
  
  modalStyle.value = {
    left: typeof left === 'number' ? `${left}px` : left,
    right: typeof right === 'string' ? right : `${right}px`,
    top: typeof top === 'number' ? `${top}px` : top,
    bottom: typeof bottom === 'number' ? `${bottom}px` : bottom,
    maxHeight,
    transform: 'none'
  }
}

const handleMouseEnter = () => {
  if (tooltipTimeout) {
    clearTimeout(tooltipTimeout)
  }
  
  calculateModalPosition()
  
  tooltipTimeout = setTimeout(() => {
    showTooltip.value = true
    // Recalculate position when showing to ensure accuracy
    nextTick(() => {
      calculateModalPosition()
    })
  }, 300) // 300ms delay
}

const handleClick = () => {
  // On mobile, toggle on click instead of hover
  if (process.client && window.innerWidth < 640) {
    if (!showTooltip.value) {
      calculateModalPosition()
      showTooltip.value = true
      nextTick(() => {
        calculateModalPosition()
      })
    } else {
      showTooltip.value = false
    }
  }
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
  
  // Check if mobile
  const checkMobile = () => {
    isMobile.value = window.innerWidth < 640
  }
  checkMobile()
  
  // Add resize listener to recalculate position
  window.addEventListener('resize', () => {
    handleWindowResize()
    checkMobile()
  })
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
    calculateModalPosition()
  }
}
</script>