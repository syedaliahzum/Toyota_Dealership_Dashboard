// app/api/upload-reports/route.ts
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const API_BASE =
  process.env.API_URL?.replace(/\/$/, "") || "http://backend:8000";

async function passThrough(upstream: Response) {
  const bodyText = await upstream.text();
  const contentType =
    upstream.headers.get("content-type") || "application/json";
  return new Response(bodyText, {
    status: upstream.status,
    headers: { "content-type": contentType },
  });
}

// rebuild FormData to avoid stream issues
async function cloneFormData(fd: FormData) {
  const out = new FormData();
  for (const [key, value] of fd.entries()) {
    if (typeof value === "string") {
      out.append(key, value);
    } else {
      const file = value as File;
      const buf = await file.arrayBuffer();
      const blob = new Blob([buf], { type: file.type || "application/pdf" });
      out.append(key, blob, file.name);
    }
  }
  return out;
}

export async function POST(req: Request) {
  const target = `${API_BASE}/upload-reports`;
  const ac = new AbortController();
  const t = setTimeout(() => ac.abort(), 45_000);

  try {
    if (!API_BASE) {
      console.error("[upload-reports] API_BASE_URL missing");
      return new Response(JSON.stringify({ detail: "API_BASE_URL not set" }), {
        status: 500,
      });
    }

    const incoming = await req.formData();
    const formData = await cloneFormData(incoming);

    const upstream = await fetch(target, {
      method: "POST",
      body: formData,
      signal: ac.signal, // don't set Content-Type manually
    });

    clearTimeout(t);
    return passThrough(upstream);
  } catch (err: any) {
    clearTimeout(t);
    console.error("[upload-reports] proxy error:", err?.name, err?.message);
    const detail =
      err?.name === "AbortError"
        ? "Proxy timeout contacting FastAPI"
        : `Proxy error: ${err?.message || "Unknown error"}`;
    return new Response(JSON.stringify({ detail }), { status: 502 });
  }
}

// Handle preflight so browsers don't return 405 before POST
export async function OPTIONS() {
  return new Response(null, {
    status: 204,
    headers: {
      "Access-Control-Allow-Methods": "POST, OPTIONS, GET",
      "Access-Control-Allow-Headers": "*",
    },
  });
}

// Simple health probe via GET /api/upload-reports?health=1
export async function GET(req: Request) {
  const url = new URL(req.url);
  if (url.searchParams.get("health") === "1") {
    try {
      const res = await fetch(`${API_BASE}/health`);
      return passThrough(res);
    } catch (e: any) {
      console.error("[upload-reports GET health] error:", e?.message);
      return new Response(
        JSON.stringify({ detail: "Unable to reach FastAPI /health" }),
        { status: 502 }
      );
    }
  }
  return new Response(JSON.stringify({ detail: "Method not allowed" }), {
    status: 405,
  });
}
