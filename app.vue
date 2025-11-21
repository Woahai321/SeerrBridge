<template>
  <div class="min-h-screen bg-background text-foreground font-outfit">
    <!-- Main content -->
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
  ]
})

// Initialize color mode
const colorMode = useColorMode()
</script>
