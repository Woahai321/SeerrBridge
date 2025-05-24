"use client";

import { Suspense, useState, useEffect } from "react";
import Link from "next/link";
import {
  ArrowLeftIcon,
  AlertTriangleIcon,
  ClockIcon,
  InfoIcon
} from "lucide-react";
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

// Interface for error log items
interface ErrorLogItem {
  id: string;
  message: string;
  timestamp: string;
  matchedLogTypeId?: string;
  matchedLogTypeName?: string;
}

export default function ErrorLogsPage() {
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
        <h1 className="text-3xl font-bold">Error Logs</h1>
        <p className="text-muted-foreground mt-2">
          All error messages from the system logs
        </p>
      </div>
      
      <div className="mt-8">
        <Suspense fallback={<div className="glass-card p-8 text-center">Loading error logs...</div>}>
          <ErrorLogsList />
        </Suspense>
      </div>
    </div>
  );
}

function ErrorLogsList() {
  const [errorData, setErrorData] = useState<{
    errors: ErrorLogItem[];
    formattedDates: string[];
    logFilePath: string;
    errorCount: number;
  }>({ errors: [], formattedDates: [], logFilePath: "", errorCount: 0 });
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

        const response = await fetch('/api/logs/errors');
        
        if (!response.ok) {
          throw new Error(`Failed to fetch data: ${response.status}`);
        }
        
        const data = await response.json();
        setErrorData(data);
      } catch (err) {
        console.error("Error fetching logs:", err);
        setError(err instanceof Error ? err.message : "Failed to load error logs");
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, []);

  if (loading) {
    return <div className="glass-card p-8 text-center">Loading error logs...</div>;
  }
  
  if (error) {
    return (
      <div className="glass-card p-8 text-center">
        <p className="text-destructive mb-2">Error loading data</p>
        <p className="text-muted-foreground">{error}</p>
      </div>
    );
  }

  const { errors, formattedDates, logFilePath, errorCount } = errorData;
  
  // Calculate pagination values
  const totalPages = Math.ceil(errors.length / ITEMS_PER_PAGE);
  const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
  const endIndex = startIndex + ITEMS_PER_PAGE;
  const paginatedErrors = errors.slice(startIndex, endIndex);
  const paginatedDates = formattedDates.slice(startIndex, endIndex);
  
  return (
    <div>
      {errors.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <p className="text-xl font-medium mb-2">No error logs found</p>
          <p className="text-muted-foreground">
            Great! Your system is running without errors
          </p>
          <p className="text-xs mt-2">{logFilePath}</p>
        </div>
      ) : (
        <div>
          <div className="glass-card p-5 mb-6">
            <div className="flex items-center">
              <AlertTriangleIcon className="mr-2 text-destructive" size={20} />
              <h3 className="text-lg font-medium">
                Total errors: <span className="text-destructive">{errorCount}</span>
              </h3>
            </div>
          </div>
          
          <div className="space-y-4">
            {paginatedErrors.map((log, index) => {
              // Extract content using log pattern
              const extractedTitle = extractContentFromLog({
                id: log.id,
                title: log.message,
                message: log.message,
                timestamp: log.timestamp,
                logTypeId: log.matchedLogTypeId
              }, logTypes);

              return (
                <div key={startIndex + index} className="glass-card overflow-hidden group hover:shadow-lg transition-all duration-300">
                  <div className="p-5 border-b border-border/50">
                    <div className="flex items-start">
                      <div className="mr-4 mt-1">
                        <AlertTriangleIcon size={24} className="text-destructive" />
                      </div>
                      <div className="flex-1">
                        <h3 className="font-medium mb-2">
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
                    <div className="flex items-center text-sm">
                      <InfoIcon size={14} className="mr-2 text-destructive" />
                      <span className="text-destructive">{log.message}</span>
                    </div>
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
        </div>
      )}
    </div>
  );
} 