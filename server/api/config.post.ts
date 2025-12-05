import { defineEventHandler, readBody } from 'h3'
import { setConfigInEnv, getConfigFromEnv, SENSITIVE_CONFIG_KEYS, maskSensitiveValue } from '~/server/utils/env-config'

/**
 * Check if a value looks like a masked value (contains asterisks in the middle)
 */
function isMaskedValue(value: string): boolean {
  if (!value || typeof value !== 'string') return false
  // Check if value contains asterisks in the middle (not just at start/end)
  // Masked values typically look like: "abc***xyz" or "ab***xy" or "***"
  const asteriskPattern = /\*{3,}/ // 3 or more consecutive asterisks
  return asteriskPattern.test(value)
}

/**
 * Extract token value from JSON format or return as-is
 * Handles both {"value": "...", "expiry": ...} and plain string formats
 */
function extractTokenValue(value: string): string {
  if (!value || typeof value !== 'string') return value
  
  // Try to parse as JSON
  try {
    const parsed = JSON.parse(value)
    if (parsed && typeof parsed === 'object' && parsed.value) {
      return parsed.value
    }
  } catch {
    // Not JSON, return as-is
  }
  
  return value
}

/**
 * Check if a value is in JSON token format
 */
function isJsonTokenFormat(value: string): boolean {
  if (!value || typeof value !== 'string') return false
  try {
    const parsed = JSON.parse(value)
    return parsed && typeof parsed === 'object' && parsed.value && parsed.expiry !== undefined
  } catch {
    return false
  }
}

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
    
    // Update each configuration in .env file
    for (const config of configs) {
      const { config_key, config_value, config_type } = config
      
      if (!config_key) continue
      
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
      
      // If this is a sensitive config and the value looks masked, keep the existing value
      if (SENSITIVE_CONFIG_KEYS.includes(config_key) && typeof envValue === 'string') {
        // Check if value is masked (for plain strings)
        if (isMaskedValue(envValue)) {
          // Value is masked - get the original from .env and keep it
          const existingValue = getConfigFromEnv(config_key)
          if (existingValue) {
            // Extract token value if it's in JSON format
            const existingTokenValue = extractTokenValue(existingValue)
            // Verify the masked value matches what we would mask the existing value to
            const expectedMasked = maskSensitiveValue(existingTokenValue)
            if (envValue === expectedMasked) {
              // This is just the masked version of the existing value - don't update
              console.log(`Skipping update for ${config_key} - value appears to be masked, keeping existing value`)
              continue
            }
          }
          // If masked value doesn't match existing, it might be a new value that happens to contain asterisks
          // But to be safe, if it's clearly masked (has many asterisks), skip it
          if (envValue.match(/\*{5,}/)) {
            console.log(`Skipping update for ${config_key} - value appears to be masked (contains many asterisks)`)
            continue
          }
        }
        
        // Check if value is a JSON token format that's been masked
        // JSON format: {"value": "abc***xyz", "expiry": 123}
        if (isJsonTokenFormat(envValue)) {
          try {
            const parsed = JSON.parse(envValue)
            if (parsed.value && isMaskedValue(parsed.value)) {
              // The token value inside JSON is masked - keep existing
              const existingValue = getConfigFromEnv(config_key)
              if (existingValue && isJsonTokenFormat(existingValue)) {
                console.log(`Skipping update for ${config_key} - JSON token value appears to be masked, keeping existing value`)
                continue
              }
            }
          } catch {
            // Not valid JSON, continue with normal processing
          }
        }
      }
      
      // For RD_ACCESS_TOKEN, save exactly as provided (no automatic conversion)
      // User can provide either JSON format {"value": "...", "expiry": ...} or plain token string
      if (config_key === 'rd_access_token' && typeof envValue === 'string' && !isMaskedValue(envValue)) {
        // If it's already in JSON format, keep it as-is
        if (isJsonTokenFormat(envValue)) {
          // Already in JSON format, use exactly as provided
          // No changes needed
        } else {
          // Plain string - save exactly as provided, no conversion
          // User provided a plain token, so save it as a plain token
          // No changes needed - save as-is
        }
      }
      
      // Write to .env file (exactly as provided, no conversion)
      setConfigInEnv(config_key, envValue)
    }
    
    // Check if setup was completed (onboarding_completed or setup_required changed)
    const setupCompleted = configs.some(config => 
      config.config_key === 'onboarding_completed' || config.config_key === 'setup_required'
    )
    
    // Check if any task-related configurations were updated
    const taskConfigKeys = [
      'enable_automatic_background_task',
      'enable_show_subscription_task',
      'refresh_interval_minutes',
      'headless_mode',
      'torrent_filter_regex',
      'max_movie_size',
      'max_episode_size'
    ]
    
    const hasTaskConfigChanges = configs.some(config => 
      taskConfigKeys.includes(config.config_key)
    )
    
    // Check if any API credentials were updated (these require reload)
    const credentialKeys = [
      'rd_access_token',
      'rd_refresh_token',
      'rd_client_id',
      'rd_client_secret',
      'overseerr_base',
      'overseerr_api_key',
      'trakt_api_key'
    ]
    
    const hasCredentialChanges = configs.some(config => 
      credentialKeys.includes(config.config_key)
    )
    
    // Always trigger reload if setup completed, credentials changed, or task configs changed
    if (setupCompleted || hasCredentialChanges || hasTaskConfigChanges) {
      // Trigger a refresh of backend (with retries for setup completion)
      const seerrbridgeUrl = process.env.SEERRBRIDGE_URL || 'http://localhost:8777'
      const maxRetries = setupCompleted ? 10 : 3 // Retry more times if setup just completed (backend might still be starting)
      const retryDelay = setupCompleted ? 2000 : 1000 // Wait longer between retries if setup completed
      const timeout = setupCompleted ? 10000 : 5000 // Longer timeout if setup completed
      
      let reloadSuccess = false
      for (let attempt = 0; attempt < maxRetries; attempt++) {
        try {
          if (attempt > 0) {
            // Wait before retry (exponential backoff for setup completion)
            const delay = setupCompleted ? retryDelay * Math.min(attempt, 3) : retryDelay
            await new Promise(resolve => setTimeout(resolve, delay))
          }
          
          // First check if backend is ready (health check)
          if (setupCompleted && attempt > 0) {
            try {
              const healthCheck = await fetch(`${seerrbridgeUrl}/status`, {
                method: 'GET',
                signal: AbortSignal.timeout(3000)
              })
              if (!healthCheck.ok) {
                console.log(`Backend not ready yet (attempt ${attempt + 1}/${maxRetries}), waiting...`)
                continue
              }
            } catch (e) {
              console.log(`Backend health check failed (attempt ${attempt + 1}/${maxRetries}), waiting...`)
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
            console.log(`Backend reload triggered successfully${setupCompleted ? ' (setup completed)' : ''}`)
            reloadSuccess = true
            break
          } else {
            console.warn(`Failed to trigger backend reload (attempt ${attempt + 1}/${maxRetries}): ${refreshResponse.statusText}`)
          }
        } catch (error) {
          console.warn(`Backend reload attempt ${attempt + 1}/${maxRetries} failed:`, error.message)
          if (attempt === maxRetries - 1) {
            // Last attempt failed
            if (setupCompleted) {
              console.warn('Setup completed but backend reload failed. Backend will pick up changes on next restart.')
            } else {
              console.debug('Backend not available for immediate refresh, changes will be picked up on next reload')
            }
          }
        }
      }
      
      if (!reloadSuccess && setupCompleted) {
        console.warn('⚠️ Setup completed but backend reload failed. You may need to restart the backend service.')
      }
    }
    
    return {
      success: true,
      message: 'Configuration updated successfully in .env file',
      taskRefreshTriggered: hasTaskConfigChanges
    }
  } catch (error) {
    console.error('Error updating configuration:', error)
    return {
      success: false,
      error: 'Failed to update configuration'
    }
  }
})
