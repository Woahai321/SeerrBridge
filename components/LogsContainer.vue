<template>
  <div class="space-y-4 sm:space-y-6">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-4">
      <div class="min-w-0 flex-1">
        <h1 class="text-xl sm:text-2xl font-bold text-foreground">System Logs</h1>
        <p class="text-sm sm:text-base text-muted-foreground mt-1">Monitor and analyze system events and activities.</p>
      </div>
      
      <div class="flex items-center gap-2 sm:gap-3 flex-shrink-0">
        <Button 
          @click="handleRefresh"
          :disabled="pending"
          variant="outline"
          size="sm"
          class="w-full sm:w-auto"
        >
          <AppIcon icon="lucide:refresh-cw" size="18" class="mr-1.5 sm:mr-2 flex-shrink-0" :class="{ 'animate-spin': pending }" />
          <span class="text-xs sm:text-sm">Refresh</span>
        </Button>
      </div>
    </div>

    <!-- Log Tabs -->
    <div class="overflow-x-auto -mx-4 sm:mx-0 px-4 sm:px-0">
      <div class="flex space-x-1 bg-muted p-1 rounded-lg w-fit min-w-full sm:min-w-0 dark:backdrop-blur-md dark:border dark:border-primary/20">
        <NuxtLink
          v-for="tab in tabs"
          :key="tab.id"
          :to="`/logs/${tab.id}`"
          class="px-2 sm:px-4 py-1.5 sm:py-2 rounded-md text-xs sm:text-sm font-medium transition-all whitespace-nowrap flex-shrink-0"
          :class="isActiveTab(tab.id) 
            ? 'bg-background text-foreground shadow-sm dark:bg-primary/20 dark:text-primary dark:border dark:border-primary/30' 
            : 'text-muted-foreground hover:text-foreground dark:hover:bg-primary/10'"
        >
          <span class="hidden sm:inline">{{ tab.name }}</span>
          <span class="sm:hidden">{{ tab.name.split(' ')[0] }}</span>
          <span v-if="tab.count > 0" class="ml-1 sm:ml-2 px-1.5 sm:px-2 py-0.5 sm:py-1 bg-muted-foreground/10 rounded-full text-[10px] sm:text-xs dark:bg-primary/30 dark:text-primary">
            {{ tab.count }}
          </span>
        </NuxtLink>
      </div>
    </div>

    <!-- Page Content -->
    <slot />
  </div>
</template>

<script setup lang="ts">
interface Tab {
  id: string
  name: string
  count: number
}

import { useLogs } from '~/composables/useLogs'
import Button from '~/components/ui/Button.vue'

const { fetchLogEntries, fetchSuccessLogs, fetchErrorLogs, fetchCriticalLogs, fetchFailureLogs } = useLogs()

const route = useRoute()
const pending = ref(false)

const tabs = computed<Tab[]>(() => [
  { id: 'all', name: 'All Logs', count: tabCountsData.value?.all || 0 },
  { id: 'success', name: 'Success', count: tabCountsData.value?.success || 0 },
  { id: 'errors', name: 'Errors', count: tabCountsData.value?.errors || 0 },
  { id: 'critical', name: 'Critical', count: tabCountsData.value?.critical || 0 },
  { id: 'failures', name: 'Failures', count: tabCountsData.value?.failures || 0 }
])

// Fetch tab counts
const { data: tabCountsData, refresh: refreshTabCounts } = await useLazyAsyncData('tab-counts', async () => {
  const [allLogs, successLogs, errorLogs, criticalLogs, failureLogs] = await Promise.all([
    fetchLogEntries(1, 1),
    fetchSuccessLogs(1, 1),
    fetchErrorLogs(1, 1),
    fetchCriticalLogs(1, 1),
    fetchFailureLogs(1, 1)
  ])
  
  return {
    all: allLogs.total,
    success: successLogs.total,
    errors: errorLogs.total,
    critical: criticalLogs.total,
    failures: failureLogs.total
  }
}, {
  server: false
})

const isActiveTab = (tabId: string) => {
  const currentPath = route.path
  if (tabId === 'all') {
    return currentPath === '/logs' || currentPath === '/logs/all'
  }
  return currentPath === `/logs/${tabId}`
}

const handleRefresh = async () => {
  try {
    pending.value = true
    // Force refresh by clearing all data and reloading the page
    await clearNuxtData()
    window.location.reload()
  } catch (error) {
    console.error('Error refreshing logs:', error)
  } finally {
    pending.value = false
  }
}
</script>
