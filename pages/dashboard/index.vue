<template>
  <div class="space-y-6">
    <!-- Welcome section -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-foreground">Welcome back!</h1>
        <p class="text-muted-foreground">Here's what's happening with your SeerrBridge service.</p>
      </div>
      
      <div class="flex items-center gap-3">
        <Button 
          @click="handleRefresh"
          :disabled="isRefreshing"
          variant="outline" 
          size="sm"
        >
          <AppIcon 
            icon="lucide:refresh-cw" 
            size="16" 
            class="mr-2" 
            :class="{ 'animate-spin': isRefreshing }" 
          />
          Refresh
        </Button>
        <Button 
          variant="outline" 
          size="sm"
          as="NuxtLink"
          to="/dashboard/settings"
        >
          <AppIcon icon="lucide:settings" size="16" class="mr-2" />
          Settings
        </Button>
      </div>
    </div>
    
    <Suspense>
      <template #default>
        <StatsCards />
      </template>
      <template #fallback>
        <div class="glass-card p-8 text-center h-36 flex items-center justify-center">
          <div class="animate-pulse">Loading stats...</div>
        </div>
      </template>
    </Suspense>
    
    <div class="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-8">
      <Suspense>
        <template #default>
          <RecentMedia />
        </template>
        <template #fallback>
          <div class="glass-card p-8 text-center min-h-[500px] flex items-center justify-center">
            <div class="animate-pulse">Loading recent media...</div>
          </div>
        </template>
      </Suspense>
      
      <Suspense>
        <template #default>
          <RecentLogs />
        </template>
        <template #fallback>
          <div class="glass-card p-8 text-center min-h-[500px] flex items-center justify-center">
            <div class="animate-pulse">Loading logs...</div>
          </div>
        </template>
      </Suspense>
    </div>
  </div>
</template>

<script setup lang="ts">
import Button from '~/components/ui/Button.vue'

const isRefreshing = ref(false)

const handleRefresh = async () => {
  isRefreshing.value = true
  
  try {
    // Clear all cached data and refresh
    await clearNuxtData()
    
    // Force a page reload to refresh all data
    window.location.reload()
  } catch (error) {
    console.error('Error refreshing dashboard:', error)
  } finally {
    isRefreshing.value = false
  }
}

// Page head configuration
useHead({
  title: 'Dashboard'
})

// Ensure data is refreshed when navigating to this page
onMounted(() => {
  console.log('Dashboard page mounted, ensuring fresh data...')
})
</script>
