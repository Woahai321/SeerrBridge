<template>
  <div class="min-h-screen bg-background text-foreground">
    <!-- Backend Initializing Screen - Show when backend is not ready (as overlay) -->
    <BackendInitializing 
      v-if="!isBackendReady && isCheckingBackend" 
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
const { isBackendReady, isChecking: isCheckingBackend, startChecking } = useBackendReady()

const handleBackendReady = () => {
  // Backend is ready - update state to hide loading screen
  isBackendReady.value = true
  isCheckingBackend.value = false
}

// Start checking backend status on app mount
onMounted(() => {
  // Only check if we're not on the setup page
  const route = useRoute()
  if (route.path !== '/setup') {
    startChecking()
  } else {
    // On setup page, assume backend will be ready after setup
    // The setup wizard will handle its own loading screen
    isBackendReady.value = true
  }
})
</script>
