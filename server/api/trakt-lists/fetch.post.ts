import { defineEventHandler, readBody, createError } from 'h3'

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody(event)
    const { listId, limit } = body

    if (!listId || !listId.trim()) {
      throw createError({
        statusCode: 400,
        statusMessage: 'listId is required'
      })
    }

    // Call SeerrBridge Python backend API
    const config = useRuntimeConfig(event)
    const seerrbridgeUrl = config.seerrbridgeUrl || 'http://localhost:8777'
    
    const response = await fetch(`${seerrbridgeUrl}/api/trakt-lists/fetch`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        listId: listId.trim(),
        limit: limit || undefined
      })
    })

    if (!response.ok) {
      const errorText = await response.text()
      let errorMessage = 'Failed to fetch Trakt list'
      
      try {
        const errorData = JSON.parse(errorText)
        errorMessage = errorData.detail || errorData.error || errorMessage
      } catch {
        errorMessage = errorText || `HTTP ${response.status}`
      }
      
      throw createError({
        statusCode: response.status,
        statusMessage: errorMessage
      })
    }

    const result = await response.json()
    
    return {
      success: true,
      items: result.items || [],
      count: result.count || 0
    }
  } catch (error: any) {
    console.error('Error fetching Trakt list:', error)
    
    // Provide user-friendly error messages
    let errorMessage = 'Failed to fetch Trakt list'
    if (error.statusCode === 400) {
      errorMessage = error.statusMessage || 'Invalid request. Please check your input.'
    } else if (error.statusCode === 500) {
      errorMessage = error.statusMessage || 'Server error. Please check your Trakt API configuration and try again.'
    } else if (error.message) {
      errorMessage = error.message
    }
    
    throw createError({
      statusCode: error.statusCode || 500,
      statusMessage: errorMessage
    })
  }
})

