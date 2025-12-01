<template>
  <div class="space-y-4 sm:space-y-6 lg:space-y-8">
    <!-- Page Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
      <div>
        <h1 class="text-2xl sm:text-3xl font-bold text-foreground mb-1 sm:mb-2">Lists</h1>
        <p class="text-sm sm:text-base text-muted-foreground">
          Manage your watchlists from Trakt and more
        </p>
      </div>
      <button
        @click="showAddModal = true"
        class="px-4 py-2 bg-primary text-primary-foreground rounded-lg transition-colors hover:bg-primary/90 flex items-center justify-center gap-2 font-medium"
      >
        <AppIcon icon="lucide:plus" size="18" />
        Add List
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="loadingLists && savedLists.length === 0" class="text-center py-12">
      <AppIcon icon="lucide:loader-2" size="32" class="animate-spin text-primary mx-auto mb-4" />
      <p class="text-muted-foreground">Loading lists...</p>
    </div>

    <!-- Empty State -->
    <EmptyState
      v-else-if="!loadingLists && savedLists.length === 0"
      icon="lucide:list"
      title="No lists yet"
      description="Add your first list to get started"
      action-label="Add List"
      action-icon="lucide:plus"
      :action-handler="() => showAddModal = true"
    />

    <!-- Lists View -->
    <div v-else class="space-y-6">
      <!-- Stats Cards -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <div class="glass-card-enhanced rounded-xl p-4 sm:p-6">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-xs sm:text-sm text-muted-foreground mb-1">Total Lists</p>
              <p class="text-2xl sm:text-3xl font-bold text-foreground">{{ savedLists.length }}</p>
            </div>
            <div class="p-3 rounded-xl bg-primary/10">
              <AppIcon icon="lucide:list" size="24" class="text-primary" />
            </div>
          </div>
        </div>

        <div class="glass-card-enhanced rounded-xl p-4 sm:p-6">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-xs sm:text-sm text-muted-foreground mb-1">Total Items</p>
              <p class="text-2xl sm:text-3xl font-bold text-foreground">
                {{ savedLists.reduce((sum, list) => sum + (list.itemCount || 0), 0) }}
              </p>
            </div>
            <div class="p-3 rounded-xl bg-primary/10">
              <AppIcon icon="lucide:layers" size="24" class="text-primary" />
            </div>
          </div>
        </div>

        <div class="glass-card-enhanced rounded-xl p-4 sm:p-6">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-xs sm:text-sm text-muted-foreground mb-1">Total Syncs</p>
              <p class="text-2xl sm:text-3xl font-bold text-foreground">
                {{ savedLists.reduce((sum, list) => sum + (list.syncCount || 0), 0) }}
              </p>
            </div>
            <div class="p-3 rounded-xl bg-primary/10">
              <AppIcon icon="lucide:refresh-cw" size="24" class="text-primary" />
            </div>
          </div>
        </div>
      </div>

      <!-- List Cards -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div
          v-for="list in savedLists"
          :key="list.id"
          @click="openListModal(list)"
          class="glass-card-enhanced rounded-xl p-5 border border-border hover:border-primary/50 transition-all hover:shadow-lg cursor-pointer h-full flex flex-col"
        >
          <!-- Source Badge -->
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-2 px-2 py-1 rounded-lg bg-primary/10 border border-primary/20">
              <AppIcon 
                :icon="getListIcon(list.listType)" 
                size="12" 
                class="text-primary" 
              />
              <span class="text-xs font-medium text-foreground uppercase">
                {{ formatListType(list.listType) }}
              </span>
            </div>
          </div>

          <!-- Content Area (flexible) -->
          <div class="flex-1 flex flex-col">
            <!-- List Name -->
            <h3 class="font-semibold text-lg text-foreground mb-2 line-clamp-2">
              {{ getListDisplayName(list) }}
            </h3>
            <p class="text-xs text-muted-foreground mb-4 line-clamp-1" :title="list.listIdentifier">
              {{ list.listIdentifier }}
            </p>

            <!-- Stats -->
            <div class="grid grid-cols-2 gap-3 mb-4">
              <div class="flex items-center gap-2">
                <div class="p-2 rounded-lg bg-muted/20">
                  <AppIcon icon="lucide:layers" size="14" class="text-foreground" />
                </div>
                <div>
                  <p class="text-[10px] text-muted-foreground">Items</p>
                  <p class="text-lg font-bold text-foreground">{{ list.itemCount || 0 }}</p>
                </div>
              </div>

              <div class="flex items-center gap-2">
                <div class="p-2 rounded-lg bg-muted/20">
                  <AppIcon icon="lucide:clock" size="14" class="text-foreground" />
                </div>
                <div class="flex-1 min-w-0">
                  <p class="text-[10px] text-muted-foreground">Last Synced</p>
                  <p class="text-xs font-medium text-foreground truncate">
                    {{ list.lastSynced ? formatDate(list.lastSynced) : 'Never' }}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-2 pt-4 border-t border-border mt-auto" @click.stop>
            <button
              @click="retriggerList(list.listIdentifier)"
              :disabled="syncing"
              class="flex-1 px-3 py-2 bg-primary text-primary-foreground rounded-lg transition-colors hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 text-sm font-medium"
            >
              <AppIcon 
                :icon="syncing ? 'lucide:loader-2' : 'lucide:refresh-cw'" 
                size="16" 
                :class="{ 'animate-spin': syncing }"
              />
              Sync Now
            </button>
            <button
              @click="deleteList(list.id)"
              class="px-3 py-2 hover:bg-destructive/20 text-destructive rounded-lg transition-colors"
              title="Delete list"
            >
              <AppIcon icon="lucide:trash-2" size="16" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Add List Modal -->
    <AddListModal
      v-model="showAddModal"
      @list-added="handleListAdded"
    />

    <!-- List Items Modal -->
    <ListItemsModal
      v-model="showListModal"
      :list-identifier="selectedList?.listIdentifier || ''"
      :list-name="selectedList ? getListDisplayName(selectedList) : ''"
      :list-id="selectedList?.id"
    />
  </div>
</template>

<script setup lang="ts">
import AddListModal from '~/components/ListSync/AddListModal.vue'
import EmptyState from '~/components/ListSync/EmptyState.vue'
import ListItemsModal from '~/components/ListSync/ListItemsModal.vue'

// State
const showAddModal = ref(false)
const showListModal = ref(false)
const selectedList = ref<any>(null)
const savedLists = ref<any[]>([])
const loadingLists = ref(false)
const syncing = ref(false)
const error = ref('')

// Lifecycle
onMounted(() => {
  loadSavedLists()
})

// Data loading
const loadSavedLists = async () => {
  loadingLists.value = true
  try {
    const response = await $fetch('/api/trakt-lists/lists')
    if (response.success) {
      savedLists.value = response.lists || []
    }
  } catch (err: any) {
    console.error('Error loading saved lists:', err)
    error.value = 'Failed to load lists'
  } finally {
    loadingLists.value = false
  }
}

const handleListAdded = async (data: { listId: string; sync: boolean }) => {
  // Refresh lists
  await loadSavedLists()
  
  if (data.sync) {
    // Trigger sync for the new list
    await retriggerList(data.listId)
  }
}

const retriggerList = async (listIdentifier: string) => {
  syncing.value = true
  error.value = ''
  
  try {
    const response = await $fetch('/api/trakt-lists/sync', {
      method: 'POST',
      body: {
        listId: listIdentifier,
        limit: null,
        dryRun: false
      }
    })
    
    if (response.success) {
      // Reload lists to update stats
      await loadSavedLists()
    } else {
      error.value = response.error || 'Failed to sync list'
    }
  } catch (err: any) {
    console.error('Error syncing list:', err)
    error.value = err.data?.message || err.message || 'Failed to sync list'
  } finally {
    syncing.value = false
  }
}

const deleteList = async (listId: number) => {
  if (!confirm('Are you sure you want to delete this list? This will not delete sync history.')) {
    return
  }
  
  try {
    const response = await $fetch(`/api/trakt-lists/${listId}`, { method: 'DELETE' })
    if (response.success) {
      await loadSavedLists()
    }
  } catch (err: any) {
    console.error('Error deleting list:', err)
    error.value = 'Failed to delete list'
  }
}

const openListModal = (list: any) => {
  selectedList.value = list
  showListModal.value = true
}

// Helpers
const getListIcon = (type: string) => {
  const icons: Record<string, string> = {
    watchlist: 'lucide:bookmark',
    trending: 'lucide:trending-up',
    popular: 'lucide:star',
    custom: 'lucide:list',
    public: 'lucide:users',
    trakt_special: 'lucide:zap',
    letterboxd: 'lucide:book-open'
  }
  return icons[type] || 'lucide:list'
}

const formatListType = (type: string) => {
  if (type === 'trakt_special') return 'TRAKT SPECIAL'
  if (type === 'letterboxd') return 'LETTERBOXD'
  return type?.toUpperCase() || 'UNKNOWN'
}

const getListDisplayName = (list: any) => {
  // For Trakt Special lists, format nicely
  if (list.listType === 'trakt_special' && list.listIdentifier) {
    const parts = list.listIdentifier.split(':')
    if (parts.length === 2) {
      const [category, mediaType] = parts
      const catFormatted = category.charAt(0).toUpperCase() + category.slice(1)
      const mediaFormatted = mediaType === 'movies' ? 'Movies' : mediaType === 'shows' ? 'TV Shows' : mediaType
      return `${catFormatted} ${mediaFormatted}`
    }
  }
  
  // Use list name if available, otherwise use identifier
  return list.listName || list.listIdentifier || 'Unknown List'
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
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined })
}
</script>

<style scoped>
.line-clamp-1 {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
