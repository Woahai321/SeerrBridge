import { useApi } from '~/composables/useApi'

interface LogEntry {
  id: string
  timestamp: string
  level: string
  message: string
  type?: string
  metadata?: Record<string, any>
}

interface LogStatistics {
  totalLogs: number
  successCount: number
  errorCount: number
  warningCount: number
  infoCount: number
  failedEpisodes: number
  successfulGrabs: number
  criticalErrors: number
  tokenStatus: any
  recentSuccesses: LogEntry[]
  recentFailures: LogEntry[]
}

interface LogsResponse {
  statistics: LogStatistics
  recentLogs: LogEntry[]
}

export const useLogs = () => {
  const { apiCall } = useApi()

  const fetchLogs = async (): Promise<LogsResponse> => {
    return await apiCall<LogsResponse>('/logs')
  }

  const fetchLogEntries = async (page = 1, limit = 50): Promise<{ entries: LogEntry[], total: number }> => {
    return await apiCall<{ entries: LogEntry[], total: number }>(`/logs/entries?page=${page}&limit=${limit}`)
  }

  const fetchSuccessLogs = async (page = 1, limit = 50): Promise<{ entries: LogEntry[], total: number }> => {
    return await apiCall<{ entries: LogEntry[], total: number }>(`/logs/success?page=${page}&limit=${limit}`)
  }

  const fetchErrorLogs = async (page = 1, limit = 50): Promise<{ entries: LogEntry[], total: number }> => {
    return await apiCall<{ entries: LogEntry[], total: number }>(`/logs/errors?page=${page}&limit=${limit}`)
  }

  const fetchCriticalLogs = async (page = 1, limit = 50): Promise<{ entries: LogEntry[], total: number }> => {
    return await apiCall<{ entries: LogEntry[], total: number }>(`/logs/critical?page=${page}&limit=${limit}`)
  }

  const fetchFailureLogs = async (page = 1, limit = 50): Promise<{ entries: LogEntry[], total: number }> => {
    return await apiCall<{ entries: LogEntry[], total: number }>(`/logs/failures?page=${page}&limit=${limit}`)
  }

  return {
    fetchLogs,
    fetchLogEntries,
    fetchSuccessLogs,
    fetchErrorLogs,
    fetchCriticalLogs,
    fetchFailureLogs
  }
}
