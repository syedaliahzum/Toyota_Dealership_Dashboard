// app/api/rework-rate-by-date/route.ts
import { NextRequest, NextResponse } from "next/server";

const FASTAPI_BASE =
  process.env.FASTAPI_BASE_URL || "http://backend:8000";

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = req.nextUrl;
    const queryString = searchParams.toString();

    const fastApiUrl = `${FASTAPI_BASE}/rework-rate-by-date${
      queryString ? `?${queryString}` : ""
    }`;

    const res = await fetch(fastApiUrl, {
      method: "GET",
      headers: {
        accept: "application/json",
      },
      cache: "no-store",
    });

    if (!res.ok) {
      const text = await res.text().catch(() => "");
      return NextResponse.json(
        {
          success: false,
          detail: `FastAPI /rework-rate-by-date error: ${res.status} ${res.statusText}`,
          raw: text,
        },
        { status: res.status }
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (err) {
    console.error("Error calling /rework-rate-by-date:", err);
    return NextResponse.json(
      {
        success: false,
        detail: "Unexpected error calling FastAPI /rework-rate-by-date",
      },
      { status: 500 }
    );
  }
}
