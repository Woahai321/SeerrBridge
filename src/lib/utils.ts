import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { format, parseISO } from "date-fns";

export interface LogEntry {
  level: string;
  message: string;
  timestamp: string;
  source?: string;
}

export interface MediaItem {
  id?: string;
  title: string;
  type: "movie" | "tv" | "unknown";
  status: "success" | "error" | "warning" | "critical";
  timestamp: string;
  details?: Record<string, string>;
  poster?: string;
  season?: number;
  episode?: string;
  message?: string;
  detailedError?: string;
  logTypeId?: string;
  matchedLogTypeId?: string;
  matchedLogTypeName?: string;
}

export interface TokenStatusData {
  expiresOn: string;
  lastRefreshedAt: string;
  status: 'valid' | 'expiring' | 'refreshing' | 'unknown';
  lastCheckedAt: string;
}

export interface LogStatistics {
  totalLogs: number;
  successCount: number;
  errorCount: number;
  warningCount: number;
  infoCount: number;
  failedEpisodes: number;
  successfulGrabs: number;
  criticalErrors: number;
  tokenStatus: TokenStatusData | "valid" | "invalid" | "expired" | null;
}

/**
 * Combines multiple class names into a single string with Tailwind's utility
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format timestamp from ISO string to readable format
 */
export function formatDate(date: string | Date): string {
  if (!date) return "Unknown";
  
  try {
    if (typeof date === 'string') {
      // Try to use parseISO if it appears to be an ISO format
      if (date.includes('T') || date.includes('Z')) {
        return format(parseISO(date), "MMM d, h:mm a");
      }
      // Otherwise, treat as regular date string
      return format(new Date(date), "MMM d, h:mm a");
    }
    return format(date, "MMM d, h:mm a");
  } catch (error) {
    console.error("Error formatting date:", error);
    return typeof date === 'string' ? date : date.toString();
  }
}

export interface ParsedLogData {
  recentLogs: LogEntry[];
  statistics: LogStatistics;
  recentSuccesses: MediaItem[];
  recentFailures: MediaItem[];
}

interface SeasonDetails {
  number: number;
  ids: {
    trakt: number;
    tvdb: number | null;
    tmdb: number;
    tvrage: number | null;
  };
  rating: number;
  votes: number;
  episode_count: number;
  aired_episodes: number;
  title: string;
  overview: string | null;
  first_aired: string | null;
  updated_at: string;
  network: string | null;
  original_title: string | null;
}

export interface ShowSubscription {
  show_title: string;
  title?: string; // Keep for backward compatibility
  season: number;
  season_number?: number;
  network?: string;
  episodeCount?: number;
  airedEpisodes: number;
  failedEpisodes: string[];
  imdb_id?: string;
  trakt_show_id?: number;
  season_details?: SeasonDetails;
  timestamp?: string;
}

// Client-safe helper functions
export function parseLogLines(logLines: string[]): any[] {
  // Define all possible log levels for proper detection
  const knownLogLevels = [
    "INFO", 
    "DEBUG", 
    "SUCCESS", 
    "WARNING", 
    "ERROR", 
    "CRITICAL"
  ];
  
  // Create a mapping of normalized levels
  const levelMapping: Record<string, string> = {
    'info': 'info',
    'information': 'info',
    'debug': 'debug',
    'success': 'success',
    'warning': 'warning',
    'warn': 'warning',
    'error': 'error',
    'err': 'error',
    'critical': 'critical',
    'crit': 'critical',
    'fatal': 'critical'
  };
  
  return logLines.map((line, index) => {
    try {
      // Try to parse standard log format: timestamp | level | source - message
      const timestampMatch = line.match(/^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)/);
      const timestamp = timestampMatch ? timestampMatch[1] : new Date().toISOString();
      
      // Validate that the timestamp is properly handled regardless of year
      let validatedTimestamp = timestamp;
      if (timestamp.includes("-")) {
        try {
          const dateParts = timestamp.split(" ")[0].split("-");
          // Make sure year is correctly preserved (2025 or whatever is in the log)
          const year = parseInt(dateParts[0], 10);
          // If valid year, just use the original timestamp
          if (year >= 2000 && year <= 2100) {
            validatedTimestamp = timestamp;
          }
        } catch (e) {
          // If date parsing fails, keep original
          console.error("Date parsing error:", e);
        }
      }
      
      // Generate a unique ID for each log entry
      const id = `log-${Date.now()}-${index}`;
      
      // Extract log level - try multiple approaches for robustness
      let level = "info"; // Default level
      let detectedLevel = "";
      
      // Approach 1: Only extract level from proper format like " | LEVEL | "
      const levelMatch = line.match(/\|\s*([A-Za-z]+)\s*\|/);
      if (levelMatch && levelMatch[1]) {
        const extractedLevel = levelMatch[1].trim().toLowerCase();
        if (extractedLevel) {
          detectedLevel = extractedLevel;
          
          // Map to normalized level
          if (levelMapping[extractedLevel]) {
            level = levelMapping[extractedLevel];
          } else {
            // If not in the mapping but it's a known level, use as is
            const knownLevelFound = knownLogLevels.find(
              l => l.toLowerCase() === extractedLevel
            );
            if (knownLevelFound) {
              level = extractedLevel;
            }
          }
        }
      }
      
      // Fallback only if no level was found through primary approach
      if (!detectedLevel) {
        // Check for explicit level formats in the raw text
        for (const knownLevel of knownLogLevels) {
          if (line.includes(`| ${knownLevel} |`)) {
            level = knownLevel.toLowerCase();
            break;
          }
        }
      }
      
      // Extract source and message
      let source = "";
      let message = line;
      
      const parts = line.split(" - ");
      if (parts.length > 1) {
        message = parts.slice(1).join(" - ");
        
        const sourceParts = parts[0].split(" | ");
        if (sourceParts.length > 2) {
          source = sourceParts[2];
        }
      }
      
      return {
        id,
        timestamp: validatedTimestamp,
        level,
        source,
        message,
        rawLog: line // Include the raw log for debugging and display
      };
    } catch (error) {
      // If parsing fails, return a basic object
      console.error("Error parsing log line:", error, "Line:", line);
      return {
        id: `log-${Date.now()}-${index}-error`,
        timestamp: new Date().toISOString(),
        level: "info",
        source: "unknown",
        message: line,
        rawLog: line
      };
    }
  });
}

export function parseEnvValue(value: string): any {
  if (value === "true") return true;
  if (value === "false") return false;
  if (value === "null") return null;
  if (value === "undefined") return undefined;
  if (!isNaN(Number(value)) && value.trim() !== '') return Number(value);
  
  // Check if it's a JSON string
  try {
    return JSON.parse(value);
  } catch (e) {
    // Not a JSON string, return as is
    return value;
  }
} 