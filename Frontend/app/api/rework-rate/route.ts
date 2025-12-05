// app/api/rework-rate/route.ts
import { NextRequest, NextResponse } from "next/server";

const FASTAPI_BASE =
  process.env.FASTAPI_BASE_URL || "http://backend:8000";

export async function GET(_req: NextRequest) {
  try {
    const fastApiUrl = `${FASTAPI_BASE}/rework-rate`;

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
          detail: `The server is currently unavailable. Please try again later.`,
          raw: text,
        },
        { status: res.status }
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (err) {
    console.error("Error calling /rework-rate:", err);
    return NextResponse.json(
      {
        success: false,
        detail: "The server is currently unavailable. Please try again later.",
      },
      { status: 500 }
    );
  }
}
