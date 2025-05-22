import { NextRequest, NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { NotificationType } from "@/lib/notifications";
import { readNotificationSettingsFromFile, sendDiscordWebhook } from "@/lib/server-notifications";

// Regular expressions to match log patterns in SeerrBridge format
const SEERR_LOG_PATTERNS = {
  success: /(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})\s+\|\s+SUCCESS\s+\|\s+(.*?)\s+-\s+(.*)/i,
  error: /(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})\s+\|\s+ERROR\s+\|\s+(.*?)\s+-\s+(.*)/i,
  warning: /(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})\s+\|\s+WARNING\s+\|\s+(.*?)\s+-\s+(.*)/i,
  info: /(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})\s+\|\s+INFO\s+\|\s+(.*?)\s+-\s+(.*)/i
};

// Fallback for standard log format
const STANDARD_LOG_PATTERNS = {
  success: /\[(.+?)\]\s+✅\s+(.*?):\s+(.*)/,
  error: /\[(.+?)\]\s+❌\s+(.*?):\s+(.*)/,
  warning: /\[(.+?)\]\s+⚠️\s+(.*?):\s+(.*)/
};

export async function GET(request: NextRequest) {
  try {
    const appRoot = process.cwd();
    const logsDir = path.join(appRoot, 'logs');
    const seerrbridgeLogPath = path.join(logsDir, 'seerrbridge.log');
    
    // Check if the file exists
    if (!fs.existsSync(seerrbridgeLogPath)) {
      return NextResponse.json({
        error: "seerrbridge.log file not found",
        logDir: logsDir,
        files: fs.existsSync(logsDir) ? fs.readdirSync(logsDir) : []
      }, { status: 404 });
    }
    
    // Read the log file
    const content = await fs.promises.readFile(seerrbridgeLogPath, 'utf8');
    const lines = content.split('\n').filter(line => line.trim().length > 0);
    
    // Process log lines
    const results = {
      totalLines: lines.length,
      processed: 0,
      matches: {
        success: 0,
        error: 0,
        warning: 0,
        info: 0
      },
      notifications: {
        sent: 0,
        failed: 0,
        skipped: 0
      },
      samples: {
        success: null as string | null,
        error: null as string | null,
        warning: null as string | null,
        info: null as string | null,
        unmatched: [] as string[]
      }
    };
    
    // Get notification settings
    const settings = await readNotificationSettingsFromFile();
    const notificationsEnabled = settings.discord_webhook_url && 
                     (settings.notify_on_success || 
                      settings.notify_on_error || 
                      settings.notify_on_warning);
    
    // Process each line
    for (const line of lines) {
      results.processed++;
      let matched = false;
      
      // Try SeerrBridge format first
      for (const [typeKey, pattern] of Object.entries(SEERR_LOG_PATTERNS)) {
        const match = line.match(pattern);
        if (match) {
          matched = true;
          const type = typeKey as "success" | "error" | "warning" | "info";
          results.matches[type]++;
          
          // Store sample if not already collected
          if (!results.samples[type]) {
            results.samples[type] = line.substring(0, 200);
          }
          
          // Skip info logs for notifications
          if (type === 'info') {
            results.notifications.skipped++;
            continue;
          }
          
          // Send notification if enabled
          const timestamp = match[1];
          const title = match[2];
          const message = match[3];
          
          // Check if this notification type is enabled
          let isEnabled = false;
          if (type === 'success') {
            isEnabled = settings.notify_on_success;
          } else if (type === 'error') {
            isEnabled = settings.notify_on_error;
          } else if (type === 'warning') {
            isEnabled = settings.notify_on_warning;
          }
          
          if (notificationsEnabled && isEnabled) {
            try {
              // Send notification (only if 'send' param is true)
              if (request.nextUrl.searchParams.has('send')) {
                const success = await sendDiscordWebhook(
                  settings.discord_webhook_url,
                  type as NotificationType,
                  title,
                  message,
                  { timestamp }
                );
                
                if (success) {
                  results.notifications.sent++;
                } else {
                  results.notifications.failed++;
                }
              } else {
                // Just count it as skipped for dry run
                results.notifications.skipped++;
              }
            } catch (error) {
              results.notifications.failed++;
            }
          } else {
            results.notifications.skipped++;
          }
          
          break;
        }
      }
      
      // Fallback to standard format
      if (!matched) {
        for (const [typeKey, pattern] of Object.entries(STANDARD_LOG_PATTERNS)) {
          const match = line.match(pattern);
          if (match) {
            matched = true;
            const type = typeKey as "success" | "error" | "warning" | "info";
            results.matches[type]++;
            
            // Store sample if not already collected
            if (!results.samples[type]) {
              results.samples[type] = line.substring(0, 200);
            }
            break;
          }
        }
      }
      
      // Add unmatched line samples (up to 5)
      if (!matched && results.samples.unmatched.length < 5) {
        results.samples.unmatched.push(line.substring(0, 200));
      }
    }
    
    return NextResponse.json({
      file: seerrbridgeLogPath,
      fileSize: content.length,
      settings: {
        discord_webhook_url: settings.discord_webhook_url ? "configured" : "missing",
        notify_on_success: settings.notify_on_success,
        notify_on_error: settings.notify_on_error,
        notify_on_warning: settings.notify_on_warning
      },
      results
    });
  } catch (error) {
    console.error("Error in SeerrBridge log debug endpoint:", error);
    
    return NextResponse.json(
      { 
        error: error instanceof Error ? error.message : "Unknown error occurred" 
      },
      { status: 500 }
    );
  }
} 