import { defineEventHandler, readBody } from 'h3'
import { getDatabaseConnection } from '~/server/utils/database'

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
    
    const db = await getDatabaseConnection()
    
    // Validate config type
    const validTypes = ['string', 'int', 'float', 'bool', 'json']
    if (!validTypes.includes(configType)) {
      return {
        success: false,
        error: `Invalid config type. Must be one of: ${validTypes.join(', ')}`
      }
    }
    
    // Convert value to string for storage
    let stringValue
    if (configType === 'json') {
      stringValue = JSON.stringify(value)
    } else {
      stringValue = String(value)
    }
    
    // Check if config exists
    const [existingConfig] = await db.execute(`
      SELECT id FROM system_config WHERE config_key = ?
    `, [configKey])
    
    if ((existingConfig as any[]).length > 0) {
      // Update existing config
      await db.execute(`
        UPDATE system_config 
        SET config_value = ?, config_type = ?, description = ?, updated_at = NOW()
        WHERE config_key = ?
      `, [stringValue, configType, description || `Configuration for ${configKey}`, configKey])
    } else {
      // Insert new config
      await db.execute(`
        INSERT INTO system_config (config_key, config_value, config_type, description, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, 1, NOW(), NOW())
      `, [configKey, stringValue, configType, description || `Configuration for ${configKey}`])
    }
    
    // Trigger background task refresh if this is a task-related config
    const taskConfigKeys = [
      'enable_automatic_background_task',
      'enable_show_subscription_task',
      'refresh_interval_minutes',
      'movie_queue_maxsize',
      'tv_queue_maxsize',
      'token_refresh_interval_minutes',
      'movie_processing_check_interval_minutes',
      'library_refresh_interval_minutes',
      'subscription_check_interval_minutes',
      'background_tasks_enabled',
      'queue_processing_enabled',
      'scheduler_enabled'
    ]
    
    if (taskConfigKeys.includes(configKey)) {
      // Trigger a refresh of background tasks
      try {
        // Call the SeerrBridge API to reload environment variables
        const seerrbridgeUrl = process.env.SEERRBRIDGE_URL || 'http://localhost:8777'
        
        const refreshResponse = await fetch(`${seerrbridgeUrl}/reload-env`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          }
        })
        
        if (refreshResponse.ok) {
          console.log(`Task configuration updated: ${configKey} = ${value}. Background tasks refresh triggered successfully.`)
        } else {
          console.warn(`Failed to trigger background task refresh: ${refreshResponse.statusText}`)
        }
      } catch (error) {
        console.warn('Failed to trigger background task refresh:', error)
      }
    }
    
    return {
      success: true,
      message: `Configuration ${configKey} updated successfully`
    }
  } catch (error) {
    console.error('Error updating task configuration:', error)
    return {
      success: false,
      error: 'Failed to update task configuration',
      details: error instanceof Error ? error.message : 'Unknown error'
    }
  }
})
