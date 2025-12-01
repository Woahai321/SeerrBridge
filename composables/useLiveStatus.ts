import { useBridgeStatus } from '~/composables/useBridgeStatus'

interface LiveStatusData {
  status: string
  uptime: string
  version: string
  lastCheck: string
  queueStatus: {
    movieQueueSize: number
    tvQueueSize: number
    isProcessing: boolean
    totalQueued: number
  }
  browserStatus: string
  libraryStats: {
    torrentsCount: number
    totalSizeTb: number
    lastUpdated: string
  }
  services: {
    database: boolean
    seerrbridge: boolean
    overseerr: boolean
    realdebrid: boolean
    trakt: boolean
  }
}

export const useLiveStatus = () => {
  const { fetchStatus } = useBridgeStatus()
  
  // Reactive status data
  const statusData = ref<LiveStatusData | null>(null)
  const isConnected = ref(false)
  const isConnecting = ref(true)
  const lastUpdate = ref<Date | null>(null)
  const updateInterval = ref<NodeJS.Timeout | null>(null)
  const connectionStartTime = ref<Date | null>(null)
  const retryCount = ref(0)
  const maxRetries = 3
  
  // Status colors and indicators based on connection state
  const getStatusColor = () => {
    if (connectionState.value === 'live') {
      // Use the actual service status when live
      const serviceStatus = statusData.value?.status || 'unknown'
      switch (serviceStatus) {
        case 'running': return 'text-success'
        case 'error': return 'text-destructive'
        case 'warning': return 'text-warning'
        default: return 'text-success' // Default to success when live
      }
    }
    
    switch (connectionState.value) {
      case 'connecting': return 'text-warning'
      case 'offline': return 'text-destructive'
      default: return 'text-muted-foreground'
    }
  }
  
  const getStatusIcon = () => {
    if (connectionState.value === 'live') {
      // Use the actual service status when live
      const serviceStatus = statusData.value?.status || 'unknown'
      switch (serviceStatus) {
        case 'running': return 'lucide:check-circle'
        case 'error': return 'lucide:x-circle'
        case 'warning': return 'lucide:alert-circle'
        default: return 'lucide:check-circle' // Default to check when live
      }
    }
    
    switch (connectionState.value) {
      case 'connecting': return 'lucide:loader-2'
      case 'offline': return 'lucide:x-circle'
      default: return 'lucide:activity'
    }
  }
  
  // Check if we should show offline (after 30 seconds of trying)
  const shouldShowOffline = computed(() => {
    if (!connectionStartTime.value) return false
    const timeSinceStart = Date.now() - connectionStartTime.value.getTime()
    return timeSinceStart > 30000 // 30 seconds
  })

  // Get current connection state
  const connectionState = computed(() => {
    if (isConnected.value) return 'live'
    if (isConnecting.value && !shouldShowOffline.value) return 'connecting'
    return 'offline'
  })

  // Fetch status data
  const updateStatus = async () => {
    try {
      const data = await fetchStatus()
      
      console.log('📡 Received data:', data)
      
      // Check if the response indicates an error
      if (data && data.status === 'error') {
        throw new Error(data.message || 'SeerrBridge connection failed')
      }
      
      // Validate the response data
      if (!data || typeof data !== 'object') {
        throw new Error('Invalid response data')
      }
      
      // Ensure we have the required status field
      if (!data.status) {
        throw new Error('Missing status field in response')
      }
      
      statusData.value = {
        status: data.status || 'unknown',
        uptime: String(data.uptime || '0s'),
        version: data.version || 'unknown',
        lastCheck: new Date().toLocaleTimeString(),
        queueStatus: {
          movieQueueSize: data.queue_status?.movie_queue_size || 0,
          tvQueueSize: data.queue_status?.tv_queue_size || 0,
          isProcessing: data.queue_status?.is_processing || false,
          totalQueued: data.queue_status?.total_queued || 0
        },
        browserStatus: data.browser_status || 'unknown',
        libraryStats: {
          torrentsCount: data.library_stats?.torrents_count || 0,
          totalSizeTb: data.library_stats?.total_size_tb || 0,
          lastUpdated: data.library_stats?.last_updated || 'never'
        },
        services: {
          database: true, // We know DB is connected if we got this far
          seerrbridge: data.status === 'running',
          overseerr: data.services?.overseerr || false,
          realdebrid: data.services?.realdebrid || false,
          trakt: data.services?.trakt || false
        }
      }
      
      // Successfully connected
      isConnected.value = true
      isConnecting.value = false
      retryCount.value = 0
      lastUpdate.value = new Date()
      
      console.log('✅ Live status connected successfully - Status:', data.status)
    } catch (error) {
      console.error('Failed to fetch live status:', error)
      
      // If we've been trying for more than 30 seconds, show offline
      if (shouldShowOffline.value) {
        isConnected.value = false
        isConnecting.value = false
        retryCount.value++
        console.log(`❌ Live status offline (retry ${retryCount.value}/${maxRetries})`)
      } else {
        // Still in connecting phase
        isConnecting.value = true
      }
    }
  }
  
  // Start live updates
  const startLiveUpdates = (initialIntervalMs = 5000, retryIntervalMs = 30000) => {
    // Set connection start time
    connectionStartTime.value = new Date()
    
    // Reset states
    isConnecting.value = true
    isConnected.value = false
    
    // Immediate first attempt
    updateStatus()
    
    // Set up interval with dynamic timing
    const setupInterval = () => {
      if (updateInterval.value) {
        clearInterval(updateInterval.value)
      }
      
      const intervalMs = isConnected.value ? initialIntervalMs : retryIntervalMs
      updateInterval.value = setInterval(updateStatus, intervalMs)
      
      console.log(`⏰ Set interval to ${intervalMs}ms - Connected: ${isConnected.value}`)
    }
    
    // Set up initial interval
    setupInterval()
    
    // Watch for connection state changes to adjust interval
    watch([isConnected, retryCount], () => {
      setupInterval()
    })
  }
  
  // Stop live updates
  const stopLiveUpdates = () => {
    if (updateInterval.value) {
      clearInterval(updateInterval.value)
      updateInterval.value = null
    }
  }
  
  // Format uptime for display
  const formatUptime = (uptime: string) => {
    return uptime || '0s'
  }
  
  // Format library size
  const formatLibrarySize = (sizeTb: number) => {
    if (sizeTb >= 1000) {
      return `${(sizeTb / 1000).toFixed(1)} PB`
    }
    return `${sizeTb.toFixed(1)} TB`
  }
  
  // Get service status summary
  const getServiceSummary = () => {
    if (!statusData.value) return 'Unknown'
    
    const { services } = statusData.value
    const totalServices = Object.keys(services).length
    const activeServices = Object.values(services).filter(Boolean).length
    
    return `${activeServices}/${totalServices} services active`
  }
  
  // Cleanup on unmount
  onUnmounted(() => {
    stopLiveUpdates()
  })
  
  return {
    // State
    statusData: readonly(statusData),
    isConnected: readonly(isConnected),
    isConnecting: readonly(isConnecting),
    connectionState: readonly(connectionState),
    lastUpdate: readonly(lastUpdate),
    retryCount: readonly(retryCount),
    
    // Methods
    updateStatus,
    startLiveUpdates,
    stopLiveUpdates,
    
    // Utilities
    getStatusColor,
    getStatusIcon,
    formatUptime,
    formatLibrarySize,
    getServiceSummary
  }
}
