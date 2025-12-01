<template>
  <span
    :class="badgeClasses"
    class="text-xs sm:text-sm font-medium capitalize px-2 py-1 rounded"
    :style="badgeStyle"
  >
    {{ displayText }}
  </span>
</template>

<script setup lang="ts">
interface Props {
  status: string
  size?: 'sm' | 'md' | 'lg'
}

const props = withDefaults(defineProps<Props>(), {
  size: 'md'
})

const statusConfig: Record<string, { class: string; style: string; label: string }> = {
  requested: {
    class: 'text-success',
    style: 'rgba(34, 197, 94, 0.1)',
    label: 'Requested'
  },
  already_requested: {
    class: 'text-info',
    style: 'rgba(147, 51, 234, 0.1)',
    label: 'Already Requested'
  },
  already_available: {
    class: 'text-primary',
    style: 'rgba(147, 51, 234, 0.1)',
    label: 'Already Available'
  },
  not_found: {
    class: 'text-warning',
    style: 'rgba(251, 191, 36, 0.1)',
    label: 'Not Found'
  },
  error: {
    class: 'text-destructive',
    style: 'rgba(239, 68, 68, 0.1)',
    label: 'Error'
  },
  completed: {
    class: 'text-success',
    style: 'rgba(34, 197, 94, 0.1)',
    label: 'Completed'
  },
  failed: {
    class: 'text-destructive',
    style: 'rgba(239, 68, 68, 0.1)',
    label: 'Failed'
  },
  in_progress: {
    class: 'text-warning',
    style: 'rgba(251, 191, 36, 0.1)',
    label: 'In Progress'
  },
  processing: {
    class: 'text-warning',
    style: 'rgba(251, 191, 36, 0.1)',
    label: 'Processing'
  },
  pending: {
    class: 'text-muted-foreground',
    style: 'rgba(128, 128, 128, 0.1)',
    label: 'Pending'
  },
  skipped: {
    class: 'text-muted-foreground',
    style: 'rgba(128, 128, 128, 0.1)',
    label: 'Skipped'
  },
  cancelled: {
    class: 'text-destructive',
    style: 'rgba(239, 68, 68, 0.1)',
    label: 'Cancelled'
  },
  ignored: {
    class: 'text-muted-foreground',
    style: 'rgba(128, 128, 128, 0.1)',
    label: 'Ignored'
  },
  unreleased: {
    class: 'text-muted-foreground',
    style: 'rgba(128, 128, 128, 0.1)',
    label: 'Unreleased'
  },
  success: {
    class: 'text-success',
    style: 'rgba(34, 197, 94, 0.1)',
    label: 'Success'
  },
  partial: {
    class: 'text-warning',
    style: 'rgba(251, 191, 36, 0.1)',
    label: 'Partial'
  }
}

const config = computed(() => statusConfig[props.status] || {
  class: 'text-muted-foreground',
  style: 'rgba(128, 128, 128, 0.1)',
  label: props.status.replace('_', ' ')
})

const badgeClasses = computed(() => config.value.class)
const badgeStyle = computed(() => ({ backgroundColor: config.value.style }))
const displayText = computed(() => config.value.label)
</script>

