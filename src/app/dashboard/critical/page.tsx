"use client";

import { Suspense, useState, useEffect } from "react";
import { type MediaItem, type LogEntry, formatDate } from "@/lib/utils";
import Link from "next/link";
import {
  ArrowLeftIcon,
  AlertTriangleIcon,
  ClockIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  FilmIcon,
  TvIcon,
  InfoIcon
} from "lucide-react";
import CriticalErrorItem from "@/components/critical-error-item";
import { Pagination } from "@/components/pagination";
import { extractContentFromLog, fetchLogTypes } from "@/lib/log-content-extractor";

// Constants
const ITEMS_PER_PAGE = 25;

// Interface for log types
interface LogType {
  id: string;
  name: string;
  pattern: string;
  description: string;
  level: string;
}

// Extended LogEntry type to include rawLine and matching info
interface ExtendedLogEntry extends LogEntry {
  rawLine?: string;
  matchedLogTypeId?: string;
  matchedLogTypeName?: string;
}

// Interface for critical error items
interface CriticalErrorItem {
  id: string;
  message: string;
  timestamp: string;
  title?: string;
  detailedError?: string;
  matchedLogTypeId?: string;
  matchedLogTypeName?: string;
}

export default function CriticalErrorsPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <Link 
        href="/dashboard" 
        className="flex items-center text-muted-foreground hover:text-foreground mb-6"
      >
        <ArrowLeftIcon size={16} className="mr-2" />
        Back to Dashboard
      </Link>
      
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Critical System Errors</h1>
        <p className="text-muted-foreground mt-2">
          These errors require your attention and may affect system operation
        </p>
      </div>
      
      <div className="mt-8">
        <Suspense fallback={<div className="glass-card p-8 text-center">Loading critical errors...</div>}>
          <CriticalErrorsList />
        </Suspense>
      </div>
    </div>
  );
}

function CriticalErrorsList() {
  const [criticalData, setCriticalData] = useState<{
    criticalErrors: CriticalErrorItem[];
    formattedDates: string[];
    criticalLogs: ExtendedLogEntry[];
    criticalCount: number;
  }>({
    criticalErrors: [],
    formattedDates: [],
    criticalLogs: [],
    criticalCount: 0
  });
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [logTypes, setLogTypes] = useState<LogType[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch log types first
        const types = await fetchLogTypes();
        setLogTypes(types);

        const response = await fetch('/api/logs/critical');
        
        if (!response.ok) {
          throw new Error(`Failed to fetch data: ${response.status}`);
        }
        
        const data = await response.json();
        setCriticalData(data);
      } catch (err) {
        console.error("Error fetching critical errors:", err);
        setError(err instanceof Error ? err.message : "Failed to load critical error data");
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, []);

  if (loading) {
    return <div className="glass-card p-8 text-center">Loading critical errors...</div>;
  }
  
  if (error) {
    return (
      <div className="glass-card p-8 text-center">
        <p className="text-destructive mb-2">Error loading data</p>
        <p className="text-muted-foreground">{error}</p>
      </div>
    );
  }

  const { criticalErrors, formattedDates, criticalCount } = criticalData;
  
  // Calculate pagination values
  const totalPages = Math.ceil(criticalErrors.length / ITEMS_PER_PAGE);
  const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
  const endIndex = startIndex + ITEMS_PER_PAGE;
  const paginatedErrors = criticalErrors.slice(startIndex, endIndex);
  const paginatedDates = formattedDates.slice(startIndex, endIndex);
  
  return (
    <div>
      {criticalErrors.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <p className="text-xl font-medium mb-2">No critical errors found</p>
          <p className="text-muted-foreground">
            Great! Your system is operating without critical failures
          </p>
        </div>
      ) : (
        <>
          <div className="glass-card p-5 mb-6">
            <div className="flex items-center">
              <AlertTriangleIcon className="mr-2 text-destructive" size={20} />
              <h3 className="text-lg font-medium">
                Total critical errors: <span className="text-destructive">{criticalCount}</span>
              </h3>
            </div>
          </div>
          
          <div className="space-y-6">
            {paginatedErrors.map((error, index) => {
              // Extract content using log pattern
              const extractedTitle = extractContentFromLog({
                id: error.id,
                title: error.title || error.message,
                message: error.message,
                timestamp: error.timestamp,
                logTypeId: error.matchedLogTypeId
              }, logTypes);

              return (
                <div key={startIndex + index} className="glass-card overflow-hidden group hover:shadow-lg transition-all duration-300">
                  <div className="p-5 border-b border-border/50">
                    <div className="flex items-start">
                      <div className="mr-4 mt-1">
                        <AlertTriangleIcon size={24} className="text-destructive" />
                      </div>
                      <div className="flex-1">
                        <h3 className="font-medium mb-2 text-destructive">
                          {extractedTitle}
                        </h3>
                        <div className="text-xs text-muted-foreground mt-1 flex items-center">
                          <span className="flex items-center">
                            <ClockIcon size={12} className="mr-1" />
                            {paginatedDates[index]}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="p-4 bg-destructive/5">
                    <div className="text-sm text-destructive mb-2">
                      {error.message}
                    </div>
                    {error.detailedError && error.detailedError !== error.message && (
                      <div className="mt-3 pt-3 border-t border-destructive/20">
                        <details className="text-xs">
                          <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
                            Show detailed error
                          </summary>
                          <pre className="mt-2 text-xs whitespace-pre-wrap font-mono bg-background/50 p-2 rounded">
                            {error.detailedError}
                          </pre>
                        </details>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
          
          <Pagination 
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={setCurrentPage}
          />
        </>
      )}
    </div>
  );
} 