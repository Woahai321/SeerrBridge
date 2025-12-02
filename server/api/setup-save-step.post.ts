import { defineEventHandler, readBody } from 'h3'
import { getDatabaseConnection } from '~/server/utils/database'

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody(event)
    const { step, config, testResults } = body
    
    if (step === undefined || !config) {
      return {
        success: false,
        error: 'Missing required data'
      }
    }
    
    const db = await getDatabaseConnection()
    
    // Save the step progress
    await db.execute(`
      INSERT INTO system_config (config_key, config_value, config_type, description, is_active, created_at, updated_at)
      VALUES (?, ?, ?, ?, true, NOW(), NOW())
      ON DUPLICATE KEY UPDATE 
        config_value = VALUES(config_value),
        updated_at = NOW()
    `, [
      `setup_step_${step}`,
      JSON.stringify({ config, testResults }),
      'json',
      `Setup step ${step} progress`
    ])
    
    // Save individual config values to .env file (not database)
    const { writeEnvFile } = await import('~/server/utils/env-file')
    const { envConfig } = await import('~/server/utils/env-config')
    
    const envUpdates: Record<string, string | boolean | number> = {}
    for (const [key, value] of Object.entries(config)) {
      if (value !== null && value !== undefined && value !== '') {
        const envKey = envConfig.mapToEnvVars[key]
        if (envKey) {
          // Convert value based on type
          if (typeof value === 'boolean') {
            envUpdates[envKey] = value ? 'true' : 'false'
          } else if (typeof value === 'number') {
            envUpdates[envKey] = String(value)
          } else {
            envUpdates[envKey] = String(value)
          }
        }
      }
    }
    
    // Write config values to .env file
    if (Object.keys(envUpdates).length > 0) {
      writeEnvFile(envUpdates)
    }
    
    // Update current step
    await db.execute(`
      INSERT INTO system_config (config_key, config_value, config_type, description, is_active, created_at, updated_at)
      VALUES (?, ?, ?, ?, true, NOW(), NOW())
      ON DUPLICATE KEY UPDATE 
        config_value = VALUES(config_value),
        updated_at = NOW()
    `, [
      'setup_current_step',
      String(step),
      'int',
      'Current setup step'
    ])
    
    return {
      success: true,
      message: 'Step progress saved successfully'
    }
  } catch (error: any) {
    console.error('Error saving step progress:', error)
    return {
      success: false,
      error: error.message || 'Unknown error'
    }
  }
})
