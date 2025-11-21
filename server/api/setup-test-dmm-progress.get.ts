import { defineEventHandler, getQuery } from 'h3'

export default defineEventHandler(async (event) => {
  try {
    const query = getQuery(event)
    const testId = query.test_id as string
    
    if (!testId) {
      return {
        success: false,
        error: 'Missing test_id parameter'
      }
    }
    
    // During setup, call the setup API server running on port 8778
    // In Docker, we use the service name from docker-compose
    // 'seerrbridge' is the service name in both prod and dev
    const setupApiUrl = 'http://seerrbridge:8778'
    
    try {
      const response = await fetch(`${setupApiUrl}/api/setup/test-dmm/progress/${testId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      })
      
      if (response.ok) {
        const result = await response.json()
        return result
      } else {
        return {
          success: false,
          error: `Failed to get progress: ${response.status}`
        }
      }
    } catch (fetchError: any) {
      console.error('Failed to call setup API for progress:', fetchError)
      return {
        success: false,
        error: 'Cannot connect to setup API server'
      }
    }
    
  } catch (error: any) {
    console.error('Error getting DMM test progress:', error)
    return {
      success: false,
      error: error.message || 'Failed to get progress'
    }
  }
})

