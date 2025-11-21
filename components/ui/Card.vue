<template>
  <div :class="cardClass">
    <slot />
  </div>
</template>

<script setup lang="ts">
interface Props {
  variant?: 'default' | 'glass' | 'elevated'
  padding?: 'none' | 'sm' | 'md' | 'lg'
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'default',
  padding: 'md'
})

const cardClass = computed(() => {
  const baseClass = 'rounded-xl border border-border'
  
  const variants = {
    default: 'bg-card text-card-foreground',
    glass: 'glass-card',
    elevated: 'bg-card text-card-foreground shadow-lg'
  }
  
  const paddings = {
    none: '',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8'
  }
  
  return `${baseClass} ${variants[props.variant]} ${paddings[props.padding]}`
})
</script>
