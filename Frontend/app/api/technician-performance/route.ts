// app/api/technician-performance/route.ts
import { NextRequest, NextResponse } from "next/server";

const FASTAPI_BASE =
  process.env.FASTAPI_BASE_URL || "http://backend:8000";

export async function GET(req: NextRequest) {
  try {
    // Take the query string (name, start_date, end_date) from the incoming request
    const { searchParams } = req.nextUrl;
    const queryString = searchParams.toString();

    // Build the FastAPI URL: http://192.168.1.27:8000/technician-performance?...
    const fastApiUrl = `${FASTAPI_BASE}/technician-performance${
      queryString ? `?${queryString}` : ""
    }`;

    const res = await fetch(fastApiUrl, {
      method: "GET",
      headers: {
        accept: "application/json",
      },
      // Avoid caching so you always get fresh data
      cache: "no-store",
    });

    if (!res.ok) {
      const text = await res.text().catch(() => "");
      return NextResponse.json(
        {
          success: false,
          detail:
            text ||
            `Failed to fetch technician performance from FastAPI (status ${res.status})`,
        },
        { status: res.status }
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error("Error in /api/technician-performance:", error);
    return NextResponse.json(
      {
        success: false,
        detail:
          error?.message ||
          "Unexpected error while calling technician-performance",
      },
      { status: 500 }
    );
  }
}
