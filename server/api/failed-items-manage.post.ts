import { getDatabaseConnection } from '~/server/utils/database'

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody(event)
    const { action, media_ids } = body
    
    if (!action || !media_ids || !Array.isArray(media_ids) || media_ids.length === 0) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Invalid request: action and media_ids are required'
      })
    }
    
    const db = await getDatabaseConnection()
    
    switch (action) {
      case 'retry':
        return await retryFailedItems(db, media_ids)
      
      case 'clear_errors':
        return await clearErrorStatus(db, media_ids)
      
      case 'reset_retry_count':
        return await resetRetryCount(db, media_ids)
      
      case 'queue_for_retry':
        return await queueForRetry(db, media_ids)
      
      case 'remove_from_queue':
        return await removeFromQueue(db, media_ids)
      
      default:
        throw createError({
          statusCode: 400,
          statusMessage: 'Invalid action. Supported actions: retry, clear_errors, reset_retry_count, queue_for_retry, remove_from_queue'
        })
    }
    
  } catch (error) {
    console.error('Error managing failed items:', error)
    
    if (error.statusCode) {
      throw error
    }
    
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to manage failed items'
    })
  }
})

async function retryFailedItems(db: any, media_ids: number[]) {
  try {
    // Reset error status and retry count for selected items
    const placeholders = media_ids.map(() => '?').join(',')
    
    await db.execute(`
      UPDATE unified_media 
      SET 
        status = 'pending',
        error_message = NULL,
        error_count = 0,
        last_error_at = NULL,
        is_in_queue = TRUE,
        queue_added_at = NOW(),
        queue_attempts = queue_attempts + 1,
        updated_at = NOW()
      WHERE id IN (${placeholders})
    `, media_ids)
    
    return {
      success: true,
      message: `Successfully queued ${media_ids.length} items for retry`,
      action: 'retry',
      processed_count: media_ids.length
    }
    
  } catch (error) {
    console.error('Error retrying failed items:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to retry failed items'
    })
  }
}

async function clearErrorStatus(db: any, media_ids: number[]) {
  try {
    const placeholders = media_ids.map(() => '?').join(',')
    
    await db.execute(`
      UPDATE unified_media 
      SET 
        error_message = NULL,
        error_count = 0,
        last_error_at = NULL,
        updated_at = NOW()
      WHERE id IN (${placeholders})
    `, media_ids)
    
    return {
      success: true,
      message: `Successfully cleared error status for ${media_ids.length} items`,
      action: 'clear_errors',
      processed_count: media_ids.length
    }
    
  } catch (error) {
    console.error('Error clearing error status:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to clear error status'
    })
  }
}

async function resetRetryCount(db: any, media_ids: number[]) {
  try {
    const placeholders = media_ids.map(() => '?').join(',')
    
    await db.execute(`
      UPDATE unified_media 
      SET 
        error_count = 0,
        last_error_at = NULL,
        updated_at = NOW()
      WHERE id IN (${placeholders})
    `, media_ids)
    
    return {
      success: true,
      message: `Successfully reset retry count for ${media_ids.length} items`,
      action: 'reset_retry_count',
      processed_count: media_ids.length
    }
    
  } catch (error) {
    console.error('Error resetting retry count:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to reset retry count'
    })
  }
}

async function queueForRetry(db: any, media_ids: number[]) {
  try {
    const placeholders = media_ids.map(() => '?').join(',')
    
    await db.execute(`
      UPDATE unified_media 
      SET 
        is_in_queue = TRUE,
        queue_added_at = NOW(),
        queue_attempts = queue_attempts + 1,
        updated_at = NOW()
      WHERE id IN (${placeholders})
    `, media_ids)
    
    return {
      success: true,
      message: `Successfully queued ${media_ids.length} items for retry`,
      action: 'queue_for_retry',
      processed_count: media_ids.length
    }
    
  } catch (error) {
    console.error('Error queuing for retry:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to queue items for retry'
    })
  }
}

async function removeFromQueue(db: any, media_ids: number[]) {
  try {
    const placeholders = media_ids.map(() => '?').join(',')
    
    await db.execute(`
      UPDATE unified_media 
      SET 
        is_in_queue = FALSE,
        queue_added_at = NULL,
        updated_at = NOW()
      WHERE id IN (${placeholders})
    `, media_ids)
    
    return {
      success: true,
      message: `Successfully removed ${media_ids.length} items from queue`,
      action: 'remove_from_queue',
      processed_count: media_ids.length
    }
    
  } catch (error) {
    console.error('Error removing from queue:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to remove items from queue'
    })
  }
}
