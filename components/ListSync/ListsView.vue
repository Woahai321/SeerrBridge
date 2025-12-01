<template>
  <div class="space-y-4 sm:space-y-6">
    <!-- Summary Stats -->
    <div v-if="lists.length > 0" class="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
      <div class="glass-card-enhanced rounded-xl p-4 text-center">
        <div class="text-2xl sm:text-3xl font-bold text-primary mb-1">{{ lists.length }}</div>
        <div class="text-xs sm:text-sm text-muted-foreground">Total Lists</div>
      </div>
      <div class="glass-card-enhanced rounded-xl p-4 text-center">
        <div class="text-2xl sm:text-3xl font-bold text-success mb-1">
          {{ lists.reduce((sum, l) => sum + l.itemCount, 0) }}
        </div>
        <div class="text-xs sm:text-sm text-muted-foreground">Total Items</div>
      </div>
      <div class="glass-card-enhanced rounded-xl p-4 text-center">
        <div class="text-2xl sm:text-3xl font-bold text-info mb-1">
          {{ lists.filter(l => l.autoSync).length }}
        </div>
        <div class="text-xs sm:text-sm text-muted-foreground">Auto-Sync</div>
      </div>
      <div class="glass-card-enhanced rounded-xl p-4 text-center">
        <div class="text-2xl sm:text-3xl font-bold text-warning mb-1">
          {{ lists.filter(l => !l.lastSynced).length }}
        </div>
        <div class="text-xs sm:text-sm text-muted-foreground">Never Synced</div>
      </div>
    </div>

    <div class="glass-card-enhanced rounded-2xl p-4 sm:p-6 lg:p-8">
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-4 mb-4 sm:mb-6">
        <div>
          <h2 class="text-xl sm:text-2xl font-semibold text-foreground">Saved Lists</h2>
          <p class="text-xs sm:text-sm text-muted-foreground mt-1">
            Manage your Trakt lists and view sync history
          </p>
        </div>
        <button
          @click="$emit('refresh')"
          class="px-4 py-2 bg-primary/10 hover:bg-primary/20 text-primary rounded-lg transition-colors text-sm font-medium flex items-center justify-center gap-2 self-start sm:self-auto"
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
      
      <EmptyState
        v-if="!loading && lists.length === 0"
        icon="lucide:list-x"
        title="No saved lists yet"
        description="Sync a Trakt list to get started!"
        action-label="Sync Your First List"
        action-icon="lucide:plus"
        :action-handler="() => $emit('go-to-sync')"
      />
      
      <div v-else-if="loading" class="text-center py-12">
        <AppIcon icon="lucide:loader-2" size="32" class="animate-spin text-primary mx-auto mb-4" />
        <p class="text-muted-foreground">Loading lists...</p>
      </div>
      
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div
          v-for="(list, index) in lists"
          :key="list.id"
          :style="{ animationDelay: `${index * 50}ms` }"
          class="p-5 bg-card border border-border rounded-xl hover:bg-muted/50 transition-all hover:shadow-lg hover:border-primary/30 animate-fade-in-up"
          :class="{ 'ring-2 ring-primary border-primary': selectedListId === list.id }"
        >
          <div class="flex items-start justify-between mb-4">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-2">
                <div class="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                  <AppIcon 
                    :icon="getListIcon(list.listType)" 
                    size="20" 
                    class="text-primary"
                  />
                </div>
                <div class="flex-1 min-w-0">
                  <h3 class="font-semibold text-foreground truncate text-sm sm:text-base">{{ list.listName || list.listIdentifier }}</h3>
                  <span class="text-xs px-2 py-0.5 rounded-full bg-muted text-muted-foreground capitalize">
                    {{ list.listType }}
                  </span>
                </div>
              </div>
              <p class="text-xs text-muted-foreground truncate mb-3" :title="list.listIdentifier">{{ list.listIdentifier }}</p>
            </div>
          </div>
          
          <div class="space-y-2.5 mb-4">
            <div class="flex items-center justify-between text-sm">
              <span class="text-muted-foreground flex items-center gap-1.5">
                <AppIcon icon="lucide:film" size="14" />
                Items
              </span>
              <span class="font-semibold text-foreground">{{ list.itemCount }}</span>
            </div>
            <div class="flex items-center justify-between text-sm">
              <span class="text-muted-foreground flex items-center gap-1.5">
                <AppIcon icon="lucide:clock" size="14" />
                Last Sync
              </span>
              <span class="font-medium text-foreground text-xs">
                {{ list.lastSynced ? formatDate(list.lastSynced) : 'Never' }}
              </span>
            </div>
            <div v-if="list.lastSyncStatus" class="flex items-center justify-between text-sm">
              <span class="text-muted-foreground">Status</span>
              <StatusBadge :status="list.lastSyncStatus" />
            </div>
            <div v-if="list.autoSync" class="flex items-center gap-1.5 text-xs text-primary bg-primary/10 px-2 py-1 rounded">
              <AppIcon icon="lucide:repeat" size="12" />
              Auto-sync enabled
              <span v-if="list.syncIntervalHours" class="text-muted-foreground">
                (every {{ list.syncIntervalHours }}h)
              </span>
            </div>
          </div>
          
          <div class="flex items-center gap-2 pt-3 border-t border-border">
            <button
              @click="$emit('select-list', list.id)"
              class="flex-1 px-3 py-2 bg-primary/10 hover:bg-primary/20 text-primary rounded-lg transition-colors text-sm font-medium flex items-center justify-center gap-2"
            >
              <AppIcon icon="lucide:history" size="16" />
              History
            </button>
            <button
              @click="$emit('delete-list', list.id)"
              class="px-3 py-2 hover:bg-destructive/20 text-destructive rounded-lg transition-colors"
              title="Delete list"
            >
              <AppIcon icon="lucide:trash-2" size="16" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Sync History for Selected List -->
    <div v-if="selectedListId && syncHistory.length > 0" class="glass-card-enhanced rounded-2xl p-4 sm:p-6 lg:p-8">
      <div class="flex items-center justify-between mb-4 sm:mb-6">
        <div>
          <h2 class="text-xl sm:text-2xl font-semibold text-foreground">Sync History</h2>
          <p v-if="selectedList" class="text-sm text-muted-foreground mt-1">
            {{ selectedList.listName || selectedList.listIdentifier }}
          </p>
        </div>
        <button
          @click="$emit('close-history')"
          class="p-2 hover:bg-muted rounded-lg transition-colors"
        >
          <AppIcon icon="lucide:x" size="18" class="text-foreground" />
        </button>
      </div>
      
      <div class="space-y-3">
        <div
          v-for="history in syncHistory"
          :key="history.id"
          class="p-4 bg-card border border-border rounded-lg hover:bg-muted/50 transition-all cursor-pointer"
          :class="{ 'ring-2 ring-primary': selectedSessionId === history.sessionId }"
          @click="$emit('select-session', history.sessionId)"
        >
          <HistoryCard :history="history" />
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
import EmptyState from '~/components/ListSync/EmptyState.vue'
import HistoryCard from '~/components/ListSync/HistoryCard.vue'
import SessionItemsView from '~/components/ListSync/SessionItemsView.vue'

interface Props {
  lists: any[]
  loading: boolean
  selectedListId: number | null
  syncHistory: any[]
  selectedSessionId: string | null
  sessionItems: any[]
}

const props = defineProps<Props>()

defineEmits<{
  refresh: []
  'select-list': [listId: number]
  'select-session': [sessionId: string]
  'delete-list': [listId: number]
  'close-history': []
  'close-items': []
  'go-to-sync': []
}>()

const selectedList = computed(() => {
  return props.lists.find(l => l.id === props.selectedListId)
})

const getListIcon = (type: string) => {
  const icons: Record<string, string> = {
    watchlist: 'lucide:bookmark',
    trending: 'lucide:trending-up',
    popular: 'lucide:star',
    custom: 'lucide:list'
  }
  return icons[type] || 'lucide:list'
}

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
</script>

