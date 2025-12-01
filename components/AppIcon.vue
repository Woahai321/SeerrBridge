<template>
  <ClientOnly>
    <span class="icon-wrapper">
      <Icon 
        v-if="icon"
        :name="icon" 
        :size="size" 
        :class="[className, 'icon-base']"
      />
    </span>
    <template #fallback>
      <span :class="[className, 'icon-base']" :style="{ width: size + 'px', height: size + 'px' }"></span>
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

<style scoped>
.icon-wrapper {
  display: inline-block;
  line-height: 0;
  vertical-align: middle;
  flex-shrink: 0;
  margin: 0;
  padding: 0;
}

.icon-base {
  display: block;
  line-height: 0;
  margin: 0;
  padding: 0;
}

.icon-base :deep(svg) {
  display: block;
  width: 100%;
  height: 100%;
  margin: 0;
  padding: 0;
  line-height: 0;
  vertical-align: top;
}

.icon-base :deep(*) {
  margin: 0;
  padding: 0;
  line-height: 0;
}
</style>