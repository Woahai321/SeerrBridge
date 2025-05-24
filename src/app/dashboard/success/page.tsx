"use client";

import { Suspense, useState, useEffect } from "react";
import Link from "next/link";
import {
  ArrowLeftIcon,
  FilmIcon,
  TvIcon,
  ClockIcon,
  CheckCircle2Icon
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

export default function SuccessPage() {
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
        <h1 className="text-3xl font-bold">Successful Media Operations</h1>
        <p className="text-muted-foreground mt-2">
          Recently processed movies and TV shows
        </p>
      </div>
      
      <div className="mt-8">
        <Suspense fallback={<div className="glass-card p-8 text-center">Loading media items...</div>}>
          <SuccessfulMediaList />
        </Suspense>
      </div>
    </div>
  );
}

function SuccessfulMediaList() {
  const [successData, setSuccessData] = useState<{
    recentSuccesses: MediaItem[];
    formattedDates: string[];
    logFilePath: string;
    successfulGrabs: number;
  }>({
    recentSuccesses: [],
    formattedDates: [],
    logFilePath: "",
    successfulGrabs: 0
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

        const response = await fetch('/api/logs/success');
        
        if (!response.ok) {
          throw new Error(`Failed to fetch data: ${response.status}`);
        }
        
        const data = await response.json();
        setSuccessData(data);
      } catch (err) {
        console.error("Error fetching success data:", err);
        setError(err instanceof Error ? err.message : "Failed to load success data");
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

  const { recentSuccesses, formattedDates, logFilePath, successfulGrabs } = successData;
  
  // Calculate pagination values
  const totalPages = Math.ceil(recentSuccesses.length / ITEMS_PER_PAGE);
  const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
  const endIndex = startIndex + ITEMS_PER_PAGE;
  const paginatedSuccesses = recentSuccesses.slice(startIndex, endIndex);
  const paginatedDates = formattedDates.slice(startIndex, endIndex);
  
  return (
    <div>
      {recentSuccesses.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <p className="text-xl font-medium mb-2">No successful media operations found</p>
          <p className="text-muted-foreground">
            Check your log file or try processing some media
          </p>
          <p className="text-xs mt-2">{logFilePath}</p>
        </div>
      ) : (
        <>
          <div className="glass-card p-5 mb-6">
            <div className="flex items-center">
              <CheckCircle2Icon className="mr-2 text-success" size={20} />
              <h3 className="text-lg font-medium">
                Total successful operations: <span className="text-success">{successfulGrabs}</span>
              </h3>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {paginatedSuccesses.map((media: MediaItem, index: number) => {
              // Extract content using log pattern
              const extractedTitle = extractContentFromLog({
                id: media.id || `success-${index}`,
                title: media.title,
                message: media.details?.message || media.message || media.title,
                timestamp: media.timestamp || '',
                logTypeId: media.matchedLogTypeId || media.logTypeId
              }, logTypes);

              return (
                <div key={startIndex + index} className="glass-card overflow-hidden group hover:shadow-lg transition-all duration-300">
                  <div className="p-5 border-b border-border/50 flex items-start">
                    <div className="mr-4 mt-1">
                      {media.type === "movie" ? (
                        <FilmIcon size={24} className="text-success" />
                      ) : (
                        <TvIcon size={24} className="text-success" />
                      )}
                    </div>
                    <div>
                      <h3 className="font-medium">
                        {extractedTitle}
                      </h3>
                      <div className="text-xs text-muted-foreground mt-1 flex items-center">
                        {media.type === "tv" && media.details?.season && (
                          <span className="mr-3">
                            Season {media.details.season} {media.details.episode && `Episode ${media.details.episode}`}
                          </span>
                        )}
                        <span className="flex items-center">
                          <ClockIcon size={12} className="mr-1" />
                          {paginatedDates[index]}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="p-4 bg-success/5">
                    <div className="flex items-center text-sm">
                      <CheckCircle2Icon size={14} className="mr-2 text-success" />
                      <span className="text-success">{media.details?.message || media.message || "Successfully processed"}</span>
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