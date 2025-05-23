import { NextRequest, NextResponse } from "next/server";
import { readNotificationHistoryFromFile } from "@/lib/server-notifications";

/**
 * GET handler for debugging notification history
 * This endpoint returns all notifications currently in the history file
 * along with additional debug information
 */
export async function GET(request: NextRequest) {
  try {
    const history = await readNotificationHistoryFromFile();
    
    // Create some test notifications if none exist
    // This is just for testing and debugging
    if (history.length === 0) {
      return NextResponse.json({
        history,
        message: "No notifications found in history",
        count: 0,
        note: "You may need to send a test notification first"
      });
    }
    
    return NextResponse.json({
      history,
      count: history.length,
      oldestTimestamp: history.length > 0 ? history[history.length - 1].timestamp : null,
      newestTimestamp: history.length > 0 ? history[0].timestamp : null,
      types: history.reduce((acc, item) => {
        acc[item.type] = (acc[item.type] || 0) + 1;
        return acc;
      }, {} as Record<string, number>),
      historyFilePath: process.env.NODE_ENV === 'development' ? 
        'logs/notification-history.json' : 
        '(file path hidden in production)'
    });
  } catch (error) {
    console.error("Error retrieving debug notification history:", error);
    
    return NextResponse.json(
      { error: "Failed to retrieve notification history debug information" },
      { status: 500 }
    );
  }
} 