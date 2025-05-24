import { NextRequest, NextResponse } from "next/server";
import { readNotificationSettingsFromFile } from "@/lib/server-notifications";
import fs from "fs";
import path from "path";
import { NotificationType } from "@/lib/notifications";
import { sendDiscordWebhook } from "@/lib/server-notifications";
import { processRecentLogsForNotifications } from '@/lib/log-notification-bridge';

// Keep track of processed log entries by hash with persistent storage
const APP_ROOT = process.cwd();
const LOGS_DIR = path.join(APP_ROOT, 'logs');
const PROCESSED_ENTRIES_FILE = path.join(LOGS_DIR, 'processed_entries.json');
const LOG_BASELINE_FILE = path.join(LOGS_DIR, 'log_baseline.json');
const CONFIG_FILE_PATH = path.join(LOGS_DIR, 'log_config.json');
console.log(`[DEBUG] Processed entries file path: ${PROCESSED_ENTRIES_FILE}`);
console.log(`[DEBUG] Log baseline file path: ${LOG_BASELINE_FILE}`);

// Flag to indicate if initial baseline has been created
let baselineInitialized = false;

// Store the file sizes at startup to only process new entries
interface LogFileBaseline {
  [filepath: string]: {
    size: number;
    lastModified: string;
    lineCount: number;
  };
}

// Regular expressions to match log patterns
const LOG_PATTERNS = {
  success: /\[(.+?)\]\s+✅\s+(.*?):\s+(.*)/,
  error: /\[(.+?)\]\s+❌\s+(.*?):\s+(.*)/,
  warning: /\[(.+?)\]\s+⚠️\s+(.*?):\s+(.*)/,
  
  // Enhanced regex patterns with better flexibility for seerbridge log format
  // Format: YYYY-MM-DD HH:MM:SS.SSS | LEVEL | module:function:line - Message
  // Case insensitive and flexible with spacing
  seerbridge_success: /(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})\s+\|\s+(?:SUCCESS|Success|success)\s+\|\s+(.*?)\s+-\s+(.*)/i,
  seerbridge_error: /(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})\s+\|\s+(?:ERROR|Error|error)\s+\|\s+(.*?)\s+-\s+(.*)/i,
  seerbridge_warning: /(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})\s+\|\s+(?:WARNING|Warning|warning)\s+\|\s+(.*?)\s+-\s+(.*)/i,
  seerbridge_info: /(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})\s+\|\s+(?:INFO|Info|info)\s+\|\s+(.*?)\s+-\s+(.*)/i
};

// Interface definitions for log configuration
interface LogType {
  id: string;
  name: string;
  pattern: string;
  description: string;
  level: "success" | "error" | "warning" | "info" | "critical";
}

interface LogDisplay {
  id: string;
  logTypeId: string;
  location: "successes" | "failures" | "critical" | "dashboard" | "all";
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

// Load the log configuration
function loadLogConfiguration(): LogConfiguration {
  console.log(`[DEBUG] Loading log configuration from: ${CONFIG_FILE_PATH}`);
  
  // Default empty configuration
  const defaultConfig: LogConfiguration = {
    version: "1.0.0",
    defaultConfig: true,
    logTypes: [],
    logDisplays: []
  };
  
  try {
    if (fs.existsSync(CONFIG_FILE_PATH)) {
      const data = fs.readFileSync(CONFIG_FILE_PATH, 'utf8');
      return JSON.parse(data);
    }
  } catch (error) {
    console.error('[DEBUG] Error reading log configuration:', error);
  }
  
  return defaultConfig;
}

// Function to check if a log entry matches any configured log type patterns
function matchesConfiguredLogType(
  message: string, 
  config: LogConfiguration
): { matches: boolean; logType?: LogType; logDisplay?: LogDisplay } {
  // If no configuration, return false
  if (!config.logTypes || config.logTypes.length === 0 || !config.logDisplays || config.logDisplays.length === 0) {
    return { matches: false };
  }
  
  // Find matching log type
  for (const logType of config.logTypes) {
    try {
      const regex = new RegExp(logType.pattern);
      if (regex.test(message)) {
        // Find display rule for this log type
        const logDisplay = config.logDisplays.find(
          display => display.logTypeId === logType.id && display.showNotification
        );
        
        // Only return a match if this log type has a display rule with notifications enabled
        if (logDisplay) {
          return { matches: true, logType, logDisplay };
        }
      }
    } catch (error) {
      console.error(`[DEBUG] Invalid regex pattern in log type ${logType.id}:`, error);
    }
  }
  
  return { matches: false };
}

/**
 * Read processed entries from file
 */
function readProcessedEntries(): Set<string> {
  try {
    console.log(`[DEBUG] Checking for processed entries file at: ${PROCESSED_ENTRIES_FILE}`);
    
    // Create logs directory if it doesn't exist
    if (!fs.existsSync(LOGS_DIR)) {
      console.log(`[DEBUG] Logs directory doesn't exist, creating it at: ${LOGS_DIR}`);
      try {
        fs.mkdirSync(LOGS_DIR, { recursive: true });
        console.log(`[DEBUG] Successfully created logs directory`);
      } catch (dirError) {
        console.error(`[DEBUG] Failed to create logs directory:`, dirError);
      }
    }
    
    console.log(`[DEBUG] File exists: ${fs.existsSync(PROCESSED_ENTRIES_FILE)}`);
    
    if (fs.existsSync(PROCESSED_ENTRIES_FILE)) {
      const data = fs.readFileSync(PROCESSED_ENTRIES_FILE, 'utf8');
      console.log(`[DEBUG] Successfully read processed entries file, size: ${data.length} bytes`);
      const entries = JSON.parse(data);
      return new Set(entries);
    } else {
      console.log(`[DEBUG] Processed entries file not found, creating new empty file`);
      
      // Create an empty file with an empty array
      try {
        fs.writeFileSync(PROCESSED_ENTRIES_FILE, JSON.stringify([]), 'utf8');
        console.log(`[DEBUG] Successfully created empty processed entries file`);
        return new Set<string>();
      } catch (fileError) {
        console.error(`[DEBUG] Failed to create empty processed entries file:`, fileError);
      }
    }
  } catch (error) {
    console.error('Error reading processed entries file:', error);
  }
  return new Set<string>();
}

/**
 * Save processed entries to file
 */
function saveProcessedEntries(entries: Set<string>): void {
  try {
    // Keep only the most recent 1000 entries to prevent the file from growing too large
    const entriesArray = Array.from(entries);
    const trimmedEntries = entriesArray.slice(-1000);
    
    console.log(`[DEBUG] Saving ${trimmedEntries.length} processed entries to: ${PROCESSED_ENTRIES_FILE}`);
    
    // Make sure the parent directory exists
    const dir = path.dirname(PROCESSED_ENTRIES_FILE);
    if (!fs.existsSync(dir)) {
      console.log(`[DEBUG] Creating parent directory: ${dir}`);
      fs.mkdirSync(dir, { recursive: true });
    }
    
    fs.writeFileSync(
      PROCESSED_ENTRIES_FILE,
      JSON.stringify(trimmedEntries),
      'utf8'
    );
    
    console.log(`[DEBUG] Successfully saved processed entries file`);
    
    // Verify file was created
    console.log(`[DEBUG] File exists after save: ${fs.existsSync(PROCESSED_ENTRIES_FILE)}`);
  } catch (error) {
    console.error('Error saving processed entries file:', error);
  }
}

/**
 * Generate a hash for a log entry to avoid duplicate processing
 */
function generateEntryHash(type: string, title: string, message: string): string {
  return `${type}:${title}:${message}`;
}

/**
 * Get all log files in the logs directory
 */
function getLogFiles(): string[] {
  try {
    console.log(`[DEBUG] Looking for log files in directory: ${LOGS_DIR}`);
    
    if (!fs.existsSync(LOGS_DIR)) {
      console.log(`[DEBUG] Creating logs directory at: ${LOGS_DIR}`);
      fs.mkdirSync(LOGS_DIR, { recursive: true });
    }
    
    // List all files in the directory first for debugging
    const allFiles = fs.readdirSync(LOGS_DIR);
    console.log(`[DEBUG] All files in logs directory: ${JSON.stringify(allFiles)}`);
    
    // Look for all log files and include absolute path
    const logFiles = allFiles
      .filter(file => file.endsWith('.log'))
      .map(file => path.join(LOGS_DIR, file));
    
    // Create sample .log file if none exist (for initialization)
    if (logFiles.length === 0) {
      const seerBridgeLogInLogs = path.join(LOGS_DIR, 'seerrbridge.log');
      const seerBridgeLogInRoot = path.join(APP_ROOT, 'seerrbridge.log');
      
      // Check if the log file exists in logs directory
      if (fs.existsSync(seerBridgeLogInLogs)) {
        console.log(`[DEBUG] Found seerrbridge.log file in logs directory`);
        logFiles.push(seerBridgeLogInLogs);
      } 
      // If not in logs directory, check app root
      else if (fs.existsSync(seerBridgeLogInRoot)) {
        console.log(`[DEBUG] Found log file in app root: ${seerBridgeLogInRoot}`);
        
        // Try to move the log file to the logs directory for better organization
        try {
          // Copy the file to logs directory
          fs.copyFileSync(seerBridgeLogInRoot, seerBridgeLogInLogs);
          console.log(`[DEBUG] Copied log file from root to logs directory`);
          logFiles.push(seerBridgeLogInLogs);
          
          // Create a README in the root to explain why the log file was moved
          const readmePath = path.join(APP_ROOT, 'logs-moved-readme.txt');
          const readmeContent = 'Log files have been moved to the logs/ directory for better organization and to avoid exposing absolute paths in configuration files.\n';
          fs.writeFileSync(readmePath, readmeContent);
        } catch (copyError) {
          // If we can't copy, use the original location
          console.error(`[DEBUG] Error copying log file to logs directory:`, copyError);
          logFiles.push(seerBridgeLogInRoot);
        }
      }
    }
    
    // Log what we found
    console.log(`[DEBUG] Found ${logFiles.length} log files: ${JSON.stringify(logFiles)}`);
    return logFiles;
  } catch (error) {
    console.error('[DEBUG] Error reading log directory:', error);
    return [];
  }
}

/**
 * Read the baseline for log files (captures the state at startup)
 */
function readLogBaseline(): LogFileBaseline {
  try {
    if (fs.existsSync(LOG_BASELINE_FILE)) {
      const data = fs.readFileSync(LOG_BASELINE_FILE, 'utf8');
      const relativeBaseline = JSON.parse(data) as LogFileBaseline;
      
      // Convert relative paths back to absolute paths
      const absoluteBaseline: LogFileBaseline = {};
      for (const [relPath, info] of Object.entries(relativeBaseline)) {
        // Convert relative path to absolute path
        const absPath = path.resolve(APP_ROOT, relPath);
        absoluteBaseline[absPath] = info;
      }
      
      return absoluteBaseline;
    }
  } catch (error) {
    console.error('[DEBUG] Error reading log baseline file:', error);
  }
  return {};
}

/**
 * Create or update the baseline for log files
 */
function saveLogBaseline(baseline: LogFileBaseline): void {
  try {
    if (!fs.existsSync(LOGS_DIR)) {
      fs.mkdirSync(LOGS_DIR, { recursive: true });
    }
    
    // Convert absolute paths to relative paths for storage
    const relativeBaseline: LogFileBaseline = {};
    for (const [absPath, info] of Object.entries(baseline)) {
      // Convert absolute path to relative path (relative to APP_ROOT)
      const relPath = path.relative(APP_ROOT, absPath);
      relativeBaseline[relPath] = info;
    }
    
    fs.writeFileSync(LOG_BASELINE_FILE, JSON.stringify(relativeBaseline, null, 2), 'utf8');
    console.log(`[DEBUG] Saved log baseline file with ${Object.keys(relativeBaseline).length} entries`);
  } catch (error) {
    console.error('[DEBUG] Error saving log baseline file:', error);
  }
}

/**
 * Initialize the log baseline on first run
 * This establishes what logs existed when the app started
 */
function initializeLogBaseline(): void {
  if (baselineInitialized) {
    return;
  }
  
  try {
    console.log(`[DEBUG] Initializing log baseline`);
    const logFiles = getLogFiles();
    const baseline: LogFileBaseline = {};
    
    for (const filePath of logFiles) {
      if (fs.existsSync(filePath)) {
        try {
          const stats = fs.statSync(filePath);
          const content = fs.readFileSync(filePath, 'utf8');
          const lines = content.split('\n').filter(line => line.trim().length > 0);
          
          baseline[filePath] = {
            size: stats.size,
            lastModified: stats.mtime.toISOString(),
            lineCount: lines.length
          };
          
          console.log(`[DEBUG] Added baseline for ${filePath}: ${lines.length} lines, ${stats.size} bytes`);
        } catch (error) {
          console.error(`[DEBUG] Error creating baseline for ${filePath}:`, error);
        }
      }
    }
    
    saveLogBaseline(baseline);
    baselineInitialized = true;
  } catch (error) {
    console.error('[DEBUG] Error initializing log baseline:', error);
  }
}

/**
 * Process log files for new notifications
 */
async function processLogFiles(): Promise<number> {
  // Initialize baseline on first run
  if (!baselineInitialized) {
    initializeLogBaseline();
  }
  
  const logFiles = getLogFiles();
  console.log(`[DEBUG] Processing ${logFiles.length} log files`);
  let notificationCount = 0;
  
  // Load processed entries from file
  const processedEntries = readProcessedEntries();
  console.log(`[DEBUG] Loaded ${processedEntries.size} processed entries from file`);
  let entriesModified = false;
  
  // Get the current baseline
  const baseline = readLogBaseline();
  let baselineModified = false;
  
  for (const filePath of logFiles) {
    try {
      console.log(`[DEBUG] Processing log file: ${filePath}`);
      
      if (!fs.existsSync(filePath)) {
        console.log(`[DEBUG] Log file doesn't exist: ${filePath}`);
        continue;
      }
      
      const content = await fs.promises.readFile(filePath, 'utf8');
      console.log(`[DEBUG] Read log file content, size: ${content.length} bytes`);
      const lines = content.split('\n').filter(line => line.trim().length > 0);
      console.log(`[DEBUG] Found ${lines.length} lines in log file`);
      
      // Get baseline info for this file - convert paths if needed
      const relPath = path.relative(APP_ROOT, filePath);
      const fileBaseline = baseline[relPath];
      const stats = fs.statSync(filePath);
      
      // Check if this is a new file or an existing file with changes
      let startLine = 0;
      
      if (fileBaseline) {
        // If file exists in baseline, only process lines after the baseline line count
        if (lines.length > fileBaseline.lineCount) {
          console.log(`[DEBUG] File has grown from ${fileBaseline.lineCount} to ${lines.length} lines`);
          startLine = fileBaseline.lineCount;
        } else {
          console.log(`[DEBUG] No new lines detected in file, skipping (${lines.length} lines)`);
          continue;
        }
      } else {
        console.log(`[DEBUG] New file detected, processing all content`);
      }
      
      // For diagnostic purposes, check the first few lines
      if (lines.length > 0) {
        console.log(`[DEBUG] First log line sample: ${lines[0].substring(0, 100)}...`);
        
        // Check if our regex patterns match this log format
        for (const [type, regex] of Object.entries(LOG_PATTERNS)) {
          const matches = lines.slice(0, Math.min(lines.length, 10)).some(line => regex.test(line));
          console.log(`[DEBUG] Pattern ${type} matches sample logs: ${matches}`);
        }
      }
      
      // Process only new lines
      if (startLine < lines.length) {
        console.log(`[DEBUG] Processing lines ${startLine} to ${lines.length - 1}`);
        
        for (let i = startLine; i < lines.length; i++) {
          const line = lines[i];
          const result = await processLogLine(line, processedEntries);
          if (result) {
            notificationCount++;
            entriesModified = true;
            console.log(`[DEBUG] Successfully processed and sent notification for log line`);
          }
        }
        
        // Update the baseline
        baseline[relPath] = {
          size: stats.size,
          lastModified: stats.mtime.toISOString(),
          lineCount: lines.length
        };
        baselineModified = true;
      }
    } catch (error) {
      console.error(`[DEBUG] Error processing log file ${filePath}:`, error);
    }
  }
  
  // Save processed entries if modified
  if (entriesModified) {
    console.log(`[DEBUG] Saving modified processed entries`);
    saveProcessedEntries(processedEntries);
  } else {
    console.log(`[DEBUG] No new log entries processed, not saving processed entries`);
  }
  
  // Save baseline if modified
  if (baselineModified) {
    console.log(`[DEBUG] Saving modified log baseline`);
    saveLogBaseline(baseline);
  }
  
  return notificationCount;
}

/**
 * Check if a line matches any of our log patterns
 */
function checkLogLineFormat(line: string): { matches: boolean, type?: string } {
  for (const [type, regex] of Object.entries(LOG_PATTERNS)) {
    if (regex.test(line)) {
      return { matches: true, type };
    }
  }
  return { matches: false };
}

/**
 * Process a single log line and send notification if needed
 */
async function processLogLine(line: string, processedEntries: Set<string>): Promise<boolean> {
  // Check if this line should be processed based on log configuration
  const logConfig = loadLogConfiguration();
  const { matches, logType, logDisplay } = matchesConfiguredLogType(line, logConfig);
  
  // If not configured to show notifications for this log type, skip
  if (!matches || !logDisplay?.showNotification) {
    return false;
  }
  
  // Try to match against our patterns
  for (const [type, regex] of Object.entries(LOG_PATTERNS)) {
    const match = line.match(regex);
    
    if (match) {
      console.log(`[DEBUG] Log line matched pattern ${type}`);
      const timestamp = match[1];
      const title = match[2];
      const message = match[3];
      
      // For SeerrBridge logs, adapt based on the type
      let notificationType: NotificationType;
      if (type.includes('success')) {
        notificationType = "success";
      } else if (type.includes('error')) {
        notificationType = "error";
      } else if (type.includes('warning')) {
        notificationType = "warning";
      } else {
        // Skip info logs by default
        console.log(`[DEBUG] Skipping info log type: ${type}`);
        continue;
      }
      
      // Generate a hash to avoid duplicates
      const hash = generateEntryHash(notificationType, title, message);
      console.log(`[DEBUG] Generated hash: ${hash}`);
      
      // Skip if already processed
      if (processedEntries.has(hash)) {
        console.log(`[DEBUG] Log entry already processed, skipping`);
        return false;
      }
      
      // Send notification
      const settings = await readNotificationSettingsFromFile();
      
      // Check if this notification type is enabled
      let isEnabled = false;
      switch (notificationType) {
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
      
      if (isEnabled && settings.discord_webhook_url) {
        console.log(`[DEBUG] Sending ${notificationType} notification for: ${title}`);
        const success = await sendDiscordWebhook(
          settings.discord_webhook_url,
          notificationType,
          title,
          message,
          { timestamp }
        );
        
        if (success) {
          // Mark as processed
          processedEntries.add(hash);
          return true;
        }
      } else {
        console.log(`[DEBUG] Notification type ${notificationType} is disabled or webhook URL not set`);
      }
    }
  }
  
  return false;
}

// In-memory buffer for console logs from the API
let consoleBuffer: Array<{
  type: NotificationType;
  title: string;
  message: string;
  timestamp: string;
  processed: boolean;
}> = [];

/**
 * Process in-memory console records
 */
async function processConsoleBuffer(): Promise<number> {
  let notificationCount = 0;
  const unprocessedRecords = consoleBuffer.filter(record => !record.processed);
  
  // Load processed entries
  const processedEntries = readProcessedEntries();
  let entriesModified = false;
  
  for (const record of unprocessedRecords) {
    const hash = generateEntryHash(record.type, record.title, record.message);
    
    // Skip if already processed
    if (processedEntries.has(hash)) {
      record.processed = true;
      continue;
    }
    
    // Get settings
    const settings = await readNotificationSettingsFromFile();
    
    // Check if this notification type is enabled
    let isEnabled = false;
    switch (record.type) {
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
    
    if (isEnabled && settings.discord_webhook_url) {
      try {
        const success = await sendDiscordWebhook(
          settings.discord_webhook_url,
          record.type,
          record.title,
          record.message,
          { timestamp: record.timestamp }
        );
        
        if (success) {
          processedEntries.add(hash);
          notificationCount++;
          entriesModified = true;
        }
      } catch (error) {
        console.error(`Failed to send notification:`, error);
      }
    }
    
    // Mark as processed regardless of outcome to avoid retrying
    record.processed = true;
  }
  
  // Cleanup processed records periodically
  if (consoleBuffer.length > 1000) {
    consoleBuffer = consoleBuffer.filter(record => !record.processed).slice(0, 500);
  }
  
  // Save processed entries if modified
  if (entriesModified) {
    saveProcessedEntries(processedEntries);
  }
  
  return notificationCount;
}

/**
 * Add a record to the console buffer
 * This function is used by the log API route
 */
export function addToConsoleBuffer(
  type: NotificationType,
  title: string,
  message: string
): void {
  consoleBuffer.unshift({
    type,
    title,
    message,
    timestamp: new Date().toISOString(),
    processed: false
  });
}

/**
 * Main function to process all logs and send notifications
 */
async function processAllLogs(): Promise<number> {
  // Initialize baseline on first run if it hasn't been done yet
  if (!baselineInitialized) {
    initializeLogBaseline();
  }
  
  // First process any log files
  const fileNotificationCount = await processLogFiles();
  
  // Then process in-memory records
  const bufferNotificationCount = await processConsoleBuffer();
  
  return fileNotificationCount + bufferNotificationCount;
}

// Add a function to clean up notifications older than 24 hours
function cleanUpOldNotifications(): void {
  try {
    // Read processed entries
    const processedEntries = readProcessedEntries();
    
    // Keep only entries from the last 24 hours
    const oneDayAgo = new Date();
    oneDayAgo.setHours(oneDayAgo.getHours() - 24);
    
    // Filter and convert to new set
    const filteredEntries = new Set<string>();
    processedEntries.forEach(entry => {
      // Try to extract timestamp from the entry (assuming format contains a timestamp)
      const match = entry.match(/(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{3}Z)/);
      
      if (match) {
        const timestamp = new Date(match[1]);
        if (timestamp >= oneDayAgo) {
          filteredEntries.add(entry);
        }
      } else {
        // If no timestamp found, keep the entry
        filteredEntries.add(entry);
      }
    });
    
    // Save the filtered entries back
    if (filteredEntries.size !== processedEntries.size) {
      console.log(`[DEBUG] Cleaned up ${processedEntries.size - filteredEntries.size} old notification entries`);
      saveProcessedEntries(filteredEntries);
    }
  } catch (error) {
    console.error('Error cleaning up old notifications:', error);
  }
}

/**
 * Background API route for processing logs and sending notifications
 * Called by the NotificationInitializer component at regular intervals
 */
export async function GET(request: NextRequest) {
  try {
    console.log('[Background] Starting log processing for notifications');
    
    // Check if notification settings are configured
    const settings = await readNotificationSettingsFromFile();
    console.log(`[Background] Notification settings loaded, webhook set: ${!!settings.discord_webhook_url}`);
    
    // Process logs for notifications using the bridge
    let configuredNotifications = 0;
    
    try {
      console.log('[Background] Calling processRecentLogsForNotifications()');
      configuredNotifications = await processRecentLogsForNotifications();
      console.log(`[Background] Processed and sent ${configuredNotifications} log notifications`);
    } catch (error) {
      console.error('[Background] Error processing recent logs for notifications:', error);
    }
    
    return NextResponse.json({
      success: true,
      processed: {
        configuredNotifications
      }
    });
  } catch (error) {
    console.error('[Background] Error in background processing route:', error);
    return NextResponse.json(
      {
        success: false,
        error: 'Failed to process logs in background'
      },
      { status: 500 }
    );
  }
} 