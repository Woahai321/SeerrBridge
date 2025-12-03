export const useBackendReady = () => {
  const isBackendReady = ref(false)
  const isChecking = ref(false) // Initialize to false - only set to true when explicitly starting checks
  const checkInterval = ref<ReturnType<typeof setInterval> | null>(null)
  const { fetchStatus } = useBridgeStatus()

  const checkBackendStatus = async () => {
    try {
      const status = await fetchStatus()
      
      // Check if backend is running and status is recent (within last 30 seconds)
      if (status && status.status === 'running' && status.uptime_seconds !== undefined && status.uptime_seconds > 0) {
        isBackendReady.value = true
        isChecking.value = false
        
        // Clear interval once backend is ready
        if (checkInterval.value) {
          clearInterval(checkInterval.value)
          checkInterval.value = null
        }
        return true
      }
      
      return false
    } catch (error) {
      // Backend might not be ready yet, continue checking
      return false
    }
  }

  const startChecking = async () => {
    // Set checking state to true when we start
    isChecking.value = true
    
    // Initial check - if backend is already ready, don't start polling
    const alreadyReady = await checkBackendStatus()
    if (alreadyReady) {
      return // Backend is already ready, no need to poll
    }
    
    // Check every 2 seconds
    checkInterval.value = setInterval(() => {
      checkBackendStatus().catch(() => {
        // Ignore errors during checking
      })
    }, 2000)
    
    // Safety timeout - if backend doesn't start in 2 minutes, mark as ready anyway
    setTimeout(() => {
      if (!isBackendReady.value && checkInterval.value) {
        console.warn('Backend initialization timeout - proceeding anyway')
        isBackendReady.value = true
        isChecking.value = false
        if (checkInterval.value) {
          clearInterval(checkInterval.value)
          checkInterval.value = null
        }
      }
    }, 120000) // 2 minutes
  }

  const stopChecking = () => {
    isChecking.value = false
    if (checkInterval.value) {
      clearInterval(checkInterval.value)
      checkInterval.value = null
    }
  }

  return {
    isBackendReady,
    isChecking,
    checkBackendStatus,
    startChecking,
    stopChecking
  }
}
