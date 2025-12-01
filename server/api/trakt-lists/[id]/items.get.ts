import { defineEventHandler, getRouterParam, createError } from 'h3'

export default defineEventHandler(async (event) => {
  try {
    const listId = getRouterParam(event, 'id')
    
    if (!listId) {
      throw createError({
        statusCode: 400,
        statusMessage: 'List ID is required'
      })
    }
    
    console.log(`[API] Getting items for list ID: ${listId}`)
    
    const config = useRuntimeConfig(event)
    const seerrbridgeUrl = config.seerrbridgeUrl || 'http://localhost:8777'
    
    try {
      const backendUrl = `${seerrbridgeUrl}/api/trakt-lists/${listId}/items`
      console.log(`[API] Calling backend: ${backendUrl}`)
      
      const response = await fetch(backendUrl, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      })
      
      console.log(`[API] Backend response status: ${response.status}`)

      if (!response.ok) {
        // If 404, return empty items instead of error (list hasn't been synced)
        if (response.status === 404) {
          return {
            success: true,
            items: [],
            count: 0,
            source: 'database'
          }
        }
        
        const errorText = await response.text()
        throw new Error(`Failed to get list items: ${response.status} ${errorText}`)
      }

      const result = await response.json()
      return result
    } catch (fetchError: any) {
      // If connection error, return empty items
      if (fetchError.message?.includes('fetch failed') || fetchError.message?.includes('ECONNREFUSED')) {
        console.error('Error connecting to SeerrBridge backend:', fetchError)
        return {
          success: true,
          items: [],
          count: 0,
          source: 'database',
          error: 'Backend connection failed'
        }
      }
      throw fetchError
    }
  } catch (error: any) {
    console.error('Error getting list items:', error)
    throw createError({
      statusCode: error.statusCode || 500,
      statusMessage: error.message || 'Failed to get list items'
    })
  }
})

