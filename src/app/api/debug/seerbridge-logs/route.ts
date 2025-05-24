import { NextRequest, NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { NotificationType } from "@/lib/notifications";
import { readNotificationSettingsFromFile, sendDiscordWebhook } from "@/lib/server-notifications";

// Enhanced regex patterns with better flexibility
const LOG_PATTERNS = {
  seerbridge_success: /(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})\s+\|\s+(?:SUCCESS|Success|success)\s+\|\s+(.*?)\s+-\s+(.*)/i,
  seerbridge_error: /(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})\s+\|\s+(?:ERROR|Error|error)\s+\|\s+(.*?)\s+-\s+(.*)/i,
  seerbridge_warning: /(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})\s+\|\s+(?:WARNING|Warning|warning)\s+\|\s+(.*?)\s+-\s+(.*)/i
};

type ScanResult = 
  | { matched: true; type: string; timestamp: string; module: string; message: string } 
  | { matched: false; line: string };

function scanLine(line: string): ScanResult {
  for (const [type, pattern] of Object.entries(LOG_PATTERNS)) {
    const match = line.match(pattern);
    if (match) {
      return {
        matched: true,
        type,
        timestamp: match[1],
        module: match[2],
        message: match[3]
      };
    }
  }
  return { matched: false, line: line.substring(0, 100) };
}

export async function GET(request: NextRequest) {
  try {
    const appRoot = process.cwd();
    const logsDir = path.join(appRoot, 'logs');
    const logFilePath = path.join(logsDir, 'seerrbridge.log');
    
    // Check if directory and file exist
    const results = {
      directory: {
        path: logsDir,
        exists: fs.existsSync(logsDir),
        files: [] as string[]
      },
      file: {
        path: logFilePath,
        exists: fs.existsSync(logFilePath),
        size: 0,
        lineCount: 0,
        sampleLines: [] as string[],
        lastModified: null as Date | null
      },
      scan: {
        success: 0,
        error: 0,
        warning: 0,
        unmatched: 0,
        samples: {
          success: null as any,
          error: null as any,
          warning: null as any,
          unmatched: [] as string[]
        }
      },
      test: {
        processingEnabled: false,
        sendEnabled: false,
        sent: [] as string[],
        errors: [] as string[]
      },
      config: await readNotificationSettingsFromFile()
    };
    
    // Get directory details
    if (results.directory.exists) {
      results.directory.files = fs.readdirSync(logsDir);
    }
    
    // Get file details
    if (results.file.exists) {
      const stats = fs.statSync(logFilePath);
      results.file.size = stats.size;
      results.file.lastModified = stats.mtime;
      
      // Read file contents (limit to last 100 lines for performance)
      const content = fs.readFileSync(logFilePath, 'utf8');
      const lines = content.split('\n').filter(line => line.trim().length > 0);
      results.file.lineCount = lines.length;
      
      // Get sample lines (last 10)
      results.file.sampleLines = lines.slice(-10).map(line => line.substring(0, 200));
      
      // Scan for log patterns
      const shouldProcess = request.nextUrl.searchParams.has('process');
      const shouldSend = request.nextUrl.searchParams.has('send');
      
      results.test.processingEnabled = shouldProcess;
      results.test.sendEnabled = shouldSend;
      
      // If processing is requested, scan more lines (last 50)
      const processLines = shouldProcess ? lines.slice(-50) : lines.slice(-10);
      
      for (const line of processLines) {
        const scanResult = scanLine(line);
        
        if (scanResult.matched) {
          const notificationType = scanResult.type.includes('success') ? 'success' :
                                  scanResult.type.includes('error') ? 'error' : 'warning';
                                  
          results.scan[notificationType as keyof typeof results.scan]++;
          
          // Save first sample of each type
          if (!results.scan.samples[notificationType as keyof typeof results.scan.samples]) {
            results.scan.samples[notificationType as keyof typeof results.scan.samples] = scanResult;
          }
          
          // If send is requested, send notification
          if (shouldSend) {
            try {
              const success = await sendDiscordWebhook(
                results.config.discord_webhook_url,
                notificationType as NotificationType,
                scanResult.module,
                scanResult.message,
                { timestamp: scanResult.timestamp }
              );
              
              if (success) {
                results.test.sent.push(`${notificationType}: ${scanResult.module}`);
              } else {
                results.test.errors.push(`Failed to send ${notificationType}: ${scanResult.module}`);
              }
            } catch (error) {
              results.test.errors.push(`Error sending ${notificationType}: ${error instanceof Error ? error.message : String(error)}`);
            }
          }
        } else {
          results.scan.unmatched++;
          if (results.scan.samples.unmatched.length < 5) {
            results.scan.samples.unmatched.push(scanResult.line);
          }
        }
      }
    }
    
    return NextResponse.json(results);
  } catch (error) {
    console.error("Error in SeerrBridge logs debug endpoint:", error);
    
    return NextResponse.json(
      { 
        error: error instanceof Error ? error.message : "Unknown error occurred" 
      },
      { status: 500 }
    );
  }
} 