import { defineEventHandler } from 'h3'
import { getDatabaseConnection } from '~/server/utils/database'

export default defineEventHandler(async (event) => {
  try {
    const db = await getDatabaseConnection()
    
    // Get current step
    const [currentStepResult] = await db.execute(`
      SELECT config_value FROM system_config 
      WHERE config_key = 'setup_current_step'
    `)
    
    const currentStep = (currentStepResult as any[])[0]?.config_value ? parseInt((currentStepResult as any[])[0].config_value) : 0
    
    // Get saved step progress
    const savedSteps: Record<number, any> = {}
    for (let step = 0; step < 4; step++) {
      const [stepResult] = await db.execute(`
        SELECT config_value FROM system_config 
        WHERE config_key = ?
      `, [`setup_step_${step}`])
      
      if ((stepResult as any[]).length > 0) {
        try {
          savedSteps[step] = JSON.parse((stepResult as any[])[0].config_value)
        } catch (e) {
          console.error(`Error parsing step ${step} data:`, e)
        }
      }
    }
    
    // Get all config values
    const [configResults] = await db.execute(`
      SELECT config_key, config_value, config_type FROM system_config 
      WHERE config_key IN ('rd_client_id', 'rd_client_secret', 'rd_access_token', 'rd_refresh_token', 
                          'overseerr_base', 'overseerr_api_key', 'trakt_api_key', 'headless_mode', 
                          'refresh_interval_minutes', 'torrent_filter_regex')
    `)
    
    const config: Record<string, any> = {}
    for (const row of configResults as any[]) {
      let value = row.config_value
      
      // Convert based on type
      if (row.config_type === 'bool') {
        value = value === 'true'
      } else if (row.config_type === 'int') {
        value = parseInt(value)
      }
      
      // Fix torrent_filter_regex if it has the wrong Unicode characters
      if (row.config_key === 'torrent_filter_regex' && value && value.includes('Ѐ-ӿ')) {
        value = '^(?!.*【.*?】)(?!.*[\\u0400-\\u04FF])(?!.*\\[esp\\]).*'
      }
      
      config[row.config_key] = value
    }
    
    return {
      success: true,
      data: {
        currentStep,
        savedSteps,
        config
      }
    }
  } catch (error: any) {
    console.error('Error loading setup state:', error)
    return {
      success: false,
      error: error.message || 'Unknown error',
      data: {
        currentStep: 0,
        savedSteps: {},
        config: {}
      }
    }
  }
})
