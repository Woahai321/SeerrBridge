"use client";

import { useState, useEffect, useRef } from "react";
import { CheckCircleIcon, XCircleIcon, ActivityIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { useRefresh } from "@/lib/refresh-context";

interface StatusResponse {
  status: string;
  version: string;
  uptime_seconds: number;
  uptime: string;
  start_time: string;
  current_time: string;
  queue_status: {
    movie_queue_size: number;
    movie_queue_max: number;
    tv_queue_size: number;
    tv_queue_max: number;
    is_processing: boolean;
    total_queued: number;
  };
  browser_status: string;
  automatic_processing: boolean;
  show_subscription: boolean;
  refresh_interval_minutes: number;
  library_stats?: {
    torrents_count: number;
    total_size_tb: number;
    last_updated: string | null;
  };
}

export function StatusIndicator() {
  const { lastChecked } = useRefresh();
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showDetails, setShowDetails] = useState(false);
  const [secondsSinceCheck, setSecondsSinceCheck] = useState(0);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const checkStatus = async () => {
    try {
      console.log("Fetching status data...");
      
      const response = await fetch("/api/bridge-status", {
        method: "GET",
        headers: {
          "Cache-Control": "no-cache, no-store, must-revalidate",
          Pragma: "no-cache",
          Expires: "0",
        },
        // Force fetch by adding a timestamp
        cache: "no-store"
      });
      
      if (!response.ok) {
        throw new Error(`Failed to fetch status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log("Received status data:", JSON.stringify(data, null, 2));
      setStatus(data);
      setError(null);
    } catch (err) {
      console.error("Error fetching status:", err);
      setStatus(null);
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    // Check immediately on mount
    checkStatus();
    
    // Set up polling every 15 seconds (reduced from 30 for testing)
    const intervalId = setInterval(checkStatus, 15000);
    
    // Listen for manual refresh events from the refresh button
    const handleRefresh = () => {
      checkStatus();
    };
    
    window.addEventListener('refresh-dashboard-data', handleRefresh);
    
    // Clean up on unmount
    return () => {
      clearInterval(intervalId);
      window.removeEventListener('refresh-dashboard-data', handleRefresh);
    };
  }, []);

  // Update the seconds since last check every second
  useEffect(() => {
    // Calculate and update the time difference initially
    const updateTimeDiff = () => {
      const seconds = Math.floor((new Date().getTime() - lastChecked.getTime()) / 1000);
      setSecondsSinceCheck(seconds);
    };
    
    // Update immediately
    updateTimeDiff();
    
    // Set up a timer to update every second
    timerRef.current = setInterval(updateTimeDiff, 1000);
    
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [lastChecked]);

  // Log status object whenever it changes for debugging
  useEffect(() => {
    if (status) {
      console.log("Status state updated:", JSON.stringify(status, null, 2));
    }
  }, [status]);

  // Determine if browser is initialized
  const isBrowserInitialized = status?.browser_status === "initialized";

  return (
    <div className="mb-5 px-1">
      <div className="flex items-center">
        <div className="relative">
          <div 
            className="flex items-center cursor-pointer" 
            onMouseEnter={() => setShowDetails(true)}
            onMouseLeave={() => setShowDetails(false)}
          >
            {isLoading ? (
              <ActivityIcon className="h-5 w-5 text-muted-foreground animate-pulse" />
            ) : status ? (
              <CheckCircleIcon className="h-5 w-5 text-success animate-pulse" />
            ) : (
              <XCircleIcon className="h-5 w-5 text-destructive animate-pulse" />
            )}
            
            <div className="ml-2">
              <span className={cn(
                "text-sm font-medium",
                status ? "text-success" : error ? "text-destructive" : "text-muted-foreground"
              )}>
                {status ? "SeerrBridge Running" : "SeerrBridge Offline"}
              </span>
              
              {status && status.library_stats && (
                <div className="text-xs text-muted-foreground">
                  Library: {status.library_stats.torrents_count.toLocaleString()} torrents • {status.library_stats.total_size_tb} TB
                </div>
              )}
              
              {status && (
                <div className="text-xs text-muted-foreground">
                  Currently Processing {status.queue_status.total_queued} {status.queue_status.total_queued === 1 ? 'Item' : 'Items'}
                </div>
              )}
            </div>
            
            {/* Enhanced tooltip with all status information */}
            {showDetails && (
              <div className="absolute top-full left-0 mt-1 z-50 bg-popover text-popover-foreground p-3 rounded-md border shadow-md max-w-[300px] text-xs">
                {status ? (
                  <div className="space-y-1">
                    <p><span className="font-semibold">Status:</span> {status.status}</p>
                    <p><span className="font-semibold">Version:</span> {status.version}</p>
                    <p><span className="font-semibold">Uptime:</span> {status.uptime}</p>
                    <p><span className="font-semibold">Browser Status:</span> {isBrowserInitialized ? "Initialized" : "Not Initialized"}</p>
                    <p><span className="font-semibold">Total Queued:</span> {status.queue_status.total_queued}</p>
                    <p><span className="font-semibold">Movie Queue:</span> {status.queue_status.movie_queue_size}/{status.queue_status.movie_queue_max}</p>
                    <p><span className="font-semibold">TV Queue:</span> {status.queue_status.tv_queue_size}/{status.queue_status.tv_queue_max}</p>
                    <p><span className="font-semibold">Processing Status:</span> {status.queue_status.is_processing ? "Active" : "Idle"}</p>
                    {status.library_stats && (
                      <>
                        <p><span className="font-semibold">Library Torrents:</span> {status.library_stats.torrents_count.toLocaleString()}</p>
                        <p><span className="font-semibold">Total Size:</span> {status.library_stats.total_size_tb} TB</p>
                        {status.library_stats.last_updated && (
                          <p><span className="font-semibold">Stats Updated:</span> {new Date(status.library_stats.last_updated).toLocaleString()}</p>
                        )}
                      </>
                    )}
                    <p><span className="font-semibold">Auto Processing:</span> {status.automatic_processing ? "Enabled" : "Disabled"}</p>
                    <p><span className="font-semibold">Show Subscription:</span> {status.show_subscription ? "Enabled" : "Disabled"}</p>
                    <p><span className="font-semibold">Refresh Interval:</span> {status.refresh_interval_minutes} minutes</p>
                    <p><span className="font-semibold">Start Time:</span> {new Date(status.start_time).toLocaleString()}</p>
                    <p><span className="font-semibold">Current Time:</span> {new Date(status.current_time).toLocaleString()}</p>
                  </div>
                ) : (
                  <div>
                    <p>Unable to connect to SeerrBridge</p>
                    {error && <p className="text-destructive">{error}</p>}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}