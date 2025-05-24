import { readDiscrepanciesFile } from "@/lib/server-utils";
import { ShowSubscription } from "@/lib/utils";
import path from "path";
import fs from "fs";
import { TvIcon, CheckCircle2Icon, NetworkIcon, CalendarIcon } from "lucide-react";

export async function TvShowsSubscribed() {
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
  }
  
  // Read the discrepancies file to get the list of subscribed TV shows
  const tvShows = await readDiscrepanciesFile(discrepanciesFilePath);
  
  console.log(`Subscribed TV Shows file path: ${discrepanciesFilePath}`);
  console.log(`TV shows found: ${tvShows.length}`);
  
  return (
    <div className="glass-card h-full">
      <div className="p-5 border-b border-border/50">
        <div className="flex items-center mb-1">
          <h2 className="text-xl font-semibold flex items-center">
            <TvIcon size={20} className="mr-2 text-primary" />
            Subscribed TV Shows
          </h2>
        </div>
        <p className="text-sm text-muted-foreground">
          Shows you're currently monitoring for new episodes
        </p>
      </div>
      
      {tvShows.length === 0 ? (
        <div className="py-16 text-center text-muted-foreground">
          <p>No TV shows found</p>
          <p className="text-sm mt-1">
            Check if the episode_discrepancies.json file exists and is accessible
          </p>
          <p className="text-xs mt-2">{discrepanciesFilePath}</p>
        </div>
      ) : (
        <div className="max-h-[450px] overflow-y-auto p-4">
          <div className="grid gap-3">
            {tvShows.map((show: ShowSubscription, index: number) => (
              <div
                key={index}
                className="glass-card bg-background/50 flex items-center p-3 hover:bg-primary/5 transition-colors duration-200"
              >
                <div className="h-9 w-9 rounded-full flex items-center justify-center bg-primary/10 mr-3 text-primary">
                  {show.show_title && show.show_title.charAt(0).toUpperCase()}
                </div>
                <div className="flex-1">
                  <p className="font-medium">{show.show_title}</p>
                  <div className="flex text-xs text-muted-foreground mt-1 space-x-3">
                    {show.network && (
                      <span className="flex items-center">
                        <NetworkIcon size={12} className="mr-1" />
                        {show.network}
                      </span>
                    )}
                    <span className="flex items-center">
                      <CalendarIcon size={12} className="mr-1" />
                      Season {show.season}
                    </span>
                  </div>
                </div>
                <CheckCircle2Icon size={18} className="text-success/70" />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
} 