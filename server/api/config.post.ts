import { defineEventHandler, readBody } from 'h3'
import { getDatabaseConnection } from '~/server/utils/database'

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
    
    const db = await getDatabaseConnection()
    
    // Update each configuration
    for (const config of configs) {
      const { config_key, config_value, config_type, description } = config
      
      if (!config_key) continue
      
      // Convert boolean values to string for database storage
      let dbValue = config_value
      if (config_type === 'bool') {
        dbValue = config_value ? 'true' : 'false'
      }
      
      // Check if config exists
      const [existing] = await db.execute(`
        SELECT id FROM system_config WHERE config_key = ?
      `, [config_key])
      
      if ((existing as any[]).length > 0) {
        // Update existing
        await db.execute(`
          UPDATE system_config 
          SET config_value = ?, config_type = ?, description = ?, updated_at = NOW()
          WHERE config_key = ?
        `, [dbValue, config_type, description, config_key])
      } else {
        // Insert new
        await db.execute(`
          INSERT INTO system_config (config_key, config_value, config_type, description, is_active, created_at, updated_at)
          VALUES (?, ?, ?, ?, true, NOW(), NOW())
        `, [config_key, dbValue, config_type, description])
      }
    }
    
    // Check if any task-related configurations were updated
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
      'scheduler_enabled',
      'headless_mode',
      'torrent_filter_regex',
      'max_movie_size',
      'max_episode_size'
    ]
    
    const hasTaskConfigChanges = configs.some(config => 
      taskConfigKeys.includes(config.config_key)
    )
    
    if (hasTaskConfigChanges) {
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
          console.log('Task configuration changes detected. Background tasks refresh triggered successfully.')
        } else {
          console.warn(`Failed to trigger background task refresh: ${refreshResponse.statusText}`)
        }
      } catch (error) {
        console.warn('Failed to trigger background task refresh:', error)
      }
    }
    
    return {
      success: true,
      message: 'Configuration updated successfully',
      taskRefreshTriggered: hasTaskConfigChanges
    }
  } catch (error) {
    console.error('Error updating configuration:', error)
    return {
      success: false,
      error: 'Failed to update configuration'
    }
  }
})
