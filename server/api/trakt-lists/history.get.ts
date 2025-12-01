import { defineEventHandler, getQuery, createError } from 'h3'

export default defineEventHandler(async (event) => {
  try {
    const config = useRuntimeConfig(event)
    const query = getQuery(event)
    const limit = parseInt(query.limit as string) || 100
    
    const seerrbridgeUrl = config.seerrbridgeUrl || 'http://localhost:8777'
    
    const response = await fetch(`${seerrbridgeUrl}/api/trakt-lists/history?limit=${limit}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    })

    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(`Failed to get sync history: ${response.status} ${errorText}`)
    }

    const result = await response.json()
    return result
  } catch (error: any) {
    console.error('Error getting sync history:', error)
    throw createError({
      statusCode: error.statusCode || 500,
      statusMessage: error.message || 'Failed to get sync history'
    })
  }
})

