import { defineEventHandler, getQuery } from 'h3'
import { getDatabaseConnection } from '~/server/utils/database'

export default defineEventHandler(async (event) => {
  try {
    // Get decrypted configuration values from SeerrBridge API
    const seerrbridgeUrl = process.env.SEERRBRIDGE_URL || 'http://localhost:8777'
    
    let configs = []
    try {
      // Try to get decrypted configs from SeerrBridge API
      const response = await fetch(`${seerrbridgeUrl}/api/config`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        if (data.success && data.configs) {
          configs = data.configs
        }
      } else {
        console.warn(`SeerrBridge API returned ${response.status}: ${response.statusText}`)
      }
    } catch (apiError) {
      console.warn('Failed to get decrypted configs from SeerrBridge API, falling back to database:', apiError)
    }
    
    // Fallback to database if API fails
    if (configs.length === 0) {
      console.log('Falling back to database configuration')
      const db = await getDatabaseConnection()
      const [dbConfigs] = await db.execute(`
        SELECT config_key, config_value, config_type, description, is_active
        FROM system_config 
        WHERE is_active = true
        ORDER BY config_key
      `)
      configs = dbConfigs as any[]
    }
    
    // Process configs from backend (already masked if from SeerrBridge API)
    const maskedConfigs = (configs as any[]).map((config: any) => {
      let value = config.config_value
      
      // Convert string boolean values back to booleans
      if (config.config_type === 'bool') {
        if (value === 'true') value = true
        else if (value === 'false') value = false
      }
      
      // Convert string number values back to numbers
      if (config.config_type === 'int' || config.config_type === 'float') {
        const numValue = parseFloat(value)
        if (!isNaN(numValue)) {
          value = config.config_type === 'int' ? Math.floor(numValue) : numValue
        }
      }
      
      // If the config already has is_encrypted and has_value from the backend, use those
      // Otherwise, fall back to the old logic for database configs
      let isEncrypted = config.is_encrypted || false
      let hasValue = config.has_value !== undefined ? config.has_value : !!config.config_value
      
      // Fallback masking logic for database configs (when backend API is not available)
      if (!config.is_encrypted && !config.has_value) {
        const sensitiveKeys = [
          'rd_access_token', 'rd_refresh_token', 'rd_client_id', 'rd_client_secret',
          'overseerr_api_key', 'trakt_api_key', 'discord_webhook_url',
          'db_password', 'mysql_root_password'
        ]
        
        if (sensitiveKeys.includes(config.config_key) && config.config_value) {
          isEncrypted = true
          // Show first 3 and last 3 characters for sensitive values
          const originalValue = config.config_value
          if (originalValue.length > 6) {
            value = `${originalValue.substring(0, 3)}${'*'.repeat(originalValue.length - 6)}${originalValue.substring(originalValue.length - 3)}`
          } else if (originalValue.length > 3) {
            // For medium length values, show first 2 and last 2
            value = `${originalValue.substring(0, 2)}${'*'.repeat(originalValue.length - 4)}${originalValue.substring(originalValue.length - 2)}`
          } else {
            // For very short values, just show asterisks
            value = '*'.repeat(originalValue.length)
          }
        }
      }
      
      return {
        ...config,
        config_value: value,
        is_encrypted: isEncrypted,
        has_value: hasValue
      }
    })
    
    return {
      success: true,
      data: maskedConfigs
    }
  } catch (error) {
    console.error('Error fetching configuration:', error)
    return {
      success: false,
      error: 'Failed to fetch configuration'
    }
  }
})
