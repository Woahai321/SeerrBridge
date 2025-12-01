import { useLogs } from '~/composables/useLogs'

export const useDashboardData = () => {
  const { fetchLogs } = useLogs()
  const route = useRoute()
  
  // Create a reactive cache key that changes based on route and timestamp
  const cacheKey = computed(() => {
    const timestamp = Date.now()
    return `dashboard-logs-${route.path}-${Math.floor(timestamp / 30000)}` // Refresh every 30 seconds
  })

  const { data: logsData, pending, error, refresh } = useLazyAsyncData(cacheKey, fetchLogs, {
    server: false,
    default: () => ({ 
      recentLogs: [], 
      statistics: { 
        totalLogs: 0, 
        successCount: 0, 
        errorCount: 0, 
        warningCount: 0, 
        infoCount: 0, 
        failedEpisodes: 0, 
        successfulGrabs: 0, 
        criticalErrors: 0, 
        tokenStatus: null, 
        recentSuccesses: [], 
        recentFailures: [] 
      } 
    })
  })

  // Watch for route changes and refresh data when returning to dashboard
  watch(() => route.path, (newPath, oldPath) => {
    if (newPath === '/dashboard' && oldPath && oldPath !== '/dashboard') {
      console.log('Returning to dashboard, refreshing data...')
      refresh()
    }
  }, { immediate: false })

  // Refresh data on component mount if we're on the dashboard
  onMounted(() => {
    if (route.path === '/dashboard') {
      console.log('Dashboard mounted, refreshing data...')
      refresh()
    }
  })

  // Refresh data when user returns to the tab (if on dashboard)
  onMounted(() => {
    const handleVisibilityChange = () => {
      if (!document.hidden && route.path === '/dashboard') {
        console.log('Tab became visible, refreshing dashboard data...')
        refresh()
      }
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)
    
    onUnmounted(() => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    })
  })

  // Expose a manual refresh function
  const refreshData = async () => {
    console.log('Manually refreshing dashboard data...')
    await refresh()
  }

  return {
    logsData,
    pending,
    error,
    refreshData
  }
}
