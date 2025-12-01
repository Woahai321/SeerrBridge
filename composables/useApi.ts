export const useApi = () => {
  const config = useRuntimeConfig()
  
  const apiCall = async <T>(endpoint: string, options: any = {}): Promise<T> => {
    console.debug(`🌐 API Call: ${config.public.apiBase}${endpoint}`)
    
    try {
      const data = await $fetch<T>(`${config.public.apiBase}${endpoint}`, {
        ...options,
        server: false
      })
      
      // DO NOT log full API response data - may contain sensitive information
      console.debug(`✅ API Success for ${endpoint}`)
      return data
    } catch (err) {
      // Only log error, not full error response which may contain sensitive data
      console.error(`❌ API Error for ${endpoint}:`, err instanceof Error ? err.message : 'Unknown error')
      throw err
    }
  }

  return {
    apiCall
  }
}
