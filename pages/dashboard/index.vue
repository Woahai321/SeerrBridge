<template>
  <div class="space-y-6 lg:space-y-8">
    <!-- Enhanced Welcome section -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div class="space-y-1">
        <h1 class="text-2xl sm:text-3xl font-bold text-foreground tracking-tight">
          {{ welcomeMessage }}
        </h1>
        <p class="text-sm sm:text-base text-muted-foreground">
          Here's what's happening with your SeerrBridge service.
        </p>
      </div>
      
      <div class="flex items-center gap-2 sm:gap-3">
        <Button 
          @click="handleRefresh"
          :disabled="isRefreshing"
          variant="outline" 
          size="sm"
          class="gap-1.5 sm:gap-2"
        >
          <AppIcon 
            icon="lucide:refresh-cw" 
            size="16" 
            class="sm:w-[18px] sm:h-[18px]"
            :class="{ 'animate-spin': isRefreshing }" 
          />
          <span class="hidden sm:inline">Refresh</span>
        </Button>
        <NuxtLink
          to="/dashboard/settings"
          class="inline-flex items-center justify-center rounded-lg font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-8 px-3 text-sm gap-1.5 sm:gap-2"
        >
          <AppIcon icon="lucide:settings" size="16" class="sm:w-[18px] sm:h-[18px]" />
          <span class="hidden sm:inline">Settings</span>
        </NuxtLink>
      </div>
    </div>
    
    <!-- Stats Cards -->
    <div>
      <Suspense>
        <template #default>
          <StatsCards />
        </template>
        <template #fallback>
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6">
            <div v-for="i in 4" :key="i" class="glass-card p-4 lg:p-6 h-28 lg:h-32 animate-pulse" />
          </div>
        </template>
        <template #error="{ error }">
          <div class="glass-card p-4 lg:p-6 text-center">
            <p class="text-sm lg:text-base text-destructive">Error loading stats: {{ error?.message || 'Unknown error' }}</p>
          </div>
        </template>
      </Suspense>
    </div>
    
    <!-- Queue and Recent Media Combined Section -->
    <div>
      <ClientOnly>
        <Suspense>
          <template #default>
            <QueueAndRecentMedia 
              :current-item="processingData?.currentItem || null"
              :queued-items="processingData?.queuedItems || []"
              :processing-items="processingData?.processingItems || []"
              :processing-count="processingData?.stats?.total_processing || 0"
              :queue-stats="processingData?.queueStats || null"
            />
          </template>
          <template #fallback>
            <div class="glass-card p-6 lg:p-8 text-center min-h-[400px] lg:min-h-[500px] flex items-center justify-center">
              <div class="space-y-3">
                <div class="w-10 h-10 lg:w-12 lg:h-12 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
                <p class="text-xs lg:text-sm text-muted-foreground">Loading queue and recent media...</p>
              </div>
            </div>
          </template>
          <template #error="{ error }">
            <div class="glass-card p-6 lg:p-8 text-center min-h-[400px] lg:min-h-[500px] flex items-center justify-center">
              <div class="text-sm lg:text-base text-destructive">Error loading queue and recent media</div>
            </div>
          </template>
        </Suspense>
        <template #fallback>
          <div class="glass-card p-6 lg:p-8 text-center min-h-[400px] lg:min-h-[500px] flex items-center justify-center">
            <div class="animate-pulse text-sm lg:text-base">Loading...</div>
          </div>
        </template>
      </ClientOnly>
    </div>
  </div>
</template>

<script setup lang="ts">
import Button from '~/components/ui/Button.vue'

const isRefreshing = ref(false)

// Get processing status - handle errors gracefully
const processingStatusResult = useProcessingStatus()
const processingData = processingStatusResult?.processingData || ref({
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
const refreshProcessing = processingStatusResult?.refresh || (() => {})

// Track previous processing state to detect when items finish
const previousProcessingCount = ref(0)
const previousCurrentItemId = ref<number | null>(null)

const welcomeMessage = computed(() => {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good morning!'
  if (hour < 18) return 'Good afternoon!'
  return 'Good evening!'
})

const handleRefresh = async () => {
  isRefreshing.value = true
  
  try {
    // Clear all cached data and refresh
    await clearNuxtData()
    await refreshProcessing()
    
    // Small delay for smooth transition
    await new Promise(resolve => setTimeout(resolve, 300))
    
    // Force a page reload to refresh all data
    window.location.reload()
  } catch (error) {
    console.error('Error refreshing dashboard:', error)
  } finally {
    isRefreshing.value = false
  }
}

// Watch for processing status changes and refresh recent media when items finish
watch(() => processingData.value?.stats?.total_processing, (newCount, oldCount) => {
  // Only trigger if we're on the dashboard and count decreased (item finished)
  if (process.client && oldCount !== undefined && newCount < oldCount && newCount !== undefined) {
    console.log(`Processing item finished: ${oldCount} -> ${newCount}, refreshing recent media...`)
    // Refresh recent media data
    refreshNuxtData('recent-media')
  }
  // Update previous count
  if (newCount !== undefined) {
    previousProcessingCount.value = newCount
  }
}, { immediate: false })

// Also watch for when currentItem changes from something to null (item finished)
watch(() => processingData.value?.currentItem?.id, (newItemId, oldItemId) => {
  // If we had a current item and now it's null, an item finished
  if (process.client && oldItemId !== null && oldItemId !== undefined && newItemId === null) {
    console.log('Current processing item finished, refreshing recent media...')
    // Small delay to ensure backend has updated
    setTimeout(() => {
      refreshNuxtData('recent-media')
    }, 1000)
  }
  // Update previous item ID
  previousCurrentItemId.value = newItemId ?? null
}, { immediate: false })

// Initialize previous values on mount
onMounted(() => {
  console.log('Dashboard page mounted, ensuring fresh data...')
  if (processingData.value) {
    previousProcessingCount.value = processingData.value.stats?.total_processing || 0
    previousCurrentItemId.value = processingData.value.currentItem?.id ?? null
  }
})

// Page head configuration
useHead({
  title: 'Dashboard'
})
</script>
