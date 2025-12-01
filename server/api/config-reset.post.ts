import { defineEventHandler, readBody } from 'h3'
import { getDatabaseConnection } from '~/server/utils/database'

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody(event)
    const { keys } = body
    
    if (!keys || !Array.isArray(keys)) {
      return {
        success: false,
        error: 'Invalid keys array provided'
      }
    }
    
    const db = await getDatabaseConnection()
    
    // Clear the specified configuration keys
    const placeholders = keys.map(() => '?').join(',')
    const [result] = await db.execute(`
      UPDATE system_config 
      SET config_value = '', updated_at = NOW()
      WHERE config_key IN (${placeholders})
    `, keys)
    
    const affectedRows = (result as any).affectedRows
    
    return {
      success: true,
      message: `Cleared ${affectedRows} configuration values`,
      clearedKeys: keys,
      affectedRows
    }
  } catch (error) {
    console.error('Error resetting configuration:', error)
    return {
      success: false,
      error: 'Failed to reset configuration',
      details: error instanceof Error ? error.message : 'Unknown error'
    }
  }
})
