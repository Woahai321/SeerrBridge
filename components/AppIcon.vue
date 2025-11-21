<template>
  <ClientOnly>
    <Icon 
      v-if="icon"
      :name="icon" 
      :size="size" 
      :class="className"
    />
    <template #fallback>
      <span :class="className" :style="{ width: size + 'px', height: size + 'px' }"></span>
    </template>
  </ClientOnly>
</template>

<script setup lang="ts">
interface Props {
  icon?: string
  size?: string | number
  class?: string | Record<string, boolean>
}

const props = withDefaults(defineProps<Props>(), {
  icon: 'lucide:help-circle',
  size: '24',
  class: ''
})

const className = computed(() => {
  if (typeof props.class === 'string') {
    return props.class
  }
  if (typeof props.class === 'object' && props.class !== null) {
    return Object.entries(props.class)
      .filter(([, value]) => value)
      .map(([key]) => key)
      .join(' ')
  }
  return ''
})
</script>