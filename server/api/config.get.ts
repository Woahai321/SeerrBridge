import { defineEventHandler } from 'h3'
import { getAllConfigsFromEnv, maskSensitiveValue, SENSITIVE_CONFIG_KEYS } from '~/server/utils/env-config'

export default defineEventHandler(async (event) => {
  try {
    // Read all configs from .env file
    const configs = getAllConfigsFromEnv()
    
    // Process configs - mask sensitive values
    const maskedConfigs = configs.map((config) => {
      let value = config.config_value
      const isSensitive = SENSITIVE_CONFIG_KEYS.includes(config.config_key)
      const hasValue = value !== null && value !== undefined && value !== ''
      
      // Mask sensitive values for display
      if (isSensitive && hasValue && typeof value === 'string') {
        value = maskSensitiveValue(value)
      }
      
      return {
        config_key: config.config_key,
        config_value: value,
        config_type: config.config_type,
        description: `Configuration for ${config.config_key}`,
        is_active: true,
        is_encrypted: isSensitive && hasValue,
        has_value: hasValue
      }
    })
    
    return {
      success: true,
      data: maskedConfigs
    }
  } catch (error) {
    console.error('Error fetching configuration:', error)
    return {
      success: false,
      error: 'Failed to fetch configuration'
    }
  }
})
