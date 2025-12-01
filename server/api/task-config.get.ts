import { defineEventHandler, getQuery } from 'h3'
import { getDatabaseConnection } from '~/server/utils/database'

export default defineEventHandler(async (event) => {
  try {
    const db = await getDatabaseConnection()
    
    // Get all task-related configurations
    const [configs] = await db.execute(`
      SELECT config_key, config_value, config_type, description, is_active
      FROM system_config 
      WHERE config_key IN (
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
        'overseerr_base',
        'headless_mode',
        'torrent_filter_regex',
        'max_movie_size',
        'max_episode_size'
      )
      AND is_active = 1
      ORDER BY config_key
    `)
    
    // Convert to object format
    const taskConfig = {}
    for (const config of configs) {
      let value = config.config_value
      
      // Convert value based on type
      switch (config.config_type) {
        case 'bool':
          value = value === 'true' || value === '1'
          break
        case 'int':
          value = parseInt(value)
          break
        case 'float':
          value = parseFloat(value)
          break
        case 'json':
          try {
            value = JSON.parse(value)
          } catch (e) {
            value = value
          }
          break
        default:
          // string - keep as is
          break
      }
      
      taskConfig[config.config_key] = {
        value,
        type: config.config_type,
        description: config.description,
        isActive: config.is_active
      }
    }
    
    return {
      success: true,
      data: taskConfig
    }
  } catch (error) {
    console.error('Error fetching task configuration:', error)
    return {
      success: false,
      error: 'Failed to fetch task configuration',
      details: error.message
    }
  }
})
