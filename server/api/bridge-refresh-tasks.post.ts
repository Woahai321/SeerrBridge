import { defineEventHandler } from 'h3'

export default defineEventHandler(async (event) => {
  try {
    // This endpoint communicates with the Python backend to refresh tasks
    const pythonBackendUrl = process.env.PYTHON_BACKEND_URL || 'http://seerrbridge:8777'
    
    const response = await fetch(`${pythonBackendUrl}/api/refresh-tasks`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    })
    
    if (!response.ok) {
      throw new Error(`Python backend responded with status: ${response.status}`)
    }
    
    const result = await response.json()
    
    return {
      success: true,
      message: 'Background tasks refreshed successfully',
      data: result
    }
  } catch (error) {
    console.error('Error refreshing background tasks:', error)
    return {
      success: false,
      error: 'Failed to refresh background tasks',
      details: error.message
    }
  }
})
