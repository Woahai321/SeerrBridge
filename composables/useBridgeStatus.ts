import { useApi } from '~/composables/useApi'

interface BridgeStatus {
  status: string
  uptime: string
  version: string
  last_check: string
  message?: string
  queue_status?: {
    movie_queue_size: number
    tv_queue_size: number
    is_processing: boolean
    total_queued: number
  }
  browser_status?: string
  library_stats?: {
    torrents_count: number
    total_size_tb: number
    last_updated: string
  }
  services: {
    database: boolean
    overseerr: boolean
    realdebrid: boolean
    trakt: boolean
  }
}

export const useBridgeStatus = () => {
  const { apiCall } = useApi()

  const fetchStatus = async (): Promise<BridgeStatus> => {
    return await apiCall<BridgeStatus>('/service-status')
  }

  const reloadBridge = async (): Promise<{ status: string; message: string }> => {
    return await apiCall<{ status: string; message: string }>('/bridge-reload', {
      method: 'POST'
    })
  }

  return {
    fetchStatus,
    reloadBridge
  }
}
