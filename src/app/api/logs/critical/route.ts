import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import { formatDate, parseLogLines } from '@/lib/utils';
import { parseLogFile } from '@/lib/server-utils';
import { type LogEntry } from "@/lib/utils";

// Extended LogEntry type to include rawLine
interface ExtendedLogEntry extends LogEntry {
  rawLine?: string;
  matchedLogTypeId?: string;
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

export async function GET(request: Request) {
  try {
    // Load the log configuration
    const logConfig = await loadLogConfig();
    
    // Check if file exists
    const fileExists = fs.existsSync(ROOT_LOG_FILE_PATH);
    console.log(`Log file found: ${fileExists}`);
    
    if (!fileExists || logConfig.logTypes.length === 0 || logConfig.logDisplays.length === 0) {
      return NextResponse.json({ 
        criticalErrors: [], 
        formattedDates: [], 
        criticalLogs: [],
        criticalCount: 0
      });
    }
    
    // Get configured display locations for critical errors
    const criticalDisplays = logConfig.logDisplays.filter(
      display => display.location === "all" || 
      (Array.isArray(display.location) && 
      (display.location.includes("critical") || display.location.includes("all")))
    );
    
    if (criticalDisplays.length === 0) {
      return NextResponse.json({ 
        criticalErrors: [], 
        formattedDates: [], 
        criticalLogs: [],
        criticalCount: 0
      });
    }
    
    const criticalLogTypeIds = criticalDisplays.map(display => display.logTypeId);
    
    // First, try to get matches from the stats API
    let logMatches: { logTypeId: string, count: number }[] = [];
    const urlOrigin = new URL(request.url).origin;
    
    try {
      const logMatchesResponse = await fetch(`${urlOrigin}/api/logs/stats/matches`);
      if (logMatchesResponse.ok) {
        const data = await logMatchesResponse.json();
        logMatches = data.stats || [];
      }
    } catch (error) {
      console.error("Error fetching log matches:", error);
    }
    
    // Calculate total critical count from matched log types
    let criticalCount = 0;
    for (const logType of logConfig.logTypes) {
      if (criticalLogTypeIds.includes(logType.id) && logType.level === "critical") {
        const match = logMatches.find(match => match.logTypeId === logType.id);
        if (match) {
          criticalCount += match.count;
        }
      }
    }
    
    // Read all log entries
    const allLogLines = await readLogEntries();
    
    // Parse all log lines into structured objects
    const parsedLogs = parseLogLines(allLogLines);
    
    // Filter logs based on configured log types
    const filteredLogs = [];
    const criticalLogEntries: ExtendedLogEntry[] = [];
    
    // Process logs to get details for display
    for (const log of parsedLogs) {
      // Check if this log matches any critical log type
      for (const logType of logConfig.logTypes) {
        if (criticalLogTypeIds.includes(logType.id) && logType.level === "critical") {
          try {
            const regex = new RegExp(logType.pattern, 'i');
            if (regex.test(log.message)) {
              // Add to critical log entries
              criticalLogEntries.push({
                ...log,
                rawLine: (log as any).rawLog || log.message,
                matchedLogTypeId: logType.id
              });
              
              // Add to formatted critical errors
              filteredLogs.push({
                id: `critical-${log.timestamp}`,
                title: log.source || "System Error",
                timestamp: log.timestamp,
                status: "critical",
                type: log.message.toLowerCase().includes("movie") ? "movie" : "tv",
                detailedError: (log as any).rawLog || log.message,
                details: {
                  message: log.message
                },
                matchedLogTypeId: logType.id,
                matchedLogTypeName: logType.name
              });
              break; // Once matched, no need to check other log types
            }
          } catch (error) {
            console.error(`Invalid regex pattern in log type ${logType.id}:`, error);
          }
        }
      }
    }
    
    // Sort by timestamp (newest first)
    filteredLogs.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
    
    console.log(`Critical errors found: ${filteredLogs.length}`);
    console.log(`Total critical count: ${criticalCount}`);
    
    return NextResponse.json({ 
      criticalErrors: filteredLogs, 
      formattedDates: filteredLogs.map(error => formatDate(error.timestamp)),
      criticalLogs: criticalLogEntries,
      criticalCount 
    });
  } catch (error) {
    console.error("Error reading log file:", error);
    return NextResponse.json(
      { 
        error: "Failed to fetch critical error logs", 
        message: error instanceof Error ? error.message : String(error)
      }, 
      { status: 500 }
    );
  }
} 