import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { parseLogLines } from "@/lib/utils";

// Define the path to the actual log file in the root directory
const ROOT_LOG_FILE_PATH = path.join(process.cwd(), "logs", "seerrbridge.log");

// Define the path to the configuration file
const CONFIG_FILE_PATH = path.join(process.cwd(), "logs", "log_config.json");

/**
 * Read the log file from the root directory
 */
async function readLogEntries(): Promise<string[]> {
  try {
    // Check if log file exists in root directory
    if (!fs.existsSync(ROOT_LOG_FILE_PATH)) {
      console.error(`Log file not found at: ${ROOT_LOG_FILE_PATH}`);
      return [];
    }
    
    // Read all lines from the log file without limitation
    console.log(`Reading log file from: ${ROOT_LOG_FILE_PATH}`);
    const logData = fs.readFileSync(ROOT_LOG_FILE_PATH, "utf-8");
    const lines = logData.split("\n").filter(line => line.trim());
    
    console.log(`Found ${lines.length} log entries in the file.`);
    
    // Return all log lines
    return lines;
  } catch (error) {
    console.error("Error reading log file:", error);
    console.error(`File path attempted: ${ROOT_LOG_FILE_PATH}`);
    return [];
  }
}

/**
 * Load the log configuration
 */
async function loadLogConfig() {
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

// GET handler for retrieving log entries
export async function GET(request: Request) {
  try {
    // Get the URL parameters
    const url = new URL(request.url);
    const itemsPerPage = parseInt(url.searchParams.get("limit") || "25", 10);
    const page = parseInt(url.searchParams.get("page") || "1", 10);
    const sortDirection = url.searchParams.get("sort") || "desc"; // Default to descending (newest first)
    const searchQuery = url.searchParams.get("search") || ""; // Search parameter
    const levelFilter = url.searchParams.get("level") || ""; // Level filter parameter
    const logTypeId = url.searchParams.get("logTypeId") || ""; // Log type filter parameter
    
    // Read ALL logs from the file
    const allLogLines = await readLogEntries();
    
    // Parse all log lines into structured objects
    const allParsedLogs = parseLogLines(allLogLines);
    
    // Define level aliases for more flexible filtering
    const levelAliases: Record<string, string[]> = {
      'info': ['info', 'information', 'inf'],
      'debug': ['debug', 'dbg'],
      'success': ['success', 'ok', 'succeeded'],
      'warning': ['warning', 'warn', 'attention'],
      'error': ['error', 'err', 'failure', 'failed'],
      'critical': ['critical', 'crit', 'fatal']
    };
    
    // Get log pattern for log type filtering
    let logTypePattern: RegExp | null = null;
    if (logTypeId) {
      const config = await loadLogConfig();
      const logType = config.logTypes.find((lt: any) => lt.id === logTypeId);
      if (logType && logType.pattern) {
        try {
          logTypePattern = new RegExp(logType.pattern, 'i');
        } catch (error) {
          console.error(`Invalid regex pattern in log type: ${logType.name}`, error);
        }
      }
    }
    
    // Filter logs if search query, level filter, or log type filter is provided
    const filteredLogs = allParsedLogs.filter(log => {
      // Apply search query filter if provided
      const matchesSearch = !searchQuery || 
        log.timestamp.toLowerCase().includes(searchQuery.toLowerCase()) ||
        log.level.toLowerCase().includes(searchQuery.toLowerCase()) ||
        log.message.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (log.source && log.source.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (log.rawLog && log.rawLog.toLowerCase().includes(searchQuery.toLowerCase()));
      
      // Apply strict level filtering - only match the exact level specified
      const matchesLevel = !levelFilter || 
        log.level.toLowerCase() === levelFilter.toLowerCase() ||
        (levelFilter && levelAliases[levelFilter.toLowerCase()]?.includes(log.level.toLowerCase()));
      
      // Apply log type pattern filtering
      const matchesLogType = !logTypePattern || logTypePattern.test(log.message);
      
      return matchesSearch && matchesLevel && matchesLogType;
    });
    
    // Sort logs by timestamp
    const sortedLogs = [...filteredLogs].sort((a, b) => {
      const dateA = new Date(a.timestamp).getTime();
      const dateB = new Date(b.timestamp).getTime();
      
      // Sort by timestamp (newest first for desc, oldest first for asc)
      return sortDirection === "desc" ? dateB - dateA : dateA - dateB;
    });
    
    // Calculate pagination
    const startIndex = (page - 1) * itemsPerPage;
    const endIndex = page * itemsPerPage;
    const paginatedLogs = sortedLogs.slice(startIndex, endIndex);
    
    console.log(`Returning ${paginatedLogs.length} logs (page ${page} of ${Math.ceil(sortedLogs.length / itemsPerPage)})`);
    console.log(`Total logs: ${sortedLogs.length}, Sort direction: ${sortDirection}`);
    if (searchQuery) {
      console.log(`Applied search filter: "${searchQuery}" - found ${filteredLogs.length} matches`);
    }
    if (levelFilter) {
      console.log(`Applied level filter: "${levelFilter}" - found ${filteredLogs.length} matches`);
    }
    if (logTypeId) {
      console.log(`Applied log type filter: "${logTypeId}" - found ${filteredLogs.length} matches`);
    }
    
    return NextResponse.json({
      logs: paginatedLogs,
      total: sortedLogs.length,
      page,
      limit: itemsPerPage,
      sortDirection,
      searchQuery,
      levelFilter,
      logTypeId,
      totalPages: Math.ceil(sortedLogs.length / itemsPerPage),
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error("Error in GET /api/logs/entries:", error);
    return NextResponse.json(
      { error: "Failed to load log entries" },
      { status: 500 }
    );
  }
} 