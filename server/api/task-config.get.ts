import { defineEventHandler } from 'h3'
import { readEnvFile } from '~/server/utils/env-file'
import { envConfig } from '~/server/utils/env-config'

export default defineEventHandler(async (event) => {
  try {
    // Read from .env file
    const envValues = readEnvFile()
    
    // Task-related config keys
    const taskConfigKeys = [
      'enable_automatic_background_task',
      'enable_show_subscription_task',
      'refresh_interval_minutes',
      'headless_mode',
      'torrent_filter_regex',
      'max_movie_size',
      'max_episode_size'
    ]
    
    // Convert to object format
    const taskConfig: Record<string, any> = {}
    for (const configKey of taskConfigKeys) {
      const envKey = envConfig.mapToEnvVars[configKey]
      if (!envKey) continue
      
      const value = envValues[envKey] || process.env[envKey]
      if (value === undefined || value === '') continue
      
      // Convert value based on type
      let convertedValue: any = value
      let configType = 'string'
      
      if (['HEADLESS_MODE', 'ENABLE_AUTOMATIC_BACKGROUND_TASK', 'ENABLE_SHOW_SUBSCRIPTION_TASK'].includes(envKey)) {
        configType = 'bool'
        convertedValue = value === 'true' || value === '1'
      } else if (['REFRESH_INTERVAL_MINUTES', 'MAX_MOVIE_SIZE', 'MAX_EPISODE_SIZE'].includes(envKey)) {
        configType = 'int'
        convertedValue = parseInt(value, 10)
        if (isNaN(convertedValue)) {
          convertedValue = value
          configType = 'string'
        }
      } else {
        configType = 'string'
        convertedValue = value
      }
      
      taskConfig[configKey] = {
        value: convertedValue,
        type: configType,
        description: `Configuration for ${configKey}`,
        isActive: true
      }
    }
    
    return {
      success: true,
      data: taskConfig
    }
  } catch (error: any) {
    console.error('Error fetching task configuration:', error)
    return {
      success: false,
      error: 'Failed to fetch task configuration',
      details: error.message
    }
  }
})
