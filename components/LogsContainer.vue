<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-foreground">System Logs</h1>
        <p class="text-muted-foreground">Monitor and analyze system events and activities.</p>
      </div>
      
      <div class="flex items-center gap-3">
        <Button 
          @click="handleRefresh"
          :disabled="pending"
          variant="outline"
          size="sm"
        >
          <AppIcon icon="lucide:refresh-cw" size="16" class="mr-2" :class="{ 'animate-spin': pending }" />
          Refresh
        </Button>
      </div>
    </div>

    <!-- Log Tabs -->
    <div class="flex space-x-1 bg-muted p-1 rounded-lg w-fit">
      <NuxtLink
        v-for="tab in tabs"
        :key="tab.id"
        :to="`/logs/${tab.id}`"
        class="px-4 py-2 rounded-md text-sm font-medium transition-all"
        :class="isActiveTab(tab.id) 
          ? 'bg-background text-foreground shadow-sm' 
          : 'text-muted-foreground hover:text-foreground'"
      >
        {{ tab.name }}
        <span v-if="tab.count > 0" class="ml-2 px-2 py-1 bg-muted-foreground/10 rounded-full text-xs">
          {{ tab.count }}
        </span>
      </NuxtLink>
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
