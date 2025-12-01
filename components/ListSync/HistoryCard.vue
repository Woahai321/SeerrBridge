<template>
  <div class="flex items-start justify-between">
    <div class="flex-1 min-w-0">
      <div class="flex items-center gap-2 mb-2">
        <AppIcon 
          :icon="history.syncType === 'automated' ? 'lucide:repeat' : 'lucide:play'" 
          size="16" 
          class="text-muted-foreground"
        />
        <span class="font-medium text-foreground capitalize">{{ history.syncType }}</span>
        <StatusBadge :status="history.status" />
      </div>
      <p class="text-xs text-muted-foreground mb-3">
        {{ formatDate(history.startTime) }}
        <span v-if="history.endTime" class="ml-2">
          • Duration: {{ formatDuration(history.startTime, history.endTime) }}
        </span>
      </p>
      <SyncStatsGrid :stats="{
        total: history.totalItems,
        requested: history.itemsRequested,
        alreadyRequested: history.itemsAlreadyRequested,
        alreadyAvailable: history.itemsAlreadyAvailable,
        errors: history.itemsErrors
      }" />
    </div>
    <AppIcon icon="lucide:chevron-right" size="18" class="text-muted-foreground ml-4 flex-shrink-0" />
  </div>
</template>

<script setup lang="ts">
import StatusBadge from '~/components/ListSync/StatusBadge.vue'
import SyncStatsGrid from '~/components/ListSync/SyncStatsGrid.vue'

interface Props {
  history: any
}

defineProps<Props>()

const formatDate = (dateString: string) => {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)
  
  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`
  if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`
  
  return date.toLocaleString()
}

const formatDuration = (startTime: string, endTime: string) => {
  const start = new Date(startTime)
  const end = new Date(endTime)
  const diffMs = end.getTime() - start.getTime()
  const diffSecs = Math.floor(diffMs / 1000)
  const diffMins = Math.floor(diffSecs / 60)
  const diffHours = Math.floor(diffMins / 60)
  
  if (diffSecs < 60) return `${diffSecs}s`
  if (diffMins < 60) return `${diffMins}m ${diffSecs % 60}s`
  return `${diffHours}h ${diffMins % 60}m`
}
</script>

