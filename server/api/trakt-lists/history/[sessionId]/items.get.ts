import { defineEventHandler, getRouterParam, createError } from 'h3'

export default defineEventHandler(async (event) => {
  try {
    const sessionId = getRouterParam(event, 'sessionId')
    
    if (!sessionId) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Session ID is required'
      })
    }
    
    const config = useRuntimeConfig(event)
    const seerrbridgeUrl = config.seerrbridgeUrl || 'http://localhost:8777'
    
    const response = await fetch(`${seerrbridgeUrl}/api/trakt-lists/history/${sessionId}/items`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    })

    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(`Failed to get sync items: ${response.status} ${errorText}`)
    }

    const result = await response.json()
    return result
  } catch (error: any) {
    console.error('Error getting sync items:', error)
    throw createError({
      statusCode: error.statusCode || 500,
      statusMessage: error.message || 'Failed to get sync items'
    })
  }
})

