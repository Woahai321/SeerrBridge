<template>
  <div class="space-y-4 sm:space-y-6">
    <!-- Summary Stats -->
    <div v-if="savedLists.length > 0 || allHistory.length > 0" class="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
      <div class="glass-card-enhanced rounded-xl p-4 text-center">
        <div class="text-2xl sm:text-3xl font-bold text-primary mb-1">{{ savedLists.length }}</div>
        <div class="text-xs sm:text-sm text-muted-foreground">Saved Lists</div>
      </div>
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
          {{ allHistory.reduce((sum, h) => sum + (h.itemsRequested || 0), 0) }}
        </div>
        <div class="text-xs sm:text-sm text-muted-foreground">Items Requested</div>
      </div>
    </div>

    <div class="glass-card-enhanced rounded-2xl p-4 sm:p-6 lg:p-8">
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-4 mb-4 sm:mb-6">
        <div>
          <h2 class="text-xl sm:text-2xl font-semibold text-foreground">Lists & Sync History</h2>
          <p class="text-xs sm:text-sm text-muted-foreground mt-1">
            View all saved lists and their sync history
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
            :disabled="loadingLists || loadingHistory"
          >
            <AppIcon 
              :icon="(loadingLists || loadingHistory) ? 'lucide:loader-2' : 'lucide:refresh-cw'" 
              size="16" 
              :class="{ 'animate-spin': loadingLists || loadingHistory }"
            />
            Refresh
          </button>
          <button
            @click="$emit('add-list')"
            class="px-4 py-2 bg-primary text-primary-foreground rounded-lg transition-colors text-sm font-medium flex items-center justify-center gap-2 hover:bg-primary/90"
          >
            <AppIcon icon="lucide:plus" size="16" />
            Add List
          </button>
        </div>
      </div>
      
      <EmptyState
        v-if="!loadingLists && !loadingHistory && savedLists.length === 0 && allHistory.length === 0"
        icon="lucide:history"
        title="No lists or history yet"
        description="Sync a Trakt list to get started!"
        action-label="Sync Your First List"
        action-icon="lucide:sync"
        :action-handler="() => $emit('go-to-sync')"
      />
      
      <div v-else-if="loadingLists || loadingHistory" class="text-center py-12">
        <AppIcon icon="lucide:loader-2" size="32" class="animate-spin text-primary mx-auto mb-4" />
        <p class="text-muted-foreground">Loading...</p>
      </div>
      
      <div v-else class="space-y-6">
        <!-- Group history by list -->
        <div
          v-for="list in groupedLists"
          :key="list.id || list.listIdentifier"
          class="space-y-4"
        >
          <!-- List Header Card -->
          <div class="p-5 bg-card border-2 border-border rounded-xl hover:bg-muted/30 transition-all">
            <div class="flex items-start justify-between mb-4">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-3 mb-3">
                  <div class="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                    <AppIcon 
                      :icon="getListIcon(list.listType)" 
                      size="24" 
                      class="text-primary"
                    />
                  </div>
                  <div class="flex-1 min-w-0">
                    <h3 class="font-semibold text-foreground text-lg mb-1 truncate">
                      {{ list.listName || list.listIdentifier || 'Unknown List' }}
                    </h3>
                    <div class="flex items-center gap-2 flex-wrap">
                      <span class="text-xs px-2 py-1 rounded-full bg-muted text-muted-foreground capitalize">
                        {{ list.listType || 'unknown' }}
                      </span>
                      <span v-if="list.autoSync" class="text-xs px-2 py-1 rounded-full bg-primary/20 text-primary flex items-center gap-1">
                        <AppIcon icon="lucide:repeat" size="12" />
                        Auto-sync
                      </span>
                    </div>
                    <p class="text-xs text-muted-foreground mt-2 truncate" :title="list.listIdentifier">
                      {{ list.listIdentifier }}
                    </p>
                  </div>
                </div>
                
                <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
                  <div class="text-center p-2 bg-muted/20 rounded-lg">
                    <div class="text-lg font-bold text-foreground">{{ list.itemCount ?? 0 }}</div>
                    <div class="text-xs text-muted-foreground">Items</div>
                  </div>
                  <div class="text-center p-2 bg-muted/20 rounded-lg">
                    <div class="text-lg font-bold text-foreground">{{ list.syncCount ?? list.historyCount ?? 0 }}</div>
                    <div class="text-xs text-muted-foreground">Total Syncs</div>
                  </div>
                  <div class="text-center p-2 bg-muted/20 rounded-lg">
                    <div class="text-xs font-medium text-foreground">
                      {{ list.lastSynced ? formatDate(list.lastSynced) : 'Never' }}
                    </div>
                    <div class="text-xs text-muted-foreground">Last Sync</div>
                  </div>
                  <div class="text-center p-2 bg-muted/20 rounded-lg">
                    <StatusBadge v-if="list.lastSyncStatus" :status="list.lastSyncStatus" />
                    <span v-else class="text-xs text-muted-foreground">No Status</span>
                  </div>
                </div>
              </div>
              
              <div class="flex items-center gap-2 ml-4 flex-shrink-0">
                <button
                  @click.stop="$emit('retrigger-list', list.listIdentifier)"
                  class="px-4 py-2 bg-success/10 hover:bg-success/20 text-success rounded-lg transition-colors text-sm font-medium flex items-center justify-center gap-2"
                  title="Resync this list"
                >
                  <AppIcon icon="lucide:refresh-cw" size="16" />
                  <span class="hidden sm:inline">Resync</span>
                </button>
                <button
                  v-if="list.id"
                  @click.stop="$emit('delete-list', list.id)"
                  class="px-3 py-2 hover:bg-destructive/20 text-destructive rounded-lg transition-colors"
                  title="Delete list"
                >
                  <AppIcon icon="lucide:trash-2" size="16" />
                </button>
              </div>
            </div>
          </div>
          
          <!-- Sync History for this List -->
          <div v-if="list.history && list.history.length > 0" class="space-y-3 ml-4 border-l-2 border-border pl-4">
            <div
              v-for="(h, index) in getFilteredHistory(list.history)"
              :key="h.id"
              :style="{ animationDelay: `${index * 30}ms` }"
              class="p-4 bg-card border border-border rounded-lg hover:bg-muted/50 transition-all cursor-pointer animate-fade-in-up"
              :class="{ 'ring-2 ring-primary border-primary': selectedSessionId === h.sessionId }"
              @click="$emit('select-session', h.sessionId)"
            >
              <div class="flex items-start justify-between">
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2 mb-2">
                    <AppIcon 
                      :icon="h.syncType === 'automated' ? 'lucide:repeat' : h.syncType === 'dry_run' ? 'lucide:test-tube' : 'lucide:play'" 
                      size="16" 
                      class="text-muted-foreground"
                    />
                    <span class="font-medium text-foreground capitalize text-sm">{{ h.syncType }}</span>
                    <StatusBadge :status="h.status" />
                  </div>
                  <p class="text-xs text-muted-foreground mb-3">
                    <span>{{ formatDate(h.startTime) }}</span>
                    <span v-if="h.endTime" class="ml-2">
                      • Duration: {{ formatDuration(h.startTime, h.endTime) }}
                    </span>
                  </p>
                  <SyncStatsGrid :stats="{
                    total: h.totalItems,
                    requested: h.itemsRequested,
                    alreadyRequested: h.itemsAlreadyRequested,
                    alreadyAvailable: h.itemsAlreadyAvailable,
                    errors: h.itemsErrors
                  }" />
                  <div v-if="h.errorMessage" class="mt-3 p-2 bg-destructive/10 border border-destructive/30 rounded-lg">
                    <div class="flex items-start gap-2">
                      <AppIcon icon="lucide:alert-circle" size="14" class="text-destructive flex-shrink-0 mt-0.5" />
                      <p class="text-xs text-destructive">{{ h.errorMessage }}</p>
                    </div>
                  </div>
                </div>
                <AppIcon icon="lucide:chevron-right" size="18" class="text-muted-foreground ml-4 flex-shrink-0" />
              </div>
            </div>
          </div>
          
          <!-- Empty state for list with no history -->
          <div v-else class="ml-4 border-l-2 border-border pl-4 py-2">
            <p class="text-xs text-muted-foreground italic">No sync history for this list yet</p>
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
import HistoryCard from '~/components/ListSync/HistoryCard.vue'
import SessionItemsView from '~/components/ListSync/SessionItemsView.vue'

interface Props {
  savedLists: any[]
  allHistory: any[]
  loadingLists: boolean
  loadingHistory: boolean
  filter: string
  selectedSessionId: string | null
  sessionItems: any[]
}

const props = defineProps<Props>()

defineEmits<{
  refresh: []
  'filter-change': [value: string]
  'select-session': [sessionId: string]
  'retrigger-list': [listIdentifier: string]
  'delete-list': [listId: number]
  'close-items': []
  'go-to-sync': []
  'add-list': []
}>()

// Group lists with their history
const groupedLists = computed(() => {
  // Create a map of lists by identifier
  const listsMap = new Map()
  
  // Add all saved lists with their database fields
  props.savedLists.forEach(list => {
    listsMap.set(list.listIdentifier, {
      id: list.id,
      listIdentifier: list.listIdentifier,
      listName: list.listName || list.listIdentifier,
      listType: list.listType || 'unknown',
      itemCount: list.itemCount || 0,
      syncCount: list.syncCount || 0, // From database
      lastSynced: list.lastSynced,
      lastSyncStatus: list.lastSyncStatus,
      autoSync: list.autoSync || false,
      syncIntervalHours: list.syncIntervalHours,
      createdAt: list.createdAt,
      updatedAt: list.updatedAt,
      history: [],
      historyCount: 0
    })
  })
  
  // Group history by list identifier
  props.allHistory.forEach(history => {
    const identifier = history.listIdentifier
    if (!identifier) return
    
    if (listsMap.has(identifier)) {
      const list = listsMap.get(identifier)
      list.history.push(history)
      list.historyCount++
      // Update lastSynced if this history is more recent
      if (history.startTime) {
        const historyDate = new Date(history.startTime).getTime()
        const currentDate = list.lastSynced ? new Date(list.lastSynced).getTime() : 0
        if (historyDate > currentDate) {
          list.lastSynced = history.startTime
          list.lastSyncStatus = history.status
        }
      }
    } else {
      // Create entry for orphaned history (history without saved list)
      listsMap.set(identifier, {
        id: null,
        listIdentifier: identifier,
        listName: history.listName || identifier,
        listType: history.listType || 'unknown',
        itemCount: 0,
        syncCount: 0, // Will be calculated from history
        lastSynced: history.startTime,
        lastSyncStatus: history.status,
        autoSync: false,
        history: [history],
        historyCount: 1
      })
    }
  })
  
  // Calculate sync count for orphaned lists from their history
  listsMap.forEach(list => {
    if (!list.id && list.history.length > 0) {
      // Count completed/failed syncs as the sync count
      list.syncCount = list.history.filter(h => h.status === 'completed' || h.status === 'failed').length
    }
  })
  
  // Sort by last sync date (most recent first)
  return Array.from(listsMap.values()).sort((a, b) => {
    const aDate = a.lastSynced ? new Date(a.lastSynced).getTime() : 0
    const bDate = b.lastSynced ? new Date(b.lastSynced).getTime() : 0
    return bDate - aDate
  })
})

const getFilteredHistory = (history: any[]) => {
  if (props.filter === 'all') return history
  return history.filter(h => h.status === props.filter)
}

const getListIcon = (type: string) => {
  const icons: Record<string, string> = {
    watchlist: 'lucide:bookmark',
    trending: 'lucide:trending-up',
    popular: 'lucide:star',
    custom: 'lucide:list',
    public: 'lucide:users'
  }
  return icons[type] || 'lucide:list'
}

const formatDate = (dateString: string) => {
  if (!dateString) return 'Never'
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
  
  return date.toLocaleString('en-US', { 
    month: 'short', 
    day: 'numeric', 
    year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
    hour: 'numeric',
    minute: '2-digit'
  })
}

const formatDuration = (startTime: string, endTime: string) => {
  if (!startTime || !endTime) return 'N/A'
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

<style scoped>
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-fade-in-up {
  animation: fadeInUp 0.5s cubic-bezier(0.4, 0, 0.2, 1) forwards;
  opacity: 0;
}
</style>

