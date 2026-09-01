import { NextRequest, NextResponse } from "next/server";

const API = process.env.WEBPOSTO_API_URL || "http://127.0.0.1:8040";

export async function GET(request: NextRequest) {
  const view = request.nextUrl.searchParams.get("view") || "summary";
  const path = view === "blocks"
    ? "/api/v1/departmental-governance/executive-adoption/block-review"
    : "/api/v1/departmental-governance/executive-adoption/summary";
  try {
    const response = await fetch(`${API}${path}`, {
      cache: "no-store",
      headers: { cookie: request.headers.get("cookie") || "" },
    });
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json({ success: false, error: "Internal Server Error" }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const response = await fetch(`${API}/api/v1/departmental-governance/executive-adoption/events`, {
      method: "POST",
      headers: { "Content-Type": "application/json", cookie: request.headers.get("cookie") || "" },
      body: JSON.stringify(body),
    });
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json({ success: false, error: "Internal Server Error" }, { status: 500 });
  }
}
