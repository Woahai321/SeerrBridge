import { NextResponse } from "next/server";

// This is the URL where your SeerrBridge is running
const SEERRBRIDGE_URL = process.env.SEERRBRIDGE_URL || "http://localhost:8777";

export const dynamic = 'force-dynamic'; // Ensure this route is not cached

export async function GET() {
  try {
    // Add timestamp to prevent caching
    const timestamp = Date.now();
    const url = `${SEERRBRIDGE_URL}/status?_=${timestamp}`;
    console.log("Fetching SeerrBridge status from", url);
    
    const response = await fetch(url, {
      method: "GET",
      headers: {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        Pragma: "no-cache",
        Expires: "0",
      },
      cache: "no-store",
      next: { revalidate: 0 }
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch status: ${response.status}`);
    }

    const data = await response.json();
    console.log("Received SeerrBridge status data:", JSON.stringify(data, null, 2));
    
    return NextResponse.json(data, {
      headers: {
        'Cache-Control': 'no-store, max-age=0',
        'Pragma': 'no-cache'
      }
    });
  } catch (error) {
    console.error("Error fetching SeerrBridge status:", error);
    return NextResponse.json(
      { error: "Failed to connect to SeerrBridge" },
      { 
        status: 500,
        headers: {
          'Cache-Control': 'no-store, max-age=0',
          'Pragma': 'no-cache'
        }
      }
    );
  }
} 