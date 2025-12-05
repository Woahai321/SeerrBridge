import { envFile } from './env-file'

/**
 * Map between config keys (database format) and environment variable names
 */
const CONFIG_TO_ENV_MAP: Record<string, string> = {
  'rd_access_token': 'RD_ACCESS_TOKEN',
  'rd_refresh_token': 'RD_REFRESH_TOKEN',
  'rd_client_id': 'RD_CLIENT_ID',
  'rd_client_secret': 'RD_CLIENT_SECRET',
  'overseerr_base': 'OVERSEERR_BASE',
  'overseerr_api_key': 'OVERSEERR_API_KEY',
  'trakt_api_key': 'TRAKT_API_KEY',
  'discord_webhook_url': 'DISCORD_WEBHOOK_URL',
  'headless_mode': 'HEADLESS_MODE',
  'enable_automatic_background_task': 'ENABLE_AUTOMATIC_BACKGROUND_TASK',
  'enable_show_subscription_task': 'ENABLE_SHOW_SUBSCRIPTION_TASK',
  'refresh_interval_minutes': 'REFRESH_INTERVAL_MINUTES',
  'torrent_filter_regex': 'TORRENT_FILTER_REGEX',
  'max_movie_size': 'MAX_MOVIE_SIZE',
  'max_episode_size': 'MAX_EPISODE_SIZE',
  'db_host': 'DB_HOST',
  'db_port': 'DB_PORT',
  'db_name': 'DB_NAME',
  'db_user': 'DB_USER',
  'db_password': 'DB_PASSWORD',
  'mysql_root_password': 'MYSQL_ROOT_PASSWORD',
  'setup_required': 'SETUP_REQUIRED',
  'onboarding_completed': 'ONBOARDING_COMPLETED',
  'enable_failed_item_retry': 'ENABLE_FAILED_ITEM_RETRY',
  'failed_item_retry_interval_minutes': 'FAILED_ITEM_RETRY_INTERVAL_MINUTES',
  'failed_item_max_retry_attempts': 'FAILED_ITEM_MAX_RETRY_ATTEMPTS',
  'failed_item_retry_delay_hours': 'FAILED_ITEM_RETRY_DELAY_HOURS',
  'failed_item_retry_backoff_multiplier': 'FAILED_ITEM_RETRY_BACKOFF_MULTIPLIER',
  'failed_item_max_retry_delay_hours': 'FAILED_ITEM_MAX_RETRY_DELAY_HOURS',
  'background_tasks_enabled': 'BACKGROUND_TASKS_ENABLED',
  'scheduler_enabled': 'SCHEDULER_ENABLED',
  'token_refresh_interval_minutes': 'TOKEN_REFRESH_INTERVAL_MINUTES',
  'movie_processing_check_interval_minutes': 'MOVIE_PROCESSING_CHECK_INTERVAL_MINUTES',
  'movie_queue_maxsize': 'MOVIE_QUEUE_MAXSIZE',
  'tv_queue_maxsize': 'TV_QUEUE_MAXSIZE'
}

/**
 * Reverse map: environment variable names to config keys
 */
const ENV_TO_CONFIG_MAP: Record<string, string> = {}
for (const [configKey, envKey] of Object.entries(CONFIG_TO_ENV_MAP)) {
  ENV_TO_CONFIG_MAP[envKey] = configKey
}

/**
 * Get config value from .env file
 */
export function getConfigFromEnv(configKey: string): string | undefined {
  const envKey = CONFIG_TO_ENV_MAP[configKey]
  if (!envKey) {
    return undefined
  }
  
  // First try .env file
  const envValue = envFile.get(envKey)
  if (envValue !== undefined) {
    return envValue
  }
  
  // Fallback to process.env (for runtime environment variables)
  return process.env[envKey]
}

/**
 * Set config value in .env file
 */
export function setConfigInEnv(configKey: string, value: string | number | boolean | null | undefined): void {
  const envKey = CONFIG_TO_ENV_MAP[configKey]
  if (!envKey) {
    console.warn(`No environment variable mapping for config key: ${configKey}`)
    return
  }
  
  envFile.set(envKey, value)
}

/**
 * Get all configs from .env file
 */
export function getAllConfigsFromEnv(): Array<{ config_key: string; config_value: any; config_type: string }> {
  const configs: Array<{ config_key: string; config_value: any; config_type: string }> = []
  const env = envFile.readEnv()
  
  // Also check process.env for any missing values
  const allEnv = { ...env, ...process.env }
  
  for (const [configKey, envKey] of Object.entries(CONFIG_TO_ENV_MAP)) {
    const value = allEnv[envKey]
    
    // Include empty strings (they're valid values), but skip undefined (missing)
    if (value === undefined) {
      continue
    }
    
    // Determine config type
    let configType = 'string'
    let configValue: any = value
    
    // Handle empty strings - they should be returned as empty strings
    if (value === '') {
      configType = 'string'
      configValue = ''
    } else {
      // Try to infer type for non-empty values
      if (value === 'true' || value === 'false') {
        configType = 'bool'
        configValue = value === 'true'
      } else if (!isNaN(Number(value)) && value !== '') {
        if (value.includes('.')) {
          configType = 'float'
          configValue = parseFloat(value)
        } else {
          configType = 'int'
          configValue = parseInt(value, 10)
        }
      }
    }
    
    configs.push({
      config_key: configKey,
      config_value: configValue,
      config_type: configType
    })
  }
  
  return configs
}

/**
 * Mask sensitive values for display
 */
export function maskSensitiveValue(value: string): string {
  if (!value || value.length === 0) {
    return ''
  }
  
  if (value.length > 6) {
    return `${value.substring(0, 3)}${'*'.repeat(value.length - 6)}${value.substring(value.length - 3)}`
  } else if (value.length > 3) {
    return `${value.substring(0, 2)}${'*'.repeat(value.length - 4)}${value.substring(value.length - 2)}`
  } else {
    return '*'.repeat(value.length)
  }
}

/**
 * List of sensitive config keys that should be masked
 */
export const SENSITIVE_CONFIG_KEYS = [
  'rd_access_token',
  'rd_refresh_token',
  'rd_client_id',
  'rd_client_secret',
  'overseerr_api_key',
  'trakt_api_key',
  'discord_webhook_url',
  'db_password',
  'mysql_root_password'
]

/**
 * Export config mapping object for direct access
 */
export const envConfig = {
  mapToEnvVars: CONFIG_TO_ENV_MAP,
  mapToConfigKeys: ENV_TO_CONFIG_MAP
}

