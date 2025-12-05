import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  try {
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://backend:8000";

    const response = await fetch(`${backendUrl}/top-5-late-cars`, {
      method: "GET",
      cache: "no-store",
    });

    if (!response.ok) {
      const error = await response.text();
      console.error(`Backend error: ${response.status} - ${error}`);
      return NextResponse.json(
        { error: "Failed to fetch top 5 late cars from backend" },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error fetching top 5 late cars:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
