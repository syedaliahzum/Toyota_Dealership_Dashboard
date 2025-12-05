// app/api/job-records/route.ts
import { NextRequest, NextResponse } from "next/server";

const FASTAPI_BASE =
  process.env.FASTAPI_BASE_URL || "http://backend:8000"; // adjust if needed

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = req.nextUrl;
    const queryString = searchParams.toString();

    const fastApiUrl = `${FASTAPI_BASE}/job-records${
      queryString ? `?${queryString}` : ""
    }`;

    const res = await fetch(fastApiUrl, {
      method: "GET",
      headers: {
        accept: "application/json",
      },
      cache: "no-store", // always fresh
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
            `Failed to fetch job records from FastAPI (status ${res.status}).`,
        },
        { status: res.status },
      );
    }

    // Pass through FastAPI JSON
    const data = JSON.parse(text);
    return NextResponse.json(data, { status: 200 });
  } catch (error: any) {
    console.error("Error in /api/job-records:", error);
    return NextResponse.json(
      {
        success: false,
        detail: "The server is currently unavailable. Please try again later.",
      },
      { status: 500 },
    );
  }
}
