import { NextRequest, NextResponse } from "next/server";

const API = process.env.WEBPOSTO_API_URL || "http://127.0.0.1:8000";

export async function POST(request: NextRequest) {
  const response = await fetch(`${API}/api/v1/departmental-governance/executive-adoption/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json", cookie: request.headers.get("cookie") || "" },
    body: JSON.stringify(await request.json()),
  });
  return NextResponse.json(await response.json(), { status: response.status });
}
