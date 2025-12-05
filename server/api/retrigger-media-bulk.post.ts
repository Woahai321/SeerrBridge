export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const { media_ids } = body
  
  if (!media_ids || !Array.isArray(media_ids) || media_ids.length === 0) {
    throw createError({
      statusCode: 400,
      statusMessage: 'media_ids array is required and must not be empty'
    })
  }

  const seerrbridgeUrl = process.env.SEERRBRIDGE_URL || 'http://localhost:8777'

  try {
    const response = await $fetch(`${seerrbridgeUrl}/retrigger-media-bulk`, {
      method: 'POST',
      body: {
        media_ids
      }
    })

    return response
  } catch (error: any) {
    throw createError({
      statusCode: error.statusCode || 500,
      statusMessage: error.statusMessage || 'Failed to bulk retrigger media processing'
    })
  }
})

