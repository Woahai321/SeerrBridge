import { defineEventHandler } from 'h3'

export default defineEventHandler(async (event) => {
  try {
    // Return only non-sensitive environment variables that can be safely shown
    // Sensitive values (tokens, keys, secrets) are not returned
    const safeEnvVars: Record<string, any> = {}
    
    // Non-sensitive configuration values
    if (process.env.HEADLESS_MODE) {
      safeEnvVars.headless_mode = process.env.HEADLESS_MODE.toLowerCase() === 'true'
    }
    
    if (process.env.REFRESH_INTERVAL_MINUTES) {
      const val = parseInt(process.env.REFRESH_INTERVAL_MINUTES, 10)
      if (!isNaN(val)) {
        safeEnvVars.refresh_interval_minutes = val
      }
    }
    
    if (process.env.TORRENT_FILTER_REGEX) {
      safeEnvVars.torrent_filter_regex = process.env.TORRENT_FILTER_REGEX
    }
    
    // Check for optional system configs
    if (process.env.MAX_MOVIE_SIZE) {
      const val = parseFloat(process.env.MAX_MOVIE_SIZE)
      if (!isNaN(val)) {
        safeEnvVars.max_movie_size = val
      }
    }
    if (process.env.MAX_EPISODE_SIZE) {
      const val = parseFloat(process.env.MAX_EPISODE_SIZE)
      if (!isNaN(val)) {
        safeEnvVars.max_episode_size = val
      }
    }
    
    // Check for task configs
    if (process.env.BACKGROUND_TASKS_ENABLED) {
      safeEnvVars.background_tasks_enabled = process.env.BACKGROUND_TASKS_ENABLED.toLowerCase() === 'true'
    }
    if (process.env.SCHEDULER_ENABLED) {
      safeEnvVars.scheduler_enabled = process.env.SCHEDULER_ENABLED.toLowerCase() === 'true'
    }
    if (process.env.TOKEN_REFRESH_INTERVAL_MINUTES) {
      const val = parseInt(process.env.TOKEN_REFRESH_INTERVAL_MINUTES, 10)
      if (!isNaN(val)) {
        safeEnvVars.token_refresh_interval_minutes = val
      }
    }
    if (process.env.MOVIE_PROCESSING_CHECK_INTERVAL_MINUTES) {
      const val = parseInt(process.env.MOVIE_PROCESSING_CHECK_INTERVAL_MINUTES, 10)
      if (!isNaN(val)) {
        safeEnvVars.movie_processing_check_interval_minutes = val
      }
    }
    if (process.env.MOVIE_QUEUE_MAXSIZE) {
      const val = parseInt(process.env.MOVIE_QUEUE_MAXSIZE, 10)
      if (!isNaN(val)) {
        safeEnvVars.movie_queue_maxsize = val
      }
    }
    if (process.env.TV_QUEUE_MAXSIZE) {
      const val = parseInt(process.env.TV_QUEUE_MAXSIZE, 10)
      if (!isNaN(val)) {
        safeEnvVars.tv_queue_maxsize = val
      }
    }
    
    // Check for failed item configs
    if (process.env.ENABLE_FAILED_ITEM_RETRY) {
      safeEnvVars.enable_failed_item_retry = process.env.ENABLE_FAILED_ITEM_RETRY.toLowerCase() === 'true'
    }
    if (process.env.FAILED_ITEM_RETRY_INTERVAL_MINUTES) {
      const val = parseInt(process.env.FAILED_ITEM_RETRY_INTERVAL_MINUTES, 10)
      if (!isNaN(val)) {
        safeEnvVars.failed_item_retry_interval_minutes = val
      }
    }
    if (process.env.FAILED_ITEM_MAX_RETRY_ATTEMPTS) {
      const val = parseInt(process.env.FAILED_ITEM_MAX_RETRY_ATTEMPTS, 10)
      if (!isNaN(val)) {
        safeEnvVars.failed_item_max_retry_attempts = val
      }
    }
    if (process.env.FAILED_ITEM_RETRY_DELAY_HOURS) {
      const val = parseInt(process.env.FAILED_ITEM_RETRY_DELAY_HOURS, 10)
      if (!isNaN(val)) {
        safeEnvVars.failed_item_retry_delay_hours = val
      }
    }
    if (process.env.FAILED_ITEM_RETRY_BACKOFF_MULTIPLIER) {
      const val = parseFloat(process.env.FAILED_ITEM_RETRY_BACKOFF_MULTIPLIER)
      if (!isNaN(val)) {
        safeEnvVars.failed_item_retry_backoff_multiplier = val
      }
    }
    if (process.env.FAILED_ITEM_MAX_RETRY_DELAY_HOURS) {
      const val = parseInt(process.env.FAILED_ITEM_MAX_RETRY_DELAY_HOURS, 10)
      if (!isNaN(val)) {
        safeEnvVars.failed_item_max_retry_delay_hours = val
      }
    }
    
    // Check if sensitive values exist (without returning them)
    const hasSensitiveValues = {
      rd_access_token: !!process.env.RD_ACCESS_TOKEN,
      rd_refresh_token: !!process.env.RD_REFRESH_TOKEN,
      rd_client_id: !!process.env.RD_CLIENT_ID,
      rd_client_secret: !!process.env.RD_CLIENT_SECRET,
      overseerr_base: !!process.env.OVERSEERR_BASE,
      overseerr_api_key: !!process.env.OVERSEERR_API_KEY,
      trakt_api_key: !!process.env.TRAKT_API_KEY
    }
    
    return {
      success: true,
      safeValues: safeEnvVars,
      hasSensitiveValues,
      allRequiredPresent: Object.values(hasSensitiveValues).every(v => v === true)
    }
  } catch (error) {
    console.error('Error getting environment values:', error)
    return {
      success: false,
      error: 'Failed to get environment values'
    }
  }
})

