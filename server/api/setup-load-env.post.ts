import { defineEventHandler } from 'h3'
import { getDatabaseConnection } from '~/server/utils/database'
import { execSync } from 'child_process'
import { join } from 'path'

export default defineEventHandler(async (event) => {
  try {
    // Map environment variable names to config keys
    const envToConfigMap: Record<string, { key: string; type: string; description: string }> = {
      'RD_ACCESS_TOKEN': { key: 'rd_access_token', type: 'string', description: 'Real-Debrid Access Token' },
      'RD_REFRESH_TOKEN': { key: 'rd_refresh_token', type: 'string', description: 'Real-Debrid Refresh Token' },
      'RD_CLIENT_ID': { key: 'rd_client_id', type: 'string', description: 'Real-Debrid Client ID' },
      'RD_CLIENT_SECRET': { key: 'rd_client_secret', type: 'string', description: 'Real-Debrid Client Secret' },
      'OVERSEERR_BASE': { key: 'overseerr_base', type: 'string', description: 'Overseerr Base URL' },
      'OVERSEERR_API_KEY': { key: 'overseerr_api_key', type: 'string', description: 'Overseerr API Key' },
      'TRAKT_API_KEY': { key: 'trakt_api_key', type: 'string', description: 'Trakt API Key' },
      'HEADLESS_MODE': { key: 'headless_mode', type: 'bool', description: 'Run browser in headless mode' },
      'REFRESH_INTERVAL_MINUTES': { key: 'refresh_interval_minutes', type: 'int', description: 'Background task refresh interval in minutes' },
      'TORRENT_FILTER_REGEX': { key: 'torrent_filter_regex', type: 'string', description: 'Torrent filter regex pattern' }
    }

    const foundConfigs: Array<{ config_key: string; config_value: any; config_type: string; description: string }> = []
    const missingConfigs: string[] = []

    // Check for required environment variables
    const requiredConfigs = [
      'RD_ACCESS_TOKEN', 'RD_REFRESH_TOKEN', 'RD_CLIENT_ID', 'RD_CLIENT_SECRET',
      'OVERSEERR_BASE', 'OVERSEERR_API_KEY', 'TRAKT_API_KEY'
    ]

    for (const envKey of requiredConfigs) {
      const envValue = process.env[envKey]
      if (envValue) {
        const mapping = envToConfigMap[envKey]
        if (mapping) {
          let value: any = envValue
          
          // Convert types appropriately
          if (mapping.type === 'bool') {
            value = envValue.toLowerCase() === 'true'
          } else if (mapping.type === 'int') {
            value = parseInt(envValue, 10)
            if (isNaN(value)) {
              value = envValue // Keep as string if not a valid number
            }
          }
          
          foundConfigs.push({
            config_key: mapping.key,
            config_value: value,
            config_type: mapping.type,
            description: mapping.description
          })
        }
      } else {
        missingConfigs.push(envKey)
      }
    }

    // Check for optional environment variables
    const optionalConfigs = ['HEADLESS_MODE', 'REFRESH_INTERVAL_MINUTES', 'TORRENT_FILTER_REGEX']
    for (const envKey of optionalConfigs) {
      const envValue = process.env[envKey]
      if (envValue) {
        const mapping = envToConfigMap[envKey]
        if (mapping) {
          let value: any = envValue
          
          if (mapping.type === 'bool') {
            value = envValue.toLowerCase() === 'true'
          } else if (mapping.type === 'int') {
            value = parseInt(envValue, 10)
            if (isNaN(value)) {
              value = envValue
            }
          }
          
          foundConfigs.push({
            config_key: mapping.key,
            config_value: value,
            config_type: mapping.type,
            description: mapping.description
          })
        }
      }
    }

    // If we have all required configs, save them to the database
    if (missingConfigs.length === 0 && foundConfigs.length > 0) {
      // Use the secure config endpoint to save (handles encryption for sensitive values)
      const seerrbridgeUrl = process.env.SEERRBRIDGE_URL || 'http://localhost:8777'
      
      try {
        const response = await fetch(`${seerrbridgeUrl}/api/config`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ configs: foundConfigs })
        })
        
        if (!response.ok) {
          const errorText = await response.text()
          throw new Error(`SeerrBridge API returned ${response.status}: ${errorText}`)
        }
        
        // Mark setup as completed
        const db = await getDatabaseConnection()
        
        // Set onboarding_completed and setup_required flags
        const completionConfigs = [
          {
            config_key: 'onboarding_completed',
            config_value: true,
            config_type: 'bool',
            description: 'Setup completed'
          },
          {
            config_key: 'setup_required',
            config_value: false,
            config_type: 'bool',
            description: 'Setup no longer required'
          }
        ]
        
        for (const config of completionConfigs) {
          const [existing] = await db.execute(`
            SELECT id FROM system_config WHERE config_key = ?
          `, [config.config_key])
          
          if ((existing as any[]).length > 0) {
            await db.execute(`
              UPDATE system_config 
              SET config_value = ?, config_type = ?, description = ?, updated_at = NOW()
              WHERE config_key = ?
            `, [config.config_value ? 'true' : 'false', config.config_type, config.description, config.config_key])
          } else {
            await db.execute(`
              INSERT INTO system_config (config_key, config_value, config_type, description, is_active, created_at, updated_at)
              VALUES (?, ?, ?, ?, true, NOW(), NOW())
            `, [config.config_key, config.config_value ? 'true' : 'false', config.config_type, config.description])
          }
        }
        
        return {
          success: true,
          message: 'Configuration loaded from environment variables and saved successfully',
          configsLoaded: foundConfigs.length,
          configs: foundConfigs.map(c => ({ key: c.config_key, type: c.config_type }))
        }
      } catch (apiError) {
        console.error('Error calling SeerrBridge API, trying Python encryption script:', apiError)
        
        // Fallback: Try to use Python encryption script directly
        const db = await getDatabaseConnection()
        const sensitiveKeys = ['rd_access_token', 'rd_refresh_token', 'rd_client_id', 'rd_client_secret', 'overseerr_api_key', 'trakt_api_key']
        
        let allSaved = true
        const failedKeys: string[] = []
        
        for (const config of foundConfigs) {
          let dbValue = String(config.config_value)
          
          // Try to encrypt sensitive values using Python script
          if (sensitiveKeys.indexOf(config.config_key) !== -1) {
            try {
              const projectRoot = process.cwd()
              const encryptScriptPath = join(projectRoot, 'scripts', 'encrypt_value.py')
              
              // Call Python script to encrypt
              const result = execSync(`python3 "${encryptScriptPath}"`, {
                input: dbValue,
                encoding: 'utf8',
                maxBuffer: 10 * 1024 * 1024,
                stdio: ['pipe', 'pipe', 'pipe'],
                env: { ...process.env }
              })
              
              const parsed = JSON.parse(result.trim())
              if (parsed.value) {
                dbValue = parsed.value
              } else {
                throw new Error('Encryption returned no value')
              }
            } catch (encryptError) {
              console.warn(`Failed to encrypt ${config.config_key} using Python script:`, encryptError)
              failedKeys.push(config.config_key)
              allSaved = false
              continue
            }
          } else if (config.config_type === 'bool') {
            dbValue = config.config_value ? 'true' : 'false'
          }
          
          // Save to database
          const [existing] = await db.execute(`
            SELECT id FROM system_config WHERE config_key = ?
          `, [config.config_key])
          
          if ((existing as any[]).length > 0) {
            await db.execute(`
              UPDATE system_config 
              SET config_value = ?, config_type = ?, description = ?, updated_at = NOW()
              WHERE config_key = ?
            `, [dbValue, config.config_type, config.description, config.config_key])
          } else {
            await db.execute(`
              INSERT INTO system_config (config_key, config_value, config_type, description, is_active, created_at, updated_at)
              VALUES (?, ?, ?, ?, true, NOW(), NOW())
            `, [config.config_key, dbValue, config.config_type, config.description])
          }
        }
        
        // Mark setup as completed if we saved all configs
        if (allSaved) {
          const completionConfigs = [
            {
              config_key: 'onboarding_completed',
              config_value: true,
              config_type: 'bool',
              description: 'Setup completed'
            },
            {
              config_key: 'setup_required',
              config_value: false,
              config_type: 'bool',
              description: 'Setup no longer required'
            }
          ]
          
          for (const config of completionConfigs) {
            const [existing] = await db.execute(`
              SELECT id FROM system_config WHERE config_key = ?
            `, [config.config_key])
            
            if ((existing as any[]).length > 0) {
              await db.execute(`
                UPDATE system_config 
                SET config_value = ?, config_type = ?, description = ?, updated_at = NOW()
                WHERE config_key = ?
              `, [config.config_value ? 'true' : 'false', config.config_type, config.description, config.config_key])
            } else {
              await db.execute(`
                INSERT INTO system_config (config_key, config_value, config_type, description, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, true, NOW(), NOW())
              `, [config.config_key, config.config_value ? 'true' : 'false', config.config_type, config.description])
            }
          }
          
          return {
            success: true,
            message: 'Configuration loaded from environment variables and saved successfully (using Python encryption)',
            configsLoaded: foundConfigs.length,
            configs: foundConfigs.map(c => ({ key: c.config_key, type: c.config_type }))
          }
        } else {
          return {
            success: false,
            error: `Failed to encrypt and save some sensitive values: ${failedKeys.join(', ')}. Please ensure Python 3 and the encryption key are available.`,
            message: 'Some configuration values could not be saved',
            configsLoaded: foundConfigs.length - failedKeys.length,
            failedKeys
          }
        }
      }
    }

    return {
      success: false,
      message: 'Not all required environment variables are set',
      missingConfigs,
      foundConfigs: foundConfigs.map(c => ({ key: c.config_key, type: c.config_type }))
    }
  } catch (error) {
    console.error('Error loading configuration from environment variables:', error)
    return {
      success: false,
      error: 'Failed to load configuration from environment variables'
    }
  }
})

