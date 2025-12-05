import { NextRequest, NextResponse } from "next/server";

const FASTAPI_BASE =
  process.env.FASTAPI_BASE_URL || "https://134cf294541c.ngrok-free.app";

export async function GET(req: NextRequest) {
  try {
    // Take the query string (category, etc.) from the incoming request
    const { searchParams } = req.nextUrl;
    const queryString = searchParams.toString();

    // Build the FastAPI URL: http://192.168.1.27:8000/msi?category=...
    const fastApiUrl = `${FASTAPI_BASE}/msi${
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

    const text = await res.text();

    if (!res.ok) {
      // Try to parse error from FastAPI
      let detail: string | undefined;
      try {
        const json = JSON.parse(text);
        detail = json.detail;
      } catch {
        // ignore
      }
      return NextResponse.json(
        {
          success: false,
          detail:
            detail ||
            `The server is currently unavailable. Please try again later.`,
        },
        { status: res.status }
      );
    }

    const data = JSON.parse(text);
    return NextResponse.json(data, { status: 200 });
  } catch (error: any) {
    console.error("Error in /api/msi:", error);
    return NextResponse.json(
      { success: false, detail: "The server is currently unavailable. Please try again later." },
      { status: 500 }
    );
  }
}
