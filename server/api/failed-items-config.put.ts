import { getDatabaseConnection } from '~/server/utils/database'

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody(event)
    const db = await getDatabaseConnection()
    
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
    
    // Update configurations
    const updatePromises = configs.map(async (config) => {
      if (config.value === undefined || config.value === null) {
        return // Skip undefined values
      }
      
      const value = config.type === 'boolean' ? (config.value ? 'true' : 'false') : String(config.value)
      
      await db.execute(`
        INSERT INTO system_config (config_key, config_value, config_type, description, is_active, updated_at)
        VALUES (?, ?, ?, ?, TRUE, NOW())
        ON DUPLICATE KEY UPDATE
        config_value = VALUES(config_value),
        updated_at = NOW()
      `, [
        config.key,
        value,
        config.type,
        getConfigDescription(config.key)
      ])
    })
    
    await Promise.all(updatePromises)
    
    return {
      success: true,
      message: 'Failed items configuration updated successfully',
      updated_configs: configs.filter(c => c.value !== undefined && c.value !== null).map(c => c.key)
    }
    
  } catch (error) {
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

function getConfigDescription(key: string): string {
  const descriptions: Record<string, string> = {
    'enable_failed_item_retry': 'Enable or disable the automatic retry of failed media items',
    'failed_item_retry_interval_minutes': 'Interval in minutes between failed item retry checks',
    'failed_item_max_retry_attempts': 'Maximum number of retry attempts for failed items',
    'failed_item_retry_delay_hours': 'Initial delay in hours before the first retry attempt for a failed item',
    'failed_item_retry_backoff_multiplier': 'Multiplier for the retry delay (e.g., 2 for exponential backoff: 2h, 4h, 8h)',
    'failed_item_max_retry_delay_hours': 'Maximum delay in hours between retry attempts for a failed item'
  }
  
  return descriptions[key] || 'Configuration setting'
}
