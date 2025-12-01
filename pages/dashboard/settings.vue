<template>
  <div class="container mx-auto px-4 py-8">
    <!-- Redirect to main settings page -->
    <div class="text-center">
      <div class="glass-card p-8 max-w-md mx-auto">
        <AppIcon icon="lucide:settings" size="48" class="mx-auto mb-4 text-primary" />
        <h1 class="text-2xl font-bold text-foreground mb-4">Settings</h1>
        <p class="text-muted-foreground mb-6">
          Settings have been moved to a unified page for better organization.
        </p>
        <NuxtLink 
          to="/settings"
          class="glass-button flex items-center justify-center px-6 py-3 mx-auto"
        >
          <AppIcon icon="lucide:arrow-right" size="16" class="mr-2" />
          Go to Settings
        </NuxtLink>
      </div>
    </div>
  </div>
</template>

<script setup>
// Redirect to main settings page
onMounted(() => {
  navigateTo('/settings')
})
</script>