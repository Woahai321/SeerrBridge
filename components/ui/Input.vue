<template>
  <input
    :value="modelValue"
    :class="inputClass"
    :disabled="disabled"
    :type="type"
    :placeholder="placeholder"
    @input="handleInput"
  />
</template>

<script setup lang="ts">
interface Props {
  modelValue?: string | number
  disabled?: boolean
  error?: boolean
  type?: string
  placeholder?: string
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: '',
  disabled: false,
  error: false,
  type: 'text',
  placeholder: ''
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const handleInput = (event: Event) => {
  const target = event.target as HTMLInputElement
  emit('update:modelValue', target.value)
}

const inputClass = computed(() => {
  const baseClass = 'flex h-10 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50'
  
  const errorClass = props.error ? 'border-destructive focus-visible:ring-destructive' : ''
  
  return `${baseClass} ${errorClass}`
})
</script>
