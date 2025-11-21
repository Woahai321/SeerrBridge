export default defineEventHandler(async (event) => {
  try {
    const query = getQuery(event)
    const url = query.url as string
    
    // Validate URL parameter
    if (!url) {
      throw createError({
        statusCode: 400,
        statusMessage: "URL parameter is required"
      })
    }
    
    // Attempt to fetch the URL
    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 5000) // 5 second timeout
      
      const response = await fetch(url, { 
        method: "GET",
        signal: controller.signal,
        headers: {
          // Add a user agent to avoid being blocked by some servers
          "User-Agent": "SeerrBridge-Validator/1.0"
        }
      })
      
      clearTimeout(timeoutId)
      
      // Return the status and response information
      return {
        status: response.status,
        message: response.ok ? "URL is accessible" : `Server responded with ${response.status} ${response.statusText}`,
        ok: response.ok
      }
    } catch (error) {
      // Handle network errors, timeouts, etc.
      let errorMessage = "Connection failed"
      
      if (error instanceof Error) {
        if (error.name === "AbortError") {
          errorMessage = "Connection timed out after 5 seconds"
        } else {
          errorMessage = error.message
        }
      }
      
      return {
        status: 0,
        message: errorMessage,
        ok: false,
        error: error instanceof Error ? error.name : "Unknown error"
      }
    }
  } catch (error) {
    // Handle any unexpected errors in the API endpoint itself
    console.error("Error in validate-url API:", error)
    throw createError({
      statusCode: 500,
      statusMessage: "Internal server error"
    })
  }
})
