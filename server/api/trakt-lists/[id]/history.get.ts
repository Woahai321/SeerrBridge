import { defineEventHandler, getRouterParam, getQuery, createError } from 'h3'

export default defineEventHandler(async (event) => {
  try {
    const listId = getRouterParam(event, 'id')
    const query = getQuery(event)
    const limit = parseInt(query.limit as string) || 50
    
    if (!listId) {
      throw createError({
        statusCode: 400,
        statusMessage: 'List ID is required'
      })
    }
    
    const config = useRuntimeConfig(event)
    const seerrbridgeUrl = config.seerrbridgeUrl || 'http://localhost:8777'
    
    const response = await fetch(`${seerrbridgeUrl}/api/trakt-lists/${listId}/history?limit=${limit}`, {
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

