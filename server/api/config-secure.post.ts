import { defineEventHandler, readBody } from 'h3'
import { setConfigInEnv } from '~/server/utils/env-config'

/**
 * Secure config endpoint - now just writes to .env file
 * This endpoint is kept for backwards compatibility but now uses .env
 */
export default defineEventHandler(async (event) => {
  try {
    const body = await readBody(event)
    const { configs } = body
    
    if (!configs || !Array.isArray(configs)) {
      return {
        success: false,
        error: 'Invalid configuration data'
      }
    }
    
    // Write all configs to .env file
    for (const config of configs) {
      const { config_key, config_value, config_type } = config
      
      if (!config_key) continue
      
      // Convert value based on type
      let envValue: string | number | boolean | null = null
      
      if (config_value === null || config_value === undefined || config_value === '') {
        envValue = null
      } else if (config_type === 'bool') {
        envValue = config_value === true || config_value === 'true'
      } else if (config_type === 'int') {
        envValue = parseInt(String(config_value), 10)
      } else if (config_type === 'float') {
        envValue = parseFloat(String(config_value))
      } else {
        envValue = String(config_value)
      }
      
      setConfigInEnv(config_key, envValue)
    }
    
    return {
      success: true,
      message: 'Configuration updated successfully in .env file'
    }
  } catch (error) {
    console.error('Error updating secure configuration:', error)
    return {
      success: false,
      error: 'Failed to update configuration'
    }
  }
})

