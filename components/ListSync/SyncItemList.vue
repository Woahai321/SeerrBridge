<template>
  <div class="space-y-2 max-h-96 overflow-y-auto">
    <div
      v-for="item in items"
      :key="item.id"
      class="flex items-center justify-between p-3 sm:p-4 bg-card border border-border rounded-lg hover:bg-muted/50 transition-colors"
    >
      <div class="flex-1 min-w-0">
        <div class="font-medium text-foreground truncate">{{ item.title }}</div>
        <div class="text-xs sm:text-sm text-muted-foreground mt-1">
          {{ item.year || 'Unknown year' }} • {{ item.mediaType || item.media_type }}
          <span v-if="item.seasonNumber || item.season_number" class="ml-1">
            • Season {{ item.seasonNumber || item.season_number }}
          </span>
        </div>
        <div v-if="item.matchMethod || item.match_method" class="text-xs text-muted-foreground mt-1">
          Matched via: {{ item.matchMethod || item.match_method }}
        </div>
      </div>
      <div class="flex items-center gap-2 ml-4 flex-shrink-0">
        <StatusBadge :status="item.status" />
        <AppIcon 
          v-if="item.errorMessage || item.error_message" 
          icon="lucide:alert-circle" 
          size="16" 
          class="text-destructive" 
          :title="item.errorMessage || item.error_message"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import StatusBadge from '~/components/ListSync/StatusBadge.vue'

interface Props {
  items: any[]
}

defineProps<Props>()
</script>

