import { readFile } from 'fs/promises'
import { join } from 'path'
import { existsSync } from 'fs'

export default defineEventHandler(async (event) => {
  try {
    const query = getQuery(event)
    const imagePath = query.path as string
    
    if (!imagePath) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Image path is required (use ?path=...)'
      })
    }
    
    // Decode the path if it's URL encoded
    let decodedPath = decodeURIComponent(imagePath)
    
    // Sanitize the path to prevent directory traversal
    const sanitizedPath = decodedPath
      .replace(/\.\./g, '') // Remove parent directory references
      .replace(/^\/+/, '') // Remove leading slashes
      .replace(/\\/g, '/') // Normalize backslashes to forward slashes
    
    // Build full path
    const dataDir = join(process.cwd(), 'data')
    const resolvedFullPath = join(dataDir, sanitizedPath)
    
    // Ensure the path is within the data directory (prevent directory traversal)
    const resolvedDataDir = join(process.cwd(), 'data')
    
    // Normalize both paths for comparison (handle Windows backslashes)
    const normalizedDataDir = resolvedDataDir.replace(/\\/g, '/').toLowerCase()
    const normalizedFullPath = resolvedFullPath.replace(/\\/g, '/').toLowerCase()
    
    if (!normalizedFullPath.startsWith(normalizedDataDir + '/') && normalizedFullPath !== normalizedDataDir) {
      throw createError({
        statusCode: 403,
        statusMessage: 'Invalid image path - directory traversal detected'
      })
    }
    
    // Check if file exists
    if (!existsSync(resolvedFullPath)) {
      console.error(`Image not found at path: ${resolvedFullPath} (requested: ${imagePath})`)
      throw createError({
        statusCode: 404,
        statusMessage: 'Image not found'
      })
    }
    
    // Read the image file
    const imageBuffer = await readFile(resolvedFullPath)
    
    // Determine content type based on file extension
    const ext = resolvedFullPath.split('.').pop()?.toLowerCase()
    let contentType = 'image/jpeg'
    
    if (ext === 'webp') {
      contentType = 'image/webp'
    } else if (ext === 'png') {
      contentType = 'image/png'
    } else if (ext === 'gif') {
      contentType = 'image/gif'
    }
    
    // Set appropriate headers
    setHeader(event, 'Content-Type', contentType)
    setHeader(event, 'Cache-Control', 'public, max-age=31536000, immutable')
    
    // Return the image buffer
    return imageBuffer
  } catch (error: any) {
    if (error.statusCode) {
      throw error
    }
    
    console.error('Error serving collection image:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to serve image',
      data: { error: error.message }
    })
  }
})

