import { getDatabaseConnection } from '~/server/utils/database'
import { configEncryption } from '~/server/utils/encryption'

/**
 * Get Overseerr configuration - primary method uses database with decryption, fallback to backend API
 */
export async function getOverseerrConfig(): Promise<{ baseUrl: string | null, apiKey: string | null }> {
  const seerrbridgeUrl = process.env.SEERRBRIDGE_URL || 'http://localhost:8777'
  
  let overseerrBaseUrl: string | null = null
  let overseerrApiKey: string | null = null
  
  // Primary method: Try to get configs from database and decrypt them
  try {
    const db = await getDatabaseConnection()
    const [dbConfigs] = await db.execute(`
      SELECT config_key, config_value
      FROM system_config 
      WHERE config_key IN ('overseerr_base', 'overseerr_api_key')
        AND is_active = true
    `) as any[]
    
    for (const config of dbConfigs) {
      if (config.config_key === 'overseerr_base' && config.config_value) {
        const rawValue = config.config_value
        
        // Try to decrypt the value - if it's encrypted, decrypt it
        const decrypted = configEncryption.decryptValue(rawValue)
        
        if (decrypted !== null && decrypted.length > 0) {
          overseerrBaseUrl = decrypted
        } else {
          // Not encrypted or decryption failed - use as-is (plaintext)
          overseerrBaseUrl = rawValue
        }
      } else if (config.config_key === 'overseerr_api_key' && config.config_value) {
        const rawValue = config.config_value
        
        // Try to decrypt the value - if it's encrypted, decrypt it
        const decrypted = configEncryption.decryptValue(rawValue)
        
        if (decrypted !== null && decrypted.length > 0) {
          overseerrApiKey = decrypted
        } else {
          // Not encrypted or decryption failed - use as-is (plaintext)
          overseerrApiKey = rawValue
        }
      }
    }
    
    // If we got both values from database, return early
    if (overseerrBaseUrl && overseerrApiKey) {
      return { baseUrl: overseerrBaseUrl, apiKey: overseerrApiKey }
    }
  } catch (dbError) {
    // Database access failed - will fall back to backend API
    console.debug('Failed to get config from database, using backend API fallback')
  }
  
  // Fallback: Try to get decrypted configs from SeerrBridge backend API
  if (!overseerrBaseUrl || !overseerrApiKey) {
    try {
      // Add timeout to prevent hanging requests
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 5000) // 5 second timeout
      
      const configResponse = await fetch(`${seerrbridgeUrl}/api/config/internal`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        },
        signal: controller.signal
      })
      
      clearTimeout(timeoutId)
      
      if (configResponse.ok) {
        const configData = await configResponse.json()
        if (configData.success && configData.data) {
          // Get raw decrypted values
          const apiBaseUrl = configData.data['overseerr_base'] || null
          const apiApiKey = configData.data['overseerr_api_key'] || null
          
          // Use API values if database didn't provide them
          if (!overseerrBaseUrl && apiBaseUrl) {
            overseerrBaseUrl = apiBaseUrl
          }
          if (!overseerrApiKey && apiApiKey) {
            overseerrApiKey = apiApiKey
          }
        }
      }
    } catch (error: any) {
      // Backend API also failed - silently continue if we already have values from database
      // Only log warning if we have no config at all
      if (!overseerrBaseUrl || !overseerrApiKey) {
        // Only log if it's not a timeout (timeouts are expected when backend is down)
        if (error.name !== 'AbortError' && !error.message?.includes('timeout')) {
          console.warn('Failed to get Overseerr config from both database and backend API', {
            hasBaseUrl: !!overseerrBaseUrl,
            hasApiKey: !!overseerrApiKey
          })
        }
      }
    }
  }
  
  return {
    baseUrl: overseerrBaseUrl,
    apiKey: overseerrApiKey
  }
}

