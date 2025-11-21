export default defineNuxtRouteMiddleware((to) => {
  // Skip middleware on server-side
  if (process.server) return

  // Only run on client-side
  if (process.client) {
    // Check if we're already on setup page
    if (to.path === '/setup') return

    // Check setup status
    $fetch('/api/setup-status').then((response) => {
      if (response.data?.needsSetup) {
        navigateTo('/setup')
      }
    }).catch((error) => {
      console.error('Error checking setup status:', error)
    })
  }
})
