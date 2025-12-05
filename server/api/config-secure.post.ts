import { defineEventHandler, readBody } from 'h3'
import { setConfigInEnv, getConfigFromEnv, SENSITIVE_CONFIG_KEYS, maskSensitiveValue } from '~/server/utils/env-config'

/**
 * Check if a value looks like a masked value (contains asterisks in the middle)
 */
function isMaskedValue(value: string): boolean {
  if (!value || typeof value !== 'string') return false
  // Masked values typically look like: "abc***xyz" or "ab***xy" or "***"
  // Check if it contains multiple asterisks (at least 3) in a row
  return /[*]{3,}/.test(value) || (value.includes('*') && value.length > 6 && value.split('*').length > 2)
}

/**
 * Secure config endpoint - writes to .env file and triggers backend reload
 * This endpoint is kept for backwards compatibility but now uses .env
 */
export default defineEventHandler(async (event) => {
  try {
    const body = await readBody(event)
    const { configs } = body
    
    if (!configs || !Array.isArray(configs)) {
      return {
        success: false,
        error: 'Invalid configuration data'
      }
    }
    
    // Track if any task configs were changed (these need backend reload)
    const taskConfigKeys = [
      'background_tasks_enabled', 'scheduler_enabled', 'enable_automatic_background_task',
      'enable_show_subscription_task', 'token_refresh_interval_minutes',
      'movie_processing_check_interval_minutes', 'movie_queue_maxsize', 'tv_queue_maxsize',
      'enable_failed_item_retry', 'failed_item_retry_interval_minutes',
      'failed_item_max_retry_attempts', 'failed_item_retry_delay_hours',
      'failed_item_retry_backoff_multiplier', 'failed_item_max_retry_delay_hours'
    ]
    
    // Track if any global configs were changed (these need backend reload)
    const globalConfigKeys = [
      'rd_access_token', 'rd_refresh_token', 'rd_client_id', 'rd_client_secret',
      'overseerr_base', 'overseerr_api_key', 'trakt_api_key',
      'headless_mode', 'torrent_filter_regex', 'max_movie_size', 'max_episode_size'
    ]
    
    let hasTaskConfigChanges = false
    let hasGlobalConfigChanges = false
    
    // Write all configs to .env file
    for (const config of configs) {
      const { config_key, config_value, config_type } = config
      
      if (!config_key) continue
      
      // CRITICAL: Check if this is a sensitive config and the value is masked
      // We should NEVER save masked values back to .env - they would overwrite real values
      const isSensitive = SENSITIVE_CONFIG_KEYS.includes(config_key)
      let shouldSkipUpdate = false
      
      if (isSensitive && typeof config_value === 'string') {
        // Check if value is masked (for plain strings)
        if (isMaskedValue(config_value)) {
          // Value is masked - get the original from .env and keep it
          const existingValue = getConfigFromEnv(config_key)
          if (existingValue) {
            // Verify the masked value matches what we would mask the existing value to
            const expectedMasked = maskSensitiveValue(existingValue)
            if (config_value === expectedMasked) {
              // This is just the masked version of the existing value - don't update
              console.log(`[config-secure] ⚠️ Skipping update for ${config_key} - value appears to be masked, keeping existing value`)
              shouldSkipUpdate = true
            }
          }
          // If masked value doesn't match existing, it might be a new value that happens to contain asterisks
          // But to be safe, if it's clearly masked (has many asterisks), skip it
          if (!shouldSkipUpdate && config_value.match(/[*]{5,}/)) {
            console.log(`[config-secure] ⚠️ Skipping update for ${config_key} - value appears to be masked (contains many asterisks)`)
            shouldSkipUpdate = true
          }
        }
        
        // Check if value is a JSON token format that's been masked
        if (!shouldSkipUpdate && config_value.trim().startsWith('{') && config_value.includes('"value"')) {
          try {
            const parsed = JSON.parse(config_value)
            if (parsed.value && isMaskedValue(parsed.value)) {
              // The token value inside JSON is masked - keep existing
              const existingValue = getConfigFromEnv(config_key)
              if (existingValue) {
                console.log(`[config-secure] ⚠️ Skipping update for ${config_key} - JSON token value appears to be masked, keeping existing value`)
                shouldSkipUpdate = true
              }
            }
          } catch {
            // Not valid JSON, continue with normal processing
          }
        }
      }
      
      // If we're skipping this update, don't count it as a change and don't write it
      if (shouldSkipUpdate) {
        continue
      }
      
      // Track what type of configs changed (only for configs we're actually updating)
      if (taskConfigKeys.includes(config_key)) {
        hasTaskConfigChanges = true
      }
      if (globalConfigKeys.includes(config_key)) {
        hasGlobalConfigChanges = true
      }
      
      // Convert value based on type
      let envValue: string | number | boolean | null | undefined = undefined
      
      // Handle empty strings - they should be written as empty string, not null
      if (config_value === null || config_value === undefined) {
        // Skip null/undefined values (don't update)
        continue
      } else if (config_value === '') {
        // Empty string should be written as empty string
        envValue = ''
      } else if (config_type === 'bool') {
        envValue = config_value === true || config_value === 'true'
      } else if (config_type === 'int') {
        envValue = parseInt(String(config_value), 10)
      } else if (config_type === 'float') {
        envValue = parseFloat(String(config_value))
      } else {
        envValue = String(config_value)
      }
      
      setConfigInEnv(config_key, envValue)
    }
    
    // Trigger backend reload if any configs that affect backend were changed
    let reloadSuccess = false
    if (hasTaskConfigChanges || hasGlobalConfigChanges) {
      const seerrbridgeUrl = process.env.SEERRBRIDGE_URL || 'http://localhost:8777'
      const maxRetries = 3
      const retryDelay = 1000
      const timeout = 5000
      
      console.log(`[config-secure] Triggering backend reload for ${hasTaskConfigChanges ? 'task' : ''}${hasTaskConfigChanges && hasGlobalConfigChanges ? ' and ' : ''}${hasGlobalConfigChanges ? 'global' : ''} config changes...`)
      
      for (let attempt = 0; attempt < maxRetries; attempt++) {
        try {
          // Wait before retry (except first attempt)
          if (attempt > 0) {
            await new Promise(resolve => setTimeout(resolve, retryDelay * attempt))
          }
          
          // First check if backend is ready (health check)
          if (attempt > 0) {
            try {
              const healthCheck = await fetch(`${seerrbridgeUrl}/status`, {
                method: 'GET',
                signal: AbortSignal.timeout(3000)
              })
              if (!healthCheck.ok) {
                console.log(`[config-secure] Backend not ready yet (attempt ${attempt + 1}/${maxRetries}), waiting...`)
                continue
              }
            } catch (e) {
              console.log(`[config-secure] Backend health check failed (attempt ${attempt + 1}/${maxRetries}), waiting...`)
              continue
            }
          }
          
          const refreshResponse = await fetch(`${seerrbridgeUrl}/reload-env`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            signal: AbortSignal.timeout(timeout)
          })
          
          if (refreshResponse.ok) {
            const responseData = await refreshResponse.json().catch(() => ({}))
            console.log(`[config-secure] ✅ Backend reload triggered successfully:`, responseData.message || 'OK')
            reloadSuccess = true
            break
          } else {
            const errorText = await refreshResponse.text().catch(() => refreshResponse.statusText)
            console.warn(`[config-secure] Failed to trigger backend reload (attempt ${attempt + 1}/${maxRetries}): ${refreshResponse.status} ${errorText}`)
          }
        } catch (error) {
          console.warn(`[config-secure] Backend reload attempt ${attempt + 1}/${maxRetries} failed:`, error instanceof Error ? error.message : String(error))
          if (attempt === maxRetries - 1) {
            console.warn('[config-secure] ⚠️ Backend reload failed after all retries. Changes saved to .env but backend will need to be restarted or will pick up changes on next operation.')
          }
        }
      }
    }
    
    return {
      success: true,
      message: 'Configuration updated successfully in .env file',
      reloadTriggered: reloadSuccess,
      hasTaskConfigChanges,
      hasGlobalConfigChanges
    }
  } catch (error) {
    console.error('Error updating secure configuration:', error)
    return {
      success: false,
      error: 'Failed to update configuration'
    }
  }
})

