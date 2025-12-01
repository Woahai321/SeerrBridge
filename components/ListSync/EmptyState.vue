<template>
  <div class="text-center py-12">
    <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-muted/50 mb-4">
      <AppIcon :icon="icon" size="32" class="text-muted-foreground opacity-50" />
    </div>
    <p class="text-foreground text-lg font-medium mb-2">{{ title }}</p>
    <p class="text-sm text-muted-foreground mb-4">{{ description }}</p>
    <slot name="action">
      <button
        v-if="actionLabel && actionHandler"
        @click="actionHandler"
        class="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors text-sm font-medium inline-flex items-center gap-2"
      >
        <AppIcon :icon="actionIcon" size="16" />
        {{ actionLabel }}
      </button>
    </slot>
  </div>
</template>

<script setup lang="ts">
interface Props {
  icon?: string
  title: string
  description: string
  actionLabel?: string
  actionIcon?: string
  actionHandler?: () => void
}

withDefaults(defineProps<Props>(), {
  icon: 'lucide:inbox',
  actionIcon: 'lucide:plus'
})
</script>

