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
    
    // Check for required configurations in database
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
    
    // Check for environment variables as fallback
    const envVarMap: Record<string, string> = {
      'rd_access_token': 'RD_ACCESS_TOKEN',
      'rd_refresh_token': 'RD_REFRESH_TOKEN',
      'rd_client_id': 'RD_CLIENT_ID',
      'rd_client_secret': 'RD_CLIENT_SECRET',
      'overseerr_base': 'OVERSEERR_BASE',
      'overseerr_api_key': 'OVERSEERR_API_KEY',
      'trakt_api_key': 'TRAKT_API_KEY'
    }
    
    const envVarsAvailable: string[] = []
    const envVarsMissing: string[] = []
    
    for (const configKey of requiredConfigs) {
      const envVar = envVarMap[configKey]
      if (envVar && process.env[envVar]) {
        envVarsAvailable.push(configKey)
      } else if (envVar) {
        envVarsMissing.push(configKey)
      }
    }
    
    // If all env vars are available, we can skip setup
    const canSkipSetup = envVarsAvailable.length === requiredConfigs.length
    
    const needsSetup = (setupRequired as any[])[0]?.config_value === 'true' || 
                      (onboardingCompleted as any[])[0]?.config_value === 'false' ||
                      (missingConfigs.length > 0 && !canSkipSetup)
    
    return {
      success: true,
      data: {
        needsSetup,
        missingConfigs,
        setupRequired: (setupRequired as any[])[0]?.config_value === 'true',
        onboardingCompleted: (onboardingCompleted as any[])[0]?.config_value === 'true',
        envVarsAvailable,
        envVarsMissing,
        canSkipSetup
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
        onboardingCompleted: false,
        envVarsAvailable: [],
        envVarsMissing: ['rd_access_token', 'rd_refresh_token', 'rd_client_id', 'rd_client_secret', 'overseerr_base', 'overseerr_api_key', 'trakt_api_key'],
        canSkipSetup: false
      }
    }
  }
})
