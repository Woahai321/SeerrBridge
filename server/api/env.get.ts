function redactSensitiveValues(envVars: Record<string, string>): Record<string, string> {
  const sensitiveKeys = ['PASSWORD', 'SECRET', 'TOKEN', 'KEY', 'AUTH']
  const redactedEnvVars: Record<string, string> = {}
  
  for (const [key, value] of Object.entries(envVars)) {
    const isSensitive = sensitiveKeys.some(sensitiveKey => 
      key.toUpperCase().includes(sensitiveKey)
    )
    
    if (isSensitive && value.length > 0) {
      redactedEnvVars[key] = '*'.repeat(Math.min(value.length, 8))
    } else {
      redactedEnvVars[key] = value
    }
  }
  
  return redactedEnvVars
}

export default defineEventHandler(async (event) => {
  try {
    // Get all environment variables that are relevant to the application
    const relevantEnvVars = [
      'DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD', 'USE_DATABASE',
      'RD_ACCESS_TOKEN', 'RD_REFRESH_TOKEN', 'RD_CLIENT_ID', 'RD_CLIENT_SECRET',
      'OVERSEERR_BASE', 'OVERSEERR_API_KEY', 'TRAKT_API_KEY',
      'HEADLESS_MODE', 'ENABLE_AUTOMATIC_BACKGROUND_TASK', 'ENABLE_SHOW_SUBSCRIPTION_TASK',
      'TORRENT_FILTER_REGEX', 'MAX_MOVIE_SIZE', 'MAX_EPISODE_SIZE', 'REFRESH_INTERVAL_MINUTES',
      'NEXTAUTH_URL', 'NEXTAUTH_SECRET', 'NODE_ENV'
    ]
    
    const envVars: Record<string, string> = {}
    
    for (const key of relevantEnvVars) {
      if (process.env[key]) {
        envVars[key] = process.env[key]!
      }
    }
    
    // Redact sensitive values before sending them to the client
    const redactedEnvVars = redactSensitiveValues(envVars)
    
    return redactedEnvVars
  } catch (error) {
    console.error("Error reading environment variables:", error)
    throw createError({
      statusCode: 500,
      statusMessage: "Failed to read environment variables"
    })
  }
})
