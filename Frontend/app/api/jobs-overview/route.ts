// app/api/jobs-overview/route.ts
import { NextResponse } from "next/server";

const FASTAPI_BASE = process.env.FASTAPI_BASE_URL || "http://backend:8000";

export async function GET() {
  try {
    const res = await fetch(`${FASTAPI_BASE}/jobs-overview`, {
      headers: { accept: "application/json" },
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
            `Failed to fetch jobs overview from FastAPI (status ${res.status}).`,
        },
        { status: res.status },
      );
    }

    const data = JSON.parse(text);
    return NextResponse.json(data);
  } catch (error: any) {
    console.error("Error in /api/jobs-overview:", error);
    return NextResponse.json(
      {
        success: false,
        detail: "The server is currently unavailable. Please try again later.",
      },
      { status: 500 },
    );
  }
}
