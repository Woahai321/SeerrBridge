import { getLogStatistics, getRecentLogs } from '~/server/utils/database'

export default defineEventHandler(async (event) => {
  try {
    console.log('Fetching logs from database...')
    
    // Get statistics and recent logs from database
    const [statistics, recentLogs] = await Promise.all([
      getLogStatistics(),
      getRecentLogs(20)
    ])
    
    console.log('Successfully fetched logs:', {
      statisticsCount: statistics.totalLogs,
      recentLogsCount: recentLogs.length
    })
    
    return {
      statistics,
      recentLogs
    }
  } catch (error) {
    console.error('Error in logs API:', error)
    
    // Return empty data instead of throwing error to prevent frontend crashes
    return {
      statistics: {
        totalLogs: 0,
        successCount: 0,
        errorCount: 0,
        warningCount: 0,
        infoCount: 0,
        failedEpisodes: 0,
        successfulGrabs: 0,
        criticalErrors: 0,
        tokenStatus: null,
        recentSuccesses: [],
        recentFailures: []
      },
      recentLogs: []
    }
  }
})
