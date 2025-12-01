<template>
  <div class="space-y-4 sm:space-y-6">
    <!-- Summary Stats -->
    <div v-if="allHistory.length > 0" class="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
      <div class="glass-card-enhanced rounded-xl p-4 text-center">
        <div class="text-2xl sm:text-3xl font-bold text-foreground mb-1">{{ allHistory.length }}</div>
        <div class="text-xs sm:text-sm text-muted-foreground">Total Syncs</div>
      </div>
      <div class="glass-card-enhanced rounded-xl p-4 text-center">
        <div class="text-2xl sm:text-3xl font-bold text-success mb-1">
          {{ allHistory.filter(h => h.status === 'completed').length }}
        </div>
        <div class="text-xs sm:text-sm text-muted-foreground">Completed</div>
      </div>
      <div class="glass-card-enhanced rounded-xl p-4 text-center">
        <div class="text-2xl sm:text-3xl font-bold text-primary mb-1">
          {{ allHistory.reduce((sum, h) => sum + h.itemsRequested, 0) }}
        </div>
        <div class="text-xs sm:text-sm text-muted-foreground">Items Requested</div>
      </div>
      <div class="glass-card-enhanced rounded-xl p-4 text-center">
        <div class="text-2xl sm:text-3xl font-bold text-destructive mb-1">
          {{ allHistory.filter(h => h.status === 'failed').length }}
        </div>
        <div class="text-xs sm:text-sm text-muted-foreground">Failed</div>
      </div>
    </div>

    <div class="glass-card-enhanced rounded-2xl p-4 sm:p-6 lg:p-8">
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-4 mb-4 sm:mb-6">
        <div>
          <h2 class="text-xl sm:text-2xl font-semibold text-foreground">All Sync History</h2>
          <p class="text-xs sm:text-sm text-muted-foreground mt-1">
            View all sync operations across all lists
          </p>
        </div>
        <div class="flex items-center gap-2">
          <select
            :value="filter"
            @change="$emit('filter-change', ($event.target as HTMLSelectElement).value)"
            class="px-3 py-2 bg-card border border-border rounded-lg text-foreground text-sm focus:outline-none focus:border-primary transition-colors"
          >
            <option value="all">All Status</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="in_progress">In Progress</option>
          </select>
          <button
            @click="$emit('refresh')"
            class="px-4 py-2 bg-primary/10 hover:bg-primary/20 text-primary rounded-lg transition-colors text-sm font-medium flex items-center justify-center gap-2"
            :disabled="loading"
          >
            <AppIcon 
              :icon="loading ? 'lucide:loader-2' : 'lucide:refresh-cw'" 
              size="16" 
              :class="{ 'animate-spin': loading }"
            />
            Refresh
          </button>
        </div>
      </div>
      
      <EmptyState
        v-if="!loading && history.length === 0"
        icon="lucide:history"
        title="No sync history yet"
        description="Sync a Trakt list to see history here"
        action-label="Sync a List"
        action-icon="lucide:sync"
        :action-handler="() => $emit('go-to-sync')"
      />
      
      <div v-else-if="loading" class="text-center py-12">
        <AppIcon icon="lucide:loader-2" size="32" class="animate-spin text-primary mx-auto mb-4" />
        <p class="text-muted-foreground">Loading history...</p>
      </div>
      
      <div v-else class="space-y-3">
        <div
          v-for="(h, index) in history"
          :key="h.id"
          :style="{ animationDelay: `${index * 30}ms` }"
          class="p-5 bg-card border border-border rounded-xl hover:bg-muted/50 transition-all hover:shadow-lg hover:border-primary/30 cursor-pointer animate-fade-in-up"
          :class="{ 'ring-2 ring-primary border-primary': selectedSessionId === h.sessionId }"
          @click="$emit('select-session', h.sessionId)"
        >
          <div class="flex items-start justify-between">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-3">
                <div class="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                  <AppIcon 
                    :icon="h.syncType === 'automated' ? 'lucide:repeat' : h.syncType === 'dry_run' ? 'lucide:test-tube' : 'lucide:play'" 
                    size="20" 
                    class="text-primary"
                  />
                </div>
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2 flex-wrap">
                    <span class="font-semibold text-foreground capitalize">{{ h.syncType }}</span>
                    <StatusBadge :status="h.status" />
                  </div>
                  <p class="text-xs text-muted-foreground mt-1">
                    {{ formatDate(h.startTime) }}
                    <span v-if="h.endTime" class="ml-2">
                      • {{ formatDuration(h.startTime, h.endTime) }}
                    </span>
                  </p>
                </div>
              </div>
              <div class="mb-3 p-3 bg-muted/30 rounded-lg">
                <p class="font-medium text-foreground text-sm mb-1">
                  {{ h.listName || h.listIdentifier || 'Unknown List' }}
                </p>
                <p class="text-xs text-muted-foreground">
                  {{ h.listType ? h.listType.charAt(0).toUpperCase() + h.listType.slice(1) : '' }} List
                </p>
              </div>
              <SyncStatsGrid :stats="{
                total: h.totalItems,
                requested: h.itemsRequested,
                alreadyRequested: h.itemsAlreadyRequested,
                alreadyAvailable: h.itemsAlreadyAvailable,
                errors: h.itemsErrors
              }" />
              <div v-if="h.errorMessage" class="mt-3 p-3 bg-destructive/10 border border-destructive/30 rounded-lg">
                <div class="flex items-start gap-2">
                  <AppIcon icon="lucide:alert-circle" size="16" class="text-destructive flex-shrink-0 mt-0.5" />
                  <p class="text-xs text-destructive">{{ h.errorMessage }}</p>
                </div>
              </div>
            </div>
            <AppIcon icon="lucide:chevron-right" size="18" class="text-muted-foreground ml-4 flex-shrink-0" />
          </div>
        </div>
      </div>
    </div>

    <!-- Session Items -->
    <SessionItemsView
      v-if="selectedSessionId && sessionItems.length > 0"
      :items="sessionItems"
      @close="$emit('close-items')"
    />
  </div>
</template>

<script setup lang="ts">
import StatusBadge from '~/components/ListSync/StatusBadge.vue'
import SyncStatsGrid from '~/components/ListSync/SyncStatsGrid.vue'
import EmptyState from '~/components/ListSync/EmptyState.vue'
import SessionItemsView from '~/components/ListSync/SessionItemsView.vue'

interface Props {
  history: any[]
  allHistory: any[]
  loading: boolean
  filter: string
  selectedSessionId: string | null
  sessionItems: any[]
}

defineProps<Props>()

defineEmits<{
  refresh: []
  'filter-change': [value: string]
  'select-session': [sessionId: string]
  'close-items': []
  'go-to-sync': []
}>()

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

