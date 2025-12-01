interface ConfigItem {
  config_key: string
  config_value: any
  config_type: string
  description: string
  is_active: boolean
  is_encrypted: boolean
  has_value: boolean
}

interface ConfigResponse {
  success: boolean
  data: ConfigItem[]
  error?: string
}

export const useConfig = () => {
  const config = ref<ConfigItem[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const fetchConfig = async () => {
    loading.value = true
    error.value = null
    
    try {
      const response = await $fetch<ConfigResponse>('/api/config')
      
      if (response.success) {
        config.value = response.data
      } else {
        error.value = response.error || 'Failed to fetch configuration'
      }
    } catch (err) {
      error.value = 'Failed to fetch configuration'
      console.error('Error fetching config:', err)
    } finally {
      loading.value = false
    }
  }

  const getConfigValue = (key: string): any => {
    const item = config.value.find(item => item.config_key === key)
    return item?.config_value || null
  }

  const hasConfigValue = (key: string): boolean => {
    const item = config.value.find(item => item.config_key === key)
    return item?.has_value || false
  }

  const isConfigEncrypted = (key: string): boolean => {
    const item = config.value.find(item => item.config_key === key)
    return item?.is_encrypted || false
  }

  // Computed properties for commonly used config values
  const overseerrBaseUrl = computed(() => {
    const url = getConfigValue('overseerr_base')
    // Ensure URL doesn't end with trailing slash
    return url ? url.replace(/\/$/, '') : null
  })

  const hasOverseerrConfig = computed(() => {
    return hasConfigValue('overseerr_base') && hasConfigValue('overseerr_api_key')
  })

  return {
    config: readonly(config),
    loading: readonly(loading),
    error: readonly(error),
    fetchConfig,
    getConfigValue,
    hasConfigValue,
    isConfigEncrypted,
    overseerrBaseUrl,
    hasOverseerrConfig
  }
}
