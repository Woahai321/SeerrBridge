import { defineEventHandler } from 'h3'
import { envFile } from '~/server/utils/env-file'
import { setConfigInEnv } from '~/server/utils/env-config'

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

    // If we have all required configs, save them to .env file
    if (missingConfigs.length === 0 && foundConfigs.length > 0) {
      // Save all configs to .env file
      for (const config of foundConfigs) {
        let envValue: string | number | boolean = config.config_value
        
        // Convert based on type
        if (config.config_type === 'bool') {
          envValue = config.config_value === true || config.config_value === 'true'
        } else if (config.config_type === 'int') {
          envValue = parseInt(String(config.config_value), 10)
        } else if (config.config_type === 'float') {
          envValue = parseFloat(String(config.config_value))
        } else {
          envValue = String(config.config_value)
        }
        
        setConfigInEnv(config.config_key, envValue)
      }
      
      // Mark setup as completed in .env
      setConfigInEnv('onboarding_completed', true)
      setConfigInEnv('setup_required', false)
      
      return {
        success: true,
        message: 'Configuration loaded from environment variables and saved to .env file',
        configsLoaded: foundConfigs.length,
        configs: foundConfigs.map(c => ({ key: c.config_key, type: c.config_type }))
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

