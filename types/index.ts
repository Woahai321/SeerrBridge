// Global type definitions for the application

export interface LogEntry {
  id: string
  timestamp: string
  level: string
  message: string
  type?: string
  metadata?: Record<string, any>
}

export interface LogStatistics {
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

export interface LogsResponse {
  statistics: LogStatistics
  recentLogs: LogEntry[]
}

export interface BridgeStatus {
  status: string
  uptime: number
  version: string
  last_check: string
  services: {
    database: boolean
    overseerr: boolean
    realdebrid: boolean
    trakt: boolean
  }
}

export interface SeasonData {
  season_number: number
  episode_count: number
  aired_episodes: number
  failed_episodes: string[]
  confirmed_episodes: string[]
  unprocessed_episodes: string[]
  season_details: any
  last_checked?: string
  updated_at: string
}

export interface GroupedTVSubscription {
  id: string
  title: string
  seasons: SeasonData[]
  status: 'active' | 'inactive'
  poster_url?: string
  poster_image_url?: string
  poster_image_format?: string
  poster_image_size?: number
  thumb_url?: string
  thumb_image_url?: string
  thumb_image_format?: string
  thumb_image_size?: number
  // Aggregated data across all seasons
  total_episodes: number
  total_aired_episodes: number
  total_confirmed_episodes: number
  total_unprocessed_episodes: number
  total_failed_episodes: number
  last_updated: string
}

// Legacy interface for backward compatibility
export interface TVSubscription {
  id: string
  title: string
  season_number: number
  episode_number: number
  episode_count: number
  aired_episodes: number
  failed_episodes: string[]
  confirmed_episodes: string[]
  unprocessed_episodes: string[]
  season_details: any
  status: 'active' | 'inactive'
  poster_url?: string
  poster_image_url?: string
  poster_image_format?: string
  poster_image_size?: number
  thumb_url?: string
  thumb_image_url?: string
  thumb_image_format?: string
  thumb_image_size?: number
  last_checked?: string
  updated_at: string
}

export interface Notification {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message: string
  timestamp: string
  read: boolean
}

export interface Settings {
  refreshInterval: number
  autoRefresh: boolean
  theme: 'dark' | 'light' | 'system'
  notifications: {
    enabled: boolean
    types: string[]
    sound: boolean
  }
  bridge: {
    url: string
    timeout: number
  }
  logs: {
    level: string
    maxEntries: number
    retentionDays: number
  }
}
