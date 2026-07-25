import { NextRequest, NextResponse } from "next/server";

const API = process.env.WEBPOSTO_API_URL || "http://127.0.0.1:8000";

export async function GET(request: NextRequest) {
  const day = request.nextUrl.searchParams.get("day") || "";
  const month = day.slice(0, 7);
  const headers = { cookie: request.headers.get("cookie") || "" };
  const paths = [
    `/api/v1/departmental-governance/proactive-radar?data=${encodeURIComponent(day)}`,
    `/api/v1/departmental-governance/proactive-agents?data=${encodeURIComponent(day)}`,
    `/api/v1/departmental-governance/proactive-value?month=${encodeURIComponent(month)}`,
  ];
  const results = await Promise.all(paths.map(async path => {
    const response = await fetch(`${API}${path}`, { cache: "no-store", headers });
    if (!response.ok) return null;
    return (await response.json()).data;
  }));
  return NextResponse.json({ radar: results[0], agents: results[1], value: results[2] });
}
