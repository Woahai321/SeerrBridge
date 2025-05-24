import { 
  sendSuccessNotification, 
  sendErrorNotification, 
  sendWarningNotification,
  addToNotificationHistory,
  NotificationHistoryItem,
  NotificationType
} from '@/lib/notifications';

interface LogType {
  id: string;
  name: string;
  pattern: string;
  description: string;
  level: "success" | "error" | "warning" | "info" | "critical";
  selectedWords?: string[];
}

interface LogDisplay {
  id: string;
  logTypeId: string;
  location: string[] | "all";
  showNotification: boolean;
  showInCard: boolean;
  triggerStatUpdate: boolean;
}

interface LogConfiguration {
  version: string;
  logTypes: LogType[];
  logDisplays: LogDisplay[];
  defaultConfig: boolean;
}

interface SystemLog {
  id: string;
  timestamp: string;
  level: string;
  message: string;
  source?: string;
  matchedLogTypeId?: string;
  rawLog?: string;
}

// Store processed log IDs and message hashes to prevent duplicate notifications across runs
const processedLogIdsCache = new Set<string>();
const processedMessageCache = new Set<string>();
let isBaselineInitialized = false;

// Persistent cache file path
const CACHE_FILENAME = 'notification-processed-logs.json';
const MESSAGE_CACHE_FILENAME = 'notification-processed-messages.json';

/**
 * Save the processed log IDs cache to a file
 */
async function saveProcessedLogIdsCache(): Promise<void> {
  if (isServerEnvironment()) {
    try {
      const fs = require('fs');
      const path = require('path');
      const appRoot = process.cwd();
      const cacheFile = path.join(appRoot, 'logs', CACHE_FILENAME);
      const messageCacheFile = path.join(appRoot, 'logs', MESSAGE_CACHE_FILENAME);
      
      // Create logs directory if it doesn't exist
      const logsDir = path.join(appRoot, 'logs');
      if (!fs.existsSync(logsDir)) {
        fs.mkdirSync(logsDir, { recursive: true });
      }
      
      // Convert Sets to Arrays for serialization
      const serializedCache = Array.from(processedLogIdsCache);
      const serializedMessageCache = Array.from(processedMessageCache);
      
      // Limit cache sizes to most recent entries to prevent unlimited growth
      const trimmedCache = serializedCache.slice(-1000);
      const trimmedMessageCache = serializedMessageCache.slice(-1000);
      
      // Write to files
      fs.writeFileSync(cacheFile, JSON.stringify(trimmedCache), 'utf8');
      fs.writeFileSync(messageCacheFile, JSON.stringify(trimmedMessageCache), 'utf8');
      
      console.log(`[Notifications] Saved ${trimmedCache.length} processed log IDs and ${trimmedMessageCache.length} message hashes to cache files`);
    } catch (error) {
      console.error('[Notifications] Error saving processed logs cache:', error);
    }
  }
}

/**
 * Load the processed log IDs and message hashes cache from files
 */
async function loadProcessedLogIdsCache(): Promise<void> {
  if (isServerEnvironment()) {
    try {
      const fs = require('fs');
      const path = require('path');
      const appRoot = process.cwd();
      const cacheFile = path.join(appRoot, 'logs', CACHE_FILENAME);
      const messageCacheFile = path.join(appRoot, 'logs', MESSAGE_CACHE_FILENAME);
      
      // Load log IDs cache
      if (fs.existsSync(cacheFile)) {
        const data = fs.readFileSync(cacheFile, 'utf8');
        const cachedIds = JSON.parse(data);
        
        // Add all cached IDs to the Set
        cachedIds.forEach((id: string) => processedLogIdsCache.add(id));
        console.log(`[Notifications] Loaded ${cachedIds.length} processed log IDs from cache file`);
      } else {
        console.log(`[Notifications] No ID cache file found, will create new one`);
      }
      
      // Load message hashes cache
      if (fs.existsSync(messageCacheFile)) {
        const data = fs.readFileSync(messageCacheFile, 'utf8');
        const cachedHashes = JSON.parse(data);
        
        // Add all cached message hashes to the Set
        cachedHashes.forEach((hash: string) => processedMessageCache.add(hash));
        console.log(`[Notifications] Loaded ${cachedHashes.length} processed message hashes from cache file`);
      } else {
        console.log(`[Notifications] No message cache file found, will create new one`);
      }
    } catch (error) {
      console.error('[Notifications] Error loading processed logs cache:', error);
    }
  }
}

/**
 * Initialize baseline for existing logs
 * @param logs Array of existing logs to establish baseline
 */
async function initializeLogBaseline(logs: SystemLog[]): Promise<void> {
  // Load existing cache first
  await loadProcessedLogIdsCache();
  
  // Mark all existing logs as already processed
  logs.forEach(log => {
    processedLogIdsCache.add(log.id);
  });
  
  console.log(`[Notifications] Initialized baseline with ${processedLogIdsCache.size} existing logs`);
  isBaselineInitialized = true;
  
  // Save the updated cache
  await saveProcessedLogIdsCache();
}

/**
 * Get server URL for API calls - using a dynamic approach
 */
function getServerBaseUrl(): string {
  // For server components, we need a valid base URL for fetch in Node.js
  if (typeof window === 'undefined') {
    // Use a valid base URL that will work in all Node.js environments
    return process.env.NEXT_PUBLIC_BASE_URL || 'http://localhost:3000';
  }
  
  // For client components, use the origin
  return window.location.origin;
}

/**
 * Get a proper URL for API fetch calls in server components
 * For Node.js environments, we need to use the internal route handling
 * @param path API path starting with /api/
 * @returns A fully qualified URL or a path
 */
function getApiUrl(path: string, params?: URLSearchParams): string {
  // Handle paths that already include the origin
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }
  
  // In server-side (Node.js) environments, we need to handle differently
  if (typeof window === 'undefined') {
    // For server-side, we can't make fetch requests to relative URLs
    const baseUrl = getServerBaseUrl();
    // Make sure path starts with '/'
    const normalizedPath = path.startsWith('/') ? path : `/${path}`;
    const urlPath = `${baseUrl}${normalizedPath}`;
    
    const queryString = params ? `?${params.toString()}` : '';
    return `${urlPath}${queryString}`;
  }
  
  // In browser environments, relative URLs work fine
  if (path.startsWith('/')) {
    const url = new URL(path, window.location.origin);
    if (params) {
      Array.from(params.entries()).forEach(([key, value]) => {
        url.searchParams.append(key, value);
      });
    }
    return url.toString();
  }
  
  return path;
}

/**
 * Check if we're running in a server environment
 */
function isServerEnvironment(): boolean {
  return typeof window === 'undefined';
}

/**
 * Loads the log configuration from the API
 */
export async function loadLogConfiguration(): Promise<LogConfiguration> {
  try {
    // Different handling for server vs client environments
    if (isServerEnvironment()) {
      try {
        // In server environment, read configuration file directly
        const fs = require('fs');
        const path = require('path');
        
        // Get app root directory
        const appRoot = process.cwd();
        const configPath = path.join(appRoot, 'logs', 'log_config.json');
        
        console.log(`[Notifications] Loading server-side log config from: ${configPath}`);
        
        if (fs.existsSync(configPath)) {
          const data = fs.readFileSync(configPath, 'utf8');
          const config = JSON.parse(data);
          console.log(`[Notifications] Successfully loaded log config with ${config.logTypes?.length || 0} log types`);
          return config;
        } else {
          console.log(`[Notifications] Log config file not found at: ${configPath}`);
        }
      } catch (fsError) {
        console.error('[Notifications] Error reading log config file:', fsError);
      }
      
      // Return default config if file reading fails
      return {
        version: "1.0.0",
        logTypes: [],
        logDisplays: [],
        defaultConfig: true
      };
    }
    
    // For client-side, fetch from API
    const url = getApiUrl('/api/logs/config');
    const response = await fetch(url);
    
    if (response.ok) {
      return await response.json();
    } else {
      console.error('Failed to load log configuration');
      // Return a basic empty configuration
      return {
        version: "1.0.0",
        logTypes: [],
        logDisplays: [],
        defaultConfig: true
      };
    }
  } catch (error) {
    console.error('Error loading log configuration:', error);
    // Return a basic empty configuration on error
    return {
      version: "1.0.0",
      logTypes: [],
      logDisplays: [],
      defaultConfig: true
    };
  }
}

/**
 * Directly send notification to the API and ensure it's added to history
 */
async function sendDirectNotification(
  type: NotificationType,
  title: string,
  message: string,
  details?: Record<string, string>
): Promise<boolean> {
  try {
    console.log(`[Notifications] Sending direct notification: ${type} - ${title}`);
    
    // Create a timestamp for the notification
    const timestamp = new Date().toISOString();
    
    // Add timestamp to details if not already present
    const enrichedDetails = {
      ...details,
      timestamp: details?.timestamp || timestamp,
      added_to_history: "true" // Flag to ensure this is added to history
    };
    
    // In server-side environment, use direct server functions
    if (isServerEnvironment()) {
      console.log(`[Notifications] Processing server-side notification for ${type}: ${title}`);
      
      try {
        // Use import() dynamically to avoid issues with webpack/bundling
        const { readNotificationSettingsFromFile, sendDiscordWebhook, addNotificationToHistoryFile } = 
          await import("@/lib/server-notifications");
        
        // Create a notification history item
        const historyItem: NotificationHistoryItem = {
          id: Date.now().toString(36) + Math.random().toString(36).substr(2, 5),
          type,
          title,
          message,
          details: enrichedDetails,
          timestamp,
          successful: true // Assume success initially
        };
        
        // Read notification settings
        const settings = await readNotificationSettingsFromFile();
        
        // Check if this type of notification is enabled
        let isEnabled = false;
        switch (type) {
          case "success":
            isEnabled = settings.notify_on_success;
            break;
          case "error":
            isEnabled = settings.notify_on_error;
            break;
          case "warning":
            isEnabled = settings.notify_on_warning;
            break;
        }
        
        // Only attempt to send if enabled and webhook URL is set
        let success = false;
        if (isEnabled && settings.discord_webhook_url) {
          // Send to Discord
          success = await sendDiscordWebhook(
            settings.discord_webhook_url,
            type,
            title,
            message,
            enrichedDetails
          );
          
          // Update the notification history item success status
          historyItem.successful = success;
        } else {
          console.log(`[Notifications] Notification type ${type} is disabled or webhook URL not set`);
          return false;
        }
        
        // Add to notification history
        await addNotificationToHistoryFile(historyItem);
        
        console.log(`[Notifications] Server-side notification processed successfully: ${success}`);
        return success;
      } catch (serverError) {
        console.error(`[Notifications] Server-side notification error:`, serverError);
        return false;
      }
    }
    
    // For client-side, use the standard API fetch approach
    const url = getApiUrl('/api/notifications/send');
    
    // Send notification directly to the API endpoint
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        type,
        title,
        message,
        details: enrichedDetails
      }),
    });
    
    // Create a notification history item
    const historyItem: NotificationHistoryItem = {
      id: Date.now().toString(36) + Math.random().toString(36).substr(2, 5),
      type,
      title,
      message,
      details: enrichedDetails,
      timestamp,
      successful: response.ok
    };
    
    // Explicitly add to notification history
    addToNotificationHistory(historyItem);
    
    // Log success or failure
    if (response.ok) {
      console.log(`[Notifications] Successfully sent ${type} notification: ${title}`);
    } else {
      console.error(`[Notifications] Failed to send ${type} notification: ${title}`, 
        await response.text());
    }
    
    return response.ok;
  } catch (error) {
    console.error(`[Notifications] Error sending notification: ${error}`);
    return false;
  }
}

/**
 * Find matching log type for a message - similar to the function in log-configurator
 */
function findMatchingLogType(
  message: string, 
  logTypes: LogType[], 
  specificLogTypeId?: string
): LogType | undefined {
  // For specific log type ID, find exact match
  if (specificLogTypeId) {
    return logTypes.find(logType => logType.id === specificLogTypeId);
  }
  
  // Try to find matching log type by regex pattern
  for (const logType of logTypes) {
    try {
      // Create RegExp from the pattern
      const regex = new RegExp(logType.pattern, 'i');
      
      // Check if message matches the pattern
      if (regex.test(message)) {
        return logType;
      }
      
      // If no match but has selectedWords, try matching those
      if (logType.selectedWords && logType.selectedWords.length > 0) {
        const allWordsPresent = logType.selectedWords.every(word => 
          message.toLowerCase().includes(word.toLowerCase())
        );
        
        if (allWordsPresent) {
          return logType;
        }
      }
    } catch (error) {
      console.error(`[Notifications] Invalid regex pattern in log type ${logType.id}:`, error);
    }
  }
  
  return undefined;
}

/**
 * Process logs for notifications
 */
export async function processLogsForNotifications(logs: SystemLog[]): Promise<number> {
  // Load existing cache first
  await loadProcessedLogIdsCache();
  
  // Initialize baseline if needed
  if (!isBaselineInitialized) {
    await initializeLogBaseline(logs);
    return 0; // Skip first run to avoid flood of notifications for existing logs
  }
  
  // Load log configuration
  const config = await loadLogConfiguration();
  
  let notificationCount = 0;
  let cacheModified = false;
  
  // Sort logs by timestamp in ascending order to process oldest first
  const sortedLogs = [...logs].sort((a, b) => 
    new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );
  
  // Process each log
  for (const log of sortedLogs) {
    // Generate a content hash for this log
    const contentHash = generateLogContentHash(log);
    
    // Skip if we've already processed this log ID or content hash
    if (processedLogIdsCache.has(log.id) || processedMessageCache.has(contentHash)) {
      continue;
    }
    
    // Mark log as processed by ID and content hash
    processedLogIdsCache.add(log.id);
    processedMessageCache.add(contentHash);
    cacheModified = true;
    
    // Skip processing logs with common patterns that don't need notifications
    if (shouldSkipCommonLog(log.message)) {
      continue;
    }
    
    // Try to find matching log type
    const matchingLogType = findMatchingLogType(log.message, config.logTypes, log.matchedLogTypeId);
    
    if (matchingLogType) {
      // Find display rule for this log type
      const displayRule = config.logDisplays.find(
        display => display.logTypeId === matchingLogType.id && display.showNotification
      );
      
      // Send notification if display rule exists
      if (displayRule) {
        console.log(`[Notifications] Match found for log ID ${log.id} - Type: ${matchingLogType.name}`);
        
        // Prepare notification title and determine type
        const title = matchingLogType.name;
        const notificationType = matchingLogType.level as NotificationType;
        
        // Add details about the log
        const details = {
          logId: log.id,
          timestamp: log.timestamp,
          source: log.source || 'unknown',
          logType: matchingLogType.id,
          level: matchingLogType.level,
          contentHash: contentHash // Add content hash to details for debugging
        };
        
        // Add delay between notifications to avoid rate limiting
        if (notificationCount > 0) {
          // Small delay between notifications to avoid rate limiting
          await new Promise(resolve => setTimeout(resolve, 300));
        }
        
        // Send the appropriate notification type
        let success = false;
        
        if (notificationType === 'success') {
          success = await sendDirectNotification('success', title, log.message, details);
        } else if (notificationType === 'error' || matchingLogType.level === 'critical') {
          success = await sendDirectNotification('error', title, log.message, details);
        } else if (notificationType === 'warning') {
          success = await sendDirectNotification('warning', title, log.message, details);
        } else {
          // Default to info notification
          success = await sendDirectNotification('success', title, log.message, details);
        }
        
        if (success) {
          notificationCount++;
        }
      }
    }
  }
  
  // Save cache if modified
  if (cacheModified) {
    await saveProcessedLogIdsCache();
  }
  
  return notificationCount;
}

/**
 * Check if a log message should be skipped (common messages we don't want notifications for)
 */
function shouldSkipCommonLog(message: string): boolean {
  // Skip common heartbeat/status messages
  const commonPatterns = [
    'heartbeat', 
    'ping', 
    'pong',
    'alive',
    'GET /api',
    'POST /api',
    'status'
  ];
  
  return commonPatterns.some(pattern => 
    message.toLowerCase().includes(pattern.toLowerCase())
  );
}

/**
 * Generate a unique identifier for a log based on its content
 * This helps identify duplicate logs even when they have different IDs
 */
function generateLogContentHash(log: SystemLog): string {
  // Include message, timestamp, and level to identify unique logs
  // For log lines from files that don't have clear IDs, this is more reliable
  const contentToHash = `${log.message}|${log.level}`;
  
  // Simple hash function
  let hash = 0;
  for (let i = 0; i < contentToHash.length; i++) {
    const char = contentToHash.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32bit integer
  }
  
  return `content-${Math.abs(hash).toString(16)}`;
}

/**
 * Process recent logs for notifications by fetching from the API
 */
export async function processRecentLogsForNotifications(): Promise<number> {
  try {
    console.log('[Notifications] Processing recent logs for notifications');
    
    // Different handling for server vs client environments
    if (isServerEnvironment()) {
      // In server environment, directly read logs instead of making a fetch request
      const fs = require('fs');
      const path = require('path');
      
      try {
        // Get app root directory
        const appRoot = process.cwd();
        const logsDir = path.join(appRoot, 'logs');
        
        // Try to find the seerrbridge log file
        let logPath = path.join(appRoot, 'seerrbridge.log');
        if (!fs.existsSync(logPath)) {
          logPath = path.join(logsDir, 'seerrbridge.log');
        }
        
        if (!fs.existsSync(logPath)) {
          console.log('[Notifications] No log file found at expected locations');
          return 0;
        }
        
        // Read the log file
        console.log(`[Notifications] Reading log file from: ${logPath}`);
        const fileContent = fs.readFileSync(logPath, 'utf8');
        const logLines = fileContent.split('\n').filter((line: string) => line.trim().length > 0);
        
        // Take the last 100 log lines
        const recentLogLines = logLines.slice(-100);
        
        // Load existing cache to check existing content hashes
        await loadProcessedLogIdsCache();
        
        // Convert to system logs format with content-based IDs
        const logs: SystemLog[] = recentLogLines.map((line: string, index: number) => {
          // Try to parse timestamp from the line
          const timestampMatch = line.match(/^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})/);
          const timestamp = timestampMatch ? new Date(timestampMatch[1]).toISOString() : new Date().toISOString();
          
          // Try to parse log level
          let level = 'info';
          if (line.includes('ERROR') || line.includes('Error')) level = 'error';
          if (line.includes('WARNING') || line.includes('Warning')) level = 'warning';
          if (line.includes('SUCCESS') || line.includes('Success')) level = 'success';
          
          // Create log object
          const log: SystemLog = {
            id: `server-log-${Date.now()}-${index}`,
            timestamp,
            level,
            message: line,
            source: 'server-logs',
            rawLog: line
          };
          
          // Generate and add a content hash ID to better identify duplicates
          const contentHash = generateLogContentHash(log);
          log.id = contentHash;
          
          return log;
        });
        
        console.log(`[Notifications] Processing ${logs.length} recent log lines from file`);
        
        // Process logs for notifications
        return await processLogsForNotifications(logs);
      } catch (fileError) {
        console.error('[Notifications] Error reading logs file:', fileError);
        return 0;
      }
    }
    
    // In client environment, fetch logs from API
    const url = getApiUrl('/api/logs/recent');
    const response = await fetch(url, {
      cache: 'no-store'
    });
    
    if (!response.ok) {
      throw new Error(`Failed to fetch recent logs: ${await response.text()}`);
    }
    
    const data = await response.json();
    
    if (!data.logs || !Array.isArray(data.logs)) {
      console.error('[Notifications] Invalid response from logs API:', data);
      return 0;
    }
    
    // Process the logs for notifications
    const notificationCount = await processLogsForNotifications(data.logs);
    
    if (notificationCount > 0) {
      console.log(`[Notifications] Sent ${notificationCount} notifications from recent logs`);
    }
    
    return notificationCount;
  } catch (error) {
    console.error('[Notifications] Error processing recent logs:', error);
    return 0;
  }
} 
