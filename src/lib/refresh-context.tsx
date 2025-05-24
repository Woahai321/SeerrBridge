"use client";

import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from "react";

interface RefreshContextType {
  lastChecked: Date;
  secondsUntilRefresh: number;
  refreshData: () => void;
  isRefreshing: boolean;
}

const RefreshContext = createContext<RefreshContextType | undefined>(undefined);

// Create a separate component to handle the countdown timer
// This isolates the frequent state updates from the main context
function CountdownManager({ 
  onCountdownComplete 
}: { 
  onCountdownComplete: () => void 
}) {
  const [secondsUntilRefresh, setSecondsUntilRefresh] = useState(30);
  
  // Effect to detect when countdown reaches zero
  useEffect(() => {
    if (secondsUntilRefresh <= 0) {
      // Reset timer
      setSecondsUntilRefresh(30);
      // Call completion callback in a separate effect cycle
      setTimeout(onCountdownComplete, 0);
    }
  }, [secondsUntilRefresh, onCountdownComplete]);

  // Effect for countdown timer
  useEffect(() => {
    const interval = setInterval(() => {
      setSecondsUntilRefresh(prev => prev - 1);
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  return null; // This component doesn't render anything
}

export function RefreshProvider({ children }: { children: React.ReactNode }) {
  // Use a fixed timestamp for initial SSR to avoid hydration mismatches
  const [lastChecked, setLastChecked] = useState<Date>(() => {
    // During SSR or initial client render, use a fixed date
    // This will be immediately replaced with the current time on client after mount
    return new Date(0); // Unix epoch as consistent initial value
  });
  
  // Store the seconds in a ref to avoid re-renders
  const [secondsUntilRefresh, setSecondsUntilRefresh] = useState(30);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Update the timestamp after mount on client-side only
  useEffect(() => {
    setLastChecked(new Date());
  }, []);

  const refreshData = useCallback(() => {
    // Set refreshing state immediately
    setIsRefreshing(true);
    
    // Defer this operation with setTimeout to avoid state updates during render
    setTimeout(() => {
      // Trigger a client-side refresh to update all data
      window.dispatchEvent(new CustomEvent("refresh-dashboard-data"));
      
      // Reset the timer
      setSecondsUntilRefresh(30);
      
      // Keep the refreshing state for a smoother animation
      // This delay ensures the animation has time to complete
      setTimeout(() => {
        // Update the last checked time AFTER the refresh completes
        setLastChecked(new Date());
        setIsRefreshing(false);
      }, 800); // Adjust timing for smoother transition
    }, 0);
  }, []);

  // Handle countdown completion
  const handleCountdownComplete = useCallback(() => {
    refreshData();
  }, [refreshData]);
  
  // Memoize the context value to prevent unnecessary re-renders of consuming components
  const contextValue = useMemo(() => ({
    lastChecked,
    secondsUntilRefresh,
    refreshData,
    isRefreshing
  }), [lastChecked, secondsUntilRefresh, refreshData, isRefreshing]);

  return (
    <RefreshContext.Provider value={contextValue}>
      <CountdownManager onCountdownComplete={handleCountdownComplete} />
      {children}
    </RefreshContext.Provider>
  );
}

export function useRefresh() {
  const context = useContext(RefreshContext);
  if (context === undefined) {
    throw new Error("useRefresh must be used within a RefreshProvider");
  }
  return context;
} 