import { readEnvFile } from '~/server/utils/env-file'
import { envConfig } from '~/server/utils/env-config'

export default defineEventHandler(async (event) => {
  try {
    // Read from .env file
    const envValues = readEnvFile()
    
    // Failed items config keys
    const failedItemConfigKeys = [
      'enable_failed_item_retry',
      'failed_item_retry_interval_minutes',
      'failed_item_max_retry_attempts',
      'failed_item_retry_delay_hours',
      'failed_item_retry_backoff_multiplier',
      'failed_item_max_retry_delay_hours'
    ]
    
    // Convert to object format
    const configs: Record<string, any> = {}
    for (const configKey of failedItemConfigKeys) {
      const envKey = envConfig.mapToEnvVars[configKey]
      if (!envKey) continue
      
      const value = envValues[envKey] || process.env[envKey]
      if (value === undefined || value === '') continue
      
      // Convert value based on type
      let convertedValue: any = value
      let configType = 'string'
      
      if (envKey === 'ENABLE_FAILED_ITEM_RETRY') {
        configType = 'boolean'
        convertedValue = value === 'true' || value === '1'
      } else {
        configType = 'integer'
        convertedValue = parseInt(value, 10)
        if (isNaN(convertedValue)) {
          convertedValue = value
          configType = 'string'
        }
      }
      
      configs[configKey] = {
        value: convertedValue,
        type: configType,
        description: getConfigDescription(configKey),
        is_active: true
      }
    }
    
    function getConfigDescription(key: string): string {
      const descriptions: Record<string, string> = {
        'enable_failed_item_retry': 'Enable or disable the automatic retry of failed media items',
        'failed_item_retry_interval_minutes': 'Interval in minutes between failed item retry checks',
        'failed_item_max_retry_attempts': 'Maximum number of retry attempts for failed items',
        'failed_item_retry_delay_hours': 'Initial delay in hours before the first retry attempt',
        'failed_item_retry_backoff_multiplier': 'Multiplier for the retry delay (e.g., 2 for exponential backoff: 2h, 4h, 8h)',
        'failed_item_max_retry_delay_hours': 'Maximum delay in hours between retry attempts for a failed item'
      }
      return descriptions[key] || 'Configuration setting'
    }
    
    // Get current failed items statistics (from database - this is application data, not config)
    const { getDatabaseConnection } = await import('~/server/utils/database')
    const db = await getDatabaseConnection()
    
    const statsQuery = `
      SELECT 
        COUNT(*) as total_failed,
        COUNT(CASE WHEN media_type = 'movie' THEN 1 END) as failed_movies,
        COUNT(CASE WHEN media_type = 'tv' THEN 1 END) as failed_tv_shows,
        COUNT(CASE WHEN is_in_queue = 1 THEN 1 END) as queued_for_retry,
        COUNT(CASE WHEN last_error_at > DATE_SUB(NOW(), INTERVAL 24 HOUR) THEN 1 END) as failed_last_24h,
        AVG(error_count) as avg_error_count,
        MAX(error_count) as max_error_count,
        COUNT(CASE WHEN error_count >= 3 THEN 1 END) as max_retries_reached
      FROM unified_media
      WHERE status = 'failed' AND error_message IS NOT NULL AND error_count > 0
    `
    
    const [statsResult] = await db.execute(statsQuery)
    const stats = (statsResult as any[])[0] || {}
    
    // Get retry schedule information
    const retryScheduleQuery = `
      SELECT 
        error_count,
        COUNT(*) as count,
        MIN(last_error_at) as oldest_error,
        MAX(last_error_at) as newest_error
      FROM unified_media
      WHERE status = 'failed' AND error_message IS NOT NULL AND error_count > 0
      GROUP BY error_count
      ORDER BY error_count
    `
    
    const [retryScheduleResult] = await db.execute(retryScheduleQuery)
    const retrySchedule = (retryScheduleResult as any[]).map(row => ({
      retry_attempt: row.error_count,
      count: row.count,
      oldest_error: row.oldest_error,
      newest_error: row.newest_error
    }))
    
    return {
      config: {
        enable_failed_item_retry: configs.enable_failed_item_retry?.value ?? true,
        failed_item_retry_interval_minutes: configs.failed_item_retry_interval_minutes?.value ?? 30,
        failed_item_max_retry_attempts: configs.failed_item_max_retry_attempts?.value ?? 3,
        failed_item_retry_delay_hours: configs.failed_item_retry_delay_hours?.value ?? 2,
        failed_item_retry_backoff_multiplier: configs.failed_item_retry_backoff_multiplier?.value ?? 2,
        failed_item_max_retry_delay_hours: configs.failed_item_max_retry_delay_hours?.value ?? 24
      },
      stats: {
        total_failed: stats.total_failed || 0,
        failed_movies: stats.failed_movies || 0,
        failed_tv_shows: stats.failed_tv_shows || 0,
        queued_for_retry: stats.queued_for_retry || 0,
        failed_last_24h: stats.failed_last_24h || 0,
        avg_error_count: Math.round((stats.avg_error_count || 0) * 10) / 10,
        max_error_count: stats.max_error_count || 0,
        max_retries_reached: stats.max_retries_reached || 0
      },
      retry_schedule: retrySchedule,
      config_descriptions: {
        enable_failed_item_retry: 'Enable or disable the automatic retry of failed media items',
        failed_item_retry_interval_minutes: 'Interval in minutes between failed item retry checks',
        failed_item_max_retry_attempts: 'Maximum number of retry attempts for failed items',
        failed_item_retry_delay_hours: 'Initial delay in hours before the first retry attempt',
        failed_item_retry_backoff_multiplier: 'Multiplier for the retry delay (exponential backoff)',
        failed_item_max_retry_delay_hours: 'Maximum delay in hours between retry attempts'
      }
    }
    
  } catch (error) {
    console.error('Error fetching failed items configuration:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to fetch failed items configuration'
    })
  }
})
