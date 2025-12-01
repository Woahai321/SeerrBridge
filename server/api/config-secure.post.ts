import { defineEventHandler, readBody } from 'h3'

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
    
    // Forward to SeerrBridge backend API which handles encryption securely
    const seerrbridgeUrl = process.env.SEERRBRIDGE_URL || 'http://localhost:8777'
    
    try {
      const response = await fetch(`${seerrbridgeUrl}/api/config`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ configs })
      })
      
      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`SeerrBridge API returned ${response.status}: ${errorText}`)
      }
      
      const data = await response.json()
      
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
      
      // Return success response matching the expected format
      return {
        success: true,
        message: 'Configuration updated successfully',
        taskRefreshTriggered: hasTaskConfigChanges
      }
    } catch (apiError) {
      console.error('Error calling SeerrBridge API:', apiError)
      
      // Define sensitive keys that require encryption
      const sensitiveKeys = [
        'rd_access_token',
        'rd_refresh_token',
        'rd_client_id',
        'rd_client_secret',
        'overseerr_api_key',
        'trakt_api_key',
        'discord_webhook_url',
        'mysql_password',
        'mysql_root_password'
      ]
      
      // Check if any sensitive keys are being updated
      const hasSensitiveKeys = configs.some(config => 
        sensitiveKeys.includes(config.config_key)
      )
      
      // If sensitive keys are present, we must not use fallback (they need encryption)
      if (hasSensitiveKeys) {
        console.error('Cannot save sensitive keys without Python backend encryption. SeerrBridge backend must be running.')
        return {
          success: false,
          error: 'SeerrBridge backend is unavailable. Cannot save sensitive API keys without encryption. Please ensure the SeerrBridge backend service is running and try again.'
        }
      }
      
      // Fallback to direct database update only for non-sensitive keys
      console.warn('SeerrBridge backend unavailable. Using fallback mode for non-sensitive keys only.')
      const { getDatabaseConnection } = await import('~/server/utils/database')
      const db = await getDatabaseConnection()
      
      // Update each configuration
      for (const config of configs) {
        const { config_key, config_value, config_type, description } = config
        
        if (!config_key) continue
        
        // Skip sensitive keys in fallback mode (they should have been caught above)
        if (sensitiveKeys.includes(config_key)) {
          console.warn(`Skipping sensitive key ${config_key} in fallback mode`)
          continue
        }
        
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
      
      return {
        success: true,
        message: 'Configuration updated successfully (fallback mode - non-sensitive keys only)',
        taskRefreshTriggered: false
      }
    }
  } catch (error) {
    console.error('Error updating secure configuration:', error)
    return {
      success: false,
      error: 'Failed to update configuration'
    }
  }
})

