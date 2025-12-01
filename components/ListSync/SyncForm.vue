<template>
  <div class="space-y-4 sm:space-y-6">
    <!-- Sync Form Card -->
    <div class="glass-card-enhanced rounded-2xl p-4 sm:p-6 lg:p-8">
      <h2 class="text-xl sm:text-2xl font-semibold text-foreground mb-4 sm:mb-6">Sync Trakt List</h2>
      
      <div class="space-y-4 sm:space-y-6">
        <div>
          <label class="block text-sm sm:text-base font-medium text-foreground mb-2">
            Trakt List URL or ID
          </label>
          <input
            :value="listId"
            @input="$emit('update:listId', ($event.target as HTMLInputElement).value)"
            type="text"
            placeholder="e.g., trending:movies, https://trakt.tv/users/username/watchlist"
            class="w-full px-4 py-3 bg-card border-2 border-border rounded-lg focus:outline-none focus:border-primary transition-colors text-foreground placeholder:text-muted-foreground"
            :disabled="loading || syncing"
            @keyup.enter="$emit('fetch')"
          />
          <p class="text-xs sm:text-sm text-muted-foreground mt-2">
            Supports: URLs, watchlists, custom lists, or shortcuts like "trending:movies", "popular:shows"
          </p>
        </div>
        
        <div>
          <label class="block text-sm sm:text-base font-medium text-foreground mb-2">
            Limit (optional, for special lists)
          </label>
          <input
            :value="limit"
            @input="$emit('update:limit', ($event.target as HTMLInputElement).value ? parseInt(($event.target as HTMLInputElement).value) : null)"
            type="number"
            placeholder="e.g., 20"
            min="1"
            max="100"
            class="w-full px-4 py-3 bg-card border-2 border-border rounded-lg focus:outline-none focus:border-primary transition-colors text-foreground placeholder:text-muted-foreground"
            :disabled="loading || syncing"
          />
        </div>
        
        <div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 sm:gap-4">
          <button
            @click="$emit('fetch')"
            :disabled="loading || syncing || !listId"
            class="flex-1 px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium flex items-center justify-center gap-2"
          >
            <AppIcon 
              :icon="loading ? 'lucide:loader-2' : 'lucide:search'" 
              size="18" 
              :class="{ 'animate-spin': loading }"
            />
            {{ loading ? 'Loading...' : 'Fetch List' }}
          </button>
          
          <button
            @click="$emit('sync')"
            :disabled="loading || syncing || !listId || !listItems.length"
            class="flex-1 px-6 py-3 bg-success text-white rounded-lg hover:bg-success/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium flex items-center justify-center gap-2"
          >
            <AppIcon 
              :icon="syncing ? 'lucide:loader-2' : 'lucide:sync'" 
              size="18" 
              :class="{ 'animate-spin': syncing }"
            />
            {{ syncing ? 'Syncing...' : 'Sync to Overseerr' }}
          </button>
          
          <label class="flex items-center gap-2 px-4 py-3 bg-muted rounded-lg cursor-pointer hover:bg-muted/80 transition-colors">
            <input
              :checked="dryRun"
              @change="$emit('update:dryRun', ($event.target as HTMLInputElement).checked)"
              type="checkbox"
              class="rounded"
              :disabled="loading || syncing"
            />
            <span class="text-sm text-foreground">Dry Run</span>
          </label>
        </div>
      </div>
    </div>

    <!-- Error Message -->
    <div v-if="error" class="glass-card-enhanced rounded-2xl p-4 sm:p-6 border-2 border-destructive/50 bg-destructive/10">
      <div class="flex items-start gap-3">
        <AppIcon icon="lucide:alert-circle" size="20" class="text-destructive flex-shrink-0 mt-0.5" />
        <div class="flex-1">
          <h3 class="font-semibold text-destructive mb-1">Error</h3>
          <p class="text-sm text-destructive/90">{{ error }}</p>
        </div>
        <button
          @click="$emit('clear-error')"
          class="p-1 hover:bg-destructive/20 rounded transition-colors"
        >
          <AppIcon icon="lucide:x" size="16" class="text-destructive" />
        </button>
      </div>
    </div>

    <!-- List Preview -->
    <div v-if="listItems.length > 0" class="glass-card-enhanced rounded-2xl p-4 sm:p-6 lg:p-8">
      <h2 class="text-xl sm:text-2xl font-semibold text-foreground mb-4 sm:mb-6">
        List Preview
        <span class="text-sm sm:text-base font-normal text-muted-foreground ml-2">
          ({{ listItems.length }} {{ listItems.length === 1 ? 'item' : 'items' }})
        </span>
      </h2>
      <SyncItemList :items="listItems.map(item => ({ ...item, mediaType: item.media_type }))" />
    </div>

    <!-- Sync Results -->
    <div v-if="syncResults" class="glass-card-enhanced rounded-2xl p-4 sm:p-6 lg:p-8">
      <h2 class="text-xl sm:text-2xl font-semibold text-foreground mb-4 sm:mb-6">Sync Results</h2>
      
      <SyncStatsGrid :stats="syncResults.results" />
      
      <div class="mt-6">
        <SyncItemList :items="syncResults.details || []" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import SyncItemList from '~/components/ListSync/SyncItemList.vue'
import SyncStatsGrid from '~/components/ListSync/SyncStatsGrid.vue'

interface Props {
  listId: string
  limit: number | null
  dryRun: boolean
  loading: boolean
  syncing: boolean
  listItems: any[]
  syncResults: any
  error: string
}

defineProps<Props>()

defineEmits<{
  'update:listId': [value: string]
  'update:limit': [value: number | null]
  'update:dryRun': [value: boolean]
  fetch: []
  sync: []
  'clear-error': []
}>()
</script>

