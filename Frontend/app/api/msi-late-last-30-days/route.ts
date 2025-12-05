import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  try {
    const backendUrl = process.env.BACKEND_URL || "http://backend:8000";
    
    const response = await fetch(`${backendUrl}/msi-late-last-30-days`, {
      method: "GET",
      headers: {
        "Accept": "application/json",
      },
      cache: "no-store",
    });

    if (!response.ok) {
      const errorText = await response.text();
      return NextResponse.json(
        {
          success: false,
          error: `Backend returned ${response.status}: ${errorText}`,
          data: [],
        },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error("API route error:", error);
    return NextResponse.json(
      {
        success: false,
        error: error?.message || "Internal server error",
        data: [],
      },
      { status: 500 }
    );
  }
}
