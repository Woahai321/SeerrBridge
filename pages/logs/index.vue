<template>
  <LogsContainer>
    <Card>
    <div v-if="pending" class="space-y-3 sm:space-y-4">
      <div v-for="i in 10" :key="i" class="animate-pulse">
        <div class="h-3 sm:h-4 bg-muted rounded w-3/4 mb-2" />
        <div class="h-2.5 sm:h-3 bg-muted rounded w-1/2" />
      </div>
    </div>

    <div v-else-if="error" class="text-center py-6 sm:py-8">
      <AppIcon icon="lucide:alert-circle" size="40" class="sm:w-12 sm:h-12 mx-auto text-destructive mb-3 sm:mb-4" />
      <p class="text-sm sm:text-base text-destructive">Failed to load logs</p>
      <Button @click="refreshLogs" class="mt-3 sm:mt-4 text-xs sm:text-sm">
        Try Again
      </Button>
    </div>

    <div v-else-if="currentLogs.length === 0" class="text-center py-6 sm:py-8">
      <AppIcon icon="lucide:file-text" size="40" class="sm:w-12 sm:h-12 mx-auto text-muted-foreground mb-3 sm:mb-4" />
      <p class="text-sm sm:text-base text-muted-foreground">No logs found</p>
    </div>

    <div v-else class="space-y-2 sm:space-y-4">
      <div 
        v-for="log in currentLogs" 
        :key="log.id"
        class="flex items-start space-x-2 sm:space-x-3 p-3 sm:p-4 rounded-lg hover:bg-muted/50 transition-colors"
      >
        <div class="flex-shrink-0 mt-0.5 sm:mt-1">
          <div 
            class="w-1.5 h-1.5 sm:w-2 sm:h-2 rounded-full"
            :class="getLogLevelColor(log.level)"
          />
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-xs sm:text-sm text-foreground font-medium break-words">
            {{ log.message }}
          </p>
          <div class="flex flex-wrap items-center gap-1.5 sm:gap-2 mt-1.5 sm:mt-2">
            <span class="text-[10px] sm:text-xs text-muted-foreground whitespace-nowrap">
              {{ formatDateTime(log.timestamp) }}
            </span>
            <span 
              class="text-[10px] sm:text-xs px-1.5 sm:px-2 py-0.5 sm:py-1 rounded-full whitespace-nowrap"
              :class="getLogLevelBadgeClass(log.level)"
            >
              {{ log.level.toUpperCase() }}
            </span>
            <span v-if="log.type" class="text-[10px] sm:text-xs px-1.5 sm:px-2 py-0.5 sm:py-1 bg-muted rounded-full whitespace-nowrap">
              {{ log.type }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="totalPages > 1" class="mt-6 sm:mt-8 flex justify-center">
      <div class="flex items-center space-x-1 sm:space-x-2">
        <Button 
          @click="currentPage = Math.max(1, currentPage - 1)"
          :disabled="currentPage === 1"
          variant="outline"
          size="sm"
          class="h-8 w-8 sm:h-9 sm:w-auto sm:px-3 p-0"
        >
          <AppIcon icon="lucide:chevron-left" size="14" class="sm:w-4 sm:h-4" />
          <span class="hidden sm:inline ml-1">Previous</span>
        </Button>
        
        <span class="text-xs sm:text-sm text-muted-foreground px-2 sm:px-4 whitespace-nowrap">
          <span class="hidden sm:inline">Page </span>{{ currentPage }}<span class="hidden sm:inline"> of {{ totalPages }}</span>
        </span>
        
        <Button 
          @click="currentPage = Math.min(totalPages, currentPage + 1)"
          :disabled="currentPage === totalPages"
          variant="outline"
          size="sm"
          class="h-8 w-8 sm:h-9 sm:w-auto sm:px-3 p-0"
        >
          <span class="hidden sm:inline mr-1">Next</span>
          <AppIcon icon="lucide:chevron-right" size="14" class="sm:w-4 sm:h-4" />
        </Button>
      </div>
    </div>
    </Card>
  </LogsContainer>
</template>

<script setup lang="ts">
interface LogEntry {
  id: string
  timestamp: string
  level: string
  message: string
  type?: string
}

import { useLogs } from '~/composables/useLogs'
import Card from '~/components/ui/Card.vue'
import Button from '~/components/ui/Button.vue'

const { fetchLogEntries } = useLogs()

const currentPage = ref(1)
const pageSize = 50

const { data: logsData, pending, error, refresh: refreshLogs } = await useLazyAsyncData('logs-index', async () => {
  return await fetchLogEntries(currentPage.value, pageSize)
}, {
  server: false,
  watch: [currentPage]
})

const currentLogs = computed<LogEntry[]>(() => {
  if (!logsData.value) return []
  
  // Handle different data structures from different endpoints
  if (Array.isArray(logsData.value)) {
    return logsData.value
  }
  
  return logsData.value.entries || []
})

const totalPages = computed(() => {
  if (!logsData.value) return 1
  
  // Handle different data structures from different endpoints
  if (Array.isArray(logsData.value)) {
    return 1 // If it's an array, assume single page
  }
  
  const total = logsData.value.total || 0
  return Math.ceil(total / pageSize)
})

const getLogLevelColor = (level: string) => {
  const colors = {
    error: 'bg-destructive',
    warning: 'bg-warning',
    info: 'bg-info',
    success: 'bg-success',
    debug: 'bg-muted-foreground'
  }
  return colors[level.toLowerCase() as keyof typeof colors] || 'bg-muted-foreground'
}

const getLogLevelBadgeClass = (level: string) => {
  const classes = {
    error: 'bg-destructive/10 text-destructive',
    warning: 'bg-warning/10 text-warning',
    info: 'bg-info/10 text-info',
    success: 'bg-success/10 text-success',
    debug: 'bg-muted/10 text-muted-foreground'
  }
  return classes[level.toLowerCase() as keyof typeof classes] || 'bg-muted/10 text-muted-foreground'
}

const formatDateTime = (timestamp: string) => {
  return new Date(timestamp).toLocaleString()
}

// Page head configuration
useHead({
  title: 'All Logs'
})
</script>
