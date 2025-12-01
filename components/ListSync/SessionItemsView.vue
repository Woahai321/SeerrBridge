<template>
  <div class="glass-card-enhanced rounded-2xl p-4 sm:p-6 lg:p-8">
    <div class="flex items-center justify-between mb-4 sm:mb-6">
      <h2 class="text-xl sm:text-2xl font-semibold text-foreground">Sync Items</h2>
      <button
        @click="$emit('close')"
        class="p-2 hover:bg-muted rounded-lg transition-colors"
      >
        <AppIcon icon="lucide:x" size="18" class="text-foreground" />
      </button>
    </div>
    
    <SyncItemList :items="items" />
  </div>
</template>

<script setup lang="ts">
import SyncItemList from '~/components/ListSync/SyncItemList.vue'

interface Props {
  items: any[]
}

defineProps<Props>()

defineEmits<{
  close: []
}>()
</script>

