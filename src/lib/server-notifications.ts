import fs from "fs";
import path from "path";
import { NotificationSettings, NotificationType, NotificationHistoryItem } from "./notifications";

// Default notification settings
export const DEFAULT_SETTINGS: NotificationSettings = {
  discord_webhook_url: "",
  notify_on_success: false,
  notify_on_error: true,
  notify_on_warning: false,
  show_debug_widget: false,
};

// Add rate limiting for Discord requests
let lastDiscordWebhookTime = 0;
const DISCORD_RATE_LIMIT_MS = 500; // Minimum 500ms between requests

/**
 * Get the notifications config file path
 * This is a server-side only function
 */
export function getConfigFilePath() {
  return path.join(process.cwd(), "logs", "notifications.json");
}

/**
 * Get the notification history file path
 */
export function getNotificationHistoryFilePath() {
  return path.join(process.cwd(), "logs", "notification-history.json");
}

/**
 * Read notification settings from the file system
 * This is a server-side only function
 */
export async function readNotificationSettingsFromFile(): Promise<NotificationSettings> {
  const configFilePath = getConfigFilePath();
  
  try {
    if (!fs.existsSync(configFilePath)) {
      // Create default settings file if it doesn't exist
      await fs.promises.writeFile(
        configFilePath,
        JSON.stringify(DEFAULT_SETTINGS, null, 2),
        "utf8"
      );
      return DEFAULT_SETTINGS;
    }
    
    const content = await fs.promises.readFile(configFilePath, "utf8");
    return JSON.parse(content);
  } catch (error) {
    console.error("Error reading notification settings:", error);
    return { ...DEFAULT_SETTINGS };
  }
}

/**
 * Write notification settings to file
 * This is a server-side only function
 */
export async function writeNotificationSettings(settings: Partial<NotificationSettings>): Promise<boolean> {
  const configFilePath = getConfigFilePath();
  
  try {
    // Read existing settings first
    const existingSettings = await readNotificationSettingsFromFile();
    
    // Merge with new settings
    const updatedSettings = {
      ...existingSettings,
      ...settings
    };
    
    // Write the updated settings
    await fs.promises.writeFile(
      configFilePath,
      JSON.stringify(updatedSettings, null, 2),
      "utf8"
    );
    
    return true;
  } catch (error) {
    console.error("Error writing notification settings:", error);
    return false;
  }
}

/**
 * Read notification history from file
 */
export async function readNotificationHistoryFromFile(): Promise<NotificationHistoryItem[]> {
  const historyFilePath = getNotificationHistoryFilePath();
  
  try {
    // Create file if it doesn't exist
    if (!fs.existsSync(historyFilePath)) {
      await fs.promises.writeFile(
        historyFilePath,
        JSON.stringify([]),
        "utf8"
      );
      return [];
    }
    
    const content = await fs.promises.readFile(historyFilePath, "utf8");
    return JSON.parse(content);
  } catch (error) {
    console.error("Error reading notification history:", error);
    return [];
  }
}

/**
 * Mark notifications as viewed in the history file
 * Returns the number of unviewed notifications remaining
 */
export async function markNotificationsAsViewed(viewTimestamp: string): Promise<number> {
  try {
    const historyFilePath = getNotificationHistoryFilePath();
    
    // Read existing history
    let history = await readNotificationHistoryFromFile();
    
    // Update all notifications before viewTimestamp to viewed
    history = history.map(item => {
      const itemTime = new Date(item.timestamp);
      const viewTime = new Date(viewTimestamp);
      
      // If notification is older than or equal to the view timestamp and not already viewed
      if (itemTime <= viewTime && !item.viewed) {
        return { ...item, viewed: true };
      }
      
      return item;
    });
    
    // Count remaining unviewed notifications
    const unviewedCount = history.filter(item => !item.viewed).length;
    
    // Write updated history back to file
    await fs.promises.writeFile(
      historyFilePath,
      JSON.stringify(history, null, 2),
      "utf8"
    );
    
    return unviewedCount;
  } catch (error) {
    console.error("Error marking notifications as viewed:", error);
    return 0;
  }
}

/**
 * Count the number of unviewed notifications
 */
export async function countUnviewedNotifications(): Promise<number> {
  try {
    const history = await readNotificationHistoryFromFile();
    return history.filter(item => !item.viewed).length;
  } catch (error) {
    console.error("Error counting unviewed notifications:", error);
    return 0;
  }
}

/**
 * Add notification to history file
 */
export async function addNotificationToHistoryFile(notification: NotificationHistoryItem): Promise<boolean> {
  try {
    const historyFilePath = getNotificationHistoryFilePath();
    
    // Read existing history
    let history = await readNotificationHistoryFromFile();
    
    // Add new notification at the beginning (newest first) with viewed set to false
    const notificationWithViewed = {
      ...notification,
      viewed: false
    };
    
    history.unshift(notificationWithViewed);
    
    // Filter out notifications older than 24 hours
    const oneDayAgo = new Date();
    oneDayAgo.setHours(oneDayAgo.getHours() - 24);
    
    history = history.filter(item => {
      const timestamp = new Date(item.timestamp);
      return timestamp >= oneDayAgo;
    });
    
    // Write updated history back to file
    await fs.promises.writeFile(
      historyFilePath,
      JSON.stringify(history, null, 2),
      "utf8"
    );
    
    return true;
  } catch (error) {
    console.error("Error adding notification to history file:", error);
    return false;
  }
}

/**
 * Prune notification history to only keep notifications from the past 24 hours
 */
export async function pruneNotificationHistoryFile(): Promise<number> {
  try {
    const historyFilePath = getNotificationHistoryFilePath();
    
    // Read existing history
    let history = await readNotificationHistoryFromFile();
    
    // Filter out notifications older than 24 hours
    const oneDayAgo = new Date();
    oneDayAgo.setHours(oneDayAgo.getHours() - 24);
    
    const originalLength = history.length;
    
    history = history.filter(item => {
      const timestamp = new Date(item.timestamp);
      return timestamp >= oneDayAgo;
    });
    
    console.log(`Pruned notification history: removed ${originalLength - history.length} old notifications`);
    
    // Write updated history back to file
    await fs.promises.writeFile(
      historyFilePath,
      JSON.stringify(history, null, 2),
      "utf8"
    );
    
    return history.length;
  } catch (error) {
    console.error("Error pruning notification history file:", error);
    return 0;
  }
}

/**
 * Send a webhook to Discord
 * Includes rate limiting to prevent 429 errors
 */
export async function sendDiscordWebhook(
  webhookUrl: string,
  type: NotificationType,
  title: string,
  message: string,
  details?: Record<string, string>
): Promise<boolean> {
  try {
    // Apply rate limiting
    const now = Date.now();
    const timeSinceLastRequest = now - lastDiscordWebhookTime;
    
    if (timeSinceLastRequest < DISCORD_RATE_LIMIT_MS) {
      const waitTime = DISCORD_RATE_LIMIT_MS - timeSinceLastRequest;
      console.log(`[Discord] Rate limiting - waiting ${waitTime}ms before sending next webhook`);
      await new Promise(resolve => setTimeout(resolve, waitTime));
    }
    
    // Validate webhook URL
    if (!webhookUrl || !webhookUrl.startsWith("https://discord.com/api/webhooks/")) {
      console.error("Invalid Discord webhook URL");
      return false;
    }
    
    // Set up colors and emoji based on notification type
    let color: number;
    let emoji: string;
    
    switch (type) {
      case "success":
        color = 5763719; // Green
        emoji = "✅";
        break;
      case "error":
        color = 15548997; // Red
        emoji = "❌";
        break;
      case "warning":
        color = 16776960; // Yellow
        emoji = "⚠️";
        break;
      default:
        color = 3447003; // Blue
        emoji = "🔔";
    }
    
    // Create fields from details if provided
    const fields = details ? 
      Object.entries(details).map(([name, value]) => ({
        name,
        value: String(value),
        inline: true,
      })) : [];
    
    // Add timestamp field if not already present
    if (!details?.timestamp) {
      fields.push({
        name: "Timestamp",
        value: new Date().toISOString(),
        inline: true,
      });
    }
    
    // Create the webhook payload
    const payload = {
      embeds: [{
        title: `${emoji} ${title}`,
        description: message,
        color,
        fields,
        footer: {
          text: "BridgeBoard Notification System",
        },
      }],
    };
    
    // Send the webhook with proper error handling
    const response = await fetch(webhookUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    
    // Update last request time
    lastDiscordWebhookTime = Date.now();
    
    if (response.ok) {
      console.log(`Successfully sent Discord webhook notification: ${type} - ${title}`);
      return true;
    } else {
      const responseText = await response.text();
      console.error(`Failed to send Discord webhook: ${response.status} ${response.statusText}`);
      console.error(`Response body: ${responseText}`);
      
      // If rate limited, wait the retry_after time and try again
      if (response.status === 429) {
        try {
          const errorData = JSON.parse(responseText);
          if (errorData.retry_after) {
            const retryAfterMs = errorData.retry_after * 1000;
            console.log(`[Discord] Rate limited, retrying after ${retryAfterMs}ms`);
            await new Promise(resolve => setTimeout(resolve, retryAfterMs + 100)); // Add 100ms buffer
            
            // Try again recursively
            return sendDiscordWebhook(webhookUrl, type, title, message, details);
          }
        } catch (parseError) {
          console.error(`Error parsing rate limit response:`, parseError);
        }
      }
      
      return false;
    }
  } catch (error) {
    console.error('Error sending Discord webhook:', error);
    return false;
  }
} 