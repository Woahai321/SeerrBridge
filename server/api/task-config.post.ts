import { defineEventHandler, readBody } from 'h3'
import { writeEnvFile } from '~/server/utils/env-file'
import { envConfig } from '~/server/utils/env-config'

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody(event)
    const { configKey, value, configType = 'string', description } = body
    
    if (!configKey) {
      return {
        success: false,
        error: 'configKey is required'
      }
    }
    
    // Get environment variable name
    const envKey = envConfig.mapToEnvVars[configKey]
    if (!envKey) {
      return {
        success: false,
        error: `No environment variable mapping for config key: ${configKey}`
      }
    }
    
    // Convert value based on type
    let envValue: string | boolean | number
    if (configType === 'bool') {
      envValue = value === true || value === 'true' || value === '1' ? 'true' : 'false'
    } else if (configType === 'int' || configType === 'float') {
      envValue = String(value)
    } else {
      envValue = String(value)
    }
    
    // Write to .env file
    writeEnvFile({ [envKey]: envValue })
    
    // Trigger background task refresh if this is a task-related config
    const taskConfigKeys = [
      'enable_automatic_background_task',
      'enable_show_subscription_task',
      'refresh_interval_minutes',
      'headless_mode',
      'torrent_filter_regex',
      'max_movie_size',
      'max_episode_size'
    ]
    
    if (taskConfigKeys.includes(configKey)) {
      // Trigger a refresh of background tasks
      try {
        const seerrbridgeUrl = process.env.SEERRBRIDGE_URL || 'http://localhost:8777'
        await fetch(`${seerrbridgeUrl}/reload-env`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          signal: AbortSignal.timeout(2000)
        })
        console.log(`Task configuration updated: ${configKey} = ${value}. Background tasks refresh triggered.`)
      } catch (error) {
        console.debug('Backend not available for immediate refresh, changes will be picked up on next reload')
      }
    }
    
    return {
      success: true,
      message: `Configuration ${configKey} updated successfully in .env file`
    }
  } catch (error: any) {
    console.error('Error updating task configuration:', error)
    return {
      success: false,
      error: 'Failed to update task configuration',
      details: error.message || 'Unknown error'
    }
  }
})
