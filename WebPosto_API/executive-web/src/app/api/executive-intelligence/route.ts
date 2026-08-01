import { NextRequest, NextResponse } from "next/server";

const API = process.env.WEBPOSTO_API_URL || "http://127.0.0.1:8040";

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
    try {
      const response = await fetch(`${API}${path}`, { cache: "no-store", headers });
      if (!response.ok) return null;
      const data = await response.json();
      return data?.data || null;
    } catch (err) {
      console.error(`Error fetching ${path}:`, err);
      return null;
    }
  }));
  return NextResponse.json({ radar: results[0], agents: results[1], value: results[2] });
}
