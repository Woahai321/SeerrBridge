import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { parseLogLines } from "@/lib/utils";

// Define the log type interface
interface LogType {
  id: string;
  name: string;
  pattern: string;
  description: string;
  level: "success" | "error" | "warning" | "info" | "critical";
  selectedWords?: string[];
}

// Load configuration from logs/log_config.json
async function loadLogConfig() {
  try {
    const CONFIG_FILE_PATH = path.join(process.cwd(), "logs", "log_config.json");
    
    // Check if configuration file exists
    if (!fs.existsSync(CONFIG_FILE_PATH)) {
      return {
        version: "1.0.0",
        defaultConfig: true,
        logTypes: [] as LogType[],
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
      logTypes: [] as LogType[],
      logDisplays: []
    };
  }
}

// Read log entries from the file system
async function readLogEntries() {
  try {
    const ROOT_LOG_FILE_PATH = path.join(process.cwd(), "logs", "seerrbridge.log");
    
    // Check if log file exists in root directory
    if (!fs.existsSync(ROOT_LOG_FILE_PATH)) {
      console.error(`Log file not found at: ${ROOT_LOG_FILE_PATH}`);
      return [];
    }
    
    // Read all lines from the log file
    const logData = fs.readFileSync(ROOT_LOG_FILE_PATH, "utf-8");
    const lines = logData.split("\n").filter(line => line.trim());
    
    return lines;
  } catch (error) {
    console.error("Error reading log file:", error);
    return [];
  }
}

export async function GET() {
  try {
    // Get log configuration
    const config = await loadLogConfig();
    
    // If no log types defined, return empty stats
    if (!config.logTypes || config.logTypes.length === 0) {
      return NextResponse.json({ stats: [] });
    }
    
    // Get all logs (process all logs to ensure accurate stats)
    const logLines = await readLogEntries();
    const logs = parseLogLines(logLines);
    
    // Calculate matches for each log type
    const stats = config.logTypes.map((logType: LogType) => {
      let count = 0;
      
      try {
        const regex = new RegExp(logType.pattern, 'i'); // Case insensitive
        
        // Count logs that match this pattern
        for (const log of logs) {
          if (regex.test(log.message)) {
            count++;
          }
        }
      } catch (error) {
        console.error(`Invalid regex pattern in log type: ${logType.name}`, error);
        // Return 0 for invalid patterns
      }
      
      return {
        logTypeId: logType.id,
        count
      };
    });
    
    return NextResponse.json({ stats });
  } catch (error) {
    console.error('Error calculating log stats:', error);
    return NextResponse.json(
      { error: 'Failed to calculate log statistics' },
      { status: 500 }
    );
  }
} 