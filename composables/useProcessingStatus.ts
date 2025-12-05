export const useProcessingStatus = () => {
  const route = useRoute()
  
  // Create a reactive cache key that changes based on route and timestamp
  const cacheKey = computed(() => {
    const timestamp = Date.now()
    return `processing-status-${route.path}-${Math.floor(timestamp / 5000)}` // Refresh every 5 seconds
  })

  const { data: processingData, pending, error, refresh } = useLazyAsyncData(
    cacheKey,
    async () => {
      try {
        const response = await $fetch('/api/processing-status')
        if (response.success) {
          return response.data
        }
        return {
          currentItem: null,
          queuedItems: [],
          processingItems: [],
          stats: {
            total_processing: 0,
            movies_processing: 0,
            tv_processing: 0
          },
          queueStats: {
            movie_queue_size: 0,
            movie_queue_max: 250,
            tv_queue_size: 0,
            tv_queue_max: 250,
            total_queued: 0,
            is_processing: false
          }
        }
      } catch (err) {
        console.error('Error fetching processing status:', err)
        return {
          currentItem: null,
          queuedItems: [],
          processingItems: [],
          stats: {
            total_processing: 0,
            movies_processing: 0,
            tv_processing: 0
          },
          queueStats: {
            movie_queue_size: 0,
            movie_queue_max: 250,
            tv_queue_size: 0,
            tv_queue_max: 250,
            total_queued: 0,
            is_processing: false
          }
        }
      }
    },
    {
      server: false,
      default: () => ({
        currentItem: null,
        queuedItems: [],
        processingItems: [],
        stats: {
          total_processing: 0,
          movies_processing: 0,
          tv_processing: 0
        },
        queueStats: {
          movie_queue_size: 0,
          movie_queue_max: 250,
          tv_queue_size: 0,
          tv_queue_max: 250,
          total_queued: 0,
          is_processing: false
        }
      })
    }
  )

  // Auto-refresh when on dashboard (client-side only)
  let refreshInterval: NodeJS.Timeout | null = null

  onMounted(() => {
    if (process.client && (route.path === '/dashboard' || route.path === '/')) {
      // Start auto-refresh every 5 seconds
      refreshInterval = setInterval(() => {
        refresh()
      }, 5000)
    }
  })

  onUnmounted(() => {
    if (refreshInterval) {
      clearInterval(refreshInterval)
    }
  })

  // Watch for route changes (client-side only)
  if (process.client) {
    watch(() => route.path, (newPath) => {
      if (refreshInterval) {
        clearInterval(refreshInterval)
        refreshInterval = null
      }
      
      if (newPath === '/dashboard' || newPath === '/') {
        refreshInterval = setInterval(() => {
          refresh()
        }, 5000)
      }
    })
  }

  return {
    processingData,
    pending,
    error,
    refresh
  }
}

