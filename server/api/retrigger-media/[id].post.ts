export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')
  
  if (!id) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Media ID is required'
    })
  }

  const seerrbridgeUrl = process.env.SEERRBRIDGE_URL || 'http://localhost:8777'

  try {
    const response = await $fetch(`${seerrbridgeUrl}/retrigger-media/${id}`, {
      method: 'POST'
    })

    return response
  } catch (error: any) {
    throw createError({
      statusCode: error.statusCode || 500,
      statusMessage: error.statusMessage || 'Failed to retrigger media processing'
    })
  }
})
