// This endpoint now redirects to the unified media endpoint
export default defineEventHandler(async (event) => {
  // Redirect to the unified media endpoint
  const query = getQuery(event)
  const queryString = new URLSearchParams(query as any).toString()
  
  // Forward the request to the unified media endpoint
  const response = await $fetch(`/api/unified-media?${queryString}`)
  return response
})