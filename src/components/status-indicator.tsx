"use client";

import { useState, useEffect } from "react";
import { CheckCircleIcon, XCircleIcon, ActivityIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface StatusResponse {
  status: string;
  version: string;
  uptime_seconds: number;
  uptime: string;
  start_time: string;
  current_time: string;
  queue_size: number;
  browser_status: string;
  automatic_processing: boolean;
  show_subscription: boolean;
}

export function StatusIndicator() {
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const [showDetails, setShowDetails] = useState(false);

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
      setLastChecked(new Date());
    } catch (err) {
      console.error("Error fetching status:", err);
      setStatus(null);
      setError(err instanceof Error ? err.message : "Unknown error");
      setLastChecked(new Date());
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    // Check immediately on mount
    checkStatus();
    
    // Set up polling every 15 seconds (reduced from 30 for testing)
    const intervalId = setInterval(checkStatus, 15000);
    
    // Clean up interval on unmount
    return () => clearInterval(intervalId);
  }, []);

  // Log status object whenever it changes for debugging
  useEffect(() => {
    if (status) {
      console.log("Status state updated:", JSON.stringify(status, null, 2));
    }
  }, [status]);

  // Format the time since last checked
  const getTimeSinceLastChecked = () => {
    if (!lastChecked) return "never";
    
    const seconds = Math.floor((new Date().getTime() - lastChecked.getTime()) / 1000);
    
    if (seconds < 60) return `${seconds} seconds ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)} minutes ago`;
    return `${Math.floor(seconds / 3600)} hours ago`;
  };

  // Determine if browser is initialized
  const isBrowserInitialized = status?.browser_status === "initialized";

  return (
    <div className="mb-5 px-1">
      <div className="flex items-center justify-between">
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
            
            <span className={cn(
              "ml-2 text-sm font-medium",
              status ? "text-success" : error ? "text-destructive" : "text-muted-foreground"
            )}>
              {status ? "SeerrBridge Running" : "SeerrBridge Offline"}
            </span>
            
            {/* Enhanced tooltip with all status information */}
            {showDetails && (
              <div className="absolute top-full left-0 mt-1 z-50 bg-popover text-popover-foreground p-3 rounded-md border shadow-md max-w-[300px] text-xs">
                {status ? (
                  <div className="space-y-1">
                    <p><span className="font-semibold">Status:</span> {status.status}</p>
                    <p><span className="font-semibold">Version:</span> {status.version}</p>
                    <p><span className="font-semibold">Uptime:</span> {status.uptime}</p>
                    <p><span className="font-semibold">Browser Status:</span> {isBrowserInitialized ? "Initialized" : "Not Initialized"}</p>
                    <p><span className="font-semibold">Queue Size:</span> {status.queue_size}</p>
                    <p><span className="font-semibold">Auto Processing:</span> {status.automatic_processing ? "Enabled" : "Disabled"}</p>
                    <p><span className="font-semibold">Show Subscription:</span> {status.show_subscription ? "Enabled" : "Disabled"}</p>
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
        
        <div className="text-xs text-muted-foreground">
          Last checked: {getTimeSinceLastChecked()}
        </div>
      </div>
    </div>
  );
} 