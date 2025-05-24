import { NextRequest, NextResponse } from "next/server";
import { parseLogFile } from "@/lib/server-utils";
import path from "path";
import fs from "fs";
import { parseLogLines } from "@/lib/utils";

interface EnhancedMediaItem {
  id: string;
  title: string;
  timestamp: string;
  [key: string]: any; // Allow other properties from MediaItem
}

// Add type definitions for the log configuration
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

// Define the path to the log file in the root directory
const ROOT_LOG_FILE_PATH = path.join(process.cwd(), "logs", "seerrbridge.log");

// Define the path to the configuration file
const CONFIG_FILE_PATH = path.join(process.cwd(), "logs", "log_config.json");

/**
 * Read the log file from the root directory
 */
async function readLogEntries(): Promise<string[]> {
  try {
    // Check if log file exists
    if (!fs.existsSync(ROOT_LOG_FILE_PATH)) {
      console.error(`Log file not found at: ${ROOT_LOG_FILE_PATH}`);
      return [];
    }
    
    // Read all lines from the log file
    const logData = fs.readFileSync(ROOT_LOG_FILE_PATH, "utf-8");
    const lines = logData.split("\n").filter(line => line.trim());
    
    console.log(`Found ${lines.length} log entries in the file.`);
    
    // Return all log lines
    return lines;
  } catch (error) {
    console.error("Error reading log file:", error);
    return [];
  }
}

/**
 * Load the log configuration
 */
async function loadLogConfig(): Promise<LogConfiguration> {
  try {
    // Check if configuration file exists
    if (!fs.existsSync(CONFIG_FILE_PATH)) {
      return {
        version: "1.0.0",
        defaultConfig: true,
        logTypes: [],
        logDisplays: []
      };
    }
    
    // Read and parse the configuration file
    const configData = fs.readFileSync(CONFIG_FILE_PATH, "utf-8");
    return JSON.parse(configData);
  } catch (error) {
    console.error("Error loading log configuration:", error);
    return {
      version: "1.0.0",
      defaultConfig: true,
      logTypes: [],
      logDisplays: []
    };
  }
}

// Helper function to extract log type IDs from displays
const extractLogTypeIds = (displays: LogDisplay[]): string[] => 
  displays.map(display => display.logTypeId);

// Helper function to get displays for a specific location
const getDisplaysForLocation = (logDisplays: LogDisplay[], location: string): LogDisplay[] => {
  return logDisplays.filter(display => 
    display.location === "all" || 
    (Array.isArray(display.location) && 
      (display.location.includes(location) || display.location.includes("all")))
  );
};

export async function GET(request: NextRequest) {
  try {
    // Load the log configuration
    const logConfig = await loadLogConfig();
    
    // If no log types or display rules defined, return empty data
    if (logConfig.logTypes.length === 0 || logConfig.logDisplays.length === 0) {
      return NextResponse.json({
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
      });
    }
    
    // First, fetch log matches using the stats API
    const logMatchesResponse = await fetch(`${request.nextUrl.origin}/api/logs/stats/matches`);
    let logMatches: { logTypeId: string, count: number }[] = [];
    
    if (logMatchesResponse.ok) {
      const data = await logMatchesResponse.json();
      logMatches = data.stats || [];
    }
    
    // Set the log file path relative to the application root
    const logFilePath = path.join(process.cwd(), "logs", "seerrbridge.log");
    
    // Check if the file exists
    if (!fs.existsSync(logFilePath)) {
      return NextResponse.json(
        { 
          error: "Log file not found",
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
        }, 
        { status: 200 }
      );
    }
    
    // Parse the log file to get raw data
    const { recentLogs: allLogs, statistics: rawStats } = await parseLogFile(logFilePath);
    const tokenStatus = rawStats.tokenStatus;
    
    // Get display configuration
    const configuredLogDisplays = logConfig.logDisplays || [];
    
    // Get display locations for dashboard components using the helper function
    const dashboardDisplays = getDisplaysForLocation(configuredLogDisplays, "dashboard");
    const statsSuccessDisplays = getDisplaysForLocation(configuredLogDisplays, "stats_success");
    const statsFailureDisplays = getDisplaysForLocation(configuredLogDisplays, "stats_failure");
    const statsErrorsDisplays = getDisplaysForLocation(configuredLogDisplays, "stats_errors");
    const statsInfoDisplays = getDisplaysForLocation(configuredLogDisplays, "stats_info");
    const statsWarningsDisplays = getDisplaysForLocation(configuredLogDisplays, "stats_warnings");
    const statsTotalDisplays = getDisplaysForLocation(configuredLogDisplays, "stats_total");
    const recentLogsDisplays = getDisplaysForLocation(configuredLogDisplays, "recent_logs");
    
    // Extract log type IDs for each display location
    const dashboardLogTypeIds = extractLogTypeIds(dashboardDisplays);
    const successLogTypeIds = extractLogTypeIds(statsSuccessDisplays);
    const failureLogTypeIds = extractLogTypeIds(statsFailureDisplays);
    const errorLogTypeIds = extractLogTypeIds(statsErrorsDisplays);
    const infoLogTypeIds = extractLogTypeIds(statsInfoDisplays);
    const warningLogTypeIds = extractLogTypeIds(statsWarningsDisplays);
    const totalLogTypeIds = extractLogTypeIds(statsTotalDisplays);
    const recentLogsTypeIds = extractLogTypeIds(recentLogsDisplays);
    
    // Calculate statistics based on matched log types and counts
    let successCount = 0;
    let errorCount = 0;
    let warningCount = 0;
    let infoCount = 0;
    let criticalErrors = 0;
    let failedEpisodes = 0;
    let successfulGrabs = 0;
    
    // Use logMatches to calculate statistics based on log type IDs
    for (const logType of logConfig.logTypes) {
      const match = logMatches.find(match => match.logTypeId === logType.id);
      const count = match ? match.count : 0;
      
      // Count based on log level
      switch (logType.level) {
        case "success":
          successCount += successLogTypeIds.includes(logType.id) ? count : 0;
          // Check if this matches success stats card types
          if (successLogTypeIds.includes(logType.id)) {
            successfulGrabs += count;
          }
          break;
        case "error":
          errorCount += errorLogTypeIds.includes(logType.id) ? count : 0;
          // Check if this matches failure stats card types
          if (failureLogTypeIds.includes(logType.id)) {
            failedEpisodes += count;
          }
          break;
        case "warning":
          warningCount += warningLogTypeIds.includes(logType.id) ? count : 0;
          break;
        case "info":
          infoCount += infoLogTypeIds.includes(logType.id) ? count : 0;
          break;
        case "critical":
          criticalErrors += count;
          // No longer adding critical errors to errorCount to keep them separate
          break;
      }
    }
    
    // Process logs to get recent successes and failures for display
    let successfulItems: EnhancedMediaItem[] = [];
    let failedItems: EnhancedMediaItem[] = [];
    let filteredLogs = [];
    
    // Read all log entries
    const allLogLines = await readLogEntries();
    
    // Parse all log lines into structured objects
    const parsedLogs = parseLogLines(allLogLines);
    
    // Match logs against log types to categorize them
    for (const log of parsedLogs) {
      let matched = false;
      let matchedTypes = [];
      
      // Check if this log matches any configured log type
      for (const logType of logConfig.logTypes) {
        try {
          const regex = new RegExp(logType.pattern, 'i');
          if (regex.test(log.message)) {
            matched = true;
            matchedTypes.push({
              typeId: logType.id,
              level: logType.level,
              name: logType.name
            });
          }
        } catch (error) {
          console.error(`Invalid regex pattern in log type ${logType.id}:`, error);
        }
      }
      
      // Only process logs that match configured types
      if (matched) {
        // Check if this log should be shown on dashboard
        const shouldShowOnDashboard = matchedTypes.some(
          match => dashboardLogTypeIds.includes(match.typeId)
        );
        
        if (shouldShowOnDashboard) {
          filteredLogs.push(log);
        }
        
        // Update statistics based on matched log types
        for (const match of matchedTypes) {
          // Sort by log level and log type
          if (match.level === "success" && successLogTypeIds.includes(match.typeId)) {
            successfulItems.push({
              id: `success-${log.timestamp}`,
              title: log.message.substring(0, 50), // Truncate for display
              timestamp: log.timestamp,
              message: log.message,
              level: log.level,
              logTypeId: match.typeId, // Track which log type matched
              logTypeName: match.name
            });
          } else if ((match.level === "error" || match.level === "critical") && failureLogTypeIds.includes(match.typeId)) {
            failedItems.push({
              id: `failure-${log.timestamp}`,
              title: log.message.substring(0, 50), // Truncate for display
              timestamp: log.timestamp,
              message: log.message,
              level: log.level,
              logTypeId: match.typeId, // Track which log type matched
              logTypeName: match.name
            });
          }
        }
      }
    }
    
    // Sort by timestamp (newest first) and limit arrays
    filteredLogs.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
    successfulItems.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
    failedItems.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
    
    // Prepare recent items for display
    const recentSuccesses = successfulItems.slice(0, 5).map((item, index) => ({
      ...item,
      id: `success-${index}-${Date.now()}`
    }));
    
    const recentFailures = failedItems.slice(0, 5).map((item, index) => ({
      ...item,
      id: `failure-${index}-${Date.now()}`
    }));
    
    // Calculate total logs count based on logMatches - only count log types in dashboard display
    const totalLogCount = logMatches.reduce((total, match) => {
      const logType = logConfig.logTypes.find(lt => lt.id === match.logTypeId);
      if (logType && totalLogTypeIds.includes(match.logTypeId)) {
        return total + match.count;
      }
      return total;
    }, 0);
    
    // Create statistics object with only configured data
    const statistics = {
      totalLogs: totalLogCount,
      successCount,
      errorCount,
      warningCount,
      infoCount,
      failedEpisodes,
      successfulGrabs,
      criticalErrors,
      tokenStatus, // Keep token status as it's not log-type dependent
      recentSuccesses,
      recentFailures
    };
    
    return NextResponse.json({
      statistics,
      recentLogs: filteredLogs.slice(0, 20)
    });
  } catch (error) {
    console.error("Error fetching log data:", error);
    return NextResponse.json({ 
      error: "Failed to parse log file",
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
    }, { status: 500 });
  }
} 