export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const seerrbridgeUrl = config.seerrbridgeUrl

  console.log(`[bridge-reload] Received reload request. Will forward to ${seerrbridgeUrl}/reload-env`)
  
  try {
    console.log(`[bridge-reload] Attempting to connect to SeerrBridge at ${seerrbridgeUrl}/reload-env`)
    
    const response = await fetch(`${seerrbridgeUrl}/reload-env`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        Pragma: "no-cache",
        Expires: "0",
      },
    })

    console.log(`[bridge-reload] Response status: ${response.status}`)
    
    if (!response.ok) {
      const errorText = await response.text().catch(() => "Could not read response body")
      console.error(`[bridge-reload] Failed response: ${errorText}`)
      throw new Error(`Failed to reload environment: ${response.status} - ${errorText}`)
    }

    const data = await response.json()
    console.log(`[bridge-reload] Success response:`, data)
    
    return {
      status: "success",
      message: "Environment variables reloaded successfully",
      seerrbridge_response: data
    }
  } catch (error) {
    console.error(`[bridge-reload] Error details:`, error)
    throw createError({
      statusCode: 500,
      statusMessage: `Failed to reload SeerrBridge: ${error instanceof Error ? error.message : 'Unknown error'}`
    })
  }
})
