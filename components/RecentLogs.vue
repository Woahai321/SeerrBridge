<template>
  <Card class="h-full">
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center space-x-3">
        <div class="p-2 bg-primary/10 rounded-lg">
          <AppIcon icon="lucide:activity" size="20" class="text-primary" />
        </div>
        <div>
          <h2 class="text-xl font-semibold text-foreground">Recent Activity</h2>
          <p class="text-sm text-muted-foreground">Latest system events and logs</p>
        </div>
      </div>
      <NuxtLink to="/logs">
        <Button variant="ghost" size="sm">
          View All
          <AppIcon icon="lucide:chevron-right" size="16" class="ml-1" />
        </Button>
      </NuxtLink>
    </div>

    <div v-if="pending" class="space-y-4">
      <div v-for="i in 5" :key="i" class="animate-pulse">
        <div class="h-4 bg-muted rounded w-3/4 mb-2" />
        <div class="h-3 bg-muted rounded w-1/2" />
      </div>
    </div>

    <div v-else-if="error" class="text-center py-8">
      <AppIcon icon="lucide:alert-circle" size="48" class="mx-auto text-destructive mb-4" />
      <p class="text-destructive">Failed to load logs</p>
    </div>

    <div v-else-if="!recentLogs || recentLogs.length === 0" class="text-center py-8">
      <AppIcon icon="lucide:file-text" size="48" class="mx-auto text-muted-foreground mb-4" />
      <p class="text-muted-foreground">No recent activity</p>
    </div>

    <div v-else class="space-y-4 max-h-96 overflow-y-auto">
      <div 
        v-for="log in recentLogs" 
        :key="log.id"
        class="flex items-start space-x-3 p-3 rounded-lg hover:bg-muted/50 transition-colors"
      >
        <div class="flex-shrink-0 mt-1">
          <div 
            class="w-2 h-2 rounded-full"
            :class="getLogLevelColor(log.level)"
          />
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-sm text-foreground font-medium truncate">
            {{ log.message }}
          </p>
          <div class="flex items-center space-x-2 mt-1">
            <span class="text-xs text-muted-foreground">
              {{ formatTime(log.timestamp) }}
            </span>
            <span 
              class="text-xs px-2 py-1 rounded-full"
              :class="getLogLevelBadgeClass(log.level)"
            >
              {{ log.level.toUpperCase() }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </Card>
</template>

<script setup lang="ts">
import { useDashboardData } from '~/composables/useDashboardData'
import Card from '~/components/ui/Card.vue'
import Button from '~/components/ui/Button.vue'

interface LogEntry {
  id: string
  timestamp: string
  level: string
  message: string
  type?: string
}

const { logsData, pending, error } = useDashboardData()

const recentLogs = computed<LogEntry[]>(() => {
  return logsData.value?.recentLogs || []
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

const formatTime = (timestamp: string) => {
  return new Date(timestamp).toLocaleTimeString()
}
</script>
