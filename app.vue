<template>
  <div class="min-h-screen bg-background text-foreground">
    <!-- Backend Initializing Screen - Show when backend is not ready (as overlay) -->
    <!-- NEVER show on /setup page or during initial setup process -->
    <BackendInitializing 
      v-if="shouldShowBackendInitializing" 
      @ready="handleBackendReady" 
    />
    
    <!-- Main content - Always render to satisfy Nuxt's static analysis -->
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>

    <!-- Notification system -->
    <NotificationSystem />
  </div>
</template>

<script setup lang="ts">
// Global head configuration
useHead({
  title: 'Darth Vadarr - SeerrBridge Dashboard',
  meta: [
    { name: 'description', content: 'Monitor and manage your SeerrBridge service with ease' }
  ],
  link: [
    { rel: 'icon', type: 'image/svg+xml', href: '/vadarr-icon.svg' },
    { rel: 'alternate icon', type: 'image/x-icon', href: '/vadarr-icon.ico' }
  ]
})

// Initialize color mode
const colorMode = useColorMode()

// Backend readiness check
const { isBackendReady, isChecking: isCheckingBackend, startChecking, stopChecking } = useBackendReady()

// Setup status tracking
const setupNeeded = ref(false)
const route = useRoute()

// Check if we should show the backend initializing screen
// NEVER show it on /setup page or when setup is needed
const shouldShowBackendInitializing = computed(() => {
  // Never show on setup page
  if (route.path === '/setup') {
    return false
  }
  
  // Never show when setup is needed
  if (setupNeeded.value) {
    return false
  }
  
  // Only show if backend is not ready and we're checking
  return !isBackendReady.value && isCheckingBackend.value
})

const handleBackendReady = () => {
  // Backend is ready - update state to hide loading screen
  isBackendReady.value = true
  isCheckingBackend.value = false
}

// Check setup status
const checkSetupStatus = async () => {
  try {
    const response = await $fetch('/api/setup-status')
    setupNeeded.value = response?.data?.needsSetup ?? false
  } catch (error) {
    // On error, assume setup is needed to be safe
    console.error('Error checking setup status:', error)
    setupNeeded.value = true
  }
}

// Watch route changes to handle setup page navigation
watch(() => route.path, (newPath) => {
  if (newPath === '/setup') {
    // On setup page - stop checking backend and mark as ready
    stopChecking()
    isBackendReady.value = true
    isCheckingBackend.value = false
    setupNeeded.value = true
  } else {
    // Not on setup page - check setup status and start backend checking if needed
    checkSetupStatus().then(() => {
      if (!setupNeeded.value) {
        // Setup is complete, start checking backend
        startChecking()
      } else {
        // Setup needed - don't check backend
        isBackendReady.value = true
        isCheckingBackend.value = false
      }
    })
  }
}, { immediate: true })

// Start checking backend status on app mount
onMounted(async () => {
  // Check setup status first
  await checkSetupStatus()
  
  // Only check backend if we're not on setup page and setup is complete
  if (route.path !== '/setup' && !setupNeeded.value) {
    startChecking()
  } else {
    // On setup page or setup needed - don't check backend
    stopChecking()
    isBackendReady.value = true
    isCheckingBackend.value = false
  }
})
</script>
