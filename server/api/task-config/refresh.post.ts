import { defineEventHandler } from 'h3'

export default defineEventHandler(async (event) => {
  try {
    console.log('Task configuration refresh requested')
    
    // Call the SeerrBridge API to reload environment variables
    const seerrbridgeUrl = process.env.SEERRBRIDGE_URL || 'http://localhost:8777'
    
    const response = await fetch(`${seerrbridgeUrl}/reload-env`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    })
    
    if (response.ok) {
      const data = await response.json()
      console.log('Task configuration refresh triggered successfully:', data)
      
      return {
        success: true,
        message: 'Task configuration refresh triggered successfully',
        seerrbridge_response: data
      }
    } else {
      const errorText = await response.text().catch(() => 'Unknown error')
      console.error(`Failed to trigger task configuration refresh: ${response.status} - ${errorText}`)
      
      return {
        success: false,
        error: 'Failed to refresh task configuration',
        details: `SeerrBridge API returned ${response.status}: ${errorText}`
      }
    }
  } catch (error) {
    console.error('Error refreshing task configuration:', error)
    return {
      success: false,
      error: 'Failed to refresh task configuration',
      details: error instanceof Error ? error.message : 'Unknown error'
    }
  }
})
