import { defineEventHandler } from 'h3'

export default defineEventHandler(async (event) => {
  try {
    // This endpoint communicates with the Python backend to re-queue stuck movies
    const pythonBackendUrl = process.env.PYTHON_BACKEND_URL || 'http://seerrbridge:8777'
    
    const response = await fetch(`${pythonBackendUrl}/api/re-queue-stuck-movies`, {
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
      message: 'Stuck movies re-queued successfully',
      data: result
    }
  } catch (error) {
    console.error('Error re-queuing stuck movies:', error)
    return {
      success: false,
      error: 'Failed to re-queue stuck movies',
      details: error.message
    }
  }
})
