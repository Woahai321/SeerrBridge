import { defineEventHandler } from 'h3'
import { getDatabaseConnection } from '~/server/utils/database'

export default defineEventHandler(async (event) => {
  try {
    const db = await getDatabaseConnection()
    
    // Check if setup is required
    const [setupRequired] = await db.execute(`
      SELECT config_value FROM system_config 
      WHERE config_key = 'setup_required'
    `)
    
    const [onboardingCompleted] = await db.execute(`
      SELECT config_value FROM system_config 
      WHERE config_key = 'onboarding_completed'
    `)
    
    // Check for required configurations
    const requiredConfigs = [
      'rd_access_token', 'rd_refresh_token', 'rd_client_id', 'rd_client_secret',
      'overseerr_base', 'overseerr_api_key', 'trakt_api_key'
    ]
    
    const missingConfigs = []
    for (const configKey of requiredConfigs) {
      const [result] = await db.execute(`
        SELECT config_value FROM system_config 
        WHERE config_key = ? AND config_value IS NOT NULL AND config_value != ''
      `, [configKey])
      
      if ((result as any[]).length === 0) {
        missingConfigs.push(configKey)
      }
    }
    
    const needsSetup = (setupRequired as any[])[0]?.config_value === 'true' || 
                      (onboardingCompleted as any[])[0]?.config_value === 'false' ||
                      missingConfigs.length > 0
    
    return {
      success: true,
      data: {
        needsSetup,
        missingConfigs,
        setupRequired: (setupRequired as any[])[0]?.config_value === 'true',
        onboardingCompleted: (onboardingCompleted as any[])[0]?.config_value === 'true'
      }
    }
  } catch (error) {
    console.error('Error checking setup status:', error)
    return {
      success: true,
      data: {
        needsSetup: true,
        missingConfigs: ['rd_access_token', 'rd_refresh_token', 'rd_client_id', 'rd_client_secret', 'overseerr_base', 'overseerr_api_key', 'trakt_api_key'],
        setupRequired: true,
        onboardingCompleted: false
      }
    }
  }
})
