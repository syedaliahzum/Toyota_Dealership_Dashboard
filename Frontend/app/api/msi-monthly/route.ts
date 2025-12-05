import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  try {
    const category = request.nextUrl.searchParams.get("category");
    
    if (!category) {
      return NextResponse.json(
        {
          success: false,
          error: "Missing 'category' query parameter",
          monthly_data: [],
        },
        { status: 400 }
      );
    }

    const backendUrl = process.env.BACKEND_URL || "http://backend:8000";
    
    const response = await fetch(
      `${backendUrl}/msi-monthly?category=${encodeURIComponent(category)}`,
      {
        method: "GET",
        headers: {
          "Accept": "application/json",
        },
        cache: "no-store",
      }
    );

    if (!response.ok) {
      const errorText = await response.text();
      return NextResponse.json(
        {
          success: false,
          error: `Backend returned ${response.status}: ${errorText}`,
          monthly_data: [],
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
        monthly_data: [],
      },
      { status: 500 }
    );
  }
}
