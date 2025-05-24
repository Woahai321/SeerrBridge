import { NextRequest, NextResponse } from "next/server";
import { readDiscrepanciesFile } from "@/lib/server-utils";
import path from "path";
import fs from "fs";

export async function GET(request: NextRequest) {
  try {
    // Define possible locations for the discrepancies file using platform-independent paths
    const APP_ROOT = process.cwd();
    const possiblePaths = [
      path.join(APP_ROOT, "logs", "episode_discrepancies.json"), // In logs directory
      path.join(APP_ROOT, "episode_discrepancies.json"), // Root directory (fallback)
      path.join(APP_ROOT, "data", "episode_discrepancies.json"), // Data directory (fallback)
    ];
    
    let discrepanciesFilePath = "";
    let fileFound = false;
    
    // Try each path until we find the file
    for (const testPath of possiblePaths) {
      try {
        if (fs.existsSync(testPath)) {
          discrepanciesFilePath = testPath;
          fileFound = true;
          console.log(`Found discrepancies file at: ${discrepanciesFilePath}`);
          break;
        }
      } catch (error) {
        console.error(`Error checking path ${testPath}:`, error);
      }
    }
    
    if (!fileFound) {
      console.error("Discrepancies file not found in any of the tested locations");
      return NextResponse.json({ error: "Discrepancies file not found", subscriptions: [] }, { status: 200 });
    }
    
    // Read the discrepancies file
    const subscriptions = await readDiscrepanciesFile(discrepanciesFilePath);
    
    // Sort by those with failed episodes first, then by show title
    const sortedSubscriptions = [...subscriptions].sort((a, b) => {
      // Add null checks for failedEpisodes property
      const aFailedLength = a.failedEpisodes?.length || 0;
      const bFailedLength = b.failedEpisodes?.length || 0;
      
      if (aFailedLength > 0 && bFailedLength === 0) return -1;
      if (aFailedLength === 0 && bFailedLength > 0) return 1;
      return a.show_title.localeCompare(b.show_title);
    });
    
    return NextResponse.json({ subscriptions: sortedSubscriptions });
  } catch (error) {
    console.error("Error fetching TV subscriptions:", error);
    return NextResponse.json({ error: "Failed to fetch TV subscriptions", subscriptions: [] }, { status: 500 });
  }
} 