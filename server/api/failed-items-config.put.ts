import { defineEventHandler, readBody, createError } from 'h3'
import { writeEnvFile } from '~/server/utils/env-file'
import { envConfig } from '~/server/utils/env-config'

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody(event)
    
    const {
      enable_failed_item_retry,
      failed_item_retry_interval_minutes,
      failed_item_max_retry_attempts,
      failed_item_retry_delay_hours,
      failed_item_retry_backoff_multiplier,
      failed_item_max_retry_delay_hours
    } = body
    
    // Validate input
    const configs = [
      { key: 'enable_failed_item_retry', value: enable_failed_item_retry, type: 'boolean' },
      { key: 'failed_item_retry_interval_minutes', value: failed_item_retry_interval_minutes, type: 'integer', min: 1, max: 1440 },
      { key: 'failed_item_max_retry_attempts', value: failed_item_max_retry_attempts, type: 'integer', min: 1, max: 10 },
      { key: 'failed_item_retry_delay_hours', value: failed_item_retry_delay_hours, type: 'integer', min: 1, max: 168 },
      { key: 'failed_item_retry_backoff_multiplier', value: failed_item_retry_backoff_multiplier, type: 'integer', min: 1, max: 10 },
      { key: 'failed_item_max_retry_delay_hours', value: failed_item_max_retry_delay_hours, type: 'integer', min: 1, max: 168 }
    ]
    
    // Validate each configuration
    for (const config of configs) {
      if (config.value === undefined || config.value === null) {
        continue // Skip undefined values
      }
      
      if (config.type === 'boolean') {
        if (typeof config.value !== 'boolean') {
          throw createError({
            statusCode: 400,
            statusMessage: `${config.key} must be a boolean value`
          })
        }
      } else if (config.type === 'integer') {
        const numValue = Number(config.value)
        if (isNaN(numValue) || !Number.isInteger(numValue)) {
          throw createError({
            statusCode: 400,
            statusMessage: `${config.key} must be an integer value`
          })
        }
        if (config.min !== undefined && numValue < config.min) {
          throw createError({
            statusCode: 400,
            statusMessage: `${config.key} must be at least ${config.min}`
          })
        }
        if (config.max !== undefined && numValue > config.max) {
          throw createError({
            statusCode: 400,
            statusMessage: `${config.key} must be at most ${config.max}`
          })
        }
      }
    }
    
    // Build updates for .env file
    const envUpdates: Record<string, string | boolean | number> = {}
    for (const config of configs) {
      if (config.value === undefined || config.value === null) {
        continue // Skip undefined values
      }
      
      const envKey = envConfig.mapToEnvVars[config.key]
      if (!envKey) {
        console.warn(`No environment variable mapping for config key: ${config.key}`)
        continue
      }
      
      if (config.type === 'boolean') {
        envUpdates[envKey] = config.value ? 'true' : 'false'
      } else {
        envUpdates[envKey] = String(config.value)
      }
    }
    
    // Write to .env file
    if (Object.keys(envUpdates).length > 0) {
      writeEnvFile(envUpdates)
    }
    
    return {
      success: true,
      message: 'Failed items configuration updated successfully in .env file',
      updated_configs: configs.filter(c => c.value !== undefined && c.value !== null).map(c => c.key)
    }
    
  } catch (error: any) {
    console.error('Error updating failed items configuration:', error)
    
    if (error.statusCode) {
      throw error
    }
    
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to update failed items configuration'
    })
  }
})
