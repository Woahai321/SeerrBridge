import { defineEventHandler } from 'h3'
import { readEnvFile } from '~/server/utils/env-file'
import { envConfig } from '~/server/utils/env-config'

export default defineEventHandler(async (event) => {
  try {
    // Read from .env file
    const envValues = readEnvFile()
    
    // Also check process.env for runtime values
    const allEnv = { ...envValues, ...process.env }
    
    // Check setup status flags from .env
    const setupRequired = allEnv['SETUP_REQUIRED']?.toLowerCase() === 'true'
    const onboardingCompleted = allEnv['ONBOARDING_COMPLETED']?.toLowerCase() === 'true'
    
    // Check for required configurations in .env
    const requiredConfigs = [
      'rd_access_token', 'rd_refresh_token', 'rd_client_id', 'rd_client_secret',
      'overseerr_base', 'overseerr_api_key', 'trakt_api_key'
    ]
    
    const missingConfigs: string[] = []
    const envVarsAvailable: string[] = []
    const envVarsMissing: string[] = []
    
    const envVarMap: Record<string, string> = {
      'rd_access_token': 'RD_ACCESS_TOKEN',
      'rd_refresh_token': 'RD_REFRESH_TOKEN',
      'rd_client_id': 'RD_CLIENT_ID',
      'rd_client_secret': 'RD_CLIENT_SECRET',
      'overseerr_base': 'OVERSEERR_BASE',
      'overseerr_api_key': 'OVERSEERR_API_KEY',
      'trakt_api_key': 'TRAKT_API_KEY'
    }
    
    for (const configKey of requiredConfigs) {
      const envVar = envVarMap[configKey]
      if (!envVar) continue
      
      const value = allEnv[envVar]
      if (value && value.trim() !== '') {
        envVarsAvailable.push(configKey)
      } else {
        missingConfigs.push(configKey)
        envVarsMissing.push(configKey)
      }
    }
    
    // If all env vars are available, we can skip setup
    const canSkipSetup = envVarsAvailable.length === requiredConfigs.length
    
    // Setup is needed if:
    // 1. SETUP_REQUIRED is explicitly true AND onboarding is not completed
    // 2. Any required configs are missing (and we can't skip setup)
    // 3. onboarding_completed is not explicitly set to true AND configs are missing
    // BUT: If all configs are present, we should allow access even if onboarding_completed is not explicitly true
    // (This prevents users from being kicked back to setup when they update configs)
    const needsSetup = (setupRequired && onboardingCompleted !== true) || 
                      (missingConfigs.length > 0 && !canSkipSetup) ||
                      (onboardingCompleted !== true && missingConfigs.length > 0 && !canSkipSetup)
    
    // If all configs are present but onboarding_completed is not true, we can still allow access
    // (This handles the case where configs were updated but onboarding flag wasn't set)
    const shouldAllowAccess = canSkipSetup && envVarsAvailable.length === requiredConfigs.length
    
    return {
      success: true,
      data: {
        needsSetup: shouldAllowAccess ? false : needsSetup, // Override needsSetup if all configs are present
        missingConfigs,
        setupRequired,
        onboardingCompleted,
        envVarsAvailable,
        envVarsMissing,
        canSkipSetup,
        shouldAllowAccess
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
