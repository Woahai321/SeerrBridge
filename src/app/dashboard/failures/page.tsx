"use client";

import { Suspense, useState, useEffect } from "react";
import Link from "next/link";
import {
  ArrowLeftIcon,
  FilmIcon,
  TvIcon,
  ClockIcon,
  AlertTriangleIcon
} from "lucide-react";
import { MediaItem } from "@/lib/utils";
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

export default function FailuresPage() {
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
        <h1 className="text-3xl font-bold">Failed Media Operations</h1>
        <p className="text-muted-foreground mt-2">
          Recent movies and TV shows that failed to process
        </p>
      </div>
      
      <div className="mt-8">
        <Suspense fallback={<div className="glass-card p-8 text-center">Loading media items...</div>}>
          <FailedMediaList />
        </Suspense>
      </div>
    </div>
  );
}

function FailedMediaList() {
  const [failureData, setFailureData] = useState<{
    failures: MediaItem[];
    formattedDates: string[];
    logFilePath: string;
  }>({
    failures: [],
    formattedDates: [],
    logFilePath: ""
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

        const response = await fetch('/api/logs/failures');
        
        if (!response.ok) {
          throw new Error(`Failed to fetch data: ${response.status}`);
        }
        
        const data = await response.json();
        setFailureData(data);
      } catch (err) {
        console.error("Error fetching failure data:", err);
        setError(err instanceof Error ? err.message : "Failed to load failure data");
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, []);

  if (loading) {
    return <div className="glass-card p-8 text-center">Loading media items...</div>;
  }
  
  if (error) {
    return (
      <div className="glass-card p-8 text-center">
        <p className="text-destructive mb-2">Error loading data</p>
        <p className="text-muted-foreground">{error}</p>
      </div>
    );
  }

  const { failures, formattedDates, logFilePath } = failureData;
  
  // Calculate pagination values
  const totalPages = Math.ceil(failures.length / ITEMS_PER_PAGE);
  const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
  const endIndex = startIndex + ITEMS_PER_PAGE;
  const paginatedFailures = failures.slice(startIndex, endIndex);
  const paginatedDates = formattedDates.slice(startIndex, endIndex);
  
  return (
    <div>
      {failures.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <p className="text-xl font-medium mb-2">No failed media operations found</p>
          <p className="text-muted-foreground">
            Great! Everything seems to be working properly
          </p>
          <p className="text-xs mt-2">{logFilePath}</p>
        </div>
      ) : (
        <>
          <div className="glass-card p-5 mb-6">
            <div className="flex items-center">
              <AlertTriangleIcon className="mr-2 text-destructive" size={20} />
              <h3 className="text-lg font-medium">
                Total failures: <span className="text-destructive">{failures.length}</span>
              </h3>
            </div>
          </div>
        
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {paginatedFailures.map((media: MediaItem, index: number) => {
              // Extract content using log pattern
              const extractedTitle = extractContentFromLog({
                id: media.id || `failure-${index}`,
                title: media.details?.message || media.message || media.title,
                message: media.details?.message || media.message || media.title,
                timestamp: media.timestamp || '',
                logTypeId: media.matchedLogTypeId || media.logTypeId
              }, logTypes);

              return (
                <div key={startIndex + index} className="glass-card overflow-hidden group hover:shadow-lg transition-all duration-300">
                  <div className="p-5 border-b border-border/50 flex items-start">
                    <div className="mr-4 mt-1">
                      {media.type === "movie" ? (
                        <FilmIcon size={24} className="text-destructive" />
                      ) : (
                        <TvIcon size={24} className="text-destructive" />
                      )}
                    </div>
                    <div>
                      <h3 className="font-medium">
                        {extractedTitle}
                      </h3>
                      <div className="text-xs text-muted-foreground mt-1 flex items-center">
                        {media.type === "tv" && media.season !== undefined && (
                          <span className="mr-3">
                            Season {media.season} {media.episode}
                          </span>
                        )}
                        <span className="flex items-center">
                          <ClockIcon size={12} className="mr-1" />
                          {paginatedDates[index]}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="p-4 bg-destructive/5 min-h-[100%] flex items-start">
                    <div className="flex items-start text-sm gap-2 w-full">
                      <AlertTriangleIcon size={14} className="text-destructive flex-shrink-0 mt-0.5" />
                      <div className="text-destructive break-words overflow-wrap-anywhere leading-relaxed min-w-0 flex-1">
                        {media.details?.message || media.message || media.title}
                      </div>
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
        </>
      )}
    </div>
  );
} 