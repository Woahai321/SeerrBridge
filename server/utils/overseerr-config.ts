import { getConfigFromEnv } from '~/server/utils/env-config'

/**
 * Get Overseerr configuration - reads directly from .env file
 */
export async function getOverseerrConfig(): Promise<{ baseUrl: string | null, apiKey: string | null }> {
  // Read from .env file
  const overseerrBaseUrl = getConfigFromEnv('overseerr_base') || null
  const overseerrApiKey = getConfigFromEnv('overseerr_api_key') || null
  
  return {
    baseUrl: overseerrBaseUrl,
    apiKey: overseerrApiKey
  }
}

