import { getDatabaseConnection } from '~/server/utils/database'

export default defineEventHandler(async (event) => {
  try {
    const id = getRouterParam(event, 'id')
    const query = getQuery(event)
    const type = (query.type as string) || 'poster'
    
    // Media image request processing
    
    if (!id) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Media ID is required'
      })
    }

    if (!['poster', 'thumb', 'fanart'].includes(type)) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Invalid image type. Must be poster, thumb, or fanart'
      })
    }

    const connection = await getDatabaseConnection()
    
    // Query for the specific image type
    const imageColumn = `${type}_image`
    const formatColumn = `${type}_image_format`
    const sizeColumn = `${type}_image_size`
    
    const [rows] = await connection.execute(
      `SELECT ${imageColumn}, ${formatColumn}, ${sizeColumn} FROM unified_media WHERE id = ? AND ${imageColumn} IS NOT NULL`,
      [id]
    )
    
    // Process query results
    
    const imageData = (rows as any[])[0]
    
    if (!imageData || !imageData[imageColumn]) {
      throw createError({
        statusCode: 404,
        statusMessage: 'Image not found'
      })
    }

    // Set appropriate headers
    const format = imageData[formatColumn] || 'jpeg'
    const size = imageData[sizeColumn] || 0
    
    setHeader(event, 'Content-Type', `image/${format}`)
    setHeader(event, 'Content-Length', size.toString())
    // Disable caching - serve fresh images every time
    setHeader(event, 'Cache-Control', 'no-cache, no-store, must-revalidate')
    setHeader(event, 'Pragma', 'no-cache')
    setHeader(event, 'Expires', '0')
    
    // Return the binary image data
    return imageData[imageColumn]
    
  } catch (error: any) {
    if (error.statusCode) {
      throw error
    }
    
    throw createError({
      statusCode: 500,
      statusMessage: 'Internal server error'
    })
  }
})
