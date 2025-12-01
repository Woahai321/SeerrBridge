<template>
  <span>{{ displayValue.toLocaleString() }}</span>
</template>

<script setup lang="ts">
interface Props {
  value: number
  duration?: number
}

const props = withDefaults(defineProps<Props>(), {
  duration: 1000
})

// Simple display - no animation for now to avoid SSR issues
const displayValue = computed(() => props.value)
</script>
