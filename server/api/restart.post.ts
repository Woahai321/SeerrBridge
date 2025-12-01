import { defineEventHandler } from 'h3'

export default defineEventHandler(async (event) => {
  try {
    // Call the SeerrBridge API to restart the service
    const seerrbridgeUrl = process.env.SEERRBRIDGE_URL || 'http://localhost:8777'
    
    const response = await fetch(`${seerrbridgeUrl}/api/restart`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    })
    
    if (response.ok) {
      const data = await response.json()
      return {
        success: true,
        message: data.message || 'Service restart initiated'
      }
    } else {
      throw new Error(`Failed to restart service: ${response.statusText}`)
    }
  } catch (error) {
    console.error('Error restarting SeerrBridge service:', error)
    return {
      success: false,
      error: 'Failed to restart service'
    }
  }
})
